LESSON_17 = {
    "zh": r"""
<p class="lead">一个 Hermes 进程能同时在 Telegram、Discord、Slack、Matrix、飞书、微信……二十多个平台上收发消息。怎么做到的?核心只认<strong>一种</strong>消息——每个平台派一个「翻译官」(适配器),把五花八门的协议都翻译成同一种统一事件,核心网关的<strong>主路径几乎不碰任何具体平台</strong>。</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 联合国同声传译</div>
  各国代表说着不同语言(Telegram 的 Update、Discord 的 Gateway 事件、IRC 的一行文本……),但会场只用<strong>一种工作语言</strong>开会。每个语种配一名同传(适配器),把本国语翻成工作语言、再把决议翻回去。主持人(核心网关)<strong>只需听懂工作语言</strong>,完全不必会二十几国语言。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 统一抽象,平台差异在边缘</div>
  核心定义两个统一抽象:<strong>MessageEvent</strong>(归一化的「一条消息」)和 <strong>BasePlatformAdapter</strong>(适配器契约)。约 28+ 个平台各写一个适配器子类,把平台原生消息翻成 MessageEvent 交给核心,再把核心的回复翻回平台格式。差异全沉在边缘,<strong>核心保持平台无关</strong>。
</div>

<h2>统一消息:MessageEvent</h2>
<p>不管消息来自哪个平台,进核心前都被归一化成同一个数据结构:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">gateway/platforms/base.py</span><span class="ln">1599-1632 · 节选</span></div>
  <pre><span class="nd">@dataclass</span>
<span class="kw">class</span> <span class="fn">MessageEvent</span>:
    <span class="cm">&quot;&quot;&quot;Incoming message from a platform.</span>
<span class="cm">    Normalized representation that all adapters produce.&quot;&quot;&quot;</span>
    text: str                              <span class="cm"># 消息正文</span>
    message_type: MessageType = MessageType.TEXT
    source: SessionSource = None           <span class="cm"># 谁/哪个会话发的(路由用)</span>
    raw_message: Any = None                <span class="cm"># 平台原始对象(留底)</span>
    media_urls: List[str] = field(default_factory=list)
    reply_to_message_id: Optional[str] = None</pre>
</div>
<p>点睛在那句 docstring:<strong>「Normalized representation that all adapters produce」——所有适配器都产出这一种归一化表示</strong>。Telegram 的富文本、Discord 的嵌入、IRC 的纯文本,进核心前统统被压成同一个 <span class="mono">MessageEvent</span>。核心的 agent 循环(第 7 章)<strong>只见过 MessageEvent,从不认识任何平台的原生格式</strong>。<span class="mono">source</span> 字段携带会话标识,核心据此把消息路由到正确的会话(每会话独立 = 约束 B)。</p>

<h2>适配器契约:BasePlatformAdapter</h2>
<p>「翻译官」要做的事被固化成一个抽象基类,每个平台子类只填平台专属的洞:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">gateway/platforms/base.py</span><span class="ln">2082-2620 · 节选</span></div>
  <pre><span class="kw">class</span> <span class="fn">BasePlatformAdapter</span>(ABC):
    <span class="cm">&quot;&quot;&quot;Base class for platform adapters.</span>
<span class="cm">    Subclasses implement platform-specific logic for:</span>
<span class="cm">    - Connecting and authenticating</span>
<span class="cm">    - Receiving messages</span>
<span class="cm">    - Sending messages/responses</span>
<span class="cm">    - Handling media&quot;&quot;&quot;</span>

    <span class="nd">@abstractmethod</span>
    <span class="kw">async def</span> <span class="fn">connect</span>(self) -&gt; bool:
        <span class="cm"># 连接平台、开始收消息</span>
        ...

    <span class="nd">@abstractmethod</span>
    <span class="kw">async def</span> <span class="fn">send</span>(self, chat_id, content, reply_to=None):
        <span class="cm"># 把核心回复翻回平台格式发出</span>
        ...</pre>
</div>
<p><span class="mono">connect()</span> / <span class="mono">disconnect()</span> / <span class="mono">send()</span> 是每个适配器<strong>必须</strong>实现的抽象方法(另含 <span class="mono">get_chat_info</span>)——这是核心与平台之间的核心契约面。网关启动时把所有启用的适配器 <span class="mono">connect()</span> 起来,然后<strong>统一</strong>等它们产出 MessageEvent,根本不关心底层是长轮询、WebSocket 还是 IRC socket。</p>

<h2>一个真实的翻译官:IRCAdapter</h2>
<p>看 IRC 适配器怎么把一行 IRC 文本翻成统一事件——这是所有 28+ 适配器共同的模式:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">plugins/platforms/irc/adapter.py</span><span class="ln">482-510 / 281-283 · 节选</span></div>
  <pre><span class="kw">class</span> <span class="fn">IRCAdapter</span>(BasePlatformAdapter):

    <span class="kw">async def</span> <span class="fn">_dispatch_message</span>(self, text, chat_id, ...):
        <span class="cm">&quot;&quot;&quot;Build a MessageEvent and hand it to the base class handler.&quot;&quot;&quot;</span>
        source = self.build_source(chat_id=chat_id, ...)
        event = MessageEvent(              <span class="cm"># IRC 原生 → 统一事件</span>
            text=text,
            message_type=MessageType.TEXT,
            source=source,
        )
        <span class="kw">await</span> self.handle_message(event)   <span class="cm"># 交给基类统一入口</span>

    <span class="kw">async def</span> <span class="fn">send_typing</span>(self, chat_id, metadata=None):
        <span class="cm">&quot;&quot;&quot;IRC has no typing indicator — no-op.&quot;&quot;&quot;</span>
        <span class="kw">pass</span>                               <span class="cm"># 平台没有的能力,在边缘吸收</span></pre>
</div>
<p>两个细节道尽设计精髓:(1) <span class="mono">_dispatch_message</span> 把 IRC 文本包成 <span class="mono">MessageEvent</span> 后调 <span class="mono">handle_message</span>——<strong>翻译完就交给基类统一入口</strong>,后面的路由/排队/审批核心全包;(2) <span class="mono">send_typing</span> 是个 <strong>no-op</strong>:IRC 没有「正在输入」指示,这个平台能力差异<strong>在边缘适配器里被悄悄吸收</strong>,核心永远不知道、也不必知道某个平台缺这个能力。</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">平台原生事件到达(Telegram Update / Discord 事件 / IRC 文本行)</span></div>
  <div class="step"><span class="num">2</span><span class="sc">适配器 <span class="mono">build_source()</span> + 构造 <span class="mono">MessageEvent</span>(归一化)</span></div>
  <div class="step"><span class="num">3</span><span class="sc"><span class="mono">handle_message(event)</span> 交基类统一入口</span></div>
  <div class="step"><span class="num">4</span><span class="sc">按 <span class="mono">source</span> / session_key 路由到对应会话</span></div>
  <div class="step"><span class="num">5</span><span class="sc">agent 处理 → <span class="mono">send()</span> 把回复翻回平台格式发出</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「单进程跨多平台」</div>
  <div class="collab-sub">① 组件清单(★本章核心,其余跨章节配合)</div>
  本章核心:<strong>MessageEvent</strong>(归一化消息)、<strong>BasePlatformAdapter</strong>(适配器契约)、<strong>handle_message</strong>(基类统一入口)、<strong>session_key 路由</strong>。跨章节配合:绝大多数适配器是 <span class="mono">plugins/platforms/</span> 下的<strong>边缘插件</strong>(第 23 章插件/技能/MCP),核心网关只认抽象——这正是<strong>窄腰</strong>(第 4 章);消息进来后先过<strong>两道守卫</strong>(第 18 章)才到 agent;统一的 MessageEvent 最终喂给 <strong>agent 核心循环</strong>(第 7 章消息流);每个平台的 bot 凭据用 <strong>token lock</strong> 防两个 profile 抢同一令牌(第 20 章 Profiles)。
  <div class="collab-sub">② 数据流时序</div>
  平台原生事件 → 适配器 <span class="mono">build_source()</span> + <span class="mono">MessageEvent(...)</span> → <span class="mono">handle_message()</span> → 按 session_key 路由到会话 → 两道守卫(第 18 章) → agent 循环 → <span class="mono">send()</span> 翻回平台格式。
  <div class="collab-sub">③ 关键点</div>
  「单进程服务 28+ 平台」靠的是<strong>两个统一抽象 + 边缘翻译</strong>:核心只认 <span class="mono">MessageEvent</span> 与 <span class="mono">BasePlatformAdapter</span>,各平台的协议/能力/格式差异(连「有没有 typing 指示」)全沉到边缘适配器。加一个新平台 = 写一个 <span class="mono">plugins/platforms/&lt;name&gt;/adapter.py</span> 子类,核心网关<strong>主路径</strong>零改动。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线:<strong>统一消息抽象 + 适配器边缘翻译 = 单进程跨 28+ 平台;平台差异在边缘(窄腰)</strong>。它主要治两条 LLM 固有约束:
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·运维</span>——一个人的 agent 要随时随地能找到它:手机上发 Telegram、工位上发 Slack、群里发微信。统一抽象让<strong>一套核心服务所有平台</strong>,运维一个进程而非二十个;加平台不动核心。</p>
  <p style="margin:.5rem 0 0"><span class="badge constraint">B·无状态</span>——核心无全局会话状态,靠 MessageEvent 里的 <span class="mono">source</span> / session_key <strong>把每条消息路由到独立会话</strong>。同一进程里 Telegram 的张三和 Discord 的李四互不串台,全凭路由键区分。</p>
  <p style="margin:.5rem 0 0">它也是<strong>窄腰</strong>(第 4 章)的极致体现:连 Telegram/Discord/Slack 这些主流平台的适配器都是<strong>边缘插件</strong>,核心网关主要通过 BasePlatformAdapter 抽象交互。(诚实地说,<span class="mono">base.py</span> 里仍残留极少数平台特例——如 Telegram 私聊话题回复锚点、Feishu 线程——但那是历史遗留的边角,不是主路径架构。)反模式:把每个平台的整套逻辑都堆进核心写成 <span class="mono">if platform == ...</span> 分支——那会让核心随平台数量爆炸膨胀。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>两个统一抽象</strong>:<span class="mono">MessageEvent</span>(归一化消息,「所有适配器都产出它」)+ <span class="mono">BasePlatformAdapter</span>(connect/disconnect/send 契约)。</li>
    <li><strong>适配器=翻译官</strong>:把平台原生消息翻成 MessageEvent 交 <span class="mono">handle_message</span>,把核心回复翻回平台格式;平台能力差异(如 IRC 无 typing)在边缘 no-op 吸收。</li>
    <li><strong>单进程 28+ 平台</strong>:核心网关主路径无平台分支;主流平台(telegram/discord/slack/matrix……)都是 <span class="mono">plugins/platforms/</span> 边缘插件,少数内置在 <span class="mono">gateway/platforms/</span>,但都实现同一 BasePlatformAdapter。</li>
    <li><strong>会话路由</strong>:核心无全局状态,靠 <span class="mono">source</span> / session_key 把消息分到独立会话(约束 B)。</li>
    <li><strong>加平台零改核心</strong>:写一个 BasePlatformAdapter 子类即可——窄腰(第 4 章)在接入层的落地。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">A single Hermes process can send and receive across Telegram, Discord, Slack, Matrix, Feishu, WeChat… twenty-plus platforms at once. How? The core knows only <strong>one</strong> kind of message — each platform gets a "translator" (adapter) that turns its motley protocol into one unified event, and the core gateway's <strong>main path barely touches any specific platform</strong>.</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · UN simultaneous interpretation</div>
  Delegates speak different languages (Telegram's Update, Discord's Gateway events, a line of IRC text…), but the floor runs in <strong>one working language</strong>. Each language gets an interpreter (adapter) who renders it into the working language and translates resolutions back. The chair (the core gateway) <strong>only needs to understand the working language</strong>, never the two dozen native tongues.
</div>

<div class="card macro">
  <div class="tag">🌍 Macro · unified abstraction, platform differences at the edges</div>
  The core defines two unified abstractions: <strong>MessageEvent</strong> (a normalized "one message") and <strong>BasePlatformAdapter</strong> (the adapter contract). Some 28+ platforms each write an adapter subclass that translates native messages into MessageEvent for the core, and translates the core's reply back to the platform format. All differences sink to the edges; <strong>the core stays platform-agnostic</strong>.
</div>

<h2>The unified message: MessageEvent</h2>
<p>No matter which platform a message comes from, it is normalized into the same data structure before entering the core:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">gateway/platforms/base.py</span><span class="ln">1599-1632 · excerpt</span></div>
  <pre><span class="nd">@dataclass</span>
<span class="kw">class</span> <span class="fn">MessageEvent</span>:
    <span class="cm">&quot;&quot;&quot;Incoming message from a platform.</span>
<span class="cm">    Normalized representation that all adapters produce.&quot;&quot;&quot;</span>
    text: str                              <span class="cm"># message body</span>
    message_type: MessageType = MessageType.TEXT
    source: SessionSource = None           <span class="cm"># who/which session (for routing)</span>
    raw_message: Any = None                <span class="cm"># original platform object (kept)</span>
    media_urls: List[str] = field(default_factory=list)
    reply_to_message_id: Optional[str] = None</pre>
</div>
<p>The punch line is that docstring: <strong>"Normalized representation that all adapters produce."</strong> Telegram's rich text, Discord's embeds, IRC's plain text — all get squashed into the same <span class="mono">MessageEvent</span> before reaching the core. The core's agent loop (ch.7) <strong>has only ever seen MessageEvent, and never knows any platform's native format</strong>. The <span class="mono">source</span> field carries the session identity, and the core routes the message to the right session by it (each session independent = constraint B).</p>

<h2>The adapter contract: BasePlatformAdapter</h2>
<p>What a "translator" must do is frozen into an abstract base class; each platform subclass fills only the platform-specific holes:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">gateway/platforms/base.py</span><span class="ln">2082-2620 · excerpt</span></div>
  <pre><span class="kw">class</span> <span class="fn">BasePlatformAdapter</span>(ABC):
    <span class="cm">&quot;&quot;&quot;Base class for platform adapters.</span>
<span class="cm">    Subclasses implement platform-specific logic for:</span>
<span class="cm">    - Connecting and authenticating</span>
<span class="cm">    - Receiving messages</span>
<span class="cm">    - Sending messages/responses</span>
<span class="cm">    - Handling media&quot;&quot;&quot;</span>

    <span class="nd">@abstractmethod</span>
    <span class="kw">async def</span> <span class="fn">connect</span>(self) -&gt; bool:
        <span class="cm"># connect to the platform, start receiving</span>
        ...

    <span class="nd">@abstractmethod</span>
    <span class="kw">async def</span> <span class="fn">send</span>(self, chat_id, content, reply_to=None):
        <span class="cm"># translate the core's reply back to the platform format</span>
        ...</pre>
</div>
<p><span class="mono">connect()</span> / <span class="mono">disconnect()</span> / <span class="mono">send()</span> are abstract methods every adapter <strong>must</strong> implement (plus <span class="mono">get_chat_info</span>) — the core contract surface between core and platform. At startup the gateway <span class="mono">connect()</span>s every enabled adapter, then <strong>uniformly</strong> waits for them to produce MessageEvents, caring not at all whether the underlying transport is long-polling, a WebSocket, or an IRC socket.</p>

<h2>A real translator: IRCAdapter</h2>
<p>See how the IRC adapter turns a line of IRC text into a unified event — the shared pattern of all 28+ adapters:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">plugins/platforms/irc/adapter.py</span><span class="ln">482-510 / 281-283 · excerpt</span></div>
  <pre><span class="kw">class</span> <span class="fn">IRCAdapter</span>(BasePlatformAdapter):

    <span class="kw">async def</span> <span class="fn">_dispatch_message</span>(self, text, chat_id, ...):
        <span class="cm">&quot;&quot;&quot;Build a MessageEvent and hand it to the base class handler.&quot;&quot;&quot;</span>
        source = self.build_source(chat_id=chat_id, ...)
        event = MessageEvent(              <span class="cm"># IRC native → unified event</span>
            text=text,
            message_type=MessageType.TEXT,
            source=source,
        )
        <span class="kw">await</span> self.handle_message(event)   <span class="cm"># hand to the base unified entry</span>

    <span class="kw">async def</span> <span class="fn">send_typing</span>(self, chat_id, metadata=None):
        <span class="cm">&quot;&quot;&quot;IRC has no typing indicator — no-op.&quot;&quot;&quot;</span>
        <span class="kw">pass</span>                               <span class="cm"># a capability the platform lacks, absorbed at the edge</span></pre>
</div>
<p>Two details capture the whole design: (1) <span class="mono">_dispatch_message</span> wraps the IRC text into a <span class="mono">MessageEvent</span> and calls <span class="mono">handle_message</span> — <strong>once translated, it hands off to the base unified entry</strong>, and the core handles all downstream routing/queuing/approval; (2) <span class="mono">send_typing</span> is a <strong>no-op</strong>: IRC has no "typing" indicator, and this capability gap is <strong>quietly absorbed inside the edge adapter</strong>, so the core never knows, and need never know, that some platform lacks it.</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">a platform-native event arrives (Telegram Update / Discord event / IRC text line)</span></div>
  <div class="step"><span class="num">2</span><span class="sc">the adapter calls <span class="mono">build_source()</span> + builds a <span class="mono">MessageEvent</span> (normalize)</span></div>
  <div class="step"><span class="num">3</span><span class="sc"><span class="mono">handle_message(event)</span> hands to the base unified entry</span></div>
  <div class="step"><span class="num">4</span><span class="sc">routed to the right session by <span class="mono">source</span> / session_key</span></div>
  <div class="step"><span class="num">5</span><span class="sc">the agent processes → <span class="mono">send()</span> translates the reply back to the platform format</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "one process across many platforms"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: <strong>MessageEvent</strong> (normalized message), <strong>BasePlatformAdapter</strong> (adapter contract), <strong>handle_message</strong> (base unified entry), <strong>session_key routing</strong>. Cross-chapter teamwork: the vast majority of adapters are <strong>edge plugins</strong> under <span class="mono">plugins/platforms/</span> (ch.23 plugins/skills/MCP), and the core gateway knows only the abstraction — exactly the <strong>narrow waist</strong> (ch.4); incoming messages first pass <strong>two guards</strong> (ch.18) before the agent; the unified MessageEvent ultimately feeds the <strong>agent core loop</strong> (ch.7 message flow); each platform's bot credential uses a <strong>token lock</strong> to stop two profiles from grabbing the same token (ch.20 Profiles).
  <div class="collab-sub">② Data-flow timing</div>
  platform-native event → adapter <span class="mono">build_source()</span> + <span class="mono">MessageEvent(...)</span> → <span class="mono">handle_message()</span> → routed to a session by session_key → two guards (ch.18) → agent loop → <span class="mono">send()</span> translates back to the platform format.
  <div class="collab-sub">③ The key point</div>
  "One process serving 28+ platforms" rests on <strong>two unified abstractions + edge translation</strong>: the core knows only <span class="mono">MessageEvent</span> and <span class="mono">BasePlatformAdapter</span>, and every platform's protocol/capability/format difference (down to "is there a typing indicator") sinks to edge adapters. Adding a new platform = write a <span class="mono">plugins/platforms/&lt;name&gt;/adapter.py</span> subclass, with no change to the core gateway's <strong>main path</strong>.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>a unified message abstraction + edge translation by adapters = one process across 28+ platforms; platform differences at the edges (narrow waist)</strong>. It mainly treats two inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·ops</span> — a personal agent must be reachable anywhere: Telegram on your phone, Slack at your desk, WeChat in a group. The unified abstraction lets <strong>one core serve every platform</strong>, operating one process instead of twenty; adding a platform doesn't touch the core.</p>
  <p style="margin:.5rem 0 0"><span class="badge constraint">B·statelessness</span> — the core holds no global session state; it routes <strong>each message to an independent session</strong> by the <span class="mono">source</span> / session_key on the MessageEvent. In one process, Telegram's Alice and Discord's Bob never cross wires, distinguished purely by the routing key.</p>
  <p style="margin:.5rem 0 0">It's also the ultimate expression of the <strong>narrow waist</strong> (ch.4): even the adapters for mainstream platforms like Telegram/Discord/Slack are <strong>edge plugins</strong>, and the core gateway interacts mainly through the BasePlatformAdapter abstraction. (To be honest, <span class="mono">base.py</span> still keeps a few platform special-cases — e.g. Telegram DM-topic reply anchors, Feishu threads — but those are legacy corners, not the main-path architecture.) The anti-pattern: piling each platform's whole logic into the core as <span class="mono">if platform == ...</span> branches — that bloats the core explosively with each platform.</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Two unified abstractions</strong>: <span class="mono">MessageEvent</span> (normalized message, "all adapters produce it") + <span class="mono">BasePlatformAdapter</span> (connect/disconnect/send contract).</li>
    <li><strong>Adapter = translator</strong>: turn native messages into MessageEvent for <span class="mono">handle_message</span>, and the core reply back to the platform format; capability gaps (e.g. IRC has no typing) are absorbed as edge no-ops.</li>
    <li><strong>One process, 28+ platforms</strong>: the core gateway's main path has no platform branches; mainstream platforms (telegram/discord/slack/matrix…) are <span class="mono">plugins/platforms/</span> edge plugins, a few built into <span class="mono">gateway/platforms/</span>, but all implement the same BasePlatformAdapter.</li>
    <li><strong>Session routing</strong>: the core holds no global state, splitting messages into independent sessions by <span class="mono">source</span> / session_key (constraint B).</li>
    <li><strong>Add a platform, zero core change</strong>: just write a BasePlatformAdapter subclass — the narrow waist (ch.4) at the ingress layer.</li>
  </ul>
</div>
"""
}


