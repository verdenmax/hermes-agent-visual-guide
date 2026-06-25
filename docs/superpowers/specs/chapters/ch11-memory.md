# ch11 Spec — 记忆：MEMORY.md / USER.md / Provider / Honcho

## 目标
讲清 Hermes 记忆如何「写入随时、注入守缓存」：MEMORY.md(agent笔记)/USER.md(用户画像) 声明性记忆；两条注入路径——①冻结快照进 system prompt volatile ②实时 prefetch 只贴当前 user 消息副本；memory nudge 不注入主对话；MemoryProvider/MemoryManager/Honcho 可插拔。

## 🎯 章末设计取舍
- 主线：**冻结快照 + 只贴当前 user 消息副本**，两条注入路径都绕开「会话中途改 system prompt」=守缓存。
- 回指：`B·无状态`(跨会话记住用户)、`A·中间遗失`(prefetch 按需取回非全塞)、`D·指令=数据`(<memory-context> 围栏 + 快照构建注入扫描)。

## 真实锚点（逐字 + 文件:行号；核心 3 个已 view 核对）
1. **冻结快照** — `tools/memory_tool.py:567-578` `format_for_system_prompt`：docstring "Return the frozen snapshot... captured at load_from_disk() time, NOT the live state. Mid-session writes do not affect this... preserving the prefix cache"；`block = self._system_prompt_snapshot.get(target, "")`。
2. **prefetch 副本注入** — `agent/conversation_loop.py:738-758`：`api_msg = msg.copy()`；注释 "the original message in messages is never mutated, so nothing leaks into session persistence"；`if idx == current_turn_user_idx and msg.get("role")=="user":` → `build_memory_context_block(_ext_prefetch_cache)` → `api_msg["content"] = _base + "\n\n" + fenced`。
3. **memory nudge** — `agent/turn_context.py:249-260`：注释 "Preserve the original user message (no nudge injection)"；`should_review_memory=False`；`if (agent._memory_nudge_interval > 0 and "memory" in agent.valid_tool_names and agent._memory_store): agent._turns_since_memory += 1; if >= interval: should_review_memory=True; reset 0`。与 ch9 skill nudge 同构，turn_finalizer fork 消费。
4.（正文/校验核实）**定义/上限** — `tools/memory_tool.py:5-14`；MEMORY.md ~2200 / USER.md ~1375 chars（`agent/agent_init.py:1154-1155` 核实）；存 `$HERMES_HOME/memories/`。
5.（正文/校验核实）**MemoryManager 单外部 provider** — `agent/memory_manager.py:335-360`（第二个外部 provider 被拒，防 schema 膨胀）；`build_memory_context_block` 围栏 ~`memory_manager.py:297-311`；MemoryProvider ABC `agent/memory_provider.py:43-315`；Honcho 注入 user 消息非 system prompt。

## 🧩 协作机制框（三段）
- ① 组件清单：MemoryStore(MEMORY/USER+冻结快照) + format_for_system_prompt(路径①) + prefetch 副本注入(路径②) + memory nudge + MemoryManager(provider 编排)。跨章节：冻结快照进 volatile 层、压缩边界才刷新(第6章)；prefetch 副本不改前缀(第6章)；memory nudge 与 skill nudge 同构、共用 turn_finalizer fork(第9章)；记忆 vs 技能=声明性 vs 程序性(第9章)。
- ② 数据流时序：load_from_disk 冻结快照→system prompt(路径①整会话不变)；memory 工具写入随时落盘(durable 不动快照)；prefetch→贴当前 user 副本(路径②原 messages 不改)；nudge 置布尔→响应后 fork review。压缩才刷快照。
- ③ 关键点：写读分离——写在磁盘+live；读(注入)用冻结快照或只贴当前 user 副本，都不碰中途 system prompt。

## 模板结构
lead → analogy(助理备忘录/拍立得快照) → macro(声明性记忆,写durable注入守缓存) → 主体(冻结快照 codefile + prefetch 副本注入 codefile + memory nudge codefile) → provider/Honcho 正文 → vflow(写入→两路注入→不破缓存) → collab → design(回指 B/A/D) → key。

## quiz 考点
- 会话中途写入的记忆为什么不会立刻进 system prompt（冻结快照，非 live）。
- 实时取回的记忆注入到哪（当前 user 消息的 API 副本，原 messages 不改）。
- memory nudge 和 skill nudge 的关系（同构，都不注入主对话、响应后 fork）。

## 验收
0 error；3 codefile 逐字真实（简化标注，docstring 内 `"""` 用 &quot; 防破坏外层 r"""）；冻结快照/副本注入/nudge 讲清；双语镜像；中文 ≥1500（不足最后统一补）。
