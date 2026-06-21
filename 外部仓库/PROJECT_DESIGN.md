# D:\eyes 开源项目集合 — 系统设计文档

> 多 Agent 共享，长期维护。记录整套系统的设计思路、决策原因、预期效果和版本改动。

---

## 一、系统概览

### 1.1 定位

D:\eyes 是一个**开源项目研究与参考库**，精选 13 个 GitHub 近期高星项目，覆盖 AI 开发工具链的四大领域：

| 领域 | 项目 | Stars | 角色 |
|------|------|-------|------|
| **Skill/规则体系** | andrej-karpathy-skills, harness, Anthropic-Cybersecurity-Skills, Cursor Plugins, claude-plugins-official | 55K/5.9K/14.1K/2K/20.2K | 规则定义、技能架构、规模化范本、插件生态规范 |
| **代码理解** | CodeGraph, Understand-Anything | 40.7K/51.9K | 代码图谱、语义索引 |
| **内容生成** | presenton, MoneyPrinterTurbo, VoxCPM, LongLive, open-notebook | 7.9K/79K/25.8K/8.9K/24.8K | PPT/视频/语音/笔记 |
| **AI 基础设施** | supermemory | 25.5K | 记忆引擎、跨会话上下文 |

### 1.2 核心目标

为 **mdskills 框架** 和 **EliteInteractivePPT 技能** 提供：

1. **Skill 架构参考** — harness 的元技能工厂模式、Karpathy 的规则哲学、Cybersecurity-Skills 的规模化格式
2. **代码感知层** — CodeGraph 的本地语义索引，让 skill 框架具备项目级代码理解能力
3. **内容生成管道** — presenton/MoneyPrinterTurbo/VoxCPM 作为 PPT 技能的上游/平行参考
4. **记忆底座** — supermemory 的跨会话记忆架构，参考其 API 设计

---

## 二、设计决策与原因

### 2.1 为什么选这些项目

| 决策 | 原因 | 权衡 |
|------|------|------|
| harness（5.9K）而非热门 Agent 框架 | 它做的是"元技能"——用 AI 设计 Agent 团队和生成子技能，跟 mdskills 方向一致 | Claude Code 专属，多平台移植需改造 |
| CodeGraph 而非 GitHub Copilot | 本地运行、零 Token 消耗、MCP 协议暴露，适合作为 skill 框架底层 | 仅支持静态分析，无运行时语义 |
| presenton 而非 Gamma API | 开源可定制、支持 18+ LLM、提供 REST API，可直接嵌入自动化工作流 | 需 Docker，部署复杂度较高 |
| VoxCPM 而非 ElevenLabs | Apache 2.0 开源商用、30 语言 9 方言、pip install 即用 | 需 8GB GPU 推理 |
| 全量拉取到本地 | 离线可读、多 Agent 共享同一份代码、避免网络波动 | 占用 ~1.5GB 磁盘 |

### 2.2 不选什么

| 不选 | 原因 |
|------|------|
| LangChain/LlamaIndex | 太重，mdskills 走轻量 Markdown 路线 |
| AutoGPT/AgentGPT | 通用 Agent，与 skill 体系定位不同 |
| ComfyUI | 已有 MoneyPrinterTurbo 覆盖视频生成，不需额外的图像工作流 |
| taste-skill/stop-slop | 概念已通过分析理解，不需拉取代码 |

---

## 三、系统架构

```
D:\eyes
├── PROJECT_DESIGN.md          ← 本文档（设计总纲）
│
├── [Skill/规则层]
│   ├── andrej-karpathy-skills/   → 规则哲学（Think First / Simplicity / Surgical / Goal-Driven）
│   ├── harness/                  → 元技能工厂（7 Phase 工作流，6 种架构模式）
│   ├── Anthropic-Cybersecurity-Skills/ → 技能规模化范本（YAML frontmatter + index.json）
│   ├── claude-plugins-official/  → 官方插件生态规范（plugin.json 标准、Skills/Commands/MCP 扩展）
│   └── plugins/                  → Cursor 插件市场结构参考
│
├── [代码理解层]
│   ├── codegraph/                → 本地代码图谱（tree-sitter → SQLite → MCP）
│   └── Understand-Anything/      → 交互式知识图谱（多 Agent 分析 + React Flow 可视化）
│
├── [内容生成层]
│   ├── presenton/                → AI PPT 生成（FastAPI + Next.js，现成竞品参照）
│   ├── MoneyPrinterTurbo/        → AI 短视频（LLM→TTS→素材→合成）
│   ├── VoxCPM/                   → Tokenizerless TTS（30 语言，48kHz）
│   ├── LongLive/                 → 长视频生成（NVIDIA NVFP4，需 B200 GPU）
│   └── open-notebook/            → NotebookLM 开源替代（Docker 部署）
│
└── [基础设施层]
    └── supermemory/              → 跨会话记忆引擎（MCP + REST API + Python SDK）
```

