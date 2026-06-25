# ch5 Spec — 一次对话的生命周期 / Conversation lifecycle

## 目标
端到端讲清 Hermes 一次对话从用户消息到最终回复：**同步主循环 + 迭代预算 + 可中断 + 严格消息角色交替**。这是 "agent loop" 的心脏。

## 🎯 章末设计取舍（design 框）
- 主线：**可中断 + 迭代预算 + 严格角色交替不变量**。
- 回指 LLM 约束：`B·无状态`（全部状态外置在 messages，每轮重发）、`F·误差累积`（迭代预算 + 中断防止失控长循环）、`A·延迟/成本`（预算限制长度）。

## 真实源码锚点（必须逐字引用 + 标注 文件:行号；不得臆造）
1. **主循环 while 条件** — `agent/conversation_loop.py:589`
   ```python
   while (api_call_count < agent.max_iterations and agent.iteration_budget.remaining > 0) or agent._budget_grace_call:
   ```
2. **循环体：计数 + 预算消费 + grace** — `agent/conversation_loop.py:601-614`
   ```python
   api_call_count += 1
   agent._api_call_count = api_call_count
   if agent._budget_grace_call:
       agent._budget_grace_call = False
   elif not agent.iteration_budget.consume():
       _turn_exit_reason = "budget_exhausted"
       break
   ```
3. **IterationBudget** — `agent/iteration_budget.py:17-59`（线程安全；parent 默认 90、subagent 默认 50）
   ```python
   def consume(self) -> bool:
       with self._lock:
           if self._used >= self.max_total:
               return False
           self._used += 1
           return True
   @property
   def remaining(self) -> int:
       with self._lock:
           return max(0, self.max_total - self._used)
   ```
   `execute_code` 等编程式调用 `refund()` 不占预算。
4. **中断检查（循环顶部）** — `agent/conversation_loop.py:594-599`
   ```python
   if agent._interrupt_requested:
       interrupted = True
       _turn_exit_reason = "interrupted_by_user"
       break
   ```
5. **interrupt() 设置** — `run_agent.py:2400-2406`：`self._interrupt_requested = True`，并向 in-flight 工具线程/子 agent 级联传播。
6. **assistant 消息含 reasoning** — `agent/chat_completion_helpers.py:885-890`
   ```python
   msg = {"role": "assistant", "content": _san_content,
          "reasoning": reasoning_text, "finish_reason": finish_reason}
   ```
7. **tool 消息格式** — `agent/tool_dispatch_helpers.py:336-343`：`{"role":"tool","name":...,"content":wrapped,"tool_call_id":...}`。
8. **严格角色交替修复** — `agent/agent_runtime_helpers.py:348-435` `repair_message_sequence`：Pass1 丢弃孤儿 tool 消息；Pass2 **合并连续 user 消息**（换行拼接）。docstring 原文："Providers (OpenAI, OpenRouter, Anthropic) expect strict alternation … no two consecutive user messages …"。
9. **chat() 是 run_conversation() 的简化封装** — `run_agent.py:5325-5337`：`return result["final_response"]`。
10. ⚠️ **诚实标注**：`run_agent.py:5302-5323` 的 `run_conversation()` 只是**转发器**，真正主循环在 `agent/conversation_loop.py`。
11. ⚠️ **诚实标注**：`_budget_grace_call` 是一个**预留放行钩子**——全仓仅 3 处引用（初始化置 False / while 条件 / 循环内消费置 False），**未找到核心代码把它设为 True**。预算耗尽的真正"宽限一轮"由独立的 `_budget_exhausted_injected` + `_handle_max_iterations` 实现。**不得**把它写成"正常会多跑一轮"。

## 🧩 协作机制框（三段）
- **① 组件清单**：`conversation_loop`（主循环）、`IterationBudget`（预算）、`_interrupt_requested`（中断标志，`interrupt()` 设置）、`repair_message_sequence`（交替修复）、`tool_executor`（执行工具 + append 结果）、`chat_completion_helpers`（构造 assistant msg）。跨章节：messages 外置状态（第 2 章 B）、预算防误差累积（第 3 章 F）、交替不变量服务 prompt 缓存（第 6 章）。
- **② 数据流时序**：用户消息 → while 循环 →〔检查中断 → consume 预算 → LLM 调用 → 处理 tool_calls → append tool 结果〕→ 无 tool_calls 收尾 → `final_response`。
- **③ 关键点**：全部状态在 messages 里、循环同步可中断、预算有界——三者合起来让 agent loop 既强又不失控。

## 模板结构（5 段式）
lead → analogy（工厂流水线/生产线）→ macro（同步循环）→ 主体（while 循环 `codefile` + `timeline`/`vflow` 时序图 + IterationBudget `codefile` + 中断 + 角色交替 `codefile`）→ 🧩collab → 🎯design → key card。quiz 在 quizzes.py。

## quiz 考点
- 主循环三种退出：达到 max_iterations / 预算耗尽 / 用户中断。
- 为什么要严格角色交替（provider 要求 + 不破缓存）。
- 诚实点：grace call 是预留钩子，未被核心触发。

## 验收
0 error；check_links 通过；模板齐全；2-3 个 codefile 逐字真实；双语结构镜像；grace call 与 run_conversation 转发器如实标注。
