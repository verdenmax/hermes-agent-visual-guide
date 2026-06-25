# Hermes Agent 图解学习指南 · 设计文档（spec）

- 日期：2026-06-25
- 主题：仿照 `llama-cpp-visual-guide` 形态，制作一份**详细、双语、图解**的
  Hermes Agent 设计原理学习指南
- 落盘：`/home/verden/course/hermes-agent-visual-guide/`
- 状态：设计已逐节确认，待用户审阅本 spec 后转入实施计划（writing-plans）

---

## 1. 背景与目标

### 1.1 这份指南要回答的问题

用户想吃透 **NousResearch/hermes-agent 在设计每个部件时"考虑了什么"**——
不是 API 用法手册，而是**设计取舍的讲解**：每个功能为什么这么做、它在
对抗 LLM 的哪个固有缺陷、它如何与全局其他子系统咬合配合。

核心叙事是一条 **"病 → 药"主线**：LLM 有一批固有约束（注意力/无状态/
幻觉/提示注入/误差累积……），Hermes 的几乎每个设计都是在治其中某个病。
指南把这条主线显式化、贯穿全书。

### 1.2 目标读者与用途

- 主：用户本人，用于**深入理解 agent 系统设计**，并可能用于**面试准备**
  （"面试很可能会问的线"）。
- 形态：自包含、可离线浏览的静态网站 + 可导出 PDF。

### 1.3 非目标（YAGNI）

- 不是 Hermes 的使用教程 / 安装文档。
- 不逐行复制 Hermes 源码；只引用**少量、标注来源**的真实片段。
- 不覆盖纯前端皮肤细节、营销内容。

---

## 2. 形态与技术架构

**完全仿照 `llama-cpp-visual-guide` 的零依赖 Python 生成器**（已实地研读其
`src/shell.py`、`src/part1.py`、`README.md` 确认形态）。

### 2.1 文件结构

```
hermes-agent-visual-guide/
├── src/
│   ├── partN.py        # 每章双语内容：LESSON_XX = {"zh": r"...", "en": r"..."}
│   ├── shell.py        # 页面外壳 + 共享 CSS 设计系统 + PAGES 有序清单
│   ├── quizzes.py      # 每章自测题（双语）
│   ├── registry.py     # 文件名 -> 内容 有序映射
│   ├── build.py        # 生成 lessons/*.html + index.html
│   ├── build_print.py  # 生成 print_zh.html + print_en.html
│   ├── check_html.py   # 结构校验（0 error / 0 warning）
│   └── check_links.py  # 内链校验（全部可解析）
├── lessons/            # 生成的章节页（提交、与源保持同步）
├── index.html          # 生成的目录页（提交）
├── print_*.html        # 生成的打印版（提交）
├── docs/superpowers/   # 设计 spec 与实施计划
├── README.md           # 项目说明 + 构建方式 + 双许可声明
├── LICENSE             # 代码 MIT
└── LICENSE-CONTENT     # 内容 CC BY 4.0
```

> 生成的 HTML 提交进 git 并与源保持同步：重跑 `build.py` 应无 diff。
> **不要手改生成的 HTML**——改 `src/partN.py` 后重跑 `build.py`/`build_print.py`。

### 2.2 关键决策（已确认）

| 维度 | 决策 |
|---|---|
| 语言 | **中英双语**，页内可切换（与 llama-cpp 完全一致） |
| 配色 | **Hermes 品牌金色**（☤，`#FFD700` / `#c8a02c` 系），区别于 llama-cpp 橙 |
| 范围 | **全景覆盖**，25 章 / 7 部分（见 §4） |
| 依赖 | 零依赖纯 Python 3，无构建工具链 |

---

## 3. 内容真实性与许可

### 3.1 真实性纪律（硬约束）

> 教训记录：第一次口头分析时，曾把 `learn_prompt.py` 误述为含
> `SKILL_NUDGE_MIN_TURNS=12` 等 nudge 触发常量——经核实**与真实源码不符**
> （该文件实为 `/learn` 命令的 prompt 构建器）。因此本指南立下纪律：

- 每段 **prompt / 代码 / 常量 / 阈值**都必须来自**逐字读到的源码**，
  并标注 `文件:行号`。绝不臆造函数名、常量、路径。
- 代码片段要么是**真实原文**，要么显式标注"简化自 `文件:行号`"。
- prompt 原文优先**逐字引用**（用户强调 prompt 极重要）。
- 实现每一章前，先用 `view`/`grep` 把该章涉及的源码读实，建立"事实锚点"
  清单，再落笔。

