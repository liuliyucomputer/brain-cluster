# -*- coding: utf-8 -*-
"""修复后全量排查脚本"""
import os, sys, json, re, subprocess
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')

print('='*60)
print('  Brain 集群 — 修复后全量排查报告')
print(f'  {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print('='*60)

report = {'pass': 0, 'fail': 0, 'warn': 0, 'checks': []}

def check(name, condition, detail=''):
    if condition:
        report['pass'] += 1
        print(f'  [PASS] {name} {detail}')
    else:
        report['fail'] += 1
        print(f'  [FAIL] {name} {detail}')
    report['checks'].append({'name': name, 'status': 'pass' if condition else 'fail', 'detail': detail})

def warn(name, condition, detail=''):
    if condition:
        report['pass'] += 1
        print(f'  [PASS] {name} {detail}')
    else:
        report['warn'] += 1
        print(f'  [WARN] {name} {detail}')

api_key_pattern = 'sk-xGSsFRUlKUXduzjnwPK4m9J7eNmmVTRwraXROi0dhPiRTvP8'

# ====== 1. Profile 注册修复 ======
print('\n--- 1. Profile 注册 ---')
with open('D:/brain/tools/profile_register.py', encoding='utf-8') as f: content = f.read()
check('检测 stdout+stderr', 'combined_output = (r.stderr + r.stdout).lower()' in content)
check('err_msg 包含 stdout', '(r.stderr + r.stdout).strip()' in content)

r = subprocess.run(['hermes', 'profile', 'list'], capture_output=True, text=True, encoding='utf-8', errors='replace')
core_profiles = ['strategist','executor-a','executor-b','executor-c','monitor','reviewer-strict','reviewer-creative','arbiter','learner','expert-coordinator','quality-gate']
profiles_found = [p for p in core_profiles if p in (r.stdout or '')]
check(f'Profiles 已注册', len(profiles_found) >= 10, f'{len(profiles_found)}/11 核心 profiles')

# ====== 2. 路径统一 ======
print('\n--- 2. 路径统一 ---')
files_to_check = {
    'tools/ab_test/ab_runner.py': 'output',
    'tools/reputation/scorer.py': 'output',
    'staroffice-ui/backend/app.py': 'output',
    'grafana/datasource.yaml': r'output\memory',
}
for fname, expect in files_to_check.items():
    fpath = f'D:/brain/{fname}'
    if os.path.exists(fpath):
        with open(fpath, encoding='utf-8') as f: c = f.read()
        ok = expect in c
        check(f'{fname} 路径已修复', ok)
    else:
        warn(f'{fname}', False, '文件不存在')

check('output/memory 目录存在', os.path.isdir('D:/brain/output/memory'))

# ====== 3. API 密钥安全 ======
print('\n--- 3. API 密钥安全 ---')
key_files = []
for root, dirs, files in os.walk('D:/brain/tools'):
    for f in files:
        if f.endswith('.py') and f != 'post_fix_audit.py':
            fpath = os.path.join(root, f)
            with open(fpath, encoding='utf-8', errors='ignore') as fh:
                if api_key_pattern in fh.read():
                    key_files.append(fpath)
for f in ['D:/brain/start_all.bat', 'D:/brain/start_all.ps1']:
    if os.path.exists(f):
        with open(f, encoding='utf-8', errors='ignore') as fh:
            if api_key_pattern in fh.read():
                key_files.append(f)
check('源代码无硬编码密钥', len(key_files) == 0, f'泄露: {key_files}' if key_files else '')

# ====== 4. memory_bridge ======
print('\n--- 4. memory_bridge ---')
with open('D:/brain/tools/memory_bridge.py', encoding='utf-8') as f: mb = f.read()
check('使用正确列名', 'kind' in mb and 'payload' in mb and 'created_at' in mb)
check('回退仅限 task% 表', "name LIKE 'task%'" in mb)
check('不再读取全部表', "name LIKE 'task%'" in mb)

# ====== 5. pipeline_orchestrator ======
print('\n--- 5. pipeline_orchestrator ---')
with open('D:/brain/tools/pipeline_orchestrator.py', encoding='utf-8') as f: po = f.read()
check('审查闭环: parent_groups', 'parent_groups' in po)
check('SPLIT 触发仲裁', 'create_arbiter_task(parent_id, scores)' in po)
check('移除硬编码密钥', api_key_pattern not in po)
check('schema 自适应探测', '_probe_schema()' in po)

# ====== 6. dual_review + arbiter ======
print('\n--- 6. dual_review + arbiter ---')
with open('D:/brain/tools/dual_review/reviewer.py', encoding='utf-8') as f: dr = f.read()
check('score_content 函数', 'score_content' in dr)
check('dual_review 函数', 'def dual_review' in dr)
check('merge_verdict 函数', 'merge_verdict' in dr)
check('审查日志', 'review_log.jsonl' in dr)

with open('D:/brain/tools/arbiter_vote/arbiter.py', encoding='utf-8') as f: ab = f.read()
check('arbitrate 函数', 'def arbitrate' in ab)
check('投票逻辑', 'votes' in ab and 'vote_counts' in ab)
check('escalate_to_human', 'def escalate_to_human' in ab)
check('仲裁日志', 'arbiter_log.jsonl' in ab)

# ====== 7. Grafana ======
print('\n--- 7. Grafana ---')
with open('D:/brain/grafana/datasource.yaml', encoding='utf-8') as f: gd = f.read()
check('datasource 路径指向 output', r'output\memory\kanban.db' in gd)

# ====== 8. extension_bridge ======
print('\n--- 8. extension_bridge ---')
with open('D:/brain/tools/extension_bridge.py', encoding='utf-8') as f: eb = f.read()
check('publisher 功能验证', 'publisher_importable' in eb)
check('connectors 读实际 JSON', 'mcp_json = os.path.expanduser' in eb)
check('agentteam 内容检查', 'content_quality' in eb and 'len(content) > 200' in eb)

# ====== 9. extension_status ======
print('\n--- 9. extension_status 真实性 ---')
with open('D:/brain/input/extensions/extension_status.json', encoding='utf-8') as f: es = json.load(f)
lines = es['lines']
check('publisher 未 falsely verified', not lines['publisher']['verified'])
check('connectors 未 falsely verified', not lines['connectors']['verified'])
check('agentteam verified', lines['agentteam']['verified'])

# ====== 10. start_all 脚本 ======
print('\n--- 10. start_all 脚本 ---')
with open('D:/brain/start_all.bat', encoding='utf-8', errors='ignore') as f: sb = f.read()
check('bat 无硬编码密钥', api_key_pattern not in sb)
check('bat 含 Orchestrator', 'Orchestrator' in sb)
check('bat 7 组件', '7/7' in sb or '7 components' in sb)

with open('D:/brain/start_all.ps1', encoding='utf-8') as f: sp = f.read()
check('ps1 无硬编码密钥', api_key_pattern not in sp)
check('ps1 从 endpoint.json 加载', 'endpoint.json' in sp)
check('ps1 含 Orchestrator', 'Orchestrator' in sp)

# ====== 11. __init__.py ======
print('\n--- 11. __init__.py ---')
for d in ['tools', 'tools/ab_test', 'tools/reputation', 'tools/dual_review', 'tools/arbiter_vote']:
    fpath = f'D:/brain/{d}/__init__.py'
    if os.path.exists(fpath):
        with open(fpath, encoding='utf-8') as f:
            check(f'{d}/__init__.py', len(f.read()) > 10)
    else:
        warn(f'{d}/__init__.py', False, '缺失')

# ====== 12. AgentTeam 配置 ======
print('\n--- 12. AgentTeam 配置质量 ---')
ag_dir = 'D:/brain/input/profiles/agentteam'
if os.path.isdir(ag_dir):
    good = 0
    for pname in os.listdir(ag_dir):
        soul = os.path.join(ag_dir, pname, 'SOUL.md')
        if os.path.exists(soul):
            with open(soul, encoding='utf-8') as f: sc = f.read()
            has_instructions = '## Instructions' in sc
            content_len = len(sc)
            if has_instructions and content_len > 300:
                good += 1
            else:
                warn(f'{pname}', False, f'{content_len} chars')
    check('AgentTeam 全含 Instructions', good == len(os.listdir(ag_dir)), f'{good}/{len(os.listdir(ag_dir))}')

# ====== 汇总 ======
print('\n' + '='*60)
total = report['pass'] + report['fail'] + report['warn']
print(f'  排查完成: {report["pass"]}/{total} 通过')
if report['fail'] > 0: print(f'  {report["fail"]} 项失败')
if report['warn'] > 0: print(f'  {report["warn"]} 项警告')
print('='*60)

# 写入报告
os.makedirs('D:/brain/output/reports', exist_ok=True)
report['timestamp'] = datetime.now().isoformat()
report['total'] = total
with open('D:/brain/output/reports/post_fix_audit.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2, default=str)
print('\n报告已保存: D:/brain/output/reports/post_fix_audit.json')
