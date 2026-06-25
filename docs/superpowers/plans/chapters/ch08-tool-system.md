# ch8 Plan — 实施步骤

## 1. 锚点
spec 已逐字给出（registry.py:234-310/110-148/337-384/390-416、model_tools.py:276-300/901、conversation_loop.py:4117-4122、iteration_budget.py:45-49、AGENTS.md:171-195）。执行 subagent 须逐一 view 核实。

## 2. 执行（subagent, opus 4.8）→ `src/_drafts/ch8.py`
- 模板齐全：lead → card analogy（机场安检+登机口 / 万能插座面板）→ card macro（能力在边缘、核心窄腰）→ **3 个 codefile**（① register + check_fn 门控过滤 get_definitions:358-364；② dispatch 统一 JSON 返回 + 错误净化 _sanitize_tool_error；③ execute_code refund，仅当 `_tc_names == {"execute_code"}`）→ **flow 图**（register→toolset过滤→check_fn门控→schema→API→tool_call→dispatch→append→refund）→ card collab（三段，含跨章节：工具发现链=窄腰第4章、工具结果 append 不改前缀=缓存第6章、check_fn 门控让工具集会话内稳定=缓存铁律第6章、refund 呼应预算第5章、delegate_task=委派第13章）→ card design（围绕"能力在边缘+核心窄腰+append-only 不破缓存"，回指 A·中间遗失 / D·指令=数据 / E·结构化输出脆弱，反模式：动辄加核心工具）→ card key。
- `<pre>` 内无裸 `<`；箭头 `-&gt;`；正文只 h2/h3 无 h1；div/pre/table 平衡；中文 ≥1500 CJK；zh/en 镜像，en 内无残留中文。
- 风格样例参考 `src/part1.py` 的 LESSON_05 与（集成后的）part2.py LESSON_06/07。

## 3. 双重校验（2× subagent, opus 4.8 max long_context）
- A 概念正确：register/check_fn 门控（30s TTL）/ dispatch 错误净化 / execute_code refund 条件（全是 execute_code）逐字真实，行号准确，无捏造。
- B 完善：覆盖 spec 全部要点 / collab 三段含跨章节且章号正确 / design 回指 A·D·E / 双语镜像 / quiz 三考点。

## 4. 集成（我）
LESSON_08 追加进 **part2.py** → 注册 PAGES + registry + quizzes(ch8 三考点) → `rm -rf __pycache__` 后 build + build_print + check_html + check_links → 0 error 才 commit。集成完 part2（ch6-8）齐活，第二部分完成。
