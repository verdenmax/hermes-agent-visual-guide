# ch27 + ch28 Spec — 深入篇·模型与运行时内幕

## 目标
为 26 章正文之外新增 **Part 8「深入篇·模型与运行时内幕」**，两章深挖前面章节"提了名字但没讲透"的核心机制——它们都是**真实存在、容易踩坑、面试/实战高频**的代码点。每个机制配 verbatim 源码（`file:line`）+ 自绘机制 SVG（状态机/决策树/扇出/时序图为主），图文配合讲透「设计成这样是为了对抗什么、不这么做会怎么踩坑」。

## 定位
- 正文 26 章（ch1–26）是主线，**不动、不 renumber**。ch26 避坑指南仍作 Part 7 收尾。
- Part 8（ch27–28）追加在最后，定位为「想再深入的读者」的**进阶机制深挖**——核心 26 章读完后，这两章把最大的两块技术真空补上。
- 与 ch26 的区别：ch26 是**实践者视角的症状→根因→对策速查**（广而浅地覆盖很多坑）；ch27/28 是**单点机制的深度剖析**（窄而深地讲透 6 个具体机制的内部设计与边界）。

## 范围（YAGNI）
- **ch27「模型·凭证·路由层」**：3 个深度块 — 凭证池状态机 / 副 LLM 路由 / context-length 解析→压缩阈值。
- **ch28「运行时韧性：中断·后台·文件」**：3 个深度块 — 中断传播扇出 / 后台进程生命周期 / 安全文件编辑管线。
- **#7（Anthropic 缓存 4 断点 + thinking 签名）** 不进新章，作为 **ch6 的 1 张补充小 SVG**（深化既有缓存章），单独一个小任务。
- 不新增其它主题；不重写既有章节（除 ch6 加一张图）。

## 风格规范（沿用全书 + ch26 模式）
- 双语 `LESSON_NN = {"zh": r"""...""", "en": r"""..."""}`，在 `src/part9.py`（新文件，ch27/28 都放这里）。
- 每章结构：`lead` → 🔌 analogy 卡 → 🌍 宏观/macro 段 → 3 个 🔬 深度块（每块：机制说明 `<p>` + verbatim 源码 `codefile` + 1–2 张机制 SVG）→ 🎯 设计取舍框 → 📌 本课要点卡（5–6 条）→ quiz（在 `quizzes.py`）。
- **SVG 以机制图为主**：状态机、决策树、扇出图、时序图、对比泳道。每章 **7–10 张**，多画（用户偏好）。
- 深度块**不强求 ❌反例/✅正例 对比**（那是 ch26 的实践坑模式）；这里以**"机制 + verbatim 源码 + 图解"**为主，像 ch26 的 E1/E3 机制块。可在关键坑处点出"不这么做会怎样"。
- 诚实铁律（与全书一致）：SVG 配色**只用 CSS 变量** `var(--*)`（禁写死 #hex，除 `#fff` 图标文字）；font-size 主标题/正文 ≥11、次要标注可到 9–10.5（全书惯例）、emoji 22–26；SVG `role="img" aria-label`；zh/en 结构对称、en 无残留中文/无全角空格 U+3000/无双 em-dash `——`；所有源码引用 **verbatim**（先跑 `sed -n` 比对，HTML 转义 `<`→`&lt;` 等，Python 三引号写 `&quot;&quot;&quot;`）。
- 注册：`registry.py` 加 `import part9` + 2 个 CONTENT 条目；`shell.py` PAGES 加 ch27/28 两行（Part 8）；`quizzes.py` 加 2 个 quiz；`check_html.py` 无需改（DIAGRAM_CLASSES 已含 figure）。

---

## ch27「模型·凭证·路由层」

**lead**：模型不是一个端点，而是一个需要**调度**的资源池——多把 API key 要轮换与熔断、不同的"副任务"要路由到不同模型、每个模型的上下文窗口要先**算出来**才能决定何时压缩。这一章拆开 Hermes 在「模型层」最容易被忽视的三套机制。

**🔌 analogy · 能源调度中心**：一堆电厂（API key / provider），有的满载跳闸进入冷却、有的彻底烧毁永久退役；调度员既**绝不能反复去戳一座已确认没电的电厂**（浪费往返、还可能被进一步惩罚），又要为不同负载（主厨房 vs 后勤打杂）派**不同机组**，还得先知道每座电厂的**额定功率**才能安排调度。

**🌍 macro**：模型层的三个隐藏复杂度——① 凭证不是一把 key，是一个**有状态的池**；② "调用模型"不止主对话，还有一堆**副 LLM 任务**各走各的路由；③ "上下文多大"不是常量，是**分层解析**出来的，并直接决定压缩何时触发。

