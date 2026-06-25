"""part4 — 第四部分 · 规模化与隔离：ch13 委派 / ch14 审查 / ch15 上下文压缩 / ch16 终端后端。

逐章 LESSON_13..16。codefile 标「节选/简化」者为可读性重排，真实性见 docs/superpowers/specs/chapters/。
"""

LESSON_13 = {
    "zh": r"""
<p class="lead">
当一个任务会产生<strong>大量中间过程</strong>（读几十个文件、跑一串命令），把它们全塞进主对话会<strong>淹没上下文</strong>。委派（<span class="mono">delegate_task</span>）的解法是：把子任务交给一个<strong>独立的子代理</strong>——它有自己的对话、自己的终端、自己的工具集，<strong>只把最终摘要带回</strong>父对话，中间的工具结果<strong>永远不进</strong>你的上下文窗口。本章是「规模化与隔离」的开篇。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 把活外包给独立小组</div>
  你是项目经理。一个调研任务要翻一百份资料，你<strong>不会</strong>把一百份资料都搬到自己桌上读（那会堆满桌面=淹没上下文）。你<strong>外包</strong>给一个独立小组：给他们一份<strong>自包含的任务书</strong>（子代理对你的对话历史一无所知），他们在<strong>自己的办公室</strong>（独立 context + 终端）干活，最后只交给你一份<strong>结论摘要</strong>。他们读过的一百份资料、试错的草稿，<strong>都不会出现在你桌上</strong>。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 上下文隔离，只带回摘要</div>
  委派的核心价值是<strong>上下文隔离</strong>。子代理拿到的是一份 <span class="mono">ephemeral_system_prompt</span>（只装 goal + context，<strong>不含</strong>父对话历史），并且 <span class="mono">skip_context_files</span> / <span class="mono">skip_memory</span>——它<strong>不读</strong>父的 AGENTS.md、不读共享 MEMORY.md。它在自己的对话里跑完，<strong>只有最终响应作为摘要返回父代理</strong>。于是父的上下文窗口<strong>始终干净</strong>：既不被中间工具结果淹没，也不被子任务的试错污染。这是对抗「上下文有限」的另一条路——第 15 章用压缩，本章用隔离。
</div>

<h2>隔离的核心：子代理拿到什么、不拿什么</h2>
<p>构造子 AIAgent 时，哪些<strong>隔离</strong>、哪些<strong>继承</strong>，是委派设计的关键：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/delegate_tool.py</span><span class="ln">1219-1250 · 简化</span></div>
  <pre>child = AIAgent(
    base_url=..., api_key=..., model=...,          <span class="cm"># 继承：provider/model 运行时</span>
    enabled_toolsets=child_toolsets,
    ephemeral_system_prompt=child_prompt,          <span class="cm"># 隔离：只装 goal+context，无父对话历史</span>
    platform=<span class="st">"subagent"</span>,
    skip_context_files=<span class="kw">True</span>,                     <span class="cm"># 隔离：不读 AGENTS.md/SOUL.md</span>
    skip_memory=<span class="kw">True</span>,                            <span class="cm"># 隔离：不读共享 MEMORY.md</span>
    clarify_callback=<span class="kw">None</span>,                       <span class="cm"># 隔离：不能向用户提问</span>
    session_db=...,                                <span class="cm"># 继承：共享会话 DB（血缘靠 parent_session_id）</span>
    iteration_budget=<span class="kw">None</span>,                       <span class="cm"># 隔离：每个子代理 fresh budget</span>
)</pre>
</div>
<p>看这份「隔离 vs 继承」清单：<strong>隔离</strong>的是会污染或淹没的东西——对话历史、上下文文件、记忆、用户交互、迭代预算（每个子代理一份<strong>全新</strong>预算）；<strong>继承</strong>的是跑起来必需的运行时——provider / model / api_key / session_db。工具描述把这条取舍说得最直白：<span class="inline">Each subagent gets its own conversation, terminal session, and toolset. Only the final summary is returned -- intermediate tool results never enter your context window</span>。</p>

<h2>两种角色：leaf 不能再委派，orchestrator 能</h2>
<p>子代理有两种 <span class="mono">role</span>。默认的 <span class="mono">leaf</span> 是<strong>专注的工人</strong>，被禁掉一批工具；<span class="mono">orchestrator</span> 则保留委派能力，能再派自己的工人：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/delegate_tool.py</span><span class="ln">44-53 / 1021-1024 · 节选</span></div>
  <pre><span class="cm"># 子代理永远不能用的工具</span>
DELEGATE_BLOCKED_TOOLS = <span class="fn">frozenset</span>([
    <span class="st">"delegate_task"</span>,   <span class="cm"># 不许递归委派（leaf）</span>
    <span class="st">"clarify"</span>,         <span class="cm"># 不许向用户提问</span>
    <span class="st">"memory"</span>,          <span class="cm"># 不许写共享 MEMORY.md</span>
    <span class="st">"send_message"</span>,    <span class="cm"># 不许跨平台副作用</span>
    <span class="st">"execute_code"</span>,    <span class="cm"># 应逐步推理，不写脚本</span>
])

<span class="cm"># role 降级：只有显式 orchestrator 且未超深度，才保留 orchestrator</span>
orchestrator_ok = _get_orchestrator_enabled() <span class="kw">and</span> child_depth &lt; max_spawn
effective_role = role <span class="kw">if</span> (role == <span class="st">"orchestrator"</span> <span class="kw">and</span> orchestrator_ok) <span class="kw">else</span> <span class="st">"leaf"</span></pre>
</div>
<p><span class="mono">_strip_blocked_tools</span> 把 <span class="mono">delegation / clarify / memory / code_execution</span> 四个 toolset <strong>整组移除</strong>——leaf 因此一并失去 delegate_task（<strong>不能再委派</strong>、避免无限套娃）、clarify、memory、execute_code；而 <span class="mono">DELEGATE_BLOCKED_TOOLS</span> 是「子代理永不可见」的<strong>权威工具清单</strong>（5 个，含 send_message），把『全员被禁』的 toolset 挡在子代理菜单之外。<span class="mono">orchestrator</span> 则被重新加回 delegation toolset、能再派工人——但<strong>默认配置下嵌套是关闭的</strong>（<span class="mono">max_spawn</span> 默认扁平，需在 config 显式抬高才解锁多级），且受<strong>嵌套深度上限</strong>（<span class="mono">child_depth &lt; max_spawn</span>）和并发上限（<span class="mono">max_concurrent_children</span>，默认 3）兜住，防止子代理军团失控。</p>

<h2>background 委派如何不破缓存</h2>
<p>顶层 model 发起的委派<strong>总是 background</strong>：立即返回一个 <span class="mono">delegation_id</span>，子代理在后台守护线程里跑。子代理跑完后，结果如何<strong>不破坏父缓存</strong>地回到对话？答案在完成队列的设计里：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/async_delegation.py</span><span class="ln">1-34 · 节选（docstring）</span></div>
  <pre>When the child finishes, a completion event is pushed onto the SHARED
completion_queue ... The CLI and gateway already poll that queue while
the agent is idle and forge a fresh user/internal turn from each event:
<span class="cm">  - completions surface as a NEW turn when the agent is idle, never</span>
<span class="cm">    spliced between a tool result and an assistant message. That keeps</span>
<span class="cm">    strict message-role alternation legal and the prompt cache intact.</span></pre>
</div>
<p>关键设计：子代理完成事件<strong>不会</strong>被硬塞进对话中段（那会破坏严格角色交替、击穿缓存）。它进一个<strong>共享完成队列</strong>，等父代理<strong>空闲时</strong>，才作为一个<strong>全新的 turn</strong> 浮现。这样既维持了严格角色交替（第 7 章）的合法性，又<strong>保住了 prompt 缓存</strong>（第 6 章）。一个细节：background 委派是<strong>进程内的</strong>——若进程退出或 <span class="mono">/new</span>，未完成的子代理会被丢弃；要可靠存活，得用 <span class="mono">cronjob</span> 或 <span class="mono">terminal(background=True, notify_on_complete=True)</span>。</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">父代理调 <span class="mono">delegate_task(goal=…)</span> 或批量 <span class="mono">tasks=[…]</span>（最多 max_concurrent_children=3 并行）</span></div>
  <div class="step"><span class="num">2</span><span class="sc">构造子 AIAgent：ephemeral_system_prompt(只装 goal+context) + skip_context_files/memory + fresh budget</span></div>
  <div class="step"><span class="num">3</span><span class="sc">子代理在<strong>独立 context + 独立终端</strong>跑完，中间工具结果全留在子 context</span></div>
  <div class="step"><span class="num">4</span><span class="sc">只把<strong>最终摘要</strong>返回父代理（父上下文窗口始终干净）</span></div>
  <div class="step"><span class="num">5</span><span class="sc">background：完成事件进共享队列 → 父<strong>空闲时</strong>作新 turn 浮现 → 严格交替+缓存不破</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「隔离而不破缓存」</div>
  <div class="collab-sub">① 组件清单（★本章核心，其余跨章节配合）</div>
  本章核心：<strong>delegate_task</strong>（单/批量入口）、<strong>子 AIAgent 隔离构造</strong>（ephemeral prompt + skip 标志）、<strong>DELEGATE_BLOCKED_TOOLS + role 降级</strong>、<strong>async_delegation 完成队列</strong>。跨章节配合：<span class="mono">delegate_task</span> 是一个特殊的<strong>工具</strong>（第 8 章，且 leaf 禁用它防递归）；子代理 <span class="mono">skip_context_files</span> / <span class="mono">skip_memory</span> 意味着不继承父的 system prompt 三层与记忆（第 6 / 11 章）；完成队列<strong>只在 idle 作新 turn</strong>，维持严格角色交替（第 7 章）+ 不破缓存（第 6 章）；上下文隔离与第 15 章压缩是对抗「上下文有限」的<strong>两条不同路</strong>（隔离 vs 压缩）。
  <div class="collab-sub">② 数据流时序</div>
  父调 delegate_task → 构造子 AIAgent（隔离对话历史/上下文文件/记忆，继承运行时）→ 子代理独立跑、中间结果留子 context → 只把摘要返回父 → （background）完成事件进共享队列 → 父空闲时作新 turn 浮现。
  <div class="collab-sub">③ 关键点</div>
  委派把「会淹没上下文的中间过程」<strong>关进子代理的独立 context</strong>，父只收摘要——既保护父上下文窗口，又（靠完成队列的 idle 重入）保护父缓存。这是「规模化」与「缓存神圣」共存的手法：<strong>把复杂度隔离到边缘</strong>。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线：<strong>上下文隔离 + 只带回摘要 + 完成队列不破缓存</strong>。它治两条 LLM 固有约束：
  <p style="margin:.5rem 0 0"><span class="badge constraint">A·中间遗失</span>——子任务的大量中间工具结果会<strong>淹没</strong>父上下文、把关键信息挤到中间被遗忘；委派把它们<strong>隔离</strong>在子 context，父只收高信号摘要；
  <span class="badge constraint">F·误差累积</span>——每个子代理<strong>fresh budget + 独立 context</strong>，避免跨任务的状态污染与误差累积。反模式：让子代理把中间过程<strong>实时回传</strong>父对话、或在对话中段<strong>硬插</strong>完成消息——前者淹没上下文，后者破坏角色交替、击穿缓存。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>上下文隔离</strong>：子代理有独立对话/终端/工具集，<span class="mono">ephemeral_system_prompt</span> 只装 goal+context、<span class="mono">skip_context_files/memory</span>，只带回摘要。</li>
    <li><strong>单 / 批量</strong>：<span class="mono">goal</span> 单任务 vs <span class="mono">tasks=[…]</span> 批量并行；并发上限 <span class="mono">max_concurrent_children</span>（默认 3）。</li>
    <li><strong>leaf vs orchestrator</strong>：leaf（默认）禁用 delegate_task/clarify/memory/send_message/execute_code；orchestrator 保留委派、能再派工人（受嵌套深度上限约束）。</li>
    <li><strong>background 不破缓存</strong>：完成事件进共享队列，父<strong>空闲时</strong>作新 turn 浮现，维持严格角色交替（第 7 章）+ 缓存（第 6 章）。</li>
    <li><strong>非持久</strong>：background 委派进程内，进程退出/<span class="mono">/new</span> 即丢；要存活用 <span class="mono">cronjob</span> 或 <span class="mono">terminal(background, notify_on_complete)</span>。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">
When a task produces <strong>tons of intermediate work</strong> (reading dozens of files, running a chain of commands), stuffing it all into the main conversation <strong>floods the context</strong>. Delegation (<span class="mono">delegate_task</span>) solves this: hand the subtask to an <strong>independent subagent</strong> — it has its own conversation, its own terminal, its own toolset, and <strong>returns only the final summary</strong> to the parent; the intermediate tool results <strong>never enter</strong> your context window. This chapter opens "scaling & isolation."
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · outsourcing to an independent team</div>
  You're the project manager. A research task requires sifting a hundred documents — you <strong>don't</strong> haul all hundred onto your own desk to read (that buries it = floods the context). You <strong>outsource</strong> to an independent team: hand them a <strong>self-contained brief</strong> (the subagent knows nothing about your conversation history), they work in <strong>their own office</strong> (independent context + terminal), and finally give you a <strong>conclusion summary</strong>. The hundred documents they read and the drafts they tried <strong>never appear on your desk</strong>.
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture · context isolation, return only the summary</div>
  Delegation's core value is <strong>context isolation</strong>. The subagent gets an <span class="mono">ephemeral_system_prompt</span> (just goal + context, <strong>not</strong> the parent's conversation history), plus <span class="mono">skip_context_files</span> / <span class="mono">skip_memory</span> — it <strong>doesn't read</strong> the parent's AGENTS.md or the shared MEMORY.md. It runs to completion in its own conversation, and <strong>only the final response is returned to the parent as a summary</strong>. So the parent's context window stays <strong>clean</strong>: neither flooded by intermediate tool results nor polluted by the subtask's trial-and-error. This is another route against "limited context" — ch.15 uses compression, this chapter uses isolation.
</div>

<h2>The heart of isolation: what the subagent gets and doesn't</h2>
<p>When constructing the child AIAgent, what is <strong>isolated</strong> vs <strong>inherited</strong> is the crux of the design:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/delegate_tool.py</span><span class="ln">1219-1250 · simplified</span></div>
  <pre>child = AIAgent(
    base_url=..., api_key=..., model=...,          <span class="cm"># inherit: provider/model runtime</span>
    enabled_toolsets=child_toolsets,
    ephemeral_system_prompt=child_prompt,          <span class="cm"># isolate: just goal+context, no parent history</span>
    platform=<span class="st">"subagent"</span>,
    skip_context_files=<span class="kw">True</span>,                     <span class="cm"># isolate: no AGENTS.md/SOUL.md</span>
    skip_memory=<span class="kw">True</span>,                            <span class="cm"># isolate: no shared MEMORY.md</span>
    clarify_callback=<span class="kw">None</span>,                       <span class="cm"># isolate: cannot ask the user</span>
    session_db=...,                                <span class="cm"># inherit: shared session DB (lineage via parent_session_id)</span>
    iteration_budget=<span class="kw">None</span>,                       <span class="cm"># isolate: fresh budget per subagent</span>
)</pre>
</div>
<p>Look at the "isolate vs inherit" list: <strong>isolated</strong> are the things that would pollute or flood — conversation history, context files, memory, user interaction, the iteration budget (each subagent gets a <strong>fresh</strong> one); <strong>inherited</strong> is the runtime needed to run — provider / model / api_key / session_db. The tool description states the trade-off most plainly: <span class="inline">Each subagent gets its own conversation, terminal session, and toolset. Only the final summary is returned -- intermediate tool results never enter your context window</span>.</p>

<h2>Two roles: leaf can't re-delegate, orchestrator can</h2>
<p>A subagent has two <span class="mono">role</span>s. The default <span class="mono">leaf</span> is a <strong>focused worker</strong> with a set of tools disabled; <span class="mono">orchestrator</span> retains delegation and can spawn its own workers:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/delegate_tool.py</span><span class="ln">44-53 / 1021-1024 · excerpt</span></div>
  <pre><span class="cm"># Tools a child must never have access to</span>
DELEGATE_BLOCKED_TOOLS = <span class="fn">frozenset</span>([
    <span class="st">"delegate_task"</span>,   <span class="cm"># no recursive delegation (leaf)</span>
    <span class="st">"clarify"</span>,         <span class="cm"># no user questions</span>
    <span class="st">"memory"</span>,          <span class="cm"># no writes to shared MEMORY.md</span>
    <span class="st">"send_message"</span>,    <span class="cm"># no cross-platform side effects</span>
    <span class="st">"execute_code"</span>,    <span class="cm"># reason step-by-step, don't write scripts</span>
])

<span class="cm"># role demotion: only an explicit orchestrator under the depth cap stays one</span>
orchestrator_ok = _get_orchestrator_enabled() <span class="kw">and</span> child_depth &lt; max_spawn
effective_role = role <span class="kw">if</span> (role == <span class="st">"orchestrator"</span> <span class="kw">and</span> orchestrator_ok) <span class="kw">else</span> <span class="st">"leaf"</span></pre>
</div>
<p><span class="mono">_strip_blocked_tools</span> removes four toolsets wholesale — <span class="mono">delegation / clarify / memory / code_execution</span> — so leaf loses delegate_task (<strong>can't re-delegate</strong>, preventing infinite nesting), clarify, memory, and execute_code; while <span class="mono">DELEGATE_BLOCKED_TOOLS</span> is the authoritative list of tools a child must <strong>never see</strong> (5 of them, including send_message), keeping the 'all-blocked' toolset out of the subagent's menu. <span class="mono">orchestrator</span> gets the delegation toolset re-added and can spawn workers — but <strong>nesting is off by default</strong> (<span class="mono">max_spawn</span> is flat by default; raise it in config to unlock multiple levels), and is bounded by a <strong>nesting depth cap</strong> (<span class="mono">child_depth &lt; max_spawn</span>) and a concurrency cap (<span class="mono">max_concurrent_children</span>, default 3), so a subagent army can't spin out of control.</p>

<h2>How background delegation avoids breaking the cache</h2>
<p>A top-level, model-issued delegation <strong>always runs in the background</strong>: it returns a <span class="mono">delegation_id</span> immediately, and the subagent runs on a background daemon thread. When the child finishes, how does the result re-enter the conversation <strong>without breaking the parent's cache</strong>? The answer is in the completion-queue design:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/async_delegation.py</span><span class="ln">1-34 · excerpt (docstring)</span></div>
  <pre>When the child finishes, a completion event is pushed onto the SHARED
completion_queue ... The CLI and gateway already poll that queue while
the agent is idle and forge a fresh user/internal turn from each event:
<span class="cm">  - completions surface as a NEW turn when the agent is idle, never</span>
<span class="cm">    spliced between a tool result and an assistant message. That keeps</span>
<span class="cm">    strict message-role alternation legal and the prompt cache intact.</span></pre>
</div>
<p>The key design: a child's completion event is <strong>not</strong> jammed into the middle of the conversation (that would break strict role alternation and shatter the cache). It goes onto a <strong>shared completion queue</strong>, and only when the parent is <strong>idle</strong> does it surface as a <strong>brand-new turn</strong>. This keeps strict role alternation (ch.7) legal and the <strong>prompt cache intact</strong> (ch.6). One detail: background delegation is <strong>process-local</strong> — if the process exits or you hit <span class="mono">/new</span>, unfinished subagents are discarded; for durable survival, use <span class="mono">cronjob</span> or <span class="mono">terminal(background=True, notify_on_complete=True)</span>.</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">parent calls <span class="mono">delegate_task(goal=…)</span> or batch <span class="mono">tasks=[…]</span> (up to max_concurrent_children=3 in parallel)</span></div>
  <div class="step"><span class="num">2</span><span class="sc">construct the child AIAgent: ephemeral_system_prompt (just goal+context) + skip_context_files/memory + fresh budget</span></div>
  <div class="step"><span class="num">3</span><span class="sc">the subagent runs in an <strong>independent context + terminal</strong>; intermediate tool results stay in the child context</span></div>
  <div class="step"><span class="num">4</span><span class="sc">only the <strong>final summary</strong> is returned to the parent (the parent's context window stays clean)</span></div>
  <div class="step"><span class="num">5</span><span class="sc">background: the completion event goes to the shared queue → surfaces as a new turn when the parent is <strong>idle</strong> → strict alternation + cache intact</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "isolate without breaking the cache"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: <strong>delegate_task</strong> (single/batch entry), the <strong>child AIAgent isolated construction</strong> (ephemeral prompt + skip flags), <strong>DELEGATE_BLOCKED_TOOLS + role demotion</strong>, the <strong>async_delegation completion queue</strong>. Cross-chapter teamwork: <span class="mono">delegate_task</span> is a special <strong>tool</strong> (ch.8, and leaf disables it to prevent recursion); the subagent's <span class="mono">skip_context_files</span> / <span class="mono">skip_memory</span> mean it doesn't inherit the parent's three-tier system prompt or memory (ch.6/11); the completion queue <strong>surfaces only as a new turn when idle</strong>, keeping strict role alternation (ch.7) + the cache (ch.6); context isolation and ch.15's compression are <strong>two different routes</strong> against "limited context" (isolate vs compress).
  <div class="collab-sub">② Data-flow timing</div>
  parent calls delegate_task → construct the child AIAgent (isolate conversation history/context files/memory, inherit runtime) → the subagent runs independently, intermediate results stay in the child context → return only the summary to the parent → (background) the completion event goes to the shared queue → surfaces as a new turn when the parent is idle.
  <div class="collab-sub">③ The key point</div>
  Delegation <strong>locks the context-flooding intermediate work inside the subagent's independent context</strong>, and the parent receives only a summary — protecting both the parent's context window and (via the queue's idle re-entry) the parent's cache. This is how "scaling" coexists with "the cache is sacred": <strong>isolate the complexity to the edges</strong>.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>context isolation + return only the summary + a completion queue that doesn't break the cache</strong>. It treats two inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">A·lost-in-the-middle</span> — a subtask's flood of intermediate tool results would <strong>bury</strong> the parent context and push key info into the forgotten middle; delegation <strong>isolates</strong> them in the child context, so the parent receives only a high-signal summary;
  <span class="badge constraint">F·error accumulation</span> — each subagent gets a <strong>fresh budget + independent context</strong>, avoiding cross-task state pollution and compounding errors. The anti-pattern: streaming the subagent's intermediate work back into the parent conversation live, or <strong>splicing</strong> the completion message into the middle of the conversation — the former floods context, the latter breaks alternation and shatters the cache.</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Context isolation</strong>: a subagent has its own conversation/terminal/toolset; <span class="mono">ephemeral_system_prompt</span> holds just goal+context, with <span class="mono">skip_context_files/memory</span>, returning only the summary.</li>
    <li><strong>Single / batch</strong>: <span class="mono">goal</span> for one task vs <span class="mono">tasks=[…]</span> for parallel batch; concurrency capped by <span class="mono">max_concurrent_children</span> (default 3).</li>
    <li><strong>leaf vs orchestrator</strong>: leaf (default) disables delegate_task/clarify/memory/send_message/execute_code; orchestrator retains delegation and can spawn workers (bounded by a nesting depth cap).</li>
    <li><strong>Background doesn't break the cache</strong>: the completion event goes to the shared queue and surfaces as a new turn when the parent is <strong>idle</strong>, keeping strict role alternation (ch.7) + the cache (ch.6).</li>
    <li><strong>Not durable</strong>: background delegation is process-local; process exit / <span class="mono">/new</span> discards it; for survival use <span class="mono">cronjob</span> or <span class="mono">terminal(background, notify_on_complete)</span>.</li>
  </ul>
</div>
""",
}

