"""Single source of truth: ordered map of output filename -> bilingual content.

Each value is a dict ``{"zh": html, "en": html}``. build.py and build_print.py
both import this so the chapter set stays in sync with shell.PAGES. Add a
chapter by (1) appending it to shell.PAGES and (2) mapping it here.
"""
import part1

CONTENT = {
    "01-what-is-hermes.html": part1.LESSON_01,
    "02-llm-constraints-single-call.html": part1.LESSON_02,
    "03-llm-constraints-autonomy.html": part1.LESSON_03,
    "04-project-map-narrow-waist.html": part1.LESSON_04,
}
