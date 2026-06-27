# 每章 worked-example 实例图 Spec

## 目标
为 **ch5–ch25（21 个核心机制章）各新增 1 张「worked-example 实例图」**（共 21 主图 × zh/en 双语 = **42 个 SVG**），用**一个具体的、带真实数据/真实代码片段的例子**把该章抽象机制**落地走一遍**，补足用户反馈的「代码引用、例子举例不够多」。现有所有 SVG **保留不动**，本次纯新增。

## 背景与动机
- 用户反馈：全书讲了很多机制/设计，但**具体例子 + 代码引用**的可视化偏少；现有图多是「架构/结构/流程」型（讲机制长什么样），缺「拿一个真实例子走一遍」（讲机制具体怎么跑）。
- 现状（SVG/codeblock 计数）：part2(ch5-7)=12svg/19code、part3(ch8-11)=16/—、part4(ch12-15)=16/—、part5(ch16-19)=16/—、part6(ch20-23)=12/18、**part7(ch24-25)=8svg/6code（最少，重点补）**。
- 跳过：ch1–4（纯概念/概览，例子图意义有限）、ch26（已 42 图，最丰富）、ch27/28（刚加 12 张逐帧图）。

## worked-example 实例图 — 定义（与现有图的根本区别）
- **现有架构/流程图**讲「机制的结构」：有哪些组件、状态、分支、步骤（抽象方框 + 箭头）。
- **worked-example 图**讲「一个具体例子走一遍」：拿**一个真实的输入/场景**，沿处理路径展示**每一步的真实数据**——真实字段名、真实示例值、真实 token 数/阈值/百分比、真实代码片段（verbatim）、真实 JSON/结构。读者看完能说「哦，原来这段代码对这个具体输入是这么处理的」。
- 判定标准：图里**必须出现具体的值**（不是 `provider`，而是 `provider=anthropic`；不是「检查阈值」，而是 `0.50 → 触发`；不是「写入记忆」，而是真实的 `MEMORY[...]=...` 结构）。每个值都能在源码 `file:line` 找到。

## 通用视觉语言（21 张图共享，节奏统一）
1. **输入→处理→输出 的横向/网格流**：左边一个**具体输入卡**（真实数据），中间若干**处理区块**（每块标真实函数/代码 + 该步的真实中间值），右边**输出卡**（真实结果）。或按「一个例子的 N 个阶段」横向排。
2. **真实代码片段嵌入**：关键步骤旁放一小段 verbatim 源码（≤3 行，等宽字体感，`var(--ink)`/`var(--muted)`），标 `file:line`。
3. **具体数据高亮**：真实值用 `var(--purple)`/`var(--accent)` 高亮，让「具体例子」一眼可见。
4. **状态色编码**（复用全书）：输入/正常 `var(--blue)`；处理/命中 `var(--accent)`；高亮值/选中 `var(--purple)`；警告/阈值 `var(--amber)`；失败/拦截 `var(--red)`；底色 `var(--panel)`/`var(--panel-2)`、描边 `var(--line)`、文字 `var(--ink)`/`var(--muted)`。
5. **底部一句「读这张图」**：图最底窄带，一句话点出这个例子证明了什么（`var(--muted)`）。
6. **布局**：viewBox **680** 宽（高度按内容 360–460），`.figure svg{width:100%}` 自适应。

## 风格与诚实铁律（沿用全书）
- 双语 `LESSON_NN` 的 `zh`/`en` 各插一份，**结构对称**（相同区块数、相同 viewBox、相同元素数）；en **无中文 / 无全角空格 U+3000 / 无中文标点 / 无弯引号**。
- **配色只用 CSS 变量** `var(--*)`（含 `-soft`/`-ink` 变体，均已在 `src/shell.py:118-133` 定义）；**禁写死 `#hex`**（含 `#fff`——金/亮色块上的文字用 `-ink` 变体，深色块上的文字也优先用 `var(--*)`，不用 `#fff`）。验证 `grep -c 'fill="#\|stroke="#'` 增量为 0。
- **font-size ≥9**（次级 9–10.5，标题更大，emoji 22–26 例外）；嵌入代码片段可 9。
- 每 SVG `role="img"` + 完整 `aria-label`（zh 中文 / en 英文）；每图配 `<div class="fig-cap">`。
- HTML 转义：`<`→`&lt;`、`>`→`&gt;`、`&`→`&amp;`、`"`→`&quot;`；嵌入代码里的 `>`/`<`/`"` 都要转义。
- **所有值/字段/代码 verbatim 来自源码**——见各章「源码锚点」；implementer 先 `sed -n` 比对再落图。

