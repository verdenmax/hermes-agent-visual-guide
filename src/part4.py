"""part4 — 第四部分 · 规模化与隔离：ch13 委派 / ch14 审查 / ch15 上下文压缩 / ch16 终端后端。

逐章 LESSON_13..16。codefile 标「节选/简化」者为可读性重排，真实性见 docs/superpowers/specs/chapters/。
"""

LESSON_13 = {
    "zh": r"""
<p class="lead">
当一个任务会产生<strong>大量中间过程</strong>（读几十个文件、跑一串命令），把它们全塞进主对话会<strong>淹没上下文</strong>。委派（<span class="mono">delegate_task</span>）的解法是：把子任务交给一个<strong>独立的子代理</strong>——它有自己的对话、自己的终端、自己的工具集，<strong>只把最终摘要带回</strong>父对话，中间的工具结果<strong>永远不进</strong>你的上下文窗口。本章是「规模化与隔离」的开篇。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 把活外包给独立小组</div>
  你是项目经理。一个调研任务要翻一百份资料，你<strong>不会</strong>把一百份资料都搬到自己桌上读（那会堆满桌面=淹没上下文）。你<strong>外包</strong>给一个独立小组：给他们一份<strong>自包含的任务书</strong>（子代理对你的对话历史一无所知），他们在<strong>自己的办公室</strong>（独立 context + 终端）干活，最后只交给你一份<strong>结论摘要</strong>。他们读过的一百份资料、试错的草稿，<strong>都不会出现在你桌上</strong>。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 上下文隔离，只带回摘要</div>
  委派的核心价值是<strong>上下文隔离</strong>。子代理拿到的是一份 <span class="mono">ephemeral_system_prompt</span>（只装 goal + context，<strong>不含</strong>父对话历史），并且 <span class="mono">skip_context_files</span> / <span class="mono">skip_memory</span>——它<strong>不读</strong>父的 AGENTS.md、不读共享 MEMORY.md。它在自己的对话里跑完，<strong>只有最终响应作为摘要返回父代理</strong>。于是父的上下文窗口<strong>始终干净</strong>：既不被中间工具结果淹没，也不被子任务的试错污染。这是对抗「上下文有限」的另一条路——第 15 章用压缩，本章用隔离。
</div>

<h2>隔离的核心：子代理拿到什么、不拿什么</h2>
<p>构造子 AIAgent 时，哪些<strong>隔离</strong>、哪些<strong>继承</strong>，是委派设计的关键：</p>
<p>为什么偏偏隔离这三样——对话历史、上下文文件、共享记忆？因为它们正是会<strong>淹没</strong>父窗口、又会<strong>击穿</strong>那段神圣缓存（第 6 章）的东西。子任务读几十个文件、试错几十轮，这些中间过程若回流父对话，关键信息会被挤进「被遗忘的中间」（约束 A）；而任何改动父的历史前缀，都让缓存前缀失配、整段重算，成本翻几倍。<span class="mono">skip_context_files</span> / <span class="mono">skip_memory</span> 不是图省事，而是<strong>刻意</strong>不让子代理把父的 AGENTS.md、共享 MEMORY.md 再加载一遍——子代理要的是一份<strong>自包含任务书</strong>，不是父的整套世界观。</p>
<p>反过来，为什么 <span class="mono">session_db</span> 和 provider / model 要<strong>继承</strong>？因为它们是「能跑起来」的运行时底座，而非会污染上下文的<strong>内容</strong>：共享会话 DB 让子代理的血缘靠 <span class="mono">parent_session_id</span> 串起来、事后可追溯，却不把父的对话搬进子窗口。而 <span class="mono">iteration_budget=None</span> 给每个子代理<strong>全新预算</strong>，是为了治约束 F（误差累积）——若一群兄弟子代理共用一份预算，一个跑飞就会饿死其余；独立预算让每个工人都有干净起点，失败也只失败它自己那一份。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/delegate_tool.py</span><span class="ln">1219-1250 · 简化</span></div>
  <pre>child = AIAgent(
    base_url=..., api_key=..., model=...,          <span class="cm"># 继承：provider/model 运行时</span>
    enabled_toolsets=child_toolsets,
    ephemeral_system_prompt=child_prompt,          <span class="cm"># 隔离：只装 goal+context，无父对话历史</span>
    platform=<span class="st">"subagent"</span>,
    skip_context_files=<span class="kw">True</span>,                     <span class="cm"># 隔离：不读 AGENTS.md/SOUL.md</span>
    skip_memory=<span class="kw">True</span>,                            <span class="cm"># 隔离：不读共享 MEMORY.md</span>
    clarify_callback=<span class="kw">None</span>,                       <span class="cm"># 隔离：不能向用户提问</span>
    session_db=...,                                <span class="cm"># 继承：共享会话 DB（血缘靠 parent_session_id）</span>
    iteration_budget=<span class="kw">None</span>,                       <span class="cm"># 隔离：每个子代理 fresh budget</span>
)</pre>
</div>
<p>看这份「隔离 vs 继承」清单：<strong>隔离</strong>的是会污染或淹没的东西——对话历史、上下文文件、记忆、用户交互、迭代预算（每个子代理一份<strong>全新</strong>预算）；<strong>继承</strong>的是跑起来必需的运行时——provider / model / api_key / session_db。工具描述把这条取舍说得最直白：<span class="inline">Each subagent gets its own conversation, terminal session, and toolset. Only the final summary is returned -- intermediate tool results never enter your context window</span>。</p>
<p>这条「隔离 vs 继承」的分界线，背后是一个统一判据：<strong>会污染上下文或缓存的，一律隔离；只供运行不入对话的，才继承</strong>。它不是逐项拍脑袋，而是把第 6 章「缓存神圣」与约束 A「中间遗失」当成<strong>硬约束</strong>反推出来的结果。也正因如此，子代理跑的是一份 <span class="mono">ephemeral_system_prompt</span> 而非父那套三层稳定 system prompt——临时、用完即弃，不参与父的缓存前缀，于是父对话从头到尾<strong>字节级稳定</strong>，每一轮都命中缓存。理解了这个判据，你就能预测任何新字段该落在隔离侧还是继承侧。</p>

<div class="figure">
<svg viewBox="0 0 680 348" role="img" aria-label="委派的上下文隔离：父代理派发任务，子代理在独立 context 与终端里跑，只把一句摘要回灌父代理">
  <text x="340" y="22" text-anchor="middle" font-size="13.5" font-weight="700" fill="var(--ink)">委派：上下文隔离 — 父只收一句摘要</text>

  <rect x="24" y="44" width="210" height="190" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2.5"/>
  <text x="129" y="68" text-anchor="middle" font-size="13" font-weight="700" fill="var(--accent-ink)">父代理 parent</text>
  <text x="40" y="96" font-size="11.5" fill="var(--ink)">• 自己的 context</text>
  <text x="40" y="120" font-size="11.5" fill="var(--ink)">• 自己的 terminal</text>
  <rect x="40" y="136" width="178" height="80" rx="8" fill="var(--panel)" stroke="var(--accent)" stroke-dasharray="4 3"/>
  <text x="129" y="162" text-anchor="middle" font-size="11.5" fill="var(--accent-ink)">🔒 神圣缓存前缀</text>
  <text x="129" y="181" text-anchor="middle" font-size="9.5" fill="var(--muted)">每轮命中 · 字节级稳定</text>
  <text x="129" y="200" text-anchor="middle" font-size="9.5" fill="var(--muted)">（第 6 章）</text>

  <rect x="446" y="44" width="210" height="190" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="2"/>
  <text x="551" y="68" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--blue)">子代理 subagent · leaf</text>
  <text x="460" y="92" font-size="11" fill="var(--ink)">• 独立 context</text>
  <text x="460" y="112" font-size="11" fill="var(--ink)">• 独立 terminal</text>
  <text x="460" y="132" font-size="10" fill="var(--ink)">• ephemeral prompt(goal+context)</text>
  <text x="460" y="150" font-size="10" fill="var(--ink)">• skip_context_files / memory</text>
  <rect x="460" y="160" width="182" height="62" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="551" y="179" text-anchor="middle" font-size="10" font-weight="700" fill="var(--red)">✖ 剥离 5 个高危工具</text>
  <text x="551" y="196" text-anchor="middle" font-size="8.5" fill="var(--red)">delegate · clarify · memory</text>
  <text x="551" y="210" text-anchor="middle" font-size="8.5" fill="var(--red)">send_message · execute_code</text>

  <text x="340" y="84" text-anchor="middle" font-size="11" font-weight="700" fill="var(--ink)">delegate_task(goal)</text>
  <line x1="238" y1="92" x2="442" y2="92" stroke="var(--ink)" stroke-width="2"/>
  <path d="M442 92 L432 87 L432 97 Z" fill="var(--ink)"/>

  <text x="340" y="142" text-anchor="middle" font-size="11" font-weight="700" fill="var(--accent-ink)">只回一句摘要</text>
  <line x1="442" y1="150" x2="238" y2="150" stroke="var(--accent-ink)" stroke-width="2"/>
  <path d="M238 150 L248 145 L248 155 Z" fill="var(--accent-ink)"/>
  <text x="340" y="170" text-anchor="middle" font-size="9.5" fill="var(--muted)">only final summary</text>

  <rect x="24" y="252" width="632" height="80" rx="10" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="40" y="276" font-size="11.5" font-weight="700" fill="var(--muted)">中间过程：读几十文件 · 跑命令 · 试错几十轮</text>
  <text x="40" y="300" font-size="11" fill="var(--blue)">✓ 全留在子代理 context（platform=&quot;subagent&quot;，用完即弃）</text>
  <text x="40" y="321" font-size="11" fill="var(--accent-ink)">✗ 永不进父 context · 不污染父缓存 → 治 A·中间遗失 + 护第 6 章缓存</text>
</svg>
<div class="fig-cap"><b>委派的上下文隔离</b>：父代理调 <span class="mono">delegate_task(goal)</span> 把子任务交给一个<b>独立子代理</b>——它有<b>独立 context + 独立终端</b>，跑在只装 goal+context 的 <span class="mono">ephemeral_system_prompt</span> 上，并 <span class="mono">skip_context_files/memory</span>；作为 leaf 还被<b>剥离 delegate/clarify/memory/send_message/execute_code</b> 五个高危工具。子代理读几十文件、试错的<b>中间过程全留在自己的 context</b>，只把<b>一句最终摘要</b>回灌父代理。于是父窗口不被淹没（治 A·中间遗失），父的神圣缓存前缀也字节级稳定（护第 6 章缓存）。</div>
</div>

<h2>两种角色：leaf 不能再委派，orchestrator 能</h2>
<p>子代理有两种 <span class="mono">role</span>。默认的 <span class="mono">leaf</span> 是<strong>专注的工人</strong>，被禁掉一批工具；<span class="mono">orchestrator</span> 则保留委派能力，能再派自己的工人：</p>
<p>为什么 leaf 默认要被剥掉这<strong>五</strong>个高危工具？这是<strong>最小权限</strong>（连第 24 章安全）落到委派上的体现，每一条禁令都对着一类具体越权风险：<span class="mono">delegate_task</span> 禁掉防无限套娃；<span class="mono">clarify</span> 禁掉是因为子代理的 <span class="mono">clarify_callback=None</span>——它根本够不到用户，留着只会卡死；<span class="mono">memory</span> 禁掉防一个隔离的子上下文去写<strong>共享</strong> MEMORY.md 污染全局；<span class="mono">send_message</span> 禁掉防工人擅自制造跨平台副作用；<span class="mono">execute_code</span> 禁掉是要它<strong>逐步推理</strong>而非一把梭写脚本。</p>
<p>为什么嵌套<strong>默认关</strong>、并发还要<strong>设上限</strong>？因为代理军团的成本是<strong>相乘</strong>的：<span class="mono">MAX_DEPTH=1</span> 让默认树扁平（父→子，孙被拒），每多一层 API 成本<strong>按扇出相乘</strong>，必须在 config 显式抬 <span class="mono">max_spawn_depth</span> 才解锁；同步批量受 <span class="mono">max_concurrent_children</span>（默认 3）限，后台委派另受 <span class="mono">max_async_children</span>（默认 3）限——且满载时新的后台派发是<strong>直接拒绝、不排队</strong>，免得一个跑飞的模型堆出无界的后台工作。<span class="mono">orchestrator_enabled</span> 则是一键全局开关，运营者无需改码即可禁掉整个编排能力。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/delegate_tool.py</span><span class="ln">44-53 / 1021-1024 · 节选</span></div>
  <pre><span class="cm"># 子代理永远不能用的工具</span>
DELEGATE_BLOCKED_TOOLS = <span class="fn">frozenset</span>([
    <span class="st">"delegate_task"</span>,   <span class="cm"># 不许递归委派（leaf）</span>
    <span class="st">"clarify"</span>,         <span class="cm"># 不许向用户提问</span>
    <span class="st">"memory"</span>,          <span class="cm"># 不许写共享 MEMORY.md</span>
    <span class="st">"send_message"</span>,    <span class="cm"># 不许跨平台副作用</span>
    <span class="st">"execute_code"</span>,    <span class="cm"># 应逐步推理，不写脚本</span>
])

<span class="cm"># role 降级：只有显式 orchestrator 且未超深度，才保留 orchestrator</span>
orchestrator_ok = _get_orchestrator_enabled() <span class="kw">and</span> child_depth &lt; max_spawn
effective_role = role <span class="kw">if</span> (role == <span class="st">"orchestrator"</span> <span class="kw">and</span> orchestrator_ok) <span class="kw">else</span> <span class="st">"leaf"</span></pre>
</div>
<p><span class="mono">_strip_blocked_tools</span> 把 <span class="mono">delegation / clarify / memory / code_execution</span> 四个 toolset <strong>整组移除</strong>——leaf 因此一并失去 delegate_task（<strong>不能再委派</strong>、避免无限套娃）、clarify、memory、execute_code；而 <span class="mono">DELEGATE_BLOCKED_TOOLS</span> 是「子代理永不可见」的<strong>权威工具清单</strong>（5 个，含 send_message），把『全员被禁』的 toolset 挡在子代理菜单之外。<span class="mono">orchestrator</span> 则被重新加回 delegation toolset、能再派工人——但<strong>默认配置下嵌套是关闭的</strong>（<span class="mono">max_spawn</span> 默认扁平，需在 config 显式抬高才解锁多级），且受<strong>嵌套深度上限</strong>（<span class="mono">child_depth &lt; max_spawn</span>）和并发上限（<span class="mono">max_concurrent_children</span>，默认 3）兜住，防止子代理军团失控。</p>

<div class="figure">
<svg viewBox="0 0 680 330" role="img" aria-label="并行批量委派与嵌套深度上限：父代理一次派发多个子代理，受并发上限 3 约束，嵌套深度默认 1，孙代理被拒">
  <text x="340" y="22" text-anchor="middle" font-size="13.5" font-weight="700" fill="var(--ink)">并行 batch + 嵌套深度上限</text>

  <rect x="270" y="36" width="140" height="44" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2.5"/>
  <text x="340" y="63" text-anchor="middle" font-size="12" font-weight="700" fill="var(--accent-ink)">父代理 · depth 0</text>

  <text x="40" y="96" font-size="10.5" fill="var(--ink)">delegate_task(tasks=[…])</text>
  <line x1="340" y1="80" x2="340" y2="100" stroke="var(--ink)" stroke-width="2"/>
  <line x1="104" y1="100" x2="576" y2="100" stroke="var(--ink)" stroke-width="2"/>
  <line x1="104" y1="100" x2="104" y2="126" stroke="var(--ink)" stroke-width="2"/>
  <path d="M104 128 L99 119 L109 119 Z" fill="var(--ink)"/>
  <line x1="340" y1="100" x2="340" y2="126" stroke="var(--ink)" stroke-width="2"/>
  <path d="M340 128 L335 119 L345 119 Z" fill="var(--ink)"/>
  <line x1="576" y1="100" x2="576" y2="126" stroke="var(--ink)" stroke-width="2"/>
  <path d="M576 128 L571 119 L581 119 Z" fill="var(--ink)"/>

  <rect x="24"  y="130" width="160" height="46" rx="10" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="104" y="151" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">子代理 #1</text>
  <text x="104" y="167" text-anchor="middle" font-size="9" fill="var(--muted)">leaf · depth 1</text>
  <rect x="260" y="130" width="160" height="46" rx="10" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="340" y="151" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">子代理 #2</text>
  <text x="340" y="167" text-anchor="middle" font-size="9" fill="var(--muted)">leaf · depth 1</text>
  <rect x="496" y="130" width="160" height="46" rx="10" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="576" y="151" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">子代理 #3</text>
  <text x="576" y="167" text-anchor="middle" font-size="9" fill="var(--muted)">leaf · depth 1</text>

  <text x="340" y="196" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">并发上限 max_concurrent_children = 3</text>
  <text x="340" y="213" text-anchor="middle" font-size="9.5" fill="var(--muted)">一次超过 3 个直接拒绝、需拆分调用</text>

  <rect x="24" y="240" width="372" height="74" rx="10" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="40" y="262" font-size="11" font-weight="700" fill="var(--muted)">嵌套深度上限</text>
  <text x="40" y="283" font-size="11" fill="var(--ink)">max_spawn_depth = 1（默认扁平 flat）</text>
  <text x="40" y="303" font-size="11" fill="var(--ink)">父 → 子 ✓　　子 → 孙 ✗（需 config 显式抬高）</text>

  <line x1="576" y1="176" x2="556" y2="246" stroke="var(--red)" stroke-width="2" stroke-dasharray="4 3"/>
  <text x="600" y="214" font-size="15" font-weight="700" fill="var(--red)">✖</text>
  <rect x="468" y="248" width="170" height="62" rx="10" fill="var(--red-soft)" stroke="var(--red)" stroke-dasharray="4 3"/>
  <text x="553" y="272" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--red)">孙代理 grandchild</text>
  <text x="553" y="290" text-anchor="middle" font-size="9.5" fill="var(--red)">depth 2 · 被拒绝</text>
</svg>
<div class="fig-cap"><b>并行 batch 与深度上限</b>：父代理用 <span class="mono">tasks=[…]</span> 一次派发多个子代理并发执行，但同步并发受 <span class="mono">max_concurrent_children</span>（默认 <b>3</b>）约束，一次<b>超出即被拒</b>（须拆成多次调用或抬高上限）。嵌套则<b>默认扁平</b>：<span class="mono">max_spawn_depth = 1</span>，父→子放行、子→孙<b>被拒</b>——要多级必须在 config 显式抬高（后台委派另受 <span class="mono">max_async_children=3</span> 限，满载直接拒绝、不排队）。代价相乘，所以默认收得很紧。</div>
</div>

<h2>background 委派如何不破缓存</h2>
<p>顶层 model 发起的委派<strong>默认是同步的</strong>——父代理会等子代理跑完、拿到摘要再继续（见下一节）。但也可以显式 <span class="mono">background=true</span> 让它<strong>异步</strong>：立即返回一个 <span class="mono">delegation_id</span>，子代理在后台守护线程里跑。这时子代理跑完后，结果如何<strong>不破坏父缓存</strong>地回到对话？答案在完成队列的设计里：</p>
<p>为什么宁可绕一大圈走<strong>共享完成队列</strong>，也不直接把结果塞回正在跑的循环？因为那条 idle 重入的轨道是<strong>现成且安全</strong>的：CLI 与 gateway 本就在空闲时轮询这条队列，复用它就白拿了<strong>去重、崩溃恢复检查点</strong>，还省得在仓库两个最大的文件里再写一套排空循环。更关键的是，硬插会在工具结果与 assistant 消息之间制造非法的同角色相邻（第 7 章），并改写历史前缀击穿缓存（第 6 章）——而作为新 turn 浮现，两样都不犯。</p>
<p>完成事件还特意携带一块<strong>自包含的任务来源</strong>（原始 goal、父给的 context、toolsets、model、派发时刻、状态、完整摘要）。为什么这么重？因为结果回灌时父可能已深陷无关上下文、早忘了当初为何派出这个子代理；这块自述让父能就地<strong>用掉结果或按新世界重派</strong>。这也解释了父为何<strong>默认等</strong>子的摘要再走：等待点就是<strong>汇总点</strong>，把多路并行的结论收拢成一段高信号文字，是上下文经济最划算的一步。</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/async_delegation.py</span><span class="ln">1-34 · 节选（docstring）</span></div>
  <pre>When the child finishes, a completion event is pushed onto the SHARED
completion_queue ... The CLI and gateway already poll that queue while
the agent is idle and forge a fresh user/internal turn from each event:
<span class="cm">  - completions surface as a NEW turn when the agent is idle, never</span>
<span class="cm">    spliced between a tool result and an assistant message. That keeps</span>
<span class="cm">    strict message-role alternation legal and the prompt cache intact.</span></pre>
</div>
<p>关键设计：子代理完成事件<strong>不会</strong>被硬塞进对话中段（那会破坏严格角色交替、击穿缓存）。它进一个<strong>共享完成队列</strong>，等父代理<strong>空闲时</strong>，才作为一个<strong>全新的 turn</strong> 浮现。这样既维持了严格角色交替（第 7 章）的合法性，又<strong>保住了 prompt 缓存</strong>（第 6 章）。一个细节：background 委派是<strong>进程内的</strong>——若进程退出或 <span class="mono">/new</span>，未完成的子代理会被丢弃；要可靠存活，得用 <span class="mono">cronjob</span> 或 <span class="mono">terminal(background=True, notify_on_complete=True)</span>。</p>
<p>把这三章串起来看就更清楚：委派、压缩（第 15 章）、记忆（第 11 章）其实是对抗「上下文有限」的<strong>三条互补路径</strong>——隔离把中间过程<strong>挡在门外</strong>，压缩把已进来的历史<strong>就地瘦身</strong>，记忆把该长期留存的<strong>沉到外部存储</strong>。委派选的是「挡在门外」这条，代价是子代理看不到父的全貌、只能靠任务书自立门户，好处是父窗口与父缓存<strong>都毫发无损</strong>。当一个任务的中间体量大、又彼此独立时，委派几乎总是比硬塞进父对话再压缩更划算，也更能保住缓存命中率。</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">父代理调 <span class="mono">delegate_task(goal=…)</span> 或批量 <span class="mono">tasks=[…]</span>（最多 max_concurrent_children=3 并行）</span></div>
  <div class="step"><span class="num">2</span><span class="sc">构造子 AIAgent：ephemeral_system_prompt(只装 goal+context) + skip_context_files/memory + fresh budget</span></div>
  <div class="step"><span class="num">3</span><span class="sc">子代理在<strong>独立 context + 独立终端</strong>跑完，中间工具结果全留在子 context</span></div>
  <div class="step"><span class="num">4</span><span class="sc">只把<strong>最终摘要</strong>返回父代理（父上下文窗口始终干净）</span></div>
  <div class="step"><span class="num">5</span><span class="sc">background：完成事件进共享队列 → 父<strong>空闲时</strong>作新 turn 浮现 → 严格交替+缓存不破</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「隔离而不破缓存」</div>
  <div class="collab-sub">① 组件清单（★本章核心，其余跨章节配合）</div>
  本章核心：<strong>delegate_task</strong>（单/批量入口）、<strong>子 AIAgent 隔离构造</strong>（ephemeral prompt + skip 标志）、<strong>DELEGATE_BLOCKED_TOOLS + role 降级</strong>、<strong>async_delegation 完成队列</strong>。跨章节配合：<span class="mono">delegate_task</span> 是一个特殊的<strong>工具</strong>（第 8 章，且 leaf 禁用它防递归）；子代理 <span class="mono">skip_context_files</span> / <span class="mono">skip_memory</span> 意味着不继承父的 system prompt 三层与记忆（第 6 / 11 章）；完成队列<strong>只在 idle 作新 turn</strong>，维持严格角色交替（第 7 章）+ 不破缓存（第 6 章）；上下文隔离与第 15 章压缩是对抗「上下文有限」的<strong>两条不同路</strong>（隔离 vs 压缩）。
  <div class="collab-sub">② 数据流时序</div>
  父调 delegate_task → 构造子 AIAgent（隔离对话历史/上下文文件/记忆，继承运行时）→ 子代理独立跑、中间结果留子 context → 只把摘要返回父 → （background）完成事件进共享队列 → 父空闲时作新 turn 浮现。
  <div class="collab-sub">③ 关键点</div>
  委派把「会淹没上下文的中间过程」<strong>关进子代理的独立 context</strong>，父只收摘要——既保护父上下文窗口，又（靠完成队列的 idle 重入）保护父缓存。这是「规模化」与「缓存神圣」共存的手法：<strong>把复杂度隔离到边缘</strong>。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线：<strong>上下文隔离 + 只带回摘要 + 完成队列不破缓存</strong>。它治两条 LLM 固有约束：
  <p style="margin:.5rem 0 0"><span class="badge constraint">A·中间遗失</span>——子任务的大量中间工具结果会<strong>淹没</strong>父上下文、把关键信息挤到中间被遗忘；委派把它们<strong>隔离</strong>在子 context，父只收高信号摘要；
  <span class="badge constraint">F·误差累积</span>——每个子代理<strong>fresh budget + 独立 context</strong>，避免跨任务的状态污染与误差累积。反模式：让子代理把中间过程<strong>实时回传</strong>父对话、或在对话中段<strong>硬插</strong>完成消息——前者淹没上下文，后者破坏角色交替、击穿缓存。</p>
  <p style="margin:.5rem 0 0">再往根上挖一层：委派之所以能让「规模化」与「缓存神圣」并存，靠的是把复杂度<strong>关到边缘</strong>而非摊进核心。子代理是一次性的隔离舱——<span class="mono">platform="subagent"</span>、独立终端会话、跑完即弃，唯一产出是返回父的一段摘要。但隔离也有代价：后台委派是<strong>进程内</strong>的守护线程，进程退出或 <span class="mono">/new</span> 即丢；要让活儿<strong>跨进程存活</strong>，得改用 <span class="mono">cronjob</span> 或 <span class="mono">terminal(background=True, notify_on_complete=True)</span>。这正是「快而不持久」与「慢而可靠」之间的清醒取舍。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>上下文隔离</strong>：子代理有独立对话/终端/工具集，<span class="mono">ephemeral_system_prompt</span> 只装 goal+context、<span class="mono">skip_context_files/memory</span>，只带回摘要。</li>
    <li><strong>单 / 批量</strong>：<span class="mono">goal</span> 单任务 vs <span class="mono">tasks=[…]</span> 批量并行；并发上限 <span class="mono">max_concurrent_children</span>（默认 3）。</li>
    <li><strong>leaf vs orchestrator</strong>：leaf（默认）禁用 delegate_task/clarify/memory/send_message/execute_code；orchestrator 保留委派、能再派工人（受嵌套深度上限约束）。</li>
    <li><strong>background 不破缓存</strong>：完成事件进共享队列，父<strong>空闲时</strong>作新 turn 浮现，维持严格角色交替（第 7 章）+ 缓存（第 6 章）。</li>
    <li><strong>非持久</strong>：background 委派进程内，进程退出/<span class="mono">/new</span> 即丢；要存活用 <span class="mono">cronjob</span> 或 <span class="mono">terminal(background, notify_on_complete)</span>。</li>
  </ul>
</div>

<div class="figure">
<svg viewBox="0 0 680 490" role="img" aria-label="一次真实 delegate_task 调用走一遍：① 调用参数 goal/context/toolsets/role=leaf；② 构造子代理隔离 ephemeral_system_prompt、platform=subagent、skip_context_files、skip_memory、iteration_budget=None，继承 base_url/api_key/model/session_db；③ 剥离 DELEGATE_BLOCKED_TOOLS 五个工具并把 role 降级为 leaf；④ 子代理读约 20 个文件的中间过程全留在子 context 永不进父；⑤ 父只收一句最终摘要，background 时先返 delegation_id。">
  <text x="340" y="22" text-anchor="middle" font-size="13.5" font-weight="700" fill="var(--ink)">一次真实 delegate_task 调用 · 参数 → 隔离构造 → 只回一句摘要</text>
  <text x="340" y="40" text-anchor="middle" font-size="10" fill="var(--muted)">例子：派一个 leaf 子代理审计 gateway 各 adapter 的 scoped lock</text>
  <text x="628" y="32" font-size="22">🧩</text>

  <rect x="20" y="50" width="640" height="60" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="32" y="68" font-size="10" font-weight="700" fill="var(--blue)">① 调用 · tools/delegate_tool.py</text>
  <text x="32" y="86" font-size="9" font-family="monospace" fill="var(--ink)">delegate_task(goal=&quot;审计 gateway/platforms/ 各 adapter connect() 缺 acquire_scoped_lock&quot;,</text>
  <text x="32" y="102" font-size="9" font-family="monospace" fill="var(--ink)">  context=&quot;模式见 irc/adapter.py&quot;, toolsets=[&quot;terminal&quot;,&quot;file&quot;,&quot;search&quot;], role=&quot;leaf&quot;)</text>

  <line x1="340" y1="110" x2="340" y2="126" stroke="var(--line)" stroke-width="2"/>
  <path d="M340 132 L334 122 L346 122 Z" fill="var(--line)"/>

  <text x="340" y="146" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--ink)">② 构造子 AIAgent · 隔离 vs 继承（:1234-1249）</text>

  <rect x="20" y="154" width="324" height="118" rx="9" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="34" y="172" font-size="10" font-weight="700" fill="var(--accent-ink)">隔离 · 不入对话 / 不进缓存前缀</text>
  <text x="34" y="190" font-size="9" font-family="monospace" fill="var(--ink)">ephemeral_system_prompt=child_prompt</text>
  <text x="34" y="206" font-size="9" font-family="monospace" fill="var(--ink)">platform=&quot;subagent&quot;</text>
  <text x="34" y="222" font-size="9" font-family="monospace" fill="var(--ink)">skip_context_files=True</text>
  <text x="34" y="238" font-size="9" font-family="monospace" fill="var(--ink)">skip_memory=True</text>
  <text x="34" y="256" font-size="9" font-family="monospace" fill="var(--purple)">iteration_budget=None  # fresh budget per subagent</text>

  <rect x="356" y="154" width="304" height="118" rx="9" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="2"/>
  <text x="370" y="172" font-size="10" font-weight="700" fill="var(--blue)">继承 · 仅供运行、不入对话</text>
  <text x="370" y="190" font-size="9" font-family="monospace" fill="var(--ink)">base_url / api_key</text>
  <text x="370" y="206" font-size="9" font-family="monospace" fill="var(--ink)">model / fallback_model</text>
  <text x="370" y="222" font-size="9" font-family="monospace" fill="var(--ink)">session_db（共享会话库）</text>
  <text x="370" y="246" font-size="9" fill="var(--muted)">运行时凭证照搬，但对话历史 / 上下文</text>
  <text x="370" y="260" font-size="9" fill="var(--muted)">文件 / 记忆一律不继承 → 父缓存零扰动</text>

  <rect x="20" y="282" width="640" height="74" rx="9" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="32" y="300" font-size="10" font-weight="700" fill="var(--red)">③ 剥离高危工具 + role 降级 · :768 / :45-53 / :1023-1024</text>
  <text x="32" y="318" font-size="9" font-family="monospace" fill="var(--ink)">child_toolsets = _strip_blocked_tools(child_toolsets)</text>
  <text x="32" y="334" font-size="9" font-family="monospace" fill="var(--red)">✖ DELEGATE_BLOCKED_TOOLS(5): delegate_task · clarify · memory · send_message · execute_code</text>
  <text x="32" y="350" font-size="9" font-family="monospace" fill="var(--purple)">effective_role = role if (role==&quot;orchestrator&quot; and orchestrator_ok) else &quot;leaf&quot;</text>

  <rect x="20" y="366" width="324" height="92" rx="9" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="34" y="384" font-size="10" font-weight="700" fill="var(--muted)">④ 子代理独立 context（永不进父）</text>
  <text x="34" y="404" font-size="9" fill="var(--ink)">读 ~20 个 adapter.py · search/grep · 试错几十轮</text>
  <text x="34" y="422" font-size="9" fill="var(--ink)">中间工具结果全留子 context</text>
  <text x="34" y="440" font-size="9" fill="var(--muted)">platform=&quot;subagent&quot; · 跑完即弃</text>

  <rect x="356" y="366" width="304" height="92" rx="9" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="370" y="384" font-size="10" font-weight="700" fill="var(--accent-ink)">⑤ 父只收一句最终摘要</text>
  <text x="370" y="404" font-size="9" fill="var(--ink)">&quot;审计 21 adapter：matrix/sms 缺 lock；</text>
  <text x="370" y="420" font-size="9" fill="var(--ink)">　余 19 合规&quot;</text>
  <text x="370" y="440" font-size="9" fill="var(--purple)">background=true → 先返 delegation_id（:2592）</text>

  <rect x="20" y="466" width="640" height="20" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="340" y="480" text-anchor="middle" font-size="9" fill="var(--muted)">读这张图：一次 delegate_task = 继承运行时 + 隔离对话/文件/记忆 + 剥 5 工具降为 leaf；父只收一句摘要，缓存零扰动</text>
</svg>
<div class="fig-cap"><b>一次真实 delegate_task</b>：父调 <span class="mono">delegate_task(goal,context,toolsets,role=&quot;leaf&quot;)</span> → 子代理<b>隔离</b>构造（<span class="mono">ephemeral_system_prompt</span> / <span class="mono">platform=&quot;subagent&quot;</span> / <span class="mono">skip_context_files</span> / <span class="mono">skip_memory</span> / <span class="mono">iteration_budget=None</span>），<b>继承</b> base_url/api_key/model/session_db；剥离 <span class="mono">DELEGATE_BLOCKED_TOOLS</span> 五个工具并把 role 降为 leaf；读约 20 个文件的<b>中间过程全留子 context</b>，父只收一句摘要「审计 21 adapter：matrix/sms 缺 lock；余 19 合规」（background 先返 <span class="mono">delegation_id</span>）。</div>
</div>
""",
    "en": r"""
<p class="lead">
When a task produces <strong>tons of intermediate work</strong> (reading dozens of files, running a chain of commands), stuffing it all into the main conversation <strong>floods the context</strong>. Delegation (<span class="mono">delegate_task</span>) solves this: hand the subtask to an <strong>independent subagent</strong> — it has its own conversation, its own terminal, its own toolset, and <strong>returns only the final summary</strong> to the parent; the intermediate tool results <strong>never enter</strong> your context window. This chapter opens "scaling & isolation."
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · outsourcing to an independent team</div>
  You're the project manager. A research task requires sifting a hundred documents — you <strong>don't</strong> haul all hundred onto your own desk to read (that buries it = floods the context). You <strong>outsource</strong> to an independent team: hand them a <strong>self-contained brief</strong> (the subagent knows nothing about your conversation history), they work in <strong>their own office</strong> (independent context + terminal), and finally give you a <strong>conclusion summary</strong>. The hundred documents they read and the drafts they tried <strong>never appear on your desk</strong>.
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture · context isolation, return only the summary</div>
  Delegation's core value is <strong>context isolation</strong>. The subagent gets an <span class="mono">ephemeral_system_prompt</span> (just goal + context, <strong>not</strong> the parent's conversation history), plus <span class="mono">skip_context_files</span> / <span class="mono">skip_memory</span> — it <strong>doesn't read</strong> the parent's AGENTS.md or the shared MEMORY.md. It runs to completion in its own conversation, and <strong>only the final response is returned to the parent as a summary</strong>. So the parent's context window stays <strong>clean</strong>: neither flooded by intermediate tool results nor polluted by the subtask's trial-and-error. This is another route against "limited context" — ch.15 uses compression, this chapter uses isolation.
</div>

<h2>The heart of isolation: what the subagent gets and doesn't</h2>
<p>When constructing the child AIAgent, what is <strong>isolated</strong> vs <strong>inherited</strong> is the crux of the design:</p>
<p>Why isolate exactly these three — conversation history, context files, shared memory? Because they're precisely what would <strong>flood</strong> the parent window and <strong>shatter</strong> the sacred cache (ch.6). A subtask reads dozens of files and burns dozens of trial-and-error rounds; if that intermediate work flows back into the parent conversation, key info gets shoved into the "forgotten middle" (constraint A), and any change to the parent's history prefix forces a cache-prefix mismatch and a full recompute at several times the cost. <span class="mono">skip_context_files</span> / <span class="mono">skip_memory</span> aren't shortcuts — they <strong>deliberately</strong> stop the subagent from re-loading the parent's AGENTS.md or shared MEMORY.md. The subagent wants a <strong>self-contained brief</strong>, not the parent's entire worldview.</p>
<p>Conversely, why <strong>inherit</strong> <span class="mono">session_db</span> and provider / model? Because they're the runtime substrate that makes it <strong>run</strong>, not context-polluting <strong>content</strong>: the shared session DB threads the subagent's lineage via <span class="mono">parent_session_id</span> for later traceability, without hauling the parent's conversation into the child window. And <span class="mono">iteration_budget=None</span> gives each subagent a <strong>fresh budget</strong> to treat constraint F (error accumulation) — if a pack of sibling subagents shared one budget, a single runaway would starve the rest; an independent budget gives every worker a clean start, and a failure only fails its own share.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/delegate_tool.py</span><span class="ln">1219-1250 · simplified</span></div>
  <pre>child = AIAgent(
    base_url=..., api_key=..., model=...,          <span class="cm"># inherit: provider/model runtime</span>
    enabled_toolsets=child_toolsets,
    ephemeral_system_prompt=child_prompt,          <span class="cm"># isolate: just goal+context, no parent history</span>
    platform=<span class="st">"subagent"</span>,
    skip_context_files=<span class="kw">True</span>,                     <span class="cm"># isolate: no AGENTS.md/SOUL.md</span>
    skip_memory=<span class="kw">True</span>,                            <span class="cm"># isolate: no shared MEMORY.md</span>
    clarify_callback=<span class="kw">None</span>,                       <span class="cm"># isolate: cannot ask the user</span>
    session_db=...,                                <span class="cm"># inherit: shared session DB (lineage via parent_session_id)</span>
    iteration_budget=<span class="kw">None</span>,                       <span class="cm"># isolate: fresh budget per subagent</span>
)</pre>
</div>
<p>Look at the "isolate vs inherit" list: <strong>isolated</strong> are the things that would pollute or flood — conversation history, context files, memory, user interaction, the iteration budget (each subagent gets a <strong>fresh</strong> one); <strong>inherited</strong> is the runtime needed to run — provider / model / api_key / session_db. The tool description states the trade-off most plainly: <span class="inline">Each subagent gets its own conversation, terminal session, and toolset. Only the final summary is returned -- intermediate tool results never enter your context window</span>.</p>
<p>This "isolate vs inherit" dividing line rests on a single criterion: <strong>anything that would pollute context or cache is isolated; only what's needed to run, without entering the conversation, is inherited</strong>. It's not item-by-item guesswork — it's reverse-derived from treating ch.6's "cache is sacred" and constraint A "lost-in-the-middle" as <strong>hard constraints</strong>. That's also why the subagent runs on an <span class="mono">ephemeral_system_prompt</span> rather than the parent's stable three-tier system prompt — temporary, throwaway, never part of the parent's cache prefix, so the parent conversation stays <strong>byte-stable</strong> end to end and hits the cache every turn. Grasp this criterion and you can predict which side any new field belongs on.</p>

<div class="figure">
<svg viewBox="0 0 680 348" role="img" aria-label="Delegation context isolation: the parent dispatches a subtask, the subagent runs in its own context and terminal, returning only a one-line summary to the parent">
  <text x="340" y="22" text-anchor="middle" font-size="13.5" font-weight="700" fill="var(--ink)">Delegation: context isolation — parent gets only a summary</text>

  <rect x="24" y="44" width="210" height="190" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2.5"/>
  <text x="129" y="68" text-anchor="middle" font-size="13" font-weight="700" fill="var(--accent-ink)">parent</text>
  <text x="40" y="96" font-size="11.5" fill="var(--ink)">• its own context</text>
  <text x="40" y="120" font-size="11.5" fill="var(--ink)">• its own terminal</text>
  <rect x="40" y="136" width="178" height="80" rx="8" fill="var(--panel)" stroke="var(--accent)" stroke-dasharray="4 3"/>
  <text x="129" y="162" text-anchor="middle" font-size="11.5" fill="var(--accent-ink)">🔒 sacred cache prefix</text>
  <text x="129" y="181" text-anchor="middle" font-size="9.5" fill="var(--muted)">hits every turn · byte-stable</text>
  <text x="129" y="200" text-anchor="middle" font-size="9.5" fill="var(--muted)">(ch.6)</text>

  <rect x="446" y="44" width="210" height="190" rx="10" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="2"/>
  <text x="551" y="68" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--blue)">subagent · leaf</text>
  <text x="460" y="92" font-size="11" fill="var(--ink)">• independent context</text>
  <text x="460" y="112" font-size="11" fill="var(--ink)">• independent terminal</text>
  <text x="460" y="132" font-size="10" fill="var(--ink)">• ephemeral prompt(goal+context)</text>
  <text x="460" y="150" font-size="10" fill="var(--ink)">• skip_context_files / memory</text>
  <rect x="460" y="160" width="182" height="62" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="551" y="179" text-anchor="middle" font-size="10" font-weight="700" fill="var(--red)">✖ 5 high-risk tools stripped</text>
  <text x="551" y="196" text-anchor="middle" font-size="8.5" fill="var(--red)">delegate · clarify · memory</text>
  <text x="551" y="210" text-anchor="middle" font-size="8.5" fill="var(--red)">send_message · execute_code</text>

  <text x="340" y="84" text-anchor="middle" font-size="11" font-weight="700" fill="var(--ink)">delegate_task(goal)</text>
  <line x1="238" y1="92" x2="442" y2="92" stroke="var(--ink)" stroke-width="2"/>
  <path d="M442 92 L432 87 L432 97 Z" fill="var(--ink)"/>

  <text x="340" y="142" text-anchor="middle" font-size="11" font-weight="700" fill="var(--accent-ink)">only final summary</text>
  <line x1="442" y1="150" x2="238" y2="150" stroke="var(--accent-ink)" stroke-width="2"/>
  <path d="M238 150 L248 145 L248 155 Z" fill="var(--accent-ink)"/>
  <text x="340" y="170" text-anchor="middle" font-size="9.5" fill="var(--muted)">one high-signal blob</text>

  <rect x="24" y="252" width="632" height="80" rx="10" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="40" y="276" font-size="11.5" font-weight="700" fill="var(--muted)">Intermediate work: read dozens of files · run commands · trial &amp; error</text>
  <text x="40" y="300" font-size="11" fill="var(--blue)">✓ stays in the subagent context (platform=&quot;subagent&quot;, discarded when done)</text>
  <text x="40" y="321" font-size="11" fill="var(--accent-ink)">✗ never enters parent context · never pollutes parent cache → treats A + guards ch.6</text>
</svg>
<div class="fig-cap"><b>Delegation context isolation</b>: the parent calls <span class="mono">delegate_task(goal)</span> to hand a subtask to an <b>independent subagent</b> — its own <b>independent context + terminal</b>, running on an <span class="mono">ephemeral_system_prompt</span> holding just goal+context, with <span class="mono">skip_context_files/memory</span>; as a leaf it's also <b>stripped of delegate/clarify/memory/send_message/execute_code</b>. The dozens of files it reads and its trial-and-error <b>all stay in its own context</b>; only <b>one final summary</b> returns to the parent. So the parent window isn't flooded (treats A·lost-in-the-middle) and its sacred cache prefix stays byte-stable (guards ch.6).</div>
</div>

<h2>Two roles: leaf can't re-delegate, orchestrator can</h2>
<p>A subagent has two <span class="mono">role</span>s. The default <span class="mono">leaf</span> is a <strong>focused worker</strong> with a set of tools disabled; <span class="mono">orchestrator</span> retains delegation and can spawn its own workers:</p>
<p>Why is leaf stripped of these <strong>five</strong> high-risk tools by default? It's <strong>least privilege</strong> (tying into ch.24 security) applied to delegation, and each ban targets a concrete over-reach risk: <span class="mono">delegate_task</span> is blocked to prevent infinite nesting; <span class="mono">clarify</span> is blocked because the child's <span class="mono">clarify_callback=None</span> — it literally can't reach the user, so keeping it would only deadlock; <span class="mono">memory</span> is blocked so an isolated child context can't write the <strong>shared</strong> MEMORY.md and pollute the global; <span class="mono">send_message</span> is blocked so a worker can't unilaterally cause cross-platform side effects; <span class="mono">execute_code</span> is blocked to force <strong>step-by-step reasoning</strong> instead of one-shot scripting.</p>
<p>Why is nesting <strong>off by default</strong> and concurrency <strong>capped</strong>? Because the cost of an agent army is <strong>multiplicative</strong>: <span class="mono">MAX_DEPTH=1</span> keeps the default tree flat (parent → child, grandchild rejected), every extra level <strong>multiplies API cost by the fan-out</strong>, and you must raise <span class="mono">max_spawn_depth</span> in config to unlock it; a synchronous batch is capped by <span class="mono">max_concurrent_children</span> (default 3), and background delegation is separately capped by <span class="mono">max_async_children</span> (default 3) — at capacity a new async dispatch is <strong>rejected outright, not queued</strong>, so a runaway model can't pile up unbounded background work. <span class="mono">orchestrator_enabled</span> is the one-switch global kill so an operator can disable the whole orchestration feature without a code change.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/delegate_tool.py</span><span class="ln">44-53 / 1021-1024 · excerpt</span></div>
  <pre><span class="cm"># Tools a child must never have access to</span>
DELEGATE_BLOCKED_TOOLS = <span class="fn">frozenset</span>([
    <span class="st">"delegate_task"</span>,   <span class="cm"># no recursive delegation (leaf)</span>
    <span class="st">"clarify"</span>,         <span class="cm"># no user questions</span>
    <span class="st">"memory"</span>,          <span class="cm"># no writes to shared MEMORY.md</span>
    <span class="st">"send_message"</span>,    <span class="cm"># no cross-platform side effects</span>
    <span class="st">"execute_code"</span>,    <span class="cm"># reason step-by-step, don't write scripts</span>
])

<span class="cm"># role demotion: only an explicit orchestrator under the depth cap stays one</span>
orchestrator_ok = _get_orchestrator_enabled() <span class="kw">and</span> child_depth &lt; max_spawn
effective_role = role <span class="kw">if</span> (role == <span class="st">"orchestrator"</span> <span class="kw">and</span> orchestrator_ok) <span class="kw">else</span> <span class="st">"leaf"</span></pre>
</div>
<p><span class="mono">_strip_blocked_tools</span> removes four toolsets wholesale — <span class="mono">delegation / clarify / memory / code_execution</span> — so leaf loses delegate_task (<strong>can't re-delegate</strong>, preventing infinite nesting), clarify, memory, and execute_code; while <span class="mono">DELEGATE_BLOCKED_TOOLS</span> is the authoritative list of tools a child must <strong>never see</strong> (5 of them, including send_message), keeping the 'all-blocked' toolset out of the subagent's menu. <span class="mono">orchestrator</span> gets the delegation toolset re-added and can spawn workers — but <strong>nesting is off by default</strong> (<span class="mono">max_spawn</span> is flat by default; raise it in config to unlock multiple levels), and is bounded by a <strong>nesting depth cap</strong> (<span class="mono">child_depth &lt; max_spawn</span>) and a concurrency cap (<span class="mono">max_concurrent_children</span>, default 3), so a subagent army can't spin out of control.</p>

<div class="figure">
<svg viewBox="0 0 680 330" role="img" aria-label="Parallel batch delegation and nesting depth cap: the parent dispatches several subagents at once, bounded by a concurrency cap of 3, with nesting depth defaulting to 1 so a grandchild is rejected">
  <text x="340" y="22" text-anchor="middle" font-size="13.5" font-weight="700" fill="var(--ink)">Parallel batch + nesting depth cap</text>

  <rect x="270" y="36" width="140" height="44" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2.5"/>
  <text x="340" y="63" text-anchor="middle" font-size="12" font-weight="700" fill="var(--accent-ink)">parent · depth 0</text>

  <text x="40" y="96" font-size="10.5" fill="var(--ink)">delegate_task(tasks=[…])</text>
  <line x1="340" y1="80" x2="340" y2="100" stroke="var(--ink)" stroke-width="2"/>
  <line x1="104" y1="100" x2="576" y2="100" stroke="var(--ink)" stroke-width="2"/>
  <line x1="104" y1="100" x2="104" y2="126" stroke="var(--ink)" stroke-width="2"/>
  <path d="M104 128 L99 119 L109 119 Z" fill="var(--ink)"/>
  <line x1="340" y1="100" x2="340" y2="126" stroke="var(--ink)" stroke-width="2"/>
  <path d="M340 128 L335 119 L345 119 Z" fill="var(--ink)"/>
  <line x1="576" y1="100" x2="576" y2="126" stroke="var(--ink)" stroke-width="2"/>
  <path d="M576 128 L571 119 L581 119 Z" fill="var(--ink)"/>

  <rect x="24"  y="130" width="160" height="46" rx="10" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="104" y="151" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">subagent #1</text>
  <text x="104" y="167" text-anchor="middle" font-size="9" fill="var(--muted)">leaf · depth 1</text>
  <rect x="260" y="130" width="160" height="46" rx="10" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="340" y="151" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">subagent #2</text>
  <text x="340" y="167" text-anchor="middle" font-size="9" fill="var(--muted)">leaf · depth 1</text>
  <rect x="496" y="130" width="160" height="46" rx="10" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="576" y="151" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">subagent #3</text>
  <text x="576" y="167" text-anchor="middle" font-size="9" fill="var(--muted)">leaf · depth 1</text>

  <text x="340" y="196" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">concurrency cap max_concurrent_children = 3</text>
  <text x="340" y="213" text-anchor="middle" font-size="9.5" fill="var(--muted)">more than 3 in one call is rejected, split it</text>

  <rect x="24" y="240" width="372" height="74" rx="10" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="40" y="262" font-size="11" font-weight="700" fill="var(--muted)">nesting depth cap</text>
  <text x="40" y="283" font-size="11" fill="var(--ink)">max_spawn_depth = 1 (flat by default)</text>
  <text x="40" y="303" font-size="11" fill="var(--ink)">parent → child ✓    child → grandchild ✗ (raise in config)</text>

  <line x1="576" y1="176" x2="556" y2="246" stroke="var(--red)" stroke-width="2" stroke-dasharray="4 3"/>
  <text x="600" y="214" font-size="15" font-weight="700" fill="var(--red)">✖</text>
  <rect x="468" y="248" width="170" height="62" rx="10" fill="var(--red-soft)" stroke="var(--red)" stroke-dasharray="4 3"/>
  <text x="553" y="272" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--red)">grandchild</text>
  <text x="553" y="290" text-anchor="middle" font-size="9.5" fill="var(--red)">depth 2 · rejected</text>
</svg>
<div class="fig-cap"><b>Parallel batch &amp; the depth cap</b>: the parent uses <span class="mono">tasks=[…]</span> to dispatch several subagents that run concurrently, but synchronous concurrency is bounded by <span class="mono">max_concurrent_children</span> (default <b>3</b>) — more than the cap in one call is <b>rejected</b> (split it into multiple calls or raise the cap). Nesting is <b>flat by default</b>: <span class="mono">max_spawn_depth = 1</span>, parent→child allowed but child→grandchild <b>rejected</b> — multiple levels require explicitly raising it in config (background delegation is separately capped by <span class="mono">max_async_children=3</span>, rejected outright at capacity, not queued). Cost is multiplicative, so the defaults are tight.</div>
</div>

<h2>How background delegation avoids breaking the cache</h2>
<p>A top-level, model-issued delegation is <strong>synchronous by default</strong> — the parent waits for the child to finish and return its summary before continuing (see the next section). But it can also be made <strong>asynchronous</strong> with an explicit <span class="mono">background=true</span>: it returns a <span class="mono">delegation_id</span> immediately, and the subagent runs on a background daemon thread. When the child then finishes, how does the result re-enter the conversation <strong>without breaking the parent's cache</strong>? The answer is in the completion-queue design:</p>
<p>Why take the long way through a <strong>shared completion queue</strong> instead of stuffing the result straight back into the running loop? Because that idle re-entry rail is <strong>already there and safe</strong>: the CLI and gateway already poll this queue while idle, so reusing it gets <strong>de-dup and a crash-recovery checkpoint</strong> for free and avoids writing a second drain loop in the two largest files in the repo. More importantly, splicing inline would create an illegal same-role adjacency between a tool result and an assistant message (ch.7) and rewrite the history prefix to shatter the cache (ch.6) — whereas surfacing as a new turn commits neither sin.</p>
<p>The completion event also deliberately carries a <strong>self-contained task-source block</strong> (the original goal, the context the parent supplied, toolsets, model, dispatch time, status, full summary). Why so heavy? Because when the result re-enters, the parent may be deep in unrelated context and has long forgotten why it spawned this subagent; the self-description lets it <strong>use the result or re-dispatch against the new world</strong> on the spot. This also explains why the parent <strong>waits by default</strong> for the child's summary: the wait point is the <strong>aggregation point</strong>, and collapsing parallel conclusions into one high-signal blob of text is the most context-economical move available.</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/async_delegation.py</span><span class="ln">1-34 · excerpt (docstring)</span></div>
  <pre>When the child finishes, a completion event is pushed onto the SHARED
completion_queue ... The CLI and gateway already poll that queue while
the agent is idle and forge a fresh user/internal turn from each event:
<span class="cm">  - completions surface as a NEW turn when the agent is idle, never</span>
<span class="cm">    spliced between a tool result and an assistant message. That keeps</span>
<span class="cm">    strict message-role alternation legal and the prompt cache intact.</span></pre>
</div>
<p>The key design: a child's completion event is <strong>not</strong> jammed into the middle of the conversation (that would break strict role alternation and shatter the cache). It goes onto a <strong>shared completion queue</strong>, and only when the parent is <strong>idle</strong> does it surface as a <strong>brand-new turn</strong>. This keeps strict role alternation (ch.7) legal and the <strong>prompt cache intact</strong> (ch.6). One detail: background delegation is <strong>process-local</strong> — if the process exits or you hit <span class="mono">/new</span>, unfinished subagents are discarded; for durable survival, use <span class="mono">cronjob</span> or <span class="mono">terminal(background=True, notify_on_complete=True)</span>.</p>
<p>String these chapters together and it gets clearer: delegation, compression (ch.15), and memory (ch.11) are <strong>three complementary routes</strong> against "limited context" — isolation <strong>keeps intermediate work outside the door</strong>, compression <strong>slims down history already inside</strong>, and memory <strong>sinks what deserves long-term retention into external storage</strong>. Delegation picks "keep it outside": the cost is that the subagent can't see the parent's full picture and must stand on its own from the brief; the benefit is that both the parent window and the parent cache are left <strong>completely untouched</strong>. When a task's intermediate volume is large yet independent, delegation almost always beats stuffing it into the parent conversation and compressing later.</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">parent calls <span class="mono">delegate_task(goal=…)</span> or batch <span class="mono">tasks=[…]</span> (up to max_concurrent_children=3 in parallel)</span></div>
  <div class="step"><span class="num">2</span><span class="sc">construct the child AIAgent: ephemeral_system_prompt (just goal+context) + skip_context_files/memory + fresh budget</span></div>
  <div class="step"><span class="num">3</span><span class="sc">the subagent runs in an <strong>independent context + terminal</strong>; intermediate tool results stay in the child context</span></div>
  <div class="step"><span class="num">4</span><span class="sc">only the <strong>final summary</strong> is returned to the parent (the parent's context window stays clean)</span></div>
  <div class="step"><span class="num">5</span><span class="sc">background: the completion event goes to the shared queue → surfaces as a new turn when the parent is <strong>idle</strong> → strict alternation + cache intact</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "isolate without breaking the cache"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: <strong>delegate_task</strong> (single/batch entry), the <strong>child AIAgent isolated construction</strong> (ephemeral prompt + skip flags), <strong>DELEGATE_BLOCKED_TOOLS + role demotion</strong>, the <strong>async_delegation completion queue</strong>. Cross-chapter teamwork: <span class="mono">delegate_task</span> is a special <strong>tool</strong> (ch.8, and leaf disables it to prevent recursion); the subagent's <span class="mono">skip_context_files</span> / <span class="mono">skip_memory</span> mean it doesn't inherit the parent's three-tier system prompt or memory (ch.6/11); the completion queue <strong>surfaces only as a new turn when idle</strong>, keeping strict role alternation (ch.7) + the cache (ch.6); context isolation and ch.15's compression are <strong>two different routes</strong> against "limited context" (isolate vs compress).
  <div class="collab-sub">② Data-flow timing</div>
  parent calls delegate_task → construct the child AIAgent (isolate conversation history/context files/memory, inherit runtime) → the subagent runs independently, intermediate results stay in the child context → return only the summary to the parent → (background) the completion event goes to the shared queue → surfaces as a new turn when the parent is idle.
  <div class="collab-sub">③ The key point</div>
  Delegation <strong>locks the context-flooding intermediate work inside the subagent's independent context</strong>, and the parent receives only a summary — protecting both the parent's context window and (via the queue's idle re-entry) the parent's cache. This is how "scaling" coexists with "the cache is sacred": <strong>isolate the complexity to the edges</strong>.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>context isolation + return only the summary + a completion queue that doesn't break the cache</strong>. It treats two inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">A·lost-in-the-middle</span> — a subtask's flood of intermediate tool results would <strong>bury</strong> the parent context and push key info into the forgotten middle; delegation <strong>isolates</strong> them in the child context, so the parent receives only a high-signal summary;
  <span class="badge constraint">F·error accumulation</span> — each subagent gets a <strong>fresh budget + independent context</strong>, avoiding cross-task state pollution and compounding errors. The anti-pattern: streaming the subagent's intermediate work back into the parent conversation live, or <strong>splicing</strong> the completion message into the middle of the conversation — the former floods context, the latter breaks alternation and shatters the cache.</p>
  <p style="margin:.5rem 0 0">Dig one level deeper to the root: delegation lets "scaling" coexist with "the cache is sacred" by <strong>locking complexity at the edge</strong> instead of smearing it through the core. A subagent is a single-use isolation pod — <span class="mono">platform="subagent"</span>, its own terminal session, discarded once done, its only output a summary returned to the parent. But isolation has a cost: background delegation is a <strong>process-local</strong> daemon thread; a process exit or <span class="mono">/new</span> discards it. For work that must <strong>survive across processes</strong>, switch to <span class="mono">cronjob</span> or <span class="mono">terminal(background=True, notify_on_complete=True)</span>. That's the clear-eyed trade-off between "fast but ephemeral" and "slow but durable."</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Context isolation</strong>: a subagent has its own conversation/terminal/toolset; <span class="mono">ephemeral_system_prompt</span> holds just goal+context, with <span class="mono">skip_context_files/memory</span>, returning only the summary.</li>
    <li><strong>Single / batch</strong>: <span class="mono">goal</span> for one task vs <span class="mono">tasks=[…]</span> for parallel batch; concurrency capped by <span class="mono">max_concurrent_children</span> (default 3).</li>
    <li><strong>leaf vs orchestrator</strong>: leaf (default) disables delegate_task/clarify/memory/send_message/execute_code; orchestrator retains delegation and can spawn workers (bounded by a nesting depth cap).</li>
    <li><strong>Background doesn't break the cache</strong>: the completion event goes to the shared queue and surfaces as a new turn when the parent is <strong>idle</strong>, keeping strict role alternation (ch.7) + the cache (ch.6).</li>
    <li><strong>Not durable</strong>: background delegation is process-local; process exit / <span class="mono">/new</span> discards it; for survival use <span class="mono">cronjob</span> or <span class="mono">terminal(background, notify_on_complete)</span>.</li>
  </ul>
</div>

<div class="figure">
<svg viewBox="0 0 680 490" role="img" aria-label="One real delegate_task call walked through: 1 call args goal/context/toolsets/role=leaf; 2 build the subagent isolating ephemeral_system_prompt, platform=subagent, skip_context_files, skip_memory, iteration_budget=None while inheriting base_url/api_key/model/session_db; 3 strip the five DELEGATE_BLOCKED_TOOLS and downgrade role to leaf; 4 the subagent reads about 20 files and all intermediate work stays in its own context, never reaching the parent; 5 the parent receives only one final summary, returning a delegation_id first when background.">
  <text x="340" y="22" text-anchor="middle" font-size="13.5" font-weight="700" fill="var(--ink)">One real delegate_task call - args to isolated build to one summary</text>
  <text x="340" y="40" text-anchor="middle" font-size="10" fill="var(--muted)">Example: dispatch a leaf subagent to audit scoped locks across gateway adapters</text>
  <text x="628" y="32" font-size="22">🧩</text>

  <rect x="20" y="50" width="640" height="60" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="32" y="68" font-size="10" font-weight="700" fill="var(--blue)">1. Call - tools/delegate_tool.py</text>
  <text x="32" y="86" font-size="9" font-family="monospace" fill="var(--ink)">delegate_task(goal=&quot;audit gateway/platforms/ adapters whose connect() lacks acquire_scoped_lock&quot;,</text>
  <text x="32" y="102" font-size="9" font-family="monospace" fill="var(--ink)">  context=&quot;pattern: irc/adapter.py&quot;, toolsets=[&quot;terminal&quot;,&quot;file&quot;,&quot;search&quot;], role=&quot;leaf&quot;)</text>

  <line x1="340" y1="110" x2="340" y2="126" stroke="var(--line)" stroke-width="2"/>
  <path d="M340 132 L334 122 L346 122 Z" fill="var(--line)"/>

  <text x="340" y="146" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--ink)">2. Build the subagent - isolate vs inherit (:1234-1249)</text>

  <rect x="20" y="154" width="324" height="118" rx="9" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="34" y="172" font-size="10" font-weight="700" fill="var(--accent-ink)">Isolated - not in conversation / cache prefix</text>
  <text x="34" y="190" font-size="9" font-family="monospace" fill="var(--ink)">ephemeral_system_prompt=child_prompt</text>
  <text x="34" y="206" font-size="9" font-family="monospace" fill="var(--ink)">platform=&quot;subagent&quot;</text>
  <text x="34" y="222" font-size="9" font-family="monospace" fill="var(--ink)">skip_context_files=True</text>
  <text x="34" y="238" font-size="9" font-family="monospace" fill="var(--ink)">skip_memory=True</text>
  <text x="34" y="256" font-size="9" font-family="monospace" fill="var(--purple)">iteration_budget=None  # fresh budget per subagent</text>

  <rect x="356" y="154" width="304" height="118" rx="9" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="2"/>
  <text x="370" y="172" font-size="10" font-weight="700" fill="var(--blue)">Inherited - runtime only, not conversation</text>
  <text x="370" y="190" font-size="9" font-family="monospace" fill="var(--ink)">base_url / api_key</text>
  <text x="370" y="206" font-size="9" font-family="monospace" fill="var(--ink)">model / fallback_model</text>
  <text x="370" y="222" font-size="9" font-family="monospace" fill="var(--ink)">session_db (shared session store)</text>
  <text x="370" y="246" font-size="9" fill="var(--muted)">Runtime creds copied, but conversation /</text>
  <text x="370" y="260" font-size="9" fill="var(--muted)">context files / memory NOT inherited - cache safe</text>

  <rect x="20" y="282" width="640" height="74" rx="9" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="32" y="300" font-size="10" font-weight="700" fill="var(--red)">3. Strip dangerous tools + role downgrade - :768 / :45-53 / :1023-1024</text>
  <text x="32" y="318" font-size="9" font-family="monospace" fill="var(--ink)">child_toolsets = _strip_blocked_tools(child_toolsets)</text>
  <text x="32" y="334" font-size="9" font-family="monospace" fill="var(--red)">x DELEGATE_BLOCKED_TOOLS(5): delegate_task · clarify · memory · send_message · execute_code</text>
  <text x="32" y="350" font-size="9" font-family="monospace" fill="var(--purple)">effective_role = role if (role==&quot;orchestrator&quot; and orchestrator_ok) else &quot;leaf&quot;</text>

  <rect x="20" y="366" width="324" height="92" rx="9" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="34" y="384" font-size="10" font-weight="700" fill="var(--muted)">4. Subagent's own context (never reaches parent)</text>
  <text x="34" y="404" font-size="9" fill="var(--ink)">reads ~20 adapter.py · search/grep · dozens of retries</text>
  <text x="34" y="422" font-size="9" fill="var(--ink)">all intermediate tool results stay in child context</text>
  <text x="34" y="440" font-size="9" fill="var(--muted)">platform=&quot;subagent&quot; · discarded when done</text>

  <rect x="356" y="366" width="304" height="92" rx="9" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="370" y="384" font-size="10" font-weight="700" fill="var(--accent-ink)">5. Parent gets only one final summary</text>
  <text x="370" y="404" font-size="9" fill="var(--ink)">&quot;audited 21 adapters: matrix/sms lack lock;</text>
  <text x="370" y="420" font-size="9" fill="var(--ink)"> 19 others compliant&quot;</text>
  <text x="370" y="440" font-size="9" fill="var(--purple)">background=true returns delegation_id first (:2592)</text>

  <rect x="20" y="466" width="640" height="20" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="340" y="480" text-anchor="middle" font-size="9" fill="var(--muted)">Read this: one delegate_task = inherit runtime + isolate conversation/files/memory + strip 5 tools to leaf; parent gets one summary, cache untouched</text>
</svg>
<div class="fig-cap"><b>One real delegate_task</b>: the parent calls <span class="mono">delegate_task(goal,context,toolsets,role=&quot;leaf&quot;)</span> -&gt; the subagent is built <b>isolated</b> (<span class="mono">ephemeral_system_prompt</span> / <span class="mono">platform=&quot;subagent&quot;</span> / <span class="mono">skip_context_files</span> / <span class="mono">skip_memory</span> / <span class="mono">iteration_budget=None</span>) while <b>inheriting</b> base_url/api_key/model/session_db; it strips the five <span class="mono">DELEGATE_BLOCKED_TOOLS</span> and downgrades role to leaf; reading ~20 files, <b>all intermediate work stays in the child context</b>, and the parent gets only the summary "audited 21 adapters: matrix/sms lack lock; 19 others compliant" (background returns a <span class="mono">delegation_id</span> first).</div>
</div>
""",
}

