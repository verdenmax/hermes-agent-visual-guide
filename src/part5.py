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

<p>为什么非要先归一化成一种结构?因为<strong>下游消费者太多</strong>:会话路由、两道守卫(第 18 章)、agent 核心循环(第 7 章消息流)、定时任务投递(cron)、审批与中断——若它们各自都要认 Telegram、Discord、微信……二十多种原生格式,复杂度就是「消费者数 × 平台数」的乘积,加一个平台得改一圈下游。在<strong>入口处翻译一次</strong>,把这层乘法塌缩成加法:平台只管产出 <span class="mono">MessageEvent</span>,下游只管消费它,两端各自演化、互不牵连。<span class="mono">raw_message</span> 仍留着平台原始对象做「留底」,真要平台专属细节时回查得到,但<strong>主路径只碰那几个归一化字段</strong>——这正是第 4 章「窄腰」在数据结构层面的投影:把宽阔的多样性收束成一道窄接口。</p>

<div class="figure">
<svg viewBox="0 0 680 352" role="img" aria-label="多平台归一化漏斗:各平台经各自适配器翻成统一 MessageEvent,再进单一 agent 核心">
  <text x="340" y="20" text-anchor="middle" font-size="13" font-weight="700" fill="var(--blue)">▲ 协议各异 · 每个平台一种原生格式</text>
  <g font-size="11.5" text-anchor="middle">
    <rect x="15"  y="34" width="100" height="34" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="65"  y="56" fill="var(--ink)">telegram</text>
    <rect x="125" y="34" width="100" height="34" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="175" y="56" fill="var(--ink)">discord</text>
    <rect x="235" y="34" width="100" height="34" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="285" y="56" fill="var(--ink)">slack</text>
    <rect x="345" y="34" width="100" height="34" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="395" y="56" fill="var(--ink)">whatsapp</text>
    <rect x="455" y="34" width="100" height="34" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="505" y="56" fill="var(--ink)">signal</text>
    <rect x="565" y="34" width="100" height="34" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="615" y="56" fill="var(--ink)">email …</text>
  </g>
  <g stroke="var(--line)">
    <line x1="65"  y1="68" x2="65"  y2="92"/>
    <line x1="175" y1="68" x2="175" y2="92"/>
    <line x1="285" y1="68" x2="285" y2="92"/>
    <line x1="395" y1="68" x2="395" y2="92"/>
    <line x1="505" y1="68" x2="505" y2="92"/>
    <line x1="615" y1="68" x2="615" y2="92"/>
  </g>
  <g font-size="10.5" text-anchor="middle">
    <rect x="15"  y="92" width="100" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="65"  y="110" fill="var(--muted)">adapter</text>
    <rect x="125" y="92" width="100" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="175" y="110" fill="var(--muted)">adapter</text>
    <rect x="235" y="92" width="100" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="285" y="110" fill="var(--muted)">adapter</text>
    <rect x="345" y="92" width="100" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="395" y="110" fill="var(--muted)">adapter</text>
    <rect x="455" y="92" width="100" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="505" y="110" fill="var(--muted)">adapter</text>
    <rect x="565" y="92" width="100" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="615" y="110" fill="var(--muted)">adapter</text>
  </g>
  <path d="M15 126 L665 126 L450 206 L230 206 Z" fill="var(--panel-2)" stroke="var(--line)" stroke-linejoin="round"/>
  <text x="340" y="172" text-anchor="middle" font-size="11.5" fill="var(--muted)">归一化漏斗 · 压成同一种</text>
  <rect x="230" y="206" width="220" height="50" rx="9" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2.5"/>
  <text x="340" y="228" text-anchor="middle" font-size="13" font-weight="700" fill="var(--accent-ink)">统一 MessageEvent</text>
  <text x="340" y="246" text-anchor="middle" font-size="10" fill="var(--accent-ink)">所有适配器都产出它</text>
  <line x1="340" y1="256" x2="340" y2="282" stroke="var(--accent)" stroke-width="2"/>
  <path d="M334 274 L340 282 L346 274 Z" fill="var(--accent)"/>
  <rect x="230" y="284" width="220" height="46" rx="9" fill="var(--panel-2)" stroke="var(--ink)" stroke-width="2"/>
  <text x="340" y="306" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">agent 核心</text>
  <text x="340" y="323" text-anchor="middle" font-size="10" fill="var(--muted)">只认这一种抽象</text>
</svg>
<div class="fig-cap"><b>多平台归一化漏斗</b>:二十多个平台各说各的协议(Telegram Update / Discord 事件 / IRC 文本行……),但每个平台派一个 <b>adapter</b> 把它翻成<b>同一个 MessageEvent</b>——漏斗在这里收口。核心 agent 只认这唯一一种抽象,从不认识任何平台的原生格式;加一个平台只是多接一条入水管,漏斗口与下游<b>纹丝不动</b>。这正是第 4 章「窄腰」在多端接入上的投影。(诚实地说,核心仍残留极少数平台特例,如 Telegram 私聊话题、Feishu 线程,但不在主路径上。)</div>
</div>

<p>诚实地说,<span class="mono">MessageEvent</span> 并非「纯净到不含一点平台味」:它身上挂着若干<strong>只有部分平台才填</strong>的可选字段——<span class="mono">platform_update_id</span>(Telegram 的 <span class="mono">update_id</span>,供 <span class="mono">/restart</span> 推进偏移、避免同一条更新被处理两次)、<span class="mono">reply_to_message_id</span> / <span class="mono">reply_to_author_id</span>(回复上下文)、<span class="mono">auto_skill</span>(Telegram 私聊话题、Discord 频道绑定时自动加载的技能)。设计上并不强求「完美纯净」,而是让这些字段<strong>默认 None、绝大多数平台直接忽略</strong>。务实地容纳少数平台的特性,好过为抽象洁癖把能力削平——抽象是为复用服务的,不是为教条服务的。这一点也提醒读者:窄腰不等于绝对零特例,而是把特例压到最小、且不让它们污染主路径。</p>

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

<p>为什么把契约固化成 <span class="mono">ABC</span> + <span class="mono">@abstractmethod</span>,而不是写个普通基类靠口头约定?因为 abstractmethod 让<strong>「没实现 connect/send 就根本实例化不了」</strong>——契约从「文档里的君子协定」升级成「导入期的硬约束」,谁也没法只写半个适配器就硬上线。更要害的是<strong>职责切分</strong>:基类独占所有<strong>共性机器</strong>——会话路由、消息排队、<span class="mono">_active_sessions</span> 中断锁、审批、typing 心跳;子类只补<strong>传输层</strong>那点平台专属逻辑(怎么连、怎么收、怎么发)。若没有这层 ABC,每个平台都得重造一遍会话与守卫机制,bug 会在二十多份实现里各自分叉,一个修复要复制二十遍,根本无从统一收口。</p>

<p>加一个平台有两条路(见 <span class="mono">ADDING_A_PLATFORM.md</span>):<strong>插件路</strong>(推荐)——在 <span class="mono">plugins/platforms/&lt;name&gt;/</span> 写 <span class="mono">adapter.py</span> 继承 <span class="mono">BasePlatformAdapter</span>,用 <span class="mono">ctx.register_platform()</span> 注册,<strong>零改核心</strong>,插件框架自动接管配置解析、用户授权、cron 投递、状态展示与网关装配;<strong>内置路</strong>仅留给核心贡献者。连 <span class="mono">Platform</span> 枚举都用 <span class="mono">_missing_()</span> 钩子为插件平台动态造成员,<span class="mono">Platform("irc")</span> 不改枚举即可成立(且身份稳定)。另外,凡用唯一凭据(如 bot token)连接的适配器,启动时都会 <span class="mono">acquire_scoped_lock</span> 抢一把<strong>令牌锁</strong>,防止两个 profile(第 20 章)拿同一个 token 同时上线、互相顶号——这是「单进程多实例」与「跨平台」必须同时成立时的安全护栏。</p>

<div class="figure">
<svg viewBox="0 0 680 300" role="img" aria-label="加平台两条路:插件路零改核心,内置路改动核心仓库,但都继承同一 BasePlatformAdapter 契约">
  <text x="340" y="20" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">加一个平台的两条路</text>
  <rect x="25"  y="36" width="300" height="30" rx="8" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="175" y="56" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--accent-ink)">✅ 插件路(推荐)</text>
  <rect x="355" y="36" width="300" height="30" rx="8" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="2"/>
  <text x="505" y="56" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--purple)">🛠 内置路(核心贡献者)</text>
  <g font-size="11" text-anchor="middle">
    <rect x="40"  y="82" width="270" height="32" rx="7" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="175" y="102" fill="var(--ink)">plugins/platforms/&lt;name&gt;/adapter.py</text>
    <rect x="40"  y="122" width="270" height="32" rx="7" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="175" y="142" fill="var(--ink)">ctx.register_platform()</text>
    <rect x="40"  y="162" width="270" height="30" rx="7" fill="var(--accent-soft)" stroke="var(--accent)"/>
    <text x="175" y="181" font-weight="700" fill="var(--accent-ink)">零改核心 · 框架自动装配</text>

    <rect x="370" y="82" width="270" height="32" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="505" y="102" fill="var(--ink)">gateway/platforms/&lt;name&gt;.py</text>
    <rect x="370" y="122" width="270" height="32" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="505" y="142" fill="var(--ink)">改动核心仓库 + 装配代码</text>
    <rect x="370" y="162" width="270" height="30" rx="7" fill="var(--purple-soft)" stroke="var(--purple)"/>
    <text x="505" y="181" font-weight="700" fill="var(--purple)">仅核心贡献者走这条</text>
  </g>
  <line x1="175" y1="192" x2="300" y2="226" stroke="var(--line)"/>
  <path d="M291 219 L301 227 L289 230 Z" fill="var(--line)"/>
  <line x1="505" y1="192" x2="380" y2="226" stroke="var(--line)"/>
  <path d="M391 230 L379 227 L389 219 Z" fill="var(--line)"/>
  <rect x="140" y="228" width="400" height="48" rx="9" fill="var(--panel-2)" stroke="var(--ink)" stroke-width="2"/>
  <text x="340" y="250" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--ink)">都继承同一 BasePlatformAdapter 契约</text>
  <text x="340" y="268" text-anchor="middle" font-size="10.5" fill="var(--muted)">→ 核心网关主路径只认这一个抽象</text>
</svg>
<div class="fig-cap"><b>加平台两条路</b>:推荐的<b>插件路</b>在 <span class="mono">plugins/platforms/&lt;name&gt;/</span> 写一个子类、用 <span class="mono">ctx.register_platform()</span> 注册,<b>零改核心</b>,框架自动接管配置、授权、cron 投递与网关装配;<b>内置路</b>留给核心贡献者,要动核心仓库。两条路殊途同归——都继承同一个 <span class="mono">BasePlatformAdapter</span> 契约,核心网关主路径始终只认这一个抽象。绝大多数主流平台(telegram/discord/slack……)其实都走插件路。</div>
</div>

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

<p>把「平台没有的能力」在边缘 no-op 吸收,而不是让核心去判断「这个平台支不支持 typing」,差别在哪?若核心要判断,就得维护一张<strong>能力矩阵</strong>外加满地的 <span class="mono">if platform == ...</span> 分支,平台一多立刻爆炸。反过来,契约把 <span class="mono">send_typing</span> / <span class="mono">format_message</span> 等定义成<strong>所有平台能力的并集</strong>,谁缺哪个就在子类里<strong>优雅降级</strong>(返回 <span class="mono">pass</span>,或回退到默认 markdown 转换)。核心永远当「每个平台都会 typing」,照常调用即可,缺失被边缘悄悄咽掉。<strong>把差异关进边缘、让核心面对一张统一且完整的接口</strong>,正是窄腰让核心保持简单所付的代价——代价不是消失,而是被转移到了不会扩散的地方。</p>

<p><span class="mono">handle_message</span> 的 docstring 写得直白:它<strong>「靠 spawn 后台任务快速返回」</strong>——这一句是整套中断能力的地基。适配器收到消息不会卡在 agent 那一长串推理上,而是开一个后台任务就立刻回头去收下一条;<span class="mono">_active_sessions</span> 存每会话的中断 <span class="mono">Event</span>,<span class="mono">_pending_messages</span> 暂存追问消息。正因为收发不被 agent 阻塞,用户才能在 agent 跑着时再发 <span class="mono">/stop</span> 把它打断、或让后续消息排队。第 18 章那两道守卫,正是<strong>架在这套异步基底之上</strong>的:基类入口先做 stale-lock 自愈、再判 <span class="mono">_active_sessions</span> 决定排队还是旁路。若 <span class="mono">handle_message</span> 改成同步阻塞,一轮长回答就会冻住整个平台的收信——异步是「边收边算」的前提。</p>

<p>那「路由到哪个会话」又靠什么?是 <span class="mono">build_session_key()</span> 从 <span class="mono">source</span> 算出的会话键,它把 <span class="mono">platform</span> + <span class="mono">chat_id</span> + 可选的 <span class="mono">user_id</span> / <span class="mono">thread_id</span> 组合起来,并受 <span class="mono">group_sessions_per_user</span>、<span class="mono">thread_sessions_per_user</span> 两个开关调制——是「整个群共享一个会话」还是「群里每人一条独立会话」,由配置说了算。正因为核心不持有任何全局会话状态(约束 B),同一进程里 Telegram 的张三、Discord 的李四、微信群里的两个人才能凭这把键各走各的上下文、互不串台。这把键也是第 18 章两道守卫的<strong>锁粒度</strong>:守卫正是按 session_key 判断「这条会话是否正忙」,从而决定旁路还是排队,这把键贯穿了接入层到守卫层的全程。</p>

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
  <p style="margin:.5rem 0 0">抽象的弹性还体现在<strong>「同一平台两种传输」</strong>:WhatsApp 同时挂着非官方 Baileys 桥(<span class="mono">whatsapp.py</span>)和官方 Cloud API(<span class="mono">whatsapp_cloud.py</span>),二者共享 <span class="mono">WhatsAppBehaviorMixin</span>(<span class="mono">whatsapp_common.py</span>)里与协议无关的门控、提及解析、广播过滤与 markdown 转换,各自只管自己的传输,还各占一个 <span class="mono">Platform</span> 枚举值以便对不同号码同时运行(mixin 必须排在基类前,其 <span class="mono">format_message</span> 才能盖过默认实现)。不是复制两份逻辑,而是<strong>抽象基类 + 行为 mixin</strong>——抽象在「一个平台内部」也照样省重复。</p>
  <p style="margin:.5rem 0 0">最后回到根:这套统一抽象之所以值得,落点还是<strong>单进程</strong>。一个进程才能共享同一份记忆、技能、cron 与配置状态,也才能让每会话的提示词缓存(项目铁律)长活;若二十个平台各起一个进程,共享状态、统一运维与缓存复用都无从谈起。窄腰把「平台数量」这条增长轴彻底挡在核心之外,核心的复杂度只跟「能力种类」走、不跟「平台个数」走——这才是单进程托管 20+ 平台在工程上真正成立的原因。</p>
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

<p>Why insist on normalizing into one structure first? Because <strong>there are too many downstream consumers</strong>: session routing, the two guards (ch.18), the agent core loop (ch.7 message flow), cron delivery, approval and interruption. If each of them had to understand Telegram, Discord, WeChat… twenty-plus native formats, complexity becomes the product "number-of-consumers × number-of-platforms," and adding one platform means editing every consumer. <strong>Translate once at the ingress</strong> and that multiplication collapses to addition: platforms only produce <span class="mono">MessageEvent</span>, consumers only consume it, and the two ends evolve independently. <span class="mono">raw_message</span> still keeps the original platform object as a fallback for when a platform-specific detail is genuinely needed, but <strong>the main path touches only the normalized fields</strong> — this is ch.4's narrow waist projected onto a data structure: funnel broad diversity into one narrow interface.</p>

<div class="figure">
<svg viewBox="0 0 680 352" role="img" aria-label="Multi-platform normalization funnel: each platform's adapter translates into one unified MessageEvent, then into a single agent core">
  <text x="340" y="20" text-anchor="middle" font-size="13" font-weight="700" fill="var(--blue)">▲ Different protocols · one native format per platform</text>
  <g font-size="11.5" text-anchor="middle">
    <rect x="15"  y="34" width="100" height="34" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="65"  y="56" fill="var(--ink)">telegram</text>
    <rect x="125" y="34" width="100" height="34" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="175" y="56" fill="var(--ink)">discord</text>
    <rect x="235" y="34" width="100" height="34" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="285" y="56" fill="var(--ink)">slack</text>
    <rect x="345" y="34" width="100" height="34" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="395" y="56" fill="var(--ink)">whatsapp</text>
    <rect x="455" y="34" width="100" height="34" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="505" y="56" fill="var(--ink)">signal</text>
    <rect x="565" y="34" width="100" height="34" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="615" y="56" fill="var(--ink)">email …</text>
  </g>
  <g stroke="var(--line)">
    <line x1="65"  y1="68" x2="65"  y2="92"/>
    <line x1="175" y1="68" x2="175" y2="92"/>
    <line x1="285" y1="68" x2="285" y2="92"/>
    <line x1="395" y1="68" x2="395" y2="92"/>
    <line x1="505" y1="68" x2="505" y2="92"/>
    <line x1="615" y1="68" x2="615" y2="92"/>
  </g>
  <g font-size="10.5" text-anchor="middle">
    <rect x="15"  y="92" width="100" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="65"  y="110" fill="var(--muted)">adapter</text>
    <rect x="125" y="92" width="100" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="175" y="110" fill="var(--muted)">adapter</text>
    <rect x="235" y="92" width="100" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="285" y="110" fill="var(--muted)">adapter</text>
    <rect x="345" y="92" width="100" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="395" y="110" fill="var(--muted)">adapter</text>
    <rect x="455" y="92" width="100" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="505" y="110" fill="var(--muted)">adapter</text>
    <rect x="565" y="92" width="100" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="615" y="110" fill="var(--muted)">adapter</text>
  </g>
  <path d="M15 126 L665 126 L450 206 L230 206 Z" fill="var(--panel-2)" stroke="var(--line)" stroke-linejoin="round"/>
  <text x="340" y="172" text-anchor="middle" font-size="11.5" fill="var(--muted)">normalization funnel · squash into one shape</text>
  <rect x="230" y="206" width="220" height="50" rx="9" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2.5"/>
  <text x="340" y="228" text-anchor="middle" font-size="13" font-weight="700" fill="var(--accent-ink)">unified MessageEvent</text>
  <text x="340" y="246" text-anchor="middle" font-size="10" fill="var(--accent-ink)">all adapters produce it</text>
  <line x1="340" y1="256" x2="340" y2="282" stroke="var(--accent)" stroke-width="2"/>
  <path d="M334 274 L340 282 L346 274 Z" fill="var(--accent)"/>
  <rect x="230" y="284" width="220" height="46" rx="9" fill="var(--panel-2)" stroke="var(--ink)" stroke-width="2"/>
  <text x="340" y="306" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">agent core</text>
  <text x="340" y="323" text-anchor="middle" font-size="10" fill="var(--muted)">knows only this one abstraction</text>