### 3.2 已验证的事实锚点（样章可直接用）

- `agent/system_prompt.py:3-20` — system prompt 三层结构（stable / context /
  volatile）+ "built **once per session** … only context compression triggers
  a rebuild … keeps the upstream prefix cache warm" 的 docstring 原文。
- `agent/prompt_caching.py:1-79` — `system_and_3` 缓存策略真实代码：
  system + 末 3 条非 system 消息共 4 个 `cache_control` 断点，
  "Reduces input token costs by **~75%**"。
- `agent/prompt_builder.py:46-62` — `_scan_context_content()`：上下文文件
  进 system prompt **之前**扫描提示注入，命中替换为 `[BLOCKED: …]`。
- `agent/learn_prompt.py:30-109` — `_AUTHORING_STANDARDS` + `build_learn_prompt()`
  真实 prompt 原文（第 9 章技能用）。

### 3.3 声明与许可

- 第三方、非官方教育材料；**不含 Hermes 源码**，仅引用少量标注来源的片段。
- 双许可：代码（`src/` 生成器/校验脚本）**MIT**；内容（课程文字与图）
  **CC BY 4.0**。

---

## 4. 全书结构（25 章 / 7 部分）

**双层叙事**：每章讲一个功能 + 章末「🎯设计取舍」点明它围绕的设计主题
（纵向）；最后一章把所有主题串成设计线矩阵（横向收束）。

| # | 章节 | 🎯 章末围绕的设计主题 |
|---|---|---|
| **一 · 宏观全景** | | |
| 1 | Hermes 是什么：自我进化的个人 AI agent | 产品愿景：内建学习闭环 + 处处可达 |
| 2 | 你在和什么打交道（上）· 单次调用的真相 | LLM 约束 A 上下文 / B 无状态&非确定 / E token 表示层 |
| 3 | 你在和什么打交道（下）· 自主化的代价 | LLM 约束 C 真实性 / D 指令遵循 / F 多步自主 / G 运维 |
| 4 | 项目全景地图：一个 agent core，五种前端 | 窄腰架构（core 窄、边缘宽） |
| 5 | 一次对话的生命周期（端到端追踪） | 同步循环 + 消息角色交替；可中断 + 迭代预算 |
| **二 · Agent 核心** | | |
| 6 | System Prompt 与 Prompt 缓存 | ★ prompt 缓存神圣不可侵犯 |
| 7 | 消息流与 provider 适配（多后端） | 严格角色交替不变量 |
| 8 | 工具系统：registry / toolsets / 发现 | 窄腰 + Footprint Ladder |
| **三 · 自我进化闭环** | | |
| 9 | 学习 Nudge 引擎 + 技能（程序性记忆） | 用 user 消息驱动学习；技能延迟失效 |
| 10 | Curator：技能生命周期园丁 | 数据安全 + 辅助模型隔离 |
| 11 | 记忆：MEMORY/USER + Provider + Honcho | 读/写方向分离保护缓存 |
| 12 | 跨会话搜索：SessionDB + FTS5 + 摘要 | 本地零成本检索 + 召回不破缓存 |
| **四 · 规模化与隔离** | | |
| 13 | 委派与子代理：delegate_task | 上下文隔离 + 并行 |
| 14 | 委派的规划/执行分离 + 审查 | 生成-验证差 / 谄媚的对策 |
| 15 | 上下文压缩 | 缓存铁律的唯一例外；对抗上下文腐烂 |
| 16 | 终端后端：local/docker/ssh/modal/… | 环境可移植 + serverless 省钱 |
| **五 · 多端与网关** | | |
| 17 | 网关与多平台适配器（单进程驱动 20+） | 共享 core + 适配器模式 |
| 18 | 网关消息守卫：两道 guard / 审批 / 旁路 | 运行中安全控制；提示注入隔离 |
| 19 | TUI 与桌面：Ink + JSON-RPC + PTY | TS 拥屏 / Python 拥会话 |
| 20 | 配置与 Profiles：多实例隔离 | 配置分层 + profile 隔离 |
| **六 · 自动化与研究** | | |
| 21 | Cron 与 Kanban：调度 + 多 agent 队列 | 不破缓存的后台自动化 |
| 22 | 评测、批量与轨迹压缩 | 研究向数据生成；模型版本漂移对策 |
| 23 | 插件 / 技能 / MCP：在边缘扩展 | 窄腰的边缘扩展哲学 |
| **七 · 速查** | | |
| 24 | 安全与威胁模型横向专题 | 提示注入 / 上下文中毒 / 最小权限 全局视角 |
| 25 | 设计原则横向收束：主题矩阵 + 术语表 | 全书设计线总览（横向收束） |