## 插入位置
每张图插在该章一个合适的深度块末尾（最后一个现有 `.figure` 或 `codefile` 之后、下一 `<h3>` 之前）。**只插入、不动现有内容。** 只编辑对应的 `src/partN.py`（part2–7），不改 registry/shell/quizzes/check_html。

## 验收（整体）
- `cd src && rm -rf __pycache__ && python3 build.py >/dev/null 2>&1; python3 build.py && python3 check_html.py` → 0 error。
- `check_links.py` 全 resolve；`grep -c hex`（除既有）增量 0；各 part `<svg>` 计数按新增数增加。
- 抽查每章新图 3–5 个数字/字段 vs 源码 verbatim 一致。

---

## 逐章 worked-example 设计

> 每章一节：worked-example 标题 / 例子主角（真实数据）/ 区块要点 / verbatim 源码锚点 / 与现有图的区别。所有锚点指向 `/home/verden/course/hermes-agent/`，已由研究 subagent verbatim 核对。
> **章号=LESSON 号**；part 分组：part1=ch5、part2=ch6-8、part3=ch9-12、part4=ch13-16、part5=ch17-20、part6=ch21-23、part7=ch24-25。

### ch5（part1.py · LESSON_05）

**ch5 对话生命周期** — 图：「一条真实消息 `北京今天天气怎么样？` 跑两圈：messages 列表 + 计数器逐步演进」
- 6 区块（胶卷式，左 messages 列表逐格增长，右计数器变化）：① 初始 `messages=[system, user("北京今天天气怎么样？")]`;`api_call_count=0`;budget `max=90,used=0,remaining=90` ② 第1圈闸门 `0<90 and 90>0`✅;`_interrupt_requested=False`;`api_call_count→1`;`consume()`→`used=1,remaining=89` ③ 第1圈模型→有 tool_calls：assistant 带 `tool_calls=[{id:"call_abc123",function:{name:"get_weather",arguments:'{"city":"北京"}'}}]`;append ④ 第1圈执行 `_execute_tool_calls`→`make_tool_result_message`→`{"role":"tool","name":"get_weather","content":"北京 晴 26°C","tool_call_id":"call_abc123"}`;messages 长 4 ⑤ 第2圈 `api_call_count→2`;`consume()`→`used=2,remaining=88`;模型→**无 tool_calls**→append final;`final_response="北京今天晴，26°C"`;`🎉 Conversation completed after 2 API call(s)`;break ⑥ 侧栏:三出口本例走「无 tool_calls 收尾」,另两条(超 max_iterations/consume 返 False)未触发。
- 锚点：`agent/conversation_loop.py:589`(while 条件)、`:601-602`(api_call_count+=1)、`:608-610`(consume)、`:4051`(append assistant)、`:4079`(_execute_tool_calls)、`:4508/4511-4512`(append final/break/🎉)、`agent/tool_dispatch_helpers.py:320/337-343`(make_tool_result_message 三件套)、`agent/iteration_budget.py:32-43`(consume;parent 90/subagent 50)、`agent/agent_init.py:165`(max_iterations=90)。
- 区别：现有 2 图讲 while 流程/星型挂载(结构),本图给一条真实消息进来后 messages 列表与计数器逐格变成什么的「快照胶卷」。

### Part 2（part2.py · ch6/7/8）

**ch6 缓存** — 图：「一条真实 system prompt 三层拼装 → 打 marker → 第 2 轮 token 账」
- 6 区块：① stable 层真实首段 `DEFAULT_AGENT_IDENTITY`「You are Hermes Agent, an intelligent AI assistant created by Nous Research…」≈6800tok ② context 层 AGENTS.md 片段 ≈1200tok ③ volatile 层真实 timestamp 块 `Conversation started: Saturday, June 27, 2026`/`Session ID`/`Model`/`Provider` ≈900tok ④ `"\n\n".join` → `_cached_system_prompt`（一次构建）⑤ 打 marker 真实 dict `{"type":"ephemeral"}`——高亮**5m 默认无 `ttl` 键，仅 1h 才加 `"ttl":"1h"`** ⑥ 第 2 轮 token 账：前缀 ≈8900tok 缓存读取价(1/10) + 尾部 ≈150tok 全价 → ↓~75%。
- 锚点：`agent/prompt_builder.py:123`(DEFAULT_AGENT_IDENTITY)、`agent/system_prompt.py:454-461`(timestamp 行)、`:486`(`"\n\n".join`)、`agent/prompt_caching.py:43-46`(`marker={"type":"ephemeral"}`;`if ttl=="1h"`)、`:51`(`cache_ttl="5m"`默认)。
- 区别：现有 2 图讲断点落点/成本色块（抽象），本图给真实字节前缀 + marker dict（5m 无 ttl 易错点）+ 真实 token 账。

