#!/usr/bin/env python3
"""Star Office UI - Backend State Service"""

import logging
import os
from datetime import datetime

from flask import Flask

from config import ROOT_DIR, FRONTEND_DIR
from routes import register_blueprints

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="/static")

# Register all blueprints
register_blueprints(app)


@app.after_request
def add_no_cache_headers(response):
    """Aggressively prevent caching for all responses"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ── Start ────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Star Office UI - Backend State Service")
    logger.info(f"Dashboard: http://0.0.0.0:18791/dashboard-v2")
    logger.info(f"State file: {os.path.join(ROOT_DIR, 'state.json')}")
    logger.info("Listening on: http://0.0.0.0:18791")
    logger.info("=" * 50)
    app.run(host="0.0.0.0", port=18791, debug=False)
