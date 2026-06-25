# ch16 Spec — 终端后端：环境可移植 + serverless 省钱

## 目标
讲清 terminal 工具如何用统一抽象支持多执行后端(local/docker/ssh/singularity/modal/daytona):BaseEnvironment ABC + 工厂按 TERMINAL_ENV 分派 + 六后端子类。环境可移植(同一 agent 跑遍各环境)、serverless 省钱。呼应窄腰(核心只认一个 terminal,后端差异在边缘)。

## 🎯 章末设计取舍
- 主线：**统一 terminal 抽象 + 多后端 = 环境可移植 + serverless 省钱;后端差异在边缘(窄腰)**。
- 回指：`G·运维`(agent 要在各种环境干活:本地/容器/远程/serverless;统一抽象让同一 agent 无改动跑遍,serverless 按需启停省钱)。

## 真实锚点（已 view 核对;explore 采集 + 抽查）
1. **后端抽象** — `tools/environments/__init__.py:1-9`(6后端 local/Docker/SSH/Singularity/Modal/Daytona 共享 BaseEnvironment ABC,工厂按 TERMINAL_ENV 选);`tools/environments/base.py:288-294` `class BaseEnvironment(ABC)` docstring "Subclasses implement _run_bash() and cleanup(). The base class provides execute() with session snapshot sourcing, CWD tracking, interrupt handling, and timeout enforcement";`@abstractmethod _run_bash`/`cleanup` :327-345;execute() 统一入口 :829。
2. **后端类导入** — `tools/terminal_tool.py:825-831`:`from tools.environments.local import LocalEnvironment as _LocalEnvironment` 等 6 个(local/singularity/ssh/docker/modal/managed_modal)。
3. **后端选择** — TERMINAL_ENV 默认 local(`tools/terminal_tool.py:569` / `skills_tool.py:424`);工厂 `_create_environment` :1225-1372(`if env_type=="local": LocalEnvironment(cwd,timeout)` elif docker/singularity/modal/daytona/ssh)。cwd 来自 terminal.cwd 配置。
4. **local 后端** — `tools/environments/local.py:572` `class LocalEnvironment(BaseEnvironment)`(subprocess+进程组隔离)。
5. **serverless** — Modal 有 direct + Nous-managed(terminal.modal_mode);ManagedModalEnvironment。按需启停省钱。
6. **background + notify** — terminal(background=True, notify_on_complete=True) gateway watcher 检测完成触发新 turn(AGENTS.md「Background Process Notifications」)。

## 🧩 协作机制框（三段）
- ① 组件清单:BaseEnvironment ABC(统一接口+execute()通用流程) + 六后端子类(各实现 _run_bash/cleanup) + _create_environment 工厂(按 TERMINAL_ENV 分派)。跨章节:terminal 是核心工具(第8章),六后端差异关进边缘子类=窄腰(第4章);子代理委派拿独立 terminal session(第13章上下文隔离);background+notify 的"后台完成→新turn"同委派完成队列(第13章)维持严格交替不破缓存。
- ② 数据流时序:模型调 terminal→工厂按 TERMINAL_ENV 选后端→BaseEnvironment 子类 execute()(基类统一快照/CWD/中断/超时)→子类 _run_bash() 在该后端 spawn→返回统一 ProcessHandle→cleanup() 释放(serverless 用完即放)。
- ③ 关键点:同一 agent 跑遍各环境靠统一抽象+工厂分派,核心只认一个 terminal 工具与 BaseEnvironment 接口,六环境差异沉到边缘子类。加新后端=写一个子类+工厂加一支,核心零改动。

## 模板结构
lead → analogy(万能遥控器) → macro(统一抽象后端差异在边缘) → 主体(BaseEnvironment ABC codefile + 工厂 codefile + 后端类导入 codefile) → vflow → collab → design(回指 G) → key。

## quiz 考点
- 加一个新执行后端(如新 serverless 平台)要改核心循环吗(不要,写 BaseEnvironment 子类+工厂加一支 elif,核心零改动)。
- 六后端的共同契约是什么(BaseEnvironment ABC,子类只实现 _run_bash/cleanup,通用 execute() 基类提供)。
- serverless 后端怎么省钱(按需启动用完 cleanup 释放,不为偶发命令常驻付费)。

## 验收
0 error；3 codefile 逐字真实(简化标注,_run_bash 的 -> 写 -&gt;);统一抽象/工厂/可移植讲清;双语镜像;中文 ≥1500(接近,最后补)。
