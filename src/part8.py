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
""",
}
