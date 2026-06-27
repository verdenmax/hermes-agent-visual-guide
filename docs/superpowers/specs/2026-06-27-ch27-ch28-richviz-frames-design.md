# ch27 + ch28 富可视化增强 Spec — 逐帧状态快照序列

## 目标
为 Part 8（ch27 模型层 / ch28 运行时韧性）的 **6 个深度块各新增 1 张「逐帧状态快照序列」SVG**（共 6 张主图 × zh/en 双语 = **12 个 SVG**），让每个机制都有一张**复杂、贴近真实场景、能充分说明**的动态演化图。现有 28 张 SVG **全部保留不动**，本次是**纯新增**。

## 背景与动机
- 现状：ch27/28 现有 28 张 SVG **全部是「框架/流程」型**——状态机、决策树、矩阵、瀑布、扇出、对比泳道（抽象结构）。
- 全书审计确认：**整本指南没有一张「带真实数字/时间戳、随步骤演化」的场景快照图**。
- 用户诉求：补上**逐帧快照序列**——每帧 = 该时刻一个**真实状态的快照**（带具体数字、时间戳、计数、状态色），帧间用箭头 + **触发条件**串联，把"机制如何随时间/步骤一步步演化"讲生动。
- 与现有流程图的区别：流程图讲**结构**（有哪些状态/分支）；逐帧序列讲**过程**（一个具体场景里，状态如何一帧帧变化）。两者互补。

## 定位（YAGNI）
- 只增 6 张主图，**不改任何现有 SVG、不改正文 `<p>`/codefile、不动 quiz**。
- 只编辑 `src/part9.py`（`LESSON_27` + `LESSON_28` 的 zh/en 块），在每个深度块末尾（`</div>` 收尾后、下一 `<h3>` 前）插入新的 `.figure`。
- **无需改** `registry.py` / `shell.py` / `quizzes.py` / `check_html.py`（图是插进既有 LESSON，注册关系不变）。

## 通用「逐帧快照序列」视觉语言（6 张图共享，保持节奏统一）
每张图遵循同一套构图语言，读者一眼就知道"这是一条时间线 / 步骤链"：

1. **帧卡（frame card）**：每帧一个圆角矩形卡（`rx≈8`），卡内画**该时刻的真实状态快照**——不是抽象标签，而是带**具体数值**的小部件（如 3 个 key 芯片各带 `count=N` + 状态色点；token 进度条带百分比刻度；进程状态徽章带时间戳）。
2. **帧头（frame header）**：每帧顶部一行 `时刻/步骤号 + 一句话状态`（如 `T0 · 三把都健康`、`+50ms · /stop 到达`、`帧3 · discovery 命中`）。时刻用等宽数字感（`font-weight:700`）。
3. **帧间连接（transition）**：帧与帧之间一个箭头（`var(--line)` 描边 + 小三角），箭头上方一个**触发条件**小标签（如 `429 命中`、`tool 跑完`、`涨到 50%`）——这是"为什么会进入下一帧"的关键。
4. **状态色编码**（全程一致，复用全书语义）：健康/正常 `var(--accent)`；冷却/警告 `var(--amber)`；死亡/失败/中断 `var(--red)`；探测/中间态 `var(--blue)`；选中/命中高亮 `var(--purple)`；底色 `var(--panel)`/`var(--panel-2)`，描边 `var(--line)`，文字 `var(--ink)`/`var(--muted)`。
5. **底部旁注条（side-note rail）**：图底一条窄横带，写 1–2 条**分支/对照旁注**（如"若是 401 → 冷却只 5min"、"detach 的 child 不在册 → 断链"），用 `var(--muted)` 小字 + 小图标，区别于主时间线。
6. **布局**：主时间线**横向排列**帧卡（3–5 帧）；帧多时可折行成 2 行网格。viewBox 统一 **680 宽**（高度按内容 360–460），`.figure svg{width:100%}` 自适应。

