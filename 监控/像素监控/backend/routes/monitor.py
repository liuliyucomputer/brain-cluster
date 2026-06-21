"""Monitor & stats routes"""

import json
import os
import sqlite3
from datetime import datetime
from flask import Blueprint, jsonify, request

from config import ROOT_DIR, KANBAN_DB
from utils import (
    logger,
    _check_port,
    _compute_stats,
    _get_kanban_db,
    _query_db,
    _get_pipeline_v2,
    _get_agents_v2,
    _get_services_metrics,
    _sse_clients,
    _sse_lock,
)

bp = Blueprint("monitor", __name__)


@bp.route("/api/monitor", methods=["GET"])
def api_monitor_direct():
    """Direct monitor data from database (replaces old 19997 proxy)"""
    try:
        kanban_db = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "hermes", "kanban.db")
        if not os.path.exists(kanban_db):
            kanban_db = KANBAN_DB

        conn = sqlite3.connect(kanban_db, timeout=5)
        cursor = conn.cursor()

        # Task counts
        cursor.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
        task_counts = dict(cursor.fetchall())

        # Recent runs
        cursor.execute("SELECT id, task_id, status, started_at, completed_at FROM task_runs ORDER BY started_at DESC LIMIT 10")
        runs = [dict(zip(["id", "task_id", "status", "started_at", "completed_at"], r)) for r in cursor.fetchall()]

        # Service status (check ports)
        services = {
            "gateway": _check_port(18789),
            "staroffice_ui": _check_port(18791),
            "grafana": _check_port(3001),
            "stats_api": _check_port(19999),
        }

        conn.close()

        return jsonify({
            "tasks": {
                "total": sum(task_counts.values()),
                "pending": task_counts.get("pending", 0),
                "in_progress": task_counts.get("in_progress", 0),
                "completed": task_counts.get("completed", 0),
                "failed": task_counts.get("failed", 0),
            },
            "runs": runs,
            "services": services,
            "updated": datetime.now().isoformat(),
        })
    except (sqlite3.Error, OSError) as e:
        logger.error(f"[monitor_direct] Failed to query monitor data: {e}")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/stats", methods=["GET"])
def api_stats():
    """Brain Cluster Stats API"""
    return jsonify(_compute_stats())


