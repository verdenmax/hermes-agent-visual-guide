"""part2 — 第二部分 · Agent 核心：ch6 System Prompt 与缓存 / ch7 消息流 / ch8 工具系统。


逐章 LESSON_06/07/08。codefile 标「节选/简化」者为可读性重排，真实性见 docs/superpowers/specs/chapters/。
"""

LESSON_06 = {
    "zh": r"""
<p class="lead">
这是全书的<strong>核心章</strong>。Hermes 几乎每一个设计，最后都要回答同一个问题：<strong>会不会破坏 prompt 缓存？</strong>本章讲清三件事——system prompt 如何分<strong>三层</strong>组装、为什么它在一次会话里<strong>逐字节不变</strong>、以及 Anthropic 的缓存断点如何把多轮对话的输入成本砍掉 <strong>~75%</strong>。记住一句话就够了：<strong>system prompt 每个会话只建一次，唯一的例外是上下文压缩</strong>。
</p>

<div class="card analogy">
  <div class="tag">🔌 生活类比</div>
  把 system prompt 想成一栋楼的<strong>地基与承重墙</strong>：开工时浇筑<strong>一次</strong>，整栋楼盖完都靠它，<strong>绝不会盖到一半再砸墙重浇</strong>——那样楼会塌。再换个角度看缓存：它像一张<strong>提前付清的“前缀月卡”</strong>——第一轮把这堵长长的前缀<strong>全款</strong>算一遍、存进上游缓存，之后每一轮只要前缀<strong>一个字节都没变</strong>，就只补尾款（新增的那几句话），省下的正是反复重算前缀的钱。一旦你中途改了前缀（换工具、重载记忆、重建 prompt），月卡作废，每轮都得重新付全款。
</div>

<h2>宏观：按稳定度排好序的三层</h2>

<div class="card macro">
  <div class="tag">🌍 宏观理解</div>
  system prompt 不是一坨随手拼的字符串，而是<strong>按稳定度排好序的三层</strong>：<span class="mono">stable</span>（身份 / 工具 / 技能 / 环境，几乎不变）、<span class="mono">context</span>（调用方消息 + 项目上下文文件，整个会话固定）、<span class="mono">volatile</span>（记忆快照 / 用户画像 / 时间戳，最容易变）。三层用 <span class="mono">\n\n</span> 拼成一整串，<strong>会话开始时构建一次</strong>，缓存在 <span class="mono">agent._cached_system_prompt</span> 上，之后每一轮原样复用。把<strong>最易变的内容压到最后</strong>，是为了即便它变了，也只动到整串的<strong>尾巴</strong>，<strong>不殃及前面已被缓存的前缀</strong>。
</div>

<p>这条纪律为什么值得<strong>全书</strong>为它让路？因为它直接决定了<strong>成本量级</strong>。个人 agent 的对话往往是<strong>长会话</strong>——几十上百轮，那堵长长的前缀被反复重发。缓存命中时，长对话的边际成本几乎只剩“新增的那几句”；缓存一破，每轮都得从头按全价再算一遍。第 1 章那条“prompt 缓存神圣不可侵犯”的铁律，到这一章终于落到了<strong>具体的代码与数字</strong>上。</p>

<p>为什么守这条纪律如此<strong>反直觉</strong>？因为每一轮都飘着“把上下文刷新一下”的诱惑——补个最新时间戳、把刚写的记忆读回来、按当前任务换一套工具。Hermes 偏偏<strong>反着来</strong>：<span class="mono">volatile</span> 里的记忆快照是<strong>会话开始那一刻</strong>取的，整轮对话都端着这份“略旧”的上下文不动，宁可牺牲一点新鲜度，也要把前缀<strong>冻死</strong>。这正是<strong>缓存与时效之间</strong>的取舍——长会话里省下的成本，远比“记忆晚几轮才更新”值钱；真要刷新，自有压缩那一下统一兜底（第 15 章），把本会话写下的东西一次性折进前缀。</p>

<h2>三层结构：越稳定越靠前</h2>
<p>组装入口是 <span class="mono">build_system_prompt_parts()</span>（<span class="mono">system_prompt.py:113</span>），它返回一个 <span class="mono">{stable, context, volatile}</span> 三键字典。三层的顺序绝非随意——<strong>越稳定的越靠前，越易变的越靠后</strong>：</p>

<div class="layers">
  <div class="layer l-core"><div class="lh"><span class="badge">stable · 最稳</span><span class="name">身份 / 工具 / 技能 / 环境</span></div>
    <div class="ld">SOUL.md 或 DEFAULT_AGENT_IDENTITY、工具与计算机使用指引、<strong>技能清单</strong>（第 9 章）、按模型族的操作指引、环境与平台提示。整个会话几乎<strong>恒定</strong>。</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">context · 会话内固定</span><span class="name">system_message + 上下文文件</span></div>
    <div class="ld">调用方传入的 <span class="mono">system_message</span>，加上 <span class="mono">TERMINAL_CWD</span> 下发现的 <strong>AGENTS.md / .cursorrules</strong> 等项目文件。会话期间<strong>不变</strong>。</div></div>
  <div class="layer l-app"><div class="lh"><span class="badge">volatile · 最易变</span><span class="name">记忆 / USER.md / 时间戳</span></div>
    <div class="ld">记忆快照、<strong>USER.md 用户画像</strong>（第 11 章）、外部记忆 provider 块、时间戳 / 会话 / 模型 / provider 行。最可能变，所以<strong>压到三层最后</strong>。</div></div>
</div>

<p>为什么非要<strong>分三层</strong>、而不是把所有东西揉成一段？因为缓存是<strong>前缀</strong>缓存——它从头开始逐字节比对，遇到第一个不同的字节，就<strong>从那里往后全部失效</strong>。如果把易变的时间戳、记忆混在最前面，那每轮变一下、整段前缀就废了。分层的本质，是把“几乎不变”“会话内不变”“每轮可能变”的三类内容<strong>物理隔离</strong>，让易变只落在整串的<strong>末尾</strong>。</p>

<p>这套“一次构建、整会话复用”的纪律，被 <span class="mono">system_prompt.py</span> 的模块 docstring 一字钉死：</p>
<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/system_prompt.py</span><span class="ln">3-19 · 节选</span></div>
  <pre><span class="cm">The agent's system prompt is built once per session and reused across all</span>
<span class="cm">turns — only context compression triggers a rebuild.  This keeps the</span>
<span class="cm">upstream prefix cache warm.</span>

<span class="cm">Three tiers are joined with `\n\n`:</span>
  * stable   — identity (SOUL.md or DEFAULT_AGENT_IDENTITY), tool guidance,
               computer-use guidance, nous subscription block, tool-use
               enforcement guidance + per-model operational guidance,
               skills prompt, alibaba model-name workaround,
               environment hints, platform hints.
  * context  — caller-supplied system_message plus context files
               (AGENTS.md / .cursorrules / etc.) discovered under TERMINAL_CWD.
  * volatile — memory snapshot, USER.md profile, external memory
               provider block, timestamp/session/model/provider line.</pre>
</div>
<p>盯住那句 <span class="inline">built once per session … only context compression triggers a rebuild</span>——“每会话只建一次，唯一触发重建的是上下文压缩”。这是本章、也是全书最重要的一条不变量。<span class="mono">build_system_prompt_parts()</span> 自己的 docstring 把后果说得更直白：<span class="inline">Hermes never re-renders parts of this string mid-session — that's the only way to keep upstream prompt caches warm across turns</span>。</p>

<p>这份逐字节稳定还得<strong>跨进程</strong>扛住：每一轮都把构建好的 system prompt 持久化进 <span class="mono">session_db</span>，下次<strong>恢复会话</strong>时直接取出、<strong>原样复用</strong>（注释写得很直白：<span class="inline">reuse the exact system prompt … so the Anthropic cache prefix matches</span>），连重启都不让前缀变样。只留一道闸：若运行时身份（<strong>模型 / provider</strong>）跟存档对不上，<span class="mono">_stored_prompt_matches_runtime</span> 判为 stale 才重建——你既然<strong>换了模型</strong>，上游那份旧前缀本就命中不了，重建反而是省钱。可见“稳定”不是抽象口号，而是要让真实字节在多轮、多次进程间<strong>分毫不差</strong>。</p>

<h2>缓存策略：system_and_3 打 4 个断点</h2>
<p>有了一条逐字节稳定的前缀，剩下的就是告诉上游“从哪里开始可以复用”。Hermes 只用<strong>一种</strong>布局——<span class="mono">system_and_3</span>：在 <strong>system prompt</strong> 和<strong>最后 3 条非 system 消息</strong>上各打一个 <span class="mono">cache_control</span> 断点，一共 <strong>4 个</strong>，同一个 TTL（5 分钟或 1 小时）。它把多轮对话的输入 token 成本<strong>降低 ~75%</strong>：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/prompt_caching.py</span><span class="ln">1-79 · 简化</span></div>
  <pre><span class="cm">Single layout: system_and_3. 4 cache_control breakpoints — system</span>
<span class="cm">prompt + last 3 non-system messages, all at the same TTL (5m or 1h).</span>
<span class="cm">Reduces input token costs by ~75% on multi-turn conversations ...</span>

<span class="kw">def</span> <span class="fn">apply_anthropic_cache_control</span>(api_messages, cache_ttl=<span class="st">"5m"</span>, native_anthropic=<span class="kw">False</span>):
    messages = copy.deepcopy(api_messages)            <span class="cm"># 深拷贝，绝不改原列表</span>
    marker = _build_marker(cache_ttl)
    breakpoints_used = 0
    <span class="kw">if</span> messages[0].get(<span class="st">"role"</span>) == <span class="st">"system"</span>:
        _apply_cache_marker(messages[0], marker)      <span class="cm"># 断点 ①：system 前缀</span>
        breakpoints_used += 1
    remaining = 4 - breakpoints_used
    non_sys = [i <span class="kw">for</span> i <span class="kw">in</span> <span class="fn">range</span>(<span class="fn">len</span>(messages))
               <span class="kw">if</span> messages[i].get(<span class="st">"role"</span>) != <span class="st">"system"</span>]
    <span class="kw">for</span> idx <span class="kw">in</span> non_sys[-remaining:]:               <span class="cm"># 断点 ②③④：最后 3 条非 system</span>
        _apply_cache_marker(messages[idx], marker)
    <span class="kw">return</span> messages</pre>
</div>
<p>这段代码有两个细节值得留意。其一，第一行就 <span class="mono">copy.deepcopy</span> 整个消息列表——它<strong>绝不在原列表上打标记</strong>，断点只加在当轮要发出去的副本上，于是被缓存的那份“干净”消息序列始终不被污染。其二，4 个断点共用<strong>同一个 TTL</strong>（<span class="mono">5m</span> 或 <span class="mono">1h</span>）：短对话用 5 分钟够便宜，长会话可切到 1 小时让前缀“保温”更久。无论哪种，断点位置永远是“system + 最后 3 条”这一种布局。</p>
<p>把它画出来就一目了然——前缀（system）+ 尾部最近 3 条，正好 4 个 🔖：</p>
<div class="cellgroup">
  <div class="cg-cap"><b>system_and_3</b>：4 个 cache_control 断点落在哪</div>
  <div class="cells">
    <span class="cell hl">system 🔖</span>
    <span class="cell dim">msg-7</span>
    <span class="cell dim">msg-6</span>
    <span class="cell dim">msg-5</span>
    <span class="cell dim">msg-4</span>
    <span class="cell">msg-3 🔖</span>
    <span class="cell">msg-2 🔖</span>
    <span class="cell">msg-1 🔖</span>
  </div>
  <div class="cg-cap">前缀那个断点命中长长的 <b>stable+context+volatile</b>；末尾 3 个滚动跟住最新对话。中间灰色部分整段命中前缀缓存，<b>一分钱不重算</b>。</div>
</div>

<p>为什么是 <strong>~75%</strong> 而不是 100%？因为缓存命中并非<strong>免费</strong>，而是<strong>打折</strong>：命中的前缀按<strong>缓存读取价</strong>计费（通常只有原价的一小部分），没命中的新增尾部仍按全价算。一次多轮长对话里，绝大部分 token 都是<strong>反复重发的固定前缀</strong>——它们每轮都吃折扣价，于是整段对话的输入成本被压到约四分之一。这也解释了<strong>反过来的代价</strong>：你只要在会话中途动了前缀一个字节，本轮起前缀<strong>整体丢失缓存、按全价重算一遍</strong>，对话越往后这一下越贵。所以“别碰前缀”不是洁癖，是真金白银。</p>

<div class="figure">
<svg viewBox="0 0 680 300" role="img" aria-label="缓存命中与缓存击穿的成本对比">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--accent-ink)">✅ 前缀逐字节不变 → 缓存命中</text>
  <rect x="20"  y="38" width="430" height="48" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="235" y="67" text-anchor="middle" font-size="12.5" fill="var(--accent-ink)">system + 历史前缀（稳定）</text>
  <rect x="458" y="38" width="202" height="48" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="559" y="67" text-anchor="middle" font-size="12.5" fill="var(--blue)">最近 3 条新增</text>
  <text x="235" y="104" text-anchor="middle" font-size="11" fill="var(--muted)">按缓存读取价 ≈ 原价 1/10</text>
  <text x="559" y="104" text-anchor="middle" font-size="11" fill="var(--muted)">全价</text>
  <text x="668" y="64" text-anchor="end" font-size="11.5" font-weight="700" fill="var(--muted)">本轮成本 ↓</text>

  <text x="20" y="168" font-size="13.5" font-weight="700" fill="var(--red)">❌ 会话中途改了前缀一个字节 → 缓存击穿</text>
  <rect x="20"  y="180" width="165" height="48" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="102" y="209" text-anchor="middle" font-size="12.5" fill="var(--accent-ink)">命中</text>
  <text x="197" y="211" text-anchor="middle" font-size="18" font-weight="700" fill="var(--red)">✕</text>
  <rect x="210" y="180" width="450" height="48" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="435" y="209" text-anchor="middle" font-size="12.5" fill="var(--red)">从改动点起整体失效，按全价重算一遍</text>
  <text x="435" y="248" text-anchor="middle" font-size="11" fill="var(--muted)">对话越往后，这一下越贵</text>
  <text x="668" y="206" text-anchor="end" font-size="11.5" font-weight="700" fill="var(--red)">本轮成本 ↑↑</text>
</svg>
<div class="fig-cap"><b>缓存的两副面孔</b>：前缀逐字节不变时，长长的固定前缀按<b>缓存读取价</b>（约原价 1/10）计费，整段对话成本压到约四分之一；可一旦在会话中途动了前缀<b>一个字节</b>，从那点起的缓存<b>整体丢失、按全价重算</b>——这就是「每个会话的 prompt 缓存神圣不可侵犯」的代价根源。</div>
</div>

<p>不过，这 4 个断点也不能<strong>无脑</strong>打。<span class="mono">_apply_cache_marker</span> 会把 marker 加到目标消息的<strong>最后一个内容块</strong>上——万一那一块恰好是 <span class="mono">thinking</span> / <span class="mono">redacted_thinking</span>，marker 就会<strong>破坏签名验证</strong>。所以转成 Anthropic 格式时，<span class="mono">anthropic_adapter</span> 会把这些块上的 <span class="mono">cache_control</span> 再<strong>剥掉</strong>（注释直说 <span class="inline">cache markers interfere with signature validation</span>），并让带 marker 的 system prompt 保持为 <strong>content blocks</strong> 而非纯字符串：</p>

<div class="figure">
<svg viewBox="0 0 680 388" role="img" aria-label="Anthropic 缓存的 4 个 cache_control 断点放置与 thinking 签名安全">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">system_and_3 · 4 个 cache_control 断点 + thinking 签名安全</text>
  <text x="20" y="52" font-size="11.5" font-weight="700" fill="var(--muted)">① 在 deepcopy 副本上打 4 断点：system 前缀 + 末 3 条非 system 消息（同 TTL）</text>

  <rect x="24" y="72" width="150" height="58" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="99" y="103" text-anchor="middle" font-size="22">🔖</text>
  <text x="99" y="121" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--accent-ink)">system 前缀</text>
  <circle cx="99" cy="72" r="12" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>
  <text x="99" y="76" text-anchor="middle" font-size="12" font-weight="800" fill="var(--accent-ink)">1</text>

  <rect x="182" y="72" width="208" height="58" rx="10" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="286" y="99" text-anchor="middle" font-size="11" fill="var(--muted)">… 中间历史消息（无断点）…</text>
  <text x="286" y="118" text-anchor="middle" font-size="10" fill="var(--faint)">整段命中前缀缓存 · 不重算</text>

  <rect x="398" y="72" width="84" height="58" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="2"/>
  <text x="440" y="103" text-anchor="middle" font-size="22">🔖</text>
  <text x="440" y="121" text-anchor="middle" font-size="11" font-weight="700" fill="var(--blue)">msg-3</text>
  <circle cx="440" cy="72" r="12" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="440" y="76" text-anchor="middle" font-size="12" font-weight="800" fill="var(--blue)">2</text>

  <rect x="488" y="72" width="84" height="58" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="2"/>
  <text x="530" y="103" text-anchor="middle" font-size="22">🔖</text>
  <text x="530" y="121" text-anchor="middle" font-size="11" font-weight="700" fill="var(--blue)">msg-2</text>
  <circle cx="530" cy="72" r="12" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="530" y="76" text-anchor="middle" font-size="12" font-weight="800" fill="var(--blue)">3</text>

  <rect x="578" y="72" width="84" height="58" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="2"/>
  <text x="620" y="103" text-anchor="middle" font-size="22">🔖</text>
  <text x="620" y="121" text-anchor="middle" font-size="11" font-weight="700" fill="var(--blue)">msg-1</text>
  <circle cx="620" cy="72" r="12" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="620" y="76" text-anchor="middle" font-size="12" font-weight="800" fill="var(--blue)">4</text>

  <rect x="24" y="148" width="340" height="40" rx="10" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="40" y="173" font-size="11" fill="var(--accent-ink)">deepcopy 副本：marker 只打副本，原 api_messages 不动</text>
  <rect x="374" y="148" width="288" height="40" rx="10" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="390" y="173" font-size="11" fill="var(--blue)">4 断点同一 TTL：ephemeral，5m（默认）或 1h</text>

  <rect x="24" y="202" width="638" height="176" rx="12" fill="var(--red-soft)" stroke="var(--red)" stroke-width="1.5"/>
  <text x="42" y="230" font-size="24">⚠️</text>
  <text x="74" y="228" font-size="12.5" font-weight="700" fill="var(--red)">关键坑：thinking / redacted_thinking 块上的 cache_control 必须剥掉</text>

  <rect x="42" y="246" width="276" height="92" rx="9" fill="var(--panel)" stroke="var(--red)"/>
  <text x="58" y="268" font-size="10.5" font-weight="700" fill="var(--ink)">assistant 消息，末块 = thinking</text>
  <text x="58" y="292" font-size="10.5" fill="var(--muted)">若 marker 落到 thinking 块上</text>
  <text x="58" y="316" font-size="10.5" font-weight="700" fill="var(--red)">✗ 破坏 Anthropic 签名验证</text>

  <text x="358" y="292" text-anchor="middle" font-size="22">✂️</text>
  <text x="358" y="316" text-anchor="middle" font-size="10" fill="var(--muted)">注入后 pop</text>

  <rect x="398" y="246" width="252" height="92" rx="9" fill="var(--panel)" stroke="var(--accent)"/>
  <text x="414" y="268" font-size="10.5" font-weight="700" fill="var(--ink)">anthropic_adapter 转换时</text>
  <text x="414" y="292" font-size="10.5" fill="var(--accent-ink)">b.pop("cache_control", None)</text>
  <text x="414" y="316" font-size="10.5" font-weight="700" fill="var(--accent-ink)">✅ 仅留 signature，验证通过</text>

  <text x="42" y="362" font-size="10.5" fill="var(--muted)">附：带 marker 的 system prompt 保持为 content blocks（list）而非纯字符串，cache_control 才不丢。</text>
</svg>
<div class="fig-cap"><b>4 断点 + 签名安全</b>：<span class="mono">system_and_3</span> 在 system 前缀和末 3 条非 system 上打 4 个 <span class="mono">cache_control</span> 断点（同 TTL、打在 deepcopy 副本上）；但 marker 必须从 <span class="mono">thinking</span> / <span class="mono">redacted_thinking</span> 块上<b>剥掉</b>，否则破坏签名验证。</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 410" role="img" aria-label="一条真实 system prompt 的三层拼装、打缓存 marker 与第 2 轮 token 账">
  <text x="18" y="23" font-size="13" font-weight="700" fill="var(--accent-ink)">实例：一条真实 system prompt 三层拼装 → 打 marker → 第 2 轮 token 账</text>

  <rect x="18" y="36" width="332" height="92" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="30" y="55" font-size="10.5" font-weight="700" fill="var(--accent-ink)">① stable 层 · DEFAULT_AGENT_IDENTITY</text>
  <text x="30" y="76" font-size="9" font-family="monospace" fill="var(--ink)">You are Hermes Agent, an intelligent AI</text>
  <text x="30" y="89" font-size="9" font-family="monospace" fill="var(--ink)">assistant created by Nous Research. ...</text>
  <text x="30" y="113" font-size="9" fill="var(--muted)">prompt_builder.py:123</text>
  <text x="338" y="113" text-anchor="end" font-size="11" font-weight="700" fill="var(--purple)">≈ 6800 tok</text>

  <rect x="18" y="136" width="332" height="62" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="30" y="155" font-size="10.5" font-weight="700" fill="var(--blue)">② context 层 · context_parts</text>
  <text x="30" y="175" font-size="9" font-family="monospace" fill="var(--ink)">AGENTS.md 项目约定（注入前已扫描）</text>
  <text x="30" y="192" font-size="9" fill="var(--muted)">system_prompt.py · context</text>
  <text x="338" y="192" text-anchor="end" font-size="11" font-weight="700" fill="var(--purple)">≈ 1200 tok</text>

  <rect x="18" y="206" width="332" height="98" rx="8" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="30" y="225" font-size="10.5" font-weight="700" fill="var(--purple)">③ volatile 层 · timestamp（放最后）</text>
  <text x="30" y="245" font-size="9" font-family="monospace" fill="var(--ink)">Conversation started: Saturday, June 27, 2026</text>
  <text x="30" y="259" font-size="9" font-family="monospace" fill="var(--ink)">Model: claude-opus-4.7</text>
  <text x="30" y="273" font-size="9" font-family="monospace" fill="var(--ink)">Provider: anthropic</text>
  <text x="30" y="296" font-size="9" fill="var(--muted)">system_prompt.py:454-461</text>
  <text x="338" y="296" text-anchor="end" font-size="11" font-weight="700" fill="var(--purple)">≈ 900 tok</text>

  <path d="M352 56 L360 56 L360 286 L352 286" fill="none" stroke="var(--accent)" stroke-width="1.3"/>
  <path d="M360 171 L370 171" stroke="var(--accent)" stroke-width="1.5"/>
  <path d="M366 167 L374 171 L366 175 Z" fill="var(--accent)"/>

  <rect x="376" y="36" width="286" height="116" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="388" y="56" font-size="10.5" font-weight="700" fill="var(--ink)">④ 一次构建 → _cached_system_prompt</text>
  <text x="388" y="78" font-size="9" font-family="monospace" fill="var(--ink)">joined = &quot;\n\n&quot;.join(p for p in</text>
  <text x="388" y="91" font-size="9" font-family="monospace" fill="var(--ink)">  (stable, context, volatile) if p)</text>
  <text x="388" y="113" font-size="9" fill="var(--muted)">每会话只建一次（仅压缩时重建）</text>
  <text x="388" y="133" font-size="9" fill="var(--muted)">system_prompt.py:486</text>

  <rect x="376" y="160" width="286" height="144" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="388" y="180" font-size="10.5" font-weight="700" fill="var(--accent-ink)">⑤ 打 cache_control marker</text>
  <text x="388" y="202" font-size="9" font-family="monospace" fill="var(--ink)">marker = {&quot;type&quot;:&quot;ephemeral&quot;}</text>
  <rect x="388" y="212" width="262" height="20" rx="4" fill="var(--panel)" stroke="var(--accent)"/>
  <text x="396" y="226" font-size="9" font-weight="700" fill="var(--accent-ink)">5m 默认：无 ttl 键（易错点）</text>
  <text x="388" y="252" font-size="9" font-family="monospace" fill="var(--ink)">if ttl==&quot;1h&quot;: marker[&quot;ttl&quot;]=&quot;1h&quot;</text>
  <text x="388" y="276" font-size="9" fill="var(--muted)">prompt_caching.py:43-46</text>
  <text x="388" y="294" font-size="9" fill="var(--muted)">cache_ttl=&quot;5m&quot;（默认）</text>

  <path d="M519 304 L519 316" stroke="var(--accent)" stroke-width="1.5"/>
  <path d="M515 310 L519 318 L523 310 Z" fill="var(--accent)"/>
  <rect x="18" y="320" width="644" height="60" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="30" y="339" font-size="10.5" font-weight="700" fill="var(--ink)">⑥ 第 2 轮 token 账：6800 + 1200 + 900 = 8900 前缀 tok</text>
  <rect x="30" y="348" width="430" height="20" rx="4" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="245" y="362" text-anchor="middle" font-size="9" fill="var(--accent-ink)">前缀 ≈ 8900 tok · 按缓存读取价 (1/10)</text>
  <rect x="466" y="348" width="78" height="20" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="505" y="362" text-anchor="middle" font-size="9" fill="var(--blue)">尾 ≈150 · 全价</text>
  <text x="656" y="362" text-anchor="end" font-size="11" font-weight="700" fill="var(--red)">→ 输入成本 ↓ ~75%</text>

  <text x="18" y="400" font-size="9.5" fill="var(--muted)">读这张图：易变的 timestamp 压在 volatile 最末；5m 默认 marker 只有 {&quot;type&quot;:&quot;ephemeral&quot;}，没有 ttl 键才是默认。</text>
</svg>
<div class="fig-cap"><b>一条真实 system prompt 走一遍</b>：stable 层（<span class="mono">DEFAULT_AGENT_IDENTITY</span> 起头，≈6800 tok）→ context（AGENTS.md ≈1200 tok）→ volatile 层（<span class="mono">timestamp</span> 起头，≈900 tok）用 <span class="mono">&quot;\n\n&quot;.join</span> 拼成 <span class="mono">_cached_system_prompt</span>，每会话只建一次；打 marker 时 <b>5m 默认只有 <span class="mono">{&quot;type&quot;:&quot;ephemeral&quot;}</span></b>、唯独 1h 才加 <span class="mono">&quot;ttl&quot;:&quot;1h&quot;</span>；第 2 轮 8900 tok 前缀按缓存读取价计费，输入成本 <b>↓~75%</b>。</div>
</div>

<h2>守住前缀的最后一道闸：注入前扫描</h2>
<p>三层里的 <span class="mono">context</span> 会把 <strong>AGENTS.md / .cursorrules</strong> 等文件原样塞进 system prompt。问题是：这些文件可能来自 clone 来的仓库，里面可能藏着 <strong>prompt 注入</strong>。一旦进了 system prompt，它就成了<strong>会话期固定前缀的一部分</strong>，用户<strong>没有任何机会</strong>拦截。所以 Hermes 在注入<strong>之前</strong>先扫一遍：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/prompt_builder.py</span><span class="ln">46-62 · 简化</span></div>
  <pre><span class="kw">def</span> <span class="fn">_scan_context_content</span>(content: str, filename: str) -&gt; str:
    <span class="cm"># context 文件进 system prompt 之前，先过一遍注入检测</span>
    findings = _scan_for_threats(content, scope=<span class="st">"context"</span>)
    <span class="kw">if</span> findings:
        logger.warning(<span class="st">"Context file %s blocked: %s"</span>, filename, <span class="st">", "</span>.join(findings))
        <span class="kw">return</span> <span class="st">f"[BLOCKED: {filename} contained potential prompt injection (…). Content not loaded.]"</span>
    <span class="kw">return</span> content</pre>
</div>
<p>注释把理由讲得很清楚：<span class="inline">the file would otherwise enter the system prompt verbatim and the user has no chance to intervene</span>——“否则该文件会<strong>逐字</strong>进入 system prompt，而用户没有机会干预”。命中就替换成 <span class="mono">[BLOCKED: …]</span> 占位，把威胁挡在前缀<strong>之外</strong>。这正对应一条 LLM 固有约束：<span class="badge constraint">D·指令=数据</span>——模型分不清“指令”和“数据”，所以喂进 prompt 的外部文本必须<strong>先过安检</strong>。</p>

<p>这道闸还很<strong>克制</strong>：它用的是 <span class="mono">"context"</span> 这档扫描范围——覆盖经典注入、promptware / C2、角色扮演劫持，但<strong>不</strong>套用更激进的 strict 档规则（SSH 后门、持久化、外泄 URL）。原因写在注释里：context 文件常来自<strong>克隆的仓库</strong>（安全研究、基建文档），用 strict 档会把正常内容误杀。安检既要挡住注入，又不能把每一份项目文档都拒之门外——这条边界本身就是一处设计权衡。</p>

<h2>一次会话里，读和写各走哪条路</h2>
<p>守住缓存的关键纪律只有一条：<strong>读只在会话开始进前缀，写只往末尾追加，会话内绝不重建</strong>。把它画成一条线：</p>
<div class="flow">
  <div class="node hl"><div class="nt">会话开始</div><div class="nd">三层组装成固定前缀</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">每轮</div><div class="nd">apply…cache_control 打 4 断点</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">命中缓存</div><div class="nd">前缀复用，省 ~75%</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">写 = 末尾 append</div><div class="nd">nudge / 技能 / 记忆，不重建</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node hl"><div class="nt">唯一例外</div><div class="nd">上下文压缩 → 重建</div></div>
</div>

<p>那<strong>唯一的例外</strong>——上下文压缩——又是怎么回事？当对话长到逼近模型上下文窗口，Hermes 会把早期历史<strong>摘要压缩</strong>成更短的一段再拼回去。这一步<strong>必然</strong>改写了前缀，缓存<strong>注定作废</strong>，所以它被设计成<strong>万不得已</strong>才触发：用一次“缓存重置”的代价，换回继续对话的空间。除此之外，自动对话回合里<strong>没有任何理由</strong>在会话中途重建 system prompt（细节见第 15 章）。<em>（严格说，用户<strong>主动</strong>切换模型 / 人格、手动改写 system prompt 这类配置操作也会触发一次重建，但那是显式发起的<strong>非常规事件</strong>，不在自动回合循环之内——正常对话回合里，压缩仍是唯一的重建。）</em></p>

<p>那会话中途<strong>非改不可</strong>怎么办——比如用户当场装了个新技能、调了工具集？Hermes 的答案是<strong>“延迟生效”</strong>：改动默认<strong>下个会话</strong>才进前缀，本轮缓存毫发无伤；只有显式加 <span class="mono">--now</span>（见 <span class="mono">/skills install --now</span>）才立刻作废重建。这条“缓存感知”准则把第 9 章的技能、工具命令全收编进同一套纪律——能不破缓存就绝不破。而压缩重建那一下，<span class="mono">invalidate_system_prompt</span> 会顺手把磁盘上的记忆<strong>重新读一遍</strong>，于是本会话新写的记忆、技能<strong>正好</strong>趁这次注定的缓存重置一起折进前缀，一分额外代价都不花（第 11、15 章）。</p>

<p>三层各自对应一段“跨章节配合”——它们都为<strong>同一条缓存纪律</strong>让路：</p>
<table class="t">
  <tr><th>层</th><th>装什么</th><th>会话内会变吗</th><th>谁来维护（跨章）</th></tr>
  <tr><td class="mono">stable</td><td>身份 / 工具 / 技能清单 / 环境</td><td>否</td><td>技能进 stable（第 9 章）</td></tr>
  <tr><td class="mono">context</td><td>system_message + 项目文件</td><td>否</td><td>注入前扫描（本章）</td></tr>
  <tr><td class="mono">volatile</td><td>记忆 / USER.md / 时间戳</td><td>会（但只在末尾）</td><td>memory / USER.md（第 11 章）</td></tr>
</table>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 全局如何合力守住缓存</div>
  <div class="collab-sub">① 组件清单（★本章核心，其余跨章节配合）</div>
  本章三块：<strong>build_system_prompt_parts()</strong>（<span class="mono">system_prompt.py:113</span>）组三层、
  <strong>apply_anthropic_cache_control()</strong>（<span class="mono">prompt_caching.py:49</span>）打 4 断点、
  <strong>_scan_context_content()</strong>（<span class="mono">prompt_builder.py:46</span>）注入前扫描。其余部件全都为同一条缓存纪律让路：
  <strong>技能清单</strong>→stable（第 9 章）、<strong>memory / USER.md</strong>→volatile（第 11 章）、
  <strong>学习 nudge</strong>→末尾 append（第 9 章）、<strong>搜索结果</strong>→tool 消息（第 12 章）、
  <strong>上下文压缩</strong>→唯一允许的重建（第 15 章）、<strong>辅助模型</strong>→独立 session、不污染主缓存（第 10 章）。
  <div class="collab-sub">② 数据流时序</div>
  会话开始：三层组装成<strong>固定前缀</strong> → 每轮 <span class="mono">apply_anthropic_cache_control</span> 打 4 断点、命中缓存；
  <strong>读</strong>（技能 / 记忆 / 搜索）只在会话开始进前缀，<strong>或</strong>在末尾以 tool / user 消息 append；
  <strong>写</strong>（nudge / 新技能 / 新记忆）只 append 末尾、<strong>当前会话不重建</strong>，下个会话才进前缀；
  <strong>唯一例外</strong>＝压缩，它重写历史、必然作废缓存，所以只在不得已时触发（第 15 章）。
  <div class="collab-sub">③ 关键点</div>
  三层<strong>按稳定度排序</strong>（stable→context→volatile），把最易变的 memory <strong>压到最后</strong>——
  即便它变了，也只动到整串的尾巴，<strong>前面已缓存的 stable / context 前缀毫发无伤</strong>。这就是“易变内容压后、不殃及前缀”的全部用意。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  一条主线压倒一切：<strong>★ prompt 缓存神圣不可侵犯</strong>。system prompt <strong>每会话只建一次</strong>，
  <strong>唯一</strong>允许重建的时机是上下文压缩（第 15 章）。由此推出三条<strong>反模式</strong>，会话中途<strong>绝不</strong>做：
  ① 换 toolset（工具 schema 也是前缀的一部分，一换全废）；② reload memory / 重读 USER.md（会改写 volatile 前缀）；
  ③ rebuild system prompt（哪怕只动一个字节，整段前缀缓存作废，成本翻几倍）。
  <p style="margin:.5rem 0 0">它同时治两条 LLM 固有约束：<span class="badge constraint">A·中间遗失</span>——三层把最关键的身份 / 指令钉在<strong>最前</strong>、稳定不动；
  <span class="badge constraint">D·指令=数据</span>——context 在注入<strong>前</strong>先扫描，别让外部文件冒充指令混进前缀。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>三层结构</strong>：<span class="mono">stable → context → volatile</span> 按稳定度排序，<span class="mono">build_system_prompt_parts()</span> 组三层、<span class="mono">build_system_prompt()</span> 用 <span class="mono">\n\n</span> 拼接。</li>
    <li><strong>会话内逐字节不变</strong>：每会话<strong>只建一次</strong>，缓存在 <span class="mono">_cached_system_prompt</span>；<strong>唯一</strong>重建时机＝上下文压缩（第 15 章）。</li>
    <li><strong>system_and_3</strong>：<span class="mono">apply_anthropic_cache_control</span> 在 system + 最后 3 条非 system 上打 <strong>4 个</strong> cache_control 断点，省 <strong>~75%</strong>。</li>
    <li><strong>memory 放最后</strong>：最易变的内容压到 volatile，变了也<strong>不殃及</strong>前面已缓存的 stable / context 前缀。</li>
    <li><strong>注入前扫描</strong>：context 文件进 system prompt <strong>之前</strong>过 <span class="mono">_scan_context_content</span>，命中替换为 <span class="mono">[BLOCKED:…]</span>，守住前缀（约束 D）。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">
This is the book's <strong>core chapter</strong>. Almost every Hermes design ultimately answers one question: <strong>does it break the prompt cache?</strong> This chapter nails three things — how the system prompt is assembled in <strong>three tiers</strong>, why it stays <strong>byte-for-byte stable</strong> within a session, and how Anthropic's cache breakpoints cut multi-turn input cost by <strong>~75%</strong>. One sentence is enough to remember: <strong>the system prompt is built once per session; the only exception is context compression</strong>.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy</div>
  Think of the system prompt as a building's <strong>foundation and load-bearing walls</strong>: poured <strong>once</strong> at the start, relied on by the whole structure, and <strong>never knocked down and re-poured halfway through</strong> — that would collapse the building. Now view caching from another angle: it's like a <strong>prepaid “prefix pass”</strong> — the first turn pays <strong>full price</strong> to compute that long prefix and stores it in the upstream cache; every later turn, as long as the prefix hasn't changed by <strong>a single byte</strong>, only pays the balance (the few new lines), saving exactly the cost of recomputing the prefix. The moment you change the prefix mid-session (swap tools, reload memory, rebuild the prompt), the pass is void and every turn pays full price again.
</div>

<h2>Macro: three tiers ordered by stability</h2>

<div class="card macro">
  <div class="tag">🌍 The big picture</div>
  The system prompt isn't a randomly concatenated blob — it's <strong>three tiers ordered by stability</strong>: <span class="mono">stable</span> (identity / tools / skills / environment, nearly constant), <span class="mono">context</span> (caller message + project context files, fixed for the session), and <span class="mono">volatile</span> (memory snapshot / user profile / timestamp, the most likely to change). The three are joined with <span class="mono">\n\n</span> into one string, <strong>built once at session start</strong>, cached on <span class="mono">agent._cached_system_prompt</span>, and reused verbatim every turn. Pushing the <strong>most volatile content to the very end</strong> means that even when it changes, only the <strong>tail</strong> of the string moves — <strong>the already-cached prefix is untouched</strong>.
</div>

<p>Why does this discipline deserve the <strong>whole book</strong> bending to it? Because it directly sets the <strong>cost order of magnitude</strong>. A personal agent's conversations tend to be <strong>long</strong> — dozens to hundreds of turns, with that long prefix resent again and again. On a cache hit, a long conversation's marginal cost is almost just “the few new lines”; once the cache breaks, every turn pays full price from scratch. Chapter 1's iron rule — “the prompt cache is sacred” — finally lands here on <strong>concrete code and numbers</strong>.</p>

<p>Why is this discipline so <strong>counter-intuitive</strong>? Because every turn dangles the temptation to “freshen the context” — drop in a newer timestamp, read back the memory you just wrote, swap toolsets for the task at hand. Hermes does the <strong>opposite</strong>: the memory snapshot in <span class="mono">volatile</span> is taken at the <strong>moment the session starts</strong>, and the whole conversation carries that slightly-stale context unchanged — trading a bit of freshness to <strong>freeze the prefix solid</strong>. That's the <strong>cache-vs-freshness</strong> trade-off: across a long session the saved cost dwarfs “memory updating a few turns late,” and when a refresh is truly needed, compression is the single catch-all (ch.15) that folds this session's writes into the prefix all at once.</p>

<h2>The three tiers: more stable goes first</h2>
<p>The assembly entry is <span class="mono">build_system_prompt_parts()</span> (<span class="mono">system_prompt.py:113</span>), which returns a three-key dict <span class="mono">{stable, context, volatile}</span>. The order is anything but arbitrary — <strong>the more stable goes first, the more volatile goes last</strong>:</p>

<div class="layers">
  <div class="layer l-core"><div class="lh"><span class="badge">stable · most stable</span><span class="name">identity / tools / skills / env</span></div>
    <div class="ld">SOUL.md or DEFAULT_AGENT_IDENTITY, tool & computer-use guidance, the <strong>skills prompt</strong> (ch.9), per-model operational guidance, environment & platform hints. Essentially <strong>constant</strong> for the whole session.</div></div>
  <div class="layer l-main"><div class="lh"><span class="badge">context · fixed in-session</span><span class="name">system_message + context files</span></div>
    <div class="ld">The caller-supplied <span class="mono">system_message</span>, plus project files like <strong>AGENTS.md / .cursorrules</strong> discovered under <span class="mono">TERMINAL_CWD</span>. <strong>Unchanged</strong> during the session.</div></div>
  <div class="layer l-app"><div class="lh"><span class="badge">volatile · most volatile</span><span class="name">memory / USER.md / timestamp</span></div>
    <div class="ld">Memory snapshot, <strong>USER.md profile</strong> (ch.11), external memory-provider block, timestamp / session / model / provider line. Most likely to change, so <strong>pushed to the very end</strong>.</div></div>
</div>

<p>Why insist on <strong>three tiers</strong> rather than mashing everything into one block? Because the cache is a <strong>prefix</strong> cache — it compares byte by byte from the start, and at the first differing byte <strong>everything from there on is invalidated</strong>. If a volatile timestamp or memory sat at the very front, every turn would change it and void the whole prefix. The essence of tiering is to <strong>physically separate</strong> the three kinds of content — “nearly never changes,” “fixed within the session,” and “may change each turn” — so that volatility only ever lands at the <strong>tail</strong> of the string.</p>

<p>This “build once, reuse all session” discipline is pinned word-for-word in <span class="mono">system_prompt.py</span>'s module docstring:</p>
<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/system_prompt.py</span><span class="ln">3-19 · excerpt</span></div>
  <pre><span class="cm">The agent's system prompt is built once per session and reused across all</span>
<span class="cm">turns — only context compression triggers a rebuild.  This keeps the</span>
<span class="cm">upstream prefix cache warm.</span>

<span class="cm">Three tiers are joined with `\n\n`:</span>
  * stable   — identity (SOUL.md or DEFAULT_AGENT_IDENTITY), tool guidance,
               computer-use guidance, nous subscription block, tool-use
               enforcement guidance + per-model operational guidance,
               skills prompt, alibaba model-name workaround,
               environment hints, platform hints.
  * context  — caller-supplied system_message plus context files
               (AGENTS.md / .cursorrules / etc.) discovered under TERMINAL_CWD.
  * volatile — memory snapshot, USER.md profile, external memory
               provider block, timestamp/session/model/provider line.</pre>
</div>
<p>Fix your eyes on <span class="inline">built once per session … only context compression triggers a rebuild</span>. This is the most important invariant of the chapter — and of the whole book. <span class="mono">build_system_prompt_parts()</span>'s own docstring spells out the consequence even more bluntly: <span class="inline">Hermes never re-renders parts of this string mid-session — that's the only way to keep upstream prompt caches warm across turns</span>.</p>

<p>This byte-stability has to survive <strong>across processes</strong> too: every turn persists the assembled system prompt into <span class="mono">session_db</span>, and the next time the session <strong>resumes</strong> it's pulled out and <strong>reused verbatim</strong> (the comment is blunt: <span class="inline">reuse the exact system prompt … so the Anthropic cache prefix matches</span>) — not even a restart is allowed to alter the prefix. Only one gate remains: if the runtime identity (<strong>model / provider</strong>) no longer matches the stored copy, <span class="mono">_stored_prompt_matches_runtime</span> flags it stale and rebuilds — since you <strong>changed models</strong>, the upstream's old prefix wouldn't hit anyway, so rebuilding actually saves money. “Stable” isn't an abstract slogan; it means the real bytes match <strong>exactly</strong> across many turns and many process restarts.</p>

<h2>The caching strategy: system_and_3 places 4 breakpoints</h2>
<p>With a byte-stable prefix in hand, all that's left is to tell the upstream “where reuse may begin.” Hermes uses just <strong>one</strong> layout — <span class="mono">system_and_3</span>: one <span class="mono">cache_control</span> breakpoint on the <strong>system prompt</strong> and one on each of the <strong>last 3 non-system messages</strong>, <strong>4 in total</strong>, all at the same TTL (5 minutes or 1 hour). It cuts multi-turn input token cost by <strong>~75%</strong>:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/prompt_caching.py</span><span class="ln">1-79 · simplified</span></div>
  <pre><span class="cm">Single layout: system_and_3. 4 cache_control breakpoints — system</span>
<span class="cm">prompt + last 3 non-system messages, all at the same TTL (5m or 1h).</span>
<span class="cm">Reduces input token costs by ~75% on multi-turn conversations ...</span>

<span class="kw">def</span> <span class="fn">apply_anthropic_cache_control</span>(api_messages, cache_ttl=<span class="st">"5m"</span>, native_anthropic=<span class="kw">False</span>):
    messages = copy.deepcopy(api_messages)            <span class="cm"># deep copy; never mutate the original</span>
    marker = _build_marker(cache_ttl)
    breakpoints_used = 0
    <span class="kw">if</span> messages[0].get(<span class="st">"role"</span>) == <span class="st">"system"</span>:
        _apply_cache_marker(messages[0], marker)      <span class="cm"># breakpoint ①: the system prefix</span>
        breakpoints_used += 1
    remaining = 4 - breakpoints_used
    non_sys = [i <span class="kw">for</span> i <span class="kw">in</span> <span class="fn">range</span>(<span class="fn">len</span>(messages))
               <span class="kw">if</span> messages[i].get(<span class="st">"role"</span>) != <span class="st">"system"</span>]
    <span class="kw">for</span> idx <span class="kw">in</span> non_sys[-remaining:]:               <span class="cm"># breakpoints ②③④: last 3 non-system</span>
        _apply_cache_marker(messages[idx], marker)
    <span class="kw">return</span> messages</pre>
</div>
<p>Two details here are worth noting. First, the very first line does <span class="mono">copy.deepcopy</span> on the whole message list — it <strong>never marks the original</strong>; breakpoints are added only to the copy sent this turn, so the cached “clean” message sequence is never polluted. Second, all 4 breakpoints share <strong>one TTL</strong> (<span class="mono">5m</span> or <span class="mono">1h</span>): a short chat is cheap at 5 minutes, a long session can switch to 1 hour to keep the prefix “warm” longer. Either way the placement is always the one layout: “system + last 3.”</p>
<p>Draw it out and it's obvious — the prefix (system) plus the 3 most recent tail messages, exactly 4 🔖:</p>
<div class="cellgroup">
  <div class="cg-cap"><b>system_and_3</b>: where the 4 cache_control breakpoints land</div>
  <div class="cells">
    <span class="cell hl">system 🔖</span>
    <span class="cell dim">msg-7</span>
    <span class="cell dim">msg-6</span>
    <span class="cell dim">msg-5</span>
    <span class="cell dim">msg-4</span>
    <span class="cell">msg-3 🔖</span>
    <span class="cell">msg-2 🔖</span>
    <span class="cell">msg-1 🔖</span>
  </div>
  <div class="cg-cap">The prefix breakpoint hits the long <b>stable+context+volatile</b> block; the trailing 3 roll forward with the newest turns. The whole grey middle hits the prefix cache — <b>recomputed for free</b>.</div>
</div>

<p>Why <strong>~75%</strong> and not 100%? Because a cache hit isn't <strong>free</strong> — it's a <strong>discount</strong>: the hit prefix bills at the <strong>cache-read price</strong> (usually a small fraction of full price), while the new tail still bills at full price. In a long multi-turn conversation the vast majority of tokens are the <strong>same fixed prefix resent every turn</strong> — each turn they pay the discounted price, so the conversation's input cost collapses to roughly a quarter. This also explains the <strong>reverse cost</strong>: change a single byte of the prefix mid-session and, from that turn on, the <strong>whole prefix loses the cache and is recomputed at full price</strong> — the deeper the conversation, the more that one slip hurts. “Don't touch the prefix” isn't fussiness; it's real money.</p>

<div class="figure">
<svg viewBox="0 0 680 300" role="img" aria-label="Cost comparison of cache hit versus cache miss">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--accent-ink)">✅ Prefix byte-identical → cache hit</text>
  <rect x="20"  y="38" width="430" height="48" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="235" y="67" text-anchor="middle" font-size="12.5" fill="var(--accent-ink)">system + history prefix (stable)</text>
  <rect x="458" y="38" width="202" height="48" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="559" y="67" text-anchor="middle" font-size="12.5" fill="var(--blue)">last 3 new</text>
  <text x="235" y="104" text-anchor="middle" font-size="11" fill="var(--muted)">billed at cache-read ≈ 1/10 of full</text>
  <text x="559" y="104" text-anchor="middle" font-size="11" fill="var(--muted)">full price</text>
  <text x="668" y="64" text-anchor="end" font-size="11.5" font-weight="700" fill="var(--muted)">turn cost ↓</text>

  <text x="20" y="168" font-size="13.5" font-weight="700" fill="var(--red)">❌ One byte of the prefix changed mid-session → cache miss</text>
  <rect x="20"  y="180" width="165" height="48" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="102" y="209" text-anchor="middle" font-size="12.5" fill="var(--accent-ink)">hit</text>
  <text x="197" y="211" text-anchor="middle" font-size="18" font-weight="700" fill="var(--red)">✕</text>
  <rect x="210" y="180" width="450" height="48" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="435" y="209" text-anchor="middle" font-size="12.5" fill="var(--red)">everything from the edit point is recomputed at full price</text>
  <text x="435" y="248" text-anchor="middle" font-size="11" fill="var(--muted)">the deeper the conversation, the costlier this slip</text>
  <text x="668" y="206" text-anchor="end" font-size="11.5" font-weight="700" fill="var(--red)">turn cost ↑↑</text>
</svg>
<div class="fig-cap"><b>The two faces of caching</b>: when the prefix is byte-identical, the long fixed prefix bills at the <b>cache-read price</b> (~1/10 of full), collapsing the whole conversation to roughly a quarter of the cost; but change <b>a single byte</b> mid-session and the cache from that point is <b>lost and recomputed at full price</b> — the root reason why "per-conversation prompt caching is sacred."</div>
</div>

<p>But these 4 breakpoints can't be applied <strong>blindly</strong>. <span class="mono">_apply_cache_marker</span> attaches the marker to the target message's <strong>last content block</strong> — and if that block happens to be a <span class="mono">thinking</span> / <span class="mono">redacted_thinking</span> block, the marker <strong>breaks signature validation</strong>. So when converting to Anthropic format, <span class="mono">anthropic_adapter</span> <strong>strips</strong> <span class="mono">cache_control</span> back off those blocks (the comment is blunt: <span class="inline">cache markers interfere with signature validation</span>) and keeps a marker-bearing system prompt as <strong>content blocks</strong> rather than a plain string:</p>

<div class="figure">
<svg viewBox="0 0 680 388" role="img" aria-label="Placement of Anthropic's 4 cache_control breakpoints and thinking-signature safety">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">system_and_3 · 4 cache_control breakpoints + thinking-signature safety</text>
  <text x="20" y="52" font-size="11.5" font-weight="700" fill="var(--muted)">① 4 breakpoints on the deepcopy: system prefix + last 3 non-system messages (same TTL)</text>

  <rect x="24" y="72" width="150" height="58" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="99" y="103" text-anchor="middle" font-size="22">🔖</text>
  <text x="99" y="121" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--accent-ink)">system prefix</text>
  <circle cx="99" cy="72" r="12" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>
  <text x="99" y="76" text-anchor="middle" font-size="12" font-weight="800" fill="var(--accent-ink)">1</text>

  <rect x="182" y="72" width="208" height="58" rx="10" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="286" y="99" text-anchor="middle" font-size="11" fill="var(--muted)">… middle history (no breakpoint) …</text>
  <text x="286" y="118" text-anchor="middle" font-size="10" fill="var(--faint)">whole block hits the prefix cache · not recomputed</text>

  <rect x="398" y="72" width="84" height="58" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="2"/>
  <text x="440" y="103" text-anchor="middle" font-size="22">🔖</text>
  <text x="440" y="121" text-anchor="middle" font-size="11" font-weight="700" fill="var(--blue)">msg-3</text>
  <circle cx="440" cy="72" r="12" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="440" y="76" text-anchor="middle" font-size="12" font-weight="800" fill="var(--blue)">2</text>

  <rect x="488" y="72" width="84" height="58" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="2"/>
  <text x="530" y="103" text-anchor="middle" font-size="22">🔖</text>
  <text x="530" y="121" text-anchor="middle" font-size="11" font-weight="700" fill="var(--blue)">msg-2</text>
  <circle cx="530" cy="72" r="12" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="530" y="76" text-anchor="middle" font-size="12" font-weight="800" fill="var(--blue)">3</text>

  <rect x="578" y="72" width="84" height="58" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="2"/>
  <text x="620" y="103" text-anchor="middle" font-size="22">🔖</text>
  <text x="620" y="121" text-anchor="middle" font-size="11" font-weight="700" fill="var(--blue)">msg-1</text>
  <circle cx="620" cy="72" r="12" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
  <text x="620" y="76" text-anchor="middle" font-size="12" font-weight="800" fill="var(--blue)">4</text>

  <rect x="24" y="148" width="340" height="40" rx="10" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="40" y="173" font-size="11" fill="var(--accent-ink)">deepcopy: marker only on the copy; original api_messages untouched</text>
  <rect x="374" y="148" width="288" height="40" rx="10" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="390" y="173" font-size="11" fill="var(--blue)">all 4 share one TTL: ephemeral, 5m (default) or 1h</text>

  <rect x="24" y="202" width="638" height="176" rx="12" fill="var(--red-soft)" stroke="var(--red)" stroke-width="1.5"/>
  <text x="42" y="230" font-size="24">⚠️</text>
  <text x="74" y="228" font-size="12.5" font-weight="700" fill="var(--red)">Key trap: strip cache_control off thinking / redacted_thinking blocks</text>

  <rect x="42" y="246" width="276" height="92" rx="9" fill="var(--panel)" stroke="var(--red)"/>
  <text x="58" y="268" font-size="10.5" font-weight="700" fill="var(--ink)">assistant message, last block = thinking</text>
  <text x="58" y="292" font-size="10.5" fill="var(--muted)">if the marker lands on the thinking block</text>
  <text x="58" y="316" font-size="10.5" font-weight="700" fill="var(--red)">✗ breaks Anthropic signature validation</text>

  <text x="358" y="292" text-anchor="middle" font-size="22">✂️</text>
  <text x="358" y="316" text-anchor="middle" font-size="10" fill="var(--muted)">pop after inject</text>

  <rect x="398" y="246" width="252" height="92" rx="9" fill="var(--panel)" stroke="var(--accent)"/>
  <text x="414" y="268" font-size="10.5" font-weight="700" fill="var(--ink)">anthropic_adapter, on conversion</text>
  <text x="414" y="292" font-size="10.5" fill="var(--accent-ink)">b.pop("cache_control", None)</text>
  <text x="414" y="316" font-size="10.5" font-weight="700" fill="var(--accent-ink)">✅ only signature remains — validates</text>

  <text x="42" y="362" font-size="10.5" fill="var(--muted)">Also: a marker-bearing system prompt stays as content blocks (a list), not a plain string, so cache_control survives.</text>
</svg>
<div class="fig-cap"><b>4 breakpoints + signature safety</b>: <span class="mono">system_and_3</span> places 4 <span class="mono">cache_control</span> breakpoints on the system prefix and the last 3 non-system messages (same TTL, on a deepcopy); but the marker must be <b>stripped</b> from <span class="mono">thinking</span> / <span class="mono">redacted_thinking</span> blocks, or it breaks signature validation.</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 410" role="img" aria-label="One real system prompt: three-tier assembly, cache marker, and the second-turn token bill">
  <text x="18" y="23" font-size="13" font-weight="700" fill="var(--accent-ink)">Example: one real system prompt - 3 tiers join, marker, 2nd-turn token bill</text>

  <rect x="18" y="36" width="332" height="92" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="30" y="55" font-size="10.5" font-weight="700" fill="var(--accent-ink)">(1) stable tier - DEFAULT_AGENT_IDENTITY</text>
  <text x="30" y="76" font-size="9" font-family="monospace" fill="var(--ink)">You are Hermes Agent, an intelligent AI</text>
  <text x="30" y="89" font-size="9" font-family="monospace" fill="var(--ink)">assistant created by Nous Research. ...</text>
  <text x="30" y="113" font-size="9" fill="var(--muted)">prompt_builder.py:123</text>
  <text x="338" y="113" text-anchor="end" font-size="11" font-weight="700" fill="var(--purple)">~ 6800 tok</text>

  <rect x="18" y="136" width="332" height="62" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="30" y="155" font-size="10.5" font-weight="700" fill="var(--blue)">(2) context tier - context_parts</text>
  <text x="30" y="175" font-size="9" font-family="monospace" fill="var(--ink)">AGENTS.md project rules (scanned first)</text>
  <text x="30" y="192" font-size="9" fill="var(--muted)">system_prompt.py - context</text>
  <text x="338" y="192" text-anchor="end" font-size="11" font-weight="700" fill="var(--purple)">~ 1200 tok</text>

  <rect x="18" y="206" width="332" height="98" rx="8" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="30" y="225" font-size="10.5" font-weight="700" fill="var(--purple)">(3) volatile tier - timestamp (last)</text>
  <text x="30" y="245" font-size="9" font-family="monospace" fill="var(--ink)">Conversation started: Saturday, June 27, 2026</text>
  <text x="30" y="259" font-size="9" font-family="monospace" fill="var(--ink)">Model: claude-opus-4.7</text>
  <text x="30" y="273" font-size="9" font-family="monospace" fill="var(--ink)">Provider: anthropic</text>
  <text x="30" y="296" font-size="9" fill="var(--muted)">system_prompt.py:454-461</text>
  <text x="338" y="296" text-anchor="end" font-size="11" font-weight="700" fill="var(--purple)">~ 900 tok</text>

  <path d="M352 56 L360 56 L360 286 L352 286" fill="none" stroke="var(--accent)" stroke-width="1.3"/>
  <path d="M360 171 L370 171" stroke="var(--accent)" stroke-width="1.5"/>
  <path d="M366 167 L374 171 L366 175 Z" fill="var(--accent)"/>

  <rect x="376" y="36" width="286" height="116" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="388" y="56" font-size="10.5" font-weight="700" fill="var(--ink)">(4) built once - _cached_system_prompt</text>
  <text x="388" y="78" font-size="9" font-family="monospace" fill="var(--ink)">joined = &quot;\n\n&quot;.join(p for p in</text>
  <text x="388" y="91" font-size="9" font-family="monospace" fill="var(--ink)">  (stable, context, volatile) if p)</text>
  <text x="388" y="113" font-size="9" fill="var(--muted)">built once per session (rebuilt only on compression)</text>
  <text x="388" y="133" font-size="9" fill="var(--muted)">system_prompt.py:486</text>

  <rect x="376" y="160" width="286" height="144" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="388" y="180" font-size="10.5" font-weight="700" fill="var(--accent-ink)">(5) apply cache_control marker</text>
  <text x="388" y="202" font-size="9" font-family="monospace" fill="var(--ink)">marker = {&quot;type&quot;:&quot;ephemeral&quot;}</text>
  <rect x="388" y="212" width="262" height="20" rx="4" fill="var(--panel)" stroke="var(--accent)"/>
  <text x="396" y="226" font-size="9" font-weight="700" fill="var(--accent-ink)">5m default: no ttl key (easy to miss)</text>
  <text x="388" y="252" font-size="9" font-family="monospace" fill="var(--ink)">if ttl==&quot;1h&quot;: marker[&quot;ttl&quot;]=&quot;1h&quot;</text>
  <text x="388" y="276" font-size="9" fill="var(--muted)">prompt_caching.py:43-46</text>
  <text x="388" y="294" font-size="9" fill="var(--muted)">cache_ttl=&quot;5m&quot; (default)</text>

  <path d="M519 304 L519 316" stroke="var(--accent)" stroke-width="1.5"/>
  <path d="M515 310 L519 318 L523 310 Z" fill="var(--accent)"/>
  <rect x="18" y="320" width="644" height="60" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="30" y="339" font-size="10.5" font-weight="700" fill="var(--ink)">(6) 2nd-turn token bill: 6800 + 1200 + 900 = 8900 prefix tok</text>
  <rect x="30" y="348" width="430" height="20" rx="4" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="245" y="362" text-anchor="middle" font-size="9" fill="var(--accent-ink)">prefix ~ 8900 tok - cache-read price (1/10)</text>
  <rect x="466" y="348" width="78" height="20" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="505" y="362" text-anchor="middle" font-size="9" fill="var(--blue)">tail ~150 - full</text>
  <text x="656" y="362" text-anchor="end" font-size="11" font-weight="700" fill="var(--red)">input cost ↓ ~75%</text>

  <text x="18" y="400" font-size="9.5" fill="var(--muted)">Read this: the volatile timestamp sits last; the 5m default marker is just {&quot;type&quot;:&quot;ephemeral&quot;} - no ttl key.</text>
</svg>
<div class="fig-cap"><b>One real system prompt, end to end</b>: stable tier (led by <span class="mono">DEFAULT_AGENT_IDENTITY</span>, ~6800 tok) + context (AGENTS.md ~1200 tok) + volatile tier (led by <span class="mono">timestamp</span>, ~900 tok) are joined by <span class="mono">&quot;\n\n&quot;.join</span> into <span class="mono">_cached_system_prompt</span>, built once per session; the <b>5m default marker is only <span class="mono">{&quot;type&quot;:&quot;ephemeral&quot;}</span></b>, and only 1h adds <span class="mono">&quot;ttl&quot;:&quot;1h&quot;</span>; on turn 2 the 8900-tok prefix bills at cache-read price, cutting input cost <b>~75%</b>.</div>
</div>

<h2>The last gate guarding the prefix: scan before injection</h2>
<p>The <span class="mono">context</span> tier drops files like <strong>AGENTS.md / .cursorrules</strong> verbatim into the system prompt. The catch: these files may come from a cloned repo and may hide a <strong>prompt injection</strong>. Once it enters the system prompt it becomes <strong>part of the session's fixed prefix</strong>, and the user has <strong>no chance whatsoever</strong> to intercept. So Hermes scans <strong>before</strong> injecting:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/prompt_builder.py</span><span class="ln">46-62 · simplified</span></div>
  <pre><span class="kw">def</span> <span class="fn">_scan_context_content</span>(content: str, filename: str) -&gt; str:
    <span class="cm"># scan for injection BEFORE the context file enters the system prompt</span>
    findings = _scan_for_threats(content, scope=<span class="st">"context"</span>)
    <span class="kw">if</span> findings:
        logger.warning(<span class="st">"Context file %s blocked: %s"</span>, filename, <span class="st">", "</span>.join(findings))
        <span class="kw">return</span> <span class="st">f"[BLOCKED: {filename} contained potential prompt injection (…). Content not loaded.]"</span>
    <span class="kw">return</span> content</pre>
</div>
<p>The comment states the reason plainly: <span class="inline">the file would otherwise enter the system prompt verbatim and the user has no chance to intervene</span>. On a hit it's swapped for a <span class="mono">[BLOCKED: …]</span> placeholder, keeping the threat <strong>out of</strong> the prefix. This maps straight onto an inherent LLM constraint: <span class="badge constraint">D·instr=data</span> — the model can't tell “instructions” from “data,” so external text fed into the prompt must <strong>clear security first</strong>.</p>

<p>The gate is also <strong>restrained</strong>: it uses the <span class="mono">"context"</span> scope — covering classic injection, promptware / C2, and role-play hijack, but <strong>not</strong> the more aggressive strict-scope rules (SSH backdoor, persistence, exfil URL). The reason is in the comment: context files often come from a <strong>cloned repo</strong> (security research, infra docs), where strict scope would kill normal content. The scan must block injection without rejecting every project doc — that boundary is itself a design trade-off.</p>

<h2>In one session, where reads and writes go</h2>
<p>There's exactly one discipline that guards the cache: <strong>reads only enter the prefix at session start, writes only append to the tail, and the session never rebuilds</strong>. As a single line:</p>
<div class="flow">
  <div class="node hl"><div class="nt">Session start</div><div class="nd">three tiers → fixed prefix</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">Each turn</div><div class="nd">apply…cache_control, 4 breakpoints</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">Cache hit</div><div class="nd">prefix reused, ~75% saved</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">Write = append tail</div><div class="nd">nudge / skill / memory, no rebuild</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node hl"><div class="nt">Only exception</div><div class="nd">context compression → rebuild</div></div>
</div>

<p>So what about the <strong>one exception</strong> — context compression? When a conversation grows close to the model's context window, Hermes <strong>summarizes and compresses</strong> the early history into a shorter span and splices it back. That step <strong>necessarily</strong> rewrites the prefix, so the cache is <strong>bound to be voided</strong> — which is exactly why it's designed to fire only as a <strong>last resort</strong>: spend one “cache reset” to buy back room to keep talking. Outside of that, within the automatic turn loop there is <strong>no reason whatsoever</strong> to rebuild the system prompt mid-session (details in ch.15). <em>(Strictly speaking, a user-initiated switch of model / personality or a manual system-prompt edit also triggers a rebuild — but those are explicit, <strong>out-of-band</strong> events, not part of a normal turn; inside the loop, compression stays the only rebuild.)</em></p>

<p>So what if something <strong>must</strong> change mid-session — the user installs a new skill on the spot, or tweaks the toolset? Hermes's answer is <strong>“deferred invalidation”</strong>: by default the change enters the prefix only <strong>next session</strong>, leaving this turn's cache untouched; only an explicit <span class="mono">--now</span> (see <span class="mono">/skills install --now</span>) voids and rebuilds immediately. This “cache-aware” rule pulls ch.9's skills and the tool commands into the same discipline — never break the cache if you can avoid it. And when compression does rebuild, <span class="mono">invalidate_system_prompt</span> also <strong>re-reads memory from disk</strong>, so the memories and skills written this session get folded into the prefix <strong>exactly</strong> during that already-inevitable cache reset — at no extra cost (ch.11, ch.15).</p>

<p>Each tier maps to a piece of “cross-chapter teamwork” — all of it bending to the <strong>same caching discipline</strong>:</p>
<table class="t">
  <tr><th>Tier</th><th>What it holds</th><th>Changes in-session?</th><th>Who maintains it (cross-ch.)</th></tr>
  <tr><td class="mono">stable</td><td>identity / tools / skills list / env</td><td>No</td><td>skills → stable (ch.9)</td></tr>
  <tr><td class="mono">context</td><td>system_message + project files</td><td>No</td><td>scan before injection (this ch.)</td></tr>
  <tr><td class="mono">volatile</td><td>memory / USER.md / timestamp</td><td>Yes (but at the tail)</td><td>memory / USER.md (ch.11)</td></tr>
</table>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the whole system guards the cache together</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  This chapter's three pieces: <strong>build_system_prompt_parts()</strong> (<span class="mono">system_prompt.py:113</span>) builds the three tiers,
  <strong>apply_anthropic_cache_control()</strong> (<span class="mono">prompt_caching.py:49</span>) places 4 breakpoints,
  <strong>_scan_context_content()</strong> (<span class="mono">prompt_builder.py:46</span>) scans before injection. Every other part bends to the same caching discipline:
  <strong>skills list</strong>→stable (ch.9), <strong>memory / USER.md</strong>→volatile (ch.11),
  <strong>learning nudge</strong>→appended to the tail (ch.9), <strong>search results</strong>→tool messages (ch.12),
  <strong>context compression</strong>→the only allowed rebuild (ch.15), <strong>auxiliary models</strong>→separate session, never polluting the main cache (ch.10).
  <div class="collab-sub">② Data-flow timing</div>
  Session start: the three tiers assemble into a <strong>fixed prefix</strong> → each turn <span class="mono">apply_anthropic_cache_control</span> places 4 breakpoints and hits the cache;
  <strong>reads</strong> (skills / memory / search) enter the prefix only at session start, <strong>or</strong> get appended at the tail as tool / user messages;
  <strong>writes</strong> (nudge / new skill / new memory) only append to the tail, <strong>no rebuild this session</strong> — they enter the prefix only next session;
  <strong>the only exception</strong> = compression, which rewrites history and necessarily voids the cache, so it fires only when unavoidable (ch.15).
  <div class="collab-sub">③ The key point</div>
  The three tiers are <strong>ordered by stability</strong> (stable→context→volatile), pushing the most volatile memory <strong>to the very end</strong> —
  so even when it changes, only the tail of the string moves and <strong>the already-cached stable / context prefix is untouched</strong>. That is the whole point of “volatile last, prefix unharmed.”
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  One throughline dominates everything: <strong>★ the prompt cache is sacred</strong>. The system prompt is <strong>built once per session</strong>, and the <strong>only</strong> moment a rebuild is allowed is context compression (ch.15). From that follow three <strong>anti-patterns</strong> you <strong>never</strong> do mid-session:
  ① swap the toolset (the tool schema is part of the prefix too — swap it and it all dies); ② reload memory / re-read USER.md (rewrites the volatile prefix);
  ③ rebuild the system prompt (change even one byte and the whole prefix cache is void, multiplying cost).
  <p style="margin:.5rem 0 0">It treats two inherent LLM constraints at once: <span class="badge constraint">A·lost-in-the-middle</span> — the tiers pin the most critical identity / instructions <strong>up front</strong>, held stable;
  <span class="badge constraint">D·instr=data</span> — context is scanned <strong>before</strong> injection so external files can't masquerade as instructions inside the prefix.</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Three tiers</strong>: <span class="mono">stable → context → volatile</span> ordered by stability, built by <span class="mono">build_system_prompt_parts()</span> and, in <span class="mono">build_system_prompt()</span>, joined with <span class="mono">\n\n</span>.</li>
    <li><strong>Byte-stable in-session</strong>: built <strong>once per session</strong>, cached on <span class="mono">_cached_system_prompt</span>; the <strong>only</strong> rebuild trigger = context compression (ch.15).</li>
    <li><strong>system_and_3</strong>: <span class="mono">apply_anthropic_cache_control</span> places <strong>4</strong> cache_control breakpoints on system + last 3 non-system messages, saving <strong>~75%</strong>.</li>
    <li><strong>Memory goes last</strong>: the most volatile content sits in volatile, so changing it <strong>doesn't disturb</strong> the already-cached stable / context prefix.</li>
    <li><strong>Scan before injection</strong>: context files pass <span class="mono">_scan_context_content</span> <strong>before</strong> entering the system prompt; a hit is swapped for <span class="mono">[BLOCKED:…]</span>, guarding the prefix (constraint D).</li>
  </ul>
</div>
""",
}

