LESSON_27 = {
    "zh": r"""
<p class="lead">模型不是一个端点，而是一个需要<strong>调度</strong>的资源池——多把 API key 要轮换与熔断、不同的副任务要路由到不同模型、每个模型的上下文窗口要先<strong>算出来</strong>才能决定何时压缩。</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 能源调度中心</div>
  把模型层想成一座<strong>电网调度中心</strong>：你手里不是一台发电机，而是<strong>一堆电厂</strong>——每座电厂是一把 API key、一个 provider。它们状态各不相同：有的<strong>满载跳闸</strong>、进入冷却等一会儿才恢复（被限流的 key），有的干脆<strong>烧毁退役</strong>、再也不会来电（被吊销的凭证）。
  <p style="margin:.6rem 0 0">调度员要同时把三件事做对：第一，<strong>绝不反复去戳一座已确认没电的电厂</strong>——明知它的额度已经归零，还一遍遍发请求，只是白白浪费往返、甚至招来更重的惩罚；第二，要按<strong>负载分派机组</strong>：主厨房的大灶（主对话）上主力机组，后勤打杂（起标题、压缩、搜索这些副 LLM 活）派一台<strong>便宜的小机组</strong>就够了；第三，排班之前得先知道每座电厂的<strong>额定功率</strong>（上下文窗口有多大），否则你根本不知道什么时候该把负载挪走（触发压缩）。这一章讲的，就是 Hermes 怎么把这三件事做成<strong>有状态的调度</strong>，而不是把模型当成一个随叫随到的无状态插座。</p>
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 模型层的三个隐藏复杂度</div>
  「调用一个模型」听起来是最简单的一步，可一旦你要把它做<strong>稳</strong>，就会冒出三层平时看不见的复杂度——
  <p style="margin:.6rem 0 0"><strong>① 凭证不是一把 key，是一个有状态的池。</strong>同一个 provider 你可能握着好几把 key；它们要轮换、要在限流时熔断进冷却、烧毁的要永久退役，还得随时记住「哪一把现在能用」。这套状态机住在 <span class="mono">agent/credential_pool.py</span>，而它最忌讳的一件事，就是去<strong>反复试探一把已确认没额度的 key</strong>——熔断只在 <span class="mono">remaining=0</span> 的确凿证据下才该触发。</p>
  <p><strong>② 「调用模型」不止主对话，还有一大堆副 LLM 任务。</strong>压缩、会话搜索、网页提取、视觉、起标题……每一项都是一次<strong>独立的模型调用</strong>，各自走各自的<strong>解析链与回退顺序</strong>，还能在 <span class="mono">config.yaml</span> 的 <span class="mono">auxiliary.&lt;task&gt;</span> 下<strong>各自钉住自己的 provider 与 model</strong>。统一入口在 <span class="mono">agent/auxiliary_client.py</span>。</p>
  <p><strong>③ 「上下文多大」不是常量，是分层解析出来的。</strong>同一个模型名，窗口大小可能来自已知表、<span class="mono">models.dev</span>、运行时探测，或兜底默认——必须先把这个数<strong>算出来</strong>，压缩才知道该在百分之多少处触发。错算一步，要么过早压缩、白砸缓存，要么超出窗口、直接报错。</p>
  <p>三件事各自独立，却共享同一条主线：<strong>把模型当成需要调度的有状态资源，而不是一个无状态端点</strong>。</p>
</div>

<p>把这三套机制摊到一张图上看——三栏分别是<strong>凭证池</strong>、<strong>副 LLM 路由</strong>、<strong>上下文窗口</strong>，每栏一句「它管什么 + 最大的坑」，底部托着三者共享的那条主线：</p>

<div class="figure">
<svg viewBox="0 0 680 338" role="img" aria-label="模型层三套机制总览：凭证池、副 LLM 路由、上下文窗口三栏，各列出它管什么与最大的坑，底部共享一条把模型当成有状态资源来调度的主线">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">模型层三套机制 · 三栏各管一摊，共享一条主线</text>
  <g>
    <rect x="14" y="42" width="208" height="216" rx="12" fill="var(--panel)" stroke="var(--accent)" stroke-width="1.5"/>
    <text x="30" y="78" font-size="24">🔑</text>
    <text x="64" y="68" font-size="13" font-weight="700" fill="var(--accent-ink)">① 凭证池</text>
    <text x="64" y="86" font-size="9.5" fill="var(--muted)">credentials</text>
    <line x1="22" y1="98" x2="214" y2="98" stroke="var(--line)"/>
    <text x="24" y="120" font-size="10" font-weight="700" fill="var(--accent-ink)">▸ 管什么</text>
    <text x="24" y="139" font-size="10.5" fill="var(--ink)">同 provider 多把 key</text>
    <text x="24" y="156" font-size="10.5" fill="var(--ink)">轮换 · 熔断 · 冷却恢复</text>
    <rect x="22" y="170" width="192" height="76" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
    <text x="34" y="190" font-size="10" font-weight="700" fill="var(--accent-ink)">▸ 最大的坑</text>
    <text x="34" y="210" font-size="10" fill="var(--ink)">别反复戳已确认空的 bucket</text>
    <text x="34" y="228" font-size="10" fill="var(--muted)">（remaining=0 才算熔断）</text>
  </g>
  <g>
    <rect x="236" y="42" width="208" height="216" rx="12" fill="var(--panel)" stroke="var(--blue)" stroke-width="1.5"/>
    <text x="252" y="78" font-size="24">🔀</text>
    <text x="286" y="68" font-size="13" font-weight="700" fill="var(--blue)">② 副 LLM 路由</text>
    <text x="286" y="86" font-size="9.5" fill="var(--muted)">side-LLM routing</text>
    <line x1="244" y1="98" x2="436" y2="98" stroke="var(--line)"/>
    <text x="246" y="120" font-size="10" font-weight="700" fill="var(--blue)">▸ 管什么</text>
    <text x="246" y="139" font-size="10.5" fill="var(--ink)">压缩 / 搜索 / 视觉 / 标题</text>
    <text x="246" y="156" font-size="10.5" fill="var(--ink)">副任务各走各的解析链</text>
    <rect x="244" y="170" width="192" height="76" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="256" y="190" font-size="10" font-weight="700" fill="var(--blue)">▸ 最大的坑</text>
    <text x="256" y="210" font-size="10" fill="var(--ink)">副任务别全压主模型</text>
    <text x="256" y="228" font-size="10" fill="var(--muted)">可 per-task 钉 provider/model</text>
  </g>
  <g>
    <rect x="458" y="42" width="208" height="216" rx="12" fill="var(--panel)" stroke="var(--purple)" stroke-width="1.5"/>
    <text x="474" y="78" font-size="24">📏</text>
    <text x="508" y="68" font-size="13" font-weight="700" fill="var(--purple)">③ 上下文窗口</text>
    <text x="508" y="86" font-size="9.5" fill="var(--muted)">context-length</text>
    <line x1="466" y1="98" x2="658" y2="98" stroke="var(--line)"/>
    <text x="468" y="120" font-size="10" font-weight="700" fill="var(--purple)">▸ 管什么</text>
    <text x="468" y="139" font-size="10.5" fill="var(--ink)">分层解析窗口大小</text>
    <text x="468" y="156" font-size="10.5" fill="var(--ink)">查表 → models.dev → 探测</text>
    <rect x="466" y="170" width="192" height="76" rx="8" fill="var(--purple-soft)" stroke="var(--purple)"/>
    <text x="478" y="190" font-size="10" font-weight="700" fill="var(--purple)">▸ 最大的坑</text>
    <text x="478" y="210" font-size="10" fill="var(--ink)">先算出来才知何时压缩</text>
    <text x="478" y="228" font-size="10" fill="var(--muted)">用常量会压错时机</text>
  </g>
  <line x1="118" y1="258" x2="118" y2="278" stroke="var(--muted)" stroke-width="1.3"/>
  <line x1="340" y1="258" x2="340" y2="278" stroke="var(--muted)" stroke-width="1.3"/>
  <line x1="562" y1="258" x2="562" y2="278" stroke="var(--muted)" stroke-width="1.3"/>
  <rect x="14" y="278" width="652" height="46" rx="10" fill="var(--panel-2)" stroke="var(--accent)"/>
  <rect x="28" y="290" width="64" height="20" rx="10" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="60" y="304" text-anchor="middle" font-size="10" font-weight="700" fill="var(--accent-ink)">共同主线</text>
  <text x="104" y="305" font-size="12" font-weight="700" fill="var(--ink)">把模型当成需要调度的「有状态资源」，而非无状态端点</text>
</svg>
<div class="fig-cap"><b>模型层三套机制</b>：凭证要轮换熔断、副任务要路由、窗口要先算出来——三者都把「调用模型」从一次性动作变成有状态调度。</div>
</div>
""",
    "en": r"""
<p class="lead">A model isn't an endpoint — it's a resource pool that needs <strong>scheduling</strong>: multiple API keys to rotate and trip, side tasks routed to different models, and each model's context window that must be <strong>computed</strong> before deciding when to compress.</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · an energy dispatch center</div>
  Picture the model layer as a <strong>power-grid dispatch center</strong>: you don't hold one generator, you hold <strong>a fleet of power plants</strong> — each plant is an API key, a provider. Their states differ: some are <strong>tripped at full load</strong> and cooling down before they come back (a rate-limited key); some have <strong>burned out for good</strong> and will never supply power again (a revoked credential).
  <p style="margin:.6rem 0 0">The dispatcher has to get three things right at once. First, <strong>never keep poking a plant you've already confirmed is dead</strong> — hammering a key whose quota is provably zero only wastes round-trips and can earn a harsher penalty. Second, <strong>match the unit to the load</strong>: the main kitchen's big stove (the primary conversation) gets the main units, while the back-of-house chores (titling, compression, search — the side-LLM work) need only a <strong>cheap little unit</strong>. Third, you must know each plant's <strong>rated capacity</strong> (how large the context window is) before you schedule, or you won't know when to shift the load off it (trigger compression). This chapter is about how Hermes turns those three into <strong>stateful scheduling</strong> instead of treating the model as a stateless socket you call on demand.</p>
</div>

<div class="card macro">
  <div class="tag">🌍 Macro · three hidden complexities of the model layer</div>
  "Call a model" sounds like the simplest step there is, yet the moment you want it to be <strong>reliable</strong>, three normally-invisible layers of complexity surface —
  <p style="margin:.6rem 0 0"><strong>① A credential isn't one key, it's a stateful pool.</strong> For a single provider you may be holding several keys; they have to rotate, trip into cooldown when rate-limited, retire permanently when dead, and remember at all times "which one works right now." That state machine lives in <span class="mono">agent/credential_pool.py</span>, and its cardinal sin is <strong>re-probing a key you've already confirmed is out of quota</strong> — the breaker should fire only on the hard evidence of <span class="mono">remaining=0</span>.</p>
  <p><strong>② "Calling the model" isn't just the main conversation — there's a crowd of side-LLM tasks.</strong> Compression, session search, web extraction, vision, title generation… each is its own <strong>independent model call</strong>, each with its own <strong>resolution chain and fallback order</strong>, and each can pin its <strong>own provider and model</strong> under <span class="mono">auxiliary.&lt;task&gt;</span> in <span class="mono">config.yaml</span>. The shared entry point is <span class="mono">agent/auxiliary_client.py</span>.</p>
  <p><strong>③ "How big is the context" isn't a constant — it's resolved in layers.</strong> For one model name the window size may come from a known table, <span class="mono">models.dev</span>, a runtime probe, or a fallback default — you must <strong>compute</strong> that number first before compression knows at what percentage to fire. Get it wrong and you either compress too early and waste the cache, or overrun the window and error out.</p>
  <p>The three are independent, yet they share one throughline: <strong>treat the model as a stateful resource to schedule, not a stateless endpoint</strong>.</p>
</div>

<p>Spread those three mechanisms onto one diagram — three columns for the <strong>credential pool</strong>, <strong>side-LLM routing</strong>, and the <strong>context window</strong>, each with a one-liner of "what it manages + its biggest pit," and the shared throughline holding them up along the bottom:</p>

<div class="figure">
<svg viewBox="0 0 680 338" role="img" aria-label="Overview of three model-layer mechanisms: credential pool, side-LLM routing, and context window in three columns, each listing what it manages and its biggest pit, with a shared bottom throughline that treats the model as a stateful resource to schedule">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">Three model-layer mechanisms · three columns, one shared throughline</text>
  <g>
    <rect x="14" y="42" width="208" height="216" rx="12" fill="var(--panel)" stroke="var(--accent)" stroke-width="1.5"/>
    <text x="30" y="78" font-size="24">🔑</text>
    <text x="64" y="68" font-size="13" font-weight="700" fill="var(--accent-ink)">① Credentials</text>
    <text x="64" y="86" font-size="9.5" fill="var(--muted)">the stateful pool</text>
    <line x1="22" y1="98" x2="214" y2="98" stroke="var(--line)"/>
    <text x="24" y="120" font-size="10" font-weight="700" fill="var(--accent-ink)">▸ Manages</text>
    <text x="24" y="139" font-size="10.5" fill="var(--ink)">many keys per provider</text>
    <text x="24" y="156" font-size="10.5" fill="var(--ink)">rotate · trip · cool down</text>
    <rect x="22" y="170" width="192" height="76" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
    <text x="34" y="190" font-size="10" font-weight="700" fill="var(--accent-ink)">▸ Biggest pit</text>
    <text x="34" y="210" font-size="10" fill="var(--ink)">never re-poke a dead bucket</text>
    <text x="34" y="228" font-size="10" fill="var(--muted)">(remaining=0 = real trip)</text>
  </g>
  <g>
    <rect x="236" y="42" width="208" height="216" rx="12" fill="var(--panel)" stroke="var(--blue)" stroke-width="1.5"/>
    <text x="252" y="78" font-size="24">🔀</text>
    <text x="286" y="68" font-size="13" font-weight="700" fill="var(--blue)">② Side-LLM routing</text>
    <text x="286" y="86" font-size="9.5" fill="var(--muted)">auxiliary tasks</text>
    <line x1="244" y1="98" x2="436" y2="98" stroke="var(--line)"/>
    <text x="246" y="120" font-size="10" font-weight="700" fill="var(--blue)">▸ Manages</text>
    <text x="246" y="139" font-size="10.5" fill="var(--ink)">compress / search / vision</text>
    <text x="246" y="156" font-size="10.5" fill="var(--ink)">each task, its own chain</text>
    <rect x="244" y="170" width="192" height="76" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="256" y="190" font-size="10" font-weight="700" fill="var(--blue)">▸ Biggest pit</text>
    <text x="256" y="210" font-size="10" fill="var(--ink)">don't pile all on main model</text>
    <text x="256" y="228" font-size="10" fill="var(--muted)">pin provider/model per task</text>
  </g>
  <g>
    <rect x="458" y="42" width="208" height="216" rx="12" fill="var(--panel)" stroke="var(--purple)" stroke-width="1.5"/>
    <text x="474" y="78" font-size="24">📏</text>
    <text x="508" y="68" font-size="13" font-weight="700" fill="var(--purple)">③ Context window</text>
    <text x="508" y="86" font-size="9.5" fill="var(--muted)">context-length</text>
    <line x1="466" y1="98" x2="658" y2="98" stroke="var(--line)"/>
    <text x="468" y="120" font-size="10" font-weight="700" fill="var(--purple)">▸ Manages</text>
    <text x="468" y="139" font-size="10.5" fill="var(--ink)">resolve the window size</text>
    <text x="468" y="156" font-size="10.5" fill="var(--ink)">table → models.dev → probe</text>
    <rect x="466" y="170" width="192" height="76" rx="8" fill="var(--purple-soft)" stroke="var(--purple)"/>
    <text x="478" y="190" font-size="10" font-weight="700" fill="var(--purple)">▸ Biggest pit</text>
    <text x="478" y="210" font-size="10" fill="var(--ink)">compute it before compressing</text>
    <text x="478" y="228" font-size="10" fill="var(--muted)">a constant mistimes it</text>
  </g>
  <line x1="118" y1="258" x2="118" y2="278" stroke="var(--muted)" stroke-width="1.3"/>
  <line x1="340" y1="258" x2="340" y2="278" stroke="var(--muted)" stroke-width="1.3"/>
  <line x1="562" y1="258" x2="562" y2="278" stroke="var(--muted)" stroke-width="1.3"/>
  <rect x="14" y="278" width="652" height="46" rx="10" fill="var(--panel-2)" stroke="var(--accent)"/>
  <rect x="28" y="290" width="104" height="20" rx="10" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="80" y="304" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--accent-ink)">Common thread</text>
  <text x="144" y="305" font-size="12" font-weight="700" fill="var(--ink)">Treat the model as a stateful resource to schedule, not a stateless endpoint</text>
</svg>
<div class="fig-cap"><b>Three model-layer mechanisms</b>: credentials rotate and trip, side tasks route, the window is computed first — all three turn "calling the model" from a one-shot action into stateful scheduling.</div>
</div>
""",
}

LESSON_28 = {
    "zh": r"""
<p class="lead">一个跑了几十轮、还开着后台进程、正在改文件的 agent，要怎么<strong>安全地急停、可靠地知道后台干完没、原子地落盘</strong>？这一章拆开 Hermes 在运行时最容易出正确性 bug 的三套机制。</p>
""",
    "en": r"""
<p class="lead">An agent that has run dozens of turns, still has background processes open, and is mid-edit on a file — how does it <strong>stop safely, reliably know when background work finishes, and persist atomically</strong>? This chapter opens up the three runtime mechanisms most prone to correctness bugs.</p>
""",
}