## 风格与诚实铁律（沿用全书 + Part 8）
- 双语：`LESSON_27`/`LESSON_28` 的 `"zh"` 与 `"en"` 块各插一份；**结构对称**（相同帧数、相同 viewBox、相同元素数），en 块**无残留中文 / 无全角空格 U+3000 / 无中文标点**。
- **配色只用 CSS 变量** `var(--accent/--blue/--purple/--red/--amber/--ink/--muted/--line/--panel/--panel-2/...-soft/...-ink)`；**禁写死 `#hex`**（唯一例外：彩色芯片上的图标文字可用 `#fff`）。验证：`grep -c 'fill="#\|stroke="#' src/part9.py` 不得因本次新增而增加（除 `#fff`）。
- font-size：帧头/正文标注 ≥9（Part 8 内部最低 9）；次级标注 9–10.5；emoji 22–26。
- 每张 SVG 必须 `role="img"` + 信息完整的 `aria-label`（中文图写中文 label，en 图写英文 label）。
- 每个 `.figure` 配一句 `<p class="fig-cap">` 图注（zh/en 各一）。
- **所有数字/状态名/时间值 verbatim 来自源码**——见各图「诚实锚点」；实施时 subagent 先 `sed -n` 比对再落图。
- HTML 转义：`<`→`&lt;`、`>`→`&gt;`、`&`→`&amp;`；codefile 里 Python 三引号写 `&quot;&quot;&quot;`（本次只画 SVG，一般不涉及）。

## 验收（每张图 + 整体）
- `cd src && rm -rf __pycache__ && python3 build.py >/dev/null 2>&1; python3 build.py >/dev/null 2>&1 && python3 check_html.py 2>&1 | tail -1` → **0 error**。
- `python3 check_links.py 2>&1 | tail -1` → 全 resolve。
- `grep -c 'fill="#[0-9a-fA-F]\|stroke="#[0-9a-fA-F]' src/part9.py`（排除 `#fff`）增量为 0。
- zh/en SVG 数各 +6（part9 `<svg>` 计数 28 → 40）。
- 抽查 3–5 个数字 vs 源码 verbatim 一致。

---

## 图① — 27.1 凭证池轮换 + 冷却（4 帧 · least_used 策略）
**插入位置**：`LESSON_27` 中 27.1 深度块末尾（现有「状态机/冷却决策/轮换对比」3 图之后）。
**场景**：一个含 3 把 key 的 anthropic 池，`least_used` 策略，演示「撞限流→冷却→跳过→复活」全过程。