LESSON_14 = {
    "zh": r"""
<p class="lead">
第 13 章给了你一把「上下文隔离的锤子」——<span class="mono">delegate_task</span>。但「先规划后执行」「让独立的人审查」这些复杂工作流，Hermes 的委派层<strong>并没有内建</strong>。这恰恰是本章最值得讲的设计取舍：Hermes <strong>不</strong>把规划/执行/审查做进核心，而是用<strong>技能编排 delegate_task 的隔离能力</strong>，在边缘搭出「生成者-验证者分离」。核心只提供一条原语（隔离的子代理），复杂度留给技能——这是窄腰哲学（第 4 章）在多代理协作上的体现。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 同行评审 / 第三方审计</div>
  没有哪个作者该<strong>自己审自己的论文</strong>——他对自己的疏漏有盲点。学术界的办法是<strong>同行评审</strong>：找一个<strong>没参与写作</strong>的人，只给他论文（不给你的草稿笔记、不给你的辩解），让他用<strong>全新的眼睛</strong>挑错。代码也一样：实现者、审查者、修复者是<strong>三个独立的人</strong>，各自<strong>全新的上下文</strong>。Hermes 把这套「独立验证」用 <span class="mono">delegate_task</span> 的上下文隔离实现——审查者拿到的<strong>只有 diff</strong>，<strong>不</strong>共享实现者的上下文。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 生成-验证分离的核心是「独立 context」</div>
  一条原则统领本章：<strong>没有 agent 应该验证自己的工作</strong>（<span class="inline">No agent should verify its own work</span>）。为什么？模型对自己刚生成的东西有<strong>确认偏误</strong>，还容易<strong>谄媚附和</strong>。对策是<strong>用全新的 context 来验证</strong>——验证者不知道生成者「想证明什么」，只看结果。Hermes 没有把这做成委派工具的内建流程，而是<strong>三个技能</strong>各司其职：<span class="mono">plan</span>（纯规划）、<span class="mono">subagent-driven-development</span>（执行 + 两阶段审查）、<span class="mono">requesting-code-review</span>（独立审查 + 自动修复）。其中<strong>执行/审查两个</strong>技能<strong>调用 delegate_task 的隔离能力</strong>制造「全新 context」（<span class="mono">plan</span> 只产出计划、本身不委派）。
</div>

<h2>Hermes 唯一内建的验证倾向：子代理自报不可全信</h2>
<p>委派工具<strong>本身</strong>只内建了一条验证指令——提醒父代理：子代理的摘要是<strong>自报</strong>，不是已核实的事实：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/delegate_tool.py</span><span class="ln">2923-2929 · 节选（工具描述）</span></div>
  <pre>- Subagent summaries are SELF-REPORTS, not verified facts. A subagent
  that claims "uploaded successfully" or "file written" may be wrong.
  For operations with external side-effects (HTTP POST/PUT, remote
  writes, file creation at shared paths, publishing), require the subagent to return a
  verifiable handle (URL, ID, absolute path, HTTP status) and verify it
  yourself -- fetch the URL, stat the file, read back the content --
  before telling the user the operation succeeded.</pre>
</div>
<p>这条指令对抗 <span class="badge constraint">C·幻觉</span>——子代理可能<strong>真诚地</strong>报告「上传成功」，但其实没有。所以涉及外部副作用时，要求子代理返回一个<strong>可验证的把手</strong>（URL / ID / 路径 / HTTP 状态），父代理<strong>自己去验</strong>（拉取 URL、stat 文件、读回内容）。这是委派层<strong>唯一</strong>的内建验证倾向；更复杂的「独立审查」流程，则交给技能。</p>
<p>为什么这条<strong>唯一</strong>的内建验证倾向只是工具描述里的一句<strong>散文提示</strong>，而不是写死在代码里的强制校验？因为要强制「凡有副作用必须核验」，核心就得<strong>枚举</strong>哪些操作算副作用——HTTP、远程写、发布、共享路径写……这张清单永远列不全，还会把窄腰（第 4 章）撑肿。Hermes 的取舍是把判断权留给模型，只在 schema 里放一句话。代价是<strong>提示可能被忽略</strong>，且这句话每轮 API 调用都随工具描述发出去（第 6 章的 token 成本）；收益是核心不必维护一张脆弱、永远不全的副作用清单。这正是窄腰哲学的微观落地——<strong>能用一句提示解决的，绝不写成状态机</strong>。</p>
<p>为什么偏偏要「可验证把手」（URL / ID / 路径 / HTTP 状态），而不直接信子代理的自然语言摘要？因为摘要是<strong>生成者自己产出的文本</strong>，拿它去印证它自己是<strong>循环论证</strong>——这正是「没有 agent 该验证自己」在单次委派里的缩影。把手不一样：它是一个<strong>外部锚点</strong>，父代理能<strong>独立地</strong>重新求值（拉 URL、stat 文件、读回内容），用<strong>客观的地面真值</strong>而非生成者的说辞来判定成败。于是即便在一次普通委派内部，也悄悄复现了「生成者产出、验证者对地面真值核验」的分离结构，正面对抗 <span class="badge constraint">C·幻觉</span>。</p>

<h2>核心原则：没有 agent 该验证自己的工作</h2>
<p>真正的「独立审查」在 <span class="mono">requesting-code-review</span> 技能里。它的核心原则只有一句话，却是整套设计的地基：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">skills/…/requesting-code-review/SKILL.md</span><span class="ln">19 / 125-198 · 节选</span></div>
  <pre><span class="cm"># Core principle</span>
No agent should verify its own work. Fresh context finds what you miss.

<span class="cm"># Step 5 — Independent reviewer subagent</span>
The reviewer gets ONLY the diff and static scan results.
No shared context with the implementer. Fail-closed.

<span class="cm"># Step 7 — Auto-fix loop</span>
Spawn a THIRD agent context -- not you (the implementer), not the reviewer.</pre>
</div>
<p>三个角色、三个<strong>独立 context</strong>：实现者写代码、审查者<strong>只看 diff</strong>（不共享实现者上下文）、修复者是<strong>第三个</strong>全新 context。审查者「fail-closed」——解析不了的回复一律判失败，绝不放水。通过的提交打上 <span class="mono">[verified]</span> 前缀，标明「一个独立审查者批准了它」。这套「独立性」正是对 <span class="badge constraint">F·误差累积</span> 与<strong>谄媚自我背书</strong>的工程对策——它不靠在 prompt 里写「别谄媚」，而靠<strong>结构上的 context 隔离</strong>。</p>
<p>为什么审查者要<strong>fail-closed</strong>（解析不了一律判失败），而不是「拿不准就放过」？因为两种错误的代价<strong>极不对称</strong>：漏掉一个真 bug（假阴性）会滚进后续任务、事后调试昂贵；多跑一轮修复（假阳性）只是浪费几次调用。验证系统的默认必须<strong>偏向抓住</strong>。所以 reviewer 的 JSON 规则写死：security_concerns 非空→passed=false、解析不了→passed=false，只有<strong>两个列表都空</strong>才算过。这条「宁可错杀」的偏置和第 22 章评测把关同源——质量门要么明确放行、要么默认拦下，绝不在模糊地带<strong>默默通过</strong>。</p>
<p>为什么审查者<strong>只</strong>拿 diff 和静态扫描结果，<strong>不</strong>给实现者的思路与上下文？多给点信息不是更好判断吗？恰恰相反：实现者的<strong>自辩</strong>正是要隔离掉的污染源。一旦 reviewer 看到「我之所以这么写是因为……」，它就<strong>继承</strong>了实现者的框架和确认偏误，开始审「<strong>那个故事</strong>」而非「<strong>代码本身</strong>」。全新 context 带来的是<strong>对抗性的独立</strong>——审查者不知道生成者想证明什么，只能照着结果挑错。这条隔离靠的是第 13 章 <span class="mono">delegate_task</span> 的上下文隔离原语，正呼应第 24 章「绝不让概率模型给自己当裁判」。</p>
<p>那个打在提交上的 <span class="mono">[verified]</span> 前缀，承载的到底是什么信任？它不是「这段代码绝对正确」的保证，而是一个<strong>过程性的事实标记</strong>——「<strong>一个与实现者无共享上下文的独立审查者批准了它</strong>」。区别很关键：前者是对结果的断言（概率模型给不了），后者是对<strong>流程</strong>的断言（结构上可保证）。Hermes 反复用这种手法把「不可信的判断」换成「可信的过程」：不去赌模型这次没编，而是确保<strong>编没编由另一个独立 context 来核</strong>。同样的把手在委派层是「可验证 handle」，在审查层就是这个 <span class="mono">[verified]</span> 标记——都把信任<strong>从生成者的自我宣称挪到外部可核验的锚点上</strong>。</p>

<div class="figure">
<svg viewBox="0 0 680 340" role="img" aria-label="生成-验证分离：生成者产出 diff 与自我汇报，自报被墙挡住，独立验证者只拿 diff 在全新 context 里对照原始要求核验">
  <text x="340" y="24" text-anchor="middle" font-size="13.5" font-weight="700" fill="var(--ink)">生成-验证分离 · 没有 agent 该验证自己的工作</text>

  <rect x="20" y="44" width="220" height="150" rx="10" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="130" y="66" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--blue)">① 生成者 · 实现子代理</text>
  <rect x="36" y="80" width="188" height="34" rx="7" fill="var(--panel)" stroke="var(--blue)"/>
  <text x="130" y="101" text-anchor="middle" font-size="11.5" fill="var(--ink)">产出：diff / 实现</text>
  <rect x="36" y="122" width="188" height="34" rx="7" fill="var(--panel)" stroke="var(--red)" stroke-dasharray="4 3"/>
  <text x="130" y="143" text-anchor="middle" font-size="11.5" fill="var(--red)">『我做完了』自我汇报</text>
  <text x="130" y="180" text-anchor="middle" font-size="10.5" fill="var(--muted)">对自己有确认偏误 · 易谄媚</text>

  <rect x="280" y="40" width="58" height="200" rx="6" fill="var(--red-soft)" stroke="var(--red)" stroke-width="2"/>
  <text x="302" y="140" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--red)" transform="rotate(90 302 140)">SELF-REPORTS 不可信</text>
  <text x="322" y="140" text-anchor="middle" font-size="11" fill="var(--red)" transform="rotate(90 322 140)">不共享 context</text>

  <text x="309" y="88" text-anchor="middle" font-size="10" fill="var(--blue)">✓ 仅传 diff</text>
  <line x1="224" y1="97" x2="372" y2="97" stroke="var(--blue)" stroke-width="2"/>
  <path d="M372 97 L363 92 L363 102 Z" fill="var(--blue)"/>
  <line x1="224" y1="139" x2="278" y2="139" stroke="var(--red)" stroke-width="2" stroke-dasharray="4 3"/>
  <text x="289" y="145" text-anchor="middle" font-size="16" font-weight="700" fill="var(--red)">✕</text>

  <rect x="378" y="44" width="282" height="196" rx="10" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="519" y="66" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--purple)">② 验证者 · 独立 fresh context</text>
  <text x="394" y="92" font-size="11.5" fill="var(--ink)">• 只拿 diff（不共享实现者上下文）</text>
  <text x="394" y="116" font-size="11.5" fill="var(--ink)">• 对照原始要求做符合性判断</text>
  <text x="394" y="140" font-size="11.5" fill="var(--ink)">• 要求可验证把手：URL/ID/路径/HTTP</text>
  <text x="394" y="164" font-size="11.5" fill="var(--ink)">• fail-closed：拿不准 → 判 false</text>
  <rect x="394" y="184" width="120" height="34" rx="7" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="454" y="205" text-anchor="middle" font-size="11" fill="var(--accent-ink)">PASS → [verified]</text>
  <rect x="524" y="184" width="120" height="34" rx="7" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="584" y="205" text-anchor="middle" font-size="11" fill="var(--red)">REQUEST_CHANGES</text>

  <text x="340" y="276" text-anchor="middle" font-size="12" font-weight="700" fill="var(--ink)">绝不让生成者自证 · 信任从「自我宣称」挪到「外部可核验锚点」</text>
  <rect x="150" y="290" width="186" height="30" rx="8" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="243" y="310" text-anchor="middle" font-size="11" fill="var(--amber)">治 C·幻觉（真诚误报）</text>
  <rect x="346" y="290" width="186" height="30" rx="8" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="439" y="310" text-anchor="middle" font-size="11" fill="var(--amber)">治 F·误差累积（自证盲点）</text>
</svg>
<div class="fig-cap"><b>生成-验证分离</b>：生成者（实现子代理）产出 diff，并附一句「我做完了」的<b>自我汇报</b>；中间一道墙挡住<b>不可信的自报</b>——验证者<b>只</b>拿 diff、不共享其上下文，在<b>独立的 fresh context</b> 里对照<b>原始要求</b>做符合性判断，并要求<b>可验证把手</b>（URL/ID/路径/HTTP）而非口头摘要。绝不让生成者自证，正面治 <b>C·幻觉</b>（真诚误报）与 <b>F·误差累积</b>（自证盲点）。</div>
</div>

<h2>两阶段审查：spec 合规 + 代码质量</h2>
<p><span class="mono">subagent-driven-development</span> 技能把审查拆成两阶段，每阶段一个独立 reviewer：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">optional-skills/…/subagent-driven-development/SKILL.md</span><span class="ln">20 / 92-148 / 246-253 · 节选</span></div>
  <pre><span class="cm"># Core principle</span>
Fresh subagent per task + two-stage review (spec then quality).

<span class="cm"># Step 2 — Spec Compliance Reviewer</span>
OUTPUT: PASS or list of specific spec gaps to fix.

<span class="cm"># Step 3 — Code Quality Reviewer</span>
Verdict: APPROVED or REQUEST_CHANGES.

<span class="cm"># Why two-stage: catches issues before they compound across tasks.</span></pre>
</div>
<p>先查<strong>是否符合 spec</strong>（PASS / 列出差距），再查<strong>代码质量</strong>（APPROVED / REQUEST_CHANGES）。为什么值得多花这些验证调用？技能里写得很实在：<strong>「在错误跨任务累积之前抓住它们」</strong>——这正是<strong>生成-验证差</strong>的工程化：验证一个结果比从头生成它<strong>便宜</strong>，多花的审查调用，换来的是不必事后调试「滚雪球式」的复合错误。这是对 <span class="badge constraint">F·误差累积</span> 的直接对策。</p>
<p>为什么要拆成<strong>两个</strong>阶段、还要强制「spec 过了才查质量」的<strong>顺序</strong>？因为这两关抓的是<strong>正交</strong>的两类失败：spec 合规查的是「<strong>做错了东西</strong>」（少做、多做、scope creep），代码质量查的是「<strong>东西做错了</strong>」（bug、风格、边界）。若先查质量，就可能在<strong>压根跑偏</strong>的代码上白白打磨。这个顺序编码了一条成本梯度——<strong>越早抓越省的，越靠前查</strong>。技能的红线里也明文写着「spec 合规 PASS 之前别开质量审查（顺序错了）」。先确认方向对、再投入精修，把宝贵的验证调用花在刀刃上。</p>
<p>那为什么值得给每个任务都付「实现者 + 两个审查者 +（可能的）修复者」这么多次调用？根子在<strong>生成-验证差</strong>：核验一个结果比从头重造它便宜，而错误会<strong>跨任务复合</strong>——任务 3 建在错的任务 1 上，调试代价是相乘而非相加。技能自己的「cost trade-off」也直说：调用是多了，但「比事后调试滚雪球式的复合问题便宜」。这也解释了为什么要<strong>每任务全新子代理</strong>——不让上一个任务的错误状态污染下一个。它和第 15 章压缩（靠限制上下文增长压制 F）一前一后，合成一条<strong>质量防线</strong>，共同对抗 <span class="badge constraint">F·误差累积</span>。</p>

<div class="figure">
<svg viewBox="0 0 680 280" role="img" aria-label="两阶段审查强制顺序：先 spec 合规审查，PASS 后才进入代码质量审查，整套 fail-closed">
  <text x="340" y="24" text-anchor="middle" font-size="13.5" font-weight="700" fill="var(--ink)">两阶段审查 · 强制顺序：spec 合规 → 质量</text>

  <rect x="24" y="44" width="266" height="116" rx="10" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="157" y="68" text-anchor="middle" font-size="13" font-weight="700" fill="var(--blue)">① spec 合规审查</text>
  <text x="157" y="92" text-anchor="middle" font-size="11.5" fill="var(--ink)">问：做对了东西吗？</text>
  <text x="157" y="112" text-anchor="middle" font-size="10.5" fill="var(--muted)">抓 under/over-build · scope creep</text>
  <rect x="44" y="124" width="226" height="28" rx="7" fill="var(--panel)" stroke="var(--blue)"/>
  <text x="157" y="143" text-anchor="middle" font-size="11" fill="var(--ink)">OUTPUT: PASS / 列出 spec 差距</text>

  <line x1="290" y1="92" x2="388" y2="92" stroke="var(--accent)" stroke-width="2.5"/>
  <path d="M388 92 L379 87 L379 97 Z" fill="var(--accent)"/>
  <rect x="300" y="100" width="78" height="24" rx="12" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="339" y="116" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--accent-ink)">仅当 PASS</text>

  <rect x="390" y="44" width="266" height="116" rx="10" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="523" y="68" text-anchor="middle" font-size="13" font-weight="700" fill="var(--purple)">② 代码质量审查</text>
  <text x="523" y="92" text-anchor="middle" font-size="11.5" fill="var(--ink)">问：东西做对了吗？</text>
  <text x="523" y="112" text-anchor="middle" font-size="10.5" fill="var(--muted)">抓 bug · 风格 · 边界</text>
  <rect x="410" y="124" width="226" height="28" rx="7" fill="var(--panel)" stroke="var(--purple)"/>
  <text x="523" y="143" text-anchor="middle" font-size="11" fill="var(--ink)">Verdict: APPROVED / REQUEST_CHANGES</text>

  <text x="340" y="184" text-anchor="middle" font-size="11" fill="var(--muted)">顺序锁死：方向错了，不在跑偏的代码上浪费质量审查</text>
  <rect x="24" y="198" width="632" height="62" rx="10" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="340" y="220" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--red)">fail-closed · 默认拦下</text>
  <text x="340" y="242" text-anchor="middle" font-size="11" fill="var(--ink)">无法解析 → passed=false　·　security_concerns 非空 → passed=false　·　两列表皆空才算过</text>
</svg>
<div class="fig-cap"><b>两阶段审查 · 强制顺序</b>：先 spec 合规审查（「做对了东西吗？」，PASS 或列出差距），<b>PASS 后才</b>进入质量审查（「东西做对了吗？」，APPROVED/REQUEST_CHANGES）。两关抓<b>正交</b>的失败类，顺序锁死避免在跑偏的代码上白磨；整套 <b>fail-closed</b>——无法解析或有安全顾虑一律判 false，只有两个列表都空才放行。</div>
</div>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc"><strong>规划</strong>：<span class="mono">plan</span> 技能——纯规划、禁止执行，产出 markdown 计划到 .hermes/plans/</span></div>
  <div class="step"><span class="num">2</span><span class="sc"><strong>执行</strong>：<span class="mono">subagent-driven-development</span> 每个任务派 fresh implementer 子代理（delegate_task 隔离）</span></div>
  <div class="step"><span class="num">3</span><span class="sc"><strong>两阶段审查</strong>：spec 合规 reviewer（PASS/gaps）→ 代码质量 reviewer（APPROVED/REQUEST_CHANGES），各自独立 context</span></div>
  <div class="step"><span class="num">4</span><span class="sc"><strong>独立审查 + 修复</strong>：<span class="mono">requesting-code-review</span> 审查者只看 diff、修复者是第三个 context → 提交打 [verified]</span></div>
  <div class="step"><span class="num">5</span><span class="sc">全程靠 delegate_task 的<strong>上下文隔离</strong>制造「全新 context」，核心不内建任何 plan/execute/review 状态机</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「生成-验证分离」</div>
  <div class="collab-sub">① 组件清单（★本章核心，其余跨章节配合）</div>
  本章核心：委派工具的<strong>「self-reports, verify yourself」</strong>指令（唯一内建）、<span class="mono">plan</span> 技能（纯规划）、<span class="mono">subagent-driven-development</span>（执行 + 两阶段审查）、<span class="mono">requesting-code-review</span>（独立 reviewer + auto-fix）。跨章节配合：所有「独立 context」都靠 <strong>delegate_task 的上下文隔离</strong>（第 13 章）制造；这些工作流是<strong>技能</strong>（第 9 章程序性记忆），而非核心内建——正是<strong>窄腰</strong>（第 4 章）；<span class="mono">background_review.py</span> 是「每轮后 fork 评估存不存技能/记忆」的自改进（第 9 章），<strong>不是</strong>委派审查，别混用。
  <div class="collab-sub">② 数据流时序</div>
  plan 技能产出计划 → subagent-driven-development 派 implementer 子代理执行 → spec 合规 reviewer（独立 context，只看实现 vs spec）→ 代码质量 reviewer（独立 context）→ requesting-code-review 派审查者（只看 diff）→ 不通过则第三个 context 修复 → [verified] 提交。
  <div class="collab-sub">③ 关键点</div>
  Hermes 没把「规划/执行/审查」做成委派的内建状态机，而是用<strong>三个技能编排 delegate_task 的隔离原语</strong>。核心保持窄：只提供「隔离的子代理」一条原语；复杂的多代理工作流<strong>在边缘（技能）演化</strong>，可被替换、可被扩展，而核心不动。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线：<strong>生成-验证分离靠「独立 context」，工作流用技能编排委派原语（窄腰）</strong>。它治两条 LLM 固有约束：
  <p style="margin:.5rem 0 0"><span class="badge constraint">F·误差累积</span>——模型对自己的输出有确认偏误、易谄媚自我背书；用<strong>独立 context 的验证者</strong>（不靠 prompt 写「别谄媚」，靠结构隔离）+ 两阶段审查「在错误复合前抓住」；
  <span class="badge constraint">C·幻觉</span>——子代理可能真诚地误报「成功」，故内建「self-reports, verify yourself」要求可验证把手。反模式：让生成者<strong>自己审自己</strong>（盲点 + 谄媚）；或把规划/审查<strong>硬塞进核心</strong>（违背窄腰，复杂工作流应在技能层演化）。注：<strong>核心 prompt 并无显式 anti-sycophancy 指令</strong>，谄媚对策完全靠「独立验证者 + fresh context」的架构。</p>
  <p style="margin:.5rem 0 0">再往根上问一句：为什么不在核心系统提示里直接写一句「<strong>别谄媚、自己复查</strong>」，让生成者自查就完了？因为<strong>用提示去对抗模型自身的偏置不可靠</strong>——那个会谄媚的模型，正是读「别谄媚」那句话的同一个模型。<strong>架构胜过指令</strong>：结构隔离<strong>从根上拿掉了自我背书的机会</strong>，而不是礼貌地请它别这么做。这是 Hermes 反复出现的模式（第 24 章）——<strong>绝不信任概率模型给自己当警察</strong>，而是把护栏建在它<strong>周围的确定性结构</strong>里。这也是窄腰的另一面：把工作流留在技能层的代价是它<strong>opt-in</strong>（得由 agent 主动触发技能），换来的是核心 schema 不为每次委派都背上一台 plan/execute/review 状态机。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>委派层无内建审查</strong>：规划/执行/审查不是 delegate_task 的内建状态机，而是<strong>三个技能</strong>（plan / subagent-driven-development / requesting-code-review）编排 delegate_task 隔离能力。</li>
    <li><strong>唯一内建验证倾向</strong>：工具描述的「Subagent summaries are SELF-REPORTS... verify it yourself」，要求可验证把手（URL/ID/路径/HTTP 状态）。</li>
    <li><strong>核心原则</strong>：<span class="inline">No agent should verify its own work. Fresh context finds what you miss</span>——实现/审查/修复三个独立 context。</li>
    <li><strong>两阶段审查</strong>：spec 合规（PASS/gaps）+ 代码质量（APPROVED/REQUEST_CHANGES），「在错误复合前抓住」——生成-验证差的工程化。</li>
    <li><strong>谄媚对策靠结构</strong>：核心 prompt 无 anti-sycophancy 指令；靠「独立验证者 + fresh context」的 context 隔离对抗自我背书。</li>
  </ul>
</div>

<div class="figure">
<svg viewBox="0 0 680 486" role="img" aria-label="同一份 diff config.py:45 把 == 改成 != 走两条独立路径：自报路径里子代理自报上传成功，你按 self-reports verify yourself 实测得到 HTTP 503 判为 C 幻觉被驳；审查路径里 spec 合规审只拿 diff 判 PASS，PASS 后质量审判 REQUEST_CHANGES 未加回归测试；fail-closed 规则要求 security_concerns 非空或无法解析则 passed 为 false；只有通过后才打 verified 提交前缀。">
  <text x="340" y="22" text-anchor="middle" font-size="13.5" font-weight="700" fill="var(--ink)">同一份 diff，三个真实判定 · 自报被驳 / PASS / REQUEST_CHANGES</text>
  <text x="340" y="40" text-anchor="middle" font-size="10" fill="var(--muted)">例子：config.py:45 把 == 改成 !=，附一句「我做完了」的自报</text>
  <text x="628" y="32" font-size="22">⚖️</text>

  <rect x="20" y="50" width="640" height="68" rx="9" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="32" y="68" font-size="10" font-weight="700" fill="var(--ink)">① 共享输入 · 生成者交 diff + 自报</text>
  <text x="32" y="86" font-size="9" font-family="monospace" fill="var(--red)">- config.py:45    if val == expected:</text>
  <text x="360" y="86" font-size="9" font-family="monospace" fill="var(--accent-ink)">+ config.py:45    if val != expected:</text>
  <text x="32" y="106" font-size="9" fill="var(--muted)">附自报：✅ &quot;改完并已上传成功&quot;（一句 SELF-REPORT，未经核验）</text>

  <rect x="20" y="132" width="324" height="170" rx="9" fill="var(--red-soft)" stroke="var(--red)" stroke-width="2"/>
  <text x="34" y="150" font-size="10" font-weight="700" fill="var(--red)">路径 A · 自报被驳（:2923-2929）</text>
  <text x="34" y="170" font-size="9" fill="var(--ink)">② 工具描述铁律：Subagent summaries</text>
  <text x="34" y="184" font-size="9" font-family="monospace" fill="var(--ink)">are SELF-REPORTS, verify it yourself</text>
  <text x="34" y="204" font-size="9" fill="var(--ink)">自报：✅ 上传成功</text>
  <text x="34" y="222" font-size="9" fill="var(--ink)">→ 你 fetch URL 实测拿到把手：</text>
  <rect x="34" y="230" width="120" height="22" rx="5" fill="var(--panel)" stroke="var(--red)"/>
  <text x="94" y="245" text-anchor="middle" font-size="10" font-weight="700" fill="var(--red)">HTTP 503</text>
  <text x="34" y="272" font-size="9" fill="var(--muted)">须返可验证把手(URL/ID/路径/HTTP)</text>
  <text x="34" y="290" font-size="9.5" font-weight="700" fill="var(--red)">判定：C·幻觉（真诚误报）→ 驳回</text>

  <rect x="356" y="132" width="304" height="170" rx="9" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="2"/>
  <text x="370" y="150" font-size="10" font-weight="700" fill="var(--blue)">路径 B · 独立审查（两阶段顺序门）</text>
  <rect x="368" y="158" width="280" height="60" rx="7" fill="var(--panel)" stroke="var(--blue)"/>
  <text x="378" y="174" font-size="9" font-weight="700" fill="var(--blue)">③ spec 合规审 · 只拿 diff（:127-130）</text>
  <text x="378" y="190" font-size="9" fill="var(--ink)">reviewer 无生成者上下文，对照 spec</text>
  <rect x="378" y="196" width="78" height="18" rx="5" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="417" y="209" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--accent-ink)">PASS (:113)</text>
  <rect x="368" y="226" width="280" height="66" rx="7" fill="var(--panel)" stroke="var(--amber)"/>
  <text x="378" y="242" font-size="9" font-weight="700" fill="var(--amber)">④ 质量审 · 仅 PASS 后（:142-145）</text>
  <text x="378" y="258" font-size="9" fill="var(--ink)">Verdict: APPROVED / REQUEST_CHANGES</text>
  <rect x="378" y="264" width="200" height="20" rx="5" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="388" y="278" font-size="9.5" font-weight="700" fill="var(--amber)">REQUEST_CHANGES — 未加回归测试</text>

  <rect x="20" y="312" width="640" height="74" rx="9" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="32" y="330" font-size="10" font-weight="700" fill="var(--purple)">⑤ fail-closed · 解析失败 / 有顾虑一律 false（:138-140）</text>
  <text x="32" y="349" font-size="9" font-family="monospace" fill="var(--ink)">security_concerns non-empty -&gt; passed must be false</text>
  <text x="360" y="349" font-size="9" font-family="monospace" fill="var(--ink)">Cannot parse diff -&gt; passed must be false</text>
  <text x="32" y="368" font-size="9" font-family="monospace" fill="var(--purple)">{&quot;passed&quot;: false, &quot;security_concerns&quot;:[…], &quot;logic_errors&quot;:[…], &quot;summary&quot;:&quot;…&quot;}</text>
  <text x="32" y="382" font-size="9" fill="var(--muted)">只有 security_concerns 与 logic_errors 两列表都空，passed 才为 true</text>

  <rect x="20" y="396" width="640" height="40" rx="9" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="32" y="414" font-size="10" font-weight="700" fill="var(--accent-ink)">⑥ 全部通过后才打 [verified]（:230-236）</text>
  <text x="32" y="430" font-size="9" font-family="monospace" fill="var(--ink)">git add -A &amp;&amp; git commit -m &quot;[verified] &lt;description&gt;&quot;</text>

  <rect x="20" y="446" width="640" height="20" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="340" y="460" text-anchor="middle" font-size="9" fill="var(--muted)">读这张图：同一份 diff，自报路径被实测 503 驳回，审查路径 spec→PASS 再质量→REQUEST_CHANGES；无 agent 自证、fail-closed</text>
</svg>
<div class="fig-cap"><b>同一份 diff，三个真实判定</b>：生成者把 <span class="mono">config.py:45</span> 的 <span class="mono">==</span> 改成 <span class="mono">!=</span> 并自报「上传成功」。<b>路径 A</b>（自报）按工具铁律「summaries are SELF-REPORTS, verify it yourself」实测 → 拿到 <span class="mono">HTTP 503</span> → 判 <b>C·幻觉</b>驳回；<b>路径 B</b>（独立审查）spec 合规审只拿 diff → <span class="mono">PASS</span>，PASS 后质量审 → <span class="mono">REQUEST_CHANGES</span>（未加回归测试）。整套 <b>fail-closed</b>：<span class="mono">security_concerns</span> 非空或无法解析则 <span class="mono">passed=false</span>，全过才打 <span class="mono">[verified]</span>。</div>
</div>
""",
    "en": r"""
<p class="lead">
Ch.13 gave you a "context-isolation hammer" — <span class="mono">delegate_task</span>. But complex workflows like "plan first, execute later" and "have an independent party review" are <strong>not built into</strong> Hermes's delegation layer. That is exactly this chapter's notable trade-off: Hermes does <strong>not</strong> bake planning/execution/review into the core — it uses <strong>skills to orchestrate delegate_task's isolation</strong>, building "generator-verifier separation" at the edges. The core provides just one primitive (an isolated subagent); the complexity lives in skills — the narrow-waist philosophy (ch.4) applied to multi-agent collaboration.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · peer review / third-party audit</div>
  No author should <strong>review their own paper</strong> — they have blind spots about their own oversights. Academia's answer is <strong>peer review</strong>: find someone who <strong>wasn't involved</strong> in the writing, give them only the paper (not your draft notes, not your rationalizations), and let <strong>fresh eyes</strong> find the flaws. Code is the same: implementer, reviewer, fixer are <strong>three separate people</strong>, each with a <strong>fresh context</strong>. Hermes implements this "independent verification" via <span class="mono">delegate_task</span>'s context isolation — the reviewer gets <strong>only the diff</strong>, with <strong>no</strong> shared context with the implementer.
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture · generator-verifier separation rests on "independent context"</div>
  One principle governs this chapter: <strong>no agent should verify its own work</strong> (<span class="inline">No agent should verify its own work</span>). Why? A model has a <strong>confirmation bias</strong> about what it just generated, and is prone to <strong>sycophantic agreement</strong>. The countermeasure is <strong>verifying with a fresh context</strong> — the verifier doesn't know what the generator "wanted to prove," it only sees the result. Hermes doesn't make this a built-in flow of the delegation tool — instead <strong>three skills</strong> each play a part: <span class="mono">plan</span> (pure planning), <span class="mono">subagent-driven-development</span> (execution + two-stage review), <span class="mono">requesting-code-review</span> (independent review + auto-fix). The <strong>execution/review two</strong> of them <strong>call delegate_task's isolation</strong> to manufacture a "fresh context" (<span class="mono">plan</span> only produces a plan and doesn't delegate).
</div>

<h2>Hermes's only built-in verification leaning: subagent self-reports aren't trustworthy</h2>
<p>The delegation tool <strong>itself</strong> builds in just one verification instruction — reminding the parent that a subagent's summary is a <strong>self-report</strong>, not a verified fact:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/delegate_tool.py</span><span class="ln">2923-2929 · excerpt (tool description)</span></div>
  <pre>- Subagent summaries are SELF-REPORTS, not verified facts. A subagent
  that claims "uploaded successfully" or "file written" may be wrong.
  For operations with external side-effects (HTTP POST/PUT, remote
  writes, file creation at shared paths, publishing), require the subagent to return a
  verifiable handle (URL, ID, absolute path, HTTP status) and verify it
  yourself -- fetch the URL, stat the file, read back the content --
  before telling the user the operation succeeded.</pre>
</div>
<p>This instruction treats <span class="badge constraint">C·hallucination</span> — a subagent may <strong>sincerely</strong> report "uploaded successfully" when it didn't. So for external side-effects, require the subagent to return a <strong>verifiable handle</strong> (URL / ID / path / HTTP status), and the parent <strong>verifies it itself</strong> (fetch the URL, stat the file, read it back). This is the delegation layer's <strong>only</strong> built-in verification leaning; the more complex "independent review" flow is left to skills.</p>
<p>Why is this <strong>one</strong> built-in leaning merely a <strong>prose hint</strong> in the tool description rather than a hard, code-enforced check? Because hard-enforcing "verify every side-effect" would require the core to <strong>enumerate</strong> which operations count as side-effects — HTTP, remote writes, publishing, shared-path writes… that list is never complete and would bloat the narrow waist (ch.4). Hermes's trade-off: leave the judgment to the model and put one sentence in the schema. The cost is that <strong>the hint can be ignored</strong>, and it ships with the tool description on <strong>every</strong> API call (ch.6's token cost); the benefit is the core never maintains a brittle, forever-incomplete side-effect list. This is the narrow waist in miniature — <strong>if a sentence solves it, don't build a state machine</strong>.</p>
<p>Why insist on a <strong>verifiable handle</strong> (URL / ID / path / HTTP status) instead of trusting the subagent's natural-language summary? Because a summary is <strong>text the generator itself produced</strong>; using it to confirm itself is <strong>circular reasoning</strong> — the very miniature of "no agent should verify its own work" inside a single delegation. A handle is different: it's an <strong>external anchor</strong> the parent can <strong>independently</strong> re-derive (fetch the URL, stat the file, read it back), judging success against <strong>objective ground truth</strong> rather than the generator's say-so. So even within an ordinary delegation, the "generator produces, verifier checks against ground truth" separation quietly reappears, treating <span class="badge constraint">C·hallucination</span> head-on.</p>

<h2>The core principle: no agent should verify its own work</h2>
<p>The real "independent review" lives in the <span class="mono">requesting-code-review</span> skill. Its core principle is a single sentence, yet it's the foundation of the whole design:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">skills/…/requesting-code-review/SKILL.md</span><span class="ln">19 / 125-198 · excerpt</span></div>
  <pre><span class="cm"># Core principle</span>
No agent should verify its own work. Fresh context finds what you miss.

<span class="cm"># Step 5 — Independent reviewer subagent</span>
The reviewer gets ONLY the diff and static scan results.
No shared context with the implementer. Fail-closed.

<span class="cm"># Step 7 — Auto-fix loop</span>
Spawn a THIRD agent context -- not you (the implementer), not the reviewer.</pre>
</div>
<p>Three roles, three <strong>independent contexts</strong>: the implementer writes code, the reviewer <strong>sees only the diff</strong> (no shared context with the implementer), the fixer is a <strong>third</strong> fresh context. The reviewer is "fail-closed" — an unparseable response is judged a failure, never waved through. An approved commit gets a <span class="mono">[verified]</span> prefix, marking "an independent reviewer approved it." This "independence" is the engineering countermeasure to <span class="badge constraint">F·error accumulation</span> and <strong>sycophantic self-endorsement</strong> — it doesn't rely on writing "don't be sycophantic" in a prompt, but on <strong>structural context isolation</strong>.</p>
<p>Why is the reviewer <strong>fail-closed</strong> (an unparseable response is judged a failure) rather than "wave it through when unsure"? Because the two error costs are <strong>wildly asymmetric</strong>: missing a real bug (false negative) rolls into later tasks and is expensive to debug; running one extra fix cycle (false positive) merely wastes a few calls. A verification system's default must <strong>bias toward catching</strong>. That's why the reviewer's JSON rules are hard-coded: security_concerns non-empty → passed=false, can't parse → passed=false, passed=true <strong>only</strong> when both lists are empty. This "better safe than sorry" bias shares a root with ch.22's eval gating — a quality gate either explicitly passes or defaults to blocking, never <strong>silently passing</strong> in the ambiguous zone.</p>
<p>Why does the reviewer get <strong>only</strong> the diff and static-scan results, and <strong>not</strong> the implementer's reasoning or context? Wouldn't more information help it judge? Quite the opposite: the implementer's <strong>rationalizations</strong> are exactly the contamination you want to exclude. Once a reviewer sees "I wrote it this way because…", it <strong>inherits</strong> the implementer's framing and confirmation bias and starts reviewing <strong>the story</strong> rather than <strong>the code itself</strong>. A fresh context gives <strong>adversarial independence</strong> — the reviewer doesn't know what the generator wanted to prove, so it can only find flaws by the result. This isolation rests on ch.13's <span class="mono">delegate_task</span> context-isolation primitive, echoing ch.24's "never let the probabilistic model be its own judge."</p>
<p>What trust does that <span class="mono">[verified]</span> commit prefix actually carry? Not a guarantee that "this code is absolutely correct," but a <strong>process fact marker</strong> — "<strong>an independent reviewer with no shared context with the implementer approved it</strong>." The distinction matters: the former asserts a result (which a probabilistic model can't deliver), the latter asserts a <strong>process</strong> (which structure can guarantee). Hermes repeatedly swaps "untrustworthy judgment" for "trustworthy process": instead of betting the model didn't fabricate this time, it ensures <strong>whether it fabricated is checked by another independent context</strong>. The same handle is the "verifiable handle" at the delegation layer and this <span class="mono">[verified]</span> mark at the review layer — both move trust <strong>from the generator's self-claim to an externally checkable anchor</strong>.</p>

<div class="figure">
<svg viewBox="0 0 680 340" role="img" aria-label="Generator-verifier separation: the generator emits a diff and a self-report, the self-report is blocked by a wall, and an independent verifier takes only the diff and checks it against the original spec in a fresh context">
  <text x="340" y="24" text-anchor="middle" font-size="13.5" font-weight="700" fill="var(--ink)">Generator–verifier separation · no agent should verify its own work</text>

  <rect x="20" y="44" width="220" height="150" rx="10" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="130" y="66" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--blue)">① Generator · implementer</text>
  <rect x="36" y="80" width="188" height="34" rx="7" fill="var(--panel)" stroke="var(--blue)"/>
  <text x="130" y="101" text-anchor="middle" font-size="11.5" fill="var(--ink)">Produces: diff / implementation</text>
  <rect x="36" y="122" width="188" height="34" rx="7" fill="var(--panel)" stroke="var(--red)" stroke-dasharray="4 3"/>
  <text x="130" y="143" text-anchor="middle" font-size="11.5" fill="var(--red)">“I'm done” self-report</text>
  <text x="130" y="180" text-anchor="middle" font-size="10.5" fill="var(--muted)">confirmation bias · prone to sycophancy</text>

  <rect x="280" y="40" width="58" height="200" rx="6" fill="var(--red-soft)" stroke="var(--red)" stroke-width="2"/>
  <text x="302" y="140" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--red)" transform="rotate(90 302 140)">SELF-REPORTS untrusted</text>
  <text x="322" y="140" text-anchor="middle" font-size="11" fill="var(--red)" transform="rotate(90 322 140)">no shared context</text>

  <text x="309" y="88" text-anchor="middle" font-size="10" fill="var(--blue)">✓ diff only</text>
  <line x1="224" y1="97" x2="372" y2="97" stroke="var(--blue)" stroke-width="2"/>
  <path d="M372 97 L363 92 L363 102 Z" fill="var(--blue)"/>
  <line x1="224" y1="139" x2="278" y2="139" stroke="var(--red)" stroke-width="2" stroke-dasharray="4 3"/>
  <text x="289" y="145" text-anchor="middle" font-size="16" font-weight="700" fill="var(--red)">✕</text>

  <rect x="378" y="44" width="282" height="196" rx="10" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="519" y="66" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--purple)">② Verifier · independent fresh context</text>
  <text x="394" y="92" font-size="11.5" fill="var(--ink)">• gets only the diff (no shared context)</text>
  <text x="394" y="116" font-size="11.5" fill="var(--ink)">• checks compliance vs original spec</text>
  <text x="394" y="140" font-size="11.5" fill="var(--ink)">• demands handles: URL/ID/path/HTTP</text>
  <text x="394" y="164" font-size="11.5" fill="var(--ink)">• fail-closed: unsure → false</text>
  <rect x="394" y="184" width="120" height="34" rx="7" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="454" y="205" text-anchor="middle" font-size="11" fill="var(--accent-ink)">PASS → [verified]</text>
  <rect x="524" y="184" width="120" height="34" rx="7" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="584" y="205" text-anchor="middle" font-size="11" fill="var(--red)">REQUEST_CHANGES</text>

  <text x="340" y="276" text-anchor="middle" font-size="12" font-weight="700" fill="var(--ink)">never self-certify · trust moves from self-claim to external anchor</text>
  <rect x="138" y="290" width="200" height="30" rx="8" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="238" y="310" text-anchor="middle" font-size="11" fill="var(--amber)">treats C·hallucination</text>
  <rect x="348" y="290" width="200" height="30" rx="8" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="448" y="310" text-anchor="middle" font-size="11" fill="var(--amber)">treats F·error accumulation</text>
</svg>
<div class="fig-cap"><b>Generator–verifier separation</b>: the generator (implementer subagent) emits a diff plus an “I'm done” <b>self-report</b>; a wall blocks the <b>untrustworthy self-report</b> — the verifier gets <b>only</b> the diff, shares none of the generator's context, and in an <b>independent fresh context</b> judges compliance against the <b>original spec</b>, demanding <b>verifiable handles</b> (URL/ID/path/HTTP) rather than a prose summary. The generator never self-certifies, treating <b>C·hallucination</b> (sincere misreport) and <b>F·error accumulation</b> (self-cert blind spot) head-on.</div>
</div>

<h2>Two-stage review: spec compliance + code quality</h2>
<p>The <span class="mono">subagent-driven-development</span> skill splits review into two stages, each an independent reviewer:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">optional-skills/…/subagent-driven-development/SKILL.md</span><span class="ln">20 / 92-148 / 246-253 · excerpt</span></div>
  <pre><span class="cm"># Core principle</span>
Fresh subagent per task + two-stage review (spec then quality).

<span class="cm"># Step 2 — Spec Compliance Reviewer</span>
OUTPUT: PASS or list of specific spec gaps to fix.

<span class="cm"># Step 3 — Code Quality Reviewer</span>
Verdict: APPROVED or REQUEST_CHANGES.

<span class="cm"># Why two-stage: catches issues before they compound across tasks.</span></pre>
</div>
<p>First check <strong>spec compliance</strong> (PASS / list gaps), then <strong>code quality</strong> (APPROVED / REQUEST_CHANGES). Why spend these extra verification calls? The skill says it plainly: <strong>"catch issues before they compound across tasks."</strong> This is exactly the engineering of the <strong>generation-verification gap</strong>: verifying a result is <strong>cheaper</strong> than generating it from scratch, and the extra review calls buy you not having to debug "snowballing" compound errors later. A direct countermeasure to <span class="badge constraint">F·error accumulation</span>.</p>
<p>Why split it into <strong>two</strong> stages and enforce the <strong>order</strong> "quality only after spec PASS"? Because the two gates catch <strong>orthogonal</strong> failure classes: spec-compliance catches "<strong>built the wrong thing</strong>" (under-build, over-build, scope creep), code-quality catches "<strong>built the thing wrong</strong>" (bugs, style, edge cases). Running quality first risks polishing code that is <strong>entirely off-target</strong>. The ordering encodes a cost gradient — <strong>what's cheapest if caught early goes first</strong>. The skill's own red flags say it outright: "don't start code-quality review before spec compliance is PASS (wrong order)." Confirm the direction is right, then invest in polish, spending precious verification calls where they count.</p>
<p>So why is it worth paying "implementer + two reviewers + (maybe) a fixer" per task? The root is the <strong>generation-verification gap</strong>: verifying a result is cheaper than regenerating it, and errors <strong>compound across tasks</strong> — task 3 built on a wrong task 1 multiplies, not adds, the debugging cost. The skill's own "cost trade-off" note says it plainly: more invocations, but "cheaper than debugging compounded problems later." It also explains the <strong>fresh subagent per task</strong> — don't let the previous task's wrong state pollute the next. Together with ch.15's compression (which fights F by bounding context growth), it forms a <strong>quality defense line</strong> jointly treating <span class="badge constraint">F·error accumulation</span>.</p>

<div class="figure">
<svg viewBox="0 0 680 280" role="img" aria-label="Two-stage review with enforced order: spec compliance first, then code quality only after PASS, the whole thing fail-closed">
  <text x="340" y="24" text-anchor="middle" font-size="13.5" font-weight="700" fill="var(--ink)">Two-stage review · enforced order: spec compliance → quality</text>

  <rect x="24" y="44" width="266" height="116" rx="10" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="157" y="68" text-anchor="middle" font-size="13" font-weight="700" fill="var(--blue)">① Spec-compliance review</text>
  <text x="157" y="92" text-anchor="middle" font-size="11.5" fill="var(--ink)">Q: built the wrong thing?</text>
  <text x="157" y="112" text-anchor="middle" font-size="10.5" fill="var(--muted)">under/over-build · scope creep</text>
  <rect x="44" y="124" width="226" height="28" rx="7" fill="var(--panel)" stroke="var(--blue)"/>
  <text x="157" y="143" text-anchor="middle" font-size="11" fill="var(--ink)">OUTPUT: PASS / list spec gaps</text>

  <line x1="290" y1="92" x2="388" y2="92" stroke="var(--accent)" stroke-width="2.5"/>
  <path d="M388 92 L379 87 L379 97 Z" fill="var(--accent)"/>
  <rect x="300" y="100" width="78" height="24" rx="12" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="339" y="116" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--accent-ink)">only on PASS</text>

  <rect x="390" y="44" width="266" height="116" rx="10" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="523" y="68" text-anchor="middle" font-size="13" font-weight="700" fill="var(--purple)">② Code-quality review</text>
  <text x="523" y="92" text-anchor="middle" font-size="11.5" fill="var(--ink)">Q: built the thing wrong?</text>
  <text x="523" y="112" text-anchor="middle" font-size="10.5" fill="var(--muted)">bugs · style · edge cases</text>
  <rect x="410" y="124" width="226" height="28" rx="7" fill="var(--panel)" stroke="var(--purple)"/>
  <text x="523" y="143" text-anchor="middle" font-size="11" fill="var(--ink)">Verdict: APPROVED / REQUEST_CHANGES</text>

  <text x="340" y="184" text-anchor="middle" font-size="11" fill="var(--muted)">Order locked: don't waste quality review on off-target code</text>
  <rect x="24" y="198" width="632" height="62" rx="10" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="340" y="220" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--red)">fail-closed · default to blocking</text>
  <text x="340" y="242" text-anchor="middle" font-size="11" fill="var(--ink)">can't parse → passed=false  ·  security_concerns non-empty → passed=false  ·  pass only when both empty</text>
</svg>
<div class="fig-cap"><b>Two-stage review · enforced order</b>: spec-compliance first (“built the wrong thing?”, PASS or list gaps); <b>only after PASS</b> comes code-quality (“built the thing wrong?”, APPROVED/REQUEST_CHANGES). The two gates catch <b>orthogonal</b> failure classes, and the locked order avoids polishing off-target code; the whole thing is <b>fail-closed</b> — can't-parse or security concerns judge false, passing only when both lists are empty.</div>
</div>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc"><strong>Plan</strong>: the <span class="mono">plan</span> skill — pure planning, no execution, writes a markdown plan to .hermes/plans/</span></div>
  <div class="step"><span class="num">2</span><span class="sc"><strong>Execute</strong>: <span class="mono">subagent-driven-development</span> spawns a fresh implementer subagent per task (delegate_task isolation)</span></div>
  <div class="step"><span class="num">3</span><span class="sc"><strong>Two-stage review</strong>: spec-compliance reviewer (PASS/gaps) → code-quality reviewer (APPROVED/REQUEST_CHANGES), each an independent context</span></div>
  <div class="step"><span class="num">4</span><span class="sc"><strong>Independent review + fix</strong>: <span class="mono">requesting-code-review</span>'s reviewer sees only the diff, the fixer is a third context → commit gets [verified]</span></div>
  <div class="step"><span class="num">5</span><span class="sc">throughout, delegate_task's <strong>context isolation</strong> manufactures "fresh context"; the core builds in no plan/execute/review state machine</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "generator-verifier separation"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: the delegation tool's <strong>"self-reports, verify yourself"</strong> instruction (the only built-in), the <span class="mono">plan</span> skill (pure planning), <span class="mono">subagent-driven-development</span> (execution + two-stage review), <span class="mono">requesting-code-review</span> (independent reviewer + auto-fix). Cross-chapter teamwork: every "fresh context" is manufactured by <strong>delegate_task's context isolation</strong> (ch.13); these workflows are <strong>skills</strong> (ch.9 procedural memory), not core built-ins — exactly the <strong>narrow waist</strong> (ch.4); <span class="mono">background_review.py</span> is the "fork after each turn to evaluate saving a skill/memory" self-improvement (ch.9), <strong>not</strong> delegation review — don't conflate them.
  <div class="collab-sub">② Data-flow timing</div>
  the plan skill produces a plan → subagent-driven-development spawns an implementer subagent to execute → spec-compliance reviewer (independent context, implementation vs spec) → code-quality reviewer (independent context) → requesting-code-review spawns a reviewer (diff only) → on failure a third context fixes → [verified] commit.
  <div class="collab-sub">③ The key point</div>
  Hermes doesn't make planning/execution/review a built-in delegation state machine — it uses <strong>three skills to orchestrate delegate_task's isolation primitive</strong>. The core stays narrow: it offers just one primitive ("an isolated subagent"); the complex multi-agent workflow <strong>evolves at the edges (skills)</strong>, replaceable and extensible, while the core stays put.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>generator-verifier separation rests on "independent context," and the workflow orchestrates the delegation primitive via skills (narrow waist)</strong>. It treats two inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">F·error accumulation</span> — a model has a confirmation bias toward its own output and is prone to sycophantic self-endorsement; use a <strong>verifier in an independent context</strong> (not "don't be sycophantic" in a prompt, but structural isolation) + two-stage review to "catch issues before they compound";
  <span class="badge constraint">C·hallucination</span> — a subagent may sincerely misreport "success," so the built-in "self-reports, verify yourself" requires a verifiable handle. The anti-pattern: letting the generator <strong>review itself</strong> (blind spots + sycophancy); or <strong>baking planning/review into the core</strong> (against the narrow waist — complex workflows should evolve in the skill layer). Note: <strong>the core prompt has no explicit anti-sycophancy instruction</strong>; the sycophancy countermeasure is entirely the "independent verifier + fresh context" architecture.</p>
  <p style="margin:.5rem 0 0">One root-level question more: why not just add "<strong>don't be sycophantic, double-check yourself</strong>" to the core system prompt and let the generator self-check? Because <strong>using a prompt to fight the model's own bias is unreliable</strong> — the model that's sycophantic is the same one reading "don't be sycophantic." <strong>Architecture beats instruction</strong>: structural isolation <strong>removes the opportunity for self-endorsement at the root</strong> rather than politely asking it not to. This is a recurring Hermes pattern (ch.24) — <strong>never trust the probabilistic model to police itself</strong>; build the guardrail into the <strong>deterministic structure around it</strong>. It's also the other face of the narrow waist: keeping the workflow in the skill layer costs you opt-in (the agent must actively invoke the skill), in exchange for the core schema not carrying a plan/execute/review state machine on every single delegation.</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>No built-in review in the delegation layer</strong>: planning/execution/review aren't a delegate_task state machine, but <strong>three skills</strong> (plan / subagent-driven-development / requesting-code-review) orchestrating delegate_task's isolation.</li>
    <li><strong>The only built-in verification leaning</strong>: the tool description's "Subagent summaries are SELF-REPORTS... verify it yourself," requiring a verifiable handle (URL/ID/path/HTTP status).</li>
    <li><strong>Core principle</strong>: <span class="inline">No agent should verify its own work. Fresh context finds what you miss</span> — implementer/reviewer/fixer are three independent contexts.</li>
    <li><strong>Two-stage review</strong>: spec compliance (PASS/gaps) + code quality (APPROVED/REQUEST_CHANGES), "catch before they compound" — the generation-verification gap engineered.</li>
    <li><strong>Sycophancy countered structurally</strong>: the core prompt has no anti-sycophancy instruction; it relies on the "independent verifier + fresh context" isolation to resist self-endorsement.</li>
  </ul>
</div>

<div class="figure">
<svg viewBox="0 0 680 486" role="img" aria-label="The same diff config.py:45 changing == to != takes two independent paths: on the self-report path the subagent claims upload succeeded, and following self-reports verify yourself you fetch and measure HTTP 503, judged C hallucination and rejected; on the review path spec compliance takes only the diff and returns PASS, then quality review returns REQUEST_CHANGES for missing regression test; fail-closed rules require passed false when security_concerns is non-empty or the diff cannot be parsed; only after passing is the verified commit prefix applied.">
  <text x="340" y="22" text-anchor="middle" font-size="13.5" font-weight="700" fill="var(--ink)">One diff, three real verdicts - self-report rejected / PASS / REQUEST_CHANGES</text>
  <text x="340" y="40" text-anchor="middle" font-size="10" fill="var(--muted)">Example: config.py:45 changes == to !=, with an "I'm done" self-report</text>
  <text x="628" y="32" font-size="22">⚖️</text>

  <rect x="20" y="50" width="640" height="68" rx="9" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="32" y="68" font-size="10" font-weight="700" fill="var(--ink)">1. Shared input - generator submits diff + self-report</text>
  <text x="32" y="86" font-size="9" font-family="monospace" fill="var(--red)">- config.py:45    if val == expected:</text>
  <text x="360" y="86" font-size="9" font-family="monospace" fill="var(--accent-ink)">+ config.py:45    if val != expected:</text>
  <text x="32" y="106" font-size="9" fill="var(--muted)">self-report: ok &quot;changed and uploaded successfully&quot; (a SELF-REPORT, unverified)</text>

  <rect x="20" y="132" width="324" height="170" rx="9" fill="var(--red-soft)" stroke="var(--red)" stroke-width="2"/>
  <text x="34" y="150" font-size="10" font-weight="700" fill="var(--red)">Path A - self-report rejected (:2923-2929)</text>
  <text x="34" y="170" font-size="9" fill="var(--ink)">2. Tool-desc rule: Subagent summaries</text>
  <text x="34" y="184" font-size="9" font-family="monospace" fill="var(--ink)">are SELF-REPORTS, verify it yourself</text>
  <text x="34" y="204" font-size="9" fill="var(--ink)">claim: ok uploaded successfully</text>
  <text x="34" y="222" font-size="9" fill="var(--ink)">you fetch the URL and measure a handle:</text>
  <rect x="34" y="230" width="120" height="22" rx="5" fill="var(--panel)" stroke="var(--red)"/>
  <text x="94" y="245" text-anchor="middle" font-size="10" font-weight="700" fill="var(--red)">HTTP 503</text>
  <text x="34" y="272" font-size="9" fill="var(--muted)">demand a handle (URL/ID/path/HTTP status)</text>
  <text x="34" y="290" font-size="9.5" font-weight="700" fill="var(--red)">verdict: C-hallucination (sincere) - rejected</text>

  <rect x="356" y="132" width="304" height="170" rx="9" fill="var(--blue-soft)" stroke="var(--blue)" stroke-width="2"/>
  <text x="370" y="150" font-size="10" font-weight="700" fill="var(--blue)">Path B - independent review (two-stage gate)</text>
  <rect x="368" y="158" width="280" height="60" rx="7" fill="var(--panel)" stroke="var(--blue)"/>
  <text x="378" y="174" font-size="9" font-weight="700" fill="var(--blue)">3. Spec compliance - diff only (:127-130)</text>
  <text x="378" y="190" font-size="9" fill="var(--ink)">reviewer has no generator context, vs spec</text>
  <rect x="378" y="196" width="78" height="18" rx="5" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="417" y="209" text-anchor="middle" font-size="9.5" font-weight="700" fill="var(--accent-ink)">PASS (:113)</text>
  <rect x="368" y="226" width="280" height="66" rx="7" fill="var(--panel)" stroke="var(--amber)"/>
  <text x="378" y="242" font-size="9" font-weight="700" fill="var(--amber)">4. Quality - only after PASS (:142-145)</text>
  <text x="378" y="258" font-size="9" fill="var(--ink)">Verdict: APPROVED / REQUEST_CHANGES</text>
  <rect x="378" y="264" width="220" height="20" rx="5" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="388" y="278" font-size="9.5" font-weight="700" fill="var(--amber)">REQUEST_CHANGES - no regression test</text>

  <rect x="20" y="312" width="640" height="74" rx="9" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="32" y="330" font-size="10" font-weight="700" fill="var(--purple)">5. Fail-closed - unparseable / any concern is false (:138-140)</text>
  <text x="32" y="349" font-size="9" font-family="monospace" fill="var(--ink)">security_concerns non-empty -&gt; passed must be false</text>
  <text x="360" y="349" font-size="9" font-family="monospace" fill="var(--ink)">Cannot parse diff -&gt; passed must be false</text>
  <text x="32" y="368" font-size="9" font-family="monospace" fill="var(--purple)">{&quot;passed&quot;: false, &quot;security_concerns&quot;:[…], &quot;logic_errors&quot;:[…], &quot;summary&quot;:&quot;…&quot;}</text>
  <text x="32" y="382" font-size="9" fill="var(--muted)">passed is true only when both security_concerns and logic_errors are empty</text>

  <rect x="20" y="396" width="640" height="40" rx="9" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="32" y="414" font-size="10" font-weight="700" fill="var(--accent-ink)">6. Only after everything passes apply [verified] (:230-236)</text>
  <text x="32" y="430" font-size="9" font-family="monospace" fill="var(--ink)">git add -A &amp;&amp; git commit -m &quot;[verified] &lt;description&gt;&quot;</text>

  <rect x="20" y="446" width="640" height="20" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="340" y="460" text-anchor="middle" font-size="9" fill="var(--muted)">Read this: one diff - the self-report path is rejected by a measured 503, the review path goes spec PASS then quality REQUEST_CHANGES; no agent self-certifies, fail-closed</text>
</svg>
<div class="fig-cap"><b>One diff, three real verdicts</b>: the generator changes <span class="mono">config.py:45</span> from <span class="mono">==</span> to <span class="mono">!=</span> and self-reports "uploaded successfully". <b>Path A</b> (self-report) follows the tool rule "summaries are SELF-REPORTS, verify it yourself", measures it -&gt; gets <span class="mono">HTTP 503</span> -&gt; judged <b>C-hallucination</b> and rejected; <b>Path B</b> (independent review) runs spec compliance on the diff only -&gt; <span class="mono">PASS</span>, then quality review -&gt; <span class="mono">REQUEST_CHANGES</span> (no regression test). The whole thing is <b>fail-closed</b>: <span class="mono">security_concerns</span> non-empty or unparseable means <span class="mono">passed=false</span>, and only when all pass is <span class="mono">[verified]</span> applied.</div>
</div>
""",
}