@bp.route("/api/stream")
def api_metrics_stream():
    """SSE 实时数据流"""
    import queue as _queue
    def event_stream():
        q = _queue.Queue(maxsize=30)
        with _sse_lock:
            _sse_clients.append(q)
        try:
            while True:
                state = {"timestamp": datetime.now().isoformat(), "pipeline": _get_pipeline_v2(),
                         "agents": _get_agents_v2(), "services": _get_services_metrics()}
                yield f"event: state\ndata: {json.dumps(state, ensure_ascii=False)}\n\n"
                for _ in range(20):
                    try:
                        yield q.get(timeout=0.1)
                    except _queue.Empty:
                        pass
        except GeneratorExit:
            pass
        finally:
            with _sse_lock:
                if q in _sse_clients:
                    _sse_clients.remove(q)
    from flask import current_app
    return current_app.response_class(
        event_stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@bp.route("/api/task_cost")
def api_task_cost():
    rows = _query_db("SELECT status, COUNT(*) FROM tasks GROUP BY status")
    sm = dict(rows)
    total = sum(sm.values())
    calls = total * 5
    cost = round(calls * 2000 / 1000000, 2)
    return jsonify({
        "total_tasks": total,
        "estimated_api_calls": calls,
        "estimated_cost_cny": cost,
        "model": "deepseek-ai/DeepSeek-V4-Pro",
        "tasks_by_status": sm
    })


@bp.route("/metrics/quality")
def metrics_quality():
    total = _query_db("SELECT COUNT(*) FROM tasks WHERE assignee LIKE 'executor-%'")[0][0]
    done = _query_db("SELECT COUNT(*) FROM tasks WHERE status='done' AND assignee LIKE 'executor-%'")[0][0]
    arb = _query_db("SELECT COUNT(*) FROM tasks WHERE assignee='arbiter'")[0][0]
    retry = _query_db("SELECT COUNT(*) FROM tasks WHERE title LIKE 'RETRY%'")[0][0]
    return jsonify({
        "pass_rate": round(done / max(total, 1) * 100, 1),
        "arbitration_rate": round(arb / max(total, 1) * 100, 1),
        "retry_rate": round(retry / max(total, 1) * 100, 1),
        "total_executions": total
    })


@bp.route("/metrics/stability")
def metrics_stability():
    log_dir = os.path.join(ROOT_DIR, "..", "output", "logs", "watchdog")
    wd_path = os.path.join(log_dir, "watchdog_state.json")
    reclaim = 0
    if os.path.exists(wd_path):
        try:
            with open(wd_path, encoding="utf-8") as f:
                reclaim = json.load(f).get("metrics", {}).get("reclaim_success_total", 0)
        except Exception:
            pass
    crashes = _query_db("SELECT COUNT(*) FROM task_runs WHERE outcome='crashed'")[0][0]
    timeouts = _query_db("SELECT COUNT(*) FROM task_runs WHERE outcome='timed_out'")[0][0]
    return jsonify({"reclaim_success": reclaim, "crashes": crashes, "timeouts": timeouts})


@bp.route("/metrics/learning")
def metrics_learning():
    mem_root = os.path.join(ROOT_DIR, "..", "output", "memory")
    last_distill = None
    for name in ["weekly", "monthly"]:
        p = os.path.join(mem_root, name)
        if os.path.isdir(p):
            files = [os.path.join(p, f) for f in os.listdir(p) if f.endswith(('.json', '.jsonl'))]
            if files:
                mtime = max(os.path.getmtime(f) for f in files)
                if last_distill is None or mtime > last_distill:
                    last_distill = mtime
    return jsonify({"last_distill": datetime.fromtimestamp(last_distill).isoformat() if last_distill else None})


# ═══════════════════════════════════════════════
#  Grafana JSON Datasource (merged from stats_api.py)
# ═══════════════════════════════════════════════

@bp.route("/grafana/query", methods=["POST"])
def grafana_query():
    """Grafana Simple JSON datasource query endpoint"""
    data = request.get_json() or {}
    targets = data.get("targets", [])
    results = []

    conn = sqlite3.connect(KANBAN_DB)
    try:
        for t in targets:
            target = t.get("target", "tasks")

            if target == "tasks":
                rows = conn.execute("SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status").fetchall()
                for r in rows:
                    results.append({"target": f"tasks.{r[0]}", "datapoints": [[r[1], 0]]})

            elif target == "agents":
                rows = conn.execute("SELECT assignee, COUNT(*) as cnt FROM tasks GROUP BY assignee").fetchall()
                for r in rows:
                    results.append({"target": f"agents.{r[0]}", "datapoints": [[r[1], 0]]})

            elif target == "recent":
                rows = conn.execute("SELECT status, created_at FROM tasks ORDER BY created_at DESC LIMIT 20").fetchall()
                for i, r in enumerate(rows):
                    results.append({"target": f"recent.{r[0]}", "datapoints": [[1, i]]})
    finally:
        conn.close()

    return jsonify(results)


@bp.route("/grafana/search", methods=["POST"])
def grafana_search():
    return jsonify(["tasks", "agents", "recent"])


@bp.route("/grafana/stats", methods=["GET"])
def grafana_stats():
    """直接查看统计 (浏览器可访问)"""
    conn = sqlite3.connect(KANBAN_DB)
    try:
        task_stats = dict(conn.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status").fetchall())
        agent_stats = dict(conn.execute("SELECT assignee, COUNT(*) FROM tasks GROUP BY assignee WHERE assignee IS NOT NULL").fetchall())
        total = sum(task_stats.values())

        letta_dir = os.path.join(os.path.dirname(os.path.dirname(ROOT_DIR)), "letta")
        logs = len([f for f in os.listdir(letta_dir) if f.startswith("sync")]) if os.path.exists(letta_dir) else 0
    finally:
        conn.close()

    return jsonify({
        "kanban": {
            "total_tasks": total,
            "by_status": task_stats,
            "by_agent": agent_stats,
        },
        "letta_sync_files": logs,
        "services": {
            "grafana": "http://localhost:3001",
            "staroffice": "http://localhost:18791",
            "dashboard": "http://localhost:9119",
        }
    })
