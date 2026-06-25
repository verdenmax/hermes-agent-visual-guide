# ch7 Spec — 消息流与 provider 适配 / Message flow & provider adapters

## 目标
讲清 Hermes 如何用**一套统一的 OpenAI 风格 messages**跑遍所有 provider：transport 注册表分派、三个 adapter 翻译、reasoning 跨轮传递、严格角色交替修复。

## 🎯 章末设计取舍
- 主线：**统一抽象 + 严格角色交替不变量**——一套 messages，多家后端；API 调用前修复交替。
- 回指：`E·结构化输出脆弱`（function calling / schema 透传）、`G·推理token不持久`（reasoning_details 跨轮 replay）、`D·提示脆弱`（统一格式隔离 provider 差异）。

## 真实锚点（逐字 + 文件:行号；不得臆造）
1. **transport 注册表（懒发现）** — `agent/transports/__init__.py:21-46`：`register_transport(api_mode, cls)` / `get_transport(api_mode)`。四 transport 模块尾自注册：`anthropic_messages`/`codex_responses`/`chat_completions`/`bedrock_converse`。
2. **按 api_mode 取缓存 transport** — `run_agent.py:4534-4544`：`t = get_transport(mode); cache[mode] = t`。
3. **出站分派 build_api_kwargs** — `agent/chat_completion_helpers.py:555-663`：`if agent.api_mode == "anthropic_messages": ... if "bedrock_converse": ... if "codex_responses": ... else chat_completions`。
4. **入站归一分派** — `agent/conversation_loop.py:1420-1443`：按 api_mode 选 `normalize_response` / `map_finish_reason`。
5. **三 adapter 职责**（transport 是薄壳，逻辑在 adapter）：
   - `agent/anthropic_adapter.py`：`convert_messages_to_anthropic`(2262)、`build_anthropic_kwargs`(2326)。
   - `agent/codex_responses_adapter.py`：`_chat_messages_to_responses_input`(306，含 encrypted reasoning 跨轮 replay)。
   - `agent/gemini_native_adapter.py`：`build_gemini_request`(405)；走客户端层替换 `agent_runtime_helpers.py:1382-1394`（`GeminiNativeClient` 顶替 OpenAI client，api_mode 仍 `chat_completions`）。
6. **reasoning 三处存储** — `agent/chat_completion_helpers.py`：885-890 `reasoning`(文本) / 892-911 `reasoning_content`(thinking 模式回传，缺失 pad 空格防 HTTP 400) / 938-953 `reasoning_details`(原样不变透传，跨轮维持推理连续性；注释逐字："Pass reasoning_details back unmodified so providers … can maintain reasoning continuity across turns")。
7. **tool_calls 解析** — `agent/transports/chat_completions.py:611-637`：构造 `ToolCall(id, name, arguments, provider_data)`（Gemini3 `thought_signature` 藏 `extra_content`，须 replay 否则 400）。
8. **角色交替修复调用点** — `agent/conversation_loop.py:729-730`：`repaired_seq = repair_message_sequence_with_cursor(agent, messages)`（**每次 API 调用前**）。定义 `agent_runtime_helpers.py:347`（pass1 删孤儿 tool / pass2 合并连续 user）。

## 🧩 协作机制框（三段）
- **① 组件清单**：transport 注册表(`__init__`) + 三 adapter(翻译) + `build_api_kwargs`(出站构造) + `conversation_loop` 入站归一 + `repair_message_sequence_with_cursor`(交替修复)。跨章节：交替不变量服务缓存(第6章)、reasoning 落可见上下文对抗 G(第3章)。
- **② 数据流时序**：统一 messages → repair 修复交替 → build_api_kwargs 按 api_mode 选 transport → adapter 翻译成各家格式 → provider API → normalize_response 归一回统一 assistant_message(含 reasoning) → append。
- **③ 关键点**：核心只认**一种** messages 格式，provider 差异全被 transport/adapter 吸收——加新 provider 不动核心循环（呼应窄腰）。

## 模板结构
lead → analogy(同声传译/万能转接头) → macro(统一抽象) → 主体(transport 注册表 codefile + build_api_kwargs 分派 codefile + reasoning 三处存储 codefile) → vflow/timeline(出站→入站数据流) → 🧩collab → 🎯design(回指 E/G/D) → key。

## quiz 考点
- 加新 provider 要不要改核心循环（不要，加 transport/adapter）。
- 为什么 reasoning_details 原样跨轮透传（推理连续性，对抗 G）。
- 角色交替修复何时跑（每次 API 调用前）。

## 验收
0 error；3 codefile 逐字真实；reasoning 三处存储讲清；双语镜像。
