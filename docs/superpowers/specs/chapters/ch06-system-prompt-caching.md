# ch6 Spec — System Prompt 与 Prompt 缓存 / System prompt & prompt caching

## 目标
全书**核心章**：讲清 system prompt 如何分三层组装、为何会话内 byte 级不变、Anthropic 缓存如何打断点省 ~75%，以及注入前扫描如何守住前缀。

## 🎯 章末设计取舍（design 框）
- 主线：★ **prompt 缓存神圣不可侵犯**——system prompt 每会话只建一次，唯一例外是上下文压缩（第 15 章）。
- 回指 LLM 约束：`A·中间遗失`（关键指令放头尾）、`D·指令与数据分不开`（context 注入前扫描）。

## 真实源码锚点（逐字 + 文件:行号；不得臆造）
1. **三层结构 + 缓存不变量 docstring** — `agent/system_prompt.py:3-20`（逐字）：
   > "The agent's system prompt is built **once per session** and reused across all turns — **only context compression triggers a rebuild**. This keeps the upstream prefix cache warm."
   三层（`\n\n` 连接）：
   - `stable` — identity (SOUL.md / DEFAULT_AGENT_IDENTITY), tool guidance, skills prompt, environment/platform hints, per-model guidance。
   - `context` — caller `system_message` + context files (AGENTS.md / .cursorrules) under `TERMINAL_CWD`。
   - `volatile` — memory snapshot, USER.md profile, external memory provider block, timestamp/session/model/provider line。
2. **缓存策略 system_and_3** — `agent/prompt_caching.py:1-79`：
   docstring：「Single layout: `system_and_3`. 4 cache_control breakpoints — system prompt + last 3 non-system messages, all at the same TTL (5m or 1h). **Reduces input token costs by ~75%**」。
   `apply_anthropic_cache_control()`（49-79）：深拷贝 messages，在 system + 最后 3 条非 system 消息打 `cache_control` marker。
3. **注入前扫描** — `agent/prompt_builder.py:46-62` `_scan_context_content()`：context 文件进 system prompt **之前**扫描 prompt injection（`scan_for_threats(scope="context")`），命中替换为 `[BLOCKED: …]`，注释原文："the file would otherwise enter the system prompt verbatim and the user has no chance to intervene"。
4. **三层组装入口** — `agent/system_prompt.py:113` `build_system_prompt_parts(agent, system_message)` 返回 `{stable, context, volatile}`。

## 🧩 协作机制框（三段，含跨章节配合——这是全书的"缓存神圣"主线汇聚点）
- **① 组件清单**（★本章核心，其余跨章节配合缓存）：`build_system_prompt_parts()`(system_prompt.py:113)、`apply_anthropic_cache_control()`(prompt_caching.py:49)、`_scan_context_content()`(prompt_builder.py:46) ＋ 技能清单→stable(第9章)、memory/USER.md→volatile(第11章)、学习 nudge→末尾 append(第9章)、搜索结果→tool 消息(第12章)、上下文压缩→唯一重建(第15章)、辅助模型→独立 session(第10章)。
- **② 数据流时序**：会话开始 三层组装成固定前缀 → 每轮 `apply_anthropic_cache_control` 打 4 断点命中缓存；读（技能/记忆/搜索）只在会话开始进前缀 **或** 末尾 append；写（nudge/技能/记忆）只 append 末尾、当前会话不重建；**唯一例外** = 压缩重建。
- **③ 关键点**：三层按稳定度排序（stable→context→volatile），把最易变的 memory 压到最后——变了也不殃及前面已缓存的 stable/context。

## 模板结构
lead → analogy（地基/不可拆的承重墙；或缓存如"提前付费的前缀"）→ macro（三层 + 一次构建）→ 主体（`layers` 三层图 + system_prompt docstring `codefile` + prompt_caching `codefile` + prompt_builder 扫描 `codefile`）→ 🧩collab（三段，重点跨章节）→ 🎯design（围绕缓存神圣，回指 A/D，反模式：绝不 mid-conversation 换 toolset/reload memory/rebuild prompt）→ key。

## quiz 考点
- 为什么 memory 放三层最后（保护前缀缓存）。
- system_and_3 打几个断点、省多少（4 个、~75%）。
- 唯一允许重建 system prompt 的时机（上下文压缩）。

## 验收
0 error；3 个 codefile 逐字真实；🧩 协作框必须体现"全局如何配合维护缓存"；双语镜像。
