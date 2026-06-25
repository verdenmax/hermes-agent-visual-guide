# ch17 Spec — 网关 + 多平台适配器：单进程跨 28+ 平台

## 目标
讲清 Hermes 网关如何用「统一消息抽象 + 适配器边缘翻译」单进程同时服务 28+ 平台:核心定义 MessageEvent(归一化消息)+ BasePlatformAdapter(适配器契约),每个平台写一个适配器子类把原生消息翻成 MessageEvent 交 handle_message,核心网关零平台专属代码。主流平台(telegram/discord/slack/matrix…)都是 plugins/platforms/ 边缘插件 = 窄腰极致。

## 🎯 章末设计取舍（双 badge）
- 主线：**统一消息抽象 + 适配器边缘翻译 = 单进程跨 28+ 平台;平台差异在边缘(窄腰)**。
- `G·运维`：一套核心服务所有平台,运维一个进程而非二十个;加平台不动核心。
- `B·无状态`：核心无全局会话状态,靠 MessageEvent 的 source/session_key 把每条消息路由到独立会话。

## 真实锚点（已 view 核对）
1. **统一消息** — `gateway/platforms/base.py:1599-1644` `@dataclass class MessageEvent` docstring "Incoming message from a platform. Normalized representation that all adapters produce."；字段 text(1607)/message_type(1608)/source(1611)/raw_message(1614)/media_urls(1628)/reply_to_message_id(1632)。
2. **适配器契约** — `base.py:2082-2091` `class BasePlatformAdapter(ABC)` docstring "Base class for platform adapters. Subclasses implement platform-specific logic for: Connecting and authenticating / Receiving messages / Sending messages/responses / Handling media"；`base.py:2601-2620` `@abstractmethod async def connect()->bool`(docstring "Connect to the platform and start receiving messages. Returns True if connection was successful.")/`disconnect()`(2610-2613)/`send(self, chat_id, content, reply_to=None, ...)`(2615-2620)。
3. **真实适配器翻译** — `plugins/platforms/irc/adapter.py:482-510` `async def _dispatch_message(self, text, chat_id, chat_type, user_id, user_name)` docstring "Build a MessageEvent and hand it to the base class handler." → `source = self.build_source(...)`(494) → `event = MessageEvent(text=text, message_type=MessageType.TEXT, source=source, message_id=..., timestamp=...)`(502) → `await self.handle_message(event)`(510)；`irc/adapter.py:281-283` `async def send_typing(self, chat_id, metadata=None)` docstring "IRC has no typing indicator — no-op." + `pass`。
4. **28+ 平台清单** — 插件式 `plugins/platforms/<name>/adapter.py`(20个,均 `class XxxAdapter(BasePlatformAdapter)`):telegram:403/discord:718/slack:400/matrix:774/mattermost:71/feishu:1409/line:638/teams:690/whatsapp/wecom:143/dingtalk:153/email:306/sms:56/irc:95/homeassistant:51/google_chat:429/ntfy:152/photon:190/raft:446/simplex:137。内置 `gateway/platforms/*.py`(9个):signal:247/webhook:107/yuanbao:4981/weixin:1138/qqbot:154/bluebubbles:112/api_server:744/msgraph_webhook:45/relay:46。
5. **命令解析** — `base.py:1663` `def get_command()`(从 MessageEvent 抽 /command,供第 18 章守卫旁路判定)。

## 🧩 协作机制框（三段）
- ① 组件清单:MessageEvent(归一化) + BasePlatformAdapter(契约) + handle_message(基类统一入口) + session_key 路由。跨章节:绝大多数适配器是 plugins/platforms/ 边缘插件(第 23 章),核心只认抽象=窄腰(第 4 章);消息进来先过两道守卫(第 18 章);统一 MessageEvent 喂 agent 核心循环(第 7 章);bot 凭据用 token lock 防多 profile 抢(第 20 章)。
- ② 数据流时序:平台原生事件 → 适配器 build_source()+MessageEvent() → handle_message() → session_key 路由 → 两道守卫 → agent 循环 → send() 翻回平台格式。
- ③ 关键点:核心只认 MessageEvent + BasePlatformAdapter 两个抽象,各平台协议/能力/格式差异(连有无 typing)全沉到边缘适配器;加平台=写一个 plugins/platforms/<name>/adapter.py 子类,核心零改动。

## 模板结构
lead → analogy(联合国同传) → macro(统一抽象,平台差异在边缘) → 主体(MessageEvent codefile + BasePlatformAdapter codefile + IRCAdapter 翻译 codefile) → vflow → collab → design(回指 G+B) → key。

## quiz 考点
- 加一个新平台(比如某新 IM)要改核心网关吗(不要,写一个 plugins/platforms/<name>/adapter.py 的 BasePlatformAdapter 子类,核心零改动)。
- 不同平台的消息进核心前长什么样(都被归一化成同一个 MessageEvent;核心从不认识平台原生格式)。
- IRC 没有「正在输入」指示,这个差异怎么处理(适配器里 send_typing 写成 no-op,平台能力差异在边缘吸收,核心不感知)。

## 验收
0 error；3 codefile 逐字真实(docstring `"""` 写 `&quot;`,`->` 写 `-&gt;`,正文 `<name>` 写 `&lt;name&gt;`);统一抽象/边缘翻译/会话路由讲清;双语镜像;回指 G+B;中文 ≥1500(接近,最后补)。
