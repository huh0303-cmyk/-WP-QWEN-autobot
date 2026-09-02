"""Require the actual final headline/body to pass Gemini and GPT checks."""
import re
from three_model_consensus import three_model_consensus
from automation_hub.editorial_language_policy import body_cliches, title_cliches

TITLE_RULE = """
Write a natural, specific headline grounded in the article's actual content.
Give the intended reader a concrete reason to read: a decision, question, or useful answer.
Never append random keyword templates, stack Practical Guide/Q&A/Step by Step,
or invent counts, savings, year-specific changes, interviews, or firsthand experience.
No 'Answers From the Field' or 'From Someone Who's Been There'.
Newsrooms require factual news headlines, not blog-guide hooks.
The word Unlock and every Unlock/Unlocking title formula are forbidden.
"""

def require_editorial_approval(*, title, content, meta, keyword, gemini_generate):
    if (not title.strip()
            or title_cliches(title)
            or re.search(r"answers from the field|from someone who.s been there|practical guide\s+q\s*&\s*a", title, re.I)):
        raise ValueError("TITLE_QUALITY_FAIL: unsupported experience or stacked template headline")
    if body_cliches(content):
        raise ValueError("REWRITE_REQUIRED: mass-produced AI body phrasing detected")
    result = three_model_consensus(title=title, content=content, meta=meta, keyword=keyword,
                                   gemini_generate=gemini_generate)
    checks = result.get("checks", {})
    if set(checks) != {"gemini", "gpt"} or not all(v.get("ok") is True for v in checks.values()):
        raise ValueError("CONSENSUS_FAILED: " + str(checks))
    return result
