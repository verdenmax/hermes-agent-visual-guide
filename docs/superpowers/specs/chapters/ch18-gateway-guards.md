# ch18 Spec — 网关消息守卫：两道 guard + 控制命令旁路（★缓存线）

## 目标
讲清 agent 运行时消息要过两道顺序守卫(适配器层 busy 排队 + 网关 runner 层 slash 分派),而审批/控制命令(/stop /new /approve /deny…)必须**同时旁路两道、内联派发**——否则被兜底丢弃成空响应(zero-char)或死锁。旁路同时守住缓存线:控制命令走控制通道、不混进对话历史,维持严格角色交替不破缓存。

## 🎯 章末设计取舍（双 badge）
- 主线：**两道守卫拦截消息 + 控制命令旁路 = 并发安全 + 不破缓存**。
- `D·指令=数据`：模型分不清指令 vs 对话内容;网关用显式 get_command() 解析 + 旁路通道把控制命令从消息流拎出走控制通道,不当对话数据喂模型。
- `G·运维`：并发消息、会话生命周期、中断、审批的运维复杂度,靠两道守卫 + 旁路 + owner-task 映射管得确定无竞争。

## 真实锚点（已 view 核对）
1. **第一道 guard 状态** — `gateway/platforms/base.py:2154-2162`:`self._active_sessions: Dict[str, asyncio.Event] = {}`(每会话中断 Event=busy 标志)、`self._pending_messages: Dict[str, MessageEvent] = {}`(busy 时排队)、`self._session_tasks: Dict[str, asyncio.Task] = {}`(会话→任务,让 /stop/new/reset 取消正确任务、确定性释放守卫;注释 2154-2159 解释 owner-task map 防 stale busy)。
2. **旁路逻辑** — `base.py:4253-4300`:on-entry self-heal 清 stale lock(#11016 split-brain) → `if session_key in self._active_sessions` → `cmd = event.get_command()` → `from hermes_cli.commands import should_bypass_active_session` → `if cmd in {"stop","new","reset"}: await self._dispatch_active_session_command(...)`(取消在途任务+序列化交接);否则 /approve /deny /status /background /restart 直接内联 dispatch。**注释 4269-4272**:"Do NOT use _process_message_background — it manages session lifecycle and its cleanup races with the running task (see PR #4926)"。
3. **旁路判定 + zero-char** — `hermes_cli/commands.py:379-399` `def should_bypass_active_session(command_name)` docstring "Return True for any resolvable slash command. Queueing is always wrong for a recognized slash command because the safety net in gateway.run discards any command text that reaches the pending queue — a mid-run /model would silently interrupt the agent AND get discarded, a zero-char response."；`return resolve_command(command_name) is not None`。
4. **第二道 guard** — `gateway/run.py:7970-7982`:`command = event.get_command()` → `from hermes_cli.commands import GATEWAY_KNOWN_COMMANDS, is_gateway_known_command, resolve_command` → `canonical = _cmd_def.name`;:8072-8258 `if canonical == "new"/"stop"/"status"/"approve"…` 分派。
5. AGENTS.md「The gateway has TWO message guards — both must bypass approval/control commands」+「(1) base adapter queues in _pending_messages when session_key in _active_sessions, (2) gateway runner intercepts /stop /new /queue /status /approve /deny」。

## 🧩 协作机制框（三段）
- ① 组件清单:_active_sessions(busy 状态) + _pending_messages(排队) + _session_tasks(会话→任务) + should_bypass_active_session(旁路判定) + 第二道 runner 守卫(GATEWAY_KNOWN_COMMANDS)。跨章节:消息先被适配器归一化成 MessageEvent(第 17 章)才进守卫;旁路保证控制命令不污染对话历史、维持严格角色交替=不破缓存(第 6 章);/stop 中断级联到子代理(第 13 章委派);/approve 是危险操作的人在回路审批(第 24 章安全)。
- ② 数据流时序:MessageEvent → 第一道守卫(session_key in _active_sessions?) → get_command()+should_bypass → 旁路(/stop 取消任务 / /approve 内联派发)或排队(_pending_messages) → 第二道守卫(runner 按 canonical 分派)。
- ③ 关键点:两道守卫都必须放行控制命令;排队控制命令=被兜底丢弃(空响应)或死锁(/approve 等不到);旁路必须内联派发而非 _process_message_background(后者管会话生命周期、清理和在跑任务抢)。

## 模板结构
lead → analogy(急诊分诊台) → macro(两道顺序守卫,控制命令旁路) → 主体(第一道 guard 状态 codefile + 旁路逻辑 codefile + should_bypass docstring codefile) → vflow → collab → design(回指 D+G) → key。

## quiz 考点
- agent 跑到一半发 /model(或 /stop),为什么不能像普通消息那样排队(网关 runner 兜底会丢弃排队的命令文本,变成 zero-char 空响应;/approve 还会死锁)。
- 两道守卫分别在哪一层(① 适配器层 busy→_pending_messages;② 网关 runner 层 slash 分派),控制命令为什么要同时旁路两道。
- 旁路为什么必须内联派发、不能走 _process_message_background(它管会话生命周期,清理会和正在跑的任务抢,见 PR #4926)。

## 验收
0 error；3 codefile 逐字真实(docstring `"""` 写 `&quot;`);两道守卫/旁路两类/zero-char/缓存线讲清;双语镜像;回指 D+G;中文 ≥1500(接近,最后补)。
