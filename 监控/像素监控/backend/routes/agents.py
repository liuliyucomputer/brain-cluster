"""Agent related routes"""

import random
import string
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request

from config import JOIN_KEYS_FILE
from utils import (
    load_agents_state,
    save_agents_state,
    load_join_keys,
    save_join_keys,
    normalize_agent_state,
    state_to_area,
)

bp = Blueprint("agents", __name__)


@bp.route("/agents", methods=["GET"])
def get_agents():
    """Get full agents list (for multi-agent UI), with auto-cleanup on access"""
    agents = load_agents_state()
    now = datetime.now()

    cleaned_agents = []
    keys_data = load_join_keys()

    for a in agents:
        if a.get("isMain"):
            cleaned_agents.append(a)
            continue

        auth_expires_at_str = a.get("authExpiresAt")
        auth_status = a.get("authStatus", "pending")

        # 1) 超时未批准自动 leave
        if auth_status == "pending" and auth_expires_at_str:
            try:
                auth_expires_at = datetime.fromisoformat(auth_expires_at_str)
                if now > auth_expires_at:
                    key = a.get("joinKey")
                    if key:
                        key_item = next((k for k in keys_data.get("keys", []) if k.get("key") == key), None)
                        if key_item:
                            key_item["used"] = False
                            key_item["usedBy"] = None
                            key_item["usedByAgentId"] = None
                            key_item["usedAt"] = None
                    continue
            except Exception:
                pass

        # 2) 超时未推送自动离线（超过5分钟）
        last_push_at_str = a.get("lastPushAt")
        if auth_status == "approved" and last_push_at_str:
            try:
                last_push_at = datetime.fromisoformat(last_push_at_str)
                age = (now - last_push_at).total_seconds()
                if age > 300:  # 5分钟无推送自动离线
                    a["authStatus"] = "offline"
            except Exception:
                pass

        cleaned_agents.append(a)

    save_agents_state(cleaned_agents)
    save_join_keys(keys_data)

    return jsonify(cleaned_agents)


@bp.route("/agent-approve", methods=["POST"])
def agent_approve():
    """Approve an agent (set authStatus to approved)"""
    try:
        data = request.get_json()
        agent_id = (data.get("agentId") or "").strip()
        if not agent_id:
            return jsonify({"ok": False, "msg": "缺少 agentId"}), 400

        agents = load_agents_state()
        target = next((a for a in agents if a.get("agentId") == agent_id and not a.get("isMain")), None)
        if not target:
            return jsonify({"ok": False, "msg": "未找到 agent"}), 404

        target["authStatus"] = "approved"
        target["authApprovedAt"] = datetime.now().isoformat()
        target["authExpiresAt"] = (datetime.now() + timedelta(hours=24)).isoformat()  # 默认授权24h

        save_agents_state(agents)
        return jsonify({"ok": True, "agentId": agent_id, "authStatus": "approved"})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


@bp.route("/agent-reject", methods=["POST"])
def agent_reject():
    """Reject an agent (set authStatus to rejected and optionally revoke key)"""
    try:
        data = request.get_json()
        agent_id = (data.get("agentId") or "").strip()
        if not agent_id:
            return jsonify({"ok": False, "msg": "缺少 agentId"}), 400

        agents = load_agents_state()
        target = next((a for a in agents if a.get("agentId") == agent_id and not a.get("isMain")), None)
        if not target:
            return jsonify({"ok": False, "msg": "未找到 agent"}), 404

        target["authStatus"] = "rejected"
        target["authRejectedAt"] = datetime.now().isoformat()

        # Optionally free join key back to unused
        join_key = target.get("joinKey")
        keys_data = load_join_keys()
        if join_key:
            key_item = next((k for k in keys_data.get("keys", []) if k.get("key") == join_key), None)
            if key_item:
                key_item["used"] = False
                key_item["usedBy"] = None
                key_item["usedByAgentId"] = None
                key_item["usedAt"] = None

        # Remove from agents list
        agents = [a for a in agents if a.get("agentId") != agent_id or a.get("isMain")]

        save_agents_state(agents)
        save_join_keys(keys_data)
        return jsonify({"ok": True, "agentId": agent_id, "authStatus": "rejected"})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500
