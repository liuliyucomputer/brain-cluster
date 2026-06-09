# -*- coding: utf-8 -*-
"""
Brain 集群 — 扩展线统一集成引擎 (Extension Bridge)
将 6 条扩展线注册为 Hermes Tool / Profile，实现高标准化对接
"""
import os, json, sys, sqlite3
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import SKILLS_DIR, PUBLISHER_DIR, B_DRIVE_ROOT, EXTENSION_STATUS, EXTENSIONS_DIR, PROFILES_DIR

SKILLS_DIR = SKILLS_DIR
PUBLISHER_CODE = PUBLISHER_DIR
B_DRIVE_AGENTTEAM = os.path.join(B_DRIVE_ROOT, "AgentTeam")
B_DRIVE_CODEWHALE = os.path.join(B_DRIVE_ROOT, "codeWhale")
B_DRIVE_FINANCE_A = os.path.join(B_DRIVE_ROOT, "A_share_News_Face_Analysis_System")
B_DRIVE_FINANCE_S = os.path.join(B_DRIVE_ROOT, "Stock_Market_Ultimate_Game")

EXTENSION_STATUS_FILE = EXTENSION_STATUS

# ─── 集成状态管理 ───

def init_status():
    """初始化扩展线状态文件"""
    status = {
        "updated": datetime.now().isoformat(),
        "lines": {
            "skills": {"name": "CodeBuddy Skills (6)", "integrated": False, "tools": [], "verified": False},
            "publisher": {"name": "Publisher Pipeline", "integrated": False, "tools": [], "verified": False},
            "connectors": {"name": "21 Connectors", "integrated": False, "tools": [], "verified": False},
            "agentteam": {"name": "AgentTeam 12 Roles", "integrated": False, "tools": [], "verified": False},
            "codewhale": {"name": "codeWhale Executor", "integrated": False, "tools": [], "verified": False},
            "finance": {"name": "Finance Automation", "integrated": False, "tools": [], "verified": False},
        }
    }
    os.makedirs(os.path.dirname(EXTENSION_STATUS_FILE), exist_ok=True)
    with open(EXTENSION_STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    return status

def load_status():
    if os.path.exists(EXTENSION_STATUS_FILE):
        with open(EXTENSION_STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return init_status()

def save_status(st):
    with open(EXTENSION_STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)

def mark_integrated(line_key, tools=None, verified=False):
    st = load_status()
    if line_key in st["lines"]:
        st["lines"][line_key]["integrated"] = True
        if tools: st["lines"][line_key]["tools"] = tools
        if verified: st["lines"][line_key]["verified"] = True
    st["updated"] = datetime.now().isoformat()
    save_status(st)
    return st

# ─── 扩展 1: Skills (6 CodeBuddy Skill → Hermes Tools) ───

def discover_skills():
    """扫描已安装的 CodeBuddy Skills"""
    skills = {}
    for name in os.listdir(SKILLS_DIR):
        skill_dir = os.path.join(SKILLS_DIR, name)
        if not os.path.isdir(skill_dir): continue
        skill_md = os.path.join(skill_dir, "SKILL.md")
        if not os.path.exists(skill_md): continue
        with open(skill_md, "r", encoding="utf-8") as f:
            content = f.read()
        # Parse frontmatter
        desc = ""
        for line in content.split("\n"):
            if line.startswith("name:"): 
                name = line.split(":",1)[1].strip()
            if line.startswith("description:") or line.startswith("description: "):
                desc = line.split(":",1)[1].strip().strip('"')
        skills[name] = {"path": skill_dir, "description": desc[:100] if desc else "unknown"}
    return skills

def register_skills():
    """注册所有 Skills 为 Hermes Tools"""
    skills = discover_skills()
    registered = []
    
    tool_registry = {
        "ppt-pro-master": "ppt_generate",
        "xhs-creator-studio": "xhs_create_note",
        "resume-screener": "resume_screen",
        "financial-analysis": "financial_analyze",
        "work-report": "work_report",
        "batch-github-setup": "github_batch",
    }
    
    for skill_name, skill_info in skills.items():
        tool_name = tool_registry.get(skill_name, skill_name.replace("-", "_"))
        registered.append({
            "skill": skill_name,
            "tool": tool_name,
            "path": skill_info["path"],
            "description": skill_info["description"],
        })
    
    # 标记为已集成
    mark_integrated("skills", tools=[r["tool"] for r in registered])
    
    return {"count": len(registered), "tools": registered}

def verify_skills():
    """验证所有 Skill 文件完整性"""
    skills = discover_skills()
    results = {}
    tools = []
    for name, info in skills.items():
        skill_dir = info["path"]
        has_scripts = os.path.isdir(os.path.join(skill_dir, "scripts"))
        has_refs = os.path.isdir(os.path.join(skill_dir, "references"))
        has_assets = os.path.isdir(os.path.join(skill_dir, "assets"))
        results[name] = {
            "exists": True,
            "scripts": has_scripts,
            "references": has_refs,
            "assets": has_assets,
            "status": "ok" if has_scripts else "partial"
        }
        tools.append(name)
    mark_integrated("skills", tools=tools, verified=all(r["status"] == "ok" for r in results.values()))
    return results

# ─── 扩展 2: Publisher (小红书发布管道) ───

def register_publisher():
    """注册小红书发布管道"""
    publisher_tools = []
    
    # 检查 publisher 代码
    publisher_py = os.path.join(PUBLISHER_CODE, "xhs_publisher.py")
    if os.path.exists(publisher_py):
        publisher_tools.append({
            "tool": "publish_xiaohongshu",
            "type": "content_publish",
            "path": publisher_py,
            "description": "发布小红书图文：自动填表 + 手动点击发布",
            "params": ["title", "body", "images", "tags"],
            "mode": "semi_auto (manual_click=True)"
        })
    
    # 检查 B: 盘发布目录
    b_publish = os.path.join(B_DRIVE_ROOT, "CLI", "电商项目", "袜子测试")
    if os.path.isdir(b_publish):
        publisher_tools.append({
            "tool": "publish_queue",
            "type": "content_publish",
            "path": b_publish,
            "description": "B: 盘电商发布队列"
        })
    
    status = "ready" if publisher_tools else "partial"
    mark_integrated("publisher", tools=[t["tool"] for t in publisher_tools])
    
    return {"count": len(publisher_tools), "tools": publisher_tools, "status": status}

def verify_publisher():
    """验证发布管道"""
    publisher_py = os.path.join(PUBLISHER_CODE, "xhs_publisher.py")
    publisher_importable = False
    try:
        sys.path.insert(0, PUBLISHER_CODE)
        import xhs_publisher
        publisher_importable = hasattr(xhs_publisher, "publish_xiaohongshu")
    except Exception:
        publisher_importable = False
    
    results = {
        "xhs_publisher.py": os.path.exists(publisher_py),
        "importable": publisher_importable,
        "status": "ok" if publisher_importable else "not_importable"
    }
    mark_integrated("publisher", verified=publisher_importable)
    return results

# ─── 扩展 3: Connectors (MCP 连接器) ───

def register_connectors():
    """读取 MCP 配置文件"""
    mcp_json = os.path.expanduser(r"~\.workbuddy\mcp.json")
    connectors = []
    
    if os.path.exists(mcp_json):
        try:
            with open(mcp_json, "r", encoding="utf-8") as f:
                mcp_config = json.load(f)
            servers = mcp_config.get("mcpServers", {})
            for name, config in servers.items():
                connectors.append({
                    "name": name,
                    "type": "mcp_server",
                    "status": "configured",
                    "command": config.get("command", "unknown"),
                })
        except Exception:
            pass
    
    # 分类连接器
    alert_connectors = [c for c in connectors if c["name"] in 
        ["wecom","feishu","dingtalk","qq-mail","netease-mail"]]
    doc_connectors = [c for c in connectors if c["name"] in 
        ["tencent-docs","kdocs","tencent-survey"]]
    
    mark_integrated("connectors", tools=[c["name"] for c in connectors])
    
    return {
        "total": len(connectors),
        "alert_channels": len(alert_connectors),
        "doc_channels": len(doc_connectors),
        "connectors": connectors,
        "alert_ready": len(alert_connectors) > 0
    }

def verify_connectors():
    """验证连接器 — 读取实际 MCP JSON 配置"""
    mcp_json = os.path.expanduser(r"~\.workbuddy\mcp.json")
    actual_connectors = []
    
    if os.path.exists(mcp_json):
        try:
            with open(mcp_json, "r", encoding="utf-8") as f:
                mcp_config = json.load(f)
            servers = mcp_config.get("mcpServers", {})
            for name, config in servers.items():
                actual_connectors.append({
                    "name": name,
                    "command": config.get("command", ""),
                    "args": config.get("args", []),
                })
        except Exception:
            actual_connectors = []
    
    tools = [c["name"] for c in actual_connectors]
    status = "configured" if actual_connectors else "empty"
    mark_integrated("connectors", verified=len(actual_connectors) > 0, tools=tools)
    return {"count": len(actual_connectors), "status": status, "connectors": tools[:10]}

# ─── 扩展 4: AgentTeam (基于 D:\eyes\harness 6 种架构模式) ───

def register_agentteam():
    """基于 harness 架构模式注册 AgentTeam Profiles"""
    harness_path = r"D:\eyes\harness"
    harness_exists = os.path.isdir(harness_path)
    
    profiles = [
        {"name": "expert-coordinator", "role": "Expert Pool Coordinator", "model": "deepseek-ai/DeepSeek-V4-Pro", "temperature": 0.3,
         "desc": "根据任务类型自动调配领域专家",
         "prompt": """你是 Brain 集群的 Expert Pool Coordinator。你有以下领域专家可用:
- executor-a: 内容创作(小红书/抖音文案)  
- executor-b: PPT和可视化设计
- executor-c: 数据分析和代码执行
- finance-analyzer: A股舆情与财务分析
- codewhale-executor: 重型代码编译构建

任务路由流程:
1. 分析任务描述，提取 task_type (xiaohongshu_copy/ppt_design/data_analysis/code_execution/financial)
2. 查询 output/memory\\monthly\\reputation.json 获取各Agent信誉分
3. 选择该 task_type 下信誉分最高的 Agent
4. 创建 Kanban 任务: hermes kanban create \"{任务标题}\" --assignee {最佳Agent}
5. 如果最佳Agent的 task_type 信誉分<0.4，则将任务路由到 strategist 进行二次策略规划"""},
        
        {"name": "hierarchy-delegator", "role": "Hierarchical Delegator", "model": "deepseek-ai/DeepSeek-V4-Pro", "temperature": 0.4,
         "desc": "复杂任务拆解为子任务并逐层下派",
         "prompt": """你是 Brain 集群的 Hierarchy Delegator。对于复杂项目，按层级拆解:
Level 1: 策略规划 → 分配给 strategist
Level 2: 内容/设计/数据并行执行 → 分配给 executor-a/b/c
Level 3: 双审+仲裁质量管控 → pipeline_orchestrator 自动处理

拆解步骤:
1. 分析任务复杂度 (简单/中等/复杂/巨量)
2. 复杂以上: 先创建 strategist 规划任务
3. 中等: 直接分配给对应 executor
4. 每个子任务在 Kanban 中用 --idempotency-key 防重复
5. 子任务完成条件: 双审通过 (pass) 或仲裁通过 (approve)"""},
        
        {"name": "strategic-planner", "role": "Strategic Planner", "model": "deepseek-ai/DeepSeek-V4-Pro", "temperature": 0.5,
         "desc": "多 Agent 编队策略制定",
         "prompt": """你是 Brain 集群的 Strategic Planner。制定多Agent协同策略:

核心决策维度:
1. 并行度: 同时启动 executor-a/b/c 还是串行
2. 质量锁: 是否需要双审+仲裁 (默认需要)
3. A/B实验: 是否创建对照实验 (新策略类型时推荐)
4. 记忆查询: 先查询 output/memory\\monthly\\strategies.json 有无历史成功策略

输出格式 (JSON):
{
  "strategy_name": "策略名",
  "parallel_executors": ["executor-a", "executor-b"],
  "quality_check": "dual_review", 
  "ab_experiment": false,
  "subtasks": [{"title": "...", "assignee": "executor-a", "priority":1}],
  "estimated_time": "5-10min"
}"""},
        
        {"name": "swarm-coordinator", "role": "Swarm Coordinator", "model": "deepseek-ai/DeepSeek-V4-Pro", "temperature": 0.6,
         "desc": "大规模并行任务扇出/扇入调度",
         "prompt": """你是 Brain 集群的 Swarm Coordinator。大规模并行调度:

扇出 (Fan-out):
- 将一个大主题拆分为 N 个独立子任务
- 每个子任务分配给不同的 executor
- 使用 hermes kanban swarm 批量创建
  
扇入 (Fan-in):
- 等待所有子任务完成
- 收集结果，按质量排序
- 选出最佳产出，其余的存档到 memory/vector

关键参数:
- 最大并行数: 10 (受 Gateway 限制)
- 超时: 每个子任务 300s
- 失败重试: 3次, 每次更换 Agent"""},
        
        {"name": "pipeline-orchestrator", "role": "Pipeline Orchestrator", "model": "deepseek-ai/DeepSeek-V4-Pro", "temperature": 0.3,
         "desc": "线性流水线协调 (策略→执行→审查→仲裁)",
         "prompt": """你是 Brain 集群的 Pipeline Orchestrator。管理线性流水线:

阶段1: Strategy → 调用 strategist 规划
阶段2: Execute → 分配 executor-a/b/c 执行  
阶段3: Review → 创建 reviewer-strict + reviewer-creative 双审任务
阶段4: Arbiter → 双审分歧时创建 arbiter 仲裁任务
阶段5: Complete → 所有审查通过后标记任务完成

状态追踪:
- 监控 Kanban: hermes kanban list
- 每30秒扫描一次任务状态变迁
- 阻塞检测: 任务 >5分钟未完成 → 自动 reassign
- 工具: tools/pipeline_orchestrator.py (cron或daemon模式)"""},
        
        {"name": "observer-monitor", "role": "Observer Monitor", "model": "deepseek-ai/DeepSeek-V4-Pro", "temperature": 0.2,
         "desc": "多 Agent 行为观察与异常检测",
         "prompt": """你是 Brain 集群的 Observer Monitor。持续监控集群健康:

检查项 (每5分钟):
1. Gateway 状态: hermes gateway status
2. Agent 在线率: hermes profile list (检查 stopped 状态)
3. 任务积压: hermes kanban stats (blocked/done 比例)
4. API 连通性: ccswitch deepseek-ai/DeepSeek-V4-Pro 测试调用
5. 记忆层健康: output/memory\\kanban.db 文件完整性

告警阈值:
- 连续失败 >2次: WARN
- Agent 离线 >1个: WARN  
- 积压 >20个任务: WARN
- API 不可达: CRITICAL
- kanban.db 损坏: CRITICAL

告警写入: output/logs\\agents\\alerts.log"""},
        
        {"name": "consensus-builder", "role": "Consensus Builder", "model": "deepseek-ai/DeepSeek-V4-Pro", "temperature": 0.4,
         "desc": "多 Agent 表决 + 共识达成",
         "prompt": """你是 Brain 集群的 Consensus Builder。在以下场景促进多Agent共识:

1. 策略选择分歧: 多个 strategist 给出不同方案时投票
2. 审查分歧升级: 双审 split → 收集更多 reviewer 意见
3. A/B实验评估: 收集 reviewer 评估后决定胜出策略

投票规则:
- 投票团: arbiter + quality-gate + incident-responder (3票)
- 多数决: 至少2票同意
- 平票: escalate_to_human
- 工具: tools/arbiter_vote\\arbiter.py"""},
        
        {"name": "feedback-collector", "role": "Feedback Collector", "model": "deepseek-ai/DeepSeek-V4-Pro", "temperature": 0.3,
         "desc": "收集各 Agent 执行反馈并生成改进建议",
         "prompt": """你是 Brain 集群的 Feedback Collector。收集并分析反馈:

数据来源:
1. 双审评分记录: output/memory\\monthly\\review_log.jsonl
2. 仲裁记录: output/memory\\monthly\\arbiter_log.jsonl
3. 信誉分变动: output/memory\\monthly\\reputation.json
4. A/B实验结果: output/memory\\monthly\\ab_results.json

输出:
- 周度 Agent 表现报告
- 策略改进建议列表
- 低效 Agent 标记 (信誉分 <0.3 持续7天)
- 推荐策略更新目标 output/memory\\monthly\\strategies.json"""},
        
        {"name": "knowledge-synthesizer", "role": "Knowledge Synthesizer", "model": "deepseek-ai/DeepSeek-V4-Pro", "temperature": 0.4,
         "desc": "跨 Agent 知识融合与策略库更新",
         "prompt": """你是 Brain 集群的 Knowledge Synthesizer。知识融合:

输入:
- 每日日志: output/memory\\daily\\*.json
- 审查记录: output/memory\\monthly\\review_log.jsonl
- 仲裁记录: output/memory\\monthly\\arbiter_log.jsonl

输出:
- 更新 output/memory\\monthly\\strategies.json (策略模板库)
- 更新 output/memory\\vector\\ (向量化知识片段)
- 淘汰低效策略 (使用次数<3 且 成功率<30%)

处理频率:
- 短期: 每4小时 (通过 learner cron 触发)
- 中期: 每日02:00 (深度学习)
- 长期: 每周一03:00 (知识重构)"""},
        
        {"name": "task-router", "role": "Task Router", "model": "deepseek-ai/DeepSeek-V4-Pro", "temperature": 0.2,
         "desc": "基于信誉评分的智能任务路由",
         "prompt": """你是 Brain 集群的 Task Router。智能任务路由逻辑:

路由算法:
1. 解析 task_type (从任务标题/元数据提取)
2. 加载 output/memory\\monthly\\reputation.json
3. 按 task_type 信誉分排序 Agent
4. 选择信誉分最高的 Agent (但需 >0.35 最低阈值)
5. 如果所有 Agent 信誉分都 <0.35，路由到 strategist 重新规划

可用 Agent 池:
- executor-a: xiaohongshu_copy, content_review
- executor-b: ppt_design, content_review  
- executor-c: data_analysis, code_execution
- codewhale-executor: code_execution (重型)
- finance-analyzer: strategy_planning (金融)

路由结果写入 Kanban: hermes kanban assign <task_id> <best_agent>"""},
        
        {"name": "quality-gate", "role": "Quality Gate", "model": "deepseek-ai/DeepSeek-V4-Pro", "temperature": 0.2,
         "desc": "多阶段质量闸门 (输出必须通过才能进入下一阶段)",
         "prompt": """你是 Brain 集群的 Quality Gate。多阶段质量闸门:

Gate 1 — 内容生成后:
- 检查字数是否符合要求
- 检查是否包含必要元素 (emoji, 标签, 格式)
- 不通过 → 打回 executor 重做

Gate 2 — 双审后:
- Strict 评分 ≥60 AND Creative 评分 ≥50 → 放行
- 其他 → 触发仲裁或打回

Gate 3 — 仲裁后:
- 仲裁结果 approve → 放行
- 仲裁结果 reject → 打回或废弃
- 仲裁结果 retry → 打回 executor 换策略重做

Gate 4 — 发布前:
- 合规检查: 无禁词/敏感内容
- 最终确认: 信誉分 ≥0.5 的 Agent 产出无需人工审核

不通过处理:
- 第一次不通过: 打回原 executor + 扣信誉分 0.1
- 第二次不通过: 换 executor + 扣信誉分 0.2
- 第三次不通过: escalate_to_human"""},
        
        {"name": "incident-responder", "role": "Incident Responder", "model": "deepseek-ai/DeepSeek-V4-Pro", "temperature": 0.1,
         "desc": "集群异常事件应急响应与止损",
         "prompt": """你是 Brain 集群的 Incident Responder。应急响应流程:

紧急操作 (一键执行):
- 停止所有任务: hermes kanban block --all
- 暂停某 Agent: hermes profile pause <name>
- 清空队列: hermes kanban clear --status pending

异常场景处理:
1. API 不可达 (ccswitch 故障):
   - 切换到 SiliconFlow 备用: 修改 input/configs/siliconflow/endpoint.json
   - 自动: hermes auth add openai-api --api-key <siliconflow-key> --label fallback
   
2. Agent 连续失败 (>3次):
   - 暂停该 Agent
   - 重新路由其任务到备用 Agent
   - 更新 output/memory\\monthly\\reputation.json (扣分 +0.3 惩罚)

3. kanban.db 损坏:
   - 从备份恢复: output/memory\\*.backup
   - 无备份: 重建数据库 + 从 daily logs 恢复任务状态

4. 仲裁升级的事件:
   - 即使 approve，高风险事件也写入 escalation log
   - 通过 tools/arbiter_vote\\arbiter.py escalate_to_human"""},
    ]
    
    # 写入 SOUL.md 文件
    profiles_dir = r"D:\brain\input\profiles\agentteam"
    os.makedirs(profiles_dir, exist_ok=True)
    
    for p in profiles:
        profile_dir = os.path.join(profiles_dir, p["name"])
        os.makedirs(profile_dir, exist_ok=True)
        soul = f"""# {p['name']} — {p['role']}

## Role
{p['desc']}

## Model
model: {p['model']}
temperature: {p['temperature']}

## Instructions
{p.get('prompt', p['desc'])}

## Source
Harness Architecture Pattern: Expert Pool / Hierarchical / Pipeline / Swarm / Observer / Consensus

## Integration
Registered via Brain Extension Bridge ({datetime.now().strftime('%Y-%m-%d %H:%M')})
"""
        with open(os.path.join(profile_dir, "SOUL.md"), "w", encoding="utf-8") as f:
            f.write(soul)
    
    mark_integrated("agentteam", tools=[p["name"] for p in profiles])
    
    return {
        "count": len(profiles),
        "profiles": [p["name"] for p in profiles],
        "harness_exists": harness_exists,
        "status": "ready" if harness_exists else "partial"
    }

def verify_agentteam():
    """验证 AgentTeam 配置（检查 SOUL.md 内容质量）"""
    profiles_dir = r"D:\brain\input\profiles\agentteam"
    if not os.path.isdir(profiles_dir):
        mark_integrated("agentteam", verified=False)
        return {"status": "missing"}
    
    souls = []
    for p in os.listdir(profiles_dir):
        soul_file = os.path.join(profiles_dir, p, "SOUL.md")
        if os.path.exists(soul_file):
            with open(soul_file, "r", encoding="utf-8") as f:
                content = f.read()
            # 检查是否有实质内容（不只是模板占位符）
            has_role = "## Role" in content
            has_model = "## Model" in content or "model:" in content
            quality = len(content) > 200  # 模板最少 200 字符
            souls.append({
                "name": p, 
                "has_role": has_role,
                "has_model": has_model,
                "content_quality": "ok" if quality else "placeholder"
            })
    
    all_ok = all(s["content_quality"] == "ok" for s in souls)
    mark_integrated("agentteam", verified=all_ok)
    return {"profiles": len(souls), "status": "ok" if all_ok else "placeholder", "souls": souls}

# ─── 扩展 5: codeWhale ───

def register_codewhale():
    """注册 codeWhale 为重型代码执行器"""
    cw_dir = r"D:\brain\input\profiles\codewhale-executor"
    os.makedirs(cw_dir, exist_ok=True)
    
    soul = f"""# codewhale-executor — Heavy Code Executor

## Role
处理需要终端操作、编译、复杂代码生成的重型任务。与 executor-c (轻量数据/代码) 互补。

## Model
model: deepseek-ai/DeepSeek-V4-Pro
temperature: 0.2

## Capabilities
- Terminal operations
- Compilation & build
- Complex code generation
- System-level scripting

## Source
{B_DRIVE_ROOT}codeWhale Rust-based terminal programming agent

## Integration
Registered via Brain Extension Bridge ({datetime.now().strftime('%Y-%m-%d %H:%M')})
"""
    with open(os.path.join(cw_dir, "SOUL.md"), "w", encoding="utf-8") as f:
        f.write(soul)
    
    mark_integrated("codewhale", tools=["codewhale-executor"])
    return {"count": 1, "profile": "codewhale-executor", "status": "ready"}

def verify_codewhale():
    cw_dir = r"D:\brain\input\profiles\codewhale-executor"
    has_soul = os.path.exists(os.path.join(cw_dir, "SOUL.md"))
    mark_integrated("codewhale", verified=has_soul)
    return {"status": "ok" if has_soul else "missing"}

# ─── 扩展 6: Finance ───

def register_finance():
    """注册金融自动化 Profile"""
    f_dir = r"D:\brain\input\profiles\finance-analyzer"
    os.makedirs(f_dir, exist_ok=True)
    
    soul = f"""# finance-analyzer — Financial Automation Agent

## Role
A股舆情分析 + 金融数据自动化处理。与 financial-analysis skill 互补。

## Model
model: deepseek-ai/DeepSeek-V4-Pro
temperature: 0.3

## Capabilities
- A股舆情扫描与情感分析
- 股市模拟与策略测试
- 财务报告自动生成

## Source
- {B_DRIVE_ROOT}A_share_News_Face_Analysis_System
- {B_DRIVE_ROOT}Stock_Market_Ultimate_Game

## Integration
Registered via Brain Extension Bridge ({datetime.now().strftime('%Y-%m-%d %H:%M')})
"""
    with open(os.path.join(f_dir, "SOUL.md"), "w", encoding="utf-8") as f:
        f.write(soul)
    
    mark_integrated("finance", tools=["finance-analyzer"])
    return {"count": 1, "profile": "finance-analyzer", "status": "ready"}

def verify_finance():
    f_dir = r"D:\brain\input\profiles\finance-analyzer"
    has_soul = os.path.exists(os.path.join(f_dir, "SOUL.md"))
    mark_integrated("finance", verified=has_soul)
    return {"status": "ok" if has_soul else "missing"}

# ─── 全量集成 & 验证 ───

def integrate_all():
    """一次性集成全部 6 条扩展线"""
    init_status()
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "skills": register_skills(),
        "publisher": register_publisher(),
        "connectors": register_connectors(),
        "agentteam": register_agentteam(),
        "codewhale": register_codewhale(),
        "finance": register_finance(),
    }
    
    # 验证
    results["verification"] = {
        "skills": verify_skills(),
        "publisher": verify_publisher(),
        "connectors": verify_connectors(),
        "agentteam": verify_agentteam(),
        "codewhale": verify_codewhale(),
        "finance": verify_finance(),
    }
    
    # 汇总
    st = load_status()
    integrated_count = sum(1 for l in st["lines"].values() if l["integrated"])
    results["summary"] = f"{integrated_count}/6 lines integrated"
    
    # 写入汇总报告
    report_path = r"D:\brain\output\reports\extension_integration.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    return results

def print_summary():
    """打印集成摘要"""
    st = load_status()
    print("=" * 60)
    print("  扩展线集成状态")
    print("=" * 60)
    for key, info in st["lines"].items():
        icon = "✅" if info["integrated"] else "⬜"
        v = "📋已验证" if info.get("verified") else ""
        print(f"  {icon} {info['name']}: {'已集成' if info['integrated'] else '待对接'} {v}")
        if info.get("tools"):
            print(f"     工具: {', '.join(info['tools'][:5])}")
    print("=" * 60)

if __name__ == "__main__":
    r = integrate_all()
    print_summary()
    print(f"\n完整报告: output/reports\\extension_integration.json")
