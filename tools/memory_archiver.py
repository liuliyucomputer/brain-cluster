# -*- coding: utf-8 -*-
"""
Brain 集群 — 记忆归档器 v2.2
职责: 负责冷热分层、定时归档、压缩清理。
      由 cron/scheduler 调用，不直接参与业务逻辑。
版本: v2.2 | 2026-06-08
"""
import json
import os
import sys
import time
import gzip
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memory_engine import (
    archive_old_events,
    cleanup_archived_events,
    get_event_summary,
    MEMORY_DB,
    COLD_DIR,
)

# 默认保留策略
DEFAULT_POLICY = {
    "hot_days": 7,      # 热数据保留天数（SQLite）
    "warm_days": 30,    # 温数据保留天数（SQLite 中已归档）
    "cold_days": 365,   # 冷数据保留天数（JSONL 文件）
    "compress_after_days": 30,  # 超过此天数的 JSONL 压缩为 .gz
}

POLICY_FILE = os.path.join(os.path.dirname(MEMORY_DB), "archive_policy.json")


def _load_policy():
    """加载归档策略"""
    if os.path.exists(POLICY_FILE):
        with open(POLICY_FILE, "r", encoding="utf-8") as f:
            return {**DEFAULT_POLICY, **json.load(f)}
    return DEFAULT_POLICY.copy()


def _save_policy(policy):
    """保存归档策略"""
    with open(POLICY_FILE, "w", encoding="utf-8") as f:
        json.dump(policy, f, ensure_ascii=False, indent=2)


def run_daily_archive():
    """
    每日归档任务：
    1. 归档超过 hot_days 的事件到冷存储
    2. 清理超过 warm_days 的已归档事件
    3. 压缩超过 compress_after_days 的 JSONL 文件
    """
    policy = _load_policy()
    hot_days = policy.get("hot_days", 7)
    warm_days = policy.get("warm_days", 30)
    compress_after = policy.get("compress_after_days", 30)

    print(f"[{datetime.now().isoformat()}] Memory archiver started")
    print(f"  Policy: hot={hot_days}d, warm={warm_days}d, compress={compress_after}d")

    # 1. 归档旧事件
    archived_files = archive_old_events(days=hot_days)
    if archived_files:
        print(f"  Archived {len(archived_files)} files: {', '.join(archived_files)}")
    else:
        print("  No events to archive")

    # 2. 清理已归档事件
    cleaned_count = cleanup_archived_events(days=warm_days)
    print(f"  Cleaned {cleaned_count} archived events from hot DB")

    # 3. 压缩旧 JSONL
    compressed_count = compress_old_jsonl(days=compress_after)
    print(f"  Compressed {compressed_count} old JSONL files")

    # 4. 统计
    summary = get_event_summary(days=hot_days)
    total_events = sum(summary.values())
    print(f"  Current hot events: {total_events}")
    print(f"  Event types: {summary}")

    print(f"[{datetime.now().isoformat()}] Memory archiver done")
    return {
        "archived_files": archived_files or [],
        "cleaned_count": cleaned_count,
        "compressed_count": compressed_count,
        "hot_events": total_events,
    }


def compress_old_jsonl(days=30):
    """
    压缩超过 days 天的 JSONL 文件为 .gz。
    返回压缩的文件数量。
    """
    if not os.path.exists(COLD_DIR):
        return 0

    cutoff = datetime.now() - timedelta(days=days)
    compressed = 0

    for filename in os.listdir(COLD_DIR):
        if not filename.startswith("events_") or not filename.endswith(".jsonl"):
            continue

        # 提取日期
        try:
            date_str = filename.replace("events_", "").replace(".jsonl", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue

        if file_date < cutoff:
            filepath = os.path.join(COLD_DIR, filename)
            gz_path = filepath + ".gz"

            # 如果已压缩则跳过
            if os.path.exists(gz_path):
                continue

            with open(filepath, "rb") as f_in:
                with gzip.open(gz_path, "wb") as f_out:
                    f_out.write(f_in.read())

            # 验证压缩成功后删除原文件
            if os.path.exists(gz_path) and os.path.getsize(gz_path) > 0:
                os.remove(filepath)
                compressed += 1

    return compressed


def cleanup_old_cold_files(days=365):
    """
    删除超过 days 天的冷存储文件（包括 .jsonl 和 .gz）。
    返回删除的文件数量。
    """
    if not os.path.exists(COLD_DIR):
        return 0

    cutoff = datetime.now() - timedelta(days=days)
    deleted = 0

    for filename in os.listdir(COLD_DIR):
        if not filename.startswith("events_"):
            continue

        # 提取日期
        try:
            date_str = filename.replace("events_", "").replace(".jsonl", "").replace(".gz", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue

        if file_date < cutoff:
            filepath = os.path.join(COLD_DIR, filename)
            os.remove(filepath)
            deleted += 1

    return deleted


def get_storage_stats():
    """获取存储统计信息"""
    stats = {
        "hot_db_size_mb": 0,
        "cold_dir_size_mb": 0,
        "cold_files": 0,
        "compressed_files": 0,
        "policy": _load_policy(),
    }

    if os.path.exists(MEMORY_DB):
        stats["hot_db_size_mb"] = round(os.path.getsize(MEMORY_DB) / (1024 * 1024), 2)

    if os.path.exists(COLD_DIR):
        total_size = 0
        files = 0
        gz_files = 0
        for filename in os.listdir(COLD_DIR):
            filepath = os.path.join(COLD_DIR, filename)
            if os.path.isfile(filepath):
                total_size += os.path.getsize(filepath)
                files += 1
                if filename.endswith(".gz"):
                    gz_files += 1
        stats["cold_dir_size_mb"] = round(total_size / (1024 * 1024), 2)
        stats["cold_files"] = files
        stats["compressed_files"] = gz_files

    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Memory archiver for Brain cluster")
    parser.add_argument("--daily", action="store_true", help="Run daily archive cycle")
    parser.add_argument("--compress", action="store_true", help="Compress old JSONL files")
    parser.add_argument("--cleanup", action="store_true", help="Delete very old cold files")
    parser.add_argument("--stats", action="store_true", help="Show storage statistics")
    parser.add_argument("--policy", type=str, help="Set policy as JSON string")
    args = parser.parse_args()

    if args.policy:
        try:
            new_policy = json.loads(args.policy)
            policy = _load_policy()
            policy.update(new_policy)
            _save_policy(policy)
            print(f"Policy updated: {policy}")
        except json.JSONDecodeError:
            print("Invalid policy JSON")
            sys.exit(1)

    if args.daily:
        run_daily_archive()
    elif args.compress:
        count = compress_old_jsonl()
        print(f"Compressed {count} files")
    elif args.cleanup:
        policy = _load_policy()
        count = cleanup_old_cold_files(days=policy.get("cold_days", 365))
        print(f"Deleted {count} old cold files")
    elif args.stats:
        stats = get_storage_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        parser.print_help()
