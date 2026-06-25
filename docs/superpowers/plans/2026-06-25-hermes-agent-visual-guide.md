# Hermes Agent 图解学习指南 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 制作一份详细、双语、图解的 Hermes Agent 设计原理学习指南（25 章 / 7 部分），仿照 `llama-cpp-visual-guide` 的零依赖 Python 生成器形态。

**Architecture:** `src/partN.py` 写双语内容（`LESSON_XX = {"zh","en"}`）→ `build.py` 经 `shell.py`（外壳+CSS）+ `quizzes.py` 渲染出 `lessons/*.html` + `index.html`；`build_print.py` 出打印版；`check_html.py`/`check_links.py` 做回归校验。生成的 HTML 提交并与源同步。

**Tech Stack:** 纯 Python 3（零依赖），HTML/CSS（内联 SVG 手绘图），无构建工具链。

---

## 内容项目的 TDD 适配

本项目产出是"教学内容"，不是可单测的函数。把 TDD 的"红→绿"循环适配为：

- **红**：`check_html.py` 报 ERR，或 `check_links.py` 有断链，或本章引用的 prompt/代码/常量**尚未**按 `文件:行号` 在 Hermes 源码中核实。
- **绿**：`build.py` 成功 → `check_html.py` **0 ERR**（WARN 允许）→ `check_links.py` 全部解析 → 本章每条源码引用都已 `view` 核实、标注真实 `文件:行号`。
- **每章一次 commit**；脚手架每个文件一次 commit。

每写一章前，先建该章"事实锚点清单"（用 `grep`/`view` 把相关源码读实），再落笔——杜绝臆造（见 spec §3.1 真实性纪律）。

---

## File Structure

```
hermes-agent-visual-guide/
├── src/
│   ├── shell.py        # PAGES 清单 + 共享 CSS（金色 + collab/design/badge）+ page()/index_page()/bi()
│   ├── registry.py     # CONTENT: filename -> partN.LESSON_XX（与 PAGES 同步）
│   ├── quizzes.py      # QUIZZES: filename -> 双语自测题；render(fname, lang)
│   ├── build.py        # 生成 index.html + lessons/*.html
│   ├── build_print.py  # 生成 print_zh.html + print_en.html
│   ├── check_html.py   # 结构校验（MAX_LESSON=25）
│   ├── check_links.py  # 内链校验
│   └── part1.py..part7.py  # 各部分章节内容（双语）
├── lessons/            # 生成产物（提交）
├── index.html          # 生成产物（提交）
├── print_zh.html / print_en.html  # 生成产物（提交）
├── docs/superpowers/{specs,plans}/
├── README.md · LICENSE（MIT）· LICENSE-CONTENT（CC BY 4.0）· .gitignore
```

**章节 → 文件 → 部分 映射（渐进式：每完成一章，把该章条目加进 `shell.PAGES` 与 `registry.CONTENT`）：**

| # | filename | part 模块 | 部分 |
|---|---|---|---|
| 1 | `01-what-is-hermes.html` | part1 | 一·宏观全景 |
| 2 | `02-llm-constraints-single-call.html` | part1 | 一·宏观全景 |
| 3 | `03-llm-constraints-autonomy.html` | part1 | 一·宏观全景 |
| 4 | `04-project-map-narrow-waist.html` | part1 | 一·宏观全景 |
| 5 | `05-conversation-lifecycle.html` | part1 | 一·宏观全景 |
| 6 | `06-system-prompt-and-caching.html` | part2 | 二·Agent 核心 |
| 7 | `07-message-flow-providers.html` | part2 | 二·Agent 核心 |
| 8 | `08-tool-system.html` | part2 | 二·Agent 核心 |
| 9 | `09-nudge-and-skills.html` | part3 | 三·自我进化闭环 |
| 10 | `10-curator.html` | part3 | 三·自我进化闭环 |
| 11 | `11-memory.html` | part3 | 三·自我进化闭环 |
| 12 | `12-session-search.html` | part3 | 三·自我进化闭环 |
| 13 | `13-delegation.html` | part4 | 四·规模化与隔离 |
| 14 | `14-delegation-plan-verify.html` | part4 | 四·规模化与隔离 |
| 15 | `15-context-compression.html` | part4 | 四·规模化与隔离 |
| 16 | `16-terminal-backends.html` | part4 | 四·规模化与隔离 |
| 17 | `17-gateway-platforms.html` | part5 | 五·多端与网关 |
| 18 | `18-gateway-guards.html` | part5 | 五·多端与网关 |
| 19 | `19-tui-desktop.html` | part5 | 五·多端与网关 |
| 20 | `20-config-profiles.html` | part5 | 五·多端与网关 |
| 21 | `21-cron-kanban.html` | part6 | 六·自动化与研究 |
| 22 | `22-eval-trajectory.html` | part6 | 六·自动化与研究 |
| 23 | `23-plugins-mcp.html` | part6 | 六·自动化与研究 |
| 24 | `24-security-threat-model.html` | part7 | 七·速查 |
| 25 | `25-design-principles-glossary.html` | part7 | 七·速查 |

