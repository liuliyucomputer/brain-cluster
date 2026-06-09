# D 盘 — AI 项目总览

> 2026-06-06 | Brain 集群 (运行中 v1.0.2) + Eyes 知识库 (储备)

---

## 一、项目地图

```
D:\
├── README.md          ← 你在这里
│
├── brain/             [100% 就绪] AI 多 Agent 集群系统
│   ├── DESIGN.md             项目设计文件 (长期维护 v1.0.2)
│   ├── DEPLOYMENT_REPORT.md  部署完成报告
│   ├── USER_MANUAL.md        使用手册 (指令+提示词)
│   ├── INTEGRATION.md        集成部署手册
│   ├── EXPANSION.md          扩展路线图 (6条线)
│   ├── start_all.bat         一键启动脚本
│   ├── agents/               Agent定义 (9个SOUL.md)
│   ├── configs/              配置文件 (Hermes/SiliconFlow/OpenClaw)
│   ├── tools/                工具脚本 (A/B/信誉/审查/仲裁/桥接/E2E)
│   ├── memory/               记忆层 (daily/weekly/monthly/vector)
│   ├── letta/                记忆分页引擎 (v0.16.8)
│   ├── hermes-agent/         执行底盘 (v0.15.1 源码)
│   ├── openclaw/             Dreaming引擎 (源码)
│   ├── staroffice-ui/        像素监控 (:18791)
│   ├── grafana/              运维大屏 (v11.6.0 :3001)
│   ├── dashboard/            指挥台 (待建)
│   └── extensions/           6条扩展线 (待接入)
│
└── eyes/              [知识储备] 可升级项目
    ├── harness/             ★团队架构工厂
    ├── supermemory/         ★记忆引擎 #1基准
    ├── plugins/orchestrate/ ★并行编排系统
    ├── codegraph/           ★代码语义图
    └── ... (12个项目)
```

---

## 二、Brain 集群 — 详细启动指令

### 前置环境

| 依赖 | 版本 | 备注 |
|------|------|------|
| Python | 3.13.4 | E:\Python3134\python.exe |
| Node.js | 22.22.2 | 已安装 |
| Hermes CLI | v0.15.1 | hermes 命令在PATH中 |
| Letta | v0.16.8 | pip installed |
| SiliconFlow | DeepSeek-V4-Pro | api.siliconflow.cn/v1 |

### 方式A: 一键启动

双击或运行:
```
D:\brain\start_all.bat
```

会依次启动: Gateway → StarOfficeUI → Dashboard (Grafana 需手动启动)

### 方式B: 分步启动 (推荐)

打开 4 个独立 cmd 窗口:

**窗口1 — Hermes Gateway (调度器)**
```cmd
set OPENAI_API_KEY=sk-your-key-here
set OPENAI_BASE_URL=https://api.siliconflow.cn/v1
hermes gateway run -v
```

**窗口2 — StarOfficeUI (像素监控 :18791)**
```cmd
cd /d D:\brain\staroffice-ui\backend
python app.py
```

**窗口3 — Grafana (运维大屏 :3001)**
```cmd
cd /d D:\brain\grafana\grafana-v11.6.0
bin\grafana-server.exe --config D:\brain\grafana\custom.ini
```

**窗口4 — Hermes Dashboard (Kanban看板)**
```cmd
hermes dashboard
```

### 启动后验证 (10项)

```bash
hermes gateway status                            # 1
curl http://127.0.0.1:18791/health               # 2
curl http://127.0.0.1:3001/api/health            # 3
hermes kanban stats                               # 4
hermes profile list                               # 5
hermes cron list --profile learner                # 6
hermes cron list --profile monitor                # 7
python D:\brain\tools\e2e_full_test.py         # 8
hermes kanban create "test" --assignee executor-a # 9
python D:\brain\tools\memory_bridge.py         # 10
```

### 停止集群

```cmd
hermes gateway stop
taskkill /f /im grafana-server.exe
taskkill /fi "WINDOWTITLE eq StarOfficeUI"
```

---

## 三、Brain 集群 — 详细架构

### 架构总览

