# Brain 集群 — 熟练使用手册

> 版本: 1.0 | 日期: 2026-06-05
> 涵盖: 日常指令、Agent提示词、紧急处理、升级方案

---

## 一、快速参考卡

### 启动集群
```bash
# 方式1: 一键启动
D:\brain\start_all.bat

# 方式2: 分步启动
hermes gateway run          # Gateway (调度器+Kanban)
hermes dashboard            # Kanban看板 (浏览器)
python D:\brain\staroffice-ui\backend\app.py  # 像素监控 (:18791)
```

### 日常操作
```bash
# 查看所有Agent状态
hermes profile list

# 查看Kanban看板（浏览器打开）
hermes dashboard

# 查看定时任务
hermes cron list --profile learner
hermes cron list --profile monitor

# 查看任务统计
hermes kanban stats

# 查看任务列表
hermes kanban list
```

---

## 二、任务管理指令

### 创建任务
```bash
# 基础创建
hermes kanban create "任务标题" --assignee <profile>

# 带幂等键（防止重复）
hermes kanban create "每日小红书文案生成" --assignee strategist --idempotency-key "daily-xhs-$(date +%Y%m%d)"

# 批量创建（swarm模式）
hermes kanban swarm "调研2026夏季防晒市场趋势" --workers executor-a,executor-b,executor-c --verifier reviewer-strict
```

### 任务操作
```bash
hermes kanban show <task_id>          # 查看任务详情
hermes kanban assign <task_id> <profile>  # 重新分配
hermes kanban comment <task_id> "评论"     # 添加评论
hermes kanban complete <task_id>      # 手动完成任务
hermes kanban block <task_id>         # 阻塞任务
hermes kanban unblock <task_id>       # 解除阻塞
hermes kanban tail <task_id>          # 实时追踪任务事件
```

### Agent 管理
```bash
hermes profile list                   # 列出所有Agent
hermes profile describe strategist    # 查看Agent描述
hermes chat --profile strategist "帮我分析当前任务队列"  # 直接对话Agent
```

---

## 三、各Agent Prompt 模板

### 策略龙 (strategist)
```
你是Brain集群的首席策略官。你有以下执行龙可用:
- executor-a: 内容创作(小红书/抖音文案)
- executor-b: PPT和可视化设计
- executor-c: 数据分析和代码执行

当前任务: {任务描述}

请拆解为可执行的子任务，每个子任务一张Kanban卡片。
查看 D:\brain\memory\weekly\ 中的历史策略，选择最优方案。
如有A/B实验结果，优先选择胜出策略。
```

### 执行龙 (executor-a/b/c)
```
你是执行龙-{类型}。当前任务: {任务描述}
使用策略: {从策略库选择的策略}

执行步骤:
1. 查 D:\brain\memory\vector\ 中的历史经验
2. 参考信誉评分选择最佳实践
3. 产出内容
4. 完成后调用 kanban_complete，附带元数据:
{
  "strategy_used": "{策略名}",
  "content_type": "{任务类型}",
  "estimated_quality": "0-100",
  "ab_group": "{A/B组别，如适用}"
}
```

### 审查龙 (reviewer-strict/creative)
```
请审查以下产出:
---
{执行龙产出的内容}
---

评分标准 (strict模式):
- 事实准确性: 0-100
- 格式规范: 0-100
- 合规性: 0-100

评分标准 (creative模式):
- 吸引力: 0-100
- 创新性: 0-100
- 情感共鸣: 0-100

输出JSON:
{"total": 85, "verdict": "pass|fail", "feedback": "具体建议"}
```

### 仲裁龙 (arbiter)
```
双审结果分歧:
- 严格审查: {score_strict}分 - {verdict_strict}
- 创意审查: {score_creative}分 - {verdict_creative}

请裁决: approve / reject / escalate_to_human
理由: 
风险等级: low / medium / high
```

### 学习龙 (learner)
```
请蒸馏以下时间段的任务日志:
时间: {开始} 到 {结束}
事件数: {count}

任务:
1. 提取成功模式
2. 标记失败原因
3. 更新信誉评分 (基于成功率)
4. 更新策略库 D:\brain\memory\monthly\strategies.json
5. 如有A/B实验完成，宣布胜出策略
```

---

## 四、定时任务配置

| Job | 调度 | Profile | 功能 |
|-----|------|---------|------|
| dreaming-short-term | 每4小时 | learner | 蒸馏最近4h任务日志 |
| dreaming-medium-term | 每日02:00 | learner | 深度巩固，更新策略库 |
| dreaming-long-term | 每周一03:00 | learner | 知识库重构，淘汰低效 |
| monitor-health-check | 每5分钟 | monitor | 扫描异常，推送告警 |

```bash
# 查看定时任务
hermes cron list --profile learner
hermes cron list --profile monitor

# 手动触发
hermes cron run <job_id> --profile learner
```

---

## 五、记忆系统操作

