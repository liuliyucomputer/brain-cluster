# 📤 输出层 (Output)

Brain集群的**所有产物**统一落盘目录。系统的日志、记忆、Agent执行结果、审查报告全部集中管理。

## 子目录说明

| 目录 | 用途 | 来源 |
|------|------|------|
| `memory/` | 四层记忆存储 | memory/ 迁移 |
| `logs/` | 分层日志系统 | log/ 迁移 |
| `artifacts/` | Agent执行产物(新建) | content + analysis + media |
| `reviews/` | 审查评分+仲裁裁决(新建) | 双审 + 仲裁输出 |
| `reports/` | 巡检+汇总报告(新建) | monitor + learner输出 |

## 数据产出方

| 子系统 | → 输出到 |
|--------|---------|
| executor-a/b/c | `artifacts/content/`, `artifacts/analysis/` |
| reviewer-strict/creative | `reviews/` |
| arbiter | `reviews/` |
| monitor | `reports/` |
| learner | `memory/`, `reports/` |
| memory_bridge | `memory/daily/` |
| Dreaming pipeline | `memory/weekly/`, `memory/monthly/`, `memory/vector/` |
| log_manager / log_aggregator | `logs/` |

## 数据流向

```
Agent执行 → artifacts/content/ + artifacts/analysis/
双审引擎  → reviews/
仲裁表决  → reviews/
监控巡检  → reports/
记忆桥接  → memory/daily/
Dreaming   → memory/weekly/ → monthly/ → vector/
日志系统   → logs/agents/ + logs/gateway/ + logs/system/
```

## 维护命令

```bash
# 查看今日日志
python tools/log_manager.py tail

# 扫描错误
python tools/log_manager.py errors

# 清理30天前日志
python tools/log_manager.py rotate

# 查看记忆统计
python tools/memory_engine.py
```
