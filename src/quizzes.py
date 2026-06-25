"""Per-chapter bilingual self-test (自测题): design-insight multiple-choice + open prompts.

Schema per chapter::

    "NN-file.html": {
        "mcq": [
            {
                "q":   {"zh": "...", "en": "..."},
                "opts": [{"zh": "...", "en": "..."}, ...],
                "answer": 1,                      # 0-based index into opts (as written)
                "why": {"zh": "...", "en": "..."},
            },
        ],
        "open": [{"zh": "...", "en": "..."}],
    }

``render(fname, lang)`` turns it into HTML that build.py appends to the bottom of
each language's chapter body. Options are deterministically shuffled per question
(same permutation for zh and en, so the correct letter matches across languages).

Quiz text (q/opts/why) is raw HTML in a text context (like the chapter body):
write literal ``<``/``&`` as ``&lt;``/``&amp;`` (or wrap code in ``<code>``).
"""
import hashlib

_HEAD = {"zh": "🧪 自测 · 想一想为什么这么设计", "en": "🧪 Self-test - think about the design"}
_SEE = {"zh": "看答案与解析", "en": "Show answer &amp; explanation"}
_CLICK = {"zh": "点击展开", "en": "click to expand"}
_ANS = {"zh": "答案：", "en": "Answer: "}
_SEP = {"zh": "。", "en": ". "}
_OPEN = {
    "zh": "💭 发散思考（没有标准答案，动手或动脑想想）",
    "en": "💭 Open questions (no single right answer - just think or try)",
}


def _shuffle(opts, answer, seed):
    """Deterministically permute opts (stable across builds); return
    (new_opts, new_answer_index) so the correct option lands in a varied slot."""
    order = sorted(
        range(len(opts)),
        key=lambda i: hashlib.md5(f"{seed}:{i}".encode("utf-8")).hexdigest(),
    )
    return [opts[i] for i in order], order.index(answer)


QUIZZES = {
    "01-what-is-hermes.html": {
        "mcq": [
            {
                "q": {
                    "zh": "Hermes 自称“自我进化”的 agent。这个“进化”最核心指的是什么？",
                    "en": "Hermes calls itself a self-improving agent. What does that mainly refer to?",
                },
                "opts": [
                    {"zh": "模型权重在使用中被在线微调", "en": "The model weights are fine-tuned online during use"},
                    {
                        "zh": "agent 把经验沉淀成可复用的技能与记忆，跨会话越用越好——模型本身不变",
                        "en": "It distills experience into reusable skills & memory across sessions; the model itself stays fixed",
                    },
                    {"zh": "它会自动升级到更强的模型", "en": "It auto-upgrades to a stronger model"},
                    {"zh": "它能改写自己的源代码", "en": "It rewrites its own source code"},
                ],
                "answer": 1,
                "why": {
                    "zh": "进化发生在模型“之外”：用 nudge 驱动 agent 把经验写成技能（怎么做）与记忆（是什么），靠 curator/搜索维护与召回。底层模型是无状态、固定的。",
                    "en": "Evolution happens *outside* the model: nudges drive the agent to save skills (how-to) and memory (facts), maintained/recalled by the curator and search. The base model is stateless and fixed.",
                },
            },
        ],
        "open": [
            {
                "zh": "如果模型每次调用都“失忆”，那么一个 agent 要“越用越聪明”，状态必须存在哪里？Hermes 给了哪几种答案？",
                "en": "If the model forgets between calls, where must an agent's growing state live? Which answers does Hermes give?",
            },
        ],
    },
    "02-llm-constraints-single-call.html": {
        "mcq": [
            {
                "q": {"zh": "“把最关键的指令放在长上下文正中间”——这个做法的主要问题是？",
                      "en": "“Put the most critical instruction right in the middle of a long context” — what's mainly wrong with that?"},
                "opts": [
                    {"zh": "中间太显眼，会被过度强调", "en": "The middle is too prominent and gets over-weighted"},
                    {"zh": "模型对中间的注意力最弱，关键指令容易“看不见”", "en": "The model attends least to the middle, so the key instruction is easily “unseen”"},
                    {"zh": "中间位置会增加 token 成本", "en": "The middle position increases token cost"},
                    {"zh": "没有问题，位置不影响效果", "en": "Nothing — position doesn't matter"},
                ],
                "answer": 1,
                "why": {"zh": "“中间遗失”：注意力两端强、中间弱。关键指令应放头尾，最相关的检索片段放边缘。",
                        "en": "“Lost in the middle”: attention is strong at both ends, weak in the middle. Put key instructions at head/tail and the most relevant snippets at the edges."},
            },
            {
                "q": {"zh": "为什么 Hermes 把“精确算术 / 数字符”交给工具，而不让模型自己算？",
                      "en": "Why does Hermes hand exact arithmetic / character-counting to tools instead of letting the model do it?"},
                "opts": [
                    {"zh": "模型按 token（词块）看世界，对单字符与精确数字天生不可靠", "en": "The model sees the world in tokens (chunks), so it's inherently unreliable at single chars and exact numbers"},
                    {"zh": "工具算得更快", "en": "Tools are simply faster"},
                    {"zh": "为了省 token", "en": "To save tokens"},
                    {"zh": "模型完全不会算术", "en": "The model can't do any arithmetic at all"},
                ],
                "answer": 0,
                "why": {"zh": "分词让“strawberry 有几个 r”这类字符 / 计数 / 算术不可靠——交给 execute_code / 计算器（第 8 章）。",
                        "en": "Tokenization makes char/count/math (“how many r in strawberry”) unreliable — hand them to execute_code / a calculator (ch.8)."},
            },
        ],
        "open": [
            {"zh": "“无状态”意味着两次调用之间模型零记忆。把它和“纯函数”联系起来：一个 agent 要有“记忆”，状态应该放在函数的哪一侧？",
             "en": "“Stateless” means zero memory between calls. Relate it to a “pure function”: for an agent to have “memory,” which side of the function should hold state?"},
        ],
    },
}


