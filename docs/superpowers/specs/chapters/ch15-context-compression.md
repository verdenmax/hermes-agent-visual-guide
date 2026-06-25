# ch15 Spec — 上下文压缩：缓存铁律的唯一例外;对抗上下文腐烂

## 目标
讲清第6章「缓存唯一例外」的那个例外。逼近窗口才触发(50%+防抖动)、保头保尾摘要中段(辅助模型结构化模板)、压缩后重建 system prompt(缓存唯一例外实证)、顺带刷新记忆快照、时序锚定/头部衰减对抗 context rot。

## 🎯 章末设计取舍
- 主线：**压缩是缓存铁律的唯一例外——用一次缓存重置换回继续对话的空间;万不得已才触发**。
- 回指：`A·中间遗失`(上下文窗口有限,长对话关键信息被挤到中间→摘要腾空间)、`F·误差累积`(上下文腐烂:旧待办重复执行/早期消息化石化→时序锚定+头部衰减)。

## 真实锚点（核心已亲验;校验须 view 核对）
1. **触发** — `agent/context_compressor.py:786-789` 默认 `threshold_percent=0.50` / `protect_first_n=3` / `protect_last_n=20` / `summary_target_ratio=0.20`;degenerate `_MIN_CTX_TRIGGER_RATIO=0.85` :722;`should_compress` :964-984(防抖动:`_ineffective_compression_count >= 2` 跳过,连续2次省<10%)。
2. **★缓存唯一例外** — `agent/conversation_compression.py:515-517`:`agent._invalidate_system_prompt()` → `new_system_prompt = agent._build_system_prompt(system_message)` → `agent._cached_system_prompt = new_system_prompt`。对照平时稳定 `turn_context.py:276-279`。
3. **invalidate + reload memory** — `agent/system_prompt.py:496-504` "Called after context compression events. Also reloads memory from disk" → `_cached_system_prompt=None; memory_store.load_from_disk()`。
4. **机制** — 模块 docstring :1-5(辅助模型摘要 middle 保护 head/tail);`call_llm(task="compression")` :1646-1668;结构化模板 :1559-1606(## Goal / Constraints & Preferences / Completed Actions / Key Decisions / Resolved Questions / Critical Context)。
5. **对抗 context rot** — 算法 :2375-2381(剪枝→保头→tail边界→摘要→迭代);`_effective_protect_first_n` :2024-2039(压缩≥1次后头部衰减到0防化石化);时序锚定 :1521-1530(待办改过去式防重复执行);剪枝旧tool :994-1001;摘要是中段消息不在缓存前缀 :1488-1491;压缩锁 hermes_state.py:1440-1462 防并发。

## 🧩 协作机制框（三段）
- ① 组件清单:should_compress(触发+防抖动) + 剪枝/保头保尾/摘要(辅助模型) + _invalidate_system_prompt+重建(缓存唯一例外) + 时序锚定/头部衰减 + 压缩锁。跨章节:平时 _cached_system_prompt 逐字节稳定(第6章),压缩是唯一重建时机;压缩边界顺带 reload 记忆快照(第11章 load_from_disk);摘要走辅助模型(第10章 auxiliary.compression);压缩(腾空间) vs 委派(隔离)对抗上下文有限两条路(第13章)。
- ② 数据流时序:逼近→should_compress(防抖动)→剪枝旧tool→保头(衰减)保尾(token预算)+辅助模型摘要中段(结构化模板+时序锚定)→_invalidate_system_prompt清缓存→_build_system_prompt重建(顺带reload记忆)→_cached_system_prompt=new→继续。
- ③ 关键点:压缩必然作废前缀缓存,所以"逼近+防抖动才触发"(万不得已);换来把会腐烂会遗失的长历史结构化压缩成高信号要点。一次缓存重置换继续空间。

## 模板结构
lead → analogy(会议纪要压要点) → macro(用一次缓存重置换空间) → 主体(should_compress触发 codefile + 缓存唯一例外515-517 codefile + 结构化摘要模板 codefile) → vflow → collab → design(回指 A/F) → key。

## quiz 考点
- 为什么压缩是缓存铁律的唯一例外(压缩重写历史前缀→必须_invalidate_system_prompt清缓存+重建)。
- 压缩为什么"万不得已才触发"(每次作废缓存,代价昂贵;50%阈值+防抖动)。
- 压缩如何对抗上下文腐烂(时序锚定待办改过去式防重复执行/头部衰减防化石化)。

## 验收
0 error；3 codefile 逐字真实(简化标注,should_compress的<写&lt;);缓存唯一例外515-517讲清;双语镜像;中文 ≥1500。
