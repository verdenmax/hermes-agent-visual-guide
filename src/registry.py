"""Single source of truth: ordered map of output filename -> bilingual content.

Each value is a dict ``{"zh": html, "en": html}``. build.py and build_print.py
both import this so the chapter set stays in sync with shell.PAGES. Add a
chapter by (1) appending it to shell.PAGES and (2) mapping it here.
"""
import part1
import part2
import part3
import part4
import part5
import part6
import part7

CONTENT = {
    "01-what-is-hermes.html": part1.LESSON_01,
    "02-llm-constraints-single-call.html": part1.LESSON_02,
    "03-llm-constraints-autonomy.html": part1.LESSON_03,
    "04-project-map-narrow-waist.html": part1.LESSON_04,
    "05-conversation-lifecycle.html": part1.LESSON_05,
    "06-system-prompt-caching.html": part2.LESSON_06,
    "07-message-flow-providers.html": part2.LESSON_07,
    "08-tool-system.html": part2.LESSON_08,
    "09-learning-nudge-skills.html": part3.LESSON_09,
    "10-curator.html": part3.LESSON_10,
    "11-memory.html": part3.LESSON_11,
    "12-session-search.html": part3.LESSON_12,
    "13-delegation.html": part4.LESSON_13,
    "14-review-verification.html": part4.LESSON_14,
    "15-context-compression.html": part4.LESSON_15,
    "16-terminal-backends.html": part4.LESSON_16,
    "17-gateway-adapters.html": part5.LESSON_17,
    "18-gateway-guards.html": part5.LESSON_18,
    "19-tui-desktop.html": part5.LESSON_19,
    "20-config-profiles.html": part5.LESSON_20,
    "21-cron-kanban.html": part6.LESSON_21,
    "22-eval-batch-trajectory.html": part6.LESSON_22,
    "23-plugins-skills-mcp.html": part6.LESSON_23,
    "24-security.html": part7.LESSON_24,
}
