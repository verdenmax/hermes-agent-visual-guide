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