</svg>
<div class="fig-cap"><b>Multi-platform normalization funnel</b>: twenty-plus platforms each speak their own protocol (Telegram Update / Discord event / IRC text line…), but each gets an <b>adapter</b> that translates it into <b>the same MessageEvent</b> — where the funnel narrows. The core agent knows only this single abstraction and never sees any platform's native format; adding a platform just adds one more inlet pipe while the funnel's neck and everything downstream stay <b>untouched</b>. This is ch.4's narrow waist projected onto multi-platform ingress. (Honestly, the core still keeps a few platform special-cases — e.g. Telegram DM topics, Feishu threads — but they're off the main path.)</div>
</div>

<p>To be honest, <span class="mono">MessageEvent</span> is not "pure, with zero platform flavor": it carries several <strong>optional fields only some platforms populate</strong> — <span class="mono">platform_update_id</span> (Telegram's <span class="mono">update_id</span>, used by <span class="mono">/restart</span> to advance the offset and avoid processing the same update twice), <span class="mono">reply_to_message_id</span> / <span class="mono">reply_to_author_id</span> (reply context), and <span class="mono">auto_skill</span> (skills auto-loaded for Telegram DM topics or Discord channel bindings). The design doesn't demand "perfect purity"; it lets these fields <strong>default to None and be ignored by most platforms</strong>. Pragmatically accommodating a few platforms' features beats flattening capability for the sake of abstraction purism — abstraction serves reuse, not dogma. A reminder, too: a narrow waist isn't zero special-cases, it's special-cases minimized and kept out of the main path.</p>

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

<p>Why freeze the contract as an <span class="mono">ABC</span> + <span class="mono">@abstractmethod</span> rather than a plain base class relying on convention? Because abstractmethod makes it so <strong>"an adapter that doesn't implement connect/send can't even be instantiated"</strong> — the contract is promoted from a gentleman's agreement in the docs to a hard, import-time constraint; nobody can ship half an adapter. More crucially, it's <strong>separation of duty</strong>: the base class owns all the <strong>common machinery</strong> — session routing, message queuing, the <span class="mono">_active_sessions</span> interrupt lock, approval, the typing heartbeat; the subclass fills only the <strong>transport layer's</strong> platform-specific bit (how to connect, receive, send). Without this ABC, every platform would rebuild the session-and-guard machinery, and bugs would diverge across twenty-plus implementations, with one fix needing to be copied twenty times — no way to close it centrally.</p>

<p>There are two paths to add a platform (see <span class="mono">ADDING_A_PLATFORM.md</span>): the <strong>plugin path</strong> (recommended) — write <span class="mono">adapter.py</span> under <span class="mono">plugins/platforms/&lt;name&gt;/</span> inheriting <span class="mono">BasePlatformAdapter</span>, register via <span class="mono">ctx.register_platform()</span>, with <strong>zero core changes</strong>, and the plugin framework auto-handles config parsing, user authorization, cron delivery, status display, and gateway wiring; the <strong>built-in path</strong> is reserved for core contributors. Even the <span class="mono">Platform</span> enum uses a <span class="mono">_missing_()</span> hook to mint members for plugin platforms dynamically, so <span class="mono">Platform("irc")</span> works without editing the enum (and is identity-stable). Also, any adapter that connects with a unique credential (e.g. a bot token) grabs a <strong>token lock</strong> via <span class="mono">acquire_scoped_lock</span> at startup, stopping two profiles (ch.20) from bringing the same token online at once and clobbering each other — the guardrail required when "multi-instance" and "multi-platform" must both hold.</p>

<div class="figure">
<svg viewBox="0 0 680 300" role="img" aria-label="Two paths to add a platform: the plugin path needs no core change, the built-in path edits the core repo, but both inherit the same BasePlatformAdapter contract">
  <text x="340" y="20" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">Two paths to add a platform</text>
  <rect x="25"  y="36" width="300" height="30" rx="8" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="175" y="56" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--accent-ink)">✅ Plugin path (recommended)</text>
  <rect x="355" y="36" width="300" height="30" rx="8" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="2"/>
  <text x="505" y="56" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--purple)">🛠 Built-in path (core contributors)</text>
  <g font-size="11" text-anchor="middle">
    <rect x="40"  y="82" width="270" height="32" rx="7" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="175" y="102" fill="var(--ink)">plugins/platforms/&lt;name&gt;/adapter.py</text>
    <rect x="40"  y="122" width="270" height="32" rx="7" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="175" y="142" fill="var(--ink)">ctx.register_platform()</text>
    <rect x="40"  y="162" width="270" height="30" rx="7" fill="var(--accent-soft)" stroke="var(--accent)"/>
    <text x="175" y="181" font-weight="700" fill="var(--accent-ink)">zero core change · auto-wired</text>

    <rect x="370" y="82" width="270" height="32" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="505" y="102" fill="var(--ink)">gateway/platforms/&lt;name&gt;.py</text>
    <rect x="370" y="122" width="270" height="32" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="505" y="142" fill="var(--ink)">edit core repo + wiring code</text>
    <rect x="370" y="162" width="270" height="30" rx="7" fill="var(--purple-soft)" stroke="var(--purple)"/>
    <text x="505" y="181" font-weight="700" fill="var(--purple)">core contributors only</text>
  </g>
  <line x1="175" y1="192" x2="300" y2="226" stroke="var(--line)"/>
  <path d="M291 219 L301 227 L289 230 Z" fill="var(--line)"/>
  <line x1="505" y1="192" x2="380" y2="226" stroke="var(--line)"/>
  <path d="M391 230 L379 227 L389 219 Z" fill="var(--line)"/>
  <rect x="140" y="228" width="400" height="48" rx="9" fill="var(--panel-2)" stroke="var(--ink)" stroke-width="2"/>
  <text x="340" y="250" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--ink)">both inherit the same BasePlatformAdapter contract</text>
  <text x="340" y="268" text-anchor="middle" font-size="10.5" fill="var(--muted)">→ the core gateway's main path knows only this abstraction</text>
</svg>
<div class="fig-cap"><b>Two paths to add a platform</b>: the recommended <b>plugin path</b> writes a subclass under <span class="mono">plugins/platforms/&lt;name&gt;/</span> and registers via <span class="mono">ctx.register_platform()</span> with <b>zero core changes</b>, the framework auto-handling config, authorization, cron delivery, and gateway wiring; the <b>built-in path</b> is for core contributors and edits the core repo. Both converge — they inherit the same <span class="mono">BasePlatformAdapter</span> contract, and the core gateway's main path always knows only this one abstraction. Most mainstream platforms (telegram/discord/slack…) actually take the plugin path.</div>
</div>

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

<p>What's the difference between absorbing "a capability the platform lacks" as an edge no-op versus having the core decide "does this platform support typing"? If the core decided, it would need a <strong>capability matrix</strong> plus <span class="mono">if platform == ...</span> branches everywhere, which explodes as platforms multiply. Conversely, the contract defines <span class="mono">send_typing</span> / <span class="mono">format_message</span> etc. as <strong>the union of all platforms' capabilities</strong>, and whoever lacks one <strong>degrades gracefully</strong> in the subclass (returning <span class="mono">pass</span>, or falling back to default markdown conversion). The core always assumes "every platform can type" and calls as usual; the gap is swallowed at the edge. <strong>Confining differences to the edge and presenting the core one unified, complete interface</strong> is the price the narrow waist pays to keep the core simple — the price doesn't vanish, it's relocated to where it can't spread.</p>

<p><span class="mono">handle_message</span>'s docstring says it plainly: it <strong>"returns quickly by spawning background tasks"</strong> — that one line is the foundation of all interruption support. On receiving a message the adapter doesn't block on the agent's long reasoning chain; it spawns a background task and immediately returns to receive the next message. <span class="mono">_active_sessions</span> holds the per-session interrupt <span class="mono">Event</span>, and <span class="mono">_pending_messages</span> stashes follow-ups. Precisely because send/receive isn't blocked by the agent, a user can fire <span class="mono">/stop</span> mid-run to interrupt it, or queue subsequent messages. The two guards in ch.18 sit <strong>atop this async substrate</strong>: the base entry first self-heals a stale lock, then checks <span class="mono">_active_sessions</span> to decide queue vs. bypass. If <span class="mono">handle_message</span> were synchronous-blocking, one long answer would freeze the whole platform's intake — async is the prerequisite for "compute while still receiving."</p>

<p>And what does "route to which session" rely on? The session key computed by <span class="mono">build_session_key()</span> from <span class="mono">source</span>, which combines <span class="mono">platform</span> + <span class="mono">chat_id</span> + optional <span class="mono">user_id</span> / <span class="mono">thread_id</span>, modulated by two switches, <span class="mono">group_sessions_per_user</span> and <span class="mono">thread_sessions_per_user</span> — whether "the whole group shares one session" or "each person in the group gets their own" is decided by config. Precisely because the core holds no global session state (constraint B), Telegram's Alice, Discord's Bob, and two people in a WeChat group can each follow their own context via this key without crossing wires. This key is also the <strong>lock granularity</strong> for ch.18's two guards: the guards judge "is this session busy" by session_key, thereby deciding bypass vs. queue, and the key runs end-to-end from ingress to the guard layer.</p>

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
  <p style="margin:.5rem 0 0">The abstraction's flexibility also shows in <strong>"one platform, two transports"</strong>: WhatsApp carries both the unofficial Baileys bridge (<span class="mono">whatsapp.py</span>) and the official Cloud API (<span class="mono">whatsapp_cloud.py</span>), both sharing the protocol-agnostic gating, mention parsing, broadcast filtering, and markdown conversion in <span class="mono">WhatsAppBehaviorMixin</span> (<span class="mono">whatsapp_common.py</span>), while each owns only its transport and claims its own <span class="mono">Platform</span> enum value so both can run against different numbers at once (the mixin must come before the base class so its <span class="mono">format_message</span> overrides the default). Not two copies of the logic, but <strong>an abstract base class + a behavior mixin</strong> — the abstraction kills duplication even "within one platform."</p>
  <p style="margin:.5rem 0 0">Finally, back to the root: this unified abstraction is worth it because of <strong>the single process</strong>. One process is what lets the same memory, skills, cron, and config state be shared, and what keeps each conversation's prompt cache (a project hard rule) alive long-term; if twenty platforms each ran their own process, shared state, unified ops, and cache reuse would all be off the table. The narrow waist keeps the "number of platforms" growth axis entirely out of the core, so core complexity tracks "kinds of capability," not "count of platforms" — that's the real reason hosting 20+ platforms in one process is engineering-feasible at all.</p>
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

<p>为什么要单独维护 <span class="mono">_session_tasks</span> 这张「会话→任务」映射?注释点破了根:没有它,旧任务结束时的 <span class="mono">finally</span> 可能误删新任务刚装上的守卫,留下 <strong>stale busy</strong> 状态。更糟的是「裂脑」——适配器还以为会话在跑、实际却没人处理,聊天会永远卡在「Interrupting current task...」直到重启网关。所以 <span class="mono">handle_message</span> 一进门就先调 <span class="mono">_heal_stale_session_lock</span>:若 owner task 已 done/cancelled 就判定锁失效,清掉三张表并放行(issue #11016)。这是<strong>运维约束 G</strong> 在会话层的自愈——宁可自己修,也绝不让用户卡死在永久 busy 里。</p>

<p>为什么 busy 状态按<strong>每会话</strong>记而不是开一把全局锁?<span class="mono">_active_sessions</span> 以 <span class="mono">session_key</span>(区分用户 / 群 / 线程)为键,不同会话各自独立排队、互不阻塞——一个用户的长任务绝不会冻住整个网关里其他人的对话。而且它存的不是布尔,是一个 <span class="mono">asyncio.Event</span>(中断信号):<span class="mono">/stop</span> 能 <span class="mono">set</span> 这个 Event,通知正在跑的回合「该停了」。这个中断会沿委派链<strong>级联到子代理</strong>(第 13 章),保证一声 <span class="mono">/stop</span> 整棵任务树都停,而不是只停最外层那一个。</p>

<p>顺带看排队本身的形状:<span class="mono">_pending_messages</span> 是 <span class="mono">Dict[str, MessageEvent]</span>——<strong>每会话只有一个槽位</strong>,而非无限堆积的列表。忙时连发的多条普通消息会经 <span class="mono">merge_pending_message_event</span> <strong>合并</strong>进同一槽:相册照片连拍归并成一条、Telegram 的连续文字补充被<strong>追加</strong>而非互相覆盖。这么设计是因为「等 agent 跑完再处理」时,用户真正想要的是「我攒的这一段完整意思」,而不是几十条割裂消息逐条回放;单槽 + 合并既防了消息洪水冲垮下一回合,又不会把多段同一思路<strong>悄悄截断</strong>成最后一句(这正是被修过的 bug)。</p>

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

<div class="figure">
<svg viewBox="0 0 680 360" role="img" aria-label="agent 忙时消息要过两道守卫，控制命令必须同时旁路两道">
  <defs><marker id="g18a" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6 Z" fill="var(--muted)"/></marker></defs>
  <text x="340" y="17" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">agent 忙时 · 两道顺序守卫 + 控制命令旁路</text>

  <rect x="275" y="26" width="130" height="30" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="340" y="45" text-anchor="middle" font-size="12" fill="var(--blue)">新消息到达</text>
  <line x1="340" y1="56" x2="340" y2="69" stroke="var(--muted)" marker-end="url(#g18a)"/>

  <rect x="30" y="70" width="620" height="50" rx="10" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="44" y="88" font-size="10.5" fill="var(--faint)">守卫① 适配器层 · gateway/platforms/base.py</text>
  <text x="340" y="110" text-anchor="middle" font-size="12.5" fill="var(--ink)">session_key ∈ _active_sessions ？ → 会话忙？</text>

  <text x="232" y="137" text-anchor="middle" font-size="10.5" fill="var(--muted)">普通对话 →</text>
  <text x="452" y="137" text-anchor="middle" font-size="10.5" fill="var(--accent-ink)">可解析命令 → 旁路</text>
  <path d="M340 120 L340 144 L130 144 L130 153" fill="none" stroke="var(--muted)" marker-end="url(#g18a)"/>
  <path d="M340 120 L340 144 L445 144 L445 153" fill="none" stroke="var(--muted)" marker-end="url(#g18a)"/>

  <rect x="45" y="156" width="170" height="62" rx="9" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="130" y="182" text-anchor="middle" font-size="12" fill="var(--ink)">排队等待</text>
  <text x="130" y="202" text-anchor="middle" font-size="10" fill="var(--muted)">→ _pending_messages</text>
  <text x="130" y="238" text-anchor="middle" font-size="10" fill="var(--faint)">等当前回合结束再喂入模型</text>

  <rect x="240" y="156" width="410" height="46" rx="10" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="254" y="174" font-size="10.5" fill="var(--faint)">守卫② 网关 runner · gateway/run.py</text>
  <text x="445" y="195" text-anchor="middle" font-size="12" fill="var(--ink)">按 canonical 名显式分派</text>
  <path d="M445 202 L445 212 L341 212 L341 221" fill="none" stroke="var(--muted)" marker-end="url(#g18a)"/>
  <path d="M445 202 L445 212 L550 212 L550 221" fill="none" stroke="var(--muted)" marker-end="url(#g18a)"/>

  <rect x="242" y="224" width="198" height="60" rx="9" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="341" y="249" text-anchor="middle" font-size="11.5" fill="var(--accent-ink)">/stop  /new  /reset</text>
  <text x="341" y="269" text-anchor="middle" font-size="9.5" fill="var(--accent-ink)">取消在途任务 · 序列化交接</text>

  <rect x="452" y="224" width="196" height="60" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="550" y="249" text-anchor="middle" font-size="11" fill="var(--blue)">/approve  /deny  /status</text>
  <text x="550" y="269" text-anchor="middle" font-size="9.5" fill="var(--blue)">内联派发（不取消任务）</text>

  <rect x="30" y="302" width="620" height="46" rx="9" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="340" y="323" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--red)">⚠ 审批类命令必须同时旁路两道守卫</text>
  <text x="340" y="341" text-anchor="middle" font-size="10" fill="var(--muted)">若排队：被兜底丢弃 = 空响应(zero-char)，或 /approve 等不到 → 死锁</text>
</svg>
<div class="fig-cap"><b>两道消息守卫 + 控制命令旁路</b>：agent 忙时,消息先过<b>守卫①</b>(适配器层 <span class="mono">base.py</span>)——普通对话进 <span class="mono">_pending_messages</span> 排队;<b>可解析 slash 命令则旁路守卫①</b>,再进<b>守卫②</b>(网关 runner <span class="mono">run.py</span>)按 <span class="mono">canonical</span> 名分派:<span class="mono">/stop /new /reset</span> 取消在途任务、<span class="mono">/approve /deny /status</span> 内联派发。<b>审批类命令必须同时旁路两道</b>,否则被兜底丢弃(空响应)或死锁。</div>
</div>

