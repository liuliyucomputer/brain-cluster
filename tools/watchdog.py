# -*- coding: utf-8 -*-
"""
Brain 集群 — Agent Watchdog (自愈引擎) v2.2
功能: 每30秒扫描 Hermes 真实运行态，基于 task_runs/heartbeat 检测卡死，
      使用 `hermes kanban reclaim` 进行安全恢复，不直接修改 task 主状态。
版本: v2.2 | 2026-06-08 重构
"""
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import KANBAN_DB, LOGS_DIR

POLL_INTERVAL = 30
RUNNING_AGE_THRESHOLD = 300
HEARTBEAT_STALE_THRESHOLD = 300
RESTART_COOLDOWN = 300
MAX_RESTART_PER_HOUR = 5

WATCHDOG_STATE = os.path.join(LOGS_DIR, "watchdog", "watchdog_state.json")
RECOVERY_LOG = os.path.join(LOGS_DIR, "watchdog", "recovery_events.jsonl")
os.makedirs(os.path.dirname(WATCHDOG_STATE), exist_ok=True)


def _load_state():
    """加载 watchdog 状态"""
    if os.path.exists(WATCHDOG_STATE):
        with open(WATCHDOG_STATE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "restart_history": {},
        "recovery_count": 0,
        "last_scan": None,
        "last_reclaimed_task_ids": [],
        "metrics": {
            "stuck_detected_total": 0,
            "reclaim_success_total": 0,
            "reclaim_fail_total": 0,
            "avg_recovery_time_ms": 0,
        },
    }


