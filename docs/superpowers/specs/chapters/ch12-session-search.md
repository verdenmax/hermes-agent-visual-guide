# ch12 Spec — 跨会话搜索：SessionDB + FTS5（零 LLM）

## 目标
讲清 Hermes 跨会话召回如何「零 LLM、零成本、不破缓存」：写入即索引（AFTER INSERT 触发器）、FTS5 MATCH+BM25+snippet 检索、CJK trigram 兜底、4 模式工具、原文 append 召回。诚实点：README "with LLM summarization" 已过时，PR#26419 移除 summary 路径。

## 🎯 章末设计取舍
- 主线：**零 LLM 直出 DB 原文 + append-only 召回**——既省成本又不破缓存。
- 回指：`B·无状态`(本地 FTS5 把全部历史变可检索外部记忆)、`A·中间遗失`(BM25 排序+锚点书签按需取回，非全塞)。

## 真实锚点（逐字 + 文件:行号；核心已 view 核对）
1. **FTS5 表 + 写入即索引触发器** — `hermes_state.py:611-633`：`CREATE VIRTUAL TABLE messages_fts USING fts5(content)`；`CREATE TRIGGER messages_fts_insert AFTER INSERT ON messages` → `INSERT INTO messages_fts(rowid, content) VALUES (new.id, COALESCE(new.content,'')||' '||COALESCE(new.tool_name,'')||' '||COALESCE(new.tool_calls,''))`。rowid=messages.id。
2. **search_messages MATCH+BM25+snippet** — `hermes_state.py:3532`(ORDER BY rank=BM25) / `:3535`(messages_fts MATCH ?) / `:3566`(snippet(messages_fts,0,'>>>','<<<','...',40))；trigram 表 `:3638`(CJK)。
3. **零 LLM 声明（诚实点）** — `tools/session_search_tool.py:21-29`："No LLM calls anywhere — every shape returns actual messages from the DB"；"History: PR #20238 seeded a fast/summary dual-mode split; ... no mode parameter, no summary LLM path"。README "with LLM summarization" 过时。
4. **4 模式** — `tools/session_search_tool.py`：`session_search`(:495) / `_discover`(:394 DISCOVERY) / `_scroll`(:270 SCROLL) / `_read_session`(:178 READ) / `_list_recent_sessions`(:227 BROWSE)。参数推断、无 mode 参数。
5.（正文/校验核实）**标题生成 fire-and-forget** — `agent/title_generator.py:158-196`：首轮后后台线程生成，不阻塞主响应。
6.（正文/校验核实）**CJK trigram 路由 + get_anchored_view 书签** — `hermes_state.py:3590-3717`(CJK)、`:2875`(get_anchored_view)。

## 🧩 协作机制框（三段）
- ① 组件清单：SessionDB FTS5 表+触发器(写入即索引) + search_messages(MATCH+BM25+snippet) + CJK trigram 路由 + session_search(4模式) + get_anchored_view(书签)。跨章节：搜索结果作为 tool 消息 append 不改前缀(第6章缓存 + 第8章工具结果 append-only)；跨会话召回对抗无状态(第2章 B)；标题生成走辅助模型链后台线程(主模型优先否则回退辅助 client，与第10章辅助模型隔离同源)。
- ② 数据流时序：消息 INSERT→触发器同步建 FTS5；session_search(query)→MATCH+BM25+snippet(CJK trigram 兜底)→get_anchored_view 锚点窗口+书签→原文 tool 消息 append→agent 自读。标题首轮后台 fire-and-forget。
- ③ 关键点：跨会话记忆不必用 LLM——本地 FTS5 写入即索引(零额外步骤)、检索零模型调用(零成本)、返回只 append tool 消息(不破缓存)。

## 模板结构
lead → analogy(图书馆卡片目录) → macro(写入即索引/原文召回/零LLM) → 主体(FTS5 触发器 codefile + search_messages SQL codefile + 零LLM声明 codefile) → 4模式+召回不破缓存正文 → vflow → collab → design(回指 B/A) → key。

## quiz 考点
- session_search 用不用 LLM 总结召回内容（不用，零 LLM 返回 DB 原文；README 过时）。
- 消息什么时候被索引（写入即索引，AFTER INSERT 触发器同步）。
- 召回结果为什么不破缓存（作为 tool 消息 append，不改 system prompt/历史）。

## 验收
0 error；3 codefile 逐字真实（简化标注，snippet 的 <<< 写 &lt;&lt;&lt;）；写入即索引/FTS5检索/零LLM 讲清；双语镜像；中文 ≥1500。