---

## 阶段总览

| 阶段 | 产出 | 章节 |
|---|---|---|
| **0** | 脚手架：生成器+校验脚本+CSS（金色/新框）+ 元文件，管线端到端跑通（含 1 个占位章） | — |
| **1** | 第一部分（宏观全景 + LLM 约束地基课） | 1–5 |
| **2** | 第二部分（Agent 核心；第 6 章样章定基准） | 6–8 |
| **3** | 第三部分（自我进化闭环） | 9–12 |
| **4** | 第四部分（规模化与隔离） | 13–16 |
| **5** | 第五部分（多端与网关） | 17–20 |
| **6** | 第六部分（自动化与研究） | 21–23 |
| **7** | 第七部分（安全专题 + 横向收束矩阵） | 24–25 |

> 每阶段结束都能 `build` 出可浏览站点并通过 `check_html`/`check_links`。
> 详细 Task 逐阶段追加（用户偏好：分步写计划、一点一点来）。

---

## 阶段 0 · 脚手架

**目标**：把 llama-cpp 的生成器骨架移植过来，换 Hermes 金色主题、加两个新框样式，跑通一个占位章，使 `check_html`（0 ERR）+ `check_links` 全绿。

### Task 0.1 — 项目元文件

**Files:**
- Create: `README.md`、`LICENSE`、`LICENSE-CONTENT`、`.gitignore`

- [x] **Step 1: 写 `.gitignore`**

```
__pycache__/
*.pyc
.DS_Store
```

- [x] **Step 2: 写 `LICENSE`（MIT，覆盖 `src/` 生成器/校验脚本）**

填入标准 MIT 文本，版权行：`Copyright (c) 2026 verdenmax`。

- [x] **Step 3: 写 `LICENSE-CONTENT`（CC BY 4.0，覆盖课程内容）**

填入 `Creative Commons Attribution 4.0 International` 标准声明摘要 + 指向 `https://creativecommons.org/licenses/by/4.0/` 的链接。

- [x] **Step 4: 写 `README.md`**

包含：项目简介（第三方非官方、解释 hermes-agent 设计、不含其源码）、双语徽章、构建方式（`cd src && python3 build.py`）、打印方式（`build_print.py`）、校验方式（`check_html.py`/`check_links.py`）、项目结构、双许可声明。仿 llama-cpp README 结构。

- [x] **Step 5: Commit**

```bash
git add README.md LICENSE LICENSE-CONTENT .gitignore
git commit -m "chore: project meta files (README, dual license, gitignore)"
```

### Task 0.2 — `src/shell.py`（外壳 + 金色 CSS + 新框）

**Files:**
- Create: `src/shell.py`（以 llama-cpp `src/shell.py` 为基底改造）

- [x] **Step 1: 复制基底并改品牌**

从 llama-cpp `src/shell.py` 复制 `esc()`、`head_meta()`、`bi()`、`page()`、`index_page()`、`FAVICON`、`INDEX_FILE`、整段 `CSS`。把 `og:site_name`、FAVICON 文案、品牌串改为 Hermes（favicon 文字 `☤`，`site_name`="Hermes Agent 设计图解"）。

- [x] **Step 2: PAGES 先只含第 1 章**

```python
# (filename, title_zh, title_en, part_zh, part_en)
PAGES = [
    ("01-what-is-hermes.html", "Hermes 是什么", "What is Hermes",
     "第一部分 · 宏观全景", "Part 1 · The Big Picture"),
]
```

- [x] **Step 3: 金色主题——覆盖 CSS 变量**

在 `CSS` 的 `:root` 把 accent 系改为 Hermes 金色（保留其余变量）：

```css
:root {
  --accent: #c8a02c; --accent-soft: #faf1d6; --accent-ink: #8a6d12;
  /* 其余 --bg/--panel/--blue/--purple/--red/--code-* 维持 llama-cpp 原值 */
}
@media (prefers-color-scheme: dark) {
  :root { --accent: #e3c05a; --accent-soft: #2e2510; --accent-ink: #f0d488; }
}
```

- [x] **Step 4: 新增两个框 + 约束徽章样式**

在 `CSS` 末尾追加：

