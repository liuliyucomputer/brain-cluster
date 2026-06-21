# -*- coding: utf-8 -*-
"""
路径管理模块 — 所有路径相对于项目根目录自动检测
=================================================================
用法: from paths import PROJECT_ROOT, MEMORY_DIR, TOOLS_DIR, ...

适用场景:
  - 项目上传到 GitHub，任何人 clone 到任意目录都能运行
  - 不再硬编码 D:/brain/ 等绝对路径
  - 跨平台兼容 (Windows/Linux/macOS)

外部依赖路径 (B: 盘等) 通过环境变量配置:
  B_DRIVE_ROOT      - B: 盘根目录 (默认 B:\)
  PYTHON_EXE        - Python 可执行文件 (默认 python，从 PATH 查找)
  HERMES_PROFILES   - Hermes profiles 目录 (默认 %LOCALAPPDATA%\hermes\profiles)
"""

import os, sys

# ── 项目根目录: 自动检测 ──
# tools/paths.py 的上两级目录 = D:\brain
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 核心目录 ──
PROJECT_ROOT = _PROJECT_ROOT
TOOLS_DIR = os.path.join(PROJECT_ROOT, "tools")
INPUT_DIR = os.path.join(PROJECT_ROOT, "input")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
CONFIGS_DIR = os.path.join(INPUT_DIR, "configs")
PROFILES_DIR = os.path.join(INPUT_DIR, "profiles")
EXTENSIONS_DIR = os.path.join(INPUT_DIR, "extensions")
GRAFANA_DIR = os.path.join(PROJECT_ROOT, "grafana")
LETTA_DIR = os.path.join(PROJECT_ROOT, "letta")
STAROFFICE_DIR = os.path.join(PROJECT_ROOT, "staroffice-ui")

# ── 记忆层 ──
MEMORY_DIR = os.path.join(OUTPUT_DIR, "memory")
MEMORY_DAILY = os.path.join(MEMORY_DIR, "daily")
MEMORY_WEEKLY = os.path.join(MEMORY_DIR, "weekly")
MEMORY_MONTHLY = os.path.join(MEMORY_DIR, "monthly")
MEMORY_VECTOR = os.path.join(MEMORY_DIR, "vector")

# ── 数据库 ──
# Primary kanban.db: gateway.json configured db_path (D:\brain\output\memory\kanban.db)
BRAIN_KANBAN_DB = os.path.join(MEMORY_DIR, "kanban.db")

# Hermes may also create kanban.db in its AppData directory (legacy default)
HERMES_KANBAN_DB = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "hermes", "kanban.db"
)

# Prefer D:\brain (our configured gateway.json db_path) if it exists and is non-empty
if os.path.exists(BRAIN_KANBAN_DB) and os.path.getsize(BRAIN_KANBAN_DB) > 1024:
    KANBAN_DB = BRAIN_KANBAN_DB
elif os.path.exists(HERMES_KANBAN_DB) and os.path.getsize(HERMES_KANBAN_DB) > 1024:
    KANBAN_DB = HERMES_KANBAN_DB
else:
    # If both exist, prefer D:\brain (our configured path)
    KANBAN_DB = BRAIN_KANBAN_DB if os.path.exists(BRAIN_KANBAN_DB) else HERMES_KANBAN_DB
MEMORY_BLOCKS_DB = os.path.join(MEMORY_DIR, "memory_blocks.db")
LETTA_DB = os.path.join(LETTA_DIR, "letta.db")

# ── 配置文件 ──
CCSWITCH_ENDPOINT = os.path.join(CONFIGS_DIR, "ccswitch", "endpoint.json")
SILICONFLOW_ENDPOINT = os.path.join(CONFIGS_DIR, "siliconflow", "endpoint.json")
HERMES_GATEWAY_CONFIG = os.path.join(CONFIGS_DIR, "hermes", "gateway.json")
OPENCLAW_DREAMING_CONFIG = os.path.join(CONFIGS_DIR, "openclaw", "dreaming.json")
EXTENSION_STATUS = os.path.join(EXTENSIONS_DIR, "extension_status.json")

# ── 报告/日志 ──
REPORTS_DIR = os.path.join(OUTPUT_DIR, "reports")
LOGS_DIR = os.path.join(OUTPUT_DIR, "logs")

# ── 外部依赖 (可配置) ──
B_DRIVE_ROOT = os.environ.get("B_DRIVE_ROOT", "B:\\")
PYTHON_EXE = os.environ.get("PYTHON_EXE", "python")
NODE_EXE = os.environ.get("NODE_EXE", "node")

# Hermes profiles (Windows 特定，Linux 需设置环境变量)
if sys.platform == "win32":
    HERMES_PROFILES = os.environ.get(
        "HERMES_PROFILES",
        os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "hermes", "profiles")
    )
else:
    HERMES_PROFILES = os.environ.get(
        "HERMES_PROFILES",
        os.path.join(os.path.expanduser("~"), ".hermes", "profiles")
    )

# MCP 配置文件
MCP_JSON = os.path.join(os.path.expanduser("~"), ".workbuddy", "mcp.json")

# CodeBuddy Skills 目录
SKILLS_DIR = os.path.join(os.path.expanduser("~"), ".workbuddy", "skills")

# Publisher 代码目录
PUBLISHER_DIR = os.environ.get(
    "PUBLISHER_DIR",
    os.path.join(os.path.expanduser("~"), "WorkBuddy", "Claw")
)

# StarOfficeUI
STAROFFICE_BACKEND = os.path.join(STAROFFICE_DIR, "backend", "app.py")


def ensure_dirs():
    """确保所有必要的目录存在"""
    for d in [MEMORY_DAILY, MEMORY_WEEKLY, MEMORY_MONTHLY, MEMORY_VECTOR, REPORTS_DIR, LOGS_DIR]:
        os.makedirs(d, exist_ok=True)
    # v2.0 log subdirectories
    for sub in ["watchdog", "orchestrator", "checkpoints"]:
        os.makedirs(os.path.join(LOGS_DIR, sub), exist_ok=True)
    # checkpoints directory
    os.makedirs(os.path.join(MEMORY_DIR, "checkpoints"), exist_ok=True)


def load_api_config():
    """从 endpoint.json 加载 API 配置"""
    import json
    if os.path.exists(CCSWITCH_ENDPOINT):
        with open(CCSWITCH_ENDPOINT, encoding="utf-8") as f:
            cfg = json.load(f)
        return {
            "api_key": cfg.get("api_key", ""),
            "base_url": cfg.get("base_url", "https://api.siliconflow.cn/v1"),
            "model": cfg.get("model", "deepseek-ai/DeepSeek-V4-Pro"),
        }
    return {
        "api_key": os.environ.get("OPENAI_API_KEY", ""),
        "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1"),
        "model": "deepseek-ai/DeepSeek-V4-Pro",
    }


# 确保目录存在
ensure_dirs()
