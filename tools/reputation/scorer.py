# -*- coding: utf-8 -*-
"""
Agent 信誉评分系统
按任务类型维度追踪每个 Agent 的表现，策略龙派发时自动路由
"""
import json, os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import MEMORY_MONTHLY

REPUTATION_FILE = os.path.join(MEMORY_MONTHLY, "reputation.json")

DEFAULT_SCORES = {
    "xiaohongshu_copy": 0.5,
    "ppt_design": 0.5,
    "data_analysis": 0.5,
    "code_execution": 0.5,
    "strategy_planning": 0.5,
    "content_review": 0.5,
    "monitoring": 0.5,
    "learning_distillation": 0.5,
}

def init_reputation():
    """初始化所有Agent的信誉分"""
    agents = ["executor-a", "executor-b", "executor-c",
              "reviewer-strict", "reviewer-creative",
              "strategist", "monitor", "learner", "arbiter"]
    os.makedirs(os.path.dirname(REPUTATION_FILE), exist_ok=True)
    if not os.path.exists(REPUTATION_FILE):
        scores = {agent: dict(DEFAULT_SCORES) for agent in agents}
        with open(REPUTATION_FILE, "w", encoding="utf-8") as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)

def update_score(agent_name, task_type, success, quality=0.7):
    """更新单个Agent某类任务的信誉分（Windows兼容版）"""
    if not os.path.exists(REPUTATION_FILE):
        init_reputation()

    # Windows 使用文件锁替代方案：临时锁文件
    import tempfile
    lock_file = REPUTATION_FILE + ".lock"
    lock_acquired = False
    max_retries = 30

    for _ in range(max_retries):
        try:
            # 尝试创建锁文件（O_CREAT | O_EXCL 保证原子性）
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            lock_acquired = True
            break
        except FileExistsError:
            # 锁文件已存在，等待后重试
            import time
            time.sleep(0.1)

    if not lock_acquired:
        raise RuntimeError(f"无法获取文件锁: {lock_file}")

    try:
        with open(REPUTATION_FILE, "r", encoding="utf-8") as f:
            scores = json.load(f)

        current = scores.get(agent_name, {}).get(task_type, 0.5)

        # 指数移动平均更新
        alpha = 0.15
        # 失败时基础分从 0.3 改为 0.1，增强惩罚效果
        base = 1.0 if success else 0.1
        new_score = alpha * base * quality + (1 - alpha) * current
        scores[agent_name][task_type] = round(min(max(new_score, 0), 1), 3)

        # 原子写入：先写临时文件，再重命名
        temp_file = REPUTATION_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, REPUTATION_FILE)
    finally:
        # 释放锁
        if lock_acquired and os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except OSError:
                pass


def route_task(task_type, available_agents=None):
    """根据信誉分，返回最适合执行某类任务的Agent"""
    if not os.path.exists(REPUTATION_FILE):
        init_reputation()
    with open(REPUTATION_FILE, "r", encoding="utf-8") as f:
        scores = json.load(f)
    
    candidates = available_agents or list(scores.keys())
    ranked = sorted(candidates, 
                    key=lambda a: scores.get(a, {}).get(task_type, 0.5), 
                    reverse=True)
    return ranked[0] if ranked else None

def get_agent_report(agent_name):
    """查询单个Agent的完整信誉报告"""
    if not os.path.exists(REPUTATION_FILE):
        init_reputation()
    with open(REPUTATION_FILE, "r", encoding="utf-8") as f:
        scores = json.load(f)
    return scores.get(agent_name, {})

init_reputation()
