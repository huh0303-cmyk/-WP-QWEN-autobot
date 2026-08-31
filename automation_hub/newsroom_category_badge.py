"""Small accessible category labels, inspired by KoreaNews365's news cards."""
import html
import re

PALETTE = [
    (("military", "군사", "국방"), "#334155"),
    (("politic", "정치"), "#6d28d9"),
    (("econom", "business", "경제"), "#1151d3"),
    (("finance", "금융"), "#047857"),
    (("society", "사회"), "#0369a1"),
    (("culture", "art", "문화", "예술"), "#a21caf"),
    (("sport", "스포츠"), "#15803d"),
    (("global", "world", "국제", "글로벌"), "#0f766e"),
    (("estate", "부동산"), "#9a3412"),
]


def add_category_badge(content, category, category_url):
    content = re.sub(r'<!-- newsroom-category:start -->.*?<!-- newsroom-category:end -->\s*', '', content, flags=re.S)
    color = next((color for words, color in PALETTE if any(w in category.lower() for w in words)), "#334155")
    label = html.escape(html.unescape(category))
    href = html.escape(category_url, quote=True)
    badge = (f'<!-- newsroom-category:start --><p class="newsroom-category" style="margin:0 0 20px;">'
             f'<a href="{href}" rel="category tag" style="display:inline-block;background:{color};'
             'color:#ffffff;padding:6px 11px;border-radius:4px;font-size:12px;font-weight:700;'
             f'line-height:1.5;letter-spacing:0.04em;text-decoration:none;">{label}</a></p>'
             '<!-- newsroom-category:end -->\n')
    return badge + content