> 说明：原拟 23 章，因纳入 LLM 约束地基课（第 2-3 章）与安全横向专题
> （第 24 章）扩为 25 章。Part 划分与顺序在实施前可再微调。

---

## 5. LLM 约束框架（A–G）与章节映射

地基课（第 2-3 章）集中讲解；后续每章「🎯设计取舍」框回指对应约束编号；
第 25 章汇成"约束 × 对策"矩阵。⭐ / ⭐⭐ = 重点 / 最重磅。

| 约束 | 关键项 | 主要落地章节 |
|---|---|---|
| **A 上下文** | 中间遗失 | 6（头尾）· 11 · 12 |
| | ⭐上下文腐烂 | 15（压缩为质量，不只省钱） |
| | 延迟/成本随长度 | 5 预算 · 15 |
| **B 无状态/不确定** | ⭐无状态 | 5（state 外置于 messages）· 9 · 11/12 |
| | ⭐自回归不可回退 | 9 先规划 · 14 规划/执行分离 |
| | 非确定性 | 22 eval / 容忍式测试 |
| **C 真实性** | ⭐幻觉+校准差 | 12 检索接地 · 8 工具验证 |
| | ⭐上下文中毒 | 11 · 21 cron 不污染主会话 · 24 |
| | 知识截止 | 6 注入当前日期 · 8 web 工具 |
| **D 指令遵循** | ⭐⭐指令与数据分不开（注入） | 18 守卫 · 14 特权规划器 vs 隔离数据处理器 · 8 最小权限 · 24 |
| | ⭐谄媚 | 14 独立批评者（background_review） |
| | 生成-验证差 | 14 · 22 |
| | 提示脆弱 | 6 byte-stable · 22 eval |
| **E 表示层** | ⭐分词/数学弱 | 8（交给 execute_code/计算器） |
| | 结构化输出脆弱 | 7 function calling/JSON/语法约束 |
| | 输出截断 | 15 分块续写 · 7 |
| **F 多步自主** | ⭐⭐误差累积 | 13 短回路/分解/检查点 · 5 步数预算 · 9 todo |
| | ⭐长程规划漂移 | 9 目标追踪 · 21 kanban · 重新接地 |
| | 工具越多越不准 | 8 窄腰/小正交集/动态加载/服务门控 |
| **G 运维** | ⭐模型版本漂移 | 22 回归 eval + 固定版本 |
| | 成本/延迟/限流不对称 | 5 预算 · smart_model_routing · 10/12 auxiliary 便宜模型 |
| | 推理 token 不跨轮持久 | 7 reasoning 存储 + 关键结论落可见上下文 |

---

## 6. 每章模板 v2（5 段式）

每章固定结构，尽可能详细、贴真实源码原文与真实 prompt：

1. **导语 lead** — 一句话点题。
2. **主体讲解** — 概念 + 🔌生活类比 + 🌍宏观理解 + 手绘 SVG 图
   （flow/layers/自定义）+ 真实代码块 / 真实 prompt 原文。
3. **🧩 协作机制框**（细分三段，**含跨章节配合的全局组分**）：
   - **① 组件清单** — 本章成分（模块/函数/数据结构/prompt）**＋ 其他章节/
     子系统中配合实现本章目标的组分**，每条标注来源（`文件:行号` 或 `第 N 章`）
     与"如何配合"。
   - **② 数据流时序图** — 手绘 SVG，端到端展示这些组件（含跨章节的）按时序
     如何咬合实现本章目标。
   - **③ 真实原文** — 贴该章相关的真实源码片段 + 真实 prompt 原文（标注来源）。
4. **🎯 设计取舍框**（加详）：核心设计原则 + **为什么**（贴证据：源码注释/
   文档/数字）+ 各机制如何服务该目标 + 回指 LLM 约束（A–G 编号）+
   反模式警示。
5. **quiz** — 双语自测题（2-4 题，含参考答案）。

### 6.1 样章基准（第 6 章 · System Prompt 与 Prompt 缓存）

已用真实源码搭出样章并获确认，作为全书"详细度 + 真实度"基准：

- 主体：三层结构（stable→context→volatile，按稳定度排序）+ docstring 原文。
- 🧩协作机制 ①组件清单：`build_system_prompt_parts()`、
  `apply_anthropic_cache_control()`、`_scan_context_content()`（本章核心）
  ＋ 技能清单→stable（第 9 章）、memory/USER.md→volatile（第 11 章）、
  nudge→末尾 append（第 9 章）、搜索结果→tool 消息（第 12 章）、
  压缩→唯一重建（第 15 章）、辅助模型→独立 session（第 10 章）。