LESSON_07 = {
    "zh": r"""
<p class="lead">
Hermes 同时支持 Anthropic、OpenAI Codex、Gemini、AWS Bedrock、以及二十多家 OpenAI 兼容后端。可它的<strong>核心对话循环</strong>从头到尾只认识<strong>一种</strong>消息格式——OpenAI 风格的 <span class="mono">messages</span>。本章讲清这套「<strong>统一抽象</strong>」是怎么做到的：一张 transport 注册表按 <span class="mono">api_mode</span> 分派，四个 adapter 把统一格式翻译成各家方言，reasoning 跨轮原样回传，外加一条贯穿始终的不变量——<strong>严格角色交替</strong>。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 同声传译 + 万能转接头</div>
  把核心循环想成一位<strong>只说一种语言</strong>的指挥官。面对来自世界各地的将领（provider），他不学二十几门外语，而是雇了一组<strong>同声传译</strong>（adapter）：指挥官永远用「普通话」（OpenAI messages）下令，传译当场翻成对方的方言（Anthropic blocks / Codex responses / Gemini parts / Bedrock converse）；对方的回话再被翻回普通话。<strong>转接头</strong>（transport 注册表）则负责「这位将领该派哪位传译」——查 <span class="mono">api_mode</span>，取对应 transport。加一个新国家，只要再雇一位传译、登记一个转接头，<strong>指挥官一个字都不用改</strong>。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 一套 messages，多家后端</div>
  核心循环（第 5 章）始终在一份 OpenAI 风格的 <span class="mono">messages</span> 上工作：<span class="mono">{"role": "system/user/assistant/tool", ...}</span>。所有 provider 差异——鉴权、字段名、reasoning 形态、tool schema 方言——都被<strong>挡在 transport + adapter 这一层</strong>，绝不渗进核心。出站时 <span class="mono">build_api_kwargs</span> 按 <span class="mono">api_mode</span> 选一个 transport 把统一 messages 翻成各家请求；入站时 <span class="mono">normalize_response</span> 再把各家响应<strong>归一</strong>回同一种 assistant 消息（含 reasoning）。这正是第 4 章「窄腰」哲学的一个具体落点：<strong>核心薄、边缘厚</strong>。
</div>

<h2>分派的起点：transport 注册表</h2>
<p>每一种 <span class="mono">api_mode</span> 对应一个 transport 类。注册表用「<strong>懒发现</strong>」装载——第一次取的时候才扫描并导入所有 transport 模块，之后命中缓存：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/transports/__init__.py</span><span class="ln">21-46 · 节选</span></div>
  <pre><span class="kw">def</span> <span class="fn">register_transport</span>(api_mode, transport_cls):
    <span class="cm"># 四个 transport 模块在文件尾各自调用它登记自己</span>
    _REGISTRY[api_mode] = transport_cls

<span class="kw">def</span> <span class="fn">get_transport</span>(api_mode):
    <span class="kw">global</span> _discovered
    <span class="kw">if</span> <span class="kw">not</span> _discovered:
        _discover_transports()              <span class="cm"># 懒发现：首次才导入所有 transport</span>
    cls = _REGISTRY.get(api_mode)
    <span class="kw">if</span> cls <span class="kw">is</span> <span class="kw">None</span>:
        _discover_transports()              <span class="cm"># miss 也重扫，容忍乱序导入</span>
        cls = _REGISTRY.get(api_mode)
    <span class="kw">if</span> cls <span class="kw">is</span> <span class="kw">None</span>:
        <span class="kw">return</span> <span class="kw">None</span>                        <span class="cm"># 允许调用方回退到旧路径</span>
    <span class="kw">return</span> cls()</pre>
</div>
<p>四个 transport——<span class="mono">anthropic_messages</span> / <span class="mono">codex_responses</span> / <span class="mono">chat_completions</span> / <span class="mono">bedrock_converse</span>——在各自模块尾部调用 <span class="mono">register_transport(...)</span> 把自己挂进 <span class="mono">_REGISTRY</span>。注意 <span class="mono">get_transport</span> 在 miss 时<strong>会再扫一次</strong>：因为测试或乱序导入可能让注册表只装了一半，「未命中就重新发现」保证合法 api_mode 永远取得到。取不到才返回 <span class="mono">None</span>，让调用方优雅回退——这是为<strong>渐进迁移</strong>留的口子。</p>
<p>这里有一个值得注意的<strong>不对称</strong>：transport 有四种（含 bedrock），但 Gemini <strong>不在其中</strong>。因为 Gemini 走的是<strong>客户端层替换</strong>——当 base_url 指向原生 Gemini 时，<span class="mono">GeminiNativeClient</span> 直接<strong>顶替底层 OpenAI client</strong>（<span class="mono">agent_runtime_helpers.py</span>），而它的 <span class="mono">api_mode</span> <strong>仍是 chat_completions</strong>。所以严格说，翻译层是「四个 transport + 一次客户端替换」，adapter 名单（anthropic / codex_responses / gemini_native / bedrock）与 transport 名单并不完全重合——但这一切对核心循环依旧<strong>透明</strong>。</p>
<p>为什么把分派做成<strong>注册表 + 懒发现</strong>，而不是在核心循环里硬写一串 <span class="mono">if api_mode == ...</span>？因为四个 transport 是在<strong>各自模块尾部</strong>才调用 <span class="mono">register_transport</span> 把自己挂上去的，模块导入顺序无法保证——首次取用时某个 transport 可能尚未被 import，注册表只装了一半。于是 <span class="mono">get_transport</span> 一旦未命中就<strong>再扫一次</strong>，专门容忍这种乱序导入；仍取不到才返回 <span class="mono">None</span>，把「这家后端我还不认识」<strong>显式留成一个可回退的空值</strong>，而不是抛异常打断调用方。这样新增一个后端只是「多登记一个 transport」，核心循环对这张表<strong>一无所知</strong>——正是第 4 章窄腰哲学的落地：把最易变的后端集合关进一张可热插拔的表，核心永远只面对抽象。</p>

<h2>出站分派：build_api_kwargs 按 api_mode 选路</h2>
<p>真正把统一 messages 变成「某一家的请求参数」的，是 <span class="mono">build_api_kwargs</span>。它是一组按 <span class="mono">api_mode</span> 的硬分支，每一支取对应 transport、调它的 <span class="mono">build_kwargs</span>：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/chat_completion_helpers.py</span><span class="ln">555-663 · 简化</span></div>
  <pre><span class="kw">def</span> <span class="fn">build_api_kwargs</span>(agent, api_messages):
    <span class="kw">if</span> agent.api_mode == <span class="st">"anthropic_messages"</span>:
        _t = agent._get_transport()                  <span class="cm"># 内部走 get_transport + 缓存</span>
        msgs = agent._prepare_anthropic_messages_for_api(api_messages)
        <span class="kw">return</span> _t.build_kwargs(model=..., messages=msgs, tools=..., ...)

    <span class="kw">if</span> agent.api_mode == <span class="st">"bedrock_converse"</span>:        <span class="cm"># 绕过 OpenAI client，直连 boto3</span>
        <span class="kw">return</span> agent._get_transport().build_kwargs(model=..., messages=api_messages, ...)

    <span class="kw">if</span> agent.api_mode == <span class="st">"codex_responses"</span>:          <span class="cm"># /responses 端点，含 xAI/GitHub 分流</span>
        <span class="kw">return</span> agent._get_transport().build_kwargs(...)

    ...                                              <span class="cm"># else: 默认 chat_completions（最常见）</span></pre>
</div>
<p>读这段要抓住一点：<strong>核心循环不知道「Anthropic 长什么样」</strong>。它只调用 <span class="mono">build_api_kwargs</span>，由后者按 <span class="mono">api_mode</span> 把活儿派给对应 transport / adapter。Bedrock 那一支甚至<strong>完全绕过 OpenAI client</strong>，由 adapter 直接做 boto3 调用——但这对核心是透明的。每加一个后端，只是在这里多一个 <span class="mono">if</span> 分支 + 一个 adapter，<strong>循环本体一行不动</strong>。</p>
<p>这里为什么宁可保留<strong>几条按 <span class="mono">api_mode</span> 的硬分支</strong>，也不去追求一套「纯多态」的优雅？因为各家的差异并不只落在消息格式上：Bedrock 那一支<strong>整个绕开 OpenAI client</strong>、直连 boto3，Codex 打的是 <span class="mono">/responses</span> 端点而非 <span class="mono">/chat/completions</span>——它们在<strong>调用点</strong>就已经分了岔，强行抹平反而会把更多 provider 细节倒灌回核心。工具 schema 同样在这一层按方言翻译：核心始终只持有一份 OpenAI 格式的 tool 定义，由各 adapter 现场把它转成自家结构。代价是每接一个后端要在此多一个 <span class="mono">if</span> 加一个 adapter，<strong>但循环本体一行不动</strong>——把「分支」这点复杂度<strong>留在边缘层</strong>，恰恰是为了守住核心那条窄腰。</p>

<h2>跨轮的连续性：reasoning 的三处存储</h2>
<p>带「思考」（reasoning / thinking）的模型有个棘手要求：这一轮的推理，<strong>下一轮要原样带回去</strong>，否则部分 provider 直接 HTTP 400。Hermes 把 reasoning 拆成<strong>三个字段</strong>分别处置：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/chat_completion_helpers.py</span><span class="ln">885-953 · 简化</span></div>
  <pre>msg = {<span class="st">"role"</span>: <span class="st">"assistant"</span>, <span class="st">"content"</span>: _san_content,
       <span class="st">"reasoning"</span>: reasoning_text, ...}      <span class="cm"># ① reasoning：内部存的思考文本</span>

<span class="cm"># ② reasoning_content：thinking 模式必须回传，缺失则补一个空格防 400</span>
<span class="kw">elif</span> assistant_tool_calls <span class="kw">and</span> agent._needs_thinking_reasoning_pad():
    msg[<span class="st">"reasoning_content"</span>] = reasoning_text <span class="kw">or</span> <span class="st">" "</span>

<span class="cm"># ③ reasoning_details：原样不变透传，维持跨轮推理连续性</span>
<span class="kw">if</span> assistant_message.reasoning_details:
    <span class="cm"># Pass reasoning_details back unmodified so providers can</span>
    <span class="cm"># maintain reasoning continuity across turns.</span>
    msg[<span class="st">"reasoning_details"</span>] = preserved      <span class="cm"># 含 signature/encrypted 等不透明字段</span></pre>
</div>
<p>三个字段各司其职：<span class="mono">reasoning</span> 是内部留存的思考文本；<span class="mono">reasoning_content</span> 是 DeepSeek-v4 / Kimi 等 thinking 模型<strong>硬性要求</strong>回传的字段——一旦缺失，重放历史就会撞上 <span class="inline">"The reasoning_content in the thinking mode must be passed back to the API"</span> 的 400，所以哪怕没捕获到文本，也要补一个<strong>空格</strong>占位（既满足非空校验，又不伪造推理内容）；<span class="mono">reasoning_details</span> 则<strong>原样不动</strong>地透传——注释写得很直白：<span class="inline">Pass reasoning_details back unmodified so providers ... can maintain reasoning continuity across turns</span>。里面的 <span class="mono">signature</span> / <span class="mono">encrypted_content</span> 等不透明字段，<strong>改一个字节都会让推理链断裂</strong>。这正对应一条 LLM 约束 <span class="badge constraint">G·推理token不持久</span>——模型自己记不住上一轮怎么想的，只能靠我们把推理痕迹<strong>原样搬回</strong>可见上下文。</p>
<p>为什么要把它拆成<strong>三个字段</strong>而不是一个？因为「思考」这件事各家的<strong>契约互不相同</strong>：有的（DeepSeek-v4 / Kimi 系）硬性要求 <span class="mono">reasoning_content</span> 非空回传，有的则要 <span class="mono">reasoning_details</span> 里的 <span class="mono">signature</span> / <span class="mono">encrypted_content</span> 原样不动地透传。这背后正是约束 <span class="badge constraint">G·推理token不持久</span>（第 3 章）——模型<strong>记不住自己上一轮的推理</strong>，痕迹一旦不回传就等于断片，部分 provider 还会直接回 400。所以哪怕这一轮没捕获到任何思考文本，也要补一个<strong>空格</strong>占位：既过得了非空校验，又不<strong>伪造</strong>出根本不存在的推理。而内部那份则照 AGENTS.md 的约定存进 <span class="mono">assistant_msg["reasoning"]</span>，与对外回传的两个字段各管各的、互不污染。</p>

<h2>出站到入站：一条完整的数据流</h2>
<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">统一 messages（OpenAI 风格，核心循环唯一认得的格式）</span></div>
  <div class="step"><span class="num">2</span><span class="sc">repair_message_sequence_with_cursor —— 每次 API 调用前修复严格角色交替</span></div>
  <div class="step"><span class="num">3</span><span class="sc">build_api_kwargs 按 api_mode 取 transport</span></div>
  <div class="step"><span class="num">4</span><span class="sc">adapter 翻译成各家方言（Anthropic blocks / Codex input / Gemini parts / Bedrock converse）</span></div>
  <div class="step"><span class="num">5</span><span class="sc">provider API 返回响应</span></div>
  <div class="step"><span class="num">6</span><span class="sc">normalize_response 归一回统一 assistant 消息（含 reasoning 三字段）</span></div>
  <div class="step"><span class="num">7</span><span class="sc">append 进 messages —— 回到核心循环，进入下一轮</span></div>
</div>
<p>第 2 步的<strong>角色交替修复</strong>是整条链的隐形守门员。Provider 普遍要求消息<strong>严格交替</strong>（不能两条同 role 连续、不能有孤儿 tool 消息），违反就返回空响应、触发重试。<span class="mono">repair_message_sequence_with_cursor</span> 在<strong>每次 API 调用前</strong>跑一遍：删掉没有配对的孤儿 tool 消息、合并连续的 user 消息。它在<strong>发送前直接就地修整</strong> live messages（<span class="mono">messages[:] = merged</span>，持久化 / SessionDB 都会看到修整结果），只做<strong>最小外科式</strong>整理、<strong>绝不激进重建上下文</strong>——避免无谓改写历史击穿缓存（第 6 章）。</p>
<p>为什么角色交替这条不变量如此<strong>不可妥协</strong>？两重原因叠加。其一是<strong>协议层</strong>：OpenAI / OpenRouter / Anthropic 都要求 system 之后 user/tool 与 assistant <strong>严格交替</strong>，一旦出现两条同 role 连续、或不跟在 assistant tool_call 之后的孤儿 tool 消息，多数 provider<strong>直接静默返回空响应</strong>，把对话拖进徒劳的「空响应重试」循环。其二是<strong>缓存层</strong>：AGENTS.md 明令 <span class="inline">never two same-role messages in a row; never a synthetic user message injected mid-loop</span>——循环中途哪怕注入一句合成的 user message，都会在<strong>正被缓存的前缀</strong>里凭空多出 token，缓存 key 一变，整段历史被迫重新编码（第 6 章）。所以「修交替」和「守缓存」其实是<strong>同一件事的两面</strong>。</p>

<div class="figure">
<svg viewBox="0 0 680 256" role="img" aria-label="严格角色交替：合法序列逐条交替，违规出现两条同角色相邻导致空响应与 empty-retry">
  <text x="20" y="24" font-size="13" font-weight="700" fill="var(--accent-ink)">✅ 合法 · system 之后 user/tool 与 assistant 严格交替</text>
  <g font-size="12" text-anchor="middle">
    <rect x="24"  y="42" width="104" height="46" rx="9" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="76"  y="71" fill="var(--ink)">system</text>
    <rect x="148" y="42" width="104" height="46" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="200" y="71" fill="var(--blue)">user</text>
    <rect x="272" y="42" width="104" height="46" rx="9" fill="var(--accent-soft)" stroke="var(--accent)"/>
    <text x="324" y="71" fill="var(--accent-ink)">assistant</text>
    <rect x="396" y="42" width="104" height="46" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="448" y="71" fill="var(--blue)">user</text>
    <rect x="520" y="42" width="104" height="46" rx="9" fill="var(--accent-soft)" stroke="var(--accent)"/>
    <text x="572" y="71" fill="var(--accent-ink)">assistant</text>
  </g>
  <g font-size="15" fill="var(--faint)" text-anchor="middle">
    <text x="138" y="70">→</text>
    <text x="262" y="70">→</text>
    <text x="386" y="70">→</text>
    <text x="510" y="70">→</text>
  </g>
  <text x="324" y="106" text-anchor="middle" font-size="11" fill="var(--muted)">相邻两条消息的 role 永不相同 → 不变量成立，缓存前缀稳定</text>

  <text x="20" y="142" font-size="13" font-weight="700" fill="var(--red)">❌ 违规 · 两条 user 连续（mid-loop 注入合成消息 / 多队列重放）</text>
  <g font-size="12" text-anchor="middle">
    <rect x="24"  y="158" width="104" height="46" rx="9" fill="var(--accent-soft)" stroke="var(--accent)"/>
    <text x="76"  y="187" fill="var(--accent-ink)">assistant</text>
    <rect x="148" y="158" width="104" height="46" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="200" y="187" fill="var(--blue)">user</text>
    <rect x="256" y="158" width="104" height="46" rx="9" fill="var(--red-soft)" stroke="var(--red)" stroke-width="2"/>
    <text x="308" y="187" fill="var(--red)">user</text>
    <text x="378" y="188" font-size="20" font-weight="700" fill="var(--red)">✕</text>
    <rect x="400" y="158" width="224" height="46" rx="9" fill="var(--red-soft)" stroke="var(--red)"/>
    <text x="512" y="187" fill="var(--red)">provider 静默返回空响应</text>
  </g>
  <text x="254" y="224" text-anchor="middle" font-size="10.5" fill="var(--red)">↑ 两条同 role 相邻</text>
  <text x="512" y="224" text-anchor="middle" font-size="10.5" fill="var(--muted)">→ 拖进徒劳的 empty-retry 重试循环</text>
  <text x="20" y="248" font-size="10" fill="var(--faint)">AGENTS.md：never two same-role messages in a row · agent_runtime_helpers.py：empty-retry loop</text>
</svg>
<div class="fig-cap"><b>严格角色交替</b>：system 之后，user/tool 必须与 assistant 逐条交替（上排 ✅）。一旦出现两条同 role 相邻——典型来自循环中途注入的合成 user 消息、网关多队列重放或会话 resume——多数 provider <b>静默返回空响应</b>，把对话拖进徒劳的 <b>empty-retry</b> 循环（下排 ❌）。这正是 <span class="mono">repair_message_sequence_with_cursor</span> 每次 API 调用前要合并连续 user、删孤儿 tool 的原因。</div>
</div>
<p>也正因如此，<span class="mono">repair_message_sequence_with_cursor</span> 只做<strong>最小外科式</strong>整理——丢掉配不上任何 <span class="mono">tool_call_id</span> 的孤儿 tool 消息、把连续的 user 合并成一条，<strong>绝不激进重建上下文</strong>，还特意保住存活消息的对象 identity，好让 SessionDB 的 flush 游标不会错位。这些破损序列从哪来？docstring 列得很清楚：网关多队列重放、会话 resume、cron、以及宿主显式传入的 <span class="mono">conversation_history</span>。这恰好解释了几处跨章设计的真正用意：cron 另起<strong>独立会话、不镜像主对话</strong>（第 21 章），网关把 <span class="mono">/stop</span>/<span class="mono">/approve</span> 等控制命令<strong>旁路出历史</strong>（第 18 章），委派子代理用<strong>隔离上下文</strong>（第 13 章）——本质都是不让外来消息混进主对话、打破它的交替与缓存。</p>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「一套 messages 跑遍所有后端」</div>
  <div class="collab-sub">① 组件清单（★本章核心，其余跨章节配合）</div>
  本章五件：<strong>transport 注册表</strong>（<span class="mono">register/get_transport</span>）登记+分派、<strong>四个 adapter</strong>（anthropic / codex_responses / gemini_native / bedrock）翻译、<strong>build_api_kwargs</strong> 出站构造、<strong>conversation_loop 入站归一</strong>（normalize_response）、<strong>repair_message_sequence_with_cursor</strong> 修复交替。跨章节配合：严格角色交替不变量<strong>服务 prompt 缓存</strong>（第 6 章——历史字节稳定，缓存才不破）；reasoning 三字段把推理痕迹<strong>落进可见上下文</strong>对抗「推理 token 不持久」（第 3 章 G）；「加新 provider 不改核心循环」正是<strong>窄腰哲学</strong>的体现（第 4 章）。
  <div class="collab-sub">② 数据流时序</div>
  统一 messages → repair 修复交替 → build_api_kwargs 按 api_mode 选 transport → adapter 翻成各家方言 → provider API → normalize_response 归一回统一 assistant 消息（含 reasoning）→ append → 下一轮。出站「翻出去」、入站「翻回来」，核心循环全程只见统一格式。
  <div class="collab-sub">③ 关键点</div>
  核心只认<strong>一种</strong> messages 格式；所有 provider 差异——鉴权、字段名、reasoning 形态、tool schema 方言——被 transport / adapter <strong>整层吸收</strong>。于是「支持一个新后端」退化成「写一个 adapter + 登记一个 transport」，<strong>核心对话循环零改动</strong>。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线：<strong>统一抽象 + 严格角色交替不变量</strong>——一套 messages，多家后端；并在每次 API 调用前修复交替。它治两条 LLM 固有约束（并把一条工程脆弱关进边缘）：
  <p style="margin:.5rem 0 0"><span class="badge constraint">E·结构化输出脆弱</span>——function calling / tool schema 统一成 OpenAI 格式，由 adapter 各自翻成方言（xAI 还要现场剥掉它不认的 schema 关键字），把「结构化输出对方言敏感」这件脆弱事关进边缘层；
  <span class="badge constraint">G·推理token不持久</span>——<span class="mono">reasoning_details</span> 原样跨轮 replay，让模型「接着上轮想」；
  <span class="badge constraint">窄腰·方言隔离</span>——统一格式把 provider 差异<strong>隔离</strong>，核心 prompt 不必为每家后端写一套。反模式：把某家 provider 的特殊字段、特殊鉴权<strong>泄漏进核心循环</strong>——那等于让指挥官去学方言，每加一家就要改一次核心。</p>
  <p style="margin:.5rem 0 0">把 <span class="badge constraint">E·结构化输出脆弱</span> 单拎出来看：模型的 function calling 输出对 schema 方言<strong>极其敏感</strong>，少一个字段、多一个它不认的关键字，就可能整段塌回自由文本。Hermes 的应对是「<strong>用统一 schema 约束、错了让模型看见错误重试</strong>」——核心只持一份 OpenAI 格式的工具定义，由 adapter 各自翻成方言、并就地剥掉对方不兼容的关键字，把这份脆弱性<strong>整层关进边缘</strong>。而这份工具 schema <strong>每一次 API 调用都会原样发送出去</strong>（AGENTS.md：每个核心工具都付出「每次调用都带上」的代价）——这也正是核心工具数量必须<strong>克制</strong>的根因。</p>
  <p style="margin:.5rem 0 0">schema「每次都发」还反过来给缓存定了一条死规矩：既然它<strong>本身就是被缓存前缀的一部分</strong>，那么<strong>会话中途换工具集 = 改 schema = 改前缀 = 缓存全废</strong>（第 6 章）。这就是为什么 Hermes 坚持「会话内工具集稳定」、靠 <span class="mono">check_fn</span> 在会话<strong>开始之前</strong>就把可用工具定下来，而不是跑到一半再增删。最该警惕的反模式，是把某家 provider 的特殊字段、特殊鉴权<strong>泄漏进核心循环</strong>——那等于让只说普通话的指挥官改去学方言：每接一家后端就要动一次核心，还顺手击穿了本该一路命中的缓存。</p>

<div class="figure">
<svg viewBox="0 0 680 252" role="img" aria-label="工具 schema 属于缓存前缀：每轮原样重发，换工具集即改前缀导致缓存整体作废">
  <text x="20" y="24" font-size="13" font-weight="700" fill="var(--accent-ink)">✅ 工具 schema 是缓存前缀的一部分，且每轮 API 调用原样重发</text>
  <g font-size="11.5" text-anchor="middle">
    <rect x="20"  y="40" width="150" height="50" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="95"  y="70" fill="var(--ink)">system 提示</text>
    <rect x="170" y="40" width="220" height="50" rx="8" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
    <text x="280" y="65" fill="var(--accent-ink)">工具 schema</text>
    <text x="280" y="81" font-size="10" fill="var(--accent-ink)">每次 API 调用都携带</text>
    <rect x="390" y="40" width="150" height="50" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="465" y="70" fill="var(--ink)">历史消息</text>
    <rect x="540" y="40" width="120" height="50" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="600" y="70" fill="var(--blue)">最近新增</text>
  </g>
  <path d="M20 98 L20 104 L540 104 L540 98" fill="none" stroke="var(--accent)" stroke-width="1.3"/>
  <text x="280" y="120" text-anchor="middle" font-size="11" fill="var(--muted)">↑ 被缓存的前缀（逐字节稳定 → 按缓存读取价命中）</text>
  <text x="600" y="104" text-anchor="middle" font-size="10.5" fill="var(--muted)">全价</text>

  <text x="20" y="156" font-size="13" font-weight="700" fill="var(--red)">❌ 会话中途换工具集 → schema 变 → 前缀变 → 缓存全废</text>
  <g font-size="11.5" text-anchor="middle">
    <rect x="20"  y="172" width="150" height="50" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="95"  y="202" fill="var(--ink)">system 提示</text>
    <rect x="170" y="172" width="220" height="50" rx="8" fill="var(--red-soft)" stroke="var(--red)" stroke-width="2"/>
    <text x="270" y="197" fill="var(--red)">工具 schema 改了</text>
    <text x="358" y="190" font-size="16" font-weight="700" fill="var(--red)">✕</text>
    <text x="280" y="213" font-size="10" fill="var(--red)">换了工具集</text>
    <rect x="390" y="172" width="270" height="50" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
    <text x="525" y="196" fill="var(--red)">前缀改变 → 缓存整体作废</text>
    <text x="525" y="212" font-size="10" fill="var(--red)">从此点起全价重算（第 6 章）</text>
  </g>
  <text x="20" y="244" font-size="10" fill="var(--faint)">AGENTS.md：never change toolsets mid-conversation · check_fn 在会话开始前定下可用工具</text>
</svg>
<div class="fig-cap"><b>工具 schema 属于缓存前缀</b>：核心持有的那份 OpenAI 格式工具 schema <b>每次 API 调用都原样发送</b>，因而它本身就是被缓存前缀的一部分（上排 ✅）。于是「会话中途换工具集」＝改 schema ＝改前缀，从改动点起缓存<b>整体作废、全价重算</b>（下排 ❌，连第 6 章）。这就是 Hermes 坚持会话内工具集稳定、用 <span class="mono">check_fn</span> 在会话<b>开始之前</b>就把可用工具定下来的原因。</div>
</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 462" role="img" aria-label="一条 Read my AGENTS.md 从统一 messages 翻译为 Anthropic 真实请求体的字段对照">
  <text x="18" y="24" font-size="13" font-weight="700" fill="var(--accent-ink)">实例：Read my AGENTS.md 从统一 messages 翻成 Anthropic 真实请求体</text>

  <rect x="18" y="36" width="644" height="74" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="30" y="55" font-size="10.5" font-weight="700" fill="var(--blue)">① 统一入口（核心只认 OpenAI messages + OpenAI 工具）</text>
  <text x="30" y="75" font-size="9" font-family="monospace" fill="var(--ink)">messages:[{role:&quot;system&quot;,...}, {role:&quot;user&quot;, content:&quot;Read my AGENTS.md&quot;}]</text>
  <text x="30" y="90" font-size="9" font-family="monospace" fill="var(--ink)">tools:[{&quot;type&quot;:&quot;function&quot;,&quot;function&quot;:{&quot;name&quot;:&quot;read_file&quot;,&quot;parameters&quot;:{...}}}]</text>
  <text x="650" y="104" text-anchor="end" font-size="9" fill="var(--muted)">chat_completion_helpers.py</text>

  <text x="340" y="127" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--accent-ink)">② api_mode==&quot;anthropic_messages&quot; → build_api_kwargs 分派 · :559</text>
  <path d="M340 130 L340 134" stroke="var(--accent)" stroke-width="1.5"/>
  <path d="M336 132 L340 140 L344 132 Z" fill="var(--accent)"/>

  <rect x="18" y="144" width="644" height="130" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="30" y="163" font-size="10.5" font-weight="700" fill="var(--ink)">③ adapter 翻译：OpenAI 字段 → Anthropic 字段（红 → 蓝）</text>

  <rect x="30" y="172" width="252" height="20" rx="4" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="40" y="186" font-size="9" fill="var(--red)">role:&quot;system&quot; 消息（在 messages 内）</text>
  <path d="M288 182 L306 182" stroke="var(--muted)" stroke-width="1.3"/>
  <path d="M302 178 L310 182 L302 186 Z" fill="var(--muted)"/>
  <rect x="316" y="172" width="252" height="20" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="326" y="186" font-size="9" fill="var(--blue)">抽到顶层 system 参数</text>
  <text x="650" y="186" text-anchor="end" font-size="9" fill="var(--faint)">:2465-2474</text>

  <rect x="30" y="197" width="252" height="20" rx="4" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="40" y="211" font-size="9" font-family="monospace" fill="var(--red)">function.parameters</text>
  <path d="M288 207 L306 207" stroke="var(--muted)" stroke-width="1.3"/>
  <path d="M302 203 L310 207 L302 211 Z" fill="var(--muted)"/>
  <rect x="316" y="197" width="252" height="20" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="326" y="211" font-size="9" font-family="monospace" fill="var(--blue)">input_schema</text>
  <text x="650" y="211" text-anchor="end" font-size="9" fill="var(--faint)">:1595-1600</text>

  <rect x="30" y="222" width="252" height="20" rx="4" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="40" y="236" font-size="9" font-family="monospace" fill="var(--red)">function.name</text>
  <path d="M288 232 L306 232" stroke="var(--muted)" stroke-width="1.3"/>
  <path d="M302 228 L310 232 L302 236 Z" fill="var(--muted)"/>
  <rect x="316" y="222" width="252" height="20" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="326" y="236" font-size="9" font-family="monospace" fill="var(--blue)">name</text>
  <text x="650" y="236" text-anchor="end" font-size="9" fill="var(--faint)">:1595-1600</text>

  <rect x="30" y="247" width="252" height="20" rx="4" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="40" y="261" font-size="9" fill="var(--red)">（缺）max_tokens</text>
  <path d="M288 257 L306 257" stroke="var(--muted)" stroke-width="1.3"/>
  <path d="M302 253 L310 257 L302 261 Z" fill="var(--muted)"/>
  <rect x="316" y="247" width="252" height="20" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="326" y="261" font-size="9" fill="var(--blue)">补 max_tokens（Anthropic 必填）</text>
  <text x="650" y="261" text-anchor="end" font-size="9" fill="var(--faint)">:2465-2474</text>

  <rect x="18" y="282" width="644" height="78" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="30" y="301" font-size="10.5" font-weight="700" fill="var(--accent-ink)">④ 真实出站请求体（Anthropic Messages API）</text>
  <text x="30" y="321" font-size="9" font-family="monospace" fill="var(--ink)">{&quot;model&quot;:&quot;claude-opus-4.7&quot;, &quot;messages&quot;:[...], &quot;max_tokens&quot;:...,</text>
  <text x="30" y="336" font-size="9" font-family="monospace" fill="var(--ink)"> &quot;system&quot;:[...], &quot;tools&quot;:[{&quot;name&quot;:&quot;read_file&quot;,&quot;input_schema&quot;:{...}}]}</text>
  <text x="650" y="354" text-anchor="end" font-size="9" fill="var(--muted)">anthropic_adapter.py:2465-2474</text>

  <rect x="18" y="370" width="314" height="82" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="30" y="389" font-size="10.5" font-weight="700" fill="var(--ink)">⑤ normalize_response 入站归一</text>
  <text x="30" y="409" font-size="9" fill="var(--muted)">Anthropic 响应 → 统一 OpenAI 风格消息</text>
  <text x="30" y="425" font-size="9" fill="var(--muted)">content / tool_calls / usage 对齐回核心</text>
  <text x="30" y="445" font-size="9" fill="var(--muted)">核心循环不感知方言差异</text>

  <rect x="344" y="370" width="318" height="82" rx="8" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="356" y="389" font-size="10.5" font-weight="700" fill="var(--purple)">⑥ reasoning 三字段（跨轮一致）</text>
  <text x="356" y="408" font-size="9" font-family="monospace" fill="var(--ink)">reasoning：内部留存 · :888</text>
  <text x="356" y="423" font-size="9" font-family="monospace" fill="var(--ink)">reasoning_content：缺补 &quot; &quot; 防 400 · :911</text>
  <text x="356" y="438" font-size="9" font-family="monospace" fill="var(--ink)">reasoning_details：原样透传 · :938-940</text>
</svg>
<div class="fig-cap"><b>同一条消息出站翻译的真实字段 diff</b>：统一 OpenAI <span class="mono">messages</span> + 工具经 <span class="mono">api_mode==&quot;anthropic_messages&quot;</span> 分派后，adapter 把 <span class="mono">role:&quot;system&quot;</span> 抽成顶层 <span class="mono">system</span>、<span class="mono">function.parameters→input_schema</span>、<span class="mono">function.name→name</span>，并补必填 <span class="mono">max_tokens</span>，拼出真实 Anthropic 请求体；入站 <span class="mono">normalize_response</span> 再归一，<span class="mono">reasoning</span> 三字段（含缺则补 <span class="mono">&quot; &quot;</span> 防 400）保证跨轮一致。</div>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>统一 messages</strong>：核心循环只认 OpenAI 风格 <span class="mono">messages</span>，provider 差异全被 transport + adapter 吸收。</li>
    <li><strong>transport 注册表</strong>：<span class="mono">register/get_transport</span> 懒发现，按 <span class="mono">api_mode</span> 分派；加后端只需登记 transport + 写 adapter。</li>
    <li><strong>build_api_kwargs</strong>：按 <span class="mono">api_mode</span> 四分支出站构造；Bedrock 直连 boto3、Codex 走 /responses，核心循环不感知。</li>
    <li><strong>reasoning 三处存储</strong>：<span class="mono">reasoning</span> 内部留存、<span class="mono">reasoning_content</span> thinking 回传（缺失 pad 空格防 400）、<span class="mono">reasoning_details</span> 原样跨轮透传（约束 G）。</li>
    <li><strong>角色交替修复</strong>：每次 API 调用前 <span class="mono">repair_message_sequence_with_cursor</span> 删孤儿 tool、合并连续 user；就地最小修整、不激进重建上下文（守缓存）。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">
Hermes speaks to Anthropic, OpenAI Codex, Gemini, AWS Bedrock, and twenty-odd OpenAI-compatible backends. Yet its <strong>core conversation loop</strong> knows just <strong>one</strong> message format end to end — OpenAI-style <span class="mono">messages</span>. This chapter shows how that <strong>unified abstraction</strong> works: a transport registry dispatches by <span class="mono">api_mode</span>, four adapters translate the unified format into each backend's dialect, reasoning is replayed verbatim across turns, plus one invariant that runs through it all — <strong>strict role alternation</strong>.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · simultaneous interpreters + a universal adapter</div>
  Picture the core loop as a commander who speaks <strong>only one language</strong>. Facing generals from all over the world (providers), he doesn't learn twenty tongues — he hires a team of <strong>simultaneous interpreters</strong> (adapters): the commander always issues orders in "standard speech" (OpenAI messages), and the interpreter translates on the spot into each dialect (Anthropic blocks / Codex responses / Gemini parts / Bedrock converse); replies are translated back. The <strong>universal adapter</strong> (the transport registry) decides "which interpreter for this general" — look up <span class="mono">api_mode</span>, fetch the matching transport. Add a new country and you just hire one interpreter and register one adapter — <strong>the commander changes not a single word</strong>.
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture · one set of messages, many backends</div>
  The core loop (ch.5) always works on one OpenAI-style <span class="mono">messages</span> list: <span class="mono">{"role": "system/user/assistant/tool", ...}</span>. Every provider difference — auth, field names, reasoning shape, tool-schema dialect — is <strong>held at the transport + adapter layer</strong> and never seeps into the core. Outbound, <span class="mono">build_api_kwargs</span> picks a transport by <span class="mono">api_mode</span> to translate the unified messages into each backend's request; inbound, <span class="mono">normalize_response</span> <strong>normalizes</strong> each backend's reply back into the same assistant message (reasoning included). This is one concrete landing spot for the ch.4 "narrow waist": <strong>thin core, thick edges</strong>.
</div>

<h2>Where dispatch begins: the transport registry</h2>
<p>Each <span class="mono">api_mode</span> maps to a transport class. The registry loads via <strong>lazy discovery</strong> — it scans and imports all transport modules only on first fetch, then hits the cache:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/transports/__init__.py</span><span class="ln">21-46 · excerpt</span></div>
  <pre><span class="kw">def</span> <span class="fn">register_transport</span>(api_mode, transport_cls):
    <span class="cm"># the four transport modules each call this at file end to register</span>
    _REGISTRY[api_mode] = transport_cls

<span class="kw">def</span> <span class="fn">get_transport</span>(api_mode):
    <span class="kw">global</span> _discovered
    <span class="kw">if</span> <span class="kw">not</span> _discovered:
        _discover_transports()              <span class="cm"># lazy: import all transports on first use</span>
    cls = _REGISTRY.get(api_mode)
    <span class="kw">if</span> cls <span class="kw">is</span> <span class="kw">None</span>:
        _discover_transports()              <span class="cm"># re-scan on miss; tolerate out-of-order imports</span>
        cls = _REGISTRY.get(api_mode)
    <span class="kw">if</span> cls <span class="kw">is</span> <span class="kw">None</span>:
        <span class="kw">return</span> <span class="kw">None</span>                        <span class="cm"># let callers fall back to the legacy path</span>
    <span class="kw">return</span> cls()</pre>
</div>
<p>The four transports — <span class="mono">anthropic_messages</span> / <span class="mono">codex_responses</span> / <span class="mono">chat_completions</span> / <span class="mono">bedrock_converse</span> — call <span class="mono">register_transport(...)</span> at the bottom of their modules to hook themselves into <span class="mono">_REGISTRY</span>. Note that <span class="mono">get_transport</span> <strong>re-scans on a miss</strong>: tests or out-of-order imports may leave the registry half-populated, so "discover again if not found" guarantees a valid api_mode is always resolvable. Only then does it return <span class="mono">None</span>, letting the caller fall back gracefully — a hook left for <strong>gradual migration</strong>.</p>
<p>One <strong>asymmetry</strong> is worth noting: there are four transports (including bedrock), but Gemini is <strong>not</strong> among them. Gemini uses <strong>client-layer substitution</strong> — when the base_url points at native Gemini, <span class="mono">GeminiNativeClient</span> directly <strong>replaces the underlying OpenAI client</strong> (<span class="mono">agent_runtime_helpers.py</span>), while its <span class="mono">api_mode</span> <strong>stays chat_completions</strong>. So strictly, the translation layer is 'four transports + one client swap', and the adapter list (anthropic / codex_responses / gemini_native / bedrock) doesn't fully overlap the transport list — yet all of this stays <strong>transparent</strong> to the core loop.</p>
<p>Why build dispatch as a <strong>registry + lazy discovery</strong> instead of a chain of <span class="mono">if api_mode == ...</span> in the core loop? Because the four transports only call <span class="mono">register_transport</span> at the <strong>bottom of their own modules</strong>, and import order isn't guaranteed — on first use a given transport may not be imported yet, leaving the registry half-populated. So <span class="mono">get_transport</span> <strong>re-scans on a miss</strong>, specifically to tolerate that out-of-order import; only if still absent does it return <span class="mono">None</span>, turning "I don't know this backend yet" into an <strong>explicit, fallback-able empty value</strong> rather than an exception that breaks the caller. Adding a backend is then just "register one more transport," and the core loop <strong>knows nothing of this table</strong> — the ch.4 narrow-waist philosophy made concrete: cage the most volatile set (backends) in a hot-pluggable table, and keep the core facing only an abstraction.</p>

<h2>Outbound dispatch: build_api_kwargs routes by api_mode</h2>
<p>What actually turns unified messages into "one backend's request params" is <span class="mono">build_api_kwargs</span>. It is a set of hard branches keyed on <span class="mono">api_mode</span>, each fetching the right transport and calling its <span class="mono">build_kwargs</span>:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/chat_completion_helpers.py</span><span class="ln">555-663 · simplified</span></div>
  <pre><span class="kw">def</span> <span class="fn">build_api_kwargs</span>(agent, api_messages):
    <span class="kw">if</span> agent.api_mode == <span class="st">"anthropic_messages"</span>:
        _t = agent._get_transport()                  <span class="cm"># wraps get_transport + caching</span>
        msgs = agent._prepare_anthropic_messages_for_api(api_messages)
        <span class="kw">return</span> _t.build_kwargs(model=..., messages=msgs, tools=..., ...)

    <span class="kw">if</span> agent.api_mode == <span class="st">"bedrock_converse"</span>:        <span class="cm"># bypass OpenAI client, talk boto3 directly</span>
        <span class="kw">return</span> agent._get_transport().build_kwargs(model=..., messages=api_messages, ...)

    <span class="kw">if</span> agent.api_mode == <span class="st">"codex_responses"</span>:          <span class="cm"># /responses endpoint, with xAI/GitHub routing</span>
        <span class="kw">return</span> agent._get_transport().build_kwargs(...)

    ...                                              <span class="cm"># else: default chat_completions (most common)</span></pre>
</div>
<p>The thing to grasp: <strong>the core loop has no idea what "Anthropic looks like."</strong> It only calls <span class="mono">build_api_kwargs</span>, which routes the work to the matching transport / adapter by <span class="mono">api_mode</span>. The Bedrock branch even <strong>bypasses the OpenAI client entirely</strong>, with the adapter making boto3 calls directly — yet that's transparent to the core. Each new backend is just one more <span class="mono">if</span> branch + an adapter here, with <strong>not a line changed in the loop itself</strong>.</p>
<p>Why keep <strong>a few hard branches keyed on <span class="mono">api_mode</span></strong> here rather than chase a "pure polymorphism" elegance? Because the differences aren't only in message format: the Bedrock branch <strong>bypasses the OpenAI client entirely</strong> and talks boto3, while Codex hits the <span class="mono">/responses</span> endpoint, not <span class="mono">/chat/completions</span> — they fork at the <strong>call site</strong>, and flattening that away would only pour more provider detail back into the core. Tool schemas are translated at this same layer: the core always holds one OpenAI-format tool definition, and each adapter converts it into its own shape on the spot. The cost is one more <span class="mono">if</span> plus an adapter per backend — <strong>but the loop body never changes</strong>. Keeping that pinch of branching complexity <strong>at the edge</strong> is exactly how the core's narrow waist is preserved.</p>

<h2>Continuity across turns: reasoning's three stores</h2>
<p>"Thinking" (reasoning) models bring a tricky demand: this turn's reasoning must be <strong>handed back verbatim next turn</strong>, or some providers return HTTP 400 outright. Hermes splits reasoning into <strong>three fields</strong>, each handled differently:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/chat_completion_helpers.py</span><span class="ln">885-953 · simplified</span></div>
  <pre>msg = {<span class="st">"role"</span>: <span class="st">"assistant"</span>, <span class="st">"content"</span>: _san_content,
       <span class="st">"reasoning"</span>: reasoning_text, ...}      <span class="cm"># ① reasoning: the internal thought text</span>

<span class="cm"># ② reasoning_content: thinking mode must replay it; pad a space if missing</span>
<span class="kw">elif</span> assistant_tool_calls <span class="kw">and</span> agent._needs_thinking_reasoning_pad():
    msg[<span class="st">"reasoning_content"</span>] = reasoning_text <span class="kw">or</span> <span class="st">" "</span>

<span class="cm"># ③ reasoning_details: passed back unmodified to keep reasoning continuous</span>
<span class="kw">if</span> assistant_message.reasoning_details:
    <span class="cm"># Pass reasoning_details back unmodified so providers can</span>
    <span class="cm"># maintain reasoning continuity across turns.</span>
    msg[<span class="st">"reasoning_details"</span>] = preserved      <span class="cm"># carries signature/encrypted opaque fields</span></pre>
</div>
<p>The three fields each do their job: <span class="mono">reasoning</span> is the internally kept thought text; <span class="mono">reasoning_content</span> is the field that DeepSeek-v4 / Kimi-style thinking models <strong>strictly require</strong> on replay — miss it and the next turn hits a 400, <span class="inline">"The reasoning_content in the thinking mode must be passed back to the API"</span>, so even with no captured text Hermes pads a single <strong>space</strong> (satisfying the non-empty check without fabricating reasoning); <span class="mono">reasoning_details</span> is passed through <strong>unchanged</strong> — the comment says it plainly: <span class="inline">Pass reasoning_details back unmodified so providers ... can maintain reasoning continuity across turns</span>. Its opaque <span class="mono">signature</span> / <span class="mono">encrypted_content</span> fields would <strong>break the reasoning chain if a single byte changed</strong>. This maps to the LLM constraint <span class="badge constraint">G·reasoning tokens not persisted</span> — the model can't remember how it reasoned last turn, so we must carry the reasoning trace <strong>verbatim</strong> back into visible context.</p>
<p>Why split it into <strong>three fields</strong> instead of one? Because "thinking" carries a <strong>different contract per provider</strong>: some (DeepSeek-v4 / Kimi-style) strictly demand a non-empty <span class="mono">reasoning_content</span> on replay, while others need the <span class="mono">signature</span> / <span class="mono">encrypted_content</span> inside <span class="mono">reasoning_details</span> passed back byte-for-byte. Behind it is constraint <span class="badge constraint">G·reasoning tokens not persisted</span> (ch.3) — the model <strong>can't recall its own prior reasoning</strong>, so dropping the trace is amnesia, and some providers answer 400 outright. That's why Hermes pads a single <strong>space</strong> even when no thought text was captured this turn: it satisfies the non-empty check without <strong>fabricating</strong> reasoning that never existed. The internal copy, per AGENTS.md, is kept in <span class="mono">assistant_msg["reasoning"]</span>, each field minding its own job without polluting the others.</p>

<h2>Outbound to inbound: one complete data flow</h2>
<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">unified messages (OpenAI style — the only format the core loop knows)</span></div>
  <div class="step"><span class="num">2</span><span class="sc">repair_message_sequence_with_cursor — fix strict role alternation before every API call</span></div>
  <div class="step"><span class="num">3</span><span class="sc">build_api_kwargs fetches a transport by api_mode</span></div>
  <div class="step"><span class="num">4</span><span class="sc">adapter translates into each dialect (Anthropic blocks / Codex input / Gemini parts / Bedrock converse)</span></div>
  <div class="step"><span class="num">5</span><span class="sc">provider API returns a response</span></div>
  <div class="step"><span class="num">6</span><span class="sc">normalize_response normalizes back to a unified assistant message (with reasoning's 3 fields)</span></div>
  <div class="step"><span class="num">7</span><span class="sc">append into messages — back to the core loop, on to the next turn</span></div>
</div>
<p>Step 2's <strong>role-alternation repair</strong> is the invisible gatekeeper of the whole chain. Providers broadly require messages to <strong>strictly alternate</strong> (no two same-role in a row, no orphan tool messages); violate it and you get an empty response and a retry. <span class="mono">repair_message_sequence_with_cursor</span> runs <strong>before every API call</strong>: it drops unpaired orphan tool messages and merges consecutive user messages. It tidies the <strong>live messages in place</strong> right before sending (<span class="mono">messages[:] = merged</span>, so persistence / SessionDB see the repair), doing only <strong>minimal surgical</strong> cleanup and <strong>never aggressively rebuilding context</strong> — avoiding needless history rewrites that would shatter the cache (ch.6).</p>
<p>Why is the role-alternation invariant so <strong>non-negotiable</strong>? Two reasons stack. First, the <strong>protocol layer</strong>: OpenAI / OpenRouter / Anthropic all require user/tool to <strong>strictly alternate</strong> with assistant after the system message; the moment two same-role messages run in a row, or an orphan tool message appears that doesn't follow an assistant tool_call, most providers <strong>silently return an empty response</strong>, dragging the dialog into a futile empty-retry loop. Second, the <strong>cache layer</strong>: AGENTS.md mandates <span class="inline">never two same-role messages in a row; never a synthetic user message injected mid-loop</span> — injecting even one synthetic user message mid-loop conjures a token into the <strong>prefix currently being cached</strong>, and once the cache key shifts the whole history is forced to re-encode (ch.6). So "fix alternation" and "guard the cache" are really <strong>two faces of the same thing</strong>.</p>

<div class="figure">
<svg viewBox="0 0 680 256" role="img" aria-label="Strict role alternation: a legal sequence alternates, a violation puts two same-role messages in a row causing an empty response and empty-retry">
  <text x="20" y="24" font-size="13" font-weight="700" fill="var(--accent-ink)">✅ Legal · after system, user/tool strictly alternates with assistant</text>
  <g font-size="12" text-anchor="middle">
    <rect x="24"  y="42" width="104" height="46" rx="9" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="76"  y="71" fill="var(--ink)">system</text>
    <rect x="148" y="42" width="104" height="46" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="200" y="71" fill="var(--blue)">user</text>
    <rect x="272" y="42" width="104" height="46" rx="9" fill="var(--accent-soft)" stroke="var(--accent)"/>
    <text x="324" y="71" fill="var(--accent-ink)">assistant</text>
    <rect x="396" y="42" width="104" height="46" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="448" y="71" fill="var(--blue)">user</text>
    <rect x="520" y="42" width="104" height="46" rx="9" fill="var(--accent-soft)" stroke="var(--accent)"/>
    <text x="572" y="71" fill="var(--accent-ink)">assistant</text>
  </g>
  <g font-size="15" fill="var(--faint)" text-anchor="middle">
    <text x="138" y="70">→</text>
    <text x="262" y="70">→</text>
    <text x="386" y="70">→</text>
    <text x="510" y="70">→</text>
  </g>
  <text x="324" y="106" text-anchor="middle" font-size="11" fill="var(--muted)">adjacent messages never share a role → invariant holds, cache prefix stays stable</text>

  <text x="20" y="142" font-size="13" font-weight="700" fill="var(--red)">❌ Violation · two user messages in a row (synthetic msg mid-loop / multi-queue replay)</text>
  <g font-size="12" text-anchor="middle">
    <rect x="24"  y="158" width="104" height="46" rx="9" fill="var(--accent-soft)" stroke="var(--accent)"/>
    <text x="76"  y="187" fill="var(--accent-ink)">assistant</text>
    <rect x="148" y="158" width="104" height="46" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="200" y="187" fill="var(--blue)">user</text>
    <rect x="256" y="158" width="104" height="46" rx="9" fill="var(--red-soft)" stroke="var(--red)" stroke-width="2"/>
    <text x="308" y="187" fill="var(--red)">user</text>
    <text x="378" y="188" font-size="20" font-weight="700" fill="var(--red)">✕</text>
    <rect x="400" y="158" width="224" height="46" rx="9" fill="var(--red-soft)" stroke="var(--red)"/>
    <text x="512" y="187" fill="var(--red)">provider returns an empty response</text>
  </g>
  <text x="254" y="224" text-anchor="middle" font-size="10.5" fill="var(--red)">↑ two same-role in a row</text>
  <text x="512" y="224" text-anchor="middle" font-size="10.5" fill="var(--muted)">→ dragged into a futile empty-retry loop</text>
  <text x="20" y="248" font-size="10" fill="var(--faint)">AGENTS.md: never two same-role messages in a row · agent_runtime_helpers.py: empty-retry loop</text>
</svg>
<div class="fig-cap"><b>Strict role alternation</b>: after system, user/tool must alternate one-for-one with assistant (top, ✅). The moment two same-role messages run in a row — typically from a synthetic user message injected mid-loop, gateway multi-queue replay, or session resume — most providers <b>silently return an empty response</b>, dragging the dialog into a futile <b>empty-retry</b> loop (bottom, ❌). That is exactly why <span class="mono">repair_message_sequence_with_cursor</span> merges consecutive user messages and drops orphan tool messages before every API call.</div>
</div>
<p>Precisely for that reason, <span class="mono">repair_message_sequence_with_cursor</span> does only <strong>minimal surgery</strong> — dropping orphan tool messages whose <span class="mono">tool_call_id</span> matches no preceding call, merging consecutive user messages into one — and <strong>never aggressively rebuilds context</strong>, deliberately preserving surviving messages' object identity so SessionDB's flush cursor doesn't slip. Where do these broken sequences come from? The docstring spells it out: gateway multi-queue replay, session resume, cron, and host-passed <span class="mono">conversation_history</span>. That clarifies the real intent behind several cross-chapter designs: cron spins up an <strong>independent session and doesn't mirror the main conversation</strong> (ch.21), the gateway <strong>routes control commands like <span class="mono">/stop</span>/<span class="mono">/approve</span> out of history</strong> (ch.18), and delegated subagents use an <strong>isolated context</strong> (ch.13) — all to keep foreign messages from contaminating the main conversation and breaking its alternation and cache.</p>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh to run "one set of messages across all backends"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  This chapter's five: the <strong>transport registry</strong> (<span class="mono">register/get_transport</span>) registers + dispatches, the <strong>four adapters</strong> (anthropic / codex_responses / gemini_native / bedrock) translate, <strong>build_api_kwargs</strong> builds outbound, <strong>conversation_loop's inbound normalize</strong> (normalize_response), and <strong>repair_message_sequence_with_cursor</strong> fixes alternation. Cross-chapter teamwork: the strict-alternation invariant <strong>serves prompt caching</strong> (ch.6 — history stays byte-stable, so the cache holds); reasoning's three fields land the reasoning trace <strong>into visible context</strong> to fight "reasoning tokens not persisted" (ch.3 G); "add a provider without touching the loop" embodies the <strong>narrow-waist philosophy</strong> (ch.4).
  <div class="collab-sub">② Data-flow timing</div>
  unified messages → repair fixes alternation → build_api_kwargs picks a transport by api_mode → adapter translates into each dialect → provider API → normalize_response normalizes back to a unified assistant message (with reasoning) → append → next turn. Outbound "translate out," inbound "translate back," and the core loop only ever sees the unified format.
  <div class="collab-sub">③ The key point</div>
  The core knows just <strong>one</strong> message format; every provider difference — auth, field names, reasoning shape, tool-schema dialect — is <strong>absorbed whole</strong> by the transport / adapter layer. So "support a new backend" collapses to "write an adapter + register a transport," with <strong>zero change to the core conversation loop</strong>.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>a unified abstraction + the strict role-alternation invariant</strong> — one set of messages, many backends; with alternation repaired before every API call. It treats two inherent LLM constraints (and cages one engineering fragility at the edge):
  <p style="margin:.5rem 0 0"><span class="badge constraint">E·brittle structured output</span> — function calling / tool schemas unify into OpenAI format, with each adapter translating into a dialect (xAI even strips schema keywords it rejects on the spot), caging the "structured output is dialect-sensitive" fragility in the edge layer;
  <span class="badge constraint">G·reasoning tokens not persisted</span> — <span class="mono">reasoning_details</span> replays verbatim across turns so the model can "keep thinking from last turn";
  <span class="badge constraint">narrow-waist · dialect isolation</span> — the unified format <strong>isolates</strong> provider differences so the core prompt needn't be rewritten per backend. The anti-pattern: <strong>leaking</strong> one provider's special fields or auth <strong>into the core loop</strong> — that's making the commander learn dialects, rewriting the core for every backend added.</p>
  <p style="margin:.5rem 0 0">Zoom in on <span class="badge constraint">E·brittle structured output</span>: a model's function-calling output is <strong>acutely sensitive</strong> to schema dialect — one missing field, one keyword it doesn't recognize, and the whole thing can collapse back into free text. Hermes's answer is "<strong>constrain with a unified schema, and on a miss let the model see the error and retry</strong>" — the core holds one OpenAI-format tool definition, and each adapter translates it into a dialect and strips the keywords the backend rejects on the spot, caging that fragility <strong>entirely in the edge layer</strong>. And this tool schema is <strong>sent verbatim on every single API call</strong> (AGENTS.md: every core tool pays the "shipped on every call" cost) — which is the root reason the core tool count must stay <strong>restrained</strong>.</p>
  <p style="margin:.5rem 0 0">"Sent every call" also imposes a hard rule on caching: since the schema is <strong>itself part of the cached prefix</strong>, <strong>swapping toolsets mid-conversation = changing the schema = changing the prefix = the cache is dead</strong> (ch.6). That's why Hermes insists on a stable in-session toolset, using <span class="mono">check_fn</span> to settle the available tools <strong>before the conversation starts</strong> rather than adding/removing them halfway. The anti-pattern to fear most is <strong>leaking</strong> one provider's special fields or auth <strong>into the core loop</strong> — that makes the standard-speech commander start learning dialects: every backend added forces a core change, and shatters the cache that should have kept hitting all along.</p>

<div class="figure">
<svg viewBox="0 0 680 252" role="img" aria-label="Tool schema is part of the cached prefix: resent verbatim every call, so swapping toolsets changes the prefix and kills the whole cache">
  <text x="20" y="24" font-size="13" font-weight="700" fill="var(--accent-ink)">✅ The tool schema is part of the cached prefix, resent verbatim every API call</text>
  <g font-size="11.5" text-anchor="middle">
    <rect x="20"  y="40" width="150" height="50" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="95"  y="70" fill="var(--ink)">system prompt</text>
    <rect x="170" y="40" width="220" height="50" rx="8" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
    <text x="280" y="65" fill="var(--accent-ink)">tool schema</text>
    <text x="280" y="81" font-size="10" fill="var(--accent-ink)">shipped on every API call</text>
    <rect x="390" y="40" width="150" height="50" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="465" y="70" fill="var(--ink)">history</text>
    <rect x="540" y="40" width="120" height="50" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="600" y="70" fill="var(--blue)">newest</text>
  </g>
  <path d="M20 98 L20 104 L540 104 L540 98" fill="none" stroke="var(--accent)" stroke-width="1.3"/>
  <text x="280" y="120" text-anchor="middle" font-size="11" fill="var(--muted)">↑ the cached prefix (byte-stable → billed at the cache-read price)</text>
  <text x="600" y="104" text-anchor="middle" font-size="10.5" fill="var(--muted)">full price</text>

  <text x="20" y="156" font-size="13" font-weight="700" fill="var(--red)">❌ Swap toolsets mid-conversation → schema changes → prefix changes → cache dead</text>
  <g font-size="11.5" text-anchor="middle">
    <rect x="20"  y="172" width="150" height="50" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="95"  y="202" fill="var(--ink)">system prompt</text>
    <rect x="170" y="172" width="220" height="50" rx="8" fill="var(--red-soft)" stroke="var(--red)" stroke-width="2"/>
    <text x="270" y="197" fill="var(--red)">tool schema changed</text>
    <text x="360" y="190" font-size="16" font-weight="700" fill="var(--red)">✕</text>
    <text x="280" y="213" font-size="10" fill="var(--red)">toolset swapped</text>
    <rect x="390" y="172" width="270" height="50" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
    <text x="525" y="196" fill="var(--red)">prefix changed → cache wholly invalid</text>
    <text x="525" y="212" font-size="10" fill="var(--red)">recomputed at full price from here (ch.6)</text>
  </g>
  <text x="20" y="244" font-size="10" fill="var(--faint)">AGENTS.md: never change toolsets mid-conversation · check_fn settles available tools before the session starts</text>
</svg>
<div class="fig-cap"><b>The tool schema is part of the cached prefix</b>: the single OpenAI-format tool schema the core holds is <b>sent verbatim on every API call</b>, so it is itself part of the cached prefix (top, ✅). Therefore "swap toolsets mid-conversation" = change the schema = change the prefix, and from that point the cache is <b>wholly invalid and recomputed at full price</b> (bottom, ❌, connecting ch.6). That is why Hermes insists on a stable in-session toolset, using <span class="mono">check_fn</span> to settle the available tools <b>before the conversation starts</b>.</div>
</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 462" role="img" aria-label="One Read my AGENTS.md message translated from unified messages into the real Anthropic request body, field by field">
  <text x="18" y="24" font-size="13" font-weight="700" fill="var(--accent-ink)">Example: Read my AGENTS.md - unified messages translated to a real Anthropic body</text>

  <rect x="18" y="36" width="644" height="74" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="30" y="55" font-size="10.5" font-weight="700" fill="var(--blue)">(1) unified entry (core sees only OpenAI messages + OpenAI tools)</text>
  <text x="30" y="75" font-size="9" font-family="monospace" fill="var(--ink)">messages:[{role:&quot;system&quot;,...}, {role:&quot;user&quot;, content:&quot;Read my AGENTS.md&quot;}]</text>
  <text x="30" y="90" font-size="9" font-family="monospace" fill="var(--ink)">tools:[{&quot;type&quot;:&quot;function&quot;,&quot;function&quot;:{&quot;name&quot;:&quot;read_file&quot;,&quot;parameters&quot;:{...}}}]</text>
  <text x="650" y="104" text-anchor="end" font-size="9" fill="var(--muted)">chat_completion_helpers.py</text>

  <text x="340" y="127" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--accent-ink)">(2) api_mode==&quot;anthropic_messages&quot; → build_api_kwargs dispatch · :559</text>
  <path d="M340 130 L340 134" stroke="var(--accent)" stroke-width="1.5"/>
  <path d="M336 132 L340 140 L344 132 Z" fill="var(--accent)"/>

  <rect x="18" y="144" width="644" height="130" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="30" y="163" font-size="10.5" font-weight="700" fill="var(--ink)">(3) adapter translation: OpenAI field → Anthropic field (red → blue)</text>

  <rect x="30" y="172" width="252" height="20" rx="4" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="40" y="186" font-size="9" fill="var(--red)">role:&quot;system&quot; message (inside messages)</text>
  <path d="M288 182 L306 182" stroke="var(--muted)" stroke-width="1.3"/>
  <path d="M302 178 L310 182 L302 186 Z" fill="var(--muted)"/>
  <rect x="316" y="172" width="252" height="20" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="326" y="186" font-size="9" fill="var(--blue)">lifted to top-level system param</text>
  <text x="650" y="186" text-anchor="end" font-size="9" fill="var(--faint)">:2465-2474</text>

  <rect x="30" y="197" width="252" height="20" rx="4" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="40" y="211" font-size="9" font-family="monospace" fill="var(--red)">function.parameters</text>
  <path d="M288 207 L306 207" stroke="var(--muted)" stroke-width="1.3"/>
  <path d="M302 203 L310 207 L302 211 Z" fill="var(--muted)"/>
  <rect x="316" y="197" width="252" height="20" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="326" y="211" font-size="9" font-family="monospace" fill="var(--blue)">input_schema</text>
  <text x="650" y="211" text-anchor="end" font-size="9" fill="var(--faint)">:1595-1600</text>

  <rect x="30" y="222" width="252" height="20" rx="4" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="40" y="236" font-size="9" font-family="monospace" fill="var(--red)">function.name</text>
  <path d="M288 232 L306 232" stroke="var(--muted)" stroke-width="1.3"/>
  <path d="M302 228 L310 232 L302 236 Z" fill="var(--muted)"/>
  <rect x="316" y="222" width="252" height="20" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="326" y="236" font-size="9" font-family="monospace" fill="var(--blue)">name</text>
  <text x="650" y="236" text-anchor="end" font-size="9" fill="var(--faint)">:1595-1600</text>

  <rect x="30" y="247" width="252" height="20" rx="4" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="40" y="261" font-size="9" fill="var(--red)">(missing) max_tokens</text>
  <path d="M288 257 L306 257" stroke="var(--muted)" stroke-width="1.3"/>
  <path d="M302 253 L310 257 L302 261 Z" fill="var(--muted)"/>
  <rect x="316" y="247" width="252" height="20" rx="4" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="326" y="261" font-size="9" fill="var(--blue)">add max_tokens (required by Anthropic)</text>
  <text x="650" y="261" text-anchor="end" font-size="9" fill="var(--faint)">:2465-2474</text>

  <rect x="18" y="282" width="644" height="78" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="30" y="301" font-size="10.5" font-weight="700" fill="var(--accent-ink)">(4) real outbound request body (Anthropic Messages API)</text>
  <text x="30" y="321" font-size="9" font-family="monospace" fill="var(--ink)">{&quot;model&quot;:&quot;claude-opus-4.7&quot;, &quot;messages&quot;:[...], &quot;max_tokens&quot;:...,</text>
  <text x="30" y="336" font-size="9" font-family="monospace" fill="var(--ink)"> &quot;system&quot;:[...], &quot;tools&quot;:[{&quot;name&quot;:&quot;read_file&quot;,&quot;input_schema&quot;:{...}}]}</text>
  <text x="650" y="354" text-anchor="end" font-size="9" fill="var(--muted)">anthropic_adapter.py:2465-2474</text>

  <rect x="18" y="370" width="314" height="82" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="30" y="389" font-size="10.5" font-weight="700" fill="var(--ink)">(5) normalize_response on the way in</text>
  <text x="30" y="409" font-size="9" fill="var(--muted)">Anthropic response → unified OpenAI-style message</text>
  <text x="30" y="425" font-size="9" fill="var(--muted)">content / tool_calls / usage realigned</text>
  <text x="30" y="445" font-size="9" fill="var(--muted)">the core loop never sees the dialect</text>

  <rect x="344" y="370" width="318" height="82" rx="8" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="356" y="389" font-size="10.5" font-weight="700" fill="var(--purple)">(6) three reasoning fields (cross-turn)</text>
  <text x="356" y="408" font-size="9" font-family="monospace" fill="var(--ink)">reasoning: kept internally · :888</text>
  <text x="356" y="423" font-size="9" font-family="monospace" fill="var(--ink)">reasoning_content: pad &quot; &quot; if missing · :911</text>
  <text x="356" y="438" font-size="9" font-family="monospace" fill="var(--ink)">reasoning_details: forwarded as-is · :938-940</text>
</svg>
<div class="fig-cap"><b>The real field-by-field diff for one outbound message</b>: unified OpenAI <span class="mono">messages</span> + tools, after the <span class="mono">api_mode==&quot;anthropic_messages&quot;</span> dispatch, are translated by the adapter - <span class="mono">role:&quot;system&quot;</span> lifted to top-level <span class="mono">system</span>, <span class="mono">function.parameters→input_schema</span>, <span class="mono">function.name→name</span>, plus the required <span class="mono">max_tokens</span> - into a real Anthropic body; <span class="mono">normalize_response</span> realigns the way back, and the three <span class="mono">reasoning</span> fields (including pad <span class="mono">&quot; &quot;</span> to avoid 400) keep continuity across turns.</div>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Unified messages</strong>: the core loop knows only OpenAI-style <span class="mono">messages</span>; provider differences are absorbed by transport + adapter.</li>
    <li><strong>Transport registry</strong>: <span class="mono">register/get_transport</span> lazy-discovers and dispatches by <span class="mono">api_mode</span>; a new backend needs only a registered transport + an adapter.</li>
    <li><strong>build_api_kwargs</strong>: four branches build outbound by <span class="mono">api_mode</span>; Bedrock talks boto3 directly, Codex uses /responses, all invisible to the loop.</li>
    <li><strong>Reasoning's three stores</strong>: <span class="mono">reasoning</span> kept internally, <span class="mono">reasoning_content</span> replayed in thinking mode (pad a space if missing to avoid 400), <span class="mono">reasoning_details</span> passed back verbatim across turns (constraint G).</li>
    <li><strong>Alternation repair</strong>: before every API call <span class="mono">repair_message_sequence_with_cursor</span> drops orphan tool messages and merges consecutive user messages; it repairs in place with minimal surgery and never aggressively rebuilds context (guarding the cache).</li>
  </ul>
</div>
""",
}

