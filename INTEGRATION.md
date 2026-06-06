# 最强集成方案 — Brain 集群部署手册

> 路径B（极致组合）：Hermes + OpenClaw Dreaming + Letta

---

## 一、架构全景

```
观测层  →  Hermes Dashboard (看板) + Grafana (大屏) + StarOfficeUI (像素)
记忆层  →  Letta (运行时记忆分页) + OpenClaw Dreaming (定时记忆巩固)
进化层  →  审查龙(双审) + 仲裁龙(表决) + A/B实验 + 信誉评分
执行层  →  Hermes Kanban (7状态机) + 调度器 (60s) + 崩溃恢复
算力层  →  ccswitch → GPT-5.5 + Codex
```

## 二、安装步骤

### Step 1 — ccswitch 配通（5分钟）
编辑 `D:\brain\configs\ccswitch\endpoint.json`
将 `base_url` 和 `api_key` 替换为你的 ccswitch 地址和密钥

### Step 2 — Hermes Agent（已装，仅配置）
```bash
# 1. 将配置复制到 Hermes 目录
copy D:\brain\configs\hermes\gateway.json %USERPROFILE%\.hermes\gateway.json

# 2. 初始化 Kanban
hermes kanban init --db D:\brain\memory\kanban.db

# 3. 注册 Agent Profiles
hermes profile create strategist   --from D:\brain\agents\strategist\SOUL.md
hermes profile create executor-a   --from D:\brain\agents\executor-a\SOUL.md
hermes profile create executor-b   --from D:\brain\agents\executor-b\SOUL.md
hermes profile create executor-c   --from D:\brain\agents\executor-c\SOUL.md
hermes profile create monitor       --from D:\brain\agents\monitor\SOUL.md
hermes profile create reviewer-strict   --from D:\brain\agents\reviewer-strict\SOUL.md
hermes profile create reviewer-creative --from D:\brain\agents\reviewer-creative\SOUL.md
hermes profile create arbiter       --from D:\brain\agents\arbiter\SOUL.md
hermes profile create learner       --from D:\brain\agents\learner\SOUL.md

# 4. 启动 Dashboard
hermes dashboard
```

### Step 3 — OpenClaw Dreaming（已装，仅配置）
```bash
copy D:\brain\configs\openclaw\dreaming.json %USERPROFILE%\.openclaw\dreaming.json
openclaw dreaming start
```

### Step 4 — Letta（需新安装）
```bash
pip install letta
letta init --db D:\brain\letta\letta.db
# 配置 Letta 读取 Dreaming 的压缩产物
```

### Step 5 — Grafana（需新安装）
```bash
# 下载安装 Grafana → 配置数据源指向 D:\brain\memory\kanban.db
# 导入 D:\brain\configs\grafana\ 下的面板 JSON
```

### Step 6 — StarOfficeUI（需手动克隆）
```bash
cd D:\brain\staroffice-ui
git clone https://github.com/ZHAOYAN-lab/star-office-ui.git .
pip install -r backend/requirements.txt
python backend/app.py
# 访问 http://127.0.0.1:19000
```

### Step 7 — 自写工具初始化
```bash
cd D:\brain\tools
python ab-test/ab_runner.py        # 初始化 A/B 实验数据库
python reputation/scorer.py        # 初始化信誉评分表
```

### Step 8 — 启动集群
```bash
# 终端1: Hermes Gateway
hermes gateway start

# 终端2: OpenClaw Dreaming
openclaw dreaming start

# 终端3: Letta
letta serve

# 终端4: Grafana
grafana-server --config D:\brain\configs\grafana\datasource.yaml

# 终端5: StarOfficeUI (可选)
cd D:\brain\staroffice-ui && python backend/app.py

# 终端6: Hermes Dashboard
hermes dashboard
```

## 三、端口规划

| 端口 | 服务 |
|------|------|
| 18789 | OpenClaw Gateway (内部) |
| 19000 | StarOfficeUI |
| 3000  | Hermes Dashboard |
| 3001  | Grafana |
| TBD   | Letta API |

## 四、第一个任务测试

```bash
# 通过 Hermes CLI 创建一个测试任务
hermes kanban create "生成一篇夏季防晒小红书文案" \
    --assignee strategist \
    --idempotency-key "first-test-001"
```

预期流程：
1. 策略龙收到 triage 任务 → 拆解为子任务 → 分配到 executor-a
2. executor-a 查记忆库 → 用最优策略生成文案 → 提交审查
3. 审查龙-A + 审查龙-B 双审 → 通过 → 任务 done
4. 学习龙每小时蒸馏 → 更新信誉分和策略库

## 五、定时任务配置

```
*/5 * * * *  hermes kanban create "health_check" --assignee monitor
0   * * * *  hermes kanban create "hourly_learn" --assignee learner
0   2 * * *  hermes kanban create "daily_consolidate" --assignee learner
0   3 * * 0  hermes kanban create "weekly_review" --assignee strategist
```
