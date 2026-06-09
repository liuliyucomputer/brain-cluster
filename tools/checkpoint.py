# -*- coding: utf-8 -*-
"""
Brain 集群 — Checkpoint Manager (断点恢复) v2.2
功能: 每5分钟保存完整任务状态快照 (JSON)，覆盖 tasks/task_links/task_runs/task_events
      及相关表；支持分级恢复（运营级/灾难级），恢复时自动验证依赖闭环和状态一致性。
版本: v2.2 | 2026-06-08 重构
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import KANBAN_DB, MEMORY_DIR, LOGS_DIR

CHECKPOINT_DIR = os.path.join(MEMORY_DIR, "checkpoints")
CHECKPOINT_INTERVAL = 300
MAX_CHECKPOINTS = 20
CHECKPOINT_VERSION = "2.2.0"

# 核心表（按依赖顺序）
SNAPSHOT_TABLES = [
    "tasks",
    "task_links",
    "task_comments",
    "task_events",
    "task_runs",
    "kanban_notify_subs",
]

# 删除顺序（先删子表，避免外键冲突）
DELETE_ORDER = [
    "kanban_notify_subs",
    "task_comments",
    "task_events",
    "task_runs",
    "task_links",
    "tasks",
]

# 恢复顺序（先恢复父表）
RESTORE_ORDER = [
    "tasks",
    "task_links",
    "task_runs",
    "task_events",
    "task_comments",
    "kanban_notify_subs",
]

# 关键配置文件
CONFIG_FILES = [
    "input/configs/hermes/gateway.json",
    "input/configs/siliconflow/endpoint.json",
    "input/configs/ccswitch/endpoint.json",
]

os.makedirs(CHECKPOINT_DIR, exist_ok=True)


def _connect():
    conn = sqlite3.connect(KANBAN_DB, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(conn, table_name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return bool(row)


def _table_columns(conn, table_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row["name"] for row in rows]


def _dump_table(conn, table_name, limit=None):
    """导出表数据，可选限制行数"""
    if not _table_exists(conn, table_name):
        return None

    columns = _table_columns(conn, table_name)
    sql = f"SELECT * FROM {table_name}"
    if limit:
        sql += f" ORDER BY rowid DESC LIMIT {limit}"
    rows = conn.execute(sql).fetchall()
    return {
        "columns": columns,
        "rows": [{col: row[col] for col in columns} for row in rows],
    }


def _dump_sqlite_sequence(conn):
    if not _table_exists(conn, "sqlite_sequence"):
        return []
    rows = conn.execute(
        "SELECT name, seq FROM sqlite_sequence WHERE name IN (%s)" %
        ",".join("?" for _ in SNAPSHOT_TABLES),
        SNAPSHOT_TABLES,
    ).fetchall()
    return [{"name": row["name"], "seq": row["seq"]} for row in rows]


def _get_kanban_stats(conn):
    rows = conn.execute("SELECT status, COUNT(*) AS cnt FROM tasks GROUP BY status").fetchall()
    return {row["status"]: row["cnt"] for row in rows}


def _get_reputation():
    rep_file = os.path.join(MEMORY_DIR, "monthly", "reputation.json")
    if os.path.exists(rep_file):
        with open(rep_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _get_retry_state():
    retry_file = os.path.join(LOGS_DIR, "orchestrator", "retry_state.json")
    if os.path.exists(retry_file):
        with open(retry_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _get_configs():
    """备份关键配置文件内容"""
    configs = {}
    for rel_path in CONFIG_FILES:
        abs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), rel_path)
        if os.path.exists(abs_path):
            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    configs[rel_path] = json.load(f)
            except Exception:
                pass
    return configs


def _table_row_count(snapshot, table_name):
    table = snapshot.get("tables", {}).get(table_name)
    return len(table.get("rows", [])) if table else 0


def save_checkpoint():
    """保存一个完整的状态快照"""
    ts = datetime.now()
    filename = f"checkpoint_{ts.strftime('%Y-%m-%d_%H-%M-%S')}.json"
    filepath = os.path.join(CHECKPOINT_DIR, filename)

    conn = _connect()
    try:
        tables = {}
        for table_name in SNAPSHOT_TABLES:
            # task_runs 和 task_events 只保留最近记录，避免快照过大
            limit = None
            if table_name == "task_runs":
                limit = 100
            elif table_name == "task_events":
                limit = 1000
            dumped = _dump_table(conn, table_name, limit=limit)
            if dumped is not None:
                tables[table_name] = dumped

        checkpoint = {
            "version": CHECKPOINT_VERSION,
            "timestamp": ts.isoformat(),
            "db_file": KANBAN_DB,
            "db_size_bytes": os.path.getsize(KANBAN_DB) if os.path.exists(KANBAN_DB) else 0,
            "kanban_stats": _get_kanban_stats(conn),
            "tables": tables,
            "sqlite_sequence": _dump_sqlite_sequence(conn),
            "reputation": _get_reputation(),
            "retry_state": _get_retry_state(),
            "configs": _get_configs(),
        }
    finally:
        conn.close()

    # 文件锁保护：原子写入，防止多进程并发损坏
    lock_file = filepath + ".lock"
    acquired = False
    for _ in range(30):
        try:
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            acquired = True
            break
        except FileExistsError:
            time.sleep(0.1)
    try:
        if not acquired:
            raise RuntimeError(f"无法获取文件锁: {lock_file}")
        tmp_file = filepath + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, filepath)
    finally:
        if acquired and os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except OSError:
                pass

    _cleanup_old_checkpoints()
    size_kb = round(os.path.getsize(filepath) / 1024, 1)
    print(
        f"[CHECKPOINT] Saved: {filename} ({size_kb} KB, "
        f"{_table_row_count(checkpoint, 'tasks')} tasks, "
        f"{_table_row_count(checkpoint, 'task_runs')} runs, "
        f"{_table_row_count(checkpoint, 'task_events')} events)"
    )
    return filepath


def _cleanup_old_checkpoints():
    files = sorted(
        [f for f in os.listdir(CHECKPOINT_DIR) if f.startswith("checkpoint_") and f.endswith(".json")],
        reverse=True,
    )
    if len(files) > MAX_CHECKPOINTS:
        for filename in files[MAX_CHECKPOINTS:]:
            os.remove(os.path.join(CHECKPOINT_DIR, filename))
            print(f"[CHECKPOINT] Purged old: {filename}")


def list_checkpoints():
    files = sorted(
        [f for f in os.listdir(CHECKPOINT_DIR) if f.startswith("checkpoint_") and f.endswith(".json")],
        reverse=True,
    )
    if not files:
        print("No checkpoints found.")
        return []

    print(f"=== {len(files)} checkpoints (max {MAX_CHECKPOINTS}) ===")
    for filename in files[:10]:
        path = os.path.join(CHECKPOINT_DIR, filename)
        size_kb = round(os.path.getsize(path) / 1024, 1)
        ts_str = filename.replace("checkpoint_", "").replace(".json", "").replace("_", " ")
        print(f"  {ts_str}  ({size_kb} KB)")
    return files


def load_checkpoint(filename=None):
    """加载一个快照"""
    if filename is None:
        files = sorted(
            [f for f in os.listdir(CHECKPOINT_DIR) if f.startswith("checkpoint_") and f.endswith(".json")],
            reverse=True,
        )
        if not files:
            print("[CHECKPOINT] No checkpoint to load.")
            return None
        filename = files[0]

    filepath = os.path.join(CHECKPOINT_DIR, filename)
    if not os.path.exists(filepath):
        print(f"[CHECKPOINT] File not found: {filepath}")
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(
        f"[CHECKPOINT] Loaded: {filename} "
        f"({_table_row_count(data, 'tasks')} tasks, {_table_row_count(data, 'task_runs')} runs)"
    )
    return data


def _restore_table(conn, table_name, table_snapshot):
    if not table_snapshot or not _table_exists(conn, table_name):
        return 0

    columns = [col for col in table_snapshot.get("columns", []) if col in _table_columns(conn, table_name)]
    rows = table_snapshot.get("rows", [])
    if not columns:
        return 0

    placeholders = ",".join("?" for _ in columns)
    sql = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"
    payload = [[row.get(col) for col in columns] for row in rows]
    if payload:
        conn.executemany(sql, payload)
    return len(payload)


def _restore_sqlite_sequence(conn, snapshot):
    if not _table_exists(conn, "sqlite_sequence"):
        return

    rows = snapshot.get("sqlite_sequence", [])
    if rows:
        conn.executemany(
            "DELETE FROM sqlite_sequence WHERE name = ?",
            [(table_name,) for table_name in SNAPSHOT_TABLES],
        )
        conn.executemany(
            "INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)",
            [(row["name"], row["seq"]) for row in rows if row.get("name")],
        )


def _reclaim_restored_running_tasks(snapshot):
    """恢复后对处于 running 状态的任务执行 reclaim"""
    tasks = snapshot.get("tables", {}).get("tasks", {}).get("rows", [])
    running_task_ids = [row["id"] for row in tasks if row.get("status") == "running" and row.get("id")]
    reclaimed = []
    for task_id in running_task_ids:
        result = subprocess.run(
            ["hermes", "kanban", "reclaim", task_id, "--reason", "checkpoint restore"],
            capture_output=True,
            text=True,
            env={**os.environ, "GATEWAY_ALLOW_ALL_USERS": "true"},
            timeout=20,
        )
        if result.returncode == 0:
            reclaimed.append(task_id)
    return reclaimed


def _validate_recovery(snapshot):
    """
    验证恢复后的数据一致性。
    返回 (is_valid, issues)
    """
    issues = []
    tables = snapshot.get("tables", {})

    # 1. 检查任务 ID 唯一性
    tasks = tables.get("tasks", {}).get("rows", [])
    task_ids = [t.get("id") for t in tasks if t.get("id")]
    if len(task_ids) != len(set(task_ids)):
        issues.append("任务 ID 存在重复")

    # 2. 检查依赖闭环（无孤儿链接）
    task_id_set = set(task_ids)
    links = tables.get("task_links", {}).get("rows", [])
    for link in links:
        parent_id = link.get("parent_id")
        child_id = link.get("child_id")
        if parent_id and parent_id not in task_id_set:
            issues.append(f"孤儿链接: parent_id={parent_id} 不存在")
        if child_id and child_id not in task_id_set:
            issues.append(f"孤儿链接: child_id={child_id} 不存在")

    # 3. 检查循环依赖（简化版：深度限制）
    def _has_cycle(task_id, visited=None, depth=0):
        if depth > 100:
            return True
        if visited is None:
            visited = set()
        if task_id in visited:
            return True
        visited.add(task_id)
        children = [l.get("child_id") for l in links if l.get("parent_id") == task_id]
        for child in children:
            if _has_cycle(child, visited.copy(), depth + 1):
                return True
        return False

    for task_id in task_ids:
        if _has_cycle(task_id):
            issues.append(f"循环依赖 detected at task_id={task_id}")
            break

    # 4. 检查状态一致性（task.status 与最新 run.outcome 对齐）
    runs = tables.get("task_runs", {}).get("rows", [])
    task_runs_map = {}
    for run in runs:
        tid = run.get("task_id")
        if tid:
            if tid not in task_runs_map or run.get("started_at", 0) > task_runs_map[tid].get("started_at", 0):
                task_runs_map[tid] = run

    for task in tasks:
        tid = task.get("id")
        status = task.get("status")
        latest_run = task_runs_map.get(tid)
        if latest_run:
            run_outcome = latest_run.get("outcome")
            # running 任务应该有未完成的 run
            if status == "running" and run_outcome not in (None, ""):
                issues.append(f"状态不一致: task={tid} status=running 但 run.outcome={run_outcome}")

    return len(issues) == 0, issues


def _generate_recovery_report(snapshot, restored_counts, reclaimed, issues):
    """生成恢复报告"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "checkpoint_version": snapshot.get("version"),
        "checkpoint_timestamp": snapshot.get("timestamp"),
        "restored_counts": restored_counts,
        "reclaimed_running_tasks": reclaimed,
        "validation_passed": len(issues) == 0,
        "issues": issues,
        "recommendations": [],
    }

    if issues:
        report["recommendations"].append("发现数据一致性问题，建议人工检查后再启动调度")
    if reclaimed:
        report["recommendations"].append(f"已 reclaim {len(reclaimed)} 个 running 任务，它们将被重新调度")

    report_path = os.path.join(CHECKPOINT_DIR, f"recovery_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[CHECKPOINT] Recovery report saved: {report_path}")
    return report


