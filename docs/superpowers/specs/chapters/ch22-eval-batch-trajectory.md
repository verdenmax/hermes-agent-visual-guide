# ch22 Spec — 评测 + 批量 + 轨迹：研究数据流水线 + 抗漂移评测

## 目标
讲清 Hermes 作为研究工具的三件事:① 批量并行跑 prompt(_process_batch_worker 多 worker)生成训练数据;② 把对话转成 JSONL 轨迹样本(conversations/tool_stats/metadata),并质量过滤(零推理样本丢弃);③ 评测/测试用行为不变量(invariant)而非数据快照(snapshot),抗模型/数据漂移(不写 change-detector tests)。同一个 AIAgent 核心既服务真实对话又产出研究数据。

## 🎯 章末设计取舍（双 badge G + F）
- 主线：**并行批量 + 完整轨迹 + 质量过滤 + 行为契约测试 = 可规模化的研究数据流水线 + 抗漂移评测**。
- `G·运维`：研究要规模——并行批量、JSONL 轨迹标准化、CI 在"模型每周变"下可维护。
- `F·误差累积`：评测量化 agent 多轮误差累积;轨迹质量门槛(需推理)剔除低质样本免喂坏训练;不变量测试防回归累积。

## 真实锚点（已 view 逐字核对）
1. **并行批量 worker** — `batch_runner.py:400-413` `def _process_batch_worker(args)` docstring "Worker function to process a single batch of prompts."；`batch_num, batch_data, output_dir, completed_prompts_set, config = args`。
2. **质量过滤 + JSONL 落盘** — `batch_runner.py:452-487`:`if result["success"] and result["trajectory"]:` → `if not reasoning.get("has_any_reasoning", True): ... continue`(丢弃零推理样本,454-460) → `trajectory_entry = {"prompt_index":..., "conversations": result["trajectory"], "metadata": result["metadata"], "tool_stats": tool_stats, "tool_error_counts":...}`(473-483) → `with open(batch_output_file, 'a', ...) as f: f.write(json.dumps(trajectory_entry, ensure_ascii=False) + "\n")`(486-487)。
3. **单次轨迹落盘** — `run_agent.py:371` `save_trajectories: bool = False`(AIAgent 参数,默认关);`:1716-1729` `def _save_trajectory(self, messages, user_query, completed)` docstring "Save conversation trajectory to JSONL file." → `if not self.save_trajectories: return` → `trajectory = self._convert_to_trajectory_format(...)` → `_save_trajectory_to_file(trajectory, self.model, completed)`;`run_agent.py:196` `from agent.trajectory import save_trajectory`。
4. **评测哲学(★)** — `AGENTS.md`「Don't write change-detector tests」段:Don't `assert "gemini-2.5-pro" in _PROVIDER_MODELS["gemini"]` / `assert DEFAULT_CONFIG["_config_version"] == 21` / `assert len(_PROVIDER_MODELS["huggingface"]) == 8`;Do `assert "gemini" in _PROVIDER_MODELS` / `assert len(...) >= 1` / `assert raw["_config_version"] == DEFAULT_CONFIG["_config_version"]` / `for m in _PROVIDER_MODELS["huggingface"]: assert m.lower() in DEFAULT_CONTEXT_LENGTHS_LOWER`。规则:"if the test reads like a snapshot of current data, delete it. If it reads like a contract about how two pieces of data must relate, keep it."
5. **轨迹元数据** — trajectory_entry 含 partial(无效工具调用停止)、api_calls、toolsets_used、tool_stats({tool:{count,success,failure}})。

## 🧩 协作机制框（三段）
- ① 组件清单:_process_batch_worker(并行批量) + _save_trajectory(轨迹落盘) + trajectory_entry(JSONL schema) + 不变量测试(评测哲学)。跨章节:批量跑的是 AIAgent 核心循环(第 7 章),轨迹里的 reasoning 来自那里;tool_stats 统计工具(第 8 章)调用;并行 worker 各自无状态独立(约束 B,第 2 章);轨迹落盘路径走 get_hermes_home() 按 profile 隔离(第 20 章)。
- ② 数据流时序:prompts 切批 → 多 _process_batch_worker 并行(各跑 AIAgent) → 质量过滤(零推理丢弃) → trajectory_entry 写 JSONL → 聚合 tool_stats;评测侧:不变量断言抗数据漂移。
- ③ 关键点:研究数据流水线 = 并行批量 + 完整轨迹 + 质量过滤;同一 agent 核心既服务真实对话又产出训练数据。评测纪律 = 锁行为不变量、不锁数据快照。

## 模板结构
lead → analogy(工厂质检流水线) → macro(数据流水线+抗漂移测试) → 主体(_process_batch_worker codefile + _save_trajectory codefile + change-detector 测试规约 codefile) → vflow → collab → design(回指 G+F) → key。
注:codefile3 标注来源为 `AGENTS.md · 测试规约` 而非源码文件(诚实标明是项目文档纪律,非某 .py)。

## quiz 考点
- 批量怎么规模化生成训练数据、又保证质量(多 worker 并行跑独立 prompt 无状态;零推理样本 continue 丢弃;每条样本一行 JSONL 带 tool_stats)。
- save_trajectories 默认开还是关(默认关,生产对话不留痕;研究时打开)。
- 为什么 `assert "gemini-2.5-pro" in models` 是坏测试、`assert len(models) >= 1` 是好测试(前者是数据快照,模型一发布就挂=change-detector;后者是行为不变量,数据怎么变都不破;抗模型漂移)。

## 验收
0 error；3 codefile 真实(batch/trajectory 逐字;codefile3 标 AGENTS.md 来源,Do/Don't 例子忠实 AGENTS.md;`>=` 写 `&gt;=`);批量/轨迹/质量过滤/不变量测试讲清;双语镜像;回指 G+F;中文 ≥1500(接近,最后补)。
