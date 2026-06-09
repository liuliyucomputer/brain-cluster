"""Supreme Commander routes"""
import json
import os
import subprocess
import sys
from flask import Blueprint, jsonify

from config import ROOT_DIR
from utils import logger

bp = Blueprint("commander", __name__)


@bp.route("/api/commander/status", methods=["GET"])
def api_commander_status():
    """Get Supreme Commander status"""
    try:
        sc_state = os.path.join(os.path.dirname(ROOT_DIR), "output", "logs", "supreme_commander", "commander_state.json")
        if os.path.exists(sc_state):
            with open(sc_state, "r", encoding="utf-8") as f:
                state = json.load(f)
            return jsonify({
                "status": state.get("status", "standby"),
                "scan_count": state.get("scan_count", 0),
                "fixes_auto": state.get("fixes_auto", 0),
                "fixes_manual": state.get("fixes_manual", 0),
                "fixes_failed": state.get("fixes_failed", 0),
                "crisis_count": state.get("crisis_count", 0),
                "crisis_mode": state.get("status") == "crisis",
                "last_scan": state.get("last_scan"),
                "agent_health": state.get("agent_health", {}),
            })
        return jsonify({"status": "not_initialized", "scan_count": 0, "fixes_auto": 0, "crisis_count": 0})
    except (json.JSONDecodeError, IOError, OSError) as e:
        logger.warning(f"[commander_status] Failed to read state: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@bp.route("/api/commander/<action>", methods=["POST"])
def api_commander_control(action):
    result = {"success": False, "message": "", "error": ""}
    tools_dir = os.path.join(os.path.dirname(ROOT_DIR), "tools")
    try:
        if action == "scan":
            proc = subprocess.Popen(
                [sys.executable, os.path.join(tools_dir, "supreme_commander.py"), "--scan-once"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            try:
                stdout, _ = proc.communicate(timeout=10)
                result["success"] = True
                result["message"] = "扫描完成"
                result["output"] = stdout[:500] if stdout else ""
            except subprocess.TimeoutExpired:
                result["success"] = True
                result["message"] = "扫描已触发（后台执行中）"
        elif action == "fix":
            proc = subprocess.Popen(
                [sys.executable, os.path.join(tools_dir, "meta_commander.py"), "--scan"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            try:
                stdout, _ = proc.communicate(timeout=10)
                result["success"] = True
                result["message"] = "安全扫描完成"
                result["output"] = stdout[:800] if stdout else ""
            except subprocess.TimeoutExpired:
                result["success"] = True
                result["message"] = "安全扫描已触发"
        else:
            result["error"] = f"未知操作: {action}"
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        logger.error(f"[commander_control] Action {action} failed: {e}")
        result["error"] = str(e)
    return jsonify(result)