```bash
# 手动同步记忆桥接
python D:\brain\tools\memory_bridge.py

# 查看每日日志
ls D:\brain\memory\daily\

# 查看策略库
cat D:\brain\memory\monthly\strategies.json

# 查看信誉评分
cat D:\brain\memory\monthly\reputation.json

# 运行全链路测试
python D:\brain\tools\e2e_test.py
```

---

## 六、紧急处理流程

### 集群宕机
```bash
hermes gateway status        # 检查Gateway
hermes gateway restart       # 重启Gateway
hermes kanban stats          # 检查任务状态
```

### 任务积压
```bash
hermes kanban stats          # 看积压量
hermes kanban list --status blocked  # 找阻塞任务
hermes kanban unblock <id>   # 逐一解阻塞
```

### Agent 异常
```bash
hermes profile list          # 检查Agent状态
hermes kanban reassign <task_id> <new_agent>  # 重新分配
```

### GPT-5.5 不通
```bash
python -c "import openai; c=openai.OpenAI(base_url='https://tokenshengsheng.com/v1', api_key='...'); print(c.chat.completions.create(model='gpt-5.5', messages=[{'role':'user','content':'test'}], max_tokens=5))"
```

---

## 七、D:\eyes 升级方案（未来）

| 项目 | 可升级内容 | 优先级 |
|------|-----------|--------|
| Supermemory | 替代Letta，Hybrid RAG+自动记忆管理 | 高 |
| Harness | 6种Agent架构模式(Expert Pool/Hierarchical) | 高 |
| Orchestrate | Andon紧急停止+结构化handoff | 中 |
| Continual-Learning | 增量记忆自动挖掘更新 | 中 |
| CodeGraph | Agent代码库语义图(-58%工具调用) | 低 |

---

## 八、Grafana 安装（下载完成后）

```bash
cd D:\brain\grafana
Expand-Archive grafana.zip .
grafana-server --config D:\brain\configs\grafana\custom.ini
grafana-cli plugins install frser-sqlite-datasource
# 访问 http://localhost:3001
```

---

## 九、项目开发实战

### 核心开发流程

```
你的想法
    |
    v
创建 Kanban 任务 --> Agent 自动处理 --> 审查/审核 --> 产出交付
    |                      |                    |
    +-- 策略龙拆解         +-- 执行龙生成        +-- 学习龙记忆
```

> 把需求写成 Kanban 任务卡片，Agent 自动完成全流程。你只需要审核最终结果。

---

### 实战 1: 开发一篇小红书文案

**第1步 — 创建任务**
```bash
hermes kanban create "写一篇夏季防晒霜小红书种草文案，800字，含5个emoji，3个话题标签" --assignee executor-a
```

**第2步 — 等待 Agent 自动完成 (约30秒)**
```bash
hermes kanban list
# 输出: running -> done
```

**第3步 — 查看结果**
```bash
hermes kanban show <task_id>
```

**第4步 — 不满意就打回**
```bash
hermes kanban comment <task_id> "标题不够吸引人，加爆款断货王这类词，重新生成"
hermes kanban reassign <task_id> executor-a
```

---

### 实战 2: 开发一个 PPT

```bash
# 简单模式 (一句话)
hermes kanban create "生成2026夏季防晒市场分析PPT，含封面、市场数据3页、竞品分析2页、总结1页" --assignee executor-b

# 专业模式 (策略龙先做规划)
hermes kanban create "策划年度投资汇报PPT，封面+目录+6章节" --assignee strategist
```

---

### 实战 3: 复杂项目 (策略龙规划 + 多执行龙并行)

```bash
hermes kanban create "制定2026夏季美妆小红书营销方案：市场调研 + 5篇文案 + 封面图 + 数据分析" --assignee strategist
```

策略龙会自动:
- 查信誉分选最优执行龙
- 查历史策略选最优方案  
- 拆成子任务, 执行龙x3并行工作
- 每个产出自动双审

---

### 项目类型 --> Agent 对照表

| 你想做什么 | 指派给 | 示例命令 |
|-----------|--------|---------|
| 小红书/抖音文案 | executor-a | hermes kanban create "..." --assignee executor-a |
| PPT/图表/可视化 | executor-b | hermes kanban create "..." --assignee executor-b |
| 数据分析/代码 | executor-c | hermes kanban create "..." --assignee executor-c |
| 复杂项目先规划 | strategist | hermes kanban create "..." --assignee strategist |

---

### 查看进度

```bash
hermes dashboard                    # 看板 (浏览器)
hermes kanban list                  # 所有任务
hermes kanban stats                 # 统计
hermes kanban show <task_id>        # 任务详情
```

### 系统自动做的事

```
每5分钟: monitor 扫描异常
每4小时: learner 蒸馏日志, 更新信誉分
每日2AM: learner 深度巩固, 更新策略库
每周一3AM: learner 知识重构, 淘汰低效策略
```

### 每天检查清单

```bash
hermes gateway status              # Gateway 运行中?
hermes kanban stats                # 有积压吗?
hermes profile list                # Agent 都在线吗?
python D:\brain\tools\e2e_full_test.py  # 全链路测试
```