**ch7 消息流** — 图：「一条 `Read my AGENTS.md` 从统一 messages 翻成 Anthropic 真实请求体（字段 in→out diff）」
- 6 区块：① 入口统一 OpenAI messages + OpenAI 工具 `{"type":"function","function":{"name":"read_file","parameters":{…}}}` ② `api_mode=="anthropic_messages"` 分派 ③ adapter 翻译（红蓝对照）：system 角色**抽顶层** `system` 参数 / `function.parameters`→`input_schema` / `function.name`→`name` / **补 `max_tokens`**(必填) ④ 真实出站体 `{"model":"claude-opus-4.7","messages":[…],"max_tokens":…,"system":[…],"tools":[{"name":"read_file","input_schema":{…}}]}` ⑤ `normalize_response` 入站归一 ⑥ reasoning 三字段 `reasoning`/`reasoning_content`(缺补空格防400)/`reasoning_details`(原样透传)。
- 锚点：`agent/chat_completion_helpers.py:559`(出站分派)、`agent/anthropic_adapter.py:1595-1600`(input_schema/name)、`:2465-2474`(kwargs+system+tools)、`chat_completion_helpers.py:888`(reasoning)、`:911`(reasoning_content or " ")、`:938-940`(reasoning_details 透传)。
- 区别：现有 2 图讲角色交替/schema 即前缀（不变量），本图给同一消息出站翻译的真实字段 diff。

**ch8 工具系统** — 图：「`read_file` 一次真实调用：register→schema→tool_call→coerce→dispatch→tool 消息」
- 6 区块：① register 真实一行 `registry.register(name="read_file",toolset="file",schema=READ_FILE_SCHEMA,…,emoji="📖",max_result_size_chars=100_000)` ② 真实 schema `properties:{path,offset(default 1),limit(default 500,max 2000)}`,`required:["path"]` ③ 模型回 tool_call 真实「脏」JSON `{"path":"AGENTS.md","offset":"1","limit":"500"}`(字符串) ④ `coerce_tool_args` 按 schema 把 `"1"→1`/`"500"→500` ⑤ dispatch：成功→handler JSON；异常→`{"error":_sanitize_tool_error(...)}` ⑥ append tool 消息；`_tc_names=={"execute_code"}` 才 refund——read_file **不退**。
- 锚点：`tools/file_tools.py:1757`(register)、`:1602-1614`(READ_FILE_SCHEMA)、`model_tools.py:644`(coerce_tool_args)、`tools/registry.py:390-416`(dispatch+sanitize)、`:337-360`(check_fn 门控)、`agent/conversation_loop.py:4120-4122`(refund 严格相等)。
- 区别：现有 2 图讲 Footprint Ladder/渐进披露（宏观决策），本图给单工具一次调用的 JSON in→out（含 `"500"→500` coerce 救场）。

### Part 3（part3.py · ch9/10/11/12）

**ch9 学习引擎** — 图：「一句抱怨 `this is too verbose, just give me the answer` 走完信号识别→第10次触发 nudge→fork review→Preference order 选档→provenance」
- 6 区块：① 真实输入信号（frustration 列为 FIRST-CLASS skill signal）② nudge 触发 `_iters_since_skill` 累到 `_skill_nudge_interval=10`→置 `_should_review_skills`，**不注入文字** ③ 响应后 fork `_spawn_background_review(messages_snapshot=list(messages),review_skills=True)` daemon ④ Preference order 真实 4 档：PATCH→UPDATE→ADD 支持文件→CREATE umbrella（禁 `fix-X`/PR 号命名）⑤ provenance `mark_agent_created`（钩 ch10）⑥ 反例区：`command not found`/`browser tools don't work` 被 review prompt 明令丢弃。
- 锚点：`agent/agent_init.py:1235-1238`(`_skill_nudge_interval=10`)、`agent/turn_finalizer.py:433-456`(nudge+spawn)、`agent/background_review.py:180-186`(FIRST-CLASS signal)、`:195-231`(Preference order)、`:249-258`(Do NOT capture)、`tools/skill_manager_tool.py:1080-1084`(mark_agent_created)。
- 区别：现有讲路径/闭环（抽象），本图给真实阈值 10 + 决策分档 + 什么不该学。

