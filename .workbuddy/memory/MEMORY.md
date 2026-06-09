# Brain 项目长期记忆

## 项目约定
- AI 助手名称: **脑机**
- 用户称呼: **礼宇**
- 项目路径: D:\brain
- Python: managed 3.13.12 (C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe)
- Node: managed 22.22.2

## 记忆系统架构
- **daily/**: JSONL 格式 (一行一条记录)，由 memory_bridge.py 写入
- **weekly/**: dreaming_compressor.py short 阶段产出
- **monthly/**: reputation.json + strategies.json，medium 阶段更新
- **vector/**: 长期知识重构，long 阶段产出
- **checkpoints/**: checkpoint.py 5分钟快照

## 信誉评分
- executor-a: 0.7063 (高 — E2E通过)
- 其他 Agent: 0.5 (基线)
- 更新方式: python tools/dreaming_compressor.py medium

## 关键文件
- DESIGN.md: 完整架构设计 (v2.0.0)
- tools/paths.py: 统一路径管理
- tools/dreaming_compressor.py: 三阶段记忆压缩
- tools/v2_integration_test.py: v2.0 集成自检 (20/20 PASS)

## Hermes kanban.db
- 真实位置: %LOCALAPPDATA%\hermes\kanban.db (被 sandbox 阻止)
- 项目副本: D:\brain\output\memory\kanban.db (空壳，0字节)
- Gateway: 18789端口
- Dashboard: 9119端口
