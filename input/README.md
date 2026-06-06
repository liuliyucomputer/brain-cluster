# 📥 输入层 (Input)

Brain集群的**系统输入**统一管理目录。所有驱动系统运行的外部资源、配置和任务入口集中在这里。

## 子目录说明

| 目录 | 用途 | 来源 |
|------|------|------|
| `profiles/` | 9个Agent角色定义(SOUL.md) | agents/ 迁移 |
| `configs/` | 系统配置文件(JSON/YAML) | configs/ 迁移 |
| `extensions/` | 6条扩展线接入指南 | extensions/ 迁移 |
| `tasks/` | 任务输入区(新建) | pending + templates |

## 数据流向

```
input/profiles/  → Hermes Agent Profile 注册
input/configs/   → Hermes Gateway / OpenClaw / ccswitch
input/extensions/ → 外部服务连接器 (企业微信/飞书/publisher等)
input/tasks/     → Kanban 任务创建
```

## 使用示例

```bash
# 注册Agent Profile
for agent in input/profiles/*/; do
  hermes profile create $(basename $agent) --from $agent/SOUL.md
done

# 查看配置
cat input/configs/hermes/gateway.json

# 添加新任务
cp my_task.json input/tasks/pending/
```