**ch10 Curator** — 图：「技能 `pdf-form-filler` 用 now=2026-06-27 把 30/90 天 cutoff 代入真实日期，active→stale→复活→archived 逐日演算」
- 6 区块：① 真实 `.usage.json` `{created_by:"agent",use_count:4,last_activity_at:"2026-03-20",state:"active",pinned:false}`,`anchor=last_activity`(回退链) ② T0 巡查 `anchor>stale_cutoff(now-30d)`→留 active(零 LLM) ③ T1 越 30 天 `anchor≤stale_cutoff & ACTIVE`→`set_state(STALE)` ④ 复活：`/pdf-form-filler`→`use_count++`刷新→`anchor>stale_cutoff & STALE`→ACTIVE ⑤ T2 越 90 天→`archive_skill`→`.archive/`(可 restore,绝不 delete) ⑥ 豁免：`pinned`→continue；`name=="plan"`(PROTECTED) 不可碰。框注门控：空闲 + `>interval_hours(168h)` + `min_idle_hours(2h)`。
- 锚点：`hermes_cli/config.py:2092-2118`(interval 168h/min_idle 2h/stale 30/archive 90)、`agent/curator.py:292-328`(cutoff 计算+三分支)、`tools/skill_usage.py:462-471`(默认字段)、`:66-68`(`PROTECTED_BUILTIN_SKILLS={"plan"}`)、`:126`(.archive)、`agent/curator.py:319-328`(archive/set_state)。
- 区别：现有讲状态机箭头，本图给 30/90 天阈值 + anchor 回退链的逐日真实算术。

**ch11 记忆** — 图：「一条真实记忆 `MEMORY.md: fly deploy→Railway` 走完会话开始冻结→第5轮写入快照不变→第8轮取回贴当前 user 副本，含真实 `<memory-context>` fence」
- 6 区块：① 会话开始 `load_from_disk` 读两 `.md`(cap 2200/1375)→`_system_prompt_snapshot` ② 进 volatile 层 `format_for_system_prompt` 冻结块(docstring `NOT the live state`)→前缀缓存命中 ③ 第5轮写入改 `MEMORY.md`→磁盘变但 snapshot **不变** ④ 第8轮取回 `api_msg=msg.copy()`;`if idx==current_turn_user_idx`→content+fenced;**原 messages 永不改** ⑤ 真实 fence 逐字 `<memory-context>`+`[System note: …NOT new user input…]`+`{clean}`+`</memory-context>` ⑥ 不变量对照表。
- 锚点：`tools/memory_tool.py:124`(cap 2200/1375)、`:152-166`(load_from_disk)、`:567-578`(format_for_system_prompt+docstring)、`agent/conversation_loop.py:740-758`(api_msg.copy 注入)、`agent/memory_manager.py:297-311`(fence 真实文本)、`tools/memory_tool.py:56-57`(memories/ 路径)。
- 区别：现有讲读写分离机制，本图给真实记忆字节 + `<memory-context>` fence 串。

**ch12 跨会话搜索** — 图：「`session_search(query='deployment plan')` 从触发器建索引→真实 snippet SQL(`>>><<<`,40)→`get_anchored_view(bookend=3)`→tool 消息 append」
- 6 区块：① 写入即索引 `messages_fts_insert` 触发器 `rowid=new.id` ② 检索 SQL `snippet(messages_fts,0,'>>>','<<<','...',40)`+`MATCH`+`ORDER BY rank`(BM25) ③ CJK 兜底 trigram→LIKE（每词<3 汉字 trigram 返 0）④ `get_anchored_view(bookend=3)` 三片 bookend_start/end ⑤ 命中原文 append 为 tool 消息(零 LLM,不破缓存)⑥ 四模式参数推断 DISCOVERY/SCROLL/READ/BROWSE + service-gated。框注:WAL retry `_WRITE_MAX_RETRIES=15`/`0.150s`。
- 锚点：`hermes_state.py:616-621`(触发器)、`:3535/3532/3566`(MATCH/rank/snippet)、`:641-643`(trigram)、`:2875-2895`(get_anchored_view bookend=3)、`:684-686`(retry 15/0.150)、`tools/session_search_tool.py:8-29`(四模式+no LLM)。
- 区别：现有讲片段 vs 全量对比，本图给真实 SQL + snippet 标记 + bookend 返回形状。

