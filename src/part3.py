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

LESSON_11 = {
    "zh": r"""
<p class="lead">
记忆让 Hermes 跨会话记住「<strong>你是谁、你偏好什么</strong>」：<span class="mono">MEMORY.md</span> 是 agent 的个人笔记，<span class="mono">USER.md</span> 是它对你的画像。但这里藏着一个尖锐矛盾——记忆<strong>随时在写入</strong>（你刚说的偏好、agent 刚学的教训），而 system prompt 又<strong>绝不能在会话中途改动</strong>（第 6 章）。Hermes 用<strong>两条精心设计的注入路径</strong>同时满足「写入随时落盘」和「缓存绝不破」：<strong>冻结快照</strong> + <strong>只贴当前用户消息的副本</strong>。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 助理的备忘录 + 拍立得快照</div>
  想象一位助理，桌上有两本本子：<strong>MEMORY.md</strong> 记「这个项目用什么部署、踩过什么坑」，<strong>USER.md</strong> 记「这位老板喜欢简洁、讨厌啰嗦」。每天上班，他<strong>拍一张快照</strong>（冻结快照）贴在工位最显眼处，<strong>一整天都看这张</strong>——哪怕中途往本子里又记了新东西，<strong>那张快照也不换</strong>，免得自己分心重读。需要临时翻某条旧记录时，他不去改工位上的快照，而是<strong>抄一张便签</strong>夹在当前这页（贴副本）。两条路都<strong>绝不动那张神圣的快照</strong>。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 声明性记忆，写 durable，注入守缓存</div>
  记忆是<strong>声明性</strong>的（「是谁 / 是什么状态」），区别于第 9 章的技能（程序性「怎么做」）。<span class="mono">MEMORY.md</span>（agent 笔记，约 2200 字符上限）和 <span class="mono">USER.md</span>（用户画像，约 1375 字符上限）存在 <span class="mono">$HERMES_HOME/memories/</span>。核心矛盾的解法是<strong>写读分离</strong>：写入随时落磁盘（durable）；但<strong>进 system prompt 用的是会话开始冻结的快照</strong>，<strong>实时取回的记忆只贴到当前用户消息的 API 副本上</strong>。两条注入路径都绕开「会话中途改 system prompt」——这就是记忆守住「缓存神圣」的全部手法。
</div>

<h2>第一条路：冻结快照进 system prompt</h2>
<p>记忆要进 system prompt 的 <span class="mono">volatile</span> 层（第 6 章三层结构的最底层）。但如果直接注入<strong>实时</strong>记忆，你每写一条记忆就改了 system prompt、击穿缓存。Hermes 的解法是——注入的<strong>永远是会话开始那一刻的冻结快照</strong>：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/memory_tool.py</span><span class="ln">567-578 · 节选</span></div>
  <pre><span class="kw">def</span> <span class="fn">format_for_system_prompt</span>(self, target):
    <span class="cm">&quot;&quot;&quot;Return the frozen snapshot for system prompt injection.</span>
<span class="cm">    This returns the state captured at load_from_disk() time, NOT the</span>
<span class="cm">    live state. Mid-session writes do not affect this. This keeps the</span>
<span class="cm">    system prompt stable across all turns, preserving the prefix cache.&quot;&quot;&quot;</span>
    block = self._system_prompt_snapshot.get(target, <span class="st">""</span>)
    <span class="kw">return</span> block <span class="kw">if</span> block <span class="kw">else</span> <span class="kw">None</span></pre>
</div>
<p>docstring 把意图钉死：<span class="inline">NOT the live state. Mid-session writes do not affect this. This keeps the system prompt stable across all turns, preserving the prefix cache</span>。<span class="mono">_system_prompt_snapshot</span> 是会话开始 <span class="mono">load_from_disk()</span> 时拍下的，之后无论你用 <span class="mono">memory</span> 工具写入多少条，<strong>这个快照都不变</strong> → system prompt 逐字节稳定 → 前缀缓存命中。快照只在<strong>下个会话开始</strong>、或<strong>上下文压缩</strong>边界（第 6 章唯一重建时机）才刷新。</p>

<h2>第二条路：实时取回只贴当前用户消息的副本</h2>
<p>那会话<strong>中途</strong>想起一条旧记忆怎么办？（比如外部 provider 取回的相关上下文。）答案是：<strong>不进 system prompt，只贴到当前这条用户消息的「发送副本」上</strong>：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/conversation_loop.py</span><span class="ln">738-758 · 简化</span></div>
  <pre>api_messages = []
<span class="kw">for</span> idx, msg <span class="kw">in</span> <span class="fn">enumerate</span>(messages):
    api_msg = msg.copy()                       <span class="cm"># 副本！原 messages 永不被改</span>
    <span class="cm"># 取回的记忆只注入到当前轮的 user 消息副本</span>
    <span class="kw">if</span> idx == current_turn_user_idx <span class="kw">and</span> msg.get(<span class="st">"role"</span>) == <span class="st">"user"</span>:
        <span class="kw">if</span> _ext_prefetch_cache:
            fenced = build_memory_context_block(_ext_prefetch_cache)  <span class="cm"># 加 &lt;memory-context&gt; 围栏</span>
            _base = api_msg.get(<span class="st">"content"</span>, <span class="st">""</span>)
            api_msg[<span class="st">"content"</span>] = _base + <span class="st">"\n\n"</span> + fenced
    api_messages.append(api_msg)</pre>
</div>
<p>关键是第三行 <span class="mono">api_msg = msg.copy()</span>——注入只发生在<strong>发往 API 的副本</strong>上，源注释说得很直白：<span class="inline">the original message in `messages` is never mutated, so nothing leaks into session persistence</span>。取回内容被 <span class="mono">build_memory_context_block</span> 包进 <span class="mono">&lt;memory-context&gt;</span> 围栏（标明「这是召回的参考资料，不是新的用户指令」），<strong>追加到当前用户消息末尾</strong>。于是：之前所有轮次字节不变（缓存前缀完好），system prompt 不变，原始 <span class="mono">messages</span> 不被污染、不写进持久化。</p>

<h2>memory nudge：和技能 nudge 同构</h2>
<p>记忆也有 nudge——每隔若干轮提醒 agent「该不该存条记忆」。它和第 9 章的技能 nudge<strong>完全同构</strong>：只置一个布尔，<strong>绝不</strong>往主对话注入文字：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/turn_context.py</span><span class="ln">249-260 · 节选</span></div>
  <pre><span class="cm"># Preserve the original user message (no nudge injection).</span>
<span class="cm"># Track memory nudge trigger (turn-based, checked here).</span>
should_review_memory = <span class="kw">False</span>
<span class="kw">if</span> (agent._memory_nudge_interval &gt; 0
        <span class="kw">and</span> <span class="st">"memory"</span> <span class="kw">in</span> agent.valid_tool_names
        <span class="kw">and</span> agent._memory_store):
    agent._turns_since_memory += 1
    <span class="kw">if</span> agent._turns_since_memory &gt;= agent._memory_nudge_interval:
        should_review_memory = <span class="kw">True</span>            <span class="cm"># 只置布尔，turn 后 fork review 消费</span>
        agent._turns_since_memory = 0</pre>
</div>
<p>第一行注释 <span class="inline">Preserve the original user message (no nudge injection)</span> 就是纲领：nudge <strong>什么都不注入</strong>，只把 <span class="mono">should_review_memory</span> 置 <span class="kw">True</span>；和技能 nudge 一样，真正的 review 在响应交付后、由 <span class="mono">turn_finalizer</span> fork 同一个后台 agent 来做（第 9 章）。记忆和技能<strong>共用</strong>这套「响应后 fork、写在别处」的机制。</p>

<h2>可插拔：MemoryProvider 与 Honcho</h2>
<p>内置的 <span class="mono">MEMORY.md/USER.md</span> 之外，Hermes 还支持<strong>外部记忆 provider</strong>（Honcho、Mem0、Supermemory…）。它们实现 <span class="mono">MemoryProvider</span> ABC，由 <span class="mono">MemoryManager</span> 编排，且<strong>同一时刻只允许一个外部 provider</strong>（防工具 schema 膨胀）。关键是：外部 provider 的取回也走<strong>第二条路</strong>——经 <span class="mono">prefetch</span> 贴到当前用户消息副本，<strong>从不</strong>污染 system prompt。像 Honcho 这种「辩证用户建模」provider，更是把所有 live 上下文都注入 user 消息、绝不碰前缀。</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc"><strong>写入（durable）</strong>：memory 工具随时把条目落进 MEMORY.md / USER.md 磁盘 + live 状态</span></div>
  <div class="step"><span class="num">2</span><span class="sc"><strong>注入路径①</strong>：会话开始 load_from_disk 拍<strong>冻结快照</strong> → 进 system prompt volatile 层 → 整会话字节稳定</span></div>
  <div class="step"><span class="num">3</span><span class="sc"><strong>注入路径②</strong>：实时 prefetch → build_memory_context_block 围栏 → 只贴<strong>当前 user 消息的 API 副本</strong>（原 messages 不改）</span></div>
  <div class="step"><span class="num">4</span><span class="sc"><strong>nudge</strong>：每隔 N 轮置 should_review_memory，<strong>不注入主对话</strong>，响应后 fork review 落盘</span></div>
  <div class="step"><span class="num">5</span><span class="sc">两条注入路径都<strong>绕开「中途改 system prompt」</strong> → 缓存全程不破</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「记忆而不破缓存」</div>
  <div class="collab-sub">① 组件清单（★本章核心，其余跨章节配合）</div>
  本章核心：<strong>MemoryStore</strong>（MEMORY.md/USER.md + 冻结快照）、<strong>format_for_system_prompt</strong>（注入路径①）、<strong>prefetch 副本注入</strong>（注入路径②）、<strong>memory nudge</strong>、<strong>MemoryManager</strong>（外部 provider 编排）。跨章节配合：冻结快照进 <strong>volatile 层</strong>、只在压缩边界刷新（第 6 章缓存）；prefetch 副本注入<strong>不改前缀</strong>（第 6 章）；memory nudge 与 skill nudge <strong>同构</strong>、共用 turn_finalizer 的「响应后 fork」（第 9 章）；记忆 vs 技能＝声明性 vs 程序性（第 9 章边界）。
  <div class="collab-sub">② 数据流时序</div>
  会话开始 load_from_disk → 冻结快照进 system prompt（路径①，整会话不变）；每轮 memory 工具写入随时落盘（durable，但不动快照）；想起旧记忆 → prefetch → 贴当前 user 消息副本（路径②，原 messages 不改）；每 N 轮 nudge 置布尔 → 响应后 fork review 落盘。压缩边界才刷新快照。
  <div class="collab-sub">③ 关键点</div>
  「写入随时、注入守缓存」靠<strong>读写分离</strong>：写发生在磁盘 + live 状态；读（注入）要么用<strong>会话开始的冻结快照</strong>，要么<strong>只贴当前用户消息的副本</strong>。两条路<strong>都不碰</strong>会话中途的 system prompt——这正是记忆对「缓存神圣」的贡献。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线：<strong>冻结快照 + 只贴当前用户消息副本</strong>，两条注入路径都绕开「会话中途改 system prompt」＝守缓存。它治三条 LLM 固有约束：
  <p style="margin:.5rem 0 0"><span class="badge constraint">B·无状态</span>——模型跨会话什么都记不住，靠 MEMORY/USER 把「你是谁、你偏好」沉淀成<strong>持久记忆</strong>；
  <span class="badge constraint">A·中间遗失</span>——记忆<strong>按需取回</strong>（prefetch）而非全塞进上下文，紧凑高信号；
  <span class="badge constraint">D·指令=数据</span>——取回内容包进 <span class="mono">&lt;memory-context&gt;</span> 围栏、标明「是参考资料非指令」，快照构建时还做注入扫描。反模式：把实时记忆<strong>直接重载进 system prompt</strong>——每写一条就击穿一次缓存。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>声明性记忆</strong>：<span class="mono">MEMORY.md</span>（agent 笔记）+ <span class="mono">USER.md</span>（用户画像），区别于第 9 章技能的程序性「怎么做」。</li>
    <li><strong>冻结快照（路径①）</strong>：<span class="mono">format_for_system_prompt</span> 返回会话开始拍的快照、非 live；中途写入不影响，守住前缀缓存。</li>
    <li><strong>副本注入（路径②）</strong>：prefetch 取回经 <span class="mono">&lt;memory-context&gt;</span> 围栏只贴<strong>当前 user 消息的 API 副本</strong>，原 messages 不改、不入持久化。</li>
    <li><strong>memory nudge</strong>：和 skill nudge 同构，只置布尔、不注入主对话，响应后 fork review（第 9 章）。</li>
    <li><strong>可插拔 provider</strong>：MemoryProvider ABC + MemoryManager，同时只一个外部 provider；取回同样只走副本路径。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">
Memory lets Hermes remember across sessions "<strong>who you are and what you prefer</strong>": <span class="mono">MEMORY.md</span> is the agent's personal notebook, <span class="mono">USER.md</span> its profile of you. But a sharp tension hides here — memory is <strong>written at any time</strong> (the preference you just stated, the lesson the agent just learned), yet the system prompt <strong>must never change mid-session</strong> (ch.6). Hermes satisfies both "write anytime" and "never break the cache" with <strong>two carefully designed injection paths</strong>: a <strong>frozen snapshot</strong> + <strong>appending only to the current user message's copy</strong>.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · an assistant's notebooks + a Polaroid snapshot</div>
  Picture an assistant with two notebooks on the desk: <strong>MEMORY.md</strong> records "what this project deploys with, what pitfalls we hit," <strong>USER.md</strong> records "this boss likes brevity, hates rambling." Each morning he <strong>takes a snapshot</strong> (the frozen snapshot) and pins it where it's most visible, and <strong>looks at that all day</strong> — even if he jots new things into the notebooks midday, <strong>he doesn't swap the snapshot</strong>, to avoid distracting himself by re-reading. When he needs an old record temporarily, he doesn't alter the pinned snapshot — he <strong>copies a sticky note</strong> onto the current page (appending to a copy). Both paths <strong>never touch that sacred snapshot</strong>.
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture · declarative memory, written durably, injected cache-safe</div>
  Memory is <strong>declarative</strong> ("who / what-state"), distinct from ch.9's procedural skills ("how to"). <span class="mono">MEMORY.md</span> (the agent's notes, ~2200-char cap) and <span class="mono">USER.md</span> (the user profile, ~1375-char cap) live under <span class="mono">$HERMES_HOME/memories/</span>. The fix for the core tension is <strong>read/write separation</strong>: writes hit disk anytime (durable); but <strong>what enters the system prompt is the snapshot frozen at session start</strong>, and <strong>real-time recalled memory is appended only to the current user message's API copy</strong>. Both injection paths bypass "changing the system prompt mid-session" — that's the whole way memory honors "the cache is sacred."
</div>

<h2>Path one: a frozen snapshot enters the system prompt</h2>
<p>Memory enters the system prompt's <span class="mono">volatile</span> tier (the lowest of ch.6's three tiers). But injecting <strong>live</strong> memory directly would change the system prompt with every memory you write, shattering the cache. Hermes's fix — what's injected is <strong>always the snapshot frozen at session start</strong>:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/memory_tool.py</span><span class="ln">567-578 · excerpt</span></div>
  <pre><span class="kw">def</span> <span class="fn">format_for_system_prompt</span>(self, target):
    <span class="cm">&quot;&quot;&quot;Return the frozen snapshot for system prompt injection.</span>
<span class="cm">    This returns the state captured at load_from_disk() time, NOT the</span>
<span class="cm">    live state. Mid-session writes do not affect this. This keeps the</span>
<span class="cm">    system prompt stable across all turns, preserving the prefix cache.&quot;&quot;&quot;</span>
    block = self._system_prompt_snapshot.get(target, <span class="st">""</span>)
    <span class="kw">return</span> block <span class="kw">if</span> block <span class="kw">else</span> <span class="kw">None</span></pre>
</div>
<p>The docstring pins the intent: <span class="inline">NOT the live state. Mid-session writes do not affect this. This keeps the system prompt stable across all turns, preserving the prefix cache</span>. <span class="mono">_system_prompt_snapshot</span> is captured at session-start <span class="mono">load_from_disk()</span>; no matter how many entries you write via the <span class="mono">memory</span> tool afterward, <strong>this snapshot doesn't change</strong> → the system prompt stays byte-stable → the prefix cache holds. The snapshot refreshes only at <strong>the next session start</strong>, or at a <strong>context-compression</strong> boundary (ch.6's sole rebuild moment).</p>

<h2>Path two: real-time recall appends only to the current user message's copy</h2>
<p>So what about recalling an old memory <strong>mid-session</strong>? (e.g. relevant context fetched by an external provider.) The answer: <strong>it doesn't enter the system prompt — it's appended only to the "send copy" of the current user message</strong>:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/conversation_loop.py</span><span class="ln">738-758 · simplified</span></div>
  <pre>api_messages = []
<span class="kw">for</span> idx, msg <span class="kw">in</span> <span class="fn">enumerate</span>(messages):
    api_msg = msg.copy()                       <span class="cm"># a copy! the original messages are never changed</span>
    <span class="cm"># recalled memory is injected only into the current user message copy</span>
    <span class="kw">if</span> idx == current_turn_user_idx <span class="kw">and</span> msg.get(<span class="st">"role"</span>) == <span class="st">"user"</span>:
        <span class="kw">if</span> _ext_prefetch_cache:
            fenced = build_memory_context_block(_ext_prefetch_cache)  <span class="cm"># wraps in &lt;memory-context&gt;</span>
            api_msg[<span class="st">"content"</span>] = _base + <span class="st">"\n\n"</span> + fenced
    api_messages.append(api_msg)</pre>
</div>
<p>The key is line three, <span class="mono">api_msg = msg.copy()</span> — injection happens only on the <strong>copy sent to the API</strong>, as the source comment states plainly: <span class="inline">the original message in `messages` is never mutated, so nothing leaks into session persistence</span>. The recalled content is wrapped by <span class="mono">build_memory_context_block</span> in a <span class="mono">&lt;memory-context&gt;</span> fence (marking it "recalled reference data, not a new user instruction") and <strong>appended to the end of the current user message</strong>. So: all prior turns stay byte-identical (the cache prefix is intact), the system prompt is unchanged, and the original <span class="mono">messages</span> aren't polluted or persisted.</p>

<h2>memory nudge: isomorphic to the skill nudge</h2>
<p>Memory also has a nudge — every so many turns it reminds the agent "should I save a memory?" It is <strong>completely isomorphic</strong> to ch.9's skill nudge: it sets a single boolean and <strong>injects no text</strong> into the main conversation:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/turn_context.py</span><span class="ln">249-260 · excerpt</span></div>
  <pre><span class="cm"># Preserve the original user message (no nudge injection).</span>
<span class="cm"># Track memory nudge trigger (turn-based, checked here).</span>
should_review_memory = <span class="kw">False</span>
<span class="kw">if</span> (agent._memory_nudge_interval &gt; 0
        <span class="kw">and</span> <span class="st">"memory"</span> <span class="kw">in</span> agent.valid_tool_names
        <span class="kw">and</span> agent._memory_store):
    agent._turns_since_memory += 1
    <span class="kw">if</span> agent._turns_since_memory &gt;= agent._memory_nudge_interval:
        should_review_memory = <span class="kw">True</span>            <span class="cm"># only a boolean; a forked review consumes it after the turn</span>
        agent._turns_since_memory = 0</pre>
</div>
<p>The first-line comment <span class="inline">Preserve the original user message (no nudge injection)</span> is the whole charter: the nudge <strong>injects nothing</strong>, just sets <span class="mono">should_review_memory</span> to <span class="kw">True</span>; as with the skill nudge, the real review happens after the response, forked by <span class="mono">turn_finalizer</span> as the same background agent (ch.9). Memory and skills <strong>share</strong> this "fork after the response, write elsewhere" mechanism.</p>

<h2>Pluggable: MemoryProvider and Honcho</h2>
<p>Beyond the built-in <span class="mono">MEMORY.md/USER.md</span>, Hermes supports <strong>external memory providers</strong> (Honcho, Mem0, Supermemory…). They implement the <span class="mono">MemoryProvider</span> ABC, orchestrated by <span class="mono">MemoryManager</span>, with <strong>only one external provider allowed at a time</strong> (to prevent tool-schema bloat). The key: an external provider's recall also takes <strong>path two</strong> — via <span class="mono">prefetch</span>, appended to the current user message copy, <strong>never</strong> polluting the system prompt. A "dialectic user-modeling" provider like Honcho injects all its live context into user messages, never touching the prefix.</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc"><strong>Write (durable)</strong>: the memory tool drops entries into MEMORY.md / USER.md disk + live state anytime</span></div>
  <div class="step"><span class="num">2</span><span class="sc"><strong>Injection path ①</strong>: at session start load_from_disk takes a <strong>frozen snapshot</strong> → enters the system prompt volatile tier → byte-stable all session</span></div>
  <div class="step"><span class="num">3</span><span class="sc"><strong>Injection path ②</strong>: real-time prefetch → build_memory_context_block fence → appended only to the <strong>current user message's API copy</strong> (original messages unchanged)</span></div>
  <div class="step"><span class="num">4</span><span class="sc"><strong>Nudge</strong>: every N turns sets should_review_memory, <strong>no injection into the main conversation</strong>, forked review writes after the response</span></div>
  <div class="step"><span class="num">5</span><span class="sc">both injection paths <strong>bypass "changing the system prompt mid-session"</strong> → the cache never breaks</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "remember without breaking the cache"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: <strong>MemoryStore</strong> (MEMORY.md/USER.md + the frozen snapshot), <strong>format_for_system_prompt</strong> (injection path ①), <strong>prefetch copy-injection</strong> (injection path ②), the <strong>memory nudge</strong>, <strong>MemoryManager</strong> (external-provider orchestration). Cross-chapter teamwork: the frozen snapshot enters the <strong>volatile tier</strong> and refreshes only at a compression boundary (ch.6 caching); prefetch copy-injection <strong>doesn't change the prefix</strong> (ch.6); the memory nudge is <strong>isomorphic</strong> to the skill nudge, sharing turn_finalizer's "fork after the response" (ch.9); memory vs skill = declarative vs procedural (ch.9's boundary).
  <div class="collab-sub">② Data-flow timing</div>
  session start load_from_disk → frozen snapshot enters the system prompt (path ①, unchanged all session); each turn the memory tool writes to disk anytime (durable, but the snapshot doesn't move); recalling an old memory → prefetch → appended to the current user message copy (path ②, original messages unchanged); every N turns the nudge sets a boolean → forked review writes after the response. The snapshot refreshes only at a compression boundary.
  <div class="collab-sub">③ The key point</div>
  "Write anytime, inject cache-safe" rests on <strong>read/write separation</strong>: writes happen on disk + live state; reads (injection) use either the <strong>session-start frozen snapshot</strong> or <strong>only the current user message's copy</strong>. Neither path <strong>touches</strong> the mid-session system prompt — that's memory's contribution to "the cache is sacred."
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>a frozen snapshot + appending only to the current user message's copy</strong> — both injection paths bypass "changing the system prompt mid-session" = guarding the cache. It treats three inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">B·stateless</span> — the model remembers nothing across sessions, so MEMORY/USER distill "who you are, what you prefer" into <strong>durable memory</strong>;
  <span class="badge constraint">A·lost-in-the-middle</span> — memory is <strong>recalled on demand</strong> (prefetch) rather than dumped wholesale, kept compact and high-signal;
  <span class="badge constraint">D·instr=data</span> — recalled content is wrapped in a <span class="mono">&lt;memory-context&gt;</span> fence marking it "reference data, not instruction," and the snapshot is injection-scanned at build time. The anti-pattern: reloading live memory <strong>directly into the system prompt</strong> — every write shatters the cache once.</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Declarative memory</strong>: <span class="mono">MEMORY.md</span> (agent notes) + <span class="mono">USER.md</span> (user profile), distinct from ch.9 skills' procedural "how-to."</li>
    <li><strong>Frozen snapshot (path ①)</strong>: <span class="mono">format_for_system_prompt</span> returns the session-start snapshot, not live; mid-session writes don't affect it, guarding the prefix cache.</li>
    <li><strong>Copy-injection (path ②)</strong>: prefetch recall, wrapped in a <span class="mono">&lt;memory-context&gt;</span> fence, is appended only to the <strong>current user message's API copy</strong>; original messages are unchanged and not persisted.</li>
    <li><strong>memory nudge</strong>: isomorphic to the skill nudge — sets a boolean, no injection into the main conversation, forked review after the response (ch.9).</li>
    <li><strong>Pluggable providers</strong>: MemoryProvider ABC + MemoryManager, one external provider at a time; its recall also takes only the copy path.</li>
  </ul>
</div>
""",
}

