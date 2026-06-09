# -*- coding: utf-8 -*-
"""
Brain 集群 — 指挥官核心模块 (Commander Core) v1.0
职责: 为 SupremeCommander 和 MetaCommander 提供公共基类与共享组件。
      包含状态管理、扫描引擎、LLM 接口、修复规则库及公共工具函数。
版本: v1.0 | 2026-06-09
"""
import ast
import json
import os
import re
import shutil
import sqlite3
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import KANBAN_DB, LOGS_DIR, TOOLS_DIR, PROJECT_ROOT

# ── 风险分级 ──
RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"
RISK_CRITICAL = "critical"

# ── 受保护文件（绝对不可修改） ──
PROTECTED_FILES = {
    "kanban.db",
    "memory_blocks.db",
    "reputation.json",
    ".env",
    "gateway.json",
    "endpoint.json",
    "checkpoint_",
}

# ── 统一修复规则库（合并去重） ──
# 字段说明:
#   name          : 规则唯一标识
#   pattern       : 正则匹配模式
#   risk          : 风险等级 (low/medium/high/critical)
#   auto_fix      : 是否可自动修复（决策引擎使用）
#   fix           : 简单替换文本（决策引擎使用）
#   description   : 问题描述
#   fix_type      : meta_commander 使用的修复类型 (replace/replace_import/mark/manual_review)
#   replacement   : fix_type=replace/replace_import 时的替换文本
#   marker        : fix_type=mark 时追加的标记
#   exclude_files : fix_type=mark 时排除的文件列表
#   llm_fixable   : 是否可调用 LLM 修复
#   message       : manual_review 时输出的提示信息
FIX_RULES = [
    {
        "name": "fix_bare_except",
        "pattern": r"except\s*:\s*$",
        "risk": RISK_LOW,
        "auto_fix": True,
        "fix": "except Exception:",
        "description": "裸 except 会捕获 KeyboardInterrupt",
        "fix_type": "replace",
        "replacement": "except Exception:",
        "llm_fixable": True,
    },
    {
        "name": "fix_fcntl_import",
# import fcntl  # Windows 不兼容，已注释
        "risk": RISK_LOW,
        "auto_fix": True,
# import fcntl  # Windows 不兼容，已注释
        "description": "Unix fcntl 在 Windows 上不可用",
        "fix_type": "replace_import",
# import fcntl  # Windows 不兼容，已注释
        "llm_fixable": True,
    },
    {
        "name": "fix_hardcoded_secret",
        "pattern": r"(api_key|apikey|secret|password)\s*=\s*['\"][^'\"]{10,}['\"]",
        "risk": RISK_HIGH,
        "auto_fix": False,
        "description": "硬编码密钥/密码",
        "fix_type": "mark",
        "marker": "# SECURITY: 硬编码凭证，建议改用环境变量",
        "exclude_files": ["endpoint.json", "gateway.json", "app.py"],
        "llm_fixable": False,
    },
    {
        "name": "fix_print_debug",
        "pattern": r"^\s*print\s*\([^)]*\)\s*$",
        "risk": RISK_LOW,
        "auto_fix": False,
        "description": "生产代码中的 print 调试语句",
        "fix_type": "mark",
        "marker": "# TODO: 移除调试打印",
        "exclude_files": ["meta_commander.py", "watchdog.py", "checkpoint.py", "memory_engine.py", "monitor_dashboard.py", "supreme_commander.py"],
        "llm_fixable": False,
    },
    {
        "name": "fix_datetime_now_tz",
        "pattern": r"datetime\.now\(\) - .*\.replace\(tzinfo=None\)",
        "risk": RISK_MEDIUM,
        "auto_fix": False,
        "description": "时区处理错误：UTC 与本地时间混算",
        "fix_type": "manual_review",
        "message": "发现时区处理错误，建议改为 datetime.now(created_dt.tzinfo)",
        "llm_fixable": True,
    },
]


def _is_protected(filepath):
    """检查文件是否受保护"""
    basename = os.path.basename(filepath)
    return any(p in basename for p in PROTECTED_FILES)


def _check_port(port, host="127.0.0.1", timeout=1):
    """检查端口是否开放"""
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        return result == 0
    except socket.error:
        return False
    finally:
        if sock:
            sock.close()


def _load_api_config():
    """加载 API 配置（优先 SiliconFlow）"""
    config_paths = [
        os.path.join(PROJECT_ROOT, "input", "configs", "siliconflow", "endpoint.json"),
        os.path.join(PROJECT_ROOT, "input", "configs", "ccswitch", "endpoint.json"),
    ]
    for path in config_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue
    return None