### 3.1 数据流

```
用户需求
    │
    ▼
mdskills 框架 ─── 规则层（harness/Karpathy 提供模式，Cybersecurity-Skills 提供格式）
    │
    ▼
代码感知层（CodeGraph 提供项目图谱）
    │
    ▼
内容生成层（presenton/VoxCPM/MoneyPrinterTurbo 提供输出能力）
    │
    ▼
记忆层（supermemory 提供跨会话上下文）
```

---

## 四、环境配置记录

### 4.1 已验证可运行（8 个）

| 项目 | 运行方式 | 验证日期 |
|------|---------|---------|
| andrej-karpathy-skills | 直接读 CLAUDE.md | 2026-06-05 |
| harness | 直接读 SKILL.md | 2026-06-05 |
| Anthropic-Cybersecurity-Skills | 直接读 index.json | 2026-06-05 |
| Cursor Plugins | 直接读 marketplace.json | 2026-06-05 |
| CodeGraph | `npm install` → `npm run build` → CLI 验证 | 2026-06-05 |
| Understand-Anything | `pnpm install` → tsc 编译通过 | 2026-06-05 |
| presenton | zip 下载解压（推荐 Docker 运行） | 2026-06-05 |
| MoneyPrinterTurbo | zip 下载解压（pip install -r requirements.txt） | 2026-06-05 |

### 4.2 需要外部依赖（2 个）

| 项目 | 依赖 | 状态 |
|------|------|------|
| open-notebook | Docker Desktop | 代码就绪，待 Docker |
| supermemory | Cloudflare Workers 账号 | 代码就绪，bun 已安装 |

### 4.3 需要 GPU（1 个）

| 项目 | 需求 | 状态 |
|------|------|------|
| LongLive | B200/H100, ≥40GB VRAM | 源码完整，无可用 GPU |

### 4.4 环境变量/工具

```bash
# 已安装的工具
pnpm    # Understand-Anything 依赖管理
bun     # supermemory 运行时
Python 3.12.12  # VoxCPM 环境（uv 管理）
Node 22.22.2    # CodeGraph/前端项目
```

### 4.5 已知问题 & 解决方案

| 问题 | 影响项目 | 根因 | 建议方案 |
|------|---------|------|---------|
| pip install 反复超时 | VoxCPM | PyTorch 123MB + llvmlite 38MB 等大包在沙箱网络下下载太慢 | ✅ **已解决！** CPU-only PyTorch (16MB/s 官方CDN) + PowerShell 分批安装，全量依赖安装成功 |
| Docker 不可用 | open-notebook | 当前环境未安装 Docker Desktop | 源码已完整（29 文件），推荐 `docker compose up -d` 或读源码学习架构 |
| Cloudflare 账号 | supermemory | 自托管需要 Cloudflare Workers | bun 已安装，注册账号后即可部署；当前读源码学习 API 设计即可 |
| 无 NVIDIA GPU | LongLive | 需 B200/H100 ≥40GB VRAM | 仅读 `inference.py` 了解推理流程，不实际运行 |

---

## 五、版本改动记录

### v1.0 — 2026-06-05（初始建立）

**拉取 12 个项目到 D:\eyes**

| 项目 | 获取方式 | 耗时 | 备注 |
|------|---------|------|------|
| andrej-karpathy-skills | git clone | 7s | 一次成功 |
| codegraph | git clone | 8s | npm build 成功 |
| Understand-Anything | git clone | 7s | pnpm install 成功 |
| harness | git clone | 9s | 纯 Markdown |
| Anthropic-Cybersecurity-Skills | git clone | 8s | 纯 Markdown |
| Cursor Plugins | git clone | 7s | 纯 Markdown |
| LongLive | git clone | 7s | 需 GPU |
| VoxCPM | git clone | 9s | ✅ 安装成功（CPU-only PyTorch + 分批 pip install，全量依赖验证通过） |
| open-notebook | git clone | 8s | 需 Docker |
| supermemory | git clone | 9s | 需 Cloudflare |
| presenton | **PowerShell zip 下载** | 6m44s | git clone 多次超时 |
| MoneyPrinterTurbo | **PowerShell zip 下载** | 7m50s | git clone 多次超时 |