LESSON_08 = {
    "zh": r"""
<p class="lead">
工具是 agent「动手」的能力——读文件、跑终端、搜网页、调浏览器。本章讲清一个工具<strong>如何从一个 Python 文件变成模型能调用的能力</strong>：注册表自动发现、<span class="mono">check_fn</span> 服务门控、按 toolset 过滤组装 schema、统一 JSON 返回 + 错误净化、以及 <span class="mono">execute_code</span> 退还预算。还要回答一个贯穿全书的问题——<strong>为什么每加一个核心工具都要如此谨慎</strong>：因为<strong>每个工具的 schema，每一次 API 调用都要发送一遍</strong>。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 机场安检 + 登机口</div>
  把工具集想成一座机场。每个航班（工具）要开放登机，得先过两道关：<strong>安检</strong>（<span class="mono">check_fn</span>）——没配齐前置条件（API key、playwright、docker）的航班<strong>根本不出现在航班表上</strong>；<strong>登机口分配</strong>（toolset 过滤）——只有这个平台启用的 toolset 里的工具才会摆上台面。乘客（模型）看到的航班表（tool schema），是<strong>每次都要重新打印发给塔台</strong>的——所以航班越多，每次通讯越贵。这就是为什么「再开一条核心航线」要慎之又慎。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 能力在边缘，核心窄腰</div>
  Hermes 的核心工具集<strong>刻意保持很窄</strong>（第 4 章的「窄腰」）。原因很硬核：每个工具的 JSON schema 都会<strong>随每一次 API 调用一起发出去</strong>——工具越多，固定开销越高，还会挤占模型注意力。所以新能力的优先级是「<strong>Footprint Ladder</strong>」：扩展现有 &gt; CLI 命令 + 技能 &gt; <span class="mono">check_fn</span> 门控工具 &gt; 插件 &gt; MCP server &gt; <strong>最后才是</strong>新核心工具。注册一个工具只要两件事：写 <span class="mono">tools/your_tool.py</span> 调 <span class="mono">registry.register(name, toolset, schema, handler, check_fn=...)</span>，再把工具名放进某个 toolset——但「该不该放进核心」永远是最贵的决定。
  <p>把这条阶梯逐级摊开就懂了「为什么核心工具排最后」：① <strong>扩展现有</strong>——零新增面，能力只是已有东西的一个变体；② <strong>CLI 命令 + 技能</strong>——凡是能用 shell 表达的配置 / 状态 / 基建，就让 agent 去跑 <span class="mono">hermes 子命令</span>，模型工具足迹为零（<span class="mono">hermes webhook</span> / <span class="mono">cron</span> / <span class="mono">tools</span>）；③ <strong>service-gated 工具</strong>——需要结构化参数返回、且只在配了前置条件时才出现；④ <strong>插件</strong>——第三方 / 小众，装进 <span class="mono">~/.hermes/plugins/</span> 运行时发现；⑤ <strong>MCP server（进 catalog）</strong>——真得做成工具但又非核心基础，挂到内置 MCP client 上；⑥ <strong>新核心工具</strong>——只有当能力「基础、几乎人人要、终端 + 文件够不着」才走到这一步。每往下一阶，都比上一阶多背一份<strong>永久</strong>的面，所以纪律是：永远挑「最靠上、还能正确解决问题」的那一阶。</p>
</div>

<div class="figure">
<svg viewBox="0 0 680 446" role="img" aria-label="Footprint Ladder 足迹阶梯：从低足迹到高足迹的六级，新核心工具排最后">
  <text x="20" y="24" font-size="13.5" font-weight="700" fill="var(--accent)">Footprint Ladder · 新能力放哪一层：选 footprint 最小、还能解决问题的那一级</text>
  <g>
    <rect x="40" y="346" width="342" height="46" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <circle cx="64" cy="369" r="13" fill="var(--blue)"/>
    <text x="64" y="373" text-anchor="middle" font-size="12" font-weight="700" fill="var(--bg)">1</text>
    <text x="86" y="366" font-size="12.5" font-weight="700" fill="var(--ink)">扩展现有代码</text>
    <text x="86" y="383" font-size="10.5" fill="var(--muted)">零新增表面 · 已有能力的一个变体</text>
  </g>
  <g>
    <rect x="66" y="290" width="342" height="46" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <circle cx="90" cy="313" r="13" fill="var(--blue)"/>
    <text x="90" y="317" text-anchor="middle" font-size="12" font-weight="700" fill="var(--bg)">2</text>
    <text x="112" y="310" font-size="12.5" font-weight="700" fill="var(--ink)">CLI 命令 + 技能</text>
    <text x="112" y="327" font-size="10.5" fill="var(--muted)">零 model-tool 足迹（hermes cron / webhook）</text>
  </g>
  <g>
    <rect x="92" y="234" width="342" height="46" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <circle cx="116" cy="257" r="13" fill="var(--blue)"/>
    <text x="116" y="261" text-anchor="middle" font-size="12" font-weight="700" fill="var(--bg)">3</text>
    <text x="138" y="254" font-size="12.5" font-weight="700" fill="var(--ink)">服务门控工具 check_fn</text>
    <text x="138" y="271" font-size="10.5" fill="var(--muted)">仅在配好前置条件时才出现</text>
  </g>
  <g>
    <rect x="118" y="178" width="342" height="46" rx="9" fill="var(--purple-soft)" stroke="var(--purple)"/>
    <circle cx="142" cy="201" r="13" fill="var(--purple)"/>
    <text x="142" y="205" text-anchor="middle" font-size="12" font-weight="700" fill="var(--bg)">4</text>
    <text x="164" y="198" font-size="12.5" font-weight="700" fill="var(--ink)">插件</text>
    <text x="164" y="215" font-size="10.5" fill="var(--muted)">~/.hermes/plugins · 运行时发现</text>
  </g>
  <g>
    <rect x="144" y="122" width="342" height="46" rx="9" fill="var(--purple-soft)" stroke="var(--purple)"/>
    <circle cx="168" cy="145" r="13" fill="var(--purple)"/>
    <text x="168" y="149" text-anchor="middle" font-size="12" font-weight="700" fill="var(--bg)">5</text>
    <text x="190" y="142" font-size="12.5" font-weight="700" fill="var(--ink)">MCP server（进 catalog）</text>
    <text x="190" y="159" font-size="10.5" fill="var(--muted)">挂内置 MCP client · 零核心 schema 足迹</text>
  </g>
  <g>
    <rect x="170" y="66" width="342" height="46" rx="9" fill="var(--red-soft)" stroke="var(--red)" stroke-width="2.5"/>
    <circle cx="194" cy="89" r="13" fill="var(--red)"/>
    <text x="194" y="93" text-anchor="middle" font-size="12" font-weight="700" fill="var(--bg)">6</text>
    <text x="216" y="86" font-size="12.5" font-weight="700" fill="var(--red)">新核心工具（最后手段）</text>
    <text x="216" y="103" font-size="10.5" fill="var(--muted)">基础、几乎人人要、终端+文件够不到</text>
  </g>
  <line x1="600" y1="392" x2="600" y2="74" stroke="var(--red)" stroke-width="2"/>
  <path d="M600 66 L594 80 L606 80 Z" fill="var(--red)"/>
  <text x="624" y="232" text-anchor="middle" font-size="11" font-weight="700" fill="var(--red)" transform="rotate(90 624 232)">footprint ↑ · 每次 API 调用都发 schema，越往上越贵</text>
  <text x="40" y="422" font-size="11" fill="var(--muted)">↓ 优先选最靠下、还能解决问题的一级（核心工具＝最后手段）</text>
</svg>
<div class="fig-cap"><b>Footprint Ladder 足迹阶梯</b>：六级从低足迹（①扩展现有代码）到高足迹（⑥新核心工具）。每个核心工具的 schema 都随<b>每一次 API 调用</b>发送，所以越往上越贵——纪律是「选能正确解决问题的、footprint <b>最小</b>的那一级」，新核心工具永远排最后。</div>
</div>

<h2>门控：check_fn 让工具「条件不满足就不出现」</h2>
<p>组装发给模型的 schema 列表时，注册表会对每个工具跑一遍它声明的 <span class="mono">check_fn</span>。返回 <span class="kw">False</span> 的工具<strong>直接被跳过、不进 schema</strong>——条件不满足时它的足迹是<strong>零</strong>：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/registry.py</span><span class="ln">337-384 · 简化</span></div>
  <pre><span class="kw">def</span> <span class="fn">get_definitions</span>(self, tool_names):
    result = []
    check_results = {}                                <span class="cm"># 同一遍组装内的 per-call 缓存</span>
    <span class="kw">for</span> name <span class="kw">in</span> <span class="fn">sorted</span>(tool_names):
        entry = entries_by_name.get(name)
        <span class="kw">if</span> entry.check_fn:                            <span class="cm"># 工具声明了前置条件</span>
            <span class="kw">if</span> entry.check_fn <span class="kw">not</span> <span class="kw">in</span> check_results:
                check_results[entry.check_fn] = _check_fn_cached(entry.check_fn)  <span class="cm"># 结果缓存 ~30s</span>
            <span class="kw">if</span> <span class="kw">not</span> check_results[entry.check_fn]:
                <span class="kw">continue</span>                            <span class="cm"># 条件不满足 → 不进 schema（零足迹）</span>
        schema_with_name = {**entry.schema, <span class="st">"name"</span>: entry.name}
        result.append({<span class="st">"type"</span>: <span class="st">"function"</span>, <span class="st">"function"</span>: schema_with_name})
    <span class="kw">return</span> result</pre>
</div>
<p>这里有两层巧思。其一，<span class="mono">check_fn</span> 的结果用 <span class="mono">_check_fn_cached</span> 缓存约 <strong>30 秒</strong>——因为像「探测 docker / 探测 playwright / 探测 API key」这种检查有成本，30 秒 TTL 让你 <span class="mono">hermes tools enable foo</span> 后近实时生效，又不必每次调用都重新探测。其二，<strong>门控让工具集对一个会话保持稳定</strong>：Home Assistant 的工具只在配了 token 时出现，否则连 schema 都不占——这正服务第 6 章的缓存铁律（工具 schema 也是前缀的一部分，<strong>会话中途绝不换 toolset</strong>）。更上一层，<span class="mono">get_tool_definitions</span>（<span class="mono">model_tools.py:276</span>）先按 <span class="mono">enabled/disabled toolsets</span> 过滤，且结果<strong>按 config.yaml 的 mtime+size 记忆化</strong>——配置不变就不重算。</p>

<p>这里藏着一个<strong>刻意的不对称</strong>：发现是自动的，接线是手动的。<span class="mono">tools/*.py</span> 里只要有顶层 <span class="mono">registry.register()</span>，就会被 <span class="mono">discover_builtin_tools</span> 自动 import 并登记 schema（<span class="mono">registry.py:57</span>）；可工具要真正<strong>暴露给模型</strong>，还得有人把它的名字<strong>手写</strong>进某个 toolset（<span class="mono">_HERMES_CORE_TOOLS</span> 或新建一个）。为什么不让它顺势自动上台？因为「进核心」是全书最贵的决定——每个核心工具的 schema 在<strong>每一次 API 调用</strong>都要随请求发一遍：工具越多越稀释模型注意力（撞第 2 章 <span class="badge constraint">A·中间遗失</span>），又把缓存前缀撑得更长（撞第 6 章）。把接线留成「<strong>人来拍板的一步</strong>」，正是给这道最贵的门加一把手动锁，逼你先问一句「这真该进核心吗」。</p>

<p>就算能力下沉到了边缘，Hermes 仍给「边缘的 token 账单」加了一道闸：<strong>Tool Search 渐进式披露</strong>（<span class="mono">model_tools.py:531</span>）。当 MCP + 插件这些<strong>非核心</strong>工具的可延迟面超过阈值（默认约上下文窗口的 10%）时，它们会被折叠到 <span class="mono">tool_search</span> / <span class="mono">tool_describe</span> / <span class="mono">tool_call</span> 三个桥接工具背后，用到时再展开；而 <span class="mono">_HERMES_CORE_TOOLS</span> 里的核心工具<strong>永不延迟</strong>。这把 <span class="mono">check_fn</span> 的「按需付费」推到极致：没配前置条件零足迹，配了但太多就懒加载。所以这条阶梯不止是写代码时的口诀，更是第 23 章插件 / MCP、第 16 章多后端、第 24 章安全边界的<strong>同一把决策尺子</strong>。</p>

<div class="figure">
<svg viewBox="0 0 680 322" role="img" aria-label="工具渐进式披露：核心工具与三个桥工具常驻，非核心 MCP 与插件工具超阈值即折叠到桥工具背后">
  <text x="20" y="22" font-size="13" font-weight="700" fill="var(--accent)">渐进式披露 · 每轮 API 调用发送的 schema 保持小而稳</text>
  <rect x="20" y="40" width="384" height="80" rx="9" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="36" y="64" font-size="12.5" font-weight="700" fill="var(--accent-ink)">核心工具 · _HERMES_CORE_TOOLS</text>
  <text x="36" y="84" font-size="10.5" fill="var(--accent-ink)">永不折叠 · 每轮 API 调用常驻</text>
  <text x="36" y="106" font-size="10.5" fill="var(--ink)">terminal · read_file · web_search · browser_navigate</text>
  <text x="420" y="36" font-size="10.5" fill="var(--muted)">+ 3 个桥工具（也常驻）</text>
  <g text-anchor="middle">
    <rect x="420" y="44" width="80" height="76" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="460" y="86" font-size="10" fill="var(--blue)">tool_search</text>
    <rect x="506" y="44" width="86" height="76" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="549" y="86" font-size="10" fill="var(--blue)">tool_describe</text>
    <rect x="598" y="44" width="64" height="76" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="630" y="86" font-size="10" fill="var(--blue)">tool_call</text>
  </g>
  <text x="20" y="150" font-size="10.5" fill="var(--muted)">触发：非核心可延迟面 &gt; ~10% 上下文窗口 → 折叠（model_tools.py:531）</text>
  <line x1="506" y1="120" x2="506" y2="176" stroke="var(--blue)" stroke-width="1.8"/>
  <path d="M506 120 L500 132 L512 132 Z" fill="var(--blue)"/>
  <path d="M506 176 L500 164 L512 164 Z" fill="var(--blue)"/>
  <text x="520" y="152" font-size="10.5" fill="var(--blue)">折叠 ⇅ 按需检索/展开</text>
  <rect x="20" y="176" width="642" height="106" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-dasharray="6 4"/>
  <text x="36" y="198" font-size="11" font-weight="700" fill="var(--blue)">折叠的非核心工具池 · 不进每轮 schema（MCP servers + 插件）</text>
  <g text-anchor="middle" font-size="10">
    <rect x="36"  y="210" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="92"  y="227" fill="var(--ink)">mcp:github</text>
    <rect x="164" y="210" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="220" y="227" fill="var(--ink)">mcp:notion</text>
    <rect x="292" y="210" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="348" y="227" fill="var(--ink)">mcp:slack</text>
    <rect x="420" y="210" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="476" y="227" fill="var(--ink)">mcp:linear</text>
    <rect x="548" y="210" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="604" y="227" fill="var(--ink)">plugin:spotify</text>
    <rect x="36"  y="244" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="92"  y="261" fill="var(--ink)">plugin:gmail</text>
    <rect x="164" y="244" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="220" y="261" fill="var(--ink)">mcp:fetch</text>
    <rect x="292" y="244" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="348" y="261" fill="var(--ink)">mcp:postgres</text>
    <rect x="420" y="244" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="476" y="261" fill="var(--ink)">plugin:home</text>
    <rect x="548" y="244" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="604" y="261" fill="var(--muted)">… + 数十个</text>
  </g>
</svg>
<div class="fig-cap"><b>Tool Search 渐进式披露</b>：随每次 API 调用发送的只有<b>核心工具 _HERMES_CORE_TOOLS（永不折叠）</b>＋ <span class="mono">tool_search / tool_describe / tool_call</span> 三个桥工具。当非核心的 MCP、插件工具<b>可延迟面</b>超过约<b>上下文窗口的 10%</b>，它们被折叠到桥工具背后、<b>不进每轮 schema</b>，模型用到时再按需检索展开。这把 <span class="mono">check_fn</span> 的「按需付费」推到极致。</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 460" role="img" aria-label="read_file 一次真实调用从注册到 schema、脏 JSON、coerce 矫正、dispatch 与 tool 消息的全过程">
  <text x="18" y="24" font-size="13" font-weight="700" fill="var(--accent-ink)">实例：read_file 一次真实调用 register → schema → coerce → dispatch</text>

  <rect x="18" y="36" width="644" height="64" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="30" y="55" font-size="10.5" font-weight="700" fill="var(--accent-ink)">① 注册（tools/file_tools.py:1757）</text>
  <text x="30" y="74" font-size="9" font-family="monospace" fill="var(--ink)">registry.register(name=&quot;read_file&quot;, toolset=&quot;file&quot;, schema=READ_FILE_SCHEMA,</text>
  <text x="30" y="88" font-size="9" font-family="monospace" fill="var(--ink)">  handler=_handle_read_file, check_fn=_check_file_reqs, emoji=&quot;📖&quot;, max_result_size_chars=100_000)</text>

  <rect x="18" y="108" width="644" height="84" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="30" y="127" font-size="10.5" font-weight="700" fill="var(--ink)">② READ_FILE_SCHEMA（tools/file_tools.py:1602-1614）</text>
  <text x="30" y="146" font-size="9" font-family="monospace" fill="var(--ink)">path:{type:&quot;string&quot;}</text>
  <text x="30" y="160" font-size="9" font-family="monospace" fill="var(--ink)">offset:{type:&quot;integer&quot;, default:1, minimum:1}</text>
  <text x="30" y="174" font-size="9" font-family="monospace" fill="var(--ink)">limit:{type:&quot;integer&quot;, default:500, maximum:2000}</text>
  <text x="650" y="146" text-anchor="end" font-size="9" font-family="monospace" fill="var(--purple)">required:[&quot;path&quot;]</text>

  <rect x="18" y="200" width="312" height="86" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="30" y="219" font-size="10.5" font-weight="700" fill="var(--blue)">③ 模型返回 tool_call（脏 JSON）</text>
  <text x="30" y="240" font-size="9" font-family="monospace" fill="var(--ink)">{&quot;path&quot;:&quot;AGENTS.md&quot;,</text>
  <text x="30" y="254" font-size="9" font-family="monospace" fill="var(--ink)"> &quot;offset&quot;:&quot;1&quot;, &quot;limit&quot;:&quot;500&quot;}</text>
  <text x="30" y="276" font-size="9" fill="var(--red)">offset / limit 是字符串 → 不合 schema</text>

  <path d="M330 243 L348 243" stroke="var(--accent)" stroke-width="1.5"/>
  <path d="M344 239 L352 243 L344 247 Z" fill="var(--accent)"/>

  <rect x="350" y="200" width="312" height="86" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="362" y="219" font-size="10.5" font-weight="700" fill="var(--accent-ink)">④ coerce_tool_args 按 schema 矫正</text>
  <text x="362" y="240" font-size="9" font-family="monospace" fill="var(--ink)">&quot;1&quot; → 1      (integer)</text>
  <text x="362" y="254" font-size="9" font-family="monospace" fill="var(--ink)">&quot;500&quot; → 500  (integer)</text>
  <text x="362" y="276" font-size="9" fill="var(--muted)">字符串安全转型；矫正失败保留原值 · model_tools.py:644</text>

  <rect x="18" y="300" width="644" height="82" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="30" y="319" font-size="10.5" font-weight="700" fill="var(--ink)">⑤ registry.dispatch：执行 handler，异常统一包成 error（tools/registry.py:390-416）</text>
  <rect x="30" y="330" width="300" height="40" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="40" y="348" font-size="9.5" font-weight="700" fill="var(--accent-ink)">成功</text>
  <text x="40" y="364" font-size="9" font-family="monospace" fill="var(--ink)">return handler(args, **kwargs) → JSON 字符串</text>
  <rect x="350" y="330" width="312" height="40" rx="6" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="360" y="348" font-size="9.5" font-weight="700" fill="var(--red)">异常</text>
  <text x="360" y="364" font-size="9" font-family="monospace" fill="var(--red)">{&quot;error&quot;: _sanitize_tool_error(...)}</text>

  <rect x="18" y="392" width="644" height="56" rx="8" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="30" y="411" font-size="10.5" font-weight="700" fill="var(--purple)">⑥ 把结果 append 成 tool 消息 + 预算判定</text>
  <text x="30" y="430" font-size="9" font-family="monospace" fill="var(--ink)">if _tc_names == {&quot;execute_code&quot;}: iteration_budget.refund()</text>
  <text x="30" y="444" font-size="9" fill="var(--muted)">本例只调 read_file → 严格相等不成立 → 不退预算（conversation_loop.py:4120-4122）</text>
</svg>
<div class="fig-cap"><b>单个工具一次调用的 JSON in→out</b>：<span class="mono">read_file</span> 在 <span class="mono">registry.register</span> 登记、<span class="mono">READ_FILE_SCHEMA</span> 声明 <span class="mono">offset</span> 默认 1 / <span class="mono">limit</span> 默认 500 上限 2000、<span class="mono">required:[&quot;path&quot;]</span>；模型回的「脏」JSON 里 <span class="mono">&quot;offset&quot;:&quot;1&quot;</span>、<span class="mono">&quot;limit&quot;:&quot;500&quot;</span> 是字符串，<span class="mono">coerce_tool_args</span> 按 schema 把 <span class="mono">&quot;1&quot;→1</span>、<span class="mono">&quot;500&quot;→500</span> 救场；<span class="mono">dispatch</span> 成功返回 JSON、异常包成 <span class="mono">{&quot;error&quot;:...}</span>；最后 append tool 消息——因为 <span class="mono">_tc_names</span> 严格等于 <span class="mono">{&quot;execute_code&quot;}</span> 才退预算，<span class="mono">read_file</span> <b>不退</b>。</div>
</div>

<p><span class="mono">check_fn</span> 门控之所以优雅，在于它把「按需付费」做成了<strong>默认安全</strong>。看 <span class="mono">_HERMES_CORE_TOOLS</span> 里那几组带门的工具就懂了：Home Assistant 的 <span class="mono">ha_*</span> 只在配了 <span class="mono">HASS_TOKEN</span> 时出现，<span class="mono">computer_use</span> 要装了 cua-driver 才上台，<span class="mono">kanban_*</span> 要么是被派成 kanban worker（<span class="mono">HERMES_KANBAN_TASK</span> 环境变量在）、要么是 profile 显式启用了 kanban toolset 才进 schema（注释见 <span class="mono">toolsets.py:64</span>）。这意味着：这些工具名虽然<strong>常驻</strong>在核心清单里，却<strong>不向没配前置条件的用户收一分 token 税</strong>——它们的成本只在「你真的用得上」时才发生。这就是「能力在边缘」的另一种写法：把昂贵的核心面，按每个用户的真实环境<strong>动态裁掉</strong>。换句话说，同一份核心清单，在没配智能家居的用户那里和配了的用户那里，发给模型的<strong>实际 schema 并不一样</strong>——门控让「窄」具体到了每个会话的环境指纹。</p>

<h2>分派：统一 JSON 返回 + 错误净化</h2>
<p>模型回来一个 tool_call，<span class="mono">dispatch</span> 按名字找到 handler 执行。所有 handler 都<strong>返回 JSON 字符串</strong>，而所有异常都被<strong>统一</strong>包成 <span class="mono">{"error": ...}</span>——而且要先<strong>净化</strong>：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/registry.py</span><span class="ln">390-416 · 简化</span></div>
  <pre><span class="kw">def</span> <span class="fn">dispatch</span>(self, name, args, **kwargs):
    entry = self.get_entry(name)
    <span class="kw">if</span> <span class="kw">not</span> entry:
        <span class="kw">return</span> json.dumps({<span class="st">"error"</span>: <span class="st">f"Unknown tool: {name}"</span>})
    <span class="kw">try</span>:
        <span class="kw">return</span> entry.handler(args, **kwargs)         <span class="cm"># handler 必返回 JSON string</span>
    <span class="kw">except</span> Exception <span class="kw">as</span> e:
        raw = <span class="st">f"Tool execution failed: {type(e).__name__}: {e}"</span>
        <span class="cm"># 经 _sanitize_tool_error 净化：异常串里的框架 token / CDATA /</span>
        <span class="cm"># 围栏不能作为结构噪声到达模型</span>
        sanitized = _sanitize_tool_error(raw)
        <span class="kw">return</span> json.dumps({<span class="st">"error"</span>: sanitized})</pre>
</div>
<p>这段的关键不是「捕获异常」，而是<strong>净化</strong>。工具的输出——无论成功结果还是报错串——对模型来说都是<strong>数据</strong>，不是指令。可异常消息里可能<strong>偶然</strong>带上模型框架的特殊 token、CDATA、代码围栏；若原样塞回去，模型可能把它们当成<strong>结构信号</strong>误解析。<span class="mono">_sanitize_tool_error</span> 把这些剥掉，让报错老老实实当数据。这正对应 <span class="badge constraint">D·指令=数据</span>——模型分不清「指令」和「数据」，所以喂回去的工具输出必须<strong>先消毒</strong>。</p>

<p>再往深一层看那条「handler <strong>必返回 JSON 字符串</strong>」的硬规矩（AGENTS.md：「All handlers MUST return a JSON string」）。它不是风格洁癖，而是<strong>统一契约</strong>：成功结果、报错、空值，全部以同一种「JSON 字符串 → tool 消息」的形状回到对话里，<span class="mono">dispatch</span> 才能对<strong>所有</strong>工具一视同仁地包裹异常、净化噪声，而不必为每个工具特判返回类型。配套的还有 <span class="mono">coerce_tool_args</span>（<span class="mono">model_tools.py:644</span>）——开源模型常把整数 <span class="mono">42</span> 写成字符串 <span class="st">"42"</span>、把单个 URL 漏写成数组，它会按 schema 声明的类型把参数<strong>悄悄纠回去</strong>，而不是直接抛一个让模型困惑的工具失败。统一的入参强制 + 统一的出参契约，一头一尾把脆弱的结构化调用（约束 E）夹稳。</p>

<h2>预算：execute_code 退还迭代</h2>
<p>第 5 章讲过迭代预算（parent 90 / subagent 50），每轮工具调用消耗一格。但有一个例外——<span class="mono">execute_code</span>（程序化工具调用）是 RPC 式的廉价调用，不该吃预算。所以本轮<strong>若且仅若所有 tool_call 都是 execute_code</strong>，就退还一格：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/conversation_loop.py</span><span class="ln">4117-4122 · 节选</span></div>
  <pre><span class="cm"># Refund the iteration if the ONLY tool(s) called were execute_code.</span>
_tc_names = {tc.function.name <span class="kw">for</span> tc <span class="kw">in</span> assistant_message.tool_calls}
<span class="kw">if</span> _tc_names == {<span class="st">"execute_code"</span>}:
    agent.iteration_budget.refund()</pre>
</div>
<p>注意那个 <span class="mono">== {"execute_code"}</span> 的严格相等：只要本轮<strong>混进</strong>了任何别的工具，就<strong>不退</strong>。这保证退还只发生在「纯程序化调用」的轮次，不会被人钻空子用 execute_code 夹带别的工具来无限续命。预算（第 5 章）、门控（本章）、缓存（第 6 章）三者合起来，才让一个能自由调工具的 agent <strong>既强大又不失控</strong>。</p>

<p>值得追问的是：为什么偏偏给 <span class="mono">execute_code</span> 开这个口子？因为它是<strong>程序化工具调用</strong>——模型一次写一段代码、在沙箱里批量调好几个工具，本质是把「多轮工具往返」压缩成「一轮 RPC」。若这种高效轮次照样吃掉一格 90 / 50 的迭代预算（第 5 章），那就等于<strong>惩罚了正确的省钱行为</strong>：模型越聪明地批处理，越快撞上预算墙。退还一格，是让预算只为「真正的思考往返」计费，而不为「一次打包多调用」重复扣账。而那个严格的 <span class="mono">== {"execute_code"}</span> 又堵死了滥用——本轮只要混进任何别的工具就<strong>不退</strong>，退还永远只奖励「纯批处理」的那种轮次，没人能拿它当无限续命的后门。这是一个小到容易被忽略、却极能体现「省钱不等于纵容」分寸感的设计。</p>

<h2>一个工具的一生</h2>
<div class="flow">
  <div class="node"><div class="nt">register</div><div class="nd">import 时登记 name/toolset/schema/handler/check_fn</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">toolset 过滤</div><div class="nd">get_tool_definitions 按 enabled 筛选</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">check_fn 门控</div><div class="nd">条件不满足就不进 schema</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node hl"><div class="nt">schema 随每次 API 调用发出</div><div class="nd">工具越多越贵</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">模型回 tool_call</div><div class="nd">dispatch 执行 + 错误净化</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">结果 append 为 tool 消息</div><div class="nd">进可见上下文，不改前缀</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">（若全是 execute_code）refund</div><div class="nd">退还一格预算</div></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「能力在边缘、核心窄腰」</div>
  <div class="collab-sub">① 组件清单（★本章核心，其余跨章节配合）</div>
  本章五件：<strong>registry.register</strong>（自动发现注册）、<strong>get_definitions</strong>（check_fn 门控）、<strong>get_tool_definitions</strong>（toolset 过滤 + 记忆化）、<strong>dispatch</strong>（统一 JSON + 错误净化）、<strong>iteration_budget.refund</strong>（execute_code 退还）。跨章节配合：工具发现链承接<strong>窄腰</strong>（第 4 章 registry → toolset → get_tool_definitions）；工具结果作为 <strong>tool 消息 append</strong> 进可见上下文、<strong>不改前缀</strong>（第 6 章缓存）；<span class="mono">check_fn</span> 门控让工具集<strong>会话内稳定</strong>＝不中途换 toolset（第 6 章铁律）；预算退还呼应<strong>迭代预算</strong>（第 5 章）；<span class="mono">delegate_task</span> 是一个「会生孩子」的特殊工具（第 13 章委派）。
  <div class="collab-sub">② 数据流时序</div>
  register（import 时）→ get_tool_definitions 按 enabled toolsets 过滤 → get_definitions 跑 check_fn 门控 + dynamic overrides → schema 随每次 API 调用发出 → 模型回 tool_call → handle_function_call → dispatch（异常净化）→ 返回 JSON string → 作为 tool 消息 append → （若本轮全是 execute_code）refund 预算。
  <div class="collab-sub">③ 关键点</div>
  每个工具 schema <strong>每次调用都发送</strong>——所以「加核心工具」成本最高、门槛最高。门控 + toolset 让「昂贵的核心面」保持窄，能力尽量<strong>下沉到边缘</strong>（CLI / skill / 插件 / MCP），这就是窄腰哲学在工具层的落地。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线：<strong>能力在边缘 + 核心窄腰 + 工具调用 append-only 不破缓存</strong>。它治三条 LLM 固有约束：
  <p style="margin:.5rem 0 0"><span class="badge constraint">A·中间遗失</span>——工具太多会挤占上下文与注意力，所以核心窄腰 + check_fn 门控，只让真正需要的工具上台；
  <span class="badge constraint">D·指令=数据</span>——工具结果是<strong>数据</strong>：dispatch 把异常串里的框架 token / CDATA / 围栏<strong>净化</strong>掉，别让模型误当成结构信号；
  <span class="badge constraint">E·结构化输出脆弱</span>——工具 schema 即 function calling，统一成 OpenAI 格式由各 adapter 翻译（第 7 章）。反模式：动不动就给核心加一个工具——每个都要在每次 API 调用里付费，正确做法是先爬一遍 Footprint Ladder。</p>
  <p style="margin:.5rem 0 0">把镜头拉远，本章真正的主角不是某个函数，而是 <strong>Footprint Ladder 这套决策纪律</strong>。它把「要不要加这个能力」从一道技术题，翻译成一道<strong>成本题</strong>：每加一阶核心面，都是给每一次 API 调用、每一个用户，<strong>永久</strong>地多收一份 token 税。所以默认答案永远是「先往阶梯上方爬」——先扩展现有，再 CLI + 技能，再 service-gated，再插件，再 MCP，新核心工具是最后手段。这正是第 4 章「窄腰」哲学在工具层的落地：核心保持窄，能力涌向边缘。它也是后面第 16 章多后端、第 23 章插件 / MCP、第 24 章安全边界要反复引用的同一把尺子——一个能力该落在哪一阶，先于「它代码写得好不好」。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>注册即发现</strong>：<span class="mono">tools/*.py</span> 里的 <span class="mono">registry.register(...)</span> 自动被导入；但「放进哪个 toolset」是手动、刻意的一步。</li>
    <li><strong>check_fn 门控</strong>：前置条件不满足的工具<strong>不进 schema</strong>（零足迹），结果缓存 ~30s；让工具集对一个会话稳定（守缓存）。</li>
    <li><strong>统一返回 + 错误净化</strong>：handler 必返回 JSON string，异常统一包成 <span class="mono">{"error":...}</span> 并经 <span class="mono">_sanitize_tool_error</span> 消毒（约束 D）。</li>
    <li><strong>execute_code 退还预算</strong>：仅当本轮 <span class="mono">_tc_names == {"execute_code"}</span> 才 refund；夹带别的工具就不退。</li>
    <li><strong>每个 schema 每次都发</strong>：加核心工具门槛最高；能力优先下沉边缘（Footprint Ladder：CLI/skill/插件/MCP &gt; 核心工具）。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">
Tools are how an agent "acts" — read files, run a terminal, search the web, drive a browser. This chapter shows how a tool <strong>goes from one Python file to a capability the model can call</strong>: registry auto-discovery, <span class="mono">check_fn</span> service gating, toolset-filtered schema assembly, a unified JSON return + error sanitizing, and <span class="mono">execute_code</span> refunding budget. It also answers a question that runs through the whole book — <strong>why adding a core tool is treated so carefully</strong>: because <strong>every tool's schema is sent on every single API call</strong>.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · airport security + gate assignment</div>
  Picture the toolset as an airport. For a flight (tool) to board, it clears two gates: <strong>security</strong> (<span class="mono">check_fn</span>) — a flight without its prerequisites (API key, playwright, docker) <strong>never even appears on the board</strong>; and <strong>gate assignment</strong> (toolset filtering) — only tools in this platform's enabled toolset make it onto the floor. The board the passenger (model) sees (the tool schema) is <strong>reprinted and sent to the tower every time</strong> — so the more flights, the costlier each transmission. That's why "opening another core route" is weighed so carefully.
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture · capability at the edges, a narrow-waist core</div>
  Hermes keeps its core toolset <strong>deliberately narrow</strong> (ch.4's "narrow waist"). The reason is hard: every tool's JSON schema <strong>ships with every API call</strong> — more tools mean higher fixed overhead and more crowded attention. So new capability follows the "<strong>Footprint Ladder</strong>": extend existing &gt; CLI command + skill &gt; <span class="mono">check_fn</span>-gated tool &gt; plugin &gt; MCP server &gt; <strong>only last</strong>, a new core tool. Registering a tool takes two things: write <span class="mono">tools/your_tool.py</span> calling <span class="mono">registry.register(name, toolset, schema, handler, check_fn=...)</span>, then put the tool name into a toolset — but "should it go in the core" is always the most expensive decision.
  <p>Lay the ladder out rung by rung and "why a core tool ranks last" becomes obvious: ① <strong>Extend existing code</strong> — zero new surface; the capability is just a variation of something already there. ② <strong>CLI command + skill</strong> — anything config/state/infra expressible as shell goes to the agent running <span class="mono">hermes &lt;subcommand&gt;</span>, with zero model-tool footprint (<span class="mono">hermes webhook</span> / <span class="mono">cron</span> / <span class="mono">tools</span>). ③ <strong>service-gated tool</strong> — needs structured params/returns AND only appears when a prerequisite is configured. ④ <strong>plugin</strong> — third-party/niche, dropped into <span class="mono">~/.hermes/plugins/</span> and discovered at runtime. ⑤ <strong>MCP server (in the catalog)</strong> — genuinely needs to be a tool but isn't core-fundamental, so hang it off the built-in MCP client. ⑥ <strong>new core tool</strong> — only when the capability is "fundamental, useful to nearly everyone, and unreachable via terminal + file." Each lower rung carries one more slice of <strong>permanent</strong> surface, so the discipline is: always pick the highest rung that still correctly solves the problem.</p>
</div>

<div class="figure">
<svg viewBox="0 0 680 446" role="img" aria-label="The Footprint Ladder: six rungs from lowest to highest footprint, with a new core tool ranking last">
  <text x="20" y="24" font-size="13.5" font-weight="700" fill="var(--accent)">Footprint Ladder · where new capability goes: the smallest-footprint rung that still solves it</text>
  <g>
    <rect x="40" y="346" width="350" height="46" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <circle cx="64" cy="369" r="13" fill="var(--blue)"/>
    <text x="64" y="373" text-anchor="middle" font-size="12" font-weight="700" fill="var(--bg)">1</text>
    <text x="86" y="366" font-size="12.5" font-weight="700" fill="var(--ink)">Extend existing code</text>
    <text x="86" y="383" font-size="10.5" fill="var(--muted)">Zero new surface · a variation of what exists</text>
  </g>
  <g>
    <rect x="66" y="290" width="350" height="46" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <circle cx="90" cy="313" r="13" fill="var(--blue)"/>
    <text x="90" y="317" text-anchor="middle" font-size="12" font-weight="700" fill="var(--bg)">2</text>
    <text x="112" y="310" font-size="12.5" font-weight="700" fill="var(--ink)">CLI command + skill</text>
    <text x="112" y="327" font-size="10.5" fill="var(--muted)">Zero model-tool footprint (hermes cron / webhook)</text>
  </g>
  <g>
    <rect x="92" y="234" width="350" height="46" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <circle cx="116" cy="257" r="13" fill="var(--blue)"/>
    <text x="116" y="261" text-anchor="middle" font-size="12" font-weight="700" fill="var(--bg)">3</text>
    <text x="138" y="254" font-size="12.5" font-weight="700" fill="var(--ink)">Service-gated tool check_fn</text>
    <text x="138" y="271" font-size="10.5" fill="var(--muted)">Appears only when a prerequisite is configured</text>
  </g>
  <g>
    <rect x="118" y="178" width="350" height="46" rx="9" fill="var(--purple-soft)" stroke="var(--purple)"/>
    <circle cx="142" cy="201" r="13" fill="var(--purple)"/>
    <text x="142" y="205" text-anchor="middle" font-size="12" font-weight="700" fill="var(--bg)">4</text>
    <text x="164" y="198" font-size="12.5" font-weight="700" fill="var(--ink)">Plugin</text>
    <text x="164" y="215" font-size="10.5" fill="var(--muted)">~/.hermes/plugins · discovered at runtime</text>
  </g>
  <g>
    <rect x="144" y="122" width="350" height="46" rx="9" fill="var(--purple-soft)" stroke="var(--purple)"/>
    <circle cx="168" cy="145" r="13" fill="var(--purple)"/>
    <text x="168" y="149" text-anchor="middle" font-size="12" font-weight="700" fill="var(--bg)">5</text>
    <text x="190" y="142" font-size="12.5" font-weight="700" fill="var(--ink)">MCP server (in the catalog)</text>
    <text x="190" y="159" font-size="10.5" fill="var(--muted)">On the built-in MCP client · zero core schema</text>
  </g>
  <g>
    <rect x="170" y="66" width="350" height="46" rx="9" fill="var(--red-soft)" stroke="var(--red)" stroke-width="2.5"/>
    <circle cx="194" cy="89" r="13" fill="var(--red)"/>
    <text x="194" y="93" text-anchor="middle" font-size="12" font-weight="700" fill="var(--bg)">6</text>
    <text x="216" y="86" font-size="12.5" font-weight="700" fill="var(--red)">New core tool (last resort)</text>
    <text x="216" y="103" font-size="10.5" fill="var(--muted)">Fundamental, near-universal, beyond terminal+file</text>
  </g>
  <line x1="608" y1="392" x2="608" y2="74" stroke="var(--red)" stroke-width="2"/>
  <path d="M608 66 L602 80 L614 80 Z" fill="var(--red)"/>
  <text x="632" y="232" text-anchor="middle" font-size="11" font-weight="700" fill="var(--red)" transform="rotate(90 632 232)">footprint ↑ · shipped on every API call — costlier the higher you go</text>
  <text x="40" y="422" font-size="11" fill="var(--muted)">↓ Prefer the lowest rung that still solves it (a core tool is the last resort)</text>
</svg>
<div class="fig-cap"><b>The Footprint Ladder</b>: six rungs from lowest footprint (① extend existing code) to highest (⑥ a new core tool). Every core tool's schema ships on <b>every single API call</b>, so higher = costlier — the discipline is "pick the <b>smallest-footprint</b> rung that still correctly solves the problem," and a new core tool always ranks last.</div>
</div>

<h2>Gating: check_fn makes a tool "vanish when prerequisites are unmet"</h2>
<p>When assembling the schema list sent to the model, the registry runs each tool's declared <span class="mono">check_fn</span>. A tool returning <span class="kw">False</span> is <strong>skipped outright — never entering the schema</strong>; when its condition is unmet, its footprint is <strong>zero</strong>:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/registry.py</span><span class="ln">337-384 · simplified</span></div>
  <pre><span class="kw">def</span> <span class="fn">get_definitions</span>(self, tool_names):
    result = []
    check_results = {}                                <span class="cm"># per-call cache within one assembly pass</span>
    <span class="kw">for</span> name <span class="kw">in</span> <span class="fn">sorted</span>(tool_names):
        entry = entries_by_name.get(name)
        <span class="kw">if</span> entry.check_fn:                            <span class="cm"># tool declared a prerequisite</span>
            <span class="kw">if</span> entry.check_fn <span class="kw">not</span> <span class="kw">in</span> check_results:
                check_results[entry.check_fn] = _check_fn_cached(entry.check_fn)  <span class="cm"># cached ~30s</span>
            <span class="kw">if</span> <span class="kw">not</span> check_results[entry.check_fn]:
                <span class="kw">continue</span>                            <span class="cm"># unmet -> not in schema (zero footprint)</span>
        schema_with_name = {**entry.schema, <span class="st">"name"</span>: entry.name}
        result.append({<span class="st">"type"</span>: <span class="st">"function"</span>, <span class="st">"function"</span>: schema_with_name})
    <span class="kw">return</span> result</pre>
</div>
<p>Two bits of cleverness. First, the <span class="mono">check_fn</span> result is cached by <span class="mono">_check_fn_cached</span> for about <strong>30 seconds</strong> — because checks like "probe docker / probe playwright / probe an API key" cost something, the 30s TTL lets <span class="mono">hermes tools enable foo</span> take effect in near-real-time without re-probing on every call. Second, <strong>gating keeps the toolset stable for a session</strong>: Home Assistant tools appear only when a token is configured, otherwise they don't even occupy a schema — which serves ch.6's caching rule (the tool schema is part of the prefix too, so <strong>never swap toolsets mid-session</strong>). One level up, <span class="mono">get_tool_definitions</span> (<span class="mono">model_tools.py:276</span>) first filters by <span class="mono">enabled/disabled toolsets</span>, and the result is <strong>memoized on config.yaml's mtime+size</strong> — no recompute if config is unchanged.</p>

<p>There's a <strong>deliberate asymmetry</strong> here: discovery is automatic, wiring is manual. Any top-level <span class="mono">registry.register()</span> in <span class="mono">tools/*.py</span> gets auto-imported and schema-registered by <span class="mono">discover_builtin_tools</span> (<span class="mono">registry.py:57</span>); but for the tool to actually be <strong>exposed to the model</strong>, someone must <strong>hand-write</strong> its name into a toolset (<span class="mono">_HERMES_CORE_TOOLS</span> or a new one). Why not let it auto-board too? Because "entering the core" is the most expensive decision in the book — every core tool's schema ships with <strong>every single API call</strong>: more tools dilute the model's attention (ch.2 <span class="badge constraint">A·lost-in-the-middle</span>) and stretch the cache prefix longer (ch.6). Leaving the wiring as "<strong>a step a human signs off on</strong>" puts a manual lock on the costliest door, forcing the question "does this really belong in the core?"</p>

<p>Even when capability sinks to the edges, Hermes still gates the "edge token bill": <strong>Tool Search progressive disclosure</strong> (<span class="mono">model_tools.py:531</span>). When the deferrable surface of <strong>non-core</strong> MCP + plugin tools exceeds a threshold (default ~10% of the context window), they're folded behind three bridge tools — <span class="mono">tool_search</span> / <span class="mono">tool_describe</span> / <span class="mono">tool_call</span> — and expanded on demand; the core tools in <span class="mono">_HERMES_CORE_TOOLS</span> are <strong>never deferred</strong>. This pushes <span class="mono">check_fn</span>'s "pay-as-you-go" to its limit: zero footprint without prerequisites, lazy-loaded when there are too many. So the ladder isn't just a coding mnemonic — it's the <strong>same decision yardstick</strong> for ch.23 (plugins/MCP), ch.16 (multi-backend), and ch.24 (security boundaries).</p>

<div class="figure">
<svg viewBox="0 0 680 322" role="img" aria-label="Tool Search progressive disclosure: core tools and three bridge tools stay resident; non-core MCP and plugin tools fold behind the bridge tools past a threshold">
  <text x="20" y="22" font-size="13" font-weight="700" fill="var(--accent)">Progressive disclosure · the per-call schema stays small and stable</text>
  <rect x="20" y="40" width="384" height="80" rx="9" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="36" y="64" font-size="12.5" font-weight="700" fill="var(--accent-ink)">Core tools · _HERMES_CORE_TOOLS</text>
  <text x="36" y="84" font-size="10.5" fill="var(--accent-ink)">Never deferred · resident on every API call</text>
  <text x="36" y="106" font-size="10.5" fill="var(--ink)">terminal · read_file · web_search · browser_navigate</text>
  <text x="420" y="36" font-size="10.5" fill="var(--muted)">+ 3 bridge tools (also resident)</text>
  <g text-anchor="middle">
    <rect x="420" y="44" width="80" height="76" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="460" y="86" font-size="10" fill="var(--blue)">tool_search</text>
    <rect x="506" y="44" width="86" height="76" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="549" y="86" font-size="10" fill="var(--blue)">tool_describe</text>
    <rect x="598" y="44" width="64" height="76" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="630" y="86" font-size="10" fill="var(--blue)">tool_call</text>
  </g>
  <text x="20" y="150" font-size="10.5" fill="var(--muted)">Trigger: non-core deferrable surface &gt; ~10% of context window → folded (model_tools.py:531)</text>
  <line x1="506" y1="120" x2="506" y2="176" stroke="var(--blue)" stroke-width="1.8"/>
  <path d="M506 120 L500 132 L512 132 Z" fill="var(--blue)"/>
  <path d="M506 176 L500 164 L512 164 Z" fill="var(--blue)"/>
  <text x="520" y="152" font-size="10.5" fill="var(--blue)">fold ⇅ retrieve on demand</text>
  <rect x="20" y="176" width="642" height="106" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-dasharray="6 4"/>
  <text x="36" y="198" font-size="11" font-weight="700" fill="var(--blue)">Folded non-core tool pool · not in the per-call schema (MCP servers + plugins)</text>
  <g text-anchor="middle" font-size="10">
    <rect x="36"  y="210" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="92"  y="227" fill="var(--ink)">mcp:github</text>
    <rect x="164" y="210" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="220" y="227" fill="var(--ink)">mcp:notion</text>
    <rect x="292" y="210" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="348" y="227" fill="var(--ink)">mcp:slack</text>
    <rect x="420" y="210" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="476" y="227" fill="var(--ink)">mcp:linear</text>
    <rect x="548" y="210" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="604" y="227" fill="var(--ink)">plugin:spotify</text>
    <rect x="36"  y="244" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="92"  y="261" fill="var(--ink)">plugin:gmail</text>
    <rect x="164" y="244" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="220" y="261" fill="var(--ink)">mcp:fetch</text>
    <rect x="292" y="244" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="348" y="261" fill="var(--ink)">mcp:postgres</text>
    <rect x="420" y="244" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="476" y="261" fill="var(--ink)">plugin:home</text>
    <rect x="548" y="244" width="112" height="26" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="604" y="261" fill="var(--muted)">… + dozens more</text>
  </g>
</svg>
<div class="fig-cap"><b>Tool Search progressive disclosure</b>: only the <b>core tools _HERMES_CORE_TOOLS (never deferred)</b> plus the three bridge tools <span class="mono">tool_search / tool_describe / tool_call</span> ship on every API call. When the <b>deferrable surface</b> of non-core MCP and plugin tools exceeds about <b>10% of the context window</b>, they are folded behind the bridge tools — <b>out of the per-call schema</b> — and retrieved/expanded on demand. This pushes <span class="mono">check_fn</span>'s "pay-as-you-go" to its limit.</div>
</div>

<div class="figure">
<svg viewBox="0 0 680 460" role="img" aria-label="One real read_file call from registration to schema, dirty JSON, coerce fix-up, dispatch and the tool message">
  <text x="18" y="24" font-size="13" font-weight="700" fill="var(--accent-ink)">Example: one real read_file call - register → schema → coerce → dispatch</text>

  <rect x="18" y="36" width="644" height="64" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="30" y="55" font-size="10.5" font-weight="700" fill="var(--accent-ink)">(1) register (tools/file_tools.py:1757)</text>
  <text x="30" y="74" font-size="9" font-family="monospace" fill="var(--ink)">registry.register(name=&quot;read_file&quot;, toolset=&quot;file&quot;, schema=READ_FILE_SCHEMA,</text>
  <text x="30" y="88" font-size="9" font-family="monospace" fill="var(--ink)">  handler=_handle_read_file, check_fn=_check_file_reqs, emoji=&quot;📖&quot;, max_result_size_chars=100_000)</text>

  <rect x="18" y="108" width="644" height="84" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="30" y="127" font-size="10.5" font-weight="700" fill="var(--ink)">(2) READ_FILE_SCHEMA (tools/file_tools.py:1602-1614)</text>
  <text x="30" y="146" font-size="9" font-family="monospace" fill="var(--ink)">path:{type:&quot;string&quot;}</text>
  <text x="30" y="160" font-size="9" font-family="monospace" fill="var(--ink)">offset:{type:&quot;integer&quot;, default:1, minimum:1}</text>
  <text x="30" y="174" font-size="9" font-family="monospace" fill="var(--ink)">limit:{type:&quot;integer&quot;, default:500, maximum:2000}</text>
  <text x="650" y="146" text-anchor="end" font-size="9" font-family="monospace" fill="var(--purple)">required:[&quot;path&quot;]</text>

  <rect x="18" y="200" width="312" height="86" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="30" y="219" font-size="10.5" font-weight="700" fill="var(--blue)">(3) model returns tool_call (dirty JSON)</text>
  <text x="30" y="240" font-size="9" font-family="monospace" fill="var(--ink)">{&quot;path&quot;:&quot;AGENTS.md&quot;,</text>
  <text x="30" y="254" font-size="9" font-family="monospace" fill="var(--ink)"> &quot;offset&quot;:&quot;1&quot;, &quot;limit&quot;:&quot;500&quot;}</text>
  <text x="30" y="276" font-size="9" fill="var(--red)">offset / limit are strings → off-schema</text>

  <path d="M330 243 L348 243" stroke="var(--accent)" stroke-width="1.5"/>
  <path d="M344 239 L352 243 L344 247 Z" fill="var(--accent)"/>

  <rect x="350" y="200" width="312" height="86" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="362" y="219" font-size="10.5" font-weight="700" fill="var(--accent-ink)">(4) coerce_tool_args fixes per schema</text>
  <text x="362" y="240" font-size="9" font-family="monospace" fill="var(--ink)">&quot;1&quot; → 1      (integer)</text>
  <text x="362" y="254" font-size="9" font-family="monospace" fill="var(--ink)">&quot;500&quot; → 500  (integer)</text>
  <text x="362" y="276" font-size="9" fill="var(--muted)">safe string cast; keeps original on failure · model_tools.py:644</text>

  <rect x="18" y="300" width="644" height="82" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="30" y="319" font-size="10.5" font-weight="700" fill="var(--ink)">(5) registry.dispatch: run handler, wrap exceptions as error (tools/registry.py:390-416)</text>
  <rect x="30" y="330" width="300" height="40" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="40" y="348" font-size="9.5" font-weight="700" fill="var(--accent-ink)">success</text>
  <text x="40" y="364" font-size="9" font-family="monospace" fill="var(--ink)">return handler(args, **kwargs) → JSON string</text>
  <rect x="350" y="330" width="312" height="40" rx="6" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="360" y="348" font-size="9.5" font-weight="700" fill="var(--red)">exception</text>
  <text x="360" y="364" font-size="9" font-family="monospace" fill="var(--red)">{&quot;error&quot;: _sanitize_tool_error(...)}</text>

  <rect x="18" y="392" width="644" height="56" rx="8" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="30" y="411" font-size="10.5" font-weight="700" fill="var(--purple)">(6) append the result as a tool message + budget check</text>
  <text x="30" y="430" font-size="9" font-family="monospace" fill="var(--ink)">if _tc_names == {&quot;execute_code&quot;}: iteration_budget.refund()</text>
  <text x="30" y="444" font-size="9" fill="var(--muted)">only read_file here → strict equality fails → no refund (conversation_loop.py:4120-4122)</text>
</svg>
<div class="fig-cap"><b>One tool, one call, JSON in to out</b>: <span class="mono">read_file</span> is registered via <span class="mono">registry.register</span>; <span class="mono">READ_FILE_SCHEMA</span> declares <span class="mono">offset</span> default 1 / <span class="mono">limit</span> default 500 max 2000 / <span class="mono">required:[&quot;path&quot;]</span>; the model's dirty JSON has <span class="mono">&quot;offset&quot;:&quot;1&quot;</span> and <span class="mono">&quot;limit&quot;:&quot;500&quot;</span> as strings, and <span class="mono">coerce_tool_args</span> saves the call by casting <span class="mono">&quot;1&quot;→1</span> and <span class="mono">&quot;500&quot;→500</span>; <span class="mono">dispatch</span> returns JSON on success or wraps an exception as <span class="mono">{&quot;error&quot;:...}</span>; finally the tool message is appended - and since the budget refunds only when <span class="mono">_tc_names</span> equals exactly <span class="mono">{&quot;execute_code&quot;}</span>, <span class="mono">read_file</span> is <b>not</b> refunded.</div>
</div>

<p>What makes <span class="mono">check_fn</span> gating elegant is that it makes "pay-as-you-go" the <strong>default-safe</strong> posture. Look at the gated groups in <span class="mono">_HERMES_CORE_TOOLS</span>: Home Assistant's <span class="mono">ha_*</span> appear only with <span class="mono">HASS_TOKEN</span> set, <span class="mono">computer_use</span> only when cua-driver is installed, and <span class="mono">kanban_*</span> only when the agent is spawned as a kanban worker (<span class="mono">HERMES_KANBAN_TASK</span> env set) or the profile explicitly enables the kanban toolset (comments at <span class="mono">toolsets.py:64</span>). So although these tool names <strong>live permanently</strong> in the core list, they <strong>charge no token tax to users who haven't configured their prerequisites</strong> — their cost only happens when you can actually use them. That's another way to write "capability at the edges": prune the expensive core surface <strong>dynamically</strong> per each user's real environment. In other words, the same core list yields a <strong>different actual schema</strong> for a user without smart-home set up versus one who has it — gating makes "narrow" specific to each session's environment fingerprint.</p>

<h2>Dispatch: a unified JSON return + error sanitizing</h2>
<p>The model returns a tool_call; <span class="mono">dispatch</span> finds the handler by name and runs it. Every handler <strong>returns a JSON string</strong>, and every exception is <strong>uniformly</strong> wrapped into <span class="mono">{"error": ...}</span> — after being <strong>sanitized</strong>:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/registry.py</span><span class="ln">390-416 · simplified</span></div>
  <pre><span class="kw">def</span> <span class="fn">dispatch</span>(self, name, args, **kwargs):
    entry = self.get_entry(name)
    <span class="kw">if</span> <span class="kw">not</span> entry:
        <span class="kw">return</span> json.dumps({<span class="st">"error"</span>: <span class="st">f"Unknown tool: {name}"</span>})
    <span class="kw">try</span>:
        <span class="kw">return</span> entry.handler(args, **kwargs)         <span class="cm"># handler must return a JSON string</span>
    <span class="kw">except</span> Exception <span class="kw">as</span> e:
        raw = <span class="st">f"Tool execution failed: {type(e).__name__}: {e}"</span>
        <span class="cm"># sanitize: framing tokens / CDATA / fences in the exception</span>
        <span class="cm"># string must not reach the model as structural noise</span>
        sanitized = _sanitize_tool_error(raw)
        <span class="kw">return</span> json.dumps({<span class="st">"error"</span>: sanitized})</pre>
</div>
<p>The point here isn't "catch the exception" — it's <strong>sanitizing</strong>. A tool's output — success result or error string alike — is <strong>data</strong> to the model, not instruction. Yet an exception message might <strong>accidentally</strong> carry the model framework's special tokens, CDATA, or code fences; fed back verbatim, the model could misparse them as <strong>structural signals</strong>. <span class="mono">_sanitize_tool_error</span> strips those so the error stays honest data. This maps to <span class="badge constraint">D·instr=data</span> — the model can't tell "instructions" from "data," so tool output fed back must be <strong>disinfected first</strong>.</p>

<p>Look one level deeper at the hard rule "handlers <strong>must return a JSON string</strong>" (AGENTS.md: "All handlers MUST return a JSON string"). It isn't stylistic fussiness — it's a <strong>uniform contract</strong>: success results, errors, and empty values all return to the conversation in the same "JSON string → tool message" shape, which is exactly what lets <span class="mono">dispatch</span> wrap exceptions and sanitize noise for <strong>every</strong> tool uniformly, without special-casing return types per tool. Its counterpart is <span class="mono">coerce_tool_args</span> (<span class="mono">model_tools.py:644</span>) — open-weight models often emit the integer <span class="mono">42</span> as the string <span class="st">"42"</span>, or a single URL where an array is expected, and it <strong>quietly fixes</strong> the args back to the schema-declared types instead of throwing a confusing tool failure. Uniform input coercion + a uniform output contract brace the brittle structured call (constraint E) at both ends.</p>

<h2>Budget: execute_code refunds an iteration</h2>
<p>Ch.5 covered the iteration budget (parent 90 / subagent 50), where each tool turn spends one slot. But there's an exception — <span class="mono">execute_code</span> (programmatic tool calling) is a cheap RPC-style call that shouldn't eat the budget. So <strong>if and only if every tool_call this turn is execute_code</strong>, one slot is refunded:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/conversation_loop.py</span><span class="ln">4117-4122 · excerpt</span></div>
  <pre><span class="cm"># Refund the iteration if the ONLY tool(s) called were execute_code.</span>
_tc_names = {tc.function.name <span class="kw">for</span> tc <span class="kw">in</span> assistant_message.tool_calls}
<span class="kw">if</span> _tc_names == {<span class="st">"execute_code"</span>}:
    agent.iteration_budget.refund()</pre>
</div>
<p>Note the strict equality <span class="mono">== {"execute_code"}</span>: if any other tool is <strong>mixed in</strong> this turn, there's <strong>no refund</strong>. This ensures refunds only happen on "purely programmatic" turns and can't be gamed by smuggling other tools inside execute_code to live forever. Budget (ch.5), gating (this chapter), and caching (ch.6) together let an agent that calls tools freely stay <strong>both powerful and under control</strong>.</p>

<p>Worth asking: why open this hatch for <span class="mono">execute_code</span> specifically? Because it's <strong>programmatic tool calling</strong> — the model writes a snippet once and batch-calls several tools in the sandbox, essentially compressing "many tool round-trips" into "one RPC." If such an efficient turn still ate one slot of the 90/50 iteration budget (ch.5), that would <strong>punish the correct cost-saving behavior</strong>: the smarter the model batches, the faster it hits the budget wall. Refunding a slot makes the budget charge only for "genuine thinking round-trips," not double-bill a "packed multi-call." And the strict <span class="mono">== {"execute_code"}</span> closes the abuse: mix in any other tool this turn and there's <strong>no refund</strong> — refunds only ever reward a "pure batch" turn, so nobody can use it as a back door to live forever. It's a small, easily-overlooked detail that captures the sense of proportion in "saving cost isn't condoning abuse."</p>

<h2>The life of a tool</h2>
<div class="flow">
  <div class="node"><div class="nt">register</div><div class="nd">at import: name/toolset/schema/handler/check_fn</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">toolset filter</div><div class="nd">get_tool_definitions filters by enabled</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">check_fn gate</div><div class="nd">unmet -> not in schema</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node hl"><div class="nt">schema ships on every API call</div><div class="nd">more tools, costlier</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">model returns tool_call</div><div class="nd">dispatch runs + error sanitize</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">result appended as tool message</div><div class="nd">into visible context, prefix unchanged</div></div>
  <div class="arrow">-&gt;</div>
  <div class="node"><div class="nt">(if all execute_code) refund</div><div class="nd">one budget slot back</div></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "capability at the edges, narrow-waist core"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  This chapter's five: <strong>registry.register</strong> (auto-discovery), <strong>get_definitions</strong> (check_fn gating), <strong>get_tool_definitions</strong> (toolset filter + memoization), <strong>dispatch</strong> (unified JSON + error sanitizing), <strong>iteration_budget.refund</strong> (execute_code refund). Cross-chapter teamwork: the discovery chain carries the <strong>narrow waist</strong> (ch.4: registry → toolset → get_tool_definitions); tool results <strong>append as tool messages</strong> into visible context and <strong>don't touch the prefix</strong> (ch.6 caching); <span class="mono">check_fn</span> gating keeps the toolset <strong>stable within a session</strong> = no mid-session toolset swap (ch.6 rule); the refund echoes the <strong>iteration budget</strong> (ch.5); <span class="mono">delegate_task</span> is a "child-spawning" special tool (ch.13 delegation).
  <div class="collab-sub">② Data-flow timing</div>
  register (at import) → get_tool_definitions filters by enabled toolsets → get_definitions runs check_fn gating + dynamic overrides → schema ships on every API call → model returns tool_call → handle_function_call → dispatch (exception sanitize) → returns a JSON string → appended as a tool message → (if all execute_code this turn) refund budget.
  <div class="collab-sub">③ The key point</div>
  Every tool schema <strong>ships on every call</strong> — so "adding a core tool" is the costliest, highest-bar move. Gating + toolsets keep the "expensive core surface" narrow, pushing capability <strong>to the edges</strong> (CLI / skill / plugin / MCP). That's the narrow-waist philosophy landing at the tool layer.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>capability at the edges + a narrow-waist core + append-only tool calls that don't break the cache</strong>. It treats three inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">A·lost-in-the-middle</span> — too many tools crowd context and attention, so a narrow core + check_fn gating lets only the truly needed tools onto the stage;
  <span class="badge constraint">D·instr=data</span> — tool results are <strong>data</strong>: dispatch <strong>sanitizes</strong> framing tokens / CDATA / fences out of exception strings so the model can't misread them as structural signals;
  <span class="badge constraint">E·brittle structured output</span> — a tool schema is function calling, unified into OpenAI format and translated by each adapter (ch.7). The anti-pattern: reflexively adding a tool to the core — each one is paid for on every API call; the right move is to climb the Footprint Ladder first.</p>
  <p style="margin:.5rem 0 0">Pull the camera back and this chapter's real protagonist isn't any one function — it's the <strong>Footprint Ladder as a decision discipline</strong>. It translates "should we add this capability" from a technical question into a <strong>cost question</strong>: every added rung of core surface levies one more token tax on every API call, for every user, <strong>permanently</strong>. So the default answer is always "climb up the ladder first" — extend existing, then CLI + skill, then service-gated, then plugin, then MCP; a new core tool is the last resort. This is ch.4's "narrow waist" landing at the tool layer: keep the core narrow, push capability to the edges. It's also the same yardstick ch.16 (multi-backend), ch.23 (plugins/MCP), and ch.24 (security boundaries) keep referencing — which rung a capability lands on comes before "how well its code is written."</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Register = discover</strong>: <span class="mono">registry.register(...)</span> in any <span class="mono">tools/*.py</span> is auto-imported; but "which toolset to put it in" is a manual, deliberate step.</li>
    <li><strong>check_fn gating</strong>: tools with unmet prerequisites <strong>don't enter the schema</strong> (zero footprint), results cached ~30s; keeps the toolset stable for a session (guards the cache).</li>
    <li><strong>Unified return + error sanitize</strong>: handlers must return a JSON string; exceptions are uniformly wrapped into <span class="mono">{"error":...}</span> and run through <span class="mono">_sanitize_tool_error</span> (constraint D).</li>
    <li><strong>execute_code refunds budget</strong>: only when <span class="mono">_tc_names == {"execute_code"}</span> this turn; smuggle another tool and there's no refund.</li>
    <li><strong>Every schema ships every time</strong>: adding a core tool has the highest bar; push capability to the edges first (Footprint Ladder: CLI/skill/plugin/MCP &gt; core tool).</li>
  </ul>
</div>
""",
}
