# ch14 Spec — 委派的规划/执行分离 + 审查：生成-验证差 / 谄媚对策

## 目标
诚实讲清:hermes 委派层**无内建** plan/execute/review 状态机,这些是**技能编排 delegate_task 隔离能力**实现的「生成者-验证者分离」。核心是"No agent should verify its own work, fresh context finds what you miss"。呼应窄腰(委派提供隔离原语,工作流在边缘技能)。

## 🎯 章末设计取舍
- 主线：**生成-验证分离靠「独立 context」,工作流用技能编排委派原语(窄腰)**。
- 回指：`F·误差累积`(确认偏误/谄媚自我背书→独立context验证者+两阶段审查"在错误复合前抓住")、`C·幻觉`(子代理真诚误报"成功"→self-reports需自验)。

## 真实锚点（explore 采集 + 已核实路径真实;校验须 view 核对）
1. **唯一内建验证倾向** — `tools/delegate_tool.py:2923-2929` "Subagent summaries are SELF-REPORTS, not verified facts. A subagent that claims 'uploaded successfully' or 'file written' may be wrong... require a verifiable handle (URL, ID, absolute path, HTTP status) and verify it yourself -- fetch the URL, stat the file, read back the content -- before telling the user the operation succeeded"。
2. **核心原则** — `skills/software-development/requesting-code-review/SKILL.md:19` "No agent should verify its own work. Fresh context finds what you miss";:125-130 Independent reviewer "gets ONLY the diff... No shared context with the implementer. Fail-closed";:194-198 auto-fix "Spawn a THIRD agent context";:233-236 "[verified]" commit。
3. **两阶段审查** — `optional-skills/software-development/subagent-driven-development/SKILL.md:20` "Fresh subagent per task + two-stage review (spec then quality)";:92-118 Spec Compliance "PASS or list of spec gaps";:121-148 Code Quality "APPROVED or REQUEST_CHANGES";:246-253 "catches issues before they compound"。
4. **规划/执行分离** — `skills/software-development/plan/SKILL.md:3` "Plan mode: write an actionable markdown plan to .hermes/plans/, no execution";:20-22 "you are planning only. Do not implement code"。
5. **诚实结论**:委派层只有 role enum [leaf,orchestrator](delegate_tool.py:3104-3107),无 plan→execute→verify 状态机;核心 prompt **无 anti-sycophancy 指令**(explore grep 零命中);background_review.py 是 skill/memory 自改进(第9章),非委派审查。

## 🧩 协作机制框（三段）
- ① 组件清单:工具描述"self-reports verify yourself"(唯一内建) + plan技能 + subagent-driven-development(执行+两阶段审查) + requesting-code-review(独立reviewer+auto-fix)。跨章节:所有"独立context"靠 delegate_task 上下文隔离(第13章);这些工作流是技能(第9章程序性记忆)非核心内建=窄腰(第4章);background_review.py 是自改进(第9章)非委派审查别混。
- ② 数据流时序:plan产出计划→subagent-driven派implementer执行→spec合规reviewer→代码质量reviewer→requesting-code-review派审查者(只看diff)→第三个context修复→[verified]提交。
- ③ 关键点:hermes没把规划/执行/审查做成委派内建状态机,而用三个技能编排delegate_task隔离原语。核心保持窄(只一条"隔离子代理"原语),复杂工作流在边缘技能演化。

## 模板结构
lead → analogy(同行评审/第三方审计) → macro(生成-验证分离靠独立context) → 主体(工具描述self-reports codefile + requesting-code-review核心原则 codefile + subagent-driven两阶段 codefile) → vflow → collab → design(回指 F/C) → key。

## quiz 考点
- hermes 的规划/执行分离+审查是 delegate_task 内建还是技能(技能编排delegate_task隔离)。
- 为什么"No agent should verify its own work"(确认偏误+谄媚,需独立fresh context验证)。
- 谄媚对策靠什么(核心prompt无anti-sycophancy指令,靠独立验证者+fresh context结构隔离)。

## 验收
0 error；3 codefile 逐字真实(简化标注,SKILL.md路径可省略号但内容真实);"委派无内建审查/靠技能/独立context"讲清;双语镜像;中文 ≥1500。
