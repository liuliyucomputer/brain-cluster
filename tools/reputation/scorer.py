# -*- coding: utf-8 -*-
"""
Agent 信誉评分系统
按任务类型维度追踪每个 Agent 的表现，策略龙派发时自动路由
"""
import json
import os
from datetime import datetime

MEMORY_DIR = r"D:\brain\memory"
REPUTATION_FILE = os.path.join(MEMORY_DIR, "monthly", "reputation.json")

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
    if not os.path.exists(REPUTATION_FILE):
        scores = {agent: dict(DEFAULT_SCORES) for agent in agents}
        with open(REPUTATION_FILE, "w", encoding="utf-8") as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)

def update_score(agent_name, task_type, success, quality=0.7):
    """更新单个Agent某类任务的信誉分"""
    with open(REPUTATION_FILE, "r", encoding="utf-8") as f:
        scores = json.load(f)
    
    current = scores.get(agent_name, {}).get(task_type, 0.5)
    
    # 指数移动平均更新
    alpha = 0.15
    new_score = alpha * (1.0 if success else 0.3) * quality + (1 - alpha) * current
    scores[agent_name][task_type] = round(min(max(new_score, 0), 1), 3)
    
    with open(REPUTATION_FILE, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)

def route_task(task_type, available_agents=None):
    """根据信誉分，返回最适合执行某类任务的Agent"""
    with open(REPUTATION_FILE, "r", encoding="utf-8") as f:
        scores = json.load(f)
    
    candidates = available_agents or list(scores.keys())
    ranked = sorted(candidates, 
                    key=lambda a: scores.get(a, {}).get(task_type, 0.5), 
                    reverse=True)
    return ranked[0] if ranked else None

def get_agent_report(agent_name):
    """查询单个Agent的完整信誉报告"""
    with open(REPUTATION_FILE, "r", encoding="utf-8") as f:
        scores = json.load(f)
    return scores.get(agent_name, {})

init_reputation()