### Part 4（part4.py · ch13/14/15/16）

**ch13 委派** — 图：「一次真实 `delegate_task` 调用：参数→ephemeral 上下文→返回 summary」
- 5 区块：① 调用 `delegate_task(goal="审计 gateway/platforms/ 各 adapter connect() 缺 acquire_scoped_lock",context="模式见 irc/adapter.py",toolsets=["terminal","file","search"],role="leaf")` ② 子构造两栏：**隔离** `ephemeral_system_prompt`/`platform="subagent"`/`skip_context_files=True`/`skip_memory=True`/`iteration_budget=None`；**继承** base_url/api_key/model/session_db ③ 剥离 `_strip_blocked_tools`+`DELEGATE_BLOCKED_TOOLS` 5 项+role 降级 ④ 子 context 读 ~20 adapter.py——**全留子 context**(灰框「永不进父」)⑤ 返回一句真实 summary「审计 21 adapter：matrix/sms 缺 lock;余 19 合规」;background 先返 delegation_id。
- 锚点：`tools/delegate_tool.py:1234`(ephemeral)、`:1236-1238`(skip flags)、`:1249`(iteration_budget=None)、`:45-53`(BLOCKED 5)、`:1023-1024`(role 降级)、`tools/async_delegation.py:10-18`(completion_queue)。
- 区别：现有讲隔离原理/并发上限，本图给真实调用参数+隔离构造+返回结构。

**ch14 审查验证** — 图：「同一份 diff 走两条独立路径：self-report 被驳、review 给 PASS/REQUEST_CHANGES」
- 6 区块：① 生成者交 diff(`config.py:45` `==`→`!=`)+自报「上传成功」② handle 自验：自报「成功」→实测 `HTTP 503`→判 C·幻觉 ③ spec 审(只拿 diff)→`PASS` ④ 质量审(仅 PASS 后)→`REQUEST_CHANGES:未加回归测试` ⑤ fail-closed:`security_concerns` 非空/解析失败→`passed=false` ⑥ 通过后打 `[verified]`。
- 锚点：`tools/delegate_tool.py:2923-2929`(SELF-REPORTS+handle)、`requesting-code-review/SKILL.md:19`(no agent verifies own)、`:129-130`(only diff+fail-closed)、`:233/236`(`[verified]`)、`subagent-driven-development/SKILL.md:113`(PASS/gaps)、`:145`(APPROVED/REQUEST_CHANGES)。
- 区别：现有讲原理墙/顺序门，本图给同一 diff 三个真实判定(503/PASS/REQUEST_CHANGES)。

**ch15 压缩** — 图：「一次真实压缩的内容变换：选哪 5 条、折成什么摘要、token 8400→600」（**不重复 ch27.3 阈值时间线**）
- 6 区块：① 入口 1 行「已判定触发(见 ch27.3)」② 边界 `protect_first_n=3`(衰减到 0)/`protect_last_n=20`,中间 5 条高亮 ③ 廉价剪枝 `_prune_old_tool_results`(无 LLM)④ 模板填真实摘要 `## Completed Actions:1.READ config.py:45 — found == should be != / 3.TEST pytest — 3/50 failed`;`## Critical Context:[REDACTED]` ⑤ ~8400tok→~600tok ⑥ 缓存唯一例外 `_invalidate_system_prompt()`→`_build_system_prompt()`→写回+`load_from_disk()`。
- 锚点：`agent/context_compressor.py:1565-1575`(模板)、`:1603`([REDACTED])、`:990`(_prune)、`:787-788`(protect 3/20)、`:2024`(衰减)、`agent/conversation_compression.py:515-517`(invalidate/build)。
- 区别：ch27.3 讲 token 涨到阈值，本图讲压缩把什么变成什么。

**ch16 终端后端** — 图：「`export TAG=v2 && cd src` 在 local/docker/ssh 三后端的真实包裹与 CWD 回传」
- 6 区块：① 统一中间脚本(三后端共享,verbatim)`source <snap>||true`→`builtin cd -- 'src'||exit 126`→`eval`→`export -p > <snap>`→`printf '\n__HERMES_CWD_<sid>__%s__' "$(pwd -P)"` ② local `[bash,-c,wrapped]`+`os.setsid` ③ docker `[docker,exec,<id>,bash,-c]` ④ ssh `ssh … bash -c shlex.quote` ⑤ CWD 回传分叉:local 读 `_cwd_file`;docker/ssh 解析 stdout 标记 ⑥ 下条 `echo $TAG`→`v2`。
- 锚点：`tools/environments/base.py:418-470`(_wrap_command)、`:280`(_cwd_marker)、`local.py:634-695`(setsid)、`docker.py:943-964`、`ssh.py:343-352`、`base.py:778-812`(_extract_cwd)。
- 区别：现有讲静态架构/spawn 示意，本图给同命令三后端真实包裹脚本(逐字相同)+CWD 通道差异。

