# Brain 集群 — 对接完成清单

> 最后更新：2026-06-05 03:00

---

## ccswitch 对接 ✅

| 配置项 | 值 |
|--------|-----|
| 中转站 | `https://tokenshengsheng.com/v1` |
| 模型 | `gpt-5.5` (reasoning_effort=high) |
| 密钥 | `sk-xGSs...PvP8` |
| API 协议 | `responses` |

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
          ccswitch
      tokenshengsheng.com/v1
               │
               ▼
         GPT-5.5 + Codex
```

---

## 快速启动

```bash
# 方式一：一键启动
D:\brain\start_all.bat

# 方式二：分别启动
hermes gateway start                              # 端口 18789
openclaw dreaming start                           # 记忆巩固
python D:\brain\staroffice-ui\backend\app.py       # 端口 19000
hermes dashboard                                   # 端口 3000
grafana-server                                     # 端口 3001 (需先装)
```

---

## 首次测试

```bash
hermes kanban create "生成一篇防晒小红书文案" --assignee strategist
```

## 定时任务配置

```
*/5 * * * *  hermes kanban create "health_check" --assignee monitor
0   * * * *  hermes kanban create "hourly_learn" --assignee learner
0   2 * * *  hermes kanban create "daily_consolidate" --assignee learner
```
