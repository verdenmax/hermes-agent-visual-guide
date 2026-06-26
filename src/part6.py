LESSON_21 = {
    "zh": r"""
<p class="lead">你让 Hermes「每天早 9 点把今天的会议汇总发我」。它得在后台<strong>定时</strong>醒来、跑完、投递——但这件事绝不能<strong>污染你正在进行的对话</strong>:不能把自动任务塞进聊天历史、不能把它记进你的「个人记忆」、更不能因为某个 job 跑飞了就卡死整个调度器。这就是 cron 的设计重心:<strong>后台自动化,但不破缓存、不污染</strong>。</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 公司的自动化助理</div>
  你雇了个助理(cron)做定时杂活:每天剪报、每周备份。他在<strong>独立的工位</strong>(独立会话)干活,干完把结果<strong>放你桌上</strong>(投递),但<strong>不会插进你正在开的会</strong>(不混进主对话),也<strong>不会把这些杂活写进你的人事档案</strong>(skip_memory)。万一他某个活卡住了,有个<strong>不活动闹钟</strong>(默认空转 10 分钟没动静就中断)把他叫停,不耽误下一件。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 调度 + 独立会话 + 安全阀</div>
  cron 由 <span class="mono">tick</span> 循环驱动(文件锁防重复),按 <span class="mono">parse_schedule</span> 解析的时刻扫到期任务。每个任务起一个<strong>独立的 cron 会话</strong>(<span class="mono">platform="cron"</span>、<span class="mono">skip_memory=True</span>),跑完把结果<strong>带框投递</strong>、<strong>不镜像进主对话</strong>。再加不活动超时(默认 600s)、半周期 catchup 窗口——安全地后台自动化。kanban 则是配套的多 agent 工作队列,workers 用零足迹工具集领活。
</div>

<h2>调度格式:四种写法</h2>
<p>agent 或用户都能排期,<span class="mono">parse_schedule</span> 把字符串解析成结构:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">cron/jobs.py</span><span class="ln">304-377 · 简化</span></div>
  <pre><span class="kw">def</span> <span class="fn">parse_schedule</span>(schedule):
    <span class="cm">&quot;&quot;&quot;Parse schedule string into structured format.&quot;&quot;&quot;</span>
    <span class="cm"># "30m"/"2h" → 一次性;"every 2h" → 周期;"0 9 * * *" → cron;ISO → 定时</span>
    <span class="kw">if</span> schedule.lower().startswith(<span class="st">"every "</span>):
        <span class="kw">return</span> {<span class="st">"kind"</span>: <span class="st">"interval"</span>, <span class="st">"minutes"</span>: parse_duration(...)}
    parts = schedule.split()
    <span class="kw">if</span> len(parts) &gt;= 5 <span class="kw">and</span> all(re.match(<span class="st">r"^[\d\*\-,/]+$"</span>, p) <span class="kw">for</span> p <span class="kw">in</span> parts[:5]):
        croniter(schedule)                  <span class="cm"># 校验 5 段 cron 表达式</span>
        <span class="kw">return</span> {<span class="st">"kind"</span>: <span class="st">"cron"</span>, <span class="st">"expr"</span>: schedule}
    <span class="kw">if</span> <span class="st">"T"</span> <span class="kw">in</span> schedule:                  <span class="cm"># ISO 时间戳 → 一次性</span>
        <span class="kw">return</span> {<span class="st">"kind"</span>: <span class="st">"once"</span>, <span class="st">"run_at"</span>: ...}</pre>
</div>
<p>四种写法覆盖几乎所有需求:<span class="mono">"30m"</span>(30 分钟后一次)、<span class="mono">"every 2h"</span>(每 2 小时)、<span class="mono">"0 9 * * *"</span>(标准 cron,每天 9 点)、<span class="mono">"2026-02-03T14:00"</span>(指定时刻一次)。解析成 <span class="mono">once</span>/<span class="mono">interval</span>/<span class="mono">cron</span> 三类,调度器据此算下次触发。</p>

<h2>独立会话:不污染主对话(★缓存线)</h2>
<p>关键一步——cron 任务<strong>不</strong>在你的主会话里跑,而是起一个独立的 agent:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">cron/scheduler.py</span><span class="ln">2050-2081 · 节选</span></div>
  <pre><span class="cm"># cron 起一个独立的 AIAgent 会话(不是主对话)</span>
agent = AIAgent(
    quiet_mode=<span class="kw">True</span>,
    load_soul_identity=<span class="kw">True</span>,            <span class="cm"># 仍读 SOUL.md 身份</span>
    skip_memory=<span class="kw">True</span>,                   <span class="cm"># Cron system prompts would corrupt user representations</span>
    platform=<span class="st">"cron"</span>,
    session_id=_cron_session_id,            <span class="cm"># 独立 session,不混进 gateway</span>
)</pre>
</div>
<p>两个设计守住缓存线:① <span class="mono">skip_memory=True</span>——cron 的系统提示若进了 memory,会<strong>污染对用户的画像</strong>(注释原话),所以 cron 默认不跑记忆;② <strong>独立 <span class="mono">session_id</span> + <span class="mono">platform="cron"</span></strong>——结果带 header/footer 框单独投递,<strong>不镜像进 gateway 主会话</strong>。于是主对话的严格<strong>角色交替</strong>(第 7 章)不被后台任务搅乱,被缓存的前缀(第 6 章)纹丝不动。后台自动化与主对话<strong>井水不犯河水</strong>。</p>

<h2>安全阀:catchup 与不活动超时</h2>
<p>定时系统怕两件事:错过了拼命补跑、跑飞了卡死。cron 各有一个阀:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">cron/jobs.py</span><span class="ln">475-490 · 简化</span></div>
  <pre><span class="kw">def</span> <span class="fn">_compute_grace_seconds</span>(schedule):
    <span class="cm">&quot;&quot;&quot;Half the schedule period, clamped between 120s and 2 hours.&quot;&quot;&quot;</span>
    MIN_GRACE, MAX_GRACE = 120, 7200        <span class="cm"># 2 小时</span>
    <span class="kw">if</span> schedule[<span class="st">"kind"</span>] == <span class="st">"interval"</span>:
        period = schedule[<span class="st">"minutes"</span>] * 60
        <span class="kw">return</span> max(MIN_GRACE, min(period // 2, MAX_GRACE))</pre>
</div>
<p><strong>catchup 窗口 = 半个周期</strong>(clamp 在 120 秒到 2 小时):错过得不久就补跑一次,错过太久就<strong>快进</strong>、不堆积补跑(免得开机时把积压的几十次一股脑全跑了)。另一头,cron 会话用<strong>不活动超时</strong>兜底:默认空转 <strong>600 秒(10 分钟)</strong>无动静(无工具调用、无流式 token)就 <span class="mono">agent.interrupt("Cron job timed out (inactivity)")</span> 中断(<span class="mono">HERMES_CRON_TIMEOUT</span> 可调;<strong>活跃干活时可跑数小时</strong>)。这样失控空转的 agent <strong>独占不了</strong>调度器,而正常长任务不会被误杀。再加 <span class="mono">.tick.lock</span> 文件锁,多个进程也不会重复 tick。</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc"><span class="mono">tick</span> 循环(<span class="mono">.tick.lock</span> 文件锁防重复)扫描到期任务</span></div>
  <div class="step"><span class="num">2</span><span class="sc">按 <span class="mono">parse_schedule</span> 的结构算下次触发;过了 catchup 窗口就快进</span></div>
  <div class="step"><span class="num">3</span><span class="sc">起独立 cron 会话:<span class="mono">platform="cron"</span> + <span class="mono">skip_memory=True</span> + 独立 <span class="mono">session_id</span></span></div>
  <div class="step"><span class="num">4</span><span class="sc">AIAgent 跑(不活动超时兜底,默认空转 600s 无动静才中断)</span></div>
  <div class="step"><span class="num">5</span><span class="sc">结果带 header/footer 框投递,<strong>不镜像进 gateway 主会话</strong></span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「不破缓存的后台自动化」</div>
  <div class="collab-sub">① 组件清单(★本章核心,其余跨章节配合)</div>
  本章核心:<strong>parse_schedule</strong>(调度格式)、<strong>tick</strong>(循环+文件锁)、<strong>cron 独立会话</strong>(skip_memory)、<strong>_compute_grace_seconds</strong>(catchup)。跨章节配合:cron 起的是一个 <strong>AIAgent 核心循环</strong>(第 7 章),只是 <span class="mono">skip_memory</span> 让<strong>记忆</strong>(第 11 章)不跑;独立会话不镜像进主对话=维持角色交替<strong>不破缓存</strong>(第 6 章);<span class="mono">cronjob</span> 与 <span class="mono">kanban</span> 是<strong>工具</strong>(第 8 章),让 agent 自己排期、领多 agent 队列的活;不活动超时的中断与委派的<strong>中断级联</strong>(第 13 章)同源。
  <div class="collab-sub">② 数据流时序</div>
  <span class="mono">tick</span>(<span class="mono">.tick.lock</span>) → 到期任务 → catchup 判定(<span class="mono">grace=period//2</span>) → 独立 cron 会话(<span class="mono">skip_memory</span>/<span class="mono">platform=cron</span>) → AIAgent 跑(不活动超时 600s) → header/footer 框投递(不进主会话)。
  <div class="collab-sub">③ 关键点</div>
  后台自动化<strong>绝不污染主对话</strong>:cron 投递不镜像进 gateway session(角色交替不变)、<span class="mono">skip_memory</span>(不污染用户画像)、独立 <span class="mono">session_id</span>。文件锁防重复 tick;半周期 catchup 防积压补跑;不活动超时(默认 600s)防失控空转独占。kanban 则把「多 agent 协作」也收进零足迹工具集。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线:<strong>独立会话 + skip_memory + 不镜像主对话 = 后台自动化既不破缓存、也不污染</strong>。它主要治两条 LLM 固有约束:
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·运维</span>——定时任务、批量、多 agent 队列是真实运维刚需,但要<strong>安全</strong>:不活动超时(默认 600s,可调)防失控空转 agent 独占调度器、<span class="mono">.tick.lock</span> 防多进程重复 tick、半周期 catchup 防积压补跑雪崩。把「自动化」做成可控的基础设施。</p>
  <p style="margin:.5rem 0 0"><span class="badge constraint">B·无状态</span>——cron 会话是<strong>独立</strong>的,不依赖、也不污染主会话的状态盘。它<strong>不镜像进 gateway session</strong>,所以主对话的角色交替/缓存前缀完全不受后台任务影响——这正是「缓存神圣」在自动化层的落地。</p>
  <p style="margin:.5rem 0 0">反模式:把 cron 结果<strong>直接灌进主会话历史</strong>——会破坏严格角色交替、击穿缓存前缀,还会让自动任务<strong>污染用户记忆画像</strong>。Hermes 用「独立会话 + skip_memory + 带框投递」从根上避开。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>四种调度</strong>:<span class="mono">parse_schedule</span> 认 duration(<span class="mono">30m</span>)、every(<span class="mono">every 2h</span>)、cron(<span class="mono">0 9 * * *</span>)、ISO 时间戳,归为 once/interval/cron。</li>
    <li><strong>独立会话(★缓存线)</strong>:cron 任务起独立 <span class="mono">session_id</span> + <span class="mono">platform="cron"</span>,结果带框投递、<strong>不镜像进主对话</strong>,角色交替(第 7 章)/缓存(第 6 章)不受扰。</li>
    <li><strong>skip_memory</strong>:cron 默认不跑记忆,免得自动任务<strong>污染用户画像</strong>(第 11 章)。</li>
    <li><strong>安全阀</strong>:不活动超时(默认 600s、可调,活跃时可跑数小时)防失控空转;<span class="mono">.tick.lock</span> 防重复 tick;半周期 catchup(120s–2h)防积压补跑。</li>
    <li><strong>kanban</strong>:多 agent 工作队列,worker 用零足迹 <span class="mono">kanban_*</span> 工具集(第 8 章)领活、回报。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">You tell Hermes "every day at 9am, send me today's meeting digest." It must wake on a <strong>schedule</strong> in the background, run, and deliver — but this must never <strong>pollute the conversation you're having</strong>: don't stuff the automated task into chat history, don't write it into your "personal memory," and certainly don't let one runaway job freeze the whole scheduler. That's cron's design focus: <strong>background automation that breaks neither the cache nor anything else</strong>.</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · the office automation assistant</div>
  You hire an assistant (cron) for scheduled chores: a daily clipping, a weekly backup. They work at a <strong>separate desk</strong> (an isolated session), put results <strong>on your desk</strong> when done (delivery), but <strong>never barge into the meeting you're in</strong> (no mixing into the main conversation), and <strong>never write these chores into your HR file</strong> (skip_memory). If a chore hangs, an <strong>inactivity alarm</strong> (interrupts after ~10 min of no activity by default) stops them so the next one isn't delayed.
</div>

<div class="card macro">
  <div class="tag">🌍 Macro · scheduling + isolated session + safety valves</div>
  Cron is driven by a <span class="mono">tick</span> loop (a file lock prevents duplicates), scanning due jobs by the times <span class="mono">parse_schedule</span> resolves. Each job spins up an <strong>isolated cron session</strong> (<span class="mono">platform="cron"</span>, <span class="mono">skip_memory=True</span>), and when done <strong>delivers framed results</strong> that are <strong>not mirrored into the main conversation</strong>. Add an inactivity timeout (default 600s) and a half-period catchup window — safe background automation. Kanban is the companion multi-agent work queue, where workers claim tasks via a zero-footprint toolset.
</div>

<h2>Schedule formats: four ways</h2>
<p>Agents or users can both schedule; <span class="mono">parse_schedule</span> turns a string into structure:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">cron/jobs.py</span><span class="ln">304-377 · simplified</span></div>
  <pre><span class="kw">def</span> <span class="fn">parse_schedule</span>(schedule):
    <span class="cm">&quot;&quot;&quot;Parse schedule string into structured format.&quot;&quot;&quot;</span>
    <span class="cm"># "30m"/"2h" → once; "every 2h" → recurring; "0 9 * * *" → cron; ISO → at time</span>
    <span class="kw">if</span> schedule.lower().startswith(<span class="st">"every "</span>):
        <span class="kw">return</span> {<span class="st">"kind"</span>: <span class="st">"interval"</span>, <span class="st">"minutes"</span>: parse_duration(...)}
    parts = schedule.split()
    <span class="kw">if</span> len(parts) &gt;= 5 <span class="kw">and</span> all(re.match(<span class="st">r"^[\d\*\-,/]+$"</span>, p) <span class="kw">for</span> p <span class="kw">in</span> parts[:5]):
        croniter(schedule)                  <span class="cm"># validate the 5-field cron expr</span>
        <span class="kw">return</span> {<span class="st">"kind"</span>: <span class="st">"cron"</span>, <span class="st">"expr"</span>: schedule}
    <span class="kw">if</span> <span class="st">"T"</span> <span class="kw">in</span> schedule:                  <span class="cm"># ISO timestamp → once</span>
        <span class="kw">return</span> {<span class="st">"kind"</span>: <span class="st">"once"</span>, <span class="st">"run_at"</span>: ...}</pre>
</div>
<p>Four forms cover nearly every need: <span class="mono">"30m"</span> (once in 30 min), <span class="mono">"every 2h"</span> (every 2 hours), <span class="mono">"0 9 * * *"</span> (standard cron, daily 9am), <span class="mono">"2026-02-03T14:00"</span> (once at a timestamp). Parsed into <span class="mono">once</span>/<span class="mono">interval</span>/<span class="mono">cron</span>, from which the scheduler computes the next fire.</p>

<h2>Isolated session: don't pollute the main conversation (★ the cache line)</h2>
<p>The key step — a cron job does <strong>not</strong> run in your main session; it spins up a separate agent:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">cron/scheduler.py</span><span class="ln">2050-2081 · excerpt</span></div>
  <pre><span class="cm"># cron spins up an isolated AIAgent session (not the main conversation)</span>
agent = AIAgent(
    quiet_mode=<span class="kw">True</span>,
    load_soul_identity=<span class="kw">True</span>,            <span class="cm"># still reads SOUL.md identity</span>
    skip_memory=<span class="kw">True</span>,                   <span class="cm"># Cron system prompts would corrupt user representations</span>
    platform=<span class="st">"cron"</span>,
    session_id=_cron_session_id,            <span class="cm"># isolated session, not mixed into gateway</span>
)</pre>
</div>
<p>Two designs guard the cache line: ① <span class="mono">skip_memory=True</span> — if cron's system prompts entered memory they'd <strong>corrupt the user representation</strong> (the comment's own words), so cron runs no memory by default; ② <strong>an isolated <span class="mono">session_id</span> + <span class="mono">platform="cron"</span></strong> — results are delivered framed, <strong>not mirrored into the gateway main session</strong>. So the main conversation's strict <strong>role alternation</strong> (ch.7) isn't disturbed by background jobs, and the cached prefix (ch.6) stays untouched. Background automation and the main conversation <strong>never cross streams</strong>.</p>

<h2>Safety valves: catchup and the inactivity timeout</h2>
<p>Schedulers fear two things: frantically catching up after a miss, and freezing on a runaway. Cron has a valve for each:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">cron/jobs.py</span><span class="ln">475-490 · simplified</span></div>
  <pre><span class="kw">def</span> <span class="fn">_compute_grace_seconds</span>(schedule):
    <span class="cm">&quot;&quot;&quot;Half the schedule period, clamped between 120s and 2 hours.&quot;&quot;&quot;</span>
    MIN_GRACE, MAX_GRACE = 120, 7200        <span class="cm"># 2 hours</span>
    <span class="kw">if</span> schedule[<span class="st">"kind"</span>] == <span class="st">"interval"</span>:
        period = schedule[<span class="st">"minutes"</span>] * 60
        <span class="kw">return</span> max(MIN_GRACE, min(period // 2, MAX_GRACE))</pre>
</div>
<p><strong>The catchup window = half the period</strong> (clamped 120s to 2h): miss it by a little and it runs once to catch up; miss it by a lot and it <strong>fast-forwards</strong> instead of piling up catch-up runs (so booting up won't fire dozens of backlogged runs at once). On the other end, a cron session is backstopped by an <strong>inactivity timeout</strong>: by default, after <strong>600 seconds (10 min)</strong> of no activity (no tool call, no stream token) it fires <span class="mono">agent.interrupt("Cron job timed out (inactivity)")</span> (tunable via <span class="mono">HERMES_CRON_TIMEOUT</span>; <strong>an actively-working job can run for hours</strong>). So a runaway idle agent <strong>can't monopolize</strong> the scheduler, while a legitimate long job isn't killed. Plus a <span class="mono">.tick.lock</span> file lock means multiple processes won't double-tick.</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc"><span class="mono">tick</span> loop (<span class="mono">.tick.lock</span> file lock prevents duplicates) scans due jobs</span></div>
  <div class="step"><span class="num">2</span><span class="sc">compute next fire from the <span class="mono">parse_schedule</span> structure; past the catchup window → fast-forward</span></div>
  <div class="step"><span class="num">3</span><span class="sc">spin up an isolated cron session: <span class="mono">platform="cron"</span> + <span class="mono">skip_memory=True</span> + isolated <span class="mono">session_id</span></span></div>
  <div class="step"><span class="num">4</span><span class="sc">AIAgent runs (inactivity-timeout backstop, kills only after ~600s idle by default)</span></div>
  <div class="step"><span class="num">5</span><span class="sc">framed result delivered, <strong>not mirrored into the gateway main session</strong></span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "cache-safe background automation"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: <strong>parse_schedule</strong> (schedule formats), <strong>tick</strong> (loop + file lock), <strong>the isolated cron session</strong> (skip_memory), <strong>_compute_grace_seconds</strong> (catchup). Cross-chapter teamwork: cron spins up an <strong>AIAgent core loop</strong> (ch.7), just with <span class="mono">skip_memory</span> so <strong>memory</strong> (ch.11) doesn't run; the isolated session isn't mirrored into the main conversation, preserving role alternation = <strong>cache intact</strong> (ch.6); <span class="mono">cronjob</span> and <span class="mono">kanban</span> are <strong>tools</strong> (ch.8) so the agent schedules its own jobs and claims work off a multi-agent queue; the inactivity-timeout interrupt shares roots with delegation's <strong>interrupt cascade</strong> (ch.13).
  <div class="collab-sub">② Data-flow timing</div>
  <span class="mono">tick</span> (<span class="mono">.tick.lock</span>) → due jobs → catchup check (<span class="mono">grace=period//2</span>) → isolated cron session (<span class="mono">skip_memory</span>/<span class="mono">platform=cron</span>) → AIAgent runs (inactivity timeout, 600s) → framed delivery (not into the main session).
  <div class="collab-sub">③ The key point</div>
  Background automation <strong>never pollutes the main conversation</strong>: cron delivery isn't mirrored into the gateway session (role alternation unchanged), <span class="mono">skip_memory</span> (no user-representation pollution), an isolated <span class="mono">session_id</span>. The file lock prevents duplicate ticks; half-period catchup prevents backlog floods; the inactivity timeout prevents runaway idle monopoly. Kanban then folds "multi-agent collaboration" into a zero-footprint toolset too.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>isolated session + skip_memory + not mirrored into the main conversation = background automation that breaks neither cache nor anything else</strong>. It mainly treats two inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·ops</span> — scheduled jobs, batches, and multi-agent queues are real operational needs, but they must be <strong>safe</strong>: an inactivity timeout (default 600s, tunable) stops a runaway idle agent from monopolizing the scheduler, <span class="mono">.tick.lock</span> stops multi-process double-ticks, half-period catchup stops backlog-flood avalanches. Automation built as controllable infrastructure.</p>
  <p style="margin:.5rem 0 0"><span class="badge constraint">B·statelessness</span> — a cron session is <strong>isolated</strong>; it neither depends on nor pollutes the main session's state store. It is <strong>not mirrored into the gateway session</strong>, so the main conversation's role alternation / cached prefix are wholly unaffected by background jobs — this is "caching is sacred" realized at the automation layer.</p>
  <p style="margin:.5rem 0 0">The anti-pattern: <strong>pouring cron results straight into the main session history</strong> — it breaks strict role alternation, shatters the cached prefix, and lets automated tasks <strong>pollute the user's memory representation</strong>. Hermes dodges all of it at the root with "isolated session + skip_memory + framed delivery."</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Four schedule formats</strong>: <span class="mono">parse_schedule</span> reads duration (<span class="mono">30m</span>), every (<span class="mono">every 2h</span>), cron (<span class="mono">0 9 * * *</span>), ISO timestamp, grouped into once/interval/cron.</li>
    <li><strong>Isolated session (★ cache line)</strong>: a cron job spins up an isolated <span class="mono">session_id</span> + <span class="mono">platform="cron"</span>, delivers framed, <strong>not mirrored into the main conversation</strong>, so role alternation (ch.7) / caching (ch.6) are undisturbed.</li>
    <li><strong>skip_memory</strong>: cron runs no memory by default, lest automated tasks <strong>pollute the user representation</strong> (ch.11).</li>
    <li><strong>Safety valves</strong>: an inactivity timeout (default 600s, tunable; active jobs can run for hours) prevents runaway idle monopoly; <span class="mono">.tick.lock</span> prevents duplicate ticks; half-period catchup (120s–2h) prevents backlog floods.</li>
    <li><strong>Kanban</strong>: a multi-agent work queue; workers claim and report via the zero-footprint <span class="mono">kanban_*</span> toolset (ch.8).</li>
  </ul>
</div>
"""
}