### Part 5（part5.py · ch17/18/19/20）

**ch17 网关适配器** — 图：「一行真实 IRC 线 `:alice!~a@host PRIVMSG #ops :hermes: deploy staging` 翻成统一 MessageEvent 的逐字段映射」
- 6 区块：① 原生 IRC 帧(prefix/command/params) ② 解析寻址 `sender_nick="alice"`/`target="#ops"`/`is_channel=True`(`#`)→`chat_type="group"`;频道须被@→剥 `hermes:` 前缀→`text="deploy staging"`;未寻址 return 丢弃 ③ `build_source`→SessionSource ④ MessageEvent 真实实例 `text/message_type=MessageType.TEXT/source/message_id=str(int(time*1000))` ⑤ session_key 路由受 `group_sessions_per_user`/`thread_sessions_per_user` 调制 ⑥ 能力降级:IRC 无 typing→`send_typing` no-op。
- 锚点：`plugins/platforms/irc/adapter.py:429-475`(解析+寻址)、`:482-509`(build_source+MessageEvent)、`gateway/platforms/base.py:5064`(build_source)、`:4249-4250`(session_key 调制)、`:1599-1632`(MessageEvent 字段)、`irc/adapter.py:281-283`(typing no-op)。
- 区别：现有讲漏斗概念/两路对比，本图给真实 IRC 帧逐字段翻成 MessageEvent。

**ch18 网关守卫** — 图：「一条 `/approve` 在 agent 阻塞于 `threading.Event.wait()` 时如何穿过两道守卫并 `set` 那个 Event」
- 6 区块：① agent 阻塞在 `_ApprovalEntry.event=threading.Event()` 的 `.wait()`(asyncio 中断叫不醒线程 Event)② 守卫①适配器层 `session_key in _active_sessions`→`cmd="approve"` ③ 旁路判定 `should_bypass_active_session("approve")`→True 且 ∉`{stop,new,reset}`→内联(**禁** `_process_message_background`)④ 守卫②runner `/approve` 绕过 interrupt→`_handle_approve_command` ⑤ 解锁 `resolve_gateway_approval`→`entry.event.set()`→agent 续跑 ⑥ 反事实(红框):排队→互锁死锁。
- 锚点：`gateway/platforms/base.py:4262-4298`(守卫①旁路)、`hermes_cli/commands.py:379-399`(should_bypass)、`gateway/run.py:7764-7771`(runner 绕 interrupt)、`tools/approval.py:690-700`(threading.Event)、`:729-754`(resolve→event.set)、`:1352-1420`(_await timeout 300s)。
- 区别：现有讲两道守卫流程/控制vs数据，本图给 `/approve` 单命令真实解锁链。

**ch19 TUI** — 图：「一次真实 `prompt.submit` 的 JSON-RPC 帧序列：request→{status:streaming}→N×message.delta→message.complete」
- 6 区块：① 前端 request `{"jsonrpc":"2.0","id":1,"method":"prompt.submit","params":{"session_id":"s1","text":"列出本目录"}}` ② 立即响应 `{"result":{"status":"streaming"}}`(忙时 `error:{code:4009}`)③ 事件流 `_emit("message.delta",{"text":delta})` 真实信封 `{"method":"event","params":{"type":"message.delta",...}}` ④ tool.start/complete/approval.request 同管道 ⑤ `history_version` 守门(不匹配→响应可见未写历史)⑥ `message.complete` payload `{text,usage,status:"complete"|"interrupted"|"error"}`。
- 锚点：`tui_gateway/server.py:6828-6894`(prompt.submit/4009)、`:887-891`(_emit 信封)、`:952-956`(_ok/_err)、`:7222-7228`(_stream→delta)、`:7244-7264`(history_version 守门)、`:7305-7319`(complete payload)。
- 区别：现有讲两进程架构/PTY 桥，本图给一次往返的真实 JSON 帧录像。