<p>为什么旁路还要再分「取消任务」和「内联派发」两类?<span class="mono">/stop</span> <span class="mono">/new</span> <span class="mono">/reset</span> 会动<strong>会话生命周期</strong>(要终止在途回合),必须走 <span class="mono">_dispatch_active_session_command</span> 这条把「取消 + 回应 + 排空队列」<strong>序列化</strong>的专路;否则旧任务的 <span class="mono">finally</span> 清理会和新命令的清理抢同一把守卫。而 <span class="mono">/approve</span> <span class="mono">/deny</span> <span class="mono">/status</span> 不碰生命周期,只发信号或只读状态,直接内联即可。注释之所以严禁走 <span class="mono">_process_message_background</span>,正因它会另起一个管生命周期的 task,清理逻辑和正在跑的任务<strong>赛跑</strong>(PR #4926)——这种竞态在压测下才偶发,极难复现,所以宁可从结构上堵死。</p>

<p>为什么 <span class="mono">/approve</span> 是死锁的重灾区?agent 此刻正阻塞在 <span class="mono">tools/approval.py</span> 里一个 <span class="mono">threading.Event.wait()</span> 上——而普通中断走的是 asyncio 路径,<strong>根本叫不醒</strong>一个卡在线程 Event 上的 agent。所以 runner 把 <span class="mono">/approve</span> <span class="mono">/deny</span> 直接路由到审批处理器去 <span class="mono">set</span> 那个 Event。若让它老实排队:agent 等审批放行、审批却在队列里等 agent 跑完,两边互锁、永久卡死。这正是第 24 章<strong>人在回路</strong>审批能在 agent 阻塞时仍然送达的底座——审批信号必须有一条不经 agent 主循环的旁路才能解锁它自己。</p>

<p>值得注意的是,runner 这一层的旁路并非「命令 = 一律放行」的二元开关,而是<strong>逐命令</strong>定细则。比如 <span class="mono">/background</span> 旁路守卫去开一个并行任务、绝不打断当前对话;<span class="mono">/kanban</span> 写的是与运行态无关的看板库,<span class="mono">/kanban unblock</span> 甚至常常是解救一个阻塞 worker 的唯一手段,所以必须能在跑动中送达;<span class="mono">/goal</span> 的 <span class="mono">status</span>/<span class="mono">pause</span>/<span class="mono">clear</span> 只读控制面、放行,但「<strong>设新目标</strong>」会和当前回合抢续写,于是被拒、提示先 <span class="mono">/stop</span>。这种细粒度恰恰说明:能否中途执行,取决于该命令<strong>碰不碰运行态</strong>,而不是它是不是命令。</p>

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

<p>为什么命令识别要用<strong>显式代码解析</strong>而不交给模型判断?<span class="mono">get_command()</span> 只做纯语法切分:取首词、剥掉 <span class="mono">/</span>、去掉 <span class="mono">@botname</span>、首词里含 <span class="mono">/</span> 的当文件路径直接拒掉;再由 <span class="mono">resolve_command()</span> 查中央 <span class="mono">COMMAND_REGISTRY</span> 的别名表确认。整条链零模型参与——因为模型分不清「这是给系统的指令还是要处理的数据」(约束 <strong>D</strong>)。一旦把判断权交给模型,一段精心构造的对话文本就能伪装成 <span class="mono">/stop</span> 骗它执行。把识别钉死在网关层,注入便没了入口。</p>

<div class="figure">
<svg viewBox="0 0 680 322" role="img" aria-label="网关用显式代码解析识别控制命令，而非交给模型判断">
  <defs><marker id="g18b" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6 Z" fill="var(--muted)"/></marker></defs>
  <text x="340" y="17" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">控制命令 vs 数据 · 网关显式代码识别（治 D：指令=数据）</text>

  <rect x="270" y="28" width="140" height="30" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="340" y="47" text-anchor="middle" font-size="12" fill="var(--ink)">消息文本 raw</text>
  <line x1="340" y1="58" x2="340" y2="71" stroke="var(--muted)" marker-end="url(#g18b)"/>

  <rect x="190" y="72" width="300" height="52" rx="10" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="340" y="94" text-anchor="middle" font-size="12" fill="var(--purple)">get_command() → resolve_command()</text>
  <text x="340" y="112" text-anchor="middle" font-size="9.5" fill="var(--muted)">纯语法切分 + 查 COMMAND_REGISTRY · 零模型参与</text>

  <path d="M340 124 L340 140 L165 140 L165 155" fill="none" stroke="var(--muted)" marker-end="url(#g18b)"/>
  <path d="M340 124 L340 140 L515 140 L515 155" fill="none" stroke="var(--muted)" marker-end="url(#g18b)"/>

  <rect x="40" y="158" width="250" height="70" rx="9" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="165" y="181" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--accent-ink)">resolve ≠ None → 控制通道</text>
  <text x="165" y="201" text-anchor="middle" font-size="10" fill="var(--accent-ink)">旁路派发，永不进对话历史</text>
  <text x="165" y="219" text-anchor="middle" font-size="9.5" fill="var(--muted)">/stop  /approve  /model …</text>

  <rect x="390" y="158" width="250" height="70" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="515" y="181" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">否则 = 数据 → 对话通道</text>
  <text x="515" y="201" text-anchor="middle" font-size="10" fill="var(--blue)">进 _pending_messages → 喂给模型</text>
  <text x="515" y="219" text-anchor="middle" font-size="9.5" fill="var(--muted)">真正的对话内容</text>

  <rect x="40" y="246" width="600" height="64" rx="9" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="56" y="266" font-size="11" font-weight="700" fill="var(--red)">✗ 反模式：把识别交给模型判断</text>
  <text x="56" y="285" font-size="10" fill="var(--muted)">构造文本可伪装 /stop 触发执行（注入）；命令混入历史 → 历史出现连续两条 user</text>
  <text x="56" y="302" font-size="10" fill="var(--muted)">→ 破坏严格角色交替（第7章）→ 动摇被缓存前缀（第6章）。显式解析 = 从源头堵死。</text>
</svg>
<div class="fig-cap"><b>控制命令 vs 数据：显式解析</b>：网关用 <span class="mono">get_command()</span>/<span class="mono">resolve_command()</span> 纯代码识别命令(确定性、零模型)——能解析的走<b>控制通道</b>旁路派发、<b>永不进对话历史</b>;否则当<b>数据</b>进 <span class="mono">_pending_messages</span> 喂给模型。这正是治 <b>D·指令=数据</b>:不让模型判断,既挡注入(伪造指令进不来),又护住第 6 章缓存前缀与第 7 章角色交替。</div>
</div>

<p>为什么旁路判据用「<strong>能否解析</strong>」而不是一张写死的白名单?<span class="mono">should_bypass_active_session</span> 直接返回 <span class="mono">resolve_command(cmd) is not None</span>——只要是注册过的 slash 命令一律旁路。<span class="mono">ACTIVE_SESSION_BYPASS_COMMANDS</span> 只是「有专属 Level-2 处理器」的子集;其余命令落到 runner 的 catch-all,回一句「Agent is running,wait or <span class="mono">/stop</span>」而不是被默默丢弃。这层兜底是一串事故堆出来的:<span class="mono">/model</span> <span class="mono">/reasoning</span> <span class="mono">/resume</span> <span class="mono">/undo</span> 等当年都漏过、变成空响应(#5057 #6252 #10370)。所以判据必须是<strong>全集</strong>覆盖,白名单一定会漏掉下一个新加的命令。</p>

<p>第二道守卫内部其实是个<strong>两级结构</strong>:有专属处理器的命令(<span class="mono">_DEDICATED_HANDLERS</span>,即 <span class="mono">ACTIVE_SESSION_BYPASS_COMMANDS</span>)被精确分派到 <span class="mono">_handle_approve_command</span>、<span class="mono">_handle_help_command</span> 这类函数;剩下所有「能解析但没专属处理器」的命令统一落到 catch-all,返回一句礼貌的「<span class="mono">/x</span> 不能中途跑,先 <span class="mono">/stop</span>」。关键在于:catch-all 是<strong>优雅拒绝</strong>而非「中断 + 丢弃」。少了它,这些命令会先<strong>悄悄打断</strong> agent、再被安全网吞掉,用户只看到空响应(#5057 #6252 #10370 正是补这个洞)。两级一起保证:认得的命令要么被正确处理,要么被明确告知,绝不静默吃掉。</p>

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
  <p style="margin:.5rem 0 0">把两道守卫连起来看为什么<strong>缺一不可</strong>:第一道(适配器)只管「忙时谁排队、谁旁路」,放行后命令还得有人接;第二道(runner)按 <span class="mono">canonical</span> 名把它精确分派给 <span class="mono">_handle_approve_command</span> 等专属处理器,并对没有处理器的命令兜底拒绝。两道职责正交——一道决定「<strong>要不要排队</strong>」,一道决定「<strong>派给谁</strong>」。少了第一道,<span class="mono">/approve</span> 进队列死锁;少了第二道,旁路出来的命令无人接、又被 catch-all 当文本丢弃,照样是空响应。</p>
  <p style="margin:.5rem 0 0">为什么说这层就是第 24 章纵深防御里的「<strong>注入隔离</strong>」:控制通道和数据通道在网关就被<strong>物理分开</strong>——能解析的命令走代码识别 + 旁路,永不进对话历史;只有真正的对话才进 <span class="mono">_pending_messages</span> 喂给模型。这条「指令绝不当数据」的边界既挡注入(伪造指令进不了控制通道),又顺手护住第 6 章缓存与第 7 章角色交替:因为历史里<strong>永远不会</strong>冒出一条被误当用户文本的 <span class="mono">/stop</span>,缓存前缀和严格交替自然就稳了。</p>
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

<p>Why maintain <span class="mono">_session_tasks</span>, a separate "session→task" map? The comment names the root: without it, an old task's <span class="mono">finally</span> could delete the guard a newer task just installed, leaving <strong>stale busy</strong> state. Worse is a split-brain — the adapter still thinks the session is running while nothing actually processes it, trapping the chat in an endless "Interrupting current task..." until the gateway restarts. So <span class="mono">handle_message</span> calls <span class="mono">_heal_stale_session_lock</span> on entry: if the owner task is already done/cancelled the lock is stale, so it clears all three maps and falls through (issue #11016). This is <strong>ops constraint G</strong> self-healing at the session layer — fix it rather than strand the user in permanent busy.</p>

<p>Why track busy state <strong>per session</strong> instead of one global lock? <span class="mono">_active_sessions</span> is keyed by <span class="mono">session_key</span> (distinguishing user / group / thread), so different sessions queue independently and never block each other — one user's long task can't freeze every other conversation in the gateway. And it stores not a boolean but an <span class="mono">asyncio.Event</span> (the interrupt signal): <span class="mono">/stop</span> can <span class="mono">set</span> that Event to tell the running turn "stop now." That interrupt <strong>cascades to subagents</strong> down the delegation chain (ch.13), so one <span class="mono">/stop</span> halts the whole task tree, not just the outermost layer.</p>

<p>It's worth noting the shape of the queue itself: <span class="mono">_pending_messages</span> is a <span class="mono">Dict[str, MessageEvent]</span> — <strong>one slot per session</strong>, not an unbounded list. Multiple ordinary messages sent while busy are <strong>merged</strong> into that single slot via <span class="mono">merge_pending_message_event</span>: a burst of album photos coalesces into one event, and bursty Telegram text follow-ups are <strong>appended</strong> rather than overwriting each other. This is deliberate because when "process after the agent finishes," what the user really wants is "the complete thought I've been assembling," not dozens of fragmented messages replayed one by one. One slot + merge both prevents a message flood from swamping the next turn and avoids <strong>silently truncating</strong> a multi-part thought down to its last fragment (a bug that was actually fixed).</p>

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

<div class="figure">
<svg viewBox="0 0 680 360" role="img" aria-label="while busy a message passes two guards; control commands must bypass both">
  <defs><marker id="g18ae" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6 Z" fill="var(--muted)"/></marker></defs>
  <text x="340" y="17" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">Agent busy · two sequential guards + control-command bypass</text>

  <rect x="270" y="26" width="140" height="30" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="340" y="45" text-anchor="middle" font-size="12" fill="var(--blue)">new message arrives</text>
  <line x1="340" y1="56" x2="340" y2="69" stroke="var(--muted)" marker-end="url(#g18ae)"/>

  <rect x="30" y="70" width="620" height="50" rx="10" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="44" y="88" font-size="10.5" fill="var(--faint)">Guard ① adapter layer · gateway/platforms/base.py</text>
  <text x="340" y="110" text-anchor="middle" font-size="12.5" fill="var(--ink)">session_key ∈ _active_sessions ？ → session busy？</text>

  <text x="228" y="137" text-anchor="middle" font-size="10.5" fill="var(--muted)">ordinary chat →</text>
  <text x="455" y="137" text-anchor="middle" font-size="10.5" fill="var(--accent-ink)">resolvable command → bypass</text>
  <path d="M340 120 L340 144 L130 144 L130 153" fill="none" stroke="var(--muted)" marker-end="url(#g18ae)"/>
  <path d="M340 120 L340 144 L445 144 L445 153" fill="none" stroke="var(--muted)" marker-end="url(#g18ae)"/>

  <rect x="45" y="156" width="170" height="62" rx="9" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="130" y="182" text-anchor="middle" font-size="12" fill="var(--ink)">queue &amp; wait</text>
  <text x="130" y="202" text-anchor="middle" font-size="10" fill="var(--muted)">→ _pending_messages</text>
  <text x="130" y="238" text-anchor="middle" font-size="10" fill="var(--faint)">fed in after the current turn ends</text>

  <rect x="240" y="156" width="410" height="46" rx="10" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="254" y="174" font-size="10.5" fill="var(--faint)">Guard ② gateway runner · gateway/run.py</text>
  <text x="445" y="195" text-anchor="middle" font-size="12" fill="var(--ink)">dispatch by canonical name</text>
  <path d="M445 202 L445 212 L341 212 L341 221" fill="none" stroke="var(--muted)" marker-end="url(#g18ae)"/>
  <path d="M445 202 L445 212 L550 212 L550 221" fill="none" stroke="var(--muted)" marker-end="url(#g18ae)"/>

  <rect x="242" y="224" width="198" height="60" rx="9" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="341" y="249" text-anchor="middle" font-size="11.5" fill="var(--accent-ink)">/stop  /new  /reset</text>
  <text x="341" y="269" text-anchor="middle" font-size="9.5" fill="var(--accent-ink)">cancel in-flight task · serialized</text>

  <rect x="452" y="224" width="196" height="60" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="550" y="249" text-anchor="middle" font-size="11" fill="var(--blue)">/approve  /deny  /status</text>
  <text x="550" y="269" text-anchor="middle" font-size="9.5" fill="var(--blue)">inline dispatch (no cancel)</text>

  <rect x="30" y="302" width="620" height="46" rx="9" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="340" y="323" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--red)">⚠ approval commands must bypass BOTH guards</text>
  <text x="340" y="341" text-anchor="middle" font-size="10" fill="var(--muted)">if queued: discarded = empty (zero-char) response, or /approve deadlocks</text>
</svg>
<div class="fig-cap"><b>Two message guards + control-command bypass</b>: while the agent is busy, a message first hits <b>guard ①</b> (adapter layer <span class="mono">base.py</span>) — ordinary chat queues into <span class="mono">_pending_messages</span>; a <b>resolvable slash command bypasses guard ①</b> and reaches <b>guard ②</b> (gateway runner <span class="mono">run.py</span>), dispatched by <span class="mono">canonical</span> name: <span class="mono">/stop /new /reset</span> cancel the in-flight task, <span class="mono">/approve /deny /status</span> dispatch inline. <b>Approval commands must bypass BOTH guards</b>, else they are discarded (empty response) or deadlock.</div>
</div>

<p>Why split the bypass further into "cancel the task" vs "inline dispatch"? <span class="mono">/stop</span> <span class="mono">/new</span> <span class="mono">/reset</span> touch <strong>session lifecycle</strong> (they must terminate the in-flight turn), so they go through <span class="mono">_dispatch_active_session_command</span>, a dedicated path that <strong>serializes</strong> "cancel + respond + drain queue"; otherwise the old task's <span class="mono">finally</span> cleanup races the new command's cleanup over the same guard. <span class="mono">/approve</span> <span class="mono">/deny</span> <span class="mono">/status</span> don't touch lifecycle — they only signal or read state — so inline is enough. The comment forbids <span class="mono">_process_message_background</span> precisely because it spawns another lifecycle-managing task whose cleanup <strong>races</strong> the running one (PR #4926) — a race that only shows up under load and is brutal to reproduce, so it is structurally designed out.</p>

<p>Why is <span class="mono">/approve</span> the worst deadlock risk? The agent is right now blocked on a <span class="mono">threading.Event.wait()</span> inside <span class="mono">tools/approval.py</span> — and an ordinary interrupt travels the asyncio path, which <strong>cannot wake</strong> an agent stuck on a thread Event. So the runner routes <span class="mono">/approve</span> <span class="mono">/deny</span> straight to the approval handler to <span class="mono">set</span> that Event. If it queued instead: the agent waits for approval while the approval waits in the queue for the agent to finish — both locked forever. This is the foundation that lets ch.24's <strong>human-in-the-loop</strong> approval reach the agent even while it is blocked: the approval signal needs a path that bypasses the agent's own loop to unlock it.</p>

<p>Notably, the runner-layer bypass is not a binary "command = always let through" switch but a <strong>per-command</strong> policy. For example <span class="mono">/background</span> bypasses the guard to start a parallel task and must never interrupt the active conversation; <span class="mono">/kanban</span> writes a board DB unrelated to runtime state, and <span class="mono">/kanban unblock</span> is often the only way to free a blocked worker, so it must be deliverable mid-run; <span class="mono">/goal</span>'s <span class="mono">status</span>/<span class="mono">pause</span>/<span class="mono">clear</span> read the control plane and pass, but "<strong>setting a new goal</strong>" would race the current turn's continuation, so it is rejected with a "wait or <span class="mono">/stop</span>" message. This granularity shows the real test: whether a command can run mid-turn depends on whether it <strong>touches runtime state</strong>, not on whether it is a command.</p>

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

<p>Why identify commands with <strong>explicit code parsing</strong> rather than letting the model judge? <span class="mono">get_command()</span> does purely syntactic splitting: take the first word, strip the <span class="mono">/</span>, drop <span class="mono">@botname</span>, and reject anything whose first word contains a <span class="mono">/</span> as a file path; then <span class="mono">resolve_command()</span> confirms it against the central <span class="mono">COMMAND_REGISTRY</span> alias table. The whole chain involves zero model judgment — because the model can't tell "is this an instruction to the system or data to process" (constraint <strong>D</strong>). Hand that decision to the model and a carefully crafted piece of conversation text could impersonate <span class="mono">/stop</span> and get it executed. Nail recognition down at the gateway and injection loses its entry point.</p>

<div class="figure">
<svg viewBox="0 0 680 322" role="img" aria-label="the gateway recognizes control commands with explicit code parsing, not by asking the model">
  <defs><marker id="g18be" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6 Z" fill="var(--muted)"/></marker></defs>
  <text x="340" y="17" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--ink)">Control command vs data · explicit code recognition (treats D: instruction=data)</text>

  <rect x="270" y="28" width="140" height="30" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="340" y="47" text-anchor="middle" font-size="12" fill="var(--ink)">raw message text</text>
  <line x1="340" y1="58" x2="340" y2="71" stroke="var(--muted)" marker-end="url(#g18be)"/>

  <rect x="190" y="72" width="300" height="52" rx="10" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="340" y="94" text-anchor="middle" font-size="12" fill="var(--purple)">get_command() → resolve_command()</text>
  <text x="340" y="112" text-anchor="middle" font-size="9.5" fill="var(--muted)">syntactic split + COMMAND_REGISTRY lookup · zero model</text>

  <path d="M340 124 L340 140 L165 140 L165 155" fill="none" stroke="var(--muted)" marker-end="url(#g18be)"/>
  <path d="M340 124 L340 140 L515 140 L515 155" fill="none" stroke="var(--muted)" marker-end="url(#g18be)"/>

  <rect x="40" y="158" width="250" height="70" rx="9" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="165" y="181" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--accent-ink)">resolve ≠ None → control channel</text>
  <text x="165" y="201" text-anchor="middle" font-size="10" fill="var(--accent-ink)">bypass dispatch, never enters history</text>
  <text x="165" y="219" text-anchor="middle" font-size="9.5" fill="var(--muted)">/stop  /approve  /model …</text>

  <rect x="390" y="158" width="250" height="70" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="515" y="181" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">otherwise = data → conversation</text>
  <text x="515" y="201" text-anchor="middle" font-size="10" fill="var(--blue)">→ _pending_messages → model</text>
  <text x="515" y="219" text-anchor="middle" font-size="9.5" fill="var(--muted)">genuine conversation content</text>

  <rect x="40" y="246" width="600" height="64" rx="9" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="56" y="266" font-size="11" font-weight="700" fill="var(--red)">✗ anti-pattern: let the model judge recognition</text>
  <text x="56" y="285" font-size="9.5" fill="var(--muted)">crafted text can impersonate /stop (injection); a leaked command → two user messages in a row</text>
  <text x="56" y="302" font-size="9.5" fill="var(--muted)">→ breaks strict role alternation (ch.7) → disturbs the cached prefix (ch.6). Explicit parsing seals it.</text>