```css
/* 🧩 协作机制框 */
.card.collab { border-left: 4px solid var(--blue); background: var(--blue-soft); }
.card.collab .tag { color: var(--blue); }
.card.collab .collab-sub { font-weight:700; font-size:.82rem; margin:.8rem 0 .3rem; color:var(--ink); }
/* 🎯 设计取舍框 */
.card.design { border-left: 4px solid var(--accent); background: var(--accent-soft); }
.card.design .tag { color: var(--accent-ink); }
/* A–G 约束回指徽章 */
.badge.constraint { display:inline-block; font-size:.7rem; font-weight:700;
  padding:.1rem .45rem; border-radius:999px; background:var(--purple-soft);
  color:var(--purple); border:1px solid var(--purple); margin:0 .2rem; white-space:nowrap; }
```

- [x] **Step 5: 验证可导入**

Run: `cd src && python3 -c "import shell; print(len(shell.PAGES), shell.INDEX_FILE)"`
Expected: 打印 `1 index.html`，无异常。

- [x] **Step 6: Commit**

```bash
git add src/shell.py
git commit -m "feat: shell.py with Hermes gold theme + collab/design cards"
```

### Task 0.3 — 构建与校验脚本

**Files:**
- Create: `src/build.py`、`src/build_print.py`、`src/check_links.py`、`src/check_html.py`（均以 llama-cpp 同名文件为基底）

- [x] **Step 1: 复制 `build.py`、`build_print.py`、`check_links.py`**

几乎照搬。改动点：
- `build_print.py`：`TITLE`/`INTRO`/`TOC` 文案改为 Hermes、课数措辞改为"全 25 章"。
- `check_links.py`：`ALLOW_MISSING` 改为 `{"hermes-agent-visual-guide-zh.pdf","hermes-agent-visual-guide-en.pdf"}`。

- [x] **Step 2: 复制 `check_html.py` 并改常量**

改动点：
- `MAX_LESSON = 25`
- `MIN_CJK = 3000`（保留）、`MIN_DIAGRAMS = 6`（保留，`DIAGRAM_CLASSES` 已含 `timeline`）
- `SOFT_EXEMPT = {"25-design-principles-glossary.html"}`（末章速查豁免图密度/要点卡）
- index pill 正则沿用 `共 (\d+) 课 · (\d+) 个部分`（`index_page` 会生成该串）

- [x] **Step 3: Commit**

```bash
git add src/build.py src/build_print.py src/check_links.py src/check_html.py
git commit -m "feat: build + print + html/link check scripts (MAX_LESSON=25)"
```

### Task 0.4 — `registry.py` + `quizzes.py` + 占位第 1 章

**Files:**
- Create: `src/registry.py`、`src/quizzes.py`、`src/part1.py`

- [x] **Step 1: `quizzes.py`——从 llama-cpp 复制 `render()` 接口**

复制 llama-cpp `quizzes.py` 的 `render(fname, lang)` 与数据结构；`QUIZZES` 先放第 1 章一道占位双语题（合法结构即可，阶段 1 再写实）。

- [x] **Step 2: `registry.py`——仅导入 part1**

```python
import part1
CONTENT = {
    "01-what-is-hermes.html": part1.LESSON_01,
}
```

- [x] **Step 3: `part1.py`——第 1 章占位（合规最小内容）**

`LESSON_01 = {"zh": ..., "en": ...}`，每语种含：一段 `lead`、一个 `card analogy`、一个 `layers` 或 `flow` 图、一个 `card key`（本课要点 / Key points）。够触发 `check_html` 0 ERR（CJK<3000 的 WARN 可接受）。**内容为占位，阶段 1 写实。**

- [x] **Step 4: build + 校验**

Run: `cd src && python3 build.py && python3 build_print.py && python3 check_html.py && python3 check_links.py`
Expected: build 写出 `lessons/01-*.html` + `index.html` + `print_*.html`；`check_html` 打印 `0 error(s)`；`check_links` 打印 `all N internal links resolve`。

- [x] **Step 5: Commit（含生成产物）**

```bash
git add src/registry.py src/quizzes.py src/part1.py index.html lessons/ print_zh.html print_en.html
git commit -m "feat: pipeline smoke test — placeholder lesson 1 builds & checks green"
```

### Task 0.5 — 提交 plan 并锁定阶段 0

- [x] **Step 1: Commit plan**

```bash
git add docs/superpowers/plans/2026-06-25-hermes-agent-visual-guide.md
git commit -m "docs: implementation plan (scaffold + phase overview)"
```

---

<!-- 阶段 1–7 的详细 Task 将在此处逐阶段追加（一点一点） -->