### 27.1 🔬 凭证池状态机（credential_pool）
- **机制**：同 provider 的多把 key 组成持久化池，每把 key 有状态 `OK → EXHAUSTED(限时冷却) → DEAD(永久排除)`；`select()` 先清理过期冷却再按策略（random / least_used / round_robin）挑；`mark_exhausted_and_rotate()` 标记失败键后立即重选。
- **核心坑**：**绝不 re-probe 一个已确认空的 bucket**——`DEAD` 无条件排除，`EXHAUSTED` 只在 `last_error_reset_at` 或 TTL 后才回归；429 给 1h 冷却、401 给 5m，并解析 provider 的 `reset_at` / "retry after" 文本覆盖默认 TTL。手动 DEAD 的 key 24h 后清除，singleton-seeded DEAD 保留到重新鉴权同步。
- **诚实锚点**（verbatim）：`agent/credential_pool.py:488-540`（DEAD/EXHAUSTED 语义）、`:250-256`（TTL 429=1h/401=5m）、`:289-345`（reset_at 解析）、`:1224-1374`（select/策略）、`:1383-1427`（mark_exhausted_and_rotate）。
- **SVG**：① **状态机图** OK→EXHAUSTED→DEAD→reauth/sync（节点+转移条件）；② **限流冷却决策** 401→5m / 429→1h / reset_at 覆盖；③ **轮换策略对比** random vs least_used vs round_robin（一行 key 池，三种选法高亮不同 key）。

### 27.2 🔬 副 LLM 路由（auxiliary_client，最大 agent 模块 274K）
- **机制**：压缩 / 视觉 / 搜索 / 标题生成等**副任务**各自路由到"最合适的 provider+model"。`_resolve_auto()` 三段解析：① 用当前**主 provider+model**（含运行期 base_url/key，由 `set_runtime_main()` 同步，不用陈旧 config）；② 查 `auxiliary.<task>.fallback_chain` 再查顶层 fallback；③ 走 discovery 链 `openrouter → nous → local/custom → api-key`。Codex 故意不在通用链里。
- **核心坑**：per-task pinning 是真的（每个副任务能独立钉 provider/model）；**402/额度错误把 provider 标 unhealthy 藏 10 分钟**（`_mark_provider_unhealthy`），避免重复撞墙；通用 fallback 链可能**静默选了更便宜/不同的模型**，除非显式钉死。
- **诚实锚点**：`agent/auxiliary_client.py:3322-3458`（_resolve_auto 三段）、`:2346-2444`（unhealthy 缓存）、`:1868-1894`（set_runtime_main）、`:318-345`（各 provider 默认副模型）。
- **SVG**：④ **路由决策树** _resolve_auto 三段（主→fallback链→discovery链，含 unhealthy 跳过分支）；⑤ **per-task 路由矩阵** curator/vision/embedding/title/session_search → 各自 provider/model（表格化）。

### 27.3 🔬 context-length 解析 → 压缩阈值（model_metadata + context_compressor）
- **机制**：压缩不是"到 X% 就压"，而是先**分层解析出真实上下文窗口**（config → 持久缓存 → 各 provider probe：Bedrock / 自定义 /models / 本地探测 / Anthropic / Codex / Nous / OpenRouter / models.dev → 硬编码默认），再由 `_compute_threshold_tokens()` 算阈值（小窗口或大 max_tokens 预留时用 85%，并 floor 在 MINIMUM_CONTEXT_LENGTH）。
- **核心坑**：某些 provider 要 **bypass 陈旧缓存**（LM Studio / Nous / Codex / Kimi / MiniMax / Grok 边缘情况）；Codex 探 `chatgpt.com/backend-api/codex/models` 的 `context_window`；本地 Ollama 优先 `num_ctx` 而非 GGUF max。窗口算错 → 压缩要么过早（浪费）要么过晚（被 provider 拒）。
- **诚实锚点**：`agent/model_metadata.py:1613-1978`（get_model_context_length 分层）、`agent/context_compressor.py:742-781`（_compute_threshold_tokens）、`:783-845`。
- **SVG**：⑥ **解析链图** config→cache→各 provider probe→default（瀑布/优先级链）；⑦ **窗口→阈值图** resolved window × max_tokens 预留 → 触发阈值（数轴 + 触发点）。

### ch27 收尾
- 🎯 **设计框**：三套机制共享一个理念——**把"模型"当成需要调度的有状态资源，而非无状态端点**；呼应「自我进化/韧性」与「窄腰」（副任务路由让核心不必内嵌多 provider 逻辑）。
- 📌 **本课要点卡**（5–6 条）：凭证池状态机 + 不 re-probe 空 bucket；副 LLM 三段路由 + per-task pinning + unhealthy 缓存；context-length 分层解析驱动压缩阈值；诚实数字（429=1h/401=5m、unhealthy=10min、压缩 85% 边缘）。