LESSON_22 = {
    "zh": r"""
<p class="lead">Hermes 不只是个产品,它是 Nous Research 的<strong>研究工具</strong>:要批量跑成千上万条 prompt、把每次对话的<strong>完整轨迹</strong>(含推理、工具调用)落盘成训练数据,还要在「模型每周都在变」的现实里写出<strong>不会天天挂掉</strong>的测试。这一章讲三件相关的事:批量、轨迹、评测哲学。</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 工厂的质检流水线</div>
  把一堆原料(prompt)送上<strong>多条并行产线</strong>(batch workers),每件产品记录<strong>完整工序</strong>(trajectory:每步推理 + 每次工具调用)。出厂前<strong>质检</strong>:不合格的(比如全程零推理)直接剔除,不混进成品库(训练集)。而质检标准看的是「<strong>是否符合规格</strong>」(不变量),不是「<strong>是否和上一批一模一样</strong>」(快照)——因为配方本来就会升级。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · 数据流水线 + 抗漂移测试</div>
  <strong>批量</strong>:多 worker 并行跑 AIAgent,每条 prompt 独立。<strong>轨迹</strong>:把对话转成 JSONL 训练样本,带 <span class="mono">conversations</span>/<span class="mono">tool_stats</span>/<span class="mono">metadata</span>,并<strong>过滤低质</strong>(零推理样本丢弃)。<strong>评测</strong>:测试锁<strong>行为不变量</strong>而非数据快照——模型目录、config 版本天天变,锁快照只会让 CI 天天红。
</div>

<h2>批量:并行 worker + 轨迹落盘</h2>
<p>批处理把 prompt 分批,每个 worker 跑完一条就质检、落盘:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">batch_runner.py</span><span class="ln">400-487 · 简化</span></div>
  <pre><span class="kw">def</span> <span class="fn">_process_batch_worker</span>(args):
    <span class="cm">&quot;&quot;&quot;Worker function to process a single batch of prompts.&quot;&quot;&quot;</span>
    batch_num, batch_data, output_dir, completed, config = args
    ...
    <span class="kw">if</span> result[<span class="st">"success"</span>] <span class="kw">and</span> result[<span class="st">"trajectory"</span>]:
        <span class="kw">if</span> <span class="kw">not</span> reasoning.get(<span class="st">"has_any_reasoning"</span>, <span class="kw">True</span>):
            <span class="kw">continue</span>                       <span class="cm"># 丢弃全程零推理的样本</span>
        trajectory_entry = {
            <span class="st">"conversations"</span>: result[<span class="st">"trajectory"</span>],
            <span class="st">"metadata"</span>: result[<span class="st">"metadata"</span>],
            <span class="st">"tool_stats"</span>: tool_stats,        <span class="cm"># {tool: {count,success,failure}}</span>
        }
        f.write(json.dumps(trajectory_entry, ensure_ascii=<span class="kw">False</span>) + <span class="st">"\n"</span>)  <span class="cm"># 追加 JSONL</span></pre>
</div>
<p>三个要点:① <strong>并行</strong>——多 worker 各跑各的 prompt,互不依赖(无状态,约束 B 又一次发力);② <strong>质量过滤</strong>——<span class="mono">has_any_reasoning</span> 为假就 <span class="mono">continue</span> 丢弃,训练集只收有推理的样本;③ <strong>JSONL 追加</strong>——每条样本一行,带 <span class="mono">tool_stats</span> 等元数据,是标准的 RL/SFT 训练格式。</p>

<h2>轨迹:一次对话变一条训练样本</h2>
<p>单次运行也能存轨迹,由一个开关控制:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">run_agent.py</span><span class="ln">1716-1729 · 节选</span></div>
  <pre><span class="kw">def</span> <span class="fn">_save_trajectory</span>(self, messages, user_query, completed):
    <span class="cm">&quot;&quot;&quot;Save conversation trajectory to JSONL file.&quot;&quot;&quot;</span>
    <span class="kw">if</span> <span class="kw">not</span> self.save_trajectories:    <span class="cm"># 开关:默认关</span>
        <span class="kw">return</span>
    trajectory = self._convert_to_trajectory_format(messages, user_query, completed)
    _save_trajectory_to_file(trajectory, self.model, completed)</pre>
</div>
<p><span class="mono">save_trajectories</span> 默认关(生产对话不留痕),研究时打开。<span class="mono">_convert_to_trajectory_format</span> 把内部的 <span class="mono">messages</span>(system/user/assistant/tool 四类角色 + reasoning)转成训练用的轨迹格式,落盘成 JSONL(成功样本进 <span class="mono">trajectory_samples.jsonl</span>、失败的进 <span class="mono">failed_trajectories.jsonl</span>;<span class="mono">model</span> 记进每条样本的元数据)。<strong>同一个 agent 核心,既服务真实对话,又顺手产出研究数据</strong>——这正是「研究工具」的一鱼两吃。</p>

<h2>评测:锁不变量,别锁快照</h2>
<p>研究项目最容易踩的测试坑——把「当前数据」写死进断言。模型每周都在变,这种测试天天挂:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">AGENTS.md · 测试规约(项目纪律)</span><span class="ln">Don't write change-detector tests</span></div>
  <pre><span class="cm"># ❌ change-detector:数据一变就挂(模型目录每次发布都变)</span>
<span class="kw">assert</span> <span class="st">"gemini-2.5-pro"</span> <span class="kw">in</span> _PROVIDER_MODELS[<span class="st">"gemini"</span>]
<span class="kw">assert</span> DEFAULT_CONFIG[<span class="st">"_config_version"</span>] == 21

<span class="cm"># ✅ 行为契约/不变量:锁「关系」,不锁「快照」</span>
<span class="kw">assert</span> <span class="st">"gemini"</span> <span class="kw">in</span> _PROVIDER_MODELS
<span class="kw">assert</span> len(_PROVIDER_MODELS[<span class="st">"gemini"</span>]) &gt;= 1
<span class="kw">assert</span> raw[<span class="st">"_config_version"</span>] == DEFAULT_CONFIG[<span class="st">"_config_version"</span>]
<span class="kw">for</span> m <span class="kw">in</span> _PROVIDER_MODELS[<span class="st">"huggingface"</span>]:
    <span class="kw">assert</span> m.lower() <span class="kw">in</span> DEFAULT_CONTEXT_LENGTHS_LOWER</pre>
</div>
<p>规则一句话:<strong>测试若读起来像「当前数据的快照」,删掉;若读起来像「两份数据必须如何关联」的契约,留下。</strong>「gemini 目录里必须有 gemini-2.5-pro」是快照(下个模型发布就错);「gemini 目录至少有一个模型」「每个模型都有对应的上下文长度」是<strong>不变量</strong>——数据怎么更新都不破。这让测试<strong>抗模型/数据漂移</strong>,routine 更新不再天天红 CI。</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">一批 prompt 切分,丢给多个 <span class="mono">_process_batch_worker</span> 并行</span></div>
  <div class="step"><span class="num">2</span><span class="sc">每个 worker 独立跑 AIAgent(第 7 章核心循环),产出 trajectory</span></div>
  <div class="step"><span class="num">3</span><span class="sc">质量过滤:零推理样本 <span class="mono">continue</span> 丢弃</span></div>
  <div class="step"><span class="num">4</span><span class="sc"><span class="mono">trajectory_entry</span>(conversations + tool_stats + metadata)写 JSONL 一行</span></div>
  <div class="step"><span class="num">5</span><span class="sc">评测/回归用<strong>不变量</strong>断言(非快照),抗模型漂移</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「研究数据流水线 + 抗漂移评测」</div>
  <div class="collab-sub">① 组件清单(★本章核心,其余跨章节配合)</div>
  本章核心:<strong>_process_batch_worker</strong>(并行批量)、<strong>_save_trajectory</strong>(轨迹落盘)、<strong>trajectory_entry</strong>(JSONL schema)、<strong>不变量测试</strong>(评测哲学)。跨章节配合:批量跑的是 <strong>AIAgent 核心循环</strong>(第 7 章),轨迹里存的 reasoning 也来自那里;<span class="mono">tool_stats</span> 统计的是<strong>工具</strong>(第 8 章)调用;并行 worker 各自<strong>无状态独立</strong>(约束 B,第 2 章);轨迹按完成状态写 JSONL(<span class="mono">trajectory_samples.jsonl</span> / <span class="mono">failed_trajectories.jsonl</span>),批量则落进 <span class="mono">data/&lt;run&gt;/</span>。
  <div class="collab-sub">② 数据流时序</div>
  prompts 切批 → 多 <span class="mono">_process_batch_worker</span> 并行(各跑 AIAgent)→ 质量过滤(零推理丢弃)→ <span class="mono">trajectory_entry</span> 写 JSONL → 聚合 <span class="mono">tool_stats</span>;评测侧:不变量断言抗数据漂移。
  <div class="collab-sub">③ 关键点</div>
  研究数据流水线 = <strong>并行批量 + 完整轨迹 + 质量过滤</strong>;同一个 agent 核心既服务真实对话又产出训练数据。评测的工程纪律 = <strong>锁行为不变量、不锁数据快照</strong>,让「模型/数据天天变」不再天天破测试。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线:<strong>并行批量 + 完整轨迹 + 质量过滤 + 行为契约测试 = 可规模化的研究数据流水线 + 抗漂移评测</strong>。它主要治两条 LLM 固有约束:
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·运维</span>——研究要规模:成千上万条 prompt 得并行跑、轨迹得标准化落盘、CI 得在「模型每周变」下还能维护。批量 worker、JSONL 轨迹、不变量测试,把「做研究」做成可规模化、低维护的基础设施。</p>
  <p style="margin:.5rem 0 0"><span class="badge constraint">F·误差累积</span>——评测的本职就是<strong>量化 agent 在多轮自主里误差累积到什么程度</strong>;轨迹的质量门槛(必须有推理)<strong>剔除低质样本</strong>,免得垃圾数据喂进训练、把误差固化进下一代模型。不变量测试也防回归在迭代中悄悄累积。</p>
  <p style="margin:.5rem 0 0">反模式:写 <strong>change-detector 测试</strong>——把模型目录、config 版本号、枚举数量写死进断言。模型一发布、配置一升级,这些测试就<strong>集体变红</strong>,逼工程师花时间「修测试」而非修 bug。锁不变量,不锁快照。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>并行批量</strong>:<span class="mono">_process_batch_worker</span> 多 worker 各跑独立 prompt(无状态,约束 B),规模化生成数据。</li>
    <li><strong>完整轨迹</strong>:对话转 JSONL 训练样本,带 <span class="mono">conversations</span>/<span class="mono">tool_stats</span>/<span class="mono">metadata</span>;<span class="mono">save_trajectories</span> 开关默认关。</li>
    <li><strong>质量过滤</strong>:零推理样本 <span class="mono">continue</span> 丢弃,训练集只收有推理的高质数据。</li>
    <li><strong>一鱼两吃</strong>:同一个 AIAgent 核心,既服务真实对话、又顺手产出研究轨迹。</li>
    <li><strong>抗漂移评测</strong>:测试锁<strong>行为不变量</strong>(关系)而非<strong>数据快照</strong>(具体值);不写 change-detector,免得模型/config 一变就全红。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">Hermes isn't just a product — it's Nous Research's <strong>research tool</strong>: it must batch-run thousands of prompts, persist each conversation's <strong>full trajectory</strong> (reasoning, tool calls) as training data, and — in a world where models change weekly — write tests that <strong>don't break every day</strong>. This chapter covers three related things: batching, trajectories, and the testing philosophy.</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · the factory QC line</div>
  Feed raw material (prompts) onto <strong>parallel production lines</strong> (batch workers); each product records its <strong>full process</strong> (the trajectory: every reasoning step + every tool call). Before shipping, <strong>QC</strong>: rejects (e.g. zero reasoning throughout) are discarded, never entering the stock (the training set). And QC checks "<strong>does it meet spec</strong>" (invariants), not "<strong>is it identical to the last batch</strong>" (a snapshot) — because the recipe is meant to evolve.
</div>

<div class="card macro">
  <div class="tag">🌍 Macro · a data pipeline + drift-proof tests</div>
  <strong>Batch</strong>: multiple workers run AIAgent in parallel, each prompt independent. <strong>Trajectory</strong>: turn a conversation into a JSONL training sample carrying <span class="mono">conversations</span>/<span class="mono">tool_stats</span>/<span class="mono">metadata</span>, and <strong>filter low quality</strong> (drop zero-reasoning samples). <strong>Eval</strong>: tests lock <strong>behavioral invariants</strong>, not data snapshots — model catalogs and config versions change daily; lock a snapshot and CI goes red daily.
</div>

<h2>Batch: parallel workers + trajectory persistence</h2>
<p>Batching splits prompts; each worker QCs and persists as soon as one finishes:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">batch_runner.py</span><span class="ln">400-487 · simplified</span></div>
  <pre><span class="kw">def</span> <span class="fn">_process_batch_worker</span>(args):
    <span class="cm">&quot;&quot;&quot;Worker function to process a single batch of prompts.&quot;&quot;&quot;</span>
    batch_num, batch_data, output_dir, completed, config = args
    ...
    <span class="kw">if</span> result[<span class="st">"success"</span>] <span class="kw">and</span> result[<span class="st">"trajectory"</span>]:
        <span class="kw">if</span> <span class="kw">not</span> reasoning.get(<span class="st">"has_any_reasoning"</span>, <span class="kw">True</span>):
            <span class="kw">continue</span>                       <span class="cm"># discard samples with zero reasoning</span>
        trajectory_entry = {
            <span class="st">"conversations"</span>: result[<span class="st">"trajectory"</span>],
            <span class="st">"metadata"</span>: result[<span class="st">"metadata"</span>],
            <span class="st">"tool_stats"</span>: tool_stats,        <span class="cm"># {tool: {count,success,failure}}</span>
        }
        f.write(json.dumps(trajectory_entry, ensure_ascii=<span class="kw">False</span>) + <span class="st">"\n"</span>)  <span class="cm"># append JSONL</span></pre>
</div>
<p>Three points: ① <strong>parallel</strong> — workers each run their own prompt, independent (stateless, constraint B at work again); ② <strong>quality filter</strong> — <span class="mono">continue</span> to drop when <span class="mono">has_any_reasoning</span> is false, the training set takes only samples with reasoning; ③ <strong>JSONL append</strong> — one sample per line with metadata like <span class="mono">tool_stats</span>, the standard RL/SFT training format.</p>

<h2>Trajectory: one conversation becomes one training sample</h2>
<p>A single run can save a trajectory too, gated by one switch:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">run_agent.py</span><span class="ln">1716-1729 · excerpt</span></div>
  <pre><span class="kw">def</span> <span class="fn">_save_trajectory</span>(self, messages, user_query, completed):
    <span class="cm">&quot;&quot;&quot;Save conversation trajectory to JSONL file.&quot;&quot;&quot;</span>
    <span class="kw">if</span> <span class="kw">not</span> self.save_trajectories:    <span class="cm"># switch: off by default</span>
        <span class="kw">return</span>
    trajectory = self._convert_to_trajectory_format(messages, user_query, completed)
    _save_trajectory_to_file(trajectory, self.model, completed)</pre>
</div>
<p><span class="mono">save_trajectories</span> is off by default (production chats leave no trace), turned on for research. <span class="mono">_convert_to_trajectory_format</span> turns the internal <span class="mono">messages</span> (system/user/assistant/tool roles + reasoning) into the training trajectory format, written to JSONL (successful samples into <span class="mono">trajectory_samples.jsonl</span>, failed ones into <span class="mono">failed_trajectories.jsonl</span>; <span class="mono">model</span> recorded as per-sample metadata). <strong>The same agent core both serves real conversations and produces research data</strong> — the two-for-one of a "research tool."</p>

<h2>Eval: lock invariants, not snapshots</h2>
<p>The easiest testing trap in a research project — freezing "current data" into assertions. Models change weekly, so such tests break daily:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">AGENTS.md · testing rule (project discipline)</span><span class="ln">Don't write change-detector tests</span></div>
  <pre><span class="cm"># ❌ change-detector: breaks whenever data changes (catalog changes every release)</span>
<span class="kw">assert</span> <span class="st">"gemini-2.5-pro"</span> <span class="kw">in</span> _PROVIDER_MODELS[<span class="st">"gemini"</span>]
<span class="kw">assert</span> DEFAULT_CONFIG[<span class="st">"_config_version"</span>] == 21

<span class="cm"># ✅ behavior contract / invariant: lock the RELATION, not the snapshot</span>
<span class="kw">assert</span> <span class="st">"gemini"</span> <span class="kw">in</span> _PROVIDER_MODELS
<span class="kw">assert</span> len(_PROVIDER_MODELS[<span class="st">"gemini"</span>]) &gt;= 1
<span class="kw">assert</span> raw[<span class="st">"_config_version"</span>] == DEFAULT_CONFIG[<span class="st">"_config_version"</span>]
<span class="kw">for</span> m <span class="kw">in</span> _PROVIDER_MODELS[<span class="st">"huggingface"</span>]:
    <span class="kw">assert</span> m.lower() <span class="kw">in</span> DEFAULT_CONTEXT_LENGTHS_LOWER</pre>
</div>
<p>The rule in one line: <strong>if a test reads like a snapshot of current data, delete it; if it reads like a contract about how two pieces of data must relate, keep it.</strong> "the gemini catalog must contain gemini-2.5-pro" is a snapshot (wrong on the next release); "the gemini catalog has at least one model," "every model has a context length" are <strong>invariants</strong> — unbroken however the data updates. This makes tests <strong>drift-proof</strong> against model/data churn, so routine updates no longer redden CI daily.</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">a batch of prompts is split and handed to several <span class="mono">_process_batch_worker</span> in parallel</span></div>
  <div class="step"><span class="num">2</span><span class="sc">each worker runs AIAgent independently (ch.7 core loop), producing a trajectory</span></div>
  <div class="step"><span class="num">3</span><span class="sc">quality filter: zero-reasoning samples are <span class="mono">continue</span>-dropped</span></div>
  <div class="step"><span class="num">4</span><span class="sc"><span class="mono">trajectory_entry</span> (conversations + tool_stats + metadata) written as one JSONL line</span></div>
  <div class="step"><span class="num">5</span><span class="sc">eval/regression use <strong>invariant</strong> assertions (not snapshots), drift-proof</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "research data pipeline + drift-proof eval"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: <strong>_process_batch_worker</strong> (parallel batch), <strong>_save_trajectory</strong> (trajectory persistence), <strong>trajectory_entry</strong> (JSONL schema), <strong>invariant tests</strong> (eval philosophy). Cross-chapter teamwork: batching runs the <strong>AIAgent core loop</strong> (ch.7), and the reasoning stored in trajectories comes from there; <span class="mono">tool_stats</span> counts <strong>tool</strong> (ch.8) calls; parallel workers are each <strong>stateless and independent</strong> (constraint B, ch.2); trajectories are written by completion status (<span class="mono">trajectory_samples.jsonl</span> / <span class="mono">failed_trajectories.jsonl</span>), batches into <span class="mono">data/&lt;run&gt;/</span>.
  <div class="collab-sub">② Data-flow timing</div>
  prompts split into batches → several <span class="mono">_process_batch_worker</span> in parallel (each runs AIAgent) → quality filter (drop zero-reasoning) → <span class="mono">trajectory_entry</span> written to JSONL → aggregate <span class="mono">tool_stats</span>; on the eval side: invariant assertions resist data drift.
  <div class="collab-sub">③ The key point</div>
  The research data pipeline = <strong>parallel batch + full trajectory + quality filter</strong>; the same agent core both serves real conversations and produces training data. The engineering discipline of eval = <strong>lock behavioral invariants, not data snapshots</strong>, so "models/data change daily" no longer breaks tests daily.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>parallel batch + full trajectory + quality filter + behavior-contract tests = a scalable research data pipeline + drift-proof eval</strong>. It mainly treats two inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·ops</span> — research needs scale: thousands of prompts must run in parallel, trajectories must persist in a standard format, and CI must stay maintainable while "models change weekly." Batch workers, JSONL trajectories, and invariant tests make "doing research" a scalable, low-maintenance infrastructure.</p>
  <p style="margin:.5rem 0 0"><span class="badge constraint">F·error accumulation</span> — eval's very job is to <strong>quantify how much error accumulates over an agent's multi-turn autonomy</strong>; the trajectory's quality gate (reasoning required) <strong>discards low-quality samples</strong>, lest garbage data feed training and bake the error into the next model. Invariant tests also stop regressions from quietly accumulating across iterations.</p>
  <p style="margin:.5rem 0 0">The anti-pattern: writing <strong>change-detector tests</strong> — freezing model catalogs, config version numbers, enumeration counts into assertions. The moment a model ships or a config bumps, these tests <strong>all go red</strong>, forcing engineers to spend time "fixing the test" instead of fixing bugs. Lock invariants, not snapshots.</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Parallel batch</strong>: <span class="mono">_process_batch_worker</span> runs independent prompts across workers (stateless, constraint B), generating data at scale.</li>
    <li><strong>Full trajectory</strong>: a conversation becomes a JSONL training sample with <span class="mono">conversations</span>/<span class="mono">tool_stats</span>/<span class="mono">metadata</span>; <span class="mono">save_trajectories</span> is off by default.</li>
    <li><strong>Quality filter</strong>: zero-reasoning samples are <span class="mono">continue</span>-dropped; the training set takes only high-quality samples with reasoning.</li>
    <li><strong>Two-for-one</strong>: the same AIAgent core both serves real conversations and produces research trajectories.</li>
    <li><strong>Drift-proof eval</strong>: tests lock <strong>behavioral invariants</strong> (relations) not <strong>data snapshots</strong> (specific values); no change-detectors, so a model/config change doesn't redden everything.</li>
  </ul>
</div>
"""
}


