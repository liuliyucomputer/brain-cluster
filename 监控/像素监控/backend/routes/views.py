"""Page / view routes"""

import os
from flask import Blueprint, make_response, redirect, send_from_directory

from config import ROOT_DIR, FRONTEND_DIR, VERSION_TIMESTAMP

bp = Blueprint("views", __name__)


@bp.route("/", methods=["GET"])
def index():
    """Serve the pixel office UI with built-in version cache busting"""
    with open(os.path.join(FRONTEND_DIR, "index.html"), "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("{{VERSION_TIMESTAMP}}", VERSION_TIMESTAMP)
    resp = make_response(html)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp


@bp.route("/join", methods=["GET"])
def join_page():
    """Serve the agent join page"""
    with open(os.path.join(FRONTEND_DIR, "join.html"), "r", encoding="utf-8") as f:
        html = f.read()
    resp = make_response(html)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp


@bp.route("/invite", methods=["GET"])
def invite_page():
    """Serve human-facing invite instruction page"""
    with open(os.path.join(FRONTEND_DIR, "invite.html"), "r", encoding="utf-8") as f:
        html = f.read()
    resp = make_response(html)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp


@bp.route("/dashboard", methods=["GET"])
def dashboard_redirect():
    """Redirect to dashboard v2"""
    return redirect("/dashboard-v2", code=302)


@bp.route("/dashboard-v2", methods=["GET"])
def dashboard_v2():
    """Brain Cluster Dashboard v2 (React SPA)"""
    dist_path = os.path.join(ROOT_DIR, "frontend-v2", "dist")
    if os.path.exists(os.path.join(dist_path, "index.html")):
        with open(os.path.join(dist_path, "index.html"), "r", encoding="utf-8") as f:
            html = f.read()
        resp = make_response(html)
        resp.headers["Content-Type"] = "text/html; charset=utf-8"
        return resp
    from flask import jsonify
    return jsonify({"msg": "Dashboard v2 not built yet. Run: cd frontend-v2 && npm run build"}), 404


@bp.route("/assets/<path:filename>", methods=["GET"])
def dashboard_v2_assets(filename):
    """Serve React SPA static assets"""
    assets_dir = os.path.join(ROOT_DIR, "frontend-v2", "dist", "assets")
    return send_from_directory(assets_dir, filename)
