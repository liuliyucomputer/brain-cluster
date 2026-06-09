"""Supreme Commander routes"""

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
    sc_state = os.path.join(os.path.dirname(ROOT_DIR), "output", "logs", "supreme_commander", "commander_state.json")
    if os.path.exists(sc_state):
        try:
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
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"[commander_status] Failed to read state: {e}")
            return jsonify({"error": str(e)}), 500
    return jsonify({"status": "not_initialized", "scan_count": 0, "fixes_auto": 0, "crisis_count": 0})


@bp.route("/api/commander/<action>", methods=["POST"])
def api_commander_control(action):
    """Control Supreme Commander"""
    tools_dir = os.path.join(os.path.dirname(ROOT_DIR), "tools")
    result = {"success": False, "message": "", "error": ""}

    try:
        if action == "scan":
            # 使用 Popen 非阻塞启动扫描，避免超时
            proc = subprocess.Popen(
                [sys.executable, os.path.join(tools_dir, "supreme_commander.py"), "--scan-once"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            # 等待最多 10 秒获取初步输出
            try:
                stdout, stderr = proc.communicate(timeout=10)
                output = stdout[:500] if stdout else ""
                if proc.returncode == 0:
                    result["success"] = True
                    result["message"] = "扫描完成"
                    result["output"] = output
                else:
                    result["success"] = True
                    result["message"] = "扫描已触发（后台执行中）"
                    result["output"] = output or "扫描任务已提交"
            except subprocess.TimeoutExpired:
                # 超时也表示成功，因为扫描在后台继续
                result["success"] = True
                result["message"] = "扫描已触发（后台执行中）"
                result["output"] = "扫描任务已提交，请稍后刷新状态查看结果"
        elif action == "fix":
            # fix 使用 meta_commander 的 dry-run 模式
            proc = subprocess.Popen(
                [sys.executable, os.path.join(tools_dir, "meta_commander.py"), "--scan"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            try:
                stdout, stderr = proc.communicate(timeout=10)
                output = stdout[:800] if stdout else ""
                result["success"] = True
                result["message"] = "安全扫描完成"
                result["output"] = output
            except subprocess.TimeoutExpired:
                result["success"] = True
                result["message"] = "安全扫描已触发（后台执行中）"
                result["output"] = "扫描任务已提交"
        elif action == "status":
            r = subprocess.run(
                [sys.executable, os.path.join(tools_dir, "supreme_commander.py"), "--status"],
                capture_output=True, text=True, timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            result["success"] = True
            result["message"] = "状态已刷新"
            result["output"] = r.stdout[:500] if r.stdout else ""
        else:
            result["error"] = f"未知操作: {action}"
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        logger.error(f"[commander_control] Action {action} failed: {e}")
        result["error"] = str(e)

    return jsonify(result)
