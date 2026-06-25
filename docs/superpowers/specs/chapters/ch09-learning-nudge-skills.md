# ch9 Spec — 学习 Nudge 引擎 + 技能（程序性记忆）/ Learning-nudge engine & skills

## 目标
讲清 Hermes "自我进化"的入口：每隔 N 轮、在 turn 结束（响应已交付）后，fork 一个 background review agent 自问"这轮该存技能 / 记忆吗"——全程**不碰主对话、不碰缓存**；技能是**程序性记忆**（怎么做这一类任务，区别于声明性的 memory）；技能变更默认**延迟失效**（下个会话才进前缀），守住缓存。

## 🎯 章末设计取舍
- 主线：**学习闭环全程不破缓存**——nudge 不往主对话注入任何文字，而是 turn 后 fork 后台 review；技能以 **user 消息**注入（非 system prompt）；技能变更默认 deferred invalidation，`--now` 才立即失效。
- 回指：`B·无状态`（跨会话把"经验"持久化成技能 / 记忆，对抗模型本身记不住）、`A·中间遗失`（技能按需加载、不全塞进 context）、并服务"缓存神圣"（第6章）。

## 真实锚点（逐字 + 文件:行号；以 view 为准，不得臆造）
1. **skill vs memory 边界**：`agent/background_review.py:231-237`（skill="how to do this class of task for this user"，memory="who the user is / current state"）；`tools/memory_tool.py:1021-1023`（"Reusable procedures belong in a skill, not memory"）。
2. **skill nudge 引擎（与 memory nudge 同构）**：`agent._skill_nudge_interval=10` 初始化 `agent/agent_init.py:1235`（config `skills.creation_nudge_interval` :1238）；触发计数 `agent/conversation_loop.py:646` + `agent/turn_finalizer.py:434-435`（`_iters_since_skill >= _skill_nudge_interval`，**turn 结束、响应已交付后**才消费）。
3. **background review fork**（daemon 线程重放 transcript 自问"该存技能/记忆吗"，主对话+prompt cache 全程不动）：`agent/background_review.py:1-8`（docstring 含 "Main conversation and prompt cache are never touched."）；fork 内 `_skill_nudge_interval=0` 防递归 spawn `:669`。
4. **技能注入为 user 消息**（非 system prompt）以保缓存：`agent/skill_commands.py`（模块 docstring "invoke skills via /skill-name commands"；`extract_user_instruction_from_skill_message` :58；`_inject_skill_config` :206）。AGENTS.md：skill slash command "injects as user message (not system prompt) to preserve prompt caching"。
5. **技能延迟失效（cache-aware slash command 典范）**：mutate system-prompt state 的命令默认 deferred invalidation（change takes effect next session），`--now` 立即失效——`/skills install --now` 是 canonical pattern（AGENTS.md「Prompt Caching Must Not Break」）。executor 须 view 核对 `tools/skills_tool.py` / `tools/skills_hub.py` 里 install 的 deferred/now 实现并贴真实片段。
6. **技能产权门控**（只有 background review fork 创建的技能才 created_by="agent"、归 curator 管；前台用户建的不碰）：`tools/skill_provenance.py:75-78`（`is_background_review()` 读 ContextVar）；`tools/skill_manager_tool.py:1082-1084`（`if action=="create": if is_background_review(): mark_agent_created(name)`）。
7. **skill_view 同时 bump use+view**（agent view 即"装入并据此行动"）：`tools/skills_tool.py:1620-1625`。

## 🧩 协作机制框（三段）
- **① 组件清单**：skill nudge 计数（`turn_finalizer`）+ background review fork（self-improvement，独立 AIAgent）+ `skill_commands`（user 消息注入）+ skill provenance 门控 + `skill_usage` 遥测。跨章节：fork review **既存技能也存记忆**（第11章 memory，同一个 fork 两条产出）；技能进 **stable 层**、变更**延迟失效**守缓存（第6章）；curator 只碰 fork 创建的 agent-skill（第10章）；skill nudge 与 memory nudge **同构**（第11章），共用 turn_finalizer 的"turn 后 fork"机制。
- **② 数据流时序**：每轮 `_iters_since_skill++` → 达阈值置 `should_review_skills` → **turn 结束、响应已发给用户后**（`turn_finalizer.py:434`）→ fork background review AIAgent → 重放 transcript 快照、自问"该抽出技能吗" → `skill_manage(create)` 落盘（provenance 标 agent-created）→ **主对话消息序列 / system prompt / 缓存全程零改动** → 新技能要到**下个会话**才进 stable 前缀。
- **③ 关键点**：学习发生在"响应之后的后台 fork"里——既**不与用户任务争模型注意力**，也**绝不改写主对话前缀**。这就是"自我进化"与"缓存神圣"能并存的根本手法：写发生在别处、生效在下次。

## 模板结构
lead → analogy（下班后复盘 / 学徒把"怎么做"记成手册）→ macro（自我进化闭环的入口）→ 主体（skill vs memory 边界 codefile + nudge 触发 codefile + background review fork docstring codefile）→ vflow/timeline（turn → nudge 计数 → 响应交付 → fork review → 落盘，全程标注"主对话/缓存不动"）→ 🧩collab → 🎯design（回指 B/A + 缓存神圣）→ key。

## quiz 考点
- nudge 触发后那段提醒文字注入到哪里（**哪里都不注入主对话**——只置一个布尔，turn 后 fork 后台 review 消费）。
- 技能为什么以 **user 消息**注入而非塞进 system prompt（保缓存：system prompt 一会话只建一次）。
- 技能变更为什么默认**延迟失效**、`--now` 才立即（中途改前缀会击穿缓存）。

## 验收
0 error；codefile 逐字真实（简化块标「· 简化」）；"nudge 不破缓存 + 技能 user 消息注入 + 延迟失效"三点讲清；双语镜像；中文 ≥1500 CJK。
