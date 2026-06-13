#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, time, random, requests, base64, re
from datetime import datetime
import xml.etree.ElementTree as ET

# 깃허브 시크릿(Secrets) 시스템 연동 완료
QWEN_API_KEY   = os.environ.get("QWEN_API_KEY")
QWEN_MODEL     = "qwen-2.5-72b-instruct"
QWEN_API_URL   = "https://api.groq.com/openai/v1/chat/completions"

PEXELS_KEY     = os.environ.get("PEXELS_KEY")
PIXABAY_KEY    = os.environ.get("PIXABAY_KEY")

WP_URL  = "https://theseouljournal.com"
WP_USER = "huh0303@gmail.com"
WP_PASS = os.environ.get("WP_PASS")

REPORTERS = [
    {"name": "Sarah Mitchell",  "title": "Senior Political Correspondent"},
    {"name": "James Anderson",  "title": "Business & Economy Reporter"},
    {"name": "Emily Carter",    "title": "Culture & Lifestyle Editor"},
    {"name": "David Thompson",  "title": "International Affairs Correspondent"},
    {"name": "Rachel Bennett",  "title": "Technology & Innovation Reporter"},
    {"name": "Sarah Kim",       "title": "Senior Political Correspondent"},
    {"name": "James Park",      "title": "Business & Economy Reporter"},
    {"name": "Emily Choi",      "title": "Culture & Lifestyle Editor"},
    {"name": "David Lee",       "title": "International Affairs Correspondent"},
    {"name": "Rachel Yoon",     "title": "Technology & Innovation Reporter"},
]

SECTIONS = [
    {"name": "Politics",      "slug": "politics",      "id": None, "rss": ["https://feeds.bbci.co.uk/news/world/rss.xml", "https://rss.cnn.com/rss/edition_world.rss"]},
    {"name": "Economy",       "slug": "economy",       "id": None, "rss": ["https://feeds.bbci.co.uk/news/business/rss.xml", "https://rss.cnn.com/rss/money_latest.rss"]},
    {"name": "Korea News",    "slug": "korea-news",    "id": None, "rss": ["https://feeds.bbci.co.uk/news/world/asia/rss.xml", "https://rss.cnn.com/rss/edition_asia.rss"]},
    {"name": "Military",      "slug": "military",      "id": None, "rss": ["https://feeds.bbci.co.uk/news/world/rss.xml", "https://rss.cnn.com/rss/edition_world.rss"]},
    {"name": "Diplomacy",     "slug": "diplomacy",     "id": None, "rss": ["https://feeds.bbci.co.uk/news/world/rss.xml", "https://rss.cnn.com/rss/edition_world.rss"]},
    {"name": "K-Culture",     "slug": "k-culture",     "id": None, "rss": ["https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml", "https://rss.cnn.com/rss/edition_entertainment.rss"]},
    {"name": "K-Health",      "slug": "k-health",      "id": None, "rss": ["https://feeds.bbci.co.uk/news/health/rss.xml", "https://rss.cnn.com/rss/edition_health.rss"]},
    {"name": "K-Beauty",      "slug": "k-beauty",      "id": None, "rss": ["https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml", "https://rss.cnn.com/rss/edition_entertainment.rss"]},
    {"name": "Tech & Science","slug": "tech-science",  "id": None, "rss": ["https://feeds.bbci.co.uk/news/technology/rss.xml", "https://rss.cnn.com/rss/edition_technology.rss"]},
]

ARTICLES_PER_SECTION = 3
POST_GAP_MIN = 3
SECTION_GAP_MIN = 5

def fetch_rss(url):
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 SeoulJournalBot/2.5"})
        root = ET.fromstring(r.content)
        items = []
        for item in root.findall(".//item")[:10]:
            title = item.findtext("title","").strip()
            desc  = re.sub(r'<[^>]+>','',item.findtext("description",""))[:500]
            link  = item.findtext("link","").strip()
            if title and len(title) > 5: items.append({"title":title,"desc":desc,"link":link})
        return items
    except: return []

