LESSON_26 = {
    "zh": r"""
<p class="lead">你做 agent 会踩的坑，几乎都是 LLM 七缺陷（A–G）在实践中的<strong>案发现场</strong>。这一章是 agent 工程的<strong>事故档案</strong>：把别人摔过的坑写成规章。</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 飞行事故档案 / 黑匣子</div>
  你坐的每一班飞机都<strong>极其安全</strong>，但这份安全不是凭空来的——民航那本厚厚的<strong>规章</strong>，几乎每一条背后都压着一次<strong>真实的空难</strong>：有人摔了，调查员翻遍<strong>黑匣子</strong>，把血的教训写成一行「今后必须……」。规章从来不是工程师拍脑袋定下的禁令，而是<strong>用事故倒推出来的</strong>。
  <p style="margin:.6rem 0 0">这一章就是 agent 工程的<strong>事故档案</strong>：后面每一条「坑」都不是抽象告诫，而是<strong>别人已经摔进去过</strong>的现场——缓存被击穿、自主循环跑飞、注入得手、JSON 解析崩掉。我们要做的，是像调查员读黑匣子那样，把每个坑<strong>还原到它撞的那条 LLM 约束</strong>上，再写成你能照做的规章。之所以用「事故档案」打比方，是想说清一件事：<strong>这些坑都已经有人替你踩过、代价也付过了，你要做的只是别再付第二遍。</strong></p>
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 坑的两个源头</div>
  把后面所有的坑摊开看，它们<strong>不是随机散落的一堆 bug</strong>，而是从<strong>两个源头</strong>里长出来的——
  <p style="margin:.6rem 0 0"><strong>① A–G 七缺陷在实践中现身。</strong>模型本就<strong>无状态、注意力两头重中间轻、分不清指令与数据、按概率续写</strong>（第 2–3 章的 A–G）：单看一次调用就已脆弱，把它串成自主体后更脆弱。后面每一个坑，本质都是这七条里的某一条在你的代码里<strong>显了形</strong>。</p>
  <p><strong>② 三条设计线（缓存神圣 / 自我进化 / 窄腰）的反面。</strong>这三条主线（第 25 章）讲的是「<strong>该怎么做</strong>」，而坑往往就是<strong>逆着它们走</strong>：会话中途改前缀 → 破<strong>缓存神圣</strong>；把学到的东西塞进系统提示而不外置成文件 → 破<strong>自我进化</strong>；什么能力都往核心里塞 → 破<strong>窄腰</strong>。</p>
  <p>所以避坑不靠死背一长串禁令，而靠一张<strong>能把坑映射回约束</strong>的地图——下面这张「坑地图」就是全章的总览。</p>
</div>

<p>把这两个源头画成一张总览——<strong>5 类坑</strong>，每一类都标出它主要<strong>撞</strong>在哪条 A–G 约束（或哪条设计线）上：</p>

<div class="figure">
<svg viewBox="0 0 680 400" role="img" aria-label="坑地图：5 类坑（上下文与缓存/自主循环/工具与扩展/安全/实践工程）分别撞在 A–G 七缺陷与缓存线上">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">坑地图 · 5 类坑 × A–G 约束（每类标它主要撞的约束）</text>
  <g>
    <rect x="14" y="48" width="206" height="54" rx="10" fill="var(--panel-2)" stroke="var(--accent)"/>
    <circle cx="40" cy="75" r="15" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>
    <text x="40" y="80" text-anchor="middle" font-size="14" font-weight="800" fill="var(--accent-ink)">A</text>
    <text x="64" y="72" font-size="12.5" font-weight="700" fill="var(--accent-ink)">上下文与缓存</text>
    <text x="64" y="91" font-size="11" fill="var(--muted)">改前缀 = 击穿缓存</text>
    <text x="232" y="80" text-anchor="middle" font-size="13" fill="var(--muted)">→</text>
    <rect x="248" y="61" width="78" height="28" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
    <text x="287" y="79" text-anchor="middle" font-size="11.5" fill="var(--accent-ink)">缓存神圣线</text>
    <rect x="336" y="61" width="67" height="28" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
    <text x="370" y="79" text-anchor="middle" font-size="11.5" fill="var(--accent-ink)">B·无状态</text>
  </g>
  <g>
    <rect x="14" y="118" width="206" height="54" rx="10" fill="var(--panel-2)" stroke="var(--blue)"/>
    <circle cx="40" cy="145" r="15" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
    <text x="40" y="150" text-anchor="middle" font-size="14" font-weight="800" fill="var(--blue)">B</text>
    <text x="64" y="142" font-size="12.5" font-weight="700" fill="var(--blue)">自主循环</text>
    <text x="64" y="161" font-size="11" fill="var(--muted)">循环越长越易跑飞</text>
    <text x="232" y="150" text-anchor="middle" font-size="13" fill="var(--muted)">→</text>
    <rect x="248" y="131" width="79" height="28" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="288" y="149" text-anchor="middle" font-size="11.5" fill="var(--blue)">F·误差累积</text>
    <rect x="337" y="131" width="55" height="28" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="364" y="149" text-anchor="middle" font-size="11.5" fill="var(--blue)">C·幻觉</text>
    <rect x="402" y="131" width="55" height="28" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="430" y="149" text-anchor="middle" font-size="11.5" fill="var(--blue)">G·运维</text>
  </g>
  <g>
    <rect x="14" y="188" width="206" height="54" rx="10" fill="var(--panel-2)" stroke="var(--purple)"/>
    <circle cx="40" cy="215" r="15" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="1.5"/>
    <text x="40" y="220" text-anchor="middle" font-size="14" font-weight="800" fill="var(--purple)">C</text>
    <text x="64" y="212" font-size="12.5" font-weight="700" fill="var(--purple)">工具与扩展</text>
    <text x="64" y="231" font-size="11" fill="var(--muted)">工具越多越稀释注意力</text>
    <text x="232" y="220" text-anchor="middle" font-size="13" fill="var(--muted)">→</text>
    <rect x="248" y="201" width="79" height="28" rx="8" fill="var(--purple-soft)" stroke="var(--purple)"/>
    <text x="288" y="219" text-anchor="middle" font-size="11.5" fill="var(--purple)">A·中间遗失</text>
    <rect x="337" y="201" width="115" height="28" rx="8" fill="var(--purple-soft)" stroke="var(--purple)"/>
    <text x="394" y="219" text-anchor="middle" font-size="11.5" fill="var(--purple)">E·结构化输出脆弱</text>
  </g>
  <g>
    <rect x="14" y="258" width="206" height="54" rx="10" fill="var(--panel-2)" stroke="var(--red)"/>
    <circle cx="40" cy="285" r="15" fill="var(--red-soft)" stroke="var(--red)" stroke-width="1.5"/>
    <text x="40" y="290" text-anchor="middle" font-size="14" font-weight="800" fill="var(--red)">D</text>
    <text x="64" y="282" font-size="12.5" font-weight="700" fill="var(--red)">安全</text>
    <text x="64" y="301" font-size="11" fill="var(--muted)">外部文本 = 潜在指令</text>
    <text x="232" y="290" text-anchor="middle" font-size="13" fill="var(--muted)">→</text>
    <rect x="248" y="271" width="86" height="28" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
    <text x="291" y="289" text-anchor="middle" font-size="11.5" fill="var(--red)">D·指令=数据</text>
  </g>
  <g>
    <rect x="14" y="328" width="206" height="54" rx="10" fill="var(--panel-2)" stroke="var(--amber)"/>
    <circle cx="40" cy="355" r="15" fill="var(--amber-soft)" stroke="var(--amber)" stroke-width="1.5"/>
    <text x="40" y="360" text-anchor="middle" font-size="14" font-weight="800" fill="var(--amber)">E</text>
    <text x="64" y="352" font-size="12.5" font-weight="700" fill="var(--amber)">实践工程</text>
    <text x="64" y="371" font-size="11" fill="var(--muted)">时区/编码/路径处处坑</text>
    <text x="232" y="360" text-anchor="middle" font-size="13" fill="var(--muted)">→</text>
    <rect x="248" y="341" width="55" height="28" rx="8" fill="var(--amber-soft)" stroke="var(--amber)"/>
    <text x="276" y="359" text-anchor="middle" font-size="11.5" fill="var(--amber)">G·运维</text>
  </g>
</svg>
<div class="fig-cap"><b>坑地图</b>：5 类坑都是 A–G 七缺陷在实践中的现身——看懂坑在哪条约束上，就知道怎么避。</div>
</div>

<h2>A 类 · 上下文与缓存</h2>
<p>第一类坑全部压在<strong>缓存神圣</strong>这条线上。它们的剧本如出一辙：你出于「让上下文更新鲜、更整齐」的好意去动了<strong>前缀</strong>或<strong>消息结构</strong>，却撞碎了「每个会话的 prompt 缓存逐字节不可侵犯」这条铁律——代价是成本翻倍、模型失忆、甚至偶发空响应。之所以把它排在第一类，是因为它<strong>最高频、也最贵</strong>：一次踩中，受伤的不是某一轮，而是整条会话往后的<strong>每一轮</strong>。四张卡分别对应缓存的四种破法——塞进前缀（A1）、中途改前缀（A2）、破坏消息结构（A3）、压缩抖动（A4），但根子都是第 25 章那条「缓存神圣」设计线的反面。先用四张陷阱卡速览，再逐个拆 <strong>❌ 反例 → ✅ 正例</strong>。</p>

<div class="pit">
  <div class="pit-h"><span class="pit-id">A1</span><span class="pit-title">把记忆 / 可变状态塞进 system prompt</span></div>
  <div class="pit-row"><span class="pit-k sym">症状</span><span class="pit-v">每轮 token 成本不降反升、agent 记不住新学的东西。</span></div>
  <div class="pit-row"><span class="pit-k root">根因</span><span class="pit-v"><strong>B·无状态</strong>的错误解法——前缀每轮变、缓存永不命中，且改 prompt 等于<strong>无法演化</strong>。</span></div>
  <div class="pit-row"><span class="pit-k fix">对策</span><span class="pit-v">状态外置到文件，system prompt 只放<strong>逐字节稳定的身份</strong>。</span></div>
  <div class="pit-row"><span class="pit-k ch">→ 章</span><span class="pit-v">ch6 / ch11</span></div>
</div>

<div class="pit">
  <div class="pit-h"><span class="pit-id">A2</span><span class="pit-title">会话中途改前缀（重排工具 / 插系统通知 / 刷新记忆）</span></div>
  <div class="pit-row"><span class="pit-k sym">症状</span><span class="pit-v">长对话越聊越贵、某轮起成本突然翻倍。</span></div>
  <div class="pit-row"><span class="pit-k root">根因</span><span class="pit-v">会话中途改了前缀，缓存从那点起<strong>全废</strong>（撞<strong>缓存神圣线</strong>）。</span></div>
  <div class="pit-row"><span class="pit-k fix">对策</span><span class="pit-v">绝不中途动前缀，<strong>只追加</strong>；要改只能在<strong>压缩边界</strong>。</span></div>
  <div class="pit-row"><span class="pit-k ch">→ 章</span><span class="pit-v">ch6 / ch15</span></div>
</div>

<div class="pit">
  <div class="pit-h"><span class="pit-id">A3</span><span class="pit-title">消息序列两个同角色相邻 / 中途注入合成 user</span></div>
  <div class="pit-row"><span class="pit-k sym">症状</span><span class="pit-v">模型偶发返回空、然后莫名重试。</span></div>
  <div class="pit-row"><span class="pit-k root">根因</span><span class="pit-v">两个同角色相邻 / 中途注入合成 user message → provider <strong>静默返回空</strong>、触发 empty-retry（<strong>E·结构化脆弱</strong> + 协议要求）。</span></div>
  <div class="pit-row"><span class="pit-k fix">对策</span><span class="pit-v">发送前跑一遍<strong>角色交替修复</strong>（删孤儿 tool、合并连续 user）。</span></div>
  <div class="pit-row"><span class="pit-k ch">→ 章</span><span class="pit-v">ch7</span></div>
</div>

<div class="pit">
  <div class="pit-h"><span class="pit-id">A4</span><span class="pit-title">压缩阈值设太低 / 每轮都压</span></div>
  <div class="pit-row"><span class="pit-k sym">症状</span><span class="pit-v">压缩频繁触发、缓存反复失效、体感变卡变贵。</span></div>
  <div class="pit-row"><span class="pit-k root">根因</span><span class="pit-v">阈值太低 / 每轮都压 → <strong>抖动</strong>，每次压缩都废一次缓存。</span></div>
  <div class="pit-row"><span class="pit-k fix">对策</span><span class="pit-v">阈值默认 <strong>~50%</strong>、连续 <strong>2 次无效压缩</strong>才停。</span></div>
  <div class="pit-row"><span class="pit-k ch">→ 章</span><span class="pit-v">ch15</span></div>
</div>

<h3>🔬 A1 · 记忆不进 system prompt，走 append-only 的对话流</h3>
<p>最自然的「记忆」写法，是每轮开头把「用户叫 X、偏好 Y、上次聊到 Z」连同当前时间戳拼进 system prompt——直觉上越新鲜越好。可 system prompt 恰恰是缓存前缀的<strong>最前一段</strong>：它每轮变一个字节，整条前缀就每轮 miss，于是「记忆越多 → 前缀越长 → 每轮全价重算越贵」；更糟的是你想「改身份」也得动这一段、再砸一次缓存——这正是 <strong>B·无状态</strong> 最典型的错误解法。</p>
<p>Hermes 反着来：system prompt 按稳定度切成 <span class="mono">stable / context / volatile</span> 三段，<strong>会话开始时整段构建一次</strong>、缓存在 <span class="mono">agent._cached_system_prompt</span> 上，之后 mid-session <strong>绝不重渲染</strong>。记忆 / 画像确实在 <span class="mono">volatile</span> 段（由 <span class="mono">tools/memory_tool.py:567</span> 的 <span class="mono">format_for_system_prompt()</span> 在 <span class="mono">agent/system_prompt.py:426-433</span> 注入），但取的是<strong>会话开始那一刻</strong>的快照、整会话不再变；新学到的东西不写回 system prompt，而是通过<strong>工具调用</strong>进入对话流（append-only），只往尾部追加、不动前缀。</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">❌ 反例 · 你可能会这么写</span></div><pre># 反例：每轮把最新记忆 / 画像 / 时间戳拼进 system prompt
def build_system_prompt(agent):
    mem = load_latest_memory()          # 每轮都不一样
    profile = load_user_profile()
    now = datetime.now().isoformat()    # 时间戳每轮都在变
    return (
        f"You are Hermes. user={profile.name}, "
        f"prefers={profile.style}, recent={mem.summary}, now={now}"
    )
# system 前缀逐字节都在变 → 每轮缓存 miss、越聊越贵；改身份还得再砸一次缓存</pre></div>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">✅ 正例 · agent/system_prompt.py:113</span></div><pre>def build_system_prompt_parts(agent: Any, system_message: Optional[str] = None) -&gt; Dict[str, str]:
    &quot;&quot;&quot;Assemble the system prompt as three ordered parts.

    Returns a dict with three keys:
      * ``stable``   — identity, tool guidance, skills prompt,
        environment hints, platform hints, model-family operational
        guidance.
      * ``context``  — context files (AGENTS.md, .cursorrules, etc.)
        and caller-supplied system_message.
      * ``volatile`` — memory snapshot, user profile, external
        memory provider block, timestamp line.

    Joined into a single string by :func:`build_system_prompt` and
    cached on ``agent._cached_system_prompt`` for the lifetime of the
    AIAgent.  Hermes never re-renders parts of this string mid-
    session — that's the only way to keep upstream prompt caches
    warm across turns.
    &quot;&quot;&quot;</pre></div>
<div class="figure">
<svg viewBox="0 0 680 400" role="img" aria-label="A1：system prompt 按稳定度分三层并在会话开始冻结，对比把可变记忆塞进前缀、每轮刷新">
  <text x="20" y="24" font-size="13.5" font-weight="700" fill="var(--ink)">A1 · system prompt 三层稳定度排序 vs 把可变记忆塞进前缀</text>
  <text x="20" y="52" font-size="12" font-weight="700" fill="var(--accent-ink)">✅ Hermes：按稳定度分三层，会话开始构建一次 → 缓存</text>
  <rect x="20" y="62" width="446" height="128" rx="10" fill="var(--panel-2)" stroke="var(--accent)"/>
  <rect x="32" y="74" width="422" height="32" rx="7" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="44" y="94" font-size="11.5" font-weight="700" fill="var(--accent-ink)">stable · 身份 / 工具 / 技能 / 环境</text>
  <text x="442" y="94" text-anchor="end" font-size="10.5" fill="var(--muted)">几乎不变</text>
  <rect x="32" y="110" width="422" height="32" rx="7" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="44" y="130" font-size="11.5" font-weight="700" fill="var(--blue)">context · 调用方消息 + 项目上下文</text>
  <text x="442" y="130" text-anchor="end" font-size="10.5" fill="var(--muted)">会话内固定</text>
  <rect x="32" y="146" width="422" height="32" rx="7" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="44" y="166" font-size="11.5" font-weight="700" fill="var(--purple)">volatile · 记忆快照 / 画像 / 时间戳</text>
  <text x="442" y="166" text-anchor="end" font-size="10.5" fill="var(--muted)">开始即冻结</text>
  <rect x="478" y="62" width="182" height="128" rx="10" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="569" y="100" text-anchor="middle" font-size="24">🔒</text>
  <text x="569" y="126" text-anchor="middle" font-size="10.5" fill="var(--accent-ink)">_cached_system_prompt</text>
  <text x="569" y="146" text-anchor="middle" font-size="10.5" fill="var(--muted)">mid-session 绝不重渲染</text>
  <text x="569" y="174" text-anchor="middle" font-size="12" font-weight="700" fill="var(--accent-ink)">✓ 每轮缓存命中</text>
  <line x1="20" y1="210" x2="660" y2="210" stroke="var(--line)"/>
  <text x="20" y="236" font-size="12" font-weight="700" fill="var(--red)">❌ 把可变记忆塞进 system prompt、每轮刷新</text>
  <rect x="20" y="246" width="446" height="92" rx="10" fill="var(--panel-2)" stroke="var(--red)"/>
  <rect x="32" y="258" width="422" height="32" rx="7" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="44" y="278" font-size="11" font-weight="700" fill="var(--red)">memory：用户叫 X · 偏好 Y · 上次聊到 Z · 时间戳</text>
  <text x="442" y="278" text-anchor="end" font-size="10.5" fill="var(--red)">每轮变</text>
  <rect x="32" y="294" width="422" height="32" rx="7" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="44" y="314" font-size="11" font-weight="700" fill="var(--accent-ink)">identity（被挤到可变内容之后）</text>
  <rect x="478" y="246" width="182" height="92" rx="10" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="569" y="282" text-anchor="middle" font-size="22" fill="var(--red)">↻</text>
  <text x="569" y="304" text-anchor="middle" font-size="10.5" fill="var(--red)">前缀逐字节在变</text>
  <text x="569" y="326" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--red)">✕ 缓存 miss · 越聊越贵</text>
  <text x="20" y="366" font-size="11" fill="var(--muted)">对策：volatile 也在会话开始冻结；新记忆经工具调用进入对话流（append-only），不动 system prompt。</text>
</svg>
<div class="fig-cap"><b>A1 · 三层冻结 vs 每轮刷新</b>：把易变记忆压进 <span class="mono">volatile</span> 段并在会话开始冻结、整段缓存，每轮命中；一旦把记忆塞进前缀、每轮刷新，前缀逐字节在变、缓存永远 miss。</div>
</div>

<h3>🔬 A2 · 只在 deepcopy 副本上打断点，绝不改原列表</h3>
<p>「顺手维护一下上下文」是 A2 的高发动作：插一条系统通知、按当前任务重排工具定义、把刚写的记忆刷新回历史中段——它们都改动了<strong>已被缓存的前缀</strong>。缓存是<strong>前缀缓存</strong>：从第一个变动的字节起，后面所有 token 的缓存断点<strong>全部作废、按全价重算</strong>，对话越靠后、被牵连重算的 token 越多，这一下可能贵到原来的好几倍。</p>
<p>Hermes 把这条纪律钉进代码：<span class="mono">apply_anthropic_cache_control</span> 第一步就 <span class="mono">copy.deepcopy(api_messages)</span>，所有 <span class="mono">cache_control</span> 断点只打在<strong>副本</strong>上，原始消息列表分毫不动——于是「打断点」这个动作本身永远不会污染被缓存的那份消息序列。真要重建，也只在<strong>压缩边界</strong>（第 15 章）一次性进行。</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">❌ 反例 · 你可能会这么写</span></div><pre># 反例：会话进行到一半，往历史中段插一条系统通知
messages.insert(3, {"role": "system", "content": "[配额仅剩 10%]"})
# 或：按当前任务重排 / 增删工具定义，顺手「整理」上下文
messages = reorder_tools_for_task(messages, current_task)
# 从插入 / 改动点起，后面每个 token 的缓存断点全部作废 → 全价重算</pre></div>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">✅ 正例 · agent/prompt_caching.py:64</span></div><pre>def apply_anthropic_cache_control(
    api_messages: List[Dict[str, Any]],
    cache_ttl: str = "5m",
    native_anthropic: bool = False,
) -&gt; List[Dict[str, Any]]:
    &quot;&quot;&quot;Apply system_and_3 caching strategy to messages for Anthropic models.

    Places up to 4 cache_control breakpoints: system prompt + last 3 non-system
    messages, all at the same TTL.

    Returns:
        Deep copy of messages with cache_control breakpoints injected.
    &quot;&quot;&quot;
    messages = copy.deepcopy(api_messages)
    if not messages:
        return messages</pre></div>
<div class="figure">
<svg viewBox="0 0 680 300" role="img" aria-label="A2：token 条带前段缓存命中，会话中途插入一条后，从插入点起整段按全价重算">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">A2 · 缓存击穿时序：中途改前缀，从那点起整段失效</text>
  <text x="20" y="56" font-size="12" font-weight="700" fill="var(--accent-ink)">✅ 前缀逐字节不变：长前缀按缓存读取价（≈ 原价 1/10）→ 整段成本 ↓</text>
  <rect x="20" y="68" width="470" height="44" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="255" y="95" text-anchor="middle" font-size="12" fill="var(--accent-ink)">system + 历史前缀（缓存读取价 ≈ 原价 1/10）</text>
  <rect x="496" y="68" width="144" height="44" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="568" y="95" text-anchor="middle" font-size="11.5" fill="var(--blue)">最近 3 条·全价</text>
  <text x="20" y="150" font-size="12" font-weight="700" fill="var(--red)">❌ 中途 insert 一条 → 从这里起缓存全废、按全价重算、成本 ↑↑</text>
  <rect x="20" y="162" width="176" height="44" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="108" y="189" text-anchor="middle" font-size="12" fill="var(--accent-ink)">命中</text>
  <line x1="206" y1="156" x2="206" y2="212" stroke="var(--red)" stroke-width="2" stroke-dasharray="5 4"/>
  <text x="206" y="228" text-anchor="middle" font-size="11" fill="var(--red)">✏ 中途 insert 一条</text>
  <rect x="216" y="162" width="424" height="44" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="428" y="189" text-anchor="middle" font-size="12" fill="var(--red)">从插入点起 → 整段按全价重算</text>
  <text x="20" y="262" font-size="11" fill="var(--muted)">对策：绝不中途动前缀，只往尾部追加；断点只打在 deepcopy 的副本上，要重建只在压缩边界。</text>
</svg>
<div class="fig-cap"><b>A2 · 缓存击穿时序</b>：前缀逐字节不变时，长前缀按缓存读取价（≈ 原价 1/10）计费；一旦中途 insert 一条，断点从那点起全废，后面整段按全价重算。</div>
</div>

<h3>🔬 A3 · 发送前强制角色交替</h3>
<p>provider（OpenAI / OpenRouter / Anthropic）都要求严格的角色交替：system 之后，user / tool 与 assistant 必须一来一回，不能两个 user 相邻、也不能出现没跟在「带 tool_calls 的 assistant」后面的 tool 结果。一旦违反，多数 provider <strong>不报错而是静默返回空</strong>，再触发一轮 empty-retry——表现就是「偶发空响应 + 莫名重试」，这是 <strong>E·结构化脆弱</strong>叠加协议硬要求的典型现场。</p>
<p>Hermes 在每次发请求前用 <span class="mono">repair_message_sequence</span> 兜底：删掉孤儿 tool 消息、合并连续的 user，把实时历史强行捋成合法交替序列（带游标的变体 <span class="mono">repair_message_sequence_with_cursor</span> 在 <span class="mono">:448</span>，供流式续写场景使用）。它跑在 API 调用的最后一刻，专门兜住网关多队列重放、会话恢复、cron、宿主直接传入的已损坏历史。</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">❌ 反例 · 你可能会这么写</span></div><pre># 反例：把两条 user 直接前后相邻塞进历史
messages = [
    {"role": "system", "content": sys_prompt},
    {"role": "user", "content": "先看看这个文件"},
    {"role": "user", "content": "顺便把测试也跑了"},   # 两个 user 相邻
]
# provider 期望严格交替 → 多数 provider 静默返回空 → 触发 empty-retry</pre></div>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">✅ 正例 · agent/agent_runtime_helpers.py:347</span></div><pre>def repair_message_sequence(agent, messages: List[Dict]) -&gt; int:
    &quot;&quot;&quot;Collapse malformed role-alternation left in the live history.

    Providers (OpenAI, OpenRouter, Anthropic) expect strict alternation:
    after the system message, user/tool alternates with assistant, with
    no two consecutive user messages and no tool-result that doesn't
    follow an assistant-with-tool_calls. Violations cause silent empty
    responses on most providers, which triggers the empty-retry loop.</pre></div>
<div class="figure">
<svg viewBox="0 0 680 300" role="img" aria-label="A3：两个 user 相邻导致空响应，对比 user 与 assistant 严格交替的合法序列">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">A3 · 消息序列：同角色相邻 → 空响应 vs 严格交替</text>
  <text x="20" y="54" font-size="12" font-weight="700" fill="var(--red)">❌ 两个 user 相邻</text>
  <rect x="20" y="66" width="128" height="44" rx="10" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="84" y="93" text-anchor="middle" font-size="11" fill="var(--blue)">user · 先看文件</text>
  <text x="158" y="93" text-anchor="middle" font-size="14" fill="var(--muted)">→</text>
  <rect x="172" y="66" width="128" height="44" rx="10" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="236" y="93" text-anchor="middle" font-size="11" fill="var(--red)">user · 再跑测试</text>
  <text x="310" y="93" text-anchor="middle" font-size="14" fill="var(--muted)">→</text>
  <rect x="324" y="66" width="150" height="44" rx="10" fill="var(--red-soft)" stroke="var(--red)" stroke-dasharray="5 4"/>
  <text x="399" y="93" text-anchor="middle" font-size="12" font-weight="700" fill="var(--red)">✕ 空响应</text>
  <text x="486" y="84" font-size="11" fill="var(--red)">provider 静默返回空</text>
  <text x="486" y="102" font-size="11" fill="var(--muted)">→ 触发 empty-retry</text>
  <line x1="20" y1="140" x2="660" y2="140" stroke="var(--line)"/>
  <text x="20" y="168" font-size="12" font-weight="700" fill="var(--accent-ink)">✅ 严格交替：user 与 assistant 一来一回</text>
  <rect x="20" y="180" width="116" height="44" rx="10" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="78" y="207" text-anchor="middle" font-size="11.5" fill="var(--blue)">user</text>
  <text x="146" y="207" text-anchor="middle" font-size="14" fill="var(--muted)">→</text>
  <rect x="158" y="180" width="116" height="44" rx="10" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="216" y="207" text-anchor="middle" font-size="11.5" fill="var(--accent-ink)">assistant</text>
  <text x="284" y="207" text-anchor="middle" font-size="14" fill="var(--muted)">→</text>
  <rect x="296" y="180" width="116" height="44" rx="10" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="354" y="207" text-anchor="middle" font-size="11.5" fill="var(--blue)">user</text>
  <text x="422" y="207" text-anchor="middle" font-size="14" fill="var(--muted)">→</text>
  <rect x="434" y="180" width="116" height="44" rx="10" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="492" y="207" text-anchor="middle" font-size="11.5" fill="var(--accent-ink)">assistant</text>
  <text x="560" y="207" font-size="11.5" font-weight="700" fill="var(--accent-ink)">✓ 交替成立</text>
  <text x="20" y="262" font-size="11" fill="var(--muted)">对策：发送前用 repair_message_sequence 兜底——删孤儿 tool、合并连续 user，强制合法交替。</text>
</svg>
<div class="fig-cap"><b>A3 · 角色交替</b>：两个 <span class="mono">user</span> 相邻，多数 provider 直接静默返回空、触发 empty-retry；严格 <span class="mono">user → assistant</span> 交替才是合法序列。</div>
</div>

<p>最后一张图收束 A 类：A4 的「压缩抖动」同样落在缓存神圣线上——阈值设太低会让压缩反复触顶，每压一次就废一次缓存，于是越压越卡、越压越贵。Hermes 的默认阈值压在约 <strong>50%</strong>，并且要求连续 <strong>2 次</strong>压缩都「没省下多少」才真正停手，用一点迟滞换前缀的长期保温——这也呼应第 15 章把压缩当作<strong>唯一</strong>允许重建前缀的边界。</p>
<div class="figure">
<svg viewBox="0 0 680 300" role="img" aria-label="A4：阈值太低导致压缩反复触顶、每次废一次缓存，对比阈值约50%加两次无效才停的平稳曲线">
  <text x="20" y="24" font-size="13.5" font-weight="700" fill="var(--ink)">A4 · 压缩阈值：太低 → 抖动击穿缓存 vs ~50% → 平稳</text>
  <text x="20" y="50" font-size="12" font-weight="700" fill="var(--red)">❌ 阈值太低 → 反复触顶、频繁压缩</text>
  <rect x="20" y="60" width="300" height="180" rx="10" fill="var(--panel-2)" stroke="var(--red)"/>
  <line x1="20" y1="88" x2="320" y2="88" stroke="var(--red)" stroke-width="1.5" stroke-dasharray="5 4"/>
  <text x="26" y="82" font-size="10.5" fill="var(--red)">阈值太低</text>
  <polyline points="28,230 80,92 86,170 140,92 146,170 200,92 206,170 260,92 266,170 312,150" fill="none" stroke="var(--red)" stroke-width="2"/>
  <text x="83" y="86" text-anchor="middle" font-size="12" font-weight="700" fill="var(--red)">✕</text>
  <text x="143" y="86" text-anchor="middle" font-size="12" font-weight="700" fill="var(--red)">✕</text>
  <text x="203" y="86" text-anchor="middle" font-size="12" font-weight="700" fill="var(--red)">✕</text>
  <text x="24" y="258" font-size="11" fill="var(--muted)">每次触顶压一次 → 废一次缓存、来回抖动</text>
  <text x="350" y="50" font-size="12" font-weight="700" fill="var(--accent-ink)">✅ 阈值 ~50% + 2 次无效才停 → 平稳</text>
  <rect x="360" y="60" width="300" height="180" rx="10" fill="var(--panel-2)" stroke="var(--accent)"/>
  <line x1="360" y1="150" x2="660" y2="150" stroke="var(--accent)" stroke-width="1.5" stroke-dasharray="5 4"/>
  <text x="366" y="144" font-size="10.5" fill="var(--accent-ink)">阈值 ~50%</text>
  <polyline points="368,230 470,152 478,186 560,152 568,176 650,150" fill="none" stroke="var(--accent)" stroke-width="2"/>
  <text x="566" y="130" text-anchor="middle" font-size="10.5" fill="var(--accent-ink)">连续 2 次无效 → 停</text>
  <text x="364" y="258" font-size="11" fill="var(--muted)">少压缩、缓存保温，体感平稳</text>
</svg>
<div class="fig-cap"><b>A4 · 压缩抖动 vs 平稳</b>：阈值太低 → 反复触顶、每次压缩废一次缓存、来回抖动；阈值 <strong>~50%</strong> 且连续 <strong>2 次无效压缩</strong>才停 → 少压缩、缓存保温、体感平稳。</div>
</div>
""",
    "en": r"""
<p class="lead">The pitfalls of building an agent are almost all <strong>crime scenes</strong> of the LLM's seven flaws (A–G) showing up in practice. This chapter is the <strong>accident file</strong> of agent engineering: turning pits others fell into rules.</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · aviation accident file / black box</div>
  Every flight you board is <strong>extraordinarily safe</strong> — but that safety wasn't free. Behind almost every line of civil-aviation <strong>regulation</strong> sits a <strong>real crash</strong>: someone went down, investigators combed the <strong>black box</strong>, and wrote the lesson in blood as a line that reads "from now on you must…". Rules were never bans an engineer dreamed up; they were <strong>reverse-engineered from accidents</strong>.
  <p style="margin:.6rem 0 0">This chapter is the <strong>accident file</strong> of agent engineering: every "pit" ahead isn't an abstract warning but a scene <strong>someone already fell into</strong> — a blown cache, an autonomy loop gone wild, a successful injection, a JSON parse that collapsed. Our job, like an investigator reading the black box, is to <strong>trace each pit back to the LLM constraint it hit</strong>, then write it up as a rule you can follow directly. The point of the "accident file" metaphor is simple: <strong>someone already paid the price for these pits — your only job is not to pay it twice.</strong></p>
</div>

<div class="card macro">
  <div class="tag">🌍 Macro · the two sources of pits</div>
  Spread out every pit that follows and they're <strong>not a random pile of bugs</strong> — they grow from <strong>two sources</strong>:
  <p style="margin:.6rem 0 0"><strong>① The seven flaws A–G surfacing in practice.</strong> The model is inherently <strong>stateless, heavy at the ends and light in the middle of its attention, unable to separate instructions from data, continuing by probability</strong> (A–G, ch.2–3): fragile on a single call, more fragile once strung into an autonomous agent. Every later pit is really one of these seven <strong>showing its face</strong> in your code.</p>
  <p><strong>② The flip side of the three design lines (sacred cache / self-evolution / narrow waist).</strong> Those three lines (ch.25) say "<strong>how to do it right</strong>"; pits are usually what happens when you <strong>go against them</strong>: edit the prefix mid-conversation → break the <strong>sacred cache</strong>; fold learnings into the system prompt instead of externalizing to files → break <strong>self-evolution</strong>; cram every capability into the core → break the <strong>narrow waist</strong>.</p>
  <p>So avoiding pits isn't about memorizing a long list of bans — it's about a map that <strong>maps each pit back to a constraint</strong>. The "pitfall map" below is that overview for the whole chapter.</p>
</div>

<p>Drawing those two sources as one overview — <strong>five pit classes</strong>, each tagged with the A–G constraint (or design line) it mainly <strong>hits</strong>:</p>

<div class="figure">
<svg viewBox="0 0 680 400" role="img" aria-label="Pitfall map: five pit classes (context and cache, autonomy loop, tools and extension, security, practical engineering) each hit A to G flaws">
  <text x="20" y="26" font-size="12.5" font-weight="700" fill="var(--ink)">Pitfall map · 5 pit classes × A–G constraints (each tagged with the constraints it mainly hits)</text>
  <g>
    <rect x="14" y="48" width="206" height="54" rx="10" fill="var(--panel-2)" stroke="var(--accent)"/>
    <circle cx="40" cy="75" r="15" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="1.5"/>
    <text x="40" y="80" text-anchor="middle" font-size="14" font-weight="800" fill="var(--accent-ink)">A</text>
    <text x="64" y="72" font-size="11.5" font-weight="700" fill="var(--accent-ink)">Context &amp; cache</text>
    <text x="64" y="91" font-size="11" fill="var(--muted)">edit prefix = cache miss</text>
    <text x="232" y="80" text-anchor="middle" font-size="13" fill="var(--muted)">→</text>
    <rect x="248" y="61" width="120" height="28" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
    <text x="308" y="78" text-anchor="middle" font-size="11.0" fill="var(--accent-ink)">sacred-cache line</text>
    <rect x="378" y="61" width="86" height="28" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
    <text x="421" y="78" text-anchor="middle" font-size="11.0" fill="var(--accent-ink)">B·stateless</text>
  </g>
  <g>
    <rect x="14" y="118" width="206" height="54" rx="10" fill="var(--panel-2)" stroke="var(--blue)"/>
    <circle cx="40" cy="145" r="15" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="1.5"/>
    <text x="40" y="150" text-anchor="middle" font-size="14" font-weight="800" fill="var(--blue)">B</text>
    <text x="64" y="142" font-size="11.5" font-weight="700" fill="var(--blue)">Autonomy loop</text>
    <text x="64" y="161" font-size="11" fill="var(--muted)">longer loop, more drift</text>
    <text x="232" y="150" text-anchor="middle" font-size="13" fill="var(--muted)">→</text>
    <rect x="248" y="131" width="136" height="28" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="316" y="148" text-anchor="middle" font-size="11.0" fill="var(--blue)">F·error-compounding</text>
    <rect x="394" y="131" width="111" height="28" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="450" y="148" text-anchor="middle" font-size="11.0" fill="var(--blue)">C·hallucination</text>
    <rect x="515" y="131" width="50" height="28" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
    <text x="540" y="148" text-anchor="middle" font-size="11.0" fill="var(--blue)">G·ops</text>
  </g>
  <g>
    <rect x="14" y="188" width="206" height="54" rx="10" fill="var(--panel-2)" stroke="var(--purple)"/>
    <circle cx="40" cy="215" r="15" fill="var(--purple-soft)" stroke="var(--purple)" stroke-width="1.5"/>
    <text x="40" y="220" text-anchor="middle" font-size="14" font-weight="800" fill="var(--purple)">C</text>
    <text x="64" y="212" font-size="11.5" font-weight="700" fill="var(--purple)">Tools &amp; extension</text>
    <text x="64" y="231" font-size="11" fill="var(--muted)">more tools, less focus</text>
    <text x="232" y="220" text-anchor="middle" font-size="13" fill="var(--muted)">→</text>
    <rect x="248" y="201" width="143" height="28" rx="8" fill="var(--purple-soft)" stroke="var(--purple)"/>
    <text x="320" y="218" text-anchor="middle" font-size="11.0" fill="var(--purple)">A·lost-in-the-middle</text>
    <rect x="401" y="201" width="136" height="28" rx="8" fill="var(--purple-soft)" stroke="var(--purple)"/>
    <text x="469" y="218" text-anchor="middle" font-size="11.0" fill="var(--purple)">E·structured-output</text>
  </g>
  <g>
    <rect x="14" y="258" width="206" height="54" rx="10" fill="var(--panel-2)" stroke="var(--red)"/>
    <circle cx="40" cy="285" r="15" fill="var(--red-soft)" stroke="var(--red)" stroke-width="1.5"/>
    <text x="40" y="290" text-anchor="middle" font-size="14" font-weight="800" fill="var(--red)">D</text>
    <text x="64" y="282" font-size="11.5" font-weight="700" fill="var(--red)">Security</text>
    <text x="64" y="301" font-size="11" fill="var(--muted)">ext. text = instructions</text>
    <text x="232" y="290" text-anchor="middle" font-size="13" fill="var(--muted)">→</text>
    <rect x="248" y="271" width="137" height="28" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
    <text x="316" y="288" text-anchor="middle" font-size="11.0" fill="var(--red)">D·instructions=data</text>
  </g>
  <g>
    <rect x="14" y="328" width="206" height="54" rx="10" fill="var(--panel-2)" stroke="var(--amber)"/>
    <circle cx="40" cy="355" r="15" fill="var(--amber-soft)" stroke="var(--amber)" stroke-width="1.5"/>
    <text x="40" y="360" text-anchor="middle" font-size="14" font-weight="800" fill="var(--amber)">E</text>
    <text x="64" y="352" font-size="11.5" font-weight="700" fill="var(--amber)">Practical eng.</text>
    <text x="64" y="371" font-size="11" fill="var(--muted)">tz / encoding / paths</text>
    <text x="232" y="360" text-anchor="middle" font-size="13" fill="var(--muted)">→</text>
    <rect x="248" y="341" width="50" height="28" rx="8" fill="var(--amber-soft)" stroke="var(--amber)"/>
    <text x="273" y="358" text-anchor="middle" font-size="11.0" fill="var(--amber)">G·ops</text>
  </g>
</svg>
<div class="fig-cap"><b>Pitfall map</b>: all five pit classes are the seven LLM flaws (A–G) surfacing in practice — see which constraint a pit sits on and you know how to avoid it.</div>
</div>

<h2>Category A · Context &amp; cache</h2>
<p>This first class of pits all rests on the <strong>sacred-cache</strong> line. The script is always the same: meaning well — "let me keep the context fresher and tidier" — you touch the <strong>prefix</strong> or the <strong>message structure</strong> and shatter the rule that "each conversation's prompt cache is byte-for-byte inviolable." The price is doubled cost, an amnesiac model, even sporadic empty responses. It comes first because it is the <strong>highest-frequency and the priciest</strong>: step on it once and the damage isn't one turn but <strong>every later turn</strong> of the whole conversation. The four cards map the four ways to break the cache — pack it into the prefix (A1), edit the prefix mid-session (A2), wreck the message structure (A3), thrash on compression (A4) — but each is the flip side of ch.25's "sacred cache" design line. Skim the four trap cards first, then we unpack each <strong>❌ wrong → ✅ right</strong>.</p>

<div class="pit">
  <div class="pit-h"><span class="pit-id">A1</span><span class="pit-title">Stuffing memory / mutable state into the system prompt</span></div>
  <div class="pit-row"><span class="pit-k sym">Symptom</span><span class="pit-v">Per-turn token cost rises instead of falling; the agent can't remember what it just learned.</span></div>
  <div class="pit-row"><span class="pit-k root">Root</span><span class="pit-v">The wrong fix for <strong>B·statelessness</strong> — the prefix changes every turn, the cache never hits, and editing the prompt means it <strong>can't evolve</strong>.</span></div>
  <div class="pit-row"><span class="pit-k fix">Fix</span><span class="pit-v">Externalize state to files; the system prompt holds only a <strong>byte-stable identity</strong>.</span></div>
  <div class="pit-row"><span class="pit-k ch">→ ch</span><span class="pit-v">ch6 / ch11</span></div>
</div>

<div class="pit">
  <div class="pit-h"><span class="pit-id">A2</span><span class="pit-title">Editing the prefix mid-session (reorder tools / inject a notice / refresh memory)</span></div>
  <div class="pit-row"><span class="pit-k sym">Symptom</span><span class="pit-v">Long chats get pricier; cost suddenly doubles from some turn on.</span></div>
  <div class="pit-row"><span class="pit-k root">Root</span><span class="pit-v">You edited the prefix mid-session, so the cache from that point on is <strong>all voided</strong> (hits the <strong>sacred-cache line</strong>).</span></div>
  <div class="pit-row"><span class="pit-k fix">Fix</span><span class="pit-v">Never touch the prefix mid-session — <strong>append only</strong>; rebuild only at the <strong>compression boundary</strong>.</span></div>
  <div class="pit-row"><span class="pit-k ch">→ ch</span><span class="pit-v">ch6 / ch15</span></div>
</div>

<div class="pit">
  <div class="pit-h"><span class="pit-id">A3</span><span class="pit-title">Two same-role messages adjacent / a synthetic user injected mid-stream</span></div>
  <div class="pit-row"><span class="pit-k sym">Symptom</span><span class="pit-v">The model occasionally returns empty, then inexplicably retries.</span></div>
  <div class="pit-row"><span class="pit-k root">Root</span><span class="pit-v">Two same-role messages adjacent / a synthetic user injected mid-stream → the provider <strong>returns empty silently</strong> and triggers empty-retry (<strong>E·brittle structure</strong> + protocol requirement).</span></div>
  <div class="pit-row"><span class="pit-k fix">Fix</span><span class="pit-v">Run a <strong>role-alternation repair</strong> before sending (drop orphan tools, merge consecutive users).</span></div>
  <div class="pit-row"><span class="pit-k ch">→ ch</span><span class="pit-v">ch7</span></div>
</div>

<div class="pit">
  <div class="pit-h"><span class="pit-id">A4</span><span class="pit-title">Compression threshold set too low / compacting every turn</span></div>
  <div class="pit-row"><span class="pit-k sym">Symptom</span><span class="pit-v">Compression fires constantly, the cache breaks again and again, everything feels slow and pricey.</span></div>
  <div class="pit-row"><span class="pit-k root">Root</span><span class="pit-v">Threshold too low / compacting every turn → <strong>thrashing</strong>, and each compaction voids the cache once.</span></div>
  <div class="pit-row"><span class="pit-k fix">Fix</span><span class="pit-v">Default the threshold to <strong>~50%</strong>; stop only after <strong>2 ineffective compactions</strong>.</span></div>
  <div class="pit-row"><span class="pit-k ch">→ ch</span><span class="pit-v">ch15</span></div>
</div>

<h3>🔬 A1 · Keep memory out of the system prompt; route it through the append-only stream</h3>
<p>The most natural way to do "memory" is to paste "the user is X, prefers Y, last talked about Z" plus the current timestamp into the system prompt at the top of every turn — surely fresher is better. But the system prompt is the very <strong>first segment</strong> of the cache prefix: change one byte each turn and the whole prefix misses every turn, so "more memory → longer prefix → pricier full recompute each turn." Worse, even editing the <em>identity</em> means touching this segment and breaking the cache again — exactly the classic wrong fix for <strong>B·statelessness</strong>.</p>
<p>Hermes does the opposite: the system prompt is cut into <span class="mono">stable / context / volatile</span> by stability, <strong>built once at session start</strong>, cached on <span class="mono">agent._cached_system_prompt</span>, and <strong>never re-rendered mid-session</strong>. Memory / profile do live in the <span class="mono">volatile</span> segment (injected by <span class="mono">format_for_system_prompt()</span> from <span class="mono">tools/memory_tool.py:567</span> at <span class="mono">agent/system_prompt.py:426-433</span>), but it's a snapshot taken <strong>the moment the session starts</strong> and never changes again for the rest of the session. New learnings aren't written back into the system prompt; they enter the conversation through <strong>tool calls</strong> (append-only), only appended at the tail, never touching the prefix.</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">❌ wrong · how you might write it</span></div><pre># Anti-pattern: pack the latest memory / profile / timestamp into the system prompt every turn
def build_system_prompt(agent):
    mem = load_latest_memory()          # differs every turn
    profile = load_user_profile()
    now = datetime.now().isoformat()    # timestamp changes every turn
    return (
        f"You are Hermes. user={profile.name}, "
        f"prefers={profile.style}, recent={mem.summary}, now={now}"
    )
# the system prefix changes byte-by-byte → cache miss every turn; editing identity re-breaks it</pre></div>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">✅ right · agent/system_prompt.py:113</span></div><pre>def build_system_prompt_parts(agent: Any, system_message: Optional[str] = None) -&gt; Dict[str, str]:
    &quot;&quot;&quot;Assemble the system prompt as three ordered parts.

    Returns a dict with three keys:
      * ``stable``   — identity, tool guidance, skills prompt,
        environment hints, platform hints, model-family operational
        guidance.
      * ``context``  — context files (AGENTS.md, .cursorrules, etc.)
        and caller-supplied system_message.
      * ``volatile`` — memory snapshot, user profile, external
        memory provider block, timestamp line.

    Joined into a single string by :func:`build_system_prompt` and
    cached on ``agent._cached_system_prompt`` for the lifetime of the
    AIAgent.  Hermes never re-renders parts of this string mid-
    session — that's the only way to keep upstream prompt caches
    warm across turns.
    &quot;&quot;&quot;</pre></div>
<div class="figure">
<svg viewBox="0 0 680 400" role="img" aria-label="A1: system prompt tiered by stability and frozen at session start, versus stuffing mutable memory into the prefix and refreshing every turn">
  <text x="20" y="24" font-size="13.5" font-weight="700" fill="var(--ink)">A1 · system prompt tiered by stability vs mutable memory in the prefix</text>
  <text x="20" y="52" font-size="12" font-weight="700" fill="var(--accent-ink)">✅ Hermes: three tiers by stability, built once at session start → cached</text>
  <rect x="20" y="62" width="446" height="128" rx="10" fill="var(--panel-2)" stroke="var(--accent)"/>
  <rect x="32" y="74" width="422" height="32" rx="7" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="44" y="94" font-size="11.5" font-weight="700" fill="var(--accent-ink)">stable · identity / tools / skills / env</text>
  <text x="442" y="94" text-anchor="end" font-size="10.5" fill="var(--muted)">rarely changes</text>
  <rect x="32" y="110" width="422" height="32" rx="7" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="44" y="130" font-size="11.5" font-weight="700" fill="var(--blue)">context · caller message + project context</text>
  <text x="442" y="130" text-anchor="end" font-size="10.5" fill="var(--muted)">fixed per session</text>
  <rect x="32" y="146" width="422" height="32" rx="7" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="44" y="166" font-size="11.5" font-weight="700" fill="var(--purple)">volatile · memory / profile / timestamp</text>
  <text x="442" y="166" text-anchor="end" font-size="10.5" fill="var(--muted)">frozen at start</text>
  <rect x="478" y="62" width="182" height="128" rx="10" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="569" y="100" text-anchor="middle" font-size="24">🔒</text>
  <text x="569" y="126" text-anchor="middle" font-size="10.5" fill="var(--accent-ink)">_cached_system_prompt</text>
  <text x="569" y="146" text-anchor="middle" font-size="10.5" fill="var(--muted)">never re-rendered mid-session</text>
  <text x="569" y="174" text-anchor="middle" font-size="12" font-weight="700" fill="var(--accent-ink)">✓ cache hit every turn</text>
  <line x1="20" y1="210" x2="660" y2="210" stroke="var(--line)"/>
  <text x="20" y="236" font-size="12" font-weight="700" fill="var(--red)">❌ stuff mutable memory into the system prompt, refresh each turn</text>
  <rect x="20" y="246" width="446" height="92" rx="10" fill="var(--panel-2)" stroke="var(--red)"/>
  <rect x="32" y="258" width="422" height="32" rx="7" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="44" y="278" font-size="11" font-weight="700" fill="var(--red)">memory: user=X · prefers=Y · last=Z · timestamp</text>
  <text x="442" y="278" text-anchor="end" font-size="10.5" fill="var(--red)">per turn</text>
  <rect x="32" y="294" width="422" height="32" rx="7" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="44" y="314" font-size="11" font-weight="700" fill="var(--accent-ink)">identity (pushed below the volatile stuff)</text>
  <rect x="478" y="246" width="182" height="92" rx="10" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="569" y="282" text-anchor="middle" font-size="22" fill="var(--red)">↻</text>
  <text x="569" y="304" text-anchor="middle" font-size="10.5" fill="var(--red)">prefix changes byte-wise</text>
  <text x="569" y="326" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--red)">✕ cache miss · pricier</text>
  <text x="20" y="366" font-size="11" fill="var(--muted)">Fix: freeze volatile at start too; new memory enters via tool calls (append-only), never the prefix.</text>
</svg>
<div class="fig-cap"><b>A1 · freeze three tiers vs refresh each turn</b>: push volatile memory into the <span class="mono">volatile</span> segment, freeze it at session start and cache the whole thing — hit every turn; stuff memory into the prefix and refresh each turn and the prefix changes byte-by-byte, missing forever.</div>
</div>

<h3>🔬 A2 · Stamp breakpoints only on a deepcopy, never mutate the original list</h3>
<p>"Just maintaining the context a bit" is what triggers A2: inject a system notice, reorder tool definitions for the current task, refresh the memory you just wrote back into the middle of the history — each one mutates the <strong>already-cached prefix</strong>. The cache is a <strong>prefix cache</strong>: from the first changed byte on, every later token's cache breakpoint is <strong>voided and recomputed at full price</strong>, and the deeper the conversation the more tokens get dragged into the recompute — sometimes several times the original cost.</p>
<p>Hermes nails this discipline into code: <span class="mono">apply_anthropic_cache_control</span> first does <span class="mono">copy.deepcopy(api_messages)</span>, and all <span class="mono">cache_control</span> breakpoints are stamped on the <strong>copy</strong> only, leaving the original message list untouched — so the act of "stamping breakpoints" can never pollute the cached message sequence. When a rebuild is truly needed, it happens once, only at the <strong>compression boundary</strong> (ch.15).</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">❌ wrong · how you might write it</span></div><pre># Anti-pattern: halfway through the session, splice a system notice into the middle
messages.insert(3, {"role": "system", "content": "[quota only 10% left]"})
# or: reorder / add / drop tool definitions for the current task, "tidying" the context
messages = reorder_tools_for_task(messages, current_task)
# from the insert / edit point on, every later token's cache breakpoint is voided → full-price recompute</pre></div>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">✅ right · agent/prompt_caching.py:64</span></div><pre>def apply_anthropic_cache_control(
    api_messages: List[Dict[str, Any]],
    cache_ttl: str = "5m",
    native_anthropic: bool = False,
) -&gt; List[Dict[str, Any]]:
    &quot;&quot;&quot;Apply system_and_3 caching strategy to messages for Anthropic models.

    Places up to 4 cache_control breakpoints: system prompt + last 3 non-system
    messages, all at the same TTL.

    Returns:
        Deep copy of messages with cache_control breakpoints injected.
    &quot;&quot;&quot;
    messages = copy.deepcopy(api_messages)
    if not messages:
        return messages</pre></div>
<div class="figure">
<svg viewBox="0 0 680 300" role="img" aria-label="A2: a token strip whose prefix is a cache hit; insert one message mid-stream and everything from that point recomputes at full price">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">A2 · cache punch-through: edit the prefix mid-session, all of it dies from there</text>
  <text x="20" y="56" font-size="12" font-weight="700" fill="var(--accent-ink)">✅ prefix byte-identical: long prefix at cache-read price (≈ 1/10) → cost ↓</text>
  <rect x="20" y="68" width="470" height="44" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="255" y="95" text-anchor="middle" font-size="12" fill="var(--accent-ink)">system + history prefix (cache-read price ≈ 1/10)</text>
  <rect x="496" y="68" width="144" height="44" rx="8" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="568" y="95" text-anchor="middle" font-size="11.5" fill="var(--blue)">last 3 · full price</text>
  <text x="20" y="150" font-size="12" font-weight="700" fill="var(--red)">❌ insert one mid-stream → cache dead from here, full-price recompute, cost ↑↑</text>
  <rect x="20" y="162" width="176" height="44" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="108" y="189" text-anchor="middle" font-size="12" fill="var(--accent-ink)">hit</text>
  <line x1="206" y1="156" x2="206" y2="212" stroke="var(--red)" stroke-width="2" stroke-dasharray="5 4"/>
  <text x="206" y="228" text-anchor="middle" font-size="11" fill="var(--red)">✏ insert one mid-session</text>
  <rect x="216" y="162" width="424" height="44" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="428" y="189" text-anchor="middle" font-size="12" fill="var(--red)">from the insert point → all recomputed at full price</text>
  <text x="20" y="262" font-size="11" fill="var(--muted)">Fix: never edit the prefix mid-session — append only; breakpoints on a deepcopy; rebuild only at compression.</text>
</svg>
<div class="fig-cap"><b>A2 · cache punch-through timeline</b>: when the prefix is byte-identical the long prefix bills at the cache-read price (≈ 1/10); insert one message mid-stream and breakpoints from that point are all voided, the rest recomputed at full price.</div>
</div>

<h3>🔬 A3 · Force role alternation before sending</h3>
<p>Providers (OpenAI / OpenRouter / Anthropic) all demand strict role alternation: after system, user / tool and assistant must take turns — no two adjacent user messages, and no tool result that doesn't follow an assistant-with-tool_calls. Break it and most providers <strong>don't error; they return empty silently</strong> and trigger another empty-retry — which shows up as "sporadic empty responses + mysterious retries," the textbook scene of <strong>E·brittle structure</strong> meeting a hard protocol requirement.</p>
<p>Hermes backstops every request with <span class="mono">repair_message_sequence</span> right before the call: drop orphan tool messages, merge consecutive users, and force the live history into a legal alternation (the cursor-aware variant <span class="mono">repair_message_sequence_with_cursor</span> is at <span class="mono">:448</span>, for streaming continuation). It runs at the very last moment before the API call, specifically to catch already-broken histories from gateway multi-queue replay, session resume, cron, or host code passing one in directly.</p>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">❌ wrong · how you might write it</span></div><pre># Anti-pattern: drop two user messages back-to-back into the history
messages = [
    {"role": "system", "content": sys_prompt},
    {"role": "user", "content": "look at this file"},
    {"role": "user", "content": "and run the tests too"},   # two user msgs adjacent
]
# providers expect strict alternation → most return empty silently → triggers empty-retry</pre></div>
<div class="codefile"><div class="cf-head"><span class="dot"></span><span class="path">✅ right · agent/agent_runtime_helpers.py:347</span></div><pre>def repair_message_sequence(agent, messages: List[Dict]) -&gt; int:
    &quot;&quot;&quot;Collapse malformed role-alternation left in the live history.

    Providers (OpenAI, OpenRouter, Anthropic) expect strict alternation:
    after the system message, user/tool alternates with assistant, with
    no two consecutive user messages and no tool-result that doesn't
    follow an assistant-with-tool_calls. Violations cause silent empty
    responses on most providers, which triggers the empty-retry loop.</pre></div>
<div class="figure">
<svg viewBox="0 0 680 300" role="img" aria-label="A3: two adjacent user messages cause an empty response, versus a legal sequence of strict user and assistant alternation">
  <text x="20" y="26" font-size="13.5" font-weight="700" fill="var(--ink)">A3 · message sequence: same role adjacent → empty vs strict alternation</text>
  <text x="20" y="54" font-size="12" font-weight="700" fill="var(--red)">❌ two user messages adjacent</text>
  <rect x="20" y="66" width="128" height="44" rx="10" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="84" y="93" text-anchor="middle" font-size="11" fill="var(--blue)">user · see file</text>
  <text x="158" y="93" text-anchor="middle" font-size="14" fill="var(--muted)">→</text>
  <rect x="172" y="66" width="128" height="44" rx="10" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="236" y="93" text-anchor="middle" font-size="11" fill="var(--red)">user · run tests</text>
  <text x="310" y="93" text-anchor="middle" font-size="14" fill="var(--muted)">→</text>
  <rect x="324" y="66" width="150" height="44" rx="10" fill="var(--red-soft)" stroke="var(--red)" stroke-dasharray="5 4"/>
  <text x="399" y="93" text-anchor="middle" font-size="12" font-weight="700" fill="var(--red)">✕ empty</text>
  <text x="486" y="84" font-size="11" fill="var(--red)">provider returns empty</text>
  <text x="486" y="102" font-size="11" fill="var(--muted)">→ empty-retry fires</text>
  <line x1="20" y1="140" x2="660" y2="140" stroke="var(--line)"/>
  <text x="20" y="168" font-size="12" font-weight="700" fill="var(--accent-ink)">✅ strict alternation: user and assistant take turns</text>
  <rect x="20" y="180" width="116" height="44" rx="10" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="78" y="207" text-anchor="middle" font-size="11.5" fill="var(--blue)">user</text>
  <text x="146" y="207" text-anchor="middle" font-size="14" fill="var(--muted)">→</text>
  <rect x="158" y="180" width="116" height="44" rx="10" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="216" y="207" text-anchor="middle" font-size="11.5" fill="var(--accent-ink)">assistant</text>
  <text x="284" y="207" text-anchor="middle" font-size="14" fill="var(--muted)">→</text>
  <rect x="296" y="180" width="116" height="44" rx="10" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="354" y="207" text-anchor="middle" font-size="11.5" fill="var(--blue)">user</text>
  <text x="422" y="207" text-anchor="middle" font-size="14" fill="var(--muted)">→</text>
  <rect x="434" y="180" width="116" height="44" rx="10" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="492" y="207" text-anchor="middle" font-size="11.5" fill="var(--accent-ink)">assistant</text>
  <text x="560" y="207" font-size="11.5" font-weight="700" fill="var(--accent-ink)">✓ alternation holds</text>
  <text x="20" y="262" font-size="11" fill="var(--muted)">Fix: repair_message_sequence before send — drop orphan tools, merge consecutive users, force alternation.</text>
</svg>
<div class="fig-cap"><b>A3 · role alternation</b>: two adjacent <span class="mono">user</span> messages make most providers return empty silently and trigger empty-retry; only strict <span class="mono">user → assistant</span> alternation is a legal sequence.</div>
</div>

<p>The last figure closes out class A: A4's "compression thrash" sits on the sacred-cache line too — set the threshold too low and compression keeps topping out, voiding the cache on every compaction, so the more you compact the slower and pricier it gets. Hermes pins the default threshold at about <strong>50%</strong> and only truly stops after <strong>2</strong> compactions in a row that "barely save anything," trading a little hysteresis for a long-warm prefix — which echoes ch.15 treating compression as the <strong>only</strong> boundary where rebuilding the prefix is allowed.</p>
<div class="figure">
<svg viewBox="0 0 680 300" role="img" aria-label="A4: a too-low threshold makes compression top out repeatedly and void the cache each time, versus a smooth curve at about 50 percent that stops after two ineffective passes">
  <text x="20" y="24" font-size="13.5" font-weight="700" fill="var(--ink)">A4 · compression threshold: too low → thrash &amp; punch cache vs ~50% → smooth</text>
  <text x="20" y="50" font-size="12" font-weight="700" fill="var(--red)">❌ too low → frequent top-outs &amp; compaction</text>
  <rect x="20" y="60" width="300" height="180" rx="10" fill="var(--panel-2)" stroke="var(--red)"/>
  <line x1="20" y1="88" x2="320" y2="88" stroke="var(--red)" stroke-width="1.5" stroke-dasharray="5 4"/>
  <text x="26" y="82" font-size="10.5" fill="var(--red)">too low</text>
  <polyline points="28,230 80,92 86,170 140,92 146,170 200,92 206,170 260,92 266,170 312,150" fill="none" stroke="var(--red)" stroke-width="2"/>
  <text x="83" y="86" text-anchor="middle" font-size="12" font-weight="700" fill="var(--red)">✕</text>
  <text x="143" y="86" text-anchor="middle" font-size="12" font-weight="700" fill="var(--red)">✕</text>
  <text x="203" y="86" text-anchor="middle" font-size="12" font-weight="700" fill="var(--red)">✕</text>
  <text x="24" y="258" font-size="11" fill="var(--muted)">each top-out = 1 compaction = 1 cache lost</text>
  <text x="350" y="50" font-size="12" font-weight="700" fill="var(--accent-ink)">✅ ~50% + stop after 2 no-ops → smooth</text>
  <rect x="360" y="60" width="300" height="180" rx="10" fill="var(--panel-2)" stroke="var(--accent)"/>
  <line x1="360" y1="150" x2="660" y2="150" stroke="var(--accent)" stroke-width="1.5" stroke-dasharray="5 4"/>
  <text x="366" y="144" font-size="10.5" fill="var(--accent-ink)">~50%</text>
  <polyline points="368,230 470,152 478,186 560,152 568,176 650,150" fill="none" stroke="var(--accent)" stroke-width="2"/>
  <text x="566" y="130" text-anchor="middle" font-size="10.5" fill="var(--accent-ink)">stop after 2 no-ops</text>
  <text x="364" y="258" font-size="11" fill="var(--muted)">few compactions, cache stays warm</text>
</svg>
<div class="fig-cap"><b>A4 · compression thrash vs smooth</b>: threshold too low → repeated top-outs, a cache voided per compaction, constant thrash; threshold <strong>~50%</strong> and stopping after <strong>2 ineffective compactions</strong> → fewer compactions, a warm cache, a smooth feel.</div>
</div>
""",
}
