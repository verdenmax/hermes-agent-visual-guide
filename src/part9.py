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

<h3>🔬 27.1 · 凭证池：从一把 key 到有状态的资源池</h3>
<p>同一个 provider，你常常握着不止一把 key——免费额度叠付费、几个账号轮着用。Hermes 把它们收进一个<strong>持久化的凭证池</strong>（<span class="mono">agent/credential_pool.py</span>）：每把 key 是池里一条 <span class="mono">PooledCredential</span>，带着自己的状态——<span class="mono">OK</span>（可用、进轮换）、<span class="mono">EXHAUSTED</span>（限时冷却、暂时退出）、<span class="mono">DEAD</span>（永久排除、再不回来）。<span class="mono">select()</span> 每次取 key，先把<strong>冷却到期</strong>的 <span class="mono">EXHAUSTED</span> 清回 <span class="mono">OK</span>（<span class="mono">clear_expired</span>），再按策略（<span class="mono">random</span> / <span class="mono">least_used</span> / <span class="mono">round_robin</span>）从可用集合里挑一把。</p>
<p>这套机制最在意的一条铁律是——<strong>绝不去反复试探一个已确认空的 bucket</strong>。一把 key 被限流，不是把它从池里删掉、也不是每隔几秒再戳一下看「好了没」，而是给它<strong>盖一个到期时间戳</strong>然后<strong>跳过</strong>：<span class="mono">DEAD</span> 无条件排除（<span class="mono">select()</span> 里直接 <span class="mono">continue</span>），<span class="mono">EXHAUSTED</span> 只有在 <span class="mono">last_error_reset_at</span> 或 TTL 到点后才回到候选。失败发生时，<span class="mono">mark_exhausted_and_rotate()</span> 先给闯祸的那把 key 盖章，再<strong>立刻重选</strong>下一把，主请求不必空等。</p>
<p>冷却时长按触发它的 HTTP 状态分档（<span class="mono">_exhausted_ttl</span>）：<strong>429 限流给 1 小时</strong>、<strong>401 认证失效只给 5 分钟</strong>（让单 key 用户能快点恢复）、其它失败默认 1 小时。但这只是<strong>兜底默认</strong>：只要 provider 在响应里给了 <span class="mono">reset_at</span>，或报错文本里写着「retry after …」「resets in 2 hr 13 min」，Hermes 就<strong>解析出真实恢复时刻去覆盖默认值</strong>，绝不提前撞一堵明知还锁着的墙。还有一种更狠的失败：401 且原因是 <span class="mono">token_revoked</span> / <span class="mono">invalid_grant</span> 这类<strong>永久 OAuth 失效</strong>——它不该走 1 小时冷却（否则每小时回来撞一次、撞完又冷却），而是直接打成 <span class="mono">DEAD</span>，只有用户<strong>重新登录、把新 token 写回</strong>时才清除。</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">agent/credential_pool.py:108</span></div><pre># Cooldown before retrying an exhausted credential.
# Transient 401 auth failures cool down briefly so single-key setups can recover.
# 429 (rate-limited), 402 (billing/quota), and other failures cool down after 1 hour.
# Provider-supplied reset_at timestamps override these defaults.
EXHAUSTED_TTL_401_SECONDS = 5 * 60           # 5 minutes
EXHAUSTED_TTL_429_SECONDS = 60 * 60          # 1 hour
EXHAUSTED_TTL_DEFAULT_SECONDS = 60 * 60      # 1 hour</pre></div>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">agent/credential_pool.py:250</span></div><pre>def _exhausted_ttl(error_code: Optional[int]) -&gt; int:
    &quot;&quot;&quot;Return cooldown seconds based on the HTTP status that caused exhaustion.&quot;&quot;&quot;
    if error_code == 401:
        return EXHAUSTED_TTL_401_SECONDS
    if error_code == 429:
        return EXHAUSTED_TTL_429_SECONDS
    return EXHAUSTED_TTL_DEFAULT_SECONDS</pre></div>

<div class="figure">
<svg viewBox="0 0 680 360" role="img" aria-label="凭证池状态机：OK、EXHAUSTED、DEAD 三个状态及其转移条件——失败盖到期戳进 EXHAUSTED，reset_at 或 TTL 到期清回 OK，401 永久认证失效直接进 DEAD 永久排除，只有重新登录写回 token 才回到 OK">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">凭证池状态机 · 每把 key 三种状态，select() 只从 OK 挑</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">EXHAUSTED 限时退出、到期自动回归；DEAD 永久排除，不靠 TTL 回来</text>
  <rect x="44" y="72" width="180" height="94" rx="14" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="134" y="110" text-anchor="middle" font-size="18" font-weight="700" fill="var(--accent-ink)">OK</text>
  <text x="134" y="130" text-anchor="middle" font-size="9.5" fill="var(--muted)">STATUS_OK</text>
  <text x="134" y="150" text-anchor="middle" font-size="10.5" fill="var(--ink)">可用，进入轮换</text>
  <rect x="456" y="72" width="180" height="94" rx="14" fill="var(--amber-soft)" stroke="var(--amber)" stroke-width="2"/>
  <text x="546" y="106" text-anchor="middle" font-size="14" font-weight="700" fill="var(--amber)">EXHAUSTED</text>
  <text x="546" y="125" text-anchor="middle" font-size="9" fill="var(--muted)">STATUS_EXHAUSTED</text>
  <text x="546" y="145" text-anchor="middle" font-size="10.5" fill="var(--ink)">限时冷却，暂时退出</text>
  <rect x="44" y="244" width="180" height="94" rx="14" fill="var(--red-soft)" stroke="var(--red)" stroke-width="2"/>
  <text x="134" y="280" text-anchor="middle" font-size="16" font-weight="700" fill="var(--red)">DEAD</text>
  <text x="134" y="299" text-anchor="middle" font-size="9" fill="var(--muted)">STATUS_DEAD</text>
  <text x="134" y="319" text-anchor="middle" font-size="10.5" fill="var(--ink)">永久排除</text>
  <line x1="224" y1="104" x2="447" y2="104" stroke="var(--amber)" stroke-width="2"/>
  <path d="M456,104 L447,99 L447,109 Z" fill="var(--amber)"/>
  <text x="335" y="95" text-anchor="middle" font-size="10" fill="var(--amber)">限流 / 认证失败 → 盖到期戳</text>
  <line x1="447" y1="138" x2="233" y2="138" stroke="var(--accent)" stroke-width="2"/>
  <path d="M224,138 L233,133 L233,143 Z" fill="var(--accent)"/>
  <text x="335" y="153" text-anchor="middle" font-size="10" fill="var(--accent-ink)">reset_at / TTL 到期 → 清冷却回 OK</text>
  <line x1="158" y1="166" x2="158" y2="240" stroke="var(--red)" stroke-width="2"/>
  <path d="M158,244 L153,235 L163,235 Z" fill="var(--red)"/>
  <line x1="190" y1="240" x2="190" y2="170" stroke="var(--muted)" stroke-width="1.6" stroke-dasharray="5 4"/>
  <path d="M190,166 L185,175 L195,175 Z" fill="var(--muted)"/>
  <rect x="266" y="250" width="370" height="88" rx="10" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="282" y="276" font-size="10.5" fill="var(--red)">↓ 401 terminal-auth → DEAD（永久排除）</text>
  <text x="298" y="296" font-size="9.5" fill="var(--muted)">token_revoked · invalid_grant · token_invalidated…</text>
  <text x="282" y="322" font-size="10.5" fill="var(--accent-ink)">↑ 仅重新登录写回 token（sync）才回到 OK</text>
</svg>
<div class="fig-cap"><b>凭证池状态机</b>：失败给 key 盖一个到期戳进 <span class="mono">EXHAUSTED</span>、到 <span class="mono">reset_at</span> / TTL 才回 <span class="mono">OK</span>；401 永久认证失效（<span class="mono">token_revoked…</span>）直接打成 <span class="mono">DEAD</span>，只有重新登录写回 token 才复活——绝不反复戳一个已确认空的 bucket。</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 348" role="img" aria-label="限流冷却时长决策：按触发的 HTTP 状态码分档——401 给 5 分钟、429 给 1 小时、其它默认 1 小时；provider 给的 reset_at 或 retry-after 文本会覆盖这些默认值">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">限流冷却时长 · 按 HTTP 状态分档，provider 文本可覆盖</text>
  <rect x="260" y="44" width="160" height="46" rx="10" fill="var(--panel-2)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="340" y="66" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">HTTP 失败状态码</text>
  <text x="340" y="82" text-anchor="middle" font-size="9" fill="var(--muted)">status_code</text>
  <line x1="340" y1="90" x2="340" y2="103" stroke="var(--muted)" stroke-width="1.6"/>
  <path d="M340,107 L335,98 L345,98 Z" fill="var(--muted)"/>
  <rect x="236" y="107" width="208" height="44" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="340" y="134" text-anchor="middle" font-size="11.5" fill="var(--blue)">_exhausted_ttl(error_code)</text>
  <line x1="318" y1="151" x2="146" y2="192" stroke="var(--amber)" stroke-width="1.6"/>
  <path d="M132,196 L127,187 L137,187 Z" fill="var(--amber)"/>
  <text x="200" y="176" text-anchor="middle" font-size="10" font-weight="700" fill="var(--amber)">== 401</text>
  <line x1="340" y1="151" x2="340" y2="192" stroke="var(--amber)" stroke-width="1.6"/>
  <path d="M340,196 L335,187 L345,187 Z" fill="var(--amber)"/>
  <text x="356" y="176" text-anchor="middle" font-size="10" font-weight="700" fill="var(--amber)">== 429</text>
  <line x1="362" y1="151" x2="534" y2="192" stroke="var(--amber)" stroke-width="1.6"/>
  <path d="M548,196 L543,187 L553,187 Z" fill="var(--amber)"/>
  <text x="480" y="176" text-anchor="middle" font-size="10" font-weight="700" fill="var(--amber)">else</text>
  <rect x="44" y="198" width="176" height="92" rx="10" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="132" y="224" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--amber)">401 · 认证失效</text>
  <text x="132" y="248" text-anchor="middle" font-size="9" fill="var(--muted)">EXHAUSTED_TTL_401_SECONDS</text>
  <text x="132" y="274" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">5 分钟（300s）</text>
  <rect x="252" y="198" width="176" height="92" rx="10" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="340" y="224" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--amber)">429 · 限流</text>
  <text x="340" y="248" text-anchor="middle" font-size="9" fill="var(--muted)">EXHAUSTED_TTL_429_SECONDS</text>
  <text x="340" y="274" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">1 小时（3600s）</text>
  <rect x="460" y="198" width="176" height="92" rx="10" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="548" y="224" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--amber)">402 / 其它失败</text>
  <text x="548" y="248" text-anchor="middle" font-size="9" fill="var(--muted)">EXHAUSTED_TTL_DEFAULT_SECONDS</text>
  <text x="548" y="274" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">1 小时（3600s）</text>
  <rect x="44" y="300" width="592" height="36" rx="10" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="340" y="323" text-anchor="middle" font-size="10.5" fill="var(--accent-ink)">⚡ provider 给的 reset_at 或「retry after / resets in N hr」会覆盖以上默认 TTL</text>
</svg>
<div class="fig-cap"><b>冷却时长决策</b>：<span class="mono">_exhausted_ttl</span> 按触发的状态码分档——401 给 5 分钟、429 与其它给 1 小时；但只要 provider 在响应或报错文本里给了 <span class="mono">reset_at</span> / 「retry after」，就用真实恢复时刻覆盖默认值。</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 372" role="img" aria-label="三种轮换策略对比：同一个含 5 把 key 的池，random 随机取一把、least_used 取请求计数最小的一把、round_robin 取队首再把它移到队尾——三种策略各选中不同的下一把 key">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">轮换策略 · 同一个 5 把 key 的池，三种选法挑出不同「下一把」</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">select() 清掉过期冷却后，按 strategy 从可用集合里挑一把</text>
  <text x="28" y="90" font-size="12" font-weight="700" fill="var(--blue)">random</text>
  <text x="28" y="107" font-size="9" fill="var(--muted)">random.choice(available)</text>
  <rect x="236" y="70" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="269" y="97" text-anchor="middle" font-size="11" fill="var(--ink)">k1</text>
  <rect x="314" y="70" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="347" y="97" text-anchor="middle" font-size="11" fill="var(--ink)">k2</text>
  <rect x="392" y="70" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="425" y="97" text-anchor="middle" font-size="11" fill="var(--ink)">k3</text>
  <rect x="470" y="70" width="66" height="44" rx="8" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="2.5"/>
  <text x="503" y="97" text-anchor="middle" font-size="11" font-weight="700" fill="var(--blue)">k4</text>
  <rect x="548" y="70" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="581" y="97" text-anchor="middle" font-size="11" fill="var(--ink)">k5</text>
  <text x="503" y="130" text-anchor="middle" font-size="9.5" fill="var(--blue)">🎲 随机命中</text>
  <text x="28" y="202" font-size="12" font-weight="700" fill="var(--purple)">least_used</text>
  <text x="28" y="219" font-size="9" fill="var(--muted)">min(request_count)</text>
  <rect x="236" y="182" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="269" y="209" text-anchor="middle" font-size="11" fill="var(--ink)">k1</text>
  <rect x="314" y="182" width="66" height="44" rx="8" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="2.5"/>
  <text x="347" y="209" text-anchor="middle" font-size="11" font-weight="700" fill="var(--purple)">k2</text>
  <rect x="392" y="182" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="425" y="209" text-anchor="middle" font-size="11" fill="var(--ink)">k3</text>
  <rect x="470" y="182" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="503" y="209" text-anchor="middle" font-size="11" fill="var(--ink)">k4</text>
  <rect x="548" y="182" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="581" y="209" text-anchor="middle" font-size="11" fill="var(--ink)">k5</text>
  <text x="269" y="240" text-anchor="middle" font-size="9.5" fill="var(--muted)">req 7</text>
  <text x="347" y="240" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--purple)">req 3</text>
  <text x="425" y="240" text-anchor="middle" font-size="9.5" fill="var(--muted)">req 9</text>
  <text x="503" y="240" text-anchor="middle" font-size="9.5" fill="var(--muted)">req 5</text>
  <text x="581" y="240" text-anchor="middle" font-size="9.5" fill="var(--muted)">req 8</text>
  <text x="347" y="258" text-anchor="middle" font-size="9.5" fill="var(--purple)">↑ 取最小</text>
  <text x="28" y="314" font-size="12" font-weight="700" fill="var(--accent-ink)">round_robin</text>
  <text x="28" y="331" font-size="9" fill="var(--muted)">取队首 → 移到队尾</text>
  <rect x="236" y="294" width="66" height="44" rx="8" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2.5"/>
  <text x="269" y="321" text-anchor="middle" font-size="11" font-weight="700" fill="var(--accent-ink)">k1</text>
  <rect x="314" y="294" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="347" y="321" text-anchor="middle" font-size="11" fill="var(--ink)">k2</text>
  <rect x="392" y="294" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="425" y="321" text-anchor="middle" font-size="11" fill="var(--ink)">k3</text>
  <rect x="470" y="294" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="503" y="321" text-anchor="middle" font-size="11" fill="var(--ink)">k4</text>
  <rect x="548" y="294" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="581" y="321" text-anchor="middle" font-size="11" fill="var(--ink)">k5</text>
  <path d="M269,294 C269,278 600,278 600,290" fill="none" stroke="var(--accent)" stroke-width="1.6" stroke-dasharray="5 4"/>
  <path d="M600,294 L595,285 L605,285 Z" fill="var(--accent)"/>
  <text x="470" y="274" text-anchor="middle" font-size="9.5" fill="var(--accent-ink)">→ 移到队尾</text>
  <text x="269" y="356" text-anchor="middle" font-size="9.5" fill="var(--accent-ink)">↑ 取队首</text>
</svg>
<div class="fig-cap"><b>三种轮换策略</b>：同一个 5 把 key 的池，<span class="mono">random</span> 随机命中一把、<span class="mono">least_used</span> 挑请求计数最小的一把、<span class="mono">round_robin</span> 取队首再把它挪到队尾——各自选中的「下一把」并不相同。</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 392" role="img" aria-label="凭证池逐帧状态快照：anthropic 池含 3 把 key、least_used 策略。T0 三把都健康，选中请求数最小的 #2；#2 撞 HTTP 429 后，T1 进入 EXHAUSTED 冷却、reset_at 为 now 加 3600 秒，available 集合只剩 #1 和 #3；T2 在 available 里改选 #1，#2 被跳过不再戳已确认空的桶；1 小时 TTL 到期后 T3 中 #2 复活回 OK、池恢复 3 把可选。旁注：401 的冷却只有 300 秒；token_revoked 等 terminal-auth 错误直接 DEAD 永不复活。">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">凭证池逐帧快照 · least_used 撞 429 → 冷却 → 跳过 → 复活</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">anthropic 池 3 把 key，沿时间线看同一把 key 如何进出 available 集合</text>
  <text x="600" y="32" text-anchor="middle" font-size="22">🔄</text>
  <rect x="10" y="66" width="122" height="216" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="20" y="86" font-size="9.5" font-weight="700" fill="var(--ink)">T0 · 三把都健康</text>
  <rect x="19" y="98" width="104" height="28" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="27" y="116" font-size="9" fill="var(--ink)">#1  count=12</text>
  <circle cx="115" cy="112" r="4" fill="var(--accent)"/>
  <rect x="19" y="132" width="104" height="28" rx="6" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="2.5"/>
  <text x="27" y="150" font-size="9" font-weight="700" fill="var(--purple)">#2  count=8</text>
  <circle cx="115" cy="146" r="4" fill="var(--accent)"/>
  <rect x="19" y="166" width="104" height="28" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="27" y="184" font-size="9" fill="var(--ink)">#3  count=15</text>
  <circle cx="115" cy="180" r="4" fill="var(--accent)"/>
  <text x="20" y="214" font-size="9" fill="var(--purple)">least_used → 取最小</text>
  <text x="20" y="230" font-size="9" fill="var(--muted)">选中 #2 → count→9</text>
  <text x="20" y="250" font-size="9" fill="var(--muted)">available = {#1,#2,#3}</text>
  <line x1="136" y1="174" x2="184" y2="174" stroke="var(--line)" stroke-width="1.6"/>
  <path d="M190,174 L182,170 L182,178 Z" fill="var(--line)"/>
  <text x="161" y="156" text-anchor="middle" font-size="9" fill="var(--amber)">#2 撞</text>
  <text x="161" y="168" text-anchor="middle" font-size="9" fill="var(--amber)">HTTP 429</text>
  <rect x="190" y="66" width="122" height="216" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="200" y="86" font-size="9.5" font-weight="700" fill="var(--ink)">T1 · #2 冷却</text>
  <rect x="199" y="98" width="104" height="28" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="207" y="116" font-size="9" fill="var(--ink)">#1  count=12</text>
  <circle cx="295" cy="112" r="4" fill="var(--accent)"/>
  <rect x="199" y="132" width="104" height="28" rx="6" fill="var(--amber-soft)" stroke="var(--amber)" stroke-width="2"/>
  <text x="207" y="150" font-size="9" font-weight="700" fill="var(--amber)">#2  EXHAUSTED</text>
  <circle cx="295" cy="146" r="4" fill="var(--amber)"/>
  <rect x="199" y="166" width="104" height="28" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="207" y="184" font-size="9" fill="var(--ink)">#3  count=15</text>
  <circle cx="295" cy="180" r="4" fill="var(--accent)"/>
  <text x="200" y="214" font-size="9" fill="var(--amber)">盖到期戳</text>
  <text x="200" y="230" font-size="9" fill="var(--muted)">reset_at = now+3600s</text>
  <text x="200" y="250" font-size="9" fill="var(--muted)">available = {#1, #3}</text>
  <line x1="316" y1="174" x2="364" y2="174" stroke="var(--line)" stroke-width="1.6"/>
  <path d="M370,174 L362,170 L362,178 Z" fill="var(--line)"/>
  <text x="341" y="156" text-anchor="middle" font-size="9" fill="var(--muted)">下一次</text>
  <text x="341" y="168" text-anchor="middle" font-size="9" fill="var(--muted)">请求</text>
  <rect x="370" y="66" width="122" height="216" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="380" y="86" font-size="9.5" font-weight="700" fill="var(--ink)">T2 · 跳过空桶</text>
  <rect x="379" y="98" width="104" height="28" rx="6" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="2.5"/>
  <text x="387" y="116" font-size="9" font-weight="700" fill="var(--purple)">#1  count=12</text>
  <circle cx="475" cy="112" r="4" fill="var(--accent)"/>
  <rect x="379" y="132" width="104" height="28" rx="6" fill="var(--amber-soft)" stroke="var(--amber)" stroke-width="2"/>
  <text x="387" y="150" font-size="9" fill="var(--amber)">#2  跳过</text>
  <circle cx="475" cy="146" r="4" fill="var(--amber)"/>
  <rect x="379" y="166" width="104" height="28" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="387" y="184" font-size="9" fill="var(--ink)">#3  count=15</text>
  <circle cx="475" cy="180" r="4" fill="var(--accent)"/>
  <text x="380" y="214" font-size="9" fill="var(--purple)">只在 available 里挑</text>
  <text x="380" y="230" font-size="9" fill="var(--muted)">选中 #1 → count→13</text>
  <text x="380" y="250" font-size="9" fill="var(--muted)">不戳已确认空的桶</text>
  <line x1="496" y1="174" x2="544" y2="174" stroke="var(--line)" stroke-width="1.6"/>
  <path d="M550,174 L542,170 L542,178 Z" fill="var(--line)"/>
  <text x="521" y="156" text-anchor="middle" font-size="9" fill="var(--accent-ink)">1h 后</text>
  <text x="521" y="168" text-anchor="middle" font-size="9" fill="var(--accent-ink)">TTL 到期</text>
  <rect x="550" y="66" width="122" height="216" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="560" y="86" font-size="9.5" font-weight="700" fill="var(--ink)">T3 · #2 复活</text>
  <rect x="559" y="98" width="104" height="28" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="567" y="116" font-size="9" fill="var(--ink)">#1  count=13</text>
  <circle cx="655" cy="112" r="4" fill="var(--accent)"/>
  <rect x="559" y="132" width="104" height="28" rx="6" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="567" y="150" font-size="9" font-weight="700" fill="var(--accent-ink)">#2  复活→OK</text>
  <circle cx="655" cy="146" r="4" fill="var(--accent)"/>
  <rect x="559" y="166" width="104" height="28" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="567" y="184" font-size="9" fill="var(--ink)">#3  count=15</text>
  <circle cx="655" cy="180" r="4" fill="var(--accent)"/>
  <text x="560" y="214" font-size="9" fill="var(--accent-ink)">TTL 到期→清冷却</text>
  <text x="560" y="230" font-size="9" fill="var(--muted)">重新进 available</text>
  <text x="560" y="250" font-size="9" fill="var(--muted)">池恢复 3 把可选</text>
  <rect x="10" y="298" width="662" height="86" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="24" y="318" font-size="9.5" font-weight="700" fill="var(--ink)">旁注 · 另两种「退出」与回收</text>
  <circle cx="26" cy="338" r="4" fill="var(--amber)"/>
  <text x="38" y="342" font-size="9" fill="var(--muted)">401（token 问题）→ 冷却只 300s（5min），短于 429 的 3600s</text>
  <circle cx="26" cy="362" r="4" fill="var(--red)"/>
  <text x="38" y="366" font-size="9" fill="var(--muted)">token_revoked / terminal-auth → 直接 DEAD ●，永不复活；重新鉴权同步才清，手动 DEAD 24h 后 prune</text>
</svg>
<div class="fig-cap"><b>逐帧状态快照</b>：同一把 key 沿时间线走完「健康 → 撞 <span class="mono">429</span> → <span class="mono">EXHAUSTED</span> 冷却 → 被跳过 → <span class="mono">reset_at</span> 到期复活」；<span class="mono">least_used</span> 每帧只在 available 集合里挑请求数最小的一把，绝不反复戳一个已确认空的 bucket。</div>
</div>

<h3>🔬 27.2 · 副 LLM 路由：每个副任务各走各的解析链</h3>
<p>主对话之外，Hermes 还跑着一大批<strong>副 LLM 任务</strong>——上下文压缩、视觉识图、网页提取、起标题、技能维护（curator）……每一项都是一次<strong>独立的模型调用</strong>，全部走同一个入口 <span class="mono">agent/auxiliary_client.py</span> 的 <span class="mono">_resolve_auto()</span>。它要做的不是「随便抓个能用的模型」，而是按一条<strong>三段解析链</strong>，把每个副任务路由到「最合适的 provider + model」。</p>
<p><strong>① 先用你当前的主 provider + 主 model。</strong>关键是用<strong>运行期</strong>的那一份，而不是 <span class="mono">config.yaml</span> 里可能已经陈旧的默认值：每轮开头由 <span class="mono">set_runtime_main()</span> 把 CLI / 网关临时切到的 provider、model、<span class="mono">base_url</span>、key 同步进来，副任务于是跟主对话用<strong>同一个模型、同一把已验证可用的 key</strong>，行为可预期，不会偷偷掉到某个便宜的默认模型。举个会咬人的场景：你这一会话用 <span class="mono">hermes model</span> 临时切到了另一个 provider，若没有这步运行期同步，副任务仍会按 <span class="mono">config.yaml</span> 里那份旧 provider 去发请求——要么打到错的端点，要么用了你已经不想再用的账号。<strong>② 主 provider 不可用时</strong>，先查该任务自己的 <span class="mono">auxiliary.&lt;task&gt;.fallback_chain</span>，再查主 agent 顶层的 fallback 策略。<strong>③ 都没命中</strong>，才走那条硬编码的 discovery 链：<span class="mono">openrouter → nous → local/custom → api-key</span>。</p>
<p>三个真实的坑必须记住。第一，<strong>per-task pinning 是真的</strong>：每个副任务都能在 <span class="mono">auxiliary.&lt;task&gt;</span> 下<strong>各自钉死</strong> <span class="mono">provider</span> 与 <span class="mono">model</span>——压缩钉一个、视觉钉另一个、起标题再钉第三个，互不干扰。第二，<strong>402 / 额度错误会把 provider 标成 unhealthy 藏一段时间</strong>：命中付费或额度耗尽时，<span class="mono">_mark_provider_unhealthy()</span> 给它盖一个到期戳，默认藏 <span class="mono">_AUX_UNHEALTHY_TTL_SECONDS = 600</span>（10 分钟）；这段时间内第 ① 步与第 ③ 步都直接<strong>跳过</strong>它，免得每次副调用都先白撞一个必败的 402，到点自动恢复、充值后无需手动干预。第三，<strong>通用 fallback 链可能静默选了一个更便宜 / 不同的模型</strong>——它只保证「找得到能用的」，不保证「和你主模型同款」；要避免，就把该任务<strong>显式钉死</strong>。举个具体的：视觉任务若被静默落到一个只有文本的便宜模型上，每次看图都会 404——这正是该把 <span class="mono">vision</span> 单独钉死的理由。</p>
<p>还有一个刻意的取舍：discovery 链里<strong>故意不含 Codex</strong>。ChatGPT 账号版的 Codex 端点只认一份不断变动、未公开的 model 白名单，拿一个猜的 model 去回退反而更易失败——所以 Codex 只在你的<strong>主 provider 本身就是</strong> <span class="mono">openai-codex</span>、或调用方显式带上 model 时才用。（顺带一提：<span class="mono">session_search</span> 自 PR #27590 起已不再走副 LLM，工具直接返回库内容，故不在下方矩阵内。）</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">agent/auxiliary_client.py:3322 · 简化</span></div><pre>def _resolve_auto(main_runtime=None, task=None):        # abridged
    # ... normalize runtime (set_runtime_main records base_url / key)
    # ── Step 1: main provider + main model → use them directly ──
    main_provider = str(runtime_provider or _read_main_provider() or "")
    main_model = str(runtime_model or _read_main_model() or "")
    if (main_provider and main_model
            and main_provider not in {"auto", ""}):
        main_chain_label = _normalize_chain_label(main_provider)
        if main_chain_label and _is_provider_unhealthy(main_chain_label):
            _log_skip_unhealthy(main_chain_label)        # just 402'd -&gt; skip
        else:
            client, resolved = resolve_provider_client(main_provider, main_model, ...)
            if client is not None:
                return client, resolved or main_model    # (1) main provider+model

    # ── Step 2: user-configured fallback policy ──
    if task:
        fb_client, fb_model, _ = _try_configured_fallback_chain(task, ...)  # auxiliary.&lt;task&gt;.fallback_chain
        if fb_client is not None:
            return fb_client, fb_model
    fb_client, fb_model, _ = _try_main_fallback_chain(task, ...)            # top-level fallback
    if fb_client is not None:
        return fb_client, fb_model                       # (2) configured fallback

    # ── Step 3: aggregator / fallback chain ──
    for label, try_fn in _get_provider_chain():          # openrouter → nous → local/custom → api-key
        if _is_provider_unhealthy(label):
            _log_skip_unhealthy(label)                   # 402/credit -&gt; hidden 10 min, skip
            continue
        client, model = try_fn()
        if client is not None:
            return client, model                         # (3) discovery chain
    return None, None</pre></div>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">agent/auxiliary_client.py:2325 · 简化</span></div><pre>def _get_provider_chain() -&gt; List[tuple]:
    &quot;&quot;&quot;Return the ordered provider detection chain.  ... (abridged)

    NOTE: ``openai-codex`` is deliberately NOT in this chain.  The
    ChatGPT-account Codex endpoint only accepts a shifting, undocumented
    allow-list of model IDs, so falling back to it with a guessed model
    fails more often than not.  Codex is used only when the user's main
    provider *is* openai-codex (see Step 1 of ``_resolve_auto``) or when
    a caller explicitly requests it with a model.&quot;&quot;&quot;
    return [
        ("openrouter", _try_openrouter),
        ("nous", _try_nous),
        ("local/custom", _try_custom_endpoint),
        ("api-key", _resolve_api_key_provider),
    ]</pre></div>

<div class="figure">
<svg viewBox="0 0 680 436" role="img" aria-label="副 LLM 路由决策树：副任务请求依次尝试第一段主 provider 加主 model、第二段任务级 fallback_chain 与顶层 fallback、第三段硬编码 discovery 链 openrouter 到 nous 到 local/custom 到 api-key，任一段命中即返回选定的 provider 与 model；命中 unhealthy 的 provider（402 或额度耗尽）会被盖到期戳藏 10 分钟并跳过">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">副 LLM 路由决策树 · 三段解析，按序命中即返回</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">每个副任务独立走一遍；命中 unhealthy 的 provider 直接跳过</text>
  <rect x="44" y="58" width="280" height="32" rx="10" fill="var(--panel-2)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="184" y="79" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">副任务请求（压缩 / 视觉 / 起标题…）</text>
  <line x1="184" y1="90" x2="184" y2="104" stroke="var(--muted)" stroke-width="1.6"/>
  <path d="M184,108 L179,99 L189,99 Z" fill="var(--muted)"/>
  <rect x="44" y="110" width="280" height="76" rx="12" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="60" y="135" font-size="12.5" font-weight="700" fill="var(--accent-ink)">① 主 provider + 主 model</text>
  <text x="60" y="155" font-size="9.5" fill="var(--muted)">set_runtime_main() 同步运行期 base_url / key</text>
  <text x="60" y="173" font-size="9.5" fill="var(--ink)">命中即用主对话同款模型，行为可预期</text>
  <line x1="184" y1="186" x2="184" y2="200" stroke="var(--muted)" stroke-width="1.6"/>
  <path d="M184,204 L179,195 L189,195 Z" fill="var(--muted)"/>
  <text x="200" y="199" font-size="9" fill="var(--red)">未命中 / 主刚 402 被藏</text>
  <rect x="44" y="204" width="280" height="72" rx="12" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="2"/>
  <text x="60" y="228" font-size="12.5" font-weight="700" fill="var(--blue)">② 配置的回退策略</text>
  <text x="60" y="248" font-size="9" fill="var(--muted)">auxiliary.&lt;task&gt;.fallback_chain（任务级）</text>
  <text x="60" y="265" font-size="9" fill="var(--muted)">→ 主 agent 顶层 fallback（兜底策略）</text>
  <line x1="184" y1="276" x2="184" y2="288" stroke="var(--muted)" stroke-width="1.6"/>
  <path d="M184,292 L179,283 L189,283 Z" fill="var(--muted)"/>
  <text x="200" y="289" font-size="9" fill="var(--muted)">未命中</text>
  <rect x="44" y="292" width="592" height="128" rx="12" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="2"/>
  <text x="60" y="316" font-size="12.5" font-weight="700" fill="var(--purple)">③ discovery 链 · 硬编码兜底（Codex 不在内）</text>
  <rect x="64" y="328" width="116" height="40" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="122" y="349" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--ink)">openrouter</text>
  <text x="122" y="362" text-anchor="middle" font-size="9" fill="var(--muted)">聚合器</text>
  <text x="190" y="352" text-anchor="middle" font-size="12" fill="var(--purple)">→</text>
  <rect x="200" y="328" width="116" height="40" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="258" y="349" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--ink)">nous</text>
  <text x="258" y="362" text-anchor="middle" font-size="9" fill="var(--muted)">Nous</text>
  <text x="326" y="352" text-anchor="middle" font-size="12" fill="var(--purple)">→</text>
  <rect x="336" y="328" width="116" height="40" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="394" y="349" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--ink)">local/custom</text>
  <text x="394" y="362" text-anchor="middle" font-size="9" fill="var(--muted)">本地 / 自建</text>
  <text x="462" y="352" text-anchor="middle" font-size="12" fill="var(--purple)">→</text>
  <rect x="472" y="328" width="116" height="40" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="530" y="349" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--ink)">api-key</text>
  <text x="530" y="362" text-anchor="middle" font-size="9" fill="var(--muted)">直连 key</text>
  <rect x="52" y="376" width="536" height="34" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="64" y="397" font-size="9.5" fill="var(--red)">✗ 命中 unhealthy 的 provider（刚吃 402 / 额度耗尽）→ 盖到期戳藏 10 分钟，本轮跳到下一个</text>
  <rect x="430" y="120" width="210" height="120" rx="12" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="535" y="164" text-anchor="middle" font-size="15" font-weight="700" fill="var(--accent-ink)">✓ 选定</text>
  <text x="535" y="189" text-anchor="middle" font-size="11.5" fill="var(--ink)">provider + model</text>
  <text x="535" y="212" text-anchor="middle" font-size="9" fill="var(--muted)">交给该副任务发起调用</text>
  <line x1="324" y1="148" x2="427" y2="160" stroke="var(--accent)" stroke-width="1.8"/>
  <path d="M430,161 L421,158 L423,168 Z" fill="var(--accent)"/>
  <text x="372" y="142" text-anchor="middle" font-size="9" fill="var(--accent-ink)">命中 ✓</text>
  <line x1="324" y1="240" x2="427" y2="214" stroke="var(--accent)" stroke-width="1.8"/>
  <path d="M430,213 L421,212 L424,222 Z" fill="var(--accent)"/>
  <text x="372" y="244" text-anchor="middle" font-size="9" fill="var(--accent-ink)">命中 ✓</text>
  <line x1="600" y1="292" x2="574" y2="244" stroke="var(--accent)" stroke-width="1.8"/>
  <path d="M572,240 L569,250 L578,247 Z" fill="var(--accent)"/>
  <text x="606" y="280" text-anchor="middle" font-size="9" fill="var(--accent-ink)">命中 ✓</text>
</svg>
<div class="fig-cap"><b>路由决策树</b>：副任务请求按 ① 主 provider+model → ② 任务级 <span class="mono">fallback_chain</span> 与顶层 fallback → ③ 硬编码 discovery 链（<span class="mono">openrouter→nous→local/custom→api-key</span>）依次解析，任一段命中即返回；命中 unhealthy 的 provider（402 / 额度）会被藏 10 分钟并跳过，避免每次副调用都白撞一个必败请求。</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 352" role="img" aria-label="副 LLM per-task 路由矩阵：行是各副任务 compression、vision、web_extract、title_generation、curator，每个任务都能在 config.yaml 的 auxiliary 任务块下各自钉住 provider 与 model，不同任务可指向不同模型；不配则为 auto，共同兜底 openrouter google gemini-3-flash-preview">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">per-task 路由矩阵 · 每个副任务各自 pin provider 与 model</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">在 config.yaml 的 auxiliary.&lt;task&gt; 下钉死；不配 = auto（= 主对话模型）</text>
  <rect x="40" y="60" width="600" height="34" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="52" y="82" font-size="11" font-weight="700" fill="var(--accent-ink)">副任务</text>
  <text x="172" y="82" font-size="10" font-weight="700" fill="var(--accent-ink)">provider · 可 pin</text>
  <text x="322" y="82" font-size="10" font-weight="700" fill="var(--accent-ink)">model · 可 pin</text>
  <text x="532" y="82" font-size="10" font-weight="700" fill="var(--accent-ink)">典型用途</text>
  <rect x="40" y="94" width="600" height="40" fill="var(--panel)"/>
  <rect x="40" y="134" width="600" height="40" fill="var(--panel-2)"/>
  <rect x="40" y="174" width="600" height="40" fill="var(--panel)"/>
  <rect x="40" y="214" width="600" height="40" fill="var(--panel-2)"/>
  <rect x="40" y="254" width="600" height="40" fill="var(--panel)"/>
  <text x="52" y="119" font-size="10.5" font-weight="700" fill="var(--ink)">compression</text>
  <text x="172" y="119" font-size="10" fill="var(--accent-ink)">openrouter</text>
  <text x="322" y="119" font-size="9.5" fill="var(--accent-ink)">google/gemini-3-flash-preview</text>
  <text x="532" y="119" font-size="9" fill="var(--muted)">压缩长上下文</text>
  <text x="52" y="159" font-size="10.5" font-weight="700" fill="var(--ink)">vision</text>
  <text x="172" y="159" font-size="10" fill="var(--accent-ink)">openrouter</text>
  <text x="322" y="159" font-size="9.5" fill="var(--accent-ink)">google/gemini-2.5-flash</text>
  <text x="532" y="159" font-size="9" fill="var(--muted)">看图 / 多模态</text>
  <text x="52" y="199" font-size="10.5" font-weight="700" fill="var(--ink)">web_extract</text>
  <text x="172" y="199" font-size="10" fill="var(--accent-ink)">nous</text>
  <text x="322" y="199" font-size="9.5" fill="var(--muted)">（provider 默认）</text>
  <text x="532" y="199" font-size="9" fill="var(--muted)">网页正文摘要</text>
  <text x="52" y="239" font-size="10.5" font-weight="700" fill="var(--ink)">title_generation</text>
  <text x="172" y="239" font-size="10" fill="var(--accent-ink)">openrouter</text>
  <text x="322" y="239" font-size="9.5" fill="var(--accent-ink)">google/gemini-3-flash-preview</text>
  <text x="532" y="239" font-size="9" fill="var(--muted)">会话起标题</text>
  <text x="52" y="279" font-size="10.5" font-weight="700" fill="var(--ink)">curator</text>
  <text x="172" y="279" font-size="10" fill="var(--muted)">auto</text>
  <text x="322" y="279" font-size="9.5" fill="var(--muted)">（= 主对话模型）</text>
  <text x="532" y="279" font-size="9" fill="var(--muted)">技能维护复盘</text>
  <line x1="160" y1="60" x2="160" y2="294" stroke="var(--line)" stroke-width="1"/>
  <line x1="310" y1="60" x2="310" y2="294" stroke="var(--line)" stroke-width="1"/>
  <line x1="520" y1="60" x2="520" y2="294" stroke="var(--line)" stroke-width="1"/>
  <rect x="40" y="304" width="600" height="34" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="340" y="325" text-anchor="middle" font-size="9.5" fill="var(--blue)">▸ 示意值：任一任务不 pin 则走 _resolve_auto 三段链，共同兜底 openrouter:google/gemini-3-flash-preview</text>
</svg>
<div class="fig-cap"><b>per-task 路由矩阵</b>：每个副任务都能在 <span class="mono">auxiliary.&lt;task&gt;.provider</span> / <span class="mono">.model</span> 下各自钉住，不同任务可指向不同模型（图中为示意值）；不 pin 则为 <span class="mono">auto</span>，共同兜底 <span class="mono">openrouter:google/gemini-3-flash-preview</span>。</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 402" role="img" aria-label="副 LLM 路由逐帧解析快照：一次 compression 副任务请求走 _resolve_auto 三段解析。帧1 试主 provider 加主 model（示意 anthropic 加 claude-opus），该 model 对副任务不可用，结果 MISS，触发主不可用转下一段。帧2 试任务级 auxiliary.compression.fallback_chain，此例为空、顶层 fallback 也未命中，结果 MISS，触发链耗尽转 discovery。帧3 按 openrouter 到 nous 到 local/custom 到 api-key 顺序探测，第一个健康的 openrouter 命中、其余三项未触达，结果 HIT。旁注：命中 unhealthy 的 provider（402 或额度耗尽）被盖到期戳藏 600 秒即 10 分钟，TTL 内后续请求直接跳过；走这条独立解析的副任务槽有 compression、vision、web_extract、title_generation、curator，各自钉自己的 provider 与 model。">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">副 LLM 路由逐帧解析 · 一次 compression 请求逐段 MISS→HIT</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">沿时间看同一次请求如何在三段链上逐段未命中，最终在 discovery 命中</text>
  <text x="600" y="34" text-anchor="middle" font-size="24">🎞️</text>
  <rect x="10" y="70" width="188" height="230" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="20" y="88" font-size="9.5" font-weight="700" fill="var(--accent-ink)">帧1 · 试 主 provider+model</text>
  <text x="20" y="102" font-size="9" fill="var(--muted)">set_runtime_main 记录的主配置</text>
  <rect x="19" y="110" width="170" height="56" rx="6" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>
  <text x="28" y="130" font-size="9" fill="var(--ink)">provider = anthropic</text>
  <text x="28" y="148" font-size="9" fill="var(--ink)">model = claude-opus</text>
  <text x="28" y="163" font-size="9" fill="var(--muted)">主对话同款 · 运行期同步</text>
  <text x="20" y="186" font-size="9" fill="var(--ink)">判定：该 model 对副任务</text>
  <text x="20" y="200" font-size="9" fill="var(--ink)">不可用（plan-only / 不合适）</text>
  <rect x="19" y="224" width="170" height="58" rx="8" fill="var(--red-soft)" stroke="var(--red)" stroke-width="2"/>
  <text x="34" y="252" font-size="16" font-weight="700" fill="var(--red)">✗</text>
  <text x="54" y="251" font-size="11" font-weight="700" fill="var(--red)">MISS</text>
  <text x="34" y="271" font-size="9" fill="var(--red)">主不可用</text>
  <line x1="200" y1="190" x2="242" y2="190" stroke="var(--line)" stroke-width="1.6"/>
  <path d="M246,190 L238,186 L238,194 Z" fill="var(--line)"/>
  <text x="221" y="171" text-anchor="middle" font-size="9" fill="var(--red)">主不可用</text>
  <text x="221" y="182" text-anchor="middle" font-size="9" fill="var(--red)">→ 下一段</text>
  <rect x="246" y="70" width="188" height="230" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="256" y="88" font-size="9.5" font-weight="700" fill="var(--blue)">帧2 · 试任务级 fallback_chain</text>
  <text x="256" y="102" font-size="9" fill="var(--muted)">auxiliary.compression 任务块</text>
  <rect x="255" y="110" width="170" height="56" rx="6" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="264" y="130" font-size="9" fill="var(--ink)">fallback_chain:</text>
  <text x="264" y="148" font-size="9" fill="var(--muted)">[ ]  ← 未配 / 空</text>
  <text x="264" y="163" font-size="9" fill="var(--muted)">顶层 fallback 也未命中</text>
  <text x="256" y="186" font-size="9" fill="var(--ink)">判定：本任务无可用的</text>
  <text x="256" y="200" font-size="9" fill="var(--ink)">回退候选</text>
  <rect x="255" y="224" width="170" height="58" rx="8" fill="var(--red-soft)" stroke="var(--red)" stroke-width="2"/>
  <text x="270" y="252" font-size="16" font-weight="700" fill="var(--red)">✗</text>
  <text x="290" y="251" font-size="11" font-weight="700" fill="var(--red)">MISS</text>
  <text x="270" y="271" font-size="9" fill="var(--red)">链为空</text>
  <line x1="436" y1="190" x2="478" y2="190" stroke="var(--line)" stroke-width="1.6"/>
  <path d="M482,190 L474,186 L474,194 Z" fill="var(--line)"/>
  <text x="458" y="171" text-anchor="middle" font-size="9" fill="var(--red)">链耗尽</text>
  <text x="458" y="182" text-anchor="middle" font-size="9" fill="var(--red)">→ discovery</text>
  <rect x="482" y="70" width="188" height="230" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="492" y="88" font-size="9.5" font-weight="700" fill="var(--purple)">帧3 · discovery 顺序探测</text>
  <text x="492" y="102" font-size="9" fill="var(--muted)">逐个探测，第一个健康即命中</text>
  <rect x="491" y="110" width="170" height="22" rx="5" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="500" y="125" font-size="9" font-weight="700" fill="var(--accent-ink)">openrouter</text>
  <text x="652" y="125" text-anchor="end" font-size="12" fill="var(--accent)">✓</text>
  <rect x="491" y="134" width="170" height="22" rx="5" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="500" y="149" font-size="9" fill="var(--muted)">nous</text>
  <text x="652" y="149" text-anchor="end" font-size="9" fill="var(--muted)">未触达</text>
  <rect x="491" y="158" width="170" height="22" rx="5" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="500" y="173" font-size="9" fill="var(--muted)">local/custom</text>
  <text x="652" y="173" text-anchor="end" font-size="9" fill="var(--muted)">未触达</text>
  <rect x="491" y="182" width="170" height="22" rx="5" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="500" y="197" font-size="9" fill="var(--muted)">api-key</text>
  <text x="652" y="197" text-anchor="end" font-size="9" fill="var(--muted)">未触达</text>
  <rect x="491" y="224" width="170" height="58" rx="8" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="506" y="252" font-size="16" font-weight="700" fill="var(--accent)">✓</text>
  <text x="526" y="251" font-size="11" font-weight="700" fill="var(--accent-ink)">HIT</text>
  <text x="506" y="271" font-size="9" fill="var(--accent-ink)">openrouter 命中</text>
  <rect x="10" y="312" width="660" height="80" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="24" y="332" font-size="9.5" font-weight="700" fill="var(--ink)">旁注 · 两条独立解析的事实</text>
  <circle cx="26" cy="352" r="4" fill="var(--red)"/>
  <text x="38" y="356" font-size="9" fill="var(--muted)">命中 unhealthy 的 provider（402 / 额度耗尽）→ 盖到期戳藏 600s（10min），TTL 内后续请求直接跳过，不再白撞必败请求</text>
  <circle cx="26" cy="376" r="4" fill="var(--purple)"/>
  <text x="38" y="380" font-size="9" fill="var(--muted)">走这条独立解析的副任务槽：compression / vision / web_extract / title_generation / curator（各自钉 provider / model）</text>
</svg>
<div class="fig-cap"><b>逐帧解析快照</b>：一次 <span class="mono">compression</span> 请求沿时间看三段链——帧1 主 <span class="mono">provider+model</span> 对副任务不可用（MISS）→ 帧2 任务级 <span class="mono">fallback_chain</span> 为空（MISS）→ 帧3 <span class="mono">discovery</span> 顺序探测，<span class="mono">openrouter</span> 第一个健康即命中（HIT）。unhealthy 的 provider 被藏 <span class="mono">600s（10min）</span>，TTL 内跳过。</div>
</div>

<h3>🔬 27.3 · 上下文窗口：先分层解析，再算压缩阈值</h3>
<p>压缩的触发，靠的从来不是「用到 X% 就压」这么一个写死的百分比——前提是你<strong>先得知道这个模型的窗口到底多大</strong>。可「窗口多大」对同一个 model 名往往众说纷纭：用户在 <span class="mono">config.yaml</span> 里覆盖过、上次探测的值缓存在磁盘上、provider 的 <span class="mono">/models</span> 接口能报、<span class="mono">models.dev</span> 有登记、本地 server 能查、再不行还有按模型家族猜的硬编码默认。<span class="mono">agent/model_metadata.py</span> 的 <span class="mono">get_model_context_length()</span> 把这些来源排成一条<strong>分层解析链</strong>，自上而下、命中即返回。</p>
<p>解析顺序（节选自其 docstring 的 resolution order）是：<strong>⓪ 显式 config 覆盖</strong>（<span class="mono">model.context_length</span> 或自定义 provider 的 per-model 设置，用户最清楚自己的端点）→ <strong>① 持久缓存</strong>（上次探测落盘的值）→ <strong>①b AWS Bedrock 静态表</strong> → <strong>② 自定义端点 /models 元数据</strong> → <strong>③ 本地 server 查询</strong> → <strong>④ Anthropic /v1/models</strong>（仅 API-key、不含 OAuth）→ <strong>⑤ provider 感知探测</strong>（Copilot、Nous live、Codex OAuth、GMI、Ollama、<span class="mono">models.dev</span>）→ <strong>⑥ OpenRouter live 元数据</strong>（带 Kimi 32k 守卫）→ <strong>⑦ 硬编码默认</strong>（按模型家族、最长键优先）→ <strong>⑧ 本地 server 兜底</strong> → <strong>⑨ 默认 256K</strong>。</p>
<p>这里最锋利的坑，是<strong>「缓存可能是陈旧的、对某些 provider 必须主动跳过」</strong>。缓存本是优化——一次探测、长期复用；可有几类 provider 的窗口要么会变、要么曾被错误落盘，盲信缓存就把窗口算错：<strong>LM Studio</strong> 的已加载上下文是<strong>瞬态</strong>的（用户随时能用别的 <span class="mono">context_length</span> 重载模型），所以它<strong>整段跳过持久缓存</strong>；<strong>Nous</strong> 的 URL 在缓存这步直接 bypass，永远以门户 <span class="mono">/v1/models</span> 为准；<strong>Codex</strong> OAuth 对每个 slug 都封顶 272K，凡缓存里 ≥ 400K 的都是旧解析路径留下的脏值，丢弃重探；<strong>Kimi</strong> 系 ≤ 32768 的缓存是 OpenRouter 的低报，<strong>MiniMax-M3</strong> ≤ 204800、<strong>Grok-4.3</strong> ≤ 256000 则都是「catalog 收录新值之前」落盘的旧值——这三者一律丢弃、回落到硬编码默认（它们其实都是 1M）。一句话：<strong>缓存命中 ≠ 可信，边角 provider 要先验真。</strong></p>
<p>窗口一旦解析出来，<span class="mono">agent/context_compressor.py</span> 的 <span class="mono">_compute_threshold_tokens()</span> 才算<strong>触发阈值</strong>。它不是简单的「窗口 × 50%」，而是三步：① 基准 = <strong>有效输入预算 × <span class="mono">threshold_percent</span></strong>（默认 <strong>0.50</strong>）；② 用 <strong><span class="mono">MINIMUM_CONTEXT_LENGTH</span> = 64K</strong> 做 floor，免得大窗口模型在 50% 就过早压缩；③ 但这个 floor 在<strong>小窗口</strong>会退化：一个 64K 的本地模型，<span class="mono">max(0.5×64000, 64000) == 64000</span> 让阈值等于<strong>整个窗口</strong>，自动压缩永远触发不了——provider 会在用量到 100% 之前就拒掉请求。所以当 floor ≥ 窗口时，改在 <strong><span class="mono">_MIN_CTX_TRIGGER_RATIO</span> = 85%</strong> 处触发。还有一层：provider 会从同一个窗口里<strong>预留 <span class="mono">max_tokens</span> 的输出空间</strong>，所以真正可用的<strong>输入</strong>预算是 <span class="mono">context_length − max_tokens</span>——百分比和退化判断都跑在这个「有效输入预算」上，否则一个大 <span class="mono">max_tokens</span>（如自定义 provider 的 65536）会让会话在压缩前就先撞 provider 的 400。阈值只决定<strong>何时</strong>该压；触发之后<strong>怎么压</strong>——保护首尾、摘要中段、重建缓存——是<strong>第 15 章</strong>的主题。</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">agent/context_compressor.py:742 · 简化</span></div><pre>def _compute_threshold_tokens(
    context_length: int, threshold_percent: float, max_tokens: int | None = None,
) -&gt; int:
    &quot;&quot;&quot;Compute the compaction trigger threshold in tokens.

    The base value is ``effective_input_budget * threshold_percent``, floored
    at ``MINIMUM_CONTEXT_LENGTH`` so large-context models don't compress
    prematurely at 50%. ...（docstring 略：#14690 退化窗口 / #43547 max_tokens 预留）
    &quot;&quot;&quot;
    effective_window = context_length - (max_tokens or 0)   # 扣掉输出预留
    if effective_window &lt;= 0:
        effective_window = context_length
    pct_value = int(effective_window * threshold_percent)   # 默认 0.50
    floored = max(pct_value, MINIMUM_CONTEXT_LENGTH)        # 64_000 floor
    # If flooring pushed the threshold to/over the effective window it can
    # never be reached. Trigger at 85% of the effective input budget so a
    # minimum-context model rides most of its budget before compacting
    # instead of wasting half.
    if effective_window &gt; 0 and floored &gt;= effective_window:
        return max(1, min(int(effective_window * ContextCompressor._MIN_CTX_TRIGGER_RATIO),
                          effective_window - 1))
    return floored</pre></div>

<div class="figure">
<svg viewBox="0 0 680 446" role="img" aria-label="上下文窗口分层解析瀑布图：自上而下依次为 config 覆盖、持久缓存、provider 逐个探测（Bedrock、自定义端点、本地、Anthropic、Codex、Nous、OpenRouter、models.dev）、硬编码默认兜底 256K，任一层解析出值即短路返回；右侧标注某些 provider 必须 bypass 陈旧缓存，包括 LM Studio、Nous、Codex、Kimi、MiniMax、Grok">
  <text x="20" y="24" font-size="13.5" font-weight="700" fill="var(--ink)">上下文窗口分层解析 · 自上而下，命中即短路返回</text>
  <text x="20" y="44" font-size="10.5" fill="var(--muted)">get_model_context_length()：同一个 model 名，窗口大小可能来自任一层</text>
  <line x1="30" y1="79" x2="30" y2="384" stroke="var(--accent)" stroke-width="1.6"/>
  <path d="M30,392 L25,382 L35,382 Z" fill="var(--accent)"/>
  <text x="38" y="74" font-size="9" font-weight="700" fill="var(--accent-ink)">✓ 命中→返回</text>
  <rect x="58" y="60" width="320" height="38" rx="9" fill="var(--panel)" stroke="var(--purple)" stroke-width="1.5"/>
  <text x="70" y="80" font-size="12" font-weight="700" fill="var(--purple)">⓪ config 覆盖（最高优先）</text>
  <text x="70" y="93" font-size="9" fill="var(--muted)">model.context_length · 自定义 provider per-model</text>
  <line x1="58" y1="79" x2="34" y2="79" stroke="var(--accent)" stroke-width="1.4"/>
  <path d="M30,79 L39,74 L39,84 Z" fill="var(--accent)"/>
  <line x1="218" y1="98" x2="218" y2="109" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M218,112 L213,103 L223,103 Z" fill="var(--muted)"/>
  <text x="228" y="109" font-size="9" fill="var(--red)">未命中</text>
  <rect x="58" y="112" width="320" height="38" rx="9" fill="var(--panel)" stroke="var(--purple)" stroke-width="1.5"/>
  <text x="70" y="132" font-size="12" font-weight="700" fill="var(--purple)">① 持久缓存（曾探测落盘）</text>
  <text x="70" y="145" font-size="9" fill="var(--muted)">Nous URL 在此跳过，以门户 /v1/models 为准</text>
  <line x1="58" y1="131" x2="34" y2="131" stroke="var(--accent)" stroke-width="1.4"/>
  <path d="M30,131 L39,126 L39,136 Z" fill="var(--accent)"/>
  <line x1="218" y1="150" x2="218" y2="161" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M218,164 L213,155 L223,155 Z" fill="var(--muted)"/>
  <text x="228" y="161" font-size="9" fill="var(--red)">未命中</text>
  <rect x="58" y="164" width="320" height="142" rx="9" fill="var(--panel)" stroke="var(--purple)" stroke-width="1.5"/>
  <text x="70" y="183" font-size="11.5" font-weight="700" fill="var(--purple)">②–⑥ provider 逐个探测（按序）</text>
  <rect x="66" y="194" width="68" height="30" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="100" y="213" text-anchor="middle" font-size="9" fill="var(--ink)">Bedrock</text>
  <rect x="142" y="194" width="68" height="30" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="176" y="213" text-anchor="middle" font-size="9" fill="var(--ink)">自定义端点</text>
  <rect x="218" y="194" width="68" height="30" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="252" y="213" text-anchor="middle" font-size="9" fill="var(--ink)">本地探测</text>
  <rect x="294" y="194" width="68" height="30" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="328" y="213" text-anchor="middle" font-size="9" fill="var(--ink)">Anthropic</text>
  <rect x="66" y="230" width="68" height="30" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="100" y="249" text-anchor="middle" font-size="9" fill="var(--ink)">Codex</text>
  <rect x="142" y="230" width="68" height="30" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="176" y="249" text-anchor="middle" font-size="9" fill="var(--ink)">Nous</text>
  <rect x="218" y="230" width="68" height="30" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="252" y="249" text-anchor="middle" font-size="9" fill="var(--ink)">OpenRouter</text>
  <rect x="294" y="230" width="68" height="30" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="328" y="249" text-anchor="middle" font-size="9" fill="var(--ink)">models.dev</text>
  <text x="70" y="280" font-size="9" fill="var(--muted)">探测成功即落盘缓存（LM Studio / Nous 除外，故下次仍重探）</text>
  <text x="70" y="296" font-size="9" fill="var(--muted)">⑥ OpenRouter 带 Kimi 32k 守卫，避免低报覆盖真实窗口</text>
  <line x1="58" y1="235" x2="34" y2="235" stroke="var(--accent)" stroke-width="1.4"/>
  <path d="M30,235 L39,230 L39,240 Z" fill="var(--accent)"/>
  <line x1="218" y1="306" x2="218" y2="317" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M218,320 L213,311 L223,311 Z" fill="var(--muted)"/>
  <text x="228" y="317" font-size="9" fill="var(--red)">未命中</text>
  <rect x="58" y="320" width="320" height="42" rx="9" fill="var(--panel-2)" stroke="var(--purple)" stroke-width="1.5"/>
  <text x="70" y="340" font-size="12" font-weight="700" fill="var(--purple)">⑦–⑨ 硬编码默认 → 兜底 256K</text>
  <text x="70" y="354" font-size="9" fill="var(--muted)">按模型家族、最长键优先；都不中则 DEFAULT_FALLBACK_CONTEXT</text>
  <line x1="58" y1="341" x2="34" y2="341" stroke="var(--accent)" stroke-width="1.4"/>
  <path d="M30,341 L39,336 L39,346 Z" fill="var(--accent)"/>
  <rect x="406" y="112" width="250" height="96" rx="10" fill="var(--amber-soft)" stroke="var(--amber)" stroke-width="1.5"/>
  <text x="418" y="132" font-size="10" font-weight="700" fill="var(--ink)">⚠ 边角 provider 须 bypass 陈旧缓存</text>
  <text x="418" y="151" font-size="9" fill="var(--muted)">缓存命中 ≠ 可信：窗口会变 / 曾错写</text>
  <text x="418" y="170" font-size="9.5" fill="var(--ink)">LM Studio · Nous · Codex</text>
  <text x="418" y="188" font-size="9.5" fill="var(--ink)">Kimi · MiniMax · Grok</text>
  <text x="418" y="202" font-size="9" fill="var(--amber)">→ 丢弃旧值、重新探测</text>
  <line x1="406" y1="140" x2="382" y2="133" stroke="var(--amber)" stroke-width="1.4"/>
  <path d="M378,132 L388,130 L385,139 Z" fill="var(--amber)"/>
  <rect x="24" y="384" width="632" height="42" rx="10" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="44" y="404" font-size="11" font-weight="700" fill="var(--accent-ink)">✓ 命中即返回：解析出的 window 值</text>
  <text x="44" y="419" font-size="9.5" fill="var(--ink)">→ 交给 _compute_threshold_tokens() 计算压缩触发阈值（不是固定百分比）</text>
</svg>
<div class="fig-cap"><b>分层解析瀑布</b>：<span class="mono">get_model_context_length()</span> 自上而下走 config 覆盖 → 持久缓存 → provider 逐个探测（Bedrock / 自定义 / 本地 / Anthropic / Codex / Nous / OpenRouter / models.dev）→ 硬编码默认兜底 256K，<strong>命中即短路返回</strong>；右侧那条是真正的坑——<strong>LM Studio / Nous / Codex / Kimi / MiniMax / Grok</strong> 必须主动 bypass 陈旧缓存，否则窗口算错。</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 372" role="img" aria-label="窗口到压缩阈值示意图：上行大窗口 256K，有效输入预算等于窗口减去 max_tokens 预留，触发阈值在有效预算的 50% 处且 floor 在 64K；下行小窗口 64K，50% 乘以预算被 floor 抬到整窗会永不触发，故退化为在 85% 处触发；底部标注窗口算错会导致压缩过早浪费缓存或过晚被 provider 拒">
  <text x="20" y="24" font-size="13.5" font-weight="700" fill="var(--ink)">窗口 → 压缩阈值 · 有效输入预算 × 百分比，floor 在 64K</text>
  <text x="20" y="44" font-size="10.5" fill="var(--muted)">阈值 = max(有效预算 × 0.50, 64K)；若 floor ≥ 窗口则退化为 85%（示意，非等比）</text>
  <text x="20" y="74" font-size="11.5" font-weight="700" fill="var(--purple)">大窗口（resolved window = 256K）</text>
  <rect x="40" y="84" width="600" height="34" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="40" y="84" width="258" height="34" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <rect x="556" y="84" width="84" height="34" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="160" y="105" text-anchor="middle" font-size="9.5" fill="var(--accent-ink)">已用 tokens（增长 →）</text>
  <text x="598" y="100" text-anchor="middle" font-size="9" fill="var(--amber)">max_tokens</text>
  <text x="598" y="111" text-anchor="middle" font-size="9" fill="var(--amber)">预留（输出）</text>
  <line x1="298" y1="76" x2="298" y2="126" stroke="var(--red)" stroke-width="1.6" stroke-dasharray="4 3"/>
  <text x="298" y="139" text-anchor="middle" font-size="9" fill="var(--red)">触发阈值 = 50% × 有效预算（≥ 64K floor）</text>
  <text x="420" y="79" font-size="9" fill="var(--muted)">有效输入预算 = 窗口 − max_tokens</text>
  <text x="335" y="105" font-size="11" fill="var(--red)">→ 越过即触发压缩</text>
  <text x="20" y="172" font-size="11.5" font-weight="700" fill="var(--purple)">小窗口（resolved window = 64K，本地模型）</text>
  <rect x="40" y="182" width="320" height="34" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="40" y="182" width="247" height="34" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <rect x="330" y="182" width="30" height="34" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="150" y="203" text-anchor="middle" font-size="9.5" fill="var(--accent-ink)">已用 tokens（增长 →）</text>
  <line x1="287" y1="174" x2="287" y2="224" stroke="var(--red)" stroke-width="1.6" stroke-dasharray="4 3"/>
  <text x="287" y="237" text-anchor="middle" font-size="9" fill="var(--red)">floor ≥ 窗口 → 退化 → 在 85% 触发</text>
  <text x="372" y="195" font-size="9" fill="var(--muted)">50%×64K = 32K，但 floor 64K = 整窗</text>
  <text x="372" y="208" font-size="9" fill="var(--muted)">→ 永不触发，故改 85%（_MIN_CTX_TRIGGER_RATIO）</text>
  <rect x="20" y="296" width="640" height="60" rx="10" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="34" y="316" font-size="10" font-weight="700" fill="var(--red)">⚠ 窗口算错的两种代价</text>
  <text x="34" y="334" font-size="9.5" fill="var(--ink)">偏大 → 阈值过高 → 压缩太晚，先被 provider 400 拒（max_tokens 没扣，输入预算虚高）</text>
  <text x="34" y="350" font-size="9.5" fill="var(--ink)">偏小 / floor 退化没处理 → 压缩太早，把还在缓存里的前缀白砸掉</text>
</svg>
<div class="fig-cap"><b>窗口 → 阈值</b>：触发点 = <span class="mono">max(有效输入预算 × 0.50, 64K)</span>；大窗口落在中段、小窗口因 floor 退化改在 <strong>85%</strong>。<span class="mono">max_tokens</span> 预留要从窗口里扣，否则<strong>过晚</strong>压缩会先撞 provider 400；floor 退化不处理则<strong>过早</strong>压缩、白砸缓存。</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 428" role="img" aria-label="各 provider 上下文窗口横向柱状对比，对数刻度（log₂，每格 ×2），从小到大八根柱：探测档 32K（32000，琥珀）；floor 兜底 64K（64000，红色高亮，MINIMUM_CONTEXT_LENGTH）；llama／qwen／grok／gemma-3 共 128K（131072，蓝）；Claude 旧版 200K（200000，蓝）；default 兜底 256K（256000，蓝，DEFAULT_FALLBACK_CONTEXT）；Codex OAuth 上限 272K（272000，蓝）；GLM-5.2 与 DeepSeek-v4 约 1M（1048576 与 1000000，金）；GPT-5.4 最大 1.05M（1050000，金）。红虚线标 floor 64K、紫虚线标 default 256K。窗口越大压缩越晚触发、能塞更多上下文但单轮越贵；解析不出则落 floor 64K。数值取自 model_metadata.py，会随模型更新而变。">
  <text x="12" y="24" font-size="13.5" font-weight="700" fill="var(--ink)">各 provider 上下文窗口横向对比 · 对数刻度（log₂，每格 ×2）</text>
  <text x="12" y="44" font-size="10.5" fill="var(--muted)">窗口大小决定压缩何时触发与内存预算；32K→1.05M 跨约 32×，故用对数刻度，小窗口才看得见</text>
  <text x="648" y="34" text-anchor="middle" font-size="24">📊</text>
  <line x1="190" y1="60" x2="190" y2="308" stroke="var(--line)" stroke-width="1.4"/>
  <line x1="265" y1="60" x2="265" y2="308" stroke="var(--line)" stroke-width="1"/>
  <line x1="340" y1="60" x2="340" y2="308" stroke="var(--line)" stroke-width="1"/>
  <line x1="415" y1="60" x2="415" y2="308" stroke="var(--line)" stroke-width="1"/>
  <line x1="490" y1="60" x2="490" y2="308" stroke="var(--line)" stroke-width="1"/>
  <line x1="565" y1="60" x2="565" y2="308" stroke="var(--line)" stroke-width="1"/>
  <line x1="640" y1="60" x2="640" y2="308" stroke="var(--line)" stroke-width="1"/>
  <text x="265" y="54" text-anchor="middle" font-size="9" fill="var(--muted)">32K</text>
  <text x="340" y="54" text-anchor="middle" font-size="9" fill="var(--muted)">64K</text>
  <text x="415" y="54" text-anchor="middle" font-size="9" fill="var(--muted)">128K</text>
  <text x="490" y="54" text-anchor="middle" font-size="9" fill="var(--muted)">256K</text>
  <text x="565" y="54" text-anchor="middle" font-size="9" fill="var(--muted)">512K</text>
  <text x="640" y="54" text-anchor="middle" font-size="9" fill="var(--muted)">1M</text>
  <text x="12" y="54" font-size="9" fill="var(--faint)">tokens →</text>
  <text x="12" y="90" font-size="9" fill="var(--ink)">探测档 · 32K</text>
  <rect x="190" y="78" width="72" height="17" rx="4" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="255" y="91" text-anchor="end" font-size="9" fill="var(--amber)">32000</text>
  <text x="12" y="119" font-size="9" font-weight="700" fill="var(--red)">floor 兜底 · 64K</text>
  <rect x="190" y="107" width="147" height="17" rx="4" fill="var(--amber-soft)" stroke="var(--red)" stroke-width="1.6"/>
  <text x="330" y="120" text-anchor="end" font-size="9" fill="var(--red)">64000</text>
  <text x="12" y="148" font-size="9" fill="var(--ink)">llama／qwen／grok · 128K</text>
  <rect x="190" y="136" width="225" height="17" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="408" y="149" text-anchor="end" font-size="9" fill="var(--blue)">131072</text>
  <text x="12" y="177" font-size="9" fill="var(--ink)">Claude 旧版 · 200K</text>
  <rect x="190" y="165" width="271" height="17" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="454" y="178" text-anchor="end" font-size="9" fill="var(--blue)">200000</text>
  <text x="12" y="206" font-size="9" fill="var(--ink)">default 兜底 · 256K</text>
  <rect x="190" y="194" width="297" height="17" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="480" y="207" text-anchor="end" font-size="9" fill="var(--blue)">256000</text>
  <text x="12" y="235" font-size="9" fill="var(--ink)">Codex OAuth · 272K</text>
  <rect x="190" y="223" width="304" height="17" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="487" y="236" text-anchor="end" font-size="9" fill="var(--blue)">272000</text>
  <text x="12" y="264" font-size="9" fill="var(--ink)">GLM-5.2／DeepSeek · 1M</text>
  <rect x="190" y="252" width="450" height="17" rx="4" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="633" y="265" text-anchor="end" font-size="9" fill="var(--accent-ink)">1048576</text>
  <text x="12" y="293" font-size="9" font-weight="700" fill="var(--accent-ink)">GPT-5.4（最大）· 1.05M</text>
  <rect x="190" y="281" width="452" height="17" rx="4" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="635" y="294" text-anchor="end" font-size="9" fill="var(--accent-ink)">1050000</text>
  <line x1="337" y1="66" x2="337" y2="308" stroke="var(--red)" stroke-width="1.6" stroke-dasharray="4 3"/>
  <line x1="487" y1="66" x2="487" y2="308" stroke="var(--purple)" stroke-width="1.6" stroke-dasharray="4 3"/>
  <rect x="12" y="320" width="656" height="96" rx="10" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="24" y="331" width="16" height="11" rx="2" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="46" y="340" font-size="9" fill="var(--ink)">小窗 32–64K</text>
  <rect x="150" y="331" width="16" height="11" rx="2" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="172" y="340" font-size="9" fill="var(--ink)">中窗 128–272K</text>
  <rect x="300" y="331" width="16" height="11" rx="2" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="322" y="340" font-size="9" fill="var(--ink)">大窗 1M+</text>
  <line x1="420" y1="337" x2="440" y2="337" stroke="var(--red)" stroke-width="1.6" stroke-dasharray="4 3"/>
  <text x="444" y="340" font-size="9" fill="var(--ink)">floor 64K</text>
  <line x1="540" y1="337" x2="560" y2="337" stroke="var(--purple)" stroke-width="1.6" stroke-dasharray="4 3"/>
  <text x="564" y="340" font-size="9" fill="var(--ink)">default 256K</text>
  <text x="24" y="364" font-size="9.5" fill="var(--ink)">窗口越大 → 压缩越晚触发 → 能塞更多上下文，但单轮越贵；解析不出则落 floor 64K（见本章上方瀑布图）。</text>
  <text x="24" y="384" font-size="9.5" fill="var(--muted)">floor 64K = MINIMUM_CONTEXT_LENGTH 兜底；default 256K = DEFAULT_FALLBACK_CONTEXT；Codex OAuth 封顶 272K。</text>
  <text x="24" y="404" font-size="9.5" fill="var(--muted)">数值取自 model_metadata.py 的真实登记值，会随模型更新而变 —— 故按契约理解，勿写成快照测试。</text>
</svg>
<div class="fig-cap"><b>窗口横向对比</b>：从探测档 <span class="mono">32K</span> 到 GPT-5.4 的 <span class="mono">1.05M</span> 跨约 32×，故用对数刻度（每格 ×2）。<span class="mono">floor 64K</span>（<span class="mono">MINIMUM_CONTEXT_LENGTH</span>，解析失败的兜底）与 <span class="mono">default 256K</span>（<span class="mono">DEFAULT_FALLBACK_CONTEXT</span>，无命中默认）分别标红、紫虚线；窗口越大压缩越晚触发、能塞更多上下文但<strong>单轮越贵</strong>。值取自 <span class="mono">model_metadata.py</span>，会随模型更新而变 —— 按契约读，勿写快照测试。</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 412" role="img" aria-label="压缩触发逐帧状态快照：一个 256K 窗口的长对话，token 一帧帧涨到 50% 阈值触发压缩再回落，每帧画一条水平 token 进度条与一条 50% 阈值虚线。T0 早期 token 约 30%（绿），注有效输入预算等于窗口 256K 减去 max_tokens 预留，未触发；对话继续增长后 T1 token 涨到恰好 50%（琥珀），抵到阈值虚线，达 threshold_percent = 0.50，触发判定；触发压缩是缓存铁律的唯一例外，T2 压缩中把 5 条长历史消息折叠成 1 个摘要块（蓝），token 条因之大幅缩短；续聊后 T3 token 回落到约 20%（绿），继续增长进入下一轮循环。底部旁注：窗口解析不出时 fallback MINIMUM_CONTEXT_LENGTH = 64K；小窗口用 _MIN_CTX_TRIGGER_RATIO = 0.85 设上限防误触，触发点约 max(有效预算×0.50, 64K)，小窗退化到 85%，default 256K、Codex 272K。">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">压缩触发逐帧快照 · token 涨到 50% 阈值 → 压缩 → 回落</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">256K 窗口的一次长对话，沿时间线看 token 进度条如何抵达阈值再回落</text>
  <text x="600" y="34" text-anchor="middle" font-size="24">📉</text>
  <rect x="10" y="66" width="122" height="226" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="20" y="86" font-size="9.5" font-weight="700" fill="var(--ink)">T0 · 早期</text>
  <text x="20" y="100" font-size="9" fill="var(--muted)">未触发</text>
  <text x="20" y="122" font-size="9" font-weight="700" fill="var(--accent-ink)">≈30%</text>
  <text x="71" y="120" text-anchor="middle" font-size="9" fill="var(--amber)">50%</text>
  <rect x="19" y="128" width="104" height="16" rx="4" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="19" y="128" width="31.2" height="16" rx="4" fill="var(--accent)"/>
  <line x1="71" y1="124" x2="71" y2="148" stroke="var(--amber)" stroke-width="1.6" stroke-dasharray="3 3"/>
  <text x="20" y="170" font-size="9" fill="var(--muted)">有效输入预算 =</text>
  <text x="20" y="184" font-size="9" fill="var(--muted)">窗口 256K −</text>
  <text x="20" y="198" font-size="9" fill="var(--muted)">max_tokens 预留</text>
  <text x="20" y="222" font-size="9" fill="var(--accent-ink)">对话持续累积</text>
  <text x="20" y="236" font-size="9" fill="var(--muted)">未达阈值</text>
  <line x1="136" y1="174" x2="184" y2="174" stroke="var(--line)" stroke-width="1.6"/>
  <path d="M190,174 L182,170 L182,178 Z" fill="var(--line)"/>
  <text x="161" y="158" text-anchor="middle" font-size="9" fill="var(--muted)">对话继续</text>
  <text x="161" y="170" text-anchor="middle" font-size="9" fill="var(--muted)">增长</text>
  <rect x="190" y="66" width="122" height="226" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="200" y="86" font-size="9.5" font-weight="700" fill="var(--ink)">T1 · 触阈值</text>
  <text x="200" y="100" font-size="9" fill="var(--amber)">触发判定</text>
  <text x="200" y="122" font-size="9" font-weight="700" fill="var(--amber)">50%</text>
  <text x="251" y="120" text-anchor="middle" font-size="9" fill="var(--amber)">50%</text>
  <rect x="199" y="128" width="104" height="16" rx="4" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="199" y="128" width="52" height="16" rx="4" fill="var(--amber)"/>
  <line x1="251" y1="124" x2="251" y2="148" stroke="var(--amber)" stroke-width="1.6" stroke-dasharray="3 3"/>
  <text x="200" y="170" font-size="9" fill="var(--muted)">达 threshold_</text>
  <text x="200" y="184" font-size="9" fill="var(--muted)">percent = 0.50</text>
  <text x="200" y="208" font-size="9" fill="var(--amber)">token 恰抵阈值线</text>
  <text x="200" y="222" font-size="9" fill="var(--amber)">→ 触发压缩</text>
  <line x1="316" y1="174" x2="364" y2="174" stroke="var(--line)" stroke-width="1.6"/>
  <path d="M370,174 L362,170 L362,178 Z" fill="var(--line)"/>
  <text x="341" y="158" text-anchor="middle" font-size="9" fill="var(--amber)">触发压缩</text>
  <text x="341" y="170" text-anchor="middle" font-size="9" fill="var(--amber)">唯一例外</text>
  <rect x="370" y="66" width="122" height="226" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="380" y="86" font-size="9.5" font-weight="700" fill="var(--ink)">T2 · 压缩中</text>
  <text x="380" y="100" font-size="9" fill="var(--blue)">长史 → 摘要</text>
  <rect x="379" y="110" width="9" height="9" rx="2" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="390" y="110" width="9" height="9" rx="2" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="401" y="110" width="9" height="9" rx="2" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="412" y="110" width="9" height="9" rx="2" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="423" y="110" width="9" height="9" rx="2" fill="var(--panel-2)" stroke="var(--line)"/>
  <line x1="436" y1="114" x2="448" y2="114" stroke="var(--blue)" stroke-width="1.4"/>
  <path d="M452,114 L445,111 L445,117 Z" fill="var(--blue)"/>
  <rect x="454" y="106" width="28" height="18" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="468" y="118" text-anchor="middle" font-size="9" fill="var(--blue)">摘要</text>
  <text x="380" y="142" font-size="9" fill="var(--blue)">5 条消息 → 1 摘要</text>
  <text x="380" y="162" font-size="9" font-weight="700" fill="var(--blue)">token ↓</text>
  <text x="431" y="160" text-anchor="middle" font-size="9" fill="var(--amber)">50%</text>
  <rect x="379" y="168" width="104" height="14" rx="4" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="379" y="168" width="23" height="14" rx="4" fill="var(--blue)"/>
  <line x1="431" y1="164" x2="431" y2="186" stroke="var(--amber)" stroke-width="1.6" stroke-dasharray="3 3"/>
  <text x="380" y="206" font-size="9" fill="var(--muted)">历史折叠成摘要</text>
  <text x="380" y="220" font-size="9" fill="var(--muted)">token 条大幅缩短</text>
  <text x="380" y="234" font-size="9" fill="var(--muted)">缓存在此重建一次</text>
  <line x1="496" y1="174" x2="544" y2="174" stroke="var(--line)" stroke-width="1.6"/>
  <path d="M550,174 L542,170 L542,178 Z" fill="var(--line)"/>
  <text x="521" y="164" text-anchor="middle" font-size="9" fill="var(--muted)">续聊</text>
  <rect x="550" y="66" width="122" height="226" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="560" y="86" font-size="9.5" font-weight="700" fill="var(--ink)">T3 · 回落</text>
  <text x="560" y="100" font-size="9" fill="var(--accent-ink)">进入下一轮</text>
  <text x="560" y="122" font-size="9" font-weight="700" fill="var(--accent-ink)">≈20%</text>
  <text x="611" y="120" text-anchor="middle" font-size="9" fill="var(--amber)">50%</text>
  <rect x="559" y="128" width="104" height="16" rx="4" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="559" y="128" width="20.8" height="16" rx="4" fill="var(--accent)"/>
  <line x1="611" y1="124" x2="611" y2="148" stroke="var(--amber)" stroke-width="1.6" stroke-dasharray="3 3"/>
  <text x="560" y="170" font-size="9" fill="var(--muted)">token 继续增长</text>
  <text x="560" y="184" font-size="9" fill="var(--muted)">进入下一轮循环</text>
  <text x="560" y="208" font-size="9" fill="var(--accent-ink)">→ 回到 T0 早期态</text>
  <rect x="10" y="304" width="662" height="96" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="24" y="324" font-size="9.5" font-weight="700" fill="var(--ink)">旁注 · 兜底与小窗口防误触（图中只用真实常量）</text>
  <circle cx="26" cy="346" r="4" fill="var(--blue)"/>
  <text x="38" y="350" font-size="9" fill="var(--muted)">窗口解析不出 → fallback MINIMUM_CONTEXT_LENGTH = 64K（兜底最小上下文）</text>
  <circle cx="26" cy="372" r="4" fill="var(--amber)"/>
  <text x="38" y="376" font-size="9" fill="var(--muted)">小窗口用 _MIN_CTX_TRIGGER_RATIO = 0.85 设上限防误触；触发点 ≈ max(有效预算×0.50, 64K)，小窗退化到 85%；default 256K、Codex 272K</text>
</svg>
<div class="fig-cap"><b>压缩触发逐帧</b>：一次 256K 长对话里 token 沿时间线 <span class="mono">T0 ≈30% → T1 50%</span>（恰抵 <span class="mono">threshold_percent = 0.50</span> 阈值线）<strong>触发压缩</strong>——这是缓存铁律的<strong>唯一例外</strong>——长历史折叠成摘要后 <span class="mono">T3</span> 回落再进入下一轮；阈值 = <span class="mono">有效输入预算 × 0.50</span>，floor <span class="mono">64K</span>，小窗退化到 <span class="mono">85%</span>。</div>
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 把「模型」当成有状态资源来调度</div>
  本章三套机制——<strong>凭证池</strong>、<strong>副 LLM 路由</strong>、<strong>context-length 解析</strong>——表面各管一摊，底层却共享同一个理念：<strong>模型不是一个无状态端点，而是需要调度的有状态资源。</strong>
  <p style="margin:.5rem 0 0"><strong>三者各自的「状态」：</strong>① 凭证池给每把 key 维护 <span class="mono">OK / EXHAUSTED / DEAD</span> 状态与到期戳，熔断只在<strong>确凿的空 bucket</strong> 上触发、绝不反复试探；② 副 LLM 路由为每个副任务维护一条解析链与 <span class="mono">unhealthy</span> 隐藏窗口，把「调用模型」从一次动作变成可路由、可钉死、可熔断的调度；③ context-length 把「窗口多大」从常量变成<strong>分层解析出的运行期事实</strong>，再据此算压缩阈值。</p>
  <p style="margin:.5rem 0 0"><strong>呼应全书两条主线：</strong>这正是<strong>韧性 / 可演化</strong>的体现——状态外置、失败有界、错值可纠（陈旧缓存主动 bypass）；同时副任务路由也守住了<strong>窄腰</strong>：核心不必把多 provider、多模型的选路逻辑内嵌进主循环，而是交给一个独立解析器按 config 调度，核心只管「拿到一个能用的 client」。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>凭证池是状态机</strong>：每把 key 在 <span class="mono">OK → EXHAUSTED → DEAD</span> 间流转——429 限流冷却 <strong>1 小时</strong>、401 认证失败 <strong>5 分钟</strong>，<span class="mono">token_revoked</span> 类永久失效直接 <span class="mono">DEAD</span>；铁律是<strong>绝不 re-probe 一个已确认空的 bucket</strong>，只在 <span class="mono">remaining=0</span> 的确凿证据下熔断。</li>
    <li><strong>副 LLM 三段路由</strong>：① 主 provider+model（运行期同步）→ ② 任务级 <span class="mono">fallback_chain</span> 与顶层 fallback → ③ 硬编码 discovery 链；每个副任务可在 <span class="mono">auxiliary.&lt;task&gt;</span> 下<strong>per-task 钉死</strong>，命中 402 的 provider 被标 <span class="mono">unhealthy</span> 藏 <strong>10 分钟</strong>跳过。</li>
    <li><strong>窗口先解析、阈值再计算</strong>：<span class="mono">get_model_context_length()</span> 走 config → 持久缓存 → provider 探测（Bedrock / 自定义 / 本地 / Anthropic / Codex / Nous / OpenRouter / models.dev）→ 硬编码默认（兜底 256K）的<strong>分层链</strong>，命中即返回；压缩阈值由此而来，<strong>不是固定百分比</strong>。</li>
    <li><strong>缓存命中 ≠ 可信</strong>：LM Studio / Nous / Codex / Kimi / MiniMax / Grok 等边角 provider 必须<strong>主动 bypass 陈旧缓存</strong>，否则窗口算错——过早压缩（白砸缓存）或过晚（超窗被 provider 400 拒）。</li>
    <li><strong>阈值三步</strong>：基准 = 有效输入预算（<span class="mono">window − max_tokens</span>）× <strong>0.50</strong>，floor 在 <strong>64K</strong>（<span class="mono">MINIMUM_CONTEXT_LENGTH</span>）；当 floor ≥ 窗口（小模型退化）时改在 <strong>85%</strong>（<span class="mono">_MIN_CTX_TRIGGER_RATIO</span>）触发，避免永不压缩。</li>
    <li><strong>共同理念</strong>：三套机制都把模型当成<strong>需要调度的有状态资源</strong>——轮换 / 熔断、路由 / 钉死、解析 / 算阈值，而非一个随叫随到的无状态插座；这是 agent 韧性与窄腰的又一次落地。</li>
  </ul>
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

<h3>🔬 27.1 · Credentials: from one key to a stateful resource pool</h3>
<p>For a single provider you often hold more than one key — a free tier stacked on a paid one, several accounts taking turns. Hermes gathers them into a <strong>persistent credential pool</strong> (<span class="mono">agent/credential_pool.py</span>): each key is a <span class="mono">PooledCredential</span> in the pool, carrying its own status — <span class="mono">OK</span> (usable, in rotation), <span class="mono">EXHAUSTED</span> (cooling down, out for now), <span class="mono">DEAD</span> (excluded for good, never coming back). Every time <span class="mono">select()</span> grabs a key it first clears any <strong>cooled-down</strong> <span class="mono">EXHAUSTED</span> entries back to <span class="mono">OK</span> (<span class="mono">clear_expired</span>), then picks one from the available set by strategy (<span class="mono">random</span> / <span class="mono">least_used</span> / <span class="mono">round_robin</span>).</p>
<p>The iron rule this machine cares about most: <strong>never re-probe a bucket you have already confirmed is empty</strong>. A rate-limited key is not deleted from the pool, nor poked every few seconds to ask "ready yet?" — it gets an <strong>expiry timestamp stamped on it</strong> and is then <strong>skipped</strong>: <span class="mono">DEAD</span> is excluded unconditionally (<span class="mono">select()</span> just <span class="mono">continue</span>s past it), <span class="mono">EXHAUSTED</span> rejoins the candidates only after <span class="mono">last_error_reset_at</span> or the TTL elapses. When a failure hits, <span class="mono">mark_exhausted_and_rotate()</span> stamps the offending key and <strong>immediately re-selects</strong> the next one, so the main request never waits.</p>
<p>The cooldown length is bucketed by the HTTP status that tripped it (<span class="mono">_exhausted_ttl</span>): <strong>429 rate-limit gets 1 hour</strong>, <strong>401 auth failure gets only 5 minutes</strong> (so single-key setups recover fast), other failures default to 1 hour. But that is only the <strong>fallback default</strong>: whenever the provider hands back a <span class="mono">reset_at</span>, or the error text says "retry after …" / "resets in 2 hr 13 min", Hermes <strong>parses the real recovery moment and overrides the default</strong>, refusing to slam early into a wall it knows is still locked. There is a nastier failure too: a 401 whose reason is <span class="mono">token_revoked</span> / <span class="mono">invalid_grant</span> — a <strong>permanent OAuth death</strong> — should not take the 1-hour cooldown (or it would come back every hour, fail, and cool down again); instead it is marked <span class="mono">DEAD</span> outright, clearing only when the user <strong>re-authenticates and writes fresh tokens back</strong>.</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">agent/credential_pool.py:108</span></div><pre># Cooldown before retrying an exhausted credential.
# Transient 401 auth failures cool down briefly so single-key setups can recover.
# 429 (rate-limited), 402 (billing/quota), and other failures cool down after 1 hour.
# Provider-supplied reset_at timestamps override these defaults.
EXHAUSTED_TTL_401_SECONDS = 5 * 60           # 5 minutes
EXHAUSTED_TTL_429_SECONDS = 60 * 60          # 1 hour
EXHAUSTED_TTL_DEFAULT_SECONDS = 60 * 60      # 1 hour</pre></div>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">agent/credential_pool.py:250</span></div><pre>def _exhausted_ttl(error_code: Optional[int]) -&gt; int:
    &quot;&quot;&quot;Return cooldown seconds based on the HTTP status that caused exhaustion.&quot;&quot;&quot;
    if error_code == 401:
        return EXHAUSTED_TTL_401_SECONDS
    if error_code == 429:
        return EXHAUSTED_TTL_429_SECONDS
    return EXHAUSTED_TTL_DEFAULT_SECONDS</pre></div>

<div class="figure">
<svg viewBox="0 0 680 360" role="img" aria-label="Credential-pool state machine: three states OK, EXHAUSTED, DEAD and their transitions — a failure stamps an expiry and enters EXHAUSTED, reset_at or TTL elapsing clears it back to OK, a permanent 401 auth failure goes straight to DEAD and is excluded for good, and only re-authentication that writes tokens back returns it to OK">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">Credential-pool state machine · three states per key, select() picks only from OK</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">EXHAUSTED leaves briefly and auto-returns on expiry; DEAD is excluded for good, not via TTL</text>
  <rect x="44" y="72" width="180" height="94" rx="14" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="134" y="110" text-anchor="middle" font-size="18" font-weight="700" fill="var(--accent-ink)">OK</text>
  <text x="134" y="130" text-anchor="middle" font-size="9.5" fill="var(--muted)">STATUS_OK</text>
  <text x="134" y="150" text-anchor="middle" font-size="10.5" fill="var(--ink)">usable, in rotation</text>
  <rect x="456" y="72" width="180" height="94" rx="14" fill="var(--amber-soft)" stroke="var(--amber)" stroke-width="2"/>
  <text x="546" y="106" text-anchor="middle" font-size="14" font-weight="700" fill="var(--amber)">EXHAUSTED</text>
  <text x="546" y="125" text-anchor="middle" font-size="9" fill="var(--muted)">STATUS_EXHAUSTED</text>
  <text x="546" y="145" text-anchor="middle" font-size="10.5" fill="var(--ink)">cooling down, out briefly</text>
  <rect x="44" y="244" width="180" height="94" rx="14" fill="var(--red-soft)" stroke="var(--red)" stroke-width="2"/>
  <text x="134" y="280" text-anchor="middle" font-size="16" font-weight="700" fill="var(--red)">DEAD</text>
  <text x="134" y="299" text-anchor="middle" font-size="9" fill="var(--muted)">STATUS_DEAD</text>
  <text x="134" y="319" text-anchor="middle" font-size="10.5" fill="var(--ink)">excluded for good</text>
  <line x1="224" y1="104" x2="447" y2="104" stroke="var(--amber)" stroke-width="2"/>
  <path d="M456,104 L447,99 L447,109 Z" fill="var(--amber)"/>
  <text x="335" y="95" text-anchor="middle" font-size="10" fill="var(--amber)">rate-limit / auth failure → stamp expiry</text>
  <line x1="447" y1="138" x2="233" y2="138" stroke="var(--accent)" stroke-width="2"/>
  <path d="M224,138 L233,133 L233,143 Z" fill="var(--accent)"/>
  <text x="335" y="153" text-anchor="middle" font-size="10" fill="var(--accent-ink)">reset_at / TTL elapsed → clear to OK</text>
  <line x1="158" y1="166" x2="158" y2="240" stroke="var(--red)" stroke-width="2"/>
  <path d="M158,244 L153,235 L163,235 Z" fill="var(--red)"/>
  <line x1="190" y1="240" x2="190" y2="170" stroke="var(--muted)" stroke-width="1.6" stroke-dasharray="5 4"/>
  <path d="M190,166 L185,175 L195,175 Z" fill="var(--muted)"/>
  <rect x="266" y="250" width="370" height="88" rx="10" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="282" y="276" font-size="10.5" fill="var(--red)">↓ 401 terminal-auth → DEAD (excluded for good)</text>
  <text x="298" y="296" font-size="9.5" fill="var(--muted)">token_revoked · invalid_grant · token_invalidated…</text>
  <text x="282" y="322" font-size="10.5" fill="var(--accent-ink)">↑ only a re-auth token write-back (sync) returns it to OK</text>
</svg>
<div class="fig-cap"><b>Credential-pool state machine</b>: a failure stamps an expiry on the key and enters <span class="mono">EXHAUSTED</span>, returning to <span class="mono">OK</span> only at <span class="mono">reset_at</span> / TTL; a permanent 401 auth failure (<span class="mono">token_revoked…</span>) is marked <span class="mono">DEAD</span> outright and revives only on a re-auth token write-back — never re-poke a bucket you have confirmed is empty.</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 348" role="img" aria-label="Cooldown-length decision: bucketed by the HTTP status that tripped it — 401 gets 5 minutes, 429 gets 1 hour, others default to 1 hour; a provider's reset_at or retry-after text overrides these defaults">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">Cooldown length · bucketed by HTTP status, provider text can override</text>
  <rect x="260" y="44" width="160" height="46" rx="10" fill="var(--panel-2)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="340" y="66" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">HTTP failure status</text>
  <text x="340" y="82" text-anchor="middle" font-size="9" fill="var(--muted)">status_code</text>
  <line x1="340" y1="90" x2="340" y2="103" stroke="var(--muted)" stroke-width="1.6"/>
  <path d="M340,107 L335,98 L345,98 Z" fill="var(--muted)"/>
  <rect x="236" y="107" width="208" height="44" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="340" y="134" text-anchor="middle" font-size="11.5" fill="var(--blue)">_exhausted_ttl(error_code)</text>
  <line x1="318" y1="151" x2="146" y2="192" stroke="var(--amber)" stroke-width="1.6"/>
  <path d="M132,196 L127,187 L137,187 Z" fill="var(--amber)"/>
  <text x="200" y="176" text-anchor="middle" font-size="10" font-weight="700" fill="var(--amber)">== 401</text>
  <line x1="340" y1="151" x2="340" y2="192" stroke="var(--amber)" stroke-width="1.6"/>
  <path d="M340,196 L335,187 L345,187 Z" fill="var(--amber)"/>
  <text x="356" y="176" text-anchor="middle" font-size="10" font-weight="700" fill="var(--amber)">== 429</text>
  <line x1="362" y1="151" x2="534" y2="192" stroke="var(--amber)" stroke-width="1.6"/>
  <path d="M548,196 L543,187 L553,187 Z" fill="var(--amber)"/>
  <text x="480" y="176" text-anchor="middle" font-size="10" font-weight="700" fill="var(--amber)">else</text>
  <rect x="44" y="198" width="176" height="92" rx="10" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="132" y="224" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--amber)">401 · auth failure</text>
  <text x="132" y="248" text-anchor="middle" font-size="9" fill="var(--muted)">EXHAUSTED_TTL_401_SECONDS</text>
  <text x="132" y="274" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">5 min (300s)</text>
  <rect x="252" y="198" width="176" height="92" rx="10" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="340" y="224" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--amber)">429 · rate limit</text>
  <text x="340" y="248" text-anchor="middle" font-size="9" fill="var(--muted)">EXHAUSTED_TTL_429_SECONDS</text>
  <text x="340" y="274" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">1 hour (3600s)</text>
  <rect x="460" y="198" width="176" height="92" rx="10" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="548" y="224" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--amber)">402 / other failures</text>
  <text x="548" y="248" text-anchor="middle" font-size="9" fill="var(--muted)">EXHAUSTED_TTL_DEFAULT_SECONDS</text>
  <text x="548" y="274" text-anchor="middle" font-size="13" font-weight="700" fill="var(--ink)">1 hour (3600s)</text>
  <rect x="44" y="300" width="592" height="36" rx="10" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="340" y="323" text-anchor="middle" font-size="10.5" fill="var(--accent-ink)">⚡ a provider's reset_at or "retry after / resets in N hr" overrides these defaults</text>
</svg>
<div class="fig-cap"><b>Cooldown decision</b>: <span class="mono">_exhausted_ttl</span> buckets by the status that tripped it — 401 gets 5 minutes, 429 and others get 1 hour; but whenever the provider supplies a <span class="mono">reset_at</span> / "retry after" in the response or error text, the real recovery moment overrides the default.</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 372" role="img" aria-label="Three rotation strategies compared: one pool of 5 keys — random picks any key, least_used picks the one with the smallest request count, round_robin takes the head and moves it to the tail — each strategy selects a different next key">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">Rotation strategies · one pool of 5 keys, three pickers choose a different "next"</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">select() clears expired cooldowns, then picks from the available set by strategy</text>
  <text x="28" y="90" font-size="12" font-weight="700" fill="var(--blue)">random</text>
  <text x="28" y="107" font-size="9" fill="var(--muted)">random.choice(available)</text>
  <rect x="236" y="70" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="269" y="97" text-anchor="middle" font-size="11" fill="var(--ink)">k1</text>
  <rect x="314" y="70" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="347" y="97" text-anchor="middle" font-size="11" fill="var(--ink)">k2</text>
  <rect x="392" y="70" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="425" y="97" text-anchor="middle" font-size="11" fill="var(--ink)">k3</text>
  <rect x="470" y="70" width="66" height="44" rx="8" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="2.5"/>
  <text x="503" y="97" text-anchor="middle" font-size="11" font-weight="700" fill="var(--blue)">k4</text>
  <rect x="548" y="70" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="581" y="97" text-anchor="middle" font-size="11" fill="var(--ink)">k5</text>
  <text x="503" y="130" text-anchor="middle" font-size="9.5" fill="var(--blue)">🎲 random hit</text>
  <text x="28" y="202" font-size="12" font-weight="700" fill="var(--purple)">least_used</text>
  <text x="28" y="219" font-size="9" fill="var(--muted)">min(request_count)</text>
  <rect x="236" y="182" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="269" y="209" text-anchor="middle" font-size="11" fill="var(--ink)">k1</text>
  <rect x="314" y="182" width="66" height="44" rx="8" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="2.5"/>
  <text x="347" y="209" text-anchor="middle" font-size="11" font-weight="700" fill="var(--purple)">k2</text>
  <rect x="392" y="182" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="425" y="209" text-anchor="middle" font-size="11" fill="var(--ink)">k3</text>
  <rect x="470" y="182" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="503" y="209" text-anchor="middle" font-size="11" fill="var(--ink)">k4</text>
  <rect x="548" y="182" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="581" y="209" text-anchor="middle" font-size="11" fill="var(--ink)">k5</text>
  <text x="269" y="240" text-anchor="middle" font-size="9.5" fill="var(--muted)">req 7</text>
  <text x="347" y="240" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--purple)">req 3</text>
  <text x="425" y="240" text-anchor="middle" font-size="9.5" fill="var(--muted)">req 9</text>
  <text x="503" y="240" text-anchor="middle" font-size="9.5" fill="var(--muted)">req 5</text>
  <text x="581" y="240" text-anchor="middle" font-size="9.5" fill="var(--muted)">req 8</text>
  <text x="347" y="258" text-anchor="middle" font-size="9.5" fill="var(--purple)">↑ fewest used</text>
  <text x="28" y="314" font-size="12" font-weight="700" fill="var(--accent-ink)">round_robin</text>
  <text x="28" y="331" font-size="9" fill="var(--muted)">head → move to tail</text>
  <rect x="236" y="294" width="66" height="44" rx="8" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2.5"/>
  <text x="269" y="321" text-anchor="middle" font-size="11" font-weight="700" fill="var(--accent-ink)">k1</text>
  <rect x="314" y="294" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="347" y="321" text-anchor="middle" font-size="11" fill="var(--ink)">k2</text>
  <rect x="392" y="294" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="425" y="321" text-anchor="middle" font-size="11" fill="var(--ink)">k3</text>
  <rect x="470" y="294" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="503" y="321" text-anchor="middle" font-size="11" fill="var(--ink)">k4</text>
  <rect x="548" y="294" width="66" height="44" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="581" y="321" text-anchor="middle" font-size="11" fill="var(--ink)">k5</text>
  <path d="M269,294 C269,278 600,278 600,290" fill="none" stroke="var(--accent)" stroke-width="1.6" stroke-dasharray="5 4"/>
  <path d="M600,294 L595,285 L605,285 Z" fill="var(--accent)"/>
  <text x="470" y="274" text-anchor="middle" font-size="9.5" fill="var(--accent-ink)">→ move to tail</text>
  <text x="269" y="356" text-anchor="middle" font-size="9.5" fill="var(--accent-ink)">↑ take head</text>
</svg>
<div class="fig-cap"><b>Three rotation strategies</b>: from one pool of 5 keys, <span class="mono">random</span> hits any key, <span class="mono">least_used</span> picks the smallest request count, <span class="mono">round_robin</span> takes the head and moves it to the tail — each strategy's "next" is a different key.</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 392" role="img" aria-label="Credential pool frame-by-frame snapshots: an anthropic pool of 3 keys with the least_used strategy. T0 all three healthy, the lowest request_count key #2 is selected; after #2 hits HTTP 429, T1 enters the EXHAUSTED cooldown with reset_at = now plus 3600 seconds and the available set holds only #1 and #3; T2 re-selects #1 within available while #2 is skipped and never re-poked; after the 1 hour TTL expires T3 revives #2 back to OK and the pool returns to 3 selectable keys. Side note: 401 cools down for only 300 seconds; token_revoked or terminal-auth errors go straight to DEAD and never revive.">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">Credential pool, frame by frame · least_used hits 429 → cool down → skip → revive</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">An anthropic pool of 3 keys; follow one key along the timeline as it leaves and re-enters available</text>
  <text x="600" y="32" text-anchor="middle" font-size="22">🔄</text>
  <rect x="10" y="66" width="122" height="216" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="20" y="86" font-size="9.5" font-weight="700" fill="var(--ink)">T0 · all three healthy</text>
  <rect x="19" y="98" width="104" height="28" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="27" y="116" font-size="9" fill="var(--ink)">#1  count=12</text>
  <circle cx="115" cy="112" r="4" fill="var(--accent)"/>
  <rect x="19" y="132" width="104" height="28" rx="6" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="2.5"/>
  <text x="27" y="150" font-size="9" font-weight="700" fill="var(--purple)">#2  count=8</text>
  <circle cx="115" cy="146" r="4" fill="var(--accent)"/>
  <rect x="19" y="166" width="104" height="28" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="27" y="184" font-size="9" fill="var(--ink)">#3  count=15</text>
  <circle cx="115" cy="180" r="4" fill="var(--accent)"/>
  <text x="20" y="214" font-size="9" fill="var(--purple)">least_used → pick min</text>
  <text x="20" y="230" font-size="9" fill="var(--muted)">selected #2 → count→9</text>
  <text x="20" y="250" font-size="9" fill="var(--muted)">available = {#1,#2,#3}</text>
  <line x1="136" y1="174" x2="184" y2="174" stroke="var(--line)" stroke-width="1.6"/>
  <path d="M190,174 L182,170 L182,178 Z" fill="var(--line)"/>
  <text x="161" y="156" text-anchor="middle" font-size="9" fill="var(--amber)">#2 hits</text>
  <text x="161" y="168" text-anchor="middle" font-size="9" fill="var(--amber)">HTTP 429</text>
  <rect x="190" y="66" width="122" height="216" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="200" y="86" font-size="9.5" font-weight="700" fill="var(--ink)">T1 · #2 cooling down</text>
  <rect x="199" y="98" width="104" height="28" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="207" y="116" font-size="9" fill="var(--ink)">#1  count=12</text>
  <circle cx="295" cy="112" r="4" fill="var(--accent)"/>
  <rect x="199" y="132" width="104" height="28" rx="6" fill="var(--amber-soft)" stroke="var(--amber)" stroke-width="2"/>
  <text x="207" y="150" font-size="9" font-weight="700" fill="var(--amber)">#2  EXHAUSTED</text>
  <circle cx="295" cy="146" r="4" fill="var(--amber)"/>
  <rect x="199" y="166" width="104" height="28" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="207" y="184" font-size="9" fill="var(--ink)">#3  count=15</text>
  <circle cx="295" cy="180" r="4" fill="var(--accent)"/>
  <text x="200" y="214" font-size="9" fill="var(--amber)">stamp reset_at</text>
  <text x="200" y="230" font-size="9" fill="var(--muted)">reset_at = now+3600s</text>
  <text x="200" y="250" font-size="9" fill="var(--muted)">available = {#1, #3}</text>
  <line x1="316" y1="174" x2="364" y2="174" stroke="var(--line)" stroke-width="1.6"/>
  <path d="M370,174 L362,170 L362,178 Z" fill="var(--line)"/>
  <text x="341" y="156" text-anchor="middle" font-size="9" fill="var(--muted)">next</text>
  <text x="341" y="168" text-anchor="middle" font-size="9" fill="var(--muted)">request</text>
  <rect x="370" y="66" width="122" height="216" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="380" y="86" font-size="9.5" font-weight="700" fill="var(--ink)">T2 · skip empty bucket</text>
  <rect x="379" y="98" width="104" height="28" rx="6" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="2.5"/>
  <text x="387" y="116" font-size="9" font-weight="700" fill="var(--purple)">#1  count=12</text>
  <circle cx="475" cy="112" r="4" fill="var(--accent)"/>
  <rect x="379" y="132" width="104" height="28" rx="6" fill="var(--amber-soft)" stroke="var(--amber)" stroke-width="2"/>
  <text x="387" y="150" font-size="9" fill="var(--amber)">#2  skipped</text>
  <circle cx="475" cy="146" r="4" fill="var(--amber)"/>
  <rect x="379" y="166" width="104" height="28" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="387" y="184" font-size="9" fill="var(--ink)">#3  count=15</text>
  <circle cx="475" cy="180" r="4" fill="var(--accent)"/>
  <text x="380" y="214" font-size="9" fill="var(--purple)">pick within available</text>
  <text x="380" y="230" font-size="9" fill="var(--muted)">selected #1 → count→13</text>
  <text x="380" y="250" font-size="9" fill="var(--muted)">no re-poking empty bucket</text>
  <line x1="496" y1="174" x2="544" y2="174" stroke="var(--line)" stroke-width="1.6"/>
  <path d="M550,174 L542,170 L542,178 Z" fill="var(--line)"/>
  <text x="521" y="156" text-anchor="middle" font-size="9" fill="var(--accent-ink)">after 1h</text>
  <text x="521" y="168" text-anchor="middle" font-size="9" fill="var(--accent-ink)">TTL expires</text>
  <rect x="550" y="66" width="122" height="216" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="560" y="86" font-size="9.5" font-weight="700" fill="var(--ink)">T3 · #2 revived</text>
  <rect x="559" y="98" width="104" height="28" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="567" y="116" font-size="9" fill="var(--ink)">#1  count=13</text>
  <circle cx="655" cy="112" r="4" fill="var(--accent)"/>
  <rect x="559" y="132" width="104" height="28" rx="6" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="567" y="150" font-size="9" font-weight="700" fill="var(--accent-ink)">#2  back→OK</text>
  <circle cx="655" cy="146" r="4" fill="var(--accent)"/>
  <rect x="559" y="166" width="104" height="28" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="567" y="184" font-size="9" fill="var(--ink)">#3  count=15</text>
  <circle cx="655" cy="180" r="4" fill="var(--accent)"/>
  <text x="560" y="214" font-size="9" fill="var(--accent-ink)">TTL expired→clear</text>
  <text x="560" y="230" font-size="9" fill="var(--muted)">re-enters available</text>
  <text x="560" y="250" font-size="9" fill="var(--muted)">pool back to 3 keys</text>
  <rect x="10" y="298" width="662" height="86" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="24" y="318" font-size="9.5" font-weight="700" fill="var(--ink)">Side note · two other exits &amp; reclaim</text>
  <circle cx="26" cy="338" r="4" fill="var(--amber)"/>
  <text x="38" y="342" font-size="9" fill="var(--muted)">401 (token issue) → cooldown only 300s (5min), shorter than 429's 3600s</text>
  <circle cx="26" cy="362" r="4" fill="var(--red)"/>
  <text x="38" y="366" font-size="9" fill="var(--muted)">token_revoked / terminal-auth → straight to DEAD ●, never revives; cleared only by re-auth sync, manual DEAD pruned after 24h</text>
</svg>
<div class="fig-cap"><b>Frame-by-frame snapshots</b>: one key walks the timeline from healthy → hitting <span class="mono">429</span> → <span class="mono">EXHAUSTED</span> cooldown → skipped → revived at <span class="mono">reset_at</span>; each frame <span class="mono">least_used</span> picks the smallest request count only within the available set, never re-poking a bucket already proven empty.</div>
</div>

<h3>🔬 27.2 · Side-LLM routing: every side task runs its own resolution chain</h3>
<p>Beyond the main conversation, Hermes runs a whole batch of <strong>side-LLM tasks</strong> — context compression, vision, web extraction, title generation, skill maintenance (curator)… each one is an <strong>independent model call</strong>, all funneled through one entry point: <span class="mono">_resolve_auto()</span> in <span class="mono">agent/auxiliary_client.py</span>. Its job is not "grab any model that works" but to route each side task to the "most appropriate provider + model" along a <strong>three-stage resolution chain</strong>.</p>
<p><strong>① First, your current main provider + main model.</strong> The key is it uses the <strong>runtime</strong> copy, not the possibly-stale default in <span class="mono">config.yaml</span>: at the top of every turn <span class="mono">set_runtime_main()</span> syncs in the provider, model, <span class="mono">base_url</span>, and key that the CLI / gateway temporarily switched to, so side tasks ride the <strong>same model and the same already-verified key</strong> as the main conversation — predictable, never silently dropping to some cheap default model. A biting example: if you used <span class="mono">hermes model</span> to switch providers just for this session, then without this runtime sync side tasks would still fire against the old provider from <span class="mono">config.yaml</span> — hitting the wrong endpoint, or an account you no longer want to use. <strong>② When the main provider is unavailable</strong>, it checks that task's own <span class="mono">auxiliary.&lt;task&gt;.fallback_chain</span> first, then the main agent's top-level fallback policy. <strong>③ Only if nothing hits</strong> does it walk the hardcoded discovery chain: <span class="mono">openrouter → nous → local/custom → api-key</span>.</p>
<p>Three real pitfalls to keep in mind. First, <strong>per-task pinning is real</strong>: every side task can <strong>pin its own</strong> <span class="mono">provider</span> and <span class="mono">model</span> under <span class="mono">auxiliary.&lt;task&gt;</span> — compression pins one, vision another, title generation a third, all independent. Second, <strong>a 402 / credit error marks the provider unhealthy and hides it for a while</strong>: on a payment or credit-exhaustion hit, <span class="mono">_mark_provider_unhealthy()</span> stamps an expiry on it, hidden for <span class="mono">_AUX_UNHEALTHY_TTL_SECONDS = 600</span> (10 minutes) by default; during that window both Step ① and Step ③ <strong>skip</strong> it, so no side call wastes a doomed 402 round-trip first — it auto-recovers at expiry, no manual intervention after a top-up. Third, <strong>the generic fallback chain may silently pick a cheaper / different model</strong> — it only guarantees "something that works," not "the same as your main model"; to avoid that, <strong>pin the task explicitly</strong>. A concrete case: if a vision task silently lands on a text-only cheap model, every image call 404s — exactly why <span class="mono">vision</span> deserves its own pin.</p>
<p>One deliberate trade-off too: the discovery chain <strong>deliberately excludes Codex</strong>. The ChatGPT-account Codex endpoint only accepts a shifting, undocumented allow-list of model IDs, so falling back with a guessed model fails more often than not — Codex is used only when your <strong>main provider itself is</strong> <span class="mono">openai-codex</span>, or when a caller explicitly passes a model. (Aside: <span class="mono">session_search</span> no longer uses a side LLM as of PR #27590 — the tool returns DB content directly — so it is not in the matrix below.)</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">agent/auxiliary_client.py:3322 · abridged</span></div><pre>def _resolve_auto(main_runtime=None, task=None):        # abridged
    # ... normalize runtime (set_runtime_main records base_url / key)
    # ── Step 1: main provider + main model → use them directly ──
    main_provider = str(runtime_provider or _read_main_provider() or "")
    main_model = str(runtime_model or _read_main_model() or "")
    if (main_provider and main_model
            and main_provider not in {"auto", ""}):
        main_chain_label = _normalize_chain_label(main_provider)
        if main_chain_label and _is_provider_unhealthy(main_chain_label):
            _log_skip_unhealthy(main_chain_label)        # just 402'd -&gt; skip
        else:
            client, resolved = resolve_provider_client(main_provider, main_model, ...)
            if client is not None:
                return client, resolved or main_model    # (1) main provider+model

    # ── Step 2: user-configured fallback policy ──
    if task:
        fb_client, fb_model, _ = _try_configured_fallback_chain(task, ...)  # auxiliary.&lt;task&gt;.fallback_chain
        if fb_client is not None:
            return fb_client, fb_model
    fb_client, fb_model, _ = _try_main_fallback_chain(task, ...)            # top-level fallback
    if fb_client is not None:
        return fb_client, fb_model                       # (2) configured fallback

    # ── Step 3: aggregator / fallback chain ──
    for label, try_fn in _get_provider_chain():          # openrouter → nous → local/custom → api-key
        if _is_provider_unhealthy(label):
            _log_skip_unhealthy(label)                   # 402/credit -&gt; hidden 10 min, skip
            continue
        client, model = try_fn()
        if client is not None:
            return client, model                         # (3) discovery chain
    return None, None</pre></div>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">agent/auxiliary_client.py:2325 · abridged</span></div><pre>def _get_provider_chain() -&gt; List[tuple]:
    &quot;&quot;&quot;Return the ordered provider detection chain.  ... (abridged)

    NOTE: ``openai-codex`` is deliberately NOT in this chain.  The
    ChatGPT-account Codex endpoint only accepts a shifting, undocumented
    allow-list of model IDs, so falling back to it with a guessed model
    fails more often than not.  Codex is used only when the user's main
    provider *is* openai-codex (see Step 1 of ``_resolve_auto``) or when
    a caller explicitly requests it with a model.&quot;&quot;&quot;
    return [
        ("openrouter", _try_openrouter),
        ("nous", _try_nous),
        ("local/custom", _try_custom_endpoint),
        ("api-key", _resolve_api_key_provider),
    ]</pre></div>

<div class="figure">
<svg viewBox="0 0 680 436" role="img" aria-label="Side-LLM routing decision tree: a side-task request tries stage one main provider plus main model, stage two per-task fallback_chain and top-level fallback, stage three the hardcoded discovery chain openrouter to nous to local/custom to api-key, returning the chosen provider and model on the first hit; an unhealthy provider (402 or out of credit) is stamped and hidden 10 minutes and skipped">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">Side-LLM routing decision tree · three stages, first hit returns</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">each side task runs it once; an unhealthy provider is skipped outright</text>
  <rect x="44" y="58" width="280" height="32" rx="10" fill="var(--panel-2)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="184" y="79" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">side task (compression / vision / title…)</text>
  <line x1="184" y1="90" x2="184" y2="104" stroke="var(--muted)" stroke-width="1.6"/>
  <path d="M184,108 L179,99 L189,99 Z" fill="var(--muted)"/>
  <rect x="44" y="110" width="280" height="76" rx="12" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="60" y="135" font-size="12.5" font-weight="700" fill="var(--accent-ink)">① main provider + main model</text>
  <text x="60" y="155" font-size="9.5" fill="var(--muted)">set_runtime_main() syncs runtime base_url / key</text>
  <text x="60" y="173" font-size="9.5" fill="var(--ink)">a hit reuses the main chat model, predictable</text>
  <line x1="184" y1="186" x2="184" y2="200" stroke="var(--muted)" stroke-width="1.6"/>
  <path d="M184,204 L179,195 L189,195 Z" fill="var(--muted)"/>
  <text x="200" y="199" font-size="9" fill="var(--red)">miss / main just 402'd, hidden</text>
  <rect x="44" y="204" width="280" height="72" rx="12" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="2"/>
  <text x="60" y="228" font-size="12.5" font-weight="700" fill="var(--blue)">② configured fallback policy</text>
  <text x="60" y="248" font-size="9" fill="var(--muted)">auxiliary.&lt;task&gt;.fallback_chain (per task)</text>
  <text x="60" y="265" font-size="9" fill="var(--muted)">→ main agent top-level fallback</text>
  <line x1="184" y1="276" x2="184" y2="288" stroke="var(--muted)" stroke-width="1.6"/>
  <path d="M184,292 L179,283 L189,283 Z" fill="var(--muted)"/>
  <text x="200" y="289" font-size="9" fill="var(--muted)">miss</text>
  <rect x="44" y="292" width="592" height="128" rx="12" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="2"/>
  <text x="60" y="316" font-size="12.5" font-weight="700" fill="var(--purple)">③ discovery chain · hardcoded default (no Codex)</text>
  <rect x="64" y="328" width="116" height="40" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="122" y="349" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--ink)">openrouter</text>
  <text x="122" y="362" text-anchor="middle" font-size="9" fill="var(--muted)">aggregator</text>
  <text x="190" y="352" text-anchor="middle" font-size="12" fill="var(--purple)">→</text>
  <rect x="200" y="328" width="116" height="40" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="258" y="349" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--ink)">nous</text>
  <text x="258" y="362" text-anchor="middle" font-size="9" fill="var(--muted)">Nous</text>
  <text x="326" y="352" text-anchor="middle" font-size="12" fill="var(--purple)">→</text>
  <rect x="336" y="328" width="116" height="40" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="394" y="349" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--ink)">local/custom</text>
  <text x="394" y="362" text-anchor="middle" font-size="9" fill="var(--muted)">local / self-host</text>
  <text x="462" y="352" text-anchor="middle" font-size="12" fill="var(--purple)">→</text>
  <rect x="472" y="328" width="116" height="40" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="530" y="349" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--ink)">api-key</text>
  <text x="530" y="362" text-anchor="middle" font-size="9" fill="var(--muted)">direct key</text>
  <rect x="52" y="376" width="536" height="34" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="64" y="397" font-size="9.5" fill="var(--red)">✗ an unhealthy provider (just 402'd / out of credit) → stamped, hidden 10 min, skip to next</text>
  <rect x="430" y="120" width="210" height="120" rx="12" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="535" y="164" text-anchor="middle" font-size="15" font-weight="700" fill="var(--accent-ink)">✓ chosen</text>
  <text x="535" y="189" text-anchor="middle" font-size="11.5" fill="var(--ink)">provider + model</text>
  <text x="535" y="212" text-anchor="middle" font-size="9" fill="var(--muted)">this side task fires the call</text>
  <line x1="324" y1="148" x2="427" y2="160" stroke="var(--accent)" stroke-width="1.8"/>
  <path d="M430,161 L421,158 L423,168 Z" fill="var(--accent)"/>
  <text x="372" y="142" text-anchor="middle" font-size="9" fill="var(--accent-ink)">hit ✓</text>
  <line x1="324" y1="240" x2="427" y2="214" stroke="var(--accent)" stroke-width="1.8"/>
  <path d="M430,213 L421,212 L424,222 Z" fill="var(--accent)"/>
  <text x="372" y="244" text-anchor="middle" font-size="9" fill="var(--accent-ink)">hit ✓</text>
  <line x1="600" y1="292" x2="574" y2="244" stroke="var(--accent)" stroke-width="1.8"/>
  <path d="M572,240 L569,250 L578,247 Z" fill="var(--accent)"/>
  <text x="606" y="280" text-anchor="middle" font-size="9" fill="var(--accent-ink)">hit ✓</text>
</svg>
<div class="fig-cap"><b>Routing decision tree</b>: a side-task request resolves in order — ① main provider+model → ② per-task <span class="mono">fallback_chain</span> and top-level fallback → ③ hardcoded discovery chain (<span class="mono">openrouter→nous→local/custom→api-key</span>) — returning on the first hit; an unhealthy provider (402 / credit) is hidden 10 min and skipped, so no side call wastes a doomed request.</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 352" role="img" aria-label="Side-LLM per-task routing matrix: rows are side tasks compression, vision, web_extract, title_generation, curator, each of which can pin its own provider and model under the auxiliary task block in config.yaml, so different tasks point at different models; unset means auto, with a shared fallback of openrouter google gemini-3-flash-preview">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">per-task routing matrix · each side task pins its own provider + model</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">pinned under auxiliary.&lt;task&gt; in config.yaml; unset = auto (= main chat model)</text>
  <rect x="40" y="60" width="600" height="34" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="52" y="82" font-size="11" font-weight="700" fill="var(--accent-ink)">side task</text>
  <text x="172" y="82" font-size="10" font-weight="700" fill="var(--accent-ink)">provider · pinnable</text>
  <text x="322" y="82" font-size="10" font-weight="700" fill="var(--accent-ink)">model · pinnable</text>
  <text x="532" y="82" font-size="10" font-weight="700" fill="var(--accent-ink)">typical use</text>
  <rect x="40" y="94" width="600" height="40" fill="var(--panel)"/>
  <rect x="40" y="134" width="600" height="40" fill="var(--panel-2)"/>
  <rect x="40" y="174" width="600" height="40" fill="var(--panel)"/>
  <rect x="40" y="214" width="600" height="40" fill="var(--panel-2)"/>
  <rect x="40" y="254" width="600" height="40" fill="var(--panel)"/>
  <text x="52" y="119" font-size="10.5" font-weight="700" fill="var(--ink)">compression</text>
  <text x="172" y="119" font-size="10" fill="var(--accent-ink)">openrouter</text>
  <text x="322" y="119" font-size="9.5" fill="var(--accent-ink)">google/gemini-3-flash-preview</text>
  <text x="532" y="119" font-size="9" fill="var(--muted)">compress context</text>
  <text x="52" y="159" font-size="10.5" font-weight="700" fill="var(--ink)">vision</text>
  <text x="172" y="159" font-size="10" fill="var(--accent-ink)">openrouter</text>
  <text x="322" y="159" font-size="9.5" fill="var(--accent-ink)">google/gemini-2.5-flash</text>
  <text x="532" y="159" font-size="9" fill="var(--muted)">image / multimodal</text>
  <text x="52" y="199" font-size="10.5" font-weight="700" fill="var(--ink)">web_extract</text>
  <text x="172" y="199" font-size="10" fill="var(--accent-ink)">nous</text>
  <text x="322" y="199" font-size="9.5" fill="var(--muted)">(provider default)</text>
  <text x="532" y="199" font-size="9" fill="var(--muted)">web summary</text>
  <text x="52" y="239" font-size="10.5" font-weight="700" fill="var(--ink)">title_generation</text>
  <text x="172" y="239" font-size="10" fill="var(--accent-ink)">openrouter</text>
  <text x="322" y="239" font-size="9.5" fill="var(--accent-ink)">google/gemini-3-flash-preview</text>
  <text x="532" y="239" font-size="9" fill="var(--muted)">session titles</text>
  <text x="52" y="279" font-size="10.5" font-weight="700" fill="var(--ink)">curator</text>
  <text x="172" y="279" font-size="10" fill="var(--muted)">auto</text>
  <text x="322" y="279" font-size="9.5" fill="var(--muted)">(= main chat model)</text>
  <text x="532" y="279" font-size="9" fill="var(--muted)">skill-usage review</text>
  <line x1="160" y1="60" x2="160" y2="294" stroke="var(--line)" stroke-width="1"/>
  <line x1="310" y1="60" x2="310" y2="294" stroke="var(--line)" stroke-width="1"/>
  <line x1="520" y1="60" x2="520" y2="294" stroke="var(--line)" stroke-width="1"/>
  <rect x="40" y="304" width="600" height="34" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="340" y="325" text-anchor="middle" font-size="9.5" fill="var(--blue)">▸ illustrative: any unpinned task runs the _resolve_auto 3-stage chain, shared fallback openrouter:google/gemini-3-flash-preview</text>
</svg>
<div class="fig-cap"><b>Per-task routing matrix</b>: every side task can be pinned independently via <span class="mono">auxiliary.&lt;task&gt;.provider</span> / <span class="mono">.model</span>, so different tasks point at different models (values shown are illustrative); unpinned means <span class="mono">auto</span>, with a shared fallback of <span class="mono">openrouter:google/gemini-3-flash-preview</span>.</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 402" role="img" aria-label="Side-LLM routing frame-by-frame snapshots: one compression side task runs the three-stage _resolve_auto resolution. Frame 1 tries the main provider plus main model (illustrative anthropic plus claude-opus); that model is not usable for side tasks, result MISS, triggering main-unusable to the next stage. Frame 2 tries the task-level auxiliary.compression.fallback_chain which is empty here and the top-level fallback also misses, result MISS, triggering chain-exhausted to discovery. Frame 3 probes openrouter then nous then local/custom then api-key in order; the first healthy one openrouter hits while the other three are not reached, result HIT. Side notes: an unhealthy provider hit (402 or credit exhausted) is stamped and hidden for 600 seconds which is 10 minutes and skipped within the TTL; the side-task slots on this separate path are compression, vision, web_extract, title_generation and curator, each pinning its own provider and model.">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">Side-LLM routing, frame by frame · one compression request, stage MISS→HIT</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">Follow one request along the timeline: misses each stage, finally hits in discovery</text>
  <text x="600" y="34" text-anchor="middle" font-size="24">🎞️</text>
  <rect x="10" y="70" width="188" height="230" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="20" y="88" font-size="9.5" font-weight="700" fill="var(--accent-ink)">Frame 1 · main provider+model</text>
  <text x="20" y="102" font-size="9" fill="var(--muted)">main config from set_runtime_main</text>
  <rect x="19" y="110" width="170" height="56" rx="6" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>
  <text x="28" y="130" font-size="9" fill="var(--ink)">provider = anthropic</text>
  <text x="28" y="148" font-size="9" fill="var(--ink)">model = claude-opus</text>
  <text x="28" y="163" font-size="9" fill="var(--muted)">same as main chat, runtime-synced</text>
  <text x="20" y="186" font-size="9" fill="var(--ink)">verdict: this model is not</text>
  <text x="20" y="200" font-size="9" fill="var(--ink)">usable for side tasks (plan-only)</text>
  <rect x="19" y="224" width="170" height="58" rx="8" fill="var(--red-soft)" stroke="var(--red)" stroke-width="2"/>
  <text x="34" y="252" font-size="16" font-weight="700" fill="var(--red)">✗</text>
  <text x="54" y="251" font-size="11" font-weight="700" fill="var(--red)">MISS</text>
  <text x="34" y="271" font-size="9" fill="var(--red)">main unusable</text>
  <line x1="200" y1="190" x2="242" y2="190" stroke="var(--line)" stroke-width="1.6"/>
  <path d="M246,190 L238,186 L238,194 Z" fill="var(--line)"/>
  <text x="221" y="171" text-anchor="middle" font-size="9" fill="var(--red)">main unusable</text>
  <text x="221" y="182" text-anchor="middle" font-size="9" fill="var(--red)">→ next stage</text>
  <rect x="246" y="70" width="188" height="230" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="256" y="88" font-size="9.5" font-weight="700" fill="var(--blue)">Frame 2 · task fallback_chain</text>
  <text x="256" y="102" font-size="9" fill="var(--muted)">auxiliary.compression block</text>
  <rect x="255" y="110" width="170" height="56" rx="6" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="264" y="130" font-size="9" fill="var(--ink)">fallback_chain:</text>
  <text x="264" y="148" font-size="9" fill="var(--muted)">[ ]  ← unset / empty</text>
  <text x="264" y="163" font-size="9" fill="var(--muted)">top-level fallback misses too</text>
  <text x="256" y="186" font-size="9" fill="var(--ink)">verdict: no fallback</text>
  <text x="256" y="200" font-size="9" fill="var(--ink)">candidate for this task</text>
  <rect x="255" y="224" width="170" height="58" rx="8" fill="var(--red-soft)" stroke="var(--red)" stroke-width="2"/>
  <text x="270" y="252" font-size="16" font-weight="700" fill="var(--red)">✗</text>
  <text x="290" y="251" font-size="11" font-weight="700" fill="var(--red)">MISS</text>
  <text x="270" y="271" font-size="9" fill="var(--red)">chain empty</text>
  <line x1="436" y1="190" x2="478" y2="190" stroke="var(--line)" stroke-width="1.6"/>
  <path d="M482,190 L474,186 L474,194 Z" fill="var(--line)"/>
  <text x="458" y="171" text-anchor="middle" font-size="9" fill="var(--red)">chain empty</text>
  <text x="458" y="182" text-anchor="middle" font-size="9" fill="var(--red)">→ discovery</text>
  <rect x="482" y="70" width="188" height="230" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="492" y="88" font-size="9.5" font-weight="700" fill="var(--purple)">Frame 3 · discovery probes</text>
  <text x="492" y="102" font-size="9" fill="var(--muted)">probe each; first healthy hits</text>
  <rect x="491" y="110" width="170" height="22" rx="5" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="500" y="125" font-size="9" font-weight="700" fill="var(--accent-ink)">openrouter</text>
  <text x="652" y="125" text-anchor="end" font-size="12" fill="var(--accent)">✓</text>
  <rect x="491" y="134" width="170" height="22" rx="5" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="500" y="149" font-size="9" fill="var(--muted)">nous</text>
  <text x="652" y="149" text-anchor="end" font-size="9" fill="var(--muted)">not reached</text>
  <rect x="491" y="158" width="170" height="22" rx="5" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="500" y="173" font-size="9" fill="var(--muted)">local/custom</text>
  <text x="652" y="173" text-anchor="end" font-size="9" fill="var(--muted)">not reached</text>
  <rect x="491" y="182" width="170" height="22" rx="5" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="500" y="197" font-size="9" fill="var(--muted)">api-key</text>
  <text x="652" y="197" text-anchor="end" font-size="9" fill="var(--muted)">not reached</text>
  <rect x="491" y="224" width="170" height="58" rx="8" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="506" y="252" font-size="16" font-weight="700" fill="var(--accent)">✓</text>
  <text x="526" y="251" font-size="11" font-weight="700" fill="var(--accent-ink)">HIT</text>
  <text x="506" y="271" font-size="9" fill="var(--accent-ink)">openrouter healthy</text>
  <rect x="10" y="312" width="660" height="80" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="24" y="332" font-size="9.5" font-weight="700" fill="var(--ink)">Side note · two facts about this separate resolution</text>
  <circle cx="26" cy="352" r="4" fill="var(--red)"/>
  <text x="38" y="356" font-size="9" fill="var(--muted)">an unhealthy provider hit (402 / credit) → hidden for 600s (10min); within the TTL later requests skip it, no doomed retries</text>
  <circle cx="26" cy="376" r="4" fill="var(--purple)"/>
  <text x="38" y="380" font-size="9" fill="var(--muted)">side-task slots on this path: compression / vision / web_extract / title_generation / curator (each pins its own provider / model)</text>
</svg>
<div class="fig-cap"><b>Frame-by-frame resolution</b>: one <span class="mono">compression</span> request along the three stages — Frame 1 main <span class="mono">provider+model</span> not usable for side tasks (MISS) → Frame 2 task <span class="mono">fallback_chain</span> empty (MISS) → Frame 3 <span class="mono">discovery</span> probes in order, <span class="mono">openrouter</span> is the first healthy hit (HIT). An unhealthy provider is hidden for <span class="mono">600s (10min)</span> and skipped within the TTL.</div>
</div>

<h3>🔬 27.3 · Context window: resolve in layers first, then compute the compression threshold</h3>
<p>Compression never fires off a hardcoded "compress at X%" — first you have to <strong>know how large this model's window actually is</strong>. And "how large" is contested for one model name: the user may have overridden it in <span class="mono">config.yaml</span>, last probe's value is cached on disk, the provider's <span class="mono">/models</span> endpoint can report it, <span class="mono">models.dev</span> has it registered, a local server can be queried, and failing all that there's a hardcoded default guessed by model family. <span class="mono">get_model_context_length()</span> in <span class="mono">agent/model_metadata.py</span> arranges these sources into a <strong>layered resolution chain</strong>, top-down, returning on the first hit.</p>
<p>The order (excerpted from its docstring's resolution order): <strong>⓪ explicit config override</strong> (<span class="mono">model.context_length</span> or a custom provider's per-model setting — the user knows their endpoint best) → <strong>① persistent cache</strong> (a previously-probed value on disk) → <strong>①b AWS Bedrock static table</strong> → <strong>② custom-endpoint /models metadata</strong> → <strong>③ local server query</strong> → <strong>④ Anthropic /v1/models</strong> (API-key only, not OAuth) → <strong>⑤ provider-aware probes</strong> (Copilot, Nous live, Codex OAuth, GMI, Ollama, <span class="mono">models.dev</span>) → <strong>⑥ OpenRouter live metadata</strong> (with a Kimi 32k guard) → <strong>⑦ hardcoded defaults</strong> (by model family, longest-key-first) → <strong>⑧ local server last resort</strong> → <strong>⑨ default 256K</strong>.</p>
<p>The sharpest pit here is <strong>"the cache may be stale, and for some providers it must be actively bypassed."</strong> The cache is an optimization — probe once, reuse for a long time; but a few providers either change their window or had a wrong value persisted, and trusting the cache blindly miscomputes the window: <strong>LM Studio</strong>'s loaded context is <strong>transient</strong> (the user can reload the model with a different <span class="mono">context_length</span> at any time), so it <strong>skips the persistent cache entirely</strong>; <strong>Nous</strong> URLs bypass the cache at this step and always defer to the portal <span class="mono">/v1/models</span>; <strong>Codex</strong> OAuth caps at 272K for every slug, so any cached value ≥ 400K is a dirty leftover from the old resolution path and is dropped and re-probed; a <strong>Kimi</strong>-family cache ≤ 32768 is an OpenRouter underreport, and <strong>MiniMax-M3</strong> ≤ 204800 / <strong>Grok-4.3</strong> ≤ 256000 are pre-catalog values persisted before the new entry existed — all three are dropped and fall back to the hardcoded default (they're actually 1M). In one line: <strong>a cache hit ≠ trustworthy; edge providers must be re-verified.</strong></p>
<p>Once the window is resolved, <span class="mono">_compute_threshold_tokens()</span> in <span class="mono">agent/context_compressor.py</span> computes the <strong>trigger threshold</strong>. It isn't a plain "window × 50%" — it's three steps: ① base = <strong>effective input budget × <span class="mono">threshold_percent</span></strong> (default <strong>0.50</strong>); ② floor it at <strong><span class="mono">MINIMUM_CONTEXT_LENGTH</span> = 64K</strong> so large-context models don't compress prematurely at 50%; ③ but that floor degenerates on a <strong>small window</strong>: for a 64K local model, <span class="mono">max(0.5×64000, 64000) == 64000</span> makes the threshold equal the <strong>entire window</strong>, so auto-compression can never fire — the provider rejects the request before usage reaches 100%. So when the floor ≥ the window, it triggers at <strong><span class="mono">_MIN_CTX_TRIGGER_RATIO</span> = 85%</strong> instead. One more layer: the provider <strong>reserves <span class="mono">max_tokens</span> of output space</strong> out of the same window, so the usable <strong>input</strong> budget is <span class="mono">context_length − max_tokens</span> — both the percentage and the degenerate-window check run on this "effective input budget," or a large <span class="mono">max_tokens</span> (e.g. 65536 on a custom provider) lets the session hit a provider 400 before compaction fires. The threshold only decides <strong>when</strong> to compact; <strong>how</strong> it compacts afterward — protecting the head/tail, summarizing the middle, rebuilding the cache — is the subject of <strong>ch.15</strong>.</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">agent/context_compressor.py:742 · abridged</span></div><pre>def _compute_threshold_tokens(
    context_length: int, threshold_percent: float, max_tokens: int | None = None,
) -&gt; int:
    &quot;&quot;&quot;Compute the compaction trigger threshold in tokens.

    The base value is ``effective_input_budget * threshold_percent``, floored
    at ``MINIMUM_CONTEXT_LENGTH`` so large-context models don't compress
    prematurely at 50%. ...(docstring abridged: #14690 degenerate window / #43547 max_tokens)
    &quot;&quot;&quot;
    effective_window = context_length - (max_tokens or 0)   # drop output reservation
    if effective_window &lt;= 0:
        effective_window = context_length
    pct_value = int(effective_window * threshold_percent)   # default 0.50
    floored = max(pct_value, MINIMUM_CONTEXT_LENGTH)        # 64_000 floor
    # If flooring pushed the threshold to/over the effective window it can
    # never be reached. Trigger at 85% of the effective input budget so a
    # minimum-context model rides most of its budget before compacting
    # instead of wasting half.
    if effective_window &gt; 0 and floored &gt;= effective_window:
        return max(1, min(int(effective_window * ContextCompressor._MIN_CTX_TRIGGER_RATIO),
                          effective_window - 1))
    return floored</pre></div>

<div class="figure">
<svg viewBox="0 0 680 446" role="img" aria-label="Layered context-window resolution waterfall: top-down through config override, persistent cache, provider probes (Bedrock, custom endpoint, local, Anthropic, Codex, Nous, OpenRouter, models.dev), and the hardcoded default falling back to 256K, returning on the first hit; the right side notes that some providers must bypass a stale cache, including LM Studio, Nous, Codex, Kimi, MiniMax, and Grok">
  <text x="20" y="24" font-size="13.5" font-weight="700" fill="var(--ink)">Layered context-window resolution · top-down, return on first hit</text>
  <text x="20" y="44" font-size="10.5" fill="var(--muted)">get_model_context_length(): one model name, the window may come from any layer</text>
  <line x1="30" y1="79" x2="30" y2="384" stroke="var(--accent)" stroke-width="1.6"/>
  <path d="M30,392 L25,382 L35,382 Z" fill="var(--accent)"/>
  <text x="38" y="74" font-size="9" font-weight="700" fill="var(--accent-ink)">✓ hit → return</text>
  <rect x="58" y="60" width="320" height="38" rx="9" fill="var(--panel)" stroke="var(--purple)" stroke-width="1.5"/>
  <text x="70" y="80" font-size="12" font-weight="700" fill="var(--purple)">⓪ config override (top priority)</text>
  <text x="70" y="93" font-size="9" fill="var(--muted)">model.context_length · custom provider per-model</text>
  <line x1="58" y1="79" x2="34" y2="79" stroke="var(--accent)" stroke-width="1.4"/>
  <path d="M30,79 L39,74 L39,84 Z" fill="var(--accent)"/>
  <line x1="218" y1="98" x2="218" y2="109" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M218,112 L213,103 L223,103 Z" fill="var(--muted)"/>
  <text x="228" y="109" font-size="9" fill="var(--red)">miss</text>
  <rect x="58" y="112" width="320" height="38" rx="9" fill="var(--panel)" stroke="var(--purple)" stroke-width="1.5"/>
  <text x="70" y="132" font-size="12" font-weight="700" fill="var(--purple)">① persistent cache (probed, on disk)</text>
  <text x="70" y="145" font-size="9" fill="var(--muted)">Nous URLs bypass here, deferring to portal /v1/models</text>
  <line x1="58" y1="131" x2="34" y2="131" stroke="var(--accent)" stroke-width="1.4"/>
  <path d="M30,131 L39,126 L39,136 Z" fill="var(--accent)"/>
  <line x1="218" y1="150" x2="218" y2="161" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M218,164 L213,155 L223,155 Z" fill="var(--muted)"/>
  <text x="228" y="161" font-size="9" fill="var(--red)">miss</text>
  <rect x="58" y="164" width="320" height="142" rx="9" fill="var(--panel)" stroke="var(--purple)" stroke-width="1.5"/>
  <text x="70" y="183" font-size="11.5" font-weight="700" fill="var(--purple)">②–⑥ provider probes (in order)</text>
  <rect x="66" y="194" width="68" height="30" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="100" y="213" text-anchor="middle" font-size="9" fill="var(--ink)">Bedrock</text>
  <rect x="142" y="194" width="68" height="30" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="176" y="213" text-anchor="middle" font-size="9" fill="var(--ink)">custom</text>
  <rect x="218" y="194" width="68" height="30" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="252" y="213" text-anchor="middle" font-size="9" fill="var(--ink)">local</text>
  <rect x="294" y="194" width="68" height="30" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="328" y="213" text-anchor="middle" font-size="9" fill="var(--ink)">Anthropic</text>
  <rect x="66" y="230" width="68" height="30" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="100" y="249" text-anchor="middle" font-size="9" fill="var(--ink)">Codex</text>
  <rect x="142" y="230" width="68" height="30" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="176" y="249" text-anchor="middle" font-size="9" fill="var(--ink)">Nous</text>
  <rect x="218" y="230" width="68" height="30" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="252" y="249" text-anchor="middle" font-size="9" fill="var(--ink)">OpenRouter</text>
  <rect x="294" y="230" width="68" height="30" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="328" y="249" text-anchor="middle" font-size="9" fill="var(--ink)">models.dev</text>
  <text x="70" y="280" font-size="9" fill="var(--muted)">a successful probe is cached (except LM Studio / Nous)</text>
  <text x="70" y="296" font-size="9" fill="var(--muted)">⑥ OpenRouter carries a Kimi 32k guard so an underreport can't win</text>
  <line x1="58" y1="235" x2="34" y2="235" stroke="var(--accent)" stroke-width="1.4"/>
  <path d="M30,235 L39,230 L39,240 Z" fill="var(--accent)"/>
  <line x1="218" y1="306" x2="218" y2="317" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M218,320 L213,311 L223,311 Z" fill="var(--muted)"/>
  <text x="228" y="317" font-size="9" fill="var(--red)">miss</text>
  <rect x="58" y="320" width="320" height="42" rx="9" fill="var(--panel-2)" stroke="var(--purple)" stroke-width="1.5"/>
  <text x="70" y="340" font-size="12" font-weight="700" fill="var(--purple)">⑦–⑨ hardcoded defaults → 256K fallback</text>
  <text x="70" y="354" font-size="9" fill="var(--muted)">by family, longest-key-first; else DEFAULT_FALLBACK_CONTEXT</text>
  <line x1="58" y1="341" x2="34" y2="341" stroke="var(--accent)" stroke-width="1.4"/>
  <path d="M30,341 L39,336 L39,346 Z" fill="var(--accent)"/>
  <rect x="406" y="112" width="250" height="96" rx="10" fill="var(--amber-soft)" stroke="var(--amber)" stroke-width="1.5"/>
  <text x="418" y="132" font-size="10" font-weight="700" fill="var(--ink)">⚠ edge providers must bypass a stale cache</text>
  <text x="418" y="151" font-size="9" fill="var(--muted)">a cache hit ≠ trustworthy: window shifts</text>
  <text x="418" y="170" font-size="9.5" fill="var(--ink)">LM Studio · Nous · Codex</text>
  <text x="418" y="188" font-size="9.5" fill="var(--ink)">Kimi · MiniMax · Grok</text>
  <text x="418" y="202" font-size="9" fill="var(--amber)">→ drop the stale value, re-probe</text>
  <line x1="406" y1="140" x2="382" y2="133" stroke="var(--amber)" stroke-width="1.4"/>
  <path d="M378,132 L388,130 L385,139 Z" fill="var(--amber)"/>
  <rect x="24" y="384" width="632" height="42" rx="10" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="44" y="404" font-size="11" font-weight="700" fill="var(--accent-ink)">✓ return on first hit: the resolved window value</text>
  <text x="44" y="419" font-size="9.5" fill="var(--ink)">→ handed to _compute_threshold_tokens() to compute the trigger (not a fixed percentage)</text>
</svg>
<div class="fig-cap"><b>Resolution waterfall</b>: <span class="mono">get_model_context_length()</span> goes top-down through config override → persistent cache → provider probes (Bedrock / custom / local / Anthropic / Codex / Nous / OpenRouter / models.dev) → hardcoded default falling back to 256K, <strong>returning on the first hit</strong>; the real pit is on the right — <strong>LM Studio / Nous / Codex / Kimi / MiniMax / Grok</strong> must actively bypass a stale cache, or the window is miscomputed.</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 372" role="img" aria-label="Window-to-threshold schematic: the top row is a large 256K window where the effective input budget equals the window minus the max_tokens reservation and the trigger sits at 50% of that budget with a 64K floor; the bottom row is a small 64K window where 50% of the budget is raised by the floor to the whole window and never fires, so it degenerates to triggering at 85%; the bottom notes that a miscomputed window compresses too early and wastes the cache or too late and is rejected by the provider">
  <text x="20" y="24" font-size="13.5" font-weight="700" fill="var(--ink)">Window → compression threshold · effective input budget × percent, 64K floor</text>
  <text x="20" y="44" font-size="10.5" fill="var(--muted)">threshold = max(budget × 0.50, 64K); if floor ≥ window it degenerates to 85% (schematic, not to scale)</text>
  <text x="20" y="74" font-size="11.5" font-weight="700" fill="var(--purple)">Large window (resolved window = 256K)</text>
  <rect x="40" y="84" width="600" height="34" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="40" y="84" width="258" height="34" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <rect x="556" y="84" width="84" height="34" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="160" y="105" text-anchor="middle" font-size="9.5" fill="var(--accent-ink)">used tokens (growing →)</text>
  <text x="598" y="100" text-anchor="middle" font-size="9" fill="var(--amber)">max_tokens</text>
  <text x="598" y="111" text-anchor="middle" font-size="9" fill="var(--amber)">reserve (output)</text>
  <line x1="298" y1="76" x2="298" y2="126" stroke="var(--red)" stroke-width="1.6" stroke-dasharray="4 3"/>
  <text x="298" y="139" text-anchor="middle" font-size="9" fill="var(--red)">trigger = 50% × budget (≥ 64K floor)</text>
  <text x="420" y="79" font-size="9" fill="var(--muted)">effective input budget = window − max_tokens</text>
  <text x="335" y="105" font-size="11" fill="var(--red)">→ cross it, compress</text>
  <text x="20" y="172" font-size="11.5" font-weight="700" fill="var(--purple)">Small window (resolved window = 64K, local model)</text>
  <rect x="40" y="182" width="320" height="34" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="40" y="182" width="247" height="34" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <rect x="330" y="182" width="30" height="34" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="150" y="203" text-anchor="middle" font-size="9.5" fill="var(--accent-ink)">used tokens (growing →)</text>
  <line x1="287" y1="174" x2="287" y2="224" stroke="var(--red)" stroke-width="1.6" stroke-dasharray="4 3"/>
  <text x="287" y="237" text-anchor="middle" font-size="9" fill="var(--red)">floor ≥ window → degenerate → trigger at 85%</text>
  <text x="372" y="195" font-size="9" fill="var(--muted)">50%×64K = 32K, but floor 64K = whole window</text>
  <text x="372" y="208" font-size="9" fill="var(--muted)">→ never fires, so use 85% (_MIN_CTX_TRIGGER_RATIO)</text>
  <rect x="20" y="296" width="640" height="60" rx="10" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="34" y="316" font-size="10" font-weight="700" fill="var(--red)">⚠ two costs of a miscomputed window</text>
  <text x="34" y="334" font-size="9.5" fill="var(--ink)">too large → threshold too high → compresses too late, hits a provider 400 first (max_tokens not subtracted)</text>
  <text x="34" y="350" font-size="9.5" fill="var(--ink)">too small / floor degeneracy unhandled → compresses too early, wastes a prefix still in cache</text>
</svg>
<div class="fig-cap"><b>Window → threshold</b>: the trigger = <span class="mono">max(effective input budget × 0.50, 64K)</span>; a large window lands mid-bar, a small one degenerates via the floor to <strong>85%</strong>. The <span class="mono">max_tokens</span> reserve must be subtracted from the window, or compressing <strong>too late</strong> hits a provider 400; leaving the floor degeneracy unhandled compresses <strong>too early</strong> and wastes the cache.</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 428" role="img" aria-label="Horizontal bar comparison of context windows by provider, log scale (log2, each step x2), eight bars small to large: probe tier 32K (32000, amber); fallback floor 64K (64000, red highlight, MINIMUM_CONTEXT_LENGTH); llama/qwen/grok/gemma-3 at 128K (131072, blue); Claude legacy 200K (200000, blue); default fallback 256K (256000, blue, DEFAULT_FALLBACK_CONTEXT); Codex OAuth cap 272K (272000, blue); GLM-5.2 and DeepSeek-v4 about 1M (1048576 and 1000000, gold); GPT-5.4 max 1.05M (1050000, gold). A red dashed line marks floor 64K and a purple dashed line marks default 256K. A bigger window fires compression later and fits more context but costs more per turn; if it cannot be resolved it falls to floor 64K. Values come from model_metadata.py and change as models update.">
  <text x="12" y="24" font-size="13.5" font-weight="700" fill="var(--ink)">Context window by provider · horizontal bars, log scale (log2, each step x2)</text>
  <text x="12" y="44" font-size="10.5" fill="var(--muted)">Window size sets when compression fires and the memory budget; 32K→1.05M spans ~32×, so a log scale keeps small windows visible</text>
  <text x="648" y="34" text-anchor="middle" font-size="24">📊</text>
  <line x1="190" y1="60" x2="190" y2="308" stroke="var(--line)" stroke-width="1.4"/>
  <line x1="265" y1="60" x2="265" y2="308" stroke="var(--line)" stroke-width="1"/>
  <line x1="340" y1="60" x2="340" y2="308" stroke="var(--line)" stroke-width="1"/>
  <line x1="415" y1="60" x2="415" y2="308" stroke="var(--line)" stroke-width="1"/>
  <line x1="490" y1="60" x2="490" y2="308" stroke="var(--line)" stroke-width="1"/>
  <line x1="565" y1="60" x2="565" y2="308" stroke="var(--line)" stroke-width="1"/>
  <line x1="640" y1="60" x2="640" y2="308" stroke="var(--line)" stroke-width="1"/>
  <text x="265" y="54" text-anchor="middle" font-size="9" fill="var(--muted)">32K</text>
  <text x="340" y="54" text-anchor="middle" font-size="9" fill="var(--muted)">64K</text>
  <text x="415" y="54" text-anchor="middle" font-size="9" fill="var(--muted)">128K</text>
  <text x="490" y="54" text-anchor="middle" font-size="9" fill="var(--muted)">256K</text>
  <text x="565" y="54" text-anchor="middle" font-size="9" fill="var(--muted)">512K</text>
  <text x="640" y="54" text-anchor="middle" font-size="9" fill="var(--muted)">1M</text>
  <text x="12" y="54" font-size="9" fill="var(--faint)">tokens →</text>
  <text x="12" y="90" font-size="9" fill="var(--ink)">Probe tier · 32K</text>
  <rect x="190" y="78" width="72" height="17" rx="4" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="255" y="91" text-anchor="end" font-size="9" fill="var(--amber)">32000</text>
  <text x="12" y="119" font-size="9" font-weight="700" fill="var(--red)">Fallback floor · 64K</text>
  <rect x="190" y="107" width="147" height="17" rx="4" fill="var(--amber-soft)" stroke="var(--red)" stroke-width="1.6"/>
  <text x="330" y="120" text-anchor="end" font-size="9" fill="var(--red)">64000</text>
  <text x="12" y="148" font-size="9" fill="var(--ink)">llama/qwen/grok · 128K</text>
  <rect x="190" y="136" width="225" height="17" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="408" y="149" text-anchor="end" font-size="9" fill="var(--blue)">131072</text>
  <text x="12" y="177" font-size="9" fill="var(--ink)">Claude legacy · 200K</text>
  <rect x="190" y="165" width="271" height="17" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="454" y="178" text-anchor="end" font-size="9" fill="var(--blue)">200000</text>
  <text x="12" y="206" font-size="9" fill="var(--ink)">Default fallback · 256K</text>
  <rect x="190" y="194" width="297" height="17" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="480" y="207" text-anchor="end" font-size="9" fill="var(--blue)">256000</text>
  <text x="12" y="235" font-size="9" fill="var(--ink)">Codex OAuth · 272K</text>
  <rect x="190" y="223" width="304" height="17" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="487" y="236" text-anchor="end" font-size="9" fill="var(--blue)">272000</text>
  <text x="12" y="264" font-size="9" fill="var(--ink)">GLM-5.2/DeepSeek · 1M</text>
  <rect x="190" y="252" width="450" height="17" rx="4" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="633" y="265" text-anchor="end" font-size="9" fill="var(--accent-ink)">1048576</text>
  <text x="12" y="293" font-size="9" font-weight="700" fill="var(--accent-ink)">GPT-5.4 (max) · 1.05M</text>
  <rect x="190" y="281" width="452" height="17" rx="4" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="635" y="294" text-anchor="end" font-size="9" fill="var(--accent-ink)">1050000</text>
  <line x1="337" y1="66" x2="337" y2="308" stroke="var(--red)" stroke-width="1.6" stroke-dasharray="4 3"/>
  <line x1="487" y1="66" x2="487" y2="308" stroke="var(--purple)" stroke-width="1.6" stroke-dasharray="4 3"/>
  <rect x="12" y="320" width="656" height="96" rx="10" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="24" y="331" width="16" height="11" rx="2" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="46" y="340" font-size="9" fill="var(--ink)">Small 32-64K</text>
  <rect x="150" y="331" width="16" height="11" rx="2" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="172" y="340" font-size="9" fill="var(--ink)">Mid 128-272K</text>
  <rect x="300" y="331" width="16" height="11" rx="2" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="322" y="340" font-size="9" fill="var(--ink)">Large 1M+</text>
  <line x1="420" y1="337" x2="440" y2="337" stroke="var(--red)" stroke-width="1.6" stroke-dasharray="4 3"/>
  <text x="444" y="340" font-size="9" fill="var(--ink)">floor 64K</text>
  <line x1="540" y1="337" x2="560" y2="337" stroke="var(--purple)" stroke-width="1.6" stroke-dasharray="4 3"/>
  <text x="564" y="340" font-size="9" fill="var(--ink)">default 256K</text>
  <text x="24" y="364" font-size="9.5" fill="var(--ink)">Bigger window → compression fires later → more context fits, but each turn costs more; if unresolved it falls to floor 64K (see the waterfall above).</text>
  <text x="24" y="384" font-size="9.5" fill="var(--muted)">floor 64K = MINIMUM_CONTEXT_LENGTH fallback; default 256K = DEFAULT_FALLBACK_CONTEXT; Codex OAuth caps at 272K.</text>
  <text x="24" y="404" font-size="9.5" fill="var(--muted)">Values are model_metadata.py real registered entries and change as models update — read them as a contract, do not snapshot-test.</text>
</svg>
<div class="fig-cap"><b>Window comparison</b>: from the probe tier <span class="mono">32K</span> to GPT-5.4's <span class="mono">1.05M</span> spans ~32×, so the axis is log scale (each step x2). <span class="mono">floor 64K</span> (<span class="mono">MINIMUM_CONTEXT_LENGTH</span>, the fallback when resolution fails) and <span class="mono">default 256K</span> (<span class="mono">DEFAULT_FALLBACK_CONTEXT</span>, the no-hit default) are marked by the red and purple dashed lines; a bigger window fires compression later and fits more context but costs <strong>more per turn</strong>. Values are from <span class="mono">model_metadata.py</span> and change as models update — read them as a contract, not a snapshot test.</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 412" role="img" aria-label="Compression-trigger frame-by-frame snapshot: in one long conversation on a 256K window, tokens climb frame by frame to the 50% threshold, fire compression, then fall back; each frame draws a horizontal token progress bar plus a 50% threshold dashed line. T0 early, token about 30% (green), noting effective input budget equals window 256K minus the max_tokens reserve, not fired; after the chat keeps growing, T1 token reaches exactly 50% (amber) right onto the threshold line, reaching threshold_percent = 0.50, trigger decision; compression firing is the one exception to the cache rule; T2 compressing folds 5 long history messages into 1 summary block (blue) and the token bar shrinks a lot; after more chat, T3 token falls back to about 20% (green) and keeps growing into the next loop. Bottom side notes: when the window cannot be resolved it falls back to MINIMUM_CONTEXT_LENGTH = 64K; a small window uses _MIN_CTX_TRIGGER_RATIO = 0.85 as a cap to avoid mis-firing, trigger is about max(budget times 0.50, 64K), a small window degenerates to 85%, default 256K, Codex 272K.">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">Compression-trigger frames · token climbs to the 50% threshold then falls back</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">one long conversation on a 256K window, watch the token bar reach the threshold and fall back</text>
  <text x="600" y="34" text-anchor="middle" font-size="24">📉</text>
  <rect x="10" y="66" width="122" height="226" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="20" y="86" font-size="9.5" font-weight="700" fill="var(--ink)">T0 · early</text>
  <text x="20" y="100" font-size="9" fill="var(--muted)">not fired</text>
  <text x="20" y="122" font-size="9" font-weight="700" fill="var(--accent-ink)">~30%</text>
  <text x="71" y="120" text-anchor="middle" font-size="9" fill="var(--amber)">50%</text>
  <rect x="19" y="128" width="104" height="16" rx="4" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="19" y="128" width="31.2" height="16" rx="4" fill="var(--accent)"/>
  <line x1="71" y1="124" x2="71" y2="148" stroke="var(--amber)" stroke-width="1.6" stroke-dasharray="3 3"/>
  <text x="20" y="170" font-size="9" fill="var(--muted)">input budget =</text>
  <text x="20" y="184" font-size="9" fill="var(--muted)">window 256K −</text>
  <text x="20" y="198" font-size="9" fill="var(--muted)">max_tokens reserve</text>
  <text x="20" y="222" font-size="9" fill="var(--accent-ink)">tokens piling up</text>
  <text x="20" y="236" font-size="9" fill="var(--muted)">below threshold</text>
  <line x1="136" y1="174" x2="184" y2="174" stroke="var(--line)" stroke-width="1.6"/>
  <path d="M190,174 L182,170 L182,178 Z" fill="var(--line)"/>
  <text x="161" y="158" text-anchor="middle" font-size="9" fill="var(--muted)">chat keeps</text>
  <text x="161" y="170" text-anchor="middle" font-size="9" fill="var(--muted)">growing</text>
  <rect x="190" y="66" width="122" height="226" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="200" y="86" font-size="9.5" font-weight="700" fill="var(--ink)">T1 · at threshold</text>
  <text x="200" y="100" font-size="9" fill="var(--amber)">fires</text>
  <text x="200" y="122" font-size="9" font-weight="700" fill="var(--amber)">50%</text>
  <text x="251" y="120" text-anchor="middle" font-size="9" fill="var(--amber)">50%</text>
  <rect x="199" y="128" width="104" height="16" rx="4" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="199" y="128" width="52" height="16" rx="4" fill="var(--amber)"/>
  <line x1="251" y1="124" x2="251" y2="148" stroke="var(--amber)" stroke-width="1.6" stroke-dasharray="3 3"/>
  <text x="200" y="170" font-size="9" fill="var(--muted)">reaches threshold_</text>
  <text x="200" y="184" font-size="9" fill="var(--muted)">percent = 0.50</text>
  <text x="200" y="208" font-size="9" fill="var(--amber)">token hits the line</text>
  <text x="200" y="222" font-size="9" fill="var(--amber)">→ fire compress</text>
  <line x1="316" y1="174" x2="364" y2="174" stroke="var(--line)" stroke-width="1.6"/>
  <path d="M370,174 L362,170 L362,178 Z" fill="var(--line)"/>
  <text x="341" y="158" text-anchor="middle" font-size="9" fill="var(--amber)">compress</text>
  <text x="341" y="170" text-anchor="middle" font-size="9" fill="var(--amber)">only exception</text>
  <rect x="370" y="66" width="122" height="226" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="380" y="86" font-size="9.5" font-weight="700" fill="var(--ink)">T2 · compressing</text>
  <text x="380" y="100" font-size="9" fill="var(--blue)">history → summary</text>
  <rect x="379" y="110" width="9" height="9" rx="2" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="390" y="110" width="9" height="9" rx="2" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="401" y="110" width="9" height="9" rx="2" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="412" y="110" width="9" height="9" rx="2" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="423" y="110" width="9" height="9" rx="2" fill="var(--panel-2)" stroke="var(--line)"/>
  <line x1="436" y1="114" x2="448" y2="114" stroke="var(--blue)" stroke-width="1.4"/>
  <path d="M452,114 L445,111 L445,117 Z" fill="var(--blue)"/>
  <rect x="454" y="106" width="28" height="18" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="468" y="118" text-anchor="middle" font-size="9" fill="var(--blue)">sum</text>
  <text x="380" y="142" font-size="9" fill="var(--blue)">5 msgs → 1 summary</text>
  <text x="380" y="162" font-size="9" font-weight="700" fill="var(--blue)">token ↓</text>
  <text x="431" y="160" text-anchor="middle" font-size="9" fill="var(--amber)">50%</text>
  <rect x="379" y="168" width="104" height="14" rx="4" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="379" y="168" width="23" height="14" rx="4" fill="var(--blue)"/>
  <line x1="431" y1="164" x2="431" y2="186" stroke="var(--amber)" stroke-width="1.6" stroke-dasharray="3 3"/>
  <text x="380" y="206" font-size="9" fill="var(--muted)">history folds to sum</text>
  <text x="380" y="220" font-size="9" fill="var(--muted)">token bar shrinks</text>
  <text x="380" y="234" font-size="9" fill="var(--muted)">cache rebuilt once</text>
  <line x1="496" y1="174" x2="544" y2="174" stroke="var(--line)" stroke-width="1.6"/>
  <path d="M550,174 L542,170 L542,178 Z" fill="var(--line)"/>
  <text x="521" y="164" text-anchor="middle" font-size="9" fill="var(--muted)">more chat</text>
  <rect x="550" y="66" width="122" height="226" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="560" y="86" font-size="9.5" font-weight="700" fill="var(--ink)">T3 · falls back</text>
  <text x="560" y="100" font-size="9" fill="var(--accent-ink)">next round</text>
  <text x="560" y="122" font-size="9" font-weight="700" fill="var(--accent-ink)">~20%</text>
  <text x="611" y="120" text-anchor="middle" font-size="9" fill="var(--amber)">50%</text>
  <rect x="559" y="128" width="104" height="16" rx="4" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="559" y="128" width="20.8" height="16" rx="4" fill="var(--accent)"/>
  <line x1="611" y1="124" x2="611" y2="148" stroke="var(--amber)" stroke-width="1.6" stroke-dasharray="3 3"/>
  <text x="560" y="170" font-size="9" fill="var(--muted)">tokens grow on</text>
  <text x="560" y="184" font-size="9" fill="var(--muted)">into the next loop</text>
  <text x="560" y="208" font-size="9" fill="var(--accent-ink)">→ back to T0 state</text>
  <rect x="10" y="304" width="662" height="96" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="24" y="324" font-size="9.5" font-weight="700" fill="var(--ink)">Side notes · fallback and small-window guard (only real constants)</text>
  <circle cx="26" cy="346" r="4" fill="var(--blue)"/>
  <text x="38" y="350" font-size="9" fill="var(--muted)">window unresolved → fallback MINIMUM_CONTEXT_LENGTH = 64K (floor context)</text>
  <circle cx="26" cy="372" r="4" fill="var(--amber)"/>
  <text x="38" y="376" font-size="9" fill="var(--muted)">small window uses _MIN_CTX_TRIGGER_RATIO = 0.85 as a cap; trigger ≈ max(budget × 0.50, 64K), small window degenerates to 85%; default 256K, Codex 272K</text>
</svg>
<div class="fig-cap"><b>Compression trigger, frame by frame</b>: in one 256K conversation tokens climb <span class="mono">T0 ~30% → T1 50%</span> (right onto the <span class="mono">threshold_percent = 0.50</span> line), <strong>firing compression</strong> — the <strong>one exception</strong> to the cache rule — long history folds into a summary, then <span class="mono">T3</span> falls back into the next loop; threshold = <span class="mono">effective input budget × 0.50</span>, floor <span class="mono">64K</span>, small window degenerates to <span class="mono">85%</span>.</div>
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · treat the "model" as a stateful resource to schedule</div>
  This chapter's three mechanisms — the <strong>credential pool</strong>, <strong>side-LLM routing</strong>, and <strong>context-length resolution</strong> — each manage a different patch on the surface, yet share one idea underneath: <strong>a model is not a stateless endpoint, it's a stateful resource that needs scheduling.</strong>
  <p style="margin:.5rem 0 0"><strong>The "state" each one carries:</strong> ① the credential pool maintains <span class="mono">OK / EXHAUSTED / DEAD</span> status and an expiry stamp per key, tripping only on a <strong>confirmed-empty bucket</strong> and never re-probing; ② side-LLM routing maintains a resolution chain and an <span class="mono">unhealthy</span> hide-window per side task, turning "call a model" into routable, pinnable, trippable scheduling; ③ context-length turns "how big is the window" from a constant into a <strong>runtime fact resolved in layers</strong>, then derives the compression threshold from it.</p>
  <p style="margin:.5rem 0 0"><strong>Echoing the book's two throughlines:</strong> this is <strong>resilience / evolvability</strong> in action — state externalized, failure bounded, wrong values correctable (actively bypassing a stale cache); and side-task routing also guards the <strong>narrow waist</strong>: the core needn't embed multi-provider, multi-model selection logic into the main loop, but hands it to an independent resolver scheduled by config, so the core only has to "get a usable client."</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>The credential pool is a state machine</strong>: each key moves through <span class="mono">OK → EXHAUSTED → DEAD</span> — 429 rate-limit cools down <strong>1 hour</strong>, 401 auth failure <strong>5 minutes</strong>, a <span class="mono">token_revoked</span>-class permanent failure goes straight to <span class="mono">DEAD</span>; the iron rule is <strong>never re-probe a bucket you've confirmed is empty</strong>, trip only on the hard evidence of <span class="mono">remaining=0</span>.</li>
    <li><strong>Side-LLM three-stage routing</strong>: ① main provider+model (runtime-synced) → ② per-task <span class="mono">fallback_chain</span> and top-level fallback → ③ hardcoded discovery chain; every side task can be <strong>pinned per-task</strong> under <span class="mono">auxiliary.&lt;task&gt;</span>, and a provider that 402s is marked <span class="mono">unhealthy</span> and hidden <strong>10 minutes</strong>.</li>
    <li><strong>Resolve the window first, compute the threshold second</strong>: <span class="mono">get_model_context_length()</span> runs a <strong>layered chain</strong> — config → persistent cache → provider probes (Bedrock / custom / local / Anthropic / Codex / Nous / OpenRouter / models.dev) → hardcoded default (256K fallback), returning on first hit; the compression threshold derives from this, <strong>not a fixed percentage</strong>.</li>
    <li><strong>A cache hit ≠ trustworthy</strong>: edge providers like LM Studio / Nous / Codex / Kimi / MiniMax / Grok must <strong>actively bypass a stale cache</strong>, or the window is miscomputed — compress too early (waste the cache) or too late (overrun and get a provider 400).</li>
    <li><strong>The threshold in three steps</strong>: base = effective input budget (<span class="mono">window − max_tokens</span>) × <strong>0.50</strong>, floored at <strong>64K</strong> (<span class="mono">MINIMUM_CONTEXT_LENGTH</span>); when the floor ≥ window (a small model degenerates) it triggers at <strong>85%</strong> (<span class="mono">_MIN_CTX_TRIGGER_RATIO</span>) instead, so compaction can still fire.</li>
    <li><strong>The shared idea</strong>: all three treat the model as a <strong>stateful resource to schedule</strong> — rotate / trip, route / pin, resolve / compute-threshold — not a stateless socket you call on demand; one more landing of agent resilience and the narrow waist.</li>
  </ul>
</div>
""",
}

LESSON_28 = {
    "zh": r"""
<p class="lead">一个跑了几十轮、还开着后台进程、正在改文件的 agent，要怎么<strong>安全地急停、可靠地知道后台干完没、原子地落盘</strong>？这一章拆开 Hermes 在运行时最容易出正确性 bug 的三套机制。</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 飞行中的紧急程序</div>
  急停从来不是<strong>瞬间</strong>的——飞行员拉杆之后，飞机要滑到<strong>下一个稳定点</strong>才真正改出（这正是<strong>协作式中断</strong>：信号在某个边界才被收下，而不是发出的那一刻）。
  <p style="margin:.6rem 0 0">同样的克制在这一章还会出现两次。后台那台引擎，要么<strong>真的还在转</strong>、要么早就停了——仪表必须<strong>如实</strong>反映，而且<strong>同一个状态不能重复报警</strong>（通知去重）。要改飞行计划，你不会在生效的那份上直接涂改：先写一份<strong>草稿</strong>、<strong>校验无误，再原子地换上</strong>（写临时文件，然后 rename）。三个运行时陷阱，一条共同的暗线：一次<strong>停</strong>、一次<strong>看</strong>、一次<strong>存</strong>，都有那么一刻，「看起来完成了」和「真的完成了」会悄悄分叉。</p>
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 运行时的三个正确性陷阱</div>
  运行时——真正负责<strong>停、看、存</strong>的那一层——藏着三处「直觉模型是错的」的地方：
  <p style="margin:.6rem 0 0"><strong>① 中断是协作式的，不是抢占式的。</strong>按下 <span class="mono">/stop</span> 只是<strong>置一面标志</strong>；主循环在它的<strong>边界</strong>（两轮迭代之间）才把它收下，而中断对<strong>子代理的传播是手工接线</strong>的——父代理遍历一张 <span class="mono">_active_children</span> 名册、逐个调 <span class="mono">child.interrupt()</span>。漏掉登记（或像异步委派那样主动 detach），子代理就<strong>永远收不到</strong>这次急停。</p>
  <p><strong>② 后台的「持久」几乎全是进程内幻觉。</strong>一个 <span class="mono">background=true</span> 的 <span class="mono">delegate_task</span> 虽然脱离了当前回合，却仍是<strong>进程本地</strong>的——进程一死它就没了。真正能<strong>熬过重启</strong>的持久，得靠 <span class="mono">cronjob</span> 或后台终端任务，而不是一个活在内存里的 future。</p>
  <p><strong>③ 落盘的原子性，挂在一个毫不起眼的 rename 上。</strong>一个写到一半的配置或会话文件就是损坏；正确的做法是先写临时文件，再<strong>原子地 rename</strong> 把它换上，让读者要么看到旧文件、要么看到完整的新文件，<strong>永远不会读到撕裂的中间态</strong>。</p>
  <p>三个陷阱各自独立，却共享同一条主线：在每一个运行时的边缘，<strong>「看起来完成」都不等于「真的完成」</strong>——而 bug 就住在这条缝里。</p>
</div>

<p>三套机制里，先拆最微妙的第一套：一次「急停」到底怎么在一个正在运行的 agent 里传播，以及为什么它<strong>那么容易传不到子代理</strong>。</p>

<h3>🔬 28.1 · 中断传播：协作式急停，子代理靠显式扇出</h3>
<p>用户按下 <span class="mono">/stop</span>（或网关收到一条中断指令），调用的是 <span class="mono">AIAgent.interrupt()</span>。它做两件事：把 <span class="mono">agent._interrupt_requested</span> 置为 <span class="mono">True</span>、记下触发它的那条新消息，然后调用 <span class="mono">_set_interrupt(True, 执行线程 id)</span>，给<strong>这个 agent 自己的执行线程</strong>盖一个线程级中断信号，让正跑在该线程上的工具（比如一条卡在网络 I/O 上的终端命令）下次自查时能提前退出。注意这个信号是<strong>按线程定向</strong>的：网关里同进程还跑着别的 agent，它们的线程不会被误伤。</p>
<p>但标志置位<strong>不是</strong>中断被「收下」的地方——那一步发生在<strong>主工具循环的边界</strong>。<span class="mono">agent/conversation_loop.py</span> 里的 <span class="mono">while</span> 循环每进入新一轮，先 poll 一次 <span class="mono">agent._interrupt_requested</span>：命中就把 <span class="mono">interrupted</span> 置真、记下 <span class="mono">_turn_exit_reason = "interrupted_by_user"</span>、打一行「Breaking out of tool loop」，然后 <span class="mono">break</span> 退出循环。关键在于：这个检查在<strong>两轮迭代之间</strong>，而不在一次 API 调用、或一个工具执行的<strong>正中间</strong>。</p>
<p>于是 Hermes 的中断是<strong>协作式（cooperative）而非抢占式（preemptive）</strong>——Python 没法从外部硬杀一个线程，所以没有任何地方能「瞬间叫停」正在执行的代码，一切都靠各处<strong>自愿轮询那面标志</strong>。除了循环边界，迭代内部还有几处自查点：流式响应的逐 token 回调里会检查 <span class="mono">_interrupt_requested</span> 并提前掐断；非流式 API 调用挂着一个后台检查循环，一旦发现中断就<strong>强制关闭 httpx 客户端</strong>，让阻塞的请求立刻抛错返回；失败重试的退避睡眠则<strong>每 200ms 轮询一次</strong>（<span class="mono">time.sleep(0.2)</span>），中断一到就放弃重试。但只要某段代码<strong>不去检查</strong>这面标志（一个纯 CPU 的紧循环、一个不配合的第三方调用），它就会一路跑到自己结束、或撞上自己的超时——循环要等它把控制权交回来，才能在下一个边界真正停下。</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">agent/conversation_loop.py:589</span></div><pre>    while (api_call_count &lt; agent.max_iterations and agent.iteration_budget.remaining &gt; 0) or agent._budget_grace_call:
        # Reset per-turn checkpoint dedup so each iteration can take one snapshot
        agent._checkpoint_mgr.new_turn()

        # Check for interrupt request (e.g., user sent new message)
        if agent._interrupt_requested:
            interrupted = True
            _turn_exit_reason = "interrupted_by_user"
            if not agent.quiet_mode:
                agent._safe_print("\n⚡ Breaking out of tool loop due to interrupt...")
            break</pre></div>
<p>第二个、也更容易踩的坑：中断<strong>对子代理的传播是显式手工接线的</strong>，并非免费。<span class="mono">interrupt()</span> 的末尾会遍历 <span class="mono">self._active_children</span> 这张<strong>活跃子代理名册</strong>，对每一个调 <span class="mono">child.interrupt(message)</span>——而 <span class="mono">child.interrupt()</span> 自己又会遍历它的 <span class="mono">_active_children</span>，于是中断<strong>递归扇出</strong>到孙代理、曾孙代理。但这条链能成立，<strong>完全依赖每个被 spawn 出来的子代理都把自己登记进父代理的 <span class="mono">_active_children</span></strong>（见 <span class="mono">delegate_tool.py</span> 里「Register child for interrupt propagation」那一步），并在跑完时注销。一旦某条委派路径<strong>忘了登记、或主动 detach</strong>，父代理的 <span class="mono">/stop</span> 就会<strong>静默地传不到</strong>那个子代理，它会在自己的流式 / 工具循环里<strong>继续跑</strong>。</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">run_agent.py:2433</span></div><pre>        # Propagate interrupt to any running child agents (subagent delegation)
        with self._active_children_lock:
            children_copy = list(self._active_children)
        for child in children_copy:
            try:
                child.interrupt(message)
            except Exception as e:
                logger.debug("Failed to propagate interrupt to child agent: %s", e)</pre></div>
<p>异步 / 后台委派正是<strong>故意 detach</strong> 的：一个 <span class="mono">background=true</span> 的批量委派会把子代理从父代理的 <span class="mono">_active_children</span> 里<strong>摘掉</strong>（它们的生命周期改由异步注册表接管，而非这一回合），转而注册一个独立的 <span class="mono">interrupt_fn</span> 去取消它们。这是设计，不是 bug——但它恰好说明了为什么「中断会自己传下去」是个危险假设：<strong>扇出是一条要靠人手维护的不变量，而不是语言级特性</strong>。新增任何一条委派路径时，谁负责把这次急停带到子代理那里，都必须<strong>显式想清楚</strong>。</p>

<div class="figure">
<svg viewBox="0 0 680 432" role="img" aria-label="中断扇出图：中心 agent.interrupt() 置 _interrupt_requested 为 True，向四条路径传播——主循环边界轮询、子代理需显式 child.interrupt()、流式回调逐 token 查标志、retry 退避每 200ms 轮询；子代理那条标红，强调必须显式传播，漏登记或 detach 就传不到">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">中断扇出 · 一面标志，四条协作式传播路径</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">interrupt() 设标志并给本线程盖信号，再由各处自愿轮询收下；唯子代理靠显式扇出</text>
  <rect x="240" y="58" width="200" height="62" rx="12" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="340" y="84" text-anchor="middle" font-size="13" font-weight="700" fill="var(--accent-ink)">agent.interrupt()</text>
  <text x="340" y="104" text-anchor="middle" font-size="9.5" fill="var(--muted)">_interrupt_requested = True</text>
  <line x1="340" y1="120" x2="92" y2="224" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M92,232 L87,223 L97,223 Z" fill="var(--muted)"/>
  <line x1="340" y1="120" x2="257" y2="224" stroke="var(--red)" stroke-width="1.8"/>
  <path d="M257,232 L252,223 L262,223 Z" fill="var(--red)"/>
  <line x1="340" y1="120" x2="422" y2="224" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M422,232 L417,223 L427,223 Z" fill="var(--muted)"/>
  <line x1="340" y1="120" x2="587" y2="224" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M587,232 L582,223 L592,223 Z" fill="var(--muted)"/>
  <rect x="16" y="232" width="152" height="120" rx="10" fill="var(--panel)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="92" y="257" text-anchor="middle" font-size="12" font-weight="700" fill="var(--blue)">主循环边界</text>
  <text x="92" y="273" text-anchor="middle" font-size="9" fill="var(--muted)">loop boundary</text>
  <line x1="26" y1="281" x2="158" y2="281" stroke="var(--line)"/>
  <text x="26" y="301" font-size="9.5" fill="var(--ink)">每轮迭代先 poll 标志</text>
  <text x="26" y="318" font-size="9.5" fill="var(--ink)">命中即 break 退循环</text>
  <text x="26" y="341" font-size="9" fill="var(--muted)">conversation_loop.py:594</text>
  <rect x="181" y="232" width="152" height="120" rx="10" fill="var(--red-soft)" stroke="var(--red)" stroke-width="2"/>
  <text x="257" y="257" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--red)">子代理 · 显式传播</text>
  <text x="257" y="273" text-anchor="middle" font-size="9" fill="var(--muted)">_active_children fan-out</text>
  <line x1="191" y1="281" x2="323" y2="281" stroke="var(--line)"/>
  <text x="191" y="301" font-size="9.5" fill="var(--ink)">遍历名册逐个</text>
  <text x="191" y="318" font-size="9.5" fill="var(--ink)">child.interrupt()</text>
  <text x="191" y="341" font-size="9" font-weight="700" fill="var(--red)">⚠ 漏登记 / detach 就断链</text>
  <rect x="346" y="232" width="152" height="120" rx="10" fill="var(--panel)" stroke="var(--purple)" stroke-width="1.5"/>
  <text x="422" y="257" text-anchor="middle" font-size="12" font-weight="700" fill="var(--purple)">流式回调</text>
  <text x="422" y="273" text-anchor="middle" font-size="9" fill="var(--muted)">streaming delta</text>
  <line x1="356" y1="281" x2="488" y2="281" stroke="var(--line)"/>
  <text x="356" y="301" font-size="9.5" fill="var(--ink)">逐 token 查标志</text>
  <text x="356" y="318" font-size="9.5" fill="var(--ink)">强关 httpx 提前断</text>
  <text x="356" y="341" font-size="9" fill="var(--muted)">force-close client</text>
  <rect x="511" y="232" width="152" height="120" rx="10" fill="var(--panel)" stroke="var(--amber)" stroke-width="1.5"/>
  <text x="587" y="257" text-anchor="middle" font-size="12" font-weight="700" fill="var(--amber)">retry 退避 poll</text>
  <text x="587" y="273" text-anchor="middle" font-size="9" fill="var(--muted)">backoff sleep</text>
  <line x1="521" y1="281" x2="653" y2="281" stroke="var(--line)"/>
  <text x="521" y="301" font-size="9.5" fill="var(--ink)">每 200ms 轮询一次</text>
  <text x="521" y="318" font-size="9.5" fill="var(--ink)">time.sleep(0.2)</text>
  <text x="521" y="341" font-size="9" fill="var(--muted)">中断到即放弃重试</text>
  <rect x="16" y="372" width="648" height="48" rx="10" fill="var(--panel-2)" stroke="var(--accent)"/>
  <text x="340" y="392" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--accent-ink)">协作式：没有线程被硬杀</text>
  <text x="340" y="410" text-anchor="middle" font-size="9.5" fill="var(--ink)">四条路径全靠各处自愿轮询那面标志——某段不检查的代码，会一路跑到自己结束才停</text>
</svg>
<div class="fig-cap"><b>中断扇出</b>：<span class="mono">interrupt()</span> 设标志 + 给本线程盖信号后，由四条路径各自<strong>自愿轮询</strong>收下——主循环边界、流式回调、retry 退避（每 <strong>200ms</strong>）都靠自查；唯独<strong>子代理</strong>要靠父代理遍历 <span class="mono">_active_children</span> 显式 <span class="mono">child.interrupt()</span> 才传得到，漏登记 / detach 就断链。</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 356" role="img" aria-label="协作式与抢占式中断时序对比：上轨 Hermes 协作式，工具执行到一半时 /stop 到达，标志置位后进入挂起等待，直到下一个循环边界才真正 break；下轨抢占式对照（Hermes 不这么做），同一时刻当场硬停，用虚线表示">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">cooperative vs preemptive · 同一刻中断，停在不同时点</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">中断在工具执行中途到达——协作式等到循环边界才收下，抢占式当场杀线程</text>
  <text x="20" y="92" font-size="11" font-weight="700" fill="var(--accent-ink)">Hermes · 协作式</text>
  <line x1="140" y1="120" x2="660" y2="120" stroke="var(--line)"/>
  <rect x="140" y="104" width="160" height="32" rx="6" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="220" y="124" text-anchor="middle" font-size="9.5" fill="var(--blue)">工具执行中</text>
  <rect x="300" y="104" width="170" height="32" rx="6" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="385" y="124" text-anchor="middle" font-size="9" fill="var(--amber)">挂起等待 · 标志已置位</text>
  <line x1="300" y1="74" x2="300" y2="178" stroke="var(--red)" stroke-width="1.6" stroke-dasharray="4 3"/>
  <text x="300" y="68" text-anchor="middle" font-size="9.5" fill="var(--red)">⚡ /stop 到达（执行中途）</text>
  <line x1="470" y1="92" x2="470" y2="150" stroke="var(--accent)" stroke-width="1.8"/>
  <text x="470" y="86" text-anchor="middle" font-size="9.5" fill="var(--accent-ink)">↧ 循环边界</text>
  <rect x="478" y="104" width="158" height="32" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="557" y="124" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--accent-ink)">✓ 真正 break 退出</text>
  <text x="140" y="158" font-size="9" fill="var(--muted)">中断在两轮迭代之间被收下——执行中的工具先跑到自查点或边界，循环才交回控制权</text>
  <line x1="300" y1="178" x2="300" y2="236" stroke="var(--muted)" stroke-width="1.2" stroke-dasharray="3 3"/>
  <text x="20" y="258" font-size="11" font-weight="700" fill="var(--muted)">抢占式 · 对照（Hermes 不这么做）</text>
  <line x1="140" y1="286" x2="660" y2="286" stroke="var(--line)" stroke-dasharray="4 3"/>
  <rect x="140" y="270" width="160" height="32" rx="6" fill="var(--panel-2)" stroke="var(--muted)" stroke-dasharray="4 3"/>
  <text x="220" y="290" text-anchor="middle" font-size="9.5" fill="var(--muted)">执行中</text>
  <line x1="300" y1="240" x2="300" y2="322" stroke="var(--red)" stroke-width="1.6" stroke-dasharray="4 3"/>
  <text x="300" y="234" text-anchor="middle" font-size="9.5" fill="var(--red)">⚡ /stop 到达</text>
  <rect x="304" y="270" width="158" height="32" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="383" y="290" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--red)">✗ 当场硬停</text>
  <text x="140" y="326" font-size="9" fill="var(--muted)">抢占式会立刻杀掉线程——但 Python 做不到，所以 Hermes 只能用协作式轮询</text>
</svg>
<div class="fig-cap"><b>协作式 vs 抢占式</b>：同一刻 <span class="mono">/stop</span> 在工具执行中途到达——Hermes <strong>协作式</strong>把它挂起到下一个循环边界才 <span class="mono">break</span>；抢占式（对照）会当场杀线程，而 Python 做不到，故只能靠各处轮询那面标志。</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 456" role="img" aria-label="/stop 中断逐帧时间线快照：一次具体 /stop 在某个耗时 tool 执行中到达，演示协作式中断。四帧沿时间线推进，每帧画两条小轨——上轨主循环状态、下轨 _interrupt_requested 标志值。T0 在 0ms，iteration N 的 terminal 工具执行中、进度条 55%，标志为 false。T1 在加 50ms 信号到达，interrupt() 只设 flag 不强杀，tool 仍在执行 82%，标志翻成 true 变琥珀。T2 时 tool 自然跑完返回结果、回到循环边界，标志仍为 true 待读取。T3 循环边界读到 _interrupt_requested 为 true，干净 break 退出、保存状态不丢数据。中部标注：flag 在 T1 置 true 却到 T3 才被读取，这段 tool 仍自然跑完的间隔正是协作式中断的置位与读取时间差。底部旁注：各处轮询粒度 time.sleep(0.2) 等于 200ms，流式回调与 retry 退避都靠自查这面 flag；interrupt() 还扇出到 _active_children，父代理遍历给每个在册子 agent 也 child.interrupt()，但 detach 或未登记的 child 不在册会断链收不到中断。">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">/stop 中断逐帧时间线 · 标志 false → true → 被读取</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">一次具体 /stop：看 _interrupt_requested 沿时间线翻转，以及 tool 在置位后仍自然跑完的间隔</text>
  <text x="600" y="36" text-anchor="middle" font-size="24">🛑</text>
  <rect x="10" y="70" width="132" height="240" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="21" y="90" font-size="9.5" font-weight="700" fill="var(--ink)">T0 · 0ms</text>
  <text x="21" y="105" font-size="9" fill="var(--accent-ink)">执行中</text>
  <text x="21" y="126" font-size="9" fill="var(--muted)">① 主循环状态</text>
  <rect x="20" y="132" width="112" height="30" rx="5" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="76" y="146" text-anchor="middle" font-size="9" fill="var(--accent-ink)">iteration N</text>
  <text x="76" y="157" text-anchor="middle" font-size="9" fill="var(--accent-ink)">terminal 工具执行中</text>
  <rect x="20" y="170" width="112" height="8" rx="3" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="20" y="170" width="61.6" height="8" rx="3" fill="var(--accent)"/>
  <text x="21" y="191" font-size="9" fill="var(--muted)">▶ tool 运行中 · 55%</text>
  <text x="21" y="206" font-size="9" fill="var(--muted)">② _interrupt_requested</text>
  <rect x="20" y="212" width="112" height="28" rx="5" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="76" y="231" text-anchor="middle" font-size="11" font-weight="700" fill="var(--accent-ink)">false</text>
  <text x="21" y="260" font-size="9" fill="var(--muted)">工具正常推进</text>
  <text x="21" y="274" font-size="9" fill="var(--muted)">标志为假 · 无中断</text>
  <line x1="142" y1="196" x2="180" y2="196" stroke="var(--red)" stroke-width="1.6"/>
  <path d="M186,196 L178,192 L178,200 Z" fill="var(--red)"/>
  <text x="164" y="150" text-anchor="middle" font-size="9" fill="var(--red)">用户发</text>
  <text x="164" y="162" text-anchor="middle" font-size="9" fill="var(--red)">/stop</text>
  <rect x="186" y="70" width="132" height="240" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="197" y="90" font-size="9.5" font-weight="700" fill="var(--ink)">T1 · +50ms</text>
  <text x="197" y="105" font-size="9" fill="var(--amber)">信号到达</text>
  <text x="197" y="126" font-size="9" fill="var(--muted)">① 主循环状态</text>
  <rect x="196" y="132" width="112" height="30" rx="5" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="252" y="146" text-anchor="middle" font-size="9" fill="var(--accent-ink)">iteration N</text>
  <text x="252" y="157" text-anchor="middle" font-size="9" fill="var(--accent-ink)">tool 仍在执行</text>
  <rect x="196" y="170" width="112" height="8" rx="3" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="196" y="170" width="91.8" height="8" rx="3" fill="var(--accent)"/>
  <text x="197" y="191" font-size="9" fill="var(--muted)">▶ 未被打断 · 82%</text>
  <text x="197" y="206" font-size="9" fill="var(--muted)">② _interrupt_requested</text>
  <rect x="196" y="212" width="112" height="28" rx="5" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="252" y="231" text-anchor="middle" font-size="11" font-weight="700" fill="var(--amber)">true</text>
  <text x="197" y="260" font-size="9" fill="var(--amber)">interrupt() 只设 flag</text>
  <text x="197" y="274" font-size="9" fill="var(--muted)">不强杀进行中的 tool</text>
  <line x1="318" y1="196" x2="356" y2="196" stroke="var(--accent)" stroke-width="1.6"/>
  <path d="M362,196 L354,192 L354,200 Z" fill="var(--accent)"/>
  <text x="340" y="150" text-anchor="middle" font-size="9" fill="var(--accent-ink)">tool</text>
  <text x="340" y="162" text-anchor="middle" font-size="9" fill="var(--accent-ink)">自然完成</text>
  <rect x="362" y="70" width="132" height="240" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="373" y="90" font-size="9.5" font-weight="700" fill="var(--ink)">T2 · tool 跑完</text>
  <text x="373" y="105" font-size="9" fill="var(--blue)">回到边界</text>
  <text x="373" y="126" font-size="9" fill="var(--muted)">① 主循环状态</text>
  <rect x="372" y="132" width="112" height="30" rx="5" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="428" y="146" text-anchor="middle" font-size="9" fill="var(--blue)">tool 返回结果</text>
  <text x="428" y="157" text-anchor="middle" font-size="9" fill="var(--blue)">→ 回到循环边界</text>
  <rect x="372" y="170" width="112" height="8" rx="3" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="372" y="170" width="112" height="8" rx="3" fill="var(--blue)"/>
  <text x="373" y="191" font-size="9" fill="var(--muted)">✓ tool 已完成</text>
  <text x="373" y="206" font-size="9" fill="var(--muted)">② _interrupt_requested</text>
  <rect x="372" y="212" width="112" height="28" rx="5" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="428" y="231" text-anchor="middle" font-size="11" font-weight="700" fill="var(--amber)">true</text>
  <text x="373" y="260" font-size="9" fill="var(--muted)">flag 已置位</text>
  <text x="373" y="274" font-size="9" fill="var(--amber)">但仍未被读取</text>
  <line x1="494" y1="196" x2="532" y2="196" stroke="var(--blue)" stroke-width="1.6"/>
  <path d="M538,196 L530,192 L530,200 Z" fill="var(--blue)"/>
  <text x="516" y="150" text-anchor="middle" font-size="9" fill="var(--blue)">loop 边界</text>
  <text x="516" y="162" text-anchor="middle" font-size="9" fill="var(--blue)">检查 flag</text>
  <rect x="538" y="70" width="132" height="240" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="549" y="90" font-size="9.5" font-weight="700" fill="var(--ink)">T3 · 干净退出</text>
  <text x="549" y="105" font-size="9" fill="var(--red)">干净 break</text>
  <text x="549" y="126" font-size="9" fill="var(--muted)">① 主循环状态</text>
  <rect x="548" y="132" width="112" height="30" rx="5" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="604" y="146" text-anchor="middle" font-size="9" fill="var(--red)">边界读 flag = true</text>
  <text x="604" y="157" text-anchor="middle" font-size="9" fill="var(--red)">→ 干净 break 退出</text>
  <rect x="548" y="170" width="112" height="8" rx="3" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="548" y="170" width="112" height="8" rx="3" fill="var(--red)"/>
  <text x="549" y="191" font-size="9" fill="var(--muted)">⏹ break · 退出循环</text>
  <text x="549" y="206" font-size="9" fill="var(--muted)">② _interrupt_requested</text>
  <rect x="548" y="212" width="112" height="28" rx="5" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="604" y="231" text-anchor="middle" font-size="11" font-weight="700" fill="var(--red)">true</text>
  <text x="549" y="260" font-size="9" fill="var(--red)">✓ 标志被读取</text>
  <text x="549" y="274" font-size="9" fill="var(--muted)">保存状态 · 不丢数据</text>
  <line x1="252" y1="330" x2="604" y2="330" stroke="var(--amber)" stroke-width="1.4"/>
  <line x1="252" y1="324" x2="252" y2="330" stroke="var(--amber)" stroke-width="1.4"/>
  <line x1="604" y1="324" x2="604" y2="330" stroke="var(--amber)" stroke-width="1.4"/>
  <text x="340" y="322" text-anchor="middle" font-size="9.5" fill="var(--amber)">flag 在 T1 置 true，却到 T3 才被读取——这段 tool 仍自然跑完的间隔，正是协作式中断的「置位 ↔ 读取」时间差</text>
  <rect x="10" y="350" width="660" height="96" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="24" y="372" font-size="9.5" font-weight="700" fill="var(--ink)">旁注 · 轮询粒度与子代理扇出（图中数字只用真实常量）</text>
  <circle cx="26" cy="392" r="4" fill="var(--blue)"/>
  <text x="38" y="396" font-size="9" fill="var(--muted)">各处轮询粒度 time.sleep(0.2) = 200ms：流式回调逐 token、retry 退避都靠自查这面 flag</text>
  <circle cx="26" cy="416" r="4" fill="var(--amber)"/>
  <text x="38" y="420" font-size="9" fill="var(--muted)">interrupt() 还扇出到 _active_children：父代理遍历，给每个在册子 agent 也 child.interrupt()</text>
  <text x="38" y="434" font-size="9" fill="var(--muted)">但 detach / 未登记的 child 不在册 → 断链、收不到中断（异步委派改注册独立 interrupt_fn）</text>
</svg>
<div class="fig-cap"><b>/stop 中断逐帧</b>：一次具体 /stop 的 4 帧快照——<span class="mono">_interrupt_requested</span> 在 <span class="mono">T1(+50ms)</span> 由 <span class="mono">false→true</span>，但执行中的 tool 不被强杀、<strong>自然跑到 T2</strong> 才结束，循环直到 <span class="mono">T3</span> 边界才<strong>读到</strong>这面标志并干净 <span class="mono">break</span>；置位与读取之间的间隔正是协作式中断的本质。各处自查粒度 <span class="mono">time.sleep(0.2)=200ms</span>，<span class="mono">interrupt()</span> 还需显式扇出到 <span class="mono">_active_children</span>。</div>
</div>

<p>急停讲完，看第二个陷阱：一个 <span class="mono">background=true</span> 的进程到底<strong>活在哪</strong>、它那声「干完了」怎么做到<strong>只报一次</strong>、以及为什么它几乎<strong>熬不过一次重启</strong>。</p>

<h3>🔬 28.2 · 后台进程生命周期：内存登记、去重通知、尽力恢复</h3>
<p>当 agent 跑起一条 <span class="mono">terminal(background=True)</span>，进程并不直接交给操作系统不管，而是登记进 <span class="mono">ProcessRegistry</span>——一张<strong>进程内</strong>的注册表，核心是两个字典：<span class="mono">_running</span>（在跑的）与 <span class="mono">_finished</span>（跑完的，留 30 分钟 TTL）。每条 <span class="mono">ProcessSession</span> 挂着一个<strong>滚动输出缓冲</strong>（上限 <span class="mono">MAX_OUTPUT_CHARS</span> = 200KB，超了从头截）、可选的 <span class="mono">watch_patterns</span>、以及一个 <span class="mono">notify_on_complete</span> 标志；后台 reader 线程不停把子进程输出泵进缓冲，agent 则用 <span class="mono">wait</span> / <span class="mono">poll</span> / <span class="mono">kill</span> / 读 log 这几个动作去等它、查它、杀它。</p>
<p>进程<strong>退出</strong>（reader 读到 EOF）或<strong>被 kill</strong> 时，都会走到同一个出口 <span class="mono">_move_to_finished()</span>。它在锁内把 session 从 <span class="mono">_running</span> 弹出、塞进 <span class="mono">_finished</span>，置上完成事件（唤醒所有阻塞在 <span class="mono">wait()</span> 上的调用），再 <span class="mono">_write_checkpoint()</span> 落一次盘。<strong>关键在最后那个 <span class="mono">if</span></strong>：只有当 <span class="mono">notify_on_complete</span> 开着、且<strong>这一次调用确实是第一次</strong>把它移走时，才往 <span class="mono">completion_queue</span> 里塞一条完成通知。</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">tools/process_registry.py:1022 · 简化</span></div><pre>    def _move_to_finished(self, session: ProcessSession):
        with self._lock:
            was_running = self._running.pop(session.id, None) is not None
            self._finished[session.id] = session
        session._completion_event.set()
        self._write_checkpoint()

        # Only enqueue completion notification on the FIRST move.  Without
        # this guard, kill_process() and the reader thread can both call
        # _move_to_finished(), producing duplicate [IMPORTANT: ...] messages.
        if was_running and session.notify_on_complete:
            from tools.ansi_strip import strip_ansi
            output_tail = strip_ansi(session.output_buffer[-2000:]) if session.output_buffer else ""
            self.completion_queue.put({
                "type": "completion",
                "session_id": session.id,
                "session_key": session.session_key,
                "command": session.command,
                "exit_code": session.exit_code,
                "completion_reason": session.completion_reason,
                "termination_source": session.termination_source,
                "output": output_tail,
            })</pre></div>
<p>那个「第一次」靠 <span class="mono">was_running = self._running.pop(...) is not None</span> 拿到——这就是<strong>第一道去重闸</strong>。<span class="mono">_move_to_finished()</span> 是<strong>幂等</strong>的：<span class="mono">kill_process()</span> 和 reader 线程可能<strong>同时</strong>发现进程没了、<strong>都来调它一次</strong>，但字典的 <span class="mono">pop</span> 只有一方拿得到非 <span class="mono">None</span>，于是只有那一方 <span class="mono">was_running</span> 为真、只有它入队。没有这道守卫，一次退出就会被报两遍 <span class="mono">[IMPORTANT: ...]</span>。这是生产端（谁来通知）的去重。</p>
<p>但入队不等于一定送达。<strong>第二道闸在消费端</strong>：CLI 的 drain 与网关 / TUI 的 watcher 取走这条通知前，都会先查 <span class="mono">_completion_consumed</span>——只要 agent 已用阻塞 <span class="mono">wait()</span> 或完整 <span class="mono">read_log()</span> 把输出拿到手，就跳过；CLI 还额外查 <span class="mono">_poll_observed</span>（只读的 <span class="mono">poll()</span> 当场看到了退出、结果已在同一回合内联返回，而网关 / TUI <strong>故意不查</strong>这个，免得一次只读探测压掉它那次自主送达）。命中任一集合，drain 就<strong>跳过</strong>这条通知，避免重复注入一条 <span class="mono">[SYSTEM: ...]</span>。两道闸合起来保证：一次完成<strong>至多报一次</strong>，agent 早已知道就<strong>一次都不报</strong>。</p>
<p>还有一条路也会汇进 <span class="mono">notify_on_complete</span>：<strong>watch 限流降级</strong>。带 <span class="mono">watch_patterns</span> 的进程，命中通知被严格限速——每 <span class="mono">WATCH_MIN_INTERVAL_SECONDS</span>（15 秒）至多一条，落在冷却窗里的命中会被丢弃并记<strong>一次 strike</strong>。连着 <span class="mono">WATCH_STRIKE_LIMIT</span> = <strong>3</strong> 个 strike 窗口后，这个 session 的 watch 被<strong>永久禁用</strong>（<span class="mono">_watch_disabled = True</span>），同时<strong>翻转</strong> <span class="mono">notify_on_complete = True</span>——一个本来狂刷中间态的 watcher，就这样自动降级成「进程真正退出时只报一次」，再走回上面那条唯一出口。</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">tools/process_registry.py:65</span></div><pre># After WATCH_STRIKE_LIMIT consecutive strike windows, watch_patterns for that
# session is permanently disabled and the session falls back to notify_on_complete
# semantics (one notification when the process actually exits).
WATCH_MIN_INTERVAL_SECONDS = 15   # Minimum spacing between consecutive watch matches
WATCH_STRIKE_LIMIT = 3            # Strikes in a row → disable watch + promote to notify_on_complete</pre></div>
<p>现在说<strong>最大的坑</strong>。上面这一整套——两个字典、输出缓冲、完成事件、reader 与 watcher 线程——全都<strong>活在进程内存里</strong>。<span class="mono">_move_to_finished()</span> 里那次 <span class="mono">_write_checkpoint()</span> 会把状态写到 <span class="mono">CHECKPOINT_PATH</span>（<span class="mono">processes.json</span>），但它<strong>仅为网关崩溃恢复</strong>而存在，而且恢复是<strong>尽力而为</strong>的：网关重启后只会重新登记那些 <strong>detached 的 host-PID 进程</strong>，还必须校验检查点里记下的 <span class="mono">host_start_time</span> 与当前 PID 仍匹配（否则 PID 可能已被内核回收给别的进程，贸然认领会误杀陌生进程）。被恢复的 session 一律标 <span class="mono">detached=True</span>——<strong>读不回输出，只能报状态 + kill</strong>。换句话说，检查点恢复的是「还能不能查 / 能不能杀」的<strong>句柄</strong>，不是进程的<strong>完整状态</strong>。</p>
<p>所以 <span class="mono">background=true</span> 的「持久」几乎全是<strong>进程内幻觉</strong>：进程一重启，内存态全丢，detached 恢复也只是尽力而为的状态 / kill 句柄。要让任务<strong>真的跨重启存活</strong>，得用真正落地的机制——<span class="mono">cron</span> 定时任务，或 <span class="mono">terminal(background=True, notify_on_complete=True)</span> 把进程交给系统托管、完成时回调（正是 ch26 的 E6 那条对策）。把「脱离本轮」误当成「持久化」，就是后台任务凭空消失的根因。</p>

<div class="figure">
<svg viewBox="0 0 680 430" role="img" aria-label="后台进程生命周期与完成通知去重图。中间竖向主线：running 进程退出或被 kill 后进入 _move_to_finished，在锁内把 session 从 _running 弹出并塞入 _finished、置完成事件、写检查点，只有第一次移走且 notify_on_complete 为真才把通知放进 completion_queue，最后至多送出一次。左侧分支：带 watch_patterns 的进程命中被限流，每 15 秒至多一条，落在冷却窗内记一次 strike，连满 WATCH_STRIKE_LIMIT 三次后禁用 watch 并翻转 notify_on_complete，汇入同一出口。右侧两道去重闸：闸一 was_running 守卫在生产端，kill 与 reader 线程都会调用但只有一方 pop 成功才入队；闸二在消费端，_completion_consumed 与 CLI 专用的 _poll_observed 集合命中时让 drain 跳过该通知，避免重复注入">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">后台进程生命周期 · 完成通知的两道去重闸</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">一条主线 running → _move_to_finished → 通知；watch 限流满 3 次翻转 notify_on_complete，最终经两道闸至多发一次</text>
  <rect x="265" y="70" width="170" height="64" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="350" y="94" text-anchor="middle" font-size="12" font-weight="700" fill="var(--blue)">running 进程</text>
  <text x="350" y="112" text-anchor="middle" font-size="9" fill="var(--muted)">_running{} · 输出缓冲 200KB</text>
  <text x="350" y="127" text-anchor="middle" font-size="9" fill="var(--muted)">reader 线程 · wait / poll / kill / log</text>
  <line x1="350" y1="134" x2="350" y2="168" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M350,176 L345,167 L355,167 Z" fill="var(--muted)"/>
  <text x="358" y="158" font-size="9" fill="var(--muted)">退出 / 被 kill</text>
  <rect x="245" y="176" width="210" height="78" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="350" y="198" text-anchor="middle" font-size="12" font-weight="700" fill="var(--accent-ink)">_move_to_finished()</text>
  <text x="350" y="216" text-anchor="middle" font-size="9" fill="var(--muted)">锁内 _running.pop → _finished</text>
  <text x="350" y="231" text-anchor="middle" font-size="9" fill="var(--muted)">set 完成事件 + _write_checkpoint</text>
  <text x="350" y="248" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--red)">闸① was_running 守卫</text>
  <line x1="350" y1="254" x2="350" y2="286" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M350,294 L345,285 L355,285 Z" fill="var(--muted)"/>
  <text x="358" y="276" font-size="9" fill="var(--muted)">首次 + notify_on_complete</text>
  <rect x="265" y="294" width="170" height="52" rx="10" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="1.5"/>
  <text x="350" y="316" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--purple)">completion_queue</text>
  <text x="350" y="334" text-anchor="middle" font-size="9" fill="var(--muted)">type: completion 入队</text>
  <line x1="350" y1="346" x2="350" y2="376" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M350,384 L345,375 L355,375 Z" fill="var(--muted)"/>
  <rect x="245" y="386" width="210" height="38" rx="9" fill="var(--panel-2)" stroke="var(--accent)" stroke-width="1.5"/>
  <text x="350" y="410" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--accent-ink)">至多发一次（已知道就一次都不发）</text>
  <rect x="18" y="176" width="182" height="78" rx="10" fill="var(--amber-soft)" stroke="var(--amber)" stroke-width="1.5"/>
  <text x="109" y="197" text-anchor="middle" font-size="11" font-weight="700" fill="var(--amber)">watch 命中限流</text>
  <text x="109" y="214" text-anchor="middle" font-size="9" fill="var(--ink)">每 15s 至多 1 条</text>
  <text x="109" y="229" text-anchor="middle" font-size="9" fill="var(--ink)">落冷却窗 = 1 strike</text>
  <text x="109" y="245" text-anchor="middle" font-size="9" font-weight="700" fill="var(--ink)">连满 3 次 → 禁 watch + 翻转</text>
  <line x1="200" y1="208" x2="241" y2="208" stroke="var(--amber)" stroke-width="1.6"/>
  <path d="M249,208 L240,203 L240,213 Z" fill="var(--amber)"/>
  <text x="205" y="266" font-size="9" fill="var(--muted)">notify_on_complete=True · 同一出口</text>
  <rect x="470" y="176" width="192" height="78" rx="10" fill="var(--red-soft)" stroke="var(--red)" stroke-width="1.5"/>
  <text x="478" y="196" font-size="10" font-weight="700" fill="var(--red)">闸① 生产端去重</text>
  <text x="478" y="213" font-size="9" fill="var(--ink)">kill 与 reader 线程都会调</text>
  <text x="478" y="228" font-size="9" fill="var(--ink)">pop 只有一方拿到非 None</text>
  <text x="478" y="243" font-size="9" fill="var(--ink)">只有它入队，否则报两遍</text>
  <line x1="470" y1="208" x2="457" y2="208" stroke="var(--red)" stroke-width="1.3" stroke-dasharray="3 3"/>
  <rect x="470" y="294" width="192" height="92" rx="10" fill="var(--red-soft)" stroke="var(--red)" stroke-width="1.5"/>
  <text x="478" y="314" font-size="10" font-weight="700" fill="var(--red)">闸② 消费端去重</text>
  <text x="478" y="331" font-size="9" fill="var(--ink)">_completion_consumed（已 wait/log）</text>
  <text x="478" y="346" font-size="9" fill="var(--ink)">_poll_observed（CLI 只读 poll）</text>
  <text x="478" y="361" font-size="9" fill="var(--ink)">命中 → drain 跳过该通知</text>
  <text x="478" y="376" font-size="9" fill="var(--ink)">免重复注入 [SYSTEM: ...]</text>
  <line x1="470" y1="340" x2="437" y2="362" stroke="var(--red)" stroke-width="1.3" stroke-dasharray="3 3"/>
</svg>
<div class="fig-cap"><b>生命周期 + 通知去重</b>：进程退出 / 被 kill → <span class="mono">_move_to_finished()</span> 锁内移表、置事件、写检查点；<strong>闸①</strong> <span class="mono">was_running</span> 让重复调用只入队一次，<strong>闸②</strong>消费端 <span class="mono">_completion_consumed</span> / <span class="mono">_poll_observed</span> 让已 wait / poll 过的通知被 drain 跳过——<strong>至多发一次</strong>。watch 限流满 <span class="mono">WATCH_STRIKE_LIMIT</span>=3 会禁 watch 并翻转 <span class="mono">notify_on_complete</span>，汇入同一出口。</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 360" role="img" aria-label="后台任务持久性三档对比。第一档进程内 background：delegate_task 后台或终端后台，_running 与 _finished 字典、输出缓冲、完成事件、reader 与 watcher 线程全在进程内存里，重启即全部丢失。第二档 detached：状态写在 processes.json 检查点，仅供网关崩溃恢复，重启后只重新登记 host-PID 仍存活且 start_time 匹配的进程，且只能报状态加 kill、读不回输出，是尽力而为而非持久态。第三档 cron：用 cron 定时任务或 terminal 后台加 notify_on_complete，把进程交给调度器与系统托管、完成回调，才是真正跨重启持久。底部主线：durability 几乎全是进程内幻觉，要跨重启用 cron 或终端后台，别押一个活在内存里的 future，呼应 ch26 的 E6">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">durability 三档 · 哪些状态能熬过一次重启</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">进程内 background（全在内存）/ detached（host-PID 尽力恢复）/ cron（真跨重启持久）</text>
  <rect x="20" y="70" width="200" height="214" rx="10" fill="var(--panel)" stroke="var(--line)"/>
  <rect x="20" y="70" width="200" height="44" rx="10" fill="var(--red-soft)" stroke="var(--red)" stroke-width="1.5"/>
  <text x="120" y="92" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--red)">进程内 background</text>
  <text x="120" y="107" text-anchor="middle" font-size="9" fill="var(--muted)">delegate_task(bg) / 终端后台</text>
  <text x="32" y="143" font-size="9.5" fill="var(--muted)">✗ _running / _finished 字典</text>
  <text x="32" y="169" font-size="9.5" fill="var(--muted)">✗ 输出缓冲 + 完成事件</text>
  <text x="32" y="195" font-size="9.5" fill="var(--muted)">✗ reader / watcher 线程</text>
  <rect x="38" y="246" width="164" height="28" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="120" y="264" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--red)">重启 = 内存态全丢</text>
  <rect x="240" y="70" width="200" height="214" rx="10" fill="var(--panel)" stroke="var(--line)"/>
  <rect x="240" y="70" width="200" height="44" rx="10" fill="var(--amber-soft)" stroke="var(--amber)" stroke-width="1.5"/>
  <text x="340" y="92" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--amber)">detached（host-PID）</text>
  <text x="340" y="107" text-anchor="middle" font-size="9" fill="var(--muted)">processes.json · 仅网关恢复</text>
  <text x="252" y="143" font-size="9.5" fill="var(--ink)">✓ host-PID + start_time 校验</text>
  <text x="252" y="169" font-size="9.5" fill="var(--ink)">✓ 报状态 + kill · detached</text>
  <text x="252" y="195" font-size="9.5" fill="var(--muted)">✗ 输出读不回</text>
  <rect x="258" y="246" width="164" height="28" rx="8" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="340" y="264" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--amber)">尽力而为 · 非持久态</text>
  <rect x="460" y="70" width="200" height="214" rx="10" fill="var(--panel)" stroke="var(--line)"/>
  <rect x="460" y="70" width="200" height="44" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>
  <text x="560" y="92" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--accent-ink)">cron（真持久）</text>
  <text x="560" y="107" text-anchor="middle" font-size="9" fill="var(--muted)">cron / terminal 后台</text>
  <text x="472" y="143" font-size="9.5" fill="var(--ink)">✓ cron 定时任务（ch21）</text>
  <text x="472" y="169" font-size="9.5" fill="var(--ink)">✓ terminal(background,notify)</text>
  <text x="472" y="195" font-size="9.5" fill="var(--ink)">✓ 交系统托管 · 完成回调</text>
  <rect x="478" y="246" width="164" height="28" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="560" y="264" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--accent-ink)">真 · 跨重启持久</text>
  <rect x="20" y="304" width="640" height="44" rx="10" fill="var(--panel-2)" stroke="var(--accent)"/>
  <text x="340" y="324" text-anchor="middle" font-size="10" font-weight="700" fill="var(--ink)">durability 几乎全是进程内幻觉——跨重启请用 cron 或 terminal 后台</text>
  <text x="340" y="340" text-anchor="middle" font-size="9" fill="var(--muted)">别押一个活在内存里的 future（呼应 ch26 · E6）</text>
</svg>
<div class="fig-cap"><b>durability 三档</b>：<strong>进程内 background</strong>（字典 / 缓冲 / 线程全在内存，重启即丢）、<strong>detached</strong>（<span class="mono">processes.json</span> 仅网关崩溃恢复，只认 host-PID、只能报状态 + kill，尽力而为）、<strong>cron</strong>（交调度器 / 系统托管，真跨重启持久）。要持久别押内存里的 future——呼应 ch26 · E6。</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 456" role="img" aria-label="单个后台进程的一生 · 五帧状态快照。帧1 spawn：进程启动入 _running 注册表，徽章 running，带 PID 与起始时间戳。帧2 running 监控：watcher 周期轮询，仍在 _running；旁支说明若配 watch_patterns 连满 WATCH_STRIKE_LIMIT 三个窗口则禁用 watch 并翻转 notify_on_complete。帧3 退出迁移：进程退出或被 kill 走 _move_to_finished，锁内把 session 从 _running 弹出塞进 _finished，置完成事件、写检查点，finished 保留 1800 秒即 30 分钟 TTL。帧4 去重 gate：判定 was_running 为真且不在 _completion_consumed 集合，认定完成仅此一次并加入该集合，重复调用只入队一次。帧5 只通知一次：把完成放进 completion_queue 触发一次新 agent turn 注入完成消息，之后只读状态查询走 _poll_observed 不消费，drain 跳过已 poll 的不重复通知。底部旁注：processes.json 检查点仅供 gateway 崩溃恢复重登记 detached 句柄、不是完成判定来源，判定全在内存 _running 与 _finished；两道闸分工，闸一 was_running 在生产端，kill 与 reader 线程都会调用但只有一方 pop 成功才入队，闸二 _completion_consumed 与 _poll_observed 在消费端，已 wait 或 poll 过的被 drain 跳过。">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">单个后台进程的一生 · 5 帧状态快照</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">从 spawn 到完成通知：看它一帧帧 running → 退出 → 迁移 → 过闸 → 只通知一次</text>
  <text x="650" y="34" text-anchor="middle" font-size="24">🔁</text>
  <text x="134.5" y="64" text-anchor="middle" font-size="9" fill="var(--accent-ink)">watcher 周期轮询</text>
  <text x="271.5" y="64" text-anchor="middle" font-size="9" fill="var(--ink)">进程退出 / 被 kill</text>
  <text x="408.5" y="64" text-anchor="middle" font-size="9" fill="var(--purple)">完成事件去重</text>
  <text x="545.5" y="64" text-anchor="middle" font-size="9" fill="var(--accent-ink)">触发新 turn</text>
  <rect x="16" y="72" width="100" height="240" rx="9" fill="var(--panel)" stroke="var(--line)"/>
  <text x="25" y="90" font-size="9.5" font-weight="700" fill="var(--ink)">帧1 · spawn</text>
  <text x="25" y="104" font-size="9" fill="var(--accent-ink)">启动 → 入 _running</text>
  <text x="25" y="124" font-size="9" fill="var(--muted)">① 状态徽章</text>
  <rect x="23" y="130" width="86" height="32" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="66" y="146" text-anchor="middle" font-size="9" font-weight="700" fill="var(--accent-ink)">running</text>
  <text x="66" y="157" text-anchor="middle" font-size="9" fill="var(--muted)">新建会话</text>
  <text x="25" y="180" font-size="9" fill="var(--muted)">② 注册表</text>
  <rect x="23" y="186" width="86" height="24" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="66" y="202" text-anchor="middle" font-size="9" font-weight="700" fill="var(--accent-ink)">_running{}</text>
  <text x="25" y="230" font-size="9" fill="var(--muted)">PID 4127</text>
  <text x="25" y="244" font-size="9" fill="var(--muted)">起始 18:06:41</text>
  <text x="25" y="258" font-size="9" fill="var(--muted)">notify=true</text>
  <text x="25" y="272" font-size="9" fill="var(--muted)">reader 泵输出缓冲</text>
  <rect x="153" y="72" width="100" height="240" rx="9" fill="var(--panel)" stroke="var(--line)"/>
  <text x="162" y="90" font-size="9.5" font-weight="700" fill="var(--ink)">帧2 · 监控</text>
  <text x="162" y="104" font-size="9" fill="var(--accent-ink)">watcher 周期轮询</text>
  <text x="162" y="124" font-size="9" fill="var(--muted)">① 状态徽章</text>
  <rect x="160" y="130" width="86" height="32" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="203" y="146" text-anchor="middle" font-size="9" font-weight="700" fill="var(--accent-ink)">running</text>
  <text x="203" y="157" text-anchor="middle" font-size="9" fill="var(--muted)">仍在跑</text>
  <text x="162" y="180" font-size="9" fill="var(--muted)">② 注册表</text>
  <rect x="160" y="186" width="86" height="24" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="203" y="202" text-anchor="middle" font-size="9" font-weight="700" fill="var(--accent-ink)">仍在 _running</text>
  <rect x="160" y="220" width="86" height="88" rx="6" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="203" y="236" text-anchor="middle" font-size="9" font-weight="700" fill="var(--amber)">旁支 · watch 降级</text>
  <text x="164" y="250" font-size="9" fill="var(--muted)">配 watch_patterns</text>
  <text x="164" y="264" font-size="9" fill="var(--muted)">连满 STRIKE=3 窗口</text>
  <text x="164" y="278" font-size="9" fill="var(--amber)">→ 禁 watch + 翻转</text>
  <text x="164" y="292" font-size="9" fill="var(--muted)">notify=true</text>
  <rect x="290" y="72" width="100" height="240" rx="9" fill="var(--panel)" stroke="var(--line)"/>
  <text x="299" y="90" font-size="9.5" font-weight="700" fill="var(--ink)">帧3 · 迁移</text>
  <text x="299" y="104" font-size="9" fill="var(--blue)">退出/被 kill → 迁移</text>
  <text x="299" y="124" font-size="9" fill="var(--muted)">① 状态徽章</text>
  <rect x="297" y="130" width="86" height="32" rx="6" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="340" y="146" text-anchor="middle" font-size="9" font-weight="700" fill="var(--blue)">finished</text>
  <text x="340" y="157" text-anchor="middle" font-size="9" fill="var(--muted)">完成事件已置</text>
  <text x="299" y="180" font-size="9" fill="var(--muted)">② 注册表</text>
  <rect x="297" y="186" width="86" height="24" rx="6" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="340" y="202" text-anchor="middle" font-size="9" font-weight="700" fill="var(--blue)">进入 _finished{}</text>
  <text x="299" y="230" font-size="9" fill="var(--muted)">锁内 pop 出表</text>
  <text x="299" y="244" font-size="9" fill="var(--muted)">置事件 + 写检查点</text>
  <text x="299" y="258" font-size="9" fill="var(--muted)">finished 留 1800s</text>
  <text x="299" y="272" font-size="9" fill="var(--muted)">= 30min TTL</text>
  <rect x="427" y="72" width="100" height="240" rx="9" fill="var(--panel)" stroke="var(--line)"/>
  <text x="436" y="90" font-size="9.5" font-weight="700" fill="var(--ink)">帧4 · 去重 gate</text>
  <text x="436" y="104" font-size="9" fill="var(--purple)">认定完成 · 仅一次</text>
  <text x="436" y="124" font-size="9" fill="var(--muted)">① 状态徽章</text>
  <rect x="434" y="130" width="86" height="32" rx="6" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="477" y="146" text-anchor="middle" font-size="9" font-weight="700" fill="var(--purple)">completion ✓</text>
  <text x="477" y="157" text-anchor="middle" font-size="9" fill="var(--muted)">首次认定</text>
  <text x="436" y="180" font-size="9" fill="var(--muted)">② 注册表</text>
  <rect x="434" y="186" width="86" height="24" rx="6" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="477" y="202" text-anchor="middle" font-size="9" font-weight="700" fill="var(--blue)">in _finished</text>
  <text x="436" y="230" font-size="9" fill="var(--muted)">was_running=true</text>
  <text x="436" y="244" font-size="9" fill="var(--muted)">且 ∉ consumed 集</text>
  <text x="436" y="258" font-size="9" fill="var(--purple)">→ 认定仅此一次</text>
  <text x="436" y="272" font-size="9" fill="var(--muted)">加入集合 · 只入队一次</text>
  <rect x="564" y="72" width="100" height="240" rx="9" fill="var(--panel)" stroke="var(--line)"/>
  <text x="573" y="90" font-size="9.5" font-weight="700" fill="var(--ink)">帧5 · 通知</text>
  <text x="573" y="104" font-size="9" fill="var(--accent-ink)">入队 → 一次新 turn</text>
  <text x="573" y="124" font-size="9" fill="var(--muted)">① 状态徽章</text>
  <rect x="571" y="130" width="86" height="32" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="614" y="146" text-anchor="middle" font-size="9" font-weight="700" fill="var(--accent-ink)">notified</text>
  <text x="614" y="157" text-anchor="middle" font-size="9" fill="var(--muted)">注入完成消息</text>
  <text x="573" y="180" font-size="9" fill="var(--muted)">② 注册表</text>
  <rect x="571" y="186" width="86" height="24" rx="6" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="614" y="202" text-anchor="middle" font-size="9" font-weight="700" fill="var(--blue)">in _finished</text>
  <text x="573" y="230" font-size="9" fill="var(--muted)">→ completion_queue</text>
  <text x="573" y="244" font-size="9" fill="var(--muted)">触发 1 次新 turn</text>
  <text x="573" y="258" font-size="9" fill="var(--muted)">之后只读查询走</text>
  <text x="573" y="272" font-size="9" fill="var(--muted)">_poll_observed 不消费</text>
  <line x1="117" y1="200" x2="144" y2="200" stroke="var(--accent)" stroke-width="1.6"/>
  <path d="M152,200 L144,195 L144,205 Z" fill="var(--accent)"/>
  <line x1="254" y1="200" x2="281" y2="200" stroke="var(--blue)" stroke-width="1.6"/>
  <path d="M289,200 L281,195 L281,205 Z" fill="var(--blue)"/>
  <line x1="391" y1="200" x2="418" y2="200" stroke="var(--purple)" stroke-width="1.6"/>
  <path d="M426,200 L418,195 L418,205 Z" fill="var(--purple)"/>
  <line x1="528" y1="200" x2="555" y2="200" stroke="var(--accent)" stroke-width="1.6"/>
  <path d="M563,200 L555,195 L555,205 Z" fill="var(--accent)"/>
  <rect x="10" y="324" width="660" height="122" rx="9" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="24" y="346" font-size="9.5" font-weight="700" fill="var(--ink)">旁注 · 检查点不是判定来源 · 两道闸的分工（图中数字只用真实常量 1800s/30min · STRIKE=3）</text>
  <circle cx="26" cy="368" r="4" fill="var(--blue)"/>
  <text x="38" y="372" font-size="9" fill="var(--muted)">① processes.json 检查点仅供 gateway 崩溃恢复重登记 detached 句柄——不是完成判定来源</text>
  <text x="38" y="386" font-size="9" fill="var(--muted)">完成判定全在内存的 _running / _finished 两个字典里，检查点不参与判定</text>
  <circle cx="26" cy="408" r="4" fill="var(--purple)"/>
  <text x="38" y="412" font-size="9" fill="var(--muted)">② 闸① was_running（生产端 · kill 与 reader 线程都会调用，但只有一方 pop 成功才入队）</text>
  <text x="38" y="426" font-size="9" fill="var(--muted)">闸② _completion_consumed / _poll_observed（消费端 · 已 wait / poll 过的被 drain 跳过，不重复注入）</text>
</svg>
<div class="fig-cap"><b>单进程逐帧一生</b>：5 帧追一个 <span class="mono">background=true</span> 进程——<span class="mono">spawn</span> 入 <span class="mono">_running</span> → <span class="mono">running</span> 监控 → 退出走 <span class="mono">_move_to_finished</span> 迁进 <span class="mono">_finished</span> → <strong>去重 gate</strong> 认定完成仅一次 → <span class="mono">completion_queue</span> 触发<strong>一次</strong>新 turn。两道闸只在 <span class="mono">帧4</span> 这一帧与底部旁注出现：闸① <span class="mono">was_running</span> 生产端、闸② <span class="mono">_completion_consumed</span> / <span class="mono">_poll_observed</span> 消费端；检查点 <span class="mono">processes.json</span> 只为崩溃恢复、<strong>不参与</strong>完成判定。</div>
</div>

<p>停讲完、看讲完，剩最后一套：一次「存」怎么做到要么<strong>整体生效</strong>、要么<strong>完全没发生</strong>——以及这份原子保证，怎么会因为一个<strong>临时文件放错目录</strong>就整盘崩掉。</p>

<h3>🔬 28.3 · 原子文件编辑：同目录 temp + rename，写后再读回校验</h3>
<p>三套机制的最后一套是<strong>落盘</strong>。Hermes 的文件能力收在四个工具里——<span class="mono">read_file</span> / <span class="mono">write_file</span> / <span class="mono">patch</span>（替换）/ <span class="mono">search</span>，全部由 <span class="mono">tools/file_operations.py</span> 的 shell 后端实现。其中<strong>会改盘的两个</strong>（write 与 patch）都不直接覆盖目标文件，而是统一走一个私有方法 <span class="mono">_atomic_write()</span>：<strong>先在目标的同一个目录里建一个临时文件、把新内容写进去、再用一次 rename 把它原子地换到目标位置</strong>。</p>
<p><span class="mono">_atomic_write()</span> 的实现是一段全引号转义的 shell 脚本：用 <span class="mono">mktemp -p "$d"</span> 把临时文件落在<strong>目标自己的目录</strong> <span class="mono">d = dirname(path)</span>（不是 <span class="mono">/tmp</span>），内容经 <strong>stdin</strong> 流入（绕开 ARG_MAX），<span class="mono">cat &gt; "$tmp"</span> 写好草稿后，再 <span class="mono">mv -f "$tmp" "$t"</span> 一步换上。三个细节值得记：① 它<strong>不是</strong> <span class="mono">os.replace()</span> 这类 Python 调用，而是落到真实的 shell <span class="mono">mv</span>（语义即同一文件系统内的原子 rename）；② 一个 <span class="mono">trap 'rm -f "$tmp"' EXIT</span> 保证<strong>任何失败路径</strong>（cat 失败、mv 失败、被信号打断）都会清掉临时文件，绝不在用户数据旁边留下半个 <span class="mono">.hermes-tmp</span> 残渣；③ 写之前还会 <span class="mono">stat</span> + <span class="mono">chmod</span> 尽力把目标原有权限复制到临时文件上，避免原子换上后<strong>悄悄放宽或收紧</strong>权限。</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">tools/file_operations.py:937 · 简化</span></div><pre>    def _atomic_write(self, path: str, content: str) -&gt; "ExecuteResult":
        q_path = self._escape_shell_arg(path)
        parent = os.path.dirname(path) or "."
        q_parent = self._escape_shell_arg(parent)
        tmpl = self._escape_shell_arg(".hermes-tmp.XXXXXX")
        script = (
            "set -e; "
            f"d={q_parent}; t={q_path}; "
            'tmp="$(mktemp -p "$d" ' + tmpl + ' 2&gt;/dev/null '
            '|| mktemp "$d/.hermes-tmp.$$.XXXXXX" 2&gt;/dev/null '
            '|| { tmp="$d/.hermes-tmp.$$"; : &gt; "$tmp" &amp;&amp; echo "$tmp"; })"; '
            "trap 'rm -f \"$tmp\"' EXIT; "
            'cat &gt; "$tmp"; '
            'mv -f "$tmp" "$t"; '
            "trap - EXIT"
        )
        return self._exec(script, stdin_data=content)</pre></div>
<p><strong>核心坑就在这里：整套原子性，全挂在「临时文件与目标同目录」这一个不起眼的前提上。</strong>rename 只有在<strong>同一个文件系统内</strong>才是原子的——内核只是把一个目录项从旧 inode 改指向新 inode，一步到位。一旦临时文件落在<strong>别的文件系统</strong>（比如把草稿写到 <span class="mono">/tmp</span> 再 mv 回项目目录），<span class="mono">mv</span> 没法做真 rename，只能<strong>降级成 copy 到目标 + unlink 源</strong>两步；要是在 copy 中途崩溃 / 断电，目标就只写了一半，留下一个<strong>撕裂的损坏文件</strong>——恰恰是原子写本想消灭的失败。所以 <span class="mono">mktemp -p "$d"</span> 里那个 <span class="mono">-p "$d"</span> 是 <strong>load-bearing</strong> 的，不是随手的选择。</p>
<p><span class="mono">patch</span>（替换）在 <span class="mono">_atomic_write</span> 之上又加了一道<strong>写后校验</strong>。它先把文件读进来、剥掉可能的 UTF-8 BOM，用<strong>模糊匹配</strong>定位 <span class="mono">old_string</span>——除非 <span class="mono">replace_all=True</span>，否则要求匹配<strong>唯一</strong>，命中多处或零处都直接报错；替换后按文件<strong>原有的行尾</strong>（LF / CRLF）规整再写回（写出去时把 BOM 补回，往返保留标记）。落盘之后，它<strong>再把文件读回来、逐字节和打算写入的内容比对</strong>：对不上就报「<span class="mono">The patch did not persist</span>」、要求重读重试。这道校验专抓<strong>静默落盘失败</strong>——后端 FS 怪癖、截断的管道，<strong>以及和另一个任务的并发改动</strong>：若在 patch 写盘到 re-read 之间，别的编辑动了同一个文件，re-read 出来的字节就和本次的 <span class="mono">new_content</span> 不一致，<strong>校验失败</strong>，patch 不会假报成功。</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">tools/file_operations.py:1534</span></div><pre>        # Post-write verification — re-read the file and confirm the bytes we
        # intended to write actually landed. Catches silent persistence
        # failures (backend FS oddities, race with another task, truncated
        # pipe, etc.) that would otherwise return success-with-diff while the
        # file is unchanged on disk.
        verify_cmd = f"cat {self._escape_shell_arg(path)} 2&gt;/dev/null"
        verify_result = self._exec(verify_cmd)
        if verify_result.exit_code != 0:
            return PatchResult(error=f"Post-write verification failed: could not re-read {path}")</pre></div>
<p>四个工具周围还有一圈防护：<strong>路径安全 deny-list</strong> 在 write / patch 前拦掉敏感文件——<span class="mono">~/.ssh/{id_rsa,authorized_keys,config}</span>、各 profile 与顶层的 <span class="mono">.env</span>、<span class="mono">.git-credentials</span>、<span class="mono">/etc/{passwd,shadow,sudoers}</span> 以及 <span class="mono">~/.aws</span>、<span class="mono">/etc/systemd</span> 等前缀，免得一次误写泄露凭证或改坏系统。<span class="mono">read_file</span> 默认<strong>分页</strong>（offset / limit，默认 500 行、上限 2000），并带<strong>二进制探测</strong>——非打印字符超过 30% 判为二进制、不返回正文，图片类扩展名则转 base64 走视觉通道。<span class="mono">search</span> 是<strong>行级</strong>的（<span class="mono">output_mode="content"</span> 给出命中行 + 可选上下文），内容查找与文件名查找分开。这些都不改变那条主线：<strong>每一次写盘，都先把「完整的新文件」准备好，再用一次原子动作让它整体生效——读者永远看不到中间态。</strong></p>

<div class="figure">
<svg viewBox="0 0 680 466" role="img" aria-label="安全文件编辑管线图。竖向主线自上而下：目标文件 t 所在的同一目录 d 等于 dirname(path)，先用 mktemp -p 在该目录里建一个隐藏 temp 文件 .hermes-tmp.XXXXXX，把新内容 cat 写进 temp 草稿，patch 路径随后再把文件读回并逐字节与打算写入的内容比对校验，校验通过才用 mv -f 把 temp 原子 rename 换到目标位置，读者于是要么看到旧文件、要么看到完整的新文件，永不读到撕裂的中间态。右侧失败分支：校验失败或写入异常时 trap 会 rm -f 删掉 temp，原文件保持不动完成回滚。左侧注记：temp 与目标同目录即同一文件系统，mv 才是真 rename。">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">安全编辑管线 · 同目录 temp → 写 → 校验 → 原子 rename</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">草稿写进同目录 temp，校验通过再 mv -f 原子换上；任一步失败则回滚，原文件不动</text>
  <rect x="130" y="64" width="200" height="44" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="230" y="85" text-anchor="middle" font-size="12" font-weight="700" fill="var(--blue)">① 目标文件 t</text>
  <text x="230" y="101" text-anchor="middle" font-size="9" fill="var(--muted)">同目录 d = dirname(path)</text>
  <line x1="230" y1="110" x2="230" y2="124" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M230,132 L225,123 L235,123 Z" fill="var(--muted)"/>
  <rect x="130" y="132" width="200" height="50" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>
  <text x="230" y="153" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--accent-ink)">② mktemp -p "$d"</text>
  <text x="230" y="170" text-anchor="middle" font-size="9" fill="var(--muted)">同目录建隐藏 temp · .hermes-tmp.XXXXXX</text>
  <line x1="230" y1="184" x2="230" y2="198" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M230,206 L225,197 L235,197 Z" fill="var(--muted)"/>
  <text x="14" y="150" font-size="9.5" font-weight="700" fill="var(--accent-ink)">同目录 = 同 FS</text>
  <text x="14" y="165" font-size="9" fill="var(--muted)">mv 才是真 rename</text>
  <text x="14" y="178" font-size="9" fill="var(--muted)">（详见下图 ⑬）</text>
  <line x1="120" y1="156" x2="128" y2="156" stroke="var(--accent)" stroke-width="1.4"/>
  <rect x="130" y="206" width="200" height="44" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="230" y="227" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">③ cat &gt; "$tmp" 写草稿</text>
  <text x="230" y="243" text-anchor="middle" font-size="9" fill="var(--muted)">内容走 stdin · 无 ARG_MAX 限制</text>
  <line x1="230" y1="252" x2="230" y2="266" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M230,274 L225,265 L235,265 Z" fill="var(--muted)"/>
  <rect x="130" y="274" width="200" height="58" rx="10" fill="var(--amber-soft)" stroke="var(--amber)" stroke-width="2"/>
  <text x="230" y="295" text-anchor="middle" font-size="12" font-weight="700" fill="var(--amber)">④ 读回验证字节</text>
  <text x="230" y="311" text-anchor="middle" font-size="9" fill="var(--ink)">patch：re-read 比对打算写入的内容</text>
  <text x="230" y="325" text-anchor="middle" font-size="9" fill="var(--ink)">捕获静默落盘失败 / 并发改动</text>
  <line x1="230" y1="332" x2="230" y2="346" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M230,354 L225,345 L235,345 Z" fill="var(--muted)"/>
  <text x="238" y="345" font-size="9" fill="var(--muted)">验证通过</text>
  <rect x="458" y="274" width="206" height="58" rx="10" fill="var(--red-soft)" stroke="var(--red)" stroke-width="1.5"/>
  <text x="466" y="294" font-size="10" font-weight="700" fill="var(--red)">失败分支 · 异常 / 校验不过</text>
  <text x="466" y="311" font-size="9" fill="var(--ink)">trap 'rm -f "$tmp"' 删掉 temp</text>
  <text x="466" y="326" font-size="9" fill="var(--ink)">原文件保持不动（回滚）</text>
  <line x1="330" y1="303" x2="450" y2="303" stroke="var(--red)" stroke-width="1.3" stroke-dasharray="3 3"/>
  <path d="M458,303 L449,298 L449,308 Z" fill="var(--red)"/>
  <rect x="130" y="354" width="200" height="50" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="230" y="375" text-anchor="middle" font-size="12" font-weight="700" fill="var(--accent-ink)">⑤ mv -f "$tmp" "$t"</text>
  <text x="230" y="391" text-anchor="middle" font-size="9" fill="var(--muted)">原子 rename · 一步换上目标</text>
  <line x1="230" y1="406" x2="230" y2="420" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M230,428 L225,419 L235,419 Z" fill="var(--muted)"/>
  <rect x="130" y="428" width="200" height="34" rx="9" fill="var(--panel-2)" stroke="var(--accent)" stroke-width="1.5"/>
  <text x="230" y="449" text-anchor="middle" font-size="10" font-weight="700" fill="var(--ink)">⑥ 读者：旧 或 完整新（永不撕裂）</text>
</svg>
<div class="fig-cap"><b>安全编辑管线</b>：write / patch 走 <span class="mono">_atomic_write</span>——<span class="mono">mktemp -p "$d"</span> 在<strong>同目录</strong>建 temp → <span class="mono">cat</span> 写草稿 →（patch 还会<strong>读回逐字节校验</strong>）→ <span class="mono">mv -f</span> 原子 rename 换上；任一步失败，<span class="mono">trap</span> 删 temp、<strong>原文件不动</strong>。读者要么见旧、要么见完整新，<strong>永不撕裂</strong>。</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 360" role="img" aria-label="跨文件系统 rename 破坏原子性的对比图。左列同一文件系统：temp 与目标同目录，rename 是单步原子操作，内核只切换目录项指向新 inode，读者要么看到旧 inode 要么看到新 inode，断电或崩溃后原文件完好，结论是原子且永不撕裂。右列跨文件系统：temp 落在别的文件系统比如 /tmp，mv 无法做真 rename 只能退化为先 copy 到目标再 unlink 源的两步操作，一旦在 copy 中途崩溃目标就只写了一半，留下撕裂的半个文件，结论是非原子且可能损坏。底部结论条：所以 temp 必须用 mktemp -p 落在目标自己的目录，保证与目标同一文件系统、让 mv 成为真正的原子 rename。">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">跨 FS rename 破原子性 · 为什么 temp 必须与目标同目录</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">同 FS = 一步原子指针切换；跨 FS = mv 降级为 copy + unlink 两步，中途崩溃留半个文件</text>
  <rect x="20" y="70" width="300" height="206" rx="10" fill="var(--panel)" stroke="var(--line)"/>
  <rect x="20" y="70" width="300" height="44" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>
  <text x="170" y="92" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--accent-ink)">同 FS · 真原子 rename</text>
  <text x="170" y="107" text-anchor="middle" font-size="9" fill="var(--muted)">temp 与目标同目录（mktemp -p "$d"）</text>
  <text x="34" y="140" font-size="9.5" fill="var(--ink)">① rename() = 单步切换目录项</text>
  <text x="34" y="164" font-size="9.5" fill="var(--ink)">② 指向新 inode，旧 inode 释放</text>
  <text x="34" y="188" font-size="9.5" fill="var(--ink)">③ 读者：要么旧、要么新 inode</text>
  <text x="34" y="212" font-size="9.5" fill="var(--ink)">④ 断电 / 崩溃：原文件完好</text>
  <rect x="38" y="234" width="264" height="30" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="170" y="253" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--accent-ink)">✓ 原子 · 永不读到撕裂中间态</text>
  <rect x="360" y="70" width="300" height="206" rx="10" fill="var(--panel)" stroke="var(--line)"/>
  <rect x="360" y="70" width="300" height="44" rx="10" fill="var(--red-soft)" stroke="var(--red)" stroke-width="1.5"/>
  <text x="510" y="92" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--red)">跨 FS · mv 降级 copy+unlink</text>
  <text x="510" y="107" text-anchor="middle" font-size="9" fill="var(--muted)">temp 落在别的文件系统（如 /tmp）</text>
  <text x="374" y="140" font-size="9.5" fill="var(--ink)">① rename 跨设备失败 → mv 兜底</text>
  <text x="374" y="164" font-size="9.5" fill="var(--ink)">② 退化为 copy 到目标 + unlink 源</text>
  <text x="374" y="188" font-size="9.5" fill="var(--ink)">③ copy 中途崩溃：目标只写一半</text>
  <text x="374" y="212" font-size="9.5" fill="var(--ink)">④ 留下撕裂 / 半个损坏文件</text>
  <rect x="378" y="234" width="264" height="30" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="510" y="253" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--red)">✗ 非原子 · 可能读到损坏文件</text>
  <rect x="20" y="296" width="640" height="48" rx="10" fill="var(--panel-2)" stroke="var(--accent)"/>
  <text x="340" y="317" text-anchor="middle" font-size="10" font-weight="700" fill="var(--ink)">结论：temp 必须 mktemp -p 落在目标自己的目录 → 同一 FS、让 mv 成为真原子 rename</text>
  <text x="340" y="334" text-anchor="middle" font-size="9" fill="var(--muted)">temp 的位置是 load-bearing 的——跨目录省事，却把原子保证悄悄换成了「可能半写」</text>
</svg>
<div class="fig-cap"><b>跨 FS rename 破原子性</b>：<strong>同目录 = 同文件系统</strong>，<span class="mono">mv</span> 是一步原子 rename（切换目录项指向新 inode），崩溃也只见旧或完整新；<strong>跨文件系统</strong> <span class="mono">mv</span> 降级为 <span class="mono">copy + unlink</span> 两步，中途崩溃留半个文件。所以 temp 必须 <span class="mono">mktemp -p "$d"</span> 落在<strong>目标自己的目录</strong>——位置是 load-bearing 的。</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 416" role="img" aria-label="文件系统逐帧状态快照：_atomic_write 覆盖 foo.py，沿时间线画同一个项目目录里每帧此刻有哪些文件、各是旧内容还是新内容。帧1 准备，mktemp -p &quot;$d&quot; 在 foo.py 同目录新建空临时文件 .hermes-tmp.XXXXXX，foo.py 仍是旧内容完好。帧2 写临时，cat 把新内容全部写进 .hermes-tmp.XXXXXX，foo.py 仍是旧内容完好，此刻是崩溃安全点：崩溃只丢临时文件、原文件不动。帧3 原子替换，mv -f 把临时文件原子 rename 成 foo.py 一步到位，目录里 foo.py 现为新内容、临时文件消失，没有半截。帧4 读回校验，patch 路径写完用 cat 读回 foo.py 逐字节比对确已落盘，不一致则报错回滚。底部旁注两条：一用 shell mv -f 统一走终端后端、docker 与 ssh 也一致，而非 os.replace；二位置是 load-bearing 的，mktemp -p &quot;$d&quot; 必须落目标同目录同文件系统，跨文件系统时 mv 降级为 copy 加 unlink 两步、中途崩溃留半个文件，破坏原子性。任一帧崩溃 foo.py 都不会半截。">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">文件系统逐帧状态 · 原子写任一帧崩溃 foo.py 都不半截</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">_atomic_write 覆盖 foo.py：每帧画此刻目录里有哪些文件、各是旧 / 新 / 空</text>
  <text x="600" y="34" font-size="22">📸</text>

  <rect x="10" y="64" width="128" height="240" rx="10" fill="var(--panel)" stroke="var(--line)"/>
  <text x="18" y="84" font-size="9.5" font-weight="700" fill="var(--ink)">帧1 · 准备</text>
  <text x="18" y="99" font-size="9" fill="var(--blue)">同目录建空 temp</text>
  <rect x="18" y="106" width="112" height="148" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="24" y="122" font-size="9" fill="var(--muted)">📁 项目目录/</text>
  <rect x="24" y="128" width="100" height="46" rx="6" fill="var(--panel)" stroke="var(--line)"/>
  <text x="30" y="144" font-size="9" fill="var(--ink)">foo.py</text>
  <rect x="30" y="150" width="88" height="16" rx="3" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="74" y="162" text-anchor="middle" font-size="9" fill="var(--accent-ink)">旧内容 · 完好</text>
  <rect x="24" y="180" width="100" height="46" rx="6" fill="var(--panel)" stroke="var(--line)"/>
  <text x="30" y="196" font-size="9" fill="var(--ink)">.hermes-tmp.XXXXXX</text>
  <rect x="30" y="202" width="88" height="16" rx="3" fill="var(--panel)" stroke="var(--blue)" stroke-dasharray="4 3"/>
  <text x="74" y="214" text-anchor="middle" font-size="9" fill="var(--blue)">空</text>
  <rect x="18" y="262" width="112" height="38" rx="7" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="24" y="278" font-size="9" fill="var(--blue)">mktemp -p &quot;$d&quot;</text>
  <text x="24" y="292" font-size="9" fill="var(--muted)">落 foo.py 同目录</text>

  <line x1="140" y1="186" x2="178" y2="186" stroke="var(--line)" stroke-width="1.8"/>
  <path d="M184,186 L176,182 L176,190 Z" fill="var(--line)"/>
  <text x="162" y="168" text-anchor="middle" font-size="9" fill="var(--blue)">cat &gt; tmp</text>
  <text x="162" y="180" text-anchor="middle" font-size="9" fill="var(--muted)">写入</text>

  <rect x="187" y="64" width="128" height="240" rx="10" fill="var(--panel)" stroke="var(--line)"/>
  <text x="195" y="84" font-size="9.5" font-weight="700" fill="var(--ink)">帧2 · 写临时</text>
  <text x="195" y="99" font-size="9" fill="var(--blue)">新内容全写进 temp</text>
  <rect x="195" y="106" width="112" height="148" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="201" y="122" font-size="9" fill="var(--muted)">📁 项目目录/</text>
  <rect x="201" y="128" width="100" height="46" rx="6" fill="var(--panel)" stroke="var(--line)"/>
  <text x="207" y="144" font-size="9" fill="var(--ink)">foo.py</text>
  <rect x="207" y="150" width="88" height="16" rx="3" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="251" y="162" text-anchor="middle" font-size="9" fill="var(--accent-ink)">旧 · 仍完好</text>
  <rect x="201" y="180" width="100" height="46" rx="6" fill="var(--panel)" stroke="var(--blue)"/>
  <text x="207" y="196" font-size="9" fill="var(--ink)">.hermes-tmp.XXXXXX</text>
  <rect x="207" y="202" width="88" height="16" rx="3" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="251" y="214" text-anchor="middle" font-size="9" fill="var(--blue)">新内容 · 全部</text>
  <rect x="195" y="262" width="112" height="38" rx="7" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="201" y="278" font-size="9" font-weight="700" fill="var(--red)">⛨ 崩溃安全点</text>
  <text x="201" y="292" font-size="9" fill="var(--muted)">崩溃只丢 temp · foo.py 不动</text>

  <line x1="317" y1="186" x2="355" y2="186" stroke="var(--line)" stroke-width="1.8"/>
  <path d="M361,186 L353,182 L353,190 Z" fill="var(--line)"/>
  <text x="339" y="168" text-anchor="middle" font-size="9" fill="var(--accent-ink)">mv -f</text>
  <text x="339" y="180" text-anchor="middle" font-size="9" fill="var(--muted)">tmp→foo.py</text>

  <rect x="364" y="64" width="128" height="240" rx="10" fill="var(--panel)" stroke="var(--line)"/>
  <text x="372" y="84" font-size="9.5" font-weight="700" fill="var(--ink)">帧3 · 原子替换</text>
  <text x="372" y="99" font-size="9" fill="var(--accent-ink)">mv -f 一步换上</text>
  <rect x="372" y="106" width="112" height="148" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="378" y="122" font-size="9" fill="var(--muted)">📁 项目目录/</text>
  <rect x="378" y="128" width="100" height="46" rx="6" fill="var(--panel)" stroke="var(--accent)"/>
  <text x="384" y="144" font-size="9" fill="var(--ink)">foo.py</text>
  <rect x="384" y="150" width="88" height="16" rx="3" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="428" y="162" text-anchor="middle" font-size="9" fill="var(--accent-ink)">新 · 已就位</text>
  <rect x="378" y="180" width="100" height="46" rx="6" fill="var(--panel)" stroke="var(--line)" stroke-dasharray="4 3"/>
  <text x="384" y="196" font-size="9" fill="var(--muted)">.hermes-tmp.XXXXXX</text>
  <text x="428" y="214" text-anchor="middle" font-size="9" fill="var(--muted)">(已 rename 消失)</text>
  <rect x="372" y="262" width="112" height="38" rx="7" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="378" y="278" font-size="9" font-weight="700" fill="var(--accent-ink)">mv -f 原子 rename</text>
  <text x="378" y="292" font-size="9" fill="var(--muted)">一步到位 · 无半截</text>

  <line x1="494" y1="186" x2="532" y2="186" stroke="var(--line)" stroke-width="1.8"/>
  <path d="M538,186 L530,182 L530,190 Z" fill="var(--line)"/>
  <text x="516" y="168" text-anchor="middle" font-size="9" fill="var(--purple)">patch 路径</text>
  <text x="516" y="180" text-anchor="middle" font-size="9" fill="var(--muted)">cat 读回</text>

  <rect x="541" y="64" width="128" height="240" rx="10" fill="var(--panel)" stroke="var(--line)"/>
  <text x="549" y="84" font-size="9.5" font-weight="700" fill="var(--ink)">帧4 · 读回校验</text>
  <text x="549" y="99" font-size="9" fill="var(--purple)">cat 读回逐字节比对</text>
  <rect x="549" y="106" width="112" height="148" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="555" y="122" font-size="9" fill="var(--muted)">📁 项目目录/</text>
  <rect x="555" y="128" width="100" height="46" rx="6" fill="var(--panel)" stroke="var(--purple)"/>
  <text x="561" y="144" font-size="9" fill="var(--ink)">foo.py ✓</text>
  <rect x="561" y="150" width="88" height="16" rx="3" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="605" y="162" text-anchor="middle" font-size="9" fill="var(--accent-ink)">新内容 · 已落盘</text>
  <rect x="555" y="180" width="100" height="46" rx="6" fill="var(--panel)" stroke="var(--line)" stroke-dasharray="4 3"/>
  <text x="561" y="196" font-size="9" fill="var(--muted)">(无临时文件)</text>
  <text x="605" y="214" text-anchor="middle" font-size="9" fill="var(--purple)">cat foo.py == 期望</text>
  <rect x="549" y="262" width="112" height="38" rx="7" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="555" y="278" font-size="9" font-weight="700" fill="var(--purple)">✓ verify 读回比对</text>
  <text x="555" y="292" font-size="9" fill="var(--muted)">不一致 → 报错回滚</text>

  <rect x="10" y="312" width="662" height="98" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="24" y="331" font-size="9.5" font-weight="700" fill="var(--ink)">旁注 · 两个不能省的前提</text>
  <circle cx="26" cy="350" r="4" fill="var(--accent)"/>
  <text x="38" y="354" font-size="9" fill="var(--muted)">① 用 shell mv -f 统一走终端后端（docker / ssh 也一致），而非 os.replace —— 同一条原子路径</text>
  <circle cx="26" cy="378" r="4" fill="var(--red)"/>
  <text x="38" y="378" font-size="9" fill="var(--muted)">② 位置是 load-bearing 的：mktemp -p &quot;$d&quot; 必须落目标同目录 / 同 FS；</text>
  <text x="38" y="394" font-size="9" fill="var(--muted)">　 跨 FS 时 mv 降级 copy + unlink 两步、中途崩溃留半个文件 → 破坏原子性</text>
</svg>
<div class="fig-cap"><b>文件系统逐帧状态</b>：沿时间看同一个目录的 4 帧文件快照——<span class="mono">帧1</span> <span class="mono">mktemp -p &quot;$d&quot;</span> 建同目录空 temp、<span class="mono">foo.py</span> 旧内容完好 → <span class="mono">帧2</span> 新内容全写进 temp、<span class="mono">foo.py</span> <strong>仍完好</strong>（<span style="color:var(--red)">⛨ 崩溃安全点</span>：崩溃只丢 temp）→ <span class="mono">帧3</span> <span class="mono">mv -f</span> 一步原子 rename、<span class="mono">foo.py</span> 变新内容、temp 消失 → <span class="mono">帧4</span>（patch 路径）<span class="mono">cat</span> 读回逐字节<strong>校验</strong>。看点：<strong>任一帧崩溃 <span class="mono">foo.py</span> 都不半截</strong>；前提是 temp 同目录 + 用 <span class="mono">mv -f</span> 而非 <span class="mono">os.replace</span>。</div>
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 异步世界里的正确性边界</div>
  本章三套机制——<strong>中断传播</strong>、<strong>后台进程生命周期</strong>、<strong>原子文件编辑</strong>——表面分管「停 / 看 / 存」三件互不相干的事，底层却守着同一条线：<strong>在一个异步、连续运行、随时可能被打断或重启的世界里，把「看起来完成」和「真的完成」死死焊在一起。</strong>
  <p style="margin:.5rem 0 0"><strong>三者各自守的边界：</strong>① 中断是一份<strong>协作式契约</strong>——置标志、在循环边界收下、对子代理显式扇出，谁都不许从外部硬杀线程，于是「停」既<strong>及时</strong>又<strong>不撕裂</strong>正在执行的工具；② 后台进程给出<strong>诚实的状态</strong>——完成至多报一次（生产端 <span class="mono">was_running</span> + 消费端 <span class="mono">_completion_consumed</span> 两道闸），且<strong>不把进程内幻觉谎称为持久</strong>；③ 落盘给出<strong>原子保证</strong>——同目录 temp + rename + 写后校验，读者要么见旧、要么见完整新。</p>
  <p style="margin:.5rem 0 0"><strong>呼应全书两条主线：</strong>这正是<strong>韧性</strong>的地基——失败有界、可回滚（<span class="mono">trap</span> 删 temp）、可恢复（detached / cron）、可纠错（re-read 校验）；也守着<strong>窄腰</strong>：核心只暴露 <span class="mono">/stop</span>、查状态、原子写这几个最小原语，真正的复杂度全下沉到循环边界、进程注册表与一段 shell 脚本里。三处「看起来完成 ≠ 真的完成」的缝，正是<strong>「自主、连续运行」可靠性的地基</strong>。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>中断是协作式、不是抢占式</strong>：<span class="mono">/stop</span> 只置一面 <span class="mono">_interrupt_requested</span> 标志，主循环在<strong>迭代边界</strong>轮询收下；Python 杀不了线程，流式回调 / 非流式后台检查 / retry 退避（每 <strong>200ms</strong>）都靠<strong>自愿轮询</strong>。中断对<strong>子代理是显式手工扇出</strong>——遍历 <span class="mono">_active_children</span> 逐个 <span class="mono">child.interrupt()</span>，漏登记或异步 detach 就<strong>静默断链</strong>。</li>
    <li><strong>后台 durability 多是进程内幻觉</strong>：<span class="mono">_running</span> / <span class="mono">_finished</span> 字典、输出缓冲、reader / watcher 线程全在内存，重启即丢；detached 恢复只认 host-PID + <span class="mono">start_time</span> 校验、只能报状态 + kill。要<strong>真跨重启</strong>用 <span class="mono">cron</span> 或 <span class="mono">terminal(background, notify_on_complete)</span>。</li>
    <li><strong>完成通知至多报一次</strong>：生产端 <span class="mono">was_running</span> 守卫（<span class="mono">pop</span> 只有一方拿到非 <span class="mono">None</span>）+ 消费端 <span class="mono">_completion_consumed</span> / <span class="mono">_poll_observed</span> 两道去重闸；watch 命中限流连满 <span class="mono">WATCH_STRIKE_LIMIT</span>=3 会禁 watch 并翻转 <span class="mono">notify_on_complete</span>，汇入同一出口。</li>
    <li><strong>原子写靠同目录 temp + rename</strong>：<span class="mono">_atomic_write</span> 用 <span class="mono">mktemp -p "$d"</span> 在<strong>目标同目录</strong>建 temp、<span class="mono">cat</span> 写、<span class="mono">mv -f</span> 原子换上、<span class="mono">trap</span> 失败清理；<strong>跨文件系统 rename 非原子</strong>（降级 copy + unlink，半写损坏），所以 temp 位置 load-bearing。</li>
    <li><strong>patch 写后再读回校验</strong>：模糊匹配要求<strong>唯一</strong>、保 BOM / CRLF、只报<strong>新增</strong> lint 错；写盘后 re-read 逐字节比对，<strong>并发编辑</strong>会让校验失败、报「did not persist」而非假成功。外加路径 deny-list、读分页、二进制 / 图片拦截、search 行级。</li>
    <li><strong>共同理念</strong>：三套机制守的都是<strong>异步世界里的正确性边界</strong>——停得及时不撕裂、状态诚实不重复、落盘原子不半写；是<strong>「自主、连续运行」可靠性的地基</strong>，也是韧性与窄腰的又一次落地。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">An agent that has run dozens of turns, still has background processes open, and is mid-edit on a file — how does it <strong>stop safely, reliably know when background work finishes, and persist atomically</strong>? This chapter opens up the three runtime mechanisms most prone to correctness bugs.</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · in-flight emergency procedures</div>
  An emergency stop is never <strong>instantaneous</strong>. After the pilot pulls back, the aircraft only recovers at the <strong>next stable point</strong> — which is exactly what a <strong>cooperative interrupt</strong> is: the signal is honored at a boundary, not the instant it is raised.
  <p style="margin:.6rem 0 0">The same restraint returns twice more in this chapter. That background engine is either <strong>really still turning</strong> or it stopped long ago — the instruments must report that <strong>truthfully</strong>, and must <strong>not raise the same alarm twice</strong> (notification de-duplication). To change the flight plan you don't scribble over the live copy: you draft it, <strong>verify it, then swap it in atomically</strong> (write a temp file, then rename). Three runtime traps, one quiet throughline: a <strong>stop</strong>, a <strong>look</strong>, and a <strong>save</strong> each have a moment where "looks done" and "is done" can silently diverge.</p>
</div>

<div class="card macro">
  <div class="tag">🌍 Macro · three runtime correctness traps</div>
  The runtime — the layer that actually <strong>stops, watches, and persists</strong> — hides three places where the intuitive model is wrong:
  <p style="margin:.6rem 0 0"><strong>① An interrupt is cooperative, not preemptive.</strong> Pressing <span class="mono">/stop</span> only <strong>sets a flag</strong>; the main loop honors it at its <strong>boundary</strong> (between iterations), and propagation to subagents is <strong>hand-wired</strong> — the parent walks an <span class="mono">_active_children</span> registry and calls <span class="mono">child.interrupt()</span> on each. Miss the registration (or deliberately detach, as async delegation does) and a child <strong>never hears</strong> the stop.</p>
  <p><strong>② Background "durability" is mostly an in-process illusion.</strong> A <span class="mono">background=true</span> <span class="mono">delegate_task</span> is detached from the turn but still <strong>process-local</strong> — it dies with the process. Durability that survives a <strong>restart</strong> needs <span class="mono">cronjob</span> or a backgrounded terminal job, not a future living in memory.</p>
  <p><strong>③ On-disk atomicity hangs on one unremarkable rename.</strong> A half-written config or session file is corruption; the fix is to write a temp file and <strong>atomically rename</strong> it into place, so a reader only ever sees either the old file or the whole new one — <strong>never a torn middle</strong>.</p>
  <p>Three independent traps, one throughline: at every runtime edge, <strong>"looks finished" is not "is finished"</strong> — and that seam is where the bug lives.</p>
</div>

<p>Of the three, we start with the subtlest: how a "stop" actually travels through a running agent — and why it so often <strong>fails to reach a subagent</strong>.</p>

<h3>🔬 28.1 · Interrupt propagation: a cooperative stop, an explicit subagent fan-out</h3>
<p>When a user presses <span class="mono">/stop</span> (or the gateway receives a stop command), the call is <span class="mono">AIAgent.interrupt()</span>. It does two things: it sets <span class="mono">agent._interrupt_requested = True</span> and records the new message that triggered it, then calls <span class="mono">_set_interrupt(True, execution-thread-id)</span> to stamp a <strong>thread-scoped</strong> interrupt signal on <strong>this agent's own execution thread</strong>, so a tool already running there (say a terminal command hung on network I/O) can bail the next time it self-checks. The signal is <strong>targeted by thread</strong>: other agents running in the same gateway process are left untouched.</p>
<p>But setting the flag is <strong>not</strong> where the interrupt is "honored" — that happens at the <strong>main tool-loop boundary</strong>. Each time the <span class="mono">while</span> loop in <span class="mono">agent/conversation_loop.py</span> begins a new iteration it polls <span class="mono">agent._interrupt_requested</span>; on a hit it sets <span class="mono">interrupted</span>, records <span class="mono">_turn_exit_reason = "interrupted_by_user"</span>, prints a "Breaking out of tool loop" line, and <span class="mono">break</span>s. The check sits <strong>between iterations</strong> — never in the middle of a single API call or a tool execution.</p>
<p>So a Hermes interrupt is <strong>cooperative, not preemptive</strong>. Python can't hard-kill a thread from the outside, so nothing instantly halts code that is already running — everything relies on each site <strong>voluntarily polling that flag</strong>. Beyond the loop boundary a few in-iteration check points exist: the streaming delta callback inspects <span class="mono">_interrupt_requested</span> and cuts the stream short; a non-streaming API call runs a background checker that <strong>force-closes the httpx client</strong> so a blocked request raises and returns at once; and the failure-retry backoff sleep <strong>polls every 200ms</strong> (<span class="mono">time.sleep(0.2)</span>) and abandons the retry the moment a stop arrives. But any stretch of code that <strong>doesn't</strong> check the flag — a tight CPU loop, an uncooperative third-party call — runs to its own end or its own timeout, and the loop can only truly stop at the next boundary once control returns.</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">agent/conversation_loop.py:589</span></div><pre>    while (api_call_count &lt; agent.max_iterations and agent.iteration_budget.remaining &gt; 0) or agent._budget_grace_call:
        # Reset per-turn checkpoint dedup so each iteration can take one snapshot
        agent._checkpoint_mgr.new_turn()

        # Check for interrupt request (e.g., user sent new message)
        if agent._interrupt_requested:
            interrupted = True
            _turn_exit_reason = "interrupted_by_user"
            if not agent.quiet_mode:
                agent._safe_print("\n⚡ Breaking out of tool loop due to interrupt...")
            break</pre></div>
<p>The second trap, and the easier one to hit: propagation to subagents is <strong>explicit hand-wiring</strong>, not free. At the end of <span class="mono">interrupt()</span> the agent walks <span class="mono">self._active_children</span> — its <strong>registry of live subagents</strong> — and calls <span class="mono">child.interrupt(message)</span> on each; that child in turn walks its own <span class="mono">_active_children</span>, so the interrupt <strong>fans out recursively</strong> to grandchildren and beyond. But the chain only holds because <strong>every spawned child registers itself in the parent's <span class="mono">_active_children</span></strong> (see the "Register child for interrupt propagation" step in <span class="mono">delegate_tool.py</span>) and unregisters when it finishes. Let a delegation path <strong>forget to register, or deliberately detach</strong>, and the parent's <span class="mono">/stop</span> <strong>silently never reaches</strong> that child — it keeps running in its own streaming / tool loop.</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">run_agent.py:2433</span></div><pre>        # Propagate interrupt to any running child agents (subagent delegation)
        with self._active_children_lock:
            children_copy = list(self._active_children)
        for child in children_copy:
            try:
                child.interrupt(message)
            except Exception as e:
                logger.debug("Failed to propagate interrupt to child agent: %s", e)</pre></div>
<p>Async / background delegation detaches on purpose: a <span class="mono">background=true</span> batch <strong>removes</strong> its children from the parent's <span class="mono">_active_children</span> (their lifecycle now belongs to the async registry, not this turn) and registers a separate <span class="mono">interrupt_fn</span> to cancel them instead. That's by design, not a bug — but it shows precisely why "the interrupt will propagate on its own" is a dangerous assumption: <strong>the fan-out is a hand-maintained invariant, not a language feature</strong>. Any new delegation path has to decide, explicitly, who carries the stop down to the children.</p>

<div class="figure">
<svg viewBox="0 0 680 432" role="img" aria-label="Interrupt fan-out: the central agent.interrupt() sets _interrupt_requested to True and propagates along four paths — main loop boundary polling, subagents needing an explicit child.interrupt(), the streaming callback checking the flag per token, and retry backoff polling every 200ms; the subagent path is marked red to stress that propagation is explicit and breaks if a child is unregistered or detached">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">Interrupt fan-out · one flag, four cooperative paths</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">interrupt() sets the flag and stamps this thread; each site polls it voluntarily — only subagents need an explicit fan-out</text>
  <rect x="240" y="58" width="200" height="62" rx="12" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="340" y="84" text-anchor="middle" font-size="13" font-weight="700" fill="var(--accent-ink)">agent.interrupt()</text>
  <text x="340" y="104" text-anchor="middle" font-size="9.5" fill="var(--muted)">_interrupt_requested = True</text>
  <line x1="340" y1="120" x2="92" y2="224" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M92,232 L87,223 L97,223 Z" fill="var(--muted)"/>
  <line x1="340" y1="120" x2="257" y2="224" stroke="var(--red)" stroke-width="1.8"/>
  <path d="M257,232 L252,223 L262,223 Z" fill="var(--red)"/>
  <line x1="340" y1="120" x2="422" y2="224" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M422,232 L417,223 L427,223 Z" fill="var(--muted)"/>
  <line x1="340" y1="120" x2="587" y2="224" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M587,232 L582,223 L592,223 Z" fill="var(--muted)"/>
  <rect x="16" y="232" width="152" height="120" rx="10" fill="var(--panel)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="92" y="257" text-anchor="middle" font-size="12" font-weight="700" fill="var(--blue)">Main loop boundary</text>
  <text x="92" y="273" text-anchor="middle" font-size="9" fill="var(--muted)">loop boundary</text>
  <line x1="26" y1="281" x2="158" y2="281" stroke="var(--line)"/>
  <text x="26" y="301" font-size="9.5" fill="var(--ink)">polls the flag each turn</text>
  <text x="26" y="318" font-size="9.5" fill="var(--ink)">hit, then break the loop</text>
  <text x="26" y="341" font-size="9" fill="var(--muted)">conversation_loop.py:594</text>
  <rect x="181" y="232" width="152" height="120" rx="10" fill="var(--red-soft)" stroke="var(--red)" stroke-width="2"/>
  <text x="257" y="257" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--red)">Subagents · explicit</text>
  <text x="257" y="273" text-anchor="middle" font-size="9" fill="var(--muted)">_active_children fan-out</text>
  <line x1="191" y1="281" x2="323" y2="281" stroke="var(--line)"/>
  <text x="191" y="301" font-size="9.5" fill="var(--ink)">walk registry, each:</text>
  <text x="191" y="318" font-size="9.5" fill="var(--ink)">child.interrupt()</text>
  <text x="191" y="341" font-size="9" font-weight="700" fill="var(--red)">⚠ unregistered / detached = lost</text>
  <rect x="346" y="232" width="152" height="120" rx="10" fill="var(--panel)" stroke="var(--purple)" stroke-width="1.5"/>
  <text x="422" y="257" text-anchor="middle" font-size="12" font-weight="700" fill="var(--purple)">Streaming callback</text>
  <text x="422" y="273" text-anchor="middle" font-size="9" fill="var(--muted)">streaming delta</text>
  <line x1="356" y1="281" x2="488" y2="281" stroke="var(--line)"/>
  <text x="356" y="301" font-size="9.5" fill="var(--ink)">checks flag per token</text>
  <text x="356" y="318" font-size="9.5" fill="var(--ink)">force-close httpx, cut</text>
  <text x="356" y="341" font-size="9" fill="var(--muted)">force-close client</text>
  <rect x="511" y="232" width="152" height="120" rx="10" fill="var(--panel)" stroke="var(--amber)" stroke-width="1.5"/>
  <text x="587" y="257" text-anchor="middle" font-size="12" font-weight="700" fill="var(--amber)">Retry backoff poll</text>
  <text x="587" y="273" text-anchor="middle" font-size="9" fill="var(--muted)">backoff sleep</text>
  <line x1="521" y1="281" x2="653" y2="281" stroke="var(--line)"/>
  <text x="521" y="301" font-size="9.5" fill="var(--ink)">polls every 200ms</text>
  <text x="521" y="318" font-size="9.5" fill="var(--ink)">time.sleep(0.2)</text>
  <text x="521" y="341" font-size="9" fill="var(--muted)">stop = abandon retry</text>
  <rect x="16" y="372" width="648" height="48" rx="10" fill="var(--panel-2)" stroke="var(--accent)"/>
  <text x="340" y="392" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--accent-ink)">Cooperative: no thread is hard-killed</text>
  <text x="340" y="410" text-anchor="middle" font-size="9.5" fill="var(--ink)">all four paths rely on voluntary polling — code that never checks runs to its own end before it stops</text>
</svg>
<div class="fig-cap"><b>Interrupt fan-out</b>: after <span class="mono">interrupt()</span> sets the flag and stamps this thread, four paths <strong>poll it voluntarily</strong> — loop boundary, streaming callback, and retry backoff (every <strong>200ms</strong>) all self-check; only <strong>subagents</strong> require the parent to walk <span class="mono">_active_children</span> and call <span class="mono">child.interrupt()</span> explicitly, so an unregistered / detached child breaks the chain.</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 356" role="img" aria-label="Cooperative versus preemptive interrupt timing: the top lane is Hermes cooperative, where /stop arrives mid tool execution, sets the flag, then waits pending until the next loop boundary before it truly breaks; the bottom lane is a preemptive contrast (which Hermes does not do), stopping instantly at the same moment, drawn dashed">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">cooperative vs preemptive · same instant, different stop point</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">the stop arrives mid tool execution — cooperative waits for the loop boundary, preemptive kills the thread on the spot</text>
  <text x="20" y="92" font-size="11" font-weight="700" fill="var(--accent-ink)">Hermes · cooperative</text>
  <line x1="140" y1="120" x2="660" y2="120" stroke="var(--line)"/>
  <rect x="140" y="104" width="160" height="32" rx="6" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="220" y="124" text-anchor="middle" font-size="9.5" fill="var(--blue)">tool executing</text>
  <rect x="300" y="104" width="170" height="32" rx="6" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="385" y="124" text-anchor="middle" font-size="9" fill="var(--amber)">pending · flag is set</text>
  <line x1="300" y1="74" x2="300" y2="178" stroke="var(--red)" stroke-width="1.6" stroke-dasharray="4 3"/>
  <text x="300" y="68" text-anchor="middle" font-size="9.5" fill="var(--red)">⚡ /stop arrives (mid-execution)</text>
  <line x1="470" y1="92" x2="470" y2="150" stroke="var(--accent)" stroke-width="1.8"/>
  <text x="470" y="86" text-anchor="middle" font-size="9.5" fill="var(--accent-ink)">↧ loop boundary</text>
  <rect x="478" y="104" width="158" height="32" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="557" y="124" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--accent-ink)">✓ truly break</text>
  <text x="140" y="158" font-size="9" fill="var(--muted)">honored between iterations — the running tool first reaches a check point or the boundary, then returns control</text>
  <line x1="300" y1="178" x2="300" y2="236" stroke="var(--muted)" stroke-width="1.2" stroke-dasharray="3 3"/>
  <text x="20" y="258" font-size="11" font-weight="700" fill="var(--muted)">preemptive · contrast (Hermes does not do this)</text>
  <line x1="140" y1="286" x2="660" y2="286" stroke="var(--line)" stroke-dasharray="4 3"/>
  <rect x="140" y="270" width="160" height="32" rx="6" fill="var(--panel-2)" stroke="var(--muted)" stroke-dasharray="4 3"/>
  <text x="220" y="290" text-anchor="middle" font-size="9.5" fill="var(--muted)">executing</text>
  <line x1="300" y1="240" x2="300" y2="322" stroke="var(--red)" stroke-width="1.6" stroke-dasharray="4 3"/>
  <text x="300" y="234" text-anchor="middle" font-size="9.5" fill="var(--red)">⚡ /stop arrives</text>
  <rect x="304" y="270" width="158" height="32" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="383" y="290" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--red)">✗ halted on the spot</text>
  <text x="140" y="326" font-size="9" fill="var(--muted)">preemption would kill the thread at once — but Python can't, so Hermes only polls cooperatively</text>
</svg>
<div class="fig-cap"><b>Cooperative vs preemptive</b>: the same <span class="mono">/stop</span> arrives mid tool execution — Hermes <strong>cooperatively</strong> holds it pending until the next loop boundary, then <span class="mono">break</span>s; a preemptive stop (contrast) would kill the thread on the spot, which Python can't do, so everything relies on polling the flag.</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 456" role="img" aria-label="/stop interrupt frame-by-frame timeline snapshot: one concrete /stop arrives mid execution of a slow tool, showing a cooperative stop. Four frames advance along the timeline, each drawing two small tracks: a top main-loop-state track and a bottom _interrupt_requested flag-value track. T0 at 0ms, iteration N runs the terminal tool at 55 percent progress with the flag false. T1 at plus 50ms the signal arrives, interrupt() only sets the flag without a hard kill, the tool still runs at 82 percent, and the flag flips to true in amber. T2 the tool finishes naturally and returns its result back to the loop boundary while the flag stays true awaiting a read. T3 the loop boundary reads _interrupt_requested as true and breaks cleanly, saving state with no data loss. Center annotation: the flag is set true at T1 yet only read at T3, and that interval where the tool still finishes naturally is the cooperative stop set-versus-read gap. Bottom side notes: polling granularity time.sleep(0.2) equals 200ms with the streaming callback and retry backoff both self-checking this flag; interrupt() also fans out to _active_children where the parent walks each registered child and calls child.interrupt(), but a detached or unregistered child is off the list and breaks the chain so it never receives the interrupt.">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">/stop interrupt frame-by-frame timeline · flag false to true to read</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">one concrete /stop: watch _interrupt_requested flip along the timeline, plus the gap where the tool still finishes after the flag is set</text>
  <text x="600" y="36" text-anchor="middle" font-size="24">🛑</text>
  <rect x="10" y="70" width="132" height="240" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="21" y="90" font-size="9.5" font-weight="700" fill="var(--ink)">T0 · 0ms</text>
  <text x="21" y="105" font-size="9" fill="var(--accent-ink)">running</text>
  <text x="21" y="126" font-size="9" fill="var(--muted)">① main-loop state</text>
  <rect x="20" y="132" width="112" height="30" rx="5" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="76" y="146" text-anchor="middle" font-size="9" fill="var(--accent-ink)">iteration N</text>
  <text x="76" y="157" text-anchor="middle" font-size="9" fill="var(--accent-ink)">terminal tool running</text>
  <rect x="20" y="170" width="112" height="8" rx="3" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="20" y="170" width="61.6" height="8" rx="3" fill="var(--accent)"/>
  <text x="21" y="191" font-size="9" fill="var(--muted)">▶ tool running · 55%</text>
  <text x="21" y="206" font-size="9" fill="var(--muted)">② _interrupt_requested</text>
  <rect x="20" y="212" width="112" height="28" rx="5" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="76" y="231" text-anchor="middle" font-size="11" font-weight="700" fill="var(--accent-ink)">false</text>
  <text x="21" y="260" font-size="9" fill="var(--muted)">tool advancing normally</text>
  <text x="21" y="274" font-size="9" fill="var(--muted)">flag is false · no interrupt</text>
  <line x1="142" y1="196" x2="180" y2="196" stroke="var(--red)" stroke-width="1.6"/>
  <path d="M186,196 L178,192 L178,200 Z" fill="var(--red)"/>
  <text x="164" y="150" text-anchor="middle" font-size="9" fill="var(--red)">user sends</text>
  <text x="164" y="162" text-anchor="middle" font-size="9" fill="var(--red)">/stop</text>
  <rect x="186" y="70" width="132" height="240" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="197" y="90" font-size="9.5" font-weight="700" fill="var(--ink)">T1 · +50ms</text>
  <text x="197" y="105" font-size="9" fill="var(--amber)">signal arrives</text>
  <text x="197" y="126" font-size="9" fill="var(--muted)">① main-loop state</text>
  <rect x="196" y="132" width="112" height="30" rx="5" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="252" y="146" text-anchor="middle" font-size="9" fill="var(--accent-ink)">iteration N</text>
  <text x="252" y="157" text-anchor="middle" font-size="9" fill="var(--accent-ink)">tool still running</text>
  <rect x="196" y="170" width="112" height="8" rx="3" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="196" y="170" width="91.8" height="8" rx="3" fill="var(--accent)"/>
  <text x="197" y="191" font-size="9" fill="var(--muted)">▶ not interrupted · 82%</text>
  <text x="197" y="206" font-size="9" fill="var(--muted)">② _interrupt_requested</text>
  <rect x="196" y="212" width="112" height="28" rx="5" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="252" y="231" text-anchor="middle" font-size="11" font-weight="700" fill="var(--amber)">true</text>
  <text x="197" y="260" font-size="9" fill="var(--amber)">interrupt() only sets flag</text>
  <text x="197" y="274" font-size="9" fill="var(--muted)">no hard-kill of the tool</text>
  <line x1="318" y1="196" x2="356" y2="196" stroke="var(--accent)" stroke-width="1.6"/>
  <path d="M362,196 L354,192 L354,200 Z" fill="var(--accent)"/>
  <text x="340" y="150" text-anchor="middle" font-size="9" fill="var(--accent-ink)">tool</text>
  <text x="340" y="162" text-anchor="middle" font-size="9" fill="var(--accent-ink)">finishes</text>
  <rect x="362" y="70" width="132" height="240" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="373" y="90" font-size="9.5" font-weight="700" fill="var(--ink)">T2 · tool done</text>
  <text x="373" y="105" font-size="9" fill="var(--blue)">back to boundary</text>
  <text x="373" y="126" font-size="9" fill="var(--muted)">① main-loop state</text>
  <rect x="372" y="132" width="112" height="30" rx="5" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="428" y="146" text-anchor="middle" font-size="9" fill="var(--blue)">tool returns result</text>
  <text x="428" y="157" text-anchor="middle" font-size="9" fill="var(--blue)">-&gt; back to boundary</text>
  <rect x="372" y="170" width="112" height="8" rx="3" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="372" y="170" width="112" height="8" rx="3" fill="var(--blue)"/>
  <text x="373" y="191" font-size="9" fill="var(--muted)">✓ tool finished</text>
  <text x="373" y="206" font-size="9" fill="var(--muted)">② _interrupt_requested</text>
  <rect x="372" y="212" width="112" height="28" rx="5" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="428" y="231" text-anchor="middle" font-size="11" font-weight="700" fill="var(--amber)">true</text>
  <text x="373" y="260" font-size="9" fill="var(--muted)">flag already set</text>
  <text x="373" y="274" font-size="9" fill="var(--amber)">but not yet read</text>
  <line x1="494" y1="196" x2="532" y2="196" stroke="var(--blue)" stroke-width="1.6"/>
  <path d="M538,196 L530,192 L530,200 Z" fill="var(--blue)"/>
  <text x="516" y="150" text-anchor="middle" font-size="9" fill="var(--blue)">loop boundary</text>
  <text x="516" y="162" text-anchor="middle" font-size="9" fill="var(--blue)">checks flag</text>
  <rect x="538" y="70" width="132" height="240" rx="8" fill="var(--panel)" stroke="var(--line)"/>
  <text x="549" y="90" font-size="9.5" font-weight="700" fill="var(--ink)">T3 · clean exit</text>
  <text x="549" y="105" font-size="9" fill="var(--red)">clean break</text>
  <text x="549" y="126" font-size="9" fill="var(--muted)">① main-loop state</text>
  <rect x="548" y="132" width="112" height="30" rx="5" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="604" y="146" text-anchor="middle" font-size="9" fill="var(--red)">boundary reads true</text>
  <text x="604" y="157" text-anchor="middle" font-size="9" fill="var(--red)">-&gt; clean break, exit</text>
  <rect x="548" y="170" width="112" height="8" rx="3" fill="var(--panel-2)" stroke="var(--line)"/>
  <rect x="548" y="170" width="112" height="8" rx="3" fill="var(--red)"/>
  <text x="549" y="191" font-size="9" fill="var(--muted)">⏹ break · leave loop</text>
  <text x="549" y="206" font-size="9" fill="var(--muted)">② _interrupt_requested</text>
  <rect x="548" y="212" width="112" height="28" rx="5" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="604" y="231" text-anchor="middle" font-size="11" font-weight="700" fill="var(--red)">true</text>
  <text x="549" y="260" font-size="9" fill="var(--red)">✓ flag is read</text>
  <text x="549" y="274" font-size="9" fill="var(--muted)">state saved · no data loss</text>
  <line x1="252" y1="330" x2="604" y2="330" stroke="var(--amber)" stroke-width="1.4"/>
  <line x1="252" y1="324" x2="252" y2="330" stroke="var(--amber)" stroke-width="1.4"/>
  <line x1="604" y1="324" x2="604" y2="330" stroke="var(--amber)" stroke-width="1.4"/>
  <text x="340" y="322" text-anchor="middle" font-size="9.5" fill="var(--amber)">flag set true at T1 yet only read at T3 — that interval, where the tool still finishes naturally, is the cooperative stop set-vs-read gap</text>
  <rect x="10" y="350" width="660" height="96" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="24" y="372" font-size="9.5" font-weight="700" fill="var(--ink)">Side note · polling granularity and subagent fan-out (only real constants here)</text>
  <circle cx="26" cy="392" r="4" fill="var(--blue)"/>
  <text x="38" y="396" font-size="9" fill="var(--muted)">polling granularity time.sleep(0.2) = 200ms: streaming callback per token and retry backoff both self-check this flag</text>
  <circle cx="26" cy="416" r="4" fill="var(--amber)"/>
  <text x="38" y="420" font-size="9" fill="var(--muted)">interrupt() also fans out to _active_children: the parent walks them and calls child.interrupt() on each registered child</text>
  <text x="38" y="434" font-size="9" fill="var(--muted)">but a detached / unregistered child is off the list -&gt; chain broken, no interrupt (async delegation registers its own interrupt_fn)</text>
</svg>
<div class="fig-cap"><b>/stop frame-by-frame</b>: a 4-frame snapshot of one concrete /stop — <span class="mono">_interrupt_requested</span> flips <span class="mono">false-&gt;true</span> at <span class="mono">T1(+50ms)</span>, yet the in-flight tool is not hard-killed and <strong>runs to T2</strong> before finishing, and the loop only <strong>reads</strong> the flag at the <span class="mono">T3</span> boundary to <span class="mono">break</span> cleanly; the gap between set and read is the essence of a cooperative stop. Each self-check runs at <span class="mono">time.sleep(0.2)=200ms</span>, and <span class="mono">interrupt()</span> must explicitly fan out to <span class="mono">_active_children</span>.</div>
</div>

<p>With the stop covered, on to the second trap: where a <span class="mono">background=true</span> process actually <strong>lives</strong>, how its "I'm done" fires <strong>exactly once</strong>, and why it almost never <strong>survives a restart</strong>.</p>

<h3>🔬 28.2 · Background-process lifecycle: in-memory registry, de-duplicated notification, best-effort recovery</h3>
<p>When an agent launches a <span class="mono">terminal(background=True)</span>, the process isn't handed straight to the OS and forgotten — it's registered in the <span class="mono">ProcessRegistry</span>, an <strong>in-process</strong> table whose core is two dicts: <span class="mono">_running</span> (live) and <span class="mono">_finished</span> (exited, kept for a 30-minute TTL). Each <span class="mono">ProcessSession</span> carries a <strong>rolling output buffer</strong> (capped at <span class="mono">MAX_OUTPUT_CHARS</span> = 200KB, trimmed from the front), optional <span class="mono">watch_patterns</span>, and a <span class="mono">notify_on_complete</span> flag; a background reader thread keeps pumping the child's output into the buffer, while the agent uses <span class="mono">wait</span> / <span class="mono">poll</span> / <span class="mono">kill</span> / read-log to wait on it, query it, or kill it.</p>
<p>When the process <strong>exits</strong> (the reader hits EOF) or is <strong>killed</strong>, both paths reach the same exit, <span class="mono">_move_to_finished()</span>. Under the lock it pops the session out of <span class="mono">_running</span>, drops it into <span class="mono">_finished</span>, sets the completion event (waking every call blocked on <span class="mono">wait()</span>), then <span class="mono">_write_checkpoint()</span> persists once. <strong>The crux is that final <span class="mono">if</span></strong>: only when <span class="mono">notify_on_complete</span> is on <strong>and this call is genuinely the first</strong> to move it does it push one completion notification onto <span class="mono">completion_queue</span>.</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">tools/process_registry.py:1022 · abridged</span></div><pre>    def _move_to_finished(self, session: ProcessSession):
        with self._lock:
            was_running = self._running.pop(session.id, None) is not None
            self._finished[session.id] = session
        session._completion_event.set()
        self._write_checkpoint()

        # Only enqueue completion notification on the FIRST move.  Without
        # this guard, kill_process() and the reader thread can both call
        # _move_to_finished(), producing duplicate [IMPORTANT: ...] messages.
        if was_running and session.notify_on_complete:
            from tools.ansi_strip import strip_ansi
            output_tail = strip_ansi(session.output_buffer[-2000:]) if session.output_buffer else ""
            self.completion_queue.put({
                "type": "completion",
                "session_id": session.id,
                "session_key": session.session_key,
                "command": session.command,
                "exit_code": session.exit_code,
                "completion_reason": session.completion_reason,
                "termination_source": session.termination_source,
                "output": output_tail,
            })</pre></div>
<p>That "first" is captured by <span class="mono">was_running = self._running.pop(...) is not None</span> — the <strong>first de-dup gate</strong>. <span class="mono">_move_to_finished()</span> is <strong>idempotent</strong>: <span class="mono">kill_process()</span> and the reader thread may notice the process is gone <strong>at the same time</strong> and <strong>both call it</strong>, but the dict <span class="mono">pop</span> only hands one of them a non-<span class="mono">None</span>, so only that caller has <span class="mono">was_running</span> true and only it enqueues. Without the guard a single exit gets reported twice as <span class="mono">[IMPORTANT: ...]</span>. This is producer-side (who notifies) de-duplication.</p>
<p>But enqueued is not delivered. <strong>The second gate is on the consumer side</strong>: before taking the notification, the CLI drain and the gateway / TUI watcher both check <span class="mono">_completion_consumed</span> — if the agent already grabbed the output via a blocking <span class="mono">wait()</span> or a full <span class="mono">read_log()</span>, skip it; the CLI additionally checks <span class="mono">_poll_observed</span> (a read-only <span class="mono">poll()</span> saw the exit and the result is returned inline this turn, whereas the gateway / TUI <strong>deliberately do not</strong> consult it, so a read-only probe can't suppress their autonomous delivery turn). A hit in either set makes the drain <strong>skip</strong> the completion, avoiding a duplicate <span class="mono">[SYSTEM: ...]</span> injection. Together the two gates guarantee a completion fires <strong>at most once</strong>, and <strong>not at all</strong> if the agent already knows.</p>
<p>One more path also feeds <span class="mono">notify_on_complete</span>: <strong>watch rate-limit demotion</strong>. For a process with <span class="mono">watch_patterns</span>, match notifications are hard-throttled — at most one per <span class="mono">WATCH_MIN_INTERVAL_SECONDS</span> (15s); a match arriving inside the cooldown is dropped and counts as <strong>one strike</strong>. After <span class="mono">WATCH_STRIKE_LIMIT</span> = <strong>3</strong> consecutive strike windows the session's watch is <strong>permanently disabled</strong> (<span class="mono">_watch_disabled = True</span>) and <span class="mono">notify_on_complete = True</span> is <strong>flipped on</strong> — a watcher that was spamming mid-process state quietly demotes to "report once when the process actually exits," routing back through that single exit.</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">tools/process_registry.py:65</span></div><pre># After WATCH_STRIKE_LIMIT consecutive strike windows, watch_patterns for that
# session is permanently disabled and the session falls back to notify_on_complete
# semantics (one notification when the process actually exits).
WATCH_MIN_INTERVAL_SECONDS = 15   # Minimum spacing between consecutive watch matches
WATCH_STRIKE_LIMIT = 3            # Strikes in a row → disable watch + promote to notify_on_complete</pre></div>
<p>Now the <strong>biggest trap</strong>. Everything above — the two dicts, the output buffer, the completion event, the reader and watcher threads — <strong>lives in process memory</strong>. The <span class="mono">_write_checkpoint()</span> inside <span class="mono">_move_to_finished()</span> writes state to <span class="mono">CHECKPOINT_PATH</span> (<span class="mono">processes.json</span>), but it exists <strong>only for gateway crash recovery</strong>, and that recovery is <strong>best-effort</strong>: after a gateway restart it re-registers only the <strong>detached host-PID processes</strong>, and only after re-validating that the <span class="mono">host_start_time</span> recorded in the checkpoint still matches the live PID (or the kernel may have recycled that number onto an unrelated process, and adopting it would kill a stranger). Recovered sessions are all flagged <span class="mono">detached=True</span> — <strong>output can't be read back, only status + kill</strong>. The checkpoint restores a <strong>handle</strong> ("can I still query / kill it?"), not the process's <strong>full state</strong>.</p>
<p>So a <span class="mono">background=true</span> process's "durability" is mostly an <strong>in-process illusion</strong>: a restart wipes the in-memory state, and detached recovery is only a best-effort status / kill handle. To make work <strong>truly survive a restart</strong>, use a mechanism that actually lands — a <span class="mono">cron</span> job, or <span class="mono">terminal(background=True, notify_on_complete=True)</span> that hands the process to the system and calls back on completion (exactly ch26's E6 fix). Mistaking "detached from this turn" for "made durable" is precisely why background tasks vanish.</p>

<div class="figure">
<svg viewBox="0 0 680 430" role="img" aria-label="Background-process lifecycle and completion-notification de-duplication. Center vertical spine: a running process, on exit or kill, enters _move_to_finished, which under the lock pops the session out of _running and into _finished, sets the completion event, and writes the checkpoint; only the first move with notify_on_complete true puts a notification onto completion_queue, sent at most once. Left branch: a process with watch_patterns is rate-limited to at most one match per 15 seconds, a match inside the cooldown counts as one strike, and after WATCH_STRIKE_LIMIT three strikes watch is disabled and notify_on_complete flipped on, merging into the same exit. Right side two de-dup gates: gate one was_running on the producer side, since kill and the reader thread both call but only one pop succeeds and enqueues; gate two on the consumer side, where the _completion_consumed and CLI-only _poll_observed sets make the drain skip the notification to avoid duplicate injection">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">Background lifecycle · two de-dup gates on the completion notice</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">one spine running → _move_to_finished → notify; 3 watch strikes flip notify_on_complete, two gates send at most once</text>
  <rect x="265" y="70" width="170" height="64" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="350" y="94" text-anchor="middle" font-size="12" font-weight="700" fill="var(--blue)">running process</text>
  <text x="350" y="112" text-anchor="middle" font-size="9" fill="var(--muted)">_running{} · 200KB output buffer</text>
  <text x="350" y="127" text-anchor="middle" font-size="9" fill="var(--muted)">reader thread · wait / poll / kill / log</text>
  <line x1="350" y1="134" x2="350" y2="168" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M350,176 L345,167 L355,167 Z" fill="var(--muted)"/>
  <text x="358" y="158" font-size="9" fill="var(--muted)">exit / killed</text>
  <rect x="245" y="176" width="210" height="78" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="350" y="198" text-anchor="middle" font-size="12" font-weight="700" fill="var(--accent-ink)">_move_to_finished()</text>
  <text x="350" y="216" text-anchor="middle" font-size="9" fill="var(--muted)">under lock _running.pop → _finished</text>
  <text x="350" y="231" text-anchor="middle" font-size="9" fill="var(--muted)">set event + _write_checkpoint</text>
  <text x="350" y="248" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--red)">gate ① was_running guard</text>
  <line x1="350" y1="254" x2="350" y2="286" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M350,294 L345,285 L355,285 Z" fill="var(--muted)"/>
  <text x="358" y="276" font-size="9" fill="var(--muted)">first move + notify_on_complete</text>
  <rect x="265" y="294" width="170" height="52" rx="10" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="1.5"/>
  <text x="350" y="316" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--purple)">completion_queue</text>
  <text x="350" y="334" text-anchor="middle" font-size="9" fill="var(--muted)">type: completion enqueued</text>
  <line x1="350" y1="346" x2="350" y2="376" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M350,384 L345,375 L355,375 Z" fill="var(--muted)"/>
  <rect x="245" y="386" width="210" height="38" rx="9" fill="var(--panel-2)" stroke="var(--accent)" stroke-width="1.5"/>
  <text x="350" y="410" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--accent-ink)">at most once (zero if already known)</text>
  <rect x="18" y="176" width="182" height="78" rx="10" fill="var(--amber-soft)" stroke="var(--amber)" stroke-width="1.5"/>
  <text x="109" y="197" text-anchor="middle" font-size="11" font-weight="700" fill="var(--amber)">watch rate-limit</text>
  <text x="109" y="214" text-anchor="middle" font-size="9" fill="var(--ink)">≤ 1 per 15s</text>
  <text x="109" y="229" text-anchor="middle" font-size="9" fill="var(--ink)">inside cooldown = 1 strike</text>
  <text x="109" y="245" text-anchor="middle" font-size="9" font-weight="700" fill="var(--ink)">3 strikes → disable + flip</text>
  <line x1="200" y1="208" x2="241" y2="208" stroke="var(--amber)" stroke-width="1.6"/>
  <path d="M249,208 L240,203 L240,213 Z" fill="var(--amber)"/>
  <text x="205" y="266" font-size="9" fill="var(--muted)">notify_on_complete=True · same exit</text>
  <rect x="470" y="176" width="192" height="78" rx="10" fill="var(--red-soft)" stroke="var(--red)" stroke-width="1.5"/>
  <text x="478" y="196" font-size="10" font-weight="700" fill="var(--red)">gate ① producer dedup</text>
  <text x="478" y="213" font-size="9" fill="var(--ink)">kill + reader both call it</text>
  <text x="478" y="228" font-size="9" fill="var(--ink)">only one pop gets non-None</text>
  <text x="478" y="243" font-size="9" fill="var(--ink)">only it enqueues, else twice</text>
  <line x1="470" y1="208" x2="457" y2="208" stroke="var(--red)" stroke-width="1.3" stroke-dasharray="3 3"/>
  <rect x="470" y="294" width="192" height="92" rx="10" fill="var(--red-soft)" stroke="var(--red)" stroke-width="1.5"/>
  <text x="478" y="314" font-size="10" font-weight="700" fill="var(--red)">gate ② consumer dedup</text>
  <text x="478" y="331" font-size="9" fill="var(--ink)">_completion_consumed (wait/log)</text>
  <text x="478" y="346" font-size="9" fill="var(--ink)">_poll_observed (CLI read-only poll)</text>
  <text x="478" y="361" font-size="9" fill="var(--ink)">hit → drain skips the notice</text>
  <text x="478" y="376" font-size="9" fill="var(--ink)">no duplicate [SYSTEM: ...]</text>
  <line x1="470" y1="340" x2="437" y2="362" stroke="var(--red)" stroke-width="1.3" stroke-dasharray="3 3"/>
</svg>
<div class="fig-cap"><b>Lifecycle + notification de-dup</b>: exit / kill → <span class="mono">_move_to_finished()</span> moves the table, sets the event, writes the checkpoint; <strong>gate ①</strong> <span class="mono">was_running</span> lets a duplicate call enqueue only once, <strong>gate ②</strong> the consumer's <span class="mono">_completion_consumed</span> / <span class="mono">_poll_observed</span> make the drain skip a notice the agent already saw via wait / poll — <strong>at most once</strong>. A watch hitting <span class="mono">WATCH_STRIKE_LIMIT</span>=3 disables watch and flips <span class="mono">notify_on_complete</span>, merging into the same exit.</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 360" role="img" aria-label="Three tiers of background-task durability. Tier one in-process background: delegate_task background or a terminal background job, where the _running and _finished dicts, output buffer, completion event, and reader and watcher threads all live in process memory and are entirely lost on restart. Tier two detached: state is written to the processes.json checkpoint for gateway crash recovery only; after a restart it re-registers only host-PID processes that are still alive with a matching start_time, and can only report status and kill, not read output back, making it best-effort rather than durable state. Tier three cron: a cron job or terminal background with notify_on_complete hands the process to the scheduler and the system with a completion callback, which is truly durable across restarts. Bottom throughline: durability is mostly an in-process illusion; for cross-restart work use cron or a terminal background job, not a future living in memory, echoing ch26 E6">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">durability tiers · what survives a restart</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">in-process background (all in memory) / detached (host-PID best-effort) / cron (truly durable)</text>
  <rect x="20" y="70" width="200" height="214" rx="10" fill="var(--panel)" stroke="var(--line)"/>
  <rect x="20" y="70" width="200" height="44" rx="10" fill="var(--red-soft)" stroke="var(--red)" stroke-width="1.5"/>
  <text x="120" y="92" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--red)">in-process background</text>
  <text x="120" y="107" text-anchor="middle" font-size="9" fill="var(--muted)">delegate_task(bg) / terminal bg</text>
  <text x="32" y="143" font-size="9.5" fill="var(--muted)">✗ _running / _finished dicts</text>
  <text x="32" y="169" font-size="9.5" fill="var(--muted)">✗ output buffer + event</text>
  <text x="32" y="195" font-size="9.5" fill="var(--muted)">✗ reader / watcher threads</text>
  <rect x="38" y="246" width="164" height="28" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="120" y="264" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--red)">restart = all in-memory lost</text>
  <rect x="240" y="70" width="200" height="214" rx="10" fill="var(--panel)" stroke="var(--line)"/>
  <rect x="240" y="70" width="200" height="44" rx="10" fill="var(--amber-soft)" stroke="var(--amber)" stroke-width="1.5"/>
  <text x="340" y="92" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--amber)">detached (host-PID)</text>
  <text x="340" y="107" text-anchor="middle" font-size="9" fill="var(--muted)">processes.json · gateway-only</text>
  <text x="252" y="143" font-size="9.5" fill="var(--ink)">✓ host-PID + start_time match</text>
  <text x="252" y="169" font-size="9.5" fill="var(--ink)">✓ status + kill · detached</text>
  <text x="252" y="195" font-size="9.5" fill="var(--muted)">✗ output not readable back</text>
  <rect x="258" y="246" width="164" height="28" rx="8" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="340" y="264" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--amber)">best-effort · not durable</text>
  <rect x="460" y="70" width="200" height="214" rx="10" fill="var(--panel)" stroke="var(--line)"/>
  <rect x="460" y="70" width="200" height="44" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>
  <text x="560" y="92" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--accent-ink)">cron (durable)</text>
  <text x="560" y="107" text-anchor="middle" font-size="9" fill="var(--muted)">cron / terminal bg</text>
  <text x="472" y="143" font-size="9.5" fill="var(--ink)">✓ cron job (ch21)</text>
  <text x="472" y="169" font-size="9.5" fill="var(--ink)">✓ terminal(background,notify)</text>
  <text x="472" y="195" font-size="9.5" fill="var(--ink)">✓ handed to the system</text>
  <rect x="478" y="246" width="164" height="28" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="560" y="264" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--accent-ink)">true cross-restart durable</text>
  <rect x="20" y="304" width="640" height="44" rx="10" fill="var(--panel-2)" stroke="var(--accent)"/>
  <text x="340" y="324" text-anchor="middle" font-size="10" font-weight="700" fill="var(--ink)">durability is mostly an in-process illusion — for cross-restart use cron or a terminal bg job</text>
  <text x="340" y="340" text-anchor="middle" font-size="9" fill="var(--muted)">don't bet on a future living in memory (echoes ch26 · E6)</text>
</svg>
<div class="fig-cap"><b>Durability tiers</b>: <strong>in-process background</strong> (dicts / buffer / threads all in memory, lost on restart), <strong>detached</strong> (<span class="mono">processes.json</span> for gateway crash recovery only, host-PID only, status + kill only, best-effort), <strong>cron</strong> (handed to the scheduler / system, truly durable across restarts). For durability don't bet on a future in memory — echoing ch26 · E6.</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 456" role="img" aria-label="The life of a single background process in five state snapshots. Frame 1 spawn: the process starts and enters the _running registry, badge running, with a PID and a start timestamp. Frame 2 running monitor: the watcher polls periodically and it stays in _running; a side branch notes that if watch_patterns are set, after WATCH_STRIKE_LIMIT three strike windows watch is disabled and notify_on_complete is flipped on. Frame 3 exit migrate: the process exits or is killed and goes through _move_to_finished, which under the lock pops the session out of _running and into _finished, sets the completion event and writes the checkpoint, and finished is kept for 1800 seconds which is a 30 minute TTL. Frame 4 de-dup gate: when was_running is true and it is not in the _completion_consumed set, completion is decided just this once and added to that set, so repeat calls enqueue only once. Frame 5 notify once: the completion is put on completion_queue and triggers one new agent turn injecting the completion message, after which read-only status checks go through _poll_observed without consuming, and the drain skips anything already polled so the notification is not duplicated. Bottom notes: the processes.json checkpoint is only for gateway crash recovery re-registration of detached handles and is not the completion decider, completion is decided entirely in-memory by _running and _finished; the two gates split the work, gate one was_running on the producer side where kill and the reader thread both call but only one pop succeeds and enqueues, gate two _completion_consumed and _poll_observed on the consumer side where anything already waited or polled is skipped by the drain.">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">The life of one background process · 5 state snapshots</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">from spawn to completion notice: watch it go frame by frame running → exit → migrate → gate → notify once</text>
  <text x="650" y="34" text-anchor="middle" font-size="24">🔁</text>
  <text x="134.5" y="64" text-anchor="middle" font-size="9" fill="var(--accent-ink)">watcher polls</text>
  <text x="271.5" y="64" text-anchor="middle" font-size="9" fill="var(--ink)">process exit / kill</text>
  <text x="408.5" y="64" text-anchor="middle" font-size="9" fill="var(--purple)">completion de-dup</text>
  <text x="545.5" y="64" text-anchor="middle" font-size="9" fill="var(--accent-ink)">trigger new turn</text>
  <rect x="16" y="72" width="100" height="240" rx="9" fill="var(--panel)" stroke="var(--line)"/>
  <text x="25" y="90" font-size="9.5" font-weight="700" fill="var(--ink)">F1 · spawn</text>
  <text x="25" y="104" font-size="9" fill="var(--accent-ink)">start → into _running</text>
  <text x="25" y="124" font-size="9" fill="var(--muted)">1 state badge</text>
  <rect x="23" y="130" width="86" height="32" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="66" y="146" text-anchor="middle" font-size="9" font-weight="700" fill="var(--accent-ink)">running</text>
  <text x="66" y="157" text-anchor="middle" font-size="9" fill="var(--muted)">new session</text>
  <text x="25" y="180" font-size="9" fill="var(--muted)">2 registry</text>
  <rect x="23" y="186" width="86" height="24" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="66" y="202" text-anchor="middle" font-size="9" font-weight="700" fill="var(--accent-ink)">_running{}</text>
  <text x="25" y="230" font-size="9" fill="var(--muted)">PID 4127</text>
  <text x="25" y="244" font-size="9" fill="var(--muted)">start 18:06:41</text>
  <text x="25" y="258" font-size="9" fill="var(--muted)">notify=true</text>
  <text x="25" y="272" font-size="9" fill="var(--muted)">reader pumps buf</text>
  <rect x="153" y="72" width="100" height="240" rx="9" fill="var(--panel)" stroke="var(--line)"/>
  <text x="162" y="90" font-size="9.5" font-weight="700" fill="var(--ink)">F2 · monitor</text>
  <text x="162" y="104" font-size="9" fill="var(--accent-ink)">watcher polls</text>
  <text x="162" y="124" font-size="9" fill="var(--muted)">1 state badge</text>
  <rect x="160" y="130" width="86" height="32" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="203" y="146" text-anchor="middle" font-size="9" font-weight="700" fill="var(--accent-ink)">running</text>
  <text x="203" y="157" text-anchor="middle" font-size="9" fill="var(--muted)">still alive</text>
  <text x="162" y="180" font-size="9" fill="var(--muted)">2 registry</text>
  <rect x="160" y="186" width="86" height="24" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="203" y="202" text-anchor="middle" font-size="9" font-weight="700" fill="var(--accent-ink)">in _running</text>
  <rect x="160" y="220" width="86" height="88" rx="6" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="203" y="236" text-anchor="middle" font-size="9" font-weight="700" fill="var(--amber)">branch · watch demote</text>
  <text x="164" y="250" font-size="9" fill="var(--muted)">watch_patterns set</text>
  <text x="164" y="264" font-size="9" fill="var(--muted)">STRIKE=3 windows</text>
  <text x="164" y="278" font-size="9" fill="var(--amber)">→ disable + flip</text>
  <text x="164" y="292" font-size="9" fill="var(--muted)">notify=true</text>
  <rect x="290" y="72" width="100" height="240" rx="9" fill="var(--panel)" stroke="var(--line)"/>
  <text x="299" y="90" font-size="9.5" font-weight="700" fill="var(--ink)">F3 · migrate</text>
  <text x="299" y="104" font-size="9" fill="var(--blue)">exit/kill → migrate</text>
  <text x="299" y="124" font-size="9" fill="var(--muted)">1 state badge</text>
  <rect x="297" y="130" width="86" height="32" rx="6" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="340" y="146" text-anchor="middle" font-size="9" font-weight="700" fill="var(--blue)">finished</text>
  <text x="340" y="157" text-anchor="middle" font-size="9" fill="var(--muted)">event set</text>
  <text x="299" y="180" font-size="9" fill="var(--muted)">2 registry</text>
  <rect x="297" y="186" width="86" height="24" rx="6" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="340" y="202" text-anchor="middle" font-size="9" font-weight="700" fill="var(--blue)">into _finished{}</text>
  <text x="299" y="230" font-size="9" fill="var(--muted)">lock pop _running</text>
  <text x="299" y="244" font-size="9" fill="var(--muted)">set event + ckpt</text>
  <text x="299" y="258" font-size="9" fill="var(--muted)">finished kept 1800s</text>
  <text x="299" y="272" font-size="9" fill="var(--muted)">= 30min TTL</text>
  <rect x="427" y="72" width="100" height="240" rx="9" fill="var(--panel)" stroke="var(--line)"/>
  <text x="436" y="90" font-size="9.5" font-weight="700" fill="var(--ink)">F4 · de-dup gate</text>
  <text x="436" y="104" font-size="9" fill="var(--purple)">completion · once</text>
  <text x="436" y="124" font-size="9" fill="var(--muted)">1 state badge</text>
  <rect x="434" y="130" width="86" height="32" rx="6" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="477" y="146" text-anchor="middle" font-size="9" font-weight="700" fill="var(--purple)">completion ✓</text>
  <text x="477" y="157" text-anchor="middle" font-size="9" fill="var(--muted)">first move</text>
  <text x="436" y="180" font-size="9" fill="var(--muted)">2 registry</text>
  <rect x="434" y="186" width="86" height="24" rx="6" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="477" y="202" text-anchor="middle" font-size="9" font-weight="700" fill="var(--blue)">in _finished</text>
  <text x="436" y="230" font-size="9" fill="var(--muted)">was_running=true</text>
  <text x="436" y="244" font-size="9" fill="var(--muted)">and not in consumed</text>
  <text x="436" y="258" font-size="9" fill="var(--purple)">→ decide once</text>
  <text x="436" y="272" font-size="9" fill="var(--muted)">add to set · one enq</text>
  <rect x="564" y="72" width="100" height="240" rx="9" fill="var(--panel)" stroke="var(--line)"/>
  <text x="573" y="90" font-size="9.5" font-weight="700" fill="var(--ink)">F5 · notify</text>
  <text x="573" y="104" font-size="9" fill="var(--accent-ink)">enqueue → one turn</text>
  <text x="573" y="124" font-size="9" fill="var(--muted)">1 state badge</text>
  <rect x="571" y="130" width="86" height="32" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="614" y="146" text-anchor="middle" font-size="9" font-weight="700" fill="var(--accent-ink)">notified</text>
  <text x="614" y="157" text-anchor="middle" font-size="9" fill="var(--muted)">inject msg</text>
  <text x="573" y="180" font-size="9" fill="var(--muted)">2 registry</text>
  <rect x="571" y="186" width="86" height="24" rx="6" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="614" y="202" text-anchor="middle" font-size="9" font-weight="700" fill="var(--blue)">in _finished</text>
  <text x="573" y="230" font-size="9" fill="var(--muted)">→ completion_queue</text>
  <text x="573" y="244" font-size="9" fill="var(--muted)">one new agent turn</text>
  <text x="573" y="258" font-size="9" fill="var(--muted)">then read-only via</text>
  <text x="573" y="272" font-size="9" fill="var(--muted)">_poll_observed · no eat</text>
  <line x1="117" y1="200" x2="144" y2="200" stroke="var(--accent)" stroke-width="1.6"/>
  <path d="M152,200 L144,195 L144,205 Z" fill="var(--accent)"/>
  <line x1="254" y1="200" x2="281" y2="200" stroke="var(--blue)" stroke-width="1.6"/>
  <path d="M289,200 L281,195 L281,205 Z" fill="var(--blue)"/>
  <line x1="391" y1="200" x2="418" y2="200" stroke="var(--purple)" stroke-width="1.6"/>
  <path d="M426,200 L418,195 L418,205 Z" fill="var(--purple)"/>
  <line x1="528" y1="200" x2="555" y2="200" stroke="var(--accent)" stroke-width="1.6"/>
  <path d="M563,200 L555,195 L555,205 Z" fill="var(--accent)"/>
  <rect x="10" y="324" width="660" height="122" rx="9" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="24" y="346" font-size="9.5" font-weight="700" fill="var(--ink)">Side notes · the checkpoint is not the decider · two gates split the work (only real constants 1800s/30min · STRIKE=3)</text>
  <circle cx="26" cy="368" r="4" fill="var(--blue)"/>
  <text x="38" y="372" font-size="9" fill="var(--muted)">1. processes.json checkpoint is only for gateway crash recovery of detached handles — not the completion decider</text>
  <text x="38" y="386" font-size="9" fill="var(--muted)">completion is decided entirely in-memory by the _running / _finished dicts; the checkpoint takes no part</text>
  <circle cx="26" cy="408" r="4" fill="var(--purple)"/>
  <text x="38" y="412" font-size="9" fill="var(--muted)">2. gate one was_running (producer side · kill and the reader thread both call but only one pop wins and enqueues)</text>
  <text x="38" y="426" font-size="9" fill="var(--muted)">gate two _completion_consumed / _poll_observed (consumer side · anything already waited or polled is skipped by the drain)</text>
</svg>
<div class="fig-cap"><b>One process, frame by frame</b>: 5 frames follow a single <span class="mono">background=true</span> process — <span class="mono">spawn</span> into <span class="mono">_running</span> → <span class="mono">running</span> monitor → exit via <span class="mono">_move_to_finished</span> into <span class="mono">_finished</span> → <strong>de-dup gate</strong> decides completion once → <span class="mono">completion_queue</span> triggers <strong>one</strong> new turn. Both gates appear only in frame <span class="mono">F4</span> and the bottom notes: gate one <span class="mono">was_running</span> producer-side, gate two <span class="mono">_completion_consumed</span> / <span class="mono">_poll_observed</span> consumer-side; the <span class="mono">processes.json</span> checkpoint is crash-recovery only and <strong>takes no part</strong> in the completion decision.</div>
</div>

<p>Stop covered, look covered — one mechanism is left: how a "save" lands either <strong>whole</strong> or <strong>not at all</strong>, and how that atomic guarantee collapses the moment a <strong>temp file is put in the wrong directory</strong>.</p>

<h3>🔬 28.3 · Atomic file edits: a same-directory temp + rename, verified by a post-write re-read</h3>
<p>The last of the three mechanisms is <strong>landing bytes</strong>. Hermes' file capability is four tools — <span class="mono">read_file</span> / <span class="mono">write_file</span> / <span class="mono">patch</span> (replace) / <span class="mono">search</span>, all implemented by the shell backend in <span class="mono">tools/file_operations.py</span>. The <strong>two that mutate disk</strong> (write and patch) never overwrite the target in place; they both funnel through one private method, <span class="mono">_atomic_write()</span>: <strong>create a temp file in the target's own directory, write the new content into it, then rename it atomically over the target in one step</strong>.</p>
<p><span class="mono">_atomic_write()</span> is one fully-quoted shell script: <span class="mono">mktemp -p "$d"</span> lands the temp in the <strong>target's own directory</strong> <span class="mono">d = dirname(path)</span> (not <span class="mono">/tmp</span>), the content streams in over <strong>stdin</strong> (sidestepping ARG_MAX), and after <span class="mono">cat &gt; "$tmp"</span> writes the draft, <span class="mono">mv -f "$tmp" "$t"</span> swaps it in one step. Three details to keep: ① it is <strong>not</strong> a Python call like <span class="mono">os.replace()</span> — it lands on a real shell <span class="mono">mv</span> (semantically a same-filesystem atomic rename); ② a <span class="mono">trap 'rm -f "$tmp"' EXIT</span> guarantees <strong>every failure path</strong> (cat fails, mv fails, a signal) cleans the temp up, never leaving half a <span class="mono">.hermes-tmp</span> turd beside the user's data; ③ before writing it does a best-effort <span class="mono">stat</span> + <span class="mono">chmod</span> to copy the target's existing mode onto the temp, so the atomic swap doesn't silently <strong>widen or narrow</strong> permissions.</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">tools/file_operations.py:937 · abridged</span></div><pre>    def _atomic_write(self, path: str, content: str) -&gt; "ExecuteResult":
        q_path = self._escape_shell_arg(path)
        parent = os.path.dirname(path) or "."
        q_parent = self._escape_shell_arg(parent)
        tmpl = self._escape_shell_arg(".hermes-tmp.XXXXXX")
        script = (
            "set -e; "
            f"d={q_parent}; t={q_path}; "
            'tmp="$(mktemp -p "$d" ' + tmpl + ' 2&gt;/dev/null '
            '|| mktemp "$d/.hermes-tmp.$$.XXXXXX" 2&gt;/dev/null '
            '|| { tmp="$d/.hermes-tmp.$$"; : &gt; "$tmp" &amp;&amp; echo "$tmp"; })"; '
            "trap 'rm -f \"$tmp\"' EXIT; "
            'cat &gt; "$tmp"; '
            'mv -f "$tmp" "$t"; '
            "trap - EXIT"
        )
        return self._exec(script, stdin_data=content)</pre></div>
<p><strong>The core trap is right here: the whole atomicity hangs on one unremarkable premise — the temp file shares the target's directory.</strong> A rename is only atomic <strong>within the same filesystem</strong> — the kernel just repoints one directory entry from the old inode to the new one, in a single step. The moment the temp lands on <strong>a different filesystem</strong> (say you draft into <span class="mono">/tmp</span> and then mv back into the project dir), <span class="mono">mv</span> can't do a true rename — it <strong>degrades to copy-into-target + unlink-source</strong>, two steps; and if a crash / power loss hits mid-copy, the target is only half-written, leaving a <strong>torn, corrupt file</strong> — exactly the failure atomic writes set out to kill. So the <span class="mono">-p "$d"</span> in <span class="mono">mktemp -p "$d"</span> is <strong>load-bearing</strong>, not a casual choice.</p>
<p><span class="mono">patch</span> (replace) adds a <strong>post-write verification</strong> on top of <span class="mono">_atomic_write</span>. It reads the file in, strips any UTF-8 BOM, locates <span class="mono">old_string</span> by <strong>fuzzy matching</strong> — and unless <span class="mono">replace_all=True</span> it requires the match to be <strong>unique</strong>, erroring out on multiple or zero hits; after substituting it normalizes to the file's <strong>existing line ending</strong> (LF / CRLF) before writing back (the BOM is restored on the way out, so the round-trip preserves the marker). Once it lands, it <strong>re-reads the file and compares it byte-for-byte against what it meant to write</strong>: a mismatch errors with "<span class="mono">The patch did not persist</span>" and asks for a re-read + retry. This verification is aimed at <strong>silent persistence failures</strong> — backend FS oddities, a truncated pipe, <strong>and a concurrent edit by another task</strong>: if something else touches the same file between patch's write and the re-read, the bytes read back won't equal this turn's <span class="mono">new_content</span>, the <strong>check fails</strong>, and patch won't falsely report success.</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">tools/file_operations.py:1534</span></div><pre>        # Post-write verification — re-read the file and confirm the bytes we
        # intended to write actually landed. Catches silent persistence
        # failures (backend FS oddities, race with another task, truncated
        # pipe, etc.) that would otherwise return success-with-diff while the
        # file is unchanged on disk.
        verify_cmd = f"cat {self._escape_shell_arg(path)} 2&gt;/dev/null"
        verify_result = self._exec(verify_cmd)
        if verify_result.exit_code != 0:
            return PatchResult(error=f"Post-write verification failed: could not re-read {path}")</pre></div>
<p>A ring of guards surrounds the four tools: a <strong>path-security deny-list</strong> blocks writes to sensitive files before write / patch — <span class="mono">~/.ssh/{id_rsa,authorized_keys,config}</span>, the per-profile and top-level <span class="mono">.env</span>, <span class="mono">.git-credentials</span>, <span class="mono">/etc/{passwd,shadow,sudoers}</span>, plus prefixes like <span class="mono">~/.aws</span> and <span class="mono">/etc/systemd</span> — so one stray write can't leak credentials or break the system. <span class="mono">read_file</span> is <strong>paginated</strong> by default (offset / limit, 500 lines default, 2000 cap) and carries <strong>binary detection</strong> — over 30% non-printable chars is judged binary and its body isn't returned, while image extensions are base64'd onto the vision channel. <span class="mono">search</span> is <strong>line-level</strong> (<span class="mono">output_mode="content"</span> yields matching lines + optional context), with content search and filename search kept separate. None of this changes the throughline: <strong>every write first stages a "whole new file," then makes it take effect in one atomic act — readers never see an in-between state.</strong></p>

<div class="figure">
<svg viewBox="0 0 680 466" role="img" aria-label="Safe file-edit pipeline. Vertical spine top to bottom: target file t lives in the same directory d equals dirname(path); mktemp -p first creates a hidden temp .hermes-tmp.XXXXXX in that directory, cat writes the new content into the temp draft, the patch path then re-reads the file and compares it byte-for-byte against the intended content, and only on a passing verify does mv -f atomically rename the temp over the target, so readers see either the old file or the whole new file, never a torn in-between state. Right failure branch: on a verify miss or a write error, trap runs rm -f to drop the temp and the original file is left untouched, a rollback. Left annotation: temp sharing the target directory means the same filesystem, so mv is a true rename.">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">Safe edit pipeline · same-dir temp → write → verify → atomic rename</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">draft into a same-dir temp, verify, then mv -f atomically; on any failure roll back, original untouched</text>
  <rect x="130" y="64" width="200" height="44" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="230" y="85" text-anchor="middle" font-size="12" font-weight="700" fill="var(--blue)">① target file t</text>
  <text x="230" y="101" text-anchor="middle" font-size="9" fill="var(--muted)">same dir d = dirname(path)</text>
  <line x1="230" y1="110" x2="230" y2="124" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M230,132 L225,123 L235,123 Z" fill="var(--muted)"/>
  <rect x="130" y="132" width="200" height="50" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>
  <text x="230" y="153" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--accent-ink)">② mktemp -p "$d"</text>
  <text x="230" y="170" text-anchor="middle" font-size="9" fill="var(--muted)">same-dir hidden temp · .hermes-tmp.XXXXXX</text>
  <line x1="230" y1="184" x2="230" y2="198" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M230,206 L225,197 L235,197 Z" fill="var(--muted)"/>
  <text x="14" y="150" font-size="9.5" font-weight="700" fill="var(--accent-ink)">same dir = same FS</text>
  <text x="14" y="165" font-size="9" fill="var(--muted)">mv is a true rename</text>
  <text x="14" y="178" font-size="9" fill="var(--muted)">(see fig ⑬ below)</text>
  <line x1="120" y1="156" x2="128" y2="156" stroke="var(--accent)" stroke-width="1.4"/>
  <rect x="130" y="206" width="200" height="44" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="230" y="227" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">③ cat &gt; "$tmp" write draft</text>
  <text x="230" y="243" text-anchor="middle" font-size="9" fill="var(--muted)">content via stdin · no ARG_MAX limit</text>
  <line x1="230" y1="252" x2="230" y2="266" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M230,274 L225,265 L235,265 Z" fill="var(--muted)"/>
  <rect x="130" y="274" width="200" height="58" rx="10" fill="var(--amber-soft)" stroke="var(--amber)" stroke-width="2"/>
  <text x="230" y="295" text-anchor="middle" font-size="12" font-weight="700" fill="var(--amber)">④ re-read &amp; verify bytes</text>
  <text x="230" y="311" text-anchor="middle" font-size="9" fill="var(--ink)">patch: re-read vs the intended content</text>
  <text x="230" y="325" text-anchor="middle" font-size="9" fill="var(--ink)">catches silent persist fail / concurrent edit</text>
  <line x1="230" y1="332" x2="230" y2="346" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M230,354 L225,345 L235,345 Z" fill="var(--muted)"/>
  <text x="238" y="345" font-size="9" fill="var(--muted)">verified</text>
  <rect x="458" y="274" width="206" height="58" rx="10" fill="var(--red-soft)" stroke="var(--red)" stroke-width="1.5"/>
  <text x="466" y="294" font-size="10" font-weight="700" fill="var(--red)">fail branch · error / verify miss</text>
  <text x="466" y="311" font-size="9" fill="var(--ink)">trap 'rm -f "$tmp"' drops temp</text>
  <text x="466" y="326" font-size="9" fill="var(--ink)">original left untouched (rollback)</text>
  <line x1="330" y1="303" x2="450" y2="303" stroke="var(--red)" stroke-width="1.3" stroke-dasharray="3 3"/>
  <path d="M458,303 L449,298 L449,308 Z" fill="var(--red)"/>
  <rect x="130" y="354" width="200" height="50" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="230" y="375" text-anchor="middle" font-size="12" font-weight="700" fill="var(--accent-ink)">⑤ mv -f "$tmp" "$t"</text>
  <text x="230" y="391" text-anchor="middle" font-size="9" fill="var(--muted)">atomic rename · one-step swap</text>
  <line x1="230" y1="406" x2="230" y2="420" stroke="var(--muted)" stroke-width="1.4"/>
  <path d="M230,428 L225,419 L235,419 Z" fill="var(--muted)"/>
  <rect x="130" y="428" width="200" height="34" rx="9" fill="var(--panel-2)" stroke="var(--accent)" stroke-width="1.5"/>
  <text x="230" y="449" text-anchor="middle" font-size="10" font-weight="700" fill="var(--ink)">⑥ readers: old or whole-new (never torn)</text>
</svg>
<div class="fig-cap"><b>Safe edit pipeline</b>: write / patch go through <span class="mono">_atomic_write</span> — <span class="mono">mktemp -p "$d"</span> makes a temp in the <strong>same dir</strong> → <span class="mono">cat</span> writes the draft → (patch also <strong>re-reads and verifies byte-for-byte</strong>) → <span class="mono">mv -f</span> renames it in atomically; any step fails and <span class="mono">trap</span> drops the temp, <strong>original untouched</strong>. Readers see either the old or the whole new file, <strong>never torn</strong>.</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 360" role="img" aria-label="Cross-filesystem rename breaks atomicity, a comparison. Left column same filesystem: the temp shares the target directory, rename is a single atomic step, the kernel just repoints the directory entry to the new inode, readers see either the old inode or the new inode, and after a power loss or crash the original file is intact, so it is atomic and never torn. Right column cross filesystem: the temp lands on another filesystem such as /tmp, mv cannot do a true rename and degrades to first copying into the target then unlinking the source, two steps, and if a crash hits mid-copy the target is only half-written, leaving a torn half file, so it is non-atomic and may be corrupt. Bottom takeaway bar: therefore the temp must use mktemp -p into the target's own directory to guarantee the same filesystem and let mv be a true atomic rename.">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">Cross-FS rename breaks atomicity · why temp must share the target dir</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">same FS = one-step atomic pointer swap; cross FS = mv degrades to copy + unlink, a crash mid-way leaves half a file</text>
  <rect x="20" y="70" width="300" height="206" rx="10" fill="var(--panel)" stroke="var(--line)"/>
  <rect x="20" y="70" width="300" height="44" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>
  <text x="170" y="92" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--accent-ink)">same FS · true atomic rename</text>
  <text x="170" y="107" text-anchor="middle" font-size="9" fill="var(--muted)">temp shares target dir (mktemp -p "$d")</text>
  <text x="34" y="140" font-size="9.5" fill="var(--ink)">① rename() = single-step entry swap</text>
  <text x="34" y="164" font-size="9.5" fill="var(--ink)">② repoints to new inode, old freed</text>
  <text x="34" y="188" font-size="9.5" fill="var(--ink)">③ readers: old or new inode, never both</text>
  <text x="34" y="212" font-size="9.5" fill="var(--ink)">④ power loss / crash: original intact</text>
  <rect x="38" y="234" width="264" height="30" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="170" y="253" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--accent-ink)">✓ atomic · never a torn read</text>
  <rect x="360" y="70" width="300" height="206" rx="10" fill="var(--panel)" stroke="var(--line)"/>
  <rect x="360" y="70" width="300" height="44" rx="10" fill="var(--red-soft)" stroke="var(--red)" stroke-width="1.5"/>
  <text x="510" y="92" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--red)">cross FS · mv degrades to copy+unlink</text>
  <text x="510" y="107" text-anchor="middle" font-size="9" fill="var(--muted)">temp on another FS (e.g. /tmp)</text>
  <text x="374" y="140" font-size="9.5" fill="var(--ink)">① cross-device rename fails → mv fallback</text>
  <text x="374" y="164" font-size="9.5" fill="var(--ink)">② degrades to copy-in + unlink-source</text>
  <text x="374" y="188" font-size="9.5" fill="var(--ink)">③ crash mid-copy: target half-written</text>
  <text x="374" y="212" font-size="9.5" fill="var(--ink)">④ leaves a torn / half-corrupt file</text>
  <rect x="378" y="234" width="264" height="30" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="510" y="253" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--red)">✗ non-atomic · may read a corrupt file</text>
  <rect x="20" y="296" width="640" height="48" rx="10" fill="var(--panel-2)" stroke="var(--accent)"/>
  <text x="340" y="317" text-anchor="middle" font-size="10" font-weight="700" fill="var(--ink)">Takeaway: temp must mktemp -p into the target's own dir → same FS, mv becomes a true atomic rename</text>
  <text x="340" y="334" text-anchor="middle" font-size="9" fill="var(--muted)">the temp's location is load-bearing — a cross-dir shortcut trades the atomic guarantee for a maybe-half-written file</text>
</svg>
<div class="fig-cap"><b>Cross-FS rename breaks atomicity</b>: <strong>same dir = same filesystem</strong>, so <span class="mono">mv</span> is a one-step atomic rename (repoint the directory entry to the new inode) and a crash shows only old or whole-new; <strong>across filesystems</strong> <span class="mono">mv</span> degrades to <span class="mono">copy + unlink</span>, two steps, a mid-copy crash leaving half a file. So the temp must <span class="mono">mktemp -p "$d"</span> into the <strong>target's own dir</strong> — the location is load-bearing.</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 416" role="img" aria-label="Filesystem state snapshots per frame: _atomic_write overwrites foo.py, and along the timeline each frame draws which files exist right now in the same project directory and whether each holds old or new bytes. Frame 1 stage: mktemp -p &quot;$d&quot; makes an empty temp file .hermes-tmp.XXXXXX in foo.py's own directory, while foo.py still holds the old, intact bytes. Frame 2 write temp: cat writes all the new bytes into .hermes-tmp.XXXXXX, foo.py is still old and intact, and this is the crash-safe point because a crash here only drops the temp file and never touches the original. Frame 3 atomic swap: mv -f atomically renames the temp into foo.py in one step, so the directory's foo.py now holds the new bytes and the temp file is gone, with no half file. Frame 4 read back: on the patch path, after writing it re-reads foo.py with cat byte-for-byte to confirm it landed, and a mismatch errors out and rolls back. Two bottom notes: one, use shell mv -f over one terminal backend so docker and ssh behave alike, not os.replace; two, the location is load-bearing because mktemp -p &quot;$d&quot; must land in the target's own dir on the same filesystem, since across filesystems mv degrades to copy plus unlink, two steps, and a mid-copy crash leaves half a file, breaking atomicity. No frame ever leaves foo.py half-written.">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">Filesystem state per frame · no frame leaves foo.py half-written</text>
  <text x="20" y="46" font-size="10.5" fill="var(--muted)">_atomic_write overwrites foo.py: each frame shows which files exist now, old / new / empty</text>
  <text x="600" y="34" font-size="22">📸</text>

  <rect x="10" y="64" width="128" height="240" rx="10" fill="var(--panel)" stroke="var(--line)"/>
  <text x="18" y="84" font-size="9.5" font-weight="700" fill="var(--ink)">Frame 1 · stage</text>
  <text x="18" y="99" font-size="9" fill="var(--blue)">empty temp in same dir</text>
  <rect x="18" y="106" width="112" height="148" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="24" y="122" font-size="9" fill="var(--muted)">📁 project dir/</text>
  <rect x="24" y="128" width="100" height="46" rx="6" fill="var(--panel)" stroke="var(--line)"/>
  <text x="30" y="144" font-size="9" fill="var(--ink)">foo.py</text>
  <rect x="30" y="150" width="88" height="16" rx="3" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="74" y="162" text-anchor="middle" font-size="9" fill="var(--accent-ink)">old · intact</text>
  <rect x="24" y="180" width="100" height="46" rx="6" fill="var(--panel)" stroke="var(--line)"/>
  <text x="30" y="196" font-size="9" fill="var(--ink)">.hermes-tmp.XXXXXX</text>
  <rect x="30" y="202" width="88" height="16" rx="3" fill="var(--panel)" stroke="var(--blue)" stroke-dasharray="4 3"/>
  <text x="74" y="214" text-anchor="middle" font-size="9" fill="var(--blue)">empty</text>
  <rect x="18" y="262" width="112" height="38" rx="7" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="24" y="278" font-size="9" fill="var(--blue)">mktemp -p &quot;$d&quot;</text>
  <text x="24" y="292" font-size="9" fill="var(--muted)">into foo.py's dir</text>

  <line x1="140" y1="186" x2="178" y2="186" stroke="var(--line)" stroke-width="1.8"/>
  <path d="M184,186 L176,182 L176,190 Z" fill="var(--line)"/>
  <text x="162" y="168" text-anchor="middle" font-size="9" fill="var(--blue)">cat &gt; tmp</text>
  <text x="162" y="180" text-anchor="middle" font-size="9" fill="var(--muted)">write</text>

  <rect x="187" y="64" width="128" height="240" rx="10" fill="var(--panel)" stroke="var(--line)"/>
  <text x="195" y="84" font-size="9.5" font-weight="700" fill="var(--ink)">Frame 2 · write temp</text>
  <text x="195" y="99" font-size="9" fill="var(--blue)">new bytes all in temp</text>
  <rect x="195" y="106" width="112" height="148" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="201" y="122" font-size="9" fill="var(--muted)">📁 project dir/</text>
  <rect x="201" y="128" width="100" height="46" rx="6" fill="var(--panel)" stroke="var(--line)"/>
  <text x="207" y="144" font-size="9" fill="var(--ink)">foo.py</text>
  <rect x="207" y="150" width="88" height="16" rx="3" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="251" y="162" text-anchor="middle" font-size="9" fill="var(--accent-ink)">old · still intact</text>
  <rect x="201" y="180" width="100" height="46" rx="6" fill="var(--panel)" stroke="var(--blue)"/>
  <text x="207" y="196" font-size="9" fill="var(--ink)">.hermes-tmp.XXXXXX</text>
  <rect x="207" y="202" width="88" height="16" rx="3" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="251" y="214" text-anchor="middle" font-size="9" fill="var(--blue)">new bytes · all</text>
  <rect x="195" y="262" width="112" height="38" rx="7" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="201" y="278" font-size="9" font-weight="700" fill="var(--red)">⛨ crash-safe point</text>
  <text x="201" y="292" font-size="9" fill="var(--muted)">crash drops temp · foo.py intact</text>

  <line x1="317" y1="186" x2="355" y2="186" stroke="var(--line)" stroke-width="1.8"/>
  <path d="M361,186 L353,182 L353,190 Z" fill="var(--line)"/>
  <text x="339" y="168" text-anchor="middle" font-size="9" fill="var(--accent-ink)">mv -f</text>
  <text x="339" y="180" text-anchor="middle" font-size="9" fill="var(--muted)">tmp→foo.py</text>

  <rect x="364" y="64" width="128" height="240" rx="10" fill="var(--panel)" stroke="var(--line)"/>
  <text x="372" y="84" font-size="9.5" font-weight="700" fill="var(--ink)">Frame 3 · atomic swap</text>
  <text x="372" y="99" font-size="9" fill="var(--accent-ink)">mv -f swaps in one step</text>
  <rect x="372" y="106" width="112" height="148" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="378" y="122" font-size="9" fill="var(--muted)">📁 project dir/</text>
  <rect x="378" y="128" width="100" height="46" rx="6" fill="var(--panel)" stroke="var(--accent)"/>
  <text x="384" y="144" font-size="9" fill="var(--ink)">foo.py</text>
  <rect x="384" y="150" width="88" height="16" rx="3" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="428" y="162" text-anchor="middle" font-size="9" fill="var(--accent-ink)">new · in place</text>
  <rect x="378" y="180" width="100" height="46" rx="6" fill="var(--panel)" stroke="var(--line)" stroke-dasharray="4 3"/>
  <text x="384" y="196" font-size="9" fill="var(--muted)">.hermes-tmp.XXXXXX</text>
  <text x="428" y="214" text-anchor="middle" font-size="9" fill="var(--muted)">(renamed away)</text>
  <rect x="372" y="262" width="112" height="38" rx="7" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="378" y="278" font-size="9" font-weight="700" fill="var(--accent-ink)">mv -f atomic rename</text>
  <text x="378" y="292" font-size="9" fill="var(--muted)">one step · no half file</text>

  <line x1="494" y1="186" x2="532" y2="186" stroke="var(--line)" stroke-width="1.8"/>
  <path d="M538,186 L530,182 L530,190 Z" fill="var(--line)"/>
  <text x="516" y="168" text-anchor="middle" font-size="9" fill="var(--purple)">patch path</text>
  <text x="516" y="180" text-anchor="middle" font-size="9" fill="var(--muted)">cat read-back</text>

  <rect x="541" y="64" width="128" height="240" rx="10" fill="var(--panel)" stroke="var(--line)"/>
  <text x="549" y="84" font-size="9.5" font-weight="700" fill="var(--ink)">Frame 4 · read back</text>
  <text x="549" y="99" font-size="9" fill="var(--purple)">cat re-reads byte-for-byte</text>
  <rect x="549" y="106" width="112" height="148" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="555" y="122" font-size="9" fill="var(--muted)">📁 project dir/</text>
  <rect x="555" y="128" width="100" height="46" rx="6" fill="var(--panel)" stroke="var(--purple)"/>
  <text x="561" y="144" font-size="9" fill="var(--ink)">foo.py ✓</text>
  <rect x="561" y="150" width="88" height="16" rx="3" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="605" y="162" text-anchor="middle" font-size="9" fill="var(--accent-ink)">new · on disk</text>
  <rect x="555" y="180" width="100" height="46" rx="6" fill="var(--panel)" stroke="var(--line)" stroke-dasharray="4 3"/>
  <text x="561" y="196" font-size="9" fill="var(--muted)">(no temp file)</text>
  <text x="605" y="214" text-anchor="middle" font-size="9" fill="var(--purple)">cat foo.py == expected</text>
  <rect x="549" y="262" width="112" height="38" rx="7" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="555" y="278" font-size="9" font-weight="700" fill="var(--purple)">✓ verify read-back</text>
  <text x="555" y="292" font-size="9" fill="var(--muted)">mismatch → error + rollback</text>

  <rect x="10" y="312" width="662" height="98" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="24" y="331" font-size="9.5" font-weight="700" fill="var(--ink)">Note · two premises you cannot drop</text>
  <circle cx="26" cy="350" r="4" fill="var(--accent)"/>
  <text x="38" y="354" font-size="9" fill="var(--muted)">① use shell mv -f over one terminal backend (docker / ssh alike), not os.replace — one atomic path</text>
  <circle cx="26" cy="378" r="4" fill="var(--red)"/>
  <text x="38" y="378" font-size="9" fill="var(--muted)">② the location is load-bearing: mktemp -p &quot;$d&quot; must land in the target's own dir / same FS;</text>
  <text x="48" y="394" font-size="9" fill="var(--muted)">across filesystems mv degrades to copy + unlink, a mid-copy crash leaves half a file → atomicity broken</text>
</svg>
<div class="fig-cap"><b>Filesystem state per frame</b>: four file snapshots of one directory along the timeline — <span class="mono">Frame 1</span> <span class="mono">mktemp -p &quot;$d&quot;</span> makes an empty same-dir temp, <span class="mono">foo.py</span> old &amp; intact → <span class="mono">Frame 2</span> new bytes all in temp, <span class="mono">foo.py</span> <strong>still intact</strong> (<span style="color:var(--red)">⛨ crash-safe point</span>: a crash only drops the temp) → <span class="mono">Frame 3</span> <span class="mono">mv -f</span> atomically renames in one step, <span class="mono">foo.py</span> turns new, temp gone → <span class="mono">Frame 4</span> (patch path) <span class="mono">cat</span> re-reads byte-for-byte to <strong>verify</strong>. The point: <strong>no frame leaves <span class="mono">foo.py</span> half-written</strong>; the premise is a same-dir temp + <span class="mono">mv -f</span> rather than <span class="mono">os.replace</span>.</div>
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · correctness boundaries in an async world</div>
  This chapter's three mechanisms — <strong>interrupt propagation</strong>, <strong>background-process lifecycle</strong>, and <strong>atomic file edits</strong> — manage three seemingly unrelated jobs on the surface ("stop / look / save"), yet guard one line underneath: <strong>in an async, continuously-running world that may be interrupted or restarted at any moment, weld "looks done" and "is actually done" tightly together.</strong>
  <p style="margin:.5rem 0 0"><strong>The boundary each one guards:</strong> ① interrupt is a <strong>cooperative contract</strong> — set a flag, take it at a loop boundary, fan out to subagents explicitly, and never hard-kill a thread from outside, so a "stop" is both <strong>timely</strong> and <strong>doesn't tear</strong> a tool mid-execution; ② background processes give an <strong>honest status</strong> — a completion fires at most once (producer-side <span class="mono">was_running</span> + consumer-side <span class="mono">_completion_consumed</span>, two gates), and an <strong>in-process illusion is never passed off as durable</strong>; ③ landing bytes gives an <strong>atomic guarantee</strong> — same-dir temp + rename + post-write verify, so readers see either the old or the whole new file.</p>
  <p style="margin:.5rem 0 0"><strong>Echoing the book's two throughlines:</strong> this is the bedrock of <strong>resilience</strong> — failure bounded, rollbackable (<span class="mono">trap</span> drops the temp), recoverable (detached / cron), correctable (the re-read verify); and it guards the <strong>narrow waist</strong>: the core exposes only a few minimal primitives — <span class="mono">/stop</span>, query status, atomic write — and sinks the real complexity into the loop boundary, the process registry, and one shell script. Those three seams where "looks done" and "is done" quietly diverge are exactly <strong>the bedrock of reliable autonomous, continuous operation</strong>.</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Interrupt is cooperative, not preemptive</strong>: <span class="mono">/stop</span> only sets an <span class="mono">_interrupt_requested</span> flag; the main loop takes it at an <strong>iteration boundary</strong>. Python can't kill a thread, so the streaming callback / the non-streaming background check / the retry backoff (every <strong>200ms</strong>) all rely on <strong>voluntary polling</strong>. Interrupt fans out to <strong>subagents by explicit hand-wiring</strong> — walk <span class="mono">_active_children</span> calling <span class="mono">child.interrupt()</span>; a missed registration or an async detach is a <strong>silent broken link</strong>.</li>
    <li><strong>Background durability is mostly an in-process illusion</strong>: the <span class="mono">_running</span> / <span class="mono">_finished</span> dicts, output buffer, and reader / watcher threads all live in memory and are lost on restart; detached recovery only takes host-PID processes with a matching <span class="mono">start_time</span>, and offers status + kill only. For <strong>true cross-restart</strong> work use <span class="mono">cron</span> or <span class="mono">terminal(background, notify_on_complete)</span>.</li>
    <li><strong>A completion fires at most once</strong>: the producer-side <span class="mono">was_running</span> guard (only one caller's <span class="mono">pop</span> gets non-<span class="mono">None</span>) plus the consumer-side <span class="mono">_completion_consumed</span> / <span class="mono">_poll_observed</span> dedup gates; a watch hitting <span class="mono">WATCH_STRIKE_LIMIT</span>=3 disables watch and flips <span class="mono">notify_on_complete</span>, merging into the same exit.</li>
    <li><strong>Atomic writes ride a same-dir temp + rename</strong>: <span class="mono">_atomic_write</span> uses <span class="mono">mktemp -p "$d"</span> to make a temp in the <strong>target's own dir</strong>, <span class="mono">cat</span> writes, <span class="mono">mv -f</span> swaps it in atomically, <span class="mono">trap</span> cleans up on failure; a <strong>cross-filesystem rename is not atomic</strong> (degrades to copy + unlink, half-write corruption), so the temp's location is load-bearing.</li>
    <li><strong>patch verifies with a post-write re-read</strong>: fuzzy match must be <strong>unique</strong>, BOM / CRLF preserved, only <strong>newly-introduced</strong> lint surfaced; after landing it re-reads and compares byte-for-byte, so a <strong>concurrent edit</strong> fails the check and reports "did not persist" instead of a false success. Plus the path deny-list, read pagination, binary / image interception, and line-level search.</li>
    <li><strong>The shared idea</strong>: all three guard <strong>correctness boundaries in an async world</strong> — stop timely without tearing, state honest without duplicates, land bytes atomically without half-writes; the <strong>bedrock of reliable autonomous, continuous operation</strong>, and one more landing of resilience and the narrow waist.</li>
  </ul>
</div>
""",
}
