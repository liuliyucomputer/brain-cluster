# -*- coding: utf-8 -*-
"""
Brain 集群 — 记忆引擎 (Letta-compatible)
轻量级内嵌实现：Agent 可以调入/调出记忆块，自动版本管理
"""
import os, json, sqlite3
from datetime import datetime

MEMORY_DB = r"D:\brain\output\memory\memory_blocks.db"

def init():
    """初始化记忆数据库"""
    conn = sqlite3.connect(MEMORY_DB)
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
    conn.commit()
    conn.close()

def write_block(agent, label, content):
    """写入记忆块 (Agent 调用)"""
    init()
    conn = sqlite3.connect(MEMORY_DB)
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
    conn.close()
    return version

def read_block(agent, label):
    """读取记忆块"""
    init()
    conn = sqlite3.connect(MEMORY_DB)
    row = conn.execute(
        "SELECT content, version, updated_at FROM blocks WHERE id=?",
        (f"{agent}:{label}",)
    ).fetchone()
    conn.close()
    if row:
        return {"content": row[0], "version": row[1], "updated": row[2]}
    return None

def list_blocks(agent=None):
    """列出所有/指定Agent的记忆块"""
    init()
    conn = sqlite3.connect(MEMORY_DB)
    if agent:
        rows = conn.execute("SELECT label, version, updated_at FROM blocks WHERE agent=?", (agent,)).fetchall()
    else:
        rows = conn.execute("SELECT agent, label, version, updated_at FROM blocks").fetchall()
    conn.close()
    return [{"agent": r[0] if len(r)>3 else agent, "label": r[-3] if len(r)>3 else r[0], 
             "version": r[-2], "updated": r[-1]} for r in rows]

def delete_block(agent, label):
    """删除记忆块"""
    init()
    conn = sqlite3.connect(MEMORY_DB)
    conn.execute("DELETE FROM blocks WHERE id=?", (f"{agent}:{label}",))
    conn.commit()
    conn.close()

# 初始化
init()
print(f"Memory engine ready: {MEMORY_DB}")
print(f"Blocks: {len(list_blocks())}")
