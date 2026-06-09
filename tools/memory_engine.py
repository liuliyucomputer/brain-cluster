# -*- coding: utf-8 -*-
"""
Brain 集群 — 记忆引擎 v2.2 (纯记忆服务)
职责: 只接收事件、存储摘要、提供检索，不参与调度判定。
版本: v2.2 | 2026-06-08 重构
"""
import os
import json
import sqlite3
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import MEMORY_BLOCKS_DB, LOGS_DIR

MEMORY_DB = MEMORY_BLOCKS_DB

# 数据分层配置
HOT_DAYS = 7      # 热数据：最近 7 天，SQLite
WARM_DAYS = 30    # 温数据：最近 30 天，SQLite
COLD_DIR = os.path.join(os.path.dirname(MEMORY_DB), "cold_storage")
os.makedirs(COLD_DIR, exist_ok=True)


def init():
    """初始化记忆数据库（热数据层）"""
    conn = sqlite3.connect(MEMORY_DB)
    try:
        # 记忆块表（Agent 产出摘要）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS blocks (
                id TEXT PRIMARY KEY,
                agent TEXT,
                label TEXT,
                content TEXT,
                created_at TEXT,
                updated_at TEXT,
                version INTEGER DEFAULT 1
            )
        """)
        # 事件表（消费 task_events）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                event_type TEXT,
                payload TEXT,
                created_at INTEGER,
                archived INTEGER DEFAULT 0
            )
        """)
        # 索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at)")
        conn.commit()
    finally:
        conn.close()


# ========== 记忆块接口 ==========

def write_block(agent, label, content):
    """写入记忆块 (Agent 调用)"""
    conn = sqlite3.connect(MEMORY_DB)
    try:
        now = datetime.now().isoformat()
        block_id = f"{agent}:{label}"

        existing = conn.execute("SELECT version FROM blocks WHERE id=?", (block_id,)).fetchone()
        if existing:
            version = existing[0] + 1
            conn.execute(
                "UPDATE blocks SET content=?, updated_at=?, version=? WHERE id=?",
                (content, now, version, block_id)
            )
        else:
            version = 1
            conn.execute(
                "INSERT INTO blocks VALUES (?,?,?,?,?,?,?)",
                (block_id, agent, label, content, now, now, version)
            )
        conn.commit()
        return version
    finally:
        conn.close()


def read_block(agent, label):
    """读取记忆块"""
    conn = sqlite3.connect(MEMORY_DB)
    try:
        row = conn.execute(
            "SELECT content, version, updated_at FROM blocks WHERE id=?",
            (f"{agent}:{label}",)
        ).fetchone()
        if row:
            return {"content": row[0], "version": row[1], "updated": row[2]}
        return None
    finally:
        conn.close()


def list_blocks(agent=None):
    """列出所有/指定Agent的记忆块"""
    conn = sqlite3.connect(MEMORY_DB)
    try:
        if agent:
            rows = conn.execute(
                "SELECT label, version, updated_at FROM blocks WHERE agent=?", (agent,)
            ).fetchall()
            return [{"agent": agent, "label": r[0], "version": r[1], "updated": r[2]} for r in rows]
        else:
            rows = conn.execute("SELECT agent, label, version, updated_at FROM blocks").fetchall()
            return [{"agent": r[0], "label": r[1], "version": r[2], "updated": r[3]} for r in rows]
    finally:
        conn.close()


def delete_block(agent, label):
    """删除记忆块"""
    conn = sqlite3.connect(MEMORY_DB)
    try:
        conn.execute("DELETE FROM blocks WHERE id=?", (f"{agent}:{label}",))
        conn.commit()
    finally:
        conn.close()


# ========== 事件接口（只读消费，不写调度） ==========

def append_event(task_id, event_type, payload):
    """追加事件（由外部系统调用，如 Hermes task_events）"""
    conn = sqlite3.connect(MEMORY_DB)
    try:
        conn.execute(
            "INSERT INTO events (task_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
            (task_id, event_type, json.dumps(payload, ensure_ascii=False), int(datetime.now().timestamp()))
        )
        conn.commit()
    finally:
        conn.close()


def query_events(task_id=None, event_type=None, days=7, limit=100):
    """查询事件（只读）"""
    conn = sqlite3.connect(MEMORY_DB)
    try:
        since = int((datetime.now() - timedelta(days=days)).timestamp())
        conditions = ["created_at >= ?"]
        params = [since]

        if task_id:
            conditions.append("task_id = ?")
            params.append(task_id)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)

        sql = f"SELECT * FROM events WHERE {' AND '.join(conditions)} ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [{
            "id": r[0],
            "task_id": r[1],
            "event_type": r[2],
            "payload": json.loads(r[3]) if r[3] else None,
            "created_at": r[4],
        } for r in rows]
    finally:
        conn.close()


def get_event_summary(days=7):
    """获取事件统计摘要"""
    conn = sqlite3.connect(MEMORY_DB)
    try:
        since = int((datetime.now() - timedelta(days=days)).timestamp())
        rows = conn.execute(
            "SELECT event_type, COUNT(*) FROM events WHERE created_at >= ? GROUP BY event_type",
            (since,)
        ).fetchall()
        return {r[0]: r[1] for r in rows}
    finally:
        conn.close()


# ========== 归档接口 ==========

def archive_old_events(days=7):
    """
    归档超过 days 天的事件到冷存储。
    返回归档的文件路径。
    """
    conn = sqlite3.connect(MEMORY_DB)
    try:
        cutoff = int((datetime.now() - timedelta(days=days)).timestamp())
        rows = conn.execute(
            "SELECT * FROM events WHERE created_at < ? AND archived = 0",
            (cutoff,)
        ).fetchall()

        if not rows:
            return None

        # 按日期分组归档
        events_by_date = {}
        for r in rows:
            date_str = datetime.fromtimestamp(r[4]).strftime("%Y-%m-%d")
            if date_str not in events_by_date:
                events_by_date[date_str] = []
            events_by_date[date_str].append({
                "id": r[0],
                "task_id": r[1],
                "event_type": r[2],
                "payload": json.loads(r[3]) if r[3] else None,
                "created_at": r[4],
            })

        archived_files = []
        for date_str, events in events_by_date.items():
            filepath = os.path.join(COLD_DIR, f"events_{date_str}.jsonl")
            with open(filepath, "a", encoding="utf-8") as f:
                for event in events:
                    f.write(json.dumps(event, ensure_ascii=False) + "\n")
            archived_files.append(filepath)

        # 标记已归档
        conn.execute("UPDATE events SET archived = 1 WHERE created_at < ?", (cutoff,))
        conn.commit()
        return archived_files
    finally:
        conn.close()


def cleanup_archived_events(days=30):
    """
    清理已归档超过 days 天的事件（从热库删除）。
    注意：数据已保存在 cold_storage 的 JSONL 文件中。
    """
    conn = sqlite3.connect(MEMORY_DB)
    try:
        cutoff = int((datetime.now() - timedelta(days=days)).timestamp())
        cursor = conn.execute("DELETE FROM events WHERE created_at < ? AND archived = 1", (cutoff,))
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


# ========== 初始化 ==========
init()
if __name__ == "__main__":
    print(f"Memory engine v2.2 ready: {MEMORY_DB}")
    print(f"Blocks: {len(list_blocks())}")
    print(f"Events (7d): {sum(get_event_summary(7).values())}")
