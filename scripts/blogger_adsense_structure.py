"""AdSense-approval-oriented article structure for Blogger posts (helpful-content / E-E-A-T style).
Rules are about structure and honesty only; they never ask the model to invent facts, sources or credentials."""
from __future__ import annotations
import re

YMYL = re.compile(r"health|medical|insurance|financ|tax|law|invest|crypto|real estate|visa|immigration|건강|의료|보험|세무|법|투자|부동산|지원금", re.I)

_RULES_TEMPLATE = """AdSense-ready structure (follow exactly, HTML only, no <h1>, no <html>/<body> tags):
1. Opening: 2-3 sentences that directly answer the reader's main question (answer first), no filler or hype.
2. {H_KEY} followed by a <ul> of 3-5 concrete points.
3. At least 5 more <h2> sections, each with real, specific, practical information; use <h3> where useful;
   include one <table> or one numbered how-to list and one actionable checklist.
4. {H_FAQ} with 3 genuine questions and short direct answers.
5. {H_VERIFY}: name the official institutions or primary sources the reader
   should verify with (e.g. a ministry, regulator or university by name). Do NOT invent URLs, statistics, quotes,
   dates, prices or credentials; if you are not sure of a number, describe it qualitatively or say it varies.
6. Original wording, no copied passages, no keyword stuffing, no clickbait, no promises of income or guaranteed results,
   no adult/violent/illegal/medical-claim content, no affiliate or advertising language.
7. For health, medical, finance, insurance, tax, legal, visa, investment or crypto topics add a short closing
   <p><em>...</em></p> note: informational only, not professional advice, consult a qualified professional (in the article language).
8. Never mention AI, models, prompts, or how the article was produced."""


def structure_issues(body: str, theme: str, language: str) -> list[str]:
    issues = []
    low = body.lower()
    if re.search(r"<h1[\s>]", low):
        issues.append("contains <h1>")
    if len(re.findall(r"<h2[\s>]", low)) < 6:
        issues.append("fewer than 6 <h2> sections")
    ko = language.lower().startswith("ko")
    if not re.search(r"<h2[^>]*>\s*(핵심 요약|key takeaways)", body, re.I):
        issues.append("missing key takeaways section")
    if not re.search(r"<h2[^>]*>\s*(자주 묻는 질문|frequently asked questions|faq)", body, re.I):
        issues.append("missing FAQ section")
    if not re.search(r"<h2[^>]*>\s*(확인할 사항|before you decide)", body, re.I):
        issues.append("missing verification/sources section")
    if not re.search(r"<(ul|ol|table)[\s>]", low):
        issues.append("no list or table")
    if re.search(r"https?://", body) is None and False:
        pass
    if YMYL.search(theme) and not re.search(r"<em>[^<]{20,}</em>", body):
        issues.append("YMYL topic missing disclaimer note")
    words = len(re.sub(r"<[^>]+>", " ", body).split()) if not ko else len(re.sub(r"<[^>]+>|\s", "", body))
    if (not ko and words < 800) or (ko and words < 1600):
        issues.append(f"too short ({words})")
    return issues


_HEADINGS = {
    "en": ("<h2>Key takeaways</h2>", "<h2>Frequently asked questions</h2>", "<h2>Before you decide</h2>"),
    "ko": ("<h2>핵심 요약</h2>", "<h2>자주 묻는 질문</h2>", "<h2>확인할 사항</h2>"),
}


def rules_for(language: str) -> str:
    """Language-specific rules so English prompts never contain Hangul (models copy it into the article)."""
    key = "ko" if str(language).lower().startswith("ko") else "en"
    k, f, v = _HEADINGS[key]
    return _RULES_TEMPLATE.replace("{H_KEY}", k).replace("{H_FAQ}", f).replace("{H_VERIFY}", v)


RULES = rules_for("en")
