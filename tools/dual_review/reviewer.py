# -*- coding: utf-8 -*-
"""
双审模块 — 严格审查 + 创意审查并行评分，分歧时自动触发仲裁
"""
import json, os, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import MEMORY_MONTHLY

SCORES_DIR = MEMORY_MONTHLY

STRICT_CRITERIA = {
    "fact_accuracy": {"weight": 0.35, "desc": "事实准确性"},
    "format_spec": {"weight": 0.25, "desc": "格式规范性"},
    "compliance": {"weight": 0.40, "desc": "合规性"},
}

CREATIVE_CRITERIA = {
    "attractiveness": {"weight": 0.35, "desc": "吸引力"},
    "innovation": {"weight": 0.35, "desc": "创新性"},
    "emotional_resonance": {"weight": 0.30, "desc": "情感共鸣"},
}


def _heuristic_score(content, criteria_type="strict"):
    """
    基于内容特征的启发式评分（当 LLM 不可用时作为降级方案）。
    实际生产环境建议通过 LLM API 调用获取更准确的评分。
    """
    if not content:
        return 30, "内容为空，无法评分"

    content = str(content)
    scores = {}
    total = 0.0

    if criteria_type == "strict":
        # 事实准确性: 检查是否有数据/引用/来源标记
        fact_score = 50
        if any(k in content for k in ["数据来源", "参考", "引用", "统计", "%", "20"]):
            fact_score += 20
        if any(k in content for k in ["据", "报告", "研究", "调查"]):
            fact_score += 10
        if len(content) > 200:
            fact_score += 10
        scores["fact_accuracy"] = min(fact_score, 100)

        # 格式规范性: 检查结构清晰度
        format_score = 50
        if "\n" in content or "\r\n" in content:
            format_score += 15
        if any(k in content for k in ["标题", "：", ":", "1.", "一、", "（1）"]):
            format_score += 15
        if len(content) > 100:
            format_score += 10
        scores["format_spec"] = min(format_score, 100)

        # 合规性: 检查敏感词
        compliance_score = 80
        risky_words = ["违法", "欺诈", "造假", "抄袭", "侵权", "虚假"]
        for w in risky_words:
            if w in content:
                compliance_score -= 20
        scores["compliance"] = max(compliance_score, 0)

        weights = {k: v["weight"] for k, v in STRICT_CRITERIA.items()}
    else:
        # 创意审查
        # 吸引力: 检查是否有情感词、互动元素
        attr_score = 50
        hooks = ["！", "？", "🔥", "💡", "✨", "👍", "必看", "揭秘", "独家", "震惊"]
        for h in hooks:
            if h in content:
                attr_score += 8
        if len(content) > 150:
            attr_score += 10
        scores["attractiveness"] = min(attr_score, 100)

        # 创新性: 检查独特表达
        innov_score = 50
        if any(k in content for k in ["新", "首创", "突破", "颠覆", "重新定义", "全新"]):
            innov_score += 20
        if len(set(content)) > len(content) * 0.5:  # 字符多样性
            innov_score += 15
        scores["innovation"] = min(innov_score, 100)

        # 情感共鸣: 检查情感词
        emotion_score = 50
        emotions = ["感动", "温暖", "共鸣", "梦想", "坚持", "努力", "爱", "感恩", "惊喜"]
        for e in emotions:
            if e in content:
                emotion_score += 10
        scores["emotional_resonance"] = min(emotion_score, 100)

        weights = {k: v["weight"] for k, v in CREATIVE_CRITERIA.items()}

    for key, score in scores.items():
        total += score * weights.get(key, 0.33)

    total = round(total, 1)

    # 生成反馈
    feedback_parts = []
    for key, score in scores.items():
        label = (STRICT_CRITERIA if criteria_type == "strict" else CREATIVE_CRITERIA).get(key, {}).get("desc", key)
        if score >= 80:
            feedback_parts.append(f"{label}优秀({score})")
        elif score >= 60:
            feedback_parts.append(f"{label}良好({score})")
        else:
            feedback_parts.append(f"{label}需改进({score})")
    feedback = "；".join(feedback_parts)

    return total, feedback


