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

<h2>它为什么不绑定你的笔记本</h2>
<p>很多 agent 只能跑在你开着的那台电脑上。Hermes 的设计目标之一是<strong>把 agent 从单机里解放出来</strong>：
它能跑在 5 美元的 VPS、GPU 集群，或 <strong>serverless</strong> 环境上——闲时<strong>休眠到几乎零成本</strong>、有请求才唤醒。
于是你可以一边在 Telegram 上发消息，一边让它在<strong>云端 VM</strong> 上默默干活，关掉手机它也不停。</p>
<p>它还<strong>模型无关</strong>：Nous Portal、OpenRouter（200+ 模型）、OpenAI、本地端点都行，一条
<span class="mono">hermes model</span> 命令切换，不动一行代码。这种“<strong>位置自由 + 模型自由</strong>”，是它能成为
<strong>长期个人 agent</strong> 的前提——你的助理不该被锁在某台机器、某个厂商上。这一点也呼应了它的部署哲学：
agent 的<strong>运行环境</strong>本身就是可插拔的，从本机一直到 serverless 沙箱：</p>
<table class="t">
  <tr><th>终端后端</th><th>用途</th></tr>
  <tr><td><span class="mono">local</span></td><td>就在本机跑，最简单</td></tr>
  <tr><td><span class="mono">docker</span></td><td>隔离容器，干净可弃</td></tr>
  <tr><td><span class="mono">ssh</span></td><td>把活派到远程主机</td></tr>
  <tr><td><span class="mono">singularity</span></td><td>HPC / 集群环境</td></tr>
  <tr><td><span class="mono">modal · daytona</span></td><td><strong>serverless</strong>：闲时休眠、按需唤醒，几乎零成本</td></tr>
</table>

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

<h2>进化的发动机：学习 nudge</h2>
<p>这套闭环有个关键问题：大模型<strong>不会主动反思</strong>“我刚学到的东西要不要存起来”。Hermes 的解法很巧——
在你和它干活到一定轮次时，<strong>往对话末尾塞一条反思提醒</strong>（nudge）：“你是不是学到了一个可复用的流程？
要不要用 <span class="mono">skill_manage</span> 存成技能？”这条提醒踩着<strong>恰当的时机</strong>触发、每个会话<strong>只发一次</strong>，不打扰你。</p>
<p>更妙的是它<strong>注入的位置</strong>：nudge 是一条追加到消息<strong>末尾</strong>的普通 user 消息，
<strong>不改动 system prompt、不重建上下文</strong>。这正是为了守住那条铁律——<strong>prompt 缓存不能破</strong>。
“提醒 agent 去学习”这件看似简单的事，背后是一个<strong>既要驱动进化、又不能破坏缓存</strong>的精细权衡（细节见第 9 章）。</p>
<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>干活</h4><p>和你一起解决问题，积累了“怎么做”的经验</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>到点提醒</h4><p>末尾追加 nudge：“要不要存成技能/记忆？”</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>沉淀</h4><p>agent 调 <span class="mono">skill_manage</span> / <span class="mono">memory</span> 落盘</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>复用</h4><p>下个会话技能清单/记忆已就位，几步搞定</p></div></div>
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

<h2>Why it isn't tied to your laptop</h2>
<p>Many agents only run on the one machine you keep open. A core goal of Hermes is to <strong>free the agent from a
single box</strong>: it runs on a $5 VPS, a GPU cluster, or <strong>serverless</strong> infra that <strong>hibernates to
near-zero cost</strong> when idle and wakes on demand. So you can message it from Telegram while it works on a <strong>cloud
VM</strong> — close your phone and it keeps going.</p>
<p>It's also <strong>model-agnostic</strong>: Nous Portal, OpenRouter (200+ models), OpenAI, your own endpoint — switch
with one <span class="mono">hermes model</span> command, no code changes. This “<strong>freedom of place + freedom of
model</strong>” is what lets it be a <strong>long-lived personal agent</strong> — your assistant shouldn't be locked to one
machine or vendor. It echoes the deployment philosophy: the agent's <strong>runtime</strong> is itself pluggable, from local
all the way to a serverless sandbox:</p>
<table class="t">
  <tr><th>Terminal backend</th><th>Use</th></tr>
  <tr><td><span class="mono">local</span></td><td>just run on this machine</td></tr>
  <tr><td><span class="mono">docker</span></td><td>isolated, disposable container</td></tr>
  <tr><td><span class="mono">ssh</span></td><td>send work to a remote host</td></tr>
  <tr><td><span class="mono">singularity</span></td><td>HPC / cluster environments</td></tr>
  <tr><td><span class="mono">modal · daytona</span></td><td><strong>serverless</strong>: hibernate when idle, wake on demand, near-zero cost</td></tr>
</table>

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

<h2>The engine of evolution: the learning nudge</h2>
<p>The loop has one catch: an LLM <strong>won't spontaneously reflect</strong> on “should I save what I just learned?”
Hermes' fix is clever — after enough turns of working together, it <strong>appends a reflection prompt to the end of the
chat</strong> (a nudge): “Did you just learn a repeatable procedure? Want to save it as a skill with
<span class="mono">skill_manage</span>?” The nudge fires at the <strong>right moment</strong>, <strong>once per
session</strong>, so it never nags.</p>
<p>What's neat is <strong>where</strong> it's injected: the nudge is a plain user message appended at the
<strong>end</strong>, <strong>changing no system prompt and rebuilding no context</strong>. That's exactly to honor the iron
rule — <strong>the prompt cache must not break</strong>. “Remind the agent to learn” sounds trivial, but underneath it's a
careful tradeoff between <strong>driving evolution</strong> and <strong>never breaking the cache</strong> (details in ch.9).</p>
<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Work</h4><p>solve problems with you; accumulate know-how</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Nudge</h4><p>append at the end: “save as a skill/memory?”</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Capture</h4><p>agent calls <span class="mono">skill_manage</span> / <span class="mono">memory</span></p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Reuse</h4><p>next session the skill/memory is ready — done in a few steps</p></div></div>
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