LESSON_12 = {
    "zh": r"""
<p class="lead">
你和 Hermes 聊过几百次，某天问它「我们<strong>以前</strong>讨论过的那个部署方案是什么来着？」——它能<strong>跨会话</strong>想起来。这就是跨会话搜索。但它有个反直觉的设计：<strong>零 LLM、零成本</strong>。它不调用任何模型去「理解」或「总结」，而是直接查一个本地 SQLite 的 <strong>FTS5 全文索引</strong>，把<strong>原始消息原文</strong>返回给 agent 自己读。而且召回结果<strong>不破坏 prompt 缓存</strong>。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 图书馆卡片目录</div>
  老式图书馆的<strong>卡片目录</strong>：每本书一上架，管理员就把它的关键词抄进卡片柜（写入即索引）。你要找书时，不需要请一位学者<strong>读完所有书再告诉你大意</strong>（那是 LLM 总结，又慢又贵）——你直接翻卡片柜，按相关性排好序，<strong>拿到书的原始页码和摘录</strong>，自己去读。Hermes 的跨会话搜索就是这个卡片柜：FTS5 索引在消息写入时<strong>同步建好</strong>，搜索时直接出原文，<strong>全程不惊动任何模型</strong>。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 写入即索引，原文召回，零 LLM</div>
  三件事拼成这条链：①<strong>写入即索引</strong>——每条消息 INSERT 进 SQLite，触发器<strong>同步</strong>把它喂进 FTS5 倒排索引（content + tool_name + tool_calls）；②<strong>FTS5 检索</strong>——搜索走 <span class="mono">MATCH</span> + BM25 相关性排序 + <span class="mono">snippet()</span> 高亮，CJK 还有 trigram 子串兜底；③<strong>原文 append</strong>——命中的<strong>原始消息</strong>作为 tool 结果消息追加到对话末尾，让 agent 自己阅读。<strong>没有一次 LLM 调用</strong>——这既省钱，又（因为只是 append tool 消息）<strong>不碰 system prompt、不破缓存</strong>。
</div>

<h2>写入即索引：AFTER INSERT 触发器</h2>
<p>不需要任何额外的「建索引」步骤——消息一写进 <span class="mono">messages</span> 表，SQLite 触发器就<strong>同步</strong>把它送进 FTS5：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">hermes_state.py</span><span class="ln">612-621 · 节选</span></div>
  <pre><span class="kw">CREATE VIRTUAL TABLE</span> messages_fts <span class="kw">USING</span> fts5(content);

<span class="kw">CREATE TRIGGER</span> messages_fts_insert <span class="kw">AFTER INSERT ON</span> messages <span class="kw">BEGIN</span>
    <span class="kw">INSERT INTO</span> messages_fts(rowid, content) <span class="kw">VALUES</span> (
        new.id,
        <span class="fn">COALESCE</span>(new.content, <span class="st">''</span>) || <span class="st">' '</span> ||
        <span class="fn">COALESCE</span>(new.tool_name, <span class="st">''</span>) || <span class="st">' '</span> ||
        <span class="fn">COALESCE</span>(new.tool_calls, <span class="st">''</span>)
    );
<span class="kw">END</span>;</pre>
</div>
<p>这里有两个巧思。其一，<span class="mono">rowid = new.id</span>——FTS 索引的行号就是 <span class="mono">messages.id</span>，命中后能直接 JOIN 回原始消息。其二，索引的不是单纯 content，而是 <span class="mono">content + tool_name + tool_calls</span> 拼接——所以连「某次调用了什么工具」也能被搜到。写入即索引意味着：<strong>无需任何离线建库</strong>，刚说完的话下一秒就可被检索。</p>

<h2>检索：FTS5 MATCH + BM25 + snippet</h2>
<p>搜索本身是一条纯 SQL，用足了 FTS5 的特性——全文匹配、相关性排序、高亮摘要：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">hermes_state.py</span><span class="ln">3532-3579 · 简化</span></div>
  <pre><span class="kw">SELECT</span> m.id, m.session_id, m.role,
       <span class="fn">snippet</span>(messages_fts, 0, <span class="st">'&gt;&gt;&gt;'</span>, <span class="st">'&lt;&lt;&lt;'</span>, <span class="st">'...'</span>, 40) <span class="kw">AS</span> snippet,
       m.content, m.timestamp, s.source
<span class="kw">FROM</span> messages_fts
<span class="kw">JOIN</span> messages m <span class="kw">ON</span> m.id = messages_fts.rowid    <span class="cm">-- rowid 直接 JOIN 回原消息</span>
<span class="kw">JOIN</span> sessions s <span class="kw">ON</span> s.id = m.session_id
<span class="kw">WHERE</span> messages_fts <span class="kw">MATCH</span> ?                    <span class="cm">-- 全文匹配</span>
<span class="kw">ORDER BY</span> rank                                <span class="cm">-- BM25 相关性排序</span>
<span class="kw">LIMIT</span> ? <span class="kw">OFFSET</span> ?</pre>
</div>
<p>三个 FTS5 特性各司其职：<span class="mono">MATCH</span> 做倒排全文匹配（支持 AND/OR/NOT/短语/前缀）；<span class="mono">ORDER BY rank</span> 是 FTS5 内建的 <strong>BM25</strong> 相关性排序；<span class="mono">snippet()</span> 把命中词用 <span class="mono">&gt;&gt;&gt;…&lt;&lt;&lt;</span> 包起来、最多 40 token 的高亮摘要。中文无空格分词，还有一张 <span class="mono">messages_fts_trigram</span>（trigram 分词器）做子串兜底，1–2 个汉字时退回 <span class="mono">LIKE</span>。整条检索<strong>没有任何模型参与</strong>。</p>

<h2>诚实的注脚：summary 路径已被移除</h2>
<p>这里有个值得讲的<strong>设计演进</strong>。早期版本（PR #20238）确实埋过一条「fast / summary 双模」——用辅助模型总结召回内容。但后来的工具集扩展（PR #26419）把整套<strong>合并重写</strong>成单一形态，summary 路径<strong>就此不复存在</strong>。今天的模块 docstring 把现状写得很清楚：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/session_search_tool.py</span><span class="ln">21-29 · 节选</span></div>
  <pre>All three modes operate on the SQLite session DB via the FTS5 index and
the get_anchored_view / get_messages_around primitives in hermes_state.
<span class="cm">No LLM calls anywhere — every shape returns actual messages from the DB.</span>

History: PR #20238 seeded a fast/summary dual-mode split; ... This module
merges all of that into a single calling shape with no mode parameter,
<span class="cm">no summary LLM path</span>, and explicit scroll support.</pre>
</div>
<p>（注意：README.md 里仍写着「FTS5 session search <strong>with LLM summarization</strong>」——那是<strong>过时的营销文案</strong>，与当前代码不符。忠于代码的说法是：<strong>零 LLM、直出 DB 原文 + BM25 排序 + 锚点书签</strong>。）这条注脚本身就是一课：当性能/成本与「让模型多做一步」冲突时，Hermes 选择了<strong>把原文交给主 agent 自己读</strong>——省一次调用，又不破缓存。</p>

<h2>四种模式 + 召回不破缓存</h2>
<p>工具 <span class="mono">session_search</span> 用<strong>参数推断</strong>四种模式（无显式 mode 参数）：给 <span class="mono">query</span> 是 <strong>DISCOVERY</strong>（FTS5 检索）；给 <span class="mono">session_id + around_message_id</span> 是 <strong>SCROLL</strong>（锚点翻页）；只给 <span class="mono">session_id</span> 是 <strong>READ</strong>（整会话）；什么都不给是 <strong>BROWSE</strong>（最近会话列表）。无论哪种，结果都<strong>原文</strong>作为 <strong>tool 消息 append</strong> 到对话末尾——不改 system prompt、不改任何历史轮次，所以缓存前缀<strong>逐字节不变</strong>。另外，会话标题由 <span class="mono">title_generator</span> 在首轮后<strong>后台线程 fire-and-forget</strong> 生成，绝不给用户响应加延迟。</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc"><strong>写入即索引</strong>：消息 INSERT → AFTER INSERT 触发器同步喂进 FTS5（content+tool_name+tool_calls，rowid=messages.id）</span></div>
  <div class="step"><span class="num">2</span><span class="sc"><strong>检索</strong>：agent 调 session_search(query=…) → MATCH + ORDER BY rank(BM25) + snippet() 高亮（CJK 走 trigram/LIKE 兜底）</span></div>
  <div class="step"><span class="num">3</span><span class="sc"><strong>锚点窗口</strong>：命中后取 ±N 条上下文 + 会话首尾书签（按需取回，不加载整段）</span></div>
  <div class="step"><span class="num">4</span><span class="sc"><strong>原文 append</strong>：结果作为 tool 消息追加到对话末尾——零 LLM 总结，原文交给 agent 自读</span></div>
  <div class="step"><span class="num">5</span><span class="sc">不改 system prompt / 不改历史轮次 → 缓存前缀逐字节不变，召回<strong>不破缓存</strong></span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「零成本召回而不破缓存」</div>
  <div class="collab-sub">① 组件清单（★本章核心，其余跨章节配合）</div>
  本章核心：<strong>SessionDB FTS5 表 + 触发器</strong>（写入即索引）、<strong>search_messages</strong>（MATCH+BM25+snippet）、<strong>CJK trigram 路由</strong>、<strong>session_search 工具</strong>（4 模式）、<strong>get_anchored_view</strong>（锚点书签）。跨章节配合：搜索结果作为 <strong>tool 消息 append</strong>、不改前缀（第 6 章缓存 + 第 8 章工具结果 append-only）；跨会话召回对抗<strong>模型无状态</strong>（第 2 章 B）；标题生成在首轮后由<strong>辅助模型链</strong>（主模型优先、否则回退辅助 client）后台线程生成、不阻塞主响应（与第 10 章辅助模型隔离同源）。
  <div class="collab-sub">② 数据流时序</div>
  消息 INSERT → 触发器同步建 FTS5 索引（写入即索引）；agent 想起旧事 → session_search(query) → MATCH+BM25+snippet（CJK trigram 兜底）→ get_anchored_view 取锚点窗口+书签 → 原文作为 tool 消息 append 到对话末尾 → agent 自读。标题生成在首轮后台 fire-and-forget。
  <div class="collab-sub">③ 关键点</div>
  「跨会话记忆」不一定要 LLM。Hermes 用<strong>本地 FTS5 + 原文 append</strong> 实现召回：写入时同步建索引（零额外步骤），检索时零模型调用（零成本），返回时只 append tool 消息（不破缓存）。三者合起来，让「想起以前」既<strong>便宜</strong>又<strong>不伤性能</strong>。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线：<strong>零 LLM 直出 DB 原文 + append-only 召回</strong>——既省成本又不破缓存。它治两条 LLM 固有约束：
  <p style="margin:.5rem 0 0"><span class="badge constraint">B·无状态</span>——模型跨会话什么都记不住，靠本地 FTS5 索引把<strong>所有历史对话</strong>变成可检索的外部记忆；
  <span class="badge constraint">A·中间遗失</span>——召回用 <strong>BM25 排序 + 锚点书签</strong> 只取最相关的片段（按需取回），而非把整段历史塞回上下文淹没注意力。反模式：为了「更聪明的召回」而引入一次 LLM 总结——它既加成本、加延迟，若把总结塞进 system prompt 还会<strong>击穿缓存</strong>。Hermes 反其道：原文交给主 agent 自己读。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>写入即索引</strong>：<span class="mono">AFTER INSERT</span> 触发器同步把消息喂进 FTS5（<span class="mono">content+tool_name+tool_calls</span>，rowid=messages.id），无需离线建库。</li>
    <li><strong>FTS5 检索</strong>：<span class="mono">MATCH</span> 全文匹配 + <span class="mono">ORDER BY rank</span>（BM25）+ <span class="mono">snippet()</span> 高亮；CJK 用 trigram/LIKE 兜底。</li>
    <li><strong>零 LLM</strong>：summary 路径在模块合并为单一形态后已不复存在（PR #20238 埋下、#26419 扩展合并）；返回 DB 原文让 agent 自读（README「with LLM summarization」是过时文案）。</li>
    <li><strong>4 种模式</strong>：参数推断 DISCOVERY / SCROLL / READ / BROWSE，无显式 mode 参数。</li>
    <li><strong>召回不破缓存</strong>：结果作为 tool 消息 append，不改 system prompt/历史 → 前缀逐字节不变（第 6/8 章）。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">
You've chatted with Hermes hundreds of times, and one day you ask, "what was that deployment plan we discussed <strong>before</strong>?" — and it remembers, <strong>across sessions</strong>. That's cross-session search. But it has a counter-intuitive design: <strong>zero LLM, zero cost</strong>. It calls no model to "understand" or "summarize" — it queries a local SQLite <strong>FTS5 full-text index</strong> directly and returns the <strong>original messages verbatim</strong> for the agent to read itself. And recall <strong>doesn't break the prompt cache</strong>.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · a library card catalog</div>
  An old library's <strong>card catalog</strong>: as each book is shelved, the librarian copies its keywords into the card drawers (index on write). To find a book, you don't hire a scholar to <strong>read every book and tell you the gist</strong> (that's LLM summarization — slow and expensive) — you flip through the cards, sorted by relevance, and <strong>get the book's page numbers and excerpts</strong> to read yourself. Hermes's cross-session search is that card drawer: the FTS5 index is <strong>built as messages are written</strong>, and a search returns originals directly, <strong>never disturbing any model</strong>.
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture · index on write, recall verbatim, zero LLM</div>
  Three things form this chain: ① <strong>index on write</strong> — each message INSERTed into SQLite is <strong>synchronously</strong> fed by a trigger into the FTS5 inverted index (content + tool_name + tool_calls); ② <strong>FTS5 retrieval</strong> — search uses <span class="mono">MATCH</span> + BM25 relevance ranking + <span class="mono">snippet()</span> highlighting, with a trigram substring fallback for CJK; ③ <strong>verbatim append</strong> — the matched <strong>original messages</strong> are appended as a tool-result message at the end of the conversation for the agent to read. <strong>Not a single LLM call</strong> — which both saves money and (being just an appended tool message) <strong>doesn't touch the system prompt or break the cache</strong>.
</div>

<h2>Index on write: an AFTER INSERT trigger</h2>
<p>No separate "build the index" step is needed — the moment a message is written into the <span class="mono">messages</span> table, a SQLite trigger <strong>synchronously</strong> sends it into FTS5:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">hermes_state.py</span><span class="ln">612-621 · excerpt</span></div>
  <pre><span class="kw">CREATE VIRTUAL TABLE</span> messages_fts <span class="kw">USING</span> fts5(content);

<span class="kw">CREATE TRIGGER</span> messages_fts_insert <span class="kw">AFTER INSERT ON</span> messages <span class="kw">BEGIN</span>
    <span class="kw">INSERT INTO</span> messages_fts(rowid, content) <span class="kw">VALUES</span> (
        new.id,
        <span class="fn">COALESCE</span>(new.content, <span class="st">''</span>) || <span class="st">' '</span> ||
        <span class="fn">COALESCE</span>(new.tool_name, <span class="st">''</span>) || <span class="st">' '</span> ||
        <span class="fn">COALESCE</span>(new.tool_calls, <span class="st">''</span>)
    );
<span class="kw">END</span>;</pre>
</div>
<p>Two bits of cleverness. First, <span class="mono">rowid = new.id</span> — the FTS index's row id is <span class="mono">messages.id</span>, so a hit can JOIN straight back to the original message. Second, what's indexed isn't just content but <span class="mono">content + tool_name + tool_calls</span> concatenated — so even "which tool was called when" is searchable. Index-on-write means: <strong>no offline indexing needed</strong>, and what you just said is retrievable a second later.</p>

<h2>Retrieval: FTS5 MATCH + BM25 + snippet</h2>
<p>The search itself is one pure SQL statement, fully using FTS5's features — full-text match, relevance ranking, highlighted excerpts:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">hermes_state.py</span><span class="ln">3532-3579 · simplified</span></div>
  <pre><span class="kw">SELECT</span> m.id, m.session_id, m.role,
       <span class="fn">snippet</span>(messages_fts, 0, <span class="st">'&gt;&gt;&gt;'</span>, <span class="st">'&lt;&lt;&lt;'</span>, <span class="st">'...'</span>, 40) <span class="kw">AS</span> snippet,
       m.content, m.timestamp, s.source
<span class="kw">FROM</span> messages_fts
<span class="kw">JOIN</span> messages m <span class="kw">ON</span> m.id = messages_fts.rowid    <span class="cm">-- rowid JOINs straight back</span>
<span class="kw">JOIN</span> sessions s <span class="kw">ON</span> s.id = m.session_id
<span class="kw">WHERE</span> messages_fts <span class="kw">MATCH</span> ?                    <span class="cm">-- full-text match</span>
<span class="kw">ORDER BY</span> rank                                <span class="cm">-- BM25 relevance ranking</span>
<span class="kw">LIMIT</span> ? <span class="kw">OFFSET</span> ?</pre>
</div>
<p>Three FTS5 features each do their job: <span class="mono">MATCH</span> does inverted full-text matching (AND/OR/NOT/phrase/prefix); <span class="mono">ORDER BY rank</span> is FTS5's built-in <strong>BM25</strong> relevance ranking; <span class="mono">snippet()</span> wraps hit terms in <span class="mono">&gt;&gt;&gt;…&lt;&lt;&lt;</span> as a highlighted excerpt of up to 40 tokens. For space-less CJK there's a second <span class="mono">messages_fts_trigram</span> table (trigram tokenizer) for substring fallback, dropping to <span class="mono">LIKE</span> for 1–2 characters. The whole retrieval involves <strong>no model at all</strong>.</p>

<h2>An honest footnote: the summary path was removed</h2>
<p>Here's a <strong>design evolution</strong> worth telling. An early version (PR #20238) did seed a "fast / summary" dual mode — using an auxiliary model to summarize recalled content. But the later toolkit expansion (PR #26419) <strong>merged and rewrote</strong> everything into a single shape, and the summary path <strong>ceased to exist</strong>. Today's module docstring states the reality plainly:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/session_search_tool.py</span><span class="ln">21-29 · excerpt</span></div>
  <pre>All three modes operate on the SQLite session DB via the FTS5 index and
the get_anchored_view / get_messages_around primitives in hermes_state.
<span class="cm">No LLM calls anywhere — every shape returns actual messages from the DB.</span>

History: PR #20238 seeded a fast/summary dual-mode split; ... This module
merges all of that into a single calling shape with no mode parameter,
<span class="cm">no summary LLM path</span>, and explicit scroll support.</pre>
</div>
<p>(Note: README.md still says "FTS5 session search <strong>with LLM summarization</strong>" — that's <strong>stale marketing copy</strong>, out of sync with the code. The code-faithful description is: <strong>zero LLM, raw DB rows + BM25 ranking + anchored bookends</strong>.) This footnote is itself a lesson: when performance/cost conflicts with "make the model do one more step," Hermes chose to <strong>hand the originals to the main agent to read</strong> — saving a call and not breaking the cache.</p>

<h2>Four modes + recall that doesn't break the cache</h2>
<p>The <span class="mono">session_search</span> tool infers <strong>four modes from parameters</strong> (no explicit mode arg): a <span class="mono">query</span> is <strong>DISCOVERY</strong> (FTS5 search); <span class="mono">session_id + around_message_id</span> is <strong>SCROLL</strong> (anchored paging); just <span class="mono">session_id</span> is <strong>READ</strong> (whole session); nothing is <strong>BROWSE</strong> (recent sessions list). Either way, results are <strong>appended verbatim as a tool message</strong> at the end of the conversation — without changing the system prompt or any prior turn, so the cache prefix stays <strong>byte-identical</strong>. Separately, session titles are generated by <span class="mono">title_generator</span> in a <strong>fire-and-forget background thread</strong> after the first turn, never adding latency to the user's reply.</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc"><strong>Index on write</strong>: message INSERT → AFTER INSERT trigger synchronously feeds FTS5 (content+tool_name+tool_calls, rowid=messages.id)</span></div>
  <div class="step"><span class="num">2</span><span class="sc"><strong>Retrieve</strong>: agent calls session_search(query=…) → MATCH + ORDER BY rank(BM25) + snippet() (CJK via trigram/LIKE fallback)</span></div>
  <div class="step"><span class="num">3</span><span class="sc"><strong>Anchored window</strong>: take ±N context messages + session bookends (on-demand, not loading the whole thing)</span></div>
  <div class="step"><span class="num">4</span><span class="sc"><strong>Append verbatim</strong>: results appended as a tool message at the conversation tail — zero LLM summary, originals handed to the agent to read</span></div>
  <div class="step"><span class="num">5</span><span class="sc">no change to system prompt / prior turns → the cache prefix stays byte-identical, recall <strong>doesn't break the cache</strong></span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "zero-cost recall without breaking the cache"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: the <strong>SessionDB FTS5 table + triggers</strong> (index on write), <strong>search_messages</strong> (MATCH+BM25+snippet), the <strong>CJK trigram route</strong>, the <strong>session_search tool</strong> (4 modes), <strong>get_anchored_view</strong> (anchored bookends). Cross-chapter teamwork: search results are <strong>appended as tool messages</strong> and don't change the prefix (ch.6 caching + ch.8 tool-result append-only); cross-session recall fights the <strong>model's statelessness</strong> (ch.2 B); title generation runs after the first turn on the <strong>auxiliary-model chain</strong> (main model preferred, else the auxiliary client) in a background thread, not blocking the main reply (same auxiliary-model isolation as ch.10).
  <div class="collab-sub">② Data-flow timing</div>
  message INSERT → trigger synchronously builds the FTS5 index (index on write); the agent recalls something → session_search(query) → MATCH+BM25+snippet (CJK trigram fallback) → get_anchored_view takes an anchored window + bookends → originals appended as a tool message at the conversation tail → the agent reads them. Title generation is fire-and-forget after the first turn.
  <div class="collab-sub">③ The key point</div>
  "Cross-session memory" doesn't require an LLM. Hermes implements recall with <strong>local FTS5 + verbatim append</strong>: build the index synchronously on write (zero extra steps), retrieve with zero model calls (zero cost), and return by appending only a tool message (no cache break). Together they make "remembering the past" both <strong>cheap</strong> and <strong>harmless to performance</strong>.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>zero-LLM raw-DB recall + append-only</strong> — saving cost and not breaking the cache. It treats two inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">B·stateless</span> — the model remembers nothing across sessions, so a local FTS5 index turns <strong>all past conversations</strong> into searchable external memory;
  <span class="badge constraint">A·lost-in-the-middle</span> — recall uses <strong>BM25 ranking + anchored bookends</strong> to take only the most relevant fragments (on-demand), rather than dumping whole histories back into context to drown attention. The anti-pattern: adding an LLM summary for "smarter recall" — it adds cost and latency, and if the summary is dropped into the system prompt it also <strong>shatters the cache</strong>. Hermes does the opposite: hand the originals to the main agent to read.</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Index on write</strong>: an <span class="mono">AFTER INSERT</span> trigger synchronously feeds messages into FTS5 (<span class="mono">content+tool_name+tool_calls</span>, rowid=messages.id), no offline indexing.</li>
    <li><strong>FTS5 retrieval</strong>: <span class="mono">MATCH</span> full-text + <span class="mono">ORDER BY rank</span> (BM25) + <span class="mono">snippet()</span> highlight; CJK via trigram/LIKE fallback.</li>
    <li><strong>Zero LLM</strong>: the summary path ceased to exist after the module merged into a single shape (PR #20238 seeded it, #26419 expanded/merged); it returns DB originals for the agent to read (README's "with LLM summarization" is stale copy).</li>
    <li><strong>Four modes</strong>: parameter-inferred DISCOVERY / SCROLL / READ / BROWSE, no explicit mode arg.</li>
    <li><strong>Recall doesn't break the cache</strong>: results are appended as a tool message, leaving the system prompt/history unchanged → byte-identical prefix (ch.6/8).</li>
  </ul>
</div>
""",
}