def restore_from_checkpoint(filename=None, level="auto"):
    """
    从快照恢复 kanban.db 状态。

    Args:
        filename: 快照文件名，None 表示最新
        level: 恢复级别
            - "auto": 自动判断（如果有 task_runs 则全量恢复，否则仅恢复 tasks+links）
            - "full": 全量恢复（灾难级）
            - "minimal": 仅恢复 tasks+task_links（运营级）

    警告: 会覆盖当前工作表数据。
    """
    snapshot = load_checkpoint(filename)
    if not snapshot:
        return False

    # 判断恢复级别
    if level == "auto":
        has_runs = _table_row_count(snapshot, "task_runs") > 0
        level = "full" if has_runs else "minimal"

    print(f"[CHECKPOINT] Recovery level: {level}")

    backup_path = KANBAN_DB + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if os.path.exists(KANBAN_DB):
        shutil.copy2(KANBAN_DB, backup_path)
        print(f"[CHECKPOINT] Backed up current DB to: {backup_path}")

    conn = _connect()
    restored_counts = {}
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("BEGIN")

        # 根据级别决定恢复范围
        if level == "minimal":
            restore_tables = ["tasks", "task_links"]
            delete_tables = ["task_links", "tasks"]
        else:
            restore_tables = RESTORE_ORDER
            delete_tables = DELETE_ORDER

        for table_name in delete_tables:
            if _table_exists(conn, table_name):
                conn.execute(f"DELETE FROM {table_name}")

        for table_name in restore_tables:
            restored_counts[table_name] = _restore_table(
                conn,
                table_name,
                snapshot.get("tables", {}).get(table_name),
            )

        _restore_sqlite_sequence(conn, snapshot)
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"[CHECKPOINT] Restore failed: {e}")
        return False
    finally:
        if conn:
            conn.close()

    # reclaim running 任务
    reclaimed = _reclaim_restored_running_tasks(snapshot)

    # 验证恢复结果
    is_valid, issues = _validate_recovery(snapshot)

    # 生成恢复报告
    report = _generate_recovery_report(snapshot, restored_counts, reclaimed, issues)

    print(
        "[CHECKPOINT] Restored tables: "
        + ", ".join(f"{name}={count}" for name, count in restored_counts.items())
    )
    if reclaimed:
        print(f"[CHECKPOINT] Reclaimed restored running tasks: {', '.join(reclaimed)}")
    if not is_valid:
        print(f"[CHECKPOINT] Validation issues ({len(issues)}):")
        for issue in issues:
            print(f"    - {issue}")

    return is_valid