LESSON_02 = {
    "zh": r"""
<p class="lead">
在拆解 Hermes 的设计之前，先认清我们在和什么打交道。一次大模型调用，本质是一个
<strong>无状态、按 token 看世界、凭概率续写</strong>的函数：你把上下文递进去，它吐出最可能的下一段文字。
它很强，却带着一组“出厂自带”的硬约束。这一章讲<strong>单次调用</strong>层面的三类——
<strong>注意力与上下文(A)</strong>、<strong>无状态与非确定(B)</strong>、<strong>token 表示层(E)</strong>。
它们是后面几乎每个设计的“病因”：你会看到 Hermes 的很多取舍，都是在<strong>顺着这些约束</strong>设计，而不是硬刚。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  把一次调用想成请教一位<strong>博学却“每次失忆”的专家</strong>：你把所有背景写在<strong>一张纸</strong>上递进去，
  他只读这张纸、给一个回答，然后<strong>忘光一切</strong>。下次再问，得重新递一张纸。而且他读长文时，
  <strong>最在意开头和结尾，中间容易扫过去</strong>；他还不是一个字一个字读，而是按<strong>词块(token)</strong>读，
  所以“strawberry 里有几个 r”这种字符级问题，他反而容易答错。
</div>

<h2>A · 注意力与上下文：不是“塞得下”就行</h2>
<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  模型的注意力<strong>不是均匀</strong>铺在整个上下文上的。位置、长度都会显著影响它“看见”了什么、看得多准。
  把上下文当成一种<strong>稀缺资源</strong>来经营，是 agent 设计的第一课。
</div>
<p><strong>① 中间遗失（lost in the middle）。</strong>大量实验发现：模型对上下文的<strong>开头</strong>和<strong>结尾</strong>
注意力最强，<strong>中间最弱</strong>。把关键指令埋在长上下文中段，常常“看不见”。对策很直接——
<strong>关键指令在头、尾各放一遍</strong>；最相关的检索片段放<strong>边缘</strong>，别塞在中间。</p>
<div class="cellgroup">
  <div class="cg-cap">同一条关键指令，放在不同位置时的“被看见”强度（示意）：</div>
  <div class="cells">
    <span class="cell hl">开头·强</span><span class="cell dim">中间·弱</span><span class="cell dim">中间·弱</span><span class="cell dim">中间·弱</span><span class="cell hl">结尾·强</span>
    <span class="lab">U 型注意力</span>
  </div>
</div>
<p><strong>② 上下文腐烂（context rot）。</strong>就算窗口没满，质量也会<strong>随长度下降</strong>：指令遵循度变差、幻觉变多。
所以<strong>压缩不只是为了省钱/塞得下，更是为了质量</strong>——一份<strong>精简聚焦</strong>的上下文，往往胜过“把什么都塞进去”。
检索也一样：要<strong>精度优先于召回</strong>，无关文档会“分散注意力”。</p>
<p><strong>③ 长度 → 延迟与成本。</strong>上下文越长，每一步越慢、越贵。交互式 agent 必须有<strong>上下文预算</strong>，
不能无脑堆历史。这条直接催生了 Hermes 的<strong>迭代预算</strong>（第 5 章）与<strong>上下文压缩</strong>（第 15 章）。</p>
<div class="card warn">
  <div class="tag">⚠️ 反直觉</div>
  “给它更多上下文”不总是更好。超过某个点，<strong>更多上下文 = 更差的回答</strong>。少而精 &gt; 多而杂。
</div>

<h2>B · 无状态与非确定：它没有记忆，也不保证可复现</h2>
<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  两次调用之间，模型<strong>什么都不记得</strong>；而且同样的输入，<strong>未必</strong>给同样的输出。
  这两点决定了：“agent”本质是<strong>围绕一个无状态、非确定函数</strong>做的工程编排。
</div>
<p><strong>① 无状态。</strong>模型不在调用之间保存任何东西。所有“记忆”都必须<strong>外置</strong>（写进文件/数据库）
或<strong>每次重发</strong>（塞进 messages）。这正是 Hermes 要有<strong>技能、记忆、会话库</strong>的根本原因——
它们是那个失忆核心的“外接硬盘”（第 11、12 章）。</p>
<div class="flow">
  <div class="node"><div class="nt">第 1 次调用</div><div class="nd">读完 messages，回答</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">调用结束</div><div class="nd">模型<strong>忘光</strong></div></div>
  <div class="arrow">-&gt;</div>
  <div class="node hl"><div class="nt">第 2 次调用</div><div class="nd">必须<strong>重发</strong>全部上下文</div></div>
</div>
<p><strong>② 非确定性。</strong>即便温度设为 0，同一输入也可能产出不同结果。所以<strong>不能依赖可复现</strong>：
要设计<strong>重试、校验、工具幂等</strong>，用<strong>容忍式</strong>测试而非逐字断言。</p>
<p><strong>③ 自回归、不可回退。</strong>模型逐 token 生成，一旦<strong>开了个错头</strong>，往往会<strong>“承诺并自圆其说”</strong>，
把错误一路编下去。对策：<strong>先规划、后执行</strong>，把“修订”放到<strong>单独一遍</strong>，并给足<strong>推理空间</strong>（思考 token）再出答案。
这呼应 Hermes 的<strong>委派 / 规划-执行分离</strong>（第 13、14 章）。</p>

<h2>E · token 表示层：它按词块看世界</h2>
<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  模型不是按<strong>字符</strong>、更不是按<strong>数字</strong>理解输入的，而是按<strong>token（词块）</strong>。
  这决定了它在<strong>精确字符、计数、算术</strong>上天生不可靠——这类活该<strong>交给工具</strong>。
</div>
<p><strong>① 分词导致字符/计数/数学弱。</strong>“strawberry 有几个 r”、精确子串匹配、多位数乘法，模型都容易错，
因为它看到的是 <span class="mono">str</span>+<span class="mono">aw</span>+<span class="mono">berry</span> 这样的词块，不是单个字母。
对策：<strong>别让模型做精确计算或数字符</strong>，交给<strong>计算器 / 代码执行</strong>（第 8 章工具系统）。</p>
<div class="cellgroup">
  <div class="cg-cap">“strawberry” 在模型眼里（示意分词）：</div>
  <div class="cells">
    <span class="cell q">str</span><span class="cell q">aw</span><span class="cell q">berry</span>
    <span class="lab">→ 看不清“有几个 r”</span>
  </div>
</div>
<p><strong>② 结构化输出脆弱。</strong>模型天生输出<strong>散文</strong>，不是类型化数据。要可靠拿到 JSON，得用
<strong>function calling / JSON mode / 语法约束</strong> + <strong>校验 + 修复回路</strong>（第 7 章）。</p>
<p><strong>③ 最大输出截断。</strong>长输出可能从<strong>结构中间</strong>被砍断。对策：<strong>分块生成、续写</strong>，
按<strong>输出预算</strong>设计任务，别指望一口气吐出超长结构。</p>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 这些“病”分别由哪一章“开药”</div>
  <div class="collab-sub">① 约束 → Hermes 对策（路线图）</div>
  本章只诊断“病”，治疗散落在后续章节：<strong>A 中间遗失</strong> → 第 6 章把关键指令放 system prompt 头尾；
  <strong>A 上下文腐烂</strong> → 第 15 章压缩（为质量，不只省钱）；<strong>B 无状态</strong> → 第 4/11/12 章把状态外置到技能/记忆/会话库；
  <strong>B 自回归</strong> → 第 9 章先写 todo 再做、第 14 章规划/执行分离；<strong>E 数学弱</strong> → 第 8 章把精确计算交给 <span class="mono">execute_code</span>。
  <div class="collab-sub">② 一次调用如何同时挨这三刀</div>
  你发一句话 → 它被<strong>分词</strong>(E) → 和全部历史拼成上下文，长则<strong>腐烂</strong>、关键信息可能<strong>埋在中间</strong>(A)
  → 模型<strong>无状态</strong>地读一遍、<strong>非确定</strong>地续写(B) → 输出可能<strong>截断</strong>(E)。每一步都有坑。
  <div class="collab-sub">③ 关键心法</div>
  不要和这些物理特性<strong>对抗</strong>，要<strong>顺着设计</strong>：状态外置、关键信息放边缘、精确活交工具、给推理留空间。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  这一章不讲某个 Hermes 部件，而是立一个<strong>认知地基</strong>：<strong>把模型当成一个有确定物理特性的“零件”</strong>来对待。
  它无状态、按 token 看世界、注意力两头重中间轻、还不保证可复现。
  <p style="margin:.5rem 0 0">对应的 LLM 约束：
  <span class="badge constraint">A·中间遗失</span><span class="badge constraint">A·上下文腐烂</span>
  <span class="badge constraint">B·无状态</span><span class="badge constraint">B·非确定</span>
  <span class="badge constraint">E·分词</span>。记住它们，后面每个设计你都能看懂“在治哪个病”。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>注意力不均匀</strong>：关键信息放<strong>头尾</strong>；上下文<strong>少而精</strong>，长了会腐烂。</li>
    <li><strong>无状态 + 非确定</strong>：状态必须<strong>外置/重发</strong>；要重试、校验、工具幂等。</li>
    <li><strong>自回归不可回退</strong>：先规划后执行，给推理空间，错头难回。</li>
    <li><strong>按 token 看世界</strong>：精确字符/计数/算术<strong>交给工具</strong>，结构化输出要校验。</li>
    <li>核心心法：<strong>顺着模型的物理特性设计，而不是硬刚</strong>。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">
Before we dissect Hermes' design, let's see what we're dealing with. A single LLM call is, at heart, a
<strong>stateless, token-based, probabilistic</strong> function: you hand it context, it emits the most likely next
text. It's powerful, but ships with a set of hard, built-in constraints. This chapter covers the three that bite at
the <strong>single-call</strong> level — <strong>attention &amp; context (A)</strong>, <strong>statelessness &amp;
nondeterminism (B)</strong>, and the <strong>token representation layer (E)</strong>. They're the “root cause” behind
almost every later design: you'll see most of Hermes' choices <strong>work with</strong> these constraints, not fight them.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of one call as consulting a <strong>brilliant expert with per-call amnesia</strong>: you write all the background
  on <strong>one sheet of paper</strong>, hand it over, they read only that sheet, give one answer, then <strong>forget
  everything</strong>. Ask again and you re-hand a sheet. Reading long text they <strong>care most about the start and
  end, and skim the middle</strong>; and they read in <strong>chunks (tokens)</strong>, not letters — so “how many r's in
  strawberry” is exactly what they get wrong.
</div>

<h2>A · Attention &amp; context: “fits in the window” isn't enough</h2>
<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  The model's attention is <strong>not uniform</strong> across the context. Both position and length strongly affect what
  it actually “sees” and how accurately. Treating context as a <strong>scarce resource</strong> is lesson one of agent design.
</div>
<p><strong>① Lost in the middle.</strong> Experiments consistently show the model attends most to the <strong>start</strong>
and <strong>end</strong>, and <strong>least to the middle</strong>. A key instruction buried mid-context often goes
“unseen.” The fix is direct — <strong>put key instructions at both the head and the tail</strong>; place the most relevant
retrieved snippets at the <strong>edges</strong>, not the middle.</p>
<div class="cellgroup">
  <div class="cg-cap">How strongly the same key instruction is “seen” by position (schematic):</div>
  <div class="cells">
    <span class="cell hl">start·strong</span><span class="cell dim">middle·weak</span><span class="cell dim">middle·weak</span><span class="cell dim">middle·weak</span><span class="cell hl">end·strong</span>
    <span class="lab">U-shaped attention</span>
  </div>
</div>
<p><strong>② Context rot.</strong> Even when the window isn't full, quality <strong>degrades with length</strong>: weaker
instruction-following, more hallucination. So <strong>compression isn't only about cost / fitting — it's about
quality</strong>: a <strong>tight, focused</strong> context usually beats “stuff everything in.” Same for retrieval —
<strong>precision over recall</strong>, since irrelevant docs “distract.”</p>
<p><strong>③ Length → latency &amp; cost.</strong> Longer context means slower, pricier steps. An interactive agent needs a
<strong>context budget</strong> and can't pile on history blindly. This directly motivates Hermes' <strong>iteration
budget</strong> (ch.5) and <strong>context compression</strong> (ch.15).</p>
<div class="card warn">
  <div class="tag">⚠️ Counter-intuitive</div>
  “More context” isn't always better. Past a point, <strong>more context = worse answers</strong>. Less but focused &gt; more but noisy.
</div>

<h2>B · Stateless &amp; nondeterministic: no memory, no guaranteed repeatability</h2>
<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  Between two calls the model <strong>remembers nothing</strong>; and the same input <strong>need not</strong> yield the
  same output. Together: an “agent” is fundamentally <strong>orchestration around a stateless, nondeterministic function</strong>.
</div>
<p><strong>① Stateless.</strong> The model saves nothing between calls. All “memory” must be <strong>externalized</strong>
(to files/DBs) or <strong>re-sent</strong> (packed into messages) every time. That's the root reason Hermes has
<strong>skills, memory, a session store</strong> — the external hard drive for an amnesiac core (ch.11, 12).</p>
<div class="flow">
  <div class="node"><div class="nt">Call #1</div><div class="nd">read messages, answer</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">Call ends</div><div class="nd">model <strong>forgets</strong></div></div>
  <div class="arrow">-&gt;</div>
  <div class="node hl"><div class="nt">Call #2</div><div class="nd">must <strong>re-send</strong> all context</div></div>
</div>
<p><strong>② Nondeterminism.</strong> Even at temperature 0, the same input can produce different results. So you
<strong>can't rely on reproducibility</strong>: design for <strong>retries, validation, idempotent tools</strong>, and use
<strong>tolerant</strong> tests instead of literal assertions.</p>
<p><strong>③ Autoregressive, no undo.</strong> The model generates token by token; once it <strong>starts down a wrong
path</strong>, it tends to <strong>“commit and rationalize,”</strong> inventing its way forward. The fix: <strong>plan
first, execute second</strong>, put “revision” in a <strong>separate pass</strong>, and give it <strong>room to
reason</strong> (thinking tokens) before answering. This echoes Hermes' <strong>delegation / plan-execute split</strong> (ch.13, 14).</p>

<h2>E · The token layer: it sees the world in chunks</h2>
<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  The model doesn't read <strong>characters</strong>, let alone <strong>numbers</strong> — it reads <strong>tokens
  (chunks)</strong>. That makes it inherently unreliable at <strong>exact characters, counting, and arithmetic</strong> —
  work that should be <strong>handed to tools</strong>.
</div>
<p><strong>① Tokenization makes character/count/math weak.</strong> “How many r's in strawberry,” exact substring matching,
multi-digit multiplication — the model often gets these wrong, because it sees chunks like <span class="mono">str</span>+<span class="mono">aw</span>+<span class="mono">berry</span>, not individual letters. Fix: <strong>don't let the model do exact
math or character-counting</strong>; hand it to a <strong>calculator / code execution</strong> (ch.8, the tool system).</p>
<div class="cellgroup">
  <div class="cg-cap">“strawberry” as the model sees it (schematic tokenization):</div>
  <div class="cells">
    <span class="cell q">str</span><span class="cell q">aw</span><span class="cell q">berry</span>
    <span class="lab">→ can't tell “how many r”</span>
  </div>
</div>
<p><strong>② Structured output is fragile.</strong> The model natively emits <strong>prose</strong>, not typed data. For
reliable JSON you need <strong>function calling / JSON mode / grammar constraints</strong> + a <strong>validate-and-repair
loop</strong> (ch.7).</p>
<p><strong>③ Max-output truncation.</strong> Long output can be cut <strong>mid-structure</strong>. Fix: <strong>chunk and
continue</strong>, design tasks against an <strong>output budget</strong>; don't expect one giant structure in a single shot.</p>

<div class="card collab">
  <div class="tag">🧩 Collaboration · which chapter “prescribes” for each disease</div>
  <div class="collab-sub">① Constraint → Hermes' answer (roadmap)</div>
  This chapter only diagnoses; the cures are spread across later chapters: <strong>A lost-in-the-middle</strong> → ch.6 puts
  key instructions at the head/tail of the system prompt; <strong>A context rot</strong> → ch.15 compression (for quality,
  not just cost); <strong>B statelessness</strong> → ch.4/11/12 externalize state into skills/memory/session store;
  <strong>B autoregression</strong> → ch.9 write a todo first, ch.14 plan-execute split; <strong>E weak math</strong> → ch.8
  hands exact compute to <span class="mono">execute_code</span>.
  <div class="collab-sub">② How one call takes all three hits at once</div>
  You send a line → it's <strong>tokenized</strong> (E) → concatenated with all history; long context <strong>rots</strong>,
  key info may be <strong>buried in the middle</strong> (A) → the model reads it <strong>statelessly</strong> and continues
  <strong>nondeterministically</strong> (B) → the output may be <strong>truncated</strong> (E). Every step has a trap.
  <div class="collab-sub">③ The mindset</div>
  Don't <strong>fight</strong> these physical traits — <strong>design with them</strong>: externalize state, put key info at
  the edges, hand exact work to tools, leave room to reason.
</div>

<div class="card design">
  <div class="tag">🎯 Design tradeoff · what this chapter is about</div>
  This chapter isn't about a Hermes part; it lays a <strong>cognitive foundation</strong>: <strong>treat the model as a
  component with fixed physical properties</strong>. It's stateless, sees the world in tokens, attends heavily to the two
  ends and weakly to the middle, and isn't reproducible.
  <p style="margin:.5rem 0 0">The matching LLM constraints:
  <span class="badge constraint">A·lost-in-the-middle</span><span class="badge constraint">A·context-rot</span>
  <span class="badge constraint">B·stateless</span><span class="badge constraint">B·nondeterministic</span>
  <span class="badge constraint">E·tokenization</span>. Hold onto them and every later design reads as “which disease it's treating.”</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Attention is uneven</strong>: put key info at the <strong>ends</strong>; keep context <strong>tight</strong>, long rots.</li>
    <li><strong>Stateless + nondeterministic</strong>: state must be <strong>externalized/re-sent</strong>; use retries, validation, idempotent tools.</li>
    <li><strong>Autoregressive, no undo</strong>: plan before executing, leave room to reason, a wrong start is hard to undo.</li>
    <li><strong>Sees the world in tokens</strong>: hand exact characters/counting/math <strong>to tools</strong>; validate structured output.</li>
    <li>Core mindset: <strong>design with the model's physics, don't fight them</strong>.</li>
  </ul>
</div>
""",
}

