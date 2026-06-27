# ch27/28 富可视化逐帧快照序列 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 用 superpowers:subagent-driven-development 逐 task 执行；每 task 走 implementer → spec-compliance 审 → code-quality 审 → 修复。步骤用 `- [ ]` 跟踪。

**Goal:** 为 Part 8（ch27/28）六个深度块各新增 1 张「逐帧状态快照序列」SVG（共 6 主图 × zh/en 双语 = 12 个 SVG），让每个机制有一张复杂、真实场景、能充分说明的动态演化图；现有 28 张流程图全部保留。

**Architecture:** 纯新增——只在 `src/part9.py` 的 `LESSON_27`/`LESSON_28` 的 zh/en 块里、每个深度块末尾插入新 `.figure`。6 图共享同一套视觉语言（帧卡 + 帧头 + 触发箭头 + 状态色 + 底部旁注条 + viewBox 680 宽）。不改 registry/shell/quizzes/check_html。

**Tech Stack:** 零依赖 Python 生成器（`src/partN.py` → `build.py` → `lessons/*.html`）；纯手写内联 SVG；配色只用 `shell.py` 的 CSS 变量（明暗自适应）；验证 `check_html.py`（0 error）+ `check_links.py`。

**完整设计见 spec:** `docs/superpowers/specs/2026-06-27-ch27-ch28-richviz-frames-design.md`（每图逐帧状态/色/数字/触发/旁注 + 诚实锚点）。

---

## 共享：每个 implementer 子代理 prompt 必含
- **模型** general-purpose **opus-4.8**；**只 `edit src/part9.py`、绝不 build**（全局 lessons/ 会与我并发竞争）。
- **范例**（先 view 学风格）：`src/part9.py` 现有 SVG（同章节奏）、`src/part1.py` `LESSON_04`（沙漏窄腰）、`src/part2.py` `LESSON_06`（缓存命中/击穿对比）。
- **通用视觉语言**（spec §「通用逐帧快照序列视觉语言」逐条照做）：帧卡 `rx≈8` 内画带具体数值的真实状态快照；帧头 `时刻/步骤号 + 一句话状态`；帧间箭头 + 触发条件标签；状态色 健康`var(--accent)`/冷却`var(--amber)`/失败`var(--red)`/中间`var(--blue)`/命中`var(--purple)`；底部旁注条 `var(--muted)` 小字 1–2 条；横向排列、viewBox **680** 宽。
- **诚实铁律**：所有数字/状态名/时间值 **verbatim** 来自该图「诚实锚点」（先 `sed -n` 比对再落图）；配色**禁写死 `#hex`**（仅彩色芯片图标文字可 `#fff`）；font ≥9；emoji 22–26；SVG `role="img"` + 中/英 `aria-label`；配一句 `<p class="fig-cap">`。
- **zh/en 双版**：zh 块插中文图、en 块插英文图，**结构对称**（同帧数/同 viewBox/同元素数）；en **无中文残留、无 U+3000、无中文标点**。
- **插入位置**：该深度块末尾（最后一个现有 `.figure` 之后、下一 `<h3>` 或卡片段之前）。**只插入、不动任何现有内容。**
- **自检**（子代理报告，不 build）：贴出新增 zh+en 两段 figure 源码；自查 `grep 'fill="#[0-9a-fA-F]' 新增段` = 0（除 `#fff`）。

## 共享：双审子代理
- **spec 审**：`task` general-purpose **opus-4.8**, reasoning_effort=high, context_tier=long_context。核对：帧序列/数字/触发/旁注是否与 spec 该图一致；数字是否 verbatim 匹配源码锚点；zh/en 是否对称。
- **质量审**：`superpowers:code-reviewer` **opus-4.8**, high, long_context。核对：配色全 `var(--*)` 无写死 hex；SVG 语法合法（标签闭合、viewBox、role/aria-label）；font≥9；不破坏既有结构；en 无中文残留。
- 审出问题 → 我或 implementer 修 → 复审通过才进下一 task。

