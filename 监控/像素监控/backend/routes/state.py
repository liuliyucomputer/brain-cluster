"""State & status routes"""

from datetime import datetime
from flask import Blueprint, jsonify, request

from utils import load_state, save_state

bp = Blueprint("state", __name__)


@bp.route("/status", methods=["GET"])
def get_status():
    """Get current main state (backward compatibility)"""
    state = load_state()
    return jsonify(state)


@bp.route("/set_state", methods=["POST"])
def set_state_endpoint():
    """Set state via POST (for UI control panel)"""
    try:
        data = request.get_json()
        if not isinstance(data, dict):
            return jsonify({"status": "error", "msg": "invalid json"}), 400
        state = load_state()
        if "state" in data:
            s = data["state"]
            valid_states = {"idle", "writing", "researching", "executing", "syncing", "error"}
            if s in valid_states:
                state["state"] = s
        if "detail" in data:
            state["detail"] = data["detail"]
        state["updated_at"] = datetime.now().isoformat()
        save_state(state)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500


@bp.route("/health", methods=["GET"])
def health():
    """Health check"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})
