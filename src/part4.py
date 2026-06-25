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