def get_news_items(section, count=3):
    all_items = []
    for url in section["rss"]: all_items.extend(fetch_rss(url))
    seen, unique = set(), []
    for item in all_items:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique.append(item)
    return random.sample(unique, min(count, len(unique))) if unique else [{"title": f"Latest {section['name']} Global Update 2026", "desc": f"In-depth analysis of {section['name']}.", "link": ""}]

def build_prompt(news, section, reporter):
    return f"""You are {reporter['name']}, {reporter['title']} at The Seoul Journal (theseouljournal.com).
Rewrite the following news source into a sophisticated, authoritative, and completely original global journalistic article. 

[SOURCE HEADLINE]: {news['title']}
[SOURCE SUMMARY]: {news['desc'][:300]}
[EDITORIAL DESK]: {section['name']}
[BYLINE CREDIT]: {reporter['name']}, {reporter['title']}

1. Critical Mobile Readability & Structure
- Every single sentence must be kept extremely short and distinct.
- Each paragraph (<p> tag) must contain exactly ONE sentence.
- You MUST insert a clear blank line (empty newline) between every single paragraph.

2. Article Architecture
- Length: 1200-1600 characters.
- Headline (TITLE): New SEO headline (50-60 chars).
- Lead Sentence: Summarize within the first 100 characters.
- Subsection Breakdown: 3+ H2 headings, 1-2 H3. No H1 tags.
- Quantitative Validation: 3+ statistics with sources/years.

3. Links
- Authority Backlinks: 3+ external hyperlinks (target="_blank").
- Strategic Native Link: Naturally integrate a link to 'k-health365.com' primary domain or category.

4. Compulsory Elements
- 1+ structured HTML data table.
- 2 image placeholders: - End with 'Outlook and Implications' segment.
- Byline: TITLE: [Your Title]
Full HTML body content (with strict short-sentence blank-line format)"""

