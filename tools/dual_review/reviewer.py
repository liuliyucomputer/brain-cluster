# -*- coding: utf-8 -*-
"""
双审引擎 — 调用两个审查龙独立评审，输出合并裁决
"""
import json

def dual_review(task_id, content, task_type):
    """
    调用审查龙-A(strict)和审查龙-B(creative)分别评审
    返回合并裁决
    """
    # 通过 Hermes Kanban API 创建两个审查子任务
    # review_a = create_review_task(task_id, assignee="reviewer-strict", content)
    # review_b = create_review_task(task_id, assignee="reviewer-creative", content)
    
    # 等待双审完成，收集评分卡
    # score_a = wait_for_result(review_a)
    # score_b = wait_for_result(review_b)
    
    # 合并裁决逻辑（由仲裁龙执行）
    pass

def merge_verdict(score_a, score_b):
    """合并双审结果"""
    pass_threshold_strict = 60
    pass_threshold_creative = 50
    
    a_pass = score_a["total"] >= pass_threshold_strict
    b_pass = score_b["total"] >= pass_threshold_creative
    
    if a_pass and b_pass:
        return {"verdict": "pass", "action": "kanban_complete", "avg_score": (score_a["total"] + score_b["total"]) / 2}
    elif a_pass != b_pass:
        return {"verdict": "split", "action": "send_to_arbiter", "scores": [score_a, score_b]}
    else:
        return {"verdict": "fail", "action": "return_to_executor", 
                "feedback_a": score_a.get("feedback", ""),
                "feedback_b": score_b.get("feedback", "")}