LESSON_18 = {
    "zh": r"""
<p class="lead">当 agent 正在跑一个长任务时,用户又发来一条消息——怎么办?默认<strong>排队</strong>,等 agent 结束再处理。但有几个命令绝不能排队:<span class="mono">/stop</span>(打断)、<span class="mono">/approve</span>(agent 正阻塞着等它批准)。它们若排队,要么<strong>泄漏成对话文本被丢弃</strong>,要么<strong>直接死锁</strong>。这就是网关「两道守卫 + 控制命令旁路」的由来。</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 急诊分诊台</div>
  普通病人挂号排队(消息进 <span class="mono">_pending_messages</span>),等叫号。但「心脏骤停」(<span class="mono">/stop</span>)必须<strong>插队直达</strong>抢救;而「主治医生正等着的化验结果」(<span class="mono">/approve</span>)如果也去排队,医生就<strong>永远等不到、卡死在那</strong>。分诊台必须能识别这些「不能排队的」并放行。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 两道顺序守卫,控制命令旁路</div>
  agent 运行时,消息要过<strong>两道顺序守卫</strong>:① 适配器层(busy 就排队)、② 网关 runner 层(分派 slash 命令)。普通对话老老实实排队;但<strong>任何可解析的 slash 命令必须同时旁路两道、内联派发</strong>——否则被当对话文本丢弃(空响应)或死锁。
</div>

<h2>第一道守卫:适配器层的 busy 状态</h2>
<p>每个适配器记三张表,追踪「这个会话是不是正忙」:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">gateway/platforms/base.py</span><span class="ln">2154-2162 · 节选</span></div>
  <pre><span class="cm"># _active_sessions 存每会话的中断 Event;_session_tasks 把</span>
<span class="cm"># 会话映射到当前处理它的 Task,好让 /stop /new /reset 取消</span>
<span class="cm"># 正确的任务、确定性地释放守卫。没有这张表,旧任务的 finally</span>
<span class="cm"># 可能误删新任务的守卫,留下 stale busy 状态。</span>
self._active_sessions: Dict[str, asyncio.Event] = {}
self._pending_messages: Dict[str, MessageEvent] = {}
self._session_tasks: Dict[str, asyncio.Task] = {}</pre>
</div>
<p><span class="mono">_active_sessions</span> 里有这个 key,就说明该会话<strong>正在跑 agent</strong>。这时新来的普通消息会被塞进 <span class="mono">_pending_messages</span> 排队,等当前回合结束再喂进去。<span class="mono">_session_tasks</span> 记下「谁在处理这个会话」,这样 <span class="mono">/stop</span> 能精准取消那个任务,而不会误删别人的守卫。</p>

<h2>旁路:控制命令不能排队</h2>
<p>会话忙时,先看这条消息是不是个该旁路的命令:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">gateway/platforms/base.py</span><span class="ln">4262-4298 · 简化</span></div>
  <pre><span class="kw">if</span> session_key <span class="kw">in</span> self._active_sessions:
    cmd = event.get_command()
    <span class="kw">from</span> hermes_cli.commands <span class="kw">import</span> should_bypass_active_session

    <span class="kw">if</span> should_bypass_active_session(cmd):
        <span class="kw">if</span> cmd <span class="kw">in</span> {<span class="st">"stop"</span>, <span class="st">"new"</span>, <span class="st">"reset"</span>}:
            <span class="cm"># 取消在途任务 + 序列化交接</span>
            <span class="kw">await</span> self._dispatch_active_session_command(event, session_key, cmd)
            <span class="kw">return</span>
        <span class="cm"># /approve /deny /status /background /restart：直接内联派发</span>
        <span class="cm"># 不要用 _process_message_background——它管会话生命周期,</span>
        <span class="cm"># 其清理会和正在跑的任务抢(见 PR #4926)</span>
        ...</pre>
</div>
<p>分两类:<span class="mono">/stop</span> <span class="mono">/new</span> <span class="mono">/reset</span> 要<strong>取消在途任务</strong>(走专门的交接路径,序列化「取消 + 回应 + 排空队列」);<span class="mono">/approve</span> <span class="mono">/deny</span> <span class="mono">/status</span> 等不取消任务、只需<strong>直接内联派发</strong>。注释点破一个坑:<strong>千万别走 <span class="mono">_process_message_background</span></strong>——它管会话生命周期,清理逻辑会和正在跑的任务发生竞争。</p>

<h2>为什么排队就出事:zero-char 响应</h2>
<p>旁路判定函数的 docstring 把后果讲透了:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">hermes_cli/commands.py</span><span class="ln">379-399 · 简化</span></div>
  <pre><span class="kw">def</span> <span class="fn">should_bypass_active_session</span>(command_name):
    <span class="cm">&quot;&quot;&quot;Return True for any resolvable slash command.</span>
<span class="cm">    Queueing is always wrong for a recognized slash command</span>
<span class="cm">    because the safety net in gateway.run discards any command</span>
<span class="cm">    text that reaches the pending queue — a mid-run /model would</span>
<span class="cm">    silently interrupt the agent AND get discarded, a zero-char</span>
<span class="cm">    response.&quot;&quot;&quot;</span>
    <span class="kw">return</span> resolve_command(command_name) <span class="kw">is</span> <span class="kw">not</span> <span class="kw">None</span> <span class="kw">if</span> command_name <span class="kw">else</span> <span class="kw">False</span></pre>
</div>
<p>道理很硬:网关 runner 有个兜底,会<strong>丢弃任何漏进排队队列的命令文本</strong>。所以一条跑到一半发的 <span class="mono">/model</span>,若被排队,就会「<strong>既悄悄打断了 agent、又被丢弃</strong>」,用户收到一个<strong>空响应</strong>。结论:只要是能解析的 slash 命令,一律旁路、立即派发,绝不排队。这也正是<strong>缓存线</strong>要守住的危险:控制命令一旦混进对话历史、被当成用户文本,就可能让历史里冒出连续两条用户消息、破坏严格角色交替(第 7 章的不变量),进而动摇被缓存的前缀(第 6 章)。旁路让控制命令走<strong>控制通道</strong>、根本不进历史,正是从源头掐断这条危险。</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">消息到达,<span class="mono">session_key</span> 在 <span class="mono">_active_sessions</span> 里吗?(该会话正忙?)</span></div>
  <div class="step"><span class="num">2</span><span class="sc">不忙 → 正常处理;忙 → 取 <span class="mono">cmd = get_command()</span></span></div>
  <div class="step"><span class="num">3</span><span class="sc"><span class="mono">should_bypass_active_session(cmd)</span>?不是命令 → 进 <span class="mono">_pending_messages</span> 排队</span></div>
  <div class="step"><span class="num">4</span><span class="sc">是 <span class="mono">/stop /new /reset</span> → 取消在途任务 + 交接;是 <span class="mono">/approve</span> 等 → 直接内联派发</span></div>
  <div class="step"><span class="num">5</span><span class="sc">旁路两道守卫,不经 <span class="mono">_process_message_background</span>(避免会话生命周期竞争)</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「并发安全 + 不破缓存」</div>
  <div class="collab-sub">① 组件清单(★本章核心,其余跨章节配合)</div>
  本章核心:<strong>_active_sessions</strong>(busy 状态)、<strong>_pending_messages</strong>(排队)、<strong>_session_tasks</strong>(会话→任务)、<strong>should_bypass_active_session</strong>(旁路判定)、<strong>第二道 runner 守卫</strong>(GATEWAY_KNOWN_COMMANDS 分派)。跨章节配合:消息先被适配器归一化成 <strong>MessageEvent</strong>(第 17 章)才进守卫;旁路保证控制命令不污染对话历史、维持严格角色交替=<strong>不破缓存</strong>(第 6 章);<span class="mono">/stop</span> 的中断会<strong>级联到子代理</strong>(第 13 章委派);<span class="mono">/approve</span> 是危险操作的<strong>人在回路审批</strong>(第 24 章安全)。
  <div class="collab-sub">② 数据流时序</div>
  MessageEvent → 第一道守卫(<span class="mono">session_key in _active_sessions</span>?) → <span class="mono">get_command()</span> + <span class="mono">should_bypass</span> → 旁路(<span class="mono">/stop</span> 取消任务 / <span class="mono">/approve</span> 内联派发)或排队(<span class="mono">_pending_messages</span>) → 第二道守卫(runner 按 <span class="mono">canonical</span> 分派)。
  <div class="collab-sub">③ 关键点</div>
  两道守卫<strong>都必须</strong>放行控制命令;排队一个控制命令 = 被兜底丢弃(空响应)或死锁(<span class="mono">/approve</span> 等不到);旁路必须走<strong>内联派发</strong>而非 <span class="mono">_process_message_background</span>,后者管会话生命周期、清理会和在跑任务抢。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线:<strong>两道守卫拦截消息 + 控制命令旁路 = 并发安全 + 不破缓存</strong>。它主要治两条 LLM 固有约束:
  <p style="margin:.5rem 0 0"><span class="badge constraint">D·指令=数据</span>——模型分不清「这是给系统的指令」还是「这是对话内容」。网关不靠模型判断,而是用<strong>显式的 <span class="mono">get_command()</span> 解析 + 旁路通道</strong>,把 <span class="mono">/stop</span> <span class="mono">/approve</span> 这类<strong>指令</strong>从消息流里拎出来走控制通道,绝不当成对话<strong>数据</strong>喂给模型。这是 D 在网关层的工程对策。</p>
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·运维</span>——并发消息、会话生命周期、中断、审批,全是运维复杂度。两道守卫 + 旁路 + owner-task 映射,把「忙时谁能插队、谁该排队、怎么取消」管得确定、无竞争。</p>
  <p style="margin:.5rem 0 0">反模式:把所有消息一视同仁排队——<span class="mono">/approve</span> 会死锁(agent 阻塞等审批,审批却在队列里等 agent),<span class="mono">/stop</span> 会丢失,跑到一半的 <span class="mono">/model</span> 变成空响应。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>两道守卫</strong>:适配器层(busy 排队 <span class="mono">_pending_messages</span>)+ 网关 runner 层(slash 命令分派)。控制命令必须<strong>同时旁路两道</strong>。</li>
    <li><strong>旁路两类</strong>:<span class="mono">/stop /new /reset</span> 取消在途任务;<span class="mono">/approve /deny /status</span> 等直接内联派发(不取消)。</li>
    <li><strong>排队=出事</strong>:控制命令进队列会被兜底<strong>丢弃</strong>(zero-char 响应)或<strong>死锁</strong>(<span class="mono">/approve</span>)。</li>
    <li><strong>不破缓存</strong>:控制命令走控制通道、不混进对话历史,维持严格角色交替(第 6 章)。</li>
    <li><strong>避开竞争</strong>:旁路用内联派发,<strong>不走</strong> <span class="mono">_process_message_background</span>(它和会话生命周期清理抢)。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">When the agent is busy on a long task and the user sends another message — what now? By default it <strong>queues</strong>, waiting for the agent to finish. But a few commands must never queue: <span class="mono">/stop</span> (interrupt), <span class="mono">/approve</span> (the agent is blocked waiting for it). If they queue, they either <strong>leak as conversation text and get discarded</strong>, or <strong>deadlock outright</strong>. Hence the gateway's "two guards + control-command bypass."</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · the ER triage desk</div>
  Ordinary patients check in and queue (messages into <span class="mono">_pending_messages</span>), waiting to be called. But "cardiac arrest" (<span class="mono">/stop</span>) must <strong>jump the queue</strong> straight to resuscitation; and "the lab result the attending is waiting on" (<span class="mono">/approve</span>), if it also queues, leaves the doctor <strong>waiting forever, stuck</strong>. The triage desk must recognize these "must-not-queue" cases and let them through.
</div>

<div class="card macro">
  <div class="tag">🌍 Macro · two sequential guards, control commands bypass</div>
  While the agent runs, a message passes <strong>two sequential guards</strong>: ① the adapter layer (queue if busy), ② the gateway runner layer (dispatch slash commands). Ordinary chat queues dutifully; but <strong>any resolvable slash command must bypass both and dispatch inline</strong> — otherwise it gets discarded as conversation text (empty response) or deadlocks.
</div>

<h2>Guard one: the adapter-layer busy state</h2>
<p>Each adapter keeps three maps to track "is this session busy right now":</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">gateway/platforms/base.py</span><span class="ln">2154-2162 · excerpt</span></div>
  <pre><span class="cm"># _active_sessions stores each session's interrupt Event; _session_tasks</span>
<span class="cm"># maps a session to the Task processing it, so /stop /new /reset can cancel</span>
<span class="cm"># the right task and release the guard deterministically. Without it, an old</span>
<span class="cm"># task's finally could delete a newer task's guard, leaving stale busy state.</span>
self._active_sessions: Dict[str, asyncio.Event] = {}
self._pending_messages: Dict[str, MessageEvent] = {}
self._session_tasks: Dict[str, asyncio.Task] = {}</pre>
</div>
<p>If this key is in <span class="mono">_active_sessions</span>, the session is <strong>running an agent</strong>. A new ordinary message then gets stuffed into <span class="mono">_pending_messages</span> to queue, fed in after the current turn ends. <span class="mono">_session_tasks</span> records "who is processing this session," so <span class="mono">/stop</span> can cancel exactly that task without deleting someone else's guard.</p>

<h2>Bypass: control commands must not queue</h2>
<p>When a session is busy, first check whether this message is a command that should bypass:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">gateway/platforms/base.py</span><span class="ln">4262-4298 · simplified</span></div>
  <pre><span class="kw">if</span> session_key <span class="kw">in</span> self._active_sessions:
    cmd = event.get_command()
    <span class="kw">from</span> hermes_cli.commands <span class="kw">import</span> should_bypass_active_session

    <span class="kw">if</span> should_bypass_active_session(cmd):
        <span class="kw">if</span> cmd <span class="kw">in</span> {<span class="st">"stop"</span>, <span class="st">"new"</span>, <span class="st">"reset"</span>}:
            <span class="cm"># cancel the in-flight task + serialized handoff</span>
            <span class="kw">await</span> self._dispatch_active_session_command(event, session_key, cmd)
            <span class="kw">return</span>
        <span class="cm"># /approve /deny /status /background /restart: dispatch inline</span>
        <span class="cm"># Do NOT use _process_message_background — it manages session</span>
        <span class="cm"># lifecycle and its cleanup races with the running task (PR #4926)</span>
        ...</pre>
</div>
<p>Two classes: <span class="mono">/stop</span> <span class="mono">/new</span> <span class="mono">/reset</span> must <strong>cancel the in-flight task</strong> (via a dedicated handoff that serializes "cancel + respond + drain queue"); <span class="mono">/approve</span> <span class="mono">/deny</span> <span class="mono">/status</span> and friends don't cancel the task and just need <strong>inline dispatch</strong>. The comment flags a trap: <strong>never go through <span class="mono">_process_message_background</span></strong> — it manages session lifecycle, and its cleanup races with the running task.</p>

<h2>Why queueing breaks things: the zero-char response</h2>
<p>The bypass predicate's docstring spells out the consequence:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">hermes_cli/commands.py</span><span class="ln">379-399 · simplified</span></div>
  <pre><span class="kw">def</span> <span class="fn">should_bypass_active_session</span>(command_name):
    <span class="cm">&quot;&quot;&quot;Return True for any resolvable slash command.</span>
<span class="cm">    Queueing is always wrong for a recognized slash command</span>
<span class="cm">    because the safety net in gateway.run discards any command</span>
<span class="cm">    text that reaches the pending queue — a mid-run /model would</span>
<span class="cm">    silently interrupt the agent AND get discarded, a zero-char</span>
<span class="cm">    response.&quot;&quot;&quot;</span>
    <span class="kw">return</span> resolve_command(command_name) <span class="kw">is</span> <span class="kw">not</span> <span class="kw">None</span> <span class="kw">if</span> command_name <span class="kw">else</span> <span class="kw">False</span></pre>
</div>
<p>The logic is hard: the gateway runner has a safety net that <strong>discards any command text that slips into the pending queue</strong>. So a <span class="mono">/model</span> sent mid-run, if queued, would "<strong>silently interrupt the agent AND get discarded</strong>," and the user gets an <strong>empty response</strong>. Conclusion: any resolvable slash command bypasses and dispatches immediately, never queues. This is exactly the danger the <strong>cache line</strong> guards against: once a control command leaks into conversation history as user text, it could put two user messages back to back, breaking strict role alternation (the invariant from ch.7) and thereby disturbing the cached prefix (ch.6). Bypass routes control commands onto a <strong>control channel</strong>, keeping them out of history entirely — cutting the danger off at the source.</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">a message arrives — is <span class="mono">session_key</span> in <span class="mono">_active_sessions</span>? (is the session busy?)</span></div>
  <div class="step"><span class="num">2</span><span class="sc">not busy → process normally; busy → take <span class="mono">cmd = get_command()</span></span></div>
  <div class="step"><span class="num">3</span><span class="sc"><span class="mono">should_bypass_active_session(cmd)</span>? not a command → queue in <span class="mono">_pending_messages</span></span></div>
  <div class="step"><span class="num">4</span><span class="sc"><span class="mono">/stop /new /reset</span> → cancel in-flight task + handoff; <span class="mono">/approve</span> etc. → inline dispatch</span></div>
  <div class="step"><span class="num">5</span><span class="sc">bypass both guards, not via <span class="mono">_process_message_background</span> (avoid session-lifecycle races)</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "concurrency-safe + cache-preserving"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: <strong>_active_sessions</strong> (busy state), <strong>_pending_messages</strong> (queue), <strong>_session_tasks</strong> (session→task), <strong>should_bypass_active_session</strong> (bypass predicate), <strong>the second runner guard</strong> (GATEWAY_KNOWN_COMMANDS dispatch). Cross-chapter teamwork: a message is first normalized by the adapter into a <strong>MessageEvent</strong> (ch.17) before reaching the guards; bypass keeps control commands out of conversation history, preserving strict role alternation = <strong>cache intact</strong> (ch.6); a <span class="mono">/stop</span> interrupt <strong>cascades to subagents</strong> (ch.13 delegation); <span class="mono">/approve</span> is the <strong>human-in-the-loop approval</strong> for dangerous operations (ch.24 security).
  <div class="collab-sub">② Data-flow timing</div>
  MessageEvent → guard one (<span class="mono">session_key in _active_sessions</span>?) → <span class="mono">get_command()</span> + <span class="mono">should_bypass</span> → bypass (<span class="mono">/stop</span> cancels task / <span class="mono">/approve</span> inline dispatch) or queue (<span class="mono">_pending_messages</span>) → guard two (runner dispatches by <span class="mono">canonical</span>).
  <div class="collab-sub">③ The key point</div>
  Both guards <strong>must</strong> let control commands through; queueing a control command = discarded by the safety net (empty response) or deadlock (<span class="mono">/approve</span> never arrives); the bypass must use <strong>inline dispatch</strong>, not <span class="mono">_process_message_background</span>, which manages session lifecycle and whose cleanup races the running task.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>two guards intercept messages + control commands bypass = concurrency-safe + cache-preserving</strong>. It mainly treats two inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">D·instr=data</span> — the model can't tell "this is an instruction to the system" from "this is conversation content." The gateway doesn't rely on the model to judge; it uses <strong>explicit <span class="mono">get_command()</span> parsing + a bypass channel</strong> to pull <strong>instructions</strong> like <span class="mono">/stop</span> <span class="mono">/approve</span> out of the message stream onto a control channel, never feeding them to the model as conversation <strong>data</strong>. This is D's engineering countermeasure at the gateway layer.</p>
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·ops</span> — concurrent messages, session lifecycle, interrupts, approvals are all operational complexity. Two guards + bypass + an owner-task map make "who can jump the queue, who should wait, how to cancel" deterministic and race-free.</p>
  <p style="margin:.5rem 0 0">The anti-pattern: queueing all messages alike — <span class="mono">/approve</span> deadlocks (the agent blocks waiting for approval while the approval waits in the queue for the agent), <span class="mono">/stop</span> is lost, and a mid-run <span class="mono">/model</span> becomes an empty response.</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Two guards</strong>: the adapter layer (busy → queue in <span class="mono">_pending_messages</span>) + the gateway runner layer (slash-command dispatch). Control commands must <strong>bypass both</strong>.</li>
    <li><strong>Two bypass classes</strong>: <span class="mono">/stop /new /reset</span> cancel the in-flight task; <span class="mono">/approve /deny /status</span> etc. dispatch inline (no cancel).</li>
    <li><strong>Queue = trouble</strong>: a queued control command gets <strong>discarded</strong> by the safety net (zero-char response) or <strong>deadlocks</strong> (<span class="mono">/approve</span>).</li>
    <li><strong>Cache intact</strong>: control commands ride a control channel, never mixing into conversation history, preserving strict role alternation (ch.6).</li>
    <li><strong>Dodge the race</strong>: bypass uses inline dispatch, <strong>not</strong> <span class="mono">_process_message_background</span> (which races session-lifecycle cleanup).</li>
  </ul>
</div>
""",
}

