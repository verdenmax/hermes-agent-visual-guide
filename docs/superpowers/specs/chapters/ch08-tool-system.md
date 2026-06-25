# ch8 Spec — 工具系统：注册 / 门控 / 分派 / 预算 / Tool system: register / gate / dispatch / budget

## 目标
讲清 Hermes 的工具如何"从一个 Python 文件变成模型能调用的能力"，以及为什么每加一个工具都要谨慎：注册表自动发现、check_fn 服务门控（零足迹）、按 toolset 过滤组装 schema、统一 JSON 返回 + 错误净化、execute_code 退还预算。串起"能力在边缘、核心窄腰"。

## 🎯 章末设计取舍
- 主线：**能力在边缘，核心窄腰；工具调用 append-only 不破缓存；check_fn 门控让工具集对一个会话稳定**。每个工具 schema 每次 API 调用都被发送——所以加核心工具的门槛极高（Footprint Ladder）。
- 回指：`A·中间遗失`（工具太多挤占上下文/注意力 → 窄腰 + 门控）、`D·指令=数据`（工具结果是数据：dispatch 错误净化防框架 token 污染）、`E·结构化输出脆弱`（工具 schema=function calling，统一 OpenAI 格式）。

## 真实锚点（逐字 + 文件:行号；以 view 为准，不得臆造）
1. **注册入口 register** — `tools/registry.py:234-310`：`register(name, toolset, schema, handler, check_fn=None, requires_env=None, ...)`；把 check_fn 记到 `_toolset_checks`（:303-304）。
2. **check_fn TTL 缓存** — `tools/registry.py:110-148`：`_check_fn_cached(fn)` 结果缓存 ~30s（:126-141），`invalidate_check_fn_cache()`（:144-148）配置变更后失效。注释逐字解释 TTL 选择理由（env 改动近实时生效，又不必每次全量刷新）。
3. **门控组装 get_definitions** — `tools/registry.py:337-384`：只有 `check_fn()` 返回 True（或无 check_fn）的工具才进 schema（:358-364）；per-call cache（:352）叠加 30s TTL；`dynamic_schema_overrides`（:372-382，如 delegate_task 描述随 config 变）；输出 `{"type":"function","function":schema}`（:383）。
4. **按 toolset 过滤 get_tool_definitions** — `model_tools.py:276-300`：`enabled_toolsets/disabled_toolsets` 过滤，"All tools must be part of a toolset to be accessible"（:285）；memoized（:300，键含 config.yaml mtime+size）。
5. **统一分派 dispatch** — `tools/registry.py:390-416`：`get_entry(name)`→handler；**所有异常**统一包成 `{"error": ...}`（:405-416），且经 `_sanitize_tool_error`（:412）净化，防异常串里的框架 token / CDATA / 围栏作为结构噪声到达模型（注释逐字 :407-409）。未知工具返回 `{"error": "Unknown tool: ..."}`（:399）。
6. **handle_function_call** — `model_tools.py:901`：对外分派入口（agent-level 工具 todo/memory 在 run_agent 里先被截走）。
7. **execute_code 退还预算** — `agent/conversation_loop.py:4117-4122`：仅当本轮 `tool_calls` **全部**是 execute_code（`_tc_names == {"execute_code"}`）才 `agent.iteration_budget.refund()`；`refund()` 定义 `agent/iteration_budget.py:45-49`，docstring 解释 execute_code 是 RPC 式廉价调用不该吃预算（:28-29）。
8.（对照）**Footprint Ladder** — `AGENTS.md:171-195` / `toolsets.py` `_HERMES_CORE_TOOLS`：加新核心工具是最后一档；优先扩展现有 / CLI+skill / check_fn 门控工具 / 插件 / MCP。

## 🧩 协作机制框（三段）
- **① 组件清单**：`registry.register`（自动发现注册）+ `get_definitions`（check_fn 门控）+ `get_tool_definitions`（toolset 过滤+memo）+ `dispatch`（统一 JSON+错误净化）+ `iteration_budget.refund`（execute_code 退还）。跨章节：工具发现链承接窄腰（第4章）；工具结果作为 **tool 消息 append** 进可见上下文、不改前缀（第6章缓存）；check_fn 门控让工具集**会话内稳定**=不中途换 toolset（第6章铁律）；预算退还呼应迭代预算（第5章）；delegate_task 是一个"会生孩子的"特殊工具（第13章委派）。
- **② 数据流时序**：register（import 时）→ get_tool_definitions 按 enabled toolsets 过滤 → get_definitions 跑 check_fn 门控 + dynamic overrides → schema 随每次 API 调用发出 → 模型回 tool_call → handle_function_call → dispatch（异常净化）→ 返回 JSON string → 作为 tool 消息 append → （若全是 execute_code）refund 预算。
- **③ 关键点**：每个工具 schema **每次调用都发送**，所以"加核心工具"成本最高、门槛最高；门控 + toolset 让"昂贵的核心面"保持窄，能力尽量下沉到边缘（CLI/skill/插件/MCP）。

## 模板结构
lead → analogy（机场安检+登机口 / 万能插座面板）→ macro（能力在边缘、核心窄腰）→ 主体（register+check_fn门控 codefile / dispatch 统一返回+错误净化 codefile / execute_code refund codefile）→ flow（register→toolset过滤→check_fn门控→schema→API→tool_call→dispatch→append→refund）→ 🧩collab → 🎯design（回指 A/D/E）→ key。

## quiz 考点
- 为什么"加一个核心工具"门槛最高（每个 schema 每次 API 调用都发送）。
- check_fn 门控的作用与零足迹（前置条件不满足时工具不进 schema，且 30s TTL）。
- 为什么只有"全是 execute_code"时才退还预算。

## 验收
0 error；3 codefile 逐字真实；check_fn 门控 / 错误净化 / execute_code refund 讲清；双语镜像；中文 ≥1500 CJK。
