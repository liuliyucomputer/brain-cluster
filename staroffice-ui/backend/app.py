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
app.config['JSON_AS_ASCII'] = False  # Ensure Unicode chars are not escaped in jsonify

# Ensure API key is loaded before blueprints import it
from config import _load_api_key
_load_api_key()

# Register all blueprints (commander, agents, events, eyes, etc.)
register_blueprints(app)

# ── Additional routes (dashboard v2, services, stats, logs, tasks, memory) ──
import json, socket, threading, sqlite3 as sql, time
from flask import jsonify, request, make_response, redirect, send_from_directory

service_processes = {}
service_lock = threading.Lock()

def _check_port(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.3)
    try: r = s.connect_ex(('127.0.0.1', port)) == 0; return r
    finally: s.close()


@app.after_request
def add_no_cache_headers(response):
    """Aggressively prevent caching for all responses"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


# ═══════════════ CUSTOM ROUTES ═══════════════

@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


@app.route("/dashboard")
def dashboard_redirect():
    return redirect("/dashboard-v2", code=302)


@app.route("/dashboard-v2")
def dashboard_v2():
    dist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend-v2", "dist")
    if os.path.exists(os.path.join(dist_path, "index.html")):
        with open(os.path.join(dist_path, "index.html"), "r", encoding="utf-8") as f:
            html = f.read()
        resp = make_response(html)
        resp.headers["Content-Type"] = "text/html; charset=utf-8"
        return resp
    return jsonify({"msg": "Dashboard v2 not built"}), 404


@app.route("/assets/<path:filename>")
def dashboard_assets(filename):
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend-v2", "dist", "assets")
    return send_from_directory(assets_dir, filename)


# ── Shutdown ──
@app.route("/api/shutdown", methods=["POST"])
def api_shutdown():
    """Gracefully stop all services and exit"""
    import threading

    def _shutdown():
        import time
        time.sleep(0.5)
        # Stop all tracked services
        for name, proc in list(service_processes.items()):
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        # Stop Grafana (port 3001)
        try:
            import subprocess
            subprocess.run(["taskkill", "/F", "/IM", "grafana-server.exe"], capture_output=True, timeout=5)
        except Exception:
            pass
        # Exit Flask
        os._exit(0)

    threading.Thread(target=_shutdown, daemon=True).start()
    return jsonify({"status": "shutting_down", "message": "所有服务正在停止..."})


# ── Monitor Proxy ──
@app.route("/api/monitor")
def api_monitor_proxy():
    try:
        import urllib.request
        data = urllib.request.urlopen("http://127.0.0.1:19997/api/full_state", timeout=3).read()
        return jsonify(json.loads(data))
    except:
        return jsonify({"error": "Monitor unavailable"}), 502


# ── Service Management ──
SERVICE_CONFIGS = {
    "Dashboard": {
        "cmd": [r"C:\Users\Administrator\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe", "dashboard"],
        "port": 9119, "zh": "看板", "cwd": os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."),
    },
    "Grafana": {
        "cmd": [r"D:\brain\grafana\grafana-v11.6.0\bin\grafana-server.exe", "--config", r"D:\brain\grafana\custom.ini",
                "--homepath", r"D:\brain\grafana\grafana-v11.6.0"],
        "port": 3001, "zh": "监控图", "cwd": r"D:\brain\grafana\grafana-v11.6.0",
    },
    "StatsAPI": {
        "cmd": ["tools/monitor_dashboard.py"],
        "port": 19999, "zh": "数据源", "cwd": os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."),
    },
    "Gateway": {
        "cmd": [
            "cmd", "/c",
            "set OPENAI_API_KEY=sk-ukkghdobyfyttizuaxhtqmmdcprycxvdcixoviwhrzlywksx && "
            "set OPENAI_BASE_URL=https://api.siliconflow.cn/v1 && "
            "set GATEWAY_ALLOW_ALL_USERS=true && set PYTHONIOENCODING=utf-8 && "
            r"C:\Users\Administrator\AppData\Local\hermes\hermes-agent\venv\Scripts\hermes.exe gateway run --replace"
        ],
        "port": 18789, "zh": "网关", "cwd": os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."),
    },
}

@app.route("/api/services/status")
def api_services_status():
    result = {"StarOfficeUI": {"running": True, "port": 18791, "zh": "面板", "pid": None}}
    for name, cfg in SERVICE_CONFIGS.items():
        running = _check_port(cfg["port"])
        proc = service_processes.get(name)
        result[name] = {"running": running, "port": cfg["port"], "zh": cfg["zh"], "pid": proc.pid if (proc and proc.poll() is None) else None}
    return jsonify(result)

@app.route("/api/services/start/<name>", methods=["POST"])
def api_services_start(name):
    if name == "StarOfficeUI":
        return jsonify({"ok": False, "msg": "Already running"}), 400
    cfg = SERVICE_CONFIGS.get(name)
    if not cfg: return jsonify({"ok": False, "msg": f"Unknown: {name}"}), 404
    with service_lock:
        if service_processes.get(name) and service_processes[name].poll() is None:
            return jsonify({"ok": False, "msg": f"{name} already running"}), 409
        if _check_port(cfg["port"]):
            return jsonify({"ok": False, "msg": f"Port {cfg['port']} in use"}), 409
        try:
            import sys as _sys
            cmd = cfg["cmd"]
            if cmd[0].endswith(".py"):
                cmd = [_sys.executable] + cmd
            proc = subprocess.Popen(cmd, cwd=cfg.get("cwd", os.path.dirname(os.path.abspath(__file__))),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            service_processes[name] = proc
            logger.info(f"[Service] Started {name} (PID {proc.pid})")
            return jsonify({"ok": True, "name": name, "pid": proc.pid, "port": cfg["port"]})
        except Exception as e:
            return jsonify({"ok": False, "msg": str(e)}), 500

@app.route("/api/services/stop/<name>", methods=["POST"])
def api_services_stop(name):
    cfg = SERVICE_CONFIGS.get(name)
    if not cfg: return jsonify({"ok": False, "msg": f"Unknown: {name}"}), 404
    with service_lock:
        proc = service_processes.pop(name, None)
        if proc and proc.poll() is None:
            try: proc.terminate(); proc.wait(timeout=5)
            except: proc.kill()
            return jsonify({"ok": True, "name": name, "stopped": True})
        return jsonify({"ok": False, "msg": f"{name} not running"}), 404


# ── Task Creator ──
@app.route("/api/tasks/create", methods=["POST"])
def api_tasks_create():
    try:
        data = request.get_json(force=True) if request.is_json else json.loads(request.data or '{}')
        title = (data.get("title") or "").strip()
        assignee = (data.get("assignee") or "strategist").strip()
        if not title: return jsonify({"ok": False, "msg": "标题不能为空"}), 400
        import uuid
        kanban_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "output", "memory", "kanban.db")
        task_id = f"t_{uuid.uuid4().hex[:8]}"
        now = int(time.time())
        conn = sql.connect(kanban_db)
        conn.execute("INSERT INTO tasks (id, title, body, assignee, status, created_by, created_at, workspace_kind) VALUES (?,?,?,?,'ready','dashboard',?,'scratch')",
                     (task_id, title, data.get("body", ""), assignee, now))
        conn.commit(); conn.close()
        logger.info(f"[Task] Created: {task_id} -> {assignee}")
        return jsonify({"ok": True, "task_id": task_id, "title": title, "assignee": assignee})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


# ── Memory Manager ──
_MEMORY_DIRS = [
    ("项目记忆", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".workbuddy", "memory")),
    ("用户记忆", os.path.expanduser("~/.workbuddy")),
]

@app.route("/api/memory/list")
def api_memory_list():
    results = []
    for label, d in _MEMORY_DIRS:
        if not os.path.isdir(d): continue
        for f in sorted(os.listdir(d)):
            fp = os.path.join(d, f)
            if os.path.isfile(fp) and (f.endswith(".md") or f.endswith(".json")):
                st = os.stat(fp)
                results.append({"label": label, "name": f, "path": fp, "size_kb": round(st.st_size/1024,1), "modified": datetime.fromtimestamp(st.st_mtime).isoformat()})
    return jsonify({"files": results})

@app.route("/api/memory/read")
def api_memory_read():
    path = request.args.get("path", "")
    if not path or not os.path.isfile(path): return jsonify({"ok": False, "msg": "不存在"}), 404
    allowed = any(os.path.abspath(path).startswith(os.path.abspath(d)) for _, d in _MEMORY_DIRS) or "MAINTENANCE_LOG" in path
    if not allowed: return jsonify({"ok": False, "msg": "禁止访问"}), 403
    with open(path, "r", encoding="utf-8", errors="replace") as f: content = f.read()
    return jsonify({"ok": True, "path": path, "content": content})

@app.route("/api/memory/update", methods=["POST"])
def api_memory_update():
    data = request.get_json(force=True)
    path = (data.get("path") or "").strip()
    if not path: return jsonify({"ok": False, "msg": "路径为空"}), 400
    allowed = any(os.path.abspath(path).startswith(os.path.abspath(d)) for _, d in _MEMORY_DIRS) or "MAINTENANCE_LOG" in path
    if not allowed: return jsonify({"ok": False, "msg": "禁止修改"}), 403
    with open(path, "w", encoding="utf-8") as f: f.write(data.get("content", ""))
    return jsonify({"ok": True})

@app.route("/api/memory/delete", methods=["POST"])
def api_memory_delete():
    data = request.get_json(force=True)
    path = (data.get("path") or "").strip()
    if not path or not path.endswith(".md"): return jsonify({"ok": False, "msg": "只允许.md"}), 400
    allowed = any(os.path.abspath(path).startswith(os.path.abspath(d)) for _, d in _MEMORY_DIRS) or "MAINTENANCE_LOG" in path
    if not allowed: return jsonify({"ok": False, "msg": "禁止删除"}), 403
    os.remove(path)
    return jsonify({"ok": True})


# ── Logs ──
LOG_ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "output", "logs")

def _read_log_tail(filepath, n=30):
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().strip().split("\n")[-n:]
        return lines
    except: return []

def _find_latest(d, prefix=""):
    try:
        return os.path.join(d, sorted([f for f in os.listdir(d) if f.endswith(".log") and f.startswith(prefix)], reverse=True)[0]) if os.path.isdir(d) else ""
    except: return ""

@app.route("/api/logs/<source>")
def api_logs(source):
    if source == "alerts": lines = _read_log_tail(os.path.join(LOG_ROOT_DIR, "alerts.log"), 20)
    elif source == "system": lines = _read_log_tail(_find_latest(os.path.join(LOG_ROOT_DIR, "system")), 40)
    elif source == "app": lines = _read_log_tail(os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.log"), 20)
    else: lines = []
    return jsonify({"lines": lines, "source": source})

AGENT_NAMES = ["strategist","executor-a","executor-b","executor-c","monitor","reviewer-strict","reviewer-creative","arbiter","learner"]
SERVICE_NAMES = ["gateway","grafana","staroffice","orchestrator"]

@app.route("/api/logs/agents/<name>")
def api_logs_agent(name):
    if name not in AGENT_NAMES: return jsonify({"lines": [], "source": name}), 404
    return jsonify({"lines": _read_log_tail(_find_latest(os.path.join(LOG_ROOT_DIR, "agents")), 20), "source": name})

@app.route("/api/logs/service/<name>")
def api_logs_service(name):
    if name not in SERVICE_NAMES: return jsonify({"lines": [], "source": name}), 404
    return jsonify({"lines": _read_log_tail(_find_latest(os.path.join(LOG_ROOT_DIR, name)), 30), "source": name})


import subprocess


# ── Task Manager API ──

@app.route("/api/tasks/list", methods=["GET"])
def api_tasks_list():
    """List all active tasks from kanban"""
    kanban_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "output", "memory", "kanban.db")
    live_db = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes", "kanban.db")
    db = live_db if os.path.exists(live_db) else kanban_db
    try:
        conn = sql.connect(db); conn.row_factory = sql.Row
        rows = conn.execute("SELECT id,title,assignee,status,created_at,worker_pid,consecutive_failures FROM tasks WHERE status NOT IN ('archived') ORDER BY rowid DESC LIMIT 50").fetchall()
        conn.close()
        tasks = [{"id":r["id"],"title":r["title"],"assignee":r["assignee"] or "?","status":r["status"],"created_at":r["created_at"],"pid":r["worker_pid"],"failures":r["consecutive_failures"]} for r in rows]
        return jsonify({"tasks":tasks,"total":len(tasks)})
    except Exception as e:
        return jsonify({"tasks":[],"total":0,"error":str(e)})

@app.route("/api/tasks/control", methods=["POST"])
def api_tasks_control():
    """Control tasks: pause/resume/kill"""
    data = json.loads(request.get_data(as_text=True) or '{}')
    action = data.get("action",""); task_ids = data.get("task_ids",[])
    if not task_ids: return jsonify({"ok":False,"msg":"请选择任务"}),400
    kanban_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "output", "memory", "kanban.db")
    live_db = os.path.join(os.environ.get("LOCALAPPDATA", ""), "hermes", "kanban.db")
    db = live_db if os.path.exists(live_db) else kanban_db
    conn = sql.connect(db)
    results = []
    for tid in task_ids:
        try:
            if action == "pause": conn.execute("UPDATE tasks SET status='blocked' WHERE id=? AND status NOT IN ('done','archived')",(tid,)); results.append(f"已暂停 {tid[:12]}")
            elif action == "resume": conn.execute("UPDATE tasks SET status='ready' WHERE id=? AND status IN ('blocked','failed')",(tid,)); results.append(f"已恢复 {tid[:12]}")
            elif action == "kill":
                row = conn.execute("SELECT worker_pid FROM tasks WHERE id=?",(tid,)).fetchone()
                if row and row[0]:
                    try: os.kill(row[0], 9)
                    except: pass
                conn.execute("UPDATE tasks SET status='archived' WHERE id=?",(tid,)); results.append(f"已终止 {tid[:12]}")
            else: return jsonify({"ok":False,"msg":f"未知操作:{action}"}),400
        except Exception as e: results.append(f"失败:{e}")
    conn.commit(); conn.close()
    return jsonify({"ok":True,"results":results})


# ── Director Agent API ──

DIRECTOR_API_KEY = "sk-ukkghdobyfyttizuaxhtqmmdcprycxvdcixoviwhrzlywksx"
DIRECTOR_BASE_URL = "https://api.siliconflow.cn/v1"
DIRECTOR_MODEL = "deepseek-ai/DeepSeek-V3"

@app.route("/api/director/analyze", methods=["POST"])
def api_director_analyze():
    """Director: analyze user request, decompose into agent tasks, generate prompts"""
    try:
        data = json.loads(request.get_data(as_text=True) or '{}')
    except json.JSONDecodeError:
        return jsonify({"ok": False, "msg": "Invalid JSON"}), 400
    user_request = (data.get("request") or "").strip()
    if not user_request:
        return jsonify({"ok": False, "msg": "请输入需求描述"}), 400

    import urllib.request as _ur
    prompt = f"""你是 Brain 集群的总监(Director)，凌驾于所有智能体之上。