LESSON_19 = {
    "zh": r"""
<p class="lead">输入 <span class="mono">hermes --tui</span>,你看到一个漂亮的终端界面。它其实是<strong>两个进程</strong>:一个 Node(Ink/React)负责画屏幕,一个 Python(tui_gateway)负责跑 agent,两者靠 stdio 上<strong>换行分隔的 JSON-RPC</strong> 对话。更妙的是:网页版仪表盘的聊天页,<strong>不是重写一遍</strong>,而是把同一个 <span class="mono">hermes --tui</span> 经 PTY 投进浏览器。</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 剧院的后台与台前</div>
  后台(Python)管演员、剧本、调度;台前(Ink)管灯光、布景、把戏呈现给观众。两边靠一根<strong>提词线</strong>(stdio 上的 JSON-RPC)协调:台前喊「观众提交了台词」(<span class="mono">prompt.submit</span>),后台一句句把演员的台词喂回来(<span class="mono">message.delta</span>)。换个剧场(浏览器)?<strong>不重排戏</strong>——直接把整台演出(<span class="mono">hermes --tui</span>)投影上去。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 一套核心,多个前端</div>
  <strong>TypeScript 拥有屏幕,Python 拥有会话/工具/模型调用</strong>,中间是一层换行分隔的 JSON-RPC。同一个 Python 后端(就是 AIAgent 核心)既服务 Ink 终端界面、又服务浏览器里嵌入的 PTY、还服务 Electron 桌面 App。前端易变、迭代快;核心稳定。各用各的生态,互不拖累。
</div>

<h2>JSON-RPC:前后端的唯一桥</h2>
<p>Python 侧用一个极简的装饰器把函数注册成「可远程调用的方法」,再统一分派:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tui_gateway/server.py</span><span class="ln">959-995 · 简化</span></div>
  <pre><span class="kw">def</span> <span class="fn">method</span>(name):
    <span class="kw">def</span> <span class="fn">dec</span>(fn):
        _methods[name] = fn          <span class="cm"># 注册进全局方法表</span>
        <span class="kw">return</span> fn
    <span class="kw">return</span> dec

<span class="kw">def</span> <span class="fn">handle_request</span>(req):
    rid, m, params = _normalize_request(req)   <span class="cm"># 校验 + 解包</span>
    fn = _methods.get(m)
    <span class="kw">if</span> <span class="kw">not</span> fn:
        <span class="kw">return</span> _err(rid, -32601, <span class="st">f"unknown method: {m}"</span>)
    <span class="kw">return</span> fn(rid, params)            <span class="cm"># 分派到注册的 handler</span></pre>
</div>
<p>每个能被前端调用的能力,只要挂一个 <span class="mono">@method("名字")</span>。<span class="mono">handle_request</span> 收到一帧 JSON-RPC,校验后按方法名查表、分派。错误也走标准的 JSON-RPC 错误信封(<span class="mono">-32601 unknown method</span>)——前端永远拿到结构化的 <span class="mono">result</span> 或 <span class="mono">error</span>,而不是去解析一段自由文本。</p>

<h2>流式回推:一个 token 一个事件</h2>
<p>用户提交后,agent 的回复要<strong>一边生成一边显示</strong>。这靠服务器主动推 <span class="mono">event</span> 帧:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tui_gateway/server.py</span><span class="ln">6828 / 887-891 / 7228 · 节选</span></div>
  <pre><span class="nd">@method</span>(<span class="st">"prompt.submit"</span>)       <span class="cm"># 前端提交一条消息</span>
<span class="kw">def</span> <span class="fn">_</span>(rid, params):
    sid, text = params.get(<span class="st">"session_id"</span>), params.get(<span class="st">"text"</span>)
    <span class="kw">if</span> session.get(<span class="st">"running"</span>):
        <span class="kw">return</span> _err(rid, 4009, <span class="st">"session busy"</span>)
    ...

<span class="kw">def</span> <span class="fn">_emit</span>(event, sid, payload=None):
    params = {<span class="st">"type"</span>: event, <span class="st">"session_id"</span>: sid, <span class="st">"payload"</span>: payload}
    write_json({<span class="st">"jsonrpc"</span>: <span class="st">"2.0"</span>, <span class="st">"method"</span>: <span class="st">"event"</span>, <span class="st">"params"</span>: params})

<span class="kw">def</span> <span class="fn">_stream</span>(delta):                            <span class="cm"># 作为 stream_callback 传给 AIAgent</span>
    _emit(<span class="st">"message.delta"</span>, sid, {<span class="st">"text"</span>: delta})   <span class="cm"># 每个流式分块推一帧</span></pre>
</div>
<p>请求/响应只是一半;另一半是<strong>服务器→前端的事件流</strong>。agent 每吐出一段文本(delta),Python 就 <span class="mono">_emit("message.delta")</span> 推一帧,Ink 收到后把它追加进 transcript——这就是你看到的「逐字蹦出来」。同一套事件机制还推 <span class="mono">tool.start/progress/complete</span>、审批请求等。</p>

<h2>仪表盘:不重写,直接嵌</h2>
<p>网页仪表盘的「聊天」页,没有用 React 重写一遍 transcript/输入框,而是把整个 <span class="mono">hermes --tui</span> 经 PTY 桥进浏览器:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">hermes_cli/web_server.py</span><span class="ln">11505-11625 · 简化</span></div>
  <pre><span class="nd">@app.websocket</span>(<span class="st">"/api/pty"</span>)
<span class="kw">async def</span> <span class="fn">pty_ws</span>(ws):
    bridge = PtyBridge.spawn(argv, cwd=cwd, env=env)  <span class="cm"># spawn 同一个 hermes --tui</span>

    <span class="kw">async def</span> <span class="fn">pump_pty_to_ws</span>():        <span class="cm"># PTY → 浏览器</span>
        <span class="kw">while</span> <span class="kw">True</span>:
            chunk = <span class="kw">await</span> loop.run_in_executor(<span class="kw">None</span>, bridge.read, ...)
            <span class="kw">if</span> chunk <span class="kw">is</span> <span class="kw">None</span>: <span class="kw">return</span>      <span class="cm"># EOF</span>
            <span class="kw">await</span> ws.send_bytes(chunk)

    <span class="kw">while</span> <span class="kw">True</span>:                        <span class="cm"># 浏览器 → PTY</span>
        msg = <span class="kw">await</span> ws.receive()
        raw = msg.get(<span class="st">"bytes"</span>)
        match = _RESIZE_RE.match(raw)       <span class="cm"># resize escape 本地拦截</span>
        ...                                 <span class="cm"># 否则原样写进 PTY</span></pre>
</div>
<p>浏览器端是 xterm.js,服务端 <span class="mono">spawn</span> 出和命令行<strong>一模一样</strong>的 <span class="mono">hermes --tui</span>,两个方向<strong>原样转发字节</strong>:PTY 输出 → <span class="mono">ws.send_bytes</span> → xterm.js 渲染;键盘输入 → PTY。只有 <span class="mono">\x1b[RESIZE:...]</span> 这样的尺寸转义在服务端本地拦截、用 <span class="mono">TIOCSWINSZ</span> 调整窗口。(PTY 桥本身也是窄腰:POSIX 用 <span class="mono">pty_bridge</span>(fcntl/termios)、Windows 用 <span class="mono">win_pty_bridge</span>(ConPTY),但 <span class="mono">spawn/read/write/resize/close</span> 是同一套公共接口,<span class="mono">/api/pty</span> handler 无需任何平台分支。)<strong>你给 Ink 加的任何新功能,仪表盘里自动就有了。</strong></p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">用户在 Ink 界面输入 → 前端发 <span class="mono">prompt.submit</span> JSON-RPC 帧</span></div>
  <div class="step"><span class="num">2</span><span class="sc">Python <span class="mono">handle_request</span> 查 <span class="mono">_methods</span> 表、分派到 handler</span></div>
  <div class="step"><span class="num">3</span><span class="sc">handler 跑 AIAgent(第 7 章核心循环),逐 token <span class="mono">_emit("message.delta")</span></span></div>
  <div class="step"><span class="num">4</span><span class="sc">Ink 收到事件流,追加进 transcript 渲染(逐字显示)</span></div>
  <div class="step"><span class="num">5</span><span class="sc">仪表盘:xterm.js ⟷ <span class="mono">/api/pty</span> WebSocket ⟷ PtyBridge ⟷ 同一个 <span class="mono">hermes --tui</span></span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「一套核心多前端」</div>
  <div class="collab-sub">① 组件清单(★本章核心,其余跨章节配合)</div>
  本章核心:<strong>method 装饰器</strong>(RPC 注册)、<strong>handle_request</strong>(分派)、<strong>_emit/write_json</strong>(事件回推)、<strong>PtyBridge</strong>(PTY 桥)。跨章节配合:JSON-RPC 后面跑的就是 <strong>AIAgent 核心循环</strong>(第 7 章)——TUI 只是它的一个前端;<span class="mono">prompt.submit</span> 的 busy 检查与<strong>网关守卫</strong>(第 18 章)同理(运行时拒新输入);仪表盘<strong>嵌入复用</strong>同一个 hermes --tui = 不重写 = <strong>窄腰</strong>(第 4 章);Electron 桌面 App 是<strong>另一个 JSON-RPC 前端</strong>(同一个 tui_gateway 后端,自带 composer)。
  <div class="collab-sub">② 数据流时序</div>
  Ink 输入 → JSON-RPC <span class="mono">prompt.submit</span> → <span class="mono">handle_request</span> 分派 → AIAgent 跑 → <span class="mono">_emit("message.delta")</span> 流式 → Ink 渲染。仪表盘旁路:xterm.js ⟷ WS <span class="mono">/api/pty</span> ⟷ <span class="mono">PtyBridge.spawn</span> ⟷ <span class="mono">hermes --tui</span> 子进程(原样转发字节)。
  <div class="collab-sub">③ 关键点</div>
  一套 agent 核心(Python)+ 多个前端(Ink TUI / 浏览器 PTY / Electron 桌面)靠 <strong>stdio JSON-RPC</strong> 解耦;仪表盘<strong>嵌入</strong>同一个 hermes --tui 而非重写;前端易变、核心稳定,各自独立迭代。给 Ink 加功能,仪表盘自动继承。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线:<strong>一套 agent 核心 + JSON-RPC 解耦多前端 + 嵌入复用 = 多端一致、不重复造轮子(窄腰)</strong>。它主要治一条 LLM 固有约束:
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·运维</span>——同一个 agent 要在命令行、TUI、网关、桌面 App、网页仪表盘多端出现。把 agent 核心收进 Python 后端、用稳定的 JSON-RPC 信封暴露,前端就能<strong>各用各的技术栈独立演进</strong>(Ink 用 React、桌面用 Electron、仪表盘用 xterm.js),而核心只维护一份。Node 前端崩了不会拖垮 Python agent,反之亦然——<strong>进程隔离</strong>也是运维健壮性。</p>
  <p style="margin:.5rem 0 0">它也是<strong>窄腰</strong>(第 4 章):聊天体验(transcript/输入/PTY 终端)只在 Ink 里实现<strong>一次</strong>,仪表盘靠 PTY 嵌入复用。反模式:为浏览器用 React <strong>重写一遍</strong> transcript 和 composer——两套实现注定漂移,改一个忘一个。AGENTS.md 为此立了硬规矩:「Do not re-implement the primary chat experience in React」。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>两进程模型</strong>:Node(Ink 渲染屏幕)⟷ stdio JSON-RPC ⟷ Python(tui_gateway 跑 AIAgent)。TS 拥有屏幕,Python 拥有会话/工具/模型。</li>
    <li><strong>JSON-RPC 桥</strong>:<span class="mono">@method("名字")</span> 注册、<span class="mono">handle_request</span> 分派、标准 result/error 信封;前端拿结构化数据而非自由文本。</li>
    <li><strong>流式事件</strong>:<span class="mono">_emit("message.delta")</span> 逐 token 推回,Ink 追加 transcript(逐字显示);tool.start/complete 同机制。</li>
    <li><strong>仪表盘嵌入</strong>:<span class="mono">/api/pty</span> WebSocket 把同一个 <span class="mono">hermes --tui</span> 经 PTY 投进 xterm.js,双向转发字节,resize 转义本地拦截。</li>
    <li><strong>窄腰复用</strong>:聊天面只实现一次(Ink),仪表盘嵌入继承;<strong>不</strong>用 React 重写——给 Ink 加功能,仪表盘自动有(第 4 章)。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">Type <span class="mono">hermes --tui</span> and you see a slick terminal UI. It's really <strong>two processes</strong>: a Node (Ink/React) one paints the screen, a Python (tui_gateway) one runs the agent, and they talk over <strong>newline-delimited JSON-RPC</strong> on stdio. Better still: the web dashboard's chat page <strong>isn't a rewrite</strong> — it pipes the same <span class="mono">hermes --tui</span> into the browser through a PTY.</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · a theatre's backstage and stage</div>
  Backstage (Python) runs the actors, the script, the cues; the stage (Ink) runs the lights, the set, presenting the play to the audience. The two coordinate via a <strong>prompter line</strong> (JSON-RPC over stdio): the stage calls "the audience submitted a line" (<span class="mono">prompt.submit</span>), backstage feeds the actor's lines back word by word (<span class="mono">message.delta</span>). A different venue (the browser)? <strong>Don't re-stage the play</strong> — just project the whole performance (<span class="mono">hermes --tui</span>) onto it.
</div>

<div class="card macro">
  <div class="tag">🌍 Macro · one core, many frontends</div>
  <strong>TypeScript owns the screen, Python owns sessions/tools/model calls</strong>, with a layer of newline-delimited JSON-RPC between them. The same Python backend (the AIAgent core) serves the Ink terminal UI, the PTY embedded in the browser, and the Electron desktop app. Frontends are volatile and iterate fast; the core is stable. Each uses its own ecosystem without dragging the other down.
</div>

<h2>JSON-RPC: the one bridge between front and back</h2>
<p>On the Python side, a tiny decorator registers a function as a "remotely callable method," then a single dispatcher routes calls:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tui_gateway/server.py</span><span class="ln">959-995 · simplified</span></div>
  <pre><span class="kw">def</span> <span class="fn">method</span>(name):
    <span class="kw">def</span> <span class="fn">dec</span>(fn):
        _methods[name] = fn          <span class="cm"># register into the global method table</span>
        <span class="kw">return</span> fn
    <span class="kw">return</span> dec

<span class="kw">def</span> <span class="fn">handle_request</span>(req):
    rid, m, params = _normalize_request(req)   <span class="cm"># validate + unpack</span>
    fn = _methods.get(m)
    <span class="kw">if</span> <span class="kw">not</span> fn:
        <span class="kw">return</span> _err(rid, -32601, <span class="st">f"unknown method: {m}"</span>)
    <span class="kw">return</span> fn(rid, params)            <span class="cm"># dispatch to the registered handler</span></pre>
</div>
<p>Any capability the frontend can call just hangs a <span class="mono">@method("name")</span> on a function. <span class="mono">handle_request</span> receives one JSON-RPC frame, validates it, looks up the method by name, and dispatches. Errors ride the standard JSON-RPC error envelope (<span class="mono">-32601 unknown method</span>) — the frontend always gets a structured <span class="mono">result</span> or <span class="mono">error</span>, never has to parse free text.</p>

<h2>Streaming back: one token, one event</h2>
<p>After the user submits, the agent's reply must <strong>display as it's generated</strong>. The server actively pushes <span class="mono">event</span> frames:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tui_gateway/server.py</span><span class="ln">6828 / 887-891 / 7228 · excerpt</span></div>
  <pre><span class="nd">@method</span>(<span class="st">"prompt.submit"</span>)       <span class="cm"># the frontend submits a message</span>
<span class="kw">def</span> <span class="fn">_</span>(rid, params):
    sid, text = params.get(<span class="st">"session_id"</span>), params.get(<span class="st">"text"</span>)
    <span class="kw">if</span> session.get(<span class="st">"running"</span>):
        <span class="kw">return</span> _err(rid, 4009, <span class="st">"session busy"</span>)
    ...

<span class="kw">def</span> <span class="fn">_emit</span>(event, sid, payload=None):
    params = {<span class="st">"type"</span>: event, <span class="st">"session_id"</span>: sid, <span class="st">"payload"</span>: payload}
    write_json({<span class="st">"jsonrpc"</span>: <span class="st">"2.0"</span>, <span class="st">"method"</span>: <span class="st">"event"</span>, <span class="st">"params"</span>: params})

<span class="kw">def</span> <span class="fn">_stream</span>(delta):                            <span class="cm"># passed to AIAgent as stream_callback</span>
    _emit(<span class="st">"message.delta"</span>, sid, {<span class="st">"text"</span>: delta})   <span class="cm"># push one frame per streamed chunk</span></pre>
</div>
<p>Request/response is only half; the other half is the <strong>server→frontend event stream</strong>. Every chunk (delta) the agent emits, Python <span class="mono">_emit("message.delta")</span> pushes a frame, and Ink appends it to the transcript — that's the "characters popping out" you see. The same event mechanism also pushes <span class="mono">tool.start/progress/complete</span>, approval requests, and more.</p>

<h2>The dashboard: don't rewrite, embed</h2>
<p>The web dashboard's "chat" page doesn't re-implement the transcript/composer in React; it bridges the whole <span class="mono">hermes --tui</span> into the browser via a PTY:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">hermes_cli/web_server.py</span><span class="ln">11505-11625 · simplified</span></div>
  <pre><span class="nd">@app.websocket</span>(<span class="st">"/api/pty"</span>)
<span class="kw">async def</span> <span class="fn">pty_ws</span>(ws):
    bridge = PtyBridge.spawn(argv, cwd=cwd, env=env)  <span class="cm"># spawn the same hermes --tui</span>

    <span class="kw">async def</span> <span class="fn">pump_pty_to_ws</span>():        <span class="cm"># PTY → browser</span>
        <span class="kw">while</span> <span class="kw">True</span>:
            chunk = <span class="kw">await</span> loop.run_in_executor(<span class="kw">None</span>, bridge.read, ...)
            <span class="kw">if</span> chunk <span class="kw">is</span> <span class="kw">None</span>: <span class="kw">return</span>      <span class="cm"># EOF</span>
            <span class="kw">await</span> ws.send_bytes(chunk)

    <span class="kw">while</span> <span class="kw">True</span>:                        <span class="cm"># browser → PTY</span>
        msg = <span class="kw">await</span> ws.receive()
        raw = msg.get(<span class="st">"bytes"</span>)
        match = _RESIZE_RE.match(raw)       <span class="cm"># resize escape intercepted locally</span>
        ...                                 <span class="cm"># otherwise written straight to the PTY</span></pre>
</div>
<p>The browser side is xterm.js; the server <span class="mono">spawn</span>s the <strong>exact same</strong> <span class="mono">hermes --tui</span> as the CLI, forwarding bytes <strong>verbatim</strong> in both directions: PTY output → <span class="mono">ws.send_bytes</span> → xterm.js renders; keystrokes → PTY. Only sizing escapes like <span class="mono">\x1b[RESIZE:...]</span> are intercepted server-side and applied with <span class="mono">TIOCSWINSZ</span>. (The PTY bridge is itself a narrow waist: POSIX uses <span class="mono">pty_bridge</span> (fcntl/termios), Windows uses <span class="mono">win_pty_bridge</span> (ConPTY), but <span class="mono">spawn/read/write/resize/close</span> is one shared interface, so the <span class="mono">/api/pty</span> handler needs no platform branches.) <strong>Any new feature you add to Ink shows up in the dashboard automatically.</strong></p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">user types in the Ink UI → frontend sends a <span class="mono">prompt.submit</span> JSON-RPC frame</span></div>
  <div class="step"><span class="num">2</span><span class="sc">Python <span class="mono">handle_request</span> looks up the <span class="mono">_methods</span> table, dispatches to the handler</span></div>
  <div class="step"><span class="num">3</span><span class="sc">the handler runs AIAgent (ch.7 core loop), <span class="mono">_emit("message.delta")</span> token by token</span></div>
  <div class="step"><span class="num">4</span><span class="sc">Ink receives the event stream, appends to the transcript (character by character)</span></div>
  <div class="step"><span class="num">5</span><span class="sc">dashboard: xterm.js ⟷ <span class="mono">/api/pty</span> WebSocket ⟷ PtyBridge ⟷ the same <span class="mono">hermes --tui</span></span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "one core, many frontends"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: the <strong>method decorator</strong> (RPC registration), <strong>handle_request</strong> (dispatch), <strong>_emit/write_json</strong> (event push), <strong>PtyBridge</strong> (the PTY bridge). Cross-chapter teamwork: behind the JSON-RPC runs the <strong>AIAgent core loop</strong> (ch.7) — the TUI is just one of its frontends; <span class="mono">prompt.submit</span>'s busy check is the same idea as the <strong>gateway guards</strong> (ch.18, rejecting new input mid-run); the dashboard <strong>embeds and reuses</strong> the same hermes --tui = no rewrite = the <strong>narrow waist</strong> (ch.4); the Electron desktop app is <strong>another JSON-RPC frontend</strong> (same tui_gateway backend, its own composer).
  <div class="collab-sub">② Data-flow timing</div>
  Ink input → JSON-RPC <span class="mono">prompt.submit</span> → <span class="mono">handle_request</span> dispatch → AIAgent runs → <span class="mono">_emit("message.delta")</span> streaming → Ink renders. Dashboard bypass: xterm.js ⟷ WS <span class="mono">/api/pty</span> ⟷ <span class="mono">PtyBridge.spawn</span> ⟷ <span class="mono">hermes --tui</span> child (verbatim byte forwarding).
  <div class="collab-sub">③ The key point</div>
  One agent core (Python) + many frontends (Ink TUI / browser PTY / Electron desktop) decoupled by <strong>stdio JSON-RPC</strong>; the dashboard <strong>embeds</strong> the same hermes --tui rather than rewriting it; frontends are volatile, the core is stable, each iterating independently. Add a feature to Ink, the dashboard inherits it.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>one agent core + JSON-RPC-decoupled frontends + embed-and-reuse = consistent across surfaces, no reinventing the wheel (narrow waist)</strong>. It mainly treats one inherent LLM constraint:
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·ops</span> — the same agent must appear on the CLI, the TUI, the gateway, the desktop app, and the web dashboard. Tucking the agent core into a Python backend exposed via a stable JSON-RPC envelope lets each frontend <strong>evolve in its own stack independently</strong> (Ink in React, desktop in Electron, dashboard in xterm.js) while the core is maintained once. A crashing Node frontend won't take down the Python agent, and vice versa — <strong>process isolation</strong> is operational robustness too.</p>
  <p style="margin:.5rem 0 0">It's also the <strong>narrow waist</strong> (ch.4): the chat experience (transcript/input/PTY terminal) is implemented <strong>once</strong> in Ink, and the dashboard reuses it by embedding via PTY. The anti-pattern: <strong>rewriting</strong> the transcript and composer in React for the browser — two implementations doomed to drift, fix one forget the other. AGENTS.md makes this a hard rule: "Do not re-implement the primary chat experience in React."</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Two-process model</strong>: Node (Ink paints the screen) ⟷ stdio JSON-RPC ⟷ Python (tui_gateway runs AIAgent). TS owns the screen, Python owns sessions/tools/model.</li>
    <li><strong>JSON-RPC bridge</strong>: <span class="mono">@method("name")</span> registers, <span class="mono">handle_request</span> dispatches, standard result/error envelope; the frontend gets structured data, not free text.</li>
    <li><strong>Streaming events</strong>: <span class="mono">_emit("message.delta")</span> pushes token by token, Ink appends to the transcript (character by character); tool.start/complete use the same mechanism.</li>
    <li><strong>Dashboard embed</strong>: the <span class="mono">/api/pty</span> WebSocket pipes the same <span class="mono">hermes --tui</span> into xterm.js via a PTY, forwarding bytes both ways, intercepting resize escapes locally.</li>
    <li><strong>Narrow-waist reuse</strong>: the chat surface is built once (Ink), the dashboard inherits it by embedding; <strong>no</strong> React rewrite — add a feature to Ink, the dashboard has it (ch.4).</li>
  </ul>
</div>
"""
}