**帧序列（横向 4 帧）**：
- **T0 · 三把都健康**：三个 key 芯片 — `#1 count=12 ●OK`、`#2 count=8 ●OK`、`#3 count=15 ●OK`（●= `var(--accent)`）。`least_used` 在 available 里取 `request_count` 最小 → **#2 高亮（`var(--purple)`）被选中**；小注「选中后 #2.count → 9」。
- **触发箭头**：`#2 请求撞 HTTP 429`
- **T1 · #2 进入冷却**：#2 变 `EXHAUSTED ●冷却`（`var(--amber)`），标注「盖到期戳 reset_at = now + 3600s」；#1/#3 仍 OK。available 池 = {#1, #3}。
- **触发箭头**：`下一次请求`
- **T2 · 跳过空桶**：`least_used` 只在 available={#1(12), #3(15)} 里挑 → **#1 高亮被选中**；#2 灰显/amber、明确标「跳过（不再去戳已确认空的桶）」。
- **触发箭头**：`1h 后 TTL 到期`
- **T3 · 复活**：#2 `reset → ●OK`（`var(--accent)`）重新进 available，池恢复 3 把可选。
**底部旁注条（2 条）**：① `401（token 问题）→ 冷却只 300s（5min）`；② `token_revoked / terminal-auth → 直接 DEAD ●永不复活（var(--red)）`，需重新鉴权同步才清；手动 DEAD 24h 后 prune。
**诚实锚点**：`agent/credential_pool.py` — 策略名 `round_robin/random/least_used`@98-100；`request_count`@153；`least_used` = `min(available, key=request_count)`@1356、选中后 `+1`@1358；`_exhausted_ttl`@250（401=300s@112 / 429=3600s@113 / default=3600s@114）；`STATUS_DEAD`@64、`token_revoked`@71、DEAD 永不重入@1414；`DEAD_MANUAL_PRUNE_TTL`=24h@89。
**aria-label 要点**：四帧时间线 + least_used 取最小计数 + 429→3600s 冷却 + 跳过空桶 + 到期复活 + 401/DEAD 旁注。

---

## 图② — 27.2 副 LLM 路由三段回退（3 帧 · compression 任务）
**插入位置**：`LESSON_27` 中 27.2 深度块末尾（现有「路由决策树/per-task 矩阵」2 图之后）。
**场景**：一次 `compression` 副任务请求走 `_resolve_auto` 的三段解析，逐段回退直到命中。

**帧序列（横向 3 帧）**：
- **帧1 · 试「主 provider + 主 model」**：画 `set_runtime_main` 记录的主配置卡（如 `provider=anthropic · model=claude-opus`）；判定该 model 对副任务不可用（plan-only / 不合适）→ **miss（`var(--red)` ✗）**。
- **触发箭头**：`主不可用 → 下一段`
- **帧2 · 试「任务级 fallback_chain」**：画 `auxiliary.compression.fallback_chain` 配置槽；此例为空/未配 → **miss（✗）**。
- **触发箭头**：`链为空 → discovery`
- **帧3 · discovery 顺序探测**：一条探测链 `openrouter → nous → local → api-key`，逐个探测，**第一个健康的命中** → **hit（`var(--accent)` ✓）**（图示 openrouter 命中、其余未触达灰显）。
**底部旁注条（2 条）**：① 失败的 provider 标 `unhealthy 600s（10min）`，TTL 内后续请求**直接跳过**；② 走这条解析的副任务槽：`compression / vision / web_extract / title_generation / curator`（各自独立解析）。
**诚实锚点**：`agent/auxiliary_client.py` — `_resolve_auto`@1884（三段：主+model → fallback_chain → discovery）；`_AUX_UNHEALTHY_TTL_SECONDS`=600@2366；`fallback_chain` 耗尽后转 discovery@3108；alias `openrouter/nous`@3072。
**aria-label 要点**：三段逐级回退 + 每段 miss/hit + discovery 探测顺序 + unhealthy 600s 旁注 + 副任务槽列举。

---

## 图③ — 27.3 压缩触发：token 增长逐帧（4 帧 · 256K 窗口）
**插入位置**：`LESSON_27` 中 27.3 深度块末尾（现有「解析瀑布/窗口→阈值」2 图之后）。
**场景**：256K 窗口的一轮长对话，token 一帧帧涨到 50% 阈值触发压缩、再回落，凸显「为什么压缩是缓存铁律的唯一例外」。

**帧序列（横向 4 帧 · 每帧一个 token 进度条 + 百分比刻度 + 50% 阈值虚线）**：
- **T0 · 早期**：token 条占 ~30%（短，`var(--accent)`）；阈值虚线立在 50%；标注「有效输入预算 = 窗口 256K − max_tokens 预留」。未触发。
- **触发箭头**：`对话继续增长`
- **T1 · 触阈值**：token 条涨到 **50%**（`threshold_percent=0.50`），刚好抵到阈值虚线 → 触发判定（条变 `var(--amber)`）。
- **触发箭头**：`触发压缩（缓存铁律唯一例外）`
- **T2 · 压缩中**：图示一段长历史消息 → 折叠成短摘要块（`var(--blue)`）；token 条大幅缩短。
- **触发箭头**：`续聊`
- **T3 · 回落**：token 条回到低位（~20%，`var(--accent)`），重新进入增长循环。
**底部旁注条（2 条）**：① 窗口**解析不出**时 fallback `MINIMUM_CONTEXT_LENGTH=64K`；② 小窗口用 `_MIN_CTX_TRIGGER_RATIO=0.85` 设上限防误触（阈值 ≈ `min(eff×0.50, eff×0.85)`）；default 256K / Codex 272K。
**诚实锚点**：`agent/context_compressor.py` — `threshold_percent`=0.50@786；`_MIN_CTX_TRIGGER_RATIO`=0.85@722；阈值 = `effective_input_budget × threshold_percent`@747/772、小窗 cap@779。`agent/model_metadata.py` — `MINIMUM_CONTEXT_LENGTH`=64000@185、default 256K@171、Codex 272K@1432。
**aria-label 要点**：token 30%→50% 触阈值→压缩折叠→回落循环 + 有效预算公式 + 64K fallback + 0.85 防误触旁注。

---

## 图④ — 28.1 /stop 中断逐帧时间线（4 帧 · 面试经典）
**插入位置**：`LESSON_28` 中 28.1 深度块末尾（现有「中断扇出/cooperative vs preemptive」2 图之后）。
**场景**：agent 正在执行一个耗时 tool 时用户发 `/stop`，演示**协作式中断**——为什么"立刻设 flag、但不强杀进行中的 tool、回到 loop 边界才退出"。双轨时间线（上轨=主循环状态，下轨=信号），带 ms 时间戳。

**帧序列（横向 4 帧）**：
- **T0 · 0ms · 执行中**：agent 在 `iteration N`，正跑 `terminal` tool（长操作进度条转动）；`_interrupt_requested = False`（`var(--accent)`）。
- **触发箭头**：`用户发 /stop`
- **T1 · +50ms · 信号到达**：`interrupt()` 把 `_interrupt_requested = True`（`var(--amber)`，**只设 flag、不强杀**）；tool **仍在跑**（强调不打断进行中的 tool）。
- **触发箭头**：`tool 自然完成`
- **T2 · tool 跑完**：tool 返回结果，控制权回到主循环边界。
- **触发箭头**：`loop 边界检查 flag`
- **T3 · 干净退出**：`conversation_loop` 在边界读 `_interrupt_requested → True` → 干净停止（`var(--red)`，保存状态、不丢数据）。
**底部旁注条（2 条）**：① 轮询粒度 `time.sleep(0.2)` = **200ms**；② `interrupt()` **扇出**到 `_active_children`（每个子 agent 也设 flag）；**detach / 未注册**的 child 不在册 → 断链、收不到中断。
**诚实锚点**：`agent/conversation_loop.py` — `_interrupt_requested` 边界检查@594/1397/2664/3557、`time.sleep(0.2)`@1408/3568。`run_agent.py` — `interrupt()`@2376、置 `True`@2400、扇出 `_active_children`@2434-2435、循环末 reset@2446。
**aria-label 要点**：tool 执行中 /stop→只设 flag 不强杀→tool 自然跑完→loop 边界查 flag 干净退出 + 200ms 轮询 + 扇出/断链旁注。

---

## 图⑤ — 28.2 后台进程生命周期 + 去重（5 帧）
**插入位置**：`LESSON_28` 中 28.2 深度块末尾（现有「生命周期+去重/durability 对比」2 图之后）。
**场景**：`terminal(background=true, notify_on_complete=true)` 启动一个后台进程，从 spawn 到完成通知，重点画**去重 gate**——为什么"完成只通知一次、查状态不会吃掉通知"。

**帧序列（横向 5 帧 · 每帧一个进程状态徽章 + 注册表归属）**：
- **帧1 · spawn**：进程启动 → 注册进 `_running`（徽章 `running`，带 PID + 起始时间戳，`var(--accent)`）。
- **触发箭头**：`watcher 周期轮询`
- **帧2 · running · 监控**：watcher 轮询进程；若配 `watch_patterns`（输出模式匹配），strike 累积——连续 `WATCH_STRIKE_LIMIT=3` 个 rate-limit window 后**禁用 watch、回退到 notify_on_complete**（`var(--amber)` 标这条分支）。
- **触发箭头**：`进程退出`
- **帧3 · 完成迁移**：进程退出 → `_move_to_finished`（从 `_running` 移到 `finished`，保留 `FINISHED_TTL=1800s（30min）`）。
- **触发箭头**：`完成事件去重`
- **帧4 · 去重 gate**：判定 `was_running=True` 且不在 `_completion_consumed` 集合 → **认定完成（仅此一次）**，加入 `_completion_consumed`（`var(--purple)` 高亮 gate）。
- **触发箭头**：`触发新 turn`
- **帧5 · 只通知一次**：触发一次新 agent turn（注入完成消息）；之后的 poll 只读状态（`_poll_observed`，read-only）**不再重复通知**。
**底部旁注条（2 条）**：① `processes.json` checkpoint 仅 gateway **崩溃恢复**用，**不是**完成判定来源；② read-only 状态查询走 `_poll_observed`、**不消费**完成 → 查状态不会"吃掉"那一次通知。
**诚实锚点**：`tools/process_registry.py` — `_move_to_finished`@483/930/977；`FINISHED_TTL_SECONDS`=1800@59；`WATCH_STRIKE_LIMIT`=3@69；`_completion_consumed`@178；`_poll_observed`@188；`processes.json`=`CHECKPOINT_PATH`@55。
**aria-label 要点**：spawn 注册→running 监控(STRIKE3 禁 watch)→退出迁移(保留 30min)→去重 gate→只通知一次 + processes.json 仅崩溃恢复 + 查状态不消费旁注。

---

## 图⑥ — 28.3 原子写防写半截：文件系统逐帧状态（4 帧）
**插入位置**：`LESSON_28` 中 28.3 深度块末尾（现有「安全编辑管线/跨 FS rename」2 图之后）。
**场景**：`_atomic_write` 覆盖 `foo.py`，逐帧画**文件系统目录里的真实状态**，凸显"任何时刻崩溃，原文件都不会留半截"。

**帧序列（横向 4 帧 · 每帧画目录里的文件状态）**：
- **帧1 · 准备**：目录里 `foo.py`（旧内容完好，`var(--accent)`）；`mktemp -p` 在**同目录**建临时文件 `tmp.XXXX`（空，`var(--blue)`）。
- **触发箭头**：`cat > tmp 写入`
- **帧2 · 写临时**：新内容**全部**写进 `tmp.XXXX`；此刻 `foo.py` **仍是旧内容** — 崩溃也只丢临时文件、原文件完好（红框标「崩溃安全点」）。
- **触发箭头**：`mv -f tmp foo.py`
- **帧3 · 原子替换**：`mv -f` 把 tmp 原子重命名为 `foo.py`（同 FS 上 rename 原子：要么旧、要么新，没有半截）；`foo.py` 现为新内容（`var(--accent)`），tmp 消失。
- **触发箭头**：`patch 路径读回`
- **帧4 · 读回校验**：patch 写后 `cat` 读回 `foo.py` 校验内容确实落盘（`verify_cmd`，`var(--purple)` ✓）。
**底部旁注条（2 条）**：① 用 shell `mv -f` 而非 `os.replace`（统一走终端后端，docker/ssh 也一致）；② 跨 FS（tmp 与目标不同挂载）时 rename 退化为 copy+unlink → **非原子**，所以 `mktemp -p` 刻意落在**目标同目录**。
**诚实锚点**：`tools/file_operations.py` — `_atomic_write`@937 = `mktemp -p`@975（fallback@976）+ `mv -f`@986；`patch_replace`@457/1465；写后 `cat` 读回校验@1539-1540。
**aria-label 要点**：原文件完好+同目录建 tmp→全写 tmp（崩溃安全点）→mv -f 原子替换→读回校验 + mv -f 非 os.replace + 跨 FS 非原子旁注。

---

## 实施与审查流程
- 6 张图分 6 个 implementer 任务（或按章 ch27 三图、ch28 三图分批），每个 implementer = general-purpose **opus-4.8**，prompt 含：该图完整帧设计 + 诚实锚点 + 通用视觉语言 + 验证命令 + 范例（part9 现有 SVG + part1 LESSON_04 沙漏 + part2 LESSON_06 缓存对比）。implementer **只 edit `src/part9.py` 不 build**（避免全局 lessons/ 竞争）。
- 每张图（或每批）跑**双审**：spec-compliance reviewer（opus-4.8, high, long_context）→ code-quality reviewer（superpowers:code-reviewer, opus-4.8, high, long_context）→ 修复循环。
- 全部落盘后由我统一 `rm -rf __pycache__ && build×2 && check_html`（0 error）+ `check_links` + hex 增量核验 + 抽查数字 verbatim，再 commit + push（自动 redeploy）。

## 自检清单（spec 自审）
- [x] 无 TBD/占位：6 张图每帧画什么、什么色、什么数字、什么触发条件、什么旁注，全部写明。
- [x] 内部一致：6 图共享同一套视觉语言（帧卡/帧头/触发箭头/状态色/旁注条/680 宽）。
- [x] 诚实闭环：每图列 verbatim `file:line` 锚点（已逐一 grep 核实）。
- [x] 范围聚焦：纯新增 6 图，不改现有 SVG/正文/quiz，单一 plan 可执行完。

