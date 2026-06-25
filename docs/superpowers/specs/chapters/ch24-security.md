# ch24 Spec — 安全与威胁模型：纵深防御（注入/中毒/最小权限）

## 目标
横向专题:agent 有真实权限(终端/浏览器/文件/消息平台),威胁真实(注入/中毒/毁系统)。Hermes 用纵深防御多层独立安全:① 危险命令审批(detect_dangerous_command 正则黑名单,12 HARDLINE+47 DANGEROUS,HARDLINE 红线连 yolo 都拦)② 子代理最小权限(DELEGATE_BLOCKED_TOOLS 剥离高危工具)③ 注入隔离(网关两道守卫把控制命令从数据流分离,第18章)④ 供应链锁定(依赖全 pin)。绝不靠模型自己判断安全。

## 🎯 章末设计取舍（双 badge D + G）
- 主线：**纵深防御——agent 有真实权限,每层独立安全,绝不靠模型自己判断**。
- `D·指令=数据`：对模型 system prompt/用户消息/工具返回/网页都是 token 无可信边界,恶意内容可伪装成指令注入;对策=不让模型当裁判,控制命令网关显式解析+旁路、危险命令正则黑名单。
- `G·运维`：安全是持续维护的运维责任(审批/最小权限/供应链 pin/profile 隔离),随真实威胁迭代。

## 真实锚点（已 view 逐字核对）
1. **危险命令审批** — `tools/approval.py:262-275` `HARDLINE_PATTERNS = [(r"\brm\s+(-[^\s]*\s+)*(/|/home|/root|/etc|/usr...)", "recursive delete of system directory"), (r"\bmkfs(\.[a-z0-9]+)?\b", "format filesystem (mkfs)"), (r"\bdd\b[^\n]*\bof=/dev/(sd|nvme|hd...)", "dd to raw block device"), (r":\(\)\s*\{...\}", "fork bomb"), (r"\bkill\s+...-1\b", "kill all processes")]`;`:657-668` `def detect_dangerous_command(command) -> tuple:` docstring "Check if a command matches any dangerous patterns. Returns: (is_dangerous, pattern_key, description) or (False, None, None)" → `for pattern_re, description in DANGEROUS_PATTERNS_COMPILED: if pattern_re.search(command_lower): return (True, pattern_key, description)`;`:3-7` 模块 docstring "single source of truth for the dangerous command system: Pattern detection (DANGEROUS_PATTERNS, detect_dangerous_command), Smart approval via auxiliary LLM (auto-approve low-risk commands)";`:288` "12 HARDLINE + 47 DANGEROUS patterns"。
2. **HARDLINE vs DANGEROUS + yolo** — `approval.py:226-241`:yolo/--yolo/approvals.mode=off/cron approve mode 可放行;`:233` 环境(singularity/modal/daytona)已绕过 dangerous 层;`:241` "(chmod -R 777, curl|sh) stay in DANGEROUS_PATTERNS where yolo can pass" → DANGEROUS 可被 yolo 放行,HARDLINE 是更严红线(校验核实:HARDLINE 是否真的连 yolo 都不放行)。
3. **子代理最小权限** — `tools/delegate_tool.py:45-53` `DELEGATE_BLOCKED_TOOLS = frozenset(["delegate_task" # no recursive delegation, "clarify" # no user interaction, "memory" # no writes to shared MEMORY.md, "send_message" # no cross-platform side effects, "execute_code" # children should reason step-by-step, not write scripts])`(逐字)。
4. **供应链锁定** — `pyproject.toml:44-52` 注释 "...radius for the next supply-chain attack" + `"openai==2.24.0"`, `"httpx[socks]==0.28.1"`, `"certifi==2026.5.20"`, `"pyyaml==6.0.3"`(exact pin);AGENTS.md「Dependency Pinning Policy」:PyPI `>=floor,<next_major`、Git URL commit SHA、Actions SHA+comment、CI-only pip `==exact`;litellm 被攻陷后立(PR#2796/#2810)。
5. **注入隔离** — 第18章网关两道守卫 get_command() 显式解析控制命令走旁路(D·指令=数据);system prompt 的 `<shell_security>` 拒 ${var@P} 等混淆构造。

## 🧩 协作机制框（三段）
- ① 组件清单:detect_dangerous_command(审批) + DELEGATE_BLOCKED_TOOLS(子代理最小权限) + 依赖 pin(供应链)。跨章节:注入隔离靠网关两道守卫把控制命令从数据流拎出(第18章,D·指令=数据);子代理在独立 context+terminal 跑(第13章),最小权限叠加隔离;profile 隔离防跨实例污染(第20章);Curator 只动 created_by:agent 技能(第10章,防技能中毒);审批 /approve 经网关旁路(第18章)。
- ② 数据流时序:命令 → detect_dangerous_command → 危险则审批(HARDLINE 锁死);派子代理 → 剥离 DELEGATE_BLOCKED_TOOLS+独立 context(第13章);消息进来 → 网关守卫把控制命令从数据分离(第18章);依赖全程 pin。
- ③ 关键点:纵深防御,每层独立单层失守有下一层。核心威胁是注入(模型分不清恶意数据与指令),安全绝不靠模型判断:危险命令正则黑名单、控制命令网关分离、权限代码剥离、依赖版本钉死。

## 模板结构
lead → analogy(银行金库多层安保) → macro(纵深防御) → 主体(HARDLINE+detect codefile + DELEGATE_BLOCKED_TOOLS codefile + pyproject pin codefile) → vflow → collab → design(回指 D+G) → key。

## quiz 考点
- 危险命令的安全决策靠模型判断还是靠代码(靠确定性代码:正则黑名单 detect_dangerous_command;不问模型这条命令危不危险——模型会被注入/幻觉骗;HARDLINE 红线连 yolo 都拦)。
- 派给子代理为什么先剥离一批工具(最小权限:不让递归派生/打扰用户/写共享记忆/跨平台发消息;把爆炸半径关进边缘)。
- Hermes 为什么把依赖全 pin 死(供应链安全:litellm 被投毒的教训;不信任任何会自动升级到恶意新版本的东西)。

## 验收
0 error；3 codefile 逐字真实(HARDLINE 正则/DELEGATE_BLOCKED_TOOLS/pyproject pin;fork bomb 的 `&` 写 `&amp;`,`>=`/`<` 写 `&gt;=`/`&lt;`;docstring `"""` 写 `&quot;`);纵深防御/注入隔离/最小权限/供应链讲清;双语镜像;回指 D+G;中文 ≥1500(达标)。