```
                    +--------------------------+
                    |   观测流 (Observation)     |
                    | Dashboard + Grafana       |
                    | + StarOfficeUI            |
                    +------------+-------------+
                                 |
    +----------------------------+----------------------------+
    |     执行流 (Execution)     |                            |
    |                            v                            |
    |  +--------------------------------------------------+ |
    |  |           Hermes Gateway (:18789)                 | |
    |  |  +-----------+  +--------+  +---------------+    | |
    |  |  | Dispatcher|  |  Cron  |  |Circuit Breaker|    | |
    |  |  | (60s扫描) |  |Scheduler|  |  (崩溃恢复)   |    | |
    |  |  +-----+-----+  +---+----+  +-------+-------+    | |
    |  |        v             v               v             | |
    |  |  +--------------------------------------------+   | |
    |  |  |          Kanban SQLite (kanban.db)          |   | |
    |  |  |  triage -> todo -> scheduled -> ready       |   | |
    |  |  |       -> running -> blocked -> done         |   | |
    |  |  +--------------------------------------------+   | |
    |  +--------------------------------------------------+ |
    |                            |                            |
    |        +-------------------+-------------------+        |
    |        v                   v                   v        |
    |  +-----------+     +-----------+     +-----------+     |
    |  | strategist |     |executor-a |     |  learner  |     |
    |  | (拆解路由) |     | (文案创作) |     | (蒸馏学习) |     |
    |  +-----+-----+     +-----+-----+     +-----+-----+     |
    |        |                 |                 |             |
    |   +----+----+       +----+----+       +----+----+       |
    |   |信誉查询  |       |executor |       |记忆桥接  |       |
    |   |A/B策略   |       |   -b    |       |策略更新  |       |
    |   +---------+       |executor |       |Letta同步 |       |
    |                      |   -c    |       +---------+       |
    |                      +---------+                         |
    |                           |                              |
    |                  +--------+--------+                     |
    |                  v                 v                     |
    |         +------------+   +------------+                 |
    |         |  reviewer  |   |  reviewer  |                 |
    |         |  -strict   |   | -creative  |                 |
    |         |(事实/格式) |   |(创意/共鸣) |                 |
    |         +-----+------+   +-----+------+                 |
    |               +-------+--------+                         |
    |                       v                                  |
    |               +------------+                             |
    |               |  arbiter   |  (分歧时)                   |
    |               | (最终裁决) |                             |
    |               +------------+                             |
    +----------------------------------------------------------+
                                 |
    +----------------------------+----------------------------+
    |     记忆流 (Memory)        |                            |
    |                            v                            |
    |  +--------------------------------------------------+  |
    |  |            Letta (v0.16.8)                        |  |
    |  |        运行时记忆分页 (OS级管理)                   |  |
    |  +------------------+-------------------------------+  |
    |                     |                                   |
    |     +---------------+----------------+                  |
    |     v               v                v                  |
    |  +-------+     +--------+     +----------+             |
    |  | daily |     | weekly |     | monthly  |             |
    |  |原始日志|     |蒸馏产物|     | 策略库   |             |
    |  |(1h粒度)|     |(4h粒度)|     |(日粒度)  |             |
    |  +-------+     +--------+     +----------+             |
    |                                          |              |
    |                                          v              |
    |                                   +----------+         |
    |                                   |  vector  |         |
    |                                   | 长期智慧 |         |
    |                                   | (周粒度) |         |
    |                                   +----------+         |
    +--------------------------------------------------------+
                                 |
    +----------------------------+----------------------------+
    |     基础层                 |                            |
    |                            v                            |
    |  +--------------------------------------------------+  |
    |  |        SiliconFlow (api.siliconflow.cn/v1)       |  |
    |  |           DeepSeek-V4-Pro (openai-api provider)    |  |
    |  +--------------------------------------------------+  |
    +--------------------------------------------------------+
```

### 三层流

**执行流**: 策略龙(拆解+信誉路由) → Kanban调度 → 执行龙x3(并行产出) → 审查龙(双审) → 仲裁龙(表决) → done

**记忆流**: task_events(kanban.db) → Letta(运行时记忆分页) → Dreaming(定时压缩: 4h/24h/7d) → 长期智慧(daily→weekly→monthly→vector)

**观测流**: Hermes Dashboard(看板) + Grafana(指标大屏) + StarOfficeUI(像素监控)

### 数据流完整生命周期

```
用户创建任务 → [Kanban] ready → [Dispatcher] running → [Agent] 生成
  → [双审] pass/fail/split → [仲裁] 最终判定 → done
  → [每4h] learner蒸馏 → daily日志 → weekly总结 → monthly策略
  → [每日] 深度巩固 → [每周] 知识重构
```

### 组件关系矩阵

| 组件 | 端口 | 类型 | 故障影响 |
|------|------|------|---------|
| Gateway | 18789 | 调度器 | Agent无法派发 |
| Kanban DB | - | SQLite | 任务状态丢失 |
| StarOfficeUI | 18791 | Flask | 像素面板不可用 |
| Grafana | 3001 | Go | 大屏不可用 |
| SiliconFlow | 443 | API | DeepSeek-V4-Pro 不可用 |
| Letta | - | Python lib | 记忆分页降级 |
| Profiles | - | spawned | 该Agent不可用 |
| Cron | - | Gateway | 学习/监控停止 |

