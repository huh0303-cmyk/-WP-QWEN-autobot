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
    return len(shared) >= 3 and len(" ".join(shared)) >= 15

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
