# 六条扩展路线 — 接入本机已有资产

> Brain 集群跑通后，按优先级逐条接入

---

## 扩展一：AgentTeam 12角色接入（最优先）

### 资产
`B:\AgentTeam\` — 12角色多智能体系统（commander/analyst/researcher等）

### 接入方案
1. 为每个角色创建 Hermes Profile
2. 注册到信誉评分系统
3. 策略龙自动路由任务到对应专家

### 接入后效果
执行龙从 3 个通用分身 → 15 个垂直领域专家

---

## 扩展二：CodeBuddy 5个Skill暴露为工具（高优先）

### 资产
ppt-pro-master / xhs-creator-studio / resume-screener / financial-analysis / work-report

### 接入方案
1. 每个 Skill 注册为 Hermes Tool
2. Agent 通过 `hermes tool call` 直接调用
3. 产出通过文件系统共享

### 接入后效果
Agent 不需要重写 PPT生成/小红书发布 逻辑，已有最佳实践直接复用

---

## 扩展三：小红书/抖音发布管道（高优先）

### 资产
- `B:\CLI\电商项目\` — 发布脚本
- `C:\...\Claw\xhs_publisher.py` — 小红书半自动发布

### 接入方案
1. 封装 `publish_xiaohongshu(title, body, images, tags)` 为 Hermes Tool
2. Agent 生成内容 → 自动填表 → 人工点发布

### 接入后效果
内容生产 → 发布全链路闭环

---

## 扩展四：21个连接器（中优先）

### 资产
企业微信/飞书/钉钉/GitHub/Gongfeng/腾讯文档/金山文档/天眼查/企查查等

### 接入方案
1. 监控龙异常推送到企业微信/钉钉
2. Agent 产出自动同步到腾讯文档
3. 调研龙可查天眼查企业数据

### 接入后效果
集群与外部世界打通，告警实时推送到手机

---

## 扩展五：codeWhale 重型任务引擎（中优先）

### 资产
`B:\codeWhale\` — Rust 终端编程Agent (DeepSeek V4)

### 接入方案
1. 注册 codeWhale 为 Hermes Profile "codewhale-executor"
2. 代码/编译/终端类任务自动路由给它
3. GPT-5.5 做策略，codeWhale 做执行

### 接入后效果
文本推理（GPT-5.5）+ 终端操作（codeWhale）互补

---

## 扩展六：金融自动化（可后置）

### 资产
- `B:\A_share_News_Face_Analysis_System\` — A股舆情分析
- `B:\Stock_Market_Ultimate_Game\` — 股市模拟
- `B:\变现执行\` — 变现自动化

### 接入方案
1. 舆情分析龙 = Hermes Profile "sentiment-analyzer"
2. 每日自动扫描A股舆情 → 策略龙判断 → 执行龙操作

### 接入后效果
集群从纯内容生产 → 内容+金融双线自动化
