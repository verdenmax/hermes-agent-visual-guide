# Hermes Agent Visual Guide / Hermes Agent 设计图解 ☤

A visual, bilingual (English + 中文) guide to the **design** of
[hermes-agent](https://github.com/NousResearch/hermes-agent) — **25 chapters**
that explain *what each part was designed to achieve*, the LLM constraint it
fights, and how it cooperates with the rest of the system.

> **Disclaimer:** This is **third-party, unofficial** educational material
> *about* hermes-agent. It contains **no hermes-agent source code**; it explains
> hermes-agent by quoting small, cited snippets (`file:line`). hermes-agent
> itself is MIT-licensed by its own authors.

Every chapter is self-contained, embeds both languages (toggle in the page),
and uses hand-drawn diagrams, **real (cited) code and prompts**, a 🧩
collaboration-mechanism box (how components cooperate), a 🎯 design-tradeoff box
(the principle it serves), and a short self-test quiz.

---

## What it covers

The guide is organized into seven parts that build up step by step:

| Part | Topic | Chapters |
| --- | --- | --- |
| 1 | The big picture + LLM constraints (the "diseases") | 1–5 |
| 2 | The agent core — loop, system prompt & cache, tools | 6–8 |
| 3 | The self-improvement loop — nudges, skills, curator, memory, search | 9–12 |
| 4 | Scale & isolation — delegation, compression, terminal backends | 13–16 |
| 5 | Edges & gateway — platforms, guards, TUI/desktop, profiles | 17–20 |
| 6 | Automation & research — cron/kanban, eval/trajectory, plugins/MCP | 21–23 |
| 7 | Reference — security threat model, design-principle matrix & glossary | 24–25 |

A throughline runs across the book: **the prompt cache is sacred**, **the core
is a narrow waist**, **the agent self-evolves** — and most designs are an
engineering answer to a fixed LLM limitation (A–G).

## How to view

**Locally** (zero dependencies, just Python 3):

```bash
cd src
python3 build.py
# then open ../index.html in a browser
```

## How to print / export a PDF

```bash
cd src
python3 build_print.py
# open ../print_zh.html (Chinese) or ../print_en.html (English), then
# File -> Print -> Save as PDF (Ctrl/Cmd+P). Each chapter starts on a new page.
```

## Build & validate

```bash
cd src
python3 build.py          # regenerate index.html + lessons/*.html
python3 build_print.py    # regenerate print_zh.html + print_en.html
python3 check_html.py     # structural checks (0 error expected)
python3 check_links.py    # all internal links must resolve
```

The generated HTML is committed and kept in sync with the sources; a re-run of
`build.py` should produce no diff.

## Project structure

```
src/            generators + tooling (pure Python 3, no dependencies)
  part1.py .. part7.py   chapter content (bilingual), grouped by part
  quizzes.py             per-chapter self-test questions
  shell.py               page shell + the shared CSS design system
  registry.py            ordered filename -> content map
  build.py               builds index.html + lessons/*.html
  build_print.py         builds print_zh.html + print_en.html
  check_html.py          structural HTML validation
  check_links.py         internal link validation
lessons/        generated chapter pages (committed, kept in sync)
index.html      generated table of contents (committed)
print_*.html    generated print editions (committed)
docs/superpowers/   design spec and implementation plan
```

## License

Dual-licensed:

- **Code** (the Python generators and validation scripts under `src/`) — MIT,
  see [LICENSE](LICENSE).
- **Content** (the chapter text and diagrams rendered into `index.html`,
  `lessons/*.html`, `print_*.html`) — CC BY 4.0, see
  [LICENSE-CONTENT](LICENSE-CONTENT).

---

## 中文说明

这是一份 [hermes-agent](https://github.com/NousResearch/hermes-agent) **设计原理**
的**图解、双语**学习指南，共 **25 章**，讲清楚*每个部件在设计时想达成什么*、
它在对抗哪个 LLM 固有约束、以及它如何与系统其他部分协作。

> **声明：** 本项目是**第三方、非官方**的学习材料，**不包含 hermes-agent 源码**，
> 只通过引用少量、标注来源（`文件:行号`）的代码片段来讲解。hermes-agent 本身由其
> 作者以 MIT 许可发布。

每一章都自成一体、内嵌中英双语（页内可切换），用手绘图、**真实（标注来源）的代码与
prompt**、一个 🧩 协作机制框（各组件如何配合）、一个 🎯 设计取舍框（它服务的设计
原则）和一段自测题来讲清一个设计。

**怎么看：** 本地零依赖，`cd src && python3 build.py` 后用浏览器打开 `index.html`。

**怎么打印：** `cd src && python3 build_print.py`，再打开 `print_zh.html`（中文）或
`print_en.html`（英文），用 `Ctrl/Cmd+P` 导出 PDF，每章自动分页。

**许可：** 双许可 —— 代码（`src/` 下的 Python 生成器与校验脚本）用 MIT；教学内容
（课程文字与图）用 CC BY 4.0。
