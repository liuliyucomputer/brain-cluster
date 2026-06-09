# Brain 集群 — 对接完成清单

> 最后更新：2026-06-08 03:00 | v2.0.3 审计修复

---

## v2.0.3 全面审计修复 ✅ (2026-06-08)

| 修复项 | 数量 | 详情 |
|--------|------|------|
| Profile配置统一 | 16/24 | provider:custom→openai-api, 移除硬编码api_key |
| 路径硬编码修复 | 5处 | stats_api/e2e_test/e2e_integration/memory_engine/gateway.json |
| 安全泄漏修复 | 1处 | gateway.json api_key→环境变量 |
| 数据持久化 | 2处 | memory_bridge追加模式 + orchestrator自动sync |
| kanban路径统一 | 1处 | gateway.json db_path→绝对路径 |

---

## v2.0.0 长期自主任务系统 ✅

| 组件 | 文件 | 状态 |
|------|------|------|
| 自愈引擎 | `tools/watchdog.py` | 30s扫描, crash自动重启+重派 |
| 3轮重试 | `tools/pipeline_orchestrator.py` | FAIL换策略/换Agent/重分析 |
| 断点恢复 | `tools/checkpoint.py` | 5min快照, 保留20个, --restore |
| 依赖图 | `tools/task_graph.py` | 自动拆解, parent->child阻塞 |
| 进度API | `tools/monitor_dashboard.py` | /api/task_progress + /api/task_cost |
| 启动脚本 | `start_all.bat` + `start_all.ps1` | 7→9组件 |
| 文档 | `DESIGN.md` + `USER_MANUAL.md` | v2.0设计+使用手册 |

---

## SiliconFlow 对接 ✅

| 配置项 | 值 |
|--------|-----|
| API 端点 | `https://api.siliconflow.cn/v1` |
| 主模型 | `deepseek-ai/DeepSeek-V4-Pro` |
| 回退模型 | `deepseek-ai/DeepSeek-V4-Flash` |
| API 协议 | `chat_completions` |

---

## 8 个项目连接关系

```
                     你
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
  StarOfficeUI    Hermes Dashboard  Grafana
  :19000           :3000             :3001
  像素监控          看板操作          运维大屏
        │             │               │
        └──────┬──────┘               │
               ▼                      │
        OpenClaw Dreaming ←───────────┘
        三阶段记忆巩固        (读 kanban.db)
               │
               ▼
           Letta
        运行时记忆分页
               │
               ▼
        Hermes Gateway (:18789)
        ┌──────┬──────┬──────┬──────┐
        ▼      ▼      ▼      ▼      ▼
      策略龙  执行龙  监控龙  审查龙  学习龙+仲裁龙
        │      │      │      │      │
        └──────┴──────┴──────┴──────┘
               │
               ▼
         SiliconFlow
      api.siliconflow.cn/v1
               │
               ▼
     DeepSeek-V4-Pro / V4-Flash / R1
```

---

## 快速启动 (v2.0 9组件)

```bash
# 方式一：一键启动
D:\brain\start_all.bat

# 方式二：分别启动
hermes gateway start                              # 端口 18789
python D:\brain\staroffice-ui\backend\app.py       # 端口 18791
grafana-server                                     # 端口 3001 (需先装)
hermes dashboard                                   # 端口 9119
python D:\brain\tools\monitor_dashboard.py          # 端口 19997
python D:\brain\tools\pipeline_orchestrator.py --daemon
python D:\brain\tools\watchdog.py --daemon          # v2.0 自愈
python D:\brain\tools\checkpoint.py --daemon        # v2.0 断点
```

---

## 首次测试

```bash
hermes kanban create "生成一篇防晒小红书文案" --assignee strategist
```

## 记忆系统 v2.0.2 激活 ✅

| 组件 | 文件 | 状态 |
|------|------|------|
| 记忆桥接 | `tools/memory_bridge.py` | JSONL格式, 无污染fallback |
| 记忆引擎 | `tools/memory_engine.py` | 记忆块CRUD+版本管理 |
| Dreaming压缩机 | `tools/dreaming_compressor.py` | 三阶段(short/medium/long) |
| Daily记忆 | `output/memory/daily/` | 4天JSONL, 42事件 |
| Weekly蒸馏 | `output/memory/weekly/` | 首个蒸馏文件 |
| Monthly策略 | `output/memory/monthly/` | reputation.json(已激活)+strategies.json |
| Vector沉淀 | `output/memory/vector/` | 首个知识重构文件 |
| v2.0自检 | `tools/v2_integration_test.py` | 20/20 ALL PASS |
| 身份系统 | `SOUL.md`+`IDENTITY.md`+`USER.md` | 脑机🧠 / 礼宇 |

### 记忆流水线使用

```bash
python tools/dreaming_compressor.py short   # 4h 短期压缩
python tools/dreaming_compressor.py medium  # 每日信誉+策略更新
python tools/dreaming_compressor.py long    # 每周知识重构
python tools/dreaming_compressor.py all     # 全量运行
```

### 当前信誉分

| Agent | 评分 | 状态 |
|-------|------|------|
| executor-a | 0.7063 | 🔥 高分 — E2E通过 |
| arbiter | 0.6964 | 审查模块实现 |
| 其他 | 0.5000 | 基线 — 待真实任务激活 |

---
## 定时任务配置

```
*/5 * * * *  hermes kanban create "health_check" --assignee monitor
0   * * * *  hermes kanban create "hourly_learn" --assignee learner
0   2 * * *  hermes kanban create "daily_consolidate" --assignee learner
```
