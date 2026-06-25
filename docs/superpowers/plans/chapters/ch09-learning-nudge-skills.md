# ch9 Plan — 实施步骤

## 1. 锚点
spec 已逐字给出（background_review.py:1-8/231-237/669、agent_init.py:1235-1238、conversation_loop.py:646、turn_finalizer.py:434-435、skill_commands.py:58/206、skill_provenance.py:75-78、skill_manager_tool.py:1082-1084、skills_tool.py:1620-1625、AGENTS.md 缓存节）。执行 subagent 须逐一 view 核实；**技能延迟失效的 --now/deferred 实现**须在 `tools/skills_tool.py`/`tools/skills_hub.py` 里 view 到真实片段后才写。

## 2. 执行（subagent, opus 4.8）→ `src/_drafts/ch9.py`
- 模板齐全：lead → card analogy（下班后复盘 / 学徒把"怎么做"记成手册）→ card macro（自我进化闭环的入口）→ **3 个 codefile**（① skill vs memory 边界 background_review.py:231-237；② nudge 触发 turn_finalizer.py:434-435 + 计数 conversation_loop.py:646；③ background review fork docstring background_review.py:1-8，含 "Main conversation and prompt cache are never touched"）→ **vflow/timeline**（turn → nudge 计数 → 响应交付 → fork review → 落盘，全程标注"主对话/缓存不动"）→ card collab（三段，含跨章节：fork 既存技能也存记忆=第11章、技能进 stable + 延迟失效守缓存=第6章、curator 只碰 agent-skill=第10章、nudge 与 memory nudge 同构=第11章）→ card design（围绕"学习闭环全程不破缓存"，回指 B·无状态 / A·中间遗失 + 缓存神圣，反模式：把 nudge 文字塞进主对话 / 把技能塞进 system prompt / 中途立即重载技能）→ card key。
- `<pre>` 内无裸 `<`；箭头 `-&gt;`；正文只 h2/h3；div/pre/table 平衡；中文 ≥1500 CJK；zh/en 镜像，en 无残留中文；内部引号用「」或单引号。
- 风格样例参考已集成的 `src/part1.py` LESSON_05、`src/part2.py` LESSON_06。
- 简化代码块 cf-head 标「· 简化」/「· simplified」，纯节选标「· 节选」/「· excerpt」。

## 3. 双重校验（2× subagent, opus 4.8 max long_context）
- A 概念正确：skill vs memory 边界 / nudge "turn 后 fork 不注入主对话" / 技能 user 消息注入 / 技能延迟失效 / provenance 门控——逐字真实、行号准确、无捏造。特别警惕把"延迟失效"说成"立即生效"或反之。
- B 完善：覆盖 spec 全部要点 / collab 三段含跨章节且章号正确（第6/10/11章）/ design 回指 B·A + 缓存 / 双语镜像 / quiz 三考点。

## 4. 集成（我）
LESSON_09 入 **part3.py**（第三部分新文件，registry 增 `import part3`）→ 注册 PAGES（part_zh="第三部分 · 自我进化闭环", part_en="Part 3 · The Self-Improvement Loop"）+ registry + quizzes(ch9 三考点) → `rm -rf __pycache__` 后 build + build_print + check_html + check_links → 0 error 才 commit。