**关键问题解决：**
- presenton/MoneyPrinterTurbo：git clone 因 GitHub 网络超时，改用 PowerShell Invoke-WebRequest 下载 zip 解压
- Understand-Anything：npm install 无法触发 pnpm，需 `npm install -g pnpm` 后重试
- VoxCPM：Python 3.13 不兼容（要求 <3.13），用 uv 安装 Python 3.12.12 创建 venv
- CodeGraph：npm.cmd 路径问题，改用 `npm` 直接调用

**环境工具安装：**
- pnpm: `npm install -g pnpm` ✅
- bun: `npm install -g bun` ✅
- Python 3.12: `uv python install 3.12` ✅
- VoxCPM venv: D:\eyes\.venv（Python 3.12，已从 D:\eyes_venv 移入）
- **VoxCPM 安装成功**：CPU-only PyTorch 经官方 CDN (16.3MB/s) + PowerShell 分批安装余下 20+ 依赖，全量验证通过

### v1.2 — 2026-06-08（补充 claude-plugins-official）

**新增项目：claude-plugins-official (20.2K Stars)**

| 项目 | 获取方式 | 备注 |
|------|---------|------|
| claude-plugins-official | git clone | Anthropic 官方 Claude Code 插件注册表，含 30+ 内部插件 + 15 外部合作伙伴插件 |

**定位：** 作为 Skill/规则层的重要补充，提供：
- `plugin.json` 标准规范（插件清单格式）
- Skills / Commands / Agents / Hooks / MCP 五种扩展方式
- `plugin-dev` 插件开发工具包（含 agent-creator、skill-reviewer、plugin-validator）
- `skill-creator` 技能创建器（eval 评估框架）
- `hookify` Hook 规则引擎（Python 实现）
- 外部合作伙伴插件参考（GitHub、Linear、Firebase 等）

**与现有项目的互补关系：**
- `andrej-karpathy-skills` 提供哲学层面的规则思想 → `claude-plugins-official` 提供工程化的插件规范实现
- `harness` 提供元技能工厂模式 → `claude-plugins-official` 提供标准化的插件分发机制
- 为 mdskills 框架提供插件架构的官方参考范本

### v1.1 — 2026-06-05 12:57（D 盘根目录清理）
- 移动 D:\eyes_venv → D:\eyes\.venv（遵循项目内原则）
- 删除 D:\.pnpm-store（519MB pnpm 缓存，从 D 盘根目录清除）
- 删除 presenton.zip(113MB) + MoneyPrinterTurbo.zip(135MB)（248MB 僵尸文件）
- VoxCPM 第 3 轮重试：改用 CPU-only PyTorch + 官方 CDN 加速
- 创建 batch-github-setup skill 固化工作流

---

## 六、多 Agent 维护协议

### 6.1 本文档更新规则

1. **版本改动**：任何项目增删、环境变更、发现重要问题 → 更新第五章
2. **设计决策**：新增项目选择或移除决定 → 更新第二章
3. **架构变更**：层间关系调整 → 更新第三章

### 6.2 项目状态标记

| 标记 | 含义 |
|------|------|
| ✅ 验证通过 | 可立即使用或学习 |
| ⚠️ 环境受阻 | 缺外部依赖但代码完整 |
| 🔧 安装中 | 后台任务进行中 |
| 📦 仅源码 | 只读学习，不运行 |

### 6.3 新增项目流程

1. 在第二章评审：是否符合 4 层架构？
2. 记录拉取方式和耗时
3. 记录环境配置步骤
4. 更新第一章统计表
5. 追加版本改动记录

### 6.4 日常维护

- 每月拉取各项目最新代码
- 每季度重新评审设计决策
- 发现过时项目及时标记废弃

---

*最后更新：2026-06-05 21:13 — VoxCPM 安装成功 + 全 3 任务完成 + 修复重复条目*
*维护者：WorkBuddy Agent，可被任意 Agent 通过 Read 工具加载*
