# -*- coding: utf-8 -*-
"""扫描项目中所有硬编码绝对路径"""
import os, re

exclude_dirs = {'node_modules','.git','__pycache__','venv','data',
                'eyes','openclaw','hermes-agent','dashboard','.workbuddy'}
extensions = ('.py','.json','.yaml','.yml','.bat','.ps1')

results = []
for root, dirs, files in os.walk('D:/brain'):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    for f in files:
        if not f.endswith(extensions):
            continue
        fpath = os.path.join(root, f)
        try:
            with open(fpath, encoding='utf-8', errors='ignore') as fh:
                lines = fh.readlines()
            for i, line in enumerate(lines, 1):
                # 匹配 D:\xxx 或 E:\xxx 等绝对路径
                for m in re.finditer(r'[A-Za-z]:\\[^\s\n\'")}]+', line):
                    path = m.group()
                    # 排除已经是相对/变量路径的
                    if len(path) > 6:
                        results.append((fpath.replace('D:\\brain\\', ''), i, path[:130]))
        except:
            pass

# 按盘符分组
groups = {}
for fp, ln, path in results:
    drive = path[:3]
    if drive not in groups:
        groups[drive] = []
    groups[drive].append((fp, ln, path))

for drive in sorted(groups):
    items = groups[drive]
    print(f'=== {drive} ({len(items)} references) ===')
    for fp, ln, path in items[:8]:
        print(f'  {fp}:{ln}  {path[:110]}')
    if len(items) > 8:
        print(f'  ... and {len(items)-8} more')
    print()

print(f'=== SUMMARY ===')
for drive in sorted(groups):
    print(f'  {drive}: {len(groups[drive])} references')
print(f'  Total: {sum(len(v) for v in groups.values())} hardcoded paths')
