# -*- coding: utf-8 -*-
"""
Brain 集群 — 日志系统
功能: 日志轮转、汇聚、查看、清除
"""
import os, sys, shutil, glob
from datetime import datetime, timedelta

LOG_ROOT = r"D:\brain\output\logs"

def write_log(service, level, message):
    """写入一条日志"""
    os.makedirs(os.path.join(LOG_ROOT, service), exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    logfile = os.path.join(LOG_ROOT, service, f"{today}.log")
    ts = datetime.now().strftime("%H:%M:%S")
    with open(logfile, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] [{level}] {message}\n")

def rotate_logs(max_days=30):
    """清理超过N天的日志"""
    cutoff = datetime.now() - timedelta(days=max_days)
    for service in os.listdir(LOG_ROOT):
        spath = os.path.join(LOG_ROOT, service)
        if not os.path.isdir(spath):
            continue
        for logfile in glob.glob(os.path.join(spath, "*.log")):
            try:
                fname = os.path.basename(logfile).replace(".log", "")
                fdate = datetime.strptime(fname, "%Y-%m-%d")
                if fdate < cutoff:
                    os.remove(logfile)
                    print(f"  purged: {logfile}")
            except ValueError:
                pass

def tail_logs(service=None, lines=20):
    """查看最近的日志"""
    if service:
        services = [service]
    else:
        services = [d for d in os.listdir(LOG_ROOT) if os.path.isdir(os.path.join(LOG_ROOT, d))]
    
    for svc in services:
        today = datetime.now().strftime("%Y-%m-%d")
        logfile = os.path.join(LOG_ROOT, svc, f"{today}.log")
        if os.path.exists(logfile):
            with open(logfile, "r", encoding="utf-8") as f:
                content = f.readlines()
            print(f"\n=== {svc} ({len(content)} lines) ===")
            for line in content[-lines:]:
                print(line.rstrip())
        else:
            print(f"\n=== {svc}: 今日无日志 ===")

def scan_errors(service=None):
    """扫描所有 ERROR 和 WARN 日志"""
    found = False
    services = [service] if service else [d for d in os.listdir(LOG_ROOT) if os.path.isdir(os.path.join(LOG_ROOT, d))]
    for svc in services:
        for logfile in glob.glob(os.path.join(LOG_ROOT, svc, "*.log")):
            with open(logfile, "r", encoding="utf-8") as f:
                for line in f:
                    if "ERROR" in line or "WARN" in line:
                        print(f"[{svc}] {line.rstrip()}")
                        found = True
    if not found:
        print("No errors found.")
    return found

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Brain 集群日志管理")
    p.add_argument("action", choices=["write", "tail", "errors", "rotate"], default="tail", nargs="?")
    p.add_argument("--service", "-s", help="服务名: gateway/staroffice/grafana/agents")
    p.add_argument("--level", "-l", default="INFO", choices=["INFO","WARN","ERROR","DEBUG"])
    p.add_argument("--message", "-m", help="日志内容")
    p.add_argument("--lines", "-n", type=int, default=20)
    args = p.parse_args()
    
    if args.action == "write":
        write_log(args.service or "system", args.level, args.message)
        print(f"logged: [{args.level}] {args.message}")
    elif args.action == "tail":
        tail_logs(args.service, args.lines)
    elif args.action == "errors":
        scan_errors(args.service)
    elif args.action == "rotate":
        rotate_logs()
        print("Log rotation complete.")