def score_content(content, criteria_type="strict"):
    """
    对内容进行评分。

    优先尝试通过 LLM API 获取真实评分，若 API 不可用则回退到启发式评分。

    Args:
        content: 待评分的内容文本
        criteria_type: "strict" 或 "creative"

    Returns:
        dict: {"total": 0-100, "verdict": "pass"/"fail", "criteria": {...}, "feedback": "..."}
    """
    criteria = STRICT_CRITERIA if criteria_type == "strict" else CREATIVE_CRITERIA
    threshold = 60 if criteria_type == "strict" else 50

    # 尝试通过 API 获取真实评分
    try:
        api_score = _llm_score_content(content, criteria_type)
        if api_score and api_score.get("total") is not None:
            return api_score
    except Exception:
        pass

    # 回退到启发式评分
    total, feedback = _heuristic_score(content, criteria_type)

    # 构建详细评分结构
    scores = {}
    for key, cfg in criteria.items():
        # 启发式评分不返回分项，使用总分按比例分配
        scores[key] = {
            "score": round(total, 1),
            "weight": cfg["weight"],
            "desc": cfg["desc"],
        }

    verdict = "pass" if total >= threshold else "fail"

    result = {
        "total": total,
        "verdict": verdict,
        "criteria": scores,
        "feedback": feedback,
    }

    return result


def _llm_score_content(content, criteria_type="strict"):
    """
    通过 LLM API 对内容进行真实评分。
    返回 dict 或 None（失败时）。
    """
    import os
    import json
    import urllib.request

    api_key = os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1")

    if not api_key or not content:
        return None

    criteria = STRICT_CRITERIA if criteria_type == "strict" else CREATIVE_CRITERIA
    criteria_desc = "\n".join([f"- {k}: {v['desc']} (权重{v['weight']})" for k, v in criteria.items()])

    prompt = f"""你是一位专业的内容审查员。请对以下内容进行{criteria_type}审查评分。

审查维度：
{criteria_desc}

请对每个维度给出 0-100 的分数，计算加权总分，并给出 pass/fail 判定。
strict 类型阈值 60 分，creative 类型阈值 50 分。

必须按以下 JSON 格式返回，不要包含其他内容：
{{
  "total": 加权总分,
  "verdict": "pass" 或 "fail",
  "criteria": {{
    "维度名": {{"score": 分数, "weight": 权重, "desc": "描述"}}
  }},
  "feedback": "具体评价建议"
}}

待审查内容：
{content[:2000]}
"""

    try:
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps({
                "model": "deepseek-ai/DeepSeek-V4-Pro",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
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

            # 提取 JSON
            json_match = None
            for pattern in [r'```json\s*(.*?)\s*```', r'\{.*\}']:
                import re
                m = re.search(pattern, message, re.DOTALL)
                if m:
                    json_match = m.group(1) if pattern.startswith(r'```') else m.group(0)
                    break

            if json_match:
                result = json.loads(json_match)
                # 验证必要字段
                if "total" in result and "verdict" in result:
                    return result
    except Exception:
        pass

    return None


def dual_review(content, task_id=None):
    """
    执行双审：同时运行 strict 和 creative 评分。
    
    返回两个评分结果，供 pipeline_orchestrator 判断是否需要仲裁。
    
    Args:
        content: 待审查的内容
        task_id: 关联的任务ID（用于日志记录）
    
    Returns:
        dict: {
            "strict": {score_result},
            "creative": {score_result},
            "consensus": "pass"/"fail"/"split",
            "task_id": task_id
        }
    """
    strict_result = score_content(content, "strict")
    creative_result = score_content(content, "creative")
    
    strict_pass = strict_result["verdict"] == "pass"
    creative_pass = creative_result["verdict"] == "pass"
    
    if strict_pass and creative_pass:
        consensus = "pass"
    elif not strict_pass and not creative_pass:
        consensus = "fail"
    else:
        consensus = "split"
    
    result = {
        "strict": strict_result,
        "creative": creative_result,
        "consensus": consensus,
        "task_id": task_id,
        "timestamp": datetime.now().isoformat(),
    }
    
    # 保存审查记录
    log_path = os.path.join(SCORES_DIR, "review_log.jsonl")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    
    return result


def merge_verdict(strict_score, creative_score):
    """
    合并双审裁决，供 execution_flow 调用。
    
    Args:
        strict_score: dict with "total" and "verdict" keys
        creative_score: dict with "total" and "verdict" keys
    
    Returns:
        dict: {"verdict": "pass"/"fail"/"split", "action": "complete"/"retry"/"arbitrate"}
    """
    strict_pass = strict_score.get("verdict") == "pass"
    creative_pass = creative_score.get("verdict") == "pass"
    
    if strict_pass and creative_pass:
        return {"verdict": "pass", "action": "complete"}
    elif not strict_pass and not creative_pass:
        return {"verdict": "fail", "action": "retry"}
    else:
        return {"verdict": "split", "action": "arbitrate"}
