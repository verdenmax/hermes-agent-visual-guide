"""part3 — 第三部分 · 自我进化闭环：ch9 学习nudge+技能 / ch10 Curator / ch11 记忆 / ch12 跨会话搜索。

逐章 LESSON_09..12。codefile 标「节选/简化」者为可读性重排，真实性见 docs/superpowers/specs/chapters/。
"""

LESSON_09 = {
    "zh": r"""
<p class="lead">
Hermes 最招牌的特性是<strong>自我进化</strong>：它会跨会话变得更懂你、更会做你这一类任务。本章讲清这套学习闭环的<strong>入口</strong>——每隔约 10 轮（默认值，可配置），在一轮对话<strong>结束、响应已经交给你之后</strong>，Hermes 会 fork 一个<strong>后台 review agent</strong>，让它重放刚才的对话，自问「<strong>这轮有没有该存下来的技能或记忆？</strong>」。最关键的一句话：这一切发生在后台，<strong>主对话和 prompt 缓存全程一个字节都不动</strong>。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 下班后复盘 / 学徒记笔记</div>
  把它想成一位敬业的学徒。白天干活时（主对话），他<strong>全神贯注</strong>把活干完，绝不停下来写日记——那会打断手上的任务。但<strong>下班之后</strong>（响应已交付），他会翻看今天的工单，把「这一类活该怎么干」<strong>沉淀成手册</strong>（技能），把「这位客户是谁、喜欢什么」<strong>记进备忘</strong>（记忆）。第二天上工，他带着<strong>更新过的手册</strong>，但今天的工作流程<strong>一点没被打断过</strong>。学习发生在「别的时间、别的人手里」——这正是不破坏缓存的关键。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 程序性记忆 vs 声明性记忆</div>
  Hermes 把「学到的东西」分成两类：<strong>技能</strong>是<strong>程序性</strong>的——「怎么做<strong>这一类</strong>任务」（SKILL.md + 脚本/模板/参考），可执行、可复用、按需加载；<strong>记忆</strong>是<strong>声明性</strong>的——「用户是谁、当前状态如何」（第 11 章）。两者由<strong>同一个</strong>后台 review fork 一起产出。技能下沉到<strong>边缘</strong>（第 4 章窄腰：能力不进核心、按需加载），既不挤占每次调用的工具 schema，也不撑爆上下文。
</div>

<h2>技能与记忆的分界：写进哪里</h2>
<p>到底什么该进技能、什么该进记忆？后台 review 的 prompt 把这条线划得很清楚——这是真实喂给 review fork 的指令原文：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/background_review.py</span><span class="ln">233-237 · 节选（review prompt 原文）</span></div>
  <pre>Memory captures <span class="st">'who the user is and what the current situation
and state of your operations are'</span>; skills capture <span class="st">'how to do
this class of task for this user'</span>. When they complain about how
you handled a task, the skill that governs that task needs to
carry the lesson.</pre>
</div>
<p>一句话：<strong>记忆 = 是谁 / 是什么状态</strong>（紧凑、每轮注入），<strong>技能 = 怎么做这一类任务</strong>（按需加载的可执行手册）。当用户抱怨你某次任务做得不好，正确的反应不是「记一条 memory」，而是<strong>去更新管这类任务的那个技能</strong>——让教训沉淀进「下次怎么做」。</p>

<h2>触发：nudge 计数，但响应之后才动手</h2>
<p>学习由一个<strong>计数器</strong>驱动：每轮累加，到阈值就置一个布尔。但关键在于——它<strong>不往主对话注入任何文字</strong>，只是个标记，<strong>等响应发出之后</strong>才被消费：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/turn_finalizer.py</span><span class="ln">432-456 · 简化</span></div>
  <pre><span class="cm"># 基于本轮用了多少工具迭代，现在就判断要不要触发技能 review</span>
_should_review_skills = <span class="kw">False</span>
<span class="kw">if</span> (agent._skill_nudge_interval &gt; 0
        <span class="kw">and</span> agent._iters_since_skill &gt;= agent._skill_nudge_interval
        <span class="kw">and</span> <span class="st">"skill_manage"</span> <span class="kw">in</span> agent.valid_tool_names):
    _should_review_skills = <span class="kw">True</span>
    agent._iters_since_skill = 0

<span class="cm"># 后台 review —— 在响应已交付【之后】才跑，绝不与用户任务争夺模型注意力</span>
<span class="kw">if</span> final_response <span class="kw">and</span> <span class="kw">not</span> interrupted <span class="kw">and</span> (_should_review_memory <span class="kw">or</span> _should_review_skills):
    agent._spawn_background_review(
        messages_snapshot=<span class="fn">list</span>(messages),       <span class="cm"># 传快照，不是 live messages</span>
        review_memory=_should_review_memory,
        review_skills=_should_review_skills,
    )</pre>
</div>
<p>注意那条注释：<span class="inline">runs AFTER the response is delivered so it never competes with the user's task for model attention</span>。nudge 触发后<strong>什么文字都不会进主对话</strong>——它只是 <span class="mono">_should_review_skills = True</span> 这个布尔；真正的 review 要等响应发完、在 <span class="mono">turn_finalizer</span> 里才被消费。传给 fork 的还是 <span class="mono">list(messages)</span> 一份<strong>快照</strong>，原始对话不受影响。</p>

<h2>不破缓存的关键：fork 一个独立 agent</h2>
<p>消费这个布尔的，是一个<strong>独立 fork 出来的 review agent</strong>。它的模块 docstring 把不变量钉死：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/background_review.py</span><span class="ln">3-8 · 节选</span></div>
  <pre>After every turn, AIAgent.run_conversation may call spawn_background_review
to fire off a daemon thread that replays the conversation snapshot in a
forked AIAgent and asks itself <span class="st">"should any skill/memory be saved
or updated?"</span>.  Writes go straight to the memory + skill stores.
<span class="cm">Main conversation and prompt cache are never touched.</span></pre>
</div>
<p>这就是「自我进化」与「缓存神圣」能并存的全部秘密：review 跑在一个 <strong>daemon 线程 + fork 的 AIAgent</strong> 里，重放对话<strong>快照</strong>、自问该不该存，写入<strong>直接落进技能/记忆库</strong>。主对话的消息序列、system prompt、上游缓存——<strong>全程零改动</strong>。写发生在<strong>别处</strong>，新技能要到<strong>下个会话</strong>才进 stable 前缀。</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">一轮对话结束，响应<strong>已经交付</strong>给用户（学习绝不发生在这之前）</span></div>
  <div class="step"><span class="num">2</span><span class="sc">nudge 计数 <span class="mono">_iters_since_skill</span> 达到阈值 → 置 <span class="mono">_should_review_skills = True</span>（<strong>不</strong>往主对话注入任何文字）</span></div>
  <div class="step"><span class="num">3</span><span class="sc">turn_finalizer fork 一个 background review AIAgent（daemon 线程）</span></div>
  <div class="step"><span class="num">4</span><span class="sc">review 重放 <span class="mono">list(messages)</span> 快照，自问「该抽出技能 / 记忆吗」</span></div>
  <div class="step"><span class="num">5</span><span class="sc"><span class="mono">skill_manage(create)</span> 落盘，provenance 标 agent-created</span></div>
  <div class="step"><span class="num">6</span><span class="sc">主对话 / system prompt / 缓存<strong>全程零改动</strong> —— 新技能下个会话才进 stable 前缀</span></div>
</div>

<h2>两道护栏：产权门控 + 延迟失效</h2>
<p>这套自动学习还有两道关键护栏。其一，<strong>产权门控</strong>：只有<strong>后台 review fork</strong> 创建的技能才被标记为「agent 创建」、归 curator 管辖（第 10 章）——你<strong>亲手</strong>建的技能 curator 永不触碰：</p>
<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/skill_manager_tool.py</span><span class="ln">1082-1084 · 节选</span></div>
  <pre><span class="kw">if</span> action == <span class="st">"create"</span>:
    <span class="kw">if</span> is_background_review():        <span class="cm"># 仅当来自后台 review fork</span>
        mark_agent_created(name)</pre>
</div>
<p>其二，<strong>延迟失效</strong>：技能清单是 system prompt 的一部分（第 6 章 stable 层）。所以凡是会改动技能集的命令，都<strong>默认延迟生效</strong>——改动<strong>下个会话</strong>才进前缀，本会话缓存不破；只有显式加 <span class="mono">--now</span>（如 <span class="mono">/skills install --now</span>）才立即失效。这正是 AGENTS.md 钉死的「cache-aware slash command」范式。还有一个细节：技能被 <span class="mono">/skill-name</span> 调用时，是作为 <strong>user 消息</strong>注入、<strong>而非</strong>塞进 system prompt——同样是为了不动那条神圣的前缀。</p>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「学习而不破缓存」</div>
  <div class="collab-sub">① 组件清单（★本章核心，其余跨章节配合）</div>
  本章核心：<strong>nudge 计数</strong>（<span class="mono">turn_finalizer</span> 的 _iters_since_skill）、<strong>background review fork</strong>（独立 AIAgent 重放快照）、<strong>skill_commands</strong>（技能以 user 消息注入）、<strong>产权门控</strong>（<span class="mono">is_background_review</span> → mark_agent_created）。跨章节配合：同一个 fork <strong>既存技能也存记忆</strong>（第 11 章——skill/memory 两条产出共用一次 review）；技能进 <strong>stable 层</strong>、变更<strong>延迟失效</strong>守缓存（第 6 章）；curator 只园丁<strong>fork 创建</strong>的 agent-skill（第 10 章）；skill nudge 与 memory nudge <strong>同构</strong>，共用 turn_finalizer 的「响应后 fork」机制（第 11 章）。
  <div class="collab-sub">② 数据流时序</div>
  每轮 <span class="mono">_iters_since_skill++</span> → 达阈值置 <span class="mono">_should_review_skills</span> → <strong>响应已交付给用户</strong>后（turn_finalizer）→ fork background review AIAgent → 重放 <span class="mono">list(messages)</span> 快照、自问「该抽出技能吗」→ <span class="mono">skill_manage(create)</span> 落盘（产权标 agent-created）→ <strong>主对话 / system prompt / 缓存全程零改动</strong> → 新技能下个会话才进 stable 前缀。
  <div class="collab-sub">③ 关键点</div>
  学习发生在「响应<strong>之后</strong>的后台 fork」里——既<strong>不与用户任务争模型注意力</strong>，也<strong>绝不改写主对话前缀</strong>。写在别处、生效在下次：这就是「自我进化」与「缓存神圣」共存的根本手法。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线：<strong>学习闭环全程不破缓存</strong>。三条具体手法：nudge 只置布尔、turn 后 fork（不注入主对话）；技能以 user 消息注入（不进 system prompt）；技能变更默认延迟失效（<span class="mono">--now</span> 才立即）。它治两条 LLM 固有约束：
  <p style="margin:.5rem 0 0"><span class="badge constraint">B·无状态</span>——模型本身跨会话什么都记不住，靠把「经验」沉淀成<strong>持久的技能 / 记忆</strong>来对抗；
  <span class="badge constraint">A·中间遗失</span>——技能是<strong>按需加载</strong>的程序性记忆，不一股脑塞进上下文，避免淹没注意力。反模式：把 nudge 文字塞进主对话、或把新技能<strong>立即</strong>重载进 system prompt——两者都会在会话中途改写前缀、击穿缓存（第 6 章）。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>技能 = 程序性记忆</strong>：「怎么做这一类任务」；记忆 = 声明性「是谁 / 什么状态」（第 11 章）。同一后台 fork 一起产出。</li>
    <li><strong>nudge 不进主对话</strong>：只置 <span class="mono">_should_review_skills</span> 布尔，<strong>响应交付后</strong>才在 turn_finalizer 消费。</li>
    <li><strong>fork 独立 review</strong>：daemon 线程 + forked AIAgent 重放快照，<span class="mono">Main conversation and prompt cache are never touched</span>。</li>
    <li><strong>产权门控</strong>：仅 <span class="mono">is_background_review()</span> 创建的技能 <span class="mono">mark_agent_created</span>、归 curator 管；你亲手建的不碰（第 10 章）。</li>
    <li><strong>延迟失效</strong>：技能在 stable 层；变更默认下个会话生效，<span class="mono">--now</span> 才立即——cache-aware slash command 范式（第 6 章）。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">
Hermes's signature feature is <strong>self-improvement</strong>: across sessions it gets better at understanding you and at doing your kind of task. This chapter covers the <strong>entry point</strong> of that learning loop — every ~10 turns (a configurable default), <strong>after a turn ends and the response is already delivered to you</strong>, Hermes forks a <strong>background review agent</strong> that replays the conversation and asks itself, "<strong>was there a skill or memory worth saving this turn?</strong>" The crucial line: all of this happens in the background, and the <strong>main conversation and prompt cache are never touched, not by a single byte</strong>.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · an after-hours debrief / an apprentice's notes</div>
  Think of a diligent apprentice. While working during the day (the main conversation) he is <strong>fully focused</strong> on finishing the job — never stopping to journal, which would interrupt the task at hand. But <strong>after hours</strong> (the response already delivered) he reviews the day's tickets, <strong>distilling "how this class of job is done" into a manual</strong> (a skill) and <strong>jotting down "who this client is and what they like" into a memo</strong> (memory). Next morning he shows up with an <strong>updated manual</strong>, yet today's workflow was <strong>never once interrupted</strong>. Learning happens "at another time, in another set of hands" — exactly why the cache stays intact.
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture · procedural vs declarative memory</div>
  Hermes splits "what it learns" into two kinds: <strong>skills</strong> are <strong>procedural</strong> — "how to do <strong>this class</strong> of task" (SKILL.md + scripts/templates/references), executable, reusable, loaded on demand; <strong>memory</strong> is <strong>declarative</strong> — "who the user is, what the current state is" (ch.11). Both are produced by the <strong>same</strong> background review fork. Skills sink to the <strong>edges</strong> (ch.4's narrow waist: capability stays out of the core, loaded on demand), so they neither crowd the per-call tool schema nor blow up the context.
</div>

<h2>The skill/memory boundary: which one to write to</h2>
<p>What goes into a skill versus a memory? The background review's prompt draws that line sharply — this is the verbatim instruction actually fed to the review fork:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/background_review.py</span><span class="ln">233-237 · excerpt (verbatim review prompt)</span></div>
  <pre>Memory captures <span class="st">'who the user is and what the current situation
and state of your operations are'</span>; skills capture <span class="st">'how to do
this class of task for this user'</span>. When they complain about how
you handled a task, the skill that governs that task needs to
carry the lesson.</pre>
</div>
<p>In a sentence: <strong>memory = who / what-state</strong> (compact, injected every turn), <strong>skill = how to do this class of task</strong> (an executable manual loaded on demand). When the user complains you handled a task poorly, the right move isn't "log a memory" — it's to <strong>update the skill that governs that class of task</strong>, so the lesson lands in "how to do it next time."</p>

<h2>The trigger: nudge counts, but acts only after the response</h2>
<p>Learning is driven by a <strong>counter</strong>: it increments each turn and sets a boolean at the threshold. The key: it <strong>injects no text into the main conversation</strong> — it's just a flag, consumed <strong>after the response has gone out</strong>:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/turn_finalizer.py</span><span class="ln">432-456 · simplified</span></div>
  <pre><span class="cm"># Decide NOW whether to trigger a skill review, based on this turn's iterations</span>
_should_review_skills = <span class="kw">False</span>
<span class="kw">if</span> (agent._skill_nudge_interval &gt; 0
        <span class="kw">and</span> agent._iters_since_skill &gt;= agent._skill_nudge_interval
        <span class="kw">and</span> <span class="st">"skill_manage"</span> <span class="kw">in</span> agent.valid_tool_names):
    _should_review_skills = <span class="kw">True</span>
    agent._iters_since_skill = 0

<span class="cm"># Background review — runs AFTER the response is delivered, never competing</span>
<span class="cm"># with the user's task for model attention</span>
<span class="kw">if</span> final_response <span class="kw">and</span> <span class="kw">not</span> interrupted <span class="kw">and</span> (_should_review_memory <span class="kw">or</span> _should_review_skills):
    agent._spawn_background_review(
        messages_snapshot=<span class="fn">list</span>(messages),       <span class="cm"># a snapshot, not live messages</span>
        review_memory=_should_review_memory,
        review_skills=_should_review_skills,
    )</pre>
</div>
<p>Note the comment: <span class="inline">runs AFTER the response is delivered so it never competes with the user's task for model attention</span>. After a nudge fires, <strong>no text enters the main conversation</strong> — it's only the boolean <span class="mono">_should_review_skills = True</span>; the real review waits until the response is out and is consumed in <span class="mono">turn_finalizer</span>. What's handed to the fork is <span class="mono">list(messages)</span> — a <strong>snapshot</strong>, leaving the original conversation untouched.</p>

<h2>Why the cache survives: fork a separate agent</h2>
<p>The boolean is consumed by a <strong>separately forked review agent</strong>. Its module docstring pins the invariant:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/background_review.py</span><span class="ln">3-8 · excerpt</span></div>
  <pre>After every turn, AIAgent.run_conversation may call spawn_background_review
to fire off a daemon thread that replays the conversation snapshot in a
forked AIAgent and asks itself <span class="st">"should any skill/memory be saved
or updated?"</span>.  Writes go straight to the memory + skill stores.
<span class="cm">Main conversation and prompt cache are never touched.</span></pre>
</div>
<p>This is the whole secret of how "self-improvement" coexists with "the cache is sacred": the review runs in a <strong>daemon thread + a forked AIAgent</strong>, replaying a conversation <strong>snapshot</strong>, asking whether to save, writing <strong>straight into the skill/memory stores</strong>. The main conversation's message sequence, system prompt, and upstream cache — <strong>all unchanged throughout</strong>. The write happens <strong>elsewhere</strong>; a new skill only enters the stable prefix <strong>next session</strong>.</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">a turn ends, the response is <strong>already delivered</strong> (learning never happens before this)</span></div>
  <div class="step"><span class="num">2</span><span class="sc">nudge counter <span class="mono">_iters_since_skill</span> hits the threshold → sets <span class="mono">_should_review_skills = True</span> (<strong>no</strong> text injected into the main conversation)</span></div>
  <div class="step"><span class="num">3</span><span class="sc">turn_finalizer forks a background review AIAgent (daemon thread)</span></div>
  <div class="step"><span class="num">4</span><span class="sc">the review replays the <span class="mono">list(messages)</span> snapshot, asking 'should a skill / memory be saved?'</span></div>
  <div class="step"><span class="num">5</span><span class="sc"><span class="mono">skill_manage(create)</span> writes to disk, provenance marked agent-created</span></div>
  <div class="step"><span class="num">6</span><span class="sc">main conversation / system prompt / cache <strong>all unchanged</strong> — the new skill enters the stable prefix only next session</span></div>
</div>

<h2>Two guardrails: provenance gating + deferred invalidation</h2>
<p>This auto-learning has two key guardrails. First, <strong>provenance gating</strong>: only skills created by the <strong>background review fork</strong> are marked "agent-created" and fall under the curator (ch.10) — skills <strong>you</strong> made by hand are never touched:</p>
<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/skill_manager_tool.py</span><span class="ln">1082-1084 · excerpt</span></div>
  <pre><span class="kw">if</span> action == <span class="st">"create"</span>:
    <span class="kw">if</span> is_background_review():        <span class="cm"># only when it comes from the background review fork</span>
        mark_agent_created(name)</pre>
</div>
<p>Second, <strong>deferred invalidation</strong>: the skills list is part of the system prompt (ch.6's stable tier). So any command that changes the skill set is <strong>deferred by default</strong> — the change enters the prefix <strong>next session</strong>, sparing this session's cache; only an explicit <span class="mono">--now</span> (e.g. <span class="mono">/skills install --now</span>) invalidates immediately. This is the "cache-aware slash command" pattern pinned in AGENTS.md. One more detail: when a skill is invoked via <span class="mono">/skill-name</span>, it is injected as a <strong>user message</strong>, <strong>not</strong> dropped into the system prompt — again, to leave that sacred prefix alone.</p>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "learn without breaking the cache"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: <strong>nudge counting</strong> (<span class="mono">turn_finalizer</span>'s _iters_since_skill), the <strong>background review fork</strong> (a separate AIAgent replaying a snapshot), <strong>skill_commands</strong> (skills injected as user messages), <strong>provenance gating</strong> (<span class="mono">is_background_review</span> → mark_agent_created). Cross-chapter teamwork: the same fork <strong>saves both skills and memory</strong> (ch.11 — two outputs from one review); skills enter the <strong>stable tier</strong> and changes use <strong>deferred invalidation</strong> to guard the cache (ch.6); the curator only gardens <strong>fork-created</strong> agent-skills (ch.10); skill nudge is <strong>isomorphic</strong> to memory nudge, sharing turn_finalizer's "fork after the response" mechanism (ch.11).
  <div class="collab-sub">② Data-flow timing</div>
  each turn <span class="mono">_iters_since_skill++</span> → at the threshold set <span class="mono">_should_review_skills</span> → <strong>after the response is delivered</strong> (turn_finalizer) → fork a background review AIAgent → replay the <span class="mono">list(messages)</span> snapshot, ask "should a skill be extracted?" → <span class="mono">skill_manage(create)</span> writes to disk (provenance = agent-created) → <strong>main conversation / system prompt / cache all unchanged</strong> → the new skill enters the stable prefix only next session.
  <div class="collab-sub">③ The key point</div>
  Learning happens in the "background fork <strong>after</strong> the response" — neither <strong>competing for model attention</strong> with the user's task nor <strong>rewriting the main conversation's prefix</strong>. Written elsewhere, effective next time: that's how "self-improvement" coexists with "the cache is sacred."
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>the learning loop never breaks the cache</strong>. Three concrete techniques: a nudge only sets a boolean and forks after the turn (no injection into the main conversation); skills are injected as user messages (not into the system prompt); skill changes default to deferred invalidation (<span class="mono">--now</span> for immediate). It treats two inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">B·stateless</span> — the model itself remembers nothing across sessions, so it fights that by distilling "experience" into <strong>durable skills / memory</strong>;
  <span class="badge constraint">A·lost-in-the-middle</span> — skills are <strong>on-demand</strong> procedural memory, not dumped wholesale into context, avoiding attention overload. The anti-pattern: injecting nudge text into the main conversation, or reloading a new skill <strong>immediately</strong> into the system prompt — both rewrite the prefix mid-session and shatter the cache (ch.6).</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Skill = procedural memory</strong>: "how to do this class of task"; memory = declarative "who / what-state" (ch.11). Both produced by the same background fork.</li>
    <li><strong>Nudge never enters the main conversation</strong>: it only sets the <span class="mono">_should_review_skills</span> boolean, consumed in turn_finalizer <strong>after the response is delivered</strong>.</li>
    <li><strong>Forked, separate review</strong>: a daemon thread + forked AIAgent replays a snapshot; <span class="mono">Main conversation and prompt cache are never touched</span>.</li>
    <li><strong>Provenance gating</strong>: only skills created via <span class="mono">is_background_review()</span> are <span class="mono">mark_agent_created</span> and curated; hand-made ones are left alone (ch.10).</li>
    <li><strong>Deferred invalidation</strong>: skills live in the stable tier; changes default to next-session, <span class="mono">--now</span> for immediate — the cache-aware slash command pattern (ch.6).</li>
  </ul>
</div>
""",
}

