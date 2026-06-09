"""Star Office UI - Backend Utilities"""

import json
import os
import re
import logging
import sqlite3
import socket
import threading
import queue
import time as _time
from datetime import datetime, timedelta, timezone

from config import (
    ROOT_DIR,
    KANBAN_DB,
    STATE_FILE,
    AGENTS_STATE_FILE,
    JOIN_KEYS_FILE,
    DEFAULT_STATE,
    DEFAULT_AGENTS,
    SERVICE_CONFIGS,
    LOG_ROOT,
    _MEMORY_DIRS,
)

logger = logging.getLogger(__name__)

# ── State helpers ──────────────────────────────────────────

def load_state():
    """Load state from file.

    Includes a simple auto-idle mechanism:
    - If the last update is older than ttl_seconds (default 25s)
      and the state is a "working" state, we fall back to idle.
    """
    state = None
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"[load_state] Failed to load state: {e}")
            state = None

    if not isinstance(state, dict):
        state = dict(DEFAULT_STATE)

    # Auto-idle
    try:
        ttl = int(state.get("ttl_seconds", 300))
        updated_at = state.get("updated_at")
        s = state.get("state", "idle")
        working_states = {"writing", "researching", "executing"}
        if updated_at and s in working_states:
            dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            if dt.tzinfo:
                age = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds()
            else:
                age = (datetime.now() - dt).total_seconds()
            if age > ttl:
                state["state"] = "idle"
                state["detail"] = "待命中（自动回到休息区）"
                state["progress"] = 0
                state["updated_at"] = datetime.now().isoformat()
                try:
                    save_state(state)
                except (IOError, OSError) as e:
                    logger.warning(f"[load_state] Failed to save auto-idle state: {e}")
    except (ValueError, TypeError) as e:
        logger.warning(f"[load_state] Auto-idle calculation error: {e}")

    return state


