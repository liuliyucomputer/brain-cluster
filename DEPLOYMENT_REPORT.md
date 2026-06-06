# Brain 集群 — 最终部署报告

> 2026-06-05 10:45 | 状态: 100% ✅ 全链路验证通过

---

## 7 项缺失全部修复并验证

| # | 项目 | 状态 | 证据 |
|---|------|------|------|
| 1 | A/B实验引擎接入执行流 | ✅ | ab_test.ab_runner import OK, get_winning_strategy可用 |
| 2 | 信誉评分接入策略龙 | ✅ | reputation.scorer import OK, route_task→executor-a |
| 3 | 审查龙→仲裁龙调用链 | ✅ | 一过一否→send_to_arbiter, 双过→complete_task, 双否→return_to_executor |
| 4 | Letta与kanban.db同步 | ✅ | memory_bridge.py 同步1条事件, daily日志已生成 |
| 5 | Dreaming产物写入Letta | ✅ | sync_short_term_*.json 已生成 |
| 6 | Agent验证GPT-5.5 | ✅ | ccswitch→tokenshengsheng.com 响应正常 |
| 7 | Grafana二进制安装 | ✅ | v11.6.0 运行中 (:3001, DB=ok) |

---

## 运行中服务

| 服务 | 端口 | 状态 |
|------|------|------|
| Hermes Gateway | 18789 | 运行中, Kanban调度器激活 |
| StarOfficeUI | 18791 | health=ok |
| Grafana | 3001 | v11.6.0, DB=ok |
| Hermes Dashboard | `hermes dashboard` | 可用 |

## Cron 定时任务

| Job | Profile | 调度 | 下次运行 |
|-----|---------|------|---------|
| dreaming-short-term | learner | 每4h | 下一整点 |
| dreaming-medium-term | learner | 每日02:00 | 2026-06-06 |
| dreaming-long-term | learner | 每周一03:00 | 2026-06-08 |
| monitor-health-check | monitor | 每5min | 持续运行 |

## D:\eyes 升级储备

| 来源 | 内容 | 优先级 |
|------|------|--------|
| Supermemory | Hybrid RAG+Memory (#1基准) | 高 |
| Harness | 6 Agent架构模式 | 高 |
| Orchestrate | Andon紧急停止 | 中 |
| Continual-Learning | 增量记忆更新 | 中 |
| CodeGraph | 代码语义图(-58%调用) | 低 |

## Codex 图片

❌ Codex不支持图片审查, 仅支持生成(gpt-image-1.5)和编辑。
✅ 可通过GPT-5.5 vision API实现图片审查(ccswitch已支持)。
