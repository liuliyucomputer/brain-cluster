# -*- coding: utf-8 -*-
"""
仲裁投票模块 — 双审结果分歧时，多Agent投票裁决
"""
import json, os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import MEMORY_MONTHLY

ARBITER_DIR = MEMORY_MONTHLY

# 仲裁 Agent 列表（按序投票）
ARBITER_PANEL = ["arbiter", "quality-gate", "incident-responder"]


def _agent_vote(agent_name, strict_score, creative_score, content_snippet, risk_level):
    """
    模拟单个 Agent 的独立投票逻辑。
    每个 Agent 有不同的投票倾向，体现多元视角。
    生产环境建议通过 LLM API 让每个 Agent 独立决策。
    """
    margin = abs(strict_score.get("total", 50) - creative_score.get("total", 50))
    strict_total = strict_score.get("total", 50)
    creative_total = creative_score.get("total", 50)

    # 不同 Agent 有不同的决策权重和倾向
    agent_profiles = {
        "arbiter": {
            "strict_weight": 0.5,
            "creative_weight": 0.5,
            "risk_averse": 0.3,  # 中等风险厌恶
        },
        "quality-gate": {
            "strict_weight": 0.7,  # 更重视严格审查
            "creative_weight": 0.3,
            "risk_averse": 0.6,  # 较高风险厌恶
        },
        "incident-responder": {
            "strict_weight": 0.3,
            "creative_weight": 0.7,  # 更重视创意
            "risk_averse": 0.1,  # 较低风险厌恶
        },
    }

    profile = agent_profiles.get(agent_name, agent_profiles["arbiter"])

    # 计算该 Agent 的加权分数
    weighted_score = (strict_total * profile["strict_weight"] +
                      creative_total * profile["creative_weight"])

    # 根据风险厌恶度调整阈值
    base_threshold = 55
    adjusted_threshold = base_threshold + profile["risk_averse"] * 20

    # 根据分数差距和内容做决策
    if risk_level == "high":
        # 高风险时，quality-gate 倾向 reject，incident-responder 可能 retry
        if agent_name == "quality-gate":
            return "reject"
        elif agent_name == "incident-responder":
            return "retry" if creative_total > 40 else "reject"
        else:
            return "retry"
    elif risk_level == "medium":
        if weighted_score >= adjusted_threshold:
            return "approve"
        else:
            return "retry"
    else:
        # 低风险
        if weighted_score >= adjusted_threshold:
            return "approve"
        elif weighted_score >= adjusted_threshold - 15:
            return "retry"
        else:
            return "reject"


def _llm_arbitrate(strict_score, creative_score, content_snippet, panel):
    """
    通过 LLM API 进行真实的多 Agent 仲裁。
    返回 dict 或 None（失败时）。
    """
    import os
    import json
    import urllib.request

    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1")

    if not api_key:
        return None

    prompt = f"""你是 Brain 集群的仲裁委员会主席。现在双审结果出现分歧，需要你来裁决。

strict reviewer 评分: {strict_score.get('total', 0)} (verdict: {strict_score.get('verdict', 'unknown')})
creative reviewer 评分: {creative_score.get('total', 0)} (verdict: {creative_score.get('verdict', 'unknown')})

内容摘要:
{content_snippet[:1000] if content_snippet else '无内容摘要'}

投票团: {', '.join(panel)}

请模拟每个 Agent 的独立投票（考虑各自的专业角度），然后统计票数给出最终裁决。

必须按以下 JSON 格式返回，不要包含其他内容：
{{
  "verdict": "approve" 或 "reject" 或 "retry",
  "votes": {{"agent名": "approve/reject/retry", ...}},
  "vote_counts": {{"approve": N, "reject": N, "retry": N}},
  "risk_level": "low/medium/high",
  "reason": "裁决理由"
}}
"""

    try:
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps({
                "model": "deepseek-ai/DeepSeek-V4-Pro",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "max_tokens": 800,
            }).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choices = data.get("choices", [])
            if not choices:
                raise ValueError(f"API 返回空 choices")
            message = choices[0].get("message", {}).get("content", "")
            if not message:
                raise ValueError(f"API 返回空 content")

            import re
            json_match = None
            for pattern in [r'```json\s*(.*?)\s*```', r'\{.*\}']:
                m = re.search(pattern, message, re.DOTALL)
                if m:
                    json_match = m.group(1) if pattern.startswith(r'```') else m.group(0)
                    break

            if json_match:
                result = json.loads(json_match)
                if "verdict" in result and "votes" in result:
                    return result
    except Exception:
        pass

    return None


