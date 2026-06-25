# ch5 Plan — 实施步骤

## 1. 锚点
已在 spec 逐字给出（conversation_loop.py:589/594-614, iteration_budget.py:17-59, run_agent.py:2400-2406/5325-5337, agent_runtime_helpers.py:348-435, chat_completion_helpers.py:885-890, tool_dispatch_helpers.py:336-343）。执行 subagent 须 view 核实后落笔。

## 2. 执行（subagent, opus 4.8）→ `src/_drafts/ch5.py`
格式 `LESSON = {"zh": r"""...""", "en": r"""..."""}`。要求：
- 模板齐全：lead / card analogy / card macro / 2–3 codefile（逐字真实）/ timeline 或 vflow 主循环时序图 / card collab（三段）/ card design（badge 回指 B/F/A）/ card key。
- `<pre>` 内无裸 `<`（用 `&lt;`）；可用 `<span class="cm|kw|fn|st">` 高亮。
- 正文无 `<h1>`；标签平衡；中文 ≥1500；zh/en 镜像。
- 诚实：grace call = 预留钩子、核心未触发；run_conversation = 转发器。

## 3. 双重校验（2× subagent, opus 4.8, 并行）
- A 概念正确性：逐条核对 文件:行号 + 代码逐字；while 条件正确；grace call 诚实；无臆造。
- B 完善性：模板齐全 / 时序图清晰 / collab 三段 / design 回指 / 双语对齐 / quiz 合理。

## 4. 集成（我）
修复 → LESSON_05 入 part1.py → 注册 PAGES+registry+quizzes → build/check → 0 error 才 commit。