- 🧩协作机制 ②时序：会话开始组装固定前缀 → 每轮打 4 断点命中缓存 →
  读只进前缀或末尾 append / 写只末尾 append、当前会话不重建 → 唯一例外=压缩。
- 🧩协作机制 ③原文：`system_prompt.py:3-20` + `prompt_caching.py:49-79` +
  `prompt_builder.py:46-62`。
- 🎯设计取舍：围绕 ★prompt 缓存神圣；为什么=~75% 省钱 + "Cache-breaking
  forces dramatically higher costs"；回指 A-中间遗失、D-⭐⭐注入；
  反模式=绝不 mid-conversation 换 toolset/reload memory/rebuild prompt。

---

## 7. 教学组件清单（沿用 + 新增）

沿用 llama-cpp 设计系统（在 `shell.py` 的共享 CSS 中定义）：

- `card analogy`（🔌生活类比）、`card macro`（🌍宏观理解）
- `cols`/`col` 双栏对比、`table.t` 表格
- `flow`（node/arrow 流程）、`layers`（分层塔）、自定义 SVG 手绘图
- `pre.code` 深色代码块（`cm` 注释 / `st` 字符串 / `mono` 等高亮 span）
- `lead` 导语、`inline`/`mono` 行内标记

新增（本指南特有）：

- `card collab`（🧩协作机制，三段式）
- `card design`（🎯设计取舍）
- `badge constraint`（A–G 约束回指小标签，如 `D⭐⭐`）

---

## 8. 构建与校验

```bash
cd src
python3 build.py          # 生成 index.html + lessons/*.html
python3 build_print.py    # 生成 print_zh.html + print_en.html
python3 check_html.py     # 结构校验：期望 0 error / 0 warning
python3 check_links.py    # 内链校验：全部可解析
```

生成产物提交进 git，重跑 `build.py` 应无 diff。

---

## 9. 验收标准

- [ ] 25 章全部生成，`index.html` 导航连通、`check_links.py` 0 失败。
- [ ] `check_html.py` 0 error / 0 warning。
- [ ] 每章具备完整 5 段式（含 🧩协作机制三段 + 🎯设计取舍 + quiz）。
- [ ] 双语对齐：每章 zh/en 内容结构一致、可页内切换。
- [ ] **真实性核验**：每章引用的 prompt/代码/常量均可在 Hermes 源码中按
      标注的 `文件:行号` 复核；无臆造。
- [ ] 每章「🎯设计取舍」框均回指至少一个 LLM 约束（A–G）。
- [ ] 第 25 章矩阵覆盖 A–G 全部约束 × 对应 Hermes 对策。

---

## 10. 实施分期（对应 writing-plans，逐 Part 推进）

按 Part 分批，每批：先建该批各章的"事实锚点"清单（读实源码）→ 写
`src/partN.py` 双语内容 + `quizzes.py` → `build.py` → 校验 → 提交。

1. 阶段 0：脚手架（`shell.py` 含金色 CSS + 两个新框样式、`build*.py`、
   `check_*.py`、`registry.py`、`index.html`、README、双 LICENSE）。
2. 阶段 1：第一部分（1-5 章，含 LLM 约束地基课）。
3. 阶段 2：第二部分（6-8，Agent 核心；第 6 章样章先行定基准）。
4. 阶段 3：第三部分（9-12，自我进化闭环）。
5. 阶段 4：第四部分（13-16，规模化与隔离）。
6. 阶段 5：第五部分（17-20，多端与网关）。
7. 阶段 6：第六部分（21-23，自动化与研究）。
8. 阶段 7：第七部分（24-25，安全专题 + 横向收束）。

> 用户偏好：实施计划逐段写、一点一点来；大文件分多次小改 edit。

---

## 11. 风险与对策

| 风险 | 对策 |
|---|---|
| Hermes 源码巨大（run_agent.py ~12k 行），易读偏/读不全 | 每章先用 grep 定位 + view_range 精读相关段；建事实锚点清单再落笔 |
| 引用失真（已发生一次） | §3.1 真实性纪律；验收做 `文件:行号` 复核 |
| 双语工作量翻倍 | 逐 Part 推进；zh 先行、en 紧随；结构镜像 |
| 跨章节协作描述前后不一致 | 以"缓存神圣/窄腰/自我进化/隔离"等主线为锚，第 25 章矩阵统一校对 |
| 章节过多导致烂尾 | 分期交付，每阶段可独立构建、可浏览 |
