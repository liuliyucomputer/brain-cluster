# -*- coding: utf-8 -*-
"""
Dreaming 记忆压缩机 — 三阶段记忆沉淀引擎
===========================================
对标 OpenClaw Dreaming 的三阶段压缩节奏，但用纯 Python 自实现。

三阶段:
  短期 (每4小时): daily.jsonl → weekly/distillation.json
      统计事件分布 + 提取关键决策 + 更新信誉分
  中期 (每日): weekly → monthly/strategies.json
      模式识别 + 策略评估 + 知识巩固  
  长期 (每周): monthly → vector/
      知识重构 + 淘汰低效策略 + 长期智慧沉淀

用法:
  python dreaming_compressor.py short   # 4h 短期压缩
  python dreaming_compressor.py medium  # 每日中期巩固
  python dreaming_compressor.py long    # 每周长期沉淀
  python dreaming_compressor.py all     # 全量运行
"""
import json, os, sys
from datetime import datetime, timedelta
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import MEMORY_DAILY, MEMORY_WEEKLY, MEMORY_MONTHLY, MEMORY_VECTOR


def load_daily_events(hours=24):
    """加载最近 N 小时的 daily JSONL 事件"""
    cutoff = datetime.now() - timedelta(hours=hours)
    events = []
    if not os.path.exists(MEMORY_DAILY):
        return events
    
    for fname in sorted(os.listdir(MEMORY_DAILY)):
        if not fname.endswith('.jsonl'):
            continue
        fpath = os.path.join(MEMORY_DAILY, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts = datetime.fromisoformat(entry.get('timestamp', '2000-01-01'))
                    if ts >= cutoff:
                        for ev in entry.get('events', []):
                            ev['_day'] = fname.replace('.jsonl', '')
                            ev['_sync_ts'] = entry.get('timestamp', '')
                            events.append(ev)
                except (json.JSONDecodeError, ValueError):
                    continue
    return events


def compute_reputation(events, current_reputation=None):
    """基于真实事件计算差异化信誉分"""
    if current_reputation is None:
        current_reputation = {}
    
    # Agent 名称从 task_id 和 payload 中提取
    agent_stats = defaultdict(lambda: {
        "tasks": 0, "success": 0, "fail": 0, "crash": 0,
        "avg_duration": 0, "total_duration": 0, "domains": Counter()
    })
    
    for ev in events:
        kind = ev.get('kind', '')
        payload = ev.get('payload', '')
        task_id = ev.get('task_id', '')
        
        # 识别 Agent
        agent = None
        for candidate in ['executor-a', 'executor-b', 'executor-c', 'strategist',
                          'reviewer-strict', 'reviewer-creative', 'arbiter', 'monitor', 'learner']:
            if candidate in task_id or candidate in payload:
                agent = candidate
                break
        
        if agent:
            agent_stats[agent]['tasks'] += 1
            if kind in ('task_run', 'verify', 'e2e_test', 'implement', 'deploy'):
                agent_stats[agent]['success'] += 1
            elif kind in ('fix', 'blocker', 'data_pollution'):
                agent_stats[agent]['fail'] += 1
            elif kind == 'crash':
                agent_stats[agent]['crash'] += 1
            
            # 领域识别
            for domain, keywords in {
                '文案创作': ['文案', '种草', '小红书', '防晒', '写作', '内容'],
                'PPT设计': ['PPT', '演示', '幻灯片', '设计', '可视化'],
                '数据分析': ['数据', '分析', 'SQL', 'API', '图表'],
                '系统运维': ['fix', 'deploy', 'config', '端口', '路径', '编译', '审计'],
                '代码开发': ['实现', 'implement', '代码', 'python', 'react', '前端', '后端'],
            }.items():
                if any(kw in payload for kw in keywords):
                    agent_stats[agent]['domains'][domain] += 1
    
    # 计算评分 (0.0-1.0) — 存入独立的 flat_scores
    flat_scores = {}
    for agent, stats in agent_stats.items():
        if stats['tasks'] == 0:
            continue
        
        total = stats['tasks']
        success_rate = stats['success'] / total
        
        # 成功率权重 50%
        score = success_rate * 0.5
        
        # 领域广度 20% (做的领域越多越好)
        domain_count = len(stats['domains'])
        score += min(domain_count / 5, 1.0) * 0.2
        
        # 稳定性 30% (crash 率越低越好)
        crash_rate = stats['crash'] / total if total > 0 else 0
        score += (1.0 - crash_rate) * 0.3
        
        # 平滑过渡: 新评分 70% + 旧评分 30%
        old_val = current_reputation.get(agent, 0.5)
        if isinstance(old_val, dict):
            scores = [v for v in old_val.values() if isinstance(v, (int, float))]
            old_score = sum(scores) / len(scores) if scores else 0.5
        else:
            old_score = float(old_val)
        flat_scores[agent] = round(score * 0.7 + old_score * 0.3, 4)
    
    # 转换为 skills-based 嵌套格式，便于路由
    SKILLS = ["xiaohongshu_copy", "ppt_design", "data_analysis", "code_execution",
              "strategy_planning", "content_review", "monitoring", "learning_distillation"]
    
    formatted = {}
    for agent in set(list(current_reputation.keys()) + list(flat_scores.keys())):
        overall = flat_scores.get(agent, 0.5)
        if isinstance(current_reputation.get(agent), dict):
            skills = dict(current_reputation[agent])
            for skill in SKILLS:
                if agent in flat_scores:
                    old_s = skills.get(skill, 0.5)
                    skills[skill] = round(overall * 0.5 + old_s * 0.5, 4)
        else:
            skills = {s: overall for s in SKILLS}
        formatted[agent] = skills
    
    return formatted


def short_term_compress():
    """短期压缩 (每4小时): daily → weekly distillation"""
    events = load_daily_events(hours=4)
    if not events:
        print("[short_term] 无新事件，跳过")
        return None
    
    # 统计事件分布
    kind_counts = Counter(e.get('kind', 'unknown') for e in events)
    
    # 提取关键事件 (fix, implement, blocker 类型)
    key_events = [
        {"task_id": e.get('task_id'), "kind": e.get('kind'),
         "summary": e.get('payload', '')[:120],
         "day": e.get('_day', '')}
        for e in events
        if e.get('kind') in ('fix', 'implement', 'blocker', 'deploy', 'verify', 'migrate')
    ]
    
    today = datetime.now().strftime("%Y-%m-%d")
    output = {
        "stage": "short_term",
        "compressed_at": datetime.now().isoformat(),
        "event_count": len(events),
        "kind_distribution": dict(kind_counts),
        "key_events": key_events[:20],
        "summary": f"过去4小时共 {len(events)} 个事件，分布: {dict(kind_counts.most_common(5))}"
    }
    
    os.makedirs(MEMORY_WEEKLY, exist_ok=True)
    fpath = os.path.join(MEMORY_WEEKLY, f"{today}-distillation.json")
    with open(fpath, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"[short_term] 压缩完成: {len(events)} 事件 → {fpath}")
    return output


def medium_term_consolidate():
    """中期巩固 (每日): weekly → monthly strategies + reputation"""
    events = load_daily_events(hours=24)
    if not events:
        print("[medium_term] 无新事件，跳过")
        return None
    
    # 更新信誉分
    rep_path = os.path.join(MEMORY_MONTHLY, "reputation.json")
    current_rep = {}
    if os.path.exists(rep_path):
        with open(rep_path, 'r', encoding='utf-8') as f:
            current_rep = json.load(f)
    
    new_reputation = compute_reputation(events, current_rep)
    os.makedirs(MEMORY_MONTHLY, exist_ok=True)
    with open(rep_path, 'w', encoding='utf-8') as f:
        json.dump(new_reputation, f, ensure_ascii=False, indent=2)
    
    # 模式识别: 哪种事件类型最频繁? 哪种修复最常用?
    kind_counts = Counter(e.get('kind', 'unknown') for e in events)
    top_patterns = kind_counts.most_common(5)
    
    # 策略库更新
    strategies_path = os.path.join(MEMORY_MONTHLY, "strategies.json")
    strategies = {
        "updated_at": datetime.now().isoformat(),
        "event_count": len(events),
        "top_patterns": [{"kind": k, "count": c} for k, c in top_patterns],
        "reputation": new_reputation,
        "insights": []
    }
    
    # 生成洞察
    if kind_counts.get('fix', 0) > kind_counts.get('implement', 0):
        strategies['insights'].append("修复类事件多于实现类，系统可能在稳定化阶段")
    if kind_counts.get('blocker', 0) > 0:
        strategies['insights'].append(f"检测到 {kind_counts['blocker']} 个阻塞事件，建议审查 API 可用性和依赖")
    
    with open(strategies_path, 'w', encoding='utf-8') as f:
        json.dump(strategies, f, ensure_ascii=False, indent=2)
    
    print(f"[medium_term] 巩固完成: {len(events)} 事件, 信誉已更新, 策略 {len(strategies['top_patterns'])} 条模式")
    return strategies


def long_term_reconstruct():
    """长期沉淀 (每周): monthly → vector/ 知识重构"""
    events = load_daily_events(hours=168)  # 7天
    
    # 读入现有策略
    strategies_path = os.path.join(MEMORY_MONTHLY, "strategies.json")
    rep_path = os.path.join(MEMORY_MONTHLY, "reputation.json")
    
    existing_strategies = {}
    if os.path.exists(strategies_path):
        with open(strategies_path, 'r', encoding='utf-8') as f:
            existing_strategies = json.load(f)
    
    reputation = {}
    if os.path.exists(rep_path):
        with open(rep_path, 'r', encoding='utf-8') as f:
            reputation = json.load(f)
    
    # 整体统计
    kind_total = Counter(e.get('kind', 'unknown') for e in events)
    
    # 计算每个 Agent 的平均分（兼容嵌套格式）
    def agent_avg(reputation, agent):
        val = reputation.get(agent, 0.5)
        if isinstance(val, dict):
            scores = [v for v in val.values() if isinstance(v, (int, float))]
            return sum(scores) / len(scores) if scores else 0.5
        return float(val)
    
    # 低效 Agent 检测: 信誉分 < 0.3 且任务数 > 0
    low_efficiency = [
        {"agent": agent, "score": round(agent_avg(reputation, agent), 4), "action": "建议降权或重新训练"}
        for agent in reputation
        if agent_avg(reputation, agent) < 0.3
    ]
    
    # 高效 Agent: 信誉分 > 0.7
    high_efficiency = [
        {"agent": agent, "score": round(agent_avg(reputation, agent), 4), "action": "优先路由"}
        for agent in reputation
        if agent_avg(reputation, agent) > 0.7
    ]
    
    today = datetime.now().strftime("%Y-%m-%d")
    long_term = {
        "stage": "long_term",
        "reconstructed_at": datetime.now().isoformat(),
        "period": f"过去7天 ({today})",
        "total_events": len(events),
        "kind_summary": dict(kind_total.most_common(10)),
        "reputation_snapshot": reputation,
        "low_efficiency_agents": low_efficiency,
        "high_efficiency_agents": high_efficiency,
        "strategy_evolution": {
            "previous_update": existing_strategies.get('updated_at', 'N/A'),
            "current_update": datetime.now().isoformat(),
            "top_patterns_7d": [{"kind": k, "count": c} for k, c in kind_total.most_common(5)]
        },
        "knowledge_fragments": []
    }
    
    # 生成知识碎片
    for kind, count in kind_total.most_common(3):
        long_term['knowledge_fragments'].append(
            f"7天内共发生 {count} 次 {kind} 类事件，为最活跃类别"
        )
    
    os.makedirs(MEMORY_VECTOR, exist_ok=True)
    fpath = os.path.join(MEMORY_VECTOR, f"{today}-reconstruction.json")
    with open(fpath, 'w', encoding='utf-8') as f:
        json.dump(long_term, f, ensure_ascii=False, indent=2)
    
    print(f"[long_term] 知识重构完成: {len(events)} 事件 → {fpath}")
    print(f"  高效 Agent: {len(high_efficiency)}, 低效 Agent: {len(low_efficiency)}")
    return long_term


def run_all():
    """全量运行三阶段"""
    print("=" * 60)
    print(f"Dreaming 压缩机 — 全量运行 @ {datetime.now().isoformat()}")
    print("=" * 60)
    
    print("\n[1/3] 短期压缩 (4h)...")
    s = short_term_compress()
    
    print("\n[2/3] 中期巩固 (24h)...")
    m = medium_term_consolidate()
    
    print("\n[3/3] 长期沉淀 (7d)...")
    l = long_term_reconstruct()
    
    print("\n" + "=" * 60)
    print("全量压缩完成 ✅")
    return {"short": s, "medium": m, "long": l}


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description='Dreaming 记忆压缩机')
    p.add_argument('stage', nargs='?', default='all',
                   choices=['short', 'medium', 'long', 'all'],
                   help='压缩阶段 (default: all)')
    args = p.parse_args()
    
    if args.stage == 'short':
        short_term_compress()
    elif args.stage == 'medium':
        medium_term_consolidate()
    elif args.stage == 'long':
        long_term_reconstruct()
    else:
        run_all()