### 9个 Agent Profile

| Agent | 职责 | 模型 | 触发 |
|-------|------|------|------|
| strategist | 拆解+信誉路由+策略选择 | DeepSeek-V4-Pro | 收到任务 |
| executor-a | 文案(小红书/抖音) | DeepSeek-V4-Pro | 策略龙分配 |
| executor-b | PPT/可视化 | DeepSeek-V4-Pro | 策略龙分配 |
| executor-c | 数据/代码/API | DeepSeek-V4-Pro | 策略龙分配 |
| monitor | 集群健康巡检 | DeepSeek-V4-Pro | Cron */5 |
| reviewer-strict | 事实/格式/合规审查 | DeepSeek-V4-Pro | 执行完成 |
| reviewer-creative | 创意/吸引力审查 | DeepSeek-V4-Pro | 执行完成 |
| arbiter | 分歧裁决 | DeepSeek-V4-Pro | 审查分歧 |
| learner | 日志蒸馏/策略更新 | DeepSeek-V4-Pro | Cron */4h |

### 4个 Cron 定时任务

| Job | 调度 | Profile | 功能 |
|-----|------|---------|------|
| dreaming-short-term | 每4小时 | learner | 蒸馏日志 + 信誉更新 |
| dreaming-medium-term | 每日02:00 | learner | 深度巩固 + 策略库更新 |
| dreaming-long-term | 每周一03:00 | learner | 知识重构 + 低效淘汰 |
| monitor-health-check | 每5分钟 | monitor | 异常扫描 + 告警 |

---

## 四、Eyes 知识库 — 可升级到 Brain

### 升级路径 (按优先级)

| Eyes项目 | 可升级到 Brain | 预计增益 | 优先级 |
|----------|---------------|---------|--------|
| harness/ | 6种Agent架构 + 7Phase工作流 | Expert Pool / Hierarchical | 高 |
| supermemory/ | Hybrid RAG+Memory #1基准 | 替代 Letta | 高 |
| orchestrate/ | 递归分解 + Andon停止 | 执行流可靠性 | 中 |
| continual-learning/ | 增量记忆自动挖掘 | 记忆全自动化 | 中 |
| codegraph/ | 代码语义图 | -58%工具调用 | 低 |

### 已对齐的模式 (Brain中已实现)
- Producer-Reviewer → 审查龙双审
- Supervisor → 策略龙路由
- Fan-out/Fan-in → 执行龙x3并行
- Pipeline → 策略→执行→审查→完成

### Eyes 项目清单

| 项目 | 内容 |
|------|------|
| harness/ | 6种Agent架构模式 + 7Phase工作流 + 5个实际案例 |
| supermemory/ | 记忆引擎 #1基准 (Hybrid RAG+自动管理) |
| plugins/orchestrate/ | 并行编排 (递归分解+Andon紧急停止) |
| codegraph/ | 代码语义图 (SQLite FTS5 + Tree-sitter) |
| plugins/continual-learning/ | 对话转录自动挖掘 → AGENTS.md更新 |
| plugins/cursor-team-kit/ | 14个团队开发skill |
| Understand-Anything/ | 7个Agent代码分析管线 |
| Anthropic-Cybersecurity-Skills/ | 754个网络安全skill |
| open-notebook/ | 多模型笔记本 (18+AI提供商) |
| LongLive/ | NVIDIA长视频生成管线 |
| VoxCPM/ | Tokenizer-Free TTS (2B参数 30语言) |
| andrej-karpathy-skills/ | Agent行为4原则 |

---

## 五、访问地址

| 面板 | 地址 | 说明 |
|------|------|------|
| Kanban看板 | `hermes dashboard` | 浏览器自动打开 |
| 运维大屏 | http://localhost:3001 | admin/admin |
| 像素监控 | http://localhost:18791/health | API接口 |

## 六、常用命令速查

```bash
# 启动
hermes gateway run
python D:\brain\staroffice-ui\backend\app.py
D:\brain\grafana\grafana-v11.6.0\bin\grafana-server.exe --config D:\brain\grafana\custom.ini

# 任务
hermes kanban create "标题" --assignee <profile>
hermes kanban list / show <id> / complete <id>

# Agent
hermes profile list

# 监控
hermes kanban stats
curl http://127.0.0.1:18791/health
curl http://127.0.0.1:3001/api/health

# 记忆
python D:\brain\tools\memory_bridge.py
python D:\brain\tools\e2e_full_test.py

# 学习
hermes cron list --profile learner
hermes cron list --profile monitor
```
