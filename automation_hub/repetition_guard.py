"""Editorial repetition checks shared by publishing platforms."""
import html
import re
from difflib import SequenceMatcher
from bs4 import BeautifulSoup

RULE = """Use an article-specific headline and opening grounded in the supplied facts.
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

def repetition_issues(title, body, history):
    lead = opening(clean_opening(title, body)).casefold()
    issues = []
    for old in history:
        old_title = old.get('title', '')
        if isinstance(old_title, dict): old_title = old_title.get('rendered', '')
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
