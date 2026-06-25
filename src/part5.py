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
