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
  主线：<strong>统一抽象 + 严格角色交替不变量</strong>——一套 messages，多家后端；并在每次 API 调用前修复交替。它治三条 LLM 固有约束：
  <p style="margin:.5rem 0 0"><span class="badge constraint">E·结构化输出脆弱</span>——function calling / tool schema 统一成 OpenAI 格式，由 adapter 各自翻成方言（xAI 还要现场剥掉它不认的 schema 关键字），把「结构化输出对方言敏感」这件脆弱事关进边缘层；
  <span class="badge constraint">G·推理token不持久</span>——<span class="mono">reasoning_details</span> 原样跨轮 replay，让模型「接着上轮想」；
  <span class="badge constraint">D·提示脆弱</span>——统一格式把 provider 差异<strong>隔离</strong>，核心 prompt 不必为每家后端写一套。反模式：把某家 provider 的特殊字段、特殊鉴权<strong>泄漏进核心循环</strong>——那等于让指挥官去学方言，每加一家就要改一次核心。</p>
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
  The throughline: <strong>a unified abstraction + the strict role-alternation invariant</strong> — one set of messages, many backends; with alternation repaired before every API call. It treats three inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">E·brittle structured output</span> — function calling / tool schemas unify into OpenAI format, with each adapter translating into a dialect (xAI even strips schema keywords it rejects on the spot), caging the "structured output is dialect-sensitive" fragility in the edge layer;
  <span class="badge constraint">G·reasoning tokens not persisted</span> — <span class="mono">reasoning_details</span> replays verbatim across turns so the model can "keep thinking from last turn";
  <span class="badge constraint">D·prompt brittleness</span> — the unified format <strong>isolates</strong> provider differences so the core prompt needn't be rewritten per backend. The anti-pattern: <strong>leaking</strong> one provider's special fields or auth <strong>into the core loop</strong> — that's making the commander learn dialects, rewriting the core for every backend added.</p>
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
