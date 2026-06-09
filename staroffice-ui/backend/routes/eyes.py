"""Eyes Tools routes"""

from flask import Blueprint, jsonify

from config import EYES_TOOLS, CATEGORY_LABELS, STATUS_LABELS

bp = Blueprint("eyes", __name__)


@bp.route("/api/eyes/tools", methods=["GET"])
def api_eyes_tools():
    """Get eyes tool library data"""
    return jsonify({"tools": EYES_TOOLS, "categories": CATEGORY_LABELS, "status_labels": STATUS_LABELS})
