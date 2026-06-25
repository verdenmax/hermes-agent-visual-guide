# ch10 Spec — Curator：技能生命周期园丁 / Curator: skill-lifecycle gardener

## 目标
讲清 Curator 如何防止「自我进化」失控：后台 inactivity 触发、确定性状态机 active→stale→archived、永不删只归档（可恢复）、pinned 豁免、forked 辅助模型独立 session 不碰主缓存、LLM 合并 opt-in。串「数据安全 + 辅助模型隔离」。

## 🎯 章末设计取舍
- 主线：**自我维护但永不破坏**（数据安全 + 辅助模型隔离）。
- 回指：`F·误差累积`（技能库无约束膨胀 → 确定性状态机持续修剪）、`G·运维`（inactivity 触发 / 状态持久化 / 可恢复归档 / 备份回滚）；并服务缓存神圣（第6章，fork 独立 cache）。

## 真实锚点（逐字 + 文件:行号；已 view 核对）
1. **四条不变量 docstring** — `agent/curator.py:15-19`：Only touches agent-created / Never auto-deletes — only archives. Archive is recoverable / Pinned skills bypass all auto-transitions / Uses the auxiliary client; never touches the main session's prompt cache。
2. **inactivity-triggered** — `agent/curator.py:3-7`（"runs inactivity-triggered (no cron daemon)... maybe_run_curator() spawns a forked AIAgent"）；门控 `maybe_run_curator` ~`:1898-1916`（agent 空闲 + 距上次超过 interval_hours）。
3. **确定性状态机** — `agent/curator.py:276-331` `apply_automatic_transitions`：pinned `continue`（:300-301）；anchor=last_activity→created_at→now（:310-313）；`anchor <= archive_cutoff → archive_skill`（:319-322）；`anchor <= stale_cutoff & ACTIVE → STALE`（:323-325）；`anchor > stale_cutoff & STALE → ACTIVE` 复活（:326-329）。零 LLM。
4. **forked AIAgent 隔离** — `agent/curator.py:1826-1845`：`AIAgent(..., max_iterations=9999, quiet_mode=True, platform="curator", skip_context_files=True, skip_memory=True)`；`_memory_nudge_interval=0` / `_skill_nudge_interval=0`（防递归）；stdout/stderr→/dev/null（:1847-1855）。
5. **consolidate opt-in** — `DEFAULT_CONSOLIDATE=False`（curator.py ~:64）；LLM umbrella 合并默认关、烧 aux token，确定性降级始终在跑。executor/校验须核对默认值。
6. **辅助模型** — `agent/auxiliary_client.py`：curator 走独立 aux 槽（`auxiliary.curator`），与主 runtime 隔离。

## 🧩 协作机制框（三段）
- ① 组件清单：maybe_run_curator（inactivity 门控）+ apply_automatic_transitions（状态机）+ forked review AIAgent（platform=curator 隔离）+ archive/restore（可恢复）。跨章节：curator 只园丁 background review fork 创建的 agent-skill（第9章产权门控）；forked agent 独立 prompt cache 不碰主对话（第6章 + 第9章 fork 同源）；降级靠 skill_usage 遥测时间戳（第9章 use/view/patch 喂回）；辅助模型独立 aux 槽。
- ② 数据流时序：agent 空闲+超 interval_hours → maybe_run_curator → apply_automatic_transitions（读 skill_usage，确定性降级，pinned 跳过）→ 持久化 .curator_state →（仅 opt-in consolidate 开）fork 辅助 review agent umbrella 合并 → 主对话/缓存零改动，最坏只搬进可恢复 .archive/。
- ③ 关键点：自我进化需自我维护兜底（防技能库膨胀=误差累积），但维护必须零破坏：永不删/不碰主缓存/pinned 豁免/合并 opt-in。

## 模板结构
lead → analogy（图书馆管理员/可恢复暂存）→ macro（自我维护但永不破坏）→ 主体（不变量 docstring codefile + 状态机 codefile + forked AIAgent codefile）→ collab → design（回指 F/G + 缓存）→ key。

## quiz 考点
- curator 最激进的动作是什么（归档，永不删除；可恢复）。
- 状态机为什么零 LLM、靠什么降级（活动时间戳；确定性）。
- forked review agent 为何 platform="curator" + nudge=0（独立缓存隔离 + 防递归）。

## 验收
0 error；3 codefile 逐字真实（简化标注）；四不变量/状态机/辅助模型隔离讲清；双语镜像；中文 ≥1500 CJK（不足则补）。
