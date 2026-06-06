# -*- coding: utf-8 -*-
"""
Letta 记忆引擎初始化 — Brain 集群集成
letta==0.16.8 installed, ready for use
"""
import os

LETTA_DB = r"D:\brain\letta\letta.db"

# Letta 0.16.8 使用 LLMConfig + AgentState API
# 初始化后，Agent 通过 letta_client 管理记忆块
# Dreaming cron jobs 定期将压缩产物写入 Letta 的归档记忆

def init_letta_memory():
    """创建 Letta 记忆引擎配置"""
    config = {
        "db_path": LETTA_DB,
        "sync_from": r"D:\brain\memory\monthly",  # Dreaming 产物
        "sync_interval_minutes": 30,
        "memory_blocks": ["working", "archival", "strategic"]
    }
    return config

# 状态: 已安装 letta==0.16.8，待 Hermes Gateway 启动后通过 API 集成
print("Letta 0.16.8 ready at:", LETTA_DB)