</svg>
<div class="fig-cap"><b>Control command vs data: explicit parsing</b>: the gateway recognizes commands with pure code — <span class="mono">get_command()</span>/<span class="mono">resolve_command()</span> (deterministic, zero model). Resolvable ones ride the <b>control channel</b>, bypass-dispatched and <b>never entering conversation history</b>; everything else is <b>data</b> queued into <span class="mono">_pending_messages</span> for the model. This treats <b>D · instruction=data</b>: not trusting the model to judge both blocks injection (a forged instruction can't get in) and protects the ch.6 cache prefix and ch.7 role alternation.</div>
</div>

<p>Why is the bypass predicate "<strong>is it resolvable</strong>" rather than a hardcoded allow-list? <span class="mono">should_bypass_active_session</span> simply returns <span class="mono">resolve_command(cmd) is not None</span> — any registered slash command bypasses. <span class="mono">ACTIVE_SESSION_BYPASS_COMMANDS</span> is only the subset with explicit Level-2 handlers; the rest land in the runner's catch-all, which replies "Agent is running, wait or <span class="mono">/stop</span>" instead of being silently discarded. That safety net was built from a string of incidents: <span class="mono">/model</span> <span class="mono">/reasoning</span> <span class="mono">/resume</span> <span class="mono">/undo</span> all once slipped through into empty responses (#5057 #6252 #10370). So the predicate must cover the <strong>full set</strong>; an allow-list will always miss the next new command.</p>

<p>Inside the second guard there is actually a <strong>two-tier structure</strong>: commands with a dedicated handler (<span class="mono">_DEDICATED_HANDLERS</span>, i.e. <span class="mono">ACTIVE_SESSION_BYPASS_COMMANDS</span>) are dispatched precisely to functions like <span class="mono">_handle_approve_command</span> and <span class="mono">_handle_help_command</span>; every other "resolvable but handler-less" command falls into the catch-all, which returns a polite "<span class="mono">/x</span> can't run mid-turn, <span class="mono">/stop</span> first." The crux: the catch-all is a <strong>graceful refusal</strong>, not "interrupt + discard." Without it, those commands would first <strong>silently interrupt</strong> the agent and then be swallowed by the safety net, leaving the user an empty response (#5057 #6252 #10370 patched exactly this hole). Together the two tiers guarantee: a recognized command is either handled correctly or explicitly told no — never silently eaten.</p>

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
  <p style="margin:.5rem 0 0">Seen together, why are the two guards <strong>each indispensable</strong>: guard one (adapter) only decides "who queues, who bypasses when busy," but a let-through command still needs someone to handle it; guard two (runner) dispatches it by <span class="mono">canonical</span> name to a dedicated handler like <span class="mono">_handle_approve_command</span>, and rejects any command with no handler. Their duties are orthogonal — one decides "<strong>queue or not</strong>," the other "<strong>dispatch to whom</strong>." Drop guard one and <span class="mono">/approve</span> deadlocks in the queue; drop guard two and a bypassed command finds no handler and is discarded as text by the catch-all — an empty response again.</p>
  <p style="margin:.5rem 0 0">Why this layer IS the "<strong>injection isolation</strong>" rung of ch.24's defense-in-depth: control channel and data channel are <strong>physically split</strong> at the gateway — resolvable commands ride code recognition + bypass and never enter conversation history; only genuine conversation enters <span class="mono">_pending_messages</span> to feed the model. This "an instruction is never data" boundary both blocks injection (a forged instruction can't reach the control channel) and incidentally protects ch.6 caching and ch.7 role alternation: because history will <strong>never</strong> sprout a <span class="mono">/stop</span> mistaken for user text, the cached prefix and strict alternation stay stable.</p>
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

<p>为什么是 stdio 上的 JSON-RPC,而不是另起一个 HTTP/REST 服务?因为 Node 前端是<strong>父进程直接 spawn 出 Python 后端</strong>的,两者天生共享一对管道——无需监听端口、无需网络鉴权、无需穿越 TCP 协议栈。一帧请求就是<strong>一行 JSON</strong>,换行即分帧,解析成本几乎为零,延迟也最低。这条进程边界还划得格外干净:<strong>TypeScript 只负责屏幕</strong>(Ink 渲染 transcript、composer、审批弹窗、活动指示),<strong>Python 独占会话、工具、模型调用,乃至 slash 命令的解析与分派</strong>(<span class="mono">slash.exec</span> 跑在常驻的 <span class="mono">_SlashWorker</span> 子进程里)。前端永不碰业务逻辑,后端永不碰像素——职责一刀两断,各自才能用各自最顺手的生态独立迭代。</p>

<div class="figure">
<svg viewBox="0 0 680 336" role="img" aria-label="TUI 两进程模型：Node 管屏幕、Python 管核心，经 stdio JSON-RPC 双向通信">
  <text x="129" y="28" text-anchor="middle" font-size="13" font-weight="700" fill="var(--blue)">TypeScript · 管屏幕</text>
  <text x="551" y="28" text-anchor="middle" font-size="13" font-weight="700" fill="var(--purple)">Python · 管核心（同一 AIAgent）</text>

  <rect x="24" y="40" width="210" height="248" rx="11" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="129" y="64" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">Node (Ink / React)</text>
  <line x1="40" y1="74" x2="218" y2="74" stroke="var(--line)"/>
  <g font-size="11" text-anchor="middle">
    <rect x="44" y="86"  width="170" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="129" y="104" fill="var(--ink)">transcript · messageLine.tsx</text>
    <rect x="44" y="122" width="170" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="129" y="140" fill="var(--ink)">composer · 输入框</text>
    <rect x="44" y="158" width="170" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="129" y="176" fill="var(--ink)">审批 · prompts.tsx</text>
    <rect x="44" y="194" width="170" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="129" y="212" fill="var(--ink)">活动 · thinking.tsx</text>
  </g>
  <text x="129" y="252" text-anchor="middle" font-size="10.5" fill="var(--muted)">只渲染像素，不碰业务逻辑</text>

  <rect x="446" y="40" width="210" height="248" rx="11" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="1.5"/>
  <text x="551" y="64" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">Python (tui_gateway)</text>
  <line x1="462" y1="74" x2="640" y2="74" stroke="var(--line)"/>
  <g font-size="11" text-anchor="middle">
    <rect x="466" y="86"  width="170" height="28" rx="7" fill="var(--accent-soft)" stroke="var(--accent)"/>
    <text x="551" y="104" fill="var(--accent-ink)">AIAgent 核心循环（第7章）</text>
    <rect x="466" y="122" width="170" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="551" y="140" fill="var(--ink)">会话 · 工具 · 模型调用</text>
    <rect x="466" y="158" width="170" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="551" y="176" fill="var(--ink)">handle_request 分派</text>
    <rect x="466" y="194" width="170" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="551" y="212" fill="var(--ink)">slash.exec · _SlashWorker</text>
  </g>
  <text x="551" y="252" text-anchor="middle" font-size="10.5" fill="var(--muted)">独占会话/工具/模型/slash</text>

  <text x="340" y="58" text-anchor="middle" font-size="10.5" fill="var(--muted)">stdio 管道</text>
  <rect x="268" y="66" width="144" height="22" rx="11" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="340" y="81" text-anchor="middle" font-size="11" font-weight="700" fill="var(--accent-ink)">换行分隔 JSON-RPC</text>

  <text x="340" y="140" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">prompt.submit →</text>
  <text x="340" y="155" text-anchor="middle" font-size="9.5" fill="var(--faint)">方法调用 request</text>
  <line x1="238" y1="170" x2="438" y2="170" stroke="var(--blue)" stroke-width="2"/>
  <polygon points="444,170 434,165 434,175" fill="var(--blue)"/>

  <text x="340" y="206" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--purple)">← message.delta / complete</text>
  <text x="340" y="221" text-anchor="middle" font-size="9.5" fill="var(--faint)">事件 event 流（含 tool.* / approval.*）</text>
  <line x1="246" y1="236" x2="442" y2="236" stroke="var(--purple)" stroke-width="2"/>
  <polygon points="240,236 250,231 250,241" fill="var(--purple)"/>

  <text x="340" y="312" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--muted)">同一个 Python 后端＝同一个 AIAgent 核心，前端可换可崩，核心只维护一份</text>
</svg>
<div class="fig-cap"><b>TUI 两进程模型</b>:<b>hermes --tui</b> 实为两个进程——Node(Ink/React) 只渲染屏幕(transcript/composer/审批/活动),Python(tui_gateway) 独占会话/工具/模型/slash 并复用同一个 <b>AIAgent 核心</b>;两者经 stdio 上换行分隔的 JSON-RPC 通信:前端发 <b>prompt.submit</b> 等方法调用(→),后端回推 <b>message.delta/complete</b> 事件流(←)。<b>TS 管屏,Python 管核心</b>。</div>
</div>

<p>为什么坚持走标准的 JSON-RPC 错误信封(<span class="mono">-32601 unknown method</span>、<span class="mono">4009 session busy</span>)而不是回一段错误文本?因为前端要<strong>程序化地</strong>区分「方法不存在」「会话忙」「参数非法」,据此决定重试、提示还是禁用按钮;自由文本只能给人读,机器得做脆弱的字符串匹配,后端一改措辞前端就崩。把 <span class="mono">result</span> 与 <span class="mono">error</span> 钉成契约,等于给两个独立演进的技术栈立了一份不随版本漂移的接口。而装饰器 <span class="mono">@method("名字")</span> + 全局 <span class="mono">_methods</span> 表,让「新增一个能力」退化成「挂一个名字」——分派器一行不改,新方法自动可被调用。这正是窄腰对扩展的友好:边界稳定,两端各自生长。</p>

<p>这套「方法 + 事件」的二分,把每个交互面都摊成一张清晰的对应表:聊天流是 <span class="mono">prompt.submit</span> → <span class="mono">message.delta/complete</span>,对应 Ink 的 <span class="mono">app.tsx</span> + <span class="mono">messageLine.tsx</span>;工具活动是 <span class="mono">tool.start/progress/complete</span>,对应 <span class="mono">thinking.tsx</span>;审批是 <span class="mono">approval.request</span> ↔ <span class="mono">approval.respond</span>,对应 <span class="mono">prompts.tsx</span>;会话选择是 <span class="mono">session.list/resume</span> 对应 <span class="mono">sessionPicker.tsx</span>;补全走 <span class="mono">complete.slash/path</span>。每加一个交互面,只是再添一对「方法 ↔ 组件」,而不动既有任何一对——这种<strong>可叠加而不耦合</strong>的结构,正是窄腰接口能撑起越来越多前端功能的原因。</p>

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

<p>为什么一次回复要推<strong>两种</strong>事件——<span class="mono">message.delta</span> 与 <span class="mono">message.complete</span>?delta 是「正在生成」的逐块流,只带文本,负责让你看到字一个个蹦出来;complete 是「这一轮定型」的收尾帧,带上 <span class="mono">usage</span>(token 用量)、<span class="mono">status</span>(complete / interrupted / error)甚至 <span class="mono">reasoning</span>。前者追实时,后者追完整与准确,两者缺一不可:只有 delta 你拿不到用量和最终状态,只有 complete 你就失去了逐字流式的临场感。关键是,<span class="mono">_stream</span> 是作为 <span class="mono">stream_callback</span> 传进 <span class="mono">run_conversation</span> 的——TUI 的流式不是前端轮询出来的,而是<strong>核心循环每吐一块就主动回调一次</strong>,和第 7 章那个同步 agent 循环是同一处血脉。</p>

<p>流式收尾处还藏着一道防线:<span class="mono">prompt.submit</span> 写回结果前会校验 <span class="mono">history_version</span>,若这一轮跑的过程中会话历史被外部改过(压缩、撤销、重试、回滚),它<strong>拒绝覆盖</strong>,转而显式报「响应可见但未写入历史」,而不是默默丢弃或污染上下文。这背后是同一条铁律:<strong>对话历史不能在一轮中途被偷偷换掉</strong>。它既守住了提示缓存那条红线(第 6 章「除压缩外绝不改动过去上下文」),也保证了消息角色的严格交替不被打乱;当多个前端共享同一个后端会话时,这种并发保护尤其要紧——少了它,一次跨窗口的撤销就可能让本轮回复落到一段已经不存在的历史上。</p>

<p>同一条事件流不止推文本,也推<strong>工具活动</strong>(<span class="mono">tool.start/progress/complete</span>,在 Ink 里由 <span class="mono">thinking.tsx</span> 渲染成「正在做什么」)和<strong>审批请求</strong>(<span class="mono">approval.request</span>,弹给 <span class="mono">prompts.tsx</span>)。为什么把这些都走同一条回推通道?因为它们本质都是「agent 跑到一半,需要把状态或请求<strong>主动告诉前端</strong>」,共用一套机制就不必为每类信号各造一条管子。审批尤其关键:它必须能在 agent <strong>正阻塞等待</strong>时穿过去,这和第 18 章网关那条「审批/控制命令要绕过运行时守卫」的纪律同根同源——若审批也被「会话忙」挡下,agent 就会永远卡在等批准上。换句话说,流式回推不只是「让字蹦得好看」,它是<strong>会话运行期间前端与后端唯一的双向窗口</strong>:进度让你知道它没死,审批让你能在关键一步前喊停,二者都靠这条事件流活着。</p>

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

<div class="figure">
<svg viewBox="0 0 680 230" role="img" aria-label="仪表盘嵌入真实 TUI：浏览器 xterm.js 经 /api/pty 转发到真正的 hermes --tui 子进程">
  <text x="340" y="26" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">同一个 hermes --tui，经 PTY 投进浏览器（不在 React 里重写）</text>

  <g font-size="11" text-anchor="middle">
    <rect x="16"  y="44" width="138" height="80" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
    <text x="85"  y="72" font-size="12.5" font-weight="700" fill="var(--ink)">浏览器 xterm.js</text>
    <text x="85"  y="92" fill="var(--muted)">WebGL · Fit</text>
    <text x="85"  y="108" fill="var(--muted)">Unicode11</text>

    <rect x="186" y="44" width="138" height="80" rx="10" fill="var(--amber-soft)" stroke="var(--amber)" stroke-width="1.5"/>
    <text x="255" y="72" font-size="12.5" font-weight="700" fill="var(--ink)">/api/pty WS</text>
    <text x="255" y="92" fill="var(--muted)">?token= · 仅 loopback</text>
    <text x="255" y="108" fill="var(--muted)">尺寸转义本地拦截</text>

    <rect x="356" y="44" width="138" height="80" rx="10" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="1.5"/>
    <text x="425" y="72" font-size="12.5" font-weight="700" fill="var(--ink)">pty_bridge.py</text>
    <text x="425" y="92" fill="var(--muted)">PtyBridge.spawn</text>
    <text x="425" y="108" fill="var(--muted)">POSIX/ConPTY 同接口</text>

    <rect x="526" y="44" width="138" height="80" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>
    <text x="595" y="72" font-size="12.5" font-weight="700" fill="var(--accent-ink)">hermes --tui</text>
    <text x="595" y="92" fill="var(--accent-ink)">真实子进程</text>
    <text x="595" y="108" fill="var(--accent-ink)">和命令行一模一样</text>
  </g>

  <g stroke="var(--muted)" fill="var(--muted)">
    <line x1="160" y1="84" x2="180" y2="84" stroke-width="2"/>
    <polygon points="154,84 162,80 162,88"/>
    <polygon points="186,84 178,80 178,88"/>
    <line x1="330" y1="84" x2="350" y2="84" stroke-width="2"/>
    <polygon points="324,84 332,80 332,88"/>
    <polygon points="356,84 348,80 348,88"/>
    <line x1="500" y1="84" x2="520" y2="84" stroke-width="2"/>
    <polygon points="494,84 502,80 502,88"/>
    <polygon points="526,84 518,80 518,88"/>
  </g>

  <rect x="16" y="146" width="648" height="66" rx="10" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="340" y="172" text-anchor="middle" font-size="11.5" fill="var(--accent-ink)">↔ 原始 PTY 字节·两个方向逐字转发；仅 RESIZE 转义在服务端拦截，用 TIOCSWINSZ 调窗口</text>
  <text x="340" y="196" text-anchor="middle" font-size="12" font-weight="700" fill="var(--accent-ink)">★ 绝不在 React 重写 transcript/composer——给 Ink 加的新功能，dashboard 自动就有</text>
</svg>
<div class="fig-cap"><b>仪表盘嵌入真实 TUI,不是 React 重写</b>:浏览器里的 xterm.js 经 <b>/api/pty</b> WebSocket 连到 pty_bridge.py,后者 <b>spawn</b> 出与命令行一模一样的真实 <b>hermes --tui</b> 子进程(POSIX PTY);PTY 字节在两个方向原样转发,仅 RESIZE 这类尺寸转义在服务端拦截。于是聊天体验只在 Ink 实现一次——<b>给 Ink 加的新功能,dashboard 自动继承</b>。</div>
</div>

<p>为什么<strong>绝不</strong>用 React 把主聊天体验重写一遍?因为那等于让 transcript、composer、PTY 终端有<strong>两套实现</strong>,注定随时间漂移——给 Ink 修了个光标 bug、加了个审批弹窗,React 版却忘了跟,用户在命令行和浏览器里看到的就是两个 Hermes。嵌入同一个 <span class="mono">hermes --tui</span> 则只有<strong>一份真相</strong>:浏览器端 <span class="mono">ChatPage.tsx</span> 挂一个 xterm.js 终端,配上 <span class="mono">WebglAddon</span>(WebGL 渲染、吃大屏滚动)、<span class="mono">FitAddon</span>(随容器自适应列宽行高)、<span class="mono">Unicode11Addon</span>(现代宽字符宽度),只负责把后端原样吐来的 ANSI 字节<strong>画</strong>出来,而不重新发明任何聊天逻辑。AGENTS.md 因此立了硬规矩:发现自己在为仪表盘重建 transcript 或 composer,就停下来,去扩 Ink。</p>