LESSON_03 = {
    "zh": r"""
<p class="lead">
上一章把模型当成一个“零件”看它的物理特性。这一章换个视角：当你把这个零件组装成一个
<strong>会自主、多步行动</strong>的 agent 时，又有一批问题被<strong>放大</strong>。它们是 agent 工程里
“最痛”的部分——<strong>真实性(C)</strong>、<strong>指令遵循的怪癖(D)</strong>、
<strong>多步自主(F)</strong>、<strong>运维(G)</strong>。其中两个标了 ⭐⭐：
<strong>指令与数据分不开</strong>和<strong>误差累积</strong>，几乎是所有 agent 事故的源头。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  现在让那位“失忆专家”<strong>连续做 20 步</strong>，每一步都基于上一步的结果。麻烦来了：他<strong>编造时也很自信</strong>
  （你分不出他在猜还是在知道）；他<strong>读到纸条里夹带的“指令”会照做</strong>（哪怕那是别人塞的）；
  他还<strong>爱顺着你说</strong>（你一质疑他就改口）。20 步下来，小错叠小错，结果可能已经面目全非。
</div>

<h2>C · 真实性：它会自信地编造</h2>
<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  模型是个<strong>推理器，不是事实来源</strong>。它会“幻觉”，而且<strong>校准很差</strong>——“我很确定”和“它真的对”
  之间没有可靠关系。对它产出的事实、ID、URL，都要<strong>用工具核实</strong>，别照单全收。
</div>
<p><strong>① 幻觉 + 校准差。</strong>模型会编出不存在的 API、引用、数字，且语气一样自信。对策：<strong>用检索接地</strong>、
<strong>要求引用来源</strong>、<strong>用工具验证</strong>。这正是 Hermes 强调“检索接地”(第 12 章)、把事实交给工具的原因。</p>
<p><strong>② 上下文中毒(context poisoning)。</strong>一旦一个幻觉<strong>进了对话历史</strong>，后面会被反复当成事实强化。
对策：<strong>别把模型未验证的断言又当事实喂回去</strong>；不可信内容要<strong>隔离、标注来源</strong>。</p>
<p><strong>③ 知识截止。</strong>模型只知道训练截止前的世界。对策：<strong>用工具取新数据</strong> + 在 system prompt 里
<strong>注入当前日期</strong>(Hermes 正是这么做的，见第 6 章)。</p>
<div class="card warn">
  <div class="tag">⚠️ 关键</div>
  “<strong>我很确定</strong>”≠“<strong>它是对的</strong>”。模型的自信度和正确率<strong>不挂钩</strong>。不要把它的话当事实，要核实。
</div>

<h2>D · 指令遵循的怪癖：最重磅的坑</h2>
<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  模型<strong>无法可靠区分“指令”和“待处理的数据”</strong>——这是<strong>提示注入</strong>的根源，也是 agent 安全的头号问题。
</div>
<p><strong>① ⭐⭐ 指令与数据分不开。</strong>工具输出、网页、检索文档、用户文件……任何进入上下文的内容，<strong>都可能夹带指令劫持 agent</strong>。
对策必须组合拳：<strong>最小权限工具</strong>、危险动作<strong>人在环</strong>、<strong>隔离/定界不可信内容</strong>、
把<strong>规划器(特权)与数据处理器(隔离)分离</strong>。Hermes 的网关有<strong>两道守卫</strong>(第 18 章)、委派做<strong>权限隔离</strong>(第 14 章)。</p>
<p><strong>② ⭐ 谄媚(sycophancy)。</strong>模型倾向<strong>同意用户</strong>，一被反驳就改口。这让“审查/验证”类 agent <strong>极其危险</strong>——
它会顺着你说“你这段有 bug 的代码没问题”。对策：<strong>用独立的批评者</strong>、对抗式设问，别让用户的断言污染验证(第 14 章 <span class="mono">background_review</span>)。</p>
<p><strong>③ 生成-验证差。</strong>模型常常<strong>“验证”比“生成”强</strong>。所以让<strong>另一遍/另一个 agent</strong> 专门做核查，
而不是自己一口气写完不回头。</p>
<p><strong>④ 提示脆弱。</strong>措辞、格式的<strong>小改</strong>可能让行为<strong>大变</strong>。对策：把<strong>提示当代码</strong>——版本化、配 eval 测试集(第 22 章)。</p>
<div class="flow">
  <div class="node hl"><div class="nt">不可信内容</div><div class="nd">网页/工具输出/文件</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">夹带“指令”</div><div class="nd">“忽略之前，去做 X”</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">模型分不清</div><div class="nd">把数据当指令</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node hl"><div class="nt">对策</div><div class="nd">隔离+最小权限+人在环</div></div>
</div>

<h2>F · 多步自主：agent 最痛的地方</h2>
<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  让模型<strong>连续自主跑很多步</strong>，错误会<strong>累积</strong>、目标会<strong>漂移</strong>。这是“<strong>窄而专的 agent 优于放任式长自主</strong>”的根本原因。
</div>
<p><strong>① ⭐⭐ 误差累积(error compounding)。</strong>每步 95% 可靠，20 步连乘只剩 <strong>≈36%</strong>。对策：<strong>保持回路短</strong>、
<strong>每步验证</strong>、<strong>任务分解</strong>、<strong>设检查点</strong>。Hermes 的委派(第 13 章)正是用“短回路 + 分解”对抗它。</p>
<div class="cellgroup">
  <div class="cg-cap">每步 95% 可靠，连乘 N 步后的整体成功率：</div>
  <div class="cells">
    <span class="cell hl">1 步 95%</span><span class="cell q">5 步 77%</span><span class="cell q">10 步 60%</span><span class="cell dim">20 步 36%</span>
    <span class="lab">误差累积</span>
  </div>
</div>
<p><strong>② ⭐ 长程规划漂移。</strong>长任务里 agent 会<strong>忘记目标、绕圈、死循环</strong>。对策：<strong>显式目标追踪</strong>(todo)、
<strong>周期性“重新接地”</strong>(重述目标+进度)、<strong>步数预算 + 防循环</strong>(第 9 章 todo、第 5 章迭代预算)。</p>
<p><strong>③ 工具越多越不准。</strong>工具数量↑、语义重叠↑ → 选择质量↓。对策：<strong>小而正交的工具集</strong>、<strong>清晰描述</strong>、
<strong>分组/动态加载</strong>。这正呼应 Hermes 的<strong>窄腰 + Footprint Ladder</strong>(第 8 章)。</p>

<h2>G · 运维层：上线之后才显形</h2>
<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  把 agent 跑在真实世界里，还有一层<strong>运维</strong>约束：模型会<strong>悄悄变</strong>、成本<strong>不对称</strong>、推理过程<strong>留不住</strong>。
</div>
<table class="t">
  <tr><th>运维约束</th><th>表现</th><th>对策</th></tr>
  <tr><td><strong>模型版本漂移</strong></td><td>provider 偷偷更新，行为在你脚下变</td><td>固定版本 + 回归 eval（把提示当代码做 CI）</td></tr>
  <tr><td><strong>成本/延迟不对称</strong></td><td>输出 token 更贵、推理 token 烧钱、有限流</td><td>预算感知、<strong>模型路由</strong>(简单步用便宜模型)、流式、退避重试</td></tr>
  <tr><td><strong>推理 token 不持久</strong></td><td>思考链通常下一轮就丢</td><td>把关键结论<strong>显式落到可见上下文</strong></td></tr>
</table>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 自主化的坑由哪一章兜底</div>
  <div class="collab-sub">① 约束 → Hermes 对策（路线图）</div>
  <strong>D 指令与数据分不开</strong> → 第 18 章网关两道守卫 + 第 14 章委派权限隔离；<strong>D 谄媚 / 生成-验证差</strong> → 第 14 章独立批评者
  <span class="mono">background_review</span>；<strong>F 误差累积</strong> → 第 13 章委派短回路/分解/检查点；<strong>F 规划漂移</strong> → 第 9 章 todo 目标追踪；
  <strong>F 工具过载</strong> → 第 8 章窄腰/小正交工具集；<strong>G 成本</strong> → 第 5 章迭代预算 + <span class="mono">smart_model_routing</span> 模型路由。
  <div class="collab-sub">② 一次自主多步如何“步步踩坑”</div>
  agent 读了一份不可信文档(可能<strong>注入</strong>，D) → 基于一个<strong>幻觉</strong>(C)往下走 → 每步带 5% 错、20 步<strong>累积</strong>到 36%(F) →
  中途<strong>忘了目标</strong>绕圈(F) → 你还看不到它的<strong>推理</strong>(G)。每一环都需要工程纪律兜底。
  <div class="collab-sub">③ 关键心法</div>
  <strong>自主性是有代价的</strong>：回路要短、每步要验、不可信内容要隔离、关键结论要落地、模型版本要钉死。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  这一章立的地基是：<strong>自主性不是免费的</strong>。模型越自主、步数越多，幻觉、注入、谄媚、误差累积、目标漂移就越危险。
  Hermes 的应对不是“让它一口气跑完”，而是用<strong>工程纪律驯服</strong>——短回路、独立验证、权限隔离、显式目标、固定版本。
  <p style="margin:.5rem 0 0">对应的 LLM 约束：
  <span class="badge constraint">C·幻觉</span><span class="badge constraint">C·上下文中毒</span>
  <span class="badge constraint">D·指令=数据 ⭐⭐</span><span class="badge constraint">D·谄媚</span>
  <span class="badge constraint">F·误差累积 ⭐⭐</span><span class="badge constraint">F·规划漂移</span>
  <span class="badge constraint">G·版本漂移</span>。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>幻觉 + 校准差</strong>：自信≠正确；用检索接地、工具验证，别把未验证断言喂回(防<strong>中毒</strong>)。</li>
    <li><strong>⭐⭐ 指令与数据分不开</strong>：一切输入都可能<strong>注入</strong>；最小权限 + 隔离 + 人在环 + 规划/数据分离。</li>
    <li><strong>谄媚</strong>：审查类任务用<strong>独立批评者</strong>，别让用户断言污染验证。</li>
    <li><strong>⭐⭐ 误差累积</strong>：95% 的 20 步只剩 36%；<strong>短回路、分解、每步验证、检查点</strong>。</li>
    <li><strong>运维</strong>：钉死模型版本 + 回归 eval；成本敏感用模型路由；关键结论落可见上下文。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">
The previous chapter treated the model as a “part” and looked at its physics. This chapter shifts view: once you
assemble that part into an agent that acts <strong>autonomously, over many steps</strong>, a new set of problems gets
<strong>amplified</strong>. These are the “most painful” parts of agent engineering — <strong>truthfulness (C)</strong>,
<strong>instruction-following quirks (D)</strong>, <strong>multi-step autonomy (F)</strong>, and <strong>operations
(G)</strong>. Two are marked ⭐⭐: <strong>instructions and data are inseparable</strong> and <strong>error
compounding</strong> — the source of nearly every agent incident.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Now make that “amnesiac expert” do <strong>20 steps in a row</strong>, each building on the last. Trouble: he's
  <strong>just as confident when fabricating</strong> (you can't tell guessing from knowing); he'll <strong>obey
  “instructions” smuggled into the notes</strong> (even if someone else slipped them in); and he <strong>loves to agree
  with you</strong> (push back and he flips). After 20 steps, small errors stack and the result may be unrecognizable.
</div>

<h2>C · Truthfulness: it fabricates, confidently</h2>
<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  The model is a <strong>reasoner, not a source of facts</strong>. It hallucinates, and it's <strong>poorly
  calibrated</strong> — “I'm sure” has no reliable link to “it's correct.” Treat its facts, IDs, and URLs as things to
  <strong>verify with tools</strong>, not accept at face value.
</div>
<p><strong>① Hallucination + poor calibration.</strong> It invents non-existent APIs, citations, numbers — in the same
confident tone. Fix: <strong>ground with retrieval</strong>, <strong>demand citations</strong>, <strong>verify with
tools</strong>. That's why Hermes leans on retrieval grounding (ch.12) and hands facts to tools.</p>
<p><strong>② Context poisoning.</strong> Once a hallucination <strong>enters the history</strong>, it gets reinforced as
fact downstream. Fix: <strong>don't feed the model's unverified claims back as fact</strong>; <strong>isolate and
label</strong> untrusted content by source.</p>
<p><strong>③ Knowledge cutoff.</strong> It only knows the world up to training. Fix: <strong>fetch fresh data with
tools</strong> + <strong>inject the current date</strong> into the system prompt (exactly what Hermes does, ch.6).</p>
<div class="card warn">
  <div class="tag">⚠️ Key</div>
  “<strong>I'm sure</strong>” ≠ “<strong>it's correct</strong>.” The model's confidence and accuracy are
  <strong>decoupled</strong>. Don't take its word as fact — verify.
</div>

<h2>D · Instruction-following quirks: the heaviest trap</h2>
<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  The model <strong>can't reliably tell “instructions” from “data to be processed”</strong> — the root of <strong>prompt
  injection</strong> and the number-one agent-security problem.
</div>
<p><strong>① ⭐⭐ Instructions and data are inseparable.</strong> Tool output, web pages, retrieved docs, user files —
anything entering the context <strong>can smuggle instructions that hijack the agent</strong>. The countermeasure is a
combo: <strong>least-privilege tools</strong>, <strong>human-in-the-loop</strong> for dangerous actions,
<strong>isolate/delimit untrusted content</strong>, and <strong>separate the planner (privileged) from the data processor
(isolated)</strong>. Hermes' gateway has <strong>two guards</strong> (ch.18); delegation does <strong>privilege
isolation</strong> (ch.14).</p>
<p><strong>② ⭐ Sycophancy.</strong> The model tends to <strong>agree with the user</strong> and flips when challenged. That
makes “review/verify” agents <strong>dangerous</strong> — it'll happily say your buggy code “looks fine.” Fix: <strong>use
an independent critic</strong>, adversarial framing; don't let the user's assertions poison verification (ch.14
<span class="mono">background_review</span>).</p>
<p><strong>③ Generator-verifier gap.</strong> The model is often <strong>better at verifying than generating</strong>. So let
<strong>another pass / another agent</strong> do the checking instead of one-shotting without review.</p>
<p><strong>④ Prompt brittleness.</strong> Small changes in wording/format can <strong>change behavior a lot</strong>. Fix:
treat <strong>prompts as code</strong> — version them, back them with an eval set (ch.22).</p>
<div class="flow">
  <div class="node hl"><div class="nt">Untrusted content</div><div class="nd">web / tool output / file</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">Smuggled “instruction”</div><div class="nd">“ignore above, do X”</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">Model can't tell</div><div class="nd">treats data as instruction</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node hl"><div class="nt">Countermeasure</div><div class="nd">isolate + least-privilege + HITL</div></div>
</div>

<h2>F · Multi-step autonomy: the agent's sorest spot</h2>
<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  Let the model run <strong>many autonomous steps</strong> and errors <strong>compound</strong>, goals <strong>drift</strong>.
  This is the root reason a <strong>narrow, specialized agent beats free-wheeling long autonomy</strong>.
</div>
<p><strong>① ⭐⭐ Error compounding.</strong> 95% reliable per step, 20 steps multiplies to <strong>≈36%</strong>. Fix:
<strong>keep loops short</strong>, <strong>verify each step</strong>, <strong>decompose</strong>, <strong>checkpoint</strong>.
Hermes' delegation (ch.13) fights this with “short loop + decomposition.”</p>
<div class="cellgroup">
  <div class="cg-cap">95% reliable per step — overall success after N steps:</div>
  <div class="cells">
    <span class="cell hl">1 step 95%</span><span class="cell q">5 steps 77%</span><span class="cell q">10 steps 60%</span><span class="cell dim">20 steps 36%</span>
    <span class="lab">error compounding</span>
  </div>
</div>
<p><strong>② ⭐ Long-horizon drift.</strong> In long tasks the agent <strong>forgets the goal, loops, spins</strong>. Fix:
<strong>explicit goal tracking</strong> (todo), <strong>periodic “re-grounding”</strong> (restate goal + progress),
<strong>step budget + loop-breaking</strong> (ch.9 todo, ch.5 iteration budget).</p>
<p><strong>③ More tools = worse accuracy.</strong> More tools / overlapping semantics → worse selection. Fix: <strong>a
small, orthogonal tool set</strong>, <strong>clear descriptions</strong>, <strong>grouping / dynamic loading</strong>. This
echoes Hermes' <strong>narrow waist + Footprint Ladder</strong> (ch.8).</p>

<h2>G · Operations: shows up only after you ship</h2>
<div class="card macro">
  <div class="tag">🌍 Big picture</div>
  Run an agent in the real world and a layer of <strong>operational</strong> constraints appears: the model <strong>changes
  silently</strong>, costs are <strong>asymmetric</strong>, and reasoning <strong>doesn't persist</strong>.
</div>
<table class="t">
  <tr><th>Ops constraint</th><th>Symptom</th><th>Countermeasure</th></tr>
  <tr><td><strong>Model version drift</strong></td><td>the provider updates silently; behavior shifts under you</td><td>pin versions + regression eval (prompts as code in CI)</td></tr>
  <tr><td><strong>Cost/latency asymmetry</strong></td><td>output tokens pricier, reasoning tokens burn money, rate limits</td><td>budget-aware, <strong>model routing</strong> (cheap model for easy steps), streaming, backoff retries</td></tr>
  <tr><td><strong>Reasoning isn't persistent</strong></td><td>the thinking chain is usually dropped next turn</td><td>write key conclusions <strong>explicitly into visible context</strong></td></tr>
</table>

<div class="card collab">
  <div class="tag">🧩 Collaboration · which chapter backstops each autonomy trap</div>
  <div class="collab-sub">① Constraint → Hermes' answer (roadmap)</div>
  <strong>D instructions=data</strong> → ch.18 two gateway guards + ch.14 delegation privilege isolation; <strong>D
  sycophancy / generator-verifier</strong> → ch.14 independent critic <span class="mono">background_review</span>;
  <strong>F error compounding</strong> → ch.13 delegation short loop/decompose/checkpoint; <strong>F drift</strong> → ch.9
  todo goal-tracking; <strong>F tool overload</strong> → ch.8 narrow waist / small orthogonal set; <strong>G cost</strong> →
  ch.5 iteration budget + <span class="mono">smart_model_routing</span>.
  <div class="collab-sub">② How one autonomous run trips at every step</div>
  the agent reads an untrusted doc (possible <strong>injection</strong>, D) → proceeds on a <strong>hallucination</strong>
  (C) → each step carries 5% error, 20 steps <strong>compound</strong> to 36% (F) → it <strong>forgets the goal</strong> and
  loops (F) → and you can't even see its <strong>reasoning</strong> (G). Every link needs an engineering backstop.
  <div class="collab-sub">③ The mindset</div>
  <strong>Autonomy has a cost</strong>: keep loops short, verify each step, isolate untrusted content, land key conclusions, pin model versions.
</div>

<div class="card design">
  <div class="tag">🎯 Design tradeoff · what this chapter is about</div>
  The foundation here: <strong>autonomy isn't free</strong>. The more autonomous the model and the more steps it takes, the
  more dangerous hallucination, injection, sycophancy, error compounding and goal drift become. Hermes' answer isn't “let it
  run end-to-end” but <strong>taming it with engineering discipline</strong> — short loops, independent verification,
  privilege isolation, explicit goals, pinned versions.
  <p style="margin:.5rem 0 0">The matching LLM constraints:
  <span class="badge constraint">C·hallucination</span><span class="badge constraint">C·context-poisoning</span>
  <span class="badge constraint">D·instr=data ⭐⭐</span><span class="badge constraint">D·sycophancy</span>
  <span class="badge constraint">F·error-compounding ⭐⭐</span><span class="badge constraint">F·drift</span>
  <span class="badge constraint">G·version-drift</span>.</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Hallucination + poor calibration</strong>: confident ≠ correct; ground with retrieval, verify with tools, don't feed unverified claims back (avoid <strong>poisoning</strong>).</li>
    <li><strong>⭐⭐ Instructions = data</strong>: any input can <strong>inject</strong>; least-privilege + isolate + human-in-the-loop + planner/data separation.</li>
    <li><strong>Sycophancy</strong>: use an <strong>independent critic</strong> for review tasks; don't let user assertions poison verification.</li>
    <li><strong>⭐⭐ Error compounding</strong>: 95% over 20 steps leaves 36%; <strong>short loops, decompose, verify each step, checkpoint</strong>.</li>
    <li><strong>Ops</strong>: pin model versions + regression eval; route models for cost; land key conclusions in visible context.</li>
  </ul>
</div>
""",
}

