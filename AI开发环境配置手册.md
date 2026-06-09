# AI 开发环境配置手册

> 最后更新：2026-06-07 | 基于 CC Switch v3.16.1 + 硅基流动 API

---

## 一、架构概览

```
Codex CLI / Claude Code
       │
       ▼
 CC Switch 代理 (127.0.0.1:15721)
       │  Responses/ChatCompletions 格式转换
       ▼
 硅基流动 API (api.siliconflow.cn/v1)
       │
       ▼
 DeepSeek-V4-Pro 模型
```

---

## 二、API 密钥

| 供应商 | 密钥 |
|--------|------|
| 硅基流动 (SiliconFlow) | `sk-ukkghdobyfyttizuaxhtqmmdcprycxvdcixoviwhrzlywksx` |

---

## 三、Codex CLI 配置

### 文件位置
- **主配置**: `~/.codex/config.toml`（已锁定只读，CC Switch 无法覆盖）
- **认证**: `~/.codex/auth.json`
- **状态库**: `~/.codex/state_5.sqlite`

### config.toml
```toml
model_provider = "custom"
model = "gpt-5.5"
model_reasoning_effort = "high"

[model_providers.custom]
name = "SiliconFlow"
requires_openai_auth = true
wire_api = "responses"
base_url = "http://127.0.0.1:15721/v1"

[model_providers.custom.properties]
key = "OPENAI_API_KEY"
```

### auth.json
```json
{
  "OPENAI_API_KEY": "PROXY_MANAGED",
  "auth_mode": "apikey"
}
```

### 使用方式
```cmd
codex
```
CLI 中可用 `/model` 切换模型，`/skills` 查看技能列表。

---

## 四、Claude Code 配置

### 文件位置
- **主配置**: `~/.claude/settings.json`（CC Switch 管理）
- **本地覆盖**: `~/.claude/settings.local.json`

### 环境变量
| 变量 | 值 |
|------|-----|
| `CLAUDE_CODE_GIT_BASH_PATH` | `E:\Git\bin\bash.exe` |
| `ANTHROPIC_BASE_URL` | `http://127.0.0.1:15721` |
| `ANTHROPIC_AUTH_TOKEN` | `PROXY_MANAGED` |

### 模型映射（CC Switch 管理）
| Claude 模型 | 实际使用 |
|-------------|----------|
| Haiku 4.5 | DeepSeek-V4-Pro |
| Sonnet 4.6 | DeepSeek-V4-Pro |
| Opus 4.8 | DeepSeek-V4-Pro |

### settings.local.json
```json
{
  "permissions": {
    "allow": [
      "Bash(python ...)",
      "Bash(pip install:*)"
    ]
  }
}
```

### 使用方式
```cmd
claude
```

---

## 五、CC Switch 配置

### 基本信息
- **版本**: v3.16.1
- **安装**: MSI 安装包（`com.ccswitch.desktop`）
- **命令行重启**: `powershell -Command "Start-Process 'shell:AppsFolder\com.ccswitch.desktop'"`

### 代理端口
- **Codex / Claude**: `127.0.0.1:15721`

### 面板操作
1. 系统托盘右键 CC Switch → 打开面板
2. 设置 → 关于：可管理 CLI 工具安装/升级
3. 供应商页：管理 API 供应商和模型映射
4. **重要**：CC Switch 会自动接管 Codex 的 config.toml，如不想被接管需锁定文件为只读

---

## 六、故障排查速查

| 症状 | 原因 | 解决 |
|------|------|------|
| Codex 显示 `Reconnecting...timeout` | 代理未启动 | 打开 CC Switch 面板开启 Codex 代理 |
| Codex 模型显示 `deepseek-ai/DeepSeek-V4-Pro` 而非 `gpt-5.5` | CC Switch 覆盖了 config.toml | 重新写入带 `model_providers.custom` 的配置并锁只读 |
| 对话正常但工具调用失败 | CC Switch Responses↔ChatCompletions 转换不完整 | 已知限制，等待 CC Switch 更新 |
| Claude Code 报 git-bash 缺失 | 环境变量未设置 | `set CLAUDE_CODE_GIT_BASH_PATH=E:\Git\bin\bash.exe` |
| Claude Code 报认证错误 | CC Switch 代理未启动 | 打开 CC Switch 面板确认代理运行 |

---

## 七、快捷操作

### 重启 CC Switch
```powershell
taskkill /F /IM "cc-switch.exe"
powershell -Command "Start-Process 'shell:AppsFolder\com.ccswitch.desktop'"
```

### 手动修正 Codex config.toml（如被 CC Switch 覆盖）
```python
# save as fix.py and run
import os
config = '''model_provider = "custom"
model = "gpt-5.5"
model_reasoning_effort = "high"

[model_providers.custom]
name = "SiliconFlow"
requires_openai_auth = true
wire_api = "responses"
base_url = "http://127.0.0.1:15721/v1"

[model_providers.custom.properties]
key = "OPENAI_API_KEY"
'''
path = os.path.expanduser('~/.codex/config.toml')
with open(path, 'w') as f: f.write(config)
os.chmod(path, 0o444)
```

### 测试代理连通性
```cmd
curl -X POST http://127.0.0.1:15721/v1/responses -H "Content-Type: application/json" -d "{\"model\":\"gpt-5.5\",\"input\":\"hi\"}"
```
