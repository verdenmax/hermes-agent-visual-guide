# 每章 worked-example 实例图 实施计划

> REQUIRED SUB-SKILL: superpowers:subagent-driven-development。逐 part 执行：implementer → spec-compliance 审 → code-quality 审 → 修复。

**Goal:** 为 ch5–25（21 章）各 +1 张 worked-example 实例图（×双语=42 SVG），用真实代码片段+真实数据的具体例子把每章机制走一遍。设计见 spec `docs/superpowers/specs/2026-06-27-per-chapter-worked-examples-design.md`（逐章 worked-example + verbatim 锚点）。

**关键执行洞察:** 21 章分布在 **7 个不同 part 文件**（part1=ch5、part2=ch6-8、part3=ch9-12、part4=ch13-16、part5=ch17-20、part6=ch21-23、part7=ch24-25）。**不同 part 文件的 implementer 可并行**（编辑不同文件，无写冲突）；**同 part 内多章由同一 implementer 顺序画**（避免同文件并发）。

**执行编排:**
- 7 个 implementer 并行（每个负责一个 part 的全部 worked-example 图，zh+en）。
- 全部落盘后，7 批双审（spec-compliance + code-quality，按 part）。
- 集成 build×2 + check + 修复 + commit + push。

---

## 共享：每个 part-implementer prompt 必含
- **模型** general-purpose **opus-4.8**；**只 edit `src/part<N>.py` 这一个文件、绝不 build**（其他 part 由别的 agent 并发编辑）。
- **逐章画**：该 part 每章 1 张 worked-example 图（zh+en 各一份），按 spec 该章设计。
- **worked-example 定义 + 通用视觉语言**（spec §「通用视觉语言」逐条）：输入卡(真实数据)→处理区块(真实函数/中间值)→输出卡(真实结果)；关键步骤旁嵌 ≤3 行 verbatim 源码片段(标 file:line)；具体值用 `var(--purple)`/`var(--accent)` 高亮；底部一句「读这张图」。
- **诚实铁律**：所有值/字段/代码 **verbatim 来自该章锚点**（先 `sed -n` 比对 `/home/verden/course/hermes-agent/`）；配色**只用 `var(--*)`（含 -soft/-ink 变体）禁写死 #hex（含 #fff）**；font ≥9；emoji 22-26；SVG `role="img"`+`aria-label`；每图配 `<div class="fig-cap">`。
- **zh/en 双版结构对称**（同区块数/viewBox/元素数）；en 无中文/无 U+3000/无中文标点/无弯引号。
- **插入位置**：每章一个合适深度块末尾（最后现有 `.figure`/`codefile` 之后、下一 `<h3>` 之前）；用 edit old_str 唯一锚定（先 grep 该章现有 fig-cap 文本）；**只插入、不动现有内容**。
- **HTML 转义**：`<`→`&lt;`、`>`→`&gt;`、`&`→`&amp;`、`"`→`&quot;`（嵌入代码/JSON 里的尖括号引号都要转义）。
- **范例**（先 view 学风格）：`src/part9.py` 现有逐帧图、`src/part2.py` LESSON_06 缓存图。
- **自检**（报告不 build）：贴新增各章 zh+en figure 源码；`grep -c 'fill="#'` 新增段=0。

## 共享：双审（每 part 一组）
- **spec 审**：task general-purpose **opus-4.8**/high/long_context——核对该 part 各章图 vs spec 该章设计：帧/区块完整、数字字段 verbatim、嵌入代码 verbatim、与现有图差异化、zh/en 对称。
- **质量审**：**superpowers:code-reviewer** opus-4.8/high/long_context——配色全 var(--*)无 #hex(含 #fff)、SVG 语法、viewBox 680、font≥9、布局不出界/不重叠、纯新增、en 无中文。
- 审出问题→修→复审通过。

## 共享：集成（全部落盘后我统一一次）
```bash
cd src && rm -rf __pycache__ && python3 build.py >/dev/null 2>&1; python3 build.py >/dev/null 2>&1 && python3 check_html.py 2>&1 | grep -E 'error|passed'
python3 check_links.py 2>&1 | tail -1
for f in part1 part2 part3 part4 part5 part6 part7; do echo "$f hex: $(grep -c 'fill=\"#\|stroke=\"#' $f.py) svg: $(grep -c '<svg' $f.py)"; done
```

---

## Task 1：part1（ch5）— implementer + 双审
**Files:** Modify `src/part1.py`（LESSON_05）。1 张图。设计见 spec §ch5。
- [ ] Step 1: implementer 画 ch5「一条消息跑两圈」（zh+en）。
- [ ] Step 2: 我 view 核对落盘。
- [ ] Step 3: spec 审。 [ ] Step 4: 质量审。 [ ] Step 5: 修复。

## Task 2：part2（ch6/7/8）— implementer + 双审
**Files:** Modify `src/part2.py`（LESSON_06/07/08）。3 张图。设计见 spec §Part2。
- [ ] Step 1: implementer 逐章画 ch6/7/8（各 zh+en）。
- [ ] Step 2-5: 核对 / spec 审 / 质量审 / 修复。

## Task 3：part3（ch9/10/11/12）— implementer + 双审
**Files:** Modify `src/part3.py`（LESSON_09-12）。4 张图。设计见 spec §Part3。
- [ ] Step 1: implementer 逐章画 ch9/10/11/12。
- [ ] Step 2-5: 核对 / spec 审 / 质量审 / 修复。

## Task 4：part4（ch13/14/15/16）— implementer + 双审
**Files:** Modify `src/part4.py`（LESSON_13-16）。4 张图。设计见 spec §Part4。
- [ ] Step 1: implementer 逐章画 ch13/14/15/16。
- [ ] Step 2-5: 核对 / spec 审 / 质量审 / 修复。

## Task 5：part5（ch17/18/19/20）— implementer + 双审
**Files:** Modify `src/part5.py`（LESSON_17-20）。4 张图。设计见 spec §Part5。
- [ ] Step 1: implementer 逐章画 ch17/18/19/20。
- [ ] Step 2-5: 核对 / spec 审 / 质量审 / 修复。

## Task 6：part6（ch21/22/23）— implementer + 双审
**Files:** Modify `src/part6.py`（LESSON_21-23）。3 张图。设计见 spec §Part6。
- [ ] Step 1: implementer 逐章画 ch21/22/23。
- [ ] Step 2-5: 核对 / spec 审 / 质量审 / 修复。

## Task 7：part7（ch24/25）— implementer + 双审
**Files:** Modify `src/part7.py`（LESSON_24/25）。2 张图（可选各 +1，先做第 1 张）。设计见 spec §Part7。
- [ ] Step 1: implementer 画 ch24/25。
- [ ] Step 2-5: 核对 / spec 审 / 质量审 / 修复。

## Task 8：集成、验证、提交、部署
- [ ] build×2 + check_html(0 error) + check_links + hex(增量 0) + svg 计数(+42)。
- [ ] 抽查各 part 新图 3-5 个数字/字段 verbatim。
- [ ] 重建 print。
- [ ] commit + push（自动 redeploy）+ 验证 live 200。

## Self-Review
- spec 21 章 ↔ Task 1-7（part1-7）一一对应；Task 8=集成。无遗漏。
- 占位扫描：每 Task 指向 spec 具体章节设计 + 共享 prompt 模板，无 TBD。
- 并发安全：7 个 implementer 编辑 7 个不同文件，无写冲突；同 part 多章由同一 implementer 顺序画。
- 范围：纯新增 21 图，不改现有 SVG/正文/quiz/注册。
