# -*- coding: utf-8 -*-
"""
Brain 集群 — 至高指挥官 (Supreme Commander) v3.1
职责: 项目全局掌控者，具备自主决策、智能修复、全局协调能力。
      无需人工触发，自主运行，主动发现问题并修复，协调所有 Agent 工作。
版本: v3.1 | 2026-06-09
"""
import os
import sys
import threading
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import KANBAN_DB, LOGS_DIR, TOOLS_DIR, PROJECT_ROOT
from commander_core import (
    StateManager,
    ScanEngine,
    LLMInterface,
    RISK_LOW,
    RISK_MEDIUM,
    RISK_HIGH,
    RISK_CRITICAL,
    _check_port,
    verify_fix,
    apply_rule_fix,
    apply_llm_fix,
    rollback_fix,
)

# ── 配置 ──
COMMANDER_LOG_DIR = os.path.join(LOGS_DIR, "supreme_commander")
STATE_FILE = os.path.join(COMMANDER_LOG_DIR, "commander_state.json")
DECISION_LOG = os.path.join(COMMANDER_LOG_DIR, "decisions.jsonl")
ERROR_LOG = os.path.join(COMMANDER_LOG_DIR, "errors.jsonl")

SCAN_INTERVAL = 300
CRISIS_SCAN_INTERVAL = 30
HEALTH_CHECK_INTERVAL = 60

BACKUP_SUFFIX = ".sc_backup"


# ═══════════════════════════════════════════════
#  决策引擎
# ═══════════════════════════════════════════════

class DecisionEngine:
    """决策引擎：评估风险，决定行动"""

    def __init__(self, state, llm):
        self.state = state
        self.llm = llm

    def decide(self, issue):
        """对单个问题做出决策"""
        risk = issue.get("risk", RISK_MEDIUM)

        if risk == RISK_LOW:
            return self._handle_low_risk(issue)
        elif risk == RISK_MEDIUM:
            return self._handle_medium_risk(issue)
        elif risk == RISK_HIGH:
            return self._handle_high_risk(issue)
        elif risk == RISK_CRITICAL:
            return self._handle_critical(issue)

    def _handle_low_risk(self, issue):
        """低风险：自动修复"""
        if issue.get("auto_fix") and issue.get("fix"):
            success, msg, fix_source = apply_rule_fix(issue, dry_run=False, backup_suffix=BACKUP_SUFFIX)
            return {
                "action": "auto_fix",
                "success": success,
                "issue": issue,
                "need_confirm": False,
                "message": msg,
            }
        return {"action": "log", "issue": issue, "need_confirm": False}

    def _handle_medium_risk(self, issue):
        """中风险：尝试 LLM 修复，记录日志"""
        if issue.get("auto_fix"):
            success, msg, fix_source = apply_llm_fix(issue, self.llm, dry_run=False, backup_suffix=BACKUP_SUFFIX)
            if success:
                return {
                    "action": "llm_fix",
                    "success": True,
                    "issue": issue,
                    "need_confirm": False,
                    "message": msg,
                }

        return {
            "action": "queue_for_review",
            "issue": issue,
            "need_confirm": False,
        }

    def _handle_high_risk(self, issue):
        """高风险：通知人类，等待确认"""
        self._notify_human(issue)
        return {
            "action": "notify_human",
            "issue": issue,
            "need_confirm": True,
        }

    def _handle_critical(self, issue):
        """危急：立即自动修复 + 通知人类"""
        if issue.get("auto_fix"):
            success, msg, fix_source = apply_rule_fix(issue, dry_run=False, backup_suffix=BACKUP_SUFFIX)
            self._notify_human(issue, emergency=True)
            return {
                "action": "emergency_fix",
                "success": success,
                "issue": issue,
                "need_confirm": False,
                "message": msg,
            }

        self._notify_human(issue, emergency=True)
        return {
            "action": "emergency_notify",
            "issue": issue,
            "need_confirm": True,
        }

    def _notify_human(self, issue, emergency=False):
        """通知人类（写入通知文件，可被其他系统读取）"""
        notify_file = os.path.join(COMMANDER_LOG_DIR, "pending_confirmations.jsonl")
        notification = {
            "type": "human_confirmation_required",
            "emergency": emergency,
            "issue": issue,
            "ts": datetime.now().isoformat(),
        }
        with open(notify_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(notification, ensure_ascii=False) + "\n")


