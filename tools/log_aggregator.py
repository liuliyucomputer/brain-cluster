# -*- coding: utf-8 -*-
"""
Brain 集群 — 日志聚合引擎
从各服务真实日志位置采集 → 统一写入 output/logs/
"""
import os, sys, time, glob, shutil
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import LOGS_DIR

LOG_ROOT = LOGS_DIR

REAL_LOGS = {
    "gateway": {
        "agent":   r"C:\Users\Administrator\.hermes\logs\agent.log",
        "errors":  r"C:\Users\Administrator\.hermes\logs\errors.log",
        "exit":    r"C:\Users\Administrator\.hermes\logs\gateway-exit-diag.log",
    },
    "grafana": {
        "main":    r"D:\brain\grafana\grafana-v11.6.0\data\log\grafana.log",
    },
    "agents": {
        "executor-a":  r"C:\Users\Administrator\.hermes\profiles\executor-a\logs\agent.log",
        "executor-b":  r"C:\Users\Administrator\.hermes\profiles\executor-b\logs\agent.log",
        "executor-c":  r"C:\Users\Administrator\.hermes\profiles\executor-c\logs\agent.log",
        "strategist":  r"C:\Users\Administrator\.hermes\profiles\strategist\logs\agent.log",
        "monitor":     r"C:\Users\Administrator\.hermes\profiles\monitor\logs\agent.log",
        "reviewer-strict":   r"C:\Users\Administrator\.hermes\profiles\reviewer-strict\logs\agent.log",
        "reviewer-creative": r"C:\Users\Administrator\.hermes\profiles\reviewer-creative\logs\agent.log",
        "arbiter":     r"C:\Users\Administrator\.hermes\profiles\arbiter\logs\agent.log",
        "learner":     r"C:\Users\Administrator\.hermes\profiles\learner\logs\agent.log",
    },
    "staroffice": {
        "app": r"D:\brain\staroffice-ui\backend\app.log",
    }
}

def init_log_dirs():
    """确保所有日志目录存在"""
    for service in REAL_LOGS:
        os.makedirs(os.path.join(LOG_ROOT, service), exist_ok=True)

def sync_logs_once():
    """一次性采集: 把各服务原生日志复制到 D:\brain\log\ """
    today = datetime.now().strftime("%Y-%m-%d")
    synced = 0

    for service, sources in REAL_LOGS.items():
        dest_dir = os.path.join(LOG_ROOT, service)
        for name, src_path in sources.items():
            if not os.path.exists(src_path):
                continue
            dest_file = os.path.join(dest_dir, f"{today}_{name}.log")
            try:
                shutil.copy2(src_path, dest_file)
                synced += 1
            except Exception as e:
                print(f"  skip {name}: {e}")
    return synced

def tail_all(service=None, lines=30):
    """查看今日所有/指定服务日志"""
    today = datetime.now().strftime("%Y-%m-%d")
    services = [service] if service else list(REAL_LOGS.keys())

    for svc in services:
        svc_dir = os.path.join(LOG_ROOT, svc)
        files = glob.glob(os.path.join(svc_dir, f"{today}_*.log"))
        if not files:
            print(f"\n--- {svc}: no logs today ---")
            continue
        
        print(f"\n{'='*60}")
        print(f"  {svc}")
        print(f"{'='*60}")
        for fpath in sorted(files):
            name = os.path.basename(fpath).replace(f"{today}_", "").replace(".log", "")
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                content = f.readlines()
            if content:
                print(f"\n  [{name}] ({len(content)} lines)")
                for line in content[-lines:]:
                    print(f"    {line.rstrip()}")
            else:
                print(f"\n  [{name}] empty")

def scan_errors(service=None):
    """扫描错误"""
    today = datetime.now().strftime("%Y-%m-%d")
    services = [service] if service else list(REAL_LOGS.keys())
    found = 0

    for svc in services:
        for fpath in glob.glob(os.path.join(LOG_ROOT, svc, f"{today}_*.log")):
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if any(kw in line.upper() for kw in ["ERROR", "FAIL", "CRASH", "401", "403", "500"]):
                        name = os.path.basename(fpath).replace(f"{today}_", "").replace(".log", "")
                        print(f"[{svc}/{name}] {line.rstrip()}")
                        found += 1
    if not found:
        print("No errors found.")
    return found

def watch_realtime(service=None, interval=5):
    """实时监控日志变化"""
    print(f"Watching logs every {interval}s... (Ctrl+C to stop)")
    seen = {}
    try:
        while True:
            sync_logs_once()
            for svc in list(REAL_LOGS.keys()):
                if service and svc != service:
                    continue
                for name, src in REAL_LOGS[svc].items():
                    if not os.path.exists(src):
                        continue
                    size = os.path.getsize(src)
                    key = f"{svc}/{name}"
                    if key not in seen:
                        seen[key] = 0
                    if size > seen[key]:
                        with open(src, "r", encoding="utf-8", errors="replace") as f:
                            f.seek(seen[key])
                            new_lines = f.readlines()
                        for line in new_lines:
                            ts = datetime.now().strftime("%H:%M:%S")
                            print(f"[{ts}] [{svc}] {line.rstrip()}")
                        seen[key] = size
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Brain 日志聚合器")
    p.add_argument("action", nargs="?", default="sync",
                   choices=["sync", "tail", "errors", "watch"])
    p.add_argument("-s", "--service", help="服务名: gateway/staroffice/grafana/agents")
    p.add_argument("-n", "--lines", type=int, default=30)
    p.add_argument("-i", "--interval", type=int, default=5, help="watch间隔秒数")
    args = p.parse_args()

    init_log_dirs()

    if args.action == "sync":
        n = sync_logs_once()
        print(f"Synced {n} log files to {LOG_ROOT}")
    elif args.action == "tail":
        tail_all(args.service, args.lines)
    elif args.action == "errors":
        scan_errors(args.service)
    elif args.action == "watch":
        watch_realtime(args.service, args.interval)