LESSON_10 = {
    "zh": r"""
<p class="lead">
第 9 章里，后台 review 会不断<strong>创建</strong>新技能。问题随之而来：技能库会不会越长越乱、塞满一堆只用过一次的「一次性」技能？这就是 <strong>Curator</strong>（技能园丁）要解决的——它在后台定期巡查 agent 创建的技能，把<strong>长期不用</strong>的自动降级、归档。但它有一条铁律：<strong>永远只归档、绝不删除</strong>，而且<strong>整个过程不碰主对话的 prompt 缓存</strong>。本章也是「数据安全 + 辅助模型隔离」的范本。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 图书馆管理员 + 可恢复的暂存库</div>
  把技能库想成一座图书馆。<strong>管理员</strong>（curator）每隔一阵子巡一次馆，把<strong>很久没人借</strong>的书先挪到「暂存区」（stale），再久没动就搬进<strong>地下库房</strong>（archived）。但他<strong>从不烧书</strong>——库房里的书随时能取回。读者<strong>钉住</strong>（pinned）的常用书永远留在书架上、不受巡查影响。最关键的是，管理员在<strong>另一间办公室</strong>干活（forked agent），从不打断正在阅览区看书的你（主对话）。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 自我维护，但永不破坏</div>
  Curator 的设计被一句话概括：<strong>自我维护，但永不破坏</strong>。它<strong>只治理「后台 review fork 自动创建」</strong>的技能（标记 <span class="mono">created_by=agent</span>）——你<strong>手工</strong>建的（不会被标记）、hub 安装的、受保护内置都不碰；它<strong>永不删除</strong>，最激进的动作是归档（可恢复）；<strong>pinned 技能豁免</strong>一切自动转换；而且它<strong>用辅助模型</strong>跑在独立 session 里，<strong>从不触碰主对话的 prompt 缓存</strong>。这四条不变量，正是「让 agent 自由进化」与「数据绝不丢、缓存绝不破」之间的安全边界。
</div>

<h2>四条不变量：写在 docstring 里的安全边界</h2>
<p>这些约束不是口头约定，而是钉死在模块 docstring 里的<strong>严格不变量</strong>：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/curator.py</span><span class="ln">15-19 · 节选</span></div>
  <pre><span class="cm">Strict invariants:</span>
<span class="cm">  - Only touches agent-created skills (see tools/skill_usage.is_agent_created)</span>
<span class="cm">  - Never auto-deletes — only archives. Archive is recoverable.</span>
<span class="cm">  - Pinned skills bypass all auto-transitions</span>
<span class="cm">  - Uses the auxiliary client; never touches the main session's prompt cache</span></pre>
</div>
<p>逐条拆开：①这里的「agent 创建」特指<strong>后台 review fork 自动创建</strong>的技能（产权门控见第 9 章，<span class="mono">created_by=agent</span>）——你<strong>手工</strong>建的不会被标记，所以<strong>永远安全</strong>；<strong>hub 安装</strong>的无条件豁免，<strong>bundled 内置</strong>默认（<span class="mono">prune_builtins</span>）也只可能被<strong>归档</strong>、绝不删改；②<strong>永不删，只归档</strong>，且归档<strong>可恢复</strong>（搬进 <span class="mono">.archive/</span>，随时 restore）；③<strong>pinned 豁免</strong>一切自动转换；④<strong>用辅助客户端、绝不碰主 session 的 prompt 缓存</strong>。最后这条把 curator 和「缓存神圣」（第 6 章）直接绑定。</p>

<h2>确定性状态机：active → stale → archived</h2>
<p>降级的核心是一个<strong>纯确定性</strong>的状态机——不调用任何 LLM，只看技能「最近一次真实活动」的时间戳：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/curator.py</span><span class="ln">276-331 · 简化</span></div>
  <pre><span class="kw">for</span> row <span class="kw">in</span> skill_usage.agent_created_report():
    <span class="kw">if</span> row.get(<span class="st">"pinned"</span>):
        <span class="kw">continue</span>                                  <span class="cm"># pinned 豁免一切转换</span>
    <span class="cm"># 活跃锚点：最近活动 -> 创建时间 -> 现在（新技能不会立刻自我归档）</span>
    anchor = last_activity <span class="kw">or</span> created_at <span class="kw">or</span> now

    <span class="kw">if</span> anchor &lt;= archive_cutoff <span class="kw">and</span> current != ARCHIVED:
        archive_skill(name)                       <span class="cm"># 90 天未动 -> 归档（可恢复）</span>
    <span class="kw">elif</span> anchor &lt;= stale_cutoff <span class="kw">and</span> current == ACTIVE:
        set_state(name, STALE)                    <span class="cm"># 30 天未动 -> 标记 stale</span>
    <span class="kw">elif</span> anchor &gt; stale_cutoff <span class="kw">and</span> current == STALE:
        set_state(name, ACTIVE)                   <span class="cm"># 又被用了 -> 复活</span></pre>
</div>
<p>三条转换都基于 <span class="mono">anchor</span>（最近活动时间）：30 天没动 <span class="mono">active → stale</span>，90 天没动 <span class="mono">stale → archived</span>，一旦又被用到则 <span class="mono">stale → active</span> 复活。注意 anchor 的回退链 <span class="mono">last_activity → created_at → now</span>——保证<strong>刚建的新技能不会立刻把自己归档</strong>。整段<strong>没有一次 LLM 调用</strong>，纯靠遥测时间戳（第 9 章的 skill_usage 喂数据），既便宜又可预测。</p>

<h2>辅助模型隔离：fork 一个独立 agent</h2>
<p>除了确定性降级，curator 还能（可选）跑一次 LLM「合并」pass——把零散技能并成「伞形」大技能。这一步用一个<strong>完全独立 fork 的 AIAgent</strong>，跑在辅助模型上：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/curator.py</span><span class="ln">1826-1845 · 简化</span></div>
  <pre>review_agent = AIAgent(
    model=_model_name, provider=_resolved_provider, ...,
    max_iterations=9999,           <span class="cm"># umbrella 扫描可能 50-100 次调用</span>
    quiet_mode=<span class="kw">True</span>,
    platform=<span class="st">"curator"</span>,           <span class="cm"># 独立 platform，独立 prompt cache</span>
    skip_context_files=<span class="kw">True</span>,
    skip_memory=<span class="kw">True</span>,
)
review_agent._memory_nudge_interval = 0    <span class="cm"># 禁止递归 nudge</span>
review_agent._skill_nudge_interval = 0     <span class="cm"># curator 绝不能再 spawn review</span></pre>
</div>
<p>注意几处关键设定：<span class="mono">platform="curator"</span> 让它有<strong>独立的 prompt 缓存</strong>，不与主对话共享；<span class="mono">skip_context_files</span> / <span class="mono">skip_memory</span> 让它<strong>不加载</strong>主 session 的上下文与记忆；两个 <span class="mono">nudge_interval = 0</span> <strong>禁止递归</strong>——curator 绝不能再触发自己的 review（否则无限套娃）。它的 stdout/stderr 还被重定向到 <span class="mono">/dev/null</span>，连终端噪声都不漏。更重要的是：这次 LLM 合并 pass <strong>默认是关闭</strong>的（opt-in）——因为它每跑一次都烧辅助模型 token，确定性降级才是常态、始终在跑。</p>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「自我维护而不破坏」</div>
  <div class="collab-sub">① 组件清单（★本章核心，其余跨章节配合）</div>
  本章核心：<strong>maybe_run_curator</strong>（inactivity 门控触发）、<strong>apply_automatic_transitions</strong>（确定性状态机）、<strong>forked review AIAgent</strong>（platform=curator 的辅助模型隔离）、<strong>archive/restore</strong>（可恢复归档）。跨章节配合：curator <strong>只园丁 background review fork 创建</strong>的 agent-skill（第 9 章产权门控）；forked agent 用<strong>独立 prompt cache</strong>、不碰主对话（第 6 章缓存 + 与第 9 章 fork 同源的「学习在别处」机制）；降级靠 <strong>skill_usage 遥测</strong>时间戳（第 9 章的 use/view/patch 计数喂回这里）；辅助模型走<strong>独立 aux 槽</strong>、与主 runtime 隔离。
  <div class="collab-sub">② 数据流时序</div>
  agent 空闲 + 距上次运行超过 interval_hours → <span class="mono">maybe_run_curator</span> → <span class="mono">apply_automatic_transitions</span>（读 skill_usage 时间戳，确定性降级，pinned 跳过）→ 持久化 .curator_state →（仅当 opt-in consolidate 开）fork 辅助模型 review agent 做 umbrella 合并 → 全程<strong>主对话 / 缓存零改动</strong>，最坏结果只是把技能搬进可恢复的 <span class="mono">.archive/</span>。
  <div class="collab-sub">③ 关键点</div>
  「自我进化」需要「自我维护」兜底，否则技能库会无限膨胀（误差累积）。但维护本身必须<strong>零破坏</strong>：永不删（只归档）、不碰主缓存（fork 独立 session）、pinned 豁免、LLM 合并 opt-in 省成本——每一条都在「主动维护」与「绝不伤害用户资产/性能」之间划线。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线：<strong>自我维护但永不破坏</strong>（数据安全 + 辅助模型隔离）。它治两条 LLM 固有约束：
  <p style="margin:.5rem 0 0"><span class="badge constraint">F·误差累积</span>——不加约束的自动学习会让技能库无限膨胀、互相污染；curator 用确定性状态机<strong>持续修剪</strong>，把熵控制住；
  <span class="badge constraint">G·运维</span>——它是一套<strong>后台运维系统</strong>：inactivity 触发、状态持久化、可恢复归档、备份/回滚。两者都服务「缓存神圣」（第 6 章）：维护跑在 forked 辅助 agent 里、<strong>独立 prompt cache</strong>。反模式：让 curator <strong>删除</strong>技能、或<strong>在主 session 里</strong>跑维护——前者毁掉用户资产，后者击穿缓存。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>四条不变量</strong>：只碰 agent 创建 / 永不删只归档（可恢复）/ pinned 豁免 / 不碰主缓存。</li>
    <li><strong>inactivity 触发</strong>：非 cron daemon——agent 空闲 + 距上次超过 interval_hours 才由 <span class="mono">maybe_run_curator</span> 跑。</li>
    <li><strong>确定性状态机</strong>：<span class="mono">active→stale→archived</span>（30/90 天）+ 复活，纯看活动时间戳、<strong>零 LLM</strong>。</li>
    <li><strong>辅助模型隔离</strong>：forked AIAgent <span class="mono">platform="curator"</span>、独立 cache、skip_context/memory、nudge=0 防递归。</li>
    <li><strong>LLM 合并 opt-in</strong>：烧 token 的 umbrella 合并默认关；确定性降级始终在跑。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">
In ch.9, the background review keeps <strong>creating</strong> new skills. A problem follows: won't the skill library grow into a mess, stuffed with one-off skills used exactly once? That's what the <strong>Curator</strong> (the skill gardener) solves — it periodically patrols agent-created skills in the background and auto-demotes / archives the <strong>long-unused</strong> ones. But it has an iron rule: <strong>archive only, never delete</strong>, and the <strong>whole process never touches the main conversation's prompt cache</strong>. This chapter is also a model of "data safety + auxiliary-model isolation."
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · a librarian + a recoverable holding stack</div>
  Picture the skill library as a real library. The <strong>librarian</strong> (curator) does a round every so often, moving books <strong>nobody has borrowed in a while</strong> to a "holding area" (stale), and after even longer into the <strong>basement stacks</strong> (archived). But he <strong>never burns books</strong> — anything in the basement can be retrieved. Books a reader has <strong>pinned</strong> stay on the shelf, untouched by the patrol. Crucially, the librarian works in <strong>a separate office</strong> (a forked agent), never interrupting you reading in the main hall (the main conversation).
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture · self-maintaining, yet never destructive</div>
  The Curator's design is captured in one phrase: <strong>self-maintaining, yet never destructive</strong>. It <strong>only touches skills auto-created by the background review fork</strong> (marked <span class="mono">created_by=agent</span>) — your <strong>hand-made</strong> ones (never marked), hub-installed, and protected built-ins are off-limits; it <strong>never deletes</strong> — the most aggressive move is archiving (recoverable); <strong>pinned skills bypass</strong> all auto-transitions; and it runs on the <strong>auxiliary model</strong> in a separate session, <strong>never touching the main conversation's prompt cache</strong>. These four invariants are exactly the safety boundary between "let the agent evolve freely" and "data is never lost, the cache is never broken."
</div>

<h2>Four invariants: the safety boundary written in the docstring</h2>
<p>These constraints aren't a verbal agreement — they're <strong>strict invariants</strong> pinned in the module docstring:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/curator.py</span><span class="ln">15-19 · excerpt</span></div>
  <pre><span class="cm">Strict invariants:</span>
<span class="cm">  - Only touches agent-created skills (see tools/skill_usage.is_agent_created)</span>
<span class="cm">  - Never auto-deletes — only archives. Archive is recoverable.</span>
<span class="cm">  - Pinned skills bypass all auto-transitions</span>
<span class="cm">  - Uses the auxiliary client; never touches the main session's prompt cache</span></pre>
</div>
<p>One by one: ① here 'agent-created' means skills <strong>auto-created by the background review fork</strong> (provenance gating, ch.9; <span class="mono">created_by=agent</span>) — your <strong>hand-made</strong> ones are never marked, so they're <strong>always safe</strong>; hub-installed skills are unconditionally exempt, and bundled built-ins can at most be <strong>archived</strong> by default (<span class="mono">prune_builtins</span>), never deleted or modified; ② it <strong>never deletes, only archives</strong>, and archives are <strong>recoverable</strong> (moved into <span class="mono">.archive/</span>, restorable anytime); ③ <strong>pinned skills bypass</strong> every auto-transition; ④ it <strong>uses the auxiliary client and never touches the main session's prompt cache</strong>. That last one binds the curator directly to "the cache is sacred" (ch.6).</p>

<h2>A deterministic state machine: active → stale → archived</h2>
<p>The core of demotion is a <strong>purely deterministic</strong> state machine — calling no LLM, looking only at a skill's "latest real activity" timestamp:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/curator.py</span><span class="ln">276-331 · simplified</span></div>
  <pre><span class="kw">for</span> row <span class="kw">in</span> skill_usage.agent_created_report():
    <span class="kw">if</span> row.get(<span class="st">"pinned"</span>):
        <span class="kw">continue</span>                                  <span class="cm"># pinned bypasses every transition</span>
    <span class="cm"># activity anchor: last_activity -> created_at -> now (new skills don't self-archive)</span>
    anchor = last_activity <span class="kw">or</span> created_at <span class="kw">or</span> now

    <span class="kw">if</span> anchor &lt;= archive_cutoff <span class="kw">and</span> current != ARCHIVED:
        archive_skill(name)                       <span class="cm"># 90 days idle -> archive (recoverable)</span>
    <span class="kw">elif</span> anchor &lt;= stale_cutoff <span class="kw">and</span> current == ACTIVE:
        set_state(name, STALE)                    <span class="cm"># 30 days idle -> mark stale</span>
    <span class="kw">elif</span> anchor &gt; stale_cutoff <span class="kw">and</span> current == STALE:
        set_state(name, ACTIVE)                   <span class="cm"># used again -> reactivate</span></pre>
</div>
<p>All three transitions hinge on <span class="mono">anchor</span> (latest activity): 30 days idle is <span class="mono">active → stale</span>, 90 days idle is <span class="mono">stale → archived</span>, and any fresh use is <span class="mono">stale → active</span>. Note the anchor fallback chain <span class="mono">last_activity → created_at → now</span> — guaranteeing a <strong>freshly-built skill won't immediately archive itself</strong>. The whole pass makes <strong>not a single LLM call</strong>, running purely on telemetry timestamps (fed by ch.9's skill_usage), making it both cheap and predictable.</p>

<h2>Auxiliary-model isolation: fork a separate agent</h2>
<p>Beyond deterministic demotion, the curator can (optionally) run one LLM "consolidation" pass — merging scattered skills into "umbrella" skills. That step uses a <strong>fully separate forked AIAgent</strong>, running on the auxiliary model:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/curator.py</span><span class="ln">1826-1845 · simplified</span></div>
  <pre>review_agent = AIAgent(
    model=_model_name, provider=_resolved_provider, ...,
    max_iterations=9999,           <span class="cm"># an umbrella sweep may take 50-100 calls</span>
    quiet_mode=<span class="kw">True</span>,
    platform=<span class="st">"curator"</span>,           <span class="cm"># separate platform, separate prompt cache</span>
    skip_context_files=<span class="kw">True</span>,
    skip_memory=<span class="kw">True</span>,
)
review_agent._memory_nudge_interval = 0    <span class="cm"># disable recursive nudges</span>
review_agent._skill_nudge_interval = 0     <span class="cm"># the curator must never spawn its own review</span></pre>
</div>
<p>Note the key settings: <span class="mono">platform="curator"</span> gives it a <strong>separate prompt cache</strong>, not shared with the main conversation; <span class="mono">skip_context_files</span> / <span class="mono">skip_memory</span> mean it <strong>doesn't load</strong> the main session's context or memory; the two <span class="mono">nudge_interval = 0</span> <strong>forbid recursion</strong> — the curator must never trigger its own review (or infinite nesting). Its stdout/stderr are even redirected to <span class="mono">/dev/null</span>, so not even terminal noise leaks. More importantly: this LLM consolidation pass is <strong>off by default</strong> (opt-in) — because each run burns auxiliary-model tokens; deterministic demotion is the always-on norm.</p>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "self-maintaining yet never destructive"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: <strong>maybe_run_curator</strong> (inactivity-gated trigger), <strong>apply_automatic_transitions</strong> (the deterministic state machine), the <strong>forked review AIAgent</strong> (platform=curator auxiliary-model isolation), <strong>archive/restore</strong> (recoverable archiving). Cross-chapter teamwork: the curator <strong>only gardens skills created by the background review fork</strong> (ch.9 provenance gating); the forked agent uses a <strong>separate prompt cache</strong> and doesn't touch the main conversation (ch.6 caching + the same "learning elsewhere" mechanism as ch.9's fork); demotion runs on <strong>skill_usage telemetry</strong> timestamps (ch.9's use/view/patch counts feed back here); the auxiliary model uses a <strong>separate aux slot</strong>, isolated from the main runtime.
  <div class="collab-sub">② Data-flow timing</div>
  agent idle + longer than interval_hours since the last run → <span class="mono">maybe_run_curator</span> → <span class="mono">apply_automatic_transitions</span> (reads skill_usage timestamps, deterministic demotion, pinned skipped) → persist .curator_state → (only if opt-in consolidate is on) fork an auxiliary-model review agent for umbrella merging → throughout, <strong>main conversation / cache unchanged</strong>, the worst outcome being a move into the recoverable <span class="mono">.archive/</span>.
  <div class="collab-sub">③ The key point</div>
  "Self-improvement" needs "self-maintenance" as a backstop, or the skill library grows without bound (error accumulation). But maintenance itself must be <strong>zero-harm</strong>: never delete (only archive), never touch the main cache (fork a separate session), pinned bypass, LLM consolidation opt-in to save cost — each draws a line between "actively maintain" and "never harm the user's assets/performance."
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>self-maintaining yet never destructive</strong> (data safety + auxiliary-model isolation). It treats two inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">F·error accumulation</span> — unconstrained auto-learning lets the skill library balloon and cross-pollute; the curator <strong>continuously prunes</strong> with a deterministic state machine, keeping entropy in check;
  <span class="badge constraint">G·ops</span> — it's a <strong>background ops system</strong>: inactivity-triggered, state persisted, recoverable archiving, backup/rollback. Both serve "the cache is sacred" (ch.6): maintenance runs in a forked auxiliary agent with a <strong>separate prompt cache</strong>. The anti-pattern: letting the curator <strong>delete</strong> skills, or running maintenance <strong>inside the main session</strong> — the former destroys the user's assets, the latter shatters the cache.</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Four invariants</strong>: only agent-created / never delete, only archive (recoverable) / pinned bypass / never touch the main cache.</li>
    <li><strong>Inactivity-triggered</strong>: not a cron daemon — only when the agent is idle and longer than interval_hours since the last run does <span class="mono">maybe_run_curator</span> run.</li>
    <li><strong>Deterministic state machine</strong>: <span class="mono">active→stale→archived</span> (30/90 days) + reactivation, purely on activity timestamps, <strong>zero LLM</strong>.</li>
    <li><strong>Auxiliary-model isolation</strong>: a forked AIAgent with <span class="mono">platform="curator"</span>, separate cache, skip_context/memory, nudge=0 to prevent recursion.</li>
    <li><strong>LLM consolidation opt-in</strong>: the token-burning umbrella merge is off by default; deterministic demotion is always running.</li>
  </ul>
</div>
""",
}