# ═══════════════════════════════════════════════
#  状态管理
# ═══════════════════════════════════════════════

class StateManager:
    """通用状态管理器（支持不同日志目录与状态文件）"""

    def __init__(self, log_dir, state_file, decision_log=None, error_log=None):
        self.log_dir = log_dir
        self.state_file = state_file
        self.decision_log = decision_log
        self.error_log = error_log
        os.makedirs(self.log_dir, exist_ok=True)
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "version": "1.0",
            "status": "active",
            "scan_count": 0,
            "fixes_auto": 0,
            "fixes_manual": 0,
            "fixes_failed": 0,
            "crisis_count": 0,
            "last_scan": None,
            "active_issues": [],
            "resolved_issues": [],
            "agent_health": {},
            # meta_commander 兼容字段
            "issues_found_total": 0,
            "fixes_applied_total": 0,
            "fixes_failed_total": 0,
            "llm_fixes_total": 0,
            "protected_skips": 0,
        }

    def save(self):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def log_decision(self, decision):
        if not self.decision_log:
            return
        decision["ts"] = datetime.now().isoformat()
        with open(self.decision_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(decision, ensure_ascii=False) + "\n")

    def log_error(self, error):
        if not self.error_log:
            return
        error["ts"] = datetime.now().isoformat()
        with open(self.error_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(error, ensure_ascii=False) + "\n")

    def log_event(self, event, log_path):
        """向指定日志文件追加事件（meta_commander 使用）"""
        event["ts"] = datetime.now().isoformat()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


# ═══════════════════════════════════════════════
#  LLM 接口
# ═══════════════════════════════════════════════

class LLMInterface:
    """LLM 调用接口"""

    def __init__(self):
        self.config = _load_api_config()

    def call(self, prompt, system="你是 Brain 集群的智能指挥官，负责诊断和修复代码问题。", temperature=0.1, max_tokens=4000, timeout=120):
        if not self.config:
            return None, "未找到 API 配置"

        api_key = self.config.get("api_key")
        base_url = self.config.get("base_url", "https://api.siliconflow.cn/v1")
        model = self.config.get("default_model", "deepseek-ai/DeepSeek-V4-Pro")

        req_data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_error = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    f"{base_url}/chat/completions",
                    data=json.dumps(req_data).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                    method="POST",
                )

                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    result = json.loads(resp.read().decode("utf-8"))

                choices = result.get("choices", [])
                if not choices:
                    return None, f"API 返回空 choices: {str(result)[:200]}"
                content = choices[0].get("message", {}).get("content", "")
                if not content:
                    return None, f"API 返回空 content: {str(choices[0])[:200]}"
                return content, None
            except urllib.error.HTTPError as e:
                last_error = f"HTTP {e.code}: {e.reason}"
                if attempt < 2:
                    time.sleep(2 ** attempt)
            except Exception as e:
                last_error = str(e)
                if attempt < 2:
                    time.sleep(2 ** attempt)

        return None, last_error or "未知错误"

    def call_for_fix(self, issue, file_content, surrounding_lines=10):
        """
        调用 LLM API 获取智能修复建议（MetaCommander 风格）。
        返回 (fix_suggestion, explanation) 或 (None, error_message)
        """
        if not self.config:
            return None, "未找到 API 配置"

        api_key = self.config.get("api_key")
        base_url = self.config.get("base_url", "https://api.siliconflow.cn/v1")
        model = self.config.get("default_model", "deepseek-ai/DeepSeek-V4-Pro")

        if not api_key:
            return None, "API Key 未配置"

        line_num = issue.get("line", 0)
        lines = file_content.split("\n")
        start = max(0, line_num - surrounding_lines - 1)
        end = min(len(lines), line_num + surrounding_lines)
        context = "\n".join(f"{i+1}: {lines[i]}" for i in range(start, end))

        prompt = f"""你是一个 Python 代码修复专家。请修复以下代码问题。

文件: {issue.get('file', 'unknown')}
问题类型: {issue.get('type', 'unknown')}
问题描述: {issue.get('message', issue.get('description', 'unknown'))}
行号: {line_num}

上下文代码:
```python
{context}
```

请提供修复后的代码片段（只修改有问题的部分，保持其他代码不变）。
输出格式:
FIX_START
<修复后的代码>
FIX_END
EXPLANATION: <简要说明修复原因>
"""

        content, error = self.call(
            prompt,
            system="你是一个专业的 Python 代码修复助手。只输出修复后的代码和简要说明。",
            temperature=0.1,
            max_tokens=2000,
            timeout=60,
        )
        if error:
            return None, error

        fix_match = re.search(r"FIX_START\n(.*?)\nFIX_END", content, re.DOTALL)
        fix_code = fix_match.group(1).strip() if fix_match else content.strip()
        expl_match = re.search(r"EXPLANATION:\s*(.+)", content)
        explanation = expl_match.group(1).strip() if expl_match else "LLM 提供的修复"
        return fix_code, explanation