<p>鉴权这一处的取舍也值得一看:<span class="mono">/api/pty</span> 的 WebSocket 用 <span class="mono">?token=&lt;session&gt;</span> 查询参数携带令牌,而不是放进 <span class="mono">Authorization</span> 头——因为浏览器在 WS 升级握手时<strong>根本无法设置自定义请求头</strong>,只能退而走 URL。令牌就是 REST 那套同一个临时 <span class="mono">_SESSION_TOKEN</span>,且整条通道<strong>只认本地回环</strong>,非 loopback 客户端一律拒绝,把「真 PTY 暴露给浏览器」的风险锁死在本机。服务端还用一把 <span class="mono">chat_argv_lock</span> 串行化 chat-argv 解析,让多个 <span class="mono">/api/pty</span> 连接并发时不会互相抢同一份启动参数。这些都是为了让「把命令行进程投进网页」这件事既能用、又不漏。</p>

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
  <p style="margin:.5rem 0 0">还有第三个前端值得单列:<strong>Electron 桌面 App</strong>(<span class="mono">apps/desktop/</span>)。它和仪表盘走的是<strong>相反</strong>的路——<strong>不嵌</strong> <span class="mono">hermes --tui</span>,而是用 <span class="mono">@assistant-ui/react</span> + nanostore 自建 composer、transcript 与 slash 管线,经同一套 JSON-RPC(<span class="mono">requestGateway</span>)连同一个 tui_gateway 后端。为什么这次允许「另起一套界面」?因为它不是终端、装不进 PTY,要的是富交互的原生桌面体验,这是一个<strong>独立的 chat surface</strong>,而非对终端体验的重复。但它的 slash 命令<strong>策展而不封杀</strong>:面板默认只摆约 19 个内置命令以免噪音,可技能、用户 quick_commands 这类<strong>扩展</strong>必须照常浮现——因为后端早已把它们一并暴露,藏的是噪音,不是用户激活的能力。</p>
  <p style="margin:.5rem 0 0">把镜头拉到全书:本章其实是「<strong>窄腰</strong>」最直观的一次落地。同一个 AIAgent 核心(第 7 章)被<strong>四类外壳</strong>共用——经典 CLI、Ink TUI、桌面 App,以及第 17 章的消息网关——它们要么是 JSON-RPC 前端,要么是网关适配器,核心只维护一份。<span class="mono">prompt.submit</span> 那句 <span class="mono">session busy</span> 忙检查,和第 18 章网关「agent 运行时拒新输入」的守卫是<strong>同一个意思</strong>:一个会话同一时刻只跑一轮。而仪表盘嵌入复用、桌面共享后端、TUI 流式回推,合起来印证了那条贯穿全书的取舍——<strong>把易变的前端推到边缘,把稳定的能力收进窄腰</strong>:前端可以百花齐放、各用各的栈崩了也不连累核心,而 agent 的会话、工具、缓存纪律只在一处被定义、被守护。</p>
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

<p>Why JSON-RPC over stdio rather than standing up an HTTP/REST service? Because the Node frontend <strong>spawns the Python backend as a child process</strong>, so the two already share a pipe pair — no port to bind, no network auth, no TCP stack to cross. One request is <strong>one line of JSON</strong>, newline-framed, with near-zero parse cost and minimal latency. The process boundary is also drawn cleanly: <strong>TypeScript only owns the screen</strong> (Ink renders the transcript, composer, approval prompts, activity), while <strong>Python owns sessions, tools, model calls, and even slash-command parsing/dispatch</strong> (<span class="mono">slash.exec</span> runs in a persistent <span class="mono">_SlashWorker</span> subprocess). The frontend never touches business logic, the backend never touches pixels — a clean split lets each evolve in its own ecosystem.</p>

<div class="figure">
<svg viewBox="0 0 680 336" role="img" aria-label="TUI two-process model: Node owns the screen, Python owns the core, talking over stdio JSON-RPC">
  <text x="129" y="28" text-anchor="middle" font-size="13" font-weight="700" fill="var(--blue)">TypeScript · owns the screen</text>
  <text x="551" y="28" text-anchor="middle" font-size="13" font-weight="700" fill="var(--purple)">Python · owns the core</text>

  <rect x="24" y="40" width="210" height="248" rx="11" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="129" y="64" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">Node (Ink / React)</text>
  <line x1="40" y1="74" x2="218" y2="74" stroke="var(--line)"/>
  <g font-size="11" text-anchor="middle">
    <rect x="44" y="86"  width="170" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="129" y="104" fill="var(--ink)">transcript · messageLine.tsx</text>
    <rect x="44" y="122" width="170" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="129" y="140" fill="var(--ink)">composer · input</text>
    <rect x="44" y="158" width="170" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="129" y="176" fill="var(--ink)">approvals · prompts.tsx</text>
    <rect x="44" y="194" width="170" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="129" y="212" fill="var(--ink)">activity · thinking.tsx</text>
  </g>
  <text x="129" y="252" text-anchor="middle" font-size="10.5" fill="var(--muted)">paints pixels, no business logic</text>

  <rect x="446" y="40" width="210" height="248" rx="11" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="1.5"/>
  <text x="551" y="64" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">Python (tui_gateway)</text>
  <line x1="462" y1="74" x2="640" y2="74" stroke="var(--line)"/>
  <g font-size="11" text-anchor="middle">
    <rect x="466" y="86"  width="170" height="28" rx="7" fill="var(--accent-soft)" stroke="var(--accent)"/>
    <text x="551" y="104" fill="var(--accent-ink)">AIAgent core loop (ch.7)</text>
    <rect x="466" y="122" width="170" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="551" y="140" fill="var(--ink)">sessions · tools · model</text>
    <rect x="466" y="158" width="170" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="551" y="176" fill="var(--ink)">handle_request dispatch</text>
    <rect x="466" y="194" width="170" height="28" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="551" y="212" fill="var(--ink)">slash.exec · _SlashWorker</text>
  </g>
  <text x="551" y="252" text-anchor="middle" font-size="10.5" fill="var(--muted)">owns sessions/tools/model/slash</text>

  <text x="340" y="58" text-anchor="middle" font-size="10.5" fill="var(--muted)">stdio pipe</text>
  <rect x="262" y="66" width="156" height="22" rx="11" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="340" y="81" text-anchor="middle" font-size="11" font-weight="700" fill="var(--accent-ink)">newline-delimited JSON-RPC</text>

  <text x="340" y="140" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">prompt.submit →</text>
  <text x="340" y="155" text-anchor="middle" font-size="9.5" fill="var(--faint)">method call (request)</text>
  <line x1="238" y1="170" x2="438" y2="170" stroke="var(--blue)" stroke-width="2"/>
  <polygon points="444,170 434,165 434,175" fill="var(--blue)"/>

  <text x="340" y="206" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--purple)">← message.delta / complete</text>
  <text x="340" y="221" text-anchor="middle" font-size="9.5" fill="var(--faint)">event stream (tool.* / approval.*)</text>
  <line x1="246" y1="236" x2="442" y2="236" stroke="var(--purple)" stroke-width="2"/>
  <polygon points="240,236 250,231 250,241" fill="var(--purple)"/>

  <text x="340" y="312" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--muted)">One Python backend = one AIAgent core; swap or crash a frontend, the core is maintained once</text>
</svg>
<div class="fig-cap"><b>TUI two-process model</b>: <b>hermes --tui</b> is really two processes — Node(Ink/React) only paints the screen (transcript/composer/approvals/activity), while Python(tui_gateway) owns sessions/tools/model/slash and reuses the one <b>AIAgent core</b>; they talk over newline-delimited JSON-RPC on stdio: the frontend sends method calls like <b>prompt.submit</b> (→), the backend pushes the <b>message.delta/complete</b> event stream (←). <b>TS owns the screen, Python owns the core.</b></div>
</div>

<p>Why insist on the standard JSON-RPC error envelope (<span class="mono">-32601 unknown method</span>, <span class="mono">4009 session busy</span>) instead of returning error text? Because the frontend must <strong>programmatically</strong> tell "no such method" from "session busy" from "bad params" to decide whether to retry, prompt, or disable a button; free text is for humans, machines resort to brittle string matching that breaks the moment the backend rewords. Pinning <span class="mono">result</span> and <span class="mono">error</span> into a contract gives two independently evolving stacks an interface that won't drift across versions. And the <span class="mono">@method("name")</span> decorator + global <span class="mono">_methods</span> table reduce "add a capability" to "hang a name" — the dispatcher never changes. That's the narrow waist being friendly to extension.</p>

<p>This "methods + events" split lays every interaction surface out as a clean mapping table: chat streaming is <span class="mono">prompt.submit</span> → <span class="mono">message.delta/complete</span>, mapped to Ink's <span class="mono">app.tsx</span> + <span class="mono">messageLine.tsx</span>; tool activity is <span class="mono">tool.start/progress/complete</span> → <span class="mono">thinking.tsx</span>; approvals are <span class="mono">approval.request</span> ↔ <span class="mono">approval.respond</span> → <span class="mono">prompts.tsx</span>; session picking is <span class="mono">session.list/resume</span> → <span class="mono">sessionPicker.tsx</span>; completions ride <span class="mono">complete.slash/path</span>. Each new surface is just one more "method ↔ component" pair, touching none of the existing ones — that <strong>additive, non-coupled</strong> structure is exactly why a narrow-waist interface can carry ever more frontend features.</p>

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

<p>Why push <strong>two</strong> kinds of event per reply — <span class="mono">message.delta</span> and <span class="mono">message.complete</span>? delta is the "being generated" chunk stream, text only, making characters pop out one by one; complete is the "turn settled" closing frame carrying <span class="mono">usage</span> (token counts), <span class="mono">status</span> (complete / interrupted / error), even <span class="mono">reasoning</span>. The first chases liveness, the second completeness and accuracy — you need both: delta alone gives no usage or final status, complete alone loses the streamed immediacy. Crucially, <span class="mono">_stream</span> is passed into <span class="mono">run_conversation</span> as the <span class="mono">stream_callback</span> — the TUI's streaming isn't frontend polling, it's the <strong>core loop actively calling back on every chunk it emits</strong>, the same bloodline as the synchronous agent loop in ch.7.</p>

<p>The closing edge hides a guard too: before writing results back, <span class="mono">prompt.submit</span> checks <span class="mono">history_version</span>; if the session history was changed externally mid-turn (compress, undo, retry, rollback), it <strong>refuses to overwrite</strong> and explicitly reports "response visible but not written to history" instead of silently dropping or corrupting context. Behind this is the same iron rule: <strong>conversation history must not be swapped out mid-turn</strong>. It guards the prompt-cache red line (ch.6, "never alter past context except for compression") and keeps strict message-role alternation intact; when several frontends share one backend session, that concurrency protection matters even more — without it, one cross-window undo could land this turn's reply on a history that no longer exists.</p>

<p>The same event stream carries more than text: it also pushes <strong>tool activity</strong> (<span class="mono">tool.start/progress/complete</span>, rendered as "what's happening" by <span class="mono">thinking.tsx</span> in Ink) and <strong>approval requests</strong> (<span class="mono">approval.request</span>, popped to <span class="mono">prompts.tsx</span>). Why route all of these through the same push channel? Because they're all "the agent is mid-run and needs to <strong>proactively tell the frontend</strong> a state or a request" — sharing one mechanism beats building a separate pipe per signal type. Approvals matter most: they must get through while the agent is <strong>blocked waiting</strong>, the same root as ch.18's gateway discipline that "approval/control commands must bypass the running guard" — if an approval were also turned away by "session busy," the agent would hang forever waiting for it. Put differently, streaming push isn't just "make the characters look nice" — it's the <strong>only two-way window between frontend and backend while a turn runs</strong>: progress tells you it isn't dead, approvals let you halt before a critical step, and both stay alive on this one event stream.</p>

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

<div class="figure">
<svg viewBox="0 0 680 230" role="img" aria-label="The dashboard embeds the real TUI: browser xterm.js forwarded over /api/pty to the real hermes --tui child">
  <text x="340" y="26" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">The same hermes --tui, piped into the browser via PTY (no React rewrite)</text>

  <g font-size="11" text-anchor="middle">
    <rect x="16"  y="44" width="138" height="80" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
    <text x="85"  y="72" font-size="12.5" font-weight="700" fill="var(--ink)">Browser xterm.js</text>
    <text x="85"  y="92" fill="var(--muted)">WebGL · Fit</text>
    <text x="85"  y="108" fill="var(--muted)">Unicode11</text>

    <rect x="186" y="44" width="138" height="80" rx="10" fill="var(--amber-soft)" stroke="var(--amber)" stroke-width="1.5"/>
    <text x="255" y="72" font-size="12.5" font-weight="700" fill="var(--ink)">/api/pty WS</text>
    <text x="255" y="92" fill="var(--muted)">?token= · loopback</text>
    <text x="255" y="108" fill="var(--muted)">resize intercepted</text>

    <rect x="356" y="44" width="138" height="80" rx="10" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="1.5"/>
    <text x="425" y="72" font-size="12.5" font-weight="700" fill="var(--ink)">pty_bridge.py</text>
    <text x="425" y="92" fill="var(--muted)">PtyBridge.spawn</text>
    <text x="425" y="108" fill="var(--muted)">POSIX/ConPTY · 1 API</text>

    <rect x="526" y="44" width="138" height="80" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>
    <text x="595" y="72" font-size="12.5" font-weight="700" fill="var(--accent-ink)">hermes --tui</text>
    <text x="595" y="92" fill="var(--accent-ink)">real subprocess</text>
    <text x="595" y="108" fill="var(--accent-ink)">same as the CLI</text>
  </g>

  <g stroke="var(--muted)" fill="var(--muted)">
    <line x1="160" y1="84" x2="180" y2="84" stroke-width="2"/>
    <polygon points="154,84 162,80 162,88"/>
    <polygon points="186,84 178,80 178,88"/>
    <line x1="330" y1="84" x2="350" y2="84" stroke-width="2"/>
    <polygon points="324,84 332,80 332,88"/>
    <polygon points="356,84 348,80 348,88"/>
    <line x1="500" y1="84" x2="520" y2="84" stroke-width="2"/>
    <polygon points="494,84 502,80 502,88"/>
    <polygon points="526,84 518,80 518,88"/>
  </g>

  <rect x="16" y="146" width="648" height="66" rx="10" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="340" y="172" text-anchor="middle" font-size="11.5" fill="var(--accent-ink)">↔ raw PTY bytes forwarded verbatim both ways; only RESIZE escapes intercepted server-side via TIOCSWINSZ</text>
  <text x="340" y="196" text-anchor="middle" font-size="12" font-weight="700" fill="var(--accent-ink)">★ Never rewrite transcript/composer in React — add a feature to Ink, the dashboard just has it</text>
</svg>
<div class="fig-cap"><b>The dashboard embeds the real TUI, it's not a React rewrite</b>: the browser's xterm.js connects over the <b>/api/pty</b> WebSocket to pty_bridge.py, which <b>spawn</b>s the exact same real <b>hermes --tui</b> child (POSIX PTY); PTY bytes are forwarded verbatim both ways, only RESIZE-style sizing escapes are intercepted server-side. So the chat experience is built once in Ink — <b>add a feature to Ink and the dashboard inherits it</b>.</div>
</div>

<p>Why <strong>never</strong> rewrite the primary chat experience in React? Because that means <strong>two implementations</strong> of the transcript, composer, and PTY terminal, doomed to drift — fix a cursor bug or add an approval prompt in Ink and the React copy forgets to follow, so the CLI and the browser show two different Hermeses. Embedding the same <span class="mono">hermes --tui</span> keeps <strong>one source of truth</strong>: the browser's <span class="mono">ChatPage.tsx</span> mounts an xterm.js terminal with <span class="mono">WebglAddon</span> (WebGL rendering, smooth on big scrollback), <span class="mono">FitAddon</span> (column/row autosize to the container), and <span class="mono">Unicode11Addon</span> (modern wide-char widths), whose only job is to <strong>paint</strong> the ANSI bytes the backend forwards verbatim — reinventing no chat logic. AGENTS.md makes it a hard rule: catch yourself rebuilding the transcript or composer for the dashboard, stop and extend Ink.</p>

<p>The auth choice here is instructive too: <span class="mono">/api/pty</span>'s WebSocket carries the token as a <span class="mono">?token=&lt;session&gt;</span> query param rather than an <span class="mono">Authorization</span> header — because browsers <strong>can't set custom headers</strong> on a WS upgrade handshake, leaving the URL as the only channel. The token is the very same ephemeral <span class="mono">_SESSION_TOKEN</span> as REST, and the whole channel is <strong>loopback-only</strong>, rejecting non-loopback clients to lock the "real PTY exposed to a browser" risk down to the local machine. The server also serializes chat-argv resolution with a <span class="mono">chat_argv_lock</span> so concurrent <span class="mono">/api/pty</span> connections don't race over the same launch args. All of it makes "project a CLI process into a web page" both usable and tight.</p>

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
  <p style="margin:.5rem 0 0">A third frontend deserves its own line: the <strong>Electron desktop app</strong> (<span class="mono">apps/desktop/</span>). It goes the <strong>opposite</strong> way from the dashboard — it does <strong>not</strong> embed <span class="mono">hermes --tui</span>, instead building its own composer, transcript, and slash pipeline with <span class="mono">@assistant-ui/react</span> + nanostore, talking to the same tui_gateway backend over the same JSON-RPC (<span class="mono">requestGateway</span>). Why allow a separate UI this time? Because it isn't a terminal and can't be stuffed into a PTY; it wants a rich native desktop experience — a genuinely <strong>separate chat surface</strong>, not a duplicate of the terminal one. Yet its slash commands are <strong>curated, not censored</strong>: the palette shows ~19 built-ins to avoid noise, but skills and user <span class="mono">quick_commands</span> — extensions the backend already surfaces — must still appear; what's hidden is noise, not user-activated capability.</p>
  <p style="margin:.5rem 0 0">Zoom out to the whole book: this chapter is the most concrete landing of the <strong>narrow waist</strong>. One AIAgent core (ch.7) is shared by <strong>four shells</strong> — the classic CLI, the Ink TUI, the desktop app, and the messaging gateway (ch.17) — each either a JSON-RPC frontend or a gateway adapter, with the core maintained once. <span class="mono">prompt.submit</span>'s <span class="mono">session busy</span> check is <strong>the same idea</strong> as ch.18's gateway guard "reject new input while the agent runs": one session runs one turn at a time. Dashboard embedding, desktop backend-sharing, and TUI streaming together prove the trade-off that runs through the book — <strong>push volatile frontends to the edges, pull stable capability into the waist</strong>: frontends can bloom and crash without dragging down the core, while sessions, tools, and cache discipline are defined and defended in exactly one place.</p>
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


