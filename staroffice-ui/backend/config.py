"""Star Office UI - Backend Configuration"""

import json
import os
from datetime import datetime


def _load_api_key():
    """Auto-load API key from config files if env var not set"""
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ.get("OPENAI_API_KEY")
    for cfg_path in [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "input", "configs", "ccswitch", "endpoint.json"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "input", "configs", "siliconflow", "endpoint.json"),
    ]:
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    key = data.get("api_key")
                    if key:
                        os.environ["OPENAI_API_KEY"] = key
                        return key
            except (json.JSONDecodeError, IOError):
                continue
    return None


# Auto-load API key on module import
_load_api_key()

# Paths (project-relative, no hardcoded absolute paths)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KANBAN_DB = os.path.join(ROOT_DIR, "..", "output", "memory", "kanban.db")
MEMORY_DIR = os.path.join(os.path.dirname(ROOT_DIR), "memory")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
STATE_FILE = os.path.join(ROOT_DIR, "state.json")
AGENTS_STATE_FILE = os.path.join(ROOT_DIR, "agents-state.json")
JOIN_KEYS_FILE = os.path.join(ROOT_DIR, "join-keys.json")

# Generate a version timestamp once at server startup for cache busting
VERSION_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# Default state
DEFAULT_STATE = {
    "state": "idle",
    "detail": "等待任务中...",
    "progress": 0,
    "updated_at": datetime.now().isoformat()
}

DEFAULT_AGENTS = [
    {
        "agentId": "star",
        "name": "Star",
        "isMain": True,
        "state": "idle",
        "detail": "待命中，随时准备为你服务",
        "updated_at": datetime.now().isoformat(),
        "area": "breakroom",
        "source": "local",
        "joinKey": None,
        "authStatus": "approved",
        "authExpiresAt": None,
        "lastPushAt": None
    },
    {
        "agentId": "npc1",
        "name": "NPC 1",
        "isMain": False,
        "state": "writing",
        "detail": "在整理热点日报...",
        "updated_at": datetime.now().isoformat(),
        "area": "writing",
        "source": "demo",
        "joinKey": None,
        "authStatus": "approved",
        "authExpiresAt": None,
        "lastPushAt": None
    }
]

# Service Management
SERVICE_CONFIGS = {
    "Grafana": {
        "cmd": [
            os.path.join(ROOT_DIR, "..", "grafana", "grafana-v11.6.0", "bin", "grafana-server.exe"),
            "--config", os.path.join(ROOT_DIR, "..", "grafana", "custom.ini"),
            "--homepath", os.path.join(ROOT_DIR, "..", "grafana", "grafana-v11.6.0"),
        ],
        "port": 3001,
        "cwd": os.path.join(ROOT_DIR, "..", "grafana", "grafana-v11.6.0"),
        "zh": "监控面板",
    },
    "Gateway": {
        "cmd": [
            "cmd", "/c",
            "set OPENAI_API_KEY=" + os.environ.get("OPENAI_API_KEY", "") + " && "
            "set OPENAI_BASE_URL=" + os.environ.get("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1") + " && "
            "set GATEWAY_ALLOW_ALL_USERS=true && "
            "set PYTHONIOENCODING=utf-8 && "
            "hermes gateway run --replace"
        ],
        "port": 18789,
        "cwd": os.path.join(ROOT_DIR, ".."),
        "zh": "网关",
    },
    "Dashboard": {
        "cmd": ["hermes", "dashboard"],
        "port": 9119,
        "cwd": os.path.join(ROOT_DIR, ".."),
        "zh": "仪表盘",
    },
    "StatsAPI": {
        "cmd": [],  # Merged into StarOfficeUI main app at /grafana/*
        "port": 19999,
        "cwd": os.path.join(ROOT_DIR, ".."),
        "zh": "统计接口",
        "merged": True,
    },
}

# Logs
LOG_ROOT = os.path.join(ROOT_DIR, "..", "output", "logs")

# Memory Manager
_MEMORY_DIRS = [
    ("项目记忆", os.path.join(ROOT_DIR, "..", ".workbuddy", "memory")),
    ("用户记忆", os.path.expanduser("~/.workbuddy")),
]

