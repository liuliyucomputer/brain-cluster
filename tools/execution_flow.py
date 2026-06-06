# -*- coding: utf-8 -*-
"""
执行流串联引擎 — 连接 A/B实验 + 信誉评分 + 审查双审 + 仲裁表决
被策略龙和执行龙在任务生命周期各阶段调用
"""
import json
import os
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ab_test.ab_runner import get_winning_strategy
from reputation.scorer import route_task, update_score

TOOLS_DIR = r"D:\brain\tools"

def strategist_route_task(task_type, task_description):
    """
    策略龙拆解任务后，调用此函数决定分配给哪个执行龙
    1. 查信誉分 → 选最优执行龙
    2. 查A/B实验结果 → 选最优策略
    """
    # 1. 信誉路由
    best_agent = route_task(task_type, ["executor-a", "executor-b", "executor-c"])
    
    # 2. 策略选择
    best_strategy = get_winning_strategy(task_type)
    
    return {
        "assigned_agent": best_agent,
        "strategy": best_strategy or "default",
        "task_type": task_type,
        "task_description": task_description
    }

def after_executor_done(agent_name, task_type, task_result):
    """
    执行龙完成任务后，触发审查流
    1. 更新信誉评分
    2. 返回审查指令
    """
    # 更新信誉分（临时评分，等审查龙确认后更新）
    update_score(agent_name, task_type, True, quality=0.7)
    
    # 返回审查指令
    return {
        "action": "send_to_review",
        "reviewers": ["reviewer-strict", "reviewer-creative"],
        "task_result": task_result
    }

def after_dual_review(score_strict, score_creative, task_id, task_result):
    """
    双审完成后，决定下一步
    """
    strict_pass = score_strict.get("total", 0) >= 60
    creative_pass = score_creative.get("total", 0) >= 50
    
    if strict_pass and creative_pass:
        return {"verdict": "pass", "action": "complete_task", "task_id": task_id}
    elif strict_pass != creative_pass:
        return {"verdict": "split", "action": "send_to_arbiter", 
                "task_id": task_id, "scores": [score_strict, score_creative]}
    else:
        return {"verdict": "fail", "action": "return_to_executor",
                "task_id": task_id, "feedback": score_strict.get("feedback", "请改进")}

if __name__ == "__main__":
    # 快速验证
    route = strategist_route_task("xiaohongshu_copy", "防晒文案")
    print(f"Strategist route: agent={route['assigned_agent']}, strategy={route['strategy']}")
    
    review = after_executor_done("executor-a", "xiaohongshu_copy", "测试内容")
    print(f"Review trigger: {review['action']} → {review['reviewers']}")
    
    verdict = after_dual_review(
        {"total": 85}, {"total": 45}, "test-001", "测试内容")
    print(f"Dual review verdict: {verdict['verdict']} → {verdict['action']}")