def arbitrate(strict_score, creative_score, content_snippet="", panel=None):
    """
    双审分歧时进行多Agent仲裁投票。

    优先尝试通过 LLM API 进行真实仲裁，若不可用则使用多 Agent 独立投票模拟。

    Args:
        strict_score: strict reviewer 的评分 (dict with "total")
        creative_score: creative reviewer 的评分 (dict with "total")
        content_snippet: 内容摘要（供投票参考）
        panel: 投票团列表，默认 ["arbiter", "quality-gate", "incident-responder"]

    Returns:
        dict: {
            "verdict": "approve"/"reject"/"retry",
            "votes": {agent: vote, ...},
            "majority": 胜出票数,
            "risk_level": "low"/"medium"/"high",
            "reason": "裁决理由"
        }
    """
    if panel is None:
        panel = ARBITER_PANEL

    # 尝试通过 LLM API 进行真实仲裁
    try:
        llm_result = _llm_arbitrate(strict_score, creative_score, content_snippet, panel)
        if llm_result:
            # 补充必要字段
            llm_result["timestamp"] = datetime.now().isoformat()
            if "majority" not in llm_result:
                winner = llm_result.get("verdict", "retry")
                counts = llm_result.get("vote_counts", {})
                winner_count = counts.get(winner, 0)
                llm_result["majority"] = f"{winner_count}/{len(panel)}"
            _save_arbiter_log(llm_result)
            return llm_result
    except Exception:
        pass

    # 回退到多 Agent 独立投票模拟
    margin = abs(strict_score.get("total", 50) - creative_score.get("total", 50))

    # 根据分数差距决定风险等级
    if margin > 30:
        risk_level = "high"
    elif margin > 15:
        risk_level = "medium"
    else:
        risk_level = "low"

    # 每个 Agent 独立投票
    votes = {}
    for agent in panel:
        votes[agent] = _agent_vote(agent, strict_score, creative_score, content_snippet, risk_level)

    # 统计票数
    vote_counts = {"approve": 0, "reject": 0, "retry": 0}
    for v in votes.values():
        vote_counts[v] = vote_counts.get(v, 0) + 1

    # 多数决（处理平局: retry > reject > approve）
    winner = max(vote_counts, key=lambda k: (vote_counts[k], {"retry": 3, "reject": 2, "approve": 1}.get(k, 0)))
    winner_count = vote_counts[winner]

    # 如果所有票数相同，默认 retry（最保守策略）
    if len(set(vote_counts.values())) == 1 and len(vote_counts) > 1:
        winner = "retry"
        winner_count = vote_counts[winner]

    result = {
        "verdict": winner,
        "votes": votes,
        "vote_counts": vote_counts,
        "majority": f"{winner_count}/{len(panel)}",
        "risk_level": risk_level,
        "reason": f"Strict: {strict_score.get('total', 0)}, Creative: {creative_score.get('total', 0)}, Margin: {margin}. "
                  f"Votes: {vote_counts}. Winner: {winner}.",
        "timestamp": datetime.now().isoformat(),
    }

    _save_arbiter_log(result)
    return result


def _save_arbiter_log(result):
    """保存仲裁记录到日志"""
    os.makedirs(ARBITER_DIR, exist_ok=True)
    log_path = os.path.join(ARBITER_DIR, "arbiter_log.jsonl")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")


def escalate_to_human(result, notification_channel=None):
    """
    高风险裁决升级为人工审核。
    
    Args:
        result: arbitrate() 的返回结果
        notification_channel: 通知渠道 (wecom/feishu/dingtalk/email)
    
    Returns:
        dict: {"escalated": True, "channel": channel, "message": "..."}
    """
    message = (
        f"[Brain 集群 · 人工审核请求]\n"
        f"风险等级: {result.get('risk_level', 'unknown')}\n"
        f"裁决结果: {result.get('verdict', 'unknown')}\n"
        f"投票分布: {result.get('vote_counts', {})}\n"
        f"理由: {result.get('reason', '')}\n"
        f"时间: {result.get('timestamp', '')}"
    )
    
    channel = notification_channel or "log"
    
    # 通知到日志文件
    alert_path = os.path.join(ARBITER_DIR, "human_escalation.jsonl")
    with open(alert_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "escalated": True,
            "channel": channel,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }, ensure_ascii=False) + "\n")
    
    return {
        "escalated": True,
        "channel": channel,
        "message": message,
    }
