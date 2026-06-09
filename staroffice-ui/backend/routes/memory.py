"""Memory Manager routes"""

import os
from datetime import datetime
from flask import Blueprint, jsonify, request

from config import _MEMORY_DIRS
from utils import logger

bp = Blueprint("memory", __name__)


@bp.route("/api/memory/list", methods=["GET"])
def api_memory_list():
    """List all available memory files"""
    results = []
    for label, d in _MEMORY_DIRS:
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            fp = os.path.join(d, f)
            if os.path.isfile(fp) and (f.endswith(".md") or f.endswith(".json")):
                stat = os.stat(fp)
                results.append({
                    "label": label, "name": f, "path": fp,
                    "size_kb": round(stat.st_size / 1024, 1),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
    return jsonify({"files": results})


@bp.route("/api/memory/read", methods=["GET"])
def api_memory_read():
    path = request.args.get("path", "")
    if not path or not os.path.isfile(path):
        return jsonify({"ok": False, "msg": "文件不存在"}), 404
    allowed = False
    for _, d in _MEMORY_DIRS:
        if os.path.abspath(path).startswith(os.path.abspath(d)):
            allowed = True; break
    if "MAINTENANCE_LOG" in path:
        allowed = True
    if not allowed:
        return jsonify({"ok": False, "msg": "不允许访问"}), 403
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return jsonify({"ok": True, "path": path, "content": content})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


@bp.route("/api/memory/update", methods=["POST"])
def api_memory_update():
    data = request.get_json(force=True)
    path = (data.get("path") or "").strip()
    content = (data.get("content") or "")
    if not path:
        return jsonify({"ok": False, "msg": "路径不能为空"}), 400
    allowed = False
    for _, d in _MEMORY_DIRS:
        if os.path.abspath(path).startswith(os.path.abspath(d)):
            allowed = True; break
    if "MAINTENANCE_LOG" in path:
        allowed = True
    if not allowed:
        return jsonify({"ok": False, "msg": "不允许修改"}), 403
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"[Memory] Updated: {path}")
        return jsonify({"ok": True, "path": path})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


@bp.route("/api/memory/delete", methods=["POST"])
def api_memory_delete():
    data = request.get_json(force=True)
    path = (data.get("path") or "").strip()
    if not path:
        return jsonify({"ok": False, "msg": "路径不能为空"}), 400
    if not path.endswith(".md"):
        return jsonify({"ok": False, "msg": "只允许删除 .md 文件"}), 400
    allowed = False
    for _, d in _MEMORY_DIRS:
        if os.path.abspath(path).startswith(os.path.abspath(d)):
            allowed = True; break
    if "MAINTENANCE_LOG" in path:
        allowed = True
    if not allowed:
        return jsonify({"ok": False, "msg": "不允许删除"}), 403
    try:
        os.remove(path)
        logger.info(f"[Memory] Deleted: {path}")
        return jsonify({"ok": True, "path": path})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500
