"""Service control routes"""

import os
import subprocess
import sys
from flask import Blueprint, jsonify

from config import ROOT_DIR, SERVICE_CONFIGS
from utils import logger, _check_port, service_processes, service_lock

bp = Blueprint("services", __name__)


@bp.route("/api/services/status", methods=["GET"])
def api_services_status():
    """Get all service statuses with port checks"""
    result = {}
    for name, cfg in SERVICE_CONFIGS.items():
        port_open = _check_port(cfg["port"])
        proc = service_processes.get(name)
        running = port_open
        result[name] = {
            "running": running,
            "port": cfg["port"],
            "zh": cfg["zh"],
            "pid": proc.pid if (proc and proc.poll() is None) else None,
        }
    # Add StarOfficeUI (itself)
    result["StarOfficeUI"] = {"running": True, "port": 18791, "zh": "StarOffice面板", "pid": None}
    return jsonify(result)


@bp.route("/api/services/start/<name>", methods=["POST"])
def api_services_start(name):
    """Start a service"""
    if name == "StarOfficeUI":
        return jsonify({"ok": False, "msg": "StarOfficeUI is already running (this server)"}), 400

    cfg = SERVICE_CONFIGS.get(name)
    if not cfg:
        return jsonify({"ok": False, "msg": f"Unknown service: {name}"}), 404

    with service_lock:
        # Check if already running
        existing = service_processes.get(name)
        if existing and existing.poll() is None:
            return jsonify({"ok": False, "msg": f"{name} is already running (PID {existing.pid})"}), 409

        if _check_port(cfg["port"]):
            return jsonify({"ok": False, "msg": f"{name} port {cfg['port']} is already in use"}), 409

        try:
            env = os.environ.copy()
            if cfg.get("env"):
                env.update(cfg["env"])

            # Use Python for .py files, otherwise run command directly
            cmd = cfg["cmd"]
            if cmd[0].endswith(".py"):
                cmd = [sys.executable] + cmd
                cwd = os.path.join(ROOT_DIR, "..")
            else:
                cwd = cfg.get("cwd", ROOT_DIR)

            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            service_processes[name] = proc
            logger.info(f"[Service] Started {name} (PID {proc.pid})")
            return jsonify({"ok": True, "name": name, "pid": proc.pid, "port": cfg["port"]})
        except Exception as e:
            logger.error(f"[Service] Failed to start {name}: {e}")
            return jsonify({"ok": False, "msg": str(e)}), 500


@bp.route("/api/services/stop/<name>", methods=["POST"])
def api_services_stop(name):
    """Stop a service"""
    if name == "StarOfficeUI":
        return jsonify({"ok": False, "msg": "Cannot stop StarOfficeUI (this server)"}), 400

    with service_lock:
        proc = service_processes.get(name)
        if not proc or proc.poll() is not None:
            return jsonify({"ok": False, "msg": f"{name} is not running"}), 404

        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            del service_processes[name]
            logger.info(f"[Service] Stopped {name}")
            return jsonify({"ok": True, "name": name})
        except Exception as e:
            logger.error(f"[Service] Failed to stop {name}: {e}")
            return jsonify({"ok": False, "msg": str(e)}), 500