def render(fname, lang):
    """Return the self-test HTML block for ``fname`` in ``lang`` ('' if none)."""
    data = QUIZZES.get(fname)
    if not data or not (data.get("mcq") or data.get("open")):
        return ""
    out = ['<div class="selftest">', f'<h2>{_HEAD[lang]}</h2>']
    for i, item in enumerate(data.get("mcq", []), 1):
        shuffled, ans = _shuffle(item["opts"], item["answer"], f"{fname}:{i}")
        opts = "\n".join(f"    <li>{o[lang]}</li>" for o in shuffled)
        letter = chr(65 + ans)
        out.append(
            f'<div class="quiz">\n'
            f'  <div class="qn">{i}. {item["q"][lang]}</div>\n'
            f'  <ol class="opts">\n{opts}\n  </ol>\n'
            f'  <details class="accordion">\n'
            f'    <summary>{_SEE[lang]} <span class="hint">{_CLICK[lang]}</span></summary>\n'
            f'    <div class="acc-body"><div class="qa"><div class="a">'
            f'<strong>{_ANS[lang]}{letter}</strong>{_SEP[lang]}{item["why"][lang]}'
            f"</div></div></div>\n"
            f"  </details>\n"
            f"</div>"
        )
    opens = data.get("open", [])
    if opens:
        lis = "\n".join(f"    <li>{o[lang]}</li>" for o in opens)
        out.append(
            '<div class="card spark">\n'
            f'  <div class="tag">{_OPEN[lang]}</div>\n'
            f"  <ul>\n{lis}\n  </ul>\n"
            "</div>"
        )
    out.append("</div>")
    return "\n".join(out)


def _validate():
    """Fail fast on authoring mistakes in QUIZZES (clear message names the chapter)."""
    for fname, data in QUIZZES.items():
        for qi, item in enumerate(data.get("mcq", []), 1):
            opts = item["opts"]
            if not (0 <= item["answer"] < len(opts)):
                raise ValueError(
                    f"quizzes[{fname!r}] Q{qi}: answer {item['answer']} out of range 0..{len(opts) - 1}"
                )
            for o in opts:
                if not ({"zh", "en"} <= o.keys()):
                    raise ValueError(f"quizzes[{fname!r}] Q{qi}: an option is missing zh/en")
            if not ({"zh", "en"} <= item["q"].keys() and {"zh", "en"} <= item["why"].keys()):
                raise ValueError(f"quizzes[{fname!r}] Q{qi}: q/why missing zh/en")
        for oi, o in enumerate(data.get("open", []), 1):
            if not ({"zh", "en"} <= o.keys()):
                raise ValueError(f"quizzes[{fname!r}] open{oi}: missing zh/en")


_validate()