def save_state(state: dict):
    """Save state to file"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# Initialize state
if not os.path.exists(STATE_FILE):
    save_state(DEFAULT_STATE)


# ── Agents helpers ─────────────────────────────────────────

def load_agents_state():
    if os.path.exists(AGENTS_STATE_FILE):
        try:
            with open(AGENTS_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"[load_agents_state] Failed to load: {e}")
    return list(DEFAULT_AGENTS)


def save_agents_state(agents):
    with open(AGENTS_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(agents, f, ensure_ascii=False, indent=2)


def load_join_keys():
    if os.path.exists(JOIN_KEYS_FILE):
        try:
            with open(JOIN_KEYS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get("keys"), list):
                    return data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"[load_join_keys] Failed to load: {e}")
    return {"keys": []}


def save_join_keys(data):
    with open(JOIN_KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# Ensure files exist
if not os.path.exists(AGENTS_STATE_FILE):
    save_agents_state(DEFAULT_AGENTS)
if not os.path.exists(JOIN_KEYS_FILE):
    save_join_keys({"keys": []})


# ── Agent state normalization ──────────────────────────────

def normalize_agent_state(s):
    """归一化状态，提高兼容性。"""
    if not s:
        return 'idle'
    s_lower = s.lower().strip()
    if s_lower in {'working', 'busy', 'write'}:
        return 'writing'
    if s_lower in {'run', 'running', 'execute', 'exec'}:
        return 'executing'
    if s_lower in {'sync'}:
        return 'syncing'
    if s_lower in {'research', 'search'}:
        return 'researching'
    if s_lower in {'idle', 'writing', 'researching', 'executing', 'syncing', 'error'}:
        return s_lower
    return 'idle'


def state_to_area(state):
    area_map = {
        "idle": "breakroom",
        "writing": "writing",
        "researching": "writing",
        "executing": "writing",
        "syncing": "writing",
        "error": "error"
    }
    return area_map.get(state, "breakroom")


# ── Service helpers ────────────────────────────────────────

def _check_port(port: int) -> bool:
    """Check if a port is open"""
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0
    except socket.error:
        return False
    finally:
        if sock:
            sock.close()


# Track service processes
service_processes: dict = {}
service_lock = threading.Lock()


# ── Stats helpers ──────────────────────────────────────────

def _get_kanban_db():
    db = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "hermes", "kanban.db")
    if not os.path.exists(db):
        db = KANBAN_DB
    return db


def _query_db(sql, params=()):
    try:
        conn = sqlite3.connect(_get_kanban_db(), timeout=3)
        c = conn.cursor()
        c.execute(sql, params)
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception:
        return []


def _query_db_dicts(sql, params=()):
    try:
        conn = sqlite3.connect(_get_kanban_db(), timeout=3)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(sql, params)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


def _load_extensions():
    """Load extension status from file"""
    ext_file = os.path.join(ROOT_DIR, "..", "input", "extensions", "extension_status.json")
    try:
        with open(ext_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"lines": {}, "updated": None}


def _load_self_healing():
    """Load v2.0 self-healing status for dashboard display"""
    result = {
        "watchdog": {"active": False, "recoveries": 0},
        "retry": {"active": False, "active_retries": 0, "escalated": 0},
        "checkpoint": {"active": False, "count": 0}
    }

    memory_dir = os.path.join(ROOT_DIR, "..", "output", "memory")
    logs_dir = os.path.join(ROOT_DIR, "..", "output", "logs")

    wd_state = os.path.join(logs_dir, "watchdog", "watchdog_state.json")
    if os.path.exists(wd_state):
        try:
            with open(wd_state, "r", encoding="utf-8") as f:
                wd = json.load(f)
            result["watchdog"] = {"active": True, "recoveries": wd.get("recovery_count", 0)}
        except Exception:
            pass

    retry_file = os.path.join(logs_dir, "orchestrator", "retry_state.json")
    if os.path.exists(retry_file):
        try:
            with open(retry_file, "r", encoding="utf-8") as f:
                rs = json.load(f)
            result["retry"] = {
                "active": True,
                "active_retries": len(rs.get("retry_counts", {})),
                "escalated": len(rs.get("escalated", []))
            }
        except Exception:
            pass

    cp_dir = os.path.join(memory_dir, "checkpoints")
    if os.path.isdir(cp_dir):
        cps = [f for f in os.listdir(cp_dir) if f.endswith(".json")]
        result["checkpoint"] = {"active": len(cps) > 0, "count": len(cps)}

    return result


def _compute_stats():
    """Enhanced stats: pipeline stages, agent details, recent activity, full task lifecycle"""
    kanban_db = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "hermes", "kanban.db")
    if not os.path.exists(kanban_db):
        kanban_db = os.path.join(ROOT_DIR, "..", "output", "memory", "kanban.db")
    conn = sqlite3.connect(kanban_db)
    conn.row_factory = sqlite3.Row

    now = _time.time()
    day_ago = now - 86400

    task_stats = dict(conn.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status").fetchall())

    agent_rows = conn.execute("""
        SELECT
            assignee,
            COUNT(*) as total,
            SUM(CASE WHEN status NOT IN ('done','archived') THEN 1 ELSE 0 END) as active,
            MAX(last_heartbeat_at) as last_heartbeat,
            SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) as done_count,
            SUM(consecutive_failures) as total_failures
        FROM tasks WHERE assignee IS NOT NULL
        GROUP BY assignee
    """).fetchall()

    agent_details = {}
    for row in agent_rows:
        agent_details[row["assignee"]] = {
            "total": row["total"],
            "active": row["active"],
            "last_heartbeat": row["last_heartbeat"],
            "done": row["done_count"],
            "failures": row["total_failures"],
        }

    pipeline = {}
    stages = [
        ("pending", "status IN ('pending','todo')"),
        ("in_progress", "status IN ('in_progress','running','executing')"),
        ("review", "status IN ('review','reviewing')"),
        ("done", "status='done'"),
        ("archived", "status='archived'"),
    ]
    for stage_key, where_clause in stages:
        rows = conn.execute(f"""
            SELECT id, title, assignee, status, created_at, started_at, completed_at,
                   consecutive_failures, last_heartbeat_at, worker_pid, result
            FROM tasks WHERE {where_clause}
            ORDER BY created_at DESC LIMIT 20
        """).fetchall()
        tasks = []
        for r in rows:
            tasks.append({
                "id": r["id"],
                "title": r["title"],
                "assignee": r["assignee"],
                "status": r["status"],
                "created_at": r["created_at"],
                "started_at": r["started_at"],
                "completed_at": r["completed_at"],
                "failures": r["consecutive_failures"],
                "heartbeat": r["last_heartbeat_at"],
                "worker_pid": r["worker_pid"],
                "result": r["result"][:80] if r["result"] else None,
                "duration": (r["completed_at"] - r["started_at"]) if (r["completed_at"] and r["started_at"]) else None,
            })
        pipeline[stage_key] = {"count": len(rows), "tasks": tasks}

    recent = conn.execute("""
        SELECT id, title, assignee, status, created_at, started_at, completed_at,
               consecutive_failures, result
        FROM tasks
        WHERE completed_at IS NOT NULL OR started_at IS NOT NULL
        ORDER BY COALESCE(completed_at, started_at) DESC LIMIT 15
    """).fetchall()

    activity = []
    for r in recent:
        duration = None
        if r["completed_at"] and r["started_at"]:
            duration = int(r["completed_at"] - r["started_at"])
        status_label = {"done": "completed", "archived": "archived"}.get(r["status"], r["status"])
        activity.append({
            "task_id": r["id"],
            "title": r["title"],
            "assignee": r["assignee"],
            "status": status_label,
            "time": r["completed_at"] or r["started_at"] or r["created_at"],
            "duration": duration,
            "result": r["result"][:60] if r["result"] else None,
            "failures": r["consecutive_failures"],
        })

    timeline = {
        "created_24h": conn.execute("SELECT COUNT(*) FROM tasks WHERE created_at > ?", (day_ago,)).fetchone()[0],
        "completed_24h": conn.execute("SELECT COUNT(*) FROM tasks WHERE completed_at > ?", (day_ago,)).fetchone()[0],
        "active_24h": conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE started_at > ? AND status NOT IN ('done','archived')", (day_ago,)
        ).fetchone()[0],
    }

    avg_dur = conn.execute(
        "SELECT AVG(completed_at - started_at) FROM tasks WHERE completed_at IS NOT NULL AND started_at IS NOT NULL"
    ).fetchone()[0]

    conn.close()

    services = {"StarOfficeUI": True}
    for name, port in [
        ("Grafana", 3001),
        ("Gateway", 18789),
        ("Dashboard", 9119),
        ("StatsAPI", 19999),
    ]:
        services[name] = _check_port(port)

    letta_syncs = len([f for f in os.listdir(r"D:\brain\letta") if f.startswith("sync")]) if os.path.exists(r"D:\brain\letta") else 0

    total_tasks = sum(task_stats.values())
    active_tasks = sum(v for k, v in task_stats.items() if k not in ('done', 'archived'))
    done_tasks = task_stats.get('done', 0) + task_stats.get('archived', 0)

    return {
        "overview": {
            "total": total_tasks,
            "active": active_tasks,
            "done": done_tasks,
            "done_today": timeline["completed_24h"],
            "avg_duration": round(avg_dur, 1) if avg_dur else 0,
        },
        "services": services,
        "agents": agent_details,
        "pipeline": pipeline,
        "activity": activity,
        "timeline": timeline,
        "letta_sync_files": letta_syncs,
        "kanban": {"by_status": task_stats, "by_agent": {k: v["total"] for k, v in agent_details.items()}},
        "extensions": _load_extensions(),
        "self_healing": _load_self_healing(),
    }


# ── Logs helpers ───────────────────────────────────────────

def _read_tail(filepath: str, lines: int = 30) -> str:
    """Read last N lines from a file, return as string"""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        all_lines = content.strip().split("\n")
        return "\n".join(all_lines[-lines:])
    except Exception:
        return ""


def _find_latest_log(directory: str, prefix: str = "") -> str:
    """Find latest log file in a directory matching optional prefix"""
    try:
        if not os.path.isdir(directory):
            return ""
        files = sorted([f for f in os.listdir(directory) if f.endswith(".log") and f.startswith(prefix)], reverse=True)
        return os.path.join(directory, files[0]) if files else ""
    except Exception:
        return ""


# ── SSE helpers ────────────────────────────────────────────

_sse_queues: dict[str, queue.Queue] = {}
_sse_lock = threading.Lock()


def _sse_broadcast(event_type: str, data: dict):
    """向所有 SSE 客户端广播事件"""
    payload = json.dumps({"type": event_type, "data": data, "ts": datetime.now().isoformat()})
    with _sse_lock:
        for q in list(_sse_queues.values()):
            try:
                q.put_nowait(payload)
            except queue.Full:
                pass


def _sse_cleanup():
    """清理断开的 SSE 客户端"""
    with _sse_lock:
        dead = [cid for cid, q in _sse_queues.items() if q.qsize() > 500]
        for cid in dead:
            del _sse_queues[cid]


# ── Metrics helpers ────────────────────────────────────────

_sse_clients = []


def _get_pipeline_v2():
    rows = _query_db("SELECT status, COUNT(*) FROM tasks GROUP BY status")
    sm = dict(rows)
    stages = [
        {"key": "triage", "count": sm.get("triage", 0)},
        {"key": "todo", "count": sm.get("todo", 0)},
        {"key": "scheduled", "count": sm.get("scheduled", 0)},
        {"key": "ready", "count": sm.get("ready", 0)},
        {"key": "running", "count": sm.get("running", 0)},
        {"key": "blocked", "count": sm.get("blocked", 0)},
        {"key": "done", "count": sm.get("done", 0)}
    ]
    total = sum(s["count"] for s in stages)
    for s in stages:
        s["pct"] = round(s["count"] / max(total, 1) * 100)
    return {"stages": stages, "total": total}


def _get_agents_v2():
    agents = ["strategist", "executor-a", "executor-b", "executor-c", "monitor",
              "reviewer-strict", "reviewer-creative", "arbiter", "learner"]
    result = {}
    for a in agents:
        rows = _query_db("SELECT status, COUNT(*) FROM tasks WHERE assignee=? GROUP BY status", (a,))
        st = dict(rows)
        result[a] = {
            "total": sum(st.values()),
            "running": st.get("running", 0),
            "done": st.get("done", 0),
            "blocked": st.get("blocked", 0)
        }
    return result


def _get_services_metrics():
    return {
        "staroffice": _check_port(18791),
        "grafana": _check_port(3001),
        "kanban_db": os.path.exists(_get_kanban_db())
    }


# ── Memo helpers ───────────────────────────────────────────

def get_yesterday_date_str():
    """获取昨天的日期字符串 YYYY-MM-DD"""
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")


def sanitize_content(text):
    """清理内容，保护隐私"""
    text = re.sub(r'ou_[a-f0-9]+', '[用户]', text)
    text = re.sub(r'user_id="[^"]+"', 'user_id="[隐藏]"', text)
    text = re.sub(r'/root/[^"\s]+', '[路径]', text)
    text = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '[IP]', text)
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[邮箱]', text)
    text = re.sub(r'1[3-9]\d{9}', '[手机号]', text)
    return text


def extract_memo_from_file(file_path):
    """从 memory 文件中提取适合展示的 memo 内容（睿智风格的总结）"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.strip().split("\n")
        core_points = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                continue
            if line.startswith("- "):
                core_points.append(line[2:].strip())
            elif len(line) > 10:
                core_points.append(line)

        if not core_points:
            return "「昨日无事记录」\n\n若有恒，何必三更眠五更起；最无益，莫过一日曝十日寒。"

        selected_points = core_points[:3]

        wisdom_quotes = [
            "「工欲善其事，必先利其器。」",
            "「不积跬步，无以至千里；不积小流，无以成江海。」",
            "「知行合一，方可致远。」",
            "「业精于勤，荒于嬉；行成于思，毁于随。」",
            "「路漫漫其修远兮，吾将上下而求索。」",
            "「昨夜西风凋碧树，独上高楼，望尽天涯路。」",
            "「衣带渐宽终不悔，为伊消得人憔悴。」",
            "「众里寻他千百度，蓦然回首，那人却在，灯火阑珊处。」",
            "「世事洞明皆学问，人情练达即文章。」",
            "「纸上得来终觉浅，绝知此事要躬行。」"
        ]

        import random
        quote = random.choice(wisdom_quotes)

        result = []
        if selected_points:
            for i, point in enumerate(selected_points):
                point = sanitize_content(point)
                if len(point) > 40:
                    point = point[:37] + "..."
                if len(point) <= 20:
                    result.append(f"· {point}")
                else:
                    for j in range(0, len(point), 20):
                        chunk = point[j:j+20]
                        if j == 0:
                            result.append(f"· {chunk}")
                        else:
                            result.append(f"  {chunk}")

        if quote:
            if len(quote) <= 20:
                result.append(f"\n{quote}")
            else:
                for j in range(0, len(quote), 20):
                    chunk = quote[j:j+20]
                    if j == 0:
                        result.append(f"\n{chunk}")
                    else:
                        result.append(chunk)

        return "\n".join(result).strip()

    except Exception as e:
        print(f"提取 memo 失败: {e}")
        return "「昨日记录加载失败」\n\n「往者不可谏，来者犹可追。」"
