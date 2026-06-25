# ch6 Plan — 实施步骤

## 1. 锚点
spec 已逐字给出（system_prompt.py:3-20/113, prompt_caching.py:1-79, prompt_builder.py:46-62）。执行 subagent 须 view 核实。

## 2. 执行（subagent, opus 4.8）→ `src/_drafts/ch6.py`
- 模板齐全：lead / card analogy（地基/承重墙，或"提前付费的前缀"）/ card macro / **layers 三层图**（stable→context→volatile）/ **3 个 codefile**（system_prompt docstring、prompt_caching system_and_3、prompt_builder 注入扫描，逐字真实）/ card collab（**三段，重点跨章节**：全局如何配合维护缓存）/ card design（围绕缓存神圣，回指 A·中间遗失 / D·注入，反模式：绝不 mid-conversation 换 toolset/reload memory/rebuild prompt）/ card key。
- `<pre>` 无裸 `<`；正文无 `<h1>`；中文 ≥1500；zh/en 镜像。
- 🧩 协作框必须体现"全局各子系统如何共同维护 prompt 缓存"（技能进 stable、记忆进 volatile、nudge/搜索末尾 append、压缩唯一例外、辅助模型独立 session）。

## 3. 双重校验（2× subagent, opus 4.8）
- A 概念正确：三层结构 / system_and_3 / ~75% / 注入扫描 逐字真实；docstring 引用准确。
- B 完善：协作框跨章节到位 / design 反模式 / 双语镜像 / quiz 合理。

## 4. 集成（我）
LESSON_06 入 **part2.py**（第二部分新文件，registry 增 `import part2`）→ 注册 PAGES+registry+quizzes → build/check → 0 error 才 commit。