LESSON_15 = {
    "zh": r"""
<p class="lead">
第 6 章立下铁律：<strong>prompt 缓存神圣不可侵犯，唯一的例外是上下文压缩</strong>。本章就讲这个例外。当对话长到逼近模型的上下文窗口，Hermes 会把早期历史<strong>摘要压缩</strong>成更短的一段。这一步<strong>必然</strong>改写了被缓存的前缀——缓存<strong>注定作废</strong>。所以它被设计成<strong>万不得已才触发</strong>：用一次「缓存重置」的代价，换回继续对话的空间。这是「缓存神圣」唯一让步的地方，也是对抗「上下文有限」和「上下文腐烂」的核心武器。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 把会议纪要压成要点</div>
  一场开了三小时的会，逐字记录有几万字——再开下去，新人根本读不完前情。聪明的做法是：<strong>保留最近的讨论</strong>（尾部）和<strong>最初的议题</strong>（头部），把<strong>中间冗长的过程</strong>压成一页<strong>结构化要点</strong>（做了什么、定了什么、还剩什么）。压缩后，会议继续，但纪要<strong>换了一版</strong>——这正是「缓存作废」的代价。Hermes 只在<strong>纪要快撑爆</strong>时才做这件事，平时绝不动它。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 用一次缓存重置，换回继续的空间</div>
  压缩的逻辑链是：①<strong>逼近才触发</strong>——默认到上下文窗口的 <strong>50%</strong> 才考虑，且有防抖动护栏；②<strong>保头保尾、摘要中段</strong>——保护最初的任务框架（头）和最近的上下文（尾），用<strong>辅助模型</strong>把中间轮摘要成结构化要点；③<strong>重建前缀</strong>——压缩改写了历史，必须 <span class="mono">_invalidate_system_prompt()</span> 清缓存、<span class="mono">_build_system_prompt()</span> 重建。这第三步就是「缓存唯一例外」的实证。它对抗 <span class="badge constraint">A·中间遗失</span>（上下文有限）和 <span class="badge constraint">F·误差累积</span>（上下文腐烂）。
</div>

<h2>何时触发：逼近才压，且防抖动</h2>
<p>压缩不是随时做，而是<strong>逼近窗口</strong>才触发，还要防止「压了一点点就又压」的抖动：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/context_compressor.py</span><span class="ln">964-984 · 简化</span></div>
  <pre><span class="kw">def</span> <span class="fn">should_compress</span>(self, prompt_tokens=<span class="kw">None</span>) -&gt; bool:
    <span class="cm"># 默认到上下文窗口 50% 的 token 阈值才触发(threshold_percent=0.50)</span>
    tokens = prompt_tokens <span class="kw">if</span> prompt_tokens <span class="kw">is</span> <span class="kw">not</span> <span class="kw">None</span> <span class="kw">else</span> self.last_prompt_tokens
    <span class="kw">if</span> tokens &lt; self.threshold_tokens:
        <span class="kw">return</span> <span class="kw">False</span>
    <span class="cm"># 防抖动:若最近两次压缩各只省下 &lt;10%,跳过,避免每次只删 1-2 条的死循环</span>
    <span class="kw">if</span> self._ineffective_compression_count &gt;= 2:
        <span class="kw">return</span> <span class="kw">False</span>
    <span class="kw">return</span> <span class="kw">True</span></pre>
</div>
<p>两道闸：其一，<strong>token 没到阈值就不压</strong>（默认窗口的 50%，小模型逼近时升到 85%）——平时尽量「省着用」整个上下文；其二，<strong>防抖动</strong>：如果最近两次压缩<strong>各只省下不到 10%</strong>，说明已经压无可压，再压只会陷入「每次删 1-2 条」的死循环，于是<strong>跳过</strong>。这两道闸合起来就是「万不得已才触发」——因为每触发一次，缓存就作废一次，代价昂贵。</p>

<p>为什么阈值定在 <strong>50%</strong> 而不是逼到 90% 才压?这是<strong>留缓冲</strong>的取舍:从触发到摘要完成还要再烧掉若干 token,而真实请求(含工具 schema)往往比粗估更大,留出半个窗口才不至于在压缩动作本身就把请求顶穿、被 provider 拒绝。反过来,为什么不<strong>每轮都压</strong>?因为每压一次就作废一次缓存(本章核心),频繁压缩等于把第 6 章「缓存神圣」的收益反复清零,成本爆炸。50% 阈值加上防抖动,正是在「太晚撞墙」和「太早废缓存」这两端之间取的平衡点——既不让上下文白白闲置,也不让缓存被无谓地反复推倒。</p>

<div class="figure">
<svg viewBox="0 0 680 250" role="img" aria-label="防抖动：为什么不每轮压缩——50%阈值加连续两次无效才放弃">
  <text x="20" y="22" font-size="13.5" font-weight="700" fill="var(--accent-ink)">防抖动：为什么不每轮压</text>

  <rect x="16" y="96" width="120" height="58" rx="9" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="76" y="120" text-anchor="middle" font-size="11.5" fill="var(--ink)">每轮检查</text>
  <text x="76" y="138" text-anchor="middle" font-size="10.5" fill="var(--muted)">should_compress</text>

  <path d="M136 125 L168 125 M160 119 L170 125 L160 131" fill="none" stroke="var(--muted)" stroke-width="1.5"/>

  <rect x="170" y="92" width="160" height="66" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="250" y="116" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">tokens ≥ 阈值？</text>
  <text x="250" y="134" text-anchor="middle" font-size="10" fill="var(--muted)">默认 50% 窗口 · 小模型 85%</text>

  <path d="M250 158 L250 186 M244 178 L250 188 L256 178" fill="none" stroke="var(--muted)" stroke-width="1.5"/>
  <text x="258" y="176" font-size="10" fill="var(--muted)">否 · 未到</text>
  <rect x="120" y="190" width="260" height="44" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="250" y="217" text-anchor="middle" font-size="11" fill="var(--accent-ink)">不压 · 向末尾追加（缓存命中）</text>

  <path d="M330 125 L362 125 M354 119 L364 125 L354 131" fill="none" stroke="var(--muted)" stroke-width="1.5"/>
  <text x="332" y="116" font-size="10" fill="var(--muted)">是</text>

  <rect x="364" y="92" width="160" height="66" rx="9" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="444" y="116" text-anchor="middle" font-size="11" font-weight="700" fill="var(--amber)">连续 2 次各省 &lt;10%？</text>
  <text x="444" y="134" text-anchor="middle" font-size="10" fill="var(--muted)">压无可压的死循环</text>

  <path d="M444 92 L444 64 M438 72 L444 62 L450 72" fill="none" stroke="var(--muted)" stroke-width="1.5"/>
  <text x="452" y="80" font-size="10" fill="var(--muted)">是</text>
  <rect x="344" y="22" width="200" height="42" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="444" y="48" text-anchor="middle" font-size="11" fill="var(--muted)">放弃压缩 · 防抖动</text>

  <path d="M524 125 L552 125 M544 119 L554 125 L544 131" fill="none" stroke="var(--muted)" stroke-width="1.5"/>
  <text x="528" y="116" font-size="10" fill="var(--muted)">否</text>
  <rect x="556" y="96" width="112" height="58" rx="9" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="612" y="118" text-anchor="middle" font-size="11" font-weight="700" fill="var(--red)">压缩一次</text>
  <text x="612" y="136" text-anchor="middle" font-size="9.5" fill="var(--red)">缓存作废+重建</text>
</svg>
<div class="fig-cap"><b>防抖动</b>：每轮调 <span class="mono">should_compress</span>，但有两道闸——① token 未达阈值（默认 <b>50%</b> 窗口，小模型升到 <b>85%</b>）就不压，继续向末尾追加、缓存命中；② 即便到阈值，若<b>连续两次</b>压缩各只省下 &lt;10%，说明压无可压，<b>跳过</b>以免陷入「每次删 1–2 条」的死循环。只有两闸都过才真正压缩一次——因为每压一次就作废一次缓存，频繁压＝不断废缓存，成本爆炸。</div>
</div>

<p>阈值还会<strong>随模型自适应</strong>,不是死板的 50%。<span class="mono">_compute_threshold_tokens</span> 先把窗口减去输出预留(<span class="mono">max_tokens</span>)算出真正可用的<strong>输入预算</strong>,再乘以阈值百分比;但若 50% 的值低于最小上下文下限被抬高、反而触到窗口本身,小窗口模型就<strong>永远压不动</strong>——provider 会在用量到 100% 前先拒绝请求。于是对这类模型改在窗口的 <strong>85%</strong>(<span class="mono">_MIN_CTX_TRIGGER_RATIO</span>)触发:既让小模型用满大半预算,又卡在被拒之前。这层细节保证「逼近才压」这条规矩在大窗口和小窗口模型下<strong>都成立</strong>,而不是只对大模型有效。</p>

<h2>缓存的唯一例外：压缩后重建 system prompt</h2>
<p>这是全书的关键三行——<strong>压缩为什么是缓存铁律的唯一例外</strong>，就实证在这里：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/conversation_compression.py</span><span class="ln">515-517 · 节选</span></div>
  <pre>agent._invalidate_system_prompt()                    <span class="cm"># 清空 _cached_system_prompt = None</span>
new_system_prompt = agent._build_system_prompt(system_message)  <span class="cm"># 重建</span>
agent._cached_system_prompt = new_system_prompt      <span class="cm"># 写回新前缀</span></pre>
</div>
<p>平时（第 6 章），<span class="mono">_cached_system_prompt</span> 一旦构建就<strong>逐字节不变</strong>，整会话复用、命中前缀缓存。但压缩<strong>重写了历史前缀</strong>——继续用旧缓存就错了。所以这里 <span class="mono">_invalidate_system_prompt()</span> 把缓存清空（置 <span class="kw">None</span>），随即 <span class="mono">_build_system_prompt()</span> 重建并写回。而 <span class="mono">invalidate_system_prompt</span> 还<strong>顺便 reload 记忆快照</strong>（<span class="mono">load_from_disk()</span>）——这正是第 11 章说的「记忆快照只在压缩边界刷新」：压缩本来就要重建，顺势把这会话写入的新记忆也纳入，<strong>不增加额外的缓存代价</strong>。</p>

<div class="figure">
<svg viewBox="0 0 680 348" role="img" aria-label="压缩是缓存的唯一例外：上下文增长到50%窗口触发压缩，重建前缀并折进新记忆">
  <text x="20" y="22" font-size="13.5" font-weight="700" fill="var(--accent-ink)">压缩：缓存的唯一例外</text>

  <text x="20" y="50" font-size="12" fill="var(--muted)">压缩前 · 上下文增长，逼近 50% 窗口</text>
  <text x="520" y="44" text-anchor="middle" font-size="11" font-weight="700" fill="var(--red)">50% 窗口阈值 → 触发</text>
  <rect x="20"  y="58" width="130" height="40" rx="7" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="85"  y="83" text-anchor="middle" font-size="11.5" fill="var(--accent-ink)">稳定前缀</text>
  <rect x="150" y="58" width="280" height="40" rx="7" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="290" y="83" text-anchor="middle" font-size="11.5" fill="var(--blue)">旧历史 · 中段（越来越长）</text>
  <rect x="430" y="58" width="90" height="40" rx="7" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="475" y="83" text-anchor="middle" font-size="11.5" fill="var(--amber)">最近轮</text>
  <line x1="520" y1="50" x2="520" y2="104" stroke="var(--red)" stroke-width="1.5" stroke-dasharray="4 3"/>
  <rect x="522" y="58" width="138" height="40" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="591" y="83" text-anchor="middle" font-size="10.5" fill="var(--faint)">剩余窗口 · 缓冲</text>

  <path d="M270 104 L270 132 M264 124 L270 134 L276 124" fill="none" stroke="var(--muted)" stroke-width="1.6"/>
  <text x="284" y="124" font-size="11.5" fill="var(--muted)">压缩 · 保头 / 摘要中段 / 保尾（辅助模型）</text>

  <text x="20" y="156" font-size="12" fill="var(--muted)">压缩后 · 重建前缀（缓存唯一一次作废）</text>
  <rect x="20"  y="164" width="130" height="40" rx="7" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2.5"/>
  <text x="85"  y="189" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--accent-ink)">新前缀 · 重建</text>
  <rect x="150" y="164" width="150" height="40" rx="7" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="225" y="184" text-anchor="middle" font-size="11" fill="var(--purple)">摘要要点</text>
  <text x="225" y="197" text-anchor="middle" font-size="9.5" fill="var(--muted)">中段消息 · 不进前缀</text>
  <rect x="300" y="164" width="90" height="40" rx="7" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="345" y="189" text-anchor="middle" font-size="11.5" fill="var(--amber)">最近轮</text>
  <text x="400" y="188" font-size="11" fill="var(--blue)">← 腾出空间，可继续对话</text>

  <path d="M85 204 L85 222" fill="none" stroke="var(--accent)" stroke-width="1.4" stroke-dasharray="3 3"/>
  <rect x="20" y="224" width="640" height="50" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="32" y="244" font-size="11.5" font-weight="700" fill="var(--accent-ink)">唯一一次被允许动前缀：_invalidate_system_prompt() → _build_system_prompt() 重建</text>
  <text x="32" y="263" font-size="11.5" fill="var(--accent-ink)">顺带 load_from_disk() 把本会话新记忆 / 技能折进新前缀，额外缓存代价 = 0</text>

  <rect x="20" y="286" width="640" height="44" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="32" y="305" font-size="11.5" font-weight="700" fill="var(--red)">不压缩的代价 ＞ 一次缓存重置：</text>
  <text x="32" y="323" font-size="11" fill="var(--red)">撞上下文窗口上限被 provider 拒绝 · A·中间遗失 · F·误差累积（上下文腐烂）</text>
</svg>
<div class="fig-cap"><b>压缩：缓存的唯一例外</b>：上下文增长到约 <b>50% 窗口</b>触发压缩——保头、用辅助模型把中段<b>摘要</b>成要点、保尾，随后 <span class="mono">_invalidate_system_prompt()</span> 清缓存、<span class="mono">_build_system_prompt()</span> 重建前缀。这是全书<b>唯一</b>被允许动缓存前缀的操作；同一刀顺带 <span class="mono">load_from_disk()</span> 把本会话新记忆 / 技能折进新前缀（连第 6 / 11 章），额外缓存代价为零。不压缩则会撞窗口上限并加剧中间遗失与误差累积，代价远大于一次缓存重置。</div>
</div>

<p>这里藏着一个<strong>省钱的合并</strong>:压缩横竖要重建前缀、缓存横竖要废一次,于是 Hermes 把「重载本会话新写的记忆」也<strong>搭在同一刀上</strong>——<span class="mono">invalidate_system_prompt</span> 顺手调 <span class="mono">load_from_disk()</span>(system_prompt.py:502-504)。若不这样,要么记忆得等到下次开新会话才生效,要么得在对话中途单独刷一次记忆、<strong>再额外废一次缓存</strong>。把两件本就要废缓存的事并到压缩这一个边界上,<strong>额外缓存代价归零</strong>。这正是第 6 章(缓存逐字节稳定)与第 11 章(记忆快照只在边界刷新)在此交汇的根由:不是它们各自巧合,而是同一条「缓存只在压缩边界破一次」的纪律推出来的必然结果。</p>

<p>还有个容易踩的反模式:把摘要<strong>塞进 system prompt 前缀</strong>当永久内容。Hermes 偏不——摘要被当作<strong>会话中段的普通消息</strong>追加进历史,而非写入缓存前缀。原因在源码注释里写得很清楚:摘要带了「当前日期」做时序锚定(context_compressor.py:1486-1491),日期天天变,若它落在缓存前缀里就会<strong>每天废一次缓存</strong>。把摘要留在中段,既能携带日期、报错值这类<strong>易变信息</strong>,又让真正稳定的前缀<strong>逐字节不动</strong>。一句话:压缩只在边界破一次缓存,而绝不让摘要里的可变内容把这条纪律拖成「每轮都破」。</p>

<h2>对抗上下文腐烂：保留什么、丢弃什么</h2>
<p>压缩不是简单截断，而是<strong>结构化保留关键、丢弃冗余</strong>。摘要用一个固定模板，逼辅助模型抽出「该记住的」：</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/context_compressor.py</span><span class="ln">1559-1606 · 节选（摘要模板）</span></div>
  <pre>## Goal
[用户整体想达成什么]
## Constraints &amp; Preferences
[用户偏好、编码风格、约束、重要决定]
## Completed Actions
[已采取的具体动作 — 工具、目标、结果]
## Key Decisions
[重要技术决定 + 为什么这么定]
## Resolved Questions
[已回答的问题 + 答案,避免重复问]
## Critical Context
[具体值、报错、配置 — 绝不含 API key]</pre>
</div>
<p>这套结构直接对抗 <span class="badge constraint">F·误差累积</span> 里的<strong>上下文腐烂</strong>：① <strong>头部保护随轮次衰减</strong>——第一次压缩保留最初几轮任务框架，但之后衰减到 0，免得早期消息「化石化」、把头部撑得无限大；② <strong>时序锚定</strong>——把「待办」改写成<strong>已完成的过去式</strong>，防止压缩恢复后<strong>重复执行</strong>旧任务；外加 <strong>STALE 标注</strong>——待办 / 剩余工作段被另标为「STALE 仅供参考，除非用户明确要求否则别执行」；③ 压缩前先<strong>廉价剪枝</strong>旧 tool 结果（无 LLM 调用，把长输出换成一行摘要）。还有一个细节：摘要本身是<strong>会话中段的消息、不在缓存前缀里</strong>，所以摘要里的日期等不会影响缓存稳定。</p>

<p>「保留什么、丢什么」本质是<strong>信号与体积的取舍</strong>:原文逐字最忠实但最占空间,纯摘要最省但会丢细节。Hermes 的折中是<strong>分层处理</strong>——压缩前先跑一道<strong>廉价剪枝</strong>(<span class="mono">_prune_old_tool_results</span>,无 LLM 调用),把陈旧的长工具输出换成一行摘要并去重(同一文件读两遍只留一份);真正要保信息密度的中段,才交辅助模型按结构化模板提炼。这样既不为省空间而牺牲关键决定,又不让冗长的旧工具回显把窗口吃光。它直接对治第 3 章 <span class="badge constraint">F·误差累积</span> 与第 2 章 <span class="badge constraint">A·中间遗失</span> 的共同病根:长历史里<strong>高价值信息被低价值噪声稀释</strong>。</p>

<p>为什么<strong>头部保护要随轮次衰减到 0</strong>,而不是永远保着最初几轮?因为 <span class="mono">protect_first_n</span>(默认 3)若每次压缩都生效,早期消息会被<strong>反复原样复制</strong>进每个子会话、永不被摘要掉,头部于是无限膨胀、把早期对话「化石化」(<span class="mono">_effective_protect_first_n</span>,#11996)。一旦压过一次,最初几轮其实已被折进摘要,就该<strong>停止再保护</strong>——而 system prompt 仍由 <span class="mono">_protect_head_size</span> 单独永久保护,任务框架绝不会丢。尾部则按 <span class="mono">protect_last_n</span>(默认 20)的 token 预算保最近上下文;外加一道<strong>压缩锁</strong>防两个进程同时压同一会话,避免 session 血缘分裂成两条互相覆盖的历史。</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc"><strong>逼近触发</strong>:token 达上下文窗口 ~50%(should_compress) + 防抖动(连续2次省&lt;10%则跳过)</span></div>
  <div class="step"><span class="num">2</span><span class="sc"><strong>剪枝</strong>:廉价剪掉旧 tool 结果(无 LLM),去重</span></div>
  <div class="step"><span class="num">3</span><span class="sc"><strong>保头保尾、摘要中段</strong>:辅助模型按结构化模板摘要中间轮(Goal/Decisions/...);时序锚定防重复执行</span></div>
  <div class="step"><span class="num">4</span><span class="sc"><strong>★重建前缀</strong>:_invalidate_system_prompt()→_build_system_prompt()→_cached_system_prompt=new(缓存唯一例外)</span></div>
  <div class="step"><span class="num">5</span><span class="sc">顺带 reload 记忆快照(load_from_disk);压缩锁防并发(防 session 血缘分裂)</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「缓存唯一例外」</div>
  <div class="collab-sub">① 组件清单（★本章核心，其余跨章节配合）</div>
  本章核心:<strong>should_compress</strong>(触发+防抖动)、<strong>剪枝+保头保尾+摘要</strong>(辅助模型)、<strong>_invalidate_system_prompt + 重建</strong>(缓存唯一例外)、<strong>时序锚定/头部衰减</strong>(对抗 rot)、<strong>压缩锁</strong>(防并发)。跨章节配合:平时 _cached_system_prompt 逐字节稳定(第 6 章),压缩是它<strong>唯一</strong>被重建的时机;压缩边界顺带 reload <strong>记忆快照</strong>(第 11 章 load_from_disk);摘要走<strong>辅助模型</strong>(第 10 章辅助模型隔离,auxiliary.compression);压缩(腾空间)与委派(隔离)是对抗「上下文有限」的<strong>两条不同路</strong>(第 13 章)。
  <div class="collab-sub">② 数据流时序</div>
  逼近窗口 → should_compress(防抖动)→ 剪枝旧 tool → 保头(衰减)保尾(token预算)、辅助模型摘要中段(结构化模板+时序锚定)→ _invalidate_system_prompt()清缓存 → _build_system_prompt()重建(顺带reload记忆)→ _cached_system_prompt=new → 继续对话。
  <div class="collab-sub">③ 关键点</div>
  压缩是「缓存神圣」唯一让步:它<strong>必然</strong>作废前缀缓存,所以设计成「逼近+防抖动才触发」(万不得已);换来的是把「会腐烂、会遗失」的长历史<strong>结构化压缩</strong>成高信号要点,让对话能继续。一次缓存重置的代价,换回继续的空间。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线:<strong>压缩是缓存铁律的唯一例外——用一次缓存重置换回继续对话的空间;万不得已才触发</strong>。它治两条 LLM 固有约束:
  <p style="margin:.5rem 0 0"><span class="badge constraint">A·中间遗失</span>——上下文窗口有限,长对话会把关键信息挤到中间被遗忘;压缩把中段<strong>摘要成高信号要点</strong>,腾出空间、保住关键;
  <span class="badge constraint">F·误差累积</span>——长对话会「上下文腐烂」(旧待办被反复执行、早期消息化石化);时序锚定(待办改过去式)+头部衰减+STALE 标注直接对治。反模式:<strong>频繁压缩</strong>(每次都作废缓存,成本爆炸)——所以要逼近+防抖动;或压缩时把摘要<strong>塞进 system prompt 前缀</strong>当永久内容(摘要应是中段消息,不进缓存前缀)。</p>
  <p style="margin:.5rem 0 0">再往根上问一句:<strong>为什么全书唯独压缩配享这个特权?</strong> 因为它是<strong>唯一无法回避的矛盾</strong>——对话只要够长,必然撞上上下文窗口的物理上限,这时摆在面前只有两条路:要么硬撞、让 provider 拒绝请求,要么主动重写历史、付一次缓存重置。其他所有「想改前缀」的诱惑(中途换工具、中途刷记忆、中途插系统提示)都有<strong>不破缓存的替代方案</strong>,唯独「腾出窗口空间」没有替代品。所以压缩不是被网开一面,而是<strong>没有别的活路</strong>。这也是它与委派(第 13 章:靠隔离子上下文绕开上限)分工的根本:压缩在原会话内<strong>腾空间</strong>,委派把工作<strong>搬到别的上下文</strong>去,两条不同的路对治同一个「上下文有限」。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>缓存唯一例外</strong>:压缩重写历史前缀 → <span class="mono">_invalidate_system_prompt()</span> 清缓存 + <span class="mono">_build_system_prompt()</span> 重建(conversation_compression.py:515-517);这是第 6 章铁律的唯一让步。</li>
    <li><strong>逼近才触发 + 防抖动</strong>:默认窗口 50% 阈值,连续两次省 &lt;10% 则跳过,避免「每次删 1-2 条」死循环。</li>
    <li><strong>保头保尾、摘要中段</strong>:辅助模型按结构化模板(Goal/Decisions/Resolved/...)摘要中间轮,保护最初任务框架与最近上下文。</li>
    <li><strong>对抗上下文腐烂</strong>:时序锚定(待办改过去式防重复执行)、头部保护衰减(防化石化)、剪枝旧 tool 结果。</li>
    <li><strong>顺带刷新记忆</strong>:invalidate 时 <span class="mono">load_from_disk()</span> 重载记忆快照(第 11 章);摘要是中段消息,不在缓存前缀。</li>
  </ul>
</div>

<div class="figure">
<svg viewBox="0 0 680 432" role="img" aria-label="一次真实压缩的内容变换：阈值时间线见第27.3章本图只讲内容怎么变；边界 protect_first_n 等于 3 且衰减到 0、protect_last_n 等于 20，中间 5 条待压；廉价剪枝 _prune_old_tool_results 无 LLM 把旧 tool 结果折成一行；模板填入真实摘要 Completed Actions 与 Critical Context REDACTED；token 从约 8400 降到约 600；缓存唯一例外 _invalidate_system_prompt 再 _build_system_prompt 写回并 load_from_disk。">
  <text x="340" y="22" text-anchor="middle" font-size="13.5" font-weight="700" fill="var(--ink)">一次压缩的内容变换 · 选哪 5 条 → 折成什么摘要 → 8400→600 tok</text>
  <text x="340" y="40" text-anchor="middle" font-size="10" fill="var(--muted)">本图只讲「内容怎么变」（已判定触发，阈值时间线见第 27.3 章）</text>
  <text x="628" y="32" font-size="22">🗜️</text>

  <rect x="20" y="50" width="176" height="214" rx="9" fill="var(--panel)" stroke="var(--line)"/>
  <text x="30" y="68" font-size="10" font-weight="700" fill="var(--ink)">② 边界（:787-788）</text>
  <rect x="30" y="76" width="156" height="32" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="38" y="90" font-size="9" font-weight="700" fill="var(--accent-ink)">protect_first_n=3</text>
  <text x="38" y="103" font-size="9" fill="var(--accent-ink)">保头 · 随增长衰减→0（:2024）</text>
  <rect x="30" y="116" width="156" height="48" rx="6" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="38" y="132" font-size="9" font-weight="700" fill="var(--purple)">中间 5 条 ← 待压</text>
  <text x="38" y="147" font-size="9" fill="var(--purple)">用辅助模型折成结构化要点</text>
  <text x="38" y="159" font-size="9" fill="var(--purple)">（高信号留、低信号弃）</text>
  <rect x="30" y="172" width="156" height="32" rx="6" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="38" y="186" font-size="9" font-weight="700" fill="var(--blue)">protect_last_n=20</text>
  <text x="38" y="199" font-size="9" fill="var(--blue)">保尾 · 最近上下文原样留</text>
  <text x="30" y="224" font-size="9" fill="var(--muted)">保头保尾、只压中段</text>
  <text x="30" y="240" font-size="9" fill="var(--muted)">→ 既省 token 又不丢</text>
  <text x="30" y="256" font-size="9" fill="var(--muted)">　 最相关的近况</text>

  <line x1="200" y1="157" x2="218" y2="157" stroke="var(--line)" stroke-width="1.8"/>
  <path d="M224 157 L216 153 L216 161 Z" fill="var(--line)"/>

  <rect x="226" y="50" width="290" height="70" rx="9" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="238" y="68" font-size="10" font-weight="700" fill="var(--ink)">③ 廉价剪枝 _prune_old_tool_results · 无 LLM（:990）</text>
  <text x="238" y="86" font-size="9" fill="var(--ink)">旧 tool 结果正文 → 1 行摘要（先省一轮，零成本）</text>
  <text x="238" y="104" font-size="9" font-family="monospace" fill="var(--muted)">[old tool output pruned: N lines]</text>

  <rect x="226" y="128" width="290" height="136" rx="9" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="238" y="146" font-size="10" font-weight="700" fill="var(--accent-ink)">④ 模板填真实摘要 · context_compressor.py:1565-1575</text>
  <text x="238" y="164" font-size="9" font-family="monospace" fill="var(--ink)">## Completed Actions</text>
  <text x="238" y="180" font-size="9" font-family="monospace" fill="var(--ink)">1. READ config.py:45 — found == should be != [tool: read_file]</text>
  <text x="238" y="196" font-size="9" font-family="monospace" fill="var(--ink)">3. TEST pytest tests/ — 3/50 failed [tool: terminal]</text>
  <text x="238" y="216" font-size="9" font-family="monospace" fill="var(--ink)">## Critical Context</text>
  <text x="238" y="232" font-size="9" font-family="monospace" fill="var(--red)">[REDACTED]   ← 凭证/密钥一律抹掉（:1603）</text>
  <text x="238" y="252" font-size="9" fill="var(--muted)">格式 N. ACTION target — outcome [tool: name]</text>

  <rect x="524" y="50" width="136" height="214" rx="9" fill="var(--panel)" stroke="var(--line)"/>
  <text x="592" y="68" text-anchor="middle" font-size="10" font-weight="700" fill="var(--ink)">⑤ token 账</text>
  <rect x="556" y="84" width="72" height="40" rx="6" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="592" y="100" text-anchor="middle" font-size="11" font-weight="700" fill="var(--amber)">~8400</text>
  <text x="592" y="116" text-anchor="middle" font-size="9" fill="var(--amber)">tok（压前）</text>
  <line x1="592" y1="130" x2="592" y2="160" stroke="var(--line)" stroke-width="2"/>
  <path d="M592 166 L586 156 L598 156 Z" fill="var(--line)"/>
  <rect x="556" y="172" width="72" height="40" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="592" y="188" text-anchor="middle" font-size="11" font-weight="700" fill="var(--accent-ink)">~600</text>
  <text x="592" y="204" text-anchor="middle" font-size="9" fill="var(--accent-ink)">tok（压后）</text>
  <text x="592" y="234" text-anchor="middle" font-size="10" font-weight="700" fill="var(--purple)">≈ -93%</text>
  <text x="592" y="252" text-anchor="middle" font-size="9" fill="var(--muted)">目标 ~0.20 比率</text>

  <rect x="20" y="276" width="640" height="116" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="32" y="294" font-size="10" font-weight="700" fill="var(--blue)">⑥ 缓存的唯一例外 · conversation_compression.py:515-517</text>
  <text x="32" y="314" font-size="9" font-family="monospace" fill="var(--ink)">agent._invalidate_system_prompt()</text>
  <text x="32" y="332" font-size="9" font-family="monospace" fill="var(--ink)">new_system_prompt = agent._build_system_prompt(system_message)</text>
  <text x="32" y="350" font-size="9" font-family="monospace" fill="var(--ink)">agent._cached_system_prompt = new_system_prompt</text>
  <text x="32" y="370" font-size="9" fill="var(--muted)">同一刀顺带 load_from_disk() 把本会话新记忆/技能折进新前缀（第 11 章）</text>
  <text x="32" y="386" font-size="9" fill="var(--purple)">这是全书唯一被允许动「神圣缓存前缀」的操作（第 6 章）</text>

  <rect x="20" y="402" width="640" height="20" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="340" y="416" text-anchor="middle" font-size="9" fill="var(--muted)">读这张图：压缩=保头(3,衰减)+保尾(20)、中段 5 条折成 ## 模板摘要、凭证抹成 [REDACTED]，8400→600 tok，并唯一一次重建缓存前缀</text>
</svg>
<div class="fig-cap"><b>一次压缩的内容变换</b>：边界 <span class="mono">protect_first_n=3</span>（随增长衰减→0）/ <span class="mono">protect_last_n=20</span>，中间 <b>5 条</b>被选中压缩；先经 <span class="mono">_prune_old_tool_results</span>（<b>无 LLM</b>）把旧 tool 结果折成一行，再用辅助模型按模板填真实摘要 <span class="mono">## Completed Actions</span>（<span class="mono">1. READ config.py:45 — found == should be !=</span> / <span class="mono">3. TEST pytest tests/ — 3/50 failed</span>）、<span class="mono">## Critical Context: [REDACTED]</span>；约 <b>8400→600 tok</b>。收尾是全书<b>唯一</b>动缓存前缀的操作：<span class="mono">_invalidate_system_prompt()</span> → <span class="mono">_build_system_prompt()</span> 写回 + <span class="mono">load_from_disk()</span>。</div>
</div>
""",
    "en": r"""
<p class="lead">
Ch.6 laid down the iron rule: <strong>the prompt cache is sacred, and the only exception is context compression</strong>. This chapter is about that exception. When a conversation grows close to the model's context window, Hermes <strong>summarizes and compresses</strong> the early history into a shorter span. That step <strong>necessarily</strong> rewrites the cached prefix — the cache is <strong>bound to be voided</strong>. So it's designed to fire only as a <strong>last resort</strong>: spend one "cache reset" to buy back room to keep talking. This is the one place "the cache is sacred" yields, and the core weapon against "limited context" and "context rot."
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · compressing meeting minutes into key points</div>
  A three-hour meeting has tens of thousands of words of verbatim notes — keep going and a newcomer can't possibly read the backstory. The smart move: <strong>keep the recent discussion</strong> (the tail) and <strong>the original agenda</strong> (the head), and compress the <strong>long middle</strong> into a page of <strong>structured key points</strong> (what was done, what was decided, what's left). After compression the meeting continues, but the minutes are <strong>a new version</strong> — exactly the cost of "cache invalidation." Hermes only does this when the minutes are <strong>about to overflow</strong>, never touching them otherwise.
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture · spend one cache reset to buy back room</div>
  Compression's logic chain: ① <strong>fire only near the limit</strong> — by default it considers compaction at <strong>50%</strong> of the context window, with anti-thrashing guards; ② <strong>protect head and tail, summarize the middle</strong> — keep the original task framing (head) and recent context (tail), and use an <strong>auxiliary model</strong> to summarize the middle turns into structured key points; ③ <strong>rebuild the prefix</strong> — compression rewrote history, so it must <span class="mono">_invalidate_system_prompt()</span> to clear the cache and <span class="mono">_build_system_prompt()</span> to rebuild. That third step is the proof of "the cache's only exception." It treats <span class="badge constraint">A·lost-in-the-middle</span> (limited context) and <span class="badge constraint">F·error accumulation</span> (context rot).
</div>

<h2>When it fires: only near the limit, and anti-thrashing</h2>
<p>Compression isn't done anytime — it fires only <strong>near the window</strong>, and guards against "compress a tiny bit then compress again" thrashing:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/context_compressor.py</span><span class="ln">964-984 · simplified</span></div>
  <pre><span class="kw">def</span> <span class="fn">should_compress</span>(self, prompt_tokens=<span class="kw">None</span>) -&gt; bool:
    <span class="cm"># fires only at the token threshold = 50% of the context window (threshold_percent=0.50)</span>
    tokens = prompt_tokens <span class="kw">if</span> prompt_tokens <span class="kw">is</span> <span class="kw">not</span> <span class="kw">None</span> <span class="kw">else</span> self.last_prompt_tokens
    <span class="kw">if</span> tokens &lt; self.threshold_tokens:
        <span class="kw">return</span> <span class="kw">False</span>
    <span class="cm"># anti-thrashing: if the last two compressions each saved &lt;10%, skip — avoid a loop that removes 1-2 msgs each time</span>
    <span class="kw">if</span> self._ineffective_compression_count &gt;= 2:
        <span class="kw">return</span> <span class="kw">False</span>
    <span class="kw">return</span> <span class="kw">True</span></pre>
</div>
<p>Two gates: first, <strong>don't compress until tokens hit the threshold</strong> (default 50% of the window, rising to 85% for small models near the edge) — normally "use up" the whole context first; second, <strong>anti-thrashing</strong>: if the last two compressions each <strong>saved less than 10%</strong>, there's nothing left to squeeze, and compressing again would spiral into a "remove 1-2 messages each time" loop, so it <strong>skips</strong>. Together these are "last resort only" — because each fire voids the cache once, an expensive cost.</p>

<p>Why set the threshold at <strong>50%</strong> rather than pushing to 90% before compacting? It's a <strong>buffer</strong> trade-off: from trigger to a finished summary still burns more tokens, and a real request (with tool schemas) often runs larger than the rough estimate, so leaving half the window keeps the compaction act itself from blowing past the limit and getting rejected by the provider. Conversely, why not compress <strong>every turn</strong>? Because each compression voids the cache once (this chapter's core), and frequent compression repeatedly zeros out ch.6's "the cache is sacred" payoff — costs explode. The 50% threshold plus anti-thrashing is exactly the balance point between "hit the wall too late" and "void the cache too early."</p>

<div class="figure">
<svg viewBox="0 0 680 250" role="img" aria-label="Anti-thrashing: why not compress every turn — 50% threshold plus two ineffective passes before giving up">
  <text x="20" y="22" font-size="13.5" font-weight="700" fill="var(--accent-ink)">Anti-thrashing: why not compress every turn</text>

  <rect x="16" y="96" width="120" height="58" rx="9" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="76" y="120" text-anchor="middle" font-size="11.5" fill="var(--ink)">every turn</text>
  <text x="76" y="138" text-anchor="middle" font-size="10.5" fill="var(--muted)">should_compress</text>

  <path d="M136 125 L168 125 M160 119 L170 125 L160 131" fill="none" stroke="var(--muted)" stroke-width="1.5"/>

  <rect x="170" y="92" width="160" height="66" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="250" y="116" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">tokens ≥ threshold?</text>
  <text x="250" y="134" text-anchor="middle" font-size="10" fill="var(--muted)">50% window · 85% small models</text>

  <path d="M250 158 L250 186 M244 178 L250 188 L256 178" fill="none" stroke="var(--muted)" stroke-width="1.5"/>
  <text x="258" y="176" font-size="10" fill="var(--muted)">No · below</text>
  <rect x="120" y="190" width="260" height="44" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="250" y="217" text-anchor="middle" font-size="11" fill="var(--accent-ink)">don't compress · append to tail (cache hit)</text>

  <path d="M330 125 L362 125 M354 119 L364 125 L354 131" fill="none" stroke="var(--muted)" stroke-width="1.5"/>
  <text x="332" y="116" font-size="10" fill="var(--muted)">Yes</text>

  <rect x="364" y="92" width="160" height="66" rx="9" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="444" y="116" text-anchor="middle" font-size="11" font-weight="700" fill="var(--amber)">last 2 each saved &lt;10%?</text>
  <text x="444" y="134" text-anchor="middle" font-size="10" fill="var(--muted)">the "nothing left" loop</text>

  <path d="M444 92 L444 64 M438 72 L444 62 L450 72" fill="none" stroke="var(--muted)" stroke-width="1.5"/>
  <text x="452" y="80" font-size="10" fill="var(--muted)">Yes</text>
  <rect x="344" y="22" width="200" height="42" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="444" y="48" text-anchor="middle" font-size="11" fill="var(--muted)">skip · anti-thrashing</text>

  <path d="M524 125 L552 125 M544 119 L554 125 L544 131" fill="none" stroke="var(--muted)" stroke-width="1.5"/>
  <text x="528" y="116" font-size="10" fill="var(--muted)">No</text>
  <rect x="556" y="96" width="112" height="58" rx="9" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="612" y="118" text-anchor="middle" font-size="11" font-weight="700" fill="var(--red)">compress once</text>
  <text x="612" y="136" text-anchor="middle" font-size="9.5" fill="var(--red)">cache voided + rebuilt</text>
</svg>
<div class="fig-cap"><b>Anti-thrashing</b>: every turn calls <span class="mono">should_compress</span>, but two gates guard it — ① if tokens are below the threshold (default <b>50%</b> of the window, rising to <b>85%</b> for small models) it doesn't compress, just appends to the tail and hits the cache; ② even at the threshold, if the <b>last two</b> compressions each saved &lt;10%, there's nothing left to squeeze, so it <b>skips</b> to avoid a "remove 1–2 messages each time" loop. Only when both gates pass does it actually compress once — because each compression voids the cache, so compressing every turn = endlessly voiding the cache, costs explode.</div>
</div>

<p>The threshold is also <strong>model-adaptive</strong>, not a rigid 50%. <span class="mono">_compute_threshold_tokens</span> first subtracts the output reservation (<span class="mono">max_tokens</span>) from the window to get the real usable <strong>input budget</strong>, then applies the percentage; but if the 50% value, floored up to the minimum-context bound, would meet the window itself, a small-window model could <strong>never compress</strong> — the provider rejects the request before usage reaches 100%. So for such models it triggers at <strong>85%</strong> of the window (<span class="mono">_MIN_CTX_TRIGGER_RATIO</span>): letting a small model use most of its budget yet firing before rejection. This detail keeps "compress only near the limit" valid for <strong>both</strong> large- and small-window models, not just large ones.</p>

<h2>The cache's only exception: rebuild the system prompt after compression</h2>
<p>Here are the book's key three lines — <strong>why compression is the iron rule's only exception</strong> is proven right here:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/conversation_compression.py</span><span class="ln">515-517 · excerpt</span></div>
  <pre>agent._invalidate_system_prompt()                    <span class="cm"># clears _cached_system_prompt = None</span>
new_system_prompt = agent._build_system_prompt(system_message)  <span class="cm"># rebuild</span>
agent._cached_system_prompt = new_system_prompt      <span class="cm"># write back the new prefix</span></pre>
</div>
<p>Normally (ch.6), once <span class="mono">_cached_system_prompt</span> is built it stays <strong>byte-stable</strong>, reused all session to hit the prefix cache. But compression <strong>rewrote the history prefix</strong> — keeping the old cache would be wrong. So here <span class="mono">_invalidate_system_prompt()</span> clears the cache (sets it <span class="kw">None</span>) and <span class="mono">_build_system_prompt()</span> rebuilds and writes back. And <span class="mono">invalidate_system_prompt</span> also <strong>reloads the memory snapshot</strong> (<span class="mono">load_from_disk()</span>) — exactly ch.11's "the memory snapshot refreshes only at a compression boundary": compression has to rebuild anyway, so it folds in the new memory written this session at <strong>no extra cache cost</strong>.</p>

<div class="figure">
<svg viewBox="0 0 680 348" role="img" aria-label="Compression is the cache's only exception: context grows to 50% of the window, triggers compression, rebuilds the prefix and folds in new memory">
  <text x="20" y="22" font-size="13.5" font-weight="700" fill="var(--accent-ink)">Compression: the cache's only exception</text>

  <text x="20" y="50" font-size="12" fill="var(--muted)">Before · context grows toward 50% of the window</text>
  <text x="520" y="44" text-anchor="middle" font-size="11" font-weight="700" fill="var(--red)">50% window → trigger</text>
  <rect x="20"  y="58" width="130" height="40" rx="7" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="85"  y="83" text-anchor="middle" font-size="11.5" fill="var(--accent-ink)">stable prefix</text>
  <rect x="150" y="58" width="280" height="40" rx="7" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="290" y="83" text-anchor="middle" font-size="11.5" fill="var(--blue)">old history · middle (growing)</text>
  <rect x="430" y="58" width="90" height="40" rx="7" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="475" y="83" text-anchor="middle" font-size="11.5" fill="var(--amber)">recent</text>
  <line x1="520" y1="50" x2="520" y2="104" stroke="var(--red)" stroke-width="1.5" stroke-dasharray="4 3"/>
  <rect x="522" y="58" width="138" height="40" rx="7" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="591" y="83" text-anchor="middle" font-size="10.5" fill="var(--faint)">remaining · buffer</text>

  <path d="M270 104 L270 132 M264 124 L270 134 L276 124" fill="none" stroke="var(--muted)" stroke-width="1.6"/>
  <text x="284" y="124" font-size="11.5" fill="var(--muted)">compress · keep head / summarize middle / keep tail (aux model)</text>

  <text x="20" y="156" font-size="12" fill="var(--muted)">After · rebuild the prefix (cache voided this one time)</text>
  <rect x="20"  y="164" width="130" height="40" rx="7" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2.5"/>
  <text x="85"  y="189" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--accent-ink)">new prefix · rebuilt</text>
  <rect x="150" y="164" width="150" height="40" rx="7" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="225" y="184" text-anchor="middle" font-size="11" fill="var(--purple)">summary points</text>
  <text x="225" y="197" text-anchor="middle" font-size="9.5" fill="var(--muted)">mid-conversation · not in prefix</text>
  <rect x="300" y="164" width="90" height="40" rx="7" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="345" y="189" text-anchor="middle" font-size="11.5" fill="var(--amber)">recent</text>
  <text x="400" y="188" font-size="11" fill="var(--blue)">← room freed, conversation continues</text>

  <path d="M85 204 L85 222" fill="none" stroke="var(--accent)" stroke-width="1.4" stroke-dasharray="3 3"/>
  <rect x="20" y="224" width="640" height="50" rx="8" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="32" y="244" font-size="11.5" font-weight="700" fill="var(--accent-ink)">Only place the prefix may change: _invalidate_system_prompt() → _build_system_prompt() rebuild</text>
  <text x="32" y="263" font-size="11.5" fill="var(--accent-ink)">Same cut folds in new memory / skills via load_from_disk() — extra cache cost = 0</text>

  <rect x="20" y="286" width="640" height="44" rx="8" fill="var(--red-soft)" stroke="var(--red)"/>
  <text x="32" y="305" font-size="11.5" font-weight="700" fill="var(--red)">Not compressing costs MORE than one cache reset:</text>
  <text x="32" y="323" font-size="11" fill="var(--red)">hit the window limit (provider rejects) · A·lost-in-the-middle · F·error accumulation (rot)</text>
</svg>
<div class="fig-cap"><b>Compression: the cache's only exception</b>: when context grows to about <b>50% of the window</b> it triggers compression — keep the head, use the auxiliary model to <b>summarize</b> the middle into points, keep the tail, then <span class="mono">_invalidate_system_prompt()</span> clears the cache and <span class="mono">_build_system_prompt()</span> rebuilds the prefix. This is the <b>only</b> operation in the whole book allowed to touch the cached prefix; the same cut piggybacks <span class="mono">load_from_disk()</span> to fold this session's new memory / skills into the new prefix (ch.6 / 11) at zero extra cache cost. Not compressing hits the window limit and worsens lost-in-the-middle and error accumulation — far costlier than one cache reset.</div>
</div>

<p>There's a <strong>cost-saving merge</strong> hidden here: compression has to rebuild the prefix and the cache has to be voided once anyway, so Hermes <strong>piggybacks</strong> "reload the memory written this session" onto the same cut — <span class="mono">invalidate_system_prompt</span> calls <span class="mono">load_from_disk()</span> right there (system_prompt.py:502-504). Without this, either memory waits until the next fresh session to take effect, or you'd refresh memory mid-conversation on its own and <strong>void the cache a second time</strong>. Folding both cache-voiding acts onto the single compression boundary makes the <strong>extra cache cost zero</strong>. This is exactly why ch.6 (byte-stable cache) and ch.11 (the memory snapshot refreshes only at a boundary) intersect here — not coincidence, but a necessary consequence of the one rule "break the cache only at a compression boundary."</p>

<p>There's also an easy anti-pattern: jamming the summary into the <strong>system-prompt prefix</strong> as permanent content. Hermes refuses — the summary is appended as an <strong>ordinary mid-conversation message</strong>, not written into the cached prefix. The reason is spelled out in a source comment: the summary carries "the current date" for temporal anchoring (context_compressor.py:1486-1491), and the date changes daily, so if it landed in the cached prefix it would <strong>void the cache every day</strong>. Keeping the summary in the middle lets it carry volatile info (dates, error values) while the truly stable prefix stays <strong>byte-for-byte unchanged</strong>. In short: compression breaks the cache once at the boundary, and never lets mutable summary content drag that rule into "break it every turn."</p>

<h2>Fighting context rot: what to keep, what to drop</h2>
<p>Compression isn't a simple truncation — it <strong>structurally keeps the key, drops the redundant</strong>. The summary uses a fixed template, forcing the auxiliary model to extract "what should be remembered":</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/context_compressor.py</span><span class="ln">1559-1606 · excerpt (summary template)</span></div>
  <pre>## Goal
[What the user is trying to accomplish overall]
## Constraints &amp; Preferences
[User preferences, coding style, constraints, important decisions]
## Completed Actions
[Concrete actions taken — tool, target, outcome]
## Key Decisions
[Important technical decisions and WHY]
## Resolved Questions
[Questions already answered + the answer, so it's not repeated]
## Critical Context
[Specific values, errors, config — NEVER include API keys]</pre>
</div>
<p>This structure directly treats the <strong>context rot</strong> within <span class="badge constraint">F·error accumulation</span>: ① <strong>head protection decays over cycles</strong> — the first compaction keeps the early task framing, but later it decays to 0, so early messages don't "fossilize" and grow the head unboundedly; ② <strong>temporal anchoring</strong> — rewrite "to-dos" as <strong>completed past tense</strong> to prevent <strong>re-execution</strong> of old tasks after recovery; plus a separate <strong>STALE marking</strong> — pending/remaining-work sections are labeled "STALE, for reference only; don't act unless the user explicitly asks"; ③ before compressing, a <strong>cheap prune</strong> of old tool results (no LLM, replacing long output with a one-line summary). One detail: the summary itself is a <strong>mid-conversation message, not in the cached prefix</strong>, so a date in it never affects cache stability.</p>

<p>"What to keep, what to drop" is fundamentally a <strong>signal-vs-volume</strong> trade-off: verbatim text is most faithful but most space-hungry; a pure summary is leanest but loses detail. Hermes' compromise is <strong>layered handling</strong> — before compressing it runs a <strong>cheap prune</strong> (<span class="mono">_prune_old_tool_results</span>, no LLM call) that replaces stale long tool outputs with a one-line summary and dedupes (read the same file twice, keep one); only the middle that genuinely needs information density is handed to the auxiliary model to distill by a structured template. This neither sacrifices key decisions to save space nor lets verbose old tool echoes eat the whole window. It directly treats the shared root cause of ch.3's <span class="badge constraint">F·error accumulation</span> and ch.2's <span class="badge constraint">A·lost-in-the-middle</span>: in a long history, <strong>high-value info gets diluted by low-value noise</strong>.</p>

<p>Why must <strong>head protection decay to 0</strong> over cycles rather than always keeping the first few turns? Because if <span class="mono">protect_first_n</span> (default 3) fired on every compaction, early messages would be <strong>copied verbatim</strong> into each child session, never summarized away — the head then grows unboundedly and "fossilizes" the early conversation (<span class="mono">_effective_protect_first_n</span>, #11996). Once compressed once, the first few turns are already folded into the summary, so it should <strong>stop re-protecting</strong> them — while the system prompt is still permanently protected separately by <span class="mono">_protect_head_size</span>, so the task framing is never lost. The tail keeps recent context by <span class="mono">protect_last_n</span>'s (default 20) token budget; plus a <strong>compression lock</strong> stops two processes compacting the same session at once, avoiding a session-lineage split into two mutually-overwriting histories.</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc"><strong>Fire near the limit</strong>: tokens hit ~50% of the window (should_compress) + anti-thrashing (skip if 2 in a row saved &lt;10%)</span></div>
  <div class="step"><span class="num">2</span><span class="sc"><strong>Prune</strong>: cheaply trim old tool results (no LLM), dedupe</span></div>
  <div class="step"><span class="num">3</span><span class="sc"><strong>Protect head/tail, summarize the middle</strong>: auxiliary model summarizes middle turns by template (Goal/Decisions/...); temporal anchoring prevents re-execution</span></div>
  <div class="step"><span class="num">4</span><span class="sc"><strong>★Rebuild the prefix</strong>: _invalidate_system_prompt()→_build_system_prompt()→_cached_system_prompt=new (the cache's only exception)</span></div>
  <div class="step"><span class="num">5</span><span class="sc">also reloads the memory snapshot (load_from_disk); a compression lock prevents concurrent compaction (avoiding session-lineage splits)</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "the cache's only exception"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: <strong>should_compress</strong> (trigger + anti-thrashing), <strong>prune + protect head/tail + summarize</strong> (auxiliary model), <strong>_invalidate_system_prompt + rebuild</strong> (the cache's only exception), <strong>temporal anchoring / head decay</strong> (fighting rot), the <strong>compression lock</strong> (anti-concurrency). Cross-chapter teamwork: normally _cached_system_prompt is byte-stable (ch.6), and compression is its <strong>only</strong> rebuild moment; the compression boundary also reloads the <strong>memory snapshot</strong> (ch.11 load_from_disk); the summary runs on the <strong>auxiliary model</strong> (ch.10 auxiliary-model isolation, auxiliary.compression); compression (make room) and delegation (isolate) are <strong>two different routes</strong> against "limited context" (ch.13).
  <div class="collab-sub">② Data-flow timing</div>
  near the window → should_compress (anti-thrashing) → prune old tools → protect head (decaying) and tail (token budget), auxiliary model summarizes the middle (structured template + temporal anchoring) → _invalidate_system_prompt() clears cache → _build_system_prompt() rebuilds (also reloads memory) → _cached_system_prompt=new → continue.
  <div class="collab-sub">③ The key point</div>
  Compression is "the cache is sacred"'s one concession: it <strong>necessarily</strong> voids the prefix cache, so it's designed to fire "only near the limit, with anti-thrashing" (last resort); in return it <strong>structurally compresses</strong> the rotting, forgettable long history into high-signal points so the conversation can continue. One cache reset bought for room to keep going.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>compression is the iron rule's only exception — spend one cache reset to buy back room; fire only as a last resort</strong>. It treats two inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">A·lost-in-the-middle</span> — the context window is finite, and a long conversation pushes key info into the forgotten middle; compression summarizes the middle into <strong>high-signal points</strong>, freeing space while keeping the essentials;
  <span class="badge constraint">F·error accumulation</span> — a long conversation "rots" (old to-dos re-executed, early messages fossilized); temporal anchoring (to-dos as past tense) + head decay + STALE marking directly counter it. The anti-pattern: <strong>frequent compression</strong> (each voids the cache, costs explode) — hence near-limit + anti-thrashing; or jamming the summary into the <strong>system-prompt prefix</strong> as permanent content (the summary should be a mid-conversation message, not in the cached prefix).</p>
  <p style="margin:.5rem 0 0">Push to the root: <strong>why is compression alone granted this privilege in the whole book?</strong> Because it's the <strong>one unavoidable contradiction</strong> — any conversation long enough will hit the physical limit of the context window, and at that point there are only two roads: hit the wall and let the provider reject the request, or proactively rewrite history and pay one cache reset. Every other temptation to "alter the prefix" (swap tools mid-stream, refresh memory mid-stream, inject a system note mid-stream) has a <strong>cache-preserving alternative</strong>; only "free up window space" has no substitute. So compression isn't given a pass — it has <strong>no other way out</strong>. This is also the root of its division of labor with delegation (ch.13: bypass the limit by isolating a child context): compression <strong>frees space</strong> within the same session, delegation <strong>moves work</strong> to another context — two different roads against the same "limited context."</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>The cache's only exception</strong>: compression rewrites the history prefix → <span class="mono">_invalidate_system_prompt()</span> clears the cache + <span class="mono">_build_system_prompt()</span> rebuilds (conversation_compression.py:515-517); ch.6's iron rule yields here alone.</li>
    <li><strong>Fire near the limit + anti-thrashing</strong>: default 50% window threshold; skip if two in a row saved &lt;10%, avoiding a "remove 1-2 each time" loop.</li>
    <li><strong>Protect head/tail, summarize the middle</strong>: the auxiliary model summarizes middle turns by a structured template (Goal/Decisions/Resolved/...), keeping the original task framing and recent context.</li>
    <li><strong>Fight context rot</strong>: temporal anchoring (to-dos to past tense to prevent re-execution), head-protection decay (no fossilizing), pruning old tool results.</li>
    <li><strong>Also refresh memory</strong>: invalidate triggers <span class="mono">load_from_disk()</span> to reload the memory snapshot (ch.11); the summary is a mid-conversation message, not in the cached prefix.</li>
  </ul>
</div>

<div class="figure">
<svg viewBox="0 0 680 432" role="img" aria-label="The content transform of one real compression: the threshold timeline is in ch.27.3 and this figure only shows how content changes; boundaries protect_first_n=3 decaying to 0 and protect_last_n=20, with 5 middle messages to compress; the cheap prune _prune_old_tool_results with no LLM folds old tool results into one line; the template fills a real summary under Completed Actions and Critical Context REDACTED; tokens drop from about 8400 to about 600; the cache's only exception is _invalidate_system_prompt then _build_system_prompt writing back and load_from_disk.">
  <text x="340" y="22" text-anchor="middle" font-size="13.5" font-weight="700" fill="var(--ink)">One compression's content transform - which 5, folded into what, 8400 to 600 tok</text>
  <text x="340" y="40" text-anchor="middle" font-size="10" fill="var(--muted)">This figure shows only how content changes (already triggered; threshold timeline in ch.27.3)</text>
  <text x="628" y="32" font-size="22">🗜️</text>

  <rect x="20" y="50" width="176" height="214" rx="9" fill="var(--panel)" stroke="var(--line)"/>
  <text x="30" y="68" font-size="10" font-weight="700" fill="var(--ink)">2. Boundary (:787-788)</text>
  <rect x="30" y="76" width="156" height="32" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="38" y="90" font-size="9" font-weight="700" fill="var(--accent-ink)">protect_first_n=3</text>
  <text x="38" y="103" font-size="9" fill="var(--accent-ink)">head, decays to 0 as it grows (:2024)</text>
  <rect x="30" y="116" width="156" height="48" rx="6" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="38" y="132" font-size="9" font-weight="700" fill="var(--purple)">middle 5 msgs - to compress</text>
  <text x="38" y="147" font-size="9" fill="var(--purple)">aux model folds into points</text>
  <text x="38" y="159" font-size="9" fill="var(--purple)">(keep high-signal, drop low)</text>
  <rect x="30" y="172" width="156" height="32" rx="6" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="38" y="186" font-size="9" font-weight="700" fill="var(--blue)">protect_last_n=20</text>
  <text x="38" y="199" font-size="9" fill="var(--blue)">tail, recent context kept as-is</text>
  <text x="30" y="224" font-size="9" fill="var(--muted)">keep head and tail,</text>
  <text x="30" y="240" font-size="9" fill="var(--muted)">compress only the middle</text>
  <text x="30" y="256" font-size="9" fill="var(--muted)">- saves tokens, keeps recents</text>

  <line x1="200" y1="157" x2="218" y2="157" stroke="var(--line)" stroke-width="1.8"/>
  <path d="M224 157 L216 153 L216 161 Z" fill="var(--line)"/>

  <rect x="226" y="50" width="290" height="70" rx="9" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="238" y="68" font-size="10" font-weight="700" fill="var(--ink)">3. Cheap prune _prune_old_tool_results - no LLM (:990)</text>
  <text x="238" y="86" font-size="9" fill="var(--ink)">old tool result body -&gt; 1-line summary (free pre-pass)</text>
  <text x="238" y="104" font-size="9" font-family="monospace" fill="var(--muted)">[old tool output pruned: N lines]</text>

  <rect x="226" y="128" width="290" height="136" rx="9" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
  <text x="238" y="146" font-size="10" font-weight="700" fill="var(--accent-ink)">4. Template fills the real summary - context_compressor.py:1565-1575</text>
  <text x="238" y="164" font-size="9" font-family="monospace" fill="var(--ink)">## Completed Actions</text>
  <text x="238" y="180" font-size="9" font-family="monospace" fill="var(--ink)">1. READ config.py:45 — found == should be != [tool: read_file]</text>
  <text x="238" y="196" font-size="9" font-family="monospace" fill="var(--ink)">3. TEST pytest tests/ — 3/50 failed [tool: terminal]</text>
  <text x="238" y="216" font-size="9" font-family="monospace" fill="var(--ink)">## Critical Context</text>
  <text x="238" y="232" font-size="9" font-family="monospace" fill="var(--red)">[REDACTED]   &lt;- creds/keys always wiped (:1603)</text>
  <text x="238" y="252" font-size="9" fill="var(--muted)">format N. ACTION target — outcome [tool: name]</text>

  <rect x="524" y="50" width="136" height="214" rx="9" fill="var(--panel)" stroke="var(--line)"/>
  <text x="592" y="68" text-anchor="middle" font-size="10" font-weight="700" fill="var(--ink)">5. Token bill</text>
  <rect x="556" y="84" width="72" height="40" rx="6" fill="var(--amber-soft)" stroke="var(--amber)"/>
  <text x="592" y="100" text-anchor="middle" font-size="11" font-weight="700" fill="var(--amber)">~8400</text>
  <text x="592" y="116" text-anchor="middle" font-size="9" fill="var(--amber)">tok (before)</text>
  <line x1="592" y1="130" x2="592" y2="160" stroke="var(--line)" stroke-width="2"/>
  <path d="M592 166 L586 156 L598 156 Z" fill="var(--line)"/>
  <rect x="556" y="172" width="72" height="40" rx="6" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="592" y="188" text-anchor="middle" font-size="11" font-weight="700" fill="var(--accent-ink)">~600</text>
  <text x="592" y="204" text-anchor="middle" font-size="9" fill="var(--accent-ink)">tok (after)</text>
  <text x="592" y="234" text-anchor="middle" font-size="10" font-weight="700" fill="var(--purple)">~ -93%</text>
  <text x="592" y="252" text-anchor="middle" font-size="9" fill="var(--muted)">target ~0.20 ratio</text>

  <rect x="20" y="276" width="640" height="116" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="32" y="294" font-size="10" font-weight="700" fill="var(--blue)">6. The cache's only exception - conversation_compression.py:515-517</text>
  <text x="32" y="314" font-size="9" font-family="monospace" fill="var(--ink)">agent._invalidate_system_prompt()</text>
  <text x="32" y="332" font-size="9" font-family="monospace" fill="var(--ink)">new_system_prompt = agent._build_system_prompt(system_message)</text>
  <text x="32" y="350" font-size="9" font-family="monospace" fill="var(--ink)">agent._cached_system_prompt = new_system_prompt</text>
  <text x="32" y="370" font-size="9" fill="var(--muted)">the same cut piggybacks load_from_disk() to fold this session's new memory/skills in (ch.11)</text>
  <text x="32" y="386" font-size="9" fill="var(--purple)">the only operation in the whole book allowed to touch the sacred cache prefix (ch.6)</text>

  <rect x="20" y="402" width="640" height="20" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="340" y="416" text-anchor="middle" font-size="9" fill="var(--muted)">Read this: compress = keep head(3, decays) + tail(20), fold middle 5 into a ## template summary, wipe creds to [REDACTED], 8400 to 600 tok, the one cache rebuild</text>
</svg>
<div class="fig-cap"><b>One compression's content transform</b>: boundaries <span class="mono">protect_first_n=3</span> (decays to 0 as it grows) / <span class="mono">protect_last_n=20</span>, with the middle <b>5 messages</b> selected to compress; first <span class="mono">_prune_old_tool_results</span> (<b>no LLM</b>) folds old tool results into one line, then the aux model fills the template summary <span class="mono">## Completed Actions</span> (<span class="mono">1. READ config.py:45 — found == should be !=</span> / <span class="mono">3. TEST pytest tests/ — 3/50 failed</span>) and <span class="mono">## Critical Context: [REDACTED]</span>; about <b>8400 to 600 tok</b>. The finish is the book's <b>only</b> cache-prefix mutation: <span class="mono">_invalidate_system_prompt()</span> -&gt; <span class="mono">_build_system_prompt()</span> write-back + <span class="mono">load_from_disk()</span>.</div>
</div>
""",
}


