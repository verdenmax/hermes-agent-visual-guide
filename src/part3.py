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