def _save_state(state):
    with open(WATCHDOG_STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _log_recovery(event):
    """记录恢复事件到日志"""
    event["ts"] = datetime.now().isoformat()
    with open(RECOVERY_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _run_command(args, timeout=20):
    env = os.environ.copy()
    env["GATEWAY_ALLOW_ALL_USERS"] = "true"
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def _can_restart(agent_name, state):
    """检查 Agent 是否可以重启（防抖）"""
    now = time.time()
    history = state["restart_history"]

    for key in list(history.keys()):
        if now - history[key] > 3600:
            del history[key]

    recent_restart = history.get(agent_name)
    if recent_restart and now - recent_restart < RESTART_COOLDOWN:
        return False

    recent_count = sum(
        1 for key, ts in history.items()
        if key == agent_name and now - ts < 3600
    )
    return recent_count < MAX_RESTART_PER_HOUR


def _restart_agent(agent_name, state):
    """可选地唤起同名 profile，避免恢复后无 worker 可领任务"""
    if not agent_name or not _can_restart(agent_name, state):
        return False

    result = _run_command(["hermes", "profile", "start", agent_name], timeout=15)
    success = result.returncode == 0 or "started" in (result.stdout + result.stderr).lower()
    if success:
        state["restart_history"][agent_name] = time.time()
        _log_recovery({
            "action": "restart_agent",
            "agent": agent_name,
            "success": True,
            "output": (result.stdout or "")[:200],
        })
        return True

    _log_recovery({
        "action": "restart_agent",
        "agent": agent_name,
        "success": False,
        "error": (result.stderr or result.stdout or "")[:200],
    })
    return False


def _get_stuck_runs():
    """
    基于 task_runs 表检测卡死运行。
    只看 status='running' 的 run 记录，检查 last_heartbeat_at 超时。
    """
    conn = sqlite3.connect(KANBAN_DB, timeout=3)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    now = int(time.time())

    # 查询 task_runs 中 status='running' 且 heartbeat 超时的记录
    cursor.execute(
        """
        SELECT
            r.id AS run_id,
            r.task_id,
            r.profile AS agent,
            r.started_at,
            r.last_heartbeat_at,
            r.claim_expires,
            r.outcome,
            t.title,
            t.status AS task_status
        FROM task_runs r
        JOIN tasks t ON t.id = r.task_id
        WHERE r.status = 'running'
        """
    )
    rows = cursor.fetchall()
    conn.close()

    stuck_runs = []
    for row in rows:
        started_at = row["started_at"]
        if started_at is None:
            continue

        running_age = now - int(started_at)
        last_heartbeat_at = row["last_heartbeat_at"]
        heartbeat_age = None if last_heartbeat_at is None else now - int(last_heartbeat_at)
        claim_expires = row["claim_expires"]
        claim_expired = claim_expires is not None and now > int(claim_expires)

        # 卡死判定：运行时间超阈值 AND (心跳超时 OR claim 过期)
        stale_by_runtime = running_age >= RUNNING_AGE_THRESHOLD
        stale_by_heartbeat = last_heartbeat_at is None or heartbeat_age >= HEARTBEAT_STALE_THRESHOLD

        if stale_by_runtime and (stale_by_heartbeat or claim_expired):
            stuck_runs.append({
                "run_id": row["run_id"],
                "task_id": row["task_id"],
                "title": row["title"],
                "agent": row["agent"],
                "task_status": row["task_status"],
                "started_at": started_at,
                "running_age_seconds": running_age,
                "heartbeat_age_seconds": heartbeat_age,
                "claim_expired": claim_expired,
                "outcome": row["outcome"],
            })
    return stuck_runs


def _reclaim_run(run_info):
    """
    通过 Hermes 原生命令 reclaim 卡死任务。
    不直接 UPDATE tasks，只调用 reclaim API。
    """
    task_id = run_info["task_id"]
    run_id = run_info["run_id"]
    reason = (
        f"watchdog stuck run={run_id} "
        f"running_age={run_info.get('running_age_seconds')} "
        f"heartbeat_age={run_info.get('heartbeat_age_seconds')} "
        f"claim_expired={run_info.get('claim_expired')}"
    )

    start_time = time.time()
    result = _run_command(
        ["hermes", "kanban", "reclaim", task_id, "--reason", reason],
        timeout=20,
    )
    elapsed_ms = int((time.time() - start_time) * 1000)

    success = result.returncode == 0
    _log_recovery({
        "action": "reclaim_run",
        "task_id": task_id,
        "run_id": run_id,
        "agent": run_info.get("agent"),
        "running_age_seconds": run_info.get("running_age_seconds"),
        "heartbeat_age_seconds": run_info.get("heartbeat_age_seconds"),
        "claim_expired": run_info.get("claim_expired"),
        "success": success,
        "elapsed_ms": elapsed_ms,
        "output": ((result.stdout or "") + (result.stderr or ""))[:300],
    })
    return success, elapsed_ms


def _notify_retry(task_id, run_id, agent):
    """
    写入 task_event 通知编排层需要重试。
    不直接创建重试任务，让编排层决定策略。
    """
    event = {
        "action": "notify_retry",
        "task_id": task_id,
        "run_id": run_id,
        "agent": agent,
        "reason": "watchdog_detected_stuck",
        "ts": datetime.now().isoformat(),
    }
    _log_recovery(event)

    # 尝试写入 Hermes task_events 表
    try:
        conn = sqlite3.connect(KANBAN_DB, timeout=3)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO task_events (task_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
            (task_id, "watchdog_retry", json.dumps(event), int(time.time()))
        )
        conn.commit()
        conn.close()
    except Exception as e:
        _log_recovery({
            "action": "notify_retry_db_fail",
            "task_id": task_id,
            "error": str(e),
        })


def scan_and_heal():
    """核心：扫描 + 自愈"""
    state = _load_state()
    stuck_runs = _get_stuck_runs()
    reclaimed = 0
    restarted = 0
    reclaim_fail = 0
    reclaimed_task_ids = []
    total_recovery_time = 0

    for run_info in stuck_runs:
        print(
            f"[WATCHDOG] Stuck run detected: run={run_info['run_id']} "
            f"task={run_info['task_id']} ({run_info.get('agent')}) "
            f"run_age={int(run_info['running_age_seconds'])}s "
            f"hb_age={run_info.get('heartbeat_age_seconds')} "
            f"claim_expired={run_info.get('claim_expired')}"
        )

        success, elapsed_ms = _reclaim_run(run_info)
        total_recovery_time += elapsed_ms

        if success:
            reclaimed += 1
            reclaimed_task_ids.append(run_info["task_id"])
            state["recovery_count"] += 1

            # 通知编排层需要重试
            _notify_retry(run_info["task_id"], run_info["run_id"], run_info.get("agent"))

            # 尝试重启 agent profile
            if run_info.get("agent") and _restart_agent(run_info["agent"], state):
                restarted += 1
        else:
            reclaim_fail += 1

    # 更新指标
    metrics = state.get("metrics", {})
    metrics["stuck_detected_total"] = metrics.get("stuck_detected_total", 0) + len(stuck_runs)
    metrics["reclaim_success_total"] = metrics.get("reclaim_success_total", 0) + reclaimed
    metrics["reclaim_fail_total"] = metrics.get("reclaim_fail_total", 0) + reclaim_fail
    if reclaimed > 0:
        avg_time = metrics.get("avg_recovery_time_ms", 0)
        total_reclaimed = metrics["reclaim_success_total"]
        metrics["avg_recovery_time_ms"] = int(
            (avg_time * (total_reclaimed - reclaimed) + total_recovery_time) / total_reclaimed
        )
    state["metrics"] = metrics

    state["last_scan"] = datetime.now().isoformat()
    state["last_reclaimed_task_ids"] = reclaimed_task_ids
    _save_state(state)
    return len(stuck_runs), reclaimed, restarted


def run_daemon():
    """持续运行"""
    print("=== Brain Watchdog v2.2 started (30s interval) ===")
    print(f"  Kanban DB: {KANBAN_DB}")
    print(f"  Running-age threshold: {RUNNING_AGE_THRESHOLD}s")
    print(f"  Heartbeat-stale threshold: {HEARTBEAT_STALE_THRESHOLD}s")
    print(f"  Restart cooldown: {RESTART_COOLDOWN}s")
    print(f"  Recovery log: {RECOVERY_LOG}")
    print("  Mode: task_runs-based detection, reclaim-only recovery")
    print("-" * 50)

    try:
        while True:
            ts = datetime.now().strftime("%H:%M:%S")
            stuck_count, reclaimed, restarted = scan_and_heal()
            if stuck_count > 0:
                print(
                    f"[{ts}] WATCHDOG: {stuck_count} stuck runs, "
                    f"{reclaimed} reclaimed, {restarted} profile restarts"
                )
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        state = _load_state()
        print(f"\nWatchdog stopped. Total recoveries: {state['recovery_count']}")


def status():
    """查看 watchdog 状态"""
    state = _load_state()
    print("=== Watchdog Status ===")
    print(f"  Total recoveries: {state['recovery_count']}")
    metrics = state.get("metrics", {})
    print(f"  Stuck detected total: {metrics.get('stuck_detected_total', 0)}")
    print(f"  Reclaim success: {metrics.get('reclaim_success_total', 0)}")
    print(f"  Reclaim fail: {metrics.get('reclaim_fail_total', 0)}")
    print(f"  Avg recovery time: {metrics.get('avg_recovery_time_ms', 0)}ms")
    print(f"  Last scan: {state.get('last_scan')}")
    print(f"  Last reclaimed tasks: {state.get('last_reclaimed_task_ids', [])}")
    print(f"  Restart history: {len(state['restart_history'])} entries")
    if state["restart_history"]:
        for key, ts in sorted(state["restart_history"].items(), key=lambda item: -item[1]):
            print(f"    {key}: {datetime.fromtimestamp(ts).strftime('%H:%M:%S')}")

    if os.path.exists(RECOVERY_LOG):
        with open(RECOVERY_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()
        recent = lines[-5:] if lines else []
        if recent:
            print(f"  Recent recoveries ({len(recent)}):")
            for line in recent:
                event = json.loads(line)
                print(
                    f"    [{event.get('action', '?')}] "
                    f"{event.get('task_id') or event.get('agent')}: "
                    f"{event.get('success', '?')}"
                )


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        run_daemon()
    elif "--status" in sys.argv:
        status()
    else:
        print("USAGE: python watchdog.py [--daemon | --status]")
        print("  --daemon   Run continuously in background")
        print("  --status   Show watchdog statistics")
