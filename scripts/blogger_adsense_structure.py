"""AdSense-approval-oriented article structure for Blogger posts (helpful-content / E-E-A-T style).
Rules are about structure and honesty only; they never ask the model to invent facts, sources or credentials."""
from __future__ import annotations
import re

# Official institutions whose HOMEPAGE (only) may be linked. Homepages are stable, so no invented/dead deep links.
_OFFICIAL = {
    "general": ["gov.kr", "korea.kr", "bokjiro.go.kr", "data.go.kr", "kostat.go.kr", "kosis.kr"],
    "health": ["kdca.go.kr", "mohw.go.kr", "mfds.go.kr", "nhis.or.kr", "hira.or.kr", "who.int", "cdc.gov", "nih.gov", "medlineplus.gov", "health.kdca.go.kr", "kosha.or.kr"],
    "finance": ["fss.or.kr", "fsc.go.kr", "bok.or.kr", "moef.go.kr", "nps.or.kr", "hf.go.kr", "fiu.go.kr", "kofia.or.kr"],
    "tax_law": ["nts.go.kr", "hometax.go.kr", "law.go.kr", "easylaw.go.kr", "moj.go.kr", "scourt.go.kr", "klac.or.kr"],
    "visa": ["hikorea.go.kr", "immigration.go.kr", "moj.go.kr", "visa.go.kr", "mofa.go.kr"],
    "jobs": ["moel.go.kr", "work.go.kr", "worknet.go.kr", "eps.go.kr", "hrdkorea.or.kr", "q-net.or.kr"],
    "education": ["moe.go.kr", "studyinkorea.go.kr", "niied.go.kr", "academyinfo.go.kr", "topik.go.kr", "kedi.re.kr"],
    "realestate": ["molit.go.kr", "reb.or.kr", "iros.go.kr", "lh.or.kr", "hf.go.kr"],
    "travel": ["visitkorea.or.kr", "knto.or.kr", "mcst.go.kr", "kocis.go.kr", "english.visitkorea.or.kr"],
    "insurance": ["fss.or.kr", "nhis.or.kr", "hira.or.kr", "kidi.or.kr", "klia.or.kr", "knia.or.kr"],
    "medtour": ["medicalkorea.or.kr", "khidi.or.kr", "mohw.go.kr", "visitkorea.or.kr"],
}
_THEME_KEYS = [
    (r"health|medical|wellness|beauty|skin|nutrition|pet|건강|의료|보건|영양|뷰티|스킨|팻|돌봄", "health"),
    (r"medical tour|의료관광", "medtour"),
    (r"insurance|보험", "insurance"),
    (r"financ|invest|crypto|stock|금융|투자|코인|주식", "finance"),
    (r"tax|law|legal|세무|세금|법", "tax_law"),
    (r"visa|immigration|비자|출입국", "visa"),
    (r"job|career|work|labor|취업|채용|근로", "jobs"),
    (r"school|study|education|university|유학|교육|학교|대학", "education"),
    (r"real estate|housing|부동산|주거", "realestate"),
    (r"travel|tour|trip|culture|k-pop|kpop|wedding|여행|문화", "travel"),
]


def official_domains(theme: str) -> list[str]:
    keys = ["general"] + [k for rx, k in _THEME_KEYS if re.search(rx, theme or "", re.I)]
    out: list[str] = []
    for k in keys:
        for d in _OFFICIAL[k]:
            if d not in out:
                out.append(d)
    return out


def _host(url: str) -> str:
    m = re.match(r"https?://([^/\s\"'<>#?]+)", url or "", re.I)
    return (m.group(1).lower() if m else "").removeprefix("www.")


