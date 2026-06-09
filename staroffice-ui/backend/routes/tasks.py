"""Task Creator routes"""

import os
import sqlite3
import time as _time
import uuid
from flask import Blueprint, jsonify, request

from config import ROOT_DIR
from utils import logger, _query_db, _get_kanban_db

bp = Blueprint("tasks", __name__)


@bp.route("/api/tasks/create", methods=["POST"])
def api_tasks_create():
    """Create a new task in kanban.db"""
    try:
        data = request.get_json(force=True)
        title = (data.get("title") or "").strip()
        assignee = (data.get("assignee") or "strategist").strip()
        body = (data.get("body") or "").strip()

        if not title:
            return jsonify({"ok": False, "msg": "任务标题不能为空"}), 400

        kanban_db = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "hermes", "kanban.db")
        if not os.path.exists(kanban_db):
            kanban_db = os.path.join(ROOT_DIR, "..", "output", "memory", "kanban.db")
        task_id = f"t_{uuid.uuid4().hex[:8]}"
        now = int(_time.time())

        conn = sqlite3.connect(kanban_db)
        conn.execute("""
            INSERT INTO tasks (id, title, body, assignee, status, created_by, created_at, workspace_kind)
            VALUES (?, ?, ?, ?, 'ready', 'dashboard', ?, 'scratch')
        """, (task_id, title, body, assignee, now))
        conn.commit()
        conn.close()

        logger.info(f"[Task] Created: {task_id} -> {assignee} ({title[:30]})")
        return jsonify({"ok": True, "task_id": task_id, "title": title, "assignee": assignee})
    except Exception as e:
        logger.error(f"[Task] Create failed: {e}")
        return jsonify({"ok": False, "msg": str(e)}), 500