# ═══════════════════════════════════════════════
#  至高指挥官主类
# ═══════════════════════════════════════════════

class SupremeCommander:
    """至高指挥官：全局掌控"""

    def __init__(self):
        self.state = StateManager(COMMANDER_LOG_DIR, STATE_FILE, DECISION_LOG, ERROR_LOG)
        self.llm = LLMInterface()
        self.scanner = ScanEngine(self.state)
        self.decision = DecisionEngine(self.state, self.llm)
        self.running = False
        self.crisis_mode = False

    def start(self, background=False):
        """启动指挥官（守护模式）

        Args:
            background: True 时作为后台线程运行，不阻塞主线程
        """
        self.running = True
        self.state.data["status"] = "active"
        self.state.save()

        print("=" * 60)
        print("  Supreme Commander v3.1 启动")
        print("  模式: 自主运行 | 智能决策 | 全局协调")
        print(f"  扫描间隔: {SCAN_INTERVAL}s | 危机模式: {CRISIS_SCAN_INTERVAL}s")
        print("=" * 60)

        threads = [
            threading.Thread(target=self._scan_loop, name="Scanner"),
            threading.Thread(target=self._health_loop, name="HealthCheck"),
            threading.Thread(target=self._coordination_loop, name="Coordinator"),
        ]

        for t in threads:
            t.daemon = True
            t.start()

        if background:
            print("[SC] 后台模式已启动，主线程返回")
            return

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """停止指挥官"""
        self.running = False
        self.state.data["status"] = "standby"
        self.state.save()
        print("\n[SC] 指挥官已停止")

    def _scan_loop(self):
        """扫描循环"""
        time.sleep(10)

        while self.running:
            interval = CRISIS_SCAN_INTERVAL if self.crisis_mode else SCAN_INTERVAL

            print(f"\n[SC] 开始第 {self.state.data['scan_count'] + 1} 次扫描...")
            issues = self.scanner.scan_all(include_services=True)

            self.state.data["scan_count"] += 1
            self.state.data["last_scan"] = datetime.now().isoformat()

            critical_count = sum(1 for i in issues if i.get("risk") == RISK_CRITICAL)
            if critical_count > 0:
                self.crisis_mode = True
                self.state.data["crisis_count"] += 1
                print(f"[SC] ⚠️  发现 {critical_count} 个危急问题，进入危机模式")
            else:
                self.crisis_mode = False

            for issue in issues:
                result = self.decision.decide(issue)
                self.state.log_decision(result)

                if result.get("success"):
                    self.state.data["fixes_auto"] += 1
                    print(f"[SC] ✅ 自动修复: {issue.get('type')} in {os.path.basename(issue.get('file', ''))}")
                elif result.get("need_confirm"):
                    self.state.data["fixes_manual"] += 1
                    print(f"[SC] ⏸️  等待确认: {issue.get('type')} - {issue.get('message', '')}")

            self.state.save()
            print(f"[SC] 扫描完成: {len(issues)} 问题，{self.state.data['fixes_auto']} 自动修复")

            for _ in range(interval):
                if not self.running:
                    break
                time.sleep(1)

    def _health_loop(self):
        """健康检查循环"""
        while self.running:
            services = {
                "hermes_gateway": 18789,
                "staroffice_ui": 18791,
                "grafana": 3001,
            }

            health = {}
            for name, port in services.items():
                health[name] = _check_port(port)

            self.state.data["agent_health"] = health

            for name, is_up in health.items():
                if not is_up:
                    print(f"[SC] ⚠️  服务 {name} 宕机，尝试重启...")
                    self._try_restart_service(name)

            time.sleep(HEALTH_CHECK_INTERVAL)

    def _coordination_loop(self):
        """协调循环：检查待处理任务，协调 Agent 工作"""
        while self.running:
            try:
                if os.path.exists(KANBAN_DB):
                    import sqlite3
                    conn = sqlite3.connect(KANBAN_DB, timeout=3)
                    cursor = conn.cursor()

                    cursor.execute(
                        "SELECT id, title, assignee FROM tasks WHERE status='running' AND updated_at < ?",
                        (int(time.time()) - 600,)
                    )
                    stuck_tasks = cursor.fetchall()

                    for task in stuck_tasks:
                        print(f"[SC] 🔄 协调: 任务 {task[0]} 卡住，尝试 reclaim...")
                        self._reclaim_task(task[0])

                    conn.close()
            except Exception as e:
                self.state.log_error({"action": "coordination_error", "error": str(e)})

            time.sleep(120)

    def _try_restart_service(self, name):
        """尝试重启服务"""
        try:
            if name == "hermes_gateway":
                subprocess.run(["hermes", "gateway", "start"], capture_output=True, timeout=30)
            print(f"[SC] ✅ 服务 {name} 重启命令已发送")
        except Exception as e:
            self.state.log_error({"action": "restart_failed", "service": name, "error": str(e)})

    def _reclaim_task(self, task_id):
        """reclaim 卡住的任务"""
        try:
            env = {**os.environ, "GATEWAY_ALLOW_ALL_USERS": "true"}
            result = subprocess.run(
                ["hermes", "kanban", "reclaim", str(task_id), "--reason", "supreme_commander_stuck"],
                capture_output=True,
                text=True,
                env=env,
                timeout=20,
            )
            return result.returncode == 0
        except Exception as e:
            self.state.log_error({"action": "reclaim_failed", "task_id": task_id, "error": str(e)})
            return False

    def get_status(self):
        """获取指挥官状态"""
        return {
            "status": self.state.data.get("status", "unknown"),
            "scan_count": self.state.data.get("scan_count", 0),
            "fixes_auto": self.state.data.get("fixes_auto", 0),
            "fixes_manual": self.state.data.get("fixes_manual", 0),
            "crisis_count": self.state.data.get("crisis_count", 0),
            "crisis_mode": self.crisis_mode,
            "last_scan": self.state.data.get("last_scan"),
            "agent_health": self.state.data.get("agent_health", {}),
        }