def run_daemon():
    """持续运行 (每5分钟保存一个快照)"""
    print(f"=== Checkpoint Manager v{CHECKPOINT_VERSION} started ({CHECKPOINT_INTERVAL}s interval) ===")
    print(f"  Directory: {CHECKPOINT_DIR}")
    print(f"  Max checkpoints: {MAX_CHECKPOINTS}")
    print(f"  Snapshot tables: {', '.join(SNAPSHOT_TABLES)}")
    print("-" * 55)

    try:
        while True:
            save_checkpoint()
            time.sleep(CHECKPOINT_INTERVAL)
    except KeyboardInterrupt:
        print("\nCheckpoint Manager stopped.")


def get_recovery_eta():
    """估算从最近快照恢复后的任务剩余量"""
    snapshot = load_checkpoint()
    if not snapshot:
        return None

    tasks = snapshot.get("tables", {}).get("tasks", {}).get("rows", [])
    total = len(tasks)
    if total == 0:
        return None

    done = sum(1 for task in tasks if task.get("status") == "done")
    archived = sum(1 for task in tasks if task.get("status") == "archived")
    running = sum(1 for task in tasks if task.get("status") == "running")
    blocked = sum(1 for task in tasks if task.get("status") == "blocked")

    return {
        "checkpoint_ts": snapshot.get("timestamp"),
        "total_tasks": total,
        "done": done,
        "archived": archived,
        "running": running,
        "blocked": blocked,
        "remaining": total - done - archived,
        "completion_pct": round((done + archived) / total * 100, 1),
        "task_runs": _table_row_count(snapshot, "task_runs"),
        "task_events": _table_row_count(snapshot, "task_events"),
        "estimated_resume_possible": True,
    }


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        run_daemon()
    elif "--list" in sys.argv:
        list_checkpoints()
    elif "--restore" in sys.argv:
        filename = sys.argv[2] if len(sys.argv) > 2 else None
        level = sys.argv[3] if len(sys.argv) > 3 else "auto"
        restore_from_checkpoint(filename, level)
    elif "--eta" in sys.argv:
        info = get_recovery_eta()
        print(json.dumps(info, ensure_ascii=False, indent=2) if info else "No checkpoint")
    else:
        print("USAGE: python checkpoint.py [--daemon | --list | --restore [file] [level] | --eta]")
        print("  --daemon     Run continuously (save every 5min)")
        print("  --list       List all checkpoints")
        print("  --restore    Restore from latest (or specified) checkpoint")
        print("               level: auto|full|minimal (default: auto)")
        print("  --eta        Show recovery estimate from latest checkpoint")
