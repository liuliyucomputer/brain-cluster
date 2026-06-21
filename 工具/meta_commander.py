# -*- coding: utf-8 -*-
"""
Brain 集群 — 元认知指挥官 (Meta Commander) v2.4
职责: 监控本项目自身代码健康，检测语法错误、导入失败、配置异常，
      并尝试自动修复（安全修复模式 + LLM 智能修复）。
      自己监控自己，自己修复自己。
版本: v2.4 | 2026-06-09
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import KANBAN_DB, LOGS_DIR, TOOLS_DIR, PROJECT_ROOT
from commander_core import (
    StateManager,
    ScanEngine,
    LLMInterface,
    FIX_RULES,
    _is_protected,
    apply_rule_fix,
    apply_llm_fix,
    rollback_fix,
)

# ── 配置 ──
META_LOG_DIR = os.path.join(LOGS_DIR, "meta_commander")
META_STATE_FILE = os.path.join(META_LOG_DIR, "meta_state.json")
META_FIX_LOG = os.path.join(META_LOG_DIR, "fix_history.jsonl")

BACKUP_SUFFIX = ".meta_backup"


def _log_event(event):
    """记录元认知事件"""
    event["ts"] = datetime.now().isoformat()
    with open(META_FIX_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def run_full_scan(fix_mode="dry_run", use_llm=False):
    """
    运行完整扫描。
    fix_mode: dry_run | safe | aggressive
        - dry_run: 只检测不修复
        - safe: 只应用已知安全修复
        - aggressive: 尝试更多自动修复（不推荐）
    use_llm: 是否调用 LLM API 进行智能修复
    """
    state_mgr = StateManager(META_LOG_DIR, META_STATE_FILE)
    state = state_mgr.data
    all_issues = []
    fixes_applied = 0
    fixes_failed = 0
    llm_fixes = 0
    protected_skips = 0

    scanner = ScanEngine(state_mgr)

    # 1. 扫描所有 Python 文件
    py_files = scanner._get_py_files()

    print(f"[META] Scanning {len(py_files)} Python files...")
    if use_llm:
        print("[META] LLM 智能修复已启用")

    for filepath in py_files:
        if _is_protected(filepath):
            protected_skips += 1
            continue

        # 语法扫描
        scanner._scan_syntax(filepath)
        # 导入扫描
        scanner._scan_imports(filepath)
        # 模式扫描
        scanner._scan_patterns(filepath)

    all_issues = scanner.issues

    # 过滤：只保留 fix_bare_except 作为需要修复的问题
    # 其他模式（print、secret）仅作为信息记录，不显示为问题
    filtered_issues = []
    for issue in all_issues:
        if issue.get("rule") == "fix_bare_except" or issue.get("type") in ("syntax_error", "platform_import", "db_missing", "db_table_missing", "db_corrupt", "db_error"):
            filtered_issues.append(issue)
    all_issues = filtered_issues

    # 2. 扫描数据库健康（已包含在 scan_all 中，但 meta_commander 需要独立调用以兼容旧行为）
    db_issues = []
    scanner._scan_db_health()
    # 将数据库问题加入 all_issues（去重）
    existing_types = {(i.get("type"), i.get("message")) for i in all_issues}
    for issue in scanner.issues:
        key = (issue.get("type"), issue.get("message"))
        if key not in existing_types and issue.get("type", "").startswith("db_"):
            all_issues.append(issue)
            existing_types.add(key)

    # 3. 尝试修复（如果模式允许）
    llm = LLMInterface() if use_llm else None

    if fix_mode in ("safe", "aggressive"):
        for issue in all_issues:
            if issue.get("severity") in ("critical", "high") and issue.get("fix_type"):
                if use_llm and issue.get("llm_fixable") and llm:
                    success, msg, fix_source = apply_llm_fix(issue, llm, dry_run=(fix_mode == "dry_run"), backup_suffix=BACKUP_SUFFIX)
                else:
                    success, msg, fix_source = apply_rule_fix(issue, dry_run=(fix_mode == "dry_run"), backup_suffix=BACKUP_SUFFIX)

                _log_event({
                    "action": "fix_attempt",
                    "issue": issue,
                    "success": success,
                    "message": msg,
                    "mode": fix_mode,
                    "fix_source": fix_source,
                })
                if success:
                    fixes_applied += 1
                    if fix_source == "llm":
                        llm_fixes += 1
                else:
                    fixes_failed += 1

    # 4. 更新状态
    state["scan_count"] += 1
    state["issues_found_total"] += len(all_issues)
    state["fixes_applied_total"] += fixes_applied
    state["fixes_failed_total"] += fixes_failed
    state["llm_fixes_total"] = state.get("llm_fixes_total", 0) + llm_fixes
    state["protected_skips"] += protected_skips
    state["last_scan"] = datetime.now().isoformat()
    state_mgr.save()

    # 5. 输出报告
    severity_counts = {}
    for issue in all_issues:
        sev = issue.get("severity", "unknown")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    print(f"[META] Scan complete: {len(all_issues)} issues found")
    print(f"  Severity: {severity_counts}")
    print(f"  Fixes applied: {fixes_applied}")
    print(f"  LLM fixes: {llm_fixes}")
    print(f"  Fixes failed: {fixes_failed}")
    print(f"  Protected skips: {protected_skips}")

    return {
        "issues": all_issues,
        "severity_counts": severity_counts,
        "fixes_applied": fixes_applied,
        "llm_fixes": llm_fixes,
        "fixes_failed": fixes_failed,
        "protected_skips": protected_skips,
        "scan_time": datetime.now().isoformat(),
    }


def status():
    """查看元认知指挥官状态"""
    state_mgr = StateManager(META_LOG_DIR, META_STATE_FILE)
    state = state_mgr.data
    print("=== Meta Commander Status ===")
    print(f"  Total scans: {state['scan_count']}")
    print(f"  Issues found: {state['issues_found_total']}")
    print(f"  Fixes applied: {state['fixes_applied_total']}")
    print(f"  LLM fixes: {state.get('llm_fixes_total', 0)}")
    print(f"  Fixes failed: {state['fixes_failed_total']}")
    print(f"  Protected skips: {state['protected_skips']}")
    print(f"  Last scan: {state.get('last_scan')}")

    if os.path.exists(META_FIX_LOG):
        with open(META_FIX_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()
        recent = lines[-5:] if lines else []
        if recent:
            print(f"  Recent fixes ({len(recent)}):")
            for line in recent:
                event = json.loads(line)
                print(f"    [{event.get('action', '?')}] {event.get('message', '')}")


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Meta Commander - Self-monitoring and self-healing for Brain cluster")
    parser.add_argument("--scan", action="store_true", help="Run full scan (dry-run mode)")
    parser.add_argument("--fix", action="store_true", help="Run scan and apply safe fixes")
    parser.add_argument("--llm-fix", action="store_true", help="Use LLM API for intelligent fixes")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--rollback", type=str, help="Rollback fixes for a file")
    args = parser.parse_args()

    if args.scan:
        run_full_scan(fix_mode="dry_run")
    elif args.fix:
        confirm = input("This will modify source files. Are you sure? (yes/no): ")
        if confirm.lower() == "yes":
            run_full_scan(fix_mode="safe", use_llm=args.llm_fix)
        else:
            print("Aborted.")
    elif args.status:
        status()
    elif args.rollback:
        if rollback_fix(args.rollback, backup_suffix=BACKUP_SUFFIX):
            print(f"Rolled back: {args.rollback}")
        else:
            print(f"No backup found for: {args.rollback}")
    else:
        parser.print_help()
