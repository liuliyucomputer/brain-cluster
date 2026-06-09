"""SSE events routes"""

import json
import queue
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request

from utils import _sse_queues, _sse_lock, _sse_broadcast, _sse_cleanup

bp = Blueprint("events", __name__)


@bp.route("/api/events", methods=["GET"])
def api_events_stream():
    """SSE 实时事件流 — 替代 3 秒轮询"""
    client_id = str(uuid.uuid4())[:8]
    q = queue.Queue(maxsize=200)
    with _sse_lock:
        _sse_queues[client_id] = q

    def generate():
        # Send initial connection event
        yield f"id: {client_id}\nevent: connected\ndata: {{\"client\": \"{client_id}\"}}\n\n"

        while True:
            try:
                # Wait up to 15s, then send heartbeat
                payload = q.get(timeout=15)
                yield f"id: {client_id}\ndata: {payload}\n\n"
            except queue.Empty:
                # Send heartbeat to keep connection alive
                yield f"id: {client_id}\nevent: heartbeat\ndata: {{\"ts\": \"{datetime.now().isoformat()}\"}}\n\n"
            except GeneratorExit:
                break

        # Cleanup on disconnect
        with _sse_lock:
            _sse_queues.pop(client_id, None)

    from flask import current_app
    return current_app.response_class(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@bp.route("/api/events/push", methods=["POST"])
def api_events_push():
    """手动推送事件（供编排器和 watchdog 调用）"""
    data = request.get_json(silent=True) or {}
    event_type = data.get("type", "generic")
    event_data = data.get("data", {})
    _sse_broadcast(event_type, event_data)

    return jsonify({
        "ok": True,
        "type": event_type,
        "clients": len(_sse_queues),
        "ts": datetime.now().isoformat(),
    })
