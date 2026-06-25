# ch13 Spec — 委派与子代理 delegate_task：上下文隔离 + 并行

## 目标
讲清 delegate_task 如何用「上下文隔离」规模化：子代理独立 context/terminal/toolset、只带回摘要、中间结果不进父 context；leaf/orchestrator 角色;单/批量并行;background 完成队列不破缓存。

## 🎯 章末设计取舍
- 主线：**上下文隔离 + 只带回摘要 + 完成队列不破缓存**。
- 回指：`A·中间遗失`(子任务中间结果会淹没父上下文 → 隔离在子context只收摘要)、`F·误差累积`(fresh budget+独立context避免跨任务污染)。

## 真实锚点（explore 逐字采集，见 files/part4-anchors.md；校验须 view 核实）
1. **上下文隔离描述** — `tools/delegate_tool.py:2885-2889` "Each subagent gets its own conversation, terminal session, and toolset. Only the final summary is returned -- intermediate tool results never enter your context window"。
2. **子 AIAgent 隔离构造** — `tools/delegate_tool.py:1219-1250`:隔离=`ephemeral_system_prompt`(只装goal+context)/`skip_context_files=True`/`skip_memory=True`/`clarify_callback=None`/`iteration_budget=None`(fresh);继承=provider/model/api_key/session_db。
3. **role leaf/orchestrator** — `DELEGATE_BLOCKED_TOOLS` :44-53={delegate_task,clarify,memory,send_message,execute_code};role 降级 :1021-1024(`effective_role = role if (role=="orchestrator" and orchestrator_ok) else "leaf"`,orchestrator_ok=enabled and child_depth<max_spawn);_strip_blocked_tools :768-776;orchestrator 保留 delegation :1074-1079。
4. **并发/深度上限** — max_concurrent_children=3(`_DEFAULT_MAX_CONCURRENT_CHILDREN=3` :132);**max_spawn_depth 代码 MAX_DEPTH=1(:139) 但 docstring/AGENTS.md 说2——不一致,草稿故意不写具体数,只说"嵌套深度上限",校验确认这处理 OK**。
5. **background 完成队列** — `tools/async_delegation.py:1-34` docstring:"completions surface as a NEW turn when the agent is idle, never spliced between a tool result and an assistant message. That keeps strict message-role alternation legal and the prompt cache intact"。顶层 model 委派总是 background(run_agent.py:5211-5241)。
6. **durability** — AGENTS.md:982-984 + delegate_tool.py:2909-2914(background NOT durable;用 cronjob 或 terminal background notify_on_complete)。

## 🧩 协作机制框（三段）
- ① 组件清单:delegate_task(单/批量) + 子 AIAgent 隔离构造 + DELEGATE_BLOCKED_TOOLS/role降级 + async_delegation 完成队列。跨章节:delegate_task 是特殊工具(第8章,leaf禁用它防递归);子代理 skip_context_files/skip_memory 不继承父三层prompt/记忆(第6/11章);完成队列只在idle作新turn维持严格交替(第7章)+不破缓存(第6章);隔离 vs 压缩是对抗上下文有限的两条路(第15章)。
- ② 数据流时序:父调delegate_task→构造子AIAgent(隔离历史/上下文文件/记忆,继承运行时)→子独立跑中间结果留子context→只摘要返父→(background)完成事件进队列→父idle作新turn。
- ③ 关键点:把会淹没上下文的中间过程关进子代理独立context,父只收摘要——既护父上下文窗口又(队列idle重入)护父缓存。把复杂度隔离到边缘。

## 模板结构
lead → analogy(外包给独立小组) → macro(上下文隔离只带回摘要) → 主体(子AIAgent隔离构造 codefile + role/BLOCKED_TOOLS codefile + async_delegation docstring codefile) → vflow → collab → design(回指 A/F) → key。

## quiz 考点
- 委派的核心价值(上下文隔离:中间结果不进父context,只带回摘要)。
- leaf 为什么不能调 delegate_task(防无限递归套娃)。
- background 委派完成后为什么不破父缓存(完成事件进队列,父idle才作新turn,不硬插对话中段)。

## 验收
0 error；3 codefile 逐字真实(简化标注);上下文隔离/role/完成队列不破缓存讲清;双语镜像;中文 ≥1500。