LESSON_14 = {
    "zh": r"""
<p class="lead">
第 13 章给了你一把「上下文隔离的锤子」——<span class="mono">delegate_task</span>。但「先规划后执行」「让独立的人审查」这些复杂工作流，Hermes 的委派层<strong>并没有内建</strong>。这恰恰是本章最值得讲的设计取舍：Hermes <strong>不</strong>把规划/执行/审查做进核心，而是用<strong>技能编排 delegate_task 的隔离能力</strong>，在边缘搭出「生成者-验证者分离」。核心只提供一条原语（隔离的子代理），复杂度留给技能——这是窄腰哲学（第 4 章）在多代理协作上的体现。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 同行评审 / 第三方审计</div>
  没有哪个作者该<strong>自己审自己的论文</strong>——他对自己的疏漏有盲点。学术界的办法是<strong>同行评审</strong>：找一个<strong>没参与写作</strong>的人，只给他论文（不给你的草稿笔记、不给你的辩解），让他用<strong>全新的眼睛</strong>挑错。代码也一样：实现者、审查者、修复者是<strong>三个独立的人</strong>，各自<strong>全新的上下文</strong>。Hermes 把这套「独立验证」用 <span class="mono">delegate_task</span> 的上下文隔离实现——审查者拿到的<strong>只有 diff</strong>，<strong>不</strong>共享实现者的上下文。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 生成-验证分离的核心是「独立 context」</div>
  一条原则统领本章：<strong>没有 agent 应该验证自己的工作</strong>（<span class="inline">No agent should verify its own work</span>）。为什么？模型对自己刚生成的东西有<strong>确认偏误</strong>，还容易<strong>谄媚附和</strong>。对策是<strong>用全新的 context 来验证</strong>——验证者不知道生成者「想证明什么」，只看结果。Hermes 没有把这做成委派工具的内建流程，而是<strong>三个技能</strong>各司其职：<span class="mono">plan</span>（纯规划）、<span class="mono">subagent-driven-development</span>（执行 + 两阶段审查）、<span class="mono">requesting-code-review</span>（独立审查 + 自动修复）。其中<strong>执行/审查两个</strong>技能<strong>调用 delegate_task 的隔离能力</strong>制造「全新 context」（<span class="mono">plan</span> 只产出计划、本身不委派）。
</div>

<h2>Hermes 唯一内建的验证倾向：子代理自报不可全信</h2>
<p>委派工具<strong>本身</strong>只内建了一条验证指令——提醒父代理：子代理的摘要是<strong>自报</strong>，不是已核实的事实：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/delegate_tool.py</span><span class="ln">2923-2929 · 节选（工具描述）</span></div>
  <pre>- Subagent summaries are SELF-REPORTS, not verified facts. A subagent
  that claims "uploaded successfully" or "file written" may be wrong.
  For operations with external side-effects (HTTP POST/PUT, remote
  writes, file creation at shared paths, publishing), require the subagent to return a
  verifiable handle (URL, ID, absolute path, HTTP status) and verify it
  yourself -- fetch the URL, stat the file, read back the content --
  before telling the user the operation succeeded.</pre>
</div>
<p>这条指令对抗 <span class="badge constraint">C·幻觉</span>——子代理可能<strong>真诚地</strong>报告「上传成功」，但其实没有。所以涉及外部副作用时，要求子代理返回一个<strong>可验证的把手</strong>（URL / ID / 路径 / HTTP 状态），父代理<strong>自己去验</strong>（拉取 URL、stat 文件、读回内容）。这是委派层<strong>唯一</strong>的内建验证倾向；更复杂的「独立审查」流程，则交给技能。</p>

<h2>核心原则：没有 agent 该验证自己的工作</h2>
<p>真正的「独立审查」在 <span class="mono">requesting-code-review</span> 技能里。它的核心原则只有一句话，却是整套设计的地基：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">skills/…/requesting-code-review/SKILL.md</span><span class="ln">19 / 125-198 · 节选</span></div>
  <pre><span class="cm"># Core principle</span>
No agent should verify its own work. Fresh context finds what you miss.

<span class="cm"># Step 5 — Independent reviewer subagent</span>
The reviewer gets ONLY the diff and static scan results.
No shared context with the implementer. Fail-closed.

<span class="cm"># Step 7 — Auto-fix loop</span>
Spawn a THIRD agent context -- not you (the implementer), not the reviewer.</pre>
</div>
<p>三个角色、三个<strong>独立 context</strong>：实现者写代码、审查者<strong>只看 diff</strong>（不共享实现者上下文）、修复者是<strong>第三个</strong>全新 context。审查者「fail-closed」——解析不了的回复一律判失败，绝不放水。通过的提交打上 <span class="mono">[verified]</span> 前缀，标明「一个独立审查者批准了它」。这套「独立性」正是对 <span class="badge constraint">F·误差累积</span> 与<strong>谄媚自我背书</strong>的工程对策——它不靠在 prompt 里写「别谄媚」，而靠<strong>结构上的 context 隔离</strong>。</p>

<h2>两阶段审查：spec 合规 + 代码质量</h2>
<p><span class="mono">subagent-driven-development</span> 技能把审查拆成两阶段，每阶段一个独立 reviewer：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">optional-skills/…/subagent-driven-development/SKILL.md</span><span class="ln">20 / 92-148 / 246-253 · 节选</span></div>
  <pre><span class="cm"># Core principle</span>
Fresh subagent per task + two-stage review (spec then quality).

<span class="cm"># Step 2 — Spec Compliance Reviewer</span>
OUTPUT: PASS or list of specific spec gaps to fix.

<span class="cm"># Step 3 — Code Quality Reviewer</span>
Verdict: APPROVED or REQUEST_CHANGES.

<span class="cm"># Why two-stage: catches issues before they compound across tasks.</span></pre>
</div>
<p>先查<strong>是否符合 spec</strong>（PASS / 列出差距），再查<strong>代码质量</strong>（APPROVED / REQUEST_CHANGES）。为什么值得多花这些验证调用？技能里写得很实在：<strong>「在错误跨任务累积之前抓住它们」</strong>——这正是<strong>生成-验证差</strong>的工程化：验证一个结果比从头生成它<strong>便宜</strong>，多花的审查调用，换来的是不必事后调试「滚雪球式」的复合错误。这是对 <span class="badge constraint">F·误差累积</span> 的直接对策。</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc"><strong>规划</strong>：<span class="mono">plan</span> 技能——纯规划、禁止执行，产出 markdown 计划到 .hermes/plans/</span></div>
  <div class="step"><span class="num">2</span><span class="sc"><strong>执行</strong>：<span class="mono">subagent-driven-development</span> 每个任务派 fresh implementer 子代理（delegate_task 隔离）</span></div>
  <div class="step"><span class="num">3</span><span class="sc"><strong>两阶段审查</strong>：spec 合规 reviewer（PASS/gaps）→ 代码质量 reviewer（APPROVED/REQUEST_CHANGES），各自独立 context</span></div>
  <div class="step"><span class="num">4</span><span class="sc"><strong>独立审查 + 修复</strong>：<span class="mono">requesting-code-review</span> 审查者只看 diff、修复者是第三个 context → 提交打 [verified]</span></div>
  <div class="step"><span class="num">5</span><span class="sc">全程靠 delegate_task 的<strong>上下文隔离</strong>制造「全新 context」，核心不内建任何 plan/execute/review 状态机</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「生成-验证分离」</div>
  <div class="collab-sub">① 组件清单（★本章核心，其余跨章节配合）</div>
  本章核心：委派工具的<strong>「self-reports, verify yourself」</strong>指令（唯一内建）、<span class="mono">plan</span> 技能（纯规划）、<span class="mono">subagent-driven-development</span>（执行 + 两阶段审查）、<span class="mono">requesting-code-review</span>（独立 reviewer + auto-fix）。跨章节配合：所有「独立 context」都靠 <strong>delegate_task 的上下文隔离</strong>（第 13 章）制造；这些工作流是<strong>技能</strong>（第 9 章程序性记忆），而非核心内建——正是<strong>窄腰</strong>（第 4 章）；<span class="mono">background_review.py</span> 是「每轮后 fork 评估存不存技能/记忆」的自改进（第 9 章），<strong>不是</strong>委派审查，别混用。
  <div class="collab-sub">② 数据流时序</div>
  plan 技能产出计划 → subagent-driven-development 派 implementer 子代理执行 → spec 合规 reviewer（独立 context，只看实现 vs spec）→ 代码质量 reviewer（独立 context）→ requesting-code-review 派审查者（只看 diff）→ 不通过则第三个 context 修复 → [verified] 提交。
  <div class="collab-sub">③ 关键点</div>
  Hermes 没把「规划/执行/审查」做成委派的内建状态机，而是用<strong>三个技能编排 delegate_task 的隔离原语</strong>。核心保持窄：只提供「隔离的子代理」一条原语；复杂的多代理工作流<strong>在边缘（技能）演化</strong>，可被替换、可被扩展，而核心不动。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线：<strong>生成-验证分离靠「独立 context」，工作流用技能编排委派原语（窄腰）</strong>。它治两条 LLM 固有约束：
  <p style="margin:.5rem 0 0"><span class="badge constraint">F·误差累积</span>——模型对自己的输出有确认偏误、易谄媚自我背书；用<strong>独立 context 的验证者</strong>（不靠 prompt 写「别谄媚」，靠结构隔离）+ 两阶段审查「在错误复合前抓住」；
  <span class="badge constraint">C·幻觉</span>——子代理可能真诚地误报「成功」，故内建「self-reports, verify yourself」要求可验证把手。反模式：让生成者<strong>自己审自己</strong>（盲点 + 谄媚）；或把规划/审查<strong>硬塞进核心</strong>（违背窄腰，复杂工作流应在技能层演化）。注：<strong>核心 prompt 并无显式 anti-sycophancy 指令</strong>，谄媚对策完全靠「独立验证者 + fresh context」的架构。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>委派层无内建审查</strong>：规划/执行/审查不是 delegate_task 的内建状态机，而是<strong>三个技能</strong>（plan / subagent-driven-development / requesting-code-review）编排 delegate_task 隔离能力。</li>
    <li><strong>唯一内建验证倾向</strong>：工具描述的「Subagent summaries are SELF-REPORTS... verify it yourself」，要求可验证把手（URL/ID/路径/HTTP 状态）。</li>
    <li><strong>核心原则</strong>：<span class="inline">No agent should verify its own work. Fresh context finds what you miss</span>——实现/审查/修复三个独立 context。</li>
    <li><strong>两阶段审查</strong>：spec 合规（PASS/gaps）+ 代码质量（APPROVED/REQUEST_CHANGES），「在错误复合前抓住」——生成-验证差的工程化。</li>
    <li><strong>谄媚对策靠结构</strong>：核心 prompt 无 anti-sycophancy 指令；靠「独立验证者 + fresh context」的 context 隔离对抗自我背书。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">
Ch.13 gave you a "context-isolation hammer" — <span class="mono">delegate_task</span>. But complex workflows like "plan first, execute later" and "have an independent party review" are <strong>not built into</strong> Hermes's delegation layer. That is exactly this chapter's notable trade-off: Hermes does <strong>not</strong> bake planning/execution/review into the core — it uses <strong>skills to orchestrate delegate_task's isolation</strong>, building "generator-verifier separation" at the edges. The core provides just one primitive (an isolated subagent); the complexity lives in skills — the narrow-waist philosophy (ch.4) applied to multi-agent collaboration.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · peer review / third-party audit</div>
  No author should <strong>review their own paper</strong> — they have blind spots about their own oversights. Academia's answer is <strong>peer review</strong>: find someone who <strong>wasn't involved</strong> in the writing, give them only the paper (not your draft notes, not your rationalizations), and let <strong>fresh eyes</strong> find the flaws. Code is the same: implementer, reviewer, fixer are <strong>three separate people</strong>, each with a <strong>fresh context</strong>. Hermes implements this "independent verification" via <span class="mono">delegate_task</span>'s context isolation — the reviewer gets <strong>only the diff</strong>, with <strong>no</strong> shared context with the implementer.
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture · generator-verifier separation rests on "independent context"</div>
  One principle governs this chapter: <strong>no agent should verify its own work</strong> (<span class="inline">No agent should verify its own work</span>). Why? A model has a <strong>confirmation bias</strong> about what it just generated, and is prone to <strong>sycophantic agreement</strong>. The countermeasure is <strong>verifying with a fresh context</strong> — the verifier doesn't know what the generator "wanted to prove," it only sees the result. Hermes doesn't make this a built-in flow of the delegation tool — instead <strong>three skills</strong> each play a part: <span class="mono">plan</span> (pure planning), <span class="mono">subagent-driven-development</span> (execution + two-stage review), <span class="mono">requesting-code-review</span> (independent review + auto-fix). The <strong>execution/review two</strong> of them <strong>call delegate_task's isolation</strong> to manufacture a "fresh context" (<span class="mono">plan</span> only produces a plan and doesn't delegate).
</div>

<h2>Hermes's only built-in verification leaning: subagent self-reports aren't trustworthy</h2>
<p>The delegation tool <strong>itself</strong> builds in just one verification instruction — reminding the parent that a subagent's summary is a <strong>self-report</strong>, not a verified fact:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/delegate_tool.py</span><span class="ln">2923-2929 · excerpt (tool description)</span></div>
  <pre>- Subagent summaries are SELF-REPORTS, not verified facts. A subagent
  that claims "uploaded successfully" or "file written" may be wrong.
  For operations with external side-effects (HTTP POST/PUT, remote
  writes, file creation at shared paths, publishing), require the subagent to return a
  verifiable handle (URL, ID, absolute path, HTTP status) and verify it
  yourself -- fetch the URL, stat the file, read back the content --
  before telling the user the operation succeeded.</pre>
</div>
<p>This instruction treats <span class="badge constraint">C·hallucination</span> — a subagent may <strong>sincerely</strong> report "uploaded successfully" when it didn't. So for external side-effects, require the subagent to return a <strong>verifiable handle</strong> (URL / ID / path / HTTP status), and the parent <strong>verifies it itself</strong> (fetch the URL, stat the file, read it back). This is the delegation layer's <strong>only</strong> built-in verification leaning; the more complex "independent review" flow is left to skills.</p>

<h2>The core principle: no agent should verify its own work</h2>
<p>The real "independent review" lives in the <span class="mono">requesting-code-review</span> skill. Its core principle is a single sentence, yet it's the foundation of the whole design:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">skills/…/requesting-code-review/SKILL.md</span><span class="ln">19 / 125-198 · excerpt</span></div>
  <pre><span class="cm"># Core principle</span>
No agent should verify its own work. Fresh context finds what you miss.

<span class="cm"># Step 5 — Independent reviewer subagent</span>
The reviewer gets ONLY the diff and static scan results.
No shared context with the implementer. Fail-closed.

<span class="cm"># Step 7 — Auto-fix loop</span>
Spawn a THIRD agent context -- not you (the implementer), not the reviewer.</pre>
</div>
<p>Three roles, three <strong>independent contexts</strong>: the implementer writes code, the reviewer <strong>sees only the diff</strong> (no shared context with the implementer), the fixer is a <strong>third</strong> fresh context. The reviewer is "fail-closed" — an unparseable response is judged a failure, never waved through. An approved commit gets a <span class="mono">[verified]</span> prefix, marking "an independent reviewer approved it." This "independence" is the engineering countermeasure to <span class="badge constraint">F·error accumulation</span> and <strong>sycophantic self-endorsement</strong> — it doesn't rely on writing "don't be sycophantic" in a prompt, but on <strong>structural context isolation</strong>.</p>

<h2>Two-stage review: spec compliance + code quality</h2>
<p>The <span class="mono">subagent-driven-development</span> skill splits review into two stages, each an independent reviewer:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">optional-skills/…/subagent-driven-development/SKILL.md</span><span class="ln">20 / 92-148 / 246-253 · excerpt</span></div>
  <pre><span class="cm"># Core principle</span>
Fresh subagent per task + two-stage review (spec then quality).

<span class="cm"># Step 2 — Spec Compliance Reviewer</span>
OUTPUT: PASS or list of specific spec gaps to fix.

<span class="cm"># Step 3 — Code Quality Reviewer</span>
Verdict: APPROVED or REQUEST_CHANGES.

<span class="cm"># Why two-stage: catches issues before they compound across tasks.</span></pre>
</div>
<p>First check <strong>spec compliance</strong> (PASS / list gaps), then <strong>code quality</strong> (APPROVED / REQUEST_CHANGES). Why spend these extra verification calls? The skill says it plainly: <strong>"catch issues before they compound across tasks."</strong> This is exactly the engineering of the <strong>generation-verification gap</strong>: verifying a result is <strong>cheaper</strong> than generating it from scratch, and the extra review calls buy you not having to debug "snowballing" compound errors later. A direct countermeasure to <span class="badge constraint">F·error accumulation</span>.</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc"><strong>Plan</strong>: the <span class="mono">plan</span> skill — pure planning, no execution, writes a markdown plan to .hermes/plans/</span></div>
  <div class="step"><span class="num">2</span><span class="sc"><strong>Execute</strong>: <span class="mono">subagent-driven-development</span> spawns a fresh implementer subagent per task (delegate_task isolation)</span></div>
  <div class="step"><span class="num">3</span><span class="sc"><strong>Two-stage review</strong>: spec-compliance reviewer (PASS/gaps) → code-quality reviewer (APPROVED/REQUEST_CHANGES), each an independent context</span></div>
  <div class="step"><span class="num">4</span><span class="sc"><strong>Independent review + fix</strong>: <span class="mono">requesting-code-review</span>'s reviewer sees only the diff, the fixer is a third context → commit gets [verified]</span></div>
  <div class="step"><span class="num">5</span><span class="sc">throughout, delegate_task's <strong>context isolation</strong> manufactures "fresh context"; the core builds in no plan/execute/review state machine</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "generator-verifier separation"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: the delegation tool's <strong>"self-reports, verify yourself"</strong> instruction (the only built-in), the <span class="mono">plan</span> skill (pure planning), <span class="mono">subagent-driven-development</span> (execution + two-stage review), <span class="mono">requesting-code-review</span> (independent reviewer + auto-fix). Cross-chapter teamwork: every "fresh context" is manufactured by <strong>delegate_task's context isolation</strong> (ch.13); these workflows are <strong>skills</strong> (ch.9 procedural memory), not core built-ins — exactly the <strong>narrow waist</strong> (ch.4); <span class="mono">background_review.py</span> is the "fork after each turn to evaluate saving a skill/memory" self-improvement (ch.9), <strong>not</strong> delegation review — don't conflate them.
  <div class="collab-sub">② Data-flow timing</div>
  the plan skill produces a plan → subagent-driven-development spawns an implementer subagent to execute → spec-compliance reviewer (independent context, implementation vs spec) → code-quality reviewer (independent context) → requesting-code-review spawns a reviewer (diff only) → on failure a third context fixes → [verified] commit.
  <div class="collab-sub">③ The key point</div>
  Hermes doesn't make planning/execution/review a built-in delegation state machine — it uses <strong>three skills to orchestrate delegate_task's isolation primitive</strong>. The core stays narrow: it offers just one primitive ("an isolated subagent"); the complex multi-agent workflow <strong>evolves at the edges (skills)</strong>, replaceable and extensible, while the core stays put.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>generator-verifier separation rests on "independent context," and the workflow orchestrates the delegation primitive via skills (narrow waist)</strong>. It treats two inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">F·error accumulation</span> — a model has a confirmation bias toward its own output and is prone to sycophantic self-endorsement; use a <strong>verifier in an independent context</strong> (not "don't be sycophantic" in a prompt, but structural isolation) + two-stage review to "catch issues before they compound";
  <span class="badge constraint">C·hallucination</span> — a subagent may sincerely misreport "success," so the built-in "self-reports, verify yourself" requires a verifiable handle. The anti-pattern: letting the generator <strong>review itself</strong> (blind spots + sycophancy); or <strong>baking planning/review into the core</strong> (against the narrow waist — complex workflows should evolve in the skill layer). Note: <strong>the core prompt has no explicit anti-sycophancy instruction</strong>; the sycophancy countermeasure is entirely the "independent verifier + fresh context" architecture.</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>No built-in review in the delegation layer</strong>: planning/execution/review aren't a delegate_task state machine, but <strong>three skills</strong> (plan / subagent-driven-development / requesting-code-review) orchestrating delegate_task's isolation.</li>
    <li><strong>The only built-in verification leaning</strong>: the tool description's "Subagent summaries are SELF-REPORTS... verify it yourself," requiring a verifiable handle (URL/ID/path/HTTP status).</li>
    <li><strong>Core principle</strong>: <span class="inline">No agent should verify its own work. Fresh context finds what you miss</span> — implementer/reviewer/fixer are three independent contexts.</li>
    <li><strong>Two-stage review</strong>: spec compliance (PASS/gaps) + code quality (APPROVED/REQUEST_CHANGES), "catch before they compound" — the generation-verification gap engineered.</li>
    <li><strong>Sycophancy countered structurally</strong>: the core prompt has no anti-sycophancy instruction; it relies on the "independent verifier + fresh context" isolation to resist self-endorsement.</li>
  </ul>
</div>
""",
}

