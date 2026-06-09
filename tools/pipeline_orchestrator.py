# -*- coding: utf-8 -*-
"""
Brain 集群 — 流水线编排引擎 v2.0 (Pipeline Orchestrator)
监听 kanban.db, 自动串联: 执行→审查→仲裁→完成
v2.0 新增: 3轮渐进式重试 (换策略→换Agent→重分析→escalate)
"""
import sqlite3, subprocess, os, time, json, sys, re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import KANBAN_DB, TOOLS_DIR, LOGS_DIR
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memory_bridge import sync_kanban_to_memory

POLL_INTERVAL = 30          # 每30秒扫描一次
MAX_RETRY_ROUNDS = 3        # 最多3轮重试
RETRY_STATE_FILE = os.path.join(LOGS_DIR, "orchestrator", "retry_state.json")

EXECUTORS = ["executor-a", "executor-b", "executor-c"]
REVIEWERS = ["reviewer-strict", "reviewer-creative"]
TASK_ID_RE = re.compile(r"\b(t_[a-f0-9]+)\b")

# ── 策略模板轮换 ──
ALT_STRATEGIES = {
    "executor-a": ["换用爆款标题公式", "加入SEO关键词", "缩短段落至3行以内", "增加互动提问"],
    "executor-b": ["简化版式、减少文字", "数据可视化优先", "故事线叙事结构", "对比冲突风格"],
    "executor-c": ["增加数据验证步骤", "先做探索性分析", "更换统计方法", "增加异常检测"],
}

# ── 信誉分扣减策略 ──
SCORE_PENALTIES = {1: 0.10, 2: 0.20, 3: 0.30}  # 随轮次递增


def _load_retry_state():
    """加载重试状态（持久化，daemon重启不丢失）"""
    if os.path.exists(RETRY_STATE_FILE):
        with open(RETRY_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"retry_counts": {}, "escalated": [], "last_cleanup": datetime.now().isoformat()}