用户的原始需求如下，你需要做三件事:
1. **分析**: 理解用户真实意图
2. **拆解**: 把需求拆成 2-4 个独立子任务
3. **分配**: 为每个子任务指定最合适的 Agent 并生成执行提示词

可选 Agent:
- strategist(策略): 任务分解、策略规划、信誉评估
- executor-a(文案): 小红书文案、创意写作
- executor-b(PPT): 演示文稿、可视化设计
- executor-c(数据): 数据分析、代码执行
- reviewer-strict(严审): 事实核查、合规审查
- reviewer-creative(创审): 创意评估、吸引力判断
- arbiter(仲裁): 分歧裁决
- monitor(监控): 健康巡检
- learner(学习): 知识蒸馏、记忆巩固

输出格式(严格JSON):
{{
  "analysis": "对用户需求的一句话分析",
  "tasks": [
    {{"title": "任务标题", "assignee": "agent-key", "prompt": "给这个Agent的详细执行提示词"}}
  ]
}}

用户需求: {user_request}"""

    try:
        payload = json.dumps({
            "model": DIRECTOR_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3, "max_tokens": 2000,
            "stream": False
        }).encode("utf-8")
        req = _ur.Request(f"{DIRECTOR_BASE_URL}/chat/completions", data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {DIRECTOR_API_KEY}"})
        resp = _ur.urlopen(req, timeout=30)
        body = json.loads(resp.read())
        content = body["choices"][0]["message"]["content"].strip()

        # Extract JSON from response (handle markdown code blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)
        logger.info(f"[Director] Analyzed request: {user_request[:30]}... -> {len(result.get('tasks',[]))} tasks")
        return jsonify({"ok": True, "analysis": result.get("analysis", ""), "tasks": result.get("tasks", [])})
    except json.JSONDecodeError as e:
        return jsonify({"ok": False, "msg": f"解析失败: {e}", "raw": content[:300] if 'content' in dir() else ""}), 500
    except Exception as e:
        logger.error(f"[Director] Failed: {e}")
        return jsonify({"ok": False, "msg": str(e)}), 500


@app.route("/api/director/dispatch", methods=["POST"])
def api_director_dispatch():
    """Dispatch Director's task plan to kanban"""
    try:
        data = json.loads(request.get_data(as_text=True) or '{}')
    except json.JSONDecodeError:
        return jsonify({"ok": False, "msg": "Invalid JSON"}), 400
    tasks = data.get("tasks", [])
    if not tasks:
        return jsonify({"ok": False, "msg": "没有任务可派发"}), 400
    import uuid
    kanban_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "output", "memory", "kanban.db")
    now = int(time.time())
    created = []
    conn = sql.connect(kanban_db)
    for t in tasks:
        task_id = f"t_{uuid.uuid4().hex[:8]}"
        conn.execute(
            "INSERT INTO tasks (id, title, body, assignee, status, created_by, created_at, workspace_kind) VALUES (?,?,?,?,'ready','director',?,'scratch')",
            (task_id, t.get("title", ""), t.get("prompt", ""), t.get("assignee", "strategist"), now))
        created.append({"task_id": task_id, "title": t.get("title", ""), "assignee": t.get("assignee", "")})
    conn.commit(); conn.close()
    logger.info(f"[Director] Dispatched {len(created)} tasks")
    return jsonify({"ok": True, "dispatched": len(created), "tasks": created})


# ── Start ────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Star Office UI - Backend State Service")
    logger.info(f"Dashboard: http://0.0.0.0:18791/dashboard-v2")
    logger.info(f"State file: {os.path.join(ROOT_DIR, 'state.json')}")
    logger.info("Listening on: http://0.0.0.0:18791")
    logger.info("Blueprints: commander, agents, events, eyes, memo, memory, monitor, services, state, tasks, views, logs")
    logger.info("Custom routes: /api/stats, /api/monitor, /api/services/*, /api/tasks/*, /api/memory/*, /api/logs/*")
    logger.info("=" * 50)
    app.run(host="0.0.0.0", port=18791, debug=False)
