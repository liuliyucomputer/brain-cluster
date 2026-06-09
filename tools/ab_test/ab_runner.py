# -*- coding: utf-8 -*-
"""
A/B 策略实验引擎
学习龙提出假设 → 创建双任务 → 审查龙评估 → 自动选优
"""
import json, os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import MEMORY_MONTHLY

AB_RESULTS = os.path.join(MEMORY_MONTHLY, "ab_results.json")

def create_ab_experiment(hypothesis, strategy_a, strategy_b, task_type, kanban_api):
    """创建一组A/B实验任务"""
    tasks = {
        "experiment_id": f"ab-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "hypothesis": hypothesis,
        "task_type": task_type,
        "group_a": {"strategy": strategy_a, "task_id": None, "result": None},
        "group_b": {"strategy": strategy_b, "task_id": None, "result": None},
        "status": "running",
        "created_at": datetime.now().isoformat()
    }
    return tasks

def evaluate_ab_result(experiment_id):
    """审查龙评估后，自动选出优胜策略"""
    if not os.path.exists(AB_RESULTS):
        return None
    with open(AB_RESULTS, "r", encoding="utf-8") as f:
        results = json.load(f)
    
    exp = results.get(experiment_id)
    if not exp or exp["status"] != "running":
        return None
    
    score_a = exp.get("group_a", {}).get("result", {}).get("review_score", 0)
    score_b = exp.get("group_b", {}).get("result", {}).get("review_score", 0)
    
    winner = "A" if score_a > score_b else "B"
    exp["winner"] = winner
    exp["status"] = "completed"
    exp["confidence"] = abs(score_a - score_b) / max(score_a, score_b)
    
    with open(AB_RESULTS, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    return exp

def get_winning_strategy(task_type):
    """查询某类任务当前的最优策略"""
    if not os.path.exists(AB_RESULTS):
        return None
    with open(AB_RESULTS, "r", encoding="utf-8") as f:
        results = json.load(f)
    
    completed = [r for r in results.values() 
                 if r.get("task_type") == task_type and r["status"] == "completed"]
    if not completed:
        return None
    
    latest = max(completed, key=lambda r: r["created_at"])
    return latest["group_" + latest["winner"].lower()]["strategy"]
