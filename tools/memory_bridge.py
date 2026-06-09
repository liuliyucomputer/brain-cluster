# -*- coding: utf-8 -*-
"""
记忆桥接引擎 — 串联 kanban.db → Letta → Dreaming → 长期智慧
每次Dreaming cron触发时自动调用
"""
import sqlite3, json, os, sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import KANBAN_DB, MEMORY_DAILY, MEMORY_WEEKLY, MEMORY_MONTHLY, MEMORY_DIR, LETTA_DIR

def sync_kanban_to_memory():
    """从kanban.db提取最近的task_events，写入每日记忆目录"""
    conn = sqlite3.connect(KANBAN_DB)
    cursor = conn.cursor()
    
    # 获取最近4小时的task_events
    # task_events 真实 schema: id, task_id, run_id, kind, payload, created_at
    cutoff_ts = int((datetime.now() - timedelta(hours=4)).timestamp())
    
    try:
        cursor.execute("""
            SELECT task_id, kind, run_id, payload, created_at
            FROM task_events 
            WHERE created_at > ?
            ORDER BY created_at DESC
            LIMIT 100
        """, (cutoff_ts,))
        events = cursor.fetchall()
    except sqlite3.OperationalError:
        # task_events 表不存在 — 不构造虚假事件，返回 0
        conn.close()
        return 0
    finally:
        conn.close()
    
    # 写入daily日志 (JSON Lines 格式: 每行一条独立记录，支持追加)
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = os.path.join(MEMORY_DAILY, f"{today}.jsonl")
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "events_count": len(events),
        "events": [{"task_id": str(e[0]), "kind": str(e[1]), "run_id": str(e[2]),
                     "payload": str(e[3]), "created_at": str(e[4])}
                    for e in events]
    }
    
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    return len(events)

def sync_to_letta(summary_text, stage="short_term"):
    """将Dreaming压缩产物同步到Letta归档记忆"""
    stage_dir = os.path.join(MEMORY_DIR, stage)
    letta_entry = {
        "stage": stage,
        "timestamp": datetime.now().isoformat(),
        "summary": summary_text,
        "source": stage_dir + os.sep
    }
    
    letta_log = os.path.join(LETTA_DIR, f"sync_{stage}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(letta_log, "w", encoding="utf-8") as f:
        json.dump(letta_entry, f, ensure_ascii=False, indent=2)
    
    return letta_log

if __name__ == "__main__":
    count = sync_kanban_to_memory()
    print(f"Memory bridge: synced {count} events from kanban.db")
    if count > 0:
        sync_to_letta(f"Auto-synced {count} task events", "short_term")
        print("Letta sync: done")
