# ch19 Spec — TUI + 桌面：Ink + JSON-RPC + PTY

## 目标
讲清 hermes --tui 的两进程架构:Node(Ink/React)画屏幕 + Python(tui_gateway)跑 AIAgent,靠 stdio 上换行分隔的 JSON-RPC 解耦;TS 拥有屏幕、Python 拥有会话/工具/模型。仪表盘聊天页不重写,而是把同一个 hermes --tui 经 PTY 投进浏览器 xterm.js。一套核心服务多前端(Ink TUI / 浏览器 PTY / Electron 桌面)。

## 🎯 章末设计取舍（单 badge G + 窄腰）
- 主线：**一套 agent 核心 + JSON-RPC 解耦多前端 + 嵌入复用 = 多端一致、不重复造轮子(窄腰)**。
- `G·运维`：同一 agent 出现在 CLI/TUI/网关/桌面/仪表盘;Python 核心维护一份,前端各用各的栈(Ink/Electron/xterm.js)独立演进;进程隔离=健壮性。
- 窄腰(第4章)：聊天面只实现一次(Ink),仪表盘 PTY 嵌入复用;反模式=用 React 重写 transcript/composer。

## 真实锚点（已 view 核对）
1. **JSON-RPC 分派** — `tui_gateway/server.py:959-964` `def method(name): def dec(fn): _methods[name] = fn; return fn; return dec`(装饰器注册);`:986-995` `def handle_request(req)`:`normalized = _normalize_request(req)` → `rid, method, params = normalized` → `fn = _methods.get(method)` → `if not fn: return _err(rid, -32601, f"unknown method: {method}")` → `return fn(rid, params)`。
2. **事件回推** — `server.py:866` `def write_json(obj)`(发一帧 JSON,按 transport 路由);`:887-891` `def _emit(event, sid, payload=None)`:`params = {"type": event, "session_id": sid}` (+payload) → `write_json({"jsonrpc": "2.0", "method": "event", "params": params})`;`:3292` `_emit("message.delta", csid, {"text": text})`(逐 token 流式)。
3. **prompt.submit handler** — `server.py:6828-6842` `@method("prompt.submit")` `def _(rid, params)`:取 session_id/text,`if session.get("running"): return _err(rid, 4009, "session busy")`(运行时拒新输入)。
4. **仪表盘 PTY 桥** — `hermes_cli/web_server.py:11505-11506` `@app.websocket("/api/pty")` `async def pty_ws(ws)`;`:11580` `bridge = PtyBridge.spawn(argv, cwd=cwd, env=env)`(spawn 同一个 hermes --tui);`:11593-11606` `async def pump_pty_to_ws()`:`chunk = await loop.run_in_executor(None, bridge.read, ...)` → `if chunk is None: return`(EOF) → `await ws.send_bytes(chunk)`(PTY→浏览器);`:11611-11625` writer loop:`msg = await ws.receive()` → `raw = msg.get("bytes")` → `match = _RESIZE_RE.match(raw)`(浏览器→PTY,resize 本地拦截);`:11055` `_RESIZE_RE = re.compile(rb"\x1b\[RESIZE:(\d+);(\d+)\]")`。
5. **POSIX/Windows PTY** — `web_server.py:11028-11053` POSIX 用 `hermes_cli.pty_bridge`(fcntl/termios/ptyprocess)、Windows 用 `win_pty_bridge`(ConPTY),同一公共接口 spawn/read/write/resize/close。
6. AGENTS.md「TUI Architecture」进程模型(Node Ink ⟷ stdio JSON-RPC ⟷ Python tui_gateway)+「Do not re-implement the primary chat experience in React」+ 桌面 Electron 是另一个 JSON-RPC 前端(requestGateway,自带 composer)。

## 🧩 协作机制框（三段）
- ① 组件清单:method 装饰器(RPC 注册) + handle_request(分派) + _emit/write_json(事件回推) + PtyBridge(PTY 桥)。跨章节:JSON-RPC 后面跑的是 AIAgent 核心循环(第 7 章),TUI 只是前端;prompt.submit 的 busy 检查与网关守卫(第 18 章)同理;仪表盘嵌入复用 hermes --tui=窄腰(第 4 章);Electron 桌面是另一个 JSON-RPC 前端(同 tui_gateway 后端)。
- ② 数据流时序:Ink 输入 → JSON-RPC prompt.submit → handle_request 分派 → AIAgent 跑 → _emit("message.delta") 流式 → Ink 渲染。仪表盘:xterm.js ⟷ WS /api/pty ⟷ PtyBridge.spawn ⟷ hermes --tui 子进程(原样转发字节)。
- ③ 关键点:一套 agent 核心(Python)+ 多前端(Ink/浏览器 PTY/Electron)靠 stdio JSON-RPC 解耦;仪表盘嵌入同一个 hermes --tui 而非重写;前端易变核心稳定,各自迭代。

## 模板结构
lead → analogy(剧院后台台前) → macro(一套核心多前端) → 主体(method+handle_request codefile + _emit 流式 codefile + PTY 双向泵 codefile) → vflow → collab → design(回指 G + 窄腰) → key。

## quiz 考点
- hermes --tui 是几个进程、怎么通信(两进程:Node Ink 画屏 + Python tui_gateway 跑 agent;stdio 上换行分隔 JSON-RPC)。
- 网页仪表盘的聊天页是用 React 重写的还是嵌入的(嵌入——把同一个 hermes --tui 经 PTY 投进 xterm.js,双向转发字节;给 Ink 加功能仪表盘自动有)。
- agent 回复怎么做到逐字显示(服务器 _emit("message.delta") 逐 token 推 event 帧,Ink 追加 transcript)。

## 验收
0 error；3 codefile 逐字真实(简化标注);两进程/JSON-RPC 信封/PTY 嵌入/不重写讲清;双语镜像;回指 G + 窄腰;中文 ≥1500(接近,最后补)。