**ch20 配置 Profiles** — 图：「`hermes -p coder chat` 启动：一个 env var 如何解析成真实路径与生效值」
- 6 区块：① `_apply_profile_override()` 裸调(import 前) argv 扫出 `profile_name="coder"`剥 `-p` ② `resolve_profile_env("coder")`→`~/.hermes/profiles/coder`→`os.environ["HERMES_HOME"]=...` ③ 业务 import 调 `get_hermes_home()`:ContextVar 空→读 env 命中→`Path(profiles/coder)` ④ `load_config()` `DEFAULT_CONFIG(_config_version:30)` 与 coder config.yaml `_deep_merge`:用户写 `agent.max_turns:40`→生效 40(覆盖默认 90);未写 `gateway_timeout` 保留 1800/`terminal.cwd` 保留 "."/`compression.threshold` 保留 0.50 ⑤ 落盘隔离 `profiles/coder/sessions|memory|logs` vs default `~/.hermes/sessions` ⑥ 侧栏:`display_hermes_home()`(给人看)vs `get_hermes_home()`(给代码)必须配对(PR #3575)。
- 锚点：`hermes_cli/main.py:336`(_apply_profile_override)、`:380`(profiles/name 拼法)、`hermes_cli/profiles.py:1866`(resolve_profile_env)、`hermes_constants.py:54/74/109`(get_hermes_home 回退)、`:388`(display_hermes_home)、`hermes_cli/config.py:5366`(_deep_merge)、`:887/900/1020/1022/1265`(默认 max_turns 90/gateway_timeout 1800/backend local/cwd "."/threshold 0.50)、`gateway/config.py:811-814`(第三 loader 直读 yaml)。
- 区别：现有讲静态三岛/yaml-vs-env 二分，本图给一条命令的动态解析链(env var→真实路径→合并生效值)。

### Part 6（part6.py · ch21/22/23）

**ch21 Cron/Kanban** — 图：「三条真实调度表达式 → 解析 → 算出真实下次触发时刻 + grace 窗口」
- 5 区块：① 基准 `now=2026-06-27T19:35` ② 行A `"0 9 * * *"`→`{kind:"cron"}`→croniter→`2026-06-28T09:00`;grace `86400//2` clamp MAX `7200s` ③ 行B `"every 5m"`→`{kind:"interval",minutes:5}`→`19:40`;grace `300//2=150s` ④ 行C `"2026-06-28T14:00"`→`{kind:"once"}`→该时刻;grace MIN `120s` ⑤ catchup:错过<grace 补跑一次,>grace 快进丢积压。
- 锚点：`cron/jobs.py:304`(parse_schedule)、`:507/546-547`(compute_next_run croniter)、`:518-527`(interval 分支)、`:475-504`(_compute_grace MIN 120/MAX 7200/period//2)、`cron/scheduler.py:2426-2432`(advance_next_run)。
- 区别：现有讲独立会话/超时流程，本图给三表达式各撞一个 clamp 边界的真实算术。

**ch22 评测/轨迹** — 图：「一条真实对话变成一条 ShareGPT 训练样本的真实 JSON 结构」
- 6 区块：① 输入 prompt `"统计当前目录有多少 .py 文件"`→`{"from":"human","value":prompt}` ② system 帧 `{"from":"system","value":"<tools>…"}` ③ gpt 帧带推理+调用 `{"from":"gpt","value":"<think>…</think>\n<tool_call>\n{\"name\":\"terminal\",\"arguments\":{\"command\":\"ls *.py|wc -l\"}}\n</tool_call>"}` ④ tool 帧 `{"from":"tool","value":"<tool_response>\n{\"name\":\"terminal\",\"content\":\"7\"}\n</tool_response>"}` ⑤ 外层 `{"conversations":[…],"tool_stats":{"terminal":{"count":1,"success":1,"failure":0}},"metadata":{"batch_num":0,…},"api_calls":2}` ⑥ 质检闸 `has_any_reasoning=True`(有`<think>`)→写;空→continue 丢弃。
- 锚点：`agent/agent_runtime_helpers.py:66`(convert_to_trajectory_format)、`:99-108`(system/human)、`:147-161`(`<tool_call>`+gpt)、`:185-199`(`<tool_response>`+tool)、`batch_runner.py:364-379`(worker 返回)、`:125-205`(_extract_tool_stats)。
- 区别：现有讲并行落盘/change-detector,本图给一条对话→ShareGPT `{from,value}` 的真实 JSON(非 OpenAI role)。

**ch23 插件/MCP** — 图：「一个真实 MCP catalog 条目，install 后真实暴露的工具 + 零足迹门控」
- 5 区块：① 真实 catalog 条目(linear/manifest.yaml verbatim)`name:linear`/`description:Find,create,and update Linear issues…`/`transport:{type:http,url:https://mcp.linear.app/mcp}`/`auth:{type:oauth}` ② `hermes mcp install linear`→写 `config.yaml` 的 `mcp_servers.linear` ③ MCP client 连接→OAuth→暴露 find/get/list+create/update ④ 对照 stdio(n8n/manifest.yaml)`transport:{type:stdio,command:${INSTALL_DIR}/.venv/bin/python}`暴露 **11 工具**,`tools.default_enabled` 剪 mutating ⑤ 零足迹:未 install→schema 不进 context;「进 catalog=经 PR 审核」。
- 锚点：`optional-mcps/linear/manifest.yaml`(整份)、`optional-mcps/n8n/manifest.yaml`(stdio+11 工具剪枝)、`hermes_cli/mcp_catalog.py:4-14`(ships disabled)、`:150/194`(_parse_manifest)、`hermes_cli/plugins.py:367`(register_tool check_fn 门控)。
- 区别：现有讲三扩展路/对比哲学,本图给 linear(远程 OAuth)+n8n(stdio 11 工具)两真实 manifest 落地。

### Part 7（part7.py · ch24/25）

**ch24 安全** — 图：「一条混淆过的 `r\m -rf /home/alice/*` 如何被第一道防线归一化还原 + HARDLINE 正则拦下」
- 5 区块：① 攻击输入 `r\m -rf /home/alice/*`(插转义反斜杠/空引号躲正则)② 归一化 `_normalize_command_for_detection`:strip_ansi→去 null→NFKC→`re.sub(r'\\([^\n])',r'\1')` 剥反斜杠→剥空引号→`_rewrite_resolved_user_home` 把 `/home/alice/`→`~/`→还原成 `rm -rf ~/` ③ HARDLINE 命中 `(r'\brm\s+(-[^\s]*\s+)*(~|\$HOME)…', "recursive delete of home directory")` ④ 硬阻断 `BLOCKED (hardline):…not even with --yolo…` ⑤ 对照(红框):问模型「危不危险」→一句「安全清理脚本」即放行;正则确定性、措辞无效。
- 锚点：`tools/approval.py:559`(_normalize 6 步)、`:574-577`(剥反斜杠/空引号 re.sub)、`:262-266`(HARDLINE_PATTERNS)、`:333-343`(detect_hardline)、`:346-359`(_hardline_block_result not even with --yolo)、`:657-668`(DANGEROUS 对照)。
- 区别：现有讲四层架构/分级对照,本图给单条混淆命令「确定性归一化战胜混淆」的真实数据流。

**ch25 设计原则** — 图：「一个真实决策：技能为何注入为 append-only user message——同一行代码同时命中三条线」
- 6 区块：① 决策点 `/my-skill`→写 system prompt 重建前缀,还是 append user message? ② 真实实现 `_build_skill_message(...)->Optional[str]` docstring「Build the user message content for a skill slash command」③ 命中线①缓存:源码注释「does NOT invalidate the skills system-prompt cache…preserves prefix caching…no cache-reset cost」④ 命中线③窄腰:技能不占核心 schema,`_HERMES_CORE_TOOLS` 仅 `skills_list/skill_view/skill_manage` 三入口 ⑤ 命中线②进化:append-only=学到的外置成文件只追加 ⑥ 反事实:若塞 system prompt→每装技能前缀逐字节变→全对话缓存作废。
- 锚点：`agent/skill_commands.py:245`(_build_skill_message)、`:523`(docstring)、`:440-444`(preserves prefix caching/no cache-reset cost)、`toolsets.py:31`(_HERMES_CORE_TOOLS 三入口)、`tools/delegate_tool.py:45-53`(DELEGATE_BLOCKED 安全横切)。
- 区别：现有讲三设计线拓扑/A-G 矩阵(抽象),本图落到一个函数+一句源码注释证明同一行同时满足三线。
- **ch24/25 可选第 2 张**（研究建议，先做第 1 张，余力再加）：ch24 第2张「子代理最小权限：父派子，子试调 memory/send_message/delegate_task 被 frozenset 逐条拦」;ch25 第2张「Footprint Ladder 一次真实裁决：webhook 落第2阶 CLI+skill 而非核心工具」。