---

## ch28「运行时韧性：中断·后台·文件」

**lead**：一个跑了几十轮、还开着后台进程、正在改文件的 agent，要怎么**安全地急停、可靠地知道后台干完没、原子地落盘**？这一章拆开 Hermes 在「运行时」最容易出正确性 bug 的三套机制——它们的共同主题是：在一个**异步、可中断、可崩溃**的世界里守住正确性。

**🔌 analogy · 飞行中的紧急程序**：急停不是瞬间的——飞行员拉杆后，飞机要到**下一个稳定点**才真正改出（中断是协作式的，不是抢占式的）；后台引擎要么**真在转**要么**早就停了**，仪表得如实反映、还不能重复报警（通知去重）；要改飞行计划，先在草稿上写好、**校验无误再原子换上**正在用的那份（temp+rename）。

**🌍 macro**：运行时韧性的三个正确性陷阱——① 中断**只在检查点生效**，且**不会自动传给子代理**；② 后台进程的"持久"几乎全是**进程内幻觉**；③ 文件落盘的原子性**挂在一个不起眼的 rename 上**。

### 28.1 🔬 中断传播扇出（interrupt propagation）
- **机制**：`/stop` 设 `agent._interrupt_requested`，主循环**在循环边界轮询**它；子代理传播需**显式** `child.interrupt()`；流式回调与 retry 退避里也各有中断检查（retry sleep 每 200ms poll）。
- **核心坑**：中断是**协作式非抢占式**——一次 API 调用或一个 tool 执行**中途不会立即停**，要等到下一个检查点；**子代理传播极易漏**：父代理必须显式把中断传下去，否则子代理在自己的流式/工具执行里继续跑；async 批量路径另走 `interrupt_fn`。
- **诚实锚点**：`agent/conversation_loop.py:589-599`（循环边界检查）、`:1393-1408`（retry 200ms poll）、`:1140-1143`、`:1670-1736`（流式）；`tools/delegate_tool.py:1658-1676`、`:2288-2304`、`:2551-2570`（child interrupt / interrupt_fn）。
- **SVG**：⑧ **中断扇出图** parent loop → child → stream → retry（四条传播路径 + 各自检查点）；⑨ **cooperative vs preemptive 时序** 一条时间轴，interrupt 在 tool 调用中途到达 → 标"挂起等待"→ 到下个检查点才真正停（对比抢占式的瞬停虚线）。

### 28.2 🔬 后台进程生命周期（process_registry）
- **机制**：后台进程登记在内存 registry（`_running` / `_finished`），带输出缓冲、watch 通知、wait/poll/kill；崩溃恢复靠 `processes.json` 检查点（仅为**网关崩溃**恢复）。`notify_on_complete` 在 `_move_to_finished()` 时发一次完成通知。
- **核心坑**：**durability 几乎全是进程内**——内存态重启即丢；detached 恢复只认 host-PID（`detached`/`pid_scope`/`host_start_time`），是"尽力而为"不是持久状态。要真正跨重启，得用 cron 或 `terminal(background, notify_on_complete)`（呼应 ch26 E6）。**通知去重**靠 `was_running` 守卫 + 消费端 dedupe 集合；watch 命中限流会反过来禁用 watch、翻转 `notify_on_complete`。
- **诚实锚点**：`tools/process_registry.py:54-60`、`:89-118`、`:141-178`（process-local durability）、`:66-69`（WATCH_STRIKE_LIMIT=3，watch 限流翻转 notify）、`:207-307`（watch/notify 限流）、`:1022`（`_move_to_finished` def）、`:1037`（dedupe 注释）。
- **SVG**：⑩ **生命周期 + 通知去重图** running→（watch 限流？）→finished→notify（was_running 守卫 + 消费端 dedupe 两道闸）；⑪ **durability 对比** 进程内 background（重启=全丢）vs cron / detached（跨重启语义）三栏对照。