LESSON_15 = {
    "zh": r"""
<p class="lead">
第 6 章立下铁律：<strong>prompt 缓存神圣不可侵犯，唯一的例外是上下文压缩</strong>。本章就讲这个例外。当对话长到逼近模型的上下文窗口，Hermes 会把早期历史<strong>摘要压缩</strong>成更短的一段。这一步<strong>必然</strong>改写了被缓存的前缀——缓存<strong>注定作废</strong>。所以它被设计成<strong>万不得已才触发</strong>：用一次「缓存重置」的代价，换回继续对话的空间。这是「缓存神圣」唯一让步的地方，也是对抗「上下文有限」和「上下文腐烂」的核心武器。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 把会议纪要压成要点</div>
  一场开了三小时的会，逐字记录有几万字——再开下去，新人根本读不完前情。聪明的做法是：<strong>保留最近的讨论</strong>（尾部）和<strong>最初的议题</strong>（头部），把<strong>中间冗长的过程</strong>压成一页<strong>结构化要点</strong>（做了什么、定了什么、还剩什么）。压缩后，会议继续，但纪要<strong>换了一版</strong>——这正是「缓存作废」的代价。Hermes 只在<strong>纪要快撑爆</strong>时才做这件事，平时绝不动它。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 用一次缓存重置，换回继续的空间</div>
  压缩的逻辑链是：①<strong>逼近才触发</strong>——默认到上下文窗口的 <strong>50%</strong> 才考虑，且有防抖动护栏；②<strong>保头保尾、摘要中段</strong>——保护最初的任务框架（头）和最近的上下文（尾），用<strong>辅助模型</strong>把中间轮摘要成结构化要点；③<strong>重建前缀</strong>——压缩改写了历史，必须 <span class="mono">_invalidate_system_prompt()</span> 清缓存、<span class="mono">_build_system_prompt()</span> 重建。这第三步就是「缓存唯一例外」的实证。它对抗 <span class="badge constraint">A·中间遗失</span>（上下文有限）和 <span class="badge constraint">F·误差累积</span>（上下文腐烂）。
</div>

<h2>何时触发：逼近才压，且防抖动</h2>
<p>压缩不是随时做，而是<strong>逼近窗口</strong>才触发，还要防止「压了一点点就又压」的抖动：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/context_compressor.py</span><span class="ln">964-984 · 简化</span></div>
  <pre><span class="kw">def</span> <span class="fn">should_compress</span>(self, prompt_tokens=<span class="kw">None</span>) -&gt; bool:
    <span class="cm"># 默认到上下文窗口 50% 的 token 阈值才触发(threshold_percent=0.50)</span>
    tokens = prompt_tokens <span class="kw">if</span> prompt_tokens <span class="kw">is</span> <span class="kw">not</span> <span class="kw">None</span> <span class="kw">else</span> self.last_prompt_tokens
    <span class="kw">if</span> tokens &lt; self.threshold_tokens:
        <span class="kw">return</span> <span class="kw">False</span>
    <span class="cm"># 防抖动:若最近两次压缩各只省下 &lt;10%,跳过,避免每次只删 1-2 条的死循环</span>
    <span class="kw">if</span> self._ineffective_compression_count &gt;= 2:
        <span class="kw">return</span> <span class="kw">False</span>
    <span class="kw">return</span> <span class="kw">True</span></pre>
</div>
<p>两道闸：其一，<strong>token 没到阈值就不压</strong>（默认窗口的 50%，小模型逼近时升到 85%）——平时尽量「省着用」整个上下文；其二，<strong>防抖动</strong>：如果最近两次压缩<strong>各只省下不到 10%</strong>，说明已经压无可压，再压只会陷入「每次删 1-2 条」的死循环，于是<strong>跳过</strong>。这两道闸合起来就是「万不得已才触发」——因为每触发一次，缓存就作废一次，代价昂贵。</p>

<h2>缓存的唯一例外：压缩后重建 system prompt</h2>
<p>这是全书的关键三行——<strong>压缩为什么是缓存铁律的唯一例外</strong>，就实证在这里：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/conversation_compression.py</span><span class="ln">515-517 · 节选</span></div>
  <pre>agent._invalidate_system_prompt()                    <span class="cm"># 清空 _cached_system_prompt = None</span>
new_system_prompt = agent._build_system_prompt(system_message)  <span class="cm"># 重建</span>
agent._cached_system_prompt = new_system_prompt      <span class="cm"># 写回新前缀</span></pre>
</div>
<p>平时（第 6 章），<span class="mono">_cached_system_prompt</span> 一旦构建就<strong>逐字节不变</strong>，整会话复用、命中前缀缓存。但压缩<strong>重写了历史前缀</strong>——继续用旧缓存就错了。所以这里 <span class="mono">_invalidate_system_prompt()</span> 把缓存清空（置 <span class="kw">None</span>），随即 <span class="mono">_build_system_prompt()</span> 重建并写回。而 <span class="mono">invalidate_system_prompt</span> 还<strong>顺便 reload 记忆快照</strong>（<span class="mono">load_from_disk()</span>）——这正是第 11 章说的「记忆快照只在压缩边界刷新」：压缩本来就要重建，顺势把这会话写入的新记忆也纳入，<strong>不增加额外的缓存代价</strong>。</p>

<h2>对抗上下文腐烂：保留什么、丢弃什么</h2>
<p>压缩不是简单截断，而是<strong>结构化保留关键、丢弃冗余</strong>。摘要用一个固定模板，逼辅助模型抽出「该记住的」：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/context_compressor.py</span><span class="ln">1559-1606 · 节选（摘要模板）</span></div>
  <pre>## Goal
[用户整体想达成什么]
## Constraints &amp; Preferences
[用户偏好、编码风格、约束、重要决定]
## Completed Actions
[已采取的具体动作 — 工具、目标、结果]
## Key Decisions
[重要技术决定 + 为什么这么定]
## Resolved Questions
[已回答的问题 + 答案,避免重复问]
## Critical Context
[具体值、报错、配置 — 绝不含 API key]</pre>
</div>
<p>这套结构直接对抗 <span class="badge constraint">F·误差累积</span> 里的<strong>上下文腐烂</strong>：① <strong>头部保护随轮次衰减</strong>——第一次压缩保留最初几轮任务框架，但之后衰减到 0，免得早期消息「化石化」、把头部撑得无限大；② <strong>时序锚定</strong>——把「待办」改写成<strong>已完成的过去式</strong>，防止压缩恢复后<strong>重复执行</strong>旧任务；外加 <strong>STALE 标注</strong>——待办 / 剩余工作段被另标为「STALE 仅供参考，除非用户明确要求否则别执行」；③ 压缩前先<strong>廉价剪枝</strong>旧 tool 结果（无 LLM 调用，把长输出换成一行摘要）。还有一个细节：摘要本身是<strong>会话中段的消息、不在缓存前缀里</strong>，所以摘要里的日期等不会影响缓存稳定。</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc"><strong>逼近触发</strong>:token 达上下文窗口 ~50%(should_compress) + 防抖动(连续2次省&lt;10%则跳过)</span></div>
  <div class="step"><span class="num">2</span><span class="sc"><strong>剪枝</strong>:廉价剪掉旧 tool 结果(无 LLM),去重</span></div>
  <div class="step"><span class="num">3</span><span class="sc"><strong>保头保尾、摘要中段</strong>:辅助模型按结构化模板摘要中间轮(Goal/Decisions/...);时序锚定防重复执行</span></div>
  <div class="step"><span class="num">4</span><span class="sc"><strong>★重建前缀</strong>:_invalidate_system_prompt()→_build_system_prompt()→_cached_system_prompt=new(缓存唯一例外)</span></div>
  <div class="step"><span class="num">5</span><span class="sc">顺带 reload 记忆快照(load_from_disk);压缩锁防并发(防 session 血缘分裂)</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「缓存唯一例外」</div>
  <div class="collab-sub">① 组件清单（★本章核心，其余跨章节配合）</div>
  本章核心:<strong>should_compress</strong>(触发+防抖动)、<strong>剪枝+保头保尾+摘要</strong>(辅助模型)、<strong>_invalidate_system_prompt + 重建</strong>(缓存唯一例外)、<strong>时序锚定/头部衰减</strong>(对抗 rot)、<strong>压缩锁</strong>(防并发)。跨章节配合:平时 _cached_system_prompt 逐字节稳定(第 6 章),压缩是它<strong>唯一</strong>被重建的时机;压缩边界顺带 reload <strong>记忆快照</strong>(第 11 章 load_from_disk);摘要走<strong>辅助模型</strong>(第 10 章辅助模型隔离,auxiliary.compression);压缩(腾空间)与委派(隔离)是对抗「上下文有限」的<strong>两条不同路</strong>(第 13 章)。
  <div class="collab-sub">② 数据流时序</div>
  逼近窗口 → should_compress(防抖动)→ 剪枝旧 tool → 保头(衰减)保尾(token预算)、辅助模型摘要中段(结构化模板+时序锚定)→ _invalidate_system_prompt()清缓存 → _build_system_prompt()重建(顺带reload记忆)→ _cached_system_prompt=new → 继续对话。
  <div class="collab-sub">③ 关键点</div>
  压缩是「缓存神圣」唯一让步:它<strong>必然</strong>作废前缀缓存,所以设计成「逼近+防抖动才触发」(万不得已);换来的是把「会腐烂、会遗失」的长历史<strong>结构化压缩</strong>成高信号要点,让对话能继续。一次缓存重置的代价,换回继续的空间。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线:<strong>压缩是缓存铁律的唯一例外——用一次缓存重置换回继续对话的空间;万不得已才触发</strong>。它治两条 LLM 固有约束:
  <p style="margin:.5rem 0 0"><span class="badge constraint">A·中间遗失</span>——上下文窗口有限,长对话会把关键信息挤到中间被遗忘;压缩把中段<strong>摘要成高信号要点</strong>,腾出空间、保住关键;
  <span class="badge constraint">F·误差累积</span>——长对话会「上下文腐烂」(旧待办被反复执行、早期消息化石化);时序锚定(待办改过去式)+头部衰减+STALE 标注直接对治。反模式:<strong>频繁压缩</strong>(每次都作废缓存,成本爆炸)——所以要逼近+防抖动;或压缩时把摘要<strong>塞进 system prompt 前缀</strong>当永久内容(摘要应是中段消息,不进缓存前缀)。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>缓存唯一例外</strong>:压缩重写历史前缀 → <span class="mono">_invalidate_system_prompt()</span> 清缓存 + <span class="mono">_build_system_prompt()</span> 重建(conversation_compression.py:515-517);这是第 6 章铁律的唯一让步。</li>
    <li><strong>逼近才触发 + 防抖动</strong>:默认窗口 50% 阈值,连续两次省 &lt;10% 则跳过,避免「每次删 1-2 条」死循环。</li>
    <li><strong>保头保尾、摘要中段</strong>:辅助模型按结构化模板(Goal/Decisions/Resolved/...)摘要中间轮,保护最初任务框架与最近上下文。</li>
    <li><strong>对抗上下文腐烂</strong>:时序锚定(待办改过去式防重复执行)、头部保护衰减(防化石化)、剪枝旧 tool 结果。</li>
    <li><strong>顺带刷新记忆</strong>:invalidate 时 <span class="mono">load_from_disk()</span> 重载记忆快照(第 11 章);摘要是中段消息,不在缓存前缀。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">
Ch.6 laid down the iron rule: <strong>the prompt cache is sacred, and the only exception is context compression</strong>. This chapter is about that exception. When a conversation grows close to the model's context window, Hermes <strong>summarizes and compresses</strong> the early history into a shorter span. That step <strong>necessarily</strong> rewrites the cached prefix — the cache is <strong>bound to be voided</strong>. So it's designed to fire only as a <strong>last resort</strong>: spend one "cache reset" to buy back room to keep talking. This is the one place "the cache is sacred" yields, and the core weapon against "limited context" and "context rot."
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · compressing meeting minutes into key points</div>
  A three-hour meeting has tens of thousands of words of verbatim notes — keep going and a newcomer can't possibly read the backstory. The smart move: <strong>keep the recent discussion</strong> (the tail) and <strong>the original agenda</strong> (the head), and compress the <strong>long middle</strong> into a page of <strong>structured key points</strong> (what was done, what was decided, what's left). After compression the meeting continues, but the minutes are <strong>a new version</strong> — exactly the cost of "cache invalidation." Hermes only does this when the minutes are <strong>about to overflow</strong>, never touching them otherwise.
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture · spend one cache reset to buy back room</div>
  Compression's logic chain: ① <strong>fire only near the limit</strong> — by default it considers compaction at <strong>50%</strong> of the context window, with anti-thrashing guards; ② <strong>protect head and tail, summarize the middle</strong> — keep the original task framing (head) and recent context (tail), and use an <strong>auxiliary model</strong> to summarize the middle turns into structured key points; ③ <strong>rebuild the prefix</strong> — compression rewrote history, so it must <span class="mono">_invalidate_system_prompt()</span> to clear the cache and <span class="mono">_build_system_prompt()</span> to rebuild. That third step is the proof of "the cache's only exception." It treats <span class="badge constraint">A·lost-in-the-middle</span> (limited context) and <span class="badge constraint">F·error accumulation</span> (context rot).
</div>

<h2>When it fires: only near the limit, and anti-thrashing</h2>
<p>Compression isn't done anytime — it fires only <strong>near the window</strong>, and guards against "compress a tiny bit then compress again" thrashing:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/context_compressor.py</span><span class="ln">964-984 · simplified</span></div>
  <pre><span class="kw">def</span> <span class="fn">should_compress</span>(self, prompt_tokens=<span class="kw">None</span>) -&gt; bool:
    <span class="cm"># fires only at the token threshold = 50% of the context window (threshold_percent=0.50)</span>
    tokens = prompt_tokens <span class="kw">if</span> prompt_tokens <span class="kw">is</span> <span class="kw">not</span> <span class="kw">None</span> <span class="kw">else</span> self.last_prompt_tokens
    <span class="kw">if</span> tokens &lt; self.threshold_tokens:
        <span class="kw">return</span> <span class="kw">False</span>
    <span class="cm"># anti-thrashing: if the last two compressions each saved &lt;10%, skip — avoid a loop that removes 1-2 msgs each time</span>
    <span class="kw">if</span> self._ineffective_compression_count &gt;= 2:
        <span class="kw">return</span> <span class="kw">False</span>
    <span class="kw">return</span> <span class="kw">True</span></pre>
</div>
<p>Two gates: first, <strong>don't compress until tokens hit the threshold</strong> (default 50% of the window, rising to 85% for small models near the edge) — normally "use up" the whole context first; second, <strong>anti-thrashing</strong>: if the last two compressions each <strong>saved less than 10%</strong>, there's nothing left to squeeze, and compressing again would spiral into a "remove 1-2 messages each time" loop, so it <strong>skips</strong>. Together these are "last resort only" — because each fire voids the cache once, an expensive cost.</p>

<h2>The cache's only exception: rebuild the system prompt after compression</h2>
<p>Here are the book's key three lines — <strong>why compression is the iron rule's only exception</strong> is proven right here:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/conversation_compression.py</span><span class="ln">515-517 · excerpt</span></div>
  <pre>agent._invalidate_system_prompt()                    <span class="cm"># clears _cached_system_prompt = None</span>
new_system_prompt = agent._build_system_prompt(system_message)  <span class="cm"># rebuild</span>
agent._cached_system_prompt = new_system_prompt      <span class="cm"># write back the new prefix</span></pre>
</div>
<p>Normally (ch.6), once <span class="mono">_cached_system_prompt</span> is built it stays <strong>byte-stable</strong>, reused all session to hit the prefix cache. But compression <strong>rewrote the history prefix</strong> — keeping the old cache would be wrong. So here <span class="mono">_invalidate_system_prompt()</span> clears the cache (sets it <span class="kw">None</span>) and <span class="mono">_build_system_prompt()</span> rebuilds and writes back. And <span class="mono">invalidate_system_prompt</span> also <strong>reloads the memory snapshot</strong> (<span class="mono">load_from_disk()</span>) — exactly ch.11's "the memory snapshot refreshes only at a compression boundary": compression has to rebuild anyway, so it folds in the new memory written this session at <strong>no extra cache cost</strong>.</p>

<h2>Fighting context rot: what to keep, what to drop</h2>
<p>Compression isn't a simple truncation — it <strong>structurally keeps the key, drops the redundant</strong>. The summary uses a fixed template, forcing the auxiliary model to extract "what should be remembered":</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/context_compressor.py</span><span class="ln">1559-1606 · excerpt (summary template)</span></div>
  <pre>## Goal
[What the user is trying to accomplish overall]
## Constraints &amp; Preferences
[User preferences, coding style, constraints, important decisions]
## Completed Actions
[Concrete actions taken — tool, target, outcome]
## Key Decisions
[Important technical decisions and WHY]
## Resolved Questions
[Questions already answered + the answer, so it's not repeated]
## Critical Context
[Specific values, errors, config — NEVER include API keys]</pre>
</div>
<p>This structure directly treats the <strong>context rot</strong> within <span class="badge constraint">F·error accumulation</span>: ① <strong>head protection decays over cycles</strong> — the first compaction keeps the early task framing, but later it decays to 0, so early messages don't "fossilize" and grow the head unboundedly; ② <strong>temporal anchoring</strong> — rewrite "to-dos" as <strong>completed past tense</strong> to prevent <strong>re-execution</strong> of old tasks after recovery; plus a separate <strong>STALE marking</strong> — pending/remaining-work sections are labeled "STALE, for reference only; don't act unless the user explicitly asks"; ③ before compressing, a <strong>cheap prune</strong> of old tool results (no LLM, replacing long output with a one-line summary). One detail: the summary itself is a <strong>mid-conversation message, not in the cached prefix</strong>, so a date in it never affects cache stability.</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc"><strong>Fire near the limit</strong>: tokens hit ~50% of the window (should_compress) + anti-thrashing (skip if 2 in a row saved &lt;10%)</span></div>
  <div class="step"><span class="num">2</span><span class="sc"><strong>Prune</strong>: cheaply trim old tool results (no LLM), dedupe</span></div>
  <div class="step"><span class="num">3</span><span class="sc"><strong>Protect head/tail, summarize the middle</strong>: auxiliary model summarizes middle turns by template (Goal/Decisions/...); temporal anchoring prevents re-execution</span></div>
  <div class="step"><span class="num">4</span><span class="sc"><strong>★Rebuild the prefix</strong>: _invalidate_system_prompt()→_build_system_prompt()→_cached_system_prompt=new (the cache's only exception)</span></div>
  <div class="step"><span class="num">5</span><span class="sc">also reloads the memory snapshot (load_from_disk); a compression lock prevents concurrent compaction (avoiding session-lineage splits)</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "the cache's only exception"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: <strong>should_compress</strong> (trigger + anti-thrashing), <strong>prune + protect head/tail + summarize</strong> (auxiliary model), <strong>_invalidate_system_prompt + rebuild</strong> (the cache's only exception), <strong>temporal anchoring / head decay</strong> (fighting rot), the <strong>compression lock</strong> (anti-concurrency). Cross-chapter teamwork: normally _cached_system_prompt is byte-stable (ch.6), and compression is its <strong>only</strong> rebuild moment; the compression boundary also reloads the <strong>memory snapshot</strong> (ch.11 load_from_disk); the summary runs on the <strong>auxiliary model</strong> (ch.10 auxiliary-model isolation, auxiliary.compression); compression (make room) and delegation (isolate) are <strong>two different routes</strong> against "limited context" (ch.13).
  <div class="collab-sub">② Data-flow timing</div>
  near the window → should_compress (anti-thrashing) → prune old tools → protect head (decaying) and tail (token budget), auxiliary model summarizes the middle (structured template + temporal anchoring) → _invalidate_system_prompt() clears cache → _build_system_prompt() rebuilds (also reloads memory) → _cached_system_prompt=new → continue.
  <div class="collab-sub">③ The key point</div>
  Compression is "the cache is sacred"'s one concession: it <strong>necessarily</strong> voids the prefix cache, so it's designed to fire "only near the limit, with anti-thrashing" (last resort); in return it <strong>structurally compresses</strong> the rotting, forgettable long history into high-signal points so the conversation can continue. One cache reset bought for room to keep going.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>compression is the iron rule's only exception — spend one cache reset to buy back room; fire only as a last resort</strong>. It treats two inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">A·lost-in-the-middle</span> — the context window is finite, and a long conversation pushes key info into the forgotten middle; compression summarizes the middle into <strong>high-signal points</strong>, freeing space while keeping the essentials;
  <span class="badge constraint">F·error accumulation</span> — a long conversation "rots" (old to-dos re-executed, early messages fossilized); temporal anchoring (to-dos as past tense) + head decay + STALE marking directly counter it. The anti-pattern: <strong>frequent compression</strong> (each voids the cache, costs explode) — hence near-limit + anti-thrashing; or jamming the summary into the <strong>system-prompt prefix</strong> as permanent content (the summary should be a mid-conversation message, not in the cached prefix).</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>The cache's only exception</strong>: compression rewrites the history prefix → <span class="mono">_invalidate_system_prompt()</span> clears the cache + <span class="mono">_build_system_prompt()</span> rebuilds (conversation_compression.py:515-517); ch.6's iron rule yields here alone.</li>
    <li><strong>Fire near the limit + anti-thrashing</strong>: default 50% window threshold; skip if two in a row saved &lt;10%, avoiding a "remove 1-2 each time" loop.</li>
    <li><strong>Protect head/tail, summarize the middle</strong>: the auxiliary model summarizes middle turns by a structured template (Goal/Decisions/Resolved/...), keeping the original task framing and recent context.</li>
    <li><strong>Fight context rot</strong>: temporal anchoring (to-dos to past tense to prevent re-execution), head-protection decay (no fossilizing), pruning old tool results.</li>
    <li><strong>Also refresh memory</strong>: invalidate triggers <span class="mono">load_from_disk()</span> to reload the memory snapshot (ch.11); the summary is a mid-conversation message, not in the cached prefix.</li>
  </ul>
</div>
""",
}


