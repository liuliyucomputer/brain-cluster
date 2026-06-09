# Brain Cluster 维护日志

## 2026-06-07: 仪表板 v3 全面重构

### 1. WebGL 上下文泄漏
- **时间**: 17:05
- **问题**: 3D 场景频繁出现 "Too many active WebGL contexts" 警告
- **原因**: ClusterGlobe 组件每次数据轮询（3s）都销毁并重建整个 Three.js 场景
- **改动**: 改为一次性场景初始化 + 增量数据更新模式，useEffect([]) 创建场景，单独 useEffect 更新 mesh 属性
- **结果**: WebGL 上下文稳定在 1 个，警告消除

### 2. Gateway 启动失败 (409 CONFLICT)
- **时间**: 16:08~17:11
- **问题**: 面板 Start 按钮无法启动 Gateway，端口 18789 无响应
- **原因**: (a) 旧进程 PID 24936 占用端口 9119；(b) `hermes gateway run` 在 subprocess 中执行时检测到 PID 锁文件报 "already running"；(c) `cmd /c` 传递 env vars 方式不兼容
- **改动**: 添加 `--replace` 标志到 gateway 命令；使用 `shell=True` 执行；杀掉僵尸 hermes 进程
- **结果**: Gateway 可通过面板启动，但需要完整消息平台配置

### 3. start_all.bat Python 语法错误
- **时间**: 22:57
- **问题**: `SyntaxError: unterminated string literal` 导致 API Key 加载失败
- **原因**: `%~dp0` 展开为 `D:\brain\`（末尾 `\`），在 `r'...'` Python 字符串中 `\'` 被解释为转义引号
- **改动**: 用 `%BRAIN_ROOT%` 替代 `%~dp0`（无尾随 `\`）；新增 siliconflow 配置回退路径
- **结果**: API Key 正常加载

### 4. 事件流时间戳虚假
- **时间**: 23:30
- **问题**: 所有事件显示相同时间 `23:28:41`
- **原因**: `new Date().toLocaleTimeString()` 取浏览器当前时间，19997 API 不返回 `time` 字段
- **改动**: 移除虚假时间戳，改为倒排序号 `#15`~`#1`
- **结果**: 事件顺序清晰，无误导

### 5. 多终端窗口弹出
- **时间**: 23:05
- **问题**: start_all.bat 启动时弹出 7 个 CMD 窗口
- **原因**: 所有 `start` 命令未最小化
- **改动**: 全部 `start` 命令加 `/MIN` 标志；所有输出重定向到日志文件；末尾 5s 自动打开面板
- **结果**: 启动时无终端弹窗

### 6. 旧面板残留 (19997 dashboard.html)
- **时间**: 23:02
- **问题**: `:19997/dashboard.html` 仍显示旧版面板
- **原因**: monitor_dashboard.py 路由未更新
- **改动**: `monitor_dashboard.py` 的 `/` 和 `/dashboard.html` 均改为 302 重定向到 `:18791/dashboard-v2`
- **结果**: 所有旧面板入口自动跳转新面板

### 7. 面板布局重构
- **需求**: 从平面卡片改为 3D 立体 + 实时数据 + 中文优先
- **新增组件**: ClusterGlobe(Three.js 3D)、PipelineFlow(6阶段柱状图)、AgentMatrix(中文标签)、EventStream(事件流)、LogPanel(21源日志)、ExecutionFlow(执行流全景)、ExtensionsPanel(扩展状态)、ServicePanel(Start/Stop)
- **移除组件**: ActivityTimeline、LearningPanel、ArchitectureView(静态SVG)、PipelineView、AgentGrid
- **关键改动**: `_compute_stats` 改为 TCP port check 替代 HTTP health check；新增 `/api/monitor` 代理 19997 数据；新增 `/api/logs/*` 日志端点