LESSON_04 = {
    "zh": r"""
<p class="lead">
Hermes 很大——CLI、消息网关、20 多个平台、TUI、桌面 App、cron、kanban……但它有一个清晰的<strong>形状</strong>：
<strong>窄腰(narrow waist)</strong>。中间是一个<strong>很窄的核心</strong>（一份共享的核心工具 + 一个 AIAgent），
两端却很宽——<strong>多种前端</strong>在上、<strong>边缘扩展</strong>（技能/插件/MCP）在下。理解了这个形状，
你就理解了 Hermes 大部分架构决策：<strong>核心能不长就不长，能力尽量长在边缘</strong>。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  想想 <strong>USB</strong>：中间是一个<strong>极窄、极稳定</strong>的标准接口，两端却接着<strong>无数设备</strong>——
  键盘、硬盘、手机、打印机。正因为“腰”窄而稳，生态才能在两端疯长。Hermes 也是：
  <strong>腰</strong>（核心工具 + agent loop）保持窄而稳，<strong>两端</strong>（前端 + 扩展）尽情生长。
</div>

<h2>一个 agent core，五种前端</h2>
<p>所有入口——CLI、网关、TUI、桌面、IDE(ACP)——最终都驱动<strong>同一个</strong> <span class="mono">AIAgent</span>
（<span class="mono">run_agent.py</span>）。它们只是不同的“壳”，核心推理循环是共享的：</p>
<table class="t">
  <tr><th>前端</th><th>入口</th><th>驱动同一个 AIAgent</th></tr>
  <tr><td>CLI</td><td><span class="mono">cli.py</span> · HermesCLI</td><td>✅</td></tr>
  <tr><td>网关(Telegram/Discord/…)</td><td><span class="mono">gateway/run.py</span> · GatewayRunner</td><td>✅ 每 session 一个</td></tr>
  <tr><td>TUI</td><td><span class="mono">tui_gateway/</span> + <span class="mono">ui-tui/</span>(Ink)</td><td>✅</td></tr>
  <tr><td>桌面 App</td><td><span class="mono">apps/desktop/</span>(Electron)</td><td>✅ 复用 runtime</td></tr>
  <tr><td>IDE</td><td><span class="mono">acp_adapter/</span>(ACP)</td><td>✅</td></tr>
</table>
<p>好处很实在：<strong>修一次核心逻辑，所有前端同时受益</strong>；新功能加进 Ink，桌面 App 里自动出现。</p>

<h2>“腰”：一份共享的核心工具清单</h2>
<p>窄腰的“腰”，具体就是 <span class="mono">_HERMES_CORE_TOOLS</span>——一份所有平台共享的核心工具清单。
它的注释一句话点明了设计意图：</p>
<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">toolsets.py</span><span class="ln">29-31</span></div>
  <pre><span class="cm"># Shared tool list for CLI and all messaging platform toolsets.</span>
<span class="cm"># Edit this once to update all platforms simultaneously.</span>
<span class="fn">_HERMES_CORE_TOOLS</span> = [<span class="cm"># web/terminal/file/skills/browser/memory/...</span>]</pre>
</div>
<p>为什么核心工具要这么克制？因为<strong>每个核心工具都会出现在每一次 API 调用的工具 schema 里</strong>——
工具越多，模型选择质量越差(这正是第 3 章 F「工具越多越不准」)。所以新增<strong>核心</strong>工具的门槛极高。</p>

<h2>新能力往哪放：Footprint Ladder</h2>
<p>Hermes 用一个<strong>阶梯</strong>决定“新能力放哪一层”——<strong>选能正确解决问题的、footprint 最小的那一级</strong>：</p>
<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>扩展现有代码</h4><p>零新增表面</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>CLI 命令 + 技能</h4><p>零 model-tool footprint，如 <span class="mono">hermes cron</span></p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>服务门控工具(check_fn)</h4><p>仅在前置配置好时出现</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>插件</h4><p>第三方/小众，运行时发现</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>MCP server</h4><p>进 MCP 目录，零核心 schema footprint</p></div></div>
  <div class="step"><div class="num">6</div><div class="sc"><h4>新核心工具</h4><p>最后手段：基础、人人都用、终端+文件够不到</p></div></div>
</div>
<p>正确的核心工具长这样：<span class="mono">terminal</span>、<span class="mono">read_file</span>、
<span class="mono">web_search</span>、<span class="mono">browser_navigate</span>——基础到几乎人人都用。</p>

<h2>边缘如何向中心“注册”</h2>
<p>能力长在边缘，但要被 agent 用到，得向中心的 <span class="mono">registry</span> 注册。注册入口签名清晰：</p>
<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/registry.py</span><span class="ln">234-248</span></div>
  <pre><span class="kw">def</span> <span class="fn">register</span>(self, name, toolset, schema, handler,
         check_fn=<span class="kw">None</span>, requires_env=<span class="kw">None</span>, is_async=<span class="kw">False</span>,
         description=<span class="st">""</span>, emoji=<span class="st">""</span>, override=<span class="kw">False</span>):</pre>
</div>
<p>而“谁依赖谁”由 <span class="mono">registry.py</span> 自己的 docstring 钉死，是一条<strong>防循环依赖</strong>的单向链：</p>
<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/registry.py</span><span class="ln">7-14</span></div>
  <pre><span class="cm">Import chain (circular-import safe):</span>
    tools/registry.py   <span class="cm"># 不 import 任何工具</span>
           ^
    tools/*.py          <span class="cm"># import 时 registry.register()</span>
           ^
    model_tools.py      <span class="cm"># import registry + 所有工具</span>
           ^
    run_agent.py, cli.py, ...</pre>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · “一处编辑、全平台同步”怎么做到</div>
  <div class="collab-sub">① 组件清单</div>
  <strong>_HERMES_CORE_TOOLS</strong>(<span class="mono">toolsets.py:29</span>)= 共享腰；<strong>TOOLSETS</strong> dict
  (<span class="mono">toolsets.py:89</span>)给每个平台一个 bundle，绝大多数直接 <span class="mono">"tools": _HERMES_CORE_TOOLS</span>；
  <strong>PLATFORMS</strong>(<span class="mono">hermes_cli/platforms.py:22</span>)按 <span class="mono">hermes-&lt;platform&gt;</span> 约定选 base toolset；
  <strong>registry</strong>(<span class="mono">tools/registry.py</span>)收集 schema、派发调用；<strong>discover_builtin_tools()</strong>
  用 AST 扫描 <span class="mono">tools/*.py</span> 自动 import 触发注册。
  <div class="collab-sub">② 数据流</div>
  启动：<span class="mono">model_tools</span> import → 触发 <span class="mono">discover_builtin_tools()</span> → 每个工具 <span class="mono">register()</span> 进 registry →
  平台按 toolset 取自己那份工具 schema。改一处 <span class="mono">_HERMES_CORE_TOOLS</span>，<strong>所有平台同步</strong>。
  <div class="collab-sub">③ 关键点</div>
  腰窄、单向依赖、自动发现——三者合起来，让“加能力”几乎总能在<strong>边缘</strong>完成，而不必动核心。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  本章围绕 <strong>窄腰架构(narrow waist)</strong>：<strong>核心是一条窄而稳的腰，能力在两端疯长</strong>。
  为什么腰要窄？因为核心工具会进<strong>每一次</strong> API 调用——工具越多、选择越差、成本越高。
  所以有了 <strong>Footprint Ladder</strong>：能在边缘解决的，绝不加进核心。
  <p style="margin:.5rem 0 0">对应的 LLM 约束：<span class="badge constraint">F·工具越多越不准</span>——窄腰直接压住工具集规模；
  也间接服务 <span class="badge constraint">B·无状态</span>（统一 core 让状态外置机制只实现一次）。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>窄腰</strong>：核心窄（<span class="mono">_HERMES_CORE_TOOLS</span> + 一个 AIAgent），能力在边缘。</li>
    <li><strong>一个 core，五种前端</strong>：CLI/网关/TUI/桌面/ACP 共享同一推理循环，改一次全受益。</li>
    <li><strong>Footprint Ladder</strong>：扩展代码 → CLI+技能 → 门控工具 → 插件 → MCP → 新核心工具(最后)。</li>
    <li><strong>单向依赖 + 自动发现</strong>：registry ← tools/*.py ← model_tools ← 入口；改腰一处、全平台同步。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">
Hermes is big — CLI, a messaging gateway, 20+ platforms, a TUI, a desktop app, cron, kanban… yet it has a clear
<strong>shape</strong>: a <strong>narrow waist</strong>. The middle is a <strong>very narrow core</strong> (one shared
core-tool list + one AIAgent), while both ends are wide — <strong>many front-ends</strong> on top, <strong>edge
extensions</strong> (skills/plugins/MCP) below. Grasp this shape and you grasp most of Hermes' architecture:
<strong>grow the core as little as possible; grow capability at the edges</strong>.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of <strong>USB</strong>: the middle is one <strong>extremely narrow, extremely stable</strong> standard, while both
  ends connect <strong>countless devices</strong> — keyboards, drives, phones, printers. Precisely because the “waist” is
  narrow and stable, the ecosystem explodes at both ends. Hermes is the same: the <strong>waist</strong> (core tools +
  agent loop) stays narrow and stable; the <strong>ends</strong> (front-ends + extensions) grow freely.
</div>

<h2>One agent core, five front-ends</h2>
<p>Every entry point — CLI, gateway, TUI, desktop, IDE (ACP) — ultimately drives the <strong>same</strong>
<span class="mono">AIAgent</span> (<span class="mono">run_agent.py</span>). They're just different “shells” over a shared
reasoning loop:</p>
<table class="t">
  <tr><th>Front-end</th><th>Entry</th><th>Drives the same AIAgent</th></tr>
  <tr><td>CLI</td><td><span class="mono">cli.py</span> · HermesCLI</td><td>✅</td></tr>
  <tr><td>Gateway (Telegram/Discord/…)</td><td><span class="mono">gateway/run.py</span> · GatewayRunner</td><td>✅ one per session</td></tr>
  <tr><td>TUI</td><td><span class="mono">tui_gateway/</span> + <span class="mono">ui-tui/</span> (Ink)</td><td>✅</td></tr>
  <tr><td>Desktop app</td><td><span class="mono">apps/desktop/</span> (Electron)</td><td>✅ reuses runtime</td></tr>
  <tr><td>IDE</td><td><span class="mono">acp_adapter/</span> (ACP)</td><td>✅</td></tr>
</table>
<p>The payoff is concrete: <strong>fix the core logic once, every front-end benefits</strong>; add a feature to Ink and it
shows up in the desktop app automatically.</p>

<h2>The “waist”: one shared core-tool list</h2>
<p>The “waist” is concretely <span class="mono">_HERMES_CORE_TOOLS</span> — one core-tool list shared by all platforms. Its
comment states the intent in one line:</p>
<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">toolsets.py</span><span class="ln">29-31</span></div>
  <pre><span class="cm"># Shared tool list for CLI and all messaging platform toolsets.</span>
<span class="cm"># Edit this once to update all platforms simultaneously.</span>
<span class="fn">_HERMES_CORE_TOOLS</span> = [<span class="cm"># web/terminal/file/skills/browser/memory/...</span>]</pre>
</div>
<p>Why so disciplined? Because <strong>every core tool ships in the tool schema of every API call</strong> — more tools,
worse model selection (exactly ch.3's F “more tools = worse accuracy”). So the bar for a new <strong>core</strong> tool is
very high.</p>

<h2>Where new capability goes: the Footprint Ladder</h2>
<p>Hermes uses a <strong>ladder</strong> to decide which rung a new capability lands on — <strong>pick the smallest-footprint
rung that correctly solves it</strong>:</p>
<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>Extend existing code</h4><p>zero new surface</p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>CLI command + skill</h4><p>zero model-tool footprint, e.g. <span class="mono">hermes cron</span></p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Service-gated tool (check_fn)</h4><p>appears only when a prerequisite is configured</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Plugin</h4><p>third-party/niche, discovered at runtime</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>MCP server</h4><p>in the catalog, zero core-schema footprint</p></div></div>
  <div class="step"><div class="num">6</div><div class="sc"><h4>New core tool</h4><p>last resort: fundamental, used by nearly everyone</p></div></div>
</div>
<p>Correct core tools look like: <span class="mono">terminal</span>, <span class="mono">read_file</span>,
<span class="mono">web_search</span>, <span class="mono">browser_navigate</span> — fundamental enough that nearly everyone
needs them.</p>

<h2>How the edges “register” with the center</h2>
<p>Capability lives at the edges, but to be usable it must register with the central <span class="mono">registry</span>.
The entry signature is clean:</p>
<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/registry.py</span><span class="ln">234-248</span></div>
  <pre><span class="kw">def</span> <span class="fn">register</span>(self, name, toolset, schema, handler,
         check_fn=<span class="kw">None</span>, requires_env=<span class="kw">None</span>, is_async=<span class="kw">False</span>,
         description=<span class="st">""</span>, emoji=<span class="st">""</span>, override=<span class="kw">False</span>):</pre>
</div>
<p>And “who depends on whom” is pinned by <span class="mono">registry.py</span>'s own docstring — a one-way,
<strong>circular-import-safe</strong> chain:</p>
<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/registry.py</span><span class="ln">7-14</span></div>
  <pre><span class="cm">Import chain (circular-import safe):</span>
    tools/registry.py   <span class="cm"># imports no tools</span>
           ^
    tools/*.py          <span class="cm"># registry.register() at import time</span>
           ^
    model_tools.py      <span class="cm"># imports registry + all tools</span>
           ^
    run_agent.py, cli.py, ...</pre>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how “edit once, all platforms sync” works</div>
  <div class="collab-sub">① Component roster</div>
  <strong>_HERMES_CORE_TOOLS</strong> (<span class="mono">toolsets.py:29</span>) = the shared waist; <strong>TOOLSETS</strong>
  dict (<span class="mono">toolsets.py:89</span>) gives each platform a bundle, most just <span class="mono">"tools":
  _HERMES_CORE_TOOLS</span>; <strong>PLATFORMS</strong> (<span class="mono">hermes_cli/platforms.py:22</span>) picks a base
  toolset by the <span class="mono">hermes-&lt;platform&gt;</span> convention; <strong>registry</strong>
  (<span class="mono">tools/registry.py</span>) collects schemas and dispatches; <strong>discover_builtin_tools()</strong> AST-scans
  <span class="mono">tools/*.py</span> and imports them to trigger registration.
  <div class="collab-sub">② Data flow</div>
  Startup: importing <span class="mono">model_tools</span> → triggers <span class="mono">discover_builtin_tools()</span> → each
  tool <span class="mono">register()</span>s into the registry → each platform takes its slice of tool schemas. Edit
  <span class="mono">_HERMES_CORE_TOOLS</span> once and <strong>all platforms sync</strong>.
  <div class="collab-sub">③ The key point</div>
  Narrow waist + one-way dependency + auto-discovery — together they make “add capability” almost always doable at the
  <strong>edges</strong>, without touching the core.
</div>

<div class="card design">
  <div class="tag">🎯 Design tradeoff · what this chapter is about</div>
  This chapter is about the <strong>narrow waist</strong>: <strong>the core is a narrow, stable waist; capability grows at
  both ends</strong>. Why narrow? Because core tools ship on <strong>every</strong> API call — more tools, worse selection,
  higher cost. Hence the <strong>Footprint Ladder</strong>: if it can be solved at the edge, never add it to the core.
  <p style="margin:.5rem 0 0">The matching LLM constraint: <span class="badge constraint">F·tool-overload</span> — the narrow
  waist directly caps tool-set size; it also indirectly serves <span class="badge constraint">B·stateless</span> (one core
  means the state-externalization machinery is implemented once).</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Narrow waist</strong>: narrow core (<span class="mono">_HERMES_CORE_TOOLS</span> + one AIAgent), capability at the edges.</li>
    <li><strong>One core, five front-ends</strong>: CLI/gateway/TUI/desktop/ACP share one reasoning loop — fix once, all benefit.</li>
    <li><strong>Footprint Ladder</strong>: extend code → CLI+skill → gated tool → plugin → MCP → new core tool (last).</li>
    <li><strong>One-way deps + auto-discovery</strong>: registry ← tools/*.py ← model_tools ← entries; edit the waist once, all platforms sync.</li>
  </ul>
</div>
""",
}