LESSON_16 = {
    "zh": r"""
<p class="lead">
Agent 要「动手」就得跑命令——但跑在<strong>哪里</strong>？你本地的机器、一个 Docker 容器、一台远程服务器、还是 Modal 这样的 <strong>serverless</strong> 平台？Hermes 的答案是：<strong>同一个 terminal 工具，背后是可插拔的多种后端</strong>。模型永远只调一个 <span class="mono">terminal</span>，至于命令落到 local / docker / ssh / modal / singularity / daytona 哪个环境，由一层<strong>统一抽象</strong>透明分派。这让同一个 agent <strong>跑遍各种环境</strong>，也让 serverless 后端能<strong>按需启动、用完释放</strong>省钱。
</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 万能遥控器</div>
  一个<strong>万能遥控器</strong>，按钮永远是「开 / 关 / 音量」（统一接口），但背后能控电视、空调、音响（多种后端）。你<strong>不需要</strong>为每台设备学一套按钮——遥控器内部把「音量+」翻译成各设备的红外码。Hermes 的 terminal 就是这个万能遥控器：模型永远按「跑这条命令」，<span class="mono">BaseEnvironment</span> 这层抽象把它翻译成 local 的 subprocess、docker 的 exec、ssh 的远程命令、modal 的 serverless 调用。换设备只换后端，<strong>遥控器的按钮一个不变</strong>。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 统一抽象,后端差异在边缘</div>
  六种执行后端——<strong>local / docker / ssh / singularity / modal / daytona</strong>——共享<strong>同一个接口</strong> <span class="mono">BaseEnvironment</span>(ABC)。每个后端只需实现 <span class="mono">_run_bash()</span> 和 <span class="mono">cleanup()</span> 两个抽象方法；统一的 <span class="mono">execute()</span>(会话快照、CWD 跟踪、中断、超时)由<strong>基类提供</strong>，所有后端复用。一个工厂 <span class="mono">_create_environment</span> 按 <span class="mono">TERMINAL_ENV</span> 配置挑后端。这正是窄腰(第 4 章)在执行层的体现:<strong>核心只认一个 terminal 工具</strong>,六种环境的差异全被关进边缘的 <span class="mono">BaseEnvironment</span> 子类——加一个新后端,核心一行不动。
</div>

<h2>统一接口:BaseEnvironment ABC</h2>
<p>所有后端的「共同契约」是一个抽象基类——子类只填两个洞，其余流程基类全包了:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/environments/base.py</span><span class="ln">288-345 · 节选</span></div>
  <pre><span class="kw">class</span> <span class="fn">BaseEnvironment</span>(ABC):
    <span class="cm">&quot;&quot;&quot;Common interface and unified execution flow for all Hermes backends.</span>
<span class="cm">    Subclasses implement _run_bash() and cleanup(). The base class</span>
<span class="cm">    provides execute() with session snapshot sourcing, CWD tracking,</span>
<span class="cm">    interrupt handling, and timeout enforcement.&quot;&quot;&quot;</span>

    <span class="kw">def</span> <span class="fn">_run_bash</span>(self, cmd_string, ...) -&gt; ProcessHandle:
        <span class="cm"># 子类必须实现:在各自后端里 spawn 一个 bash 进程</span>
        <span class="kw">raise</span> NotImplementedError

    <span class="nd">@abstractmethod</span>
    <span class="kw">def</span> <span class="fn">cleanup</span>(self):
        <span class="cm"># 释放后端资源(容器/实例/连接)</span>
        ...</pre>
</div>
<p>注意分工:<strong>子类只实现 <span class="mono">_run_bash()</span>(怎么 spawn 进程)和 <span class="mono">cleanup()</span>(怎么释放资源)</strong>;而 <span class="mono">execute()</span>——会话快照恢复、CWD 跟踪、中断处理、超时强制——这些<strong>跨后端通用的流程</strong>由基类<strong>统一提供</strong>,六个后端复用同一套。于是 docker 后端只关心「怎么在容器里跑 bash」,ssh 后端只关心「怎么在远程跑」,通用的会话状态管理它们<strong>都不用重写</strong>。</p>
<p>为什么偏偏让基类握住 <span class="mono">execute()</span>、只把 <span class="mono">_run_bash()</span> 和 <span class="mono">cleanup()</span> 两个洞留给子类?因为会话快照、CWD 跟踪、中断、超时这套流程是<strong>跨后端不变的难点</strong>——一旦写错(CWD 没跟上、超时没强制),六个后端会同时犯病。把它收进基类,等于<strong>写一次、修一次,六个后端同时受益</strong>;新加后端也<strong>无从绕过</strong>这些保护,不会因为作者偷懒就丢掉超时或中断。反过来,若让每个后端各写一份 <span class="mono">execute()</span>,就是六份几乎一样的快照逻辑、六处潜在 bug——这正是「通用骨架沉到基类、可变步骤留给子类」的价值,也是边缘子类能保持<strong>薄而专注</strong>的前提。</p>

<div class="figure">
<svg viewBox="0 0 680 308" role="img" aria-label="多后端统一抽象：核心只认一个 terminal 工具与 BaseEnvironment.execute()，六种后端差异关进各自子类">
  <text x="340" y="15" text-anchor="middle" font-size="13" font-weight="700" fill="var(--accent-ink)">核心只认一个抽象 · 后端差异沉到边缘子类</text>

  <rect x="240" y="26" width="200" height="40" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="340" y="43" text-anchor="middle" font-size="11.5" fill="var(--blue)">模型只调一个</text>
  <text x="340" y="59" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--blue)">terminal 工具</text>
  <polygon points="335,67 345,67 340,75" fill="var(--muted)"/>

  <rect x="150" y="80" width="380" height="66" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2.5"/>
  <text x="340" y="103" text-anchor="middle" font-size="13.5" font-weight="700" fill="var(--accent-ink)">BaseEnvironment.execute() · 统一流程</text>
  <text x="340" y="122" text-anchor="middle" font-size="10.5" fill="var(--accent-ink)">会话快照 · CWD 跟踪 · 中断 · 超时（基类统一提供）</text>
  <text x="340" y="138" text-anchor="middle" font-size="10" fill="var(--accent-ink)">— 窄腰：核心薄，只认这一个接口 —</text>
  <polygon points="335,146 345,146 340,154" fill="var(--muted)"/>

  <rect x="230" y="159" width="220" height="40" rx="9" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="340" y="176" text-anchor="middle" font-size="12" font-weight="700" fill="var(--purple)">_create_environment 工厂</text>
  <text x="340" y="191" text-anchor="middle" font-size="10" fill="var(--purple)">按 TERMINAL_ENV 分派（默认 local）</text>

  <path d="M340 199 L340 210" stroke="var(--line)" stroke-width="1.5"/>
  <path d="M70 210 L610 210" stroke="var(--line)" stroke-width="1.5"/>
  <g font-size="11" font-weight="700" text-anchor="middle">
    <polygon points="66,212 74,212 70,220" fill="var(--muted)"/>
    <rect x="20"  y="220" width="100" height="56" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="70"  y="245" fill="var(--ink)">local</text>
    <polygon points="174,212 182,212 178,220" fill="var(--muted)"/>
    <rect x="128" y="220" width="100" height="56" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="178" y="245" fill="var(--ink)">docker</text>
    <polygon points="282,212 290,212 286,220" fill="var(--muted)"/>
    <rect x="236" y="220" width="100" height="56" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="286" y="245" fill="var(--ink)">ssh</text>
    <polygon points="390,212 398,212 394,220" fill="var(--muted)"/>
    <rect x="344" y="220" width="100" height="56" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="394" y="245" fill="var(--ink)">modal</text>
    <polygon points="498,212 506,212 502,220" fill="var(--muted)"/>
    <rect x="452" y="220" width="100" height="56" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="502" y="245" fill="var(--ink)">daytona</text>
    <polygon points="606,212 614,212 610,220" fill="var(--muted)"/>
    <rect x="560" y="220" width="100" height="56" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="610" y="245" fill="var(--ink)">singularity</text>
  </g>
  <g font-size="9" text-anchor="middle" fill="var(--muted)">
    <text x="70"  y="264">本地子进程</text>
    <text x="178" y="264">容器 · 挂载</text>
    <text x="286" y="264">远程 · 同步</text>
    <text x="394" y="264">serverless</text>
    <text x="502" y="264">云 · 同步</text>
    <text x="610" y="264">容器 · HPC</text>
  </g>
  <text x="340" y="297" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--muted)">▼ 六种后端：隔离 / 文件可见性 / 资源回收的差异，全关进各自子类</text>
</svg>
<div class="fig-cap"><b>多后端统一抽象</b>：模型永远只调一个 <span class="mono">terminal</span>，核心也只认一个 <span class="mono">BaseEnvironment.execute()</span> 抽象（会话快照 / CWD / 中断 / 超时由基类统一兜底）；<span class="mono">_create_environment</span> 工厂按 <span class="mono">TERMINAL_ENV</span> 分派到六个子类。这就是<b>窄腰</b>（第 4 章）在执行层的投影——<span class="mono">terminal</span> 是「该进核心」的工具（第 8 章），而六种环境的差异全沉到<b>边缘子类</b>，加一个后端核心一行不动。</div>
</div>

<p>那么「会话快照」到底是什么?以 local 后端为例,设计很巧:<strong>每次 <span class="mono">execute()</span> 都重新 spawn 一个全新的 bash 进程</strong>(spawn-per-call),命令跑完进程即退。可这样一来,上一条命令 <span class="mono">export</span> 的环境变量、<span class="mono">cd</span> 切换的目录,下一条岂不全丢?基类的「会话快照」正为此:<strong>每条命令结束后把环境变量快照进文件、当前工作目录也写进文件;下一条命令开跑前先回读、source 回来</strong>。于是一串无状态的短命 bash 进程,被串成一个「有记忆」的会话——这正是<strong>约束 B(无状态)</strong>在 shell 执行层的对策:底层进程无状态,靠外部文件快照重建连续性。</p>
<p>那为何不干脆开一个<strong>常驻的交互式 bash</strong>、让状态天然留住,省去快照这套?因为常驻 shell 是<strong>有状态且脆弱</strong>的:进程可能挂死、被某条命令污染,在 docker/ssh/modal 各后端行为还各不相同,难以统一中断与超时。<span class="mono">spawn-per-call</span> 反其道而行——每条命令一个干净的 <span class="mono">bash -c</span>,跑完即弃,<strong>幂等、可重入、六个后端共用一套模型</strong>;状态不靠进程记忆,而靠外部快照文件重建。这与第 2 章「模型调用本身无状态、状态外置」是<strong>同一招在 shell 层的复刻</strong>:底座越无状态,越好移植、越好恢复——daytona 后端被中断后还能从停止的 sandbox 重启接着跑,正得益于这种「状态不在进程里」的设计。</p>
<p>快照里还藏着一处「就地取材」的巧思:环境变量好办——<span class="mono">export -p</span> 重导进快照文件即可;但<strong>当前目录</strong>怎么跨进程传?本地后端直接把 <span class="mono">pwd</span> 写进一个临时文件、下条命令开跑前回读;可远程后端(ssh)没有共享文件系统,于是改用<strong>带内 stdout 标记</strong>——命令尾部 <span class="mono">printf</span> 出一对独有标记包住 <span class="mono">pwd</span>,基类再从输出里把它解析、剥离。同一个「记住 CWD」的需求,本地与远程用了<strong>两条物理通道</strong>,却都收敛到基类同一套 CWD 跟踪逻辑——这又是「通用契约在基类、落地差异在子类」的微观一例。</p>

<div class="figure">
<svg viewBox="0 0 680 312" role="img" aria-label="spawn-per-call 会话快照：每条命令一个全新 bash -c，开跑前 re-source 快照、跑完写回，状态因此延续">
  <text x="340" y="15" text-anchor="middle" font-size="13" font-weight="700" fill="var(--accent-ink)">spawn-per-call：无状态进程 + 外部快照 = 连续会话</text>

  <rect x="20" y="30" width="120" height="46" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="80" y="51" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">init 拍快照</text>
  <text x="80" y="67" text-anchor="middle" font-size="9.5" fill="var(--blue)">函数 / 别名</text>
  <polygon points="148,49 148,57 156,53" fill="var(--muted)"/>

  <rect x="158" y="30" width="502" height="46" rx="9" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2.5"/>
  <text x="409" y="50" text-anchor="middle" font-size="12" font-weight="700" fill="var(--accent-ink)">会话快照文件 · env vars / 函数 / 别名 + CWD</text>
  <text x="409" y="67" text-anchor="middle" font-size="10" fill="var(--accent-ink)">（跨命令持久，下一条命令的“记忆”来源）</text>

  <text x="340" y="97" text-anchor="middle" font-size="10" fill="var(--muted)">每条命令开跑前 re-source 快照（↓），跑完把 env + CWD 写回（↑）——无状态进程被串成连续会话</text>

  <g>
    <line x1="87"  y1="104" x2="87"  y2="134" stroke="var(--accent)" stroke-width="1.5"/>
    <polygon points="83,132 91,132 87,140" fill="var(--accent)"/>
    <line x1="163" y1="138" x2="163" y2="108" stroke="var(--blue)" stroke-width="1.5"/>
    <polygon points="159,110 167,110 163,102" fill="var(--blue)"/>
    <line x1="302" y1="104" x2="302" y2="134" stroke="var(--accent)" stroke-width="1.5"/>
    <polygon points="298,132 306,132 302,140" fill="var(--accent)"/>
    <line x1="378" y1="138" x2="378" y2="108" stroke="var(--blue)" stroke-width="1.5"/>
    <polygon points="374,110 382,110 378,102" fill="var(--blue)"/>
    <line x1="517" y1="104" x2="517" y2="134" stroke="var(--accent)" stroke-width="1.5"/>
    <polygon points="513,132 521,132 517,140" fill="var(--accent)"/>
    <line x1="593" y1="138" x2="593" y2="108" stroke="var(--blue)" stroke-width="1.5"/>
    <polygon points="589,110 597,110 593,102" fill="var(--blue)"/>
  </g>

  <g text-anchor="middle">
    <rect x="40"  y="140" width="170" height="64" rx="9" fill="var(--panel-2)" stroke="var(--line)" stroke-dasharray="5 4"/>
    <text x="125" y="166" font-size="12.5" font-weight="700" fill="var(--ink)">bash -c "cmd₁"</text>
    <text x="125" y="186" font-size="9.5" fill="var(--muted)">全新进程，跑完即退</text>
    <rect x="255" y="140" width="170" height="64" rx="9" fill="var(--panel-2)" stroke="var(--line)" stroke-dasharray="5 4"/>
    <text x="340" y="166" font-size="12.5" font-weight="700" fill="var(--ink)">bash -c "cmd₂"</text>
    <text x="340" y="186" font-size="9.5" fill="var(--muted)">全新进程，跑完即退</text>
    <rect x="470" y="140" width="170" height="64" rx="9" fill="var(--panel-2)" stroke="var(--line)" stroke-dasharray="5 4"/>
    <text x="555" y="166" font-size="12.5" font-weight="700" fill="var(--ink)">bash -c "cmd₃"</text>
    <text x="555" y="186" font-size="9.5" fill="var(--muted)">全新进程，跑完即退</text>
  </g>

  <rect x="40" y="224" width="600" height="44" rx="9" fill="var(--panel)" stroke="var(--line)"/>
  <text x="340" y="244" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--ink)">CWD 怎么跨进程传？</text>
  <text x="340" y="261" text-anchor="middle" font-size="9.5" fill="var(--muted)">本地后端 → 写临时文件、下条回读　|　远程(ssh) → stdout 标记包住 pwd，基类解析剥离</text>

  <text x="340" y="296" text-anchor="middle" font-size="11" font-weight="700" fill="var(--muted)">底层 bash 无状态（约束 B）→ 靠外部快照重建连续性</text>
</svg>
<div class="fig-cap"><b>spawn-per-call 会话快照</b>：模型每轮失忆（第 2 章 B），终端却要维持状态。解法是底层每条命令都起一个<b>全新 <span class="mono">bash -c</span></b>（跑完即退、无状态），但开跑前先 <b>re-source</b> 一份会话快照（env / 函数 / 别名）、跑完把 <span class="mono">env + CWD</span> 写回——一串短命进程因此被串成「有记忆」的连续会话。CWD 经<b>临时文件</b>（本地）或 <b>stdout 标记</b>（远程 ssh）跨进程传递。</div>
</div>

<h2>工厂:按 TERMINAL_ENV 挑后端</h2>
<p>选哪个后端,由一个工厂函数按配置分派——这是「换设备只换后端」的开关:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/terminal_tool.py</span><span class="ln">569 / 1225-1372 · 简化</span></div>
  <pre><span class="cm"># 默认 local;TERMINAL_ENV 配置切换后端</span>
terminal_env = os.getenv(<span class="st">"TERMINAL_ENV"</span>, <span class="st">"local"</span>).strip().lower() <span class="kw">or</span> <span class="st">"local"</span>

<span class="kw">def</span> <span class="fn">_create_environment</span>(env_type, image, cwd, timeout, ...):
    <span class="kw">if</span> env_type == <span class="st">"local"</span>:
        <span class="kw">return</span> _LocalEnvironment(cwd=cwd, timeout=timeout)
    <span class="kw">elif</span> env_type == <span class="st">"docker"</span>:
        <span class="kw">return</span> _DockerEnvironment(...)
    <span class="kw">elif</span> env_type == <span class="st">"modal"</span>:
        <span class="kw">return</span> _ModalEnvironment(...)        <span class="cm"># serverless:按需启动,用完释放</span>
    <span class="kw">elif</span> env_type == <span class="st">"ssh"</span>:
        <span class="kw">return</span> _SSHEnvironment(...)
    ...                                       <span class="cm"># singularity / daytona</span></pre>
</div>
<p><span class="mono">TERMINAL_ENV</span> 默认 <span class="mono">local</span>(本地 subprocess + 进程组隔离),改一个配置就切到 docker(容器隔离)、ssh(远程执行)、modal(serverless)。每个 <span class="mono">_XxxEnvironment</span> 都是 <span class="mono">BaseEnvironment</span> 的子类。工厂是唯一的「分派点」——模型和核心循环<strong>完全不知道</strong>命令落到了哪个环境。换环境=改 <span class="mono">TERMINAL_ENV</span>,不改任何调用代码。</p>
<p>为什么要养这么多后端?因为「跑命令」的真实诉求<strong>各不相同</strong>:本地最快但无隔离、docker/singularity 要容器隔离、ssh 要够到远程主机、modal/daytona 要云端弹性算力。差异不止在「在哪 spawn」,还在<strong>文件怎么可见</strong>:docker/singularity 用 <strong>bind mount</strong> 直接挂宿主目录(实时同主机视图),而 ssh/modal/daytona 是远端、看不到本地文件,于是由 <span class="mono">file_sync</span> 按 mtime+size <strong>事务式同步</strong>本地改动(含删除)过去。所以当远程后端「看不到某个文件」时,正确解法是<strong>修同步/挂载</strong>,而非给核心加一个新工具——这也呼应第 8 章 Footprint Ladder:<span class="mono">terminal</span> 是少数「该进核心」的基础工具,扩能力靠后端在边缘演化,不靠膨胀核心。</p>
<p>这六个后端各自是 <span class="mono">tools/environments/</span> 下一个独立文件里的类——加一个新后端，只需新增一个文件 + 工厂里加一支 <span class="mono">elif</span>：</p>
<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/terminal_tool.py</span><span class="ln">825-831 · 节选</span></div>
  <pre><span class="cm"># Environment classes now live in tools/environments/</span>
<span class="kw">from</span> tools.environments.local <span class="kw">import</span> LocalEnvironment
<span class="kw">from</span> tools.environments.docker <span class="kw">import</span> DockerEnvironment
<span class="kw">from</span> tools.environments.ssh <span class="kw">import</span> SSHEnvironment
<span class="kw">from</span> tools.environments.modal <span class="kw">import</span> ModalEnvironment
<span class="kw">from</span> tools.environments.singularity <span class="kw">import</span> SingularityEnvironment
<span class="kw">from</span> tools.environments.managed_modal <span class="kw">import</span> ManagedModalEnvironment</pre>
</div>
<p style="font-size:.92em;opacity:.85">注:这份顶层 import 与「六个后端」并非一一对应——<span class="mono">daytona</span> 走<strong>惰性导入</strong>(只在被选中时才在工厂分支内 <span class="mono">import</span>),而 <span class="mono">managed_modal</span> 是 modal 的 <strong>Nous 托管模式</strong>(由 <span class="mono">terminal.modal_mode</span> 选),并非独立的 <span class="mono">TERMINAL_ENV</span> 取值。六个 env_type 始终是 local/docker/ssh/singularity/modal/daytona。</p>

<h2>serverless 省钱 + 后台进程</h2>
<p>多后端不只是「能移植」,还能<strong>省钱</strong>。<span class="mono">modal</span> 这类 <strong>serverless</strong> 后端<strong>按需启动</strong>容器、命令跑完就<strong>释放</strong>——你不必常驻一台云服务器,只为偶尔跑几条命令付全天的钱。另外,terminal 支持 <span class="mono">background=True, notify_on_complete=True</span>:长命令在后台跑,gateway 的 watcher 检测到进程完成时<strong>触发一个新 turn</strong>把结果带回——这条「后台完成→新 turn」的路径(和第 13 章委派的完成队列同理)维持了严格角色交替、不破缓存。</p>
<p>serverless 的「用完释放」背后还有一套<strong>资源生命周期</strong>要兜:modal 在 <span class="mono">cleanup()</span> 里 <span class="mono">terminate</span> 掉 sandbox、daytona 停掉持久 sandbox、local 则用 <span class="mono">os.setsid</span> 把命令关进<strong>独立进程组</strong>、清理时整组 SIGTERM→SIGKILL,杜绝孤儿子进程。docker 更棘手:进程被 SIGKILL/OOM 打断会绕过 <span class="mono">atexit</span> 钩子<strong>漏下容器</strong>,所以加了「孤儿回收器」按 <span class="mono">hermes-agent=1</span> 标签每进程一次性清扫,免得下次按 (task, profile) 复用时捡到脏容器。还有一层安全:命令真正下发前要过 <span class="mono">_check_all_guards(command, env_type)</span> 的危险命令审批(第 24 章)——后端再多,危险命令的拦截都收在这<strong>统一一关</strong>,不会因为换了 docker 或 ssh 就漏掉。</p>
<p>容器后端还有一对看似矛盾、实为权衡的开关:<span class="mono">persistent_filesystem</span> 与「按 (task, profile) 复用容器」。每次都新建新销毁最干净,但<strong>冷启动慢、装好的依赖全丢</strong>;于是默认让同一任务复用同一容器、保留文件系统,把「环境搭一次、多条命令接着用」做成常态。代价是容器会跨命令、甚至跨进程留存,这才需要前面那套标签 + 孤儿回收来收尾。可见多后端的复杂度并非凭空堆叠——它是在<strong>启动速度、状态保留、资源回收</strong>三者间替用户做的取舍,而这些取舍统统被关进子类,核心始终只面对一个干净的 <span class="mono">terminal</span>。</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">模型调统一的 <span class="mono">terminal</span> 工具(只管「跑这条命令」)</span></div>
  <div class="step"><span class="num">2</span><span class="sc">工厂 <span class="mono">_create_environment</span> 按 <span class="mono">TERMINAL_ENV</span> 挑后端(local/docker/ssh/modal/...)</span></div>
  <div class="step"><span class="num">3</span><span class="sc">对应 <span class="mono">BaseEnvironment</span> 子类的 <span class="mono">execute()</span>(基类统一:快照/CWD/中断/超时)→ 子类 <span class="mono">_run_bash()</span> 在该后端 spawn 进程</span></div>
  <div class="step"><span class="num">4</span><span class="sc">返回统一的 <span class="mono">ProcessHandle</span>——核心循环不感知后端差异</span></div>
  <div class="step"><span class="num">5</span><span class="sc">serverless 用完 <span class="mono">cleanup()</span> 释放资源;background+notify_on_complete 则后台跑、完成时作新 turn</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「环境可移植」</div>
  <div class="collab-sub">① 组件清单（★本章核心,其余跨章节配合）</div>
  本章核心:<strong>BaseEnvironment ABC</strong>(统一接口 + execute() 通用流程)、<strong>六个后端子类</strong>(各实现 _run_bash/cleanup)、<strong>_create_environment 工厂</strong>(按 TERMINAL_ENV 分派)。跨章节配合:<span class="mono">terminal</span> 是一个核心<strong>工具</strong>(第 8 章),六种后端差异全被关进边缘子类——这正是<strong>窄腰</strong>(第 4 章:核心薄、后端在边缘);子代理委派时拿到<strong>独立的 terminal session</strong>(第 13 章上下文隔离);background+notify_on_complete 的「后台完成→新 turn」与委派完成队列同理(第 13 章),维持严格角色交替不破缓存。
  <div class="collab-sub">② 数据流时序</div>
  模型调 terminal → 工厂按 TERMINAL_ENV 选后端 → BaseEnvironment 子类 execute()(基类统一会话快照/CWD/中断/超时)→ 子类 _run_bash() 在该后端 spawn → 返回统一 ProcessHandle → cleanup() 释放(serverless 用完即放)。
  <div class="collab-sub">③ 关键点</div>
  「同一个 agent 跑遍各种环境」靠的是<strong>统一抽象 + 工厂分派</strong>:核心只认一个 terminal 工具与一个 BaseEnvironment 接口,六种环境(本地/容器/远程/serverless)的全部差异<strong>沉到边缘的子类</strong>。加新后端=写一个 BaseEnvironment 子类 + 工厂加一支,核心零改动。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线:<strong>统一 terminal 抽象 + 多后端 = 环境可移植 + serverless 省钱;后端差异在边缘(窄腰)</strong>。它主要治两条 LLM 固有约束:
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·运维</span>——真实 agent 要在各种环境里干活:本地开发、容器隔离、远程服务器、serverless 弹性。统一的 <span class="mono">BaseEnvironment</span> 抽象让<strong>同一个 agent 无改动地跑遍它们</strong>,serverless 后端还能<strong>按需启停省钱</strong>;会话快照/CWD/超时等运维细节由基类统一兜底。它也是<strong>窄腰</strong>(第 4 章)的体现:核心只认一个 terminal,环境差异在边缘演化。反模式:为每种环境在核心里写一套 if-else 执行逻辑——那会让核心随后端数量膨胀,违背「核心薄、边缘厚」。</p>
  <p style="margin:.5rem 0 0"><span class="badge constraint">B·无状态</span>——底层 bash 进程是无状态的(spawn-per-call,每条命令一个新进程),基类的<strong>会话快照</strong>(环境变量 + CWD 经文件快照/回读)把它们串成连续会话。无状态的执行底座靠外部快照重建记忆——与全书反复出现的「无状态内核 + 外部状态」一脉相承。</p>
  <p style="margin:.5rem 0 0">值得强调的是,这两条约束的解法<strong>共用同一块基座</strong>:正因核心只认一个 <span class="mono">terminal</span> 抽象(窄腰),才能让运维差异(G)与无状态重建(B)<strong>各自在边缘解决而互不打架</strong>——六个后端可以在文件可见性、资源回收、隔离强度上自由分化,核心却始终只看见统一的 <span class="mono">execute()</span> 与 <span class="mono">ProcessHandle</span>。这也是为什么第 8 章把 <span class="mono">terminal</span> 列为「该进核心」的范例:它足够基础、近乎人人要用,且能力扩展不必膨胀核心,只在子类边缘生长。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>统一抽象</strong>:六后端(local/docker/ssh/singularity/modal/daytona)共享 <span class="mono">BaseEnvironment</span> ABC;子类只实现 <span class="mono">_run_bash()</span> + <span class="mono">cleanup()</span>,通用 <span class="mono">execute()</span> 由基类提供。</li>
    <li><strong>工厂分派</strong>:<span class="mono">_create_environment</span> 按 <span class="mono">TERMINAL_ENV</span>(默认 local)挑后端;换环境只改配置,核心零改动。</li>
    <li><strong>环境可移植</strong>:同一 agent 无改动跑遍本地/容器/远程/serverless——窄腰(第 4 章)在执行层的落地。</li>
    <li><strong>serverless 省钱</strong>:modal 等后端按需启动、用完 <span class="mono">cleanup()</span> 释放,不为偶发命令常驻付费。</li>
    <li><strong>后台进程</strong>:<span class="mono">background=True, notify_on_complete=True</span> 后台跑,完成时作新 turn(同委派完成队列,第 13 章),不破缓存。</li>
  </ul>
</div>

<div class="figure">
<svg viewBox="0 0 680 484" role="img" aria-label="export TAG=v2 在 local docker ssh 三后端的真实包裹与 CWD 回传：统一中间脚本三后端逐字相同，先 source 快照、builtin cd 入会话目录、eval 命令、回写 export -p 快照、pwd -P 写临时文件并 printf 吐出 HERMES_CWD 标记；local 用 bash -c 加 os.setsid；docker 用 docker exec id bash -c；ssh 用 ssh bash -c shlex.quote；CWD 回传分叉本地读临时文件、docker 与 ssh 解析 stdout 标记；下一条 echo TAG 得到 v2。">
  <text x="340" y="22" text-anchor="middle" font-size="13.5" font-weight="700" fill="var(--ink)">一条命令，三后端真实包裹 · 同脚本逐字相同 + CWD 回传分叉</text>
  <text x="340" y="40" text-anchor="middle" font-size="10" fill="var(--muted)">例子：terminal(&quot;export TAG=v2&quot;) 在 local / docker / ssh 三后端怎么跑</text>
  <text x="628" y="32" font-size="22">🖥️</text>

  <rect x="20" y="50" width="300" height="258" rx="9" fill="var(--panel)" stroke="var(--line)"/>
  <text x="30" y="68" font-size="10" font-weight="700" fill="var(--ink)">① 统一中间脚本 · 三后端共享 verbatim</text>
  <text x="30" y="82" font-size="9" fill="var(--muted)">tools/environments/base.py:418-470（_wrap_command）</text>
  <text x="30" y="102" font-size="9" font-family="monospace" fill="var(--ink)">source &lt;snap&gt; &gt;/dev/null 2&gt;&amp;1 || true</text>
  <text x="30" y="120" font-size="9" font-family="monospace" fill="var(--accent-ink)">builtin cd -- 'src' || exit 126</text>
  <text x="30" y="138" font-size="9" font-family="monospace" fill="var(--purple)">eval 'export TAG=v2'</text>
  <text x="30" y="156" font-size="9" font-family="monospace" fill="var(--ink)">__hermes_ec=$?</text>
  <text x="30" y="174" font-size="9" font-family="monospace" fill="var(--ink)">export -p &gt; &lt;snap&gt; 2&gt;/dev/null || true</text>
  <text x="30" y="192" font-size="9" font-family="monospace" fill="var(--blue)">pwd -P &gt; &lt;cwd_file&gt; 2&gt;/dev/null || true</text>
  <text x="30" y="210" font-size="9" font-family="monospace" fill="var(--purple)">printf '\n__HERMES_CWD_s1__%s__HERMES_CWD_s1__\n'</text>
  <text x="42" y="226" font-size="9" font-family="monospace" fill="var(--purple)">&quot;$(pwd -P)&quot;</text>
  <text x="30" y="244" font-size="9" font-family="monospace" fill="var(--ink)">exit $__hermes_ec</text>
  <text x="30" y="266" font-size="9" fill="var(--muted)">cd 入会话 cwd → 跑命令 → 回写 env 快照</text>
  <text x="30" y="280" font-size="9" fill="var(--muted)">→ 双通道吐 CWD（临时文件 + stdout 标记）</text>
  <text x="30" y="298" font-size="9" fill="var(--muted)">_cwd_marker(sid)=__HERMES_CWD_s1__（:280）</text>

  <rect x="336" y="50" width="324" height="74" rx="9" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="348" y="68" font-size="10" font-weight="700" fill="var(--accent-ink)">② local · environments/local.py:634-695</text>
  <text x="348" y="88" font-size="9" font-family="monospace" fill="var(--ink)">args = [bash, &quot;-c&quot;, wrapped]</text>
  <text x="348" y="108" font-size="9" font-family="monospace" fill="var(--ink)">preexec_fn = os.setsid  # 独立进程组，可整组中断</text>

  <rect x="336" y="132" width="324" height="74" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="348" y="150" font-size="10" font-weight="700" fill="var(--blue)">③ docker · environments/docker.py:943-964</text>
  <text x="348" y="170" font-size="9" font-family="monospace" fill="var(--ink)">cmd = [docker, exec, &lt;id&gt;, bash, -c, wrapped]</text>
  <text x="348" y="190" font-size="9" fill="var(--muted)">同一脚本塞进容器内 bash 跑</text>

  <rect x="336" y="214" width="324" height="74" rx="9" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="348" y="232" font-size="10" font-weight="700" fill="var(--purple)">④ ssh · environments/ssh.py:343-352</text>
  <text x="348" y="252" font-size="9" font-family="monospace" fill="var(--ink)">ssh … bash -c shlex.quote(wrapped)</text>
  <text x="348" y="272" font-size="9" fill="var(--muted)">整段脚本 shlex.quote 后过 SSH</text>

  <rect x="20" y="320" width="640" height="74" rx="9" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="32" y="338" font-size="10" font-weight="700" fill="var(--ink)">⑤ CWD 回传分叉 · base.py:778-812（_extract_cwd_from_output）</text>
  <text x="32" y="358" font-size="9" fill="var(--blue)">local：读临时文件 _cwd_file（脚本里 pwd -P 已写入）</text>
  <text x="32" y="378" font-size="9" fill="var(--purple)">docker / ssh：解析 stdout 的 __HERMES_CWD_s1__…__HERMES_CWD_s1__ 标记并剥离</text>

  <rect x="20" y="402" width="640" height="40" rx="9" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="32" y="420" font-size="10" font-weight="700" fill="var(--accent-ink)">⑥ 下一条命令（env 经快照跨进程延续）</text>
  <text x="32" y="436" font-size="9" font-family="monospace" fill="var(--ink)">terminal(&quot;echo $TAG&quot;)  →  v2</text>

  <rect x="20" y="452" width="640" height="20" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="340" y="466" text-anchor="middle" font-size="9" fill="var(--muted)">读这张图：同一段包裹脚本三后端逐字相同，只有 spawn 方式（bash -c / docker exec / ssh）和 CWD 回传通道（临时文件 / stdout 标记）不同</text>
</svg>
<div class="fig-cap"><b>一条命令，三后端真实包裹</b>：<span class="mono">_wrap_command</span> 生成的中间脚本三后端<b>逐字相同</b>——<span class="mono">source &lt;snap&gt;</span> → <span class="mono">builtin cd -- 'src' || exit 126</span> → <span class="mono">eval 'export TAG=v2'</span> → <span class="mono">export -p &gt; &lt;snap&gt;</span> → <span class="mono">pwd -P &gt; &lt;cwd_file&gt;</span> → <span class="mono">printf '\n__HERMES_CWD_s1__%s__HERMES_CWD_s1__\n'</span>。差异只在 spawn：local <span class="mono">[bash,-c]+os.setsid</span>、docker <span class="mono">[docker,exec,&lt;id&gt;,bash,-c]</span>、ssh <span class="mono">bash -c shlex.quote</span>；CWD 回传分叉——local 读 <span class="mono">_cwd_file</span>，docker/ssh 解析 stdout 标记。下条 <span class="mono">echo $TAG</span> → <span class="mono">v2</span>。</div>
</div>
""",
    "en": r"""
<p class="lead">
For an agent to "act" it must run commands — but <strong>where</strong>? Your local machine, a Docker container, a remote server, or a <strong>serverless</strong> platform like Modal? Hermes's answer: <strong>one terminal tool, backed by pluggable backends</strong>. The model always calls a single <span class="mono">terminal</span>; whether a command lands on local / docker / ssh / modal / singularity / daytona is dispatched transparently by a <strong>unified abstraction</strong>. This lets one agent <strong>run across all environments</strong>, and lets serverless backends <strong>spin up on demand and release when done</strong> to save money.
</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · a universal remote</div>
  A <strong>universal remote</strong>'s buttons are always "on / off / volume" (unified interface), but it can drive a TV, an AC, a speaker (multiple backends). You <strong>don't</strong> learn a new button layout per device — the remote internally translates "volume+" into each device's IR code. Hermes's terminal is that universal remote: the model always presses "run this command," and the <span class="mono">BaseEnvironment</span> abstraction translates it into local's subprocess, docker's exec, ssh's remote command, modal's serverless call. Swap the device by swapping the backend — <strong>the remote's buttons don't change at all</strong>.
</div>

<div class="card macro">
  <div class="tag">🌍 The big picture · a unified abstraction, backend differences at the edges</div>
  Six execution backends — <strong>local / docker / ssh / singularity / modal / daytona</strong> — share <strong>one interface</strong>, <span class="mono">BaseEnvironment</span> (ABC). Each backend implements just two abstract methods, <span class="mono">_run_bash()</span> and <span class="mono">cleanup()</span>; the unified <span class="mono">execute()</span> (session snapshot, CWD tracking, interrupt, timeout) is <strong>provided by the base class</strong> and reused by all. A factory, <span class="mono">_create_environment</span>, picks the backend by the <span class="mono">TERMINAL_ENV</span> config. This is the narrow waist (ch.4) at the execution layer: <strong>the core knows only one terminal tool</strong>, and the differences of six environments are all caged in edge <span class="mono">BaseEnvironment</span> subclasses — add a new backend, and the core doesn't change a line.
</div>

<h2>The unified interface: the BaseEnvironment ABC</h2>
<p>All backends' "common contract" is an abstract base class — subclasses fill just two holes, the base class handles the rest:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/environments/base.py</span><span class="ln">288-345 · excerpt</span></div>
  <pre><span class="kw">class</span> <span class="fn">BaseEnvironment</span>(ABC):
    <span class="cm">&quot;&quot;&quot;Common interface and unified execution flow for all Hermes backends.</span>
<span class="cm">    Subclasses implement _run_bash() and cleanup(). The base class</span>
<span class="cm">    provides execute() with session snapshot sourcing, CWD tracking,</span>
<span class="cm">    interrupt handling, and timeout enforcement.&quot;&quot;&quot;</span>

    <span class="kw">def</span> <span class="fn">_run_bash</span>(self, cmd_string, ...) -&gt; ProcessHandle:
        <span class="cm"># subclass must implement: spawn a bash process in its own backend</span>
        <span class="kw">raise</span> NotImplementedError

    <span class="nd">@abstractmethod</span>
    <span class="kw">def</span> <span class="fn">cleanup</span>(self):
        <span class="cm"># release backend resources (container/instance/connection)</span>
        ...</pre>
</div>
<p>Note the division: <strong>subclasses implement only <span class="mono">_run_bash()</span> (how to spawn a process) and <span class="mono">cleanup()</span> (how to release resources)</strong>; while <span class="mono">execute()</span> — session snapshot restoration, CWD tracking, interrupt handling, timeout enforcement — these <strong>cross-backend common flows</strong> are <strong>provided uniformly by the base class</strong>, reused by all six backends. So the docker backend cares only about "how to run bash in a container," the ssh backend only about "how to run remotely," and neither <strong>rewrites</strong> the common session-state management.</p>
<p>Why let the base class own <span class="mono">execute()</span> and leave subclasses only the two holes <span class="mono">_run_bash()</span> and <span class="mono">cleanup()</span>? Because session snapshot, CWD tracking, interrupt, and timeout are the <strong>cross-backend invariant hard parts</strong> — get one wrong (CWD doesn't follow, timeout isn't enforced) and all six backends break at once. Folding it into the base class means <strong>write once, fix once, all six benefit</strong>; a new backend <strong>can't bypass</strong> these protections or drop timeouts/interrupts through author laziness. Conversely, letting each backend write its own <span class="mono">execute()</span> would mean six near-identical copies of snapshot logic and six places for bugs — this is the value of "common skeleton sinks to the base, variable steps stay in subclasses," and the precondition for edge subclasses staying <strong>thin and focused</strong>.</p>

<div class="figure">
<svg viewBox="0 0 680 308" role="img" aria-label="A unified multi-backend abstraction: the core knows only one terminal tool and BaseEnvironment.execute(); six backends' differences are caged in subclasses">
  <text x="340" y="15" text-anchor="middle" font-size="13" font-weight="700" fill="var(--accent-ink)">The core knows one abstraction · backend differences sink to edge subclasses</text>

  <rect x="240" y="26" width="200" height="40" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="340" y="43" text-anchor="middle" font-size="11.5" fill="var(--blue)">the model calls one</text>
  <text x="340" y="59" text-anchor="middle" font-size="12.5" font-weight="700" fill="var(--blue)">terminal tool</text>
  <polygon points="335,67 345,67 340,75" fill="var(--muted)"/>

  <rect x="150" y="80" width="380" height="66" rx="10" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2.5"/>
  <text x="340" y="103" text-anchor="middle" font-size="13.5" font-weight="700" fill="var(--accent-ink)">BaseEnvironment.execute() · common flow</text>
  <text x="340" y="122" text-anchor="middle" font-size="10.5" fill="var(--accent-ink)">session snapshot · CWD · interrupt · timeout (base-provided)</text>
  <text x="340" y="138" text-anchor="middle" font-size="10" fill="var(--accent-ink)">— narrow waist: a thin core, one interface only —</text>
  <polygon points="335,146 345,146 340,154" fill="var(--muted)"/>

  <rect x="230" y="159" width="220" height="40" rx="9" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="340" y="176" text-anchor="middle" font-size="12" font-weight="700" fill="var(--purple)">_create_environment factory</text>
  <text x="340" y="191" text-anchor="middle" font-size="10" fill="var(--purple)">dispatch by TERMINAL_ENV (default local)</text>

  <path d="M340 199 L340 210" stroke="var(--line)" stroke-width="1.5"/>
  <path d="M70 210 L610 210" stroke="var(--line)" stroke-width="1.5"/>
  <g font-size="11" font-weight="700" text-anchor="middle">
    <polygon points="66,212 74,212 70,220" fill="var(--muted)"/>
    <rect x="20"  y="220" width="100" height="56" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="70"  y="245" fill="var(--ink)">local</text>
    <polygon points="174,212 182,212 178,220" fill="var(--muted)"/>
    <rect x="128" y="220" width="100" height="56" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="178" y="245" fill="var(--ink)">docker</text>
    <polygon points="282,212 290,212 286,220" fill="var(--muted)"/>
    <rect x="236" y="220" width="100" height="56" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="286" y="245" fill="var(--ink)">ssh</text>
    <polygon points="390,212 398,212 394,220" fill="var(--muted)"/>
    <rect x="344" y="220" width="100" height="56" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="394" y="245" fill="var(--ink)">modal</text>
    <polygon points="498,212 506,212 502,220" fill="var(--muted)"/>
    <rect x="452" y="220" width="100" height="56" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="502" y="245" fill="var(--ink)">daytona</text>
    <polygon points="606,212 614,212 610,220" fill="var(--muted)"/>
    <rect x="560" y="220" width="100" height="56" rx="8" fill="var(--panel-2)" stroke="var(--line)"/>
    <text x="610" y="245" fill="var(--ink)">singularity</text>
  </g>
  <g font-size="9" text-anchor="middle" fill="var(--muted)">
    <text x="70"  y="264">local subproc</text>
    <text x="178" y="264">container · mount</text>
    <text x="286" y="264">remote · sync</text>
    <text x="394" y="264">serverless</text>
    <text x="502" y="264">cloud · sync</text>
    <text x="610" y="264">container · HPC</text>
  </g>
  <text x="340" y="297" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--muted)">▼ Six backends: isolation / file visibility / cleanup differences all caged in subclasses</text>
</svg>
<div class="fig-cap"><b>Unified multi-backend abstraction</b>: the model always calls one <span class="mono">terminal</span>, and the core knows only one <span class="mono">BaseEnvironment.execute()</span> abstraction (session snapshot / CWD / interrupt / timeout handled by the base class); the <span class="mono">_create_environment</span> factory dispatches to six subclasses by <span class="mono">TERMINAL_ENV</span>. This is the <b>narrow waist</b> (ch.4) projected onto the execution layer — <span class="mono">terminal</span> is a tool that "belongs in the core" (ch.8), while six environments' differences sink to <b>edge subclasses</b>: add a backend, the core doesn't change a line.</div>
</div>

<p>So what exactly is that "session snapshot"? Take the local backend — the design is elegant: <strong>every <span class="mono">execute()</span> spawns a brand-new bash process</strong> (spawn-per-call) that exits the moment the command finishes. But then wouldn't the env vars <span class="mono">export</span>ed by the previous command, and the directory it <span class="mono">cd</span>'d into, be lost for the next one? The base class's "session snapshot" is exactly for this: <strong>after each command it snapshots env vars into a file and writes the current working directory to a file too; before the next command runs, it reads them back and sources them in</strong>. So a string of stateless, short-lived bash processes is woven into a session "with memory" — precisely the countermeasure for <strong>constraint B (statelessness)</strong> at the shell-execution layer: the underlying processes are stateless, and continuity is rebuilt from external file snapshots.</p>
<p>So why not just open a <strong>long-lived interactive bash</strong> and let state persist naturally, skipping the snapshot machinery? Because a persistent shell is <strong>stateful and fragile</strong>: the process can hang, get polluted by some command, and behaves differently across docker/ssh/modal backends, making unified interrupt and timeout hard. <span class="mono">spawn-per-call</span> goes the other way — each command gets a clean <span class="mono">bash -c</span>, discarded once done, <strong>idempotent, re-entrant, one model shared by all six backends</strong>; state isn't kept in process memory but rebuilt from external snapshot files. This is <strong>the same move as ch.2's "the model call itself is stateless, state lives outside," replayed at the shell layer</strong>: the more stateless the substrate, the easier to port and recover — the daytona backend can even restart a stopped sandbox and resume after an interrupt, precisely thanks to this "state isn't in the process" design.</p>
<p>The snapshot also hides a "use what's already there" trick: env vars are easy — just <span class="mono">export -p</span> them back into the snapshot file; but how do you carry the <strong>current directory</strong> across processes? The local backend writes <span class="mono">pwd</span> into a temp file and reads it back before the next command; but a remote backend (ssh) has no shared filesystem, so it switches to an <strong>in-band stdout marker</strong> — the command tail <span class="mono">printf</span>s a unique pair of markers wrapping <span class="mono">pwd</span>, and the base class parses and strips it from the output. The very same "remember the CWD" need uses <strong>two physical channels</strong> for local vs remote, yet both converge on the base class's single CWD-tracking logic — another micro example of "common contract in the base, landing differences in subclasses."</p>

<div class="figure">
<svg viewBox="0 0 680 312" role="img" aria-label="spawn-per-call session snapshot: each command is a fresh bash -c; re-source the snapshot before, write it back after, so state carries across">
  <text x="340" y="15" text-anchor="middle" font-size="13" font-weight="700" fill="var(--accent-ink)">spawn-per-call: stateless processes + an external snapshot = a continuous session</text>

  <rect x="20" y="30" width="120" height="46" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="80" y="51" text-anchor="middle" font-size="11.5" font-weight="700" fill="var(--blue)">init snapshot</text>
  <text x="80" y="67" text-anchor="middle" font-size="9.5" fill="var(--blue)">functions / aliases</text>
  <polygon points="148,49 148,57 156,53" fill="var(--muted)"/>

  <rect x="158" y="30" width="502" height="46" rx="9" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2.5"/>
  <text x="409" y="50" text-anchor="middle" font-size="12" font-weight="700" fill="var(--accent-ink)">session snapshot file · env vars / functions / aliases + CWD</text>
  <text x="409" y="67" text-anchor="middle" font-size="10" fill="var(--accent-ink)">(persists across commands — the next command's "memory")</text>

  <text x="340" y="97" text-anchor="middle" font-size="10" fill="var(--muted)">before each command re-source the snapshot (↓), after it write env + CWD back (↑) — stateless processes woven into a session</text>

  <g>
    <line x1="87"  y1="104" x2="87"  y2="134" stroke="var(--accent)" stroke-width="1.5"/>
    <polygon points="83,132 91,132 87,140" fill="var(--accent)"/>
    <line x1="163" y1="138" x2="163" y2="108" stroke="var(--blue)" stroke-width="1.5"/>
    <polygon points="159,110 167,110 163,102" fill="var(--blue)"/>
    <line x1="302" y1="104" x2="302" y2="134" stroke="var(--accent)" stroke-width="1.5"/>
    <polygon points="298,132 306,132 302,140" fill="var(--accent)"/>
    <line x1="378" y1="138" x2="378" y2="108" stroke="var(--blue)" stroke-width="1.5"/>
    <polygon points="374,110 382,110 378,102" fill="var(--blue)"/>
    <line x1="517" y1="104" x2="517" y2="134" stroke="var(--accent)" stroke-width="1.5"/>
    <polygon points="513,132 521,132 517,140" fill="var(--accent)"/>
    <line x1="593" y1="138" x2="593" y2="108" stroke="var(--blue)" stroke-width="1.5"/>
    <polygon points="589,110 597,110 593,102" fill="var(--blue)"/>
  </g>

  <g text-anchor="middle">
    <rect x="40"  y="140" width="170" height="64" rx="9" fill="var(--panel-2)" stroke="var(--line)" stroke-dasharray="5 4"/>
    <text x="125" y="166" font-size="12.5" font-weight="700" fill="var(--ink)">bash -c "cmd₁"</text>
    <text x="125" y="186" font-size="9.5" fill="var(--muted)">fresh process, exits when done</text>
    <rect x="255" y="140" width="170" height="64" rx="9" fill="var(--panel-2)" stroke="var(--line)" stroke-dasharray="5 4"/>
    <text x="340" y="166" font-size="12.5" font-weight="700" fill="var(--ink)">bash -c "cmd₂"</text>
    <text x="340" y="186" font-size="9.5" fill="var(--muted)">fresh process, exits when done</text>
    <rect x="470" y="140" width="170" height="64" rx="9" fill="var(--panel-2)" stroke="var(--line)" stroke-dasharray="5 4"/>
    <text x="555" y="166" font-size="12.5" font-weight="700" fill="var(--ink)">bash -c "cmd₃"</text>
    <text x="555" y="186" font-size="9.5" fill="var(--muted)">fresh process, exits when done</text>
  </g>

  <rect x="40" y="224" width="600" height="44" rx="9" fill="var(--panel)" stroke="var(--line)"/>
  <text x="340" y="244" text-anchor="middle" font-size="10.5" font-weight="700" fill="var(--ink)">How is CWD carried across processes?</text>
  <text x="340" y="261" text-anchor="middle" font-size="9.5" fill="var(--muted)">local backend → temp file, read back next time  |  remote (ssh) → stdout markers wrap pwd, base class parses &amp; strips</text>

  <text x="340" y="296" text-anchor="middle" font-size="11" font-weight="700" fill="var(--muted)">underlying bash is stateless (constraint B) → continuity rebuilt from external snapshots</text>
</svg>
<div class="fig-cap"><b>spawn-per-call session snapshot</b>: the model is amnesiac every turn (ch.2 B), yet the terminal must keep state. The fix: each command spawns a <b>fresh <span class="mono">bash -c</span></b> (exits when done, stateless), but before it runs it <b>re-sources</b> a session snapshot (env / functions / aliases) and after it writes <span class="mono">env + CWD</span> back — a string of short-lived processes woven into a session "with memory." CWD travels across processes via a <b>temp file</b> (local) or <b>stdout markers</b> (remote ssh).</div>
</div>

<h2>The factory: pick the backend by TERMINAL_ENV</h2>
<p>Which backend is chosen is dispatched by a factory function from config — the switch for "swap the device by swapping the backend":</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/terminal_tool.py</span><span class="ln">569 / 1225-1372 · simplified</span></div>
  <pre><span class="cm"># default local; TERMINAL_ENV switches the backend</span>
terminal_env = os.getenv(<span class="st">"TERMINAL_ENV"</span>, <span class="st">"local"</span>).strip().lower() <span class="kw">or</span> <span class="st">"local"</span>

<span class="kw">def</span> <span class="fn">_create_environment</span>(env_type, image, cwd, timeout, ...):
    <span class="kw">if</span> env_type == <span class="st">"local"</span>:
        <span class="kw">return</span> _LocalEnvironment(cwd=cwd, timeout=timeout)
    <span class="kw">elif</span> env_type == <span class="st">"docker"</span>:
        <span class="kw">return</span> _DockerEnvironment(...)
    <span class="kw">elif</span> env_type == <span class="st">"modal"</span>:
        <span class="kw">return</span> _ModalEnvironment(...)        <span class="cm"># serverless: spin up on demand, release when done</span>
    <span class="kw">elif</span> env_type == <span class="st">"ssh"</span>:
        <span class="kw">return</span> _SSHEnvironment(...)
    ...                                       <span class="cm"># singularity / daytona</span></pre>
</div>
<p><span class="mono">TERMINAL_ENV</span> defaults to <span class="mono">local</span> (local subprocess + process-group isolation); change one config to switch to docker (container isolation), ssh (remote), modal (serverless). Each <span class="mono">_XxxEnvironment</span> is a subclass of <span class="mono">BaseEnvironment</span>. The factory is the single "dispatch point" — the model and the core loop have <strong>no idea</strong> which environment a command landed on. Switch environments = change <span class="mono">TERMINAL_ENV</span>, change no calling code.</p>
<p>Why keep so many backends? Because the real needs behind "run a command" <strong>differ</strong>: local is fastest but unisolated, docker/singularity want container isolation, ssh must reach a remote host, modal/daytona want elastic cloud compute. The difference isn't only "where to spawn" but also <strong>how files become visible</strong>: docker/singularity use <strong>bind mounts</strong> onto the host directory (a live host-FS view), while ssh/modal/daytona are remote and can't see local files, so <span class="mono">file_sync</span> <strong>transactionally syncs</strong> local changes (deletions included) over by mtime+size. So when a remote backend "can't see a file," the right fix is to <strong>fix the sync/mount</strong>, not add a new core tool — echoing ch.8's Footprint Ladder: <span class="mono">terminal</span> is one of the few foundational tools that <strong>belong in the core</strong>, with capability growing at the backend edges rather than by bloating the core.</p>
<p>Each of these six backends is a class in its own file under <span class="mono">tools/environments/</span> — adding a new backend just needs a new file + one <span class="mono">elif</span> in the factory:</p>
<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/terminal_tool.py</span><span class="ln">825-831 · excerpt</span></div>
  <pre><span class="cm"># Environment classes now live in tools/environments/</span>
<span class="kw">from</span> tools.environments.local <span class="kw">import</span> LocalEnvironment
<span class="kw">from</span> tools.environments.docker <span class="kw">import</span> DockerEnvironment
<span class="kw">from</span> tools.environments.ssh <span class="kw">import</span> SSHEnvironment
<span class="kw">from</span> tools.environments.modal <span class="kw">import</span> ModalEnvironment
<span class="kw">from</span> tools.environments.singularity <span class="kw">import</span> SingularityEnvironment
<span class="kw">from</span> tools.environments.managed_modal <span class="kw">import</span> ManagedModalEnvironment</pre>
</div>
<p style="font-size:.92em;opacity:.85">Note: this top-level import list is <strong>not</strong> one-to-one with the "six backends" — <span class="mono">daytona</span> is <strong>lazily imported</strong> (only <span class="mono">import</span>ed inside its factory branch when selected), and <span class="mono">managed_modal</span> is modal's <strong>Nous-managed mode</strong> (chosen via <span class="mono">terminal.modal_mode</span>), not a standalone <span class="mono">TERMINAL_ENV</span> value. The six env types are always local/docker/ssh/singularity/modal/daytona.</p>

<h2>serverless savings + background processes</h2>
<p>Multiple backends aren't just "portable" — they also <strong>save money</strong>. Serverless backends like <span class="mono">modal</span> <strong>spin up</strong> a container on demand and <strong>release</strong> it when the command finishes — you needn't keep a cloud server running around the clock just to run a few commands occasionally. Also, the terminal supports <span class="mono">background=True, notify_on_complete=True</span>: a long command runs in the background, and when the gateway's watcher detects the process finished it <strong>triggers a new turn</strong> to bring the result back — this "background done → new turn" path (same idea as ch.13's delegation completion queue) keeps strict role alternation and doesn't break the cache.</p>
<p>Behind serverless's "release when done" sits a whole <strong>resource lifecycle</strong> to handle: modal <span class="mono">terminate</span>s its sandbox in <span class="mono">cleanup()</span>, daytona stops its persistent sandbox, and local uses <span class="mono">os.setsid</span> to cage the command in its <strong>own process group</strong>, escalating SIGTERM→SIGKILL on the whole group at cleanup so no orphaned children survive. Docker is trickier: a process killed by SIGKILL/OOM bypasses the <span class="mono">atexit</span> hook and <strong>leaks containers</strong>, so an "orphan reaper" sweeps labeled (<span class="mono">hermes-agent=1</span>) containers once per process, so the next (task, profile) reuse doesn't pick up a dirty container. And one more layer — security: before a command actually runs it passes <span class="mono">_check_all_guards(command, env_type)</span> for dangerous-command approval (ch.24) — no matter how many backends there are, dangerous-command interception sits at this <strong>single uniform gate</strong>, never dropped just because you switched to docker or ssh.</p>
<p>Container backends carry one more seemingly-contradictory but really-a-trade-off pair of switches: <span class="mono">persistent_filesystem</span> and "reuse a container by (task, profile)." Create-and-destroy every time is cleanest, but <strong>cold starts are slow and installed deps are lost</strong>; so by default the same task reuses the same container and keeps its filesystem, making "build the environment once, then run many commands on it" the norm. The cost is that containers persist across commands — even across processes — which is exactly why the earlier label + orphan-reaper machinery is needed to clean up. So the complexity of multiple backends isn't piled on for nothing — it's a trade-off made on the user's behalf among <strong>startup speed, state retention, and resource reclamation</strong>, and all of those trade-offs are caged in subclasses while the core only ever faces one clean <span class="mono">terminal</span>.</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">the model calls the unified <span class="mono">terminal</span> tool (just "run this command")</span></div>
  <div class="step"><span class="num">2</span><span class="sc">the factory <span class="mono">_create_environment</span> picks the backend by <span class="mono">TERMINAL_ENV</span> (local/docker/ssh/modal/...)</span></div>
  <div class="step"><span class="num">3</span><span class="sc">the matching <span class="mono">BaseEnvironment</span> subclass's <span class="mono">execute()</span> (base: snapshot/CWD/interrupt/timeout) → subclass <span class="mono">_run_bash()</span> spawns a process in that backend</span></div>
  <div class="step"><span class="num">4</span><span class="sc">returns a unified <span class="mono">ProcessHandle</span> — the core loop is unaware of backend differences</span></div>
  <div class="step"><span class="num">5</span><span class="sc">serverless <span class="mono">cleanup()</span> releases resources when done; background+notify_on_complete runs in the background, surfacing as a new turn on completion</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "environment portability"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: the <strong>BaseEnvironment ABC</strong> (unified interface + execute() common flow), the <strong>six backend subclasses</strong> (each implements _run_bash/cleanup), the <strong>_create_environment factory</strong> (dispatch by TERMINAL_ENV). Cross-chapter teamwork: <span class="mono">terminal</span> is one core <strong>tool</strong> (ch.8), and six backends' differences are all caged in edge subclasses — exactly the <strong>narrow waist</strong> (ch.4: thin core, backends at the edges); a delegated subagent gets its own <strong>independent terminal session</strong> (ch.13 context isolation); background+notify_on_complete's "background done → new turn" works like the delegation completion queue (ch.13), keeping strict alternation and the cache.
  <div class="collab-sub">② Data-flow timing</div>
  the model calls terminal → the factory picks the backend by TERMINAL_ENV → the BaseEnvironment subclass's execute() (base-unified session snapshot/CWD/interrupt/timeout) → the subclass's _run_bash() spawns in that backend → returns a unified ProcessHandle → cleanup() releases (serverless frees when done).
  <div class="collab-sub">③ The key point</div>
  "One agent runs across all environments" rests on a <strong>unified abstraction + factory dispatch</strong>: the core knows only one terminal tool and one BaseEnvironment interface, and all the differences of six environments (local/container/remote/serverless) <strong>sink to edge subclasses</strong>. Add a new backend = write a BaseEnvironment subclass + one factory branch, with zero change to the core.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>a unified terminal abstraction + multiple backends = environment portability + serverless savings; backend differences at the edges (narrow waist)</strong>. It mainly treats two inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·ops</span> — a real agent must work in all kinds of environments: local dev, container isolation, remote servers, serverless elasticity. The unified <span class="mono">BaseEnvironment</span> abstraction lets <strong>one agent run across them unchanged</strong>, and serverless backends can <strong>start/stop on demand to save money</strong>; ops details like session snapshot/CWD/timeout are handled uniformly by the base class. It's also the <strong>narrow waist</strong> (ch.4): the core knows only one terminal, and environment differences evolve at the edges. The anti-pattern: writing per-environment if-else execution logic in the core — that bloats the core with each backend added, against "thin core, thick edges."</p>
  <p style="margin:.5rem 0 0"><span class="badge constraint">B·statelessness</span> — the underlying bash processes are stateless (spawn-per-call, a new process per command); the base class's <strong>session snapshot</strong> (env vars + CWD via file snapshot/read-back) strings them into a continuous session. A stateless execution substrate rebuilds memory from external snapshots — of a piece with the book's recurring "stateless core + external state."</p>
  <p style="margin:.5rem 0 0">Worth stressing: the fixes for both constraints <strong>share one substrate</strong>: precisely because the core knows only one <span class="mono">terminal</span> abstraction (the narrow waist), ops differences (G) and stateless rebuild (B) can <strong>each be solved at the edges without colliding</strong> — the six backends are free to diverge on file visibility, resource reclamation, and isolation strength, while the core only ever sees a unified <span class="mono">execute()</span> and <span class="mono">ProcessHandle</span>. This is also why ch.8 lists <span class="mono">terminal</span> as the model of a tool that <strong>belongs in the core</strong>: it's foundational, almost universally needed, and its capability grows at subclass edges without bloating the core.</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Unified abstraction</strong>: six backends (local/docker/ssh/singularity/modal/daytona) share the <span class="mono">BaseEnvironment</span> ABC; subclasses implement only <span class="mono">_run_bash()</span> + <span class="mono">cleanup()</span>, the common <span class="mono">execute()</span> is provided by the base class.</li>
    <li><strong>Factory dispatch</strong>: <span class="mono">_create_environment</span> picks the backend by <span class="mono">TERMINAL_ENV</span> (default local); switch environments by config only, zero core change.</li>
    <li><strong>Environment portability</strong>: one agent runs across local/container/remote/serverless unchanged — the narrow waist (ch.4) at the execution layer.</li>
    <li><strong>serverless savings</strong>: backends like modal start on demand and <span class="mono">cleanup()</span> when done, not paying to keep a server running for occasional commands.</li>
    <li><strong>Background processes</strong>: <span class="mono">background=True, notify_on_complete=True</span> runs in the background and surfaces as a new turn on completion (like the delegation completion queue, ch.13), not breaking the cache.</li>
  </ul>
</div>

<div class="figure">
<svg viewBox="0 0 680 484" role="img" aria-label="export TAG=v2 wrapped across local docker and ssh backends with CWD return: the unified middle script is byte-identical across backends, sourcing the snapshot, builtin cd into the session dir, eval the command, write back export -p snapshot, pwd -P to a temp file and printf emits the HERMES_CWD marker; local uses bash -c plus os.setsid; docker uses docker exec id bash -c; ssh uses ssh bash -c shlex.quote; CWD return forks where local reads the temp file and docker and ssh parse the stdout marker; the next command echo TAG yields v2.">
  <text x="340" y="22" text-anchor="middle" font-size="13.5" font-weight="700" fill="var(--ink)">One command, three real wrappers - same script byte-for-byte + CWD return fork</text>
  <text x="340" y="40" text-anchor="middle" font-size="10" fill="var(--muted)">Example: how terminal(&quot;export TAG=v2&quot;) runs on local / docker / ssh</text>
  <text x="628" y="32" font-size="22">🖥️</text>

  <rect x="20" y="50" width="300" height="258" rx="9" fill="var(--panel)" stroke="var(--line)"/>
  <text x="30" y="68" font-size="10" font-weight="700" fill="var(--ink)">1. Unified middle script - shared verbatim by all 3</text>
  <text x="30" y="82" font-size="9" fill="var(--muted)">tools/environments/base.py:418-470 (_wrap_command)</text>
  <text x="30" y="102" font-size="9" font-family="monospace" fill="var(--ink)">source &lt;snap&gt; &gt;/dev/null 2&gt;&amp;1 || true</text>
  <text x="30" y="120" font-size="9" font-family="monospace" fill="var(--accent-ink)">builtin cd -- 'src' || exit 126</text>
  <text x="30" y="138" font-size="9" font-family="monospace" fill="var(--purple)">eval 'export TAG=v2'</text>
  <text x="30" y="156" font-size="9" font-family="monospace" fill="var(--ink)">__hermes_ec=$?</text>
  <text x="30" y="174" font-size="9" font-family="monospace" fill="var(--ink)">export -p &gt; &lt;snap&gt; 2&gt;/dev/null || true</text>
  <text x="30" y="192" font-size="9" font-family="monospace" fill="var(--blue)">pwd -P &gt; &lt;cwd_file&gt; 2&gt;/dev/null || true</text>
  <text x="30" y="210" font-size="9" font-family="monospace" fill="var(--purple)">printf '\n__HERMES_CWD_s1__%s__HERMES_CWD_s1__\n'</text>
  <text x="42" y="226" font-size="9" font-family="monospace" fill="var(--purple)">&quot;$(pwd -P)&quot;</text>
  <text x="30" y="244" font-size="9" font-family="monospace" fill="var(--ink)">exit $__hermes_ec</text>
  <text x="30" y="266" font-size="9" fill="var(--muted)">cd into session cwd -&gt; run -&gt; write env snapshot</text>
  <text x="30" y="280" font-size="9" fill="var(--muted)">-&gt; emit CWD on two channels (temp file + stdout)</text>
  <text x="30" y="298" font-size="9" fill="var(--muted)">_cwd_marker(sid)=__HERMES_CWD_s1__ (:280)</text>

  <rect x="336" y="50" width="324" height="74" rx="9" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="348" y="68" font-size="10" font-weight="700" fill="var(--accent-ink)">2. local - environments/local.py:634-695</text>
  <text x="348" y="88" font-size="9" font-family="monospace" fill="var(--ink)">args = [bash, &quot;-c&quot;, wrapped]</text>
  <text x="348" y="108" font-size="9" font-family="monospace" fill="var(--ink)">preexec_fn = os.setsid  # own pgid, group-interruptible</text>

  <rect x="336" y="132" width="324" height="74" rx="9" fill="var(--blue-soft)" stroke="var(--blue)"/>
  <text x="348" y="150" font-size="10" font-weight="700" fill="var(--blue)">3. docker - environments/docker.py:943-964</text>
  <text x="348" y="170" font-size="9" font-family="monospace" fill="var(--ink)">cmd = [docker, exec, &lt;id&gt;, bash, -c, wrapped]</text>
  <text x="348" y="190" font-size="9" fill="var(--muted)">same script, run by bash inside the container</text>

  <rect x="336" y="214" width="324" height="74" rx="9" fill="var(--purple-soft)" stroke="var(--purple)"/>
  <text x="348" y="232" font-size="10" font-weight="700" fill="var(--purple)">4. ssh - environments/ssh.py:343-352</text>
  <text x="348" y="252" font-size="9" font-family="monospace" fill="var(--ink)">ssh … bash -c shlex.quote(wrapped)</text>
  <text x="348" y="272" font-size="9" fill="var(--muted)">whole script shlex.quote'd, sent over SSH</text>

  <rect x="20" y="320" width="640" height="74" rx="9" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="32" y="338" font-size="10" font-weight="700" fill="var(--ink)">5. CWD return fork - base.py:778-812 (_extract_cwd_from_output)</text>
  <text x="32" y="358" font-size="9" fill="var(--blue)">local: reads the temp file _cwd_file (pwd -P already wrote it)</text>
  <text x="32" y="378" font-size="9" fill="var(--purple)">docker / ssh: parse the stdout __HERMES_CWD_s1__…__HERMES_CWD_s1__ marker and strip it</text>

  <rect x="20" y="402" width="640" height="40" rx="9" fill="var(--accent-soft)" stroke="var(--accent)"/>
  <text x="32" y="420" font-size="10" font-weight="700" fill="var(--accent-ink)">6. Next command (env carries across via the snapshot)</text>
  <text x="32" y="436" font-size="9" font-family="monospace" fill="var(--ink)">terminal(&quot;echo $TAG&quot;)  -&gt;  v2</text>

  <rect x="20" y="452" width="640" height="20" rx="6" fill="var(--panel-2)" stroke="var(--line)"/>
  <text x="340" y="466" text-anchor="middle" font-size="9" fill="var(--muted)">Read this: the same wrapper script is byte-identical across backends; only the spawn (bash -c / docker exec / ssh) and the CWD channel (temp file / stdout marker) differ</text>
</svg>
<div class="fig-cap"><b>One command, three real wrappers</b>: the middle script from <span class="mono">_wrap_command</span> is <b>byte-identical</b> across backends - <span class="mono">source &lt;snap&gt;</span> -&gt; <span class="mono">builtin cd -- 'src' || exit 126</span> -&gt; <span class="mono">eval 'export TAG=v2'</span> -&gt; <span class="mono">export -p &gt; &lt;snap&gt;</span> -&gt; <span class="mono">pwd -P &gt; &lt;cwd_file&gt;</span> -&gt; <span class="mono">printf '\n__HERMES_CWD_s1__%s__HERMES_CWD_s1__\n'</span>. Only the spawn differs: local <span class="mono">[bash,-c]+os.setsid</span>, docker <span class="mono">[docker,exec,&lt;id&gt;,bash,-c]</span>, ssh <span class="mono">bash -c shlex.quote</span>; the CWD return forks - local reads <span class="mono">_cwd_file</span>, docker/ssh parse the stdout marker. The next <span class="mono">echo $TAG</span> -&gt; <span class="mono">v2</span>.</div>
</div>
""",
}
