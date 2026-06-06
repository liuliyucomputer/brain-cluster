# Brain 集群 — AI Agent 智能协同系统

> 23 Agent · 7 状态机 · 8 面板实时监控 · 6 条扩展线 · 全链路自动化

## 🚀 快速开始（新机器只需 3 步）

```bash
# 1. 克隆仓库
git clone <this-repo> brain
cd brain

# 2. 一键环境配置
setup.bat

# 3. 启动集群
start_all.bat
```

然后访问 `http://localhost:19996` 查看监控看板。

---

## 📋 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | ≥ 3.11 | `setup.bat` 自动检查 |
| Git | 任意 | 用于克隆和版本管理 |
| Hermes Agent CLI | v0.15+ | Gateway 调度引擎（需单独安装） |

---

## 🏗 架构

```
brain/
├── tools/              ← 17 个 Python 工具模块
│   ├── monitor_dashboard.py  全链路监控看板 (19996)
│   ├── extension_bridge.py   扩展线统一集成引擎
│   ├── pipeline_orchestrator.py  流水线编排
│   ├── memory_engine.py      记忆引擎
│   └── ...
├── input/
│   ├── configs/       ← ccswitch, hermes 等配置文件
│   ├── extensions/    ← 6 条扩展线接入指南
│   └── profiles/      ← 23 Agent SOUL Profile
├── eyes/              ← 参考项目集
│   ├── MoneyPrinterTurbo/    AI 视频生成
│   ├── presenton/           演示工具
│   └── PROJECT_DESIGN.md    项目规划
├── grafana/
│   ├── dashboards/    ← 仪表板 JSON
│   └── custom.ini     ← Grafana 配置
└── start_all.bat      ← 一键启动 5 个服务
```

---

## 🔗 服务面板

| 面板 | URL | 端口 |
|------|-----|------|
| 全链路监控 | `http://localhost:19996` | 19996 |
| Hermes Dashboard | `http://localhost:9119` | 9119 |
| StarOfficeUI | `http://localhost:18791` | 18791 |
| Grafana | `http://localhost:3001` | 3001 (admin/admin) |

---

## 👥 多人开发流程

```bash
# 开发机
git clone <repo>
cd brain && setup.bat
# 修改代码...
git add -A && git commit -m "my changes"
git push

# 其他人的机器
git pull
# 改动已在本地，无需重新 setup
```