# ═══════════════════════════════════════════════
#  命令行接口
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Supreme Commander - Brain Cluster Global Controller")
    parser.add_argument("--start", action="store_true", help="启动守护模式")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--stop", action="store_true", help="停止指挥官")
    parser.add_argument("--scan-once", action="store_true", help="单次扫描")
    args = parser.parse_args()

    if args.start:
        commander = SupremeCommander()
        commander.start()
    elif args.status:
        state = StateManager(COMMANDER_LOG_DIR, STATE_FILE, DECISION_LOG, ERROR_LOG)
        print("=== Supreme Commander Status ===")
        print(f"  状态: {state.data.get('status', 'unknown')}")
        print(f"  扫描次数: {state.data.get('scan_count', 0)}")
        print(f"  自动修复: {state.data.get('fixes_auto', 0)}")
        print(f"  人工确认: {state.data.get('fixes_manual', 0)}")
        print(f"  危机次数: {state.data.get('crisis_count', 0)}")
        print(f"  最后扫描: {state.data.get('last_scan')}")
        print(f"  Agent 健康: {state.data.get('agent_health', {})}")
    elif args.scan_once:
        commander = SupremeCommander()
        commander.state.data["status"] = "active"
        commander.state.save()
        issues = commander.scanner.scan_all(include_services=True)
        commander.state.data["scan_count"] += 1
        commander.state.data["last_scan"] = datetime.now().isoformat()
        commander.state.save()
        print(f"扫描完成: 发现 {len(issues)} 个问题")
        for issue in issues:
            print(f"  [{issue.get('risk', '?')}] {issue.get('type')}: {issue.get('message', '')}")
    else:
        parser.print_help()