LESSON_16 = {
    "zh": r"""
<p class="lead">
Agent 要「动手」就得跑命令——但跑在<strong>哪里</strong>？你本地的机器、一个 Docker 容器、一台远程服务器、还是 Modal 这样的 <strong>serverless</strong> 平台？Hermes 的答案是：<strong>同一个 terminal 工具，背后是可插拔的多种后端</strong>。模型永远只调一个 <span class="mono">terminal</span>，至于命令落到 local / docker / ssh / modal / singularity / daytona 哪个环境，由一层<strong>统一抽象</strong>透明分派。这让同一个 agent <strong>跑遍各种环境</strong>，也让 serverless 后端能<strong>按需启动、用完释放</strong>省钱。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 万能遥控器</div>
  一个<strong>万能遥控器</strong>，按钮永远是「开 / 关 / 音量」（统一接口），但背后能控电视、空调、音响（多种后端）。你<strong>不需要</strong>为每台设备学一套按钮——遥控器内部把「音量+」翻译成各设备的红外码。Hermes 的 terminal 就是这个万能遥控器：模型永远按「跑这条命令」，<span class="mono">BaseEnvironment</span> 这层抽象把它翻译成 local 的 subprocess、docker 的 exec、ssh 的远程命令、modal 的 serverless 调用。换设备只换后端，<strong>遥控器的按钮一个不变</strong>。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 统一抽象,后端差异在边缘</div>
  六种执行后端——<strong>local / docker / ssh / singularity / modal / daytona</strong>——共享<strong>同一个接口</strong> <span class="mono">BaseEnvironment</span>(ABC)。每个后端只需实现 <span class="mono">_run_bash()</span> 和 <span class="mono">cleanup()</span> 两个抽象方法；统一的 <span class="mono">execute()</span>(会话快照、CWD 跟踪、中断、超时)由<strong>基类提供</strong>，所有后端复用。一个工厂 <span class="mono">_create_environment</span> 按 <span class="mono">TERMINAL_ENV</span> 配置挑后端。这正是窄腰(第 4 章)在执行层的体现:<strong>核心只认一个 terminal 工具</strong>,六种环境的差异全被关进边缘的 <span class="mono">BaseEnvironment</span> 子类——加一个新后端,核心一行不动。
</div>

<h2>统一接口:BaseEnvironment ABC</h2>
<p>所有后端的「共同契约」是一个抽象基类——子类只填两个洞，其余流程基类全包了:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/environments/base.py</span><span class="ln">288-345 · 节选</span></div>
  <pre><span class="kw">class</span> <span class="fn">BaseEnvironment</span>(ABC):
    <span class="cm">&quot;&quot;&quot;Common interface and unified execution flow for all Hermes backends.</span>
<span class="cm">    Subclasses implement _run_bash() and cleanup(). The base class</span>
<span class="cm">    provides execute() with session snapshot sourcing, CWD tracking,</span>
<span class="cm">    interrupt handling, and timeout enforcement.&quot;&quot;&quot;</span>

    <span class="kw">def</span> <span class="fn">_run_bash</span>(self, cmd_string, ...) -&gt; ProcessHandle:
        <span class="cm"># 子类必须实现:在各自后端里 spawn 一个 bash 进程</span>
        <span class="kw">raise</span> NotImplementedError

    <span class="nd">@abstractmethod</span>
    <span class="kw">def</span> <span class="fn">cleanup</span>(self):
        <span class="cm"># 释放后端资源(容器/实例/连接)</span>
        ...</pre>
</div>
<p>注意分工:<strong>子类只实现 <span class="mono">_run_bash()</span>(怎么 spawn 进程)和 <span class="mono">cleanup()</span>(怎么释放资源)</strong>;而 <span class="mono">execute()</span>——会话快照恢复、CWD 跟踪、中断处理、超时强制——这些<strong>跨后端通用的流程</strong>由基类<strong>统一提供</strong>,六个后端复用同一套。于是 docker 后端只关心「怎么在容器里跑 bash」,ssh 后端只关心「怎么在远程跑」,通用的会话状态管理它们<strong>都不用重写</strong>。</p>

<p>那么「会话快照」到底是什么?以 local 后端为例,设计很巧:<strong>每次 <span class="mono">execute()</span> 都重新 spawn 一个全新的 bash 进程</strong>(spawn-per-call),命令跑完进程即退。可这样一来,上一条命令 <span class="mono">export</span> 的环境变量、<span class="mono">cd</span> 切换的目录,下一条岂不全丢?基类的「会话快照」正为此:<strong>每条命令结束后把环境变量快照进文件、当前工作目录也写进文件;下一条命令开跑前先回读、source 回来</strong>。于是一串无状态的短命 bash 进程,被串成一个「有记忆」的会话——这正是<strong>约束 B(无状态)</strong>在 shell 执行层的对策:底层进程无状态,靠外部文件快照重建连续性。</p>

<h2>工厂:按 TERMINAL_ENV 挑后端</h2>
<p>选哪个后端,由一个工厂函数按配置分派——这是「换设备只换后端」的开关:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/terminal_tool.py</span><span class="ln">569 / 1225-1372 · 简化</span></div>
  <pre><span class="cm"># 默认 local;TERMINAL_ENV 配置切换后端</span>
terminal_env = os.getenv(<span class="st">"TERMINAL_ENV"</span>, <span class="st">"local"</span>).strip().lower() <span class="kw">or</span> <span class="st">"local"</span>

<span class="kw">def</span> <span class="fn">_create_environment</span>(env_type, image, cwd, timeout, ...):
    <span class="kw">if</span> env_type == <span class="st">"local"</span>:
        <span class="kw">return</span> _LocalEnvironment(cwd=cwd, timeout=timeout)
    <span class="kw">elif</span> env_type == <span class="st">"docker"</span>:
        <span class="kw">return</span> _DockerEnvironment(...)
    <span class="kw">elif</span> env_type == <span class="st">"modal"</span>:
        <span class="kw">return</span> _ModalEnvironment(...)        <span class="cm"># serverless:按需启动,用完释放</span>
    <span class="kw">elif</span> env_type == <span class="st">"ssh"</span>:
        <span class="kw">return</span> _SSHEnvironment(...)
    ...                                       <span class="cm"># singularity / daytona</span></pre>
</div>
<p><span class="mono">TERMINAL_ENV</span> 默认 <span class="mono">local</span>(本地 subprocess + 进程组隔离),改一个配置就切到 docker(容器隔离)、ssh(远程执行)、modal(serverless)。每个 <span class="mono">_XxxEnvironment</span> 都是 <span class="mono">BaseEnvironment</span> 的子类。工厂是唯一的「分派点」——模型和核心循环<strong>完全不知道</strong>命令落到了哪个环境。换环境=改 <span class="mono">TERMINAL_ENV</span>,不改任何调用代码。</p>
<p>这六个后端各自是 <span class="mono">tools/environments/</span> 下一个独立文件里的类——加一个新后端，只需新增一个文件 + 工厂里加一支 <span class="mono">elif</span>：</p>
<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/terminal_tool.py</span><span class="ln">825-831 · 节选</span></div>
  <pre><span class="cm"># Environment classes now live in tools/environments/</span>
<span class="kw">from</span> tools.environments.local <span class="kw">import</span> LocalEnvironment
<span class="kw">from</span> tools.environments.docker <span class="kw">import</span> DockerEnvironment
<span class="kw">from</span> tools.environments.ssh <span class="kw">import</span> SSHEnvironment
<span class="kw">from</span> tools.environments.modal <span class="kw">import</span> ModalEnvironment
<span class="kw">from</span> tools.environments.singularity <span class="kw">import</span> SingularityEnvironment
<span class="kw">from</span> tools.environments.managed_modal <span class="kw">import</span> ManagedModalEnvironment</pre>
</div>
<p style="font-size:.92em;opacity:.85">注:这份顶层 import 与「六个后端」并非一一对应——<span class="mono">daytona</span> 走<strong>惰性导入</strong>(只在被选中时才在工厂分支内 <span class="mono">import</span>),而 <span class="mono">managed_modal</span> 是 modal 的 <strong>Nous 托管模式</strong>(由 <span class="mono">terminal.modal_mode</span> 选),并非独立的 <span class="mono">TERMINAL_ENV</span> 取值。六个 env_type 始终是 local/docker/ssh/singularity/modal/daytona。</p>

<h2>serverless 省钱 + 后台进程</h2>
<p>多后端不只是「能移植」,还能<strong>省钱</strong>。<span class="mono">modal</span> 这类 <strong>serverless</strong> 后端<strong>按需启动</strong>容器、命令跑完就<strong>释放</strong>——你不必常驻一台云服务器,只为偶尔跑几条命令付全天的钱。另外,terminal 支持 <span class="mono">background=True, notify_on_complete=True</span>:长命令在后台跑,gateway 的 watcher 检测到进程完成时<strong>触发一个新 turn</strong>把结果带回——这条「后台完成→新 turn」的路径(和第 13 章委派的完成队列同理)维持了严格角色交替、不破缓存。</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">模型调统一的 <span class="mono">terminal</span> 工具(只管「跑这条命令」)</span></div>
  <div class="step"><span class="num">2</span><span class="sc">工厂 <span class="mono">_create_environment</span> 按 <span class="mono">TERMINAL_ENV</span> 挑后端(local/docker/ssh/modal/...)</span></div>
  <div class="step"><span class="num">3</span><span class="sc">对应 <span class="mono">BaseEnvironment</span> 子类的 <span class="mono">execute()</span>(基类统一:快照/CWD/中断/超时)→ 子类 <span class="mono">_run_bash()</span> 在该后端 spawn 进程</span></div>
  <div class="step"><span class="num">4</span><span class="sc">返回统一的 <span class="mono">ProcessHandle</span>——核心循环不感知后端差异</span></div>
  <div class="step"><span class="num">5</span><span class="sc">serverless 用完 <span class="mono">cleanup()</span> 释放资源;background+notify_on_complete 则后台跑、完成时作新 turn</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「环境可移植」</div>
  <div class="collab-sub">① 组件清单（★本章核心,其余跨章节配合）</div>
  本章核心:<strong>BaseEnvironment ABC</strong>(统一接口 + execute() 通用流程)、<strong>六个后端子类</strong>(各实现 _run_bash/cleanup)、<strong>_create_environment 工厂</strong>(按 TERMINAL_ENV 分派)。跨章节配合:<span class="mono">terminal</span> 是一个核心<strong>工具</strong>(第 8 章),六种后端差异全被关进边缘子类——这正是<strong>窄腰</strong>(第 4 章:核心薄、后端在边缘);子代理委派时拿到<strong>独立的 terminal session</strong>(第 13 章上下文隔离);background+notify_on_complete 的「后台完成→新 turn」与委派完成队列同理(第 13 章),维持严格角色交替不破缓存。
  <div class="collab-sub">② 数据流时序</div>
  模型调 terminal → 工厂按 TERMINAL_ENV 选后端 → BaseEnvironment 子类 execute()(基类统一会话快照/CWD/中断/超时)→ 子类 _run_bash() 在该后端 spawn → 返回统一 ProcessHandle → cleanup() 释放(serverless 用完即放)。
  <div class="collab-sub">③ 关键点</div>
  「同一个 agent 跑遍各种环境」靠的是<strong>统一抽象 + 工厂分派</strong>:核心只认一个 terminal 工具与一个 BaseEnvironment 接口,六种环境(本地/容器/远程/serverless)的全部差异<strong>沉到边缘的子类</strong>。加新后端=写一个 BaseEnvironment 子类 + 工厂加一支,核心零改动。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线:<strong>统一 terminal 抽象 + 多后端 = 环境可移植 + serverless 省钱;后端差异在边缘(窄腰)</strong>。它主要治两条 LLM 固有约束:
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·运维</span>——真实 agent 要在各种环境里干活:本地开发、容器隔离、远程服务器、serverless 弹性。统一的 <span class="mono">BaseEnvironment</span> 抽象让<strong>同一个 agent 无改动地跑遍它们</strong>,serverless 后端还能<strong>按需启停省钱</strong>;会话快照/CWD/超时等运维细节由基类统一兜底。它也是<strong>窄腰</strong>(第 4 章)的体现:核心只认一个 terminal,环境差异在边缘演化。反模式:为每种环境在核心里写一套 if-else 执行逻辑——那会让核心随后端数量膨胀,违背「核心薄、边缘厚」。</p>
  <p style="margin:.5rem 0 0"><span class="badge constraint">B·无状态</span>——底层 bash 进程是无状态的(spawn-per-call,每条命令一个新进程),基类的<strong>会话快照</strong>(环境变量 + CWD 经文件快照/回读)把它们串成连续会话。无状态的执行底座靠外部快照重建记忆——与全书反复出现的「无状态内核 + 外部状态」一脉相承。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>统一抽象</strong>:六后端(local/docker/ssh/singularity/modal/daytona)共享 <span class="mono">BaseEnvironment</span> ABC;子类只实现 <span class="mono">_run_bash()</span> + <span class="mono">cleanup()</span>,通用 <span class="mono">execute()</span> 由基类提供。</li>
    <li><strong>工厂分派</strong>:<span class="mono">_create_environment</span> 按 <span class="mono">TERMINAL_ENV</span>(默认 local)挑后端;换环境只改配置,核心零改动。</li>
    <li><strong>环境可移植</strong>:同一 agent 无改动跑遍本地/容器/远程/serverless——窄腰(第 4 章)在执行层的落地。</li>
    <li><strong>serverless 省钱</strong>:modal 等后端按需启动、用完 <span class="mono">cleanup()</span> 释放,不为偶发命令常驻付费。</li>
    <li><strong>后台进程</strong>:<span class="mono">background=True, notify_on_complete=True</span> 后台跑,完成时作新 turn(同委派完成队列,第 13 章),不破缓存。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">
For an agent to "act" it must run commands — but <strong>where</strong>? Your local machine, a Docker container, a remote server, or a <strong>serverless</strong> platform like Modal? Hermes's answer: <strong>one terminal tool, backed by pluggable backends</strong>. The model always calls a single <span class="mono">terminal</span>; whether a command lands on local / docker / ssh / modal / singularity / daytona is dispatched transparently by a <strong>unified abstraction</strong>. This lets one agent <strong>run across all environments</strong>, and lets serverless backends <strong>spin up on demand and release when done</strong> to save money.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · a universal remote</div>
  A <strong>universal remote</strong>'s buttons are always "on / off / volume" (unified interface), but it can drive a TV, an AC, a speaker (multiple backends). You <strong>don't</strong> learn a new button layout per device — the remote internally translates "volume+" into each device's IR code. Hermes's terminal is that universal remote: the model always presses "run this command," and the <span class="mono">BaseEnvironment</span> abstraction translates it into local's subprocess, docker's exec, ssh's remote command, modal's serverless call. Swap the device by swapping the backend — <strong>the remote's buttons don't change at all</strong>.
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture · a unified abstraction, backend differences at the edges</div>
  Six execution backends — <strong>local / docker / ssh / singularity / modal / daytona</strong> — share <strong>one interface</strong>, <span class="mono">BaseEnvironment</span> (ABC). Each backend implements just two abstract methods, <span class="mono">_run_bash()</span> and <span class="mono">cleanup()</span>; the unified <span class="mono">execute()</span> (session snapshot, CWD tracking, interrupt, timeout) is <strong>provided by the base class</strong> and reused by all. A factory, <span class="mono">_create_environment</span>, picks the backend by the <span class="mono">TERMINAL_ENV</span> config. This is the narrow waist (ch.4) at the execution layer: <strong>the core knows only one terminal tool</strong>, and the differences of six environments are all caged in edge <span class="mono">BaseEnvironment</span> subclasses — add a new backend, and the core doesn't change a line.
</div>

<h2>The unified interface: the BaseEnvironment ABC</h2>
<p>All backends' "common contract" is an abstract base class — subclasses fill just two holes, the base class handles the rest:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/environments/base.py</span><span class="ln">288-345 · excerpt</span></div>
  <pre><span class="kw">class</span> <span class="fn">BaseEnvironment</span>(ABC):
    <span class="cm">&quot;&quot;&quot;Common interface and unified execution flow for all Hermes backends.</span>
<span class="cm">    Subclasses implement _run_bash() and cleanup(). The base class</span>
<span class="cm">    provides execute() with session snapshot sourcing, CWD tracking,</span>
<span class="cm">    interrupt handling, and timeout enforcement.&quot;&quot;&quot;</span>

    <span class="kw">def</span> <span class="fn">_run_bash</span>(self, cmd_string, ...) -&gt; ProcessHandle:
        <span class="cm"># subclass must implement: spawn a bash process in its own backend</span>
        <span class="kw">raise</span> NotImplementedError

    <span class="nd">@abstractmethod</span>
    <span class="kw">def</span> <span class="fn">cleanup</span>(self):
        <span class="cm"># release backend resources (container/instance/connection)</span>
        ...</pre>
</div>
<p>Note the division: <strong>subclasses implement only <span class="mono">_run_bash()</span> (how to spawn a process) and <span class="mono">cleanup()</span> (how to release resources)</strong>; while <span class="mono">execute()</span> — session snapshot restoration, CWD tracking, interrupt handling, timeout enforcement — these <strong>cross-backend common flows</strong> are <strong>provided uniformly by the base class</strong>, reused by all six backends. So the docker backend cares only about "how to run bash in a container," the ssh backend only about "how to run remotely," and neither <strong>rewrites</strong> the common session-state management.</p>

<p>So what exactly is that "session snapshot"? Take the local backend — the design is elegant: <strong>every <span class="mono">execute()</span> spawns a brand-new bash process</strong> (spawn-per-call) that exits the moment the command finishes. But then wouldn't the env vars <span class="mono">export</span>ed by the previous command, and the directory it <span class="mono">cd</span>'d into, be lost for the next one? The base class's "session snapshot" is exactly for this: <strong>after each command it snapshots env vars into a file and writes the current working directory to a file too; before the next command runs, it reads them back and sources them in</strong>. So a string of stateless, short-lived bash processes is woven into a session "with memory" — precisely the countermeasure for <strong>constraint B (statelessness)</strong> at the shell-execution layer: the underlying processes are stateless, and continuity is rebuilt from external file snapshots.</p>

<h2>The factory: pick the backend by TERMINAL_ENV</h2>
<p>Which backend is chosen is dispatched by a factory function from config — the switch for "swap the device by swapping the backend":</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/terminal_tool.py</span><span class="ln">569 / 1225-1372 · simplified</span></div>
  <pre><span class="cm"># default local; TERMINAL_ENV switches the backend</span>
terminal_env = os.getenv(<span class="st">"TERMINAL_ENV"</span>, <span class="st">"local"</span>).strip().lower() <span class="kw">or</span> <span class="st">"local"</span>

<span class="kw">def</span> <span class="fn">_create_environment</span>(env_type, image, cwd, timeout, ...):
    <span class="kw">if</span> env_type == <span class="st">"local"</span>:
        <span class="kw">return</span> _LocalEnvironment(cwd=cwd, timeout=timeout)
    <span class="kw">elif</span> env_type == <span class="st">"docker"</span>:
        <span class="kw">return</span> _DockerEnvironment(...)
    <span class="kw">elif</span> env_type == <span class="st">"modal"</span>:
        <span class="kw">return</span> _ModalEnvironment(...)        <span class="cm"># serverless: spin up on demand, release when done</span>
    <span class="kw">elif</span> env_type == <span class="st">"ssh"</span>:
        <span class="kw">return</span> _SSHEnvironment(...)
    ...                                       <span class="cm"># singularity / daytona</span></pre>
</div>
<p><span class="mono">TERMINAL_ENV</span> defaults to <span class="mono">local</span> (local subprocess + process-group isolation); change one config to switch to docker (container isolation), ssh (remote), modal (serverless). Each <span class="mono">_XxxEnvironment</span> is a subclass of <span class="mono">BaseEnvironment</span>. The factory is the single "dispatch point" — the model and the core loop have <strong>no idea</strong> which environment a command landed on. Switch environments = change <span class="mono">TERMINAL_ENV</span>, change no calling code.</p>
<p>Each of these six backends is a class in its own file under <span class="mono">tools/environments/</span> — adding a new backend just needs a new file + one <span class="mono">elif</span> in the factory:</p>
<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/terminal_tool.py</span><span class="ln">825-831 · excerpt</span></div>
  <pre><span class="cm"># Environment classes now live in tools/environments/</span>
<span class="kw">from</span> tools.environments.local <span class="kw">import</span> LocalEnvironment
<span class="kw">from</span> tools.environments.docker <span class="kw">import</span> DockerEnvironment
<span class="kw">from</span> tools.environments.ssh <span class="kw">import</span> SSHEnvironment
<span class="kw">from</span> tools.environments.modal <span class="kw">import</span> ModalEnvironment
<span class="kw">from</span> tools.environments.singularity <span class="kw">import</span> SingularityEnvironment
<span class="kw">from</span> tools.environments.managed_modal <span class="kw">import</span> ManagedModalEnvironment</pre>
</div>
<p style="font-size:.92em;opacity:.85">Note: this top-level import list is <strong>not</strong> one-to-one with the "six backends" — <span class="mono">daytona</span> is <strong>lazily imported</strong> (only <span class="mono">import</span>ed inside its factory branch when selected), and <span class="mono">managed_modal</span> is modal's <strong>Nous-managed mode</strong> (chosen via <span class="mono">terminal.modal_mode</span>), not a standalone <span class="mono">TERMINAL_ENV</span> value. The six env types are always local/docker/ssh/singularity/modal/daytona.</p>

<h2>serverless savings + background processes</h2>
<p>Multiple backends aren't just "portable" — they also <strong>save money</strong>. Serverless backends like <span class="mono">modal</span> <strong>spin up</strong> a container on demand and <strong>release</strong> it when the command finishes — you needn't keep a cloud server running around the clock just to run a few commands occasionally. Also, the terminal supports <span class="mono">background=True, notify_on_complete=True</span>: a long command runs in the background, and when the gateway's watcher detects the process finished it <strong>triggers a new turn</strong> to bring the result back — this "background done → new turn" path (same idea as ch.13's delegation completion queue) keeps strict role alternation and doesn't break the cache.</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">the model calls the unified <span class="mono">terminal</span> tool (just "run this command")</span></div>
  <div class="step"><span class="num">2</span><span class="sc">the factory <span class="mono">_create_environment</span> picks the backend by <span class="mono">TERMINAL_ENV</span> (local/docker/ssh/modal/...)</span></div>
  <div class="step"><span class="num">3</span><span class="sc">the matching <span class="mono">BaseEnvironment</span> subclass's <span class="mono">execute()</span> (base: snapshot/CWD/interrupt/timeout) → subclass <span class="mono">_run_bash()</span> spawns a process in that backend</span></div>
  <div class="step"><span class="num">4</span><span class="sc">returns a unified <span class="mono">ProcessHandle</span> — the core loop is unaware of backend differences</span></div>
  <div class="step"><span class="num">5</span><span class="sc">serverless <span class="mono">cleanup()</span> releases resources when done; background+notify_on_complete runs in the background, surfacing as a new turn on completion</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "environment portability"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: the <strong>BaseEnvironment ABC</strong> (unified interface + execute() common flow), the <strong>six backend subclasses</strong> (each implements _run_bash/cleanup), the <strong>_create_environment factory</strong> (dispatch by TERMINAL_ENV). Cross-chapter teamwork: <span class="mono">terminal</span> is one core <strong>tool</strong> (ch.8), and six backends' differences are all caged in edge subclasses — exactly the <strong>narrow waist</strong> (ch.4: thin core, backends at the edges); a delegated subagent gets its own <strong>independent terminal session</strong> (ch.13 context isolation); background+notify_on_complete's "background done → new turn" works like the delegation completion queue (ch.13), keeping strict alternation and the cache.
  <div class="collab-sub">② Data-flow timing</div>
  the model calls terminal → the factory picks the backend by TERMINAL_ENV → the BaseEnvironment subclass's execute() (base-unified session snapshot/CWD/interrupt/timeout) → the subclass's _run_bash() spawns in that backend → returns a unified ProcessHandle → cleanup() releases (serverless frees when done).
  <div class="collab-sub">③ The key point</div>
  "One agent runs across all environments" rests on a <strong>unified abstraction + factory dispatch</strong>: the core knows only one terminal tool and one BaseEnvironment interface, and all the differences of six environments (local/container/remote/serverless) <strong>sink to edge subclasses</strong>. Add a new backend = write a BaseEnvironment subclass + one factory branch, with zero change to the core.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>a unified terminal abstraction + multiple backends = environment portability + serverless savings; backend differences at the edges (narrow waist)</strong>. It mainly treats two inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·ops</span> — a real agent must work in all kinds of environments: local dev, container isolation, remote servers, serverless elasticity. The unified <span class="mono">BaseEnvironment</span> abstraction lets <strong>one agent run across them unchanged</strong>, and serverless backends can <strong>start/stop on demand to save money</strong>; ops details like session snapshot/CWD/timeout are handled uniformly by the base class. It's also the <strong>narrow waist</strong> (ch.4): the core knows only one terminal, and environment differences evolve at the edges. The anti-pattern: writing per-environment if-else execution logic in the core — that bloats the core with each backend added, against "thin core, thick edges."</p>
  <p style="margin:.5rem 0 0"><span class="badge constraint">B·statelessness</span> — the underlying bash processes are stateless (spawn-per-call, a new process per command); the base class's <strong>session snapshot</strong> (env vars + CWD via file snapshot/read-back) strings them into a continuous session. A stateless execution substrate rebuilds memory from external snapshots — of a piece with the book's recurring "stateless core + external state."</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Unified abstraction</strong>: six backends (local/docker/ssh/singularity/modal/daytona) share the <span class="mono">BaseEnvironment</span> ABC; subclasses implement only <span class="mono">_run_bash()</span> + <span class="mono">cleanup()</span>, the common <span class="mono">execute()</span> is provided by the base class.</li>
    <li><strong>Factory dispatch</strong>: <span class="mono">_create_environment</span> picks the backend by <span class="mono">TERMINAL_ENV</span> (default local); switch environments by config only, zero core change.</li>
    <li><strong>Environment portability</strong>: one agent runs across local/container/remote/serverless unchanged — the narrow waist (ch.4) at the execution layer.</li>
    <li><strong>serverless savings</strong>: backends like modal start on demand and <span class="mono">cleanup()</span> when done, not paying to keep a server running for occasional commands.</li>
    <li><strong>Background processes</strong>: <span class="mono">background=True, notify_on_complete=True</span> runs in the background and surfaces as a new turn on completion (like the delegation completion queue, ch.13), not breaking the cache.</li>
  </ul>
</div>
""",
}
