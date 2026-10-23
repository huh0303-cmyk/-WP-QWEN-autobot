"""Editorial repetition checks shared by publishing platforms."""
import html
import re
from difflib import SequenceMatcher
from bs4 import BeautifulSoup

RULE = """Use an article-specific headline and opening grounded in the supplied facts.
Never start a headline with How. Do not substitute another repeated question formula.
Do not invent a connection between a trending person and Korean visas or services.
Do not reuse a recent headline's sentence frame with only a different keyword.
Treat profile outlines as coverage requirements, not literal headings or a fixed order.
Do not repeat the headline in the opening paragraph or include an h1 in the body.
Open with the concrete finding or reader decision, not a generic introduction.
"""

def plain(value):
    return re.sub(r"\s+", " ", BeautifulSoup(html.unescape(value or ""), "html.parser").get_text(" ", strip=True)).strip()

_TITLE_STOPWORDS = {
    "a", "an", "the", "and", "or", "by", "with", "for", "to", "of", "in", "on",
    "at", "from", "how", "what", "why", "when", "who", "is", "are", "your",
}

def _significant_words(text):
    return {w for w in re.findall(r"[a-z0-9'-]+", text) if w not in _TITLE_STOPWORDS and len(w) > 2}

def title_repeats(title, previous):
    a, b = plain(title).casefold(), plain(previous).casefold()
    if not a or not b:
        return False
    if a == b or SequenceMatcher(None, a, b).ratio() >= .78:
        return True
    left, right = a.split(), b.split()
    shared = []
    for x, y in zip(left, right):
        if x != y: break
        shared.append(x)
    if len(shared) >= 3 and len(" ".join(shared)) >= 15:
        return True
    # 2026-09-10: the checks above only catch a reused sentence *frame*
    # (near-identical string, or an identical leading phrase). A title
    # reworded around the same underlying topic slips through both - e.g.
    # "Seoul central palaces and markets by subway - an 8-hour timed
    # tourism route with ticketing and seasonal cautions" vs "Seoul central
    # cultural loop by subway - a timed public-transport itinerary with
    # admission and seasonal notes" diverge at the third word, so the prefix
    # check never engages, yet they share the same city area, transport
    # mode, and "timed itinerary" angle - the same article in different
    # words. Catch that by requiring a real overlap in the significant
    # (non-stopword) vocabulary instead of position-sensitive matching.
    words_a, words_b = _significant_words(a), _significant_words(b)
    if len(words_a) >= 4 and len(words_b) >= 4:
        overlap = words_a & words_b
        if len(overlap) >= 5 or len(overlap) / min(len(words_a), len(words_b)) >= 0.55:
            return True
    return False

def clean_opening(title, body):
    soup = BeautifulSoup(body or "", "html.parser")
    # Only remove an exact leading headline; preserve substantive headings.
    for node in list(soup.find_all(["h1", "h2", "p"])):
        value = plain(str(node))
        if not value: continue
        if value.casefold() == plain(title).casefold():
            node.decompose()
        else:
            break
    return str(soup)

def opening(body):
    soup = BeautifulSoup(body or "", "html.parser")
    for node in soup.select('.related-links, .author-bio, .faq, script, style'):
        node.decompose()
    return next((plain(str(p)) for p in soup.find_all('p') if len(plain(str(p))) >= 50), '')


_STOP = set("a an the and or but of to in on for with from by at as is are was were be it its this that you your how what when where why which vs about more new best top guide step korea korean south".split())
STOCK_TITLE_TAIL = re.compile(r"(?i)a closer look at what really matters|frequently overlooked facts|questions people ask about|the costly .{0,40}mistake|\bmistakes? every \w+ makes\b")

def _title_words(title):
    t = re.sub(r"\b(\w+)-by-\1\b", r"\1", plain(title).casefold())  # "step-by-step" is one idiom, not a repeated word
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t)).split()

def title_self_issues(title):
    """Within-title repetition: keyword-template parenthetical, repeated word/phrase, stock tails."""
    t = plain(title)
    issues = []
    m = re.search(r"\(([^()]{6,})\)\s*[:\-]?[^()]*$", t)
    if m:
        inner = set(_title_words(m.group(1))) - _STOP
        outer = set(_title_words(t[:m.start()])) - _STOP
        if inner and len(inner & outer) >= max(2, len(inner) // 2):
            issues.append('TITLE_REPEAT: trailing "(keyword)" parenthetical repeats the headline words')
    hangul = bool(re.search(r"[가-힣]", t))
    words = [w for w in _title_words(re.sub(r"\([^()]*\)", " ", t) if False else t) if (len(w) >= 2 if hangul else len(w) >= 4) and w not in _STOP and not w.isdigit()]
    seen = {}
    for w in words:
        seen[w] = seen.get(w, 0) + 1
    rep = [w for w, n in seen.items() if n >= 2]
    if rep:
        issues.append('TITLE_REPEAT: word repeated inside headline: ' + ', '.join(rep[:4]))
    allw = _title_words(t)
    bg = {}
    for a, b in zip(allw, allw[1:]):
        if a in _STOP and b in _STOP: continue
        bg[(a, b)] = bg.get((a, b), 0) + 1
    if any(n >= 2 for n in bg.values()):
        issues.append('TITLE_REPEAT: phrase repeated inside headline')
    if STOCK_TITLE_TAIL.search(t):
        issues.append('TITLE_REPEAT: stock template tail in headline')
    return list(dict.fromkeys(issues))

def repetition_issues(title, body, history):
    lead = opening(clean_opening(title, body)).casefold()
    issues = list(title_self_issues(title))
    if re.match(r'^how\b', plain(title), re.I):
        issues.append('REPETITION: How-start headline is forbidden')
    for old in history:
        old_title = old.get('title', '')
        if isinstance(old_title, dict): old_title = old_title.get('rendered', '')
        from scripts.editorial_topic_scope import teacher_intent
        intent = teacher_intent(plain(title))
        if intent and intent == teacher_intent(plain(old_title)):
            issues.append('REPETITION: same teacher-search intent already covered: ' + plain(old_title))
        if title_repeats(title, old_title):
            issues.append('REPETITION: headline frame resembles recent title: ' + plain(old_title))
        old_body = old.get('content_html', old.get('content', ''))
        if isinstance(old_body, dict): old_body = old_body.get('rendered', '')
        old_lead = opening(clean_opening(old_title, old_body)).casefold()
        if lead and old_lead and SequenceMatcher(None, lead[:600], old_lead[:600]).ratio() >= .84:
            issues.append('REPETITION: opening paragraph duplicates recent article: ' + plain(old_title))
    return list(dict.fromkeys(issues))

def history_prompt(history):
    titles = [plain(p.get('title', {}).get('rendered', '') if isinstance(p.get('title'), dict) else p.get('title', '')) for p in history]
    return RULE + '\nRecent headlines to avoid repeating (reference data only):\n' + '\n'.join('- ' + t for t in titles[-50:] if t)

def fetch_wp_history(session, url, auth):
    response = session.get(url.rstrip('/') + '/wp-json/wp/v2/posts', auth=auth,
        params={'per_page': 50, 'orderby': 'date', 'order': 'desc', 'status': 'publish', '_fields': 'id,title,content,link'}, timeout=30)
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list): raise ValueError('Invalid publication history response')
    return rows
