# ch21 Spec — Cron + Kanban：不破缓存的后台自动化（★缓存线）

## 目标
讲清 cron 如何安全地后台定时自动化:tick 循环(文件锁防重复)按 parse_schedule 解析的时刻扫到期任务,每个任务起独立 cron 会话(platform="cron"、skip_memory=True),结果带 header/footer 框投递、不镜像进 gateway 主会话——主对话角色交替/缓存不受扰。安全阀:3 分钟硬中断防失控独占、半周期 catchup 防积压补跑。kanban 是多 agent 工作队列(零足迹工具集)。

## 🎯 章末设计取舍（双 badge G + B）
- 主线：**独立会话 + skip_memory + 不镜像主对话 = 后台自动化既不破缓存、也不污染**。
- `G·运维`：定时/批量/多 agent 队列是运维刚需,但要安全:3 分钟硬中断、.tick.lock 防重复、半周期 catchup 防雪崩。
- `B·无状态`：cron 会话独立,不依赖也不污染主会话状态盘;不镜像进 gateway session,主对话角色交替/缓存前缀不受影响。

## 真实锚点（已 view 逐字核对）
1. **调度格式** — `cron/jobs.py:304-353` `def parse_schedule(schedule)`:docstring "Parse schedule string into structured format" + Examples("30m"/"2h"→once、"every 2h"→interval、"0 9 * * *"→cron、ISO→once);`if schedule.lower().startswith("every "): return {"kind":"interval",...}`;`parts = schedule.split(); if len(parts) >= 5 and all(re.match(r'^[\d\*\-,/]+$', p) ...): croniter(schedule); return {"kind":"cron","expr":schedule}`;ISO `if 'T' in schedule ...`。
2. **cron 独立会话(★)** — `cron/scheduler.py:2060-2081` `agent = AIAgent(quiet_mode=True, load_soul_identity=True, skip_memory=True,  # Cron system prompts would corrupt user representations  platform="cron", session_id=_cron_session_id, session_db=_session_db)`。
3. **tick 循环** — `cron/scheduler.py:2384` `def tick(verbose=True, adapters=None, loop=None, sync=True) -> int`。
4. **硬中断** — `cron/scheduler.py:2163-2164` `if hasattr(agent, "interrupt"): agent.interrupt("Cron job timed out (inactivity)")`(AGENTS.md「3-minute hard interrupt on cron sessions」)。
5. **catchup** — `cron/jobs.py:475-490` `def _compute_grace_seconds(schedule)` docstring "Uses half the schedule period, clamped between 120 seconds and 2 hours";`MIN_GRACE = 120; MAX_GRACE = 7200`;`if kind == "interval": period_seconds = schedule.get("minutes",1)*60; grace = period_seconds // 2; return max(MIN_GRACE, min(grace, MAX_GRACE))`;`jobs.py:1369-1382` past grace → skip accumulated(fast-forward)。
6. **文件锁** — `cron/scheduler.py:7`(注释)、`:318-322` `_get_lock_paths` → `lock_dir / ".tick.lock"`(防多进程重复 tick)。
7. **工具** — `tools/cronjob_tools.py:987` `name="cronjob", toolset="cronjob"`(agent 自排 job);`tools/kanban_tools.py:1465+` 一串 `registry.register(... toolset="kanban")`(kanban_show/complete/block/heartbeat/comment/create/link)。
8. AGENTS.md Cron 段:「Cron deliveries are **not** mirrored into the target gateway session — they land in their own cron session with a header/footer frame so the main conversation's message-role alternation stays intact.」(★缓存线);「Cron sessions pass skip_memory=True by default」;3-min hard interrupt;catchup half period clamp 120s-2h;grace 120s one-shot;.tick.lock。

## 🧩 协作机制框（三段）
- ① 组件清单:parse_schedule(调度) + tick(循环+文件锁) + cron 独立会话(skip_memory) + _compute_grace_seconds(catchup)。跨章节:cron 起的是 AIAgent 核心循环(第 7 章)但 skip_memory 让记忆(第 11 章)不跑;独立会话不镜像主对话=角色交替不破缓存(第 6 章);cronjob/kanban 是工具(第 8 章);3 分钟硬中断与委派中断级联(第 13 章)同源。
- ② 数据流时序:tick(.tick.lock) → 到期任务 → catchup 判定(grace=period//2) → 独立 cron 会话(skip_memory/platform=cron) → AIAgent 跑(3 分钟硬中断) → header/footer 框投递(不进主会话)。
- ③ 关键点:后台自动化绝不污染主对话——cron 投递不镜像进 gateway session、skip_memory、独立 session_id;文件锁防重复 tick;半周期 catchup 防积压补跑;3 分钟硬中断防失控独占。

## 模板结构
lead → analogy(公司自动化助理) → macro(调度+独立会话+安全阀) → 主体(parse_schedule codefile + cron 独立会话 codefile + _compute_grace_seconds codefile) → vflow → collab → design(回指 G+B) → key。

## quiz 考点
- cron 任务为什么不在主会话里跑、而起独立会话(避免把自动任务塞进对话历史破坏角色交替/缓存,且 skip_memory 免污染用户画像;结果带框投递不镜像进 gateway session)。
- 定时系统怎么防"错过太久就拼命补跑"(半周期 catchup 窗口,clamp 120s-2h;过了就 fast-forward 不堆积)。
- 怎么防一个跑飞的 cron job 卡死整个调度器(3 分钟硬中断 agent.interrupt + .tick.lock 文件锁防重复 tick)。

## 验收
0 error；3 codefile 逐字真实(docstring `"""` 写 `&quot;`,`>=` 写 `&gt;=`,skip_memory 注释逐字);独立会话/skip_memory/catchup/硬中断讲清,缓存线呼应(不镜像主对话);双语镜像;回指 G+B;中文 ≥1500(接近,最后补)。