def call_qwen(prompt):
    headers = {"Authorization": f"Bearer {QWEN_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": QWEN_MODEL,
        "messages": [
            {"role": "system", "content": "You are the Editor-in-Chief of an elite international English newspaper."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.65, "max_tokens": 4096
    }
    try:
        r = requests.post(QWEN_API_URL, headers=headers, json=payload, timeout=100)
        r.raise_for_status()
        time.sleep(4)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  ❌ Qwen API Error: {e}")
        time.sleep(12)
        return None

def get_image(query):
    try:
        r = requests.get(f"https://api.pexels.com/v1/search?query={query}&per_page=5&orientation=landscape", headers={"Authorization":PEXELS_KEY}, timeout=10)
        photos = r.json().get("photos", [])
        if photos:
            p = random.choice(photos)
            return {"src": p["src"]["large"], "credit": f'Photo by {p["photographer"]} on Pexels'}
    except: pass
    try:
        r = requests.get(f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={requests.utils.quote(query)}&image_type=photo&per_page=5&safesearch=true", timeout=10)
        hits = r.json().get("hits", [])
        if hits:
            p = random.choice(hits)
            return {"src": p["webformatURL"], "credit": "Image via Pixabay"}
    except: pass
    return {}

def process_content(raw):
    raw = raw.strip()
    raw = re.sub(r'^```[a-zA-Z]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw)
    lines = raw.split("\n")
    title = slug = meta = tags_s = byline = ""
    content = raw
    for i, line in enumerate(lines):
        if line.startswith("TITLE:"): title = line.replace("TITLE:", "").strip().strip('`"\' ')
        if "SLUG:" in line: slug = line.split("SLUG:")[-1].replace("-->", "").strip(); slug = re.sub(r'[^a-z0-9\-]', '', slug.lower().replace(" ", "-")).strip('-')
        if "META_DESCRIPTION:" in line: meta = line.split("META_DESCRIPTION:")[-1].replace("-->","").strip()
        if "TAGS:" in line: tags_s = line.split("TAGS:")[-1].replace("-->","").strip()
        if "BYLINE:" in line: byline = line.split("BYLINE:")[-1].replace("-->","").strip()
        if title and meta: content = "\n".join(lines[i+1:]); break

    def img_replacer(m):
        img = get_image(m.group(1).strip())
        alt = m.group(2).strip()
        if img: return f'<figure class="wp-block-image size-large aligncenter" style="margin:25px auto; text-align:center;"><img src="{img["src"]}" alt="{alt}" loading="lazy" style="border-radius:4px; max-width:100%; height:auto;"/><figcaption style="font-size:12px; color:#666; margin-top:6px;">{img["credit"]}</figcaption></figure>'
        return f'<p style="text-align:center; color:#999;"><em>[Photo: {alt}]</em></p>'

    content = re.sub(r'\s*', img_replacer, content, flags=re.DOTALL)
    if byline: content = f'<p style="color:#444; font-weight:bold; font-size:13px; border-bottom:2px solid #111; padding-bottom:6px; margin-bottom:20px;">✍️ By {byline} | The Seoul Journal Desk</p>\n' + content
    tags = [t.strip() for t in tags_s.split(",") if t.strip()][:10]
    return {"title": title or "Global News Report", "slug": slug, "meta": meta, "content": content, "tags": tags}

def seo_score(parsed):
    c, t, m = parsed["content"], parsed["title"], parsed["meta"]
    checks = [len(t)>=20, len(m)>=70, len(c)>=1000, len(c)<=1800, c.count("<h2")>=3, c.count("<h3")>=1, "<img" in c, c.count("<table")>=1, c.count('target="_blank"')>=3, c.count("theseouljournal.com")>=3, len(parsed.get("tags",[]))>=8]
    return round(sum(100/len(checks) for ok in checks if ok))

def get_cat_id(slug, name):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    try:
        r = requests.get(f"{WP_URL}/wp-json/wp/v2/categories?slug={slug}", headers={"Authorization": f"Basic {auth}"}, timeout=10)
        if r.json(): return r.json()[0]["id"]
        r2 = requests.post(f"{WP_URL}/wp-json/wp/v2/categories", headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"}, json={"name": name, "slug": slug}, timeout=10)
        return r2.json().get("id", 1)
    except: return 1

def post_to_wp(parsed, cat_id):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    tag_ids = []
    for tag in parsed.get("tags", [])[:10]:
        try:
            r = requests.post(f"{WP_URL}/wp-json/wp/v2/tags", headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"}, json={"name": tag}, timeout=10)
            if r.status_code in [200, 201]: tag_ids.append(r.json()["id"])
            elif r.status_code == 400:
                sr = requests.get(f"{WP_URL}/wp-json/wp/v2/tags?search={requests.utils.quote(tag)}", headers={"Authorization": f"Basic {auth}"}, timeout=10)
                if sr.json(): tag_ids.append(sr.json()[0]["id"])
        except: pass
    try:
        r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"}, json={"title": parsed["title"], "content": parsed["content"], "status": "publish", "categories": [cat_id], "tags": tag_ids, **({"slug": parsed["slug"]} if parsed.get("slug") else {}), "meta": {"rank_math_description": parsed["meta"]}}, timeout=30)
        return r.json().get("id"), r.json().get("link", "")
    except: return None, None

def run_daily():
    for sec in SECTIONS:
        if sec["id"] is None: sec["id"] = get_cat_id(sec["slug"], sec["name"])
    results = []
    used_reporters = []
    for si, section in enumerate(SECTIONS):
        news_items = get_news_items(section, ARTICLES_PER_SECTION)
        for ai, news in enumerate(news_items):
            if ai > 0: time.sleep(POST_GAP_MIN * 60)
            choices = [r for r in REPORTERS if r["name"] != (used_reporters[-1]["name"] if used_reporters else None)]
            reporter = random.choice(choices); used_reporters.append(reporter)
            raw = call_qwen(build_prompt(news, section, reporter))
            if not raw: continue
            parsed = process_content(raw); score = seo_score(parsed)
            pid, purl = post_to_wp(parsed, section["id"])
            if pid: results.append({"section": section["name"], "title": parsed["title"], "url": purl})
        if si < len(SECTIONS)-1: time.sleep(SECTION_GAP_MIN * 60)
    return results

if __name__ == "__main__":
    run_daily()
