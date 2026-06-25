# ch7 Plan — 实施步骤

## 1. 锚点
spec 已逐字给出（transports/__init__.py:21-46、run_agent.py:4534-4544、chat_completion_helpers.py:555-663 与 885-953、conversation_loop.py:1420-1443 与 729-730、agent_runtime_helpers.py:347、transports/chat_completions.py:611-637、三 adapter 文件）。执行 subagent 须逐一 view 核实。

## 2. 执行（subagent, opus 4.8）→ `src/_drafts/ch7.py`
- 模板齐全：lead → card analogy（同声传译 / 万能转接头）→ card macro（一套 messages 跑遍所有后端）→ **3 个 codefile**（① transport 注册表 register/get_transport 懒发现；② build_api_kwargs 按 api_mode 分派；③ reasoning 三处存储 reasoning/reasoning_content/reasoning_details，逐字真实含"maintain reasoning continuity across turns"注释）→ **vflow/timeline 出站→入站数据流**（统一 messages → repair 修复交替 → build_api_kwargs 选 transport → adapter 翻译 → provider → normalize 归一回 assistant_message）→ card collab（三段，含跨章节：交替不变量服务缓存=第6章、reasoning 落可见上下文对抗 G=第3章、新增 provider 不动核心=窄腰第4章）→ card design（围绕"统一抽象 + 严格角色交替不变量"，回指 E·结构化输出脆弱 / G·推理token不持久 / D·提示脆弱，反模式：把 provider 差异泄进核心循环）→ card key。
- `<pre>` 内无裸 `<`（写 `&lt;`）；箭头 `-&gt;`；正文只用 h2/h3 无 h1；div/pre/table/details 标签平衡；中文 ≥1500 CJK；zh/en 段落一一镜像，en 内无残留中文（badge/标题/表头都译）。
- 风格样例参考已完成章节 `src/part1.py` 的 LESSON_05（HTML 结构与 CSS 类用法：card analogy/macro/collab/design/key、codefile cf-head/dot/path/ln、vflow/flow、badge constraint、table.t）。

## 3. 双重校验（2× subagent, opus 4.8 max long_context）
- A 概念正确：transport 懒注册 / build_api_kwargs 四分支 / reasoning 三处存储语义（尤其 reasoning_details 原样跨轮 replay 维持连续性、reasoning_content 缺失 pad 空格防 400）/ 角色交替修复"每次 API 调用前"——逐字真实，行号准确，无捏造。
- B 完善：覆盖 spec 全部要点 / collab 三段含跨章节且章号正确（第6章缓存、第3章G、第4章窄腰）/ design 回指 E·G·D / 双语镜像 / quiz 三考点。

## 4. 集成（我）
LESSON_07 追加进 **part2.py**（ch6 集成时已创建并 `import part2`）→ 注册 PAGES + registry + quizzes(ch7 三考点) → `rm -rf __pycache__` 后 build + build_print + check_html + check_links → 0 error 才 commit。