### 28.3 🔬 安全文件编辑管线（file_operations）
- **机制**：read / write / patch / search 工具，写与 patch 走 `_atomic_write()`——在**目标同目录**建 temp（`mktemp`）、写、`mv -f` 原子换上；patch 后**再读回**验证字节落盘；保 BOM/CRLF；只报**新增**的 lint 错误。
- **核心坑**：**原子性挂在"同目录 temp + rename"上**——跨文件系统的 rename 不是原子的，所以 temp 的位置是 load-bearing；`patch_replace()` 要求模糊匹配**唯一**，写后 re-read 校验，**并发编辑会让 re-read 校验失败**；路径安全（敏感路径 deny-list）、大文件分页、二进制/图片被拦或转向、search 是行级（不支持多行正则）。
- **诚实锚点**：`tools/file_operations.py:937-989`（_atomic_write temp+rename）、`:1408-1426`、`:1465-1586`（patch_replace + re-read 验证）、`:1340-1459`、`:1706-1789`。
- **SVG**：⑫ **安全编辑管线** 同目录 temp → 写 → 读回验证 → `mv -f` 原子换上（失败回滚）；⑬ **跨 FS rename 破原子性** 同 FS rename=原子（一步） vs 跨 FS=copy+unlink（中途崩溃留半个文件）。

### ch28 收尾
- 🎯 **设计框**：三套机制守的都是**异步世界里的正确性边界**——中断的协作式契约、后台的诚实状态、落盘的原子保证。它们是「自主、连续运行」可靠性的地基。
- 📌 **本课要点卡**（5–6 条）：中断协作式非抢占 + 子代理需显式传播；后台 durability 是进程内幻觉 + 跨重启要 cron；通知去重双闸；原子写靠同目录 temp+rename + 写后校验；并发编辑会校验失败。

---

## #7 — ch6 补充小图（独立小任务）
在既有 **ch6（System Prompt 与缓存）** 加 **1 张 SVG**：Anthropic 缓存 **4 断点放置 + thinking 签名安全**——`system + 末 3 条非 system` 打 4 个 `cache_control` 断点（同 TTL，注入前 deepcopy）；**cache_control 必须从 thinking/redacted_thinking 块移除**否则破坏签名验证；带 marker 的 system prompt 保持为 content blocks 而非纯字符串。诚实锚点：`agent/prompt_caching.py:49-79`、`agent/anthropic_adapter.py:1793-1812`、`:2271-2295`。不改 ch6 既有文字（除非需一句过渡），只加图 + fig-cap。

---

## 诚实性铁律（reviewer 必查）
- 所有 `file:line` 引用**先跑 `sed -n` 核对**，引文 verbatim（HTML 转义、Python 三引号 `&quot;&quot;&quot;`）。
- 关键数字与全书一致：429=1h、401=5m、unhealthy=10min、retry poll=200ms、max_iterations=90、DANGEROUS=61、HARDLINE=12、max_spawn_depth=1、压缩 0.50/85% 边缘。
- 不得引用源仓库不存在的文件/行号（audit 教训：`agent/memory_tool.py` 不存在、行号要对准 snippet 首行、AGENTS.md 行号要落在正确区块）。
- SVG 配色全 `var(--*)`（`grep -c 'fill="#\|stroke="#' src/part9.py` = 0，除 `#fff` 图标）；en 无残留中文 / U+3000 / 双 `——`；zh/en SVG 元素数 + viewBox 对称。

## 验证标准
- `python3 -c "import part9, shell, registry, quizzes"` 无错；ch27/28 在 `registry.CONTENT`。
- build 两次 → `check_html.py` **0 error**（ch27/28 有 analogy + key-points + ≥6 visual blocks，不应有这两类 WARN）；`check_links.py` 全解析（链接数从 104 增至 ~106+）。
- 每章：3 个 🔬 深度块（verbatim 源码）、7–10 张 SVG、zh/en 对称、analogy + 设计框 + 要点卡 + quiz 齐。
- `build_print.py` → 28 lessons each（含新 2 章）。
- README + index：章数 26→28，新增 Part 8 行。

## 任务分解概要（writing-plans 细化）
1. 脚手架：`part9.py` 骨架 + `shell.py` PAGES（Part 8）+ `registry.py` import/CONTENT + `quizzes.py` 占位 + README/index 章数。
2. ch27 开篇（lead + analogy + macro）+ 坑/机制总览图。
3. ch27 · 27.1 凭证池（深度块 + 3 SVG）。
4. ch27 · 27.2 副 LLM 路由（深度块 + 2 SVG）。
5. ch27 · 27.3 context-length→阈值（深度块 + 2 SVG）+ ch27 收尾（设计框 + 要点卡）。
6. ch28 开篇 + 28.1 中断扇出（深度块 + 2 SVG）。
7. ch28 · 28.2 后台进程（深度块 + 2 SVG）。
8. ch28 · 28.3 文件编辑（深度块 + 2 SVG）+ ch28 收尾。
9. #7 ch6 补充小图。
10. quiz（ch27 + ch28）+ 全量验证 + 打印版 + README/index + push。
（每个任务走 implementer → spec 审查 → 质量审查 双审循环。）

