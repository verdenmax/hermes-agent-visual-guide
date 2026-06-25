# ch23 Spec — 插件 / 技能 / MCP：窄腰收束 + Footprint Ladder

## 目标
讲清贯穿全书的窄腰纪律在扩展机制上的落地:能力在边缘扩展、核心保持窄腰。三机制:① 插件(register(ctx) 委托 tools.registry 挂工具/命令/钩子,不改核心文件)② 技能(内容注入为 user message,不进 system prompt=不破缓存)③ MCP(外部工具进 catalog)。用 Footprint Ladder(扩展现有→CLI+技能→服务门控工具→插件→MCP→新核心工具)指导"加能力选最小足迹那一阶"。

## 🎯 章末设计取舍（双 badge A + G）
- 主线：**Footprint Ladder——能力推到边缘,核心保持窄腰**。
- `A·中间遗失`：每个核心工具 schema 都进每次 API call 的 context;工具越多 context 越膨胀,真正要用的越淹没(中间遗失)。能力压到边缘,核心工具集精简。
- `G·运维`：每个核心工具是永久维护负担(每次 API call 发、所有平台带);边缘扩展近零核心成本。

## 真实锚点（已 view 逐字核对）
1. **插件挂工具** — `hermes_cli/plugins.py:367-400` `class PluginContext` `def register_tool(self, name, toolset, schema, handler, check_fn=None, requires_env=None, ..., override=False)` docstring "Register a tool in the global registry **and** track it as plugin-provided. Pass override=True to replace an existing built-in tool..." → `from tools.registry import registry; registry.register(name=name, toolset=toolset, schema=schema, handler=handler, check_fn=check_fn, ..., override=override)`;`plugins.py:30` 注释 "PluginContext.register_tool() delegates to tools.registry.register()"。
2. **生命周期钩子** — `plugins.py:128-155` `VALID_HOOKS: Set[str] = {"pre_tool_call", "post_tool_call", "transform_terminal_output", "transform_tool_result", "transform_llm_output", "pre_llm_call", "post_llm_call", "pre_api_request", "post_api_request", "api_request_error", "on_session_start", "on_session_end", "on_session_finalize", "on_session_reset", "subagent_start", "subagent_stop", "pre_gateway_dispatch", ...}`。
3. **技能注入 user message(★)** — `agent/skill_commands.py:245-282` `def _build_skill_message(loaded_skill, skill_dir, activation_note, user_instruction="", ...)` docstring "Format a loaded skill into a user/system message payload." → `content = str(loaded_skill.get("content") or "")` → `parts = [activation_note, "", content.strip()]` → `if skill_dir: parts.append(f"[Skill directory: {skill_dir}]")`。技能作为 user message 注入(AGENTS.md「skill slash commands... injected as user message (not system prompt) to preserve prompt caching」)。
4. **其他注册接口** — `plugins.py:437` register_cli_command(hermes <subcmd>)、`:817` register_platform(平台适配器=插件,印证 ch17)、`:1044` register_hook。
5. **Footprint Ladder + Teknium 规则** — AGENTS.md「The Footprint Ladder」6 阶(extend existing→CLI+skill→service-gated tool check_fn→plugin→MCP server in catalog→new core tool last resort)+「plugins MUST NOT modify core files (run_agent.py, cli.py, gateway/run.py...)」;动机「every model tool we add is sent on every API call, so the bar for a new core tool is high」。

## 🧩 协作机制框（三段）
- ① 组件清单:PluginContext.register_tool(插件挂工具) + VALID_HOOKS(生命周期扩展点) + 技能 user message 注入 + MCP catalog。跨章节:register_tool 委托的是工具系统(第 8 章)那个 registry,服务门控用同一 check_fn;技能注入 user message 不进 system prompt=不破缓存(第 6 章);钩子在工具/LLM/会话/子代理(第 13 章)固定节点触发;平台适配器(第 17 章)、记忆后端(第 11 章)、provider 都是插件。
- ② 数据流时序:新能力 → Footprint Ladder 选阶 → 插件 register(ctx)(register_tool/register_hook)或技能(user message 注入)或 MCP(catalog) → 边缘挂载,核心工具 schema 不膨胀。
- ③ 关键点:能力在边缘扩展核心保持窄腰;插件不改核心文件(Teknium 铁律)、技能注入 user message 保缓存、MCP 把外部工具关在 catalog。新核心工具是最后手段(每个都在每次 API call 发送)。

## 模板结构
lead → analogy(瑞士军刀 vs 工具箱) → macro(Footprint Ladder) → 主体(register_tool codefile + VALID_HOOKS codefile + _build_skill_message codefile) → vflow → collab → design(回指 A+G) → key。

## quiz 考点
- 加个新能力为什么不直接加成核心工具(每个核心工具的 schema 都在每次 API call 发送→膨胀 context 稀释注意力(A·中间遗失)+ 永久维护(G);Footprint Ladder 逼你先选更高那一阶)。
- 插件怎么给 Hermes 加工具而不碰核心文件(register(ctx) 的 register_tool 委托同一个 tools.registry,Teknium 铁律:插件绝不改核心文件)。
- 技能内容为什么注入成 user message 而不是塞进 system prompt(system prompt 一改就击穿整会话缓存前缀;user message 是 append-only,缓存不作废)。

## 验收
0 error；3 codefile 逐字真实(register_tool/VALID_HOOKS/_build_skill_message;docstring `"""` 写 `&quot;`);footprint ladder/插件不改核心/技能保缓存讲清,缓存线呼应;双语镜像;回指 A+G;中文 ≥1500(接近,最后补)。
