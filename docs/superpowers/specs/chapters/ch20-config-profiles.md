# ch20 Spec — 配置 + Profiles：多实例隔离

## 目标
讲清 profile 多实例隔离的核心机制:在任何业务模块 import 之前,_apply_profile_override() 抢先把 HERMES_HOME 设成 ~/.hermes/profiles/<name>;之后全代码库唯一路径入口 get_hermes_home() 自动指向该目录,config/密钥/记忆/会话/技能全隔离。配置再分两层:行为设置进 config.yaml(DEFAULT_CONFIG)、密钥进 .env(OPTIONAL_ENV_VARS,全 password:True)。

## 🎯 章末设计取舍（双 badge G + B）
- 主线：**import 前抢设 HERMES_HOME + 单一真相源路径 = 完全隔离的多实例;配置再分层(密钥独立)**。
- `G·运维`：一个人跑 work/personal/各客户多实例,密钥/记忆/会话/网关绝不混;一个环境变量切换整套状态盘,"开新实例"="建新目录"。
- `B·无状态`：核心无全局"当前哪个实例"状态,全靠 HERMES_HOME 一个外部变量 + get_hermes_home() 一个入口推导。

## 真实锚点（已 view 核对）
1. **profile 抢先覆盖** — `hermes_cli/main.py:336` `def _apply_profile_override() -> None:` docstring "Pre-parse --profile/-p and set HERMES_HOME before imports."；`:481` `if profile_name is not None:` → `:485` `hermes_home = resolve_profile_env(profile_name)` → `:501` `os.environ["HERMES_HOME"] = hermes_home` → `:502-505` strip argv;`:508` 模块级 `_apply_profile_override()`(在其余 import 之前执行)。
2. **单一真相源** — `hermes_constants.py:54` `def get_hermes_home() -> Path:` docstring "Reads HERMES_HOME env var, falls back to the platform-native default. This is the single source of truth — all other copies should import this."；`:70-76` `override = get_hermes_home_override(); if override: return Path(override)` → `val = os.environ.get("HERMES_HOME", "").strip(); if val: return Path(val)` → fallback `_get_platform_default_hermes_home()`；`:388` `def display_hermes_home() -> str:`(用户可见消息,default ~/.hermes / profile ~/.hermes/profiles/coder)。
3. **配置分层** — `hermes_cli/config.py:883` `DEFAULT_CONFIG = {` (行为设置 config.yaml:model/agent/terminal/compression/memory/gateway…)；`:2860` `"_config_version": 30,`；`:2885` `OPTIONAL_ENV_VARS = {`(密钥 .env,每条 `"password": True` + category:provider/messaging/tool)。
4. **profile root HOME-anchored** — AGENTS.md「Profile operations are HOME-anchored, not HERMES_HOME-anchored」(让 hermes -p coder profile list 能看到所有 profile)。
5. AGENTS.md「Profiles: Multi-Instance Support」+「DO NOT hardcode ~/.hermes paths」(PR#3575 修 5 bug)+「.env is for secrets only; behavioral settings go in config.yaml」+「MESSAGING_CWD removed → terminal.cwd」。

## 🧩 协作机制框（三段）
- ① 组件清单:_apply_profile_override(import 前抢设 env) + get_hermes_home(单一真相源) + DEFAULT_CONFIG/OPTIONAL_ENV_VARS(配置分层)。跨章节:HERMES_HOME 决定记忆(第 11 章)、技能(第 9 章)、Curator(第 10 章)、会话库、网关日志各落哪个 profile;平台适配器用 token lock 防两 profile 抢同一 bot 凭据(第 17 章);profile 之间是独立的岛——隔离本身就是设计,不做跨 profile 实时配置继承。
- ② 数据流时序:-p coder → _apply_profile_override()(模块顶层,import 前)→ HERMES_HOME=profiles/coder → import 链铺开 → 30+ 处模块级 get_hermes_home() 缓存成 coder → 该进程全程认 coder 实例。
- ③ 关键点:profile 隔离 = "import 前设一个环境变量" + "所有路径走 get_hermes_home() 单一入口";硬编码 ~/.hermes 击穿隔离;非密配置塞 .env 是另一种坏味道(应进 config.yaml)。

## 模板结构
lead → analogy(连锁酒店分店) → macro(一个环境变量决定一切) → 主体(_apply_profile_override codefile + get_hermes_home codefile + 配置分层 codefile) → vflow → collab → design(回指 G+B) → key。

## quiz 考点
- profile 多实例隔离靠什么实现(在任何业务 import 之前 _apply_profile_override() 抢先设 HERMES_HOME 环境变量;之后所有路径经 get_hermes_home() 自动指向 profile 目录)。
- 代码里要拿 hermes home 目录,该怎么拿、不能怎么拿(调 get_hermes_home() 单一真相源;禁止硬编码 Path.home()/'.hermes',否则击穿 profile 隔离,PR#3575)。
- 一个"messaging 工作目录"该写 .env 还是 config.yaml(config.yaml 的 terminal.cwd;.env 只放密钥,非密行为设置一律 config.yaml)。

## 验收
0 error；3 codefile 逐字真实(docstring `"""` 写 `&quot;`,`->` 写 `-&gt;`,正文 `<name>` 写 `&lt;name&gt;`);抢设 env/单一真相源/配置分层讲清;双语镜像;回指 G+B;中文 ≥1500(接近,最后补)。
