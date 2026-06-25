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
