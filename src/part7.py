LESSON_24 = {
    "zh": r"""
<p class="lead">Hermes 有<strong>真实的权限</strong>:跑终端命令、开浏览器、读写文件、连你的消息平台。这意味着威胁也是真实的——恶意输入想<strong>注入</strong>指令、被污染的技能想<strong>中毒</strong>、一条 <span class="mono">rm -rf /</span> 想<strong>毁掉系统</strong>。本章是横向专题:Hermes 怎么用<strong>纵深防御</strong>把这些威胁层层挡住。</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 银行金库的多层安保</div>
  没有哪一道锁是绝对的,所以银行<strong>层层设防</strong>:门禁刷卡(命令审批)、保安认黑名单脸(危险模式检测)、柜员权限分级(子代理最小权限)、供应商背景审查(依赖锁定)。<strong>单层失守,还有下一层兜底。</strong>关键是:别指望"信任一个聪明的内部人"就够了——因为那个内部人(模型)可能被一句话<strong>骗</strong>(注入)。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 纵深防御(Defense in Depth)</div>
  agent 越能干,爆炸半径越大,所以安全是<strong>多层独立</strong>的:① 危险命令要<strong>审批</strong>(红线模式连 yolo 都不放行);② 子代理<strong>剥离</strong>高危工具(最小权限);③ 控制命令在网关就和数据流<strong>分离</strong>(防注入,第 18 章);④ 依赖全<strong>钉死版本</strong>(防供应链投毒)。不靠模型自己"判断安全"——模型会被骗。
</div>

<h2>第一层:危险命令审批</h2>
<p>agent 要跑的每条命令,先过一个"危险模式"黑名单:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/approval.py</span><span class="ln">262-275 / 657-668 · 简化</span></div>
  <pre>HARDLINE_PATTERNS = [                       <span class="cm"># 红线:连 yolo 也不放行</span>
    (<span class="st">r"\brm\s+(-[^\s]*\s+)*(/|/home|/root|/etc|/usr)"</span>, <span class="st">"recursive delete of system directory"</span>),
    (<span class="st">r"\bmkfs(\.[a-z0-9]+)?\b"</span>, <span class="st">"format filesystem (mkfs)"</span>),
    (<span class="st">r"\bdd\b[^\n]*\bof=/dev/(sd|nvme|hd)"</span>, <span class="st">"dd to raw block device"</span>),
    (<span class="st">r":\(\)\s*\{\s*:\s*\|\s*:\s*&amp;\s*\}\s*;\s*:"</span>, <span class="st">"fork bomb"</span>),
]

<span class="kw">def</span> <span class="fn">detect_dangerous_command</span>(command):
    <span class="cm">&quot;&quot;&quot;Returns (is_dangerous, pattern_key, description).&quot;&quot;&quot;</span>
    <span class="kw">for</span> pattern_re, description <span class="kw">in</span> DANGEROUS_PATTERNS_COMPILED:
        <span class="kw">if</span> pattern_re.search(command_lower):
            <span class="kw">return</span> (<span class="kw">True</span>, description, description)
    <span class="kw">return</span> (<span class="kw">False</span>, <span class="kw">None</span>, <span class="kw">None</span>)</pre>
</div>
<p><span class="mono">approval.py</span> 是危险命令系统的<strong>单一真相源</strong>:12 条 <strong>HARDLINE</strong>(删根、格式化、写裸盘、fork 炸弹……)+ 47 条 <strong>DANGEROUS</strong>。命中就要用户<strong>审批</strong>。区别在:<span class="mono">/yolo</span> 模式能放行 DANGEROUS,但 <strong>HARDLINE 红线永远拦</strong>——给"省心"留了口子,却把"会毁系统"的死死焊住。还有一层<strong>智能审批</strong>:用辅助 LLM 自动放行低风险命令,减少打扰。</p>

<h2>第二层:子代理最小权限</h2>
<p>派给子代理干活时,先把一批高危工具从它手里<strong>拿掉</strong>:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/delegate_tool.py</span><span class="ln">45-53 · 逐字</span></div>
  <pre>DELEGATE_BLOCKED_TOOLS = frozenset([
    <span class="st">"delegate_task"</span>,  <span class="cm"># no recursive delegation</span>
    <span class="st">"clarify"</span>,        <span class="cm"># no user interaction</span>
    <span class="st">"memory"</span>,         <span class="cm"># no writes to shared MEMORY.md</span>
    <span class="st">"send_message"</span>,   <span class="cm"># no cross-platform side effects</span>
    <span class="st">"execute_code"</span>,   <span class="cm"># children should reason step-by-step, not write scripts</span>
])</pre>
</div>
<p>每个被剥离的工具都有<strong>明确理由</strong>:不让子代理<strong>递归派生</strong>(防爆炸)、不让它<strong>打扰用户</strong>、不让它<strong>写共享记忆</strong>(防污染)、不让它<strong>跨平台发消息</strong>(防外部副作用)。这就是<strong>最小权限</strong>:子代理只拿完成任务<strong>够用</strong>的工具,把爆炸半径关进边缘(第 13 章委派隔离的安全面)。</p>

<h2>第三层:供应链锁定</h2>
<p>最隐蔽的攻击来自依赖。Hermes 把每个依赖<strong>钉死版本</strong>:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">pyproject.toml</span><span class="ln">45-52 · 节选</span></div>
  <pre><span class="cm"># exact pins 收窄下一次供应链攻击的爆炸半径</span>
dependencies = [
    <span class="st">"openai==2.24.0"</span>,
    <span class="st">"httpx[socks]==0.28.1"</span>,
    <span class="st">"certifi==2026.5.20"</span>,
    <span class="st">"pyyaml==6.0.3"</span>,
    <span class="cm"># 策略:PyPI &gt;=floor,&lt;next_major;Git URL 用 commit SHA;Actions 用 SHA</span>
]</pre>
</div>
<p>这条纪律是 <span class="mono">litellm</span> 被投毒(供应链攻击)后立的:每个 PyPI 包都有<strong>上界</strong>(<span class="mono">&gt;=floor,&lt;next_major</span>),Git 依赖钉 <strong>commit SHA</strong>,连 GitHub Actions 都钉 SHA;而核心运行时包(如上面的 openai/httpx)在 Mini Shai-Hulud worm 击中 mistralai 后,更被<strong>额外收紧为 exact</strong>(<span class="mono">==</span>)。一个被攻陷的上游包,没法靠"自动升级到恶意新版本"溜进来。<strong>不信任任何会自动变的东西</strong>——这和"不信任模型会自己判断安全"是同一种偏执。</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">agent 要跑命令 → <span class="mono">detect_dangerous_command</span> 匹配 HARDLINE/DANGEROUS</span></div>
  <div class="step"><span class="num">2</span><span class="sc">命中 → 要用户审批;HARDLINE 连 <span class="mono">/yolo</span> 都拦,DANGEROUS 可被 yolo 放行</span></div>
  <div class="step"><span class="num">3</span><span class="sc">派子代理 → 先剥离 <span class="mono">DELEGATE_BLOCKED_TOOLS</span>(最小权限)</span></div>
  <div class="step"><span class="num">4</span><span class="sc">控制命令(<span class="mono">/stop</span>/<span class="mono">/approve</span>)在网关就和数据流分离(防注入,第 18 章)</span></div>
  <div class="step"><span class="num">5</span><span class="sc">依赖全钉死版本(<span class="mono">==</span>/SHA),防供应链投毒</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各层安全如何咬合成「纵深防御」</div>
  <div class="collab-sub">① 组件清单(★本章核心,其余跨章节配合)</div>
  本章核心:<strong>detect_dangerous_command</strong>(危险命令审批)、<strong>DELEGATE_BLOCKED_TOOLS</strong>(子代理最小权限)、<strong>依赖 pin</strong>(供应链锁定)。跨章节配合:<strong>注入隔离</strong>靠网关两道守卫把控制命令从数据流拎出(第 18 章,D·指令=数据);子代理在<strong>独立 context + terminal</strong> 里跑(第 13 章),最小权限叠加隔离;<strong>profile 隔离</strong>防跨实例数据污染(第 20 章);<strong>Curator</strong> 只动 <span class="mono">created_by:agent</span> 的技能、绝不碰用户/官方技能(第 10 章,防技能中毒);审批 <span class="mono">/approve</span> 经网关旁路送达(第 18 章)。
  <div class="collab-sub">② 数据流时序</div>
  命令 → <span class="mono">detect_dangerous_command</span> → 危险则审批(HARDLINE 锁死);派子代理 → 剥离 <span class="mono">DELEGATE_BLOCKED_TOOLS</span> + 独立 context(第 13 章);消息进来 → 网关守卫把控制命令从数据分离(第 18 章);依赖 → 全程 pin 死。
  <div class="collab-sub">③ 关键点</div>
  <strong>纵深防御</strong>:每层独立,单层失守有下一层。核心威胁是<strong>注入</strong>——模型分不清"这是恶意数据还是给我的指令",所以安全<strong>绝不靠模型自己判断</strong>:危险命令用<strong>正则黑名单</strong>拦、控制命令在<strong>网关</strong>分离、权限用<strong>代码</strong>剥离、依赖用<strong>版本</strong>钉死。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线:<strong>纵深防御——agent 有真实权限,每层独立安全,绝不靠模型自己判断</strong>。它主要治两条 LLM 固有约束:
  <p style="margin:.5rem 0 0"><span class="badge constraint">D·指令=数据</span>——对模型而言,system prompt、用户消息、工具返回、网页内容<strong>都是 token,没有可信边界</strong>。一段恶意网页/文件可以伪装成"系统指令"<strong>注入</strong>。对策是<strong>不让模型当裁判</strong>:控制命令在网关用 <span class="mono">get_command()</span> 显式解析、走旁路通道(第 18 章);危险命令用<strong>正则黑名单</strong>而非"问模型这条命令危不危险"。把信任边界<strong>挪到代码层</strong>。</p>
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·运维</span>——安全是<strong>运维责任</strong>,不是一次性功能:审批系统、最小权限、供应链 pin、profile 隔离都是<strong>持续维护的基础设施</strong>。供应链投毒推动全仓依赖 pin(<span class="mono">litellm</span> 立上界政策、Mini Shai-Hulud worm 后核心包收紧为 <span class="mono">==</span>),HARDLINE 红线则借鉴 Mercury Agent 的硬化黑名单——安全纪律随真实威胁迭代。</p>
  <p style="margin:.5rem 0 0">反模式:<strong>信任模型自己判断安全</strong>("这条命令看起来没问题就跑")——模型会被注入、会幻觉、会被诱导。Hermes 把安全决策<strong>钉在确定性的代码</strong>(正则、frozenset、版本号)上,而非概率性的模型判断上。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>纵深防御</strong>:多层独立安全(审批 + 最小权限 + 注入隔离 + 供应链锁定),单层失守有下一层。</li>
    <li><strong>危险命令审批</strong>:<span class="mono">detect_dangerous_command</span> 用正则黑名单(12 HARDLINE + 47 DANGEROUS);HARDLINE 红线连 <span class="mono">/yolo</span> 都拦。</li>
    <li><strong>子代理最小权限</strong>:<span class="mono">DELEGATE_BLOCKED_TOOLS</span> 剥离递归派生/打扰/写记忆/跨平台/写脚本,把爆炸半径关进边缘(第 13 章)。</li>
    <li><strong>注入隔离(★)</strong>:控制命令在网关用 <span class="mono">get_command()</span> 显式解析、走旁路(第 18 章),不让模型当裁判(D·指令=数据)。</li>
    <li><strong>供应链锁定</strong>:依赖全 pin(<span class="mono">==</span>/上界/commit SHA),不信任任何会自动变的东西(<span class="mono">litellm</span> 教训)。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">Hermes has <strong>real privileges</strong>: it runs terminal commands, opens browsers, reads/writes files, connects to your messaging platforms. That means the threats are real too — malicious input wants to <strong>inject</strong> instructions, a poisoned skill wants to <strong>contaminate</strong>, a single <span class="mono">rm -rf /</span> wants to <strong>destroy the system</strong>. This chapter is a cross-cutting deep-dive: how Hermes uses <strong>defense in depth</strong> to block these threats layer by layer.</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · a bank vault's layered security</div>
  No single lock is absolute, so a bank <strong>layers its defenses</strong>: keycard access (command approval), guards who recognize blacklisted faces (dangerous-pattern detection), tellers with tiered permissions (subagent least-privilege), vendor background checks (dependency pinning). <strong>One layer falls, the next catches it.</strong> The key: don't count on "trusting one smart insider" — because that insider (the model) can be <strong>fooled</strong> by a single sentence (injection).
</div>

<div class="card macro">
  <div class="tag">🌍 Macro · Defense in Depth</div>
  The more capable the agent, the bigger the blast radius, so security is <strong>multiple independent layers</strong>: ① dangerous commands need <strong>approval</strong> (hardline patterns aren't even cleared by yolo); ② subagents are <strong>stripped</strong> of high-risk tools (least privilege); ③ control commands are <strong>separated</strong> from the data stream at the gateway (anti-injection, ch.18); ④ dependencies are all <strong>version-pinned</strong> (anti-supply-chain). Never rely on the model to "judge safety" itself — it can be fooled.
</div>

<h2>Layer one: dangerous-command approval</h2>
<p>Every command the agent wants to run first passes a "dangerous pattern" blacklist:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/approval.py</span><span class="ln">262-275 / 657-668 · simplified</span></div>
  <pre>HARDLINE_PATTERNS = [                       <span class="cm"># red lines: not even yolo clears these</span>
    (<span class="st">r"\brm\s+(-[^\s]*\s+)*(/|/home|/root|/etc|/usr)"</span>, <span class="st">"recursive delete of system directory"</span>),
    (<span class="st">r"\bmkfs(\.[a-z0-9]+)?\b"</span>, <span class="st">"format filesystem (mkfs)"</span>),
    (<span class="st">r"\bdd\b[^\n]*\bof=/dev/(sd|nvme|hd)"</span>, <span class="st">"dd to raw block device"</span>),
    (<span class="st">r":\(\)\s*\{\s*:\s*\|\s*:\s*&amp;\s*\}\s*;\s*:"</span>, <span class="st">"fork bomb"</span>),
]

<span class="kw">def</span> <span class="fn">detect_dangerous_command</span>(command):
    <span class="cm">&quot;&quot;&quot;Returns (is_dangerous, pattern_key, description).&quot;&quot;&quot;</span>
    <span class="kw">for</span> pattern_re, description <span class="kw">in</span> DANGEROUS_PATTERNS_COMPILED:
        <span class="kw">if</span> pattern_re.search(command_lower):
            <span class="kw">return</span> (<span class="kw">True</span>, description, description)
    <span class="kw">return</span> (<span class="kw">False</span>, <span class="kw">None</span>, <span class="kw">None</span>)</pre>
</div>
<p><span class="mono">approval.py</span> is the <strong>single source of truth</strong> for the dangerous-command system: 12 <strong>HARDLINE</strong> patterns (delete root, format, raw-disk write, fork bomb…) + 47 <strong>DANGEROUS</strong>. A match requires user <strong>approval</strong>. The distinction: <span class="mono">/yolo</span> mode can clear DANGEROUS, but <strong>HARDLINE red lines always block</strong> — leaving a "convenience" door open while welding shut the "will destroy the system" ones. There's also a <strong>smart-approval</strong> layer: an auxiliary LLM auto-clears low-risk commands to cut the nagging.</p>

<h2>Layer two: subagent least-privilege</h2>
<p>When delegating to a subagent, a batch of high-risk tools is <strong>taken away</strong> first:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">tools/delegate_tool.py</span><span class="ln">45-53 · verbatim</span></div>
  <pre>DELEGATE_BLOCKED_TOOLS = frozenset([
    <span class="st">"delegate_task"</span>,  <span class="cm"># no recursive delegation</span>
    <span class="st">"clarify"</span>,        <span class="cm"># no user interaction</span>
    <span class="st">"memory"</span>,         <span class="cm"># no writes to shared MEMORY.md</span>
    <span class="st">"send_message"</span>,   <span class="cm"># no cross-platform side effects</span>
    <span class="st">"execute_code"</span>,   <span class="cm"># children should reason step-by-step, not write scripts</span>
])</pre>
</div>
<p>Each stripped tool has an <strong>explicit reason</strong>: no <strong>recursive spawning</strong> (prevents explosion), no <strong>bothering the user</strong>, no <strong>writing shared memory</strong> (prevents pollution), no <strong>cross-platform messaging</strong> (prevents external side effects). This is <strong>least privilege</strong>: a subagent gets only the tools <strong>sufficient</strong> for its task, caging the blast radius at the edge (the security face of ch.13's delegation isolation).</p>

<h2>Layer three: supply-chain pinning</h2>
<p>The stealthiest attack comes through dependencies. Hermes <strong>version-pins</strong> every one:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">pyproject.toml</span><span class="ln">45-52 · excerpt</span></div>
  <pre><span class="cm"># exact pins shrink the blast radius for the next supply-chain attack</span>
dependencies = [
    <span class="st">"openai==2.24.0"</span>,
    <span class="st">"httpx[socks]==0.28.1"</span>,
    <span class="st">"certifi==2026.5.20"</span>,
    <span class="st">"pyyaml==6.0.3"</span>,
    <span class="cm"># policy: PyPI &gt;=floor,&lt;next_major; Git URL commit SHA; Actions SHA</span>
]</pre>
</div>
<p>This discipline was set after <span class="mono">litellm</span> was poisoned (a supply-chain attack): every PyPI package has an <strong>upper bound</strong> (<span class="mono">&gt;=floor,&lt;next_major</span>), Git deps pin a <strong>commit SHA</strong>, even GitHub Actions pin a SHA; and core runtime packages (like the openai/httpx above) were <strong>further tightened to exact</strong> (<span class="mono">==</span>) after the Mini Shai-Hulud worm hit mistralai. A compromised upstream package can't sneak in by "auto-upgrading to a malicious new version." <strong>Trust nothing that changes automatically</strong> — the same paranoia as "don't trust the model to judge safety itself."</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">agent wants to run a command → <span class="mono">detect_dangerous_command</span> matches HARDLINE/DANGEROUS</span></div>
  <div class="step"><span class="num">2</span><span class="sc">match → user approval required; HARDLINE blocks even <span class="mono">/yolo</span>, DANGEROUS can be cleared by yolo</span></div>
  <div class="step"><span class="num">3</span><span class="sc">delegating → strip <span class="mono">DELEGATE_BLOCKED_TOOLS</span> first (least privilege)</span></div>
  <div class="step"><span class="num">4</span><span class="sc">control commands (<span class="mono">/stop</span>/<span class="mono">/approve</span>) separated from the data stream at the gateway (anti-injection, ch.18)</span></div>
  <div class="step"><span class="num">5</span><span class="sc">all dependencies version-pinned (<span class="mono">==</span>/SHA), anti-supply-chain</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the security layers mesh into "defense in depth"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: <strong>detect_dangerous_command</strong> (dangerous-command approval), <strong>DELEGATE_BLOCKED_TOOLS</strong> (subagent least-privilege), <strong>dependency pinning</strong> (supply-chain lock). Cross-chapter teamwork: <strong>injection isolation</strong> rests on the gateway's two guards pulling control commands out of the data stream (ch.18, D·instr=data); subagents run in an <strong>isolated context + terminal</strong> (ch.13), least-privilege on top of isolation; <strong>profile isolation</strong> prevents cross-instance data contamination (ch.20); the <strong>Curator</strong> only touches <span class="mono">created_by:agent</span> skills, never user/official ones (ch.10, anti skill-poisoning); <span class="mono">/approve</span> reaches the runner via the gateway bypass (ch.18).
  <div class="collab-sub">② Data-flow timing</div>
  command → <span class="mono">detect_dangerous_command</span> → approve if dangerous (HARDLINE locked); delegate → strip <span class="mono">DELEGATE_BLOCKED_TOOLS</span> + isolated context (ch.13); message arrives → gateway guards split control commands from data (ch.18); dependencies → pinned throughout.
  <div class="collab-sub">③ The key point</div>
  <strong>Defense in depth</strong>: each layer independent, one falls the next catches. The core threat is <strong>injection</strong> — the model can't tell "is this malicious data or an instruction to me," so security <strong>never relies on the model's own judgment</strong>: dangerous commands blocked by a <strong>regex blacklist</strong>, control commands split at the <strong>gateway</strong>, privileges stripped in <strong>code</strong>, dependencies nailed by <strong>version</strong>.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>defense in depth — the agent has real privileges, each layer independently secure, never relying on the model's own judgment</strong>. It mainly treats two inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">D·instr=data</span> — to the model, the system prompt, user messages, tool returns, and web content are <strong>all tokens with no trusted boundary</strong>. A malicious web page/file can masquerade as a "system instruction" and <strong>inject</strong>. The countermeasure: <strong>don't let the model be the judge</strong>: control commands are explicitly parsed at the gateway via <span class="mono">get_command()</span> and routed on a bypass channel (ch.18); dangerous commands use a <strong>regex blacklist</strong>, not "ask the model whether this command is dangerous." Move the trust boundary <strong>into the code layer</strong>.</p>
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·ops</span> — security is an <strong>operational responsibility</strong>, not a one-off feature: the approval system, least privilege, supply-chain pins, and profile isolation are all <strong>continuously maintained infrastructure</strong>. Supply-chain poisonings drove repo-wide dependency pinning (<span class="mono">litellm</span> set the upper-bound policy; the Mini Shai-Hulud worm later tightened core packages to <span class="mono">==</span>), while the HARDLINE red lines borrow from Mercury Agent's hardened blocklist — the security discipline iterates with real threats.</p>
  <p style="margin:.5rem 0 0">The anti-pattern: <strong>trusting the model to judge safety</strong> ("this command looks fine, run it") — the model gets injected, hallucinates, gets lured. Hermes nails security decisions to <strong>deterministic code</strong> (regexes, frozensets, version numbers), not the model's probabilistic judgment.</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Defense in depth</strong>: multiple independent layers (approval + least privilege + injection isolation + supply-chain lock); one falls, the next catches.</li>
    <li><strong>Dangerous-command approval</strong>: <span class="mono">detect_dangerous_command</span> uses a regex blacklist (12 HARDLINE + 47 DANGEROUS); HARDLINE red lines block even <span class="mono">/yolo</span>.</li>
    <li><strong>Subagent least-privilege</strong>: <span class="mono">DELEGATE_BLOCKED_TOOLS</span> strips recursive-spawn/interaction/memory-write/cross-platform/script-write, caging the blast radius at the edge (ch.13).</li>
    <li><strong>Injection isolation (★)</strong>: control commands explicitly parsed at the gateway via <span class="mono">get_command()</span> on a bypass (ch.18), never letting the model judge (D·instr=data).</li>
    <li><strong>Supply-chain lock</strong>: all deps pinned (<span class="mono">==</span>/upper bound/commit SHA), trusting nothing that auto-changes (the <span class="mono">litellm</span> lesson).</li>
  </ul>
</div>
"""
}