# Eyes Tools
EYES_TOOLS = [
    {"name": "andrej-karpathy-skills", "zh": "Karpathy 规则哲学", "category": "skill", "stars": "55K", "status": "verified", "desc": "Think First / Simplicity / Surgical / Goal-Driven", "dir": "andrej-karpathy-skills", "color": "indigo"},
    {"name": "harness", "zh": "元技能工厂", "category": "skill", "stars": "5.9K", "status": "verified", "desc": "7 Phase 工作流，6 种架构模式", "dir": "harness", "color": "indigo"},
    {"name": "Anthropic-Cybersecurity-Skills", "zh": "安全技能范本", "category": "skill", "stars": "14.1K", "status": "verified", "desc": "YAML frontmatter + index.json 规模化格式", "dir": "Anthropic-Cybersecurity-Skills", "color": "indigo"},
    {"name": "plugins", "zh": "Cursor 插件市场", "category": "skill", "stars": "2K", "status": "verified", "desc": "Cursor 插件市场结构参考", "dir": "plugins", "color": "indigo"},
    {"name": "claude-plugins-official", "zh": "Claude 官方插件", "category": "skill", "stars": "20.2K", "status": "verified", "desc": "plugin.json 标准，Skills/Commands/MCP 扩展", "dir": "claude-plugins-official", "color": "indigo"},
    {"name": "codegraph", "zh": "代码知识图谱", "category": "code", "stars": "40.7K", "status": "verified", "desc": "tree-sitter → SQLite → MCP 本地语义索引", "dir": "codegraph", "color": "cyan"},
    {"name": "Understand-Anything", "zh": "代码库导航仪", "category": "code", "stars": "51.9K", "status": "verified", "desc": "多 Agent 分析 + React Flow 可视化", "dir": "Understand-Anything", "color": "cyan"},
    {"name": "presenton", "zh": "AI PPT 生成", "category": "content", "stars": "7.9K", "status": "docker", "desc": "FastAPI + Next.js，支持 18+ LLM", "dir": "presenton", "color": "emerald"},
    {"name": "MoneyPrinterTurbo", "zh": "AI 短视频", "category": "content", "stars": "79K", "status": "verified", "desc": "LLM→TTS→素材→合成 全流程", "dir": "MoneyPrinterTurbo", "color": "emerald"},
    {"name": "VoxCPM", "zh": "免分词 TTS", "category": "content", "stars": "25.8K", "status": "verified", "desc": "30 语言 9 方言，48kHz，pip install 即用", "dir": "VoxCPM", "color": "emerald"},
    {"name": "LongLive", "zh": "长视频生成", "category": "content", "stars": "8.9K", "status": "gpu", "desc": "NVFP4 量化，需 B200/H100 40GB+ VRAM", "dir": "LongLive", "color": "emerald"},
    {"name": "open-notebook", "zh": "NotebookLM 替代", "category": "content", "stars": "24.8K", "status": "docker", "desc": "Docker 部署，源码完整待环境", "dir": "open-notebook", "color": "emerald"},
    {"name": "supermemory", "zh": "跨会话记忆引擎", "category": "infra", "stars": "25.5K", "status": "cloudflare", "desc": "MCP + REST API + Python SDK", "dir": "supermemory", "color": "violet"},
]

CATEGORY_LABELS = {
    "skill":   {"zh": "Skill/规则层", "en": "Skills & Rules"},
    "code":    {"zh": "代码理解层", "en": "Code Understanding"},
    "content": {"zh": "内容生成层", "en": "Content Generation"},
    "infra":   {"zh": "基础设施层", "en": "Infrastructure"},
}

STATUS_LABELS = {
    "verified":   {"zh": "可用", "en": "Ready", "cls": "success"},
    "docker":     {"zh": "需 Docker", "en": "Needs Docker", "cls": "warning"},
    "cloudflare": {"zh": "需 Cloudflare", "en": "Needs Cloudflare", "cls": "warning"},
    "gpu":        {"zh": "需 GPU", "en": "Needs GPU", "cls": "danger"},
}