def source_link_issues(body: str, theme: str) -> list[str]:
    """Official-source gate: >=2 distinct allow-listed institutions linked, homepage only; no other external links."""
    allowed = official_domains(theme)
    hrefs = re.findall(r'href=["\']?(https?://[^"\' >]+)', body, re.I)
    good, bad = set(), []
    for h in hrefs:
        host = _host(h)
        path = re.sub(r"^https?://[^/]+", "", h).split("?")[0].split("#")[0]
        if any(host == d or host.endswith("." + d) for d in allowed):
            if path not in ("", "/"):
                bad.append(h[:60] + " (homepage only)")
            else:
                good.add(host)
        else:
            bad.append(h[:60] + " (not an approved official source)")
    issues = []
    if len(good) < 2:
        issues.append(f"needs >=2 approved official-source links (homepage only), found {len(good)}")
    if bad:
        issues.append("disallowed links: " + "; ".join(bad[:3]))
    return issues


YMYL = re.compile(r"health|medical|insurance|financ|tax|law|invest|crypto|real estate|visa|immigration|건강|의료|보험|세무|법|투자|부동산|지원금", re.I)

_RULES_TEMPLATE = """AdSense-ready structure (follow exactly, HTML only, no <h1>, no <html>/<body> tags):
1. Opening: 2-3 sentences that directly answer the reader's main question (answer first), no filler or hype.
2. {H_KEY} followed by a <ul> of 3-5 concrete points.
3. At least 5 more <h2> sections, each with real, specific, practical information; use <h3> where useful;
   include one <table> or one numbered how-to list and one actionable checklist.
4. {H_FAQ} with 3 genuine questions and short direct answers.
5. {H_VERIFY}: a <ul> of 2-4 links to official institutions, chosen ONLY from this approved list and written as
   <a href="https://DOMAIN/" rel="noopener" target="_blank">institution name</a> (homepage only, never a deep link, never any other site):
   {SOURCES}
   Next to each link say in one line what the reader can verify there. End the section with "기준일: <current month and year 2026>" (English: "As of: <month> 2026").
   Do NOT invent statistics, quotes, dates, prices or credentials. Every number must be attributable to a named institution, otherwise describe it qualitatively or say it varies.
6. Original wording, no copied passages, no keyword stuffing, no clickbait, no promises of income or guaranteed results,
   no adult/violent/illegal/medical-claim content, no affiliate or advertising language.
7. For health, medical, finance, insurance, tax, legal, visa, investment or crypto topics add a short closing
   <p><em>...</em></p> note: informational only, not professional advice, consult a qualified professional (in the article language).
8. Never mention AI, models, prompts, or how the article was produced.
9. Depth over volume: give concrete, checkable specifics a reader cannot get from a generic summary (named programs, eligibility conditions,
   steps in order, common mistakes, what to prepare). No template-style titles ("...: 7가지", "...하면 됩니다"); the title must name the specific question the article answers.
10. Mention at least once, naturally, who the information is for and when it was last checked; never claim to be a doctor, lawyer, tax accountant or any real person."""


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
    issues += source_link_issues(body, theme)
    words = len(re.sub(r"<[^>]+>", " ", body).split()) if not ko else len(re.sub(r"<[^>]+>|\s", "", body))
    if (not ko and words < 800) or (ko and words < 1600):
        issues.append(f"too short ({words})")
    return issues


_HEADINGS = {
    "en": ("<h2>Key takeaways</h2>", "<h2>Frequently asked questions</h2>", "<h2>Before you decide</h2>"),
    "ko": ("<h2>핵심 요약</h2>", "<h2>자주 묻는 질문</h2>", "<h2>확인할 사항</h2>"),
}


def rules_for(language: str, theme: str = "") -> str:
    """Language-specific rules so English prompts never contain Hangul (models copy it into the article)."""
    key = "ko" if str(language).lower().startswith("ko") else "en"
    k, f, v = _HEADINGS[key]
    return (_RULES_TEMPLATE.replace("{H_KEY}", k).replace("{H_FAQ}", f).replace("{H_VERIFY}", v)
            .replace("{SOURCES}", ", ".join(official_domains(theme))))


RULES = rules_for("en")