# ═══════════════════════════════════════════════
#  扫描引擎
# ═══════════════════════════════════════════════

class ScanEngine:
    """代码扫描引擎"""

    def __init__(self, state=None):
        self.state = state
        self.issues = []

    def scan_all(self, include_services=False):
        """全面扫描
        Args:
            include_services: 是否扫描服务端口健康（SupremeCommander 使用）
        """
        self.issues = []
        py_files = self._get_py_files()

        for filepath in py_files:
            if _is_protected(filepath):
                continue
            self._scan_syntax(filepath)
            self._scan_imports(filepath)
            self._scan_patterns(filepath)

        self._scan_db_health()
        if include_services:
            self._scan_services()

        return self.issues

    def _get_py_files(self):
        files = []
        for root, dirs, filenames in os.walk(TOOLS_DIR):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in filenames:
                if f.endswith(".py"):
                    files.append(os.path.join(root, f))
        return files

    def _scan_syntax(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
            ast.parse(source)
        except SyntaxError as e:
            self.issues.append({
                "type": "syntax_error",
                "file": filepath,
                "line": e.lineno,
                "message": str(e),
                "risk": RISK_CRITICAL,
                "auto_fix": True,
                "severity": "critical",
                "llm_fixable": True,
            })

    def _scan_imports(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except Exception:
            return

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [a.name.split(".")[0] for a in node.names]
                elif node.module:
                    modules = [node.module.split(".")[0]]

                for mod in modules:
                    if mod in ["fcntl", "resource", "termios"]:
                        self.issues.append({
                            "type": "platform_import",
                            "file": filepath,
                            "line": node.lineno,
                            "module": mod,
                            "message": f"模块 {mod} 在 Windows 不可用",
                            "risk": RISK_LOW,
                            "auto_fix": True,
                            "severity": "high",
                            "llm_fixable": True,
                        })

    def _scan_patterns(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return

        basename = os.path.basename(filepath)
        for i, line in enumerate(lines, 1):
            for rule in FIX_RULES:
                excluded = rule.get("exclude_files", [])
                if basename in excluded:
                    continue
                if re.search(rule["pattern"], line):
                    issue = {
                        "type": "pattern",
                        "rule": rule["name"],
                        "file": filepath,
                        "line": i,
                        "message": rule.get("description", rule["name"]),
                        "risk": rule["risk"],
                        "auto_fix": rule.get("auto_fix", False),
                        "fix": rule.get("fix"),
                        "content": line.strip(),
                        # meta_commander 兼容字段
                        "description": rule.get("description", rule["name"]),
                        "fix_type": rule.get("fix_type"),
                        "severity": "medium",
                        "llm_fixable": rule.get("llm_fixable", False),
                        "replacement": rule.get("replacement"),
                        "marker": rule.get("marker"),
                    }
                    self.issues.append(issue)

    def _scan_db_health(self):
        if not os.path.exists(KANBAN_DB):
            self.issues.append({
                "type": "db_missing",
                "message": "kanban.db 不存在",
                "risk": RISK_CRITICAL,
                "auto_fix": False,
                "severity": "critical",
                "llm_fixable": False,
            })
            return

        conn = None
        try:
            conn = sqlite3.connect(KANBAN_DB, timeout=3)
            cursor = conn.cursor()

            for table in ["tasks", "task_links", "task_runs", "task_events"]:
                cursor.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                    (table,)
                )
                if not cursor.fetchone():
                    self.issues.append({
                        "type": "db_table_missing",
                        "table": table,
                        "risk": RISK_HIGH,
                        "auto_fix": False,
                        "severity": "high",
                        "llm_fixable": False,
                    })

            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            if result and result[0] != "ok":
                self.issues.append({
                    "type": "db_corrupt",
                    "message": result[0],
                    "risk": RISK_CRITICAL,
                    "auto_fix": False,
                    "severity": "critical",
                    "llm_fixable": False,
                })
        except (sqlite3.Error, OSError) as e:
            self.issues.append({
                "type": "db_error",
                "message": str(e),
                "risk": RISK_CRITICAL,
                "auto_fix": False,
                "severity": "critical",
                "llm_fixable": False,
            })
        finally:
            if conn:
                conn.close()

    def _scan_services(self):
        """检查关键服务状态"""
        services = {
            "hermes_gateway": 18789,
            "staroffice_ui": 18791,
            "grafana": 3001,
            "dashboard": 9119,
        }

        for name, port in services.items():
            if not _check_port(port):
                self.issues.append({
                    "type": "service_down",
                    "service": name,
                    "port": port,
                    "risk": RISK_HIGH,
                    "auto_fix": False,
                    "severity": "high",
                    "llm_fixable": False,
                })


# ═══════════════════════════════════════════════
#  修复工具函数
# ═══════════════════════════════════════════════

def verify_fix(filepath):
    """验证修复后的文件语法是否正确"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            ast.parse(f.read())
        return True
    except Exception:
        return False


def apply_rule_fix(issue, dry_run=True, backup_suffix=".backup"):
    """
    基于 FIX_RULES 中的 fix_type 应用修复。
    返回 (success, message, fix_source)
    """
    filepath = issue.get("file")
    if not filepath or _is_protected(filepath):
        return False, "文件受保护，跳过", "skipped"

    fix_type = issue.get("fix_type")
    line_num = issue.get("line", 0)

    if fix_type == "replace_import":
        return _fix_replace_line(filepath, line_num, issue.get("pattern"), issue.get("replacement", ""), dry_run, backup_suffix)
    elif fix_type == "replace":
        return _fix_replace_line(filepath, line_num, None, issue.get("replacement", ""), dry_run, backup_suffix)
    elif fix_type == "mark":
        return _fix_add_marker(filepath, line_num, issue.get("marker", ""), dry_run, backup_suffix)
    elif fix_type == "manual_review":
        return False, f"需要人工审查: {issue.get('message', '')}", "manual"
    else:
        # 回退到简单的 fix 字段替换（supreme_commander 风格）
        fix_text = issue.get("fix")
        if fix_text:
            return _fix_replace_line(filepath, line_num, None, fix_text, dry_run, backup_suffix)
        return False, "未知修复类型", "unknown"


def apply_llm_fix(issue, llm, dry_run=True, backup_suffix=".backup"):
    """
    调用 LLM 获取修复建议并应用。
    返回 (success, message, fix_source)
    """
    filepath = issue.get("file")
    if not filepath or _is_protected(filepath):
        return False, "文件受保护，跳过", "skipped"

    line_num = issue.get("line", 0)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            file_content = f.read()

        fix_code, explanation = llm.call_for_fix(issue, file_content)
        if fix_code:
            backup_path = filepath + backup_suffix
            if not dry_run:
                shutil.copy2(filepath, backup_path)
                lines = file_content.split("\n")
                if line_num > 0 and line_num <= len(lines):
                    lines[line_num - 1] = fix_code
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write("\n".join(lines))

            return True, f"{'[DRY-RUN] ' if dry_run else ''}LLM 修复: {explanation}", "llm"
        else:
            return False, f"LLM 无法提供修复: {explanation}", "llm_failed"
    except Exception as e:
        return False, f"LLM 修复失败: {str(e)}", "llm_error"


def _fix_replace_line(filepath, line_num, pattern, replacement, dry_run, backup_suffix=".backup"):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if line_num < 1 or line_num > len(lines):
            return False, "行号越界", "rule"

        backup_path = filepath + backup_suffix
        if not dry_run:
            shutil.copy2(filepath, backup_path)
            lines[line_num - 1] = replacement + "\n"
            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(lines)

        return True, f"{'[DRY-RUN] ' if dry_run else ''}替换第 {line_num} 行", "rule"
    except Exception as e:
        return False, str(e), "rule"


def _fix_add_marker(filepath, line_num, marker, dry_run, backup_suffix=".backup"):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if line_num < 1 or line_num > len(lines):
            return False, "行号越界", "rule"

        backup_path = filepath + backup_suffix
        if not dry_run:
            shutil.copy2(filepath, backup_path)
            lines[line_num - 1] = lines[line_num - 1].rstrip() + f"  {marker}\n"
            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(lines)

        return True, f"{'[DRY-RUN] ' if dry_run else ''}第 {line_num} 行添加标记", "rule"
    except Exception as e:
        return False, str(e), "rule"


def rollback_fix(filepath, backup_suffix=".backup"):
    """回滚自动修复"""
    backup_path = filepath + backup_suffix
    if os.path.exists(backup_path):
        shutil.copy2(backup_path, filepath)
        os.remove(backup_path)
        return True
    return False