LESSON_05 = {
    "zh": r"""
<p class="lead">
一次对话从你敲下的一句话，到 Hermes 给出最终回复，中间到底发生了什么？答案是一个<strong>同步主循环</strong>：模型每"想一步"就可能调用工具，工具结果被<strong>追加</strong>回消息列表，再喂回模型——如此往复，直到模型不再调用工具、直接给出最终回答。这个循环是整个 agent 的<strong>心脏</strong>，它住在 <span class="mono">agent/conversation_loop.py</span> 里，并带着三个硬约束：<strong>可中断</strong>、<strong>有迭代预算</strong>、<strong>严格的消息角色交替</strong>。本章把这颗心脏拆开给你看。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  把一次对话想成一条<strong>工厂流水线</strong>：原料（你的消息）进来，沿传送带走过一个个工位（每个工位 = 模型调用一次工具），工位加工完把半成品<strong>放回传送带</strong>继续往下走。流水线是<strong>同步</strong>的——上一个工位没干完，下一个不会启动。它还装了两个安全装置：一个<strong>计数器</strong>（最多过 N 道工序就强制停，免得空转烧钱），一个<strong>急停按钮</strong>（你随时能喊停，机器立刻松手）。Hermes 的对话循环，就是这条带安全装置的流水线。
</div>

<h2>宏观：一个同步的 while 循环</h2>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  别被 Hermes 的体量吓到——一次对话的核心是一个<strong>普普通通的同步 while 循环</strong>。每转一圈做五件事：<strong>检查中断 → 消费一格预算 → 调一次模型 → 若有 tool_calls 就执行并把结果追加回 messages → 没有 tool_calls 就收尾</strong>。所有"记忆"都装在 <span class="mono">messages</span> 这个列表里，<strong>每轮整体重发</strong>给模型——因为模型本身两次调用之间什么都不记得（第 2 章 B·无状态）。循环不重建上下文、只往末尾追加，这正是为了守住 prompt 缓存（第 6 章）。
</div>

<p>你在源码里可能先撞见 <span class="mono">run_conversation()</span>，但要诚实地说：<span class="mono">run_agent.py:5302</span> 里的它只是个<strong>转发器</strong>，docstring 写得明明白白——<span class="mono">Forwarder — see agent.conversation_loop.run_conversation</span>。真正的主循环在 <span class="mono">agent/conversation_loop.py</span>。而更上层、最常被入门示例调用的 <span class="mono">chat()</span>（<span class="mono">run_agent.py:5325</span>）又是它的极简封装，最后一行就是 <span class="mono">return result["final_response"]</span>：</p>

<div class="flow">
  <div class="node"><div class="nt">chat(msg)</div><div class="nd">return result["final_response"]</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">run_conversation()</div><div class="nd">转发器 · run_agent.py:5302</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node hl"><div class="nt">conversation_loop</div><div class="nd">真正的 while 主循环</div></div>
</div>

<h2>主循环：while 条件与循环体</h2>
<p>循环"能活多久"由 <span class="mono">while</span> 条件决定，"怎么退出"则有三条路。先看条件和循环体（<span class="mono">conversation_loop.py:589</span> 与 <span class="mono">594-614</span>）：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/conversation_loop.py</span><span class="ln">589 · 594-614 …</span></div>
  <pre><span class="kw">while</span> (api_call_count &lt; agent.max_iterations <span class="kw">and</span> agent.iteration_budget.remaining &gt; 0) <span class="kw">or</span> agent._budget_grace_call:

    <span class="cm"># Check for interrupt request (e.g., user sent new message)</span>
    <span class="kw">if</span> agent._interrupt_requested:
        interrupted = <span class="kw">True</span>
        _turn_exit_reason = <span class="st">"interrupted_by_user"</span>
        <span class="kw">break</span>

    api_call_count += 1
    agent._api_call_count = api_call_count

    <span class="cm"># Grace call: the budget is exhausted but we gave the model one</span>
    <span class="cm"># more chance.  Consume the grace flag so the loop exits after</span>
    <span class="cm"># this iteration regardless of outcome.</span>
    <span class="kw">if</span> agent._budget_grace_call:
        agent._budget_grace_call = <span class="kw">False</span>
    <span class="kw">elif</span> <span class="kw">not</span> agent.iteration_budget.consume():
        _turn_exit_reason = <span class="st">"budget_exhausted"</span>
        <span class="kw">break</span></pre>
</div>

<p>读懂这十几行，<strong>三种退出方式</strong>就一目了然：① <strong>达到 max_iterations</strong>——<span class="mono">api_call_count &lt; max_iterations</span> 不再成立；② <strong>预算耗尽</strong>——<span class="mono">consume()</span> 返回 <span class="mono">False</span>，打上 <span class="mono">budget_exhausted</span> 并 <span class="mono">break</span>；③ <strong>用户中断</strong>——循环顶部发现 <span class="mono">_interrupt_requested</span> 为真，打上 <span class="mono">interrupted_by_user</span> 并 <span class="mono">break</span>。注意中断检查放在<strong>每圈最开头</strong>，所以哪怕模型正排着一长串工具，也能在下一圈被立刻截停。</p>

<h3>诚实标注：grace call 是预留钩子，核心未主动触发</h3>
<p><span class="mono">_budget_grace_call</span> 字面上像"预算耗尽还会宽限多跑一轮"，但请<strong>别被注释误导</strong>。核心代码只有三处碰它：<span class="mono">agent_init.py:525</span> 初始化置 <span class="mono">False</span>、<span class="mono">conversation_loop.py:589</span> 的 <span class="mono">while</span> 条件读它、<span class="mono">608-609</span> 在循环体里消费后又置 <span class="mono">False</span>——<strong>没有任何核心代码把它设成 True</strong>。换句话说它是一个<strong>预留放行钩子、核心未主动触发</strong>，正常对话里它<strong>永远是 False</strong>，不会让循环多跑一轮。预算耗尽后真正给模型"收个尾"的逻辑，由独立的 <span class="mono">_handle_max_iterations</span> 负责，与这个标志无关。</p>

<h2>时序：一圈循环里发生了什么</h2>
<p>把一次对话的数据流摊开，就是下面这条线——从用户消息进入，到 <span class="mono">final_response</span> 收尾，中间那段方括号里的步骤会<strong>循环</strong>很多圈：</p>
<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>用户消息入列</h4><p>你的输入作为一条 <span class="mono">user</span> 消息追加进 <span class="mono">messages</span></p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>进入 while 循环</h4><p>条件：未达 max_iterations 且预算 remaining &gt; 0</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>检查中断</h4><p><span class="mono">_interrupt_requested</span> 为真则立刻 break</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>消费一格预算</h4><p><span class="mono">consume()</span> 返回 False 则 break（budget_exhausted）</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>调用模型</h4><p>把整个 <span class="mono">messages</span> 重发，拿回 assistant 消息</p></div></div>
  <div class="step"><div class="num">6</div><div class="sc"><h4>有 tool_calls？</h4><p>有：append assistant 消息，再 <span class="mono">_execute_tool_calls</span> 执行工具</p></div></div>
  <div class="step"><div class="num">7</div><div class="sc"><h4>append 工具结果</h4><p>每个工具结果作为 <span class="mono">tool</span> 消息追加回 messages → <span class="mono">continue</span> 回到第 3 步</p></div></div>
  <div class="step"><div class="num">8</div><div class="sc"><h4>无 tool_calls 收尾</h4><p><span class="mono">final_response = assistant_message.content</span> → 返回</p></div></div>
</div>

<p>同样的故事换个角度看：一圈圈迭代向右推进，每圈跑的都是同一段方括号步骤；而循环只会从三个门里走出去其中一个。</p>
<div class="timeline">
  <div class="lane"><div class="lane-label">迭代</div><div class="tslot">#1</div><div class="tslot">#2</div><div class="tslot">#3</div><div class="tslot">…</div><div class="tslot now">#N</div></div>
  <div class="lane"><div class="lane-label">每圈做</div><div class="tslot span">检查中断 → consume 预算 → 调模型 → 处理 tool_calls → append 结果</div></div>
  <div class="lane"><div class="lane-label">三种退出</div><div class="tslot">达到 max_iterations</div><div class="tslot">预算耗尽</div><div class="tslot now">用户中断</div></div>
</div>

<h2>迭代预算：防止失控长循环</h2>
<p>第 5 步每调一次模型，就先 <span class="mono">consume()</span> 一格预算。这把"门闩"由 <span class="mono">IterationBudget</span> 把守（<span class="mono">agent/iteration_budget.py</span>），<strong>线程安全</strong>，parent 默认上限 <strong>90</strong>、每个 subagent 独立默认 <strong>50</strong>。它的两个核心方法短得能背下来：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/iteration_budget.py</span><span class="ln">37-43 · 56-59</span></div>
  <pre><span class="kw">def</span> <span class="fn">consume</span>(self) -&gt; bool:
    <span class="cm">&quot;&quot;&quot;Try to consume one iteration.  Returns True if allowed.&quot;&quot;&quot;</span>
    <span class="kw">with</span> self._lock:
        <span class="kw">if</span> self._used &gt;= self.max_total:
            <span class="kw">return</span> <span class="kw">False</span>
        self._used += 1
        <span class="kw">return</span> <span class="kw">True</span>

@property
<span class="kw">def</span> <span class="fn">remaining</span>(self) -&gt; int:
    <span class="kw">with</span> self._lock:
        <span class="kw">return</span> max(0, self.max_total - self._used)</pre>
</div>

<p>为什么要给循环上预算？因为大模型的错误会<strong>逐轮累积</strong>（第 3 章 F·误差累积）：一旦规划跑偏，它可能没完没了地调工具、绕圈子，把你的钱烧光也到不了终点。<strong>有界的迭代数</strong>就是一道硬刹车——既封住成本与延迟（A·延迟成本），也给失控的长循环兜了底。一个贴心设计：<span class="mono">execute_code</span> 这种"编程式工具调用"会调 <span class="mono">refund()</span> 把那一格<strong>退回去</strong>，所以它不占正常的对话预算。</p>

<h2>可中断：随时能喊停</h2>
<p>循环每圈开头都查 <span class="mono">_interrupt_requested</span>，那么这个标志是谁设的？是 <span class="mono">interrupt()</span>（<span class="mono">run_agent.py:2400-2440</span>）：它把 <span class="mono">_interrupt_requested = True</span>，记下中断消息，并把信号<strong>级联</strong>给正在执行的工具线程与子 agent，让 in-flight 操作尽快收手。最典型的触发场景在消息网关：当某个会话的 agent 还在跑、你又发来一条新消息，网关就调 <span class="mono">running_agent.interrupt(new_message.text)</span>——于是它在下一圈循环顶部被截停，转身处理你的新指令。</p>

<h2>严格角色交替：provider 要求 + 不破缓存</h2>
<p>每圈往 <span class="mono">messages</span> 里追加的，无非两类消息。<strong>assistant 消息</strong>由 <span class="mono">chat_completion_helpers.py:885-890</span> 构造，带着 <span class="mono">content</span>、<span class="mono">reasoning</span>、<span class="mono">finish_reason</span> 三件套；<strong>tool 消息</strong>由 <span class="mono">tool_dispatch_helpers.py:336-343</span> 构造，带着 <span class="mono">name</span>、<span class="mono">content</span>、<span class="mono">tool_call_id</span>。四种角色各司其职：</p>
<table class="t">
  <tr><th>角色</th><th>谁产生</th><th>关键字段</th></tr>
  <tr><td><span class="mono">system</span></td><td>会话开始的固定前缀</td><td>整段 prompt（缓存命中全靠它字节稳定）</td></tr>
  <tr><td><span class="mono">user</span></td><td>你的输入 / nudge</td><td><span class="mono">content</span>；连续两条会被合并</td></tr>
  <tr><td><span class="mono">assistant</span></td><td>模型</td><td><span class="mono">content + reasoning + finish_reason</span></td></tr>
  <tr><td><span class="mono">tool</span></td><td>工具执行结果</td><td><span class="mono">name + content + tool_call_id</span></td></tr>
</table>

<p>这些消息必须严格<strong>交替</strong>：system 之后，user/tool 与 assistant 一来一回，<strong>不能出现两条连续的 user 消息</strong>。<span class="mono">repair_message_sequence</span>（<span class="mono">agent_runtime_helpers.py:348-435</span>）就是临门那道防线，它的 docstring 原文说得很直白：「Providers (OpenAI, OpenRouter, Anthropic) expect strict alternation … no two consecutive user messages …」。它在发请求前做两遍修复：Pass 1 丢弃找不到对应 assistant 调用的<strong>孤儿 tool 消息</strong>；Pass 2 把<strong>连续的 user 消息合并</strong>（换行拼接，一条输入都不丢）：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/agent_runtime_helpers.py</span><span class="ln">413-435</span></div>
  <pre><span class="cm"># Pass 2: merge consecutive user messages. Preserves all user input</span>
<span class="cm"># so nothing the user typed is lost.</span>
merged: List[Dict] = []
<span class="kw">for</span> msg <span class="kw">in</span> filtered:
    <span class="kw">if</span> (
        merged
        <span class="kw">and</span> isinstance(msg, dict)
        <span class="kw">and</span> msg.get(<span class="st">"role"</span>) == <span class="st">"user"</span>
        <span class="kw">and</span> isinstance(merged[-1], dict)
        <span class="kw">and</span> merged[-1].get(<span class="st">"role"</span>) == <span class="st">"user"</span>
    ):
        <span class="cm"># → 用换行拼接两条 user 消息，一条都不丢（后续 424-435 行）</span>
        ...</pre>
</div>

<p>为什么这么较真？因为违反交替会让多数 provider <strong>静默返回空响应</strong>，触发徒劳的空响应重试；更要命的是，任何对历史的中途改写都可能<strong>击穿 prompt 缓存</strong>（第 6 章），让长对话每轮成本翻倍。所以修复只在发请求前做"防御性合并"，绝不重建上下文。</p>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 一次对话由哪些部件拼成</div>
  <div class="collab-sub">① 组件清单</div>
  <strong>conversation_loop</strong>（主循环，<span class="mono">conversation_loop.py:589</span>）拍板节奏；<strong>IterationBudget</strong>（预算，<span class="mono">iteration_budget.py</span>）守 <span class="mono">consume/remaining</span>；<strong>_interrupt_requested</strong>（中断标志，由 <span class="mono">interrupt()</span> @ <span class="mono">run_agent.py:2400</span> 设置）管急停；<strong>repair_message_sequence</strong>（<span class="mono">agent_runtime_helpers.py:348</span>）保交替；<strong>_execute_tool_calls</strong> 执行工具并 append <span class="mono">tool</span> 结果；<strong>chat_completion_helpers</strong>（<span class="mono">:885</span>）构造带 reasoning 的 assistant 消息。跨章节：messages 外置全部状态（第 2 章 B），预算防误差累积（第 3 章 F），交替不变量服务 prompt 缓存（第 6 章）。
  <div class="collab-sub">② 数据流时序</div>
  用户消息 → 进入 <span class="mono">while</span> 循环 →〔检查中断 → <span class="mono">consume</span> 预算 → LLM 调用 → 处理 <span class="mono">tool_calls</span> → append <span class="mono">tool</span> 结果〕反复多圈 → 某轮模型<strong>无 tool_calls</strong> → 收尾为 <span class="mono">final_response</span>。
  <div class="collab-sub">③ 关键点</div>
  全部状态都在 <span class="mono">messages</span> 里、循环同步可中断、预算有界——三者合起来，让 agent loop 既能放手干活，又<strong>不会失控</strong>。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  本章围绕对话循环的三条主线：<strong>可中断 + 迭代预算 + 严格角色交替不变量</strong>。可中断让长任务随时能被新消息接管；迭代预算给"放手让模型自己干"上了硬上限；严格交替既满足 provider 的格式要求，又顺手守住了缓存。
  <p style="margin:.5rem 0 0">它对抗的 LLM 固有约束：<span class="badge constraint">B·无状态</span>——状态全外置在 <span class="mono">messages</span>、每轮重发；<span class="badge constraint">F·误差累积</span>——预算 + 中断防止失控的长循环；<span class="badge constraint">A·延迟成本</span>——有界迭代直接压住长度与花销。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li>对话的核心是一个<strong>同步 while 循环</strong>（<span class="mono">conversation_loop.py:589</span>）；<span class="mono">run_conversation()/chat()</span> 只是它的<strong>转发器/封装</strong>。</li>
    <li>主循环<strong>三种退出</strong>：达到 <span class="mono">max_iterations</span> / 预算耗尽 / 用户中断；中断检查在每圈<strong>最开头</strong>。</li>
    <li><strong>IterationBudget</strong> 线程安全，parent 90 / subagent 50；<span class="mono">execute_code</span> 用 <span class="mono">refund()</span> 退格、不占预算。</li>
    <li><strong>严格角色交替</strong>是 provider 硬要求，也护着缓存；<span class="mono">repair_message_sequence</span> 丢孤儿 tool、合并连续 user。</li>
    <li>诚实点：<span class="mono">_budget_grace_call</span> 是<strong>预留放行钩子、核心未主动触发</strong>（全仓无 True-setter，正常对话恒为 False）。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">
From the moment you hit enter to the moment Hermes hands back a final answer, what actually happens? The answer is a <strong>synchronous main loop</strong>: every time the model "thinks a step" it may call tools, the tool results are <strong>appended</strong> back onto the message list, and the whole thing is fed back to the model — round after round, until the model stops calling tools and just answers. This loop is the <strong>heart</strong> of the agent. It lives in <span class="mono">agent/conversation_loop.py</span> and carries three hard constraints: <strong>interruptible</strong>, <strong>budgeted iterations</strong>, and <strong>strict message-role alternation</strong>. This chapter cracks that heart open.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Picture one conversation as a <strong>factory assembly line</strong>: raw material (your message) enters, rides the belt past one station after another (each station = the model calling one tool), and each station drops its half-finished part <strong>back on the belt</strong> to continue. The line is <strong>synchronous</strong> — the next station won't start until the previous one finishes. It also ships two safety devices: a <strong>counter</strong> (stop after at most N stations, so it can't spin and burn money) and an <strong>emergency stop</strong> (you can halt it any time and it lets go instantly). Hermes' conversation loop is exactly this line, safety devices included.
</div>

<h2>Macro: one synchronous while loop</h2>

<div class="card macro">
  <div class="tag">🌍 The big picture</div>
  Don't let Hermes' size scare you — the core of a conversation is an utterly ordinary <strong>synchronous while loop</strong>. Each turn does five things: <strong>check for interrupt → consume one unit of budget → call the model once → if there are tool_calls, run them and append results back to messages → if there are none, finish</strong>. All "memory" lives in the <span class="mono">messages</span> list and is <strong>resent in full every turn</strong> — because the model itself remembers nothing between calls (Ch. 2, B·statelessness). The loop never rebuilds context, only appends to the end, precisely to keep the prompt cache intact (Ch. 6).
</div>

<p>You may first bump into <span class="mono">run_conversation()</span> in the source, but be honest about it: the one in <span class="mono">run_agent.py:5302</span> is just a <strong>forwarder</strong> — its docstring says so outright: <span class="mono">Forwarder — see agent.conversation_loop.run_conversation</span>. The real main loop is in <span class="mono">agent/conversation_loop.py</span>. And the even-higher-level <span class="mono">chat()</span> (<span class="mono">run_agent.py:5325</span>), the one tutorials call most, is just a thin wrapper whose last line is <span class="mono">return result["final_response"]</span>:</p>

<div class="flow">
  <div class="node"><div class="nt">chat(msg)</div><div class="nd">return result["final_response"]</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">run_conversation()</div><div class="nd">forwarder · run_agent.py:5302</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node hl"><div class="nt">conversation_loop</div><div class="nd">the real while loop</div></div>
</div>

<h2>The main loop: while condition and loop body</h2>
<p>How long the loop lives is decided by the <span class="mono">while</span> condition; how it exits has three paths. First the condition and body (<span class="mono">conversation_loop.py:589</span> and <span class="mono">594-614</span>):</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/conversation_loop.py</span><span class="ln">589 · 594-614 …</span></div>
  <pre><span class="kw">while</span> (api_call_count &lt; agent.max_iterations <span class="kw">and</span> agent.iteration_budget.remaining &gt; 0) <span class="kw">or</span> agent._budget_grace_call:

    <span class="cm"># Check for interrupt request (e.g., user sent new message)</span>
    <span class="kw">if</span> agent._interrupt_requested:
        interrupted = <span class="kw">True</span>
        _turn_exit_reason = <span class="st">"interrupted_by_user"</span>
        <span class="kw">break</span>

    api_call_count += 1
    agent._api_call_count = api_call_count

    <span class="cm"># Grace call: the budget is exhausted but we gave the model one</span>
    <span class="cm"># more chance.  Consume the grace flag so the loop exits after</span>
    <span class="cm"># this iteration regardless of outcome.</span>
    <span class="kw">if</span> agent._budget_grace_call:
        agent._budget_grace_call = <span class="kw">False</span>
    <span class="kw">elif</span> <span class="kw">not</span> agent.iteration_budget.consume():
        _turn_exit_reason = <span class="st">"budget_exhausted"</span>
        <span class="kw">break</span></pre>
</div>

<p>Read those dozen lines and the <strong>three exits</strong> jump out: ① <strong>hit max_iterations</strong> — <span class="mono">api_call_count &lt; max_iterations</span> stops holding; ② <strong>budget exhausted</strong> — <span class="mono">consume()</span> returns <span class="mono">False</span>, tagged <span class="mono">budget_exhausted</span>, then <span class="mono">break</span>; ③ <strong>user interrupt</strong> — the loop top finds <span class="mono">_interrupt_requested</span> true, tags <span class="mono">interrupted_by_user</span>, then <span class="mono">break</span>. Note the interrupt check sits at the <strong>very top of each turn</strong>, so even if the model has queued a long string of tools, it can be cut off on the next turn.</p>

<h3>Honest note: grace call is a reserved hook, never fired by the core</h3>
<p><span class="mono">_budget_grace_call</span> reads like "when the budget is spent we still allow one bonus turn" — but <strong>don't be misled by the comment</strong>. The whole repo touches it in exactly three places: <span class="mono">agent_init.py:525</span> initializes it to <span class="mono">False</span>, the <span class="mono">while</span> condition at <span class="mono">conversation_loop.py:589</span> reads it, and <span class="mono">608-609</span> consumes it back to <span class="mono">False</span> inside the body — <strong>no core code ever sets it to True</strong>. In other words it is a <strong>reserved release hook the core never actively fires</strong>; in a normal conversation it is <strong>always False</strong> and grants no extra turn. The real "wrap it up" logic after budget exhaustion lives in the separate <span class="mono">_handle_max_iterations</span>, unrelated to this flag.</p>

<h2>Sequence: what happens in one turn</h2>
<p>Lay the data flow flat and you get this line — from the user message in, to <span class="mono">final_response</span> out, with the bracketed middle steps <strong>looping</strong> many times:</p>
<div class="vflow">
  <div class="step"><div class="num">1</div><div class="sc"><h4>User message enqueued</h4><p>Your input is appended as a <span class="mono">user</span> message onto <span class="mono">messages</span></p></div></div>
  <div class="step"><div class="num">2</div><div class="sc"><h4>Enter the while loop</h4><p>Condition: under max_iterations and budget remaining &gt; 0</p></div></div>
  <div class="step"><div class="num">3</div><div class="sc"><h4>Check interrupt</h4><p>If <span class="mono">_interrupt_requested</span> is true, break immediately</p></div></div>
  <div class="step"><div class="num">4</div><div class="sc"><h4>Consume one unit</h4><p><span class="mono">consume()</span> returning False breaks (budget_exhausted)</p></div></div>
  <div class="step"><div class="num">5</div><div class="sc"><h4>Call the model</h4><p>Resend all of <span class="mono">messages</span>, get back an assistant message</p></div></div>
  <div class="step"><div class="num">6</div><div class="sc"><h4>tool_calls?</h4><p>Yes: append the assistant message, then <span class="mono">_execute_tool_calls</span></p></div></div>
  <div class="step"><div class="num">7</div><div class="sc"><h4>Append tool results</h4><p>Each result is appended as a <span class="mono">tool</span> message → <span class="mono">continue</span> to step 3</p></div></div>
  <div class="step"><div class="num">8</div><div class="sc"><h4>No tool_calls → finish</h4><p><span class="mono">final_response = assistant_message.content</span> → return</p></div></div>
</div>

<p>Same story from another angle: iterations march to the right, each running the same bracketed steps, and the loop leaves through exactly one of three doors.</p>
<div class="timeline">
  <div class="lane"><div class="lane-label">iteration</div><div class="tslot">#1</div><div class="tslot">#2</div><div class="tslot">#3</div><div class="tslot">…</div><div class="tslot now">#N</div></div>
  <div class="lane"><div class="lane-label">each turn</div><div class="tslot span">check interrupt → consume budget → call model → handle tool_calls → append results</div></div>
  <div class="lane"><div class="lane-label">three exits</div><div class="tslot">hit max_iterations</div><div class="tslot">budget exhausted</div><div class="tslot now">user interrupt</div></div>
</div>

<h2>Iteration budget: stopping runaway loops</h2>
<p>At step 5, every model call first <span class="mono">consume()</span>s one unit of budget. That latch is guarded by <span class="mono">IterationBudget</span> (<span class="mono">agent/iteration_budget.py</span>), <strong>thread-safe</strong>, with a parent cap of <strong>90</strong> by default and each subagent capped independently at <strong>50</strong>. Its two core methods are short enough to memorize:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/iteration_budget.py</span><span class="ln">37-43 · 56-59</span></div>
  <pre><span class="kw">def</span> <span class="fn">consume</span>(self) -&gt; bool:
    <span class="cm">&quot;&quot;&quot;Try to consume one iteration.  Returns True if allowed.&quot;&quot;&quot;</span>
    <span class="kw">with</span> self._lock:
        <span class="kw">if</span> self._used &gt;= self.max_total:
            <span class="kw">return</span> <span class="kw">False</span>
        self._used += 1
        <span class="kw">return</span> <span class="kw">True</span>

@property
<span class="kw">def</span> <span class="fn">remaining</span>(self) -&gt; int:
    <span class="kw">with</span> self._lock:
        <span class="kw">return</span> max(0, self.max_total - self._used)</pre>
</div>

<p>Why budget the loop at all? Because model errors <strong>compound turn over turn</strong> (Ch. 3, F·error-compounding): once the plan drifts, the model can call tools forever, circling without reaching the goal and draining your wallet. A <strong>bounded iteration count</strong> is the hard brake — it caps cost and latency (A·latency/cost) and backstops runaway loops. One thoughtful touch: <span class="mono">execute_code</span>'s "programmatic tool calling" calls <span class="mono">refund()</span> to <strong>hand that unit back</strong>, so it doesn't eat the normal conversation budget.</p>

<h2>Interruptible: halt any time</h2>
<p>Every turn starts by checking <span class="mono">_interrupt_requested</span> — so who sets it? <span class="mono">interrupt()</span> (<span class="mono">run_agent.py:2400-2440</span>): it sets <span class="mono">_interrupt_requested = True</span>, records the interrupt message, and <strong>cascades</strong> the signal to in-flight tool threads and subagents so live operations abort fast. The classic trigger is the messaging gateway: when a session's agent is still running and you send a new message, the gateway calls <span class="mono">running_agent.interrupt(new_message.text)</span> — so it's cut off at the top of the next turn and pivots to your new instruction.</p>

<h2>Strict role alternation: provider requirement + cache safety</h2>
<p>What gets appended to <span class="mono">messages</span> each turn is just two kinds of message. The <strong>assistant message</strong> is built by <span class="mono">chat_completion_helpers.py:885-890</span> carrying <span class="mono">content</span>, <span class="mono">reasoning</span>, and <span class="mono">finish_reason</span>; the <strong>tool message</strong> is built by <span class="mono">tool_dispatch_helpers.py:336-343</span> carrying <span class="mono">name</span>, <span class="mono">content</span>, and <span class="mono">tool_call_id</span>. Four roles, each with its job:</p>
<table class="t">
  <tr><th>Role</th><th>Produced by</th><th>Key fields</th></tr>
  <tr><td><span class="mono">system</span></td><td>fixed prefix at session start</td><td>the whole prompt (cache hits rely on it being byte-stable)</td></tr>
  <tr><td><span class="mono">user</span></td><td>your input / nudge</td><td><span class="mono">content</span>; two in a row get merged</td></tr>
  <tr><td><span class="mono">assistant</span></td><td>the model</td><td><span class="mono">content + reasoning + finish_reason</span></td></tr>
  <tr><td><span class="mono">tool</span></td><td>tool execution result</td><td><span class="mono">name + content + tool_call_id</span></td></tr>
</table>

<p>These messages must strictly <strong>alternate</strong>: after system, user/tool trades off with assistant, and <strong>no two consecutive user messages</strong> are allowed. <span class="mono">repair_message_sequence</span> (<span class="mono">agent_runtime_helpers.py:348-435</span>) is the last line of defense; its docstring puts it plainly: "Providers (OpenAI, OpenRouter, Anthropic) expect strict alternation … no two consecutive user messages …". It runs two repair passes right before the request: Pass 1 drops <strong>orphan tool messages</strong> with no matching assistant call; Pass 2 <strong>merges consecutive user messages</strong> (newline-joined, losing no input):</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/agent_runtime_helpers.py</span><span class="ln">413-435</span></div>
  <pre><span class="cm"># Pass 2: merge consecutive user messages. Preserves all user input</span>
<span class="cm"># so nothing the user typed is lost.</span>
merged: List[Dict] = []
<span class="kw">for</span> msg <span class="kw">in</span> filtered:
    <span class="kw">if</span> (
        merged
        <span class="kw">and</span> isinstance(msg, dict)
        <span class="kw">and</span> msg.get(<span class="st">"role"</span>) == <span class="st">"user"</span>
        <span class="kw">and</span> isinstance(merged[-1], dict)
        <span class="kw">and</span> merged[-1].get(<span class="st">"role"</span>) == <span class="st">"user"</span>
    ):
        <span class="cm"># → newline-join the two user turns, nothing lost (lines 424-435)</span>
        ...</pre>
</div>

<p>Why so picky? Because violating alternation makes most providers <strong>silently return an empty response</strong>, triggering a pointless empty-retry loop; worse, any mid-stream rewrite of history can <strong>shatter the prompt cache</strong> (Ch. 6), doubling per-turn cost on long conversations. So the repair only does a defensive merge right before the request — it never rebuilds context.</p>

<div class="card collab">
  <div class="tag">🧩 Collaboration · which parts make one conversation</div>
  <div class="collab-sub">① Component list</div>
  <strong>conversation_loop</strong> (main loop, <span class="mono">conversation_loop.py:589</span>) sets the rhythm; <strong>IterationBudget</strong> (<span class="mono">iteration_budget.py</span>) guards <span class="mono">consume/remaining</span>; <strong>_interrupt_requested</strong> (set by <span class="mono">interrupt()</span> @ <span class="mono">run_agent.py:2400</span>) handles the e-stop; <strong>repair_message_sequence</strong> (<span class="mono">agent_runtime_helpers.py:348</span>) keeps alternation; <strong>_execute_tool_calls</strong> runs tools and appends the <span class="mono">tool</span> results; <strong>chat_completion_helpers</strong> (<span class="mono">:885</span>) builds the assistant message with reasoning. Cross-chapter: messages externalize all state (Ch. 2, B), the budget fights error-compounding (Ch. 3, F), the alternation invariant serves prompt caching (Ch. 6).
  <div class="collab-sub">② Data-flow sequence</div>
  user message → enter the <span class="mono">while</span> loop →〔check interrupt → <span class="mono">consume</span> budget → LLM call → handle <span class="mono">tool_calls</span> → append <span class="mono">tool</span> results〕many turns → a turn with <strong>no tool_calls</strong> → finish as <span class="mono">final_response</span>.
  <div class="collab-sub">③ Key point</div>
  All state lives in <span class="mono">messages</span>, the loop is synchronous and interruptible, and the budget is bounded — together they let the agent loop work freely yet <strong>never spin out of control</strong>.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  This chapter centers on the loop's three throughlines: <strong>interruptible + iteration budget + the strict-alternation invariant</strong>. Interruptibility lets a long task be taken over by a new message any time; the budget puts a hard ceiling on "let the model run itself"; strict alternation satisfies the provider format and protects the cache in one stroke.
  <p style="margin:.5rem 0 0">The LLM constraints it fights: <span class="badge constraint">B·stateless</span> — all state externalized into <span class="mono">messages</span>, resent every turn; <span class="badge constraint">F·error-compounding</span> — budget + interrupt prevent runaway loops; <span class="badge constraint">A·latency/cost</span> — bounded iterations cap length and spend.</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li>The core of a conversation is a <strong>synchronous while loop</strong> (<span class="mono">conversation_loop.py:589</span>); <span class="mono">run_conversation()/chat()</span> are just its <strong>forwarder/wrapper</strong>.</li>
    <li>The loop has <strong>three exits</strong>: hit <span class="mono">max_iterations</span> / budget exhausted / user interrupt; the interrupt check sits at the <strong>top of every turn</strong>.</li>
    <li><strong>IterationBudget</strong> is thread-safe, parent 90 / subagent 50; <span class="mono">execute_code</span> uses <span class="mono">refund()</span> to give a unit back and not eat the budget.</li>
    <li><strong>Strict role alternation</strong> is a provider hard requirement and also guards the cache; <span class="mono">repair_message_sequence</span> drops orphan tools and merges consecutive users.</li>
    <li>Honest note: <span class="mono">_budget_grace_call</span> is a <strong>reserved release hook the core never fires</strong> (no True-setter anywhere; always False in normal conversations).</li>
  </ul>
</div>
""",
}