## 共享：集成验证（全部 task 落盘后，由我统一执行一次）
```bash
cd src && rm -rf __pycache__ && python3 build.py >/dev/null 2>&1; python3 build.py >/dev/null 2>&1 && python3 check_html.py 2>&1 | tail -1   # 期望 0 error
python3 check_links.py 2>&1 | tail -1                                                                                                      # 期望全 resolve
grep -c 'fill="#[0-9a-fA-F]\|stroke="#[0-9a-fA-F]' part9.py                                                                                # 仅 #fff 允许
grep -c '<svg' part9.py                                                                                                                    # 期望 28 → 40
```

---

## Task 1：图① 27.1 凭证池轮换 + 冷却（4 帧）

**Files:**
- Modify: `src/part9.py`（`LESSON_27` 的 `zh` 与 `en` 块，27.1 深度块末尾各插一份）

- [ ] **Step 1：dispatch implementer 子代理画图①（zh+en）**
  - 子代理 = general-purpose opus-4.8，prompt 含「共享：每个 implementer 子代理 prompt 必含」全部条目 + 下述图①设计；**只 edit part9.py、不 build**。
  - **图①设计**（= spec §图①）：含 3 把 key 的 anthropic 池、`least_used` 策略，4 帧横向时间线：
    - T0 · 三把都健康：`#1 count=12 ●OK` `#2 count=8 ●OK` `#3 count=15 ●OK`（●=accent）；least_used 取 request_count 最小 → **#2 高亮(purple) 选中**，注「选中后 #2.count→9」。
    - 箭头`#2 撞 HTTP 429` → T1 · #2 进冷却：#2 变 `EXHAUSTED ●冷却`(amber)，注「盖到期戳 reset_at=now+3600s」；available={#1,#3}。
    - 箭头`下一次请求` → T2 · 跳过空桶：least_used 仅在 {#1(12),#3(15)} 挑 → **#1 高亮**；#2 amber 标「跳过（不再戳已确认空的桶）」。
    - 箭头`1h 后 TTL 到期` → T3 · 复活：#2 `reset→●OK`(accent) 重进 available。
    - 底部旁注条 2 条：①`401(token)→冷却只 300s`；②`token_revoked/terminal-auth→直接 DEAD ●永不复活`(red)，手动 DEAD 24h 后 prune。
  - **诚实锚点**（先 sed 比对源码 `/home/verden/course/hermes-agent/agent/credential_pool.py`）：策略`round_robin/random/least_used`@98-100；`request_count`@153；`least_used=min(available,request_count)`@1356、选中`+1`@1358；`_exhausted_ttl`@250（401=300s@112/429=3600s@113）；`STATUS_DEAD`@64、`token_revoked`@71、DEAD 永不重入@1414；`DEAD_MANUAL_PRUNE_TTL`=24h@89。

- [ ] **Step 2：核对落盘** — 我 `view` 新增 zh+en figure 段，确认插入位置正确、未动现有内容、数字与锚点一致。

- [ ] **Step 3：spec-compliance 审**（task opus-4.8/high/long_context）— 核帧序列/数字/触发/旁注 vs spec 图①、数字 verbatim、zh/en 对称。

- [ ] **Step 4：code-quality 审**（superpowers:code-reviewer opus-4.8/high/long_context）— 配色全 `var(--*)`（除 #fff）、SVG 语法、font≥9、不破坏既有结构、en 无中文残留。

- [ ] **Step 5：修复** 审出的问题（若有），复审通过才进 Task 2。commit 留到全部 task 后统一。

---

## Task 2：图② 27.2 副 LLM 路由三段回退（3 帧）

**Files:**
- Modify: `src/part9.py`（`LESSON_27` 的 `zh` 与 `en` 块，27.2 深度块末尾各插一份）

- [ ] **Step 1：dispatch implementer 子代理画图②（zh+en）**
  - 同「共享 implementer prompt」+ 下述图②设计；只 edit、不 build。
  - **图②设计**（= spec §图②）：一次 `compression` 副任务走 `_resolve_auto` 三段解析，3 帧横向：
    - 帧1 · 试「主 provider+主 model」：`set_runtime_main` 记录的主配置卡（如 `provider=anthropic·model=claude-opus`），该 model 对副任务不可用(plan-only) → **miss(red ✗)**。
    - 箭头`主不可用→下一段` → 帧2 · 试「任务级 fallback_chain」：`auxiliary.compression.fallback_chain` 槽，此例为空/未配 → **miss(✗)**。
    - 箭头`链为空→discovery` → 帧3 · discovery 顺序探测：链 `openrouter→nous→local→api-key`，第一个健康的命中 → **hit(accent ✓)**（openrouter 命中、其余灰显未触达）。
    - 底部旁注条 2 条：①失败 provider 标 `unhealthy 600s(10min)`，TTL 内后续直接跳过；②走此解析的副任务槽 `compression/vision/web_extract/title_generation/curator`。
  - **诚实锚点**（先 sed 比对 `/home/verden/course/hermes-agent/agent/auxiliary_client.py`）：`_resolve_auto`@1884（三段）；`_AUX_UNHEALTHY_TTL_SECONDS`=600@2366；`fallback_chain` 耗尽转 discovery@3108；alias `openrouter/nous`@3072。

- [ ] **Step 2：核对落盘**（同 Task 1 Step 2）。
- [ ] **Step 3：spec-compliance 审**（同上，vs spec 图②）。
- [ ] **Step 4：code-quality 审**（同上）。
- [ ] **Step 5：修复**，复审通过进 Task 3。

---

## Task 3：图③ 27.3 压缩触发：token 增长逐帧（4 帧）

**Files:**
- Modify: `src/part9.py`（`LESSON_27` 的 `zh`/`en` 块，27.3 深度块末尾各插一份）

- [ ] **Step 1：dispatch implementer 画图③（zh+en）**
  - 同「共享 implementer prompt」+ 下述设计；只 edit、不 build。
  - **图③设计**（= spec §图③）：256K 窗口、每帧一个 token 进度条 + 百分比刻度 + 50% 阈值虚线，4 帧横向：
    - T0 · 早期：token 条 ~30%(accent)；50% 阈值虚线；注「有效输入预算 = 窗口 256K − max_tokens 预留」；未触发。
    - 箭头`对话继续增长` → T1 · 触阈值：条涨到 **50%**(`threshold_percent=0.50`) 抵阈值线 → 触发(条变 amber)。
    - 箭头`触发压缩（缓存铁律唯一例外）` → T2 · 压缩中：长历史消息 → 折叠成短摘要块(blue)，条大幅缩短。
    - 箭头`续聊` → T3 · 回落：条回到 ~20%(accent)，重入增长循环。
    - 底部旁注条 2 条：①窗口解析不出 fallback `MINIMUM_CONTEXT_LENGTH=64K`；②小窗口 `_MIN_CTX_TRIGGER_RATIO=0.85` 设上限防误触（阈值≈`min(eff×0.50, eff×0.85)`）；default 256K / Codex 272K。
  - **诚实锚点**（先 sed 比对 `agent/context_compressor.py` + `agent/model_metadata.py`）：`threshold_percent`=0.50@786；`_MIN_CTX_TRIGGER_RATIO`=0.85@722；阈值=`effective_input_budget×threshold_percent`@747/772、小窗 cap@779；`MINIMUM_CONTEXT_LENGTH`=64000@185、default 256K@171、Codex 272K@1432。

- [ ] **Step 2：核对落盘**（同上）。
- [ ] **Step 3：spec-compliance 审**（vs spec 图③）。
- [ ] **Step 4：code-quality 审**（同上）。
- [ ] **Step 5：修复**，复审通过进 Task 4。

---

## Task 4：图④ 28.1 /stop 中断逐帧时间线（4 帧 · 面试经典）

**Files:**
- Modify: `src/part9.py`（`LESSON_28` 的 `zh`/`en` 块，28.1 深度块末尾各插一份）

- [ ] **Step 1：dispatch implementer 画图④（zh+en）**
  - 同「共享 implementer prompt」+ 下述设计；只 edit、不 build。
  - **图④设计**（= spec §图④）：双轨时间线（上轨=主循环、下轨=信号）带 ms 时间戳，4 帧横向：
    - T0 · 0ms · 执行中：agent 在 `iteration N` 跑 `terminal` tool（进度条转）；`_interrupt_requested=False`(accent)。
    - 箭头`用户发 /stop` → T1 · +50ms · 信号到达：`interrupt()` 置 `_interrupt_requested=True`(amber，**只设 flag 不强杀**)；tool **仍在跑**。
    - 箭头`tool 自然完成` → T2 · tool 跑完：返回结果，控制权回主循环边界。
    - 箭头`loop 边界检查 flag` → T3 · 干净退出：`conversation_loop` 边界读 flag→True→干净停止(red，保存状态不丢数据)。
    - 底部旁注条 2 条：①轮询粒度 `time.sleep(0.2)`=**200ms**；②`interrupt()` 扇出到 `_active_children`（每个子也设 flag）；**detach/未注册** child 不在册→断链收不到中断。
  - **诚实锚点**（先 sed 比对 `agent/conversation_loop.py` + `run_agent.py`）：`_interrupt_requested` 边界查@594/1397/2664/3557、`time.sleep(0.2)`@1408/3568；`interrupt()`@2376、置 True@2400、扇出 `_active_children`@2434-2435、循环末 reset@2446。

- [ ] **Step 2：核对落盘**（同上）。
- [ ] **Step 3：spec-compliance 审**（vs spec 图④）。
- [ ] **Step 4：code-quality 审**（同上）。
- [ ] **Step 5：修复**，复审通过进 Task 5。

---

## Task 5：图⑤ 28.2 后台进程生命周期 + 去重（5 帧）

**Files:**
- Modify: `src/part9.py`（`LESSON_28` 的 `zh`/`en` 块，28.2 深度块末尾各插一份）

- [ ] **Step 1：dispatch implementer 画图⑤（zh+en）**
  - 同「共享 implementer prompt」+ 下述设计；只 edit、不 build。
  - **图⑤设计**（= spec §图⑤）：`terminal(background=true,notify_on_complete=true)`，每帧一个进程状态徽章 + 注册表归属，5 帧横向：
    - 帧1 · spawn：进程启动→注册进 `_running`（徽章 `running`+PID+起始时间戳，accent）。
    - 箭头`watcher 周期轮询` → 帧2 · running·监控：watcher 轮询；若配 `watch_patterns`，连续 `WATCH_STRIKE_LIMIT=3` 个 rate-limit window 后**禁用 watch、回退 notify_on_complete**(amber 标这分支)。
    - 箭头`进程退出` → 帧3 · 完成迁移：`_move_to_finished`（`_running`→`finished`，保留 `FINISHED_TTL=1800s(30min)`）。
    - 箭头`完成事件去重` → 帧4 · 去重 gate：`was_running=True` 且不在 `_completion_consumed` → **认定完成(仅此一次)**，加入集合(purple 高亮 gate)。
    - 箭头`触发新 turn` → 帧5 · 只通知一次：触发一次新 agent turn(注入完成消息)；之后 poll 只读状态(`_poll_observed`,read-only)**不再重复通知**。
    - 底部旁注条 2 条：①`processes.json` 仅 gateway **崩溃恢复**用、非完成判定来源；②read-only 查询走 `_poll_observed` **不消费**完成→查状态不会吃掉通知。
  - **诚实锚点**（先 sed 比对 `tools/process_registry.py`）：`_move_to_finished`@483/930/977；`FINISHED_TTL_SECONDS`=1800@59；`WATCH_STRIKE_LIMIT`=3@69；`_completion_consumed`@178；`_poll_observed`@188；`CHECKPOINT_PATH`(processes.json)@55。

- [ ] **Step 2：核对落盘**（同上）。
- [ ] **Step 3：spec-compliance 审**（vs spec 图⑤）。
- [ ] **Step 4：code-quality 审**（同上）。
- [ ] **Step 5：修复**，复审通过进 Task 6。

---

## Task 6：图⑥ 28.3 原子写防写半截：文件系统逐帧状态（4 帧）

**Files:**
- Modify: `src/part9.py`（`LESSON_28` 的 `zh`/`en` 块，28.3 深度块末尾各插一份）

- [ ] **Step 1：dispatch implementer 画图⑥（zh+en）**
  - 同「共享 implementer prompt」+ 下述设计；只 edit、不 build。
  - **图⑥设计**（= spec §图⑥）：`_atomic_write` 覆盖 `foo.py`，每帧画目录里的文件状态，4 帧横向：
    - 帧1 · 准备：目录里 `foo.py`(旧内容完好,accent)；`mktemp -p` 在**同目录**建 `tmp.XXXX`(空,blue)。
    - 箭头`cat > tmp 写入` → 帧2 · 写临时：新内容**全部**写进 tmp；`foo.py` **仍是旧内容**——崩溃只丢临时文件(红框标「崩溃安全点」)。
    - 箭头`mv -f tmp foo.py` → 帧3 · 原子替换：`mv -f` 原子重命名→`foo.py` 现为新内容(accent)，tmp 消失(注「同 FS rename 原子：要么旧要么新」)。
    - 箭头`patch 路径读回` → 帧4 · 读回校验：patch 写后 `cat` 读回 `foo.py` 校验落盘(`verify_cmd`,purple ✓)。
    - 底部旁注条 2 条：①用 shell `mv -f` 而非 `os.replace`（统一走终端后端，docker/ssh 一致）；②跨 FS 时 rename 退化 copy+unlink→**非原子**，故 `mktemp -p` 刻意落目标同目录。
  - **诚实锚点**（先 sed 比对 `tools/file_operations.py`）：`_atomic_write`@937=`mktemp -p`@975(fallback@976)+`mv -f`@986；`patch_replace`@457/1465；写后 `cat` 读回校验@1539-1540。

- [ ] **Step 2：核对落盘**（同上）。
- [ ] **Step 3：spec-compliance 审**（vs spec 图⑥）。
- [ ] **Step 4：code-quality 审**（同上）。
- [ ] **Step 5：修复**，复审通过进集成。

---

## Task 7：集成、验证、提交、部署

**Files:** `src/part9.py`（已改）；构建产物 `lessons/lesson-27.html`/`lesson-28.html`/`index.html`、`print_zh.html`/`print_en.html`。

- [ ] **Step 1：build×2 + check_html**
  Run: `cd src && rm -rf __pycache__ && python3 build.py >/dev/null 2>&1; python3 build.py >/dev/null 2>&1 && python3 check_html.py 2>&1 | tail -1`
  Expected: `0 error`（visual-blocks WARN 等软警告无所谓）。
- [ ] **Step 2：链接 + hex + SVG 计数核验**
  Run: `cd src && python3 check_links.py 2>&1 | tail -1 && grep -c 'fill="#[0-9a-fA-F]\|stroke="#[0-9a-fA-F]' part9.py && grep -c '<svg' part9.py`
  Expected: 链接全 resolve；hex 计数仅含既有 `#fff`（无新增彩色 hex）；`<svg` 计数 = **40**（28+12）。
- [ ] **Step 3：抽查数字 verbatim** — 随机挑 3–5 个新图数字（如 3600s、0.50、200ms、1800、64K）`grep` 源码确认一致。
- [ ] **Step 4：重建 print 版**
  Run: `cd src && python3 build_print.py >/dev/null 2>&1 && echo done`
- [ ] **Step 5：commit + push（自动 redeploy）**
  ```bash
  git add src/part9.py lessons/ index.html print_zh.html print_en.html docs/superpowers/plans/2026-06-27-ch27-ch28-richviz-frames.md
  git -c user.name="verdenmax" -c user.email="verdenmax@users.noreply.github.com" commit -m "feat(ch27/28): 新增 6 张逐帧状态快照序列 SVG（富可视化）" # + Co-authored-by trailer
  git push   # core.sshCommand 已设 ssh -p 22；Pages ~75-90s 后 live
  ```
- [ ] **Step 6：验证 live** — `curl -sI https://verdenmax.github.io/hermes-agent-visual-guide/lessons/lesson-27.html | head -1`（期望 200）。

---

## Self-Review（spec 覆盖 / 占位 / 一致性）
- **spec 覆盖**：spec 6 张图 ↔ Task 1–6 一一对应；Task 7 = spec「实施与审查流程」+「验收」。无遗漏。
- **占位扫描**：每 Task Step 1 含完整图设计 + verbatim 锚点 + 源码路径；无 TBD/「类似上面」/空 handler。
- **类型/命名一致**：状态色语义（accent/amber/red/blue/purple）、viewBox 680、font≥9、`_completion_consumed`/`_poll_observed`/`_active_children`/`_atomic_write` 等符号名跨 Task 与 spec、源码锚点一致。
- **范围**：纯新增 6 图，单 plan 可完成，不改现有 SVG/正文/quiz/注册。

