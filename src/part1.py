"""Part 1 — The Big Picture. Chapter 1 ships as the visual baseline."""

LESSON_01 = {
    "zh": r"""
<p class="lead">
Hermes 是 <a href="https://github.com/NousResearch/hermes-agent">Nous Research</a> 做的
<strong>自我进化的个人 AI agent</strong>。它官网第一句话就把自己定义成
<strong>“唯一内建学习闭环的 agent”</strong>：在使用中<strong>创建技能</strong>、
<strong>改进技能</strong>、<strong>提醒自己把知识记下来</strong>、<strong>搜索自己的过往对话</strong>，
并跨会话<strong>越来越懂你</strong>。同一套 agent 核心，能跑在 CLI、消息网关、TUI 和桌面 App 上。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  把普通 agent 想成一个<strong>每天失忆的临时工</strong>：今天教会的事，明天又得从头教。
  Hermes 更像一个<strong>会记工作笔记的老员工</strong>：每做完一件棘手的活，就把
  “这类问题该怎么解”写进<strong>技能手册</strong>，把“关于你的事实”写进<strong>记忆</strong>。
  下次遇到同类问题，它翻笔记、几步就搞定——<strong>越用越顺手</strong>。
</div>

<h2>它到底是什么</h2>
<p>一句话：<strong>一个把“经验”沉淀成“能力”的 agent</strong>。它不替你训练模型，而是在你用它干活的过程中，
把成功的做法变成<strong>可复用的程序性知识</strong>。这件事之所以重要，是因为大模型本身有个硬伤——
<strong>两次调用之间它什么都不记得</strong>。Hermes 的全部“进化”机制，本质都是在<strong>对抗这个失忆</strong>。</p>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  同一个 <span class="inline">AIAgent</span> 核心，被 CLI、网关（Telegram/Discord/Slack…）、TUI、桌面 App
  共用。能力主要<strong>长在边缘</strong>——通过<strong>技能</strong>、<strong>插件</strong>、<strong>MCP</strong> 扩展，
  而<strong>核心保持很窄</strong>。再加一条铁律：<strong>每个会话的 prompt 缓存神圣不可侵犯</strong>，
  几乎所有设计都要绕着它走。
</div>

<h2>自我进化的学习闭环：四件套</h2>
<p>Hermes 的“进化”不是玄学，而是<strong>四个协作的子系统</strong>，把一次性的对话变成可积累的资产：</p>

<div class="layers">
  <div class="layer l-app"><div class="lh"><span class="badge">技能</span><span class="name">skill_manage</span></div>
    <div class="ld">程序性记忆：“某类任务<strong>怎么做</strong>”。agent 自己创建、用 <span class="mono">patch</span> 改进。</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">记忆</span><span class="name">MEMORY.md · USER.md</span></div>
    <div class="ld">声明性知识：项目事实与<strong>用户画像</strong>。会话开始注入，跨会话加深。</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">搜索</span><span class="name">SessionDB · FTS5</span></div>
    <div class="ld">跨会话召回：全文检索<strong>自己的过往对话</strong>，按需想起“以前怎么弄的”。</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">园丁</span><span class="name">Curator</span></div>
    <div class="ld">后台维护：自动归档没人用的旧技能，<strong>永不删除、只归档</strong>，可恢复。</div></div>
</div>

<h2>一次“变聪明”长什么样</h2>
<p>把闭环跑一遍，就是下面这条线：解决问题 → 被<strong>提醒</strong>该沉淀了 → 写成技能/记忆 → 下次更快：</p>
<div class="flow">
  <div class="node"><div class="nt">解决一个难题</div><div class="nd">和你一起干完一件活</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node hl"><div class="nt">学习 nudge</div><div class="nd">“要不要存成技能？”</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">沉淀</div><div class="nd">写技能 / 记忆</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node hl"><div class="nt">下次更快</div><div class="nd">翻笔记，几步搞定</div></div>
</div>

<h2>和普通 agent 的区别</h2>
<div class="cols">
  <div class="col"><h4>🤖 普通 agent</h4>
    <ul><li>会话结束即<strong>失忆</strong></li><li>绑定你的笔记本</li><li>能力靠堆<strong>核心工具</strong></li><li>换模型要改代码</li></ul></div>
  <div class="col"><h4>☤ Hermes</h4>
    <ul><li>技能/记忆<strong>跨会话累积</strong></li><li>跑在 VPS/云/serverless，<strong>处处可达</strong></li><li>能力长在<strong>边缘</strong>（技能/插件/MCP）</li><li><strong>模型无关</strong>，一条命令切换</li></ul></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 四件套如何拼成闭环</div>
  <div class="collab-sub">① 组件清单（本章概览，细节见后续章）</div>
  <strong>学习 nudge</strong>（第 9 章）在干活到一定轮次时，往对话<strong>末尾</strong>追加一条反思提醒；
  agent 据此调用 <strong>skill_manage</strong>（第 9 章）写<strong>技能</strong>、调用 <strong>memory</strong> 工具（第 11 章）写
  <strong>MEMORY/USER.md</strong>；<strong>Curator</strong>（第 10 章）在后台用<strong>辅助模型</strong>修剪旧技能；
  <strong>SessionDB+FTS5</strong>（第 12 章）把每轮对话索引下来，供 <strong>session_search</strong> 召回。
  <div class="collab-sub">② 数据流时序</div>
  会话开始：读 MEMORY/USER.md + 扫描技能清单 → 注入<strong>固定前缀</strong>；
  会话中：nudge / 技能全文 / 搜索结果都只往<strong>末尾追加</strong>；
  会话后：对话进 SessionDB、技能与记忆落盘 → 喂给<strong>下一个</strong>会话。
  <div class="collab-sub">③ 关键点</div>
  四件套各管一段，但都遵守同一条纪律——<strong>读只在会话开始进前缀、写只在末尾追加</strong>，
  于是“变聪明”不必重建上下文、不破坏缓存。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  全书有三条主线贯穿每个部件：<strong>① 自我进化</strong>（把经验变能力）、
  <strong>② prompt 缓存神圣不可侵犯</strong>（长对话每轮复用缓存前缀，绝不中途改写）、
  <strong>③ 窄腰架构</strong>（核心小、能力在边缘长）。
  <p style="margin:.5rem 0 0">它对抗的 LLM 固有约束：<span class="badge constraint">B·无状态</span>——
  模型两次调用之间零记忆，所以“状态”必须<strong>外置</strong>到技能、记忆、会话库里。这就是“进化”存在的根本理由。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li>Hermes = <strong>自我进化的个人 agent</strong>：把经验沉淀成<strong>技能</strong>（怎么做）和<strong>记忆</strong>（是什么）。</li>
    <li>进化在模型<strong>之外</strong>：底层模型无状态、固定；靠 nudge + 技能 + 记忆 + 搜索 + curator 协作。</li>
    <li>同一 agent 核心驱动多端；能力<strong>长在边缘</strong>，核心保持<strong>窄腰</strong>。</li>
    <li>一条铁律：<strong>每个会话的 prompt 缓存神圣不可侵犯</strong>——后面几乎每章都在为它让路。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">
Hermes is <a href="https://github.com/NousResearch/hermes-agent">Nous Research</a>'s
<strong>self-improving personal AI agent</strong>. Its tagline calls it
<strong>“the only agent with a built-in learning loop”</strong>: while you use it, it
<strong>creates skills</strong>, <strong>improves them</strong>,
<strong>nudges itself to persist knowledge</strong>, <strong>searches its own past
conversations</strong>, and grows a <strong>deepening model of you</strong> across sessions.
One agent core runs the CLI, the messaging gateway, the TUI and a desktop app.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  A normal agent is a <strong>temp worker with daily amnesia</strong>: what you taught it today
  must be re-taught tomorrow. Hermes is more like a <strong>seasoned employee who keeps notes</strong>:
  after each tricky job it writes “how to solve this class of problem” into a <strong>skill book</strong>
  and “facts about you” into <strong>memory</strong>. Next time, it flips to the notes and finishes in a
  few steps — <strong>better the more you use it</strong>.
</div>

<h2>What it actually is</h2>
<p>In one line: <strong>an agent that turns experience into capability</strong>. It doesn't train models for
you; it turns proven approaches into <strong>reusable procedural knowledge</strong> as you work. This matters
because LLMs have a hard limitation — <strong>they remember nothing between two calls</strong>. Every Hermes
“evolution” mechanism is, at heart, <strong>a fight against that amnesia</strong>.</p>

<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  One <span class="inline">AIAgent</span> core is shared by the CLI, the gateway (Telegram/Discord/Slack…),
  the TUI and a desktop app. Capability mostly <strong>lives at the edges</strong> — via <strong>skills</strong>,
  <strong>plugins</strong> and <strong>MCP</strong> — while the <strong>core stays narrow</strong>. Plus one iron
  rule: <strong>per-conversation prompt caching is sacred</strong>, and almost every design bends around it.
</div>

<h2>The self-improvement loop: four parts</h2>
<p>Hermes' “evolution” isn't magic — it's <strong>four cooperating subsystems</strong> that turn one-off chats
into accumulating assets:</p>

<div class="layers">
  <div class="layer l-app"><div class="lh"><span class="badge">Skills</span><span class="name">skill_manage</span></div>
    <div class="ld">Procedural memory: <strong>how to do</strong> a class of task. The agent creates them and improves them with <span class="mono">patch</span>.</div></div>
  <div class="layer l-part"><div class="lh"><span class="badge">Memory</span><span class="name">MEMORY.md · USER.md</span></div>
    <div class="ld">Declarative knowledge: project facts and a <strong>user profile</strong>. Injected at session start, deepened across sessions.</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">Search</span><span class="name">SessionDB · FTS5</span></div>
    <div class="ld">Cross-session recall: full-text search of <strong>its own past chats</strong> — “how did I do this before?”</div></div>
  <div class="layer l-core"><div class="lh"><span class="badge">Gardener</span><span class="name">Curator</span></div>
    <div class="ld">Background upkeep: auto-archives unused old skills — <strong>never deletes, only archives</strong>, restorable.</div></div>
</div>

<h2>What “getting smarter” looks like</h2>
<p>Run the loop once and you get this line: solve a problem → get <strong>nudged</strong> to capture it → save a
skill/memory → next time it's faster:</p>
<div class="flow">
  <div class="node"><div class="nt">Solve a hard task</div><div class="nd">finish a job with you</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node hl"><div class="nt">Learning nudge</div><div class="nd">“save this as a skill?”</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">Capture</div><div class="nd">write skill / memory</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node hl"><div class="nt">Faster next time</div><div class="nd">flip to notes, done</div></div>
</div>

<h2>How it differs from a normal agent</h2>
<div class="cols">
  <div class="col"><h4>🤖 Normal agent</h4>
    <ul><li><strong>Amnesia</strong> when the session ends</li><li>Tied to your laptop</li><li>Capability by piling on <strong>core tools</strong></li><li>Switching models means code changes</li></ul></div>
  <div class="col"><h4>☤ Hermes</h4>
    <ul><li>Skills/memory <strong>accumulate across sessions</strong></li><li>Runs on VPS/cloud/serverless — <strong>lives everywhere</strong></li><li>Capability grows at the <strong>edges</strong> (skills/plugins/MCP)</li><li><strong>Model-agnostic</strong>, switch with one command</li></ul></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the four parts form the loop</div>
  <div class="collab-sub">① Component roster (overview; details in later chapters)</div>
  The <strong>learning nudge</strong> (ch.9) appends a reflection prompt to the <strong>end</strong> of the chat after
  enough turns; the agent then calls <strong>skill_manage</strong> (ch.9) to write a <strong>skill</strong> and the
  <strong>memory</strong> tool (ch.11) to write <strong>MEMORY/USER.md</strong>; the <strong>Curator</strong> (ch.10)
  prunes old skills in the background with an <strong>auxiliary model</strong>; <strong>SessionDB+FTS5</strong> (ch.12)
  indexes every turn for <strong>session_search</strong> to recall.
  <div class="collab-sub">② Data-flow timing</div>
  Session start: read MEMORY/USER.md + scan the skill list → inject the <strong>fixed prefix</strong>;
  during the session: nudges / skill bodies / search results are only <strong>appended at the end</strong>;
  after: the chat goes into SessionDB, skills & memory persist → feed the <strong>next</strong> session.
  <div class="collab-sub">③ The key point</div>
  Each part owns one stage, but all obey one rule — <strong>reads enter the prefix at session start, writes only
  append at the end</strong> — so “getting smarter” never rebuilds context or breaks the cache.
</div>

<div class="card design">
  <div class="tag">🎯 Design tradeoff · what this chapter is about</div>
  Three throughlines run through every part of the book: <strong>① self-evolution</strong> (experience → capability),
  <strong>② prompt caching is sacred</strong> (a long chat reuses a cached prefix every turn, never rewritten mid-way),
  and <strong>③ the narrow waist</strong> (small core, capability at the edges).
  <p style="margin:.5rem 0 0">The LLM constraint it fights: <span class="badge constraint">B·Statelessness</span> —
  the model has zero memory between calls, so “state” must be <strong>externalized</strong> into skills, memory and the
  session store. That is the root reason “evolution” exists at all.</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li>Hermes = a <strong>self-improving personal agent</strong>: it distills experience into <strong>skills</strong> (how-to) and <strong>memory</strong> (facts).</li>
    <li>Evolution lives <strong>outside</strong> the model: the base model is stateless and fixed; nudge + skills + memory + search + curator cooperate.</li>
    <li>One agent core drives every front-end; capability grows at the <strong>edges</strong>, the core stays a <strong>narrow waist</strong>.</li>
    <li>One iron rule: <strong>per-conversation prompt caching is sacred</strong> — nearly every later chapter bends around it.</li>
  </ul>
</div>
""",
}
