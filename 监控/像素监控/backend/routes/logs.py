"""Logs routes"""

import os
from flask import Blueprint, jsonify

from config import ROOT_DIR, LOG_ROOT
from utils import _read_tail, _find_latest_log

bp = Blueprint("logs", __name__)


@bp.route("/api/logs/system", methods=["GET"])
def api_logs_system():
    """Recent system-level logs"""
    lines = _read_tail(_find_latest_log(os.path.join(LOG_ROOT, "system")), 40)
    return jsonify({"lines": lines.split("\n") if lines else [], "source": "system"})


@bp.route("/api/logs/alerts", methods=["GET"])
def api_logs_alerts():
    """Recent alert logs"""
    lines = _read_tail(os.path.join(LOG_ROOT, "alerts.log"), 20)
    return jsonify({"lines": lines.split("\n") if lines else [], "source": "alerts"})


@bp.route("/api/logs/agents/<name>", methods=["GET"])
def api_logs_agents(name):
    """Recent agent-specific logs"""
    valid = ["strategist","executor-a","executor-b","executor-c","monitor","reviewer-strict","reviewer-creative","arbiter","learner"]
    if name not in valid:
        return jsonify({"lines": [], "source": "agents"}), 404
    lines = _read_tail(_find_latest_log(os.path.join(LOG_ROOT, "agents")), 20)
    return jsonify({"lines": lines.split("\n") if lines else [], "source": "agents"})


@bp.route("/api/logs/app", methods=["GET"])
def api_logs_app():
    """Recent StarOfficeUI app logs"""
    lines = _read_tail(os.path.join(ROOT_DIR, "app.log"), 20)
    return jsonify({"lines": lines.split("\n") if lines else [], "source": "app"})


@bp.route("/api/logs/service/<name>", methods=["GET"])
def api_logs_service(name):
    """Recent service-level logs (gateway, grafana, staroffice, orchestrator, commander)"""
    valid = ["gateway", "grafana", "staroffice", "orchestrator", "commander"]
    if name not in valid:
        return jsonify({"lines": [], "source": name}), 404
    if name == "commander":
        # 读取指挥官真正的日志文件（decisions.jsonl 和 errors.jsonl），而不是状态文件
        sc_dir = os.path.join(LOG_ROOT, "supreme_commander")
        decisions = _read_tail(os.path.join(sc_dir, "decisions.jsonl"), 20)
        errors = _read_tail(os.path.join(sc_dir, "errors.jsonl"), 10)
        lines = []
        if decisions:
            lines.append("=== 决策日志 ===")
            lines.extend(decisions.split("\n"))
        if errors:
            lines.append("=== 错误日志 ===")
            lines.extend(errors.split("\n"))
        if not lines:
            lines.append("指挥官暂无日志记录")
        return jsonify({"lines": lines, "source": "commander"})
    lines = _read_tail(_find_latest_log(os.path.join(LOG_ROOT, name)), 30)
    return jsonify({"lines": lines.split("\n") if lines else [], "source": name})