LESSON_20 = {
    "zh": r"""
<p class="lead">同一台机器上,你想跑两个完全独立的 Hermes:一个「工作号」、一个「私人号」,各有各的 API key、记忆、会话、技能、网关——互不串台。这就是 <strong>profile</strong>。它的全部魔法,浓缩成一句话:<strong>在任何模块 import 之前,抢先设好一个环境变量 <span class="mono">HERMES_HOME</span></strong>。</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 连锁酒店的分店</div>
  同一套管理系统(Hermes 代码),开了多家分店(profile)。每家分店有<strong>独立的钥匙、账本、客房</strong>(各自的 <span class="mono">HERMES_HOME</span> 目录)。你一进门,前台先确认「您是哪家分店的」(<span class="mono">_apply_profile_override</span> 抢先设 <span class="mono">HERMES_HOME</span>),之后你办的<strong>每一件事</strong>都自动用那家店的资源——不会刷错账本、拿错钥匙。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 一个环境变量决定一切</div>
  profile 切换只做<strong>一件事</strong>:在 <span class="mono">main.py</span> 的<strong>模块顶层</strong>、其余 import 之前,把 <span class="mono">HERMES_HOME</span> 设成 <span class="mono">~/.hermes/profiles/&lt;名字&gt;</span>。之后全代码库唯一的路径入口 <span class="mono">get_hermes_home()</span> 自动指向那个目录,配置/密钥/记忆/会话/技能<strong>全部隔离</strong>。配置本身再分两层:行为设置进 <span class="mono">config.yaml</span>、密钥进 <span class="mono">.env</span>。
</div>

<h2>抢跑:import 之前设 HERMES_HOME</h2>
<p>关键在「时机」——必须赶在任何模块把路径缓存下来<strong>之前</strong>:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">hermes_cli/main.py</span><span class="ln">336-508 · 简化</span></div>
  <pre><span class="kw">def</span> <span class="fn">_apply_profile_override</span>() -&gt; <span class="kw">None</span>:
    <span class="cm">&quot;&quot;&quot;Pre-parse --profile/-p and set HERMES_HOME before imports.&quot;&quot;&quot;</span>
    profile_name = ...                       <span class="cm"># 从 argv 解析 -p / --profile</span>
    <span class="kw">if</span> profile_name <span class="kw">is</span> <span class="kw">not</span> <span class="kw">None</span>:
        hermes_home = resolve_profile_env(profile_name)   <span class="cm"># → ~/.hermes/profiles/coder</span>
        os.environ[<span class="st">"HERMES_HOME"</span>] = hermes_home          <span class="cm"># 抢先设环境变量</span>
        <span class="cm"># 再把 -p 标志从 argv 剥掉,免得后面 argparse 报错</span>

_apply_profile_override()   <span class="cm"># 模块级:在其余 import 之前就执行</span></pre>
</div>
<p>注意最后那行 <span class="mono">_apply_profile_override()</span> 是<strong>模块级调用</strong>——在 <span class="mono">main.py</span> 顶层执行,<strong>早于</strong> <span class="mono">config</span>、<span class="mono">env_loader</span> 等会读取/缓存 <span class="mono">HERMES_HOME</span> 的落盘业务模块被 <span class="mono">import</span>。等到那些模块加载时去读 <span class="mono">HERMES_HOME</span>,看到的已经是 profile 的目录了。一个环境变量,把整棵依赖树重定向到了正确的实例。</p>
<p>为什么非得在<strong>模块顶层、import 之前</strong>调用,而不是塞进某个 <span class="mono">main()</span> 函数里?因为 Python 的 import 只执行一次,很多落盘模块在被 import 的<strong>那一刻</strong>就用 <span class="mono">get_hermes_home()</span> 算出路径、缓存进模块级常量(这正是第 8 章自动发现「import 即注册」的同一性质)。只要 <span class="mono">config</span>、<span class="mono">env_loader</span> 里任意一个抢先 import 成功,它读到的就是默认 <span class="mono">~/.hermes</span>,profile 再设也晚了——缓存已被定死,无从更正。把 <span class="mono">_apply_profile_override()</span> 写成裸调用、且放在文件最顶端,等于用「import 顺序」这把唯一可靠的锁,保证环境变量永远先于第一个落盘模块就位。这也解释了它为何要自己手撸 argv 解析、而不用 <span class="mono">argparse</span>:后者得先 import 一堆模块,太晚了。</p>
<p>这套抢跑机制还有两个常被忽视的收尾。其一,设好 <span class="mono">HERMES_HOME</span> 之后,<span class="mono">_apply_profile_override()</span> 会把 <span class="mono">-p/--profile</span> 标志从 <span class="mono">argv</span> 里剥掉,免得后面正式的 <span class="mono">argparse</span> 因不认识这个参数而报错——也就是说 profile 解析故意走在标准参数解析<strong>之前</strong>、独立成一套轻量逻辑。其二,源码里回退的「平台默认」并非写死的 <span class="mono">~/.hermes</span>:在 Windows 上 <span class="mono">_get_platform_default_hermes_home()</span> 会改用 <span class="mono">LOCALAPPDATA</span> 下的目录。所以这个「单一入口」不仅服务于 profile 隔离,也顺手把跨平台的路径差异一并收进了同一个函数,让所有调用方对此一律无感——这正是单一真相源在「可维护性」上的额外红利。</p>

<h2>单一真相源:所有路径都问它</h2>
<p>全代码库不准硬编码 <span class="mono">~/.hermes</span>,一律走这一个函数:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">hermes_constants.py</span><span class="ln">54-109 · 节选</span></div>
  <pre><span class="kw">def</span> <span class="fn">get_hermes_home</span>() -&gt; Path:
    <span class="cm">&quot;&quot;&quot;Reads HERMES_HOME env var, falls back to the platform-native default.</span>
<span class="cm">    This is the single source of truth — all other copies should import this.&quot;&quot;&quot;</span>
    override = get_hermes_home_override()    <span class="cm"># ContextVar 级覆盖(并发隔离)</span>
    <span class="kw">if</span> override:
        <span class="kw">return</span> Path(override)
    val = os.environ.get(<span class="st">"HERMES_HOME"</span>, <span class="st">""</span>).strip()
    <span class="kw">if</span> val:
        <span class="kw">return</span> Path(val)                     <span class="cm"># ← profile 设的就是这个</span>
    <span class="kw">return</span> _get_platform_default_hermes_home()   <span class="cm"># 默认 ~/.hermes</span></pre>
</div>
<p><strong>「single source of truth — all other copies should import this」</strong>:全代码库 30+ 处要落盘的地方,都不自己拼 <span class="mono">~/.hermes</span>,而是调 <span class="mono">get_hermes_home()</span>。于是 profile 一旦在开头设好 <span class="mono">HERMES_HOME</span>,会话库、记忆、技能、网关日志……<strong>统统自动</strong>落到 profile 目录。反过来,任何一处硬编码 <span class="mono">Path.home()/".hermes"</span> 都会<strong>击穿隔离</strong>(PR #3575 一次就修了 5 个这种 bug)。</p>
<p>为什么是一个<strong>函数</strong>而不是一个模块级常量?因为常量在 import 时就被求值、之后再也无法改变;而 profile、子代理、并发线程都可能要在运行期临时切换 home。<span class="mono">get_hermes_home()</span> 每次调用先看 <span class="mono">ContextVar</span> 覆盖——让同一进程内并发的子代理各认各的实例,呼应第 16 章委派的隔离——再看 <span class="mono">HERMES_HOME</span> 环境变量,最后才回退平台默认。源码还特意保留一段逻辑:当环境变量缺失、但 <span class="mono">active_profile</span> 文件指向一个非默认 profile 时,往 <span class="mono">errors.log</span> 打一条响亮的一次性告警。为什么是告警而不是抛异常?因为这函数有 30+ 个模块级调用方在 import 期就会执行它,一旦抛异常会把它们全部弄崩,所以宁可告警、留下可诊断的线索,也绝不阻断启动。</p>
<p>这个回退设计透露的工程哲学值得品味:<span class="mono">get_hermes_home()</span> 宁可在 <span class="mono">HERMES_HOME</span> 缺失时<strong>安静回退默认 + 留一条告警</strong>,也不肯把自己变成一个会抛异常的「严格守门人」。原因前面说过——它是被 30+ 个模块在 import 期同步调用的底座,任何会失败的底座都会让整个进程的启动变脆。把不确定性挡在 import 之外、用环境变量在最前面一次性定死,再让所有调用方无脑信任这唯一入口,正是「无状态内核 + 外部一个变量定乾坤」在路径层面的具体落地。也正因如此,子进程派生(<span class="mono">systemd</span> 模板、kanban 调度器)必须显式把 <span class="mono">HERMES_HOME</span> 透传下去,否则子进程读不到环境变量,会悄悄退回默认实例、写错 profile——这是分布式跑多实例时最隐蔽的一类污染源。</p>

<div class="figure">
<svg viewBox="0 0 680 392" role="img" aria-label="Profiles 是独立的岛:每个 profile 有独立 HERMES_HOME,彼此完全隔离、不做实时继承">
  <rect x="20" y="20" width="300" height="46" rx="9" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="170" y="40" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--accent-ink)">_apply_profile_override()</text>
  <text x="170" y="57" text-anchor="middle" font-size="10.5" fill="var(--accent-ink)">任何 import 之前 · 抢设 HERMES_HOME</text>
  <line x1="320" y1="43" x2="356" y2="43" stroke="var(--muted)" stroke-width="2"/>
  <polygon points="356,38 366,43 356,48" fill="var(--muted)"/>
  <rect x="368" y="20" width="292" height="46" rx="9" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="2"/>
  <text x="514" y="40" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--blue)">get_hermes_home()</text>
  <text x="514" y="57" text-anchor="middle" font-size="10.5" fill="var(--blue)">单一入口 · 所有路径都问它</text>

  <text x="340" y="86" text-anchor="middle" font-size="11" fill="var(--muted)">每个进程的 HERMES_HOME 只指向其中<tspan font-weight="700" fill="var(--ink)">一座岛</tspan>;岛之间完全隔离</text>

  <path d="M118 132 Q229 96 340 132" fill="none" stroke="var(--purple)" stroke-width="1.6" stroke-dasharray="5 4"/>
  <polygon points="335,123 343,134 329,132" fill="var(--purple)"/>
  <text x="229" y="108" text-anchor="middle" font-size="10" fill="var(--purple)">--clone:创建时一次性拷贝(之后各走各路)</text>

  <rect x="20" y="134" width="196" height="216" rx="12" fill="var(--panel-2)" stroke="var(--line)" stroke-width="1.5"/>
  <text x="118" y="158" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--ink)">default</text>
  <text x="118" y="173" text-anchor="middle" font-size="9" fill="var(--muted)" font-family="monospace">~/.hermes</text>
  <line x1="34" y1="182" x2="202" y2="182" stroke="var(--line)"/>
  <g font-size="10.5" fill="var(--ink)">
    <text x="34" y="203">· config.yaml</text>
    <text x="34" y="222">· .env(密钥)</text>
    <text x="34" y="241">· 记忆 memory</text>
    <text x="34" y="260">· 会话 sessions</text>
    <text x="34" y="279">· 技能 skills</text>
    <text x="34" y="298">· 网关 gateway</text>
  </g>

  <rect x="242" y="134" width="196" height="216" rx="12" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="340" y="158" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--blue)">coder</text>
  <text x="340" y="173" text-anchor="middle" font-size="9" fill="var(--muted)" font-family="monospace">~/.hermes/profiles/coder</text>
  <line x1="256" y1="182" x2="424" y2="182" stroke="var(--blue)" stroke-opacity="0.4"/>
  <g font-size="10.5" fill="var(--ink)">
    <text x="256" y="203">· config.yaml</text>
    <text x="256" y="222">· .env(密钥)</text>
    <text x="256" y="241">· 记忆 memory</text>
    <text x="256" y="260">· 会话 sessions</text>
    <text x="256" y="279">· 技能 skills</text>
    <text x="256" y="298">· 网关 gateway</text>
  </g>

  <rect x="464" y="134" width="196" height="216" rx="12" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="1.5"/>
  <text x="562" y="158" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--purple)">personal</text>
  <text x="562" y="173" text-anchor="middle" font-size="9" fill="var(--muted)" font-family="monospace">~/.hermes/profiles/personal</text>
  <line x1="478" y1="182" x2="646" y2="182" stroke="var(--purple)" stroke-opacity="0.4"/>
  <g font-size="10.5" fill="var(--ink)">
    <text x="478" y="203">· config.yaml</text>
    <text x="478" y="222">· .env(密钥)</text>
    <text x="478" y="241">· 记忆 memory</text>
    <text x="478" y="260">· 会话 sessions</text>
    <text x="478" y="279">· 技能 skills</text>
    <text x="478" y="298">· 网关 gateway</text>
  </g>

  <line x1="229" y1="190" x2="229" y2="344" stroke="var(--red)" stroke-width="1.4" stroke-dasharray="4 4"/>
  <text x="229" y="261" text-anchor="middle" font-size="13" font-weight="700" fill="var(--red)">✕</text>
  <line x1="451" y1="190" x2="451" y2="344" stroke="var(--red)" stroke-width="1.4" stroke-dasharray="4 4"/>
  <text x="451" y="261" text-anchor="middle" font-size="13" font-weight="700" fill="var(--red)">✕</text>

  <text x="340" y="378" text-anchor="middle" font-size="10.5" fill="var(--muted)"><tspan fill="var(--red)" font-weight="700">✕</tspan> 不做实时继承　·　硬编码 ~/.hermes 会击穿隔离(PR #3575)</text>
</svg>
<div class="fig-cap"><b>Profiles:独立的岛</b>:<span class="mono">_apply_profile_override()</span> 在任何 import 前抢设 <span class="mono">HERMES_HOME</span>,全代码库再走 <span class="mono">get_hermes_home()</span> 单一入口——于是每个 profile 的 config/密钥/记忆/会话/技能/网关<b>各落各的目录、完全隔离</b>。岛与岛之间<b>刻意不做实时继承</b>(避免改一处污染全体);要「从默认起步」就用创建时一次性拷贝的 <span class="mono">--clone</span>。</div>
</div>

<h2>配置分层:行为进 yaml,密钥进 env</h2>
<p>profile 隔离的是「存哪」;而「存什么」分两层,泾渭分明:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">hermes_cli/config.py</span><span class="ln">883 / 2860 / 2885 · 简化</span></div>
  <pre><span class="cm"># config.yaml —— 所有行为设置(超时/阈值/开关/显示偏好)</span>
DEFAULT_CONFIG = {
    <span class="st">"_config_version"</span>: 30,
    <span class="st">"model"</span>: {...}, <span class="st">"agent"</span>: {...}, <span class="st">"terminal"</span>: {...},
    <span class="st">"compression"</span>: {...}, <span class="st">"memory"</span>: {...}, <span class="st">"gateway"</span>: {...},
}

<span class="cm"># .env —— 凭据/密钥(密钥标 password:True,setup 时掩码输入)</span>
OPTIONAL_ENV_VARS = {
    <span class="st">"OPENROUTER_API_KEY"</span>: {<span class="st">"password"</span>: <span class="kw">True</span>, <span class="st">"category"</span>: <span class="st">"provider"</span>},
    <span class="st">"TELEGRAM_BOT_TOKEN"</span>: {<span class="st">"password"</span>: <span class="kw">True</span>, <span class="st">"category"</span>: <span class="st">"messaging"</span>},
}</pre>
</div>
<p>设计意图很明确:<strong><span class="mono">.env</span> 主要放凭据</strong>(密钥条目标 <span class="mono">password: True</span>、setup 向导掩码输入;<span class="mono">OPTIONAL_ENV_VARS</span> 里也有少量 <span class="mono">password: False</span> 的非密连接项,如 base URL、代理);而超时、阈值、功能开关、显示偏好这些<strong>行为设置一律进 <span class="mono">config.yaml</span></strong>。所以「给 messaging 设个工作目录」绝不能塞进 <span class="mono">.env</span>(已废弃的 <span class="mono">MESSAGING_CWD</span> 就是反例),而要写 <span class="mono">terminal.cwd</span>。这条线让凭据独立成一个可单独保护、单独 gitignore 的文件。</p>
<p>为什么一定要把密钥和行为设置劈成两个文件?因为它们的生命周期与信任级别天差地别:密钥绝不能进版本控制,<span class="mono">.env</span> 因此能被单独 <span class="mono">gitignore</span>、单独收紧权限;而 <span class="mono">config.yaml</span> 是可读、可 diff、可随项目迁移的行为快照,团队成员照着改也不怕泄密。这里还藏着一个工程红利:<span class="mono">DEFAULT_CONFIG</span> 与用户 yaml 走 <span class="mono">_deep_merge</span> 合并,<strong>新增一个键会被自动补全</strong>,所以只有改键名、改结构这种破坏性迁移才需要 bump <span class="mono">_config_version</span>。代价是配置读取分了三条路径——CLI 的 <span class="mono">load_cli_config</span>、子命令的 <span class="mono">load_config</span>、网关直读 yaml——加键时三条都得覆盖到,否则会出现「CLI 看得见、网关看不见」的诡异不一致。</p>
<p>这里必须对「<span class="mono">.env</span> 里全是密钥」保持诚实:那是<strong>设计政策与理想</strong>,现实并不绝对。翻一翻 <span class="mono">OPTIONAL_ENV_VARS</span>,会看到不少标着 <span class="mono">password: False</span> 的非密项,例如 <span class="mono">NOUS_BASE_URL</span>、<span class="mono">GEMINI_BASE_URL</span>、<span class="mono">XAI_BASE_URL</span> 这类 base URL 覆盖——它们出于历史与兼容,至今仍寄居在 <span class="mono">.env</span> 里。所以准确的说法是:<strong>政策上 <span class="mono">.env</span> 应只放凭据,但历史包袱让它仍混着少量非密的连接项</strong>。判断一个新设置该放哪,标准很简单——看它是不是秘密:是 API key、token 就进 <span class="mono">.env</span>;是超时、阈值、开关、显示偏好就进 <span class="mono">config.yaml</span>,别被现存的反例带偏。</p>
<p>把 <span class="mono">config.yaml</span> 单独拎出来还有个全局意义:它几乎是全书各章行为的<strong>总开关面板</strong>。一个 yaml 文件里,<span class="mono">model</span> 决定路由、<span class="mono">compression</span> 调压缩阈值、<span class="mono">delegation</span> 管子代理并发与深度(第 16 章)、<span class="mono">curator</span> 控技能生命周期(第 10 章)、<span class="mono">gateway</span> 配各平台网关(第 17 章)、<span class="mono">memory</span> 选记忆后端(第 11 章)。正因为这些行为设置全是可读、可 diff 的纯数据,profile 才能靠「复制一个目录」就连同<strong>整套行为策略</strong>一起克隆;若它们散落在代码常量或 <span class="mono">.env</span> 里,profile 隔离就只能隔离密钥、隔离不了行为,多实例的价值会大打折扣。配置分层与 profile 隔离,本质上是同一个「状态外置、目录即实例」理念的一体两面。</p>

<div class="figure">
<svg viewBox="0 0 680 348" role="img" aria-label="config.yaml 放行为设置、.env 放凭据的分工,以及 .env 里仍有少量非密项">
  <rect x="170" y="18" width="340" height="48" rx="10" fill="var(--panel-2)" stroke="var(--line)" stroke-width="1.5"/>
  <text x="340" y="40" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--ink)">新设置该放哪?</text>
  <text x="340" y="58" text-anchor="middle" font-size="11" fill="var(--muted)">判断:它是秘密吗(API key / token)?</text>

  <line x1="250" y1="66" x2="172" y2="102" stroke="var(--blue)" stroke-width="1.8"/>
  <polygon points="168,94 170,106 179,99" fill="var(--blue)"/>
  <text x="196" y="90" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--blue)">否 → 行为</text>
  <line x1="430" y1="66" x2="508" y2="102" stroke="var(--accent)" stroke-width="1.8"/>
  <polygon points="512,94 510,106 501,99" fill="var(--accent)"/>
  <text x="486" y="90" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--accent-ink)">是 → 凭据</text>

  <rect x="20" y="110" width="312" height="218" rx="12" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="36" y="134" font-size="12.5" font-weight="700" fill="var(--blue)">config.yaml · DEFAULT_CONFIG</text>
  <text x="36" y="151" font-size="10.5" fill="var(--muted)">行为设置(非密 · _deep_merge 自动补键)</text>
  <line x1="34" y1="160" x2="318" y2="160" stroke="var(--blue)" stroke-opacity="0.4"/>
  <g font-size="11" fill="var(--ink)">
    <text x="36" y="182">· 超时 timeouts</text>
    <text x="36" y="203">· 阈值 thresholds</text>
    <text x="36" y="224">· 功能开关 feature flags</text>
    <text x="36" y="245">· 显示偏好 display</text>
    <text x="36" y="266">· model / compression / gateway 区块</text>
    <text x="36" y="287">· _config_version(迁移用)</text>
  </g>

  <rect x="348" y="110" width="312" height="218" rx="12" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>
  <text x="364" y="134" font-size="12.5" font-weight="700" fill="var(--accent-ink)">.env · OPTIONAL_ENV_VARS</text>
  <text x="364" y="151" font-size="10.5" fill="var(--muted)">凭据/密钥(password:True · setup 掩码)</text>
  <line x1="362" y1="160" x2="646" y2="160" stroke="var(--accent)" stroke-opacity="0.5"/>
  <g font-size="11" fill="var(--ink)">
    <text x="364" y="182">🔒 OPENROUTER_API_KEY　password:True</text>
    <text x="364" y="203">🔒 TELEGRAM_BOT_TOKEN　password:True</text>
  </g>
  <rect x="362" y="216" width="284" height="100" rx="9" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="374" y="236" font-size="10.5" font-weight="700" fill="var(--ink)">⚠ 历史包袱 · 并非绝对</text>
  <text x="374" y="255" font-size="10" fill="var(--ink)">仍混入少量 password:False 非密项:</text>
  <text x="374" y="273" font-size="10" fill="var(--muted)" font-family="monospace">NOUS_BASE_URL / GEMINI_BASE_URL</text>
  <text x="374" y="288" font-size="10" fill="var(--muted)" font-family="monospace">/ XAI_BASE_URL(base URL 覆盖)</text>
  <text x="374" y="307" font-size="10" fill="var(--ink)">政策上应只放凭据,现实并不绝对。</text>
</svg>
<div class="fig-cap"><b>config.yaml vs .env 分工</b>:判断标准只有一句——<b>是不是秘密</b>。行为设置(超时/阈值/开关/显示)进 <span class="mono">config.yaml</span>(<span class="mono">DEFAULT_CONFIG</span>,<span class="mono">_deep_merge</span> 自动补键);凭据(API key/token)进 <span class="mono">.env</span>(<span class="mono">OPTIONAL_ENV_VARS</span>,密钥标 <span class="mono">password:True</span> 掩码输入)。但别把它绝对化:<span class="mono">OPTIONAL_ENV_VARS</span> 里至今仍混着少量 <span class="mono">password:False</span> 的非密连接项(如各种 <span class="mono">*_BASE_URL</span>),是历史包袱而非理想。</div>
</div>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc"><span class="mono">hermes -p coder ...</span> 启动</span></div>
  <div class="step"><span class="num">2</span><span class="sc"><span class="mono">main.py</span> 顶层 <span class="mono">_apply_profile_override()</span> 解析 <span class="mono">-p coder</span></span></div>
  <div class="step"><span class="num">3</span><span class="sc"><span class="mono">os.environ["HERMES_HOME"] = ~/.hermes/profiles/coder</span>(早于业务 import)</span></div>
  <div class="step"><span class="num">4</span><span class="sc">其余模块加载,各自调 <span class="mono">get_hermes_home()</span> 读到 coder 目录</span></div>
  <div class="step"><span class="num">5</span><span class="sc">config / .env / 记忆 / 会话 / 技能 / 网关日志 全落在 coder 实例,与 default 完全隔离</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「多实例完全隔离」</div>
  <div class="collab-sub">① 组件清单(★本章核心,其余跨章节配合)</div>
  本章核心:<strong>_apply_profile_override</strong>(import 前抢设 env)、<strong>get_hermes_home</strong>(单一真相源)、<strong>DEFAULT_CONFIG / OPTIONAL_ENV_VARS</strong>(配置分层)。跨章节配合:<span class="mono">HERMES_HOME</span> 决定<strong>记忆</strong>(第 11 章)、<strong>技能</strong>(第 9 章)、<strong>Curator</strong>(第 10 章)、会话库、网关日志各自落哪个 profile;每个平台适配器用 <strong>token lock</strong> 防两个 profile 抢同一 bot 凭据(第 17 章);profile 之间是<strong>独立的岛</strong>——隔离本身就是设计,不做跨 profile 的实时配置继承。
  <div class="collab-sub">② 数据流时序</div>
  <span class="mono">-p coder</span> → <span class="mono">_apply_profile_override()</span>(模块顶层,import 前)→ <span class="mono">HERMES_HOME=profiles/coder</span> → import 链铺开 → 30+ 处模块级 <span class="mono">get_hermes_home()</span> 把路径缓存成 coder → 该进程全程认 coder 实例。
  <div class="collab-sub">③ 关键点</div>
  profile 隔离的全部实现 = 「在 import 之前设一个环境变量」+「所有路径走 <span class="mono">get_hermes_home()</span> 单一入口」。任何硬编码 <span class="mono">~/.hermes</span> 都会击穿隔离;非密配置塞 <span class="mono">.env</span> 是另一种坏味道(应进 <span class="mono">config.yaml</span>)。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线:<strong>import 前抢设 HERMES_HOME + 单一真相源路径 = 完全隔离的多实例;配置再分层(密钥独立)</strong>。它主要治两条 LLM 固有约束:
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·运维</span>——一个人要同时跑 work / personal / 各客户的多个 agent 实例,各自的密钥、记忆、会话、网关绝不能混。一个环境变量切换整套状态盘,运维上「开一个新实例」=「建一个新目录」,干净利落;<span class="mono">display_hermes_home()</span> 还让所有用户可见消息显示正确的 profile 路径。</p>
  <p style="margin:.5rem 0 0"><span class="badge constraint">B·无状态</span>——核心代码里<strong>没有</strong>全局的「当前是哪个实例」状态,全靠 <span class="mono">HERMES_HOME</span> 这一个外部变量 + <span class="mono">get_hermes_home()</span> 这一个入口推导。无状态内核 + 外部一个变量定乾坤,正是全书反复出现的母题。</p>
  <p style="margin:.5rem 0 0">反模式:① 在代码里硬编码 <span class="mono">Path.home()/".hermes"</span>——会无视 profile、把数据写错实例(PR #3575 修了 5 个);② 把超时/开关这类<strong>非密行为</strong>配置塞进 <span class="mono">.env</span>——污染了「.env 放凭据、行为设置进 config.yaml」的边界。</p>
  <p style="margin:.5rem 0 0">为什么 profile 之间是<strong>独立的岛</strong>、刻意不做实时配置继承?因为耦合恰恰是隔离要防的东西:若 coder profile 实时继承 default 的 config,那改一下 default 就会悄悄改动所有 profile,跨实例污染卷土重来。需要「从我的默认起步」时,正确做法是创建时<strong>一次性拷贝</strong>——<span class="mono">hermes profile create coder --clone</span> 把 config、<span class="mono">.env</span>、技能等复制过去,此后两者各走各路、互不影响。还有个易忽略的细节:<span class="mono">_get_profiles_root()</span> 锚定在<strong>默认</strong> home 而非当前 <span class="mono">HERMES_HOME</span>,这样即便你正身处 coder 实例,<span class="mono">hermes -p coder profile list</span> 也照样能看见所有 profile,而不是只看见自己。</p>
  <p style="margin:.5rem 0 0">隔离还要堵住一个跨实例陷阱:两个 profile 若用同一个 bot token 同时连 Telegram,平台会互踢、消息错乱。所以网关平台适配器在 <span class="mono">connect()</span> 里调 <span class="mono">acquire_scoped_lock()</span>(来自 <span class="mono">gateway.status</span>)按凭据上锁、在 <span class="mono">disconnect()</span> 时释放,确保同一凭据全局只有一个实例在用(详见第 17 章)。这条与 profile 目录隔离合起来,正是第 24 章安全防线的一环——要防的不只是外部攻击,也防你自己的多个实例互相串台、污染彼此的记忆与会话。</p>
  <p style="margin:.5rem 0 0">最后一处易被忽略的对称:代码取路径用 <span class="mono">get_hermes_home()</span>,<strong>给人看</strong>路径却要用 <span class="mono">display_hermes_home()</span>。后者把绝对路径压成 <span class="mono">~/.hermes</span> 或 <span class="mono">~/.hermes/profiles/coder</span> 这样的友好写法,让 setup、日志、报错里印出的目录一眼就能认出「现在在哪个 profile」。若这里图省事硬编码 <span class="mono">~/.hermes</span>,profile 用户就会被「提示路径」与「真实路径」不一致坑到——这正是 PR #3575 那 5 个 bug 的同源教训:无论是写盘的代码还是给人读的文案,只要碰 home 路径,就得走 profile-aware 的那唯一一个入口。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>一个环境变量</strong>:profile = 在任何 import 之前把 <span class="mono">HERMES_HOME</span> 设成 <span class="mono">~/.hermes/profiles/&lt;名字&gt;</span>;<span class="mono">_apply_profile_override()</span> 是模块级调用,抢在最前。</li>
    <li><strong>单一真相源</strong>:全代码库走 <span class="mono">get_hermes_home()</span> 读 <span class="mono">HERMES_HOME</span>;<strong>禁止</strong>硬编码 <span class="mono">~/.hermes</span>(否则击穿隔离,PR #3575)。</li>
    <li><strong>配置分层</strong>:行为设置(超时/阈值/开关)进 <span class="mono">config.yaml</span>(<span class="mono">DEFAULT_CONFIG</span>);凭据进 <span class="mono">.env</span>(<span class="mono">OPTIONAL_ENV_VARS</span>,密钥标 <span class="mono">password: True</span> 掩码输入)。</li>
    <li><strong>完全隔离</strong>:每个 profile 的 config / 密钥 / 记忆 / 会话 / 技能 / 网关全独立;profile 之间是独立的岛,不做实时配置继承。</li>
    <li><strong>用户可见路径</strong>:打印/日志用 <span class="mono">display_hermes_home()</span>(default 显示 <span class="mono">~/.hermes</span>、profile 显示 <span class="mono">~/.hermes/profiles/coder</span>)。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">On one machine you want two fully independent Hermes instances: a "work" one and a "personal" one, each with its own API keys, memory, sessions, skills, gateway — never crossing wires. That's a <strong>profile</strong>. All its magic boils down to one sentence: <strong>before any module is imported, set one environment variable, <span class="mono">HERMES_HOME</span>, first</strong>.</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · branches of a hotel chain</div>
  One management system (the Hermes code) runs many branches (profiles). Each branch has <strong>its own keys, ledgers, rooms</strong> (its own <span class="mono">HERMES_HOME</span> directory). The moment you walk in, the front desk confirms "which branch are you" (<span class="mono">_apply_profile_override</span> sets <span class="mono">HERMES_HOME</span> first), and from then on <strong>everything</strong> you do automatically uses that branch's resources — no charging the wrong ledger, no grabbing the wrong key.
</div>

<div class="card macro">
  <div class="tag">🌍 Macro · one env var decides everything</div>
  Switching profiles does <strong>one thing</strong>: at the <strong>module top level</strong> of <span class="mono">main.py</span>, before any other import, set <span class="mono">HERMES_HOME</span> to <span class="mono">~/.hermes/profiles/&lt;name&gt;</span>. After that, the codebase's single path entry point <span class="mono">get_hermes_home()</span> automatically points there, and config/keys/memory/sessions/skills are <strong>fully isolated</strong>. Config itself splits in two layers: behavioral settings go in <span class="mono">config.yaml</span>, secrets in <span class="mono">.env</span>.
</div>

<h2>Win the race: set HERMES_HOME before imports</h2>
<p>The key is timing — it must happen <strong>before</strong> any module caches a path:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">hermes_cli/main.py</span><span class="ln">336-508 · simplified</span></div>
  <pre><span class="kw">def</span> <span class="fn">_apply_profile_override</span>() -&gt; <span class="kw">None</span>:
    <span class="cm">&quot;&quot;&quot;Pre-parse --profile/-p and set HERMES_HOME before imports.&quot;&quot;&quot;</span>
    profile_name = ...                       <span class="cm"># parse -p / --profile from argv</span>
    <span class="kw">if</span> profile_name <span class="kw">is</span> <span class="kw">not</span> <span class="kw">None</span>:
        hermes_home = resolve_profile_env(profile_name)   <span class="cm"># → ~/.hermes/profiles/coder</span>
        os.environ[<span class="st">"HERMES_HOME"</span>] = hermes_home          <span class="cm"># set the env var first</span>
        <span class="cm"># then strip the -p flag from argv so argparse won't choke</span>

_apply_profile_override()   <span class="cm"># module-level: runs before the other imports</span></pre>
</div>
<p>Notice that last line, <span class="mono">_apply_profile_override()</span>, is a <strong>module-level call</strong> — it runs at the top of <span class="mono">main.py</span>, <strong>earlier than</strong> importing the persistence modules like <span class="mono">config</span> and <span class="mono">env_loader</span> that read/cache <span class="mono">HERMES_HOME</span>. By the time those modules read <span class="mono">HERMES_HOME</span> at load time, it already points at the profile's directory. One env var redirects the whole dependency tree to the right instance.</p>
<p>Why must this run at the <strong>module top level, before any import</strong>, rather than inside some <span class="mono">main()</span> function? Because Python imports run exactly once, and many persistence modules compute their path with <span class="mono">get_hermes_home()</span> and cache it into a module-level constant at the very moment they're imported (the same "import = register" property as auto-discovery in ch.8). If <span class="mono">config</span> or <span class="mono">env_loader</span> gets imported first, it reads the default <span class="mono">~/.hermes</span>, and setting the profile afterward is too late — the cache is frozen and cannot be corrected. Writing <span class="mono">_apply_profile_override()</span> as a bare call at the very top of the file uses "import order," the one reliable lock, to guarantee the env var is in place before the first persistence module loads. That's also why it hand-rolls its own argv parsing instead of using <span class="mono">argparse</span>: argparse would have to import a pile of modules first, too late.</p>
<p>This race-winning mechanism has two easily-missed finishing touches. First, after setting <span class="mono">HERMES_HOME</span>, <span class="mono">_apply_profile_override()</span> strips the <span class="mono">-p/--profile</span> flag out of <span class="mono">argv</span> so the real <span class="mono">argparse</span> later won't choke on an argument it doesn't know — profile parsing deliberately runs <strong>before</strong> standard argument parsing, as a separate lightweight pass. Second, the fallback "platform default" isn't a hardcoded <span class="mono">~/.hermes</span>: on Windows <span class="mono">_get_platform_default_hermes_home()</span> uses a directory under <span class="mono">LOCALAPPDATA</span> instead. So this single entry point serves not only profile isolation but also folds cross-platform path differences into one function, invisible to every caller — the maintainability dividend of a single source of truth.</p>

<h2>Single source of truth: every path asks it</h2>
<p>The codebase must not hardcode <span class="mono">~/.hermes</span>; everything goes through this one function:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">hermes_constants.py</span><span class="ln">54-109 · excerpt</span></div>
  <pre><span class="kw">def</span> <span class="fn">get_hermes_home</span>() -&gt; Path:
    <span class="cm">&quot;&quot;&quot;Reads HERMES_HOME env var, falls back to the platform-native default.</span>
<span class="cm">    This is the single source of truth — all other copies should import this.&quot;&quot;&quot;</span>
    override = get_hermes_home_override()    <span class="cm"># ContextVar-level override (concurrency)</span>
    <span class="kw">if</span> override:
        <span class="kw">return</span> Path(override)
    val = os.environ.get(<span class="st">"HERMES_HOME"</span>, <span class="st">""</span>).strip()
    <span class="kw">if</span> val:
        <span class="kw">return</span> Path(val)                     <span class="cm"># ← exactly what the profile set</span>
    <span class="kw">return</span> _get_platform_default_hermes_home()   <span class="cm"># default ~/.hermes</span></pre>
</div>
<p><strong>"single source of truth — all other copies should import this"</strong>: all 30+ places in the codebase that persist state don't splice <span class="mono">~/.hermes</span> themselves — they call <span class="mono">get_hermes_home()</span>. So once a profile sets <span class="mono">HERMES_HOME</span> up front, the session store, memory, skills, gateway logs… <strong>all automatically</strong> land in the profile directory. Conversely, any one hardcoded <span class="mono">Path.home()/".hermes"</span> would <strong>pierce the isolation</strong> (PR #3575 fixed 5 such bugs in one go).</p>
<p>The engineering philosophy behind this fallback is worth savoring: <span class="mono">get_hermes_home()</span> would rather <strong>quietly fall back to the default plus a warning</strong> when <span class="mono">HERMES_HOME</span> is missing than turn itself into a strict gatekeeper that throws. The reason, as above: it's the foundation called synchronously by 30+ modules at import time, and any foundation that can fail makes the whole process's startup brittle. Keep uncertainty out of the import phase, pin it once up front via the env var, then let every caller blindly trust this one entry — that's the book's "stateless core plus one external variable to rule them all" realized at the path layer. That is also exactly why subprocess spawners (the <span class="mono">systemd</span> template, the kanban dispatcher) must propagate <span class="mono">HERMES_HOME</span> explicitly; otherwise the child can't read the env var, silently falls back to the default instance, and writes to the wrong profile — the most insidious source of contamination when running many instances.</p>
<p>Why a <strong>function</strong> and not a module-level constant? Because a constant is evaluated at import time and can never change afterward, whereas profiles, subagents, and concurrent threads may all need to switch home at runtime. Each call to <span class="mono">get_hermes_home()</span> first checks a <span class="mono">ContextVar</span> override — letting concurrent subagents in the same process each honor their own instance, echoing the delegation isolation of ch.16 — then the <span class="mono">HERMES_HOME</span> env var, and only then falls back to the platform default. The source even keeps a deliberate branch: when the env var is missing but an <span class="mono">active_profile</span> file points at a non-default profile, it logs a loud one-shot warning to <span class="mono">errors.log</span>. Why warn instead of raise? Because this function has 30+ module-level callers that run it at import time; raising would crash them all, so it prefers a diagnosable warning over blocking startup.</p>

<div class="figure">
<svg viewBox="0 0 680 392" role="img" aria-label="Profiles are independent islands: each profile has its own HERMES_HOME, fully isolated, with no live inheritance">
  <rect x="20" y="20" width="300" height="46" rx="9" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="170" y="40" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--accent-ink)">_apply_profile_override()</text>
  <text x="170" y="57" text-anchor="middle" font-size="10.5" fill="var(--accent-ink)">before any import · sets HERMES_HOME first</text>
  <line x1="320" y1="43" x2="356" y2="43" stroke="var(--muted)" stroke-width="2"/>
  <polygon points="356,38 366,43 356,48" fill="var(--muted)"/>
  <rect x="368" y="20" width="292" height="46" rx="9" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="2"/>
  <text x="514" y="40" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--blue)">get_hermes_home()</text>
  <text x="514" y="57" text-anchor="middle" font-size="10.5" fill="var(--blue)">single entry · every path asks it</text>

  <text x="340" y="86" text-anchor="middle" font-size="11" fill="var(--muted)">each process's HERMES_HOME points at only <tspan font-weight="700" fill="var(--ink)">one island</tspan>; islands stay isolated</text>

  <path d="M118 132 Q229 96 340 132" fill="none" stroke="var(--purple)" stroke-width="1.6" stroke-dasharray="5 4"/>
  <polygon points="335,123 343,134 329,132" fill="var(--purple)"/>
  <text x="229" y="108" text-anchor="middle" font-size="10" fill="var(--purple)">--clone: one-time copy at creation (separate ever after)</text>

  <rect x="20" y="134" width="196" height="216" rx="12" fill="var(--panel-2)" stroke="var(--line)" stroke-width="1.5"/>
  <text x="118" y="158" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--ink)">default</text>
  <text x="118" y="173" text-anchor="middle" font-size="9" fill="var(--muted)" font-family="monospace">~/.hermes</text>
  <line x1="34" y1="182" x2="202" y2="182" stroke="var(--line)"/>
  <g font-size="10.5" fill="var(--ink)">
    <text x="34" y="203">· config.yaml</text>
    <text x="34" y="222">· .env (secrets)</text>
    <text x="34" y="241">· memory</text>
    <text x="34" y="260">· sessions</text>
    <text x="34" y="279">· skills</text>
    <text x="34" y="298">· gateway</text>
  </g>

  <rect x="242" y="134" width="196" height="216" rx="12" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="340" y="158" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--blue)">coder</text>
  <text x="340" y="173" text-anchor="middle" font-size="9" fill="var(--muted)" font-family="monospace">~/.hermes/profiles/coder</text>
  <line x1="256" y1="182" x2="424" y2="182" stroke="var(--blue)" stroke-opacity="0.4"/>
  <g font-size="10.5" fill="var(--ink)">
    <text x="256" y="203">· config.yaml</text>
    <text x="256" y="222">· .env (secrets)</text>
    <text x="256" y="241">· memory</text>
    <text x="256" y="260">· sessions</text>
    <text x="256" y="279">· skills</text>
    <text x="256" y="298">· gateway</text>
  </g>

  <rect x="464" y="134" width="196" height="216" rx="12" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="1.5"/>
  <text x="562" y="158" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--purple)">personal</text>
  <text x="562" y="173" text-anchor="middle" font-size="9" fill="var(--muted)" font-family="monospace">~/.hermes/profiles/personal</text>
  <line x1="478" y1="182" x2="646" y2="182" stroke="var(--purple)" stroke-opacity="0.4"/>
  <g font-size="10.5" fill="var(--ink)">
    <text x="478" y="203">· config.yaml</text>
    <text x="478" y="222">· .env (secrets)</text>
    <text x="478" y="241">· memory</text>
    <text x="478" y="260">· sessions</text>
    <text x="478" y="279">· skills</text>
    <text x="478" y="298">· gateway</text>
  </g>

  <line x1="229" y1="190" x2="229" y2="344" stroke="var(--red)" stroke-width="1.4" stroke-dasharray="4 4"/>
  <text x="229" y="261" text-anchor="middle" font-size="13" font-weight="700" fill="var(--red)">✕</text>
  <line x1="451" y1="190" x2="451" y2="344" stroke="var(--red)" stroke-width="1.4" stroke-dasharray="4 4"/>
  <text x="451" y="261" text-anchor="middle" font-size="13" font-weight="700" fill="var(--red)">✕</text>

  <text x="340" y="378" text-anchor="middle" font-size="10.5" fill="var(--muted)"><tspan fill="var(--red)" font-weight="700">✕</tspan> no live inheritance　·　hardcoding ~/.hermes pierces isolation (PR #3575)</text>
</svg>
<div class="fig-cap"><b>Profiles: independent islands</b>: <span class="mono">_apply_profile_override()</span> sets <span class="mono">HERMES_HOME</span> before any import, and the whole codebase then goes through the single <span class="mono">get_hermes_home()</span> entry — so each profile's config/secrets/memory/sessions/skills/gateway <b>land in their own directory, fully isolated</b>. Islands <b>deliberately do no live inheritance</b> (so one edit can't pollute all); to "start from default," use the one-time copy-at-creation <span class="mono">--clone</span>.</div>
</div>

<h2>Config layering: behavior in yaml, secrets in env</h2>
<p>Profiles isolate "where to store"; "what to store" splits cleanly in two:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">hermes_cli/config.py</span><span class="ln">883 / 2860 / 2885 · simplified</span></div>
  <pre><span class="cm"># config.yaml — all behavioral settings (timeouts/thresholds/flags/display)</span>
DEFAULT_CONFIG = {
    <span class="st">"_config_version"</span>: 30,
    <span class="st">"model"</span>: {...}, <span class="st">"agent"</span>: {...}, <span class="st">"terminal"</span>: {...},
    <span class="st">"compression"</span>: {...}, <span class="st">"memory"</span>: {...}, <span class="st">"gateway"</span>: {...},
}

<span class="cm"># .env — credentials/secrets (secret entries password:True, masked in setup)</span>
OPTIONAL_ENV_VARS = {
    <span class="st">"OPENROUTER_API_KEY"</span>: {<span class="st">"password"</span>: <span class="kw">True</span>, <span class="st">"category"</span>: <span class="st">"provider"</span>},
    <span class="st">"TELEGRAM_BOT_TOKEN"</span>: {<span class="st">"password"</span>: <span class="kw">True</span>, <span class="st">"category"</span>: <span class="st">"messaging"</span>},
}</pre>
</div>
<p>The design intent is clear: <strong><span class="mono">.env</span> is mainly for credentials</strong> (secret entries marked <span class="mono">password: True</span> and masked in the setup wizard; <span class="mono">OPTIONAL_ENV_VARS</span> also holds a few <span class="mono">password: False</span> non-secret connection entries like base URLs and proxies); while timeouts, thresholds, feature flags, display prefs — those <strong>behavioral settings all go in <span class="mono">config.yaml</span></strong>. So "set a working directory for messaging" must never go in <span class="mono">.env</span> (the deprecated <span class="mono">MESSAGING_CWD</span> is the cautionary tale) but in <span class="mono">terminal.cwd</span>. This line keeps credentials in a separately protectable, separately gitignored file.</p>
<p>Why insist on splitting secrets and behavioral settings into two files? Because their lifecycle and trust level are worlds apart: secrets must never enter version control, so <span class="mono">.env</span> can be separately <span class="mono">gitignore</span>d and separately permission-locked, while <span class="mono">config.yaml</span> is a readable, diffable behavioral snapshot that travels with the project — teammates can edit it without fear of leaking anything. There's a hidden engineering dividend too: <span class="mono">DEFAULT_CONFIG</span> and the user yaml merge via <span class="mono">_deep_merge</span>, so adding a new key is auto-filled, and only destructive migrations (renaming keys, changing structure) need a <span class="mono">_config_version</span> bump. The cost is three config-read paths — the CLI's <span class="mono">load_cli_config</span>, subcommands' <span class="mono">load_config</span>, and the gateway reading yaml raw — and a new key must cover all three, or you get the weird "the CLI sees it but the gateway doesn't" inconsistency.</p>
<p>Here we must stay honest about "<span class="mono">.env</span> is all secrets": that's the <strong>design policy and ideal</strong>, not the absolute reality. Browse <span class="mono">OPTIONAL_ENV_VARS</span> and you'll find plenty of non-secret entries marked <span class="mono">password: False</span> — for example <span class="mono">NOUS_BASE_URL</span>, <span class="mono">GEMINI_BASE_URL</span>, <span class="mono">XAI_BASE_URL</span> and other base-URL overrides — that, for historical and compatibility reasons, still live in <span class="mono">.env</span>. So the accurate phrasing is: <strong>by policy <span class="mono">.env</span> should hold only credentials, but historical baggage means it still mixes in a few non-secret connection entries</strong>. The test for where a new setting belongs is simple — is it a secret? An API key or token goes in <span class="mono">.env</span>; a timeout, threshold, flag, or display pref goes in <span class="mono">config.yaml</span>. Don't let the existing exceptions mislead you.</p>
<p>Pulling <span class="mono">config.yaml</span> out on its own carries a global significance too: it is essentially the <strong>master switchboard</strong> for the behaviors of every chapter in this book. In one yaml file, <span class="mono">model</span> drives routing, <span class="mono">compression</span> tunes the compression threshold, <span class="mono">delegation</span> governs subagent concurrency and depth (ch.16), <span class="mono">curator</span> controls skill lifecycle (ch.10), <span class="mono">gateway</span> configures the per-platform gateways (ch.17), and <span class="mono">memory</span> selects the memory backend (ch.11). Precisely because these behavioral settings are all readable, diffable pure data, a profile can clone an <strong>entire behavioral policy</strong> just by copying a directory; if they were scattered across code constants or <span class="mono">.env</span>, profile isolation could only isolate secrets, not behavior, and the value of multi-instance would be badly diminished. Config layering and profile isolation are two sides of the same "state externalized, a directory is an instance" idea.</p>

<div class="figure">
<svg viewBox="0 0 680 348" role="img" aria-label="config.yaml holds behavioral settings, .env holds credentials, and .env still mixes in a few non-secret entries">
  <rect x="170" y="18" width="340" height="48" rx="10" fill="var(--panel-2)" stroke="var(--line)" stroke-width="1.5"/>
  <text x="340" y="40" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--ink)">Where does a new setting go?</text>
  <text x="340" y="58" text-anchor="middle" font-size="11" fill="var(--muted)">Test: is it a secret (API key / token)?</text>

  <line x1="250" y1="66" x2="172" y2="102" stroke="var(--blue)" stroke-width="1.8"/>
  <polygon points="168,94 170,106 179,99" fill="var(--blue)"/>
  <text x="196" y="90" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--blue)">no → behavior</text>
  <line x1="430" y1="66" x2="508" y2="102" stroke="var(--accent)" stroke-width="1.8"/>
  <polygon points="512,94 510,106 501,99" fill="var(--accent)"/>
  <text x="486" y="90" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--accent-ink)">yes → secret</text>

  <rect x="20" y="110" width="312" height="218" rx="12" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="36" y="134" font-size="12.5" font-weight="700" fill="var(--blue)">config.yaml · DEFAULT_CONFIG</text>
  <text x="36" y="151" font-size="10.5" fill="var(--muted)">behavioral (non-secret · _deep_merge auto-fills)</text>
  <line x1="34" y1="160" x2="318" y2="160" stroke="var(--blue)" stroke-opacity="0.4"/>
  <g font-size="11" fill="var(--ink)">
    <text x="36" y="182">· timeouts</text>
    <text x="36" y="203">· thresholds</text>
    <text x="36" y="224">· feature flags</text>
    <text x="36" y="245">· display prefs</text>
    <text x="36" y="266">· model / compression / gateway blocks</text>
    <text x="36" y="287">· _config_version (migration)</text>
  </g>

  <rect x="348" y="110" width="312" height="218" rx="12" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>
  <text x="364" y="134" font-size="12.5" font-weight="700" fill="var(--accent-ink)">.env · OPTIONAL_ENV_VARS</text>
  <text x="364" y="151" font-size="10.5" fill="var(--muted)">credentials (password:True · masked in setup)</text>
  <line x1="362" y1="160" x2="646" y2="160" stroke="var(--accent)" stroke-opacity="0.5"/>
  <g font-size="11" fill="var(--ink)">
    <text x="364" y="182">🔒 OPENROUTER_API_KEY　password:True</text>
    <text x="364" y="203">🔒 TELEGRAM_BOT_TOKEN　password:True</text>
  </g>
  <rect x="362" y="216" width="284" height="100" rx="9" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="374" y="236" font-size="10.5" font-weight="700" fill="var(--ink)">⚠ Historical baggage · not absolute</text>
  <text x="374" y="255" font-size="10" fill="var(--ink)">a few password:False non-secret entries:</text>
  <text x="374" y="273" font-size="10" fill="var(--muted)" font-family="monospace">NOUS_BASE_URL / GEMINI_BASE_URL</text>
  <text x="374" y="288" font-size="10" fill="var(--muted)" font-family="monospace">/ XAI_BASE_URL (base-URL overrides)</text>
  <text x="374" y="307" font-size="10" fill="var(--ink)">policy: secrets only — reality differs.</text>
</svg>
<div class="fig-cap"><b>config.yaml vs .env split</b>: the test is one question — <b>is it a secret?</b> Behavioral settings (timeouts/thresholds/flags/display) go in <span class="mono">config.yaml</span> (<span class="mono">DEFAULT_CONFIG</span>, <span class="mono">_deep_merge</span> auto-fills keys); credentials (API key/token) go in <span class="mono">.env</span> (<span class="mono">OPTIONAL_ENV_VARS</span>, secrets marked <span class="mono">password:True</span>, masked input). But don't take it as absolute: <span class="mono">OPTIONAL_ENV_VARS</span> still mixes in a few <span class="mono">password:False</span> non-secret connection entries (various <span class="mono">*_BASE_URL</span>) — historical baggage, not the ideal.</div>
</div>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc"><span class="mono">hermes -p coder ...</span> starts</span></div>
  <div class="step"><span class="num">2</span><span class="sc"><span class="mono">main.py</span> top-level <span class="mono">_apply_profile_override()</span> parses <span class="mono">-p coder</span></span></div>
  <div class="step"><span class="num">3</span><span class="sc"><span class="mono">os.environ["HERMES_HOME"] = ~/.hermes/profiles/coder</span> (before business imports)</span></div>
  <div class="step"><span class="num">4</span><span class="sc">other modules load, each calls <span class="mono">get_hermes_home()</span> and reads the coder dir</span></div>
  <div class="step"><span class="num">5</span><span class="sc">config / .env / memory / sessions / skills / gateway logs all land in the coder instance, fully isolated from default</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "fully isolated multi-instance"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: <strong>_apply_profile_override</strong> (set env before imports), <strong>get_hermes_home</strong> (single source of truth), <strong>DEFAULT_CONFIG / OPTIONAL_ENV_VARS</strong> (config layering). Cross-chapter teamwork: <span class="mono">HERMES_HOME</span> decides which profile holds <strong>memory</strong> (ch.11), <strong>skills</strong> (ch.9), the <strong>Curator</strong> (ch.10), the session store, and gateway logs; each platform adapter uses a <strong>token lock</strong> so two profiles can't grab the same bot credential (ch.17); profiles are <strong>independent islands</strong> — isolation is the design, so there's no live cross-profile config inheritance.
  <div class="collab-sub">② Data-flow timing</div>
  <span class="mono">-p coder</span> → <span class="mono">_apply_profile_override()</span> (module top level, before imports) → <span class="mono">HERMES_HOME=profiles/coder</span> → the import chain unfolds → 30+ module-level <span class="mono">get_hermes_home()</span> calls cache the path as coder → that process honors the coder instance throughout.
  <div class="collab-sub">③ The key point</div>
  All of profile isolation = "set one env var before imports" + "every path goes through the single <span class="mono">get_hermes_home()</span> entry." Any hardcoded <span class="mono">~/.hermes</span> pierces the isolation; stuffing non-secret config into <span class="mono">.env</span> is the other bad smell (it belongs in <span class="mono">config.yaml</span>).
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>set HERMES_HOME before imports + a single source of truth for paths = fully isolated instances; then layer config (secrets apart)</strong>. It mainly treats two inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·ops</span> — one person runs work / personal / per-client agent instances at once, and their keys, memory, sessions, gateways must never mix. One env var switches the whole state directory, so operationally "spin up a new instance" = "make a new directory," clean and simple; <span class="mono">display_hermes_home()</span> also makes every user-facing message show the correct profile path.</p>
  <p style="margin:.5rem 0 0"><span class="badge constraint">B·statelessness</span> — the core code holds <strong>no</strong> global "which instance am I" state; it derives everything from the one external <span class="mono">HERMES_HOME</span> var plus the one <span class="mono">get_hermes_home()</span> entry. A stateless core plus one external variable to rule them all — the book's recurring motif.</p>
  <p style="margin:.5rem 0 0">Anti-patterns: ① hardcoding <span class="mono">Path.home()/".hermes"</span> in code — ignores the profile and writes to the wrong instance (PR #3575 fixed 5); ② stuffing <strong>non-secret behavioral</strong> config like timeouts/flags into <span class="mono">.env</span> — pollutes the ".env for credentials, behavioral settings in config.yaml" boundary.</p>
  <p style="margin:.5rem 0 0">Why are profiles <strong>independent islands</strong> by design, deliberately without live config inheritance? Because coupling is exactly what isolation is meant to prevent: if the coder profile inherited default's config live, one edit to default would silently mutate every profile, and cross-instance contamination would return. When you want to "start from my default," the right move is a one-time copy at creation — <span class="mono">hermes profile create coder --clone</span> copies config, <span class="mono">.env</span>, skills and so on across, after which the two go their own ways untouched. An easily-missed detail: <span class="mono">_get_profiles_root()</span> is anchored to the <strong>default</strong> home rather than the current <span class="mono">HERMES_HOME</span>, so even while you're inside the coder instance, <span class="mono">hermes -p coder profile list</span> can still see all profiles, not just its own.</p>
  <p style="margin:.5rem 0 0">Isolation also has to plug a cross-instance trap: if two profiles use the same bot token to connect to Telegram at once, the platform kicks them back and forth and messages scramble. So a gateway platform adapter calls <span class="mono">acquire_scoped_lock()</span> (from <span class="mono">gateway.status</span>) in <span class="mono">connect()</span> to lock by credential and releases it in <span class="mono">disconnect()</span>, ensuring only one instance globally uses a given credential (see ch.17). Combined with profile directory isolation, this is one strand of ch.24's security defense — what it guards against is not only external attackers but also your own multiple instances crossing wires and polluting each other's memory and sessions.</p>
  <p style="margin:.5rem 0 0">One last easily-overlooked symmetry: code reads paths with <span class="mono">get_hermes_home()</span>, but <strong>showing</strong> a path to a human uses <span class="mono">display_hermes_home()</span>. The latter compresses the absolute path into friendly forms like <span class="mono">~/.hermes</span> or <span class="mono">~/.hermes/profiles/coder</span>, so the directory printed in setup, logs, and errors instantly reveals which profile you're in. Hardcode <span class="mono">~/.hermes</span> here to save effort and profile users get burned by a mismatch between the "displayed path" and the "real path" — exactly the shared lesson of those 5 PR #3575 bugs: whether it's disk-writing code or human-readable copy, anytime you touch the home path you must go through that one profile-aware entry.</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>One env var</strong>: a profile = setting <span class="mono">HERMES_HOME</span> to <span class="mono">~/.hermes/profiles/&lt;name&gt;</span> before any import; <span class="mono">_apply_profile_override()</span> is a module-level call that runs first.</li>
    <li><strong>Single source of truth</strong>: the whole codebase calls <span class="mono">get_hermes_home()</span> to read <span class="mono">HERMES_HOME</span>; <strong>never</strong> hardcode <span class="mono">~/.hermes</span> (or you pierce isolation, PR #3575).</li>
    <li><strong>Config layering</strong>: behavioral settings (timeouts/thresholds/flags) go in <span class="mono">config.yaml</span> (<span class="mono">DEFAULT_CONFIG</span>); credentials in <span class="mono">.env</span> (<span class="mono">OPTIONAL_ENV_VARS</span>, secret entries marked <span class="mono">password: True</span>).</li>
    <li><strong>Full isolation</strong>: each profile's config / secrets / memory / sessions / skills / gateway are independent; profiles are independent islands, no live config inheritance.</li>
    <li><strong>User-facing paths</strong>: print/log with <span class="mono">display_hermes_home()</span> (default shows <span class="mono">~/.hermes</span>, a profile shows <span class="mono">~/.hermes/profiles/coder</span>).</li>
  </ul>
</div>
"""
}
