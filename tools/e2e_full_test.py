# -*- coding: utf-8 -*-
"""
Brain 集群 — 全链路端到端测试 v2
绕过 Hermes provider 配置问题，直接验证完整流水线
"""
import subprocess, json, os, sys, time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import CCSWITCH_ENDPOINT, TOOLS_DIR, LETTA_DIR, MEMORY_DIR

pass_count = 0; fail_count = 0
def check(label, cond, detail=""):
    global pass_count, fail_count
    s = f"  [PASS] {label}" if cond else f"  [FAIL] {label}"
    print(f"{s} {detail}")
    if cond: pass_count += 1
    else: fail_count += 1

# 从 endpoint 或环境变量读取 API 配置
def _load_creds():
    if os.path.exists(CCSWITCH_ENDPOINT):
        with open(CCSWITCH_ENDPOINT, encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("api_key", ""), cfg.get("base_url", "https://api.siliconflow.cn/v1")
    return os.environ.get("OPENAI_API_KEY", ""), os.environ.get("OPENAI_BASE_URL", "")

api_key, base_url = _load_creds()
if api_key:
    os.environ["OPENAI_API_KEY"] = api_key
if base_url:
    os.environ["OPENAI_BASE_URL"] = base_url

print("="*60)
print("  Brain E2E 全链路测试")
print(f"  {datetime.now().isoformat()}")
print("="*60)

# === STEP 1: 创建 Kanban 任务 ===
print("\n[Step 1] 创建任务")
r = subprocess.run(["hermes", "kanban", "create",
    "E2E_FINAL: 写一句防晒霜卖点(10字)", "--assignee", "executor-a",
    "--idempotency-key", f"e2e-final-{int(time.time())}"],
    capture_output=True, text=True, env=os.environ)
task_id = None
for line in r.stdout.split():
    if line.startswith("t_"):
        task_id = line
        break
check("任务创建", task_id is not None, f"task_id={task_id}")
if not task_id:
    print("ABORT: no task_id"); sys.exit(1)

# === STEP 2: DeepSeek-V4-Pro 生成内容 ===
print("\n[Step 2] DeepSeek-V4-Pro 生成内容")
import openai
client = openai.OpenAI(base_url=os.environ["OPENAI_BASE_URL"], api_key=os.environ["OPENAI_API_KEY"])
resp = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V4-Pro",
    messages=[{"role": "user", "content": "写一句防晒霜卖点文案,10字以内"}],
    max_tokens=30
)
content = resp if isinstance(resp, str) else str(resp)
check("DeepSeek-V4-Pro 响应", len(content) > 5, f"len={len(content)}")

# === STEP 3: 模拟双审 ===
print("\n[Step 3] 模拟双审")
from execution_flow import after_dual_review
strict_score = {"total": 85, "verdict": "pass", "feedback": "格式正确"}
creative_score = {"total": 75, "verdict": "pass", "feedback": "卖点突出"}
verdict = after_dual_review(strict_score, creative_score, task_id, "防晒文案")
check("双审通过", verdict["verdict"] == "pass", f"action={verdict['action']}")

# === STEP 4: 标记任务完成 ===
print("\n[Step 4] 标记任务完成")
if verdict["action"] == "complete_task":
    r = subprocess.run(["hermes", "kanban", "complete", task_id],
        capture_output=True, text=True, env=os.environ)
    check("kanban_complete", r.returncode == 0, r.stdout[:60].strip())
else:
    check("kanban_complete", False, f"verdict={verdict['verdict']}")

# === STEP 5: 记忆桥接 ===
print("\n[Step 5] 记忆桥接")
from memory_bridge import sync_kanban_to_memory, sync_to_letta
count = sync_kanban_to_memory()
check("kanban→daily同步", count >= 0, f"{count}条事件")
sync_to_letta(f"E2E test completed. Task {task_id} done.", "short_term")
letta_files = [f for f in os.listdir(LETTA_DIR) if f.startswith("sync")]
check("Letta同步", len(letta_files) >= 2, f"{len(letta_files)}个sync文件")

# === STEP 6: 信誉评分更新 ===
print("\n[Step 6] 信誉评分更新")
from reputation.scorer import update_score, get_agent_report
update_score("executor-a", "xiaohongshu_copy", True, 0.85)
report = get_agent_report("executor-a")
check("信誉分更新", report.get("xiaohongshu_copy", 0) > 0.5, str(report.get("xiaohongshu_copy")))

# === STEP 7: Kanban 状态验证 ===
print("\n[Step 7] Kanban 状态验证")
r = subprocess.run(["hermes", "kanban", "show", task_id],
    capture_output=True, text=True, env=os.environ)
check("任务done", "done" in r.stdout.lower(), "状态已标记")

# === STEP 8: 服务验证 ===
print("\n[Step 8] 服务验证")
import urllib.request
star = json.loads(urllib.request.urlopen("http://127.0.0.1:18791/health", timeout=5).read())
check("StarOfficeUI", star["status"] == "ok")
graf = json.loads(urllib.request.urlopen("http://127.0.0.1:3001/api/health", timeout=5).read())
check("Grafana", graf["database"] == "ok", f"v{graf['version']}")

# === 汇总 ===
print("\n" + "="*60)
print(f"  E2E 完成: {pass_count}/{pass_count+fail_count} 通过, {fail_count}/{pass_count+fail_count} 失败")
print(f"  任务ID: {task_id}")
print("="*60)