def _save_retry_state(state):
    os.makedirs(os.path.dirname(RETRY_STATE_FILE), exist_ok=True)
    with open(RETRY_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _cleanup_old_retries(state, max_age_hours=24):
    """清理超过24小时的旧重试记录"""
    cutoff = datetime.now()
    old_count = 0
    for task_id in list(state["retry_counts"].keys()):
        entry = state["retry_counts"].get(task_id, {})
        try:
            last = datetime.fromisoformat(entry.get("last_retry", "2000-01-01"))
            if (cutoff - last).total_seconds() > max_age_hours * 3600:
                del state["retry_counts"][task_id]
                old_count += 1
        except Exception:
            del state["retry_counts"][task_id]
    if old_count > 0:
        state["last_cleanup"] = cutoff.isoformat()


def get_done_tasks_without_review():
    """找出已完成但未审查的executor任务"""
    conn = sqlite3.connect(KANBAN_DB)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT t.id, t.title, t.assignee
            FROM tasks t
            WHERE t.status='done'
              AND t.assignee IN ('executor-a','executor-b','executor-c')
              AND NOT EXISTS (
                  SELECT 1
                  FROM task_links l
                  JOIN tasks c ON c.id = l.child_id
                  WHERE l.parent_id = t.id
                    AND c.assignee IN ('reviewer-strict','reviewer-creative')
              )
            ORDER BY rowid DESC
            LIMIT 10
        """)
    except Exception:
        cursor.execute("SELECT id, title, assignee FROM tasks WHERE status='done' LIMIT 5")

    try:
        tasks = [{"id": r[0], "title": r[1], "assignee": r[2]} for r in cursor.fetchall()]
    except Exception:
        tasks = []
    finally:
        conn.close()
    return tasks


def create_review_tasks(executor_task):
    """为executor产出创建双审任务"""
    task_id = executor_task["id"]
    title = executor_task["title"]
    created = []
    env = os.environ.copy()

    for reviewer in REVIEWERS:
        review_title = f"REVIEW[{reviewer}]: {title}"
        r = subprocess.run(
            ["hermes", "kanban", "create", review_title, "--assignee", reviewer, "--parent", task_id],
            capture_output=True, text=True, env=env, timeout=30
        )
        if "Created" in r.stdout:
            match = TASK_ID_RE.search(r.stdout)
            review_id = match.group(1) if match else None
            created.append({"reviewer": reviewer, "id": review_id})
            print(f"  created review: {reviewer} -> {review_id}")

    return created


def _parse_scores_from_reviews(reviews):
    """从审查结果中提取评分"""
    scores = {}
    for rv in reviews:
        try:
            result = json.loads(rv["result"]) if rv["result"] else {"total": 50}
        except Exception:
            result = {"total": 50}
        scores[rv["reviewer"]] = result.get("total", 50)
    return scores


def check_review_results(review_task_ids):
    """检查双审结果，分歧时触发仲裁 (保留原有接口兼容)"""
    conn = sqlite3.connect(KANBAN_DB)
    cursor = conn.cursor()
    scores = {}

    for r in review_task_ids:
        cursor.execute("SELECT status, result FROM tasks WHERE id=?", (r["id"],))
        row = cursor.fetchone()
        if row and row[0] == "done":
            try:
                result = json.loads(row[1]) if row[1] else {"total": 50}
            except:
                result = {"total": 50}
            scores[r["reviewer"]] = result.get("total", 50)

    conn.close()

    if len(scores) < 2:
        return False

    strict_score = scores.get("reviewer-strict", 50)
    creative_score = scores.get("reviewer-creative", 50)

    if strict_score >= 60 and creative_score >= 50:
        return "pass"
    elif strict_score < 60 and creative_score < 50:
        return "fail"
    else:
        return "split"


def create_arbiter_task(parent_id, scores):
    """创建仲裁任务"""
    env = os.environ.copy()
    title = f"ARBITER: split decision on {parent_id} (strict:{scores.get('reviewer-strict')} vs creative:{scores.get('reviewer-creative')})"
    r = subprocess.run(
        ["hermes", "kanban", "create", title, "--assignee", "arbiter", "--parent", parent_id],
        capture_output=True, text=True, env=env, timeout=30
    )
    print(f"  created arbiter: {r.stdout[:60].strip()}")


# ═══════════════════════════════════════════
#  v2.0: 3轮渐进式重试
# ═══════════════════════════════════════════

def _get_alt_executor(current_executor, retry_round):
    """获取替代 executor（按积分轮换）"""
    others = [e for e in EXECUTORS if e != current_executor]
    if not others:
        return current_executor
    return others[retry_round % len(others)]


def _get_alt_strategy(executor_name, retry_round):
    """获取替代策略模板"""
    strategies = ALT_STRATEGIES.get(executor_name, ["尝试不同方法"])
    return strategies[retry_round % len(strategies)]


def _apply_reputation_penalty(parent_id, retry_round, state):
    """对任务的原 executor 扣信誉分"""
    # 获取原任务的 assignee
    conn = sqlite3.connect(KANBAN_DB, timeout=3)
    cursor = conn.cursor()
    cursor.execute("SELECT assignee FROM tasks WHERE id=?", (parent_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return

    assignee = row[0]
    penalty = SCORE_PENALTIES.get(retry_round, 0.30)

    # 写入惩罚记录（后续由 memory_bridge 同步到 reputation.json）
    penalty_log = os.path.join(LOGS_DIR, "orchestrator", "reputation_penalties.jsonl")
    os.makedirs(os.path.dirname(penalty_log), exist_ok=True)
    with open(penalty_log, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.now().isoformat(),
            "task_id": parent_id,
            "agent": assignee,
            "penalty": penalty,
            "retry_round": retry_round,
        }, ensure_ascii=False) + "\n")

    print(f"  reputation penalty: {assignee} -{penalty} (round {retry_round})")


def _handle_fail_with_retry(parent_id, parent_title, current_assignee, scores, state):
    """处理 FAIL: 3轮渐进式重试"""
    entry = state["retry_counts"].get(parent_id, {"count": 0, "last_retry": ""})
    retry_count = entry.get("count", 0) + 1
    entry = {"count": retry_count, "last_retry": datetime.now().isoformat(),
             "assignee": current_assignee, "scores": scores}
    state["retry_counts"][parent_id] = entry
    _save_retry_state(state)

    strict_score = scores.get("reviewer-strict", 50)
    creative_score = scores.get("reviewer-creative", 50)

    if retry_count > MAX_RETRY_ROUNDS:
        return _escalate_to_human(parent_id, parent_title, retry_count, scores, state)

    # 扣信誉分
    _apply_reputation_penalty(parent_id, retry_count, state)

    if retry_count == 1:
        # 第1轮: 换策略模板 + 派发原 executor
        alt_st = _get_alt_strategy(current_assignee, 0)
        retry_title = f"RETRY[R{retry_count}][src:{parent_id}]: {parent_title} (策略: {alt_st})"
        retry_assignee = current_assignee
        print(f"  RETRY ROUND {retry_count}: new strategy '{alt_st}' -> {retry_assignee}")

    elif retry_count == 2:
        # 第2轮: 换 executor + 换策略模板
        alt_st = _get_alt_strategy(current_assignee, 1)
        retry_assignee = _get_alt_executor(current_assignee, 1)
        retry_title = f"RETRY[R{retry_count}][src:{parent_id}]: {parent_title} (策略: {alt_st}, 换Agent: {retry_assignee})"
        print(f"  RETRY ROUND {retry_count}: new executor '{retry_assignee}' + strategy '{alt_st}'")

    else:
        # 第3轮: strategist 重新分析
        retry_title = f"RETRY[R{retry_count}][src:{parent_id}]: {parent_title} (strategist 重新分析, scores: s={strict_score}/c={creative_score})"
        retry_assignee = "strategist"
        print(f"  RETRY ROUND {retry_count}: escalate to strategist for re-analysis")

    # 创建重试任务
    env = os.environ.copy()
    r = subprocess.run(
        ["hermes", "kanban", "create", retry_title, "--assignee", retry_assignee],
        capture_output=True, text=True, env=env, timeout=30
    )
    if "Created" in r.stdout:
        print(f"  retry task created: {r.stdout[:60].strip()}")
    else:
        print(f"  retry task failed: {r.stderr[:100].strip()}")


def _escalate_to_human(parent_id, parent_title, retry_count, scores, state):
    """重试耗尽，升级到人类"""
    state["escalated"].append({
        "task_id": parent_id,
        "title": parent_title,
        "retries": retry_count,
        "scores": scores,
        "ts": datetime.now().isoformat()
    })
    _save_retry_state(state)

    escalation_log = os.path.join(LOGS_DIR, "orchestrator", "escalations.jsonl")
    os.makedirs(os.path.dirname(escalation_log), exist_ok=True)
    with open(escalation_log, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": datetime.now().isoformat(),
            "task_id": parent_id,
            "title": parent_title,
            "retries": retry_count,
            "scores": scores,
            "status": "AWAITING_HUMAN",
        }, ensure_ascii=False) + "\n")

    # 标记任务为 blocked（不再自动处理）
    conn = sqlite3.connect(KANBAN_DB, timeout=3)
    try:
        conn.execute("UPDATE tasks SET status='blocked' WHERE id=?", (parent_id,))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()

    print(f"  ESCALATED to human: task {parent_id} failed after {retry_count} retries")
    print(f"  scores: strict={scores.get('reviewer-strict')} creative={scores.get('reviewer-creative')}")
    return "escalated"


# ═══════════════════════════════════════════
#  Schema probing
# ═══════════════════════════════════════════

__schema_probed = False
__has_completed_at = False
__has_result_col = False


def _probe_schema():
    global __schema_probed, __has_completed_at, __has_result_col
    if __schema_probed:
        return
    conn = sqlite3.connect(KANBAN_DB)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(tasks)")
    cols = [r[1] for r in cursor.fetchall()]
    conn.close()
    __has_completed_at = "completed_at" in cols
    __has_result_col = "result" in cols
    __schema_probed = True


def _mark_parent_done(parent_id):
    """当 retry 任务 PASS 后，标记原父任务为 done（清理循环引用）"""
    conn = sqlite3.connect(KANBAN_DB, timeout=3)
    try:
        conn.execute("UPDATE tasks SET status='done' WHERE id=?", (parent_id,))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def _get_retry_source_id(title):
    """从重试任务标题中提取原始任务ID"""
    match = re.search(r"\[src:(t_[a-f0-9]+)\]", title or "")
    return match.group(1) if match else None


def run_once():
    """一次扫描周期"""
    _probe_schema()
    state = _load_retry_state()
    _cleanup_old_retries(state)
    ts = datetime.now().strftime("%H:%M:%S")

    # 1. 扫描已完成但未审查的 executor 任务
    tasks = get_done_tasks_without_review()
    if tasks:
        print(f"\n[{ts}] Found {len(tasks)} done tasks without review")
        for task in tasks[:3]:
            # 检查是否是重试任务（title 以 RETRY 开头，避免误判普通任务）
            is_retry = str(task.get("title", "")).startswith("RETRY")
            print(f"  Processing: {task['id']} by {task['assignee']}" + (" [RETRY]" if is_retry else ""))
            created = create_review_tasks(task)
            if created:
                time.sleep(2)

    # 2. 检查已完成的审查任务，触发仲裁、重试或标记完成
    conn = sqlite3.connect(KANBAN_DB)
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, title, status, result FROM tasks
            WHERE title LIKE 'REVIEW%' AND status='done'
            ORDER BY rowid DESC LIMIT 20
        """)
    except Exception:
        cursor.execute("SELECT id, title, status, result FROM tasks WHERE title LIKE 'REVIEW%' AND status='done' LIMIT 20")

    review_tasks = cursor.fetchall()
    conn.close()

    if review_tasks:
        parent_groups = {}
        conn = sqlite3.connect(KANBAN_DB, timeout=3)
        cursor = conn.cursor()
        for rt in review_tasks:
            rid, rtitle, rstatus, rresult = rt
            reviewer_match = re.search(r'REVIEW\[([^\]]+)\]', rtitle or "")
            reviewer = reviewer_match.group(1) if reviewer_match else "unknown"
            parent_id = None
            try:
                cursor.execute("SELECT parent_id FROM task_links WHERE child_id=? LIMIT 1", (rid,))
                row = cursor.fetchone()
                parent_id = row[0] if row else None
            except Exception:
                parent_id = None

            # 兼容旧版本标题里写 parent 的历史任务
            if not parent_id:
                match = re.search(r'\(parent:\s*(\S+)\)', rtitle or "")
                parent_id = match.group(1) if match else None

            if parent_id:
                if parent_id not in parent_groups:
                    parent_groups[parent_id] = {}
                parent_groups[parent_id][reviewer] = {
                    "id": rid, "reviewer": reviewer, "result": rresult
                }
        conn.close()

        for parent_id, review_map in parent_groups.items():
            reviews = list(review_map.values())
            if len(reviews) < 2:
                continue

            scores = _parse_scores_from_reviews(reviews)
            strict_score = scores.get("reviewer-strict", 50)
            creative_score = scores.get("reviewer-creative", 50)
            strict_pass = strict_score >= 60
            creative_pass = creative_score >= 50

            # 获取原任务信息
            conn = sqlite3.connect(KANBAN_DB, timeout=3)
            cursor = conn.cursor()
            cursor.execute("SELECT title, assignee FROM tasks WHERE id=?", (parent_id,))
            parent_row = cursor.fetchone()
            conn.close()
            parent_title = parent_row[0] if parent_row else str(parent_id)
            parent_assignee = parent_row[1] if parent_row else "executor-a"

            if strict_pass and creative_pass:
                print(f"  PASS for {parent_id}: strict={strict_score}, creative={creative_score}")
                # 清除重试记录（任务已成功）
                if parent_id in state["retry_counts"]:
                    del state["retry_counts"][parent_id]
                    _save_retry_state(state)
                # 如果是重试任务，补标记其原始任务完成
                if parent_title.startswith("RETRY["):
                    source_id = _get_retry_source_id(parent_title)
                    if source_id:
                        _mark_parent_done(source_id)
                # 持久化产出到 daily/ 记忆
                try:
                    sync_kanban_to_memory()
                    print(f"  memory synced: output saved to daily/")
                except Exception as e:
                    print(f"  memory sync failed: {e}")

            elif not strict_pass and not creative_pass:
                # 双否决 → 触发重试
                print(f"  FAIL for {parent_id}: strict={strict_score}, creative={creative_score}")
                _handle_fail_with_retry(parent_id, parent_title, parent_assignee, scores, state)

            else:
                # 分歧 → 仲裁
                print(f"  SPLIT for {parent_id}: strict={strict_score}, creative={creative_score}")
                create_arbiter_task(parent_id, scores)

    return len(tasks) if tasks else 0


def run_daemon():
    """持续运行"""
    print("=== Pipeline Orchestrator v2.0 started (30s interval) ===")
    print(f"  Max retry rounds: {MAX_RETRY_ROUNDS}")
    print(f"  Retry state file: {RETRY_STATE_FILE}")
    print("-" * 55)
    try:
        while True:
            run_once()
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\nOrchestrator stopped.")


def run_once_and_exit():
    run_once()


def status():
    """查看重试状态"""
    state = _load_retry_state()
    print("=== Retry State ===")
    print(f"  Active retries: {len(state['retry_counts'])}")
    for tid, info in state["retry_counts"].items():
        print(f"    {tid}: {info['count']} retries, last={info['last_retry']}")
    print(f"  Escalated: {len(state['escalated'])}")
    for e in state["escalated"]:
        print(f"    {e['task_id']}: {e['retries']} retries, {e['ts']}")
    print(f"  Last cleanup: {state.get('last_cleanup', 'never')}")


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        run_daemon()
    elif "--status" in sys.argv:
        status()
    else:
        run_once_and_exit()
        print("Done.")
