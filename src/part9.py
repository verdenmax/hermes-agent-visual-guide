LESSON_27 = {
    "zh": r"""
<p class="lead">模型不是一个端点,而是一个需要<strong>调度</strong>的资源池——多把 API key 要轮换与熔断、不同的副任务要路由到不同模型、每个模型的上下文窗口要先<strong>算出来</strong>才能决定何时压缩。</p>
""",
    "en": r"""
<p class="lead">A model isn't an endpoint — it's a resource pool that needs <strong>scheduling</strong>: multiple API keys to rotate and trip, side tasks routed to different models, and each model's context window that must be <strong>computed</strong> before deciding when to compress.</p>
""",
}

LESSON_28 = {
    "zh": r"""
<p class="lead">一个跑了几十轮、还开着后台进程、正在改文件的 agent,要怎么<strong>安全地急停、可靠地知道后台干完没、原子地落盘</strong>?这一章拆开 Hermes 在运行时最容易出正确性 bug 的三套机制。</p>
""",
    "en": r"""
<p class="lead">An agent that has run dozens of turns, still has background processes open, and is mid-edit on a file — how does it <strong>stop safely, reliably know when background work finishes, and persist atomically</strong>? This chapter opens up the three runtime mechanisms most prone to correctness bugs.</p>
""",
}
