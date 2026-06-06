# -*- coding: utf-8 -*-
"""
记忆桥接引擎 — 串联 kanban.db → Letta → Dreaming → 长期智慧
每次Dreaming cron触发时自动调用
"""
import sqlite3
import json
import os
from datetime import datetime, timedelta

KANBAN_DB = r"D:\brain\output\memory\kanban.db"
MEMORY_DAILY = r"D:\brain\output\memory\daily"
MEMORY_WEEKLY = r"D:\brain\output\memory\weekly"
MEMORY_MONTHLY = r"D:\brain\output\memory\monthly"
LETTA_DB = r"D:\brain\letta\letta.db"

def sync_kanban_to_memory():
    """从kanban.db提取最近的task_events，写入每日记忆目录"""
    conn = sqlite3.connect(KANBAN_DB)
    cursor = conn.cursor()
    
    # 获取最近4小时的task_events
    cutoff = (datetime.now() - timedelta(hours=4)).isoformat()
    
    try:
        cursor.execute("""
            SELECT task_id, event_type, old_status, new_status, timestamp, metadata
            FROM task_events 
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        """, (cutoff,))
        events = cursor.fetchall()
    except sqlite3.OperationalError:
        # 表结构可能不同，尝试简化查询
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]
        events = [("tables_found", str(tables), "", "", datetime.now().isoformat(), "{}")]
    finally:
        conn.close()
    
    # 写入daily日志
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = os.path.join(MEMORY_DAILY, f"{today}.json")
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "events_count": len(events),
        "events": [{"task_id": str(e[0]), "type": str(e[1]), "old": str(e[2]), 
                     "new": str(e[3]), "time": str(e[4]), "meta": str(e[5])} 
                    for e in events[:100]]  # 最多100条
    }
    
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_entry, f, ensure_ascii=False, indent=2)
    
    return len(events)

def sync_to_letta(summary_text, stage="short_term"):
    """将Dreaming压缩产物同步到Letta归档记忆"""
    letta_entry = {
        "stage": stage,
        "timestamp": datetime.now().isoformat(),
        "summary": summary_text,
        "source": f"D:\\brain\\output\\memory\\{stage}\\"
    }
    
    letta_log = os.path.join(r"D:\brain\letta", f"sync_{stage}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(letta_log, "w", encoding="utf-8") as f:
        json.dump(letta_entry, f, ensure_ascii=False, indent=2)
    
    return letta_log

if __name__ == "__main__":
    count = sync_kanban_to_memory()
    print(f"Memory bridge: synced {count} events from kanban.db")
    if count > 0:
        sync_to_letta(f"Auto-synced {count} task events", "short_term")
        print("Letta sync: done")
