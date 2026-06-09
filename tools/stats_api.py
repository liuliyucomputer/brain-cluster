# -*- coding: utf-8 -*-
"""
Brain 集群 — 统计 API (Grafana JSON Datasource)
提供 kanban.db → Grafana 可读取的 JSON 数据
"""
from flask import Flask, jsonify, request
import sqlite3, os

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import KANBAN_DB

app = Flask(__name__)

@app.route("/", methods=["GET"])
def root():
    return jsonify({"service": "brain-stats-api", "port": 19999})

@app.route("/query", methods=["POST"])
def query():
    """Grafana Simple JSON datasource query endpoint"""
    data = request.get_json()
    targets = data.get("targets", [])
    results = []
    
    conn = sqlite3.connect(KANBAN_DB)
    
    for t in targets:
        target = t.get("target", "tasks")
        
        if target == "tasks":
            rows = conn.execute("SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status").fetchall()
            for r in rows:
                results.append({"target": f"tasks.{r[0]}", "datapoints": [[r[1], 0]]})
        
        elif target == "agents":
            rows = conn.execute("SELECT assignee, COUNT(*) as cnt FROM tasks GROUP BY assignee").fetchall()
            for r in rows:
                results.append({"target": f"agents.{r[0]}", "datapoints": [[r[1], 0]]})
        
        elif target == "recent":
            rows = conn.execute("SELECT status, created_at FROM tasks ORDER BY created_at DESC LIMIT 20").fetchall()
            for i, r in enumerate(rows):
                results.append({"target": f"recent.{r[0]}", "datapoints": [[1, i]]})
    
    conn.close()
    return jsonify(results)

@app.route("/search", methods=["POST"])
def search():
    return jsonify(["tasks", "agents", "recent"])

@app.route("/stats", methods=["GET"])
def stats():
    """直接查看统计 (浏览器可访问)"""
    conn = sqlite3.connect(KANBAN_DB)
    
    task_stats = dict(conn.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status").fetchall())
    agent_stats = dict(conn.execute("SELECT assignee, COUNT(*) FROM tasks GROUP BY assignee WHERE assignee IS NOT NULL").fetchall())
    total = sum(task_stats.values())
    
    logs = len([f for f in os.listdir(r"D:\brain\letta") if f.startswith("sync")]) if os.path.exists(r"D:\brain\letta") else 0
    
    conn.close()
    
    return jsonify({
        "kanban": {
            "total_tasks": total,
            "by_status": task_stats,
            "by_agent": agent_stats,
        },
        "letta_sync_files": logs,
        "services": {
            "grafana": "http://localhost:3001",
            "staroffice": "http://localhost:18791",
            "dashboard": "http://localhost:9119",
            "stats_api": "http://localhost:19999",
        }
    })

if __name__ == "__main__":
    print("Brain Stats API on http://localhost:19999")
    print("  /stats  — full statistics")
    print("  /query  — Grafana JSON datasource endpoint")
    app.run(host="0.0.0.0", port=19999, debug=False)