LESSON_23 = {
    "zh": r"""
<p class="lead">前面 22 章,Hermes 的核心几乎没怎么"长大"——平台适配器、记忆后端、模型 provider、聊天技能,绝大多数能力都是从<strong>边缘</strong>挂上去的。这一章讲清那条贯穿全书的纪律:<strong>能力在边缘扩展,核心保持窄腰</strong>。机制有三:插件、技能、MCP。</p>

<div class="card analogy">
  <div class="tag">🔌 类比 · 瑞士军刀 vs 工具箱</div>
  核心只该放最常用的几把刀(核心工具);其余工具放<strong>工具箱</strong>(插件/技能/MCP),用时才取。要是把所有工具都焊死在军刀上,军刀会重得<strong>拿不动</strong>——因为每次出门(每次 API 调用)都得带上<strong>全部工具的说明书</strong>(工具 schema 全进 context)。工具越多,真正要用的那把越<strong>淹没在说明书堆里</strong>。
</div>

<div class="card macro">
  <div class="tag">🌍 宏观 · Footprint Ladder(足迹阶梯)</div>
  加新能力,按<strong>足迹从小到大</strong>选最高那一阶:① 扩展现有代码 → ② CLI 命令 + 技能 → ③ 服务门控工具(<span class="mono">check_fn</span>)→ ④ 插件 → ⑤ MCP server(进 catalog)→ ⑥ 新核心工具(<strong>最后手段</strong>)。越往下,永久占用的核心面越大。绝大多数能力都该停在前几阶。
</div>

<h2>插件:挂上核心,但不改核心</h2>
<p>插件通过一个 <span class="mono">register(ctx)</span> 把工具/命令/钩子挂进 Hermes,<strong>一行核心文件都不碰</strong>:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">hermes_cli/plugins.py</span><span class="ln">367-400 · 简化</span></div>
  <pre><span class="kw">class</span> <span class="fn">PluginContext</span>:
    <span class="kw">def</span> <span class="fn">register_tool</span>(self, name, toolset, schema, handler,
                      check_fn=<span class="kw">None</span>, override=<span class="kw">False</span>):
        <span class="cm">&quot;&quot;&quot;Register a tool in the global registry and track it as plugin-provided.&quot;&quot;&quot;</span>
        <span class="kw">from</span> tools.registry <span class="kw">import</span> registry
        registry.register(name=name, toolset=toolset, schema=schema,
                          handler=handler, check_fn=check_fn, override=override)</pre>
</div>
<p><span class="mono">register_tool</span> 只是<strong>委托</strong>给和内置工具<strong>同一个</strong> <span class="mono">tools.registry</span>(第 8 章)——插件工具和核心工具走完全相同的注册/分派/可用性检查路径。<span class="mono">check_fn</span> 让工具<strong>服务门控</strong>(没配凭据就不出现,零足迹);<span class="mono">override</span> 甚至能替换内置工具。铁律(Teknium):<strong>插件绝不能改核心文件</strong>(<span class="mono">run_agent.py</span>/<span class="mono">cli.py</span>…);要更多能力,就把通用插件面拓宽,而非在核心里硬编码插件逻辑。</p>

<p>为什么这条"插件绝不能改核心文件"要立成<strong>铁律</strong>,而不是"尽量别改"?因为核心一旦被某个插件的特例逻辑<strong>硬编码</strong>污染,它就被那个插件<strong>绑架</strong>了——下次重构 <span class="mono">run_agent.py</span> 得先担心会不会踩坏某个插件的隐式约定,核心的可演化性就此<strong>冻结</strong>。把规则反过来立:插件需要新能力,不是在核心开一个特例,而是<strong>拓宽通用插件面</strong>(加一个新 hook、加一个新 <span class="mono">ctx</span> 方法)。这样核心面对的永远是<strong>有限、通用</strong>的扩展点,而不是无穷无尽的插件特例。AGENTS.md 记着 PR #5295 删掉 95 行硬编码进 <span class="mono">main.py</span> 的某插件 argparse——就是这条铁律的执行记录。</p>

<p>注意 <span class="mono">register_tool</span> 委托的是和内置工具<strong>同一个</strong> <span class="mono">tools.registry</span>——这意味着插件工具不是"二等公民":它走相同的 schema 收集、相同的分派、相同的可用性检查。<span class="mono">check_fn</span> 是其中最关键的一环:工具<strong>只在前置条件满足时才出现</strong>(比如配了某个 API key),否则连 schema 都不进 context,真正做到<strong>零足迹</strong>。这正是 Footprint Ladder 第三阶"服务门控工具"的实现底座——核心工具集里那些 <span class="mono">ha_*</span>(Home Assistant)、<span class="mono">computer_use</span> 用的也是同一招:没配 token 就隐身。</p>

<p>插件能挂的不止工具和钩子,还有 <strong>CLI 子命令</strong>:<span class="mono">ctx.register_cli_command(...)</span> 会把插件的 argparse 子树在启动时<strong>接进</strong> <span class="mono">hermes</span>,于是 <span class="mono">hermes &lt;插件名&gt; &lt;子命令&gt;</span> 直接能用,<span class="mono">main.py</span> 一行不用改。这对应 Footprint Ladder 的<strong>第二阶</strong>"CLI 命令 + 技能":很多管理类能力(订阅、定时任务、服务配置)根本不需要做成模型工具——做成一条 shell 子命令,再写一个技能教 agent 去跑 <span class="mono">hermes &lt;子命令&gt;</span> 就够了,<strong>模型工具足迹为零</strong>。</p>

<h2>钩子:在核心生命周期的关节插手</h2>
<p>插件还能在 agent 运行的关键节点挂回调,而无需碰核心循环:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">hermes_cli/plugins.py</span><span class="ln">128-155 · 节选</span></div>
  <pre>VALID_HOOKS = {
    <span class="st">"pre_tool_call"</span>, <span class="st">"post_tool_call"</span>,
    <span class="st">"transform_llm_output"</span>,        <span class="cm"># 改写返回给用户的文本</span>
    <span class="st">"pre_llm_call"</span>, <span class="st">"post_llm_call"</span>,
    <span class="st">"on_session_start"</span>, <span class="st">"on_session_end"</span>,
    <span class="st">"subagent_start"</span>, <span class="st">"subagent_stop"</span>,
    <span class="st">"pre_gateway_dispatch"</span>,         <span class="cm"># 网关分发前(可 skip/rewrite)</span>
}</pre>
</div>
<p>这些是<strong>预留的扩展点</strong>:工具调用前后、LLM 调用前后、会话起止、子代理起止、网关分发前。插件挂一个回调就能<strong>观察或改写</strong>流程(比如 <span class="mono">transform_llm_output</span> 做人格化改写、<span class="mono">pre_gateway_dispatch</span> 拦截消息)。核心在固定位置触发这些钩子,但<strong>不知道也不关心</strong>具体挂了谁——又一次窄腰。</p>

<p>钩子听起来像"预留扩展点",但 Hermes 对<strong>投机性扩展点</strong>是明确拒绝的:加一个没有真实消费者的 hook 很容易,等插件依赖上了再想删却<strong>极难</strong>。所以 <span class="mono">VALID_HOOKS</span> 里每一个名字背后都该有真实用例——<span class="mono">transform_llm_output</span> 给人格化改写、<span class="mono">pre_gateway_dispatch</span> 在鉴权前拦截/改写消息、<span class="mono">subagent_start</span>/<span class="mono">subagent_stop</span> 围着子代理(第 13 章)的边界。这条纪律和"窄腰"是一体两面:核心暴露的扩展面也要<strong>尽量小且有人用</strong>,而不是无脑预留一堆没人接的回调。</p>

<p>插件挂载完全靠<strong>发现</strong>而非<strong>注册表登记</strong>:启动时扫四处——仓库自带的 <span class="mono">plugins/</span>、用户的 <span class="mono">~/.hermes/plugins/</span>、项目级 <span class="mono">./.hermes/plugins/</span>(需显式开启)、以及 pip 装的 entry-point 包。你想加一个插件,只要把目录丢进 <span class="mono">~/.hermes/plugins/</span>,<strong>核心文件一行都不用动</strong>,下次启动自动被发现并 <span class="mono">register(ctx)</span>。这就是"边缘扩展"在文件系统层面的样子:能力是<strong>挂上去的</strong>,不是<strong>编译进去的</strong>。</p>

<h2>技能:注入 user message,不破缓存(★缓存线)</h2>
<p>技能是另一条边缘扩展线,它的注入方式特意守住了缓存:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/skill_commands.py</span><span class="ln">245-274 · 节选</span></div>
  <pre><span class="kw">def</span> <span class="fn">_build_skill_message</span>(loaded_skill, skill_dir, activation_note, ...):
    <span class="cm">&quot;&quot;&quot;Format a loaded skill into a user/system message payload.&quot;&quot;&quot;</span>
    content = str(loaded_skill.get(<span class="st">"content"</span>) <span class="kw">or</span> <span class="st">""</span>)
    parts = [activation_note, <span class="st">""</span>, content.strip()]
    <span class="kw">if</span> skill_dir:
        parts.append(<span class="st">f"[Skill directory: {skill_dir}]"</span>)
    ...                                  <span class="cm"># 作为一条 user message 注入,不进 system prompt</span></pre>
</div>
<p>关键在<strong>注入位置</strong>:技能内容被拼成一条 <strong>user message</strong> 喂进对话,而<strong>不是</strong>塞进 system prompt。这是刻意的——system prompt 一改就<strong>击穿整会话的缓存前缀</strong>(第 6 章铁律);而追加一条 user message 是 append-only,缓存前缀<strong>纹丝不动</strong>。所以你 <span class="mono">/技能名</span> 临时调一个技能,不会让整段对话的缓存作废。边缘扩展,也要对缓存线负责。</p>

<p>再把"为什么走 user message"挖深一层。一段长对话每一轮都在<strong>复用</strong>一个缓存前缀(system prompt + 早期消息),命中缓存的那部分 token 又快又便宜。一旦你往 system prompt 里塞技能内容,这个前缀就<strong>变了</strong>,从那一轮起整个前缀<strong>全部 miss</strong>,得按全价重算——而且是<strong>每一轮</strong>都重算,不是一次性的。把技能拼成一条 <strong>user message</strong> 追加在<strong>末尾</strong>,前缀<strong>纹丝不动</strong>,缓存继续命中。这就是为什么"缓存神圣线"(第 6 章)能约束到边缘扩展:不是技能本身不重要,而是<strong>注入位置</strong>直接决定了用户的钱包。</p>

<p>技能本身也分层:<span class="mono">skills/</span> 是默认就加载的<strong>内置技能</strong>,<span class="mono">optional-skills/</span> 是随仓库发货但<strong>默认不激活</strong>、要 <span class="mono">hermes skills install</span> 显式装的重型/小众技能,再往外是用户自己的插件技能。这套分层和 Footprint Ladder 一个逻辑:<strong>越常用越靠核心,越小众越靠边缘</strong>。MCP 走的是另一条边缘路——外部工具进 <span class="mono">optional-mcps/</span> catalog,默认禁用,<span class="mono">hermes mcp install</span> 才连上,核心通过内置 MCP client 对接,<strong>零核心 schema 足迹</strong>。"进了 catalog = 经过审核",没有社区层、没有自动更新。</p>

<p>顺带说一句发现机制的微妙处:不是所有插件都走同一套发现。通用 <span class="mono">PluginManager</span> 管工具/钩子/CLI 命令;而<strong>模型 provider</strong> 插件走的是<strong>另一套惰性发现</strong>——第一次 <span class="mono">get_provider_profile()</span> 或 <span class="mono">list_providers()</span> 被调用时才扫描,而不是由 <span class="mono">PluginManager</span> 导入(否则会重复实例化 <span class="mono">ProviderProfile</span>)。同名的用户插件会<strong>覆盖</strong>内置 profile(last-writer-wins),第三方不打补丁就能换掉任何内置 provider。同一条"边缘扩展"哲学,落到不同子系统就长出不同的发现路径。</p>

<p>缓存这条线甚至约束到"装技能"本身:会改动 system-prompt 状态的 slash 命令(技能、工具、记忆)都是<strong>缓存感知</strong>的——默认<strong>延迟失效</strong>(改动下个会话才生效),想立刻生效得显式加 <span class="mono">--now</span>。<span class="mono">/skills install --now</span> 就是这条范式的样板。换句话说:边缘扩展不仅要<strong>挂得上</strong>,还要挂得<strong>不打扰正在进行的对话</strong>——能力是边缘的,但缓存纪律是全局的。</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">要加新能力 → 沿 Footprint Ladder 选<strong>足迹最小</strong>的一阶</span></div>
  <div class="step"><span class="num">2</span><span class="sc">插件:<span class="mono">register(ctx)</span> → <span class="mono">register_tool</span>(委托 registry)/<span class="mono">register_hook</span>,不碰核心文件</span></div>
  <div class="step"><span class="num">3</span><span class="sc">技能:内容拼成 <strong>user message</strong> 注入(不进 system prompt,不破缓存)</span></div>
  <div class="step"><span class="num">4</span><span class="sc">MCP:外部工具进 catalog,核心经内置 MCP client 连接,零核心 schema 足迹</span></div>
  <div class="step"><span class="num">5</span><span class="sc">新核心工具 = 最后手段(每个都在<strong>每次 API 调用</strong>发送)</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 协作机制 · 各组分如何咬合实现「能力在边缘、核心窄腰」</div>
  <div class="collab-sub">① 组件清单(★本章核心,其余跨章节配合)</div>
  本章核心:<strong>PluginContext.register_tool</strong>(插件挂工具)、<strong>VALID_HOOKS</strong>(生命周期扩展点)、<strong>技能 user message 注入</strong>、<strong>MCP catalog</strong>。跨章节配合:插件 <span class="mono">register_tool</span> 委托的就是<strong>工具系统</strong>(第 8 章)那个 registry,服务门控用同一个 <span class="mono">check_fn</span>;技能注入 user message <strong>不进 system prompt = 不破缓存</strong>(第 6 章);钩子在工具/LLM/会话/子代理(第 13 章)的固定节点触发;连<strong>平台适配器</strong>(第 17 章)、记忆后端(第 11 章)、provider 都是插件——印证了全书"核心薄、边缘厚"。
  <div class="collab-sub">② 数据流时序</div>
  新能力 → Footprint Ladder 选阶 → 插件 <span class="mono">register(ctx)</span>(register_tool/register_hook)或技能(user message 注入)或 MCP(catalog)→ 边缘挂载,核心工具 schema 不膨胀。
  <div class="collab-sub">③ 关键点</div>
  能力在<strong>边缘</strong>扩展,核心保持<strong>窄腰</strong>:插件不改核心文件(Teknium 铁律)、技能注入 user message 保缓存、MCP 把外部工具关在 catalog。新核心工具是最后手段——因为每个核心工具都在<strong>每次 API 调用</strong>发送,既花 token 又稀释模型注意力。
</div>

<div class="card design">
  <div class="tag">🎯 设计取舍 · 本章围绕什么</div>
  主线:<strong>Footprint Ladder——能力推到边缘,核心保持窄腰</strong>。它主要治两条 LLM 固有约束:
  <p style="margin:.5rem 0 0"><span class="badge constraint">A·中间遗失</span>——每个<strong>核心工具的 schema 都进每一次 API 调用的 context</strong>。工具越多,context 越膨胀,真正该用的那个越容易<strong>淹没在工具堆里</strong>(中间遗失)。把能力压到边缘(技能/插件/MCP 按需出现),核心工具集保持精简,模型的注意力才不被几十个用不上的工具稀释。</p>
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·运维</span>——每个核心工具都是<strong>永久的维护负担</strong>(每次 API call 都发、所有平台都带)。边缘扩展几乎<strong>零核心成本</strong>:插件装进 <span class="mono">~/.hermes/plugins/</span>、技能放进 <span class="mono">~/.hermes/skills/</span>、MCP 进 catalog,加一个不用动核心、不影响别的用户。</p>
  <p style="margin:.5rem 0 0">反模式:什么能力都加成<strong>核心工具</strong>——核心 schema 随能力数量线性膨胀,每次 API 调用都更贵、模型注意力都更散,且每个都得永久维护。Footprint Ladder 的存在,就是逼你先问"能不能停在更高那一阶"。</p>
  <p style="margin:.5rem 0 0">这条取舍在代码里有个很硬的落点:当 MCP/插件工具的 schema 体积超过阈值(默认约<strong>上下文窗口的 10%</strong>),它们会被<strong>折叠</strong>到三个桥工具(<span class="mono">tool_search</span> / <span class="mono">tool_describe</span> / <span class="mono">tool_call</span>)后面,按需检索;而 <span class="mono">_HERMES_CORE_TOOLS</span> 里的核心工具<strong>永远不被折叠</strong>。这恰恰反证了"核心工具贵":系统宁可把成百上千的边缘工具藏进桥后面,也要保证那几十个核心工具每轮<strong>原样常驻</strong>——因为它们被判定为"几乎每个用户每一轮都要用"。能进这个常驻名单,门槛极高。</p>
  <p style="margin:.5rem 0 0">还有一层取舍是"<strong>别重复造</strong>":当三个以上的 PR 想接同一类东西(记忆后端、provider、通知器),正确做法不是一个个并进来,而是设计<strong>一个共享接口</strong>(ABC + 编排器),把现有内置实现包成第一个 provider,再让那些 PR 变成这个接口下的插件。记忆后端(第 11 章)、模型 provider 都是这么收口的——核心只认<strong>一个抽象</strong>,具体实现全在边缘。这就是为什么 Hermes 能在核心几乎不动的前提下,支持二十多个平台、一堆记忆后端和 provider:<strong>抽象在腰,实现在边</strong>。</p>
  <p style="margin:.5rem 0 0">Footprint Ladder 还有个反面清单:<strong>能用终端 + 文件解决的,就别做成新核心工具</strong>;<strong>非密钥的配置,别塞新的 <span class="mono">HERMES_*</span> 环境变量</strong>(<span class="mono">.env</span> 只放密钥,行为开关进 <span class="mono">config.yaml</span>)。这些"不要"和"要走哪一阶"是同一套价值观的两面:核心面每多一个工具、每多一个环境变量,都是<strong>永久的、全局的</strong>负担。把判断前置成一道阶梯,就是让"先问能不能更轻"变成肌肉记忆,而不是事后再来心疼 context 和维护成本。</p>
</div>

<div class="card key">
  <div class="tag">📌 本课要点</div>
  <ul>
    <li><strong>Footprint Ladder</strong>:扩展现有代码 → CLI+技能 → 服务门控工具 → 插件 → MCP → 新核心工具(最后手段);选足迹最小的一阶。</li>
    <li><strong>插件不改核心</strong>:<span class="mono">register(ctx)</span> 委托 <span class="mono">tools.registry</span>(第 8 章)挂工具/命令/钩子,绝不碰 <span class="mono">run_agent.py</span> 等核心文件(Teknium 铁律)。</li>
    <li><strong>生命周期钩子</strong>:<span class="mono">VALID_HOOKS</span> 在工具/LLM/会话/子代理/网关的固定节点开放观察与改写。</li>
    <li><strong>技能保缓存(★)</strong>:技能内容注入为 <strong>user message</strong>(append-only),不进 system prompt,整会话缓存前缀不作废(第 6 章)。</li>
    <li><strong>为什么核心工具贵</strong>:每个核心工具的 schema 都在<strong>每次 API 调用</strong>发送——膨胀 context(A·中间遗失)+ 永久维护(G·运维)。</li>
  </ul>
</div>
""",
    "en": r"""
<p class="lead">Across the previous 22 chapters, Hermes's core has barely "grown" — platform adapters, memory backends, model providers, chat skills: the vast majority of capability is bolted on from the <strong>edges</strong>. This chapter pins down the discipline that runs through the whole book: <strong>capability extends at the edges, the core stays a narrow waist</strong>. Three mechanisms: plugins, skills, MCP.</p>

<div class="card analogy">
  <div class="tag">🔌 Analogy · the Swiss Army knife vs the toolbox</div>
  The core should hold only the few most-used blades (core tools); everything else goes in the <strong>toolbox</strong> (plugins/skills/MCP), pulled out only when needed. Weld every tool onto the knife and it gets <strong>too heavy to carry</strong> — because every outing (every API call) must lug <strong>the manual for all tools</strong> (every tool schema in the context). The more tools, the more the one you actually need <strong>drowns in the pile of manuals</strong>.
</div>

<div class="card macro">
  <div class="tag">🌍 Macro · the Footprint Ladder</div>
  To add a capability, pick the highest rung by <strong>smallest footprint</strong>: ① extend existing code → ② CLI command + skill → ③ service-gated tool (<span class="mono">check_fn</span>) → ④ plugin → ⑤ MCP server (in the catalog) → ⑥ a new core tool (<strong>last resort</strong>). The further down, the more permanent core surface it occupies. Most capabilities should stop at the top rungs.
</div>

<h2>Plugins: hook into the core without touching it</h2>
<p>A plugin attaches tools/commands/hooks to Hermes through one <span class="mono">register(ctx)</span>, <strong>touching not a single core file</strong>:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">hermes_cli/plugins.py</span><span class="ln">367-400 · simplified</span></div>
  <pre><span class="kw">class</span> <span class="fn">PluginContext</span>:
    <span class="kw">def</span> <span class="fn">register_tool</span>(self, name, toolset, schema, handler,
                      check_fn=<span class="kw">None</span>, override=<span class="kw">False</span>):
        <span class="cm">&quot;&quot;&quot;Register a tool in the global registry and track it as plugin-provided.&quot;&quot;&quot;</span>
        <span class="kw">from</span> tools.registry <span class="kw">import</span> registry
        registry.register(name=name, toolset=toolset, schema=schema,
                          handler=handler, check_fn=check_fn, override=override)</pre>
</div>
<p><span class="mono">register_tool</span> merely <strong>delegates</strong> to the <strong>same</strong> <span class="mono">tools.registry</span> as built-in tools (ch.8) — plugin tools and core tools take the exact same register/dispatch/availability path. <span class="mono">check_fn</span> makes a tool <strong>service-gated</strong> (absent until its credential is configured, zero footprint); <span class="mono">override</span> can even replace a built-in. The iron rule (Teknium): <strong>plugins must NOT modify core files</strong> (<span class="mono">run_agent.py</span>/<span class="mono">cli.py</span>…); if you need more, widen the generic plugin surface rather than hardcoding plugin logic into the core.</p>

<p>Why make "plugins must NOT modify core files" an <strong>iron rule</strong> rather than "try not to"? Because the moment the core is polluted by one plugin's special-case logic <strong>hardcoded</strong> in, it's <strong>held hostage</strong> by that plugin — the next refactor of <span class="mono">run_agent.py</span> has to worry whether it'll break some plugin's implicit contract, and the core's evolvability <strong>freezes</strong>. Flip the rule instead: when a plugin needs a new capability, you don't carve a special case into the core, you <strong>widen the generic plugin surface</strong> (add a new hook, add a new <span class="mono">ctx</span> method). That way the core only ever faces a <strong>finite, generic</strong> set of extension points, not an endless stream of plugin special cases. AGENTS.md records PR #5295 deleting 95 lines of one plugin's hardcoded argparse from <span class="mono">main.py</span> — the enforcement log of exactly this rule.</p>

<p>Note that <span class="mono">register_tool</span> delegates to the <strong>same</strong> <span class="mono">tools.registry</span> as built-in tools — meaning plugin tools aren't "second-class citizens": they take the same schema collection, same dispatch, same availability check. <span class="mono">check_fn</span> is the crucial piece: a tool <strong>appears only when its prerequisite is met</strong> (e.g. a configured API key), otherwise not even its schema enters the context — truly <strong>zero footprint</strong>. This is the bedrock of rung three on the Footprint Ladder ("service-gated tool"); the core toolset's own <span class="mono">ha_*</span> (Home Assistant) and <span class="mono">computer_use</span> use the same trick — invisible until their token is configured.</p>

<p>Plugins can attach more than tools and hooks — also <strong>CLI subcommands</strong>: <span class="mono">ctx.register_cli_command(...)</span> wires the plugin's argparse subtree into <span class="mono">hermes</span> at startup, so <span class="mono">hermes &lt;plugin&gt; &lt;subcmd&gt;</span> just works with not one line of <span class="mono">main.py</span> changed. This is rung <strong>two</strong> of the Footprint Ladder ("CLI command + skill"): plenty of management capabilities (subscriptions, scheduled tasks, service config) need not be model tools at all — make a shell subcommand and write a skill teaching the agent to run <span class="mono">hermes &lt;subcmd&gt;</span>, and the <strong>model-tool footprint is zero</strong>.</p>

<h2>Hooks: intervene at the core's lifecycle joints</h2>
<p>Plugins can also attach callbacks at key points of the agent's run, without touching the core loop:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">hermes_cli/plugins.py</span><span class="ln">128-155 · excerpt</span></div>
  <pre>VALID_HOOKS = {
    <span class="st">"pre_tool_call"</span>, <span class="st">"post_tool_call"</span>,
    <span class="st">"transform_llm_output"</span>,        <span class="cm"># rewrite the text returned to the user</span>
    <span class="st">"pre_llm_call"</span>, <span class="st">"post_llm_call"</span>,
    <span class="st">"on_session_start"</span>, <span class="st">"on_session_end"</span>,
    <span class="st">"subagent_start"</span>, <span class="st">"subagent_stop"</span>,
    <span class="st">"pre_gateway_dispatch"</span>,         <span class="cm"># before gateway dispatch (can skip/rewrite)</span>
}</pre>
</div>
<p>These are <strong>reserved extension points</strong>: around tool calls, around LLM calls, session start/end, subagent start/stop, before gateway dispatch. A plugin attaches a callback to <strong>observe or rewrite</strong> the flow (e.g. <span class="mono">transform_llm_output</span> for persona rewriting, <span class="mono">pre_gateway_dispatch</span> to intercept messages). The core fires these hooks at fixed positions but <strong>neither knows nor cares</strong> who's attached — the narrow waist again.</p>

<p>Hooks sound like "reserved extension points," but Hermes explicitly rejects <strong>speculative infrastructure</strong>: adding a hook with no real consumer is easy; removing it once plugins depend on it is <strong>brutally hard</strong>. So every name in <span class="mono">VALID_HOOKS</span> should have a real use case behind it — <span class="mono">transform_llm_output</span> for persona rewriting, <span class="mono">pre_gateway_dispatch</span> to intercept/rewrite a message before auth, <span class="mono">subagent_start</span>/<span class="mono">subagent_stop</span> bracketing subagents (ch.13). This discipline is the flip side of the narrow waist: the extension surface the core exposes must also be <strong>as small as possible and actually used</strong>, not a pile of speculatively-reserved callbacks nobody attaches to.</p>

<p>Plugin attachment is by <strong>discovery</strong>, not by a registration manifest: at startup four places are scanned — the repo's own <span class="mono">plugins/</span>, the user's <span class="mono">~/.hermes/plugins/</span>, project-level <span class="mono">./.hermes/plugins/</span> (opt-in), and pip-installed entry-point packages. To add a plugin you just drop a directory into <span class="mono">~/.hermes/plugins/</span> — <strong>not one core file changes</strong> — and next startup auto-discovers it and calls <span class="mono">register(ctx)</span>. That's what "edge extension" looks like at the filesystem level: capability is <strong>bolted on</strong>, not <strong>compiled in</strong>.</p>

<h2>Skills: inject a user message, don't break the cache (★ cache line)</h2>
<p>Skills are another edge-extension line, and their injection method deliberately preserves the cache:</p>

<div class="codefile">
  <div class="cf-head"><span class="dot"></span><span class="path">agent/skill_commands.py</span><span class="ln">245-274 · excerpt</span></div>
  <pre><span class="kw">def</span> <span class="fn">_build_skill_message</span>(loaded_skill, skill_dir, activation_note, ...):
    <span class="cm">&quot;&quot;&quot;Format a loaded skill into a user/system message payload.&quot;&quot;&quot;</span>
    content = str(loaded_skill.get(<span class="st">"content"</span>) <span class="kw">or</span> <span class="st">""</span>)
    parts = [activation_note, <span class="st">""</span>, content.strip()]
    <span class="kw">if</span> skill_dir:
        parts.append(<span class="st">f"[Skill directory: {skill_dir}]"</span>)
    ...                                  <span class="cm"># injected as a user message, not into the system prompt</span></pre>
</div>
<p>The key is the <strong>injection point</strong>: a skill's content is assembled into a <strong>user message</strong> fed into the conversation, <strong>not</strong> stuffed into the system prompt. This is deliberate — change the system prompt and you <strong>shatter the whole conversation's cached prefix</strong> (the ch.6 iron rule); but appending a user message is append-only, leaving the cached prefix <strong>untouched</strong>. So when you <span class="mono">/skill-name</span> to pull in a skill mid-conversation, you don't void the whole conversation's cache. Edge extension answers to the cache line too.</p>

<p>Dig one layer deeper into "why a user message." A long conversation <strong>reuses</strong> a cached prefix (system prompt + early messages) every turn, and the cache-hit tokens are fast and cheap. Stuff skill content into the system prompt and that prefix <strong>changes</strong>; from that turn on the entire prefix <strong>misses</strong> and is recomputed at full price — and <strong>every turn</strong> thereafter, not just once. Assemble the skill into a <strong>user message</strong> appended at the <strong>end</strong> and the prefix is <strong>untouched</strong>, the cache keeps hitting. That's why the "cache is sacred" line (ch.6) reaches all the way out to edge extension: it isn't that the skill doesn't matter, it's that the <strong>injection point</strong> directly decides the user's bill.</p>

<p>Skills themselves are layered: <span class="mono">skills/</span> are <strong>built-in skills</strong> loaded by default; <span class="mono">optional-skills/</span> ship with the repo but are <strong>not active by default</strong>, installed explicitly via <span class="mono">hermes skills install</span> (heavier/niche skills); and beyond that are the user's own plugin skills. This layering follows the same logic as the Footprint Ladder: <strong>the more common, the closer to the core; the more niche, the closer to the edge</strong>. MCP takes another edge path — external tools go into the <span class="mono">optional-mcps/</span> catalog, disabled by default, connected only on <span class="mono">hermes mcp install</span>, reached through the built-in MCP client with <strong>zero core-schema footprint</strong>. "In the catalog = approved" — no community tier, no auto-update.</p>

<p>A subtle aside on discovery: not every plugin uses the same discovery. The general <span class="mono">PluginManager</span> handles tools/hooks/CLI commands; but <strong>model-provider</strong> plugins use a <strong>separate, lazy discovery</strong> — scanned on the first <span class="mono">get_provider_profile()</span> or <span class="mono">list_providers()</span> call, NOT imported by the <span class="mono">PluginManager</span> (which would double-instantiate <span class="mono">ProviderProfile</span>). A user plugin of the same name <strong>overrides</strong> a built-in profile (last-writer-wins), so a third party can swap out any built-in provider without patching the repo. The same "edge extension" philosophy grows different discovery paths in different subsystems.</p>

<p>The cache line even constrains "installing a skill" itself: slash commands that mutate system-prompt state (skills, tools, memory) are <strong>cache-aware</strong> — they <strong>defer invalidation</strong> by default (the change takes effect next session), and you must opt in with <span class="mono">--now</span> for it to apply immediately. <span class="mono">/skills install --now</span> is the canonical template. In other words: edge extension must not only <strong>attach</strong>, it must attach <strong>without disturbing the in-flight conversation</strong> — capability is at the edge, but cache discipline is global.</p>

<div class="vflow">
  <div class="step"><span class="num">1</span><span class="sc">need a new capability → pick the <strong>smallest-footprint</strong> rung on the Footprint Ladder</span></div>
  <div class="step"><span class="num">2</span><span class="sc">plugin: <span class="mono">register(ctx)</span> → <span class="mono">register_tool</span> (delegates to registry) / <span class="mono">register_hook</span>, no core files touched</span></div>
  <div class="step"><span class="num">3</span><span class="sc">skill: content assembled into a <strong>user message</strong> (not the system prompt, cache intact)</span></div>
  <div class="step"><span class="num">4</span><span class="sc">MCP: external tools in the catalog, the core connects via its built-in MCP client, zero core-schema footprint</span></div>
  <div class="step"><span class="num">5</span><span class="sc">a new core tool = last resort (each is sent on <strong>every API call</strong>)</span></div>
</div>

<div class="card collab">
  <div class="tag">🧩 Collaboration · how the parts mesh for "capability at the edges, core narrow"</div>
  <div class="collab-sub">① Component roster (★ this chapter's core; the rest is cross-chapter teamwork)</div>
  Core: <strong>PluginContext.register_tool</strong> (plugins attach tools), <strong>VALID_HOOKS</strong> (lifecycle extension points), <strong>skill user-message injection</strong>, <strong>the MCP catalog</strong>. Cross-chapter teamwork: <span class="mono">register_tool</span> delegates to the very <strong>tool system</strong> (ch.8) registry, service-gating with the same <span class="mono">check_fn</span>; skills inject a user message that <strong>doesn't enter the system prompt = cache intact</strong> (ch.6); hooks fire at fixed points of tools/LLM/session/subagents (ch.13); even <strong>platform adapters</strong> (ch.17), memory backends (ch.11), and providers are plugins — vindicating the book's "thin core, thick edges."
  <div class="collab-sub">② Data-flow timing</div>
  new capability → pick a Footprint Ladder rung → plugin <span class="mono">register(ctx)</span> (register_tool/register_hook), or skill (user-message injection), or MCP (catalog) → attached at the edge, the core tool schema doesn't grow.
  <div class="collab-sub">③ The key point</div>
  Capability extends at the <strong>edges</strong>, the core stays a <strong>narrow waist</strong>: plugins don't touch core files (the Teknium iron rule), skills inject a user message to preserve the cache, MCP cages external tools in the catalog. A new core tool is the last resort — because each core tool is sent on <strong>every API call</strong>, costing tokens and diluting the model's attention.
</div>

<div class="card design">
  <div class="tag">🎯 Design trade-off · what this chapter is about</div>
  The throughline: <strong>the Footprint Ladder — push capability to the edges, keep the core a narrow waist</strong>. It mainly treats two inherent LLM constraints:
  <p style="margin:.5rem 0 0"><span class="badge constraint">A·lost-in-the-middle</span> — every <strong>core tool's schema enters the context of every single API call</strong>. The more tools, the more the context bloats and the more the one you actually need <strong>drowns in the tool pile</strong> (lost in the middle). Push capability to the edges (skills/plugins/MCP appearing on demand), keep the core toolset lean, and the model's attention isn't diluted by dozens of unused tools.</p>
  <p style="margin:.5rem 0 0"><span class="badge constraint">G·ops</span> — every core tool is a <strong>permanent maintenance burden</strong> (sent on every API call, carried on every platform). Edge extension is nearly <strong>zero core cost</strong>: a plugin drops into <span class="mono">~/.hermes/plugins/</span>, a skill into <span class="mono">~/.hermes/skills/</span>, an MCP into the catalog; adding one touches no core and affects no other user.</p>
  <p style="margin:.5rem 0 0">The anti-pattern: making every capability a <strong>core tool</strong> — the core schema bloats linearly with capability count, every API call gets pricier and the model's attention thinner, and each one needs permanent upkeep. The Footprint Ladder exists to force the question first: "can this stop at a higher rung?"</p>
  <p style="margin:.5rem 0 0">This trade-off has a very hard anchor in the code: when the schema size of MCP/plugin tools exceeds a threshold (default ~<strong>10% of the context window</strong>), they get <strong>folded</strong> behind three bridge tools (<span class="mono">tool_search</span> / <span class="mono">tool_describe</span> / <span class="mono">tool_call</span>) and retrieved on demand; the core tools in <span class="mono">_HERMES_CORE_TOOLS</span> are <strong>never folded</strong>. That's the converse proof that "core tools are expensive": the system would rather hide hundreds of edge tools behind a bridge than not keep those few dozen core tools <strong>resident verbatim</strong> every turn — because they're judged "needed by nearly every user every turn." The bar to make that resident list is very high.</p>
  <p style="margin:.5rem 0 0">One more trade-off is "<strong>don't duplicate</strong>": when 3+ PRs want to integrate the same category of thing (memory backends, providers, notifiers), the right move isn't to merge them one by one but to design <strong>one shared interface</strong> (an ABC + orchestrator), wrap the existing built-in as the first provider, and turn those PRs into plugins against that interface. Memory backends (ch.11) and model providers were closed off exactly this way — the core knows only <strong>one abstraction</strong>, every concrete implementation lives at the edge. That's how Hermes supports twenty-plus platforms, a pile of memory backends and providers while the core barely moves: <strong>abstraction at the waist, implementation at the edge</strong>.</p>
  <p style="margin:.5rem 0 0">The Footprint Ladder also has a flip-side don't-list: <strong>if terminal + file already do the job, don't make a new core tool</strong>; <strong>for non-secret config, don't add a new <span class="mono">HERMES_*</span> env var</strong> (<span class="mono">.env</span> is for secrets only, behavioral switches go in <span class="mono">config.yaml</span>). These "don'ts" and the "which rung" question are two sides of one value: every extra tool, every extra env var on the core surface is a <strong>permanent, global</strong> burden. Front-loading the judgment into a ladder turns "ask first whether it can be lighter" into muscle memory, instead of regretting the context and upkeep cost afterward.</p>
</div>

<div class="card key">
  <div class="tag">📌 Key points</div>
  <ul>
    <li><strong>Footprint Ladder</strong>: extend existing code → CLI+skill → service-gated tool → plugin → MCP → a new core tool (last resort); pick the smallest-footprint rung.</li>
    <li><strong>Plugins don't touch the core</strong>: <span class="mono">register(ctx)</span> delegates to <span class="mono">tools.registry</span> (ch.8) to attach tools/commands/hooks, never touching <span class="mono">run_agent.py</span> etc. (the Teknium iron rule).</li>
    <li><strong>Lifecycle hooks</strong>: <span class="mono">VALID_HOOKS</span> opens observe-and-rewrite points around tools/LLM/session/subagents/gateway.</li>
    <li><strong>Skills preserve the cache (★)</strong>: a skill's content is injected as a <strong>user message</strong> (append-only), not into the system prompt, so the whole conversation's cached prefix isn't voided (ch.6).</li>
    <li><strong>Why core tools are expensive</strong>: every core tool's schema is sent on <strong>every API call</strong> — bloating the context (A·lost-in-the-middle) + permanent upkeep (G·ops).</li>
  </ul>
</div>
"""
}
