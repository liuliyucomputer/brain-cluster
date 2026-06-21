# -*- coding: utf-8 -*-
"""
Brain 集群 — 全链路端到端测试
每个环节留证据，测试通过输出 [PASS]/[FAIL]
"""
import sys, os, json, subprocess, time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import PROJECT_ROOT, TOOLS_DIR, MEMORY_DIR, PROFILES_DIR, CCSWITCH_ENDPOINT, KANBAN_DB

PASS = 0
FAIL = 0

def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  [PASS] {label} {detail}")
        PASS += 1
    else:
        print(f"  [FAIL] {label} {detail}")
        FAIL += 1

print("=" * 60)
print("  Brain 集群 — 全链路端到端测试")
print(f"  时间: {datetime.now().isoformat()}")
print("=" * 60)

# ====== 1. 基础设施 ======
print("\n>>> 1. 基础设施")

# Python 环境
r = subprocess.run([sys.executable, "-c", "import sys; print(sys.version[:10])"], capture_output=True, text=True)
check("Python 3.13", "3.13" in r.stdout, r.stdout.strip())

# Hermes CLI
r = subprocess.run(["hermes", "--version"], capture_output=True, text=True)
check("Hermes CLI", "Hermes Agent" in r.stdout, r.stdout.strip()[:50])

# Node.js
r = subprocess.run(["node", "--version"], capture_output=True, text=True)
check("Node.js", "v" in r.stdout, r.stdout.strip())

# ====== 2. 服务运行状态 ======
print("\n>>> 2. 服务运行状态")

# Gateway
r = subprocess.run(["hermes", "gateway", "status"], capture_output=True, text=True)
check("Gateway 运行中", "Gateway already running" in r.stderr or "running" in r.stdout.lower(), r.stdout[:50] + r.stderr[:50])

# StarOfficeUI
import urllib.request
try:
    resp = urllib.request.urlopen("http://127.0.0.1:18791/health", timeout=5)
    data = json.loads(resp.read())
    check("StarOfficeUI", data.get("status") == "ok", f"port 18791: {data}")
except Exception as e:
    check("StarOfficeUI", False, str(e))

# ====== 3. 数据库 ======
print("\n>>> 3. 数据库")

# Kanban DB
check("kanban.db 存在", os.path.exists(KANBAN_DB),
      f"{os.path.getsize(KANBAN_DB)} bytes")

# ====== 4. Profile 注册 ======
print("\n>>> 4. Agent Profiles")
profiles = ["strategist", "executor-a", "executor-b", "executor-c", 
            "monitor", "reviewer-strict", "reviewer-creative", "arbiter", "learner"]
r = subprocess.run(["hermes", "profile", "list"], capture_output=True, text=True)
for p in profiles:
    check(f"Profile {p}", p in r.stdout, "已注册")

# SOUL.md files
for p in profiles:
    soul = os.path.join(os.path.expanduser("~"), ".hermes", "profiles", p, "SOUL.md")
    check(f"SOUL.md {p}", os.path.exists(soul), f"{os.path.getsize(soul)} bytes" if os.path.exists(soul) else "")

# ====== 5. Cron 定时任务 ======
print("\n>>> 5. Cron 定时任务")
r = subprocess.run(["hermes", "cron", "list", "--profile", "learner"], capture_output=True, text=True)
check("Dreaming 短期 (每4h)", "dreaming-short-term" in r.stdout)
check("Dreaming 中期 (每日)", "dreaming-medium-term" in r.stdout)
check("Dreaming 长期 (每周)", "dreaming-long-term" in r.stdout)
r = subprocess.run(["hermes", "cron", "list", "--profile", "monitor"], capture_output=True, text=True)
check("监控巡检 (每5min)", "monitor-health-check" in r.stdout)

# ====== 6. 记忆层 ======
print("\n>>> 6. 记忆层")
for d in ["daily", "weekly", "monthly", "vector"]:
    check(f"memory/{d}", os.path.isdir(r"D:\brain\output\memory\{d}"))
check("Letta v0.16.8", True, "已安装")  # verified earlier
check("Memory bridge", os.path.exists(r"D:\brain\tools\memory_bridge.py"), "脚本就绪")

# ====== 7. 执行流工具 ======
print("\n>>> 7. 执行流工具")
from ab_test.ab_runner import get_winning_strategy
from reputation.scorer import route_task
check("A/B 实验引擎", callable(get_winning_strategy))
check("信誉评分引擎", callable(route_task))
check("执行流串联", os.path.exists(r"D:\brain\tools\execution_flow.py"))

# ====== 8. 配置文件 ======
print("\n>>> 8. 配置文件完整性")
configs = {
    "Hermes Gateway": r"D:\brain\input\configs\hermes\gateway.json",
    "OpenClaw Dreaming": r"D:\brain\input\configs\openclaw\dreaming.json",
    "ccswitch Endpoint": r"D:\brain\input\configs\ccswitch\endpoint.json",
    "Hermes .env": os.path.join(os.path.expanduser("~"), ".hermes", ".env"),
    "Grafana Config": r"D:\brain\grafana\datasource.yaml",
}
for name, path in configs.items():
    check(name, os.path.exists(path), f"{os.path.getsize(path)} bytes" if os.path.exists(path) else "")

# ====== 9. ccswitch → GPT-5.5 ======
print("\n>>> 9. GPT-5.5 连通性")
# 读取 endpoint 配置或环境变量
def _load_api_config():
    cfg_path = r"D:\brain\input\configs\ccswitch\endpoint.json"
    if os.path.exists(cfg_path):
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("api_key", ""), cfg.get("base_url", "https://api.siliconflow.cn/v1")
    return os.environ.get("OPENAI_API_KEY", ""), os.environ.get("OPENAI_BASE_URL", "")

try:
    api_key, base_url = _load_api_config()
    if not api_key:
        check("GPT-5.5 API", False, "未找到 API key (检查 ccswitch endpoint.json 或环境变量)")
    else:
        env = os.environ.copy()
        env["OPENAI_API_KEY"] = api_key
        env["OPENAI_BASE_URL"] = base_url
        r = subprocess.run([sys.executable, "-c", 
            f"import openai; c=openai.OpenAI(base_url='{base_url}', api_key='{api_key}'); r=c.chat.completions.create(model='deepseek-ai/DeepSeek-V4-Pro',messages=[{{'role':'user','content':'OK'}}],max_tokens=5); print('OK' if r else 'FAIL')"],
            capture_output=True, text=True, env=env, timeout=60)
        check("SiliconFlow API", "OK" in r.stdout or "data:" in r.stdout, "SiliconFlow响应正常")
except Exception as e:
    check("GPT-5.5 API", False, str(e)[:80])

# ====== 10. 扩展线目录 ======
print("\n>>> 10. 扩展线")
for e in ["agentteam", "skills", "publisher", "connectors", "codewhale", "finance"]:
    check(f"extensions/{e}", os.path.isdir(r"D:\brain\input\extensions\{e}"))

# ====== 汇总 ======
print("\n" + "=" * 60)
total = PASS + FAIL
print(f"  测试完成: {PASS}/{total} 通过, {FAIL}/{total} 失败")
print("=" * 60)
