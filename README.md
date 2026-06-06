# Brain 集群 — AI Agent 智能协同系统

[![Stack](https://img.shields.io/badge/23-Agent-blue)](.)
[![Lines](https://img.shields.io/badge/6-Extensions-green)](.)
[![Repo](https://img.shields.io/badge/repo-347KB-success)](.)

> 23 Agent · 7 状态机 · 8 面板实时监控 · 全链路自动化

## 🚀 快速启动

### 环境要求
- Python ≥ 3.11
- Hermes Agent CLI (用于 Gateway)
- Grafana v11.6+ (二进制包)

### 安装依赖项目 (这些不在 git 中，需要单独克隆)
```bash
# 调度引擎
git clone <hermes-agent-url> hermes-agent/

# 多平台适配
git clone <openclaw-url> openclaw/
```

### 启动集群
```bash
start_all.bat
# 或逐项启动:
python tools/monitor_dashboard.py   # 监控看板 :19996
hermes gateway run                  # 调度引擎 (CLI内部)
```

## 📊 架构

```
brain/
├── tools/              ← 17个 Python 工具模块
│   ├── monitor_dashboard.py   监控看板
│   ├── extension_bridge.py    扩展线集成引擎
│   ├── pipeline_orchestrator.py  流水线编排
│   ├── memory_engine.py       记忆引擎
│   └── ...
├── input/
│   ├── configs/       ← 配置文件 (ccswitch, hermes, ...)
│   ├── extensions/    ← 6条扩展线接入指南
│   └── profiles/      ← 23 Agent SOUL Profile
├── eyes/              ← 13个参考项目设计文档
├── grafana/           ← Grafana 仪表板配置
└── start_all.bat      ← 一键启动脚本
```

## 🔗 面板

| 面板 | URL | 数据源 |
|------|-----|--------|
| 全链路监控 | `http://localhost:19996` | 8 API 实时数据 |
| Hermes Dashboard | `http://localhost:9119` | Kanban 界面 |
| StarOfficeUI | `http://localhost:18791` | 前端 UI |
| Grafana | `http://localhost:3001` | 运维大屏 (admin/admin) |

## 👥 协作方式

```bash
git clone <this-repo> brain/
cd brain
# 安装依赖项目, 启动, 开发
```
