# -*- coding: utf-8 -*-
"""
仲裁表决引擎 — 关键决策三方投票，少数服从多数
"""
import json
from datetime import datetime

def arbitrate(proposal, votes):
    """
    proposal: { "type": "strategy_change|quality_dispute|policy_update", ... }
    votes: { "strategist": "yes|no", "learner": "yes|no", "arbiter": "yes|no" }
    """
    yes_count = sum(1 for v in votes.values() if v == "yes")
    total = len(votes)
    
    if yes_count == total:
        decision = "approve"
        risk = "low"
    elif yes_count >= total * 2/3:
        decision = "approve_with_risk"
        risk = "medium"
    else:
        decision = "reject"
        risk = "high"
    
    return {
        "decision": decision,
        "risk_level": risk,
        "votes": votes,
        "timestamp": datetime.now().isoformat(),
        "rationale": f"{yes_count}/{total} 票通过"
    }

def escalate_to_human(issue):
    """需要人工介入时，通过连接器推送"""
    message = {
        "level": "ESCALATION",
        "issue": issue,
        "timestamp": datetime.now().isoformat(),
        "action_required": "请人工审查并决策"
    }
    # 通过企业微信/钉钉/飞书连接器推送
    # notifier.send(message)
    return message
