#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
theseouljournal.com English international news bot (Qwen Mega Version)
- 9 sections x 3 articles = 27/day, single round (for GitHub Actions)
- Rewriting with Qwen Free API Infrastructure, 1000-1500 chars, real newspaper style
- Mobile-optimized: Severe sentence-level breaking with forced blank lines
"""

import os, json, time, random, requests, base64, re
from datetime import datetime
import xml.etree.ElementTree as ET

# ══════════════════════════════════════════════
#  ★ 100% Free API Infrastructure & WP Settings ★
# ══════════════════════════════════════════════
QWEN_API_KEY   = "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"
QWEN_MODEL     = "qwen-2.5-72b-instruct"  # Fully compatible with Groq/OpenAI completions endpoint style
QWEN_API_URL   = "https://api.groq.com/openai/v1/chat/completions"

PEXELS_KEY     = "41q16JQ0qBM123kTUgEk2YKAfK3e43l6NCErWoWn0Fv41Zmdfub0XAs8"
PIXABAY_KEY    = "u_g0pmau3m85"

WP_URL  = "https://theseouljournal.com"
WP_USER = "huh0303@gmail.com"
WP_PASS = "SY4UJX)NyT5Ukg(sdSz$q%zg"

# ── Reporter pool (10): 5 Western surnames + 5 Korean-American ──
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
    {"name": "Politics",      "slug": "politics",      "id": None,
     "rss": ["https://feeds.bbci.co.uk/news/world/rss.xml",
             "https://rss.cnn.com/rss/edition_world.rss"]},
    {"name": "Economy",       "slug": "economy",       "id": None,
     "rss": ["https://feeds.bbci.co.uk/news/business/rss.xml",
             "https://rss.cnn.com/rss/money_latest.rss"]},
    {"name": "Korea News",    "slug": "korea-news",    "id": None,
     "rss": ["https://feeds.bbci.co.uk/news/world/asia/rss.xml",
             "https://rss.cnn.com/rss/edition_asia.rss"]},
    {"name": "Military",      "slug": "military",      "id": None,
     "rss": ["https://feeds.bbci.co.uk/news/world/rss.xml",
             "https://rss.cnn.com/rss/edition_world.rss"]},
    {"name": "Diplomacy",     "slug": "diplomacy",     "id": None,
     "rss": ["https://feeds.bbci.co.uk/news/world/rss.xml",
             "https://rss.cnn.com/rss/edition_world.rss"]},
    {"name": "K-Culture",     "slug": "k-culture",     "id": None,
     "rss": ["https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
             "https://rss.cnn.com/rss/edition_entertainment.rss"]},
    {"name": "K-Health",      "slug": "k-health",      "id": None,
     "rss": ["https://feeds.bbci.co.uk/news/health/rss.xml",
             "https://rss.cnn.com/rss/edition_health.rss"]},
    {"name": "K-Beauty",      "slug": "k-beauty",      "id": None,
     "rss": ["https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
             "https://rss.cnn.com/rss/edition_entertainment.rss"]},
    {"name": "Tech & Science","slug": "tech-science",  "id": None,
     "rss": ["https://feeds.bbci.co.uk/news/technology/rss.xml",
             "https://rss.cnn.com/rss/edition_technology.rss"]},
]

ARTICLES_PER_SECTION = 3
POST_GAP_MIN = 3
SECTION_GAP_MIN = 5

# ──────────────────────────────────────────────

def fetch_rss(url):
    try:
        r = requests.get(url, timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SeoulJournalBot/2.5"})
        root = ET.fromstring(r.content)
        items = []
        for item in root.findall(".//item")[:10]:
            title = item.findtext("title","").strip()
            desc  = re.sub(r'<[^>]+>','',item.findtext("description",""))[:500]
            link  = item.findtext("link","").strip()
            if title and len(title) > 5:
                items.append({"title":title,"desc":desc,"link":link})
        return items
    except:
        return []


def get_news_items(section, count=3):
    all_items = []
    for url in section["rss"]:
        all_items.extend(fetch_rss(url))
    seen, unique = set(), []
    for item in all_items:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique.append(item)
    return random.sample(unique, min(count, len(unique))) if unique else [
        {"title": f"Latest {section['name']} Global Update 2026",
         "desc": f"In-depth intelligence analysis of the breaking trends shaping {section['name']}.",
         "link": ""} for _ in range(count)]


def build_prompt(news, section, reporter):
    return f"""You are {reporter['name']}, {reporter['title']} at The Seoul Journal (theseouljournal.com).
Rewrite the following news source into a sophisticated, authoritative, and completely original global journalistic article. 
Do not replicate sentences from the source material; craft entirely fresh prose with high analytical credibility.

[SOURCE HEADLINE]: {news['title']}
[SOURCE SUMMARY]: {news['desc'][:300]}
[EDITORIAL DESK]: {section['name']}
[BYLINE CREDIT]: {reporter['name']}, {reporter['title']}

══════════════════════════
[GEMS Global Editorial & SEO Guidelines]
══════════════════════════

1. Critical Mobile Readability & Structure (★ MANDATORY)
- To maximize readability on smartphone screens, every single sentence must be kept extremely short, punchy, and distinct.
- Each paragraph (<p> tag) should contain exactly ONE sentence, and under no circumstances exceed two sentences.
- You MUST insert a clear blank line (empty newline) between every single paragraph in the output HTML code to provide optimal visual breathing room for mobile users.

2. Article Architecture
- Length: 1,200 to 1,600 characters of high-quality English text.
- Headline (TITLE): Draft a new, captivating, and professional journalistic headline including core SEO keywords (50-60 characters).
- Lead Sentence: Summarize the core event utilizing the 5W1H matrix within the first 100 characters.
- Subsection Breakdown: Insert at least 3 H2 headings and 1-2 H3 subheadings to establish an immaculate data hierarchy. Never use H1 tags.
- Quantitative Validation: Integrate at least 3 relevant statistics or data markers with specified institutional sources or years.

3. Interlinked Network Architecture
- Authority Backlinks: Embed at least 3 external hyperlinks pointing to global public records, government agencies, or prominent global think tanks (target="_blank" is required).
- Strategic Native Link: Naturally integrate a descriptive anchor text hyperlink seamlessly redirecting to the premium health hub partner 'k-health365.com' (e.g., linking to its primary domain or a relevant niche category) to maximize domain authority integration.

4. Compulsory News Elements
- Provide 1+ systematically structured HTML data/comparison table summarizing the core analytics.
- Image placeholders at 2 optimal positions: - End the piece with an insightful segment titled 'Outlook and Implications' evaluating long-term market or macro developments.
- Embed the structural byline: [OUTPUT FORMAT - STERNLY ENFORCED]
Line 1: TITLE: [Your Created Article Title]
Line 2: Line 3: Line 4: Line 5: Line 6+: Full HTML body content (Adhering strictly to the short-sentence mobile blank-line criteria)"""


def call_qwen(prompt):
    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": QWEN_MODEL,
        "messages": [
            {"role": "system", "content": "You are the Editor-in-Chief and SEO Director of an elite international English newspaper."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.65,
        "max_tokens": 4096
    }
    try:
        r = requests.post(QWEN_API_URL, headers=headers, json=payload, timeout=100)
        r.raise_for_status()
        time.sleep(4)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  ❌ Qwen API Exception: {e}")
        time.sleep(12)
        return None


def get_image(query):
    try:
        r = requests.get(
            f"https://api.pexels.com/v1/search?query={query}&per_page=5&orientation=landscape",
            headers={"Authorization":PEXELS_KEY},timeout=10)
        photos = r.json().get("photos", [])
        if photos:
            p = random.choice(photos)
            return {"src": p["src"]["large"], "credit": f'Photo by {p["photographer"]} on Pexels'}
    except: pass
    try:
        r = requests.get(
            f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={requests.utils.quote(query)}"
            f"&image_type=photo&per_page=5&safesearch=true",timeout=10)
        hits = r.json().get("hits", [])
        if hits:
            p = random.choice(hits)
            return {"src": p["webformatURL"], "credit": "Image via Pixabay Content License"}
    except: pass
    return {}


def process_content(raw):
    raw = raw.strip()
    raw = re.sub(r'^```[a-zA-Z]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw)
    raw = raw.strip()

    lines = raw.strip().split("\n")
    title = slug = meta = tags_s = byline = ""
    content = raw
    
    for i, line in enumerate(lines):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip().strip('`"\' ')
        if "SLUG:" in line:
            slug = line.split("SLUG:")[-1].replace("-->", "").strip()
            slug = re.sub(r'[^a-z0-9\-]', '', slug.lower().replace(" ", "-"))
            slug = re.sub(r'-+', '-', slug).strip('-')
        if "META_DESCRIPTION:" in line: 
            meta = line.split("META_DESCRIPTION:")[-1].replace("-->","").strip()
        if "TAGS:" in line: 
            tags_s = line.split("TAGS:")[-1].replace("-->","").strip()
        if "BYLINE:" in line: 
            byline = line.split("BYLINE:")[-1].replace("-->","").strip()
        if title and meta:
            content = "\n".join(lines[i+1:])
            break

    def img_replacer(m):
        img = get_image(m.group(1).strip())
        alt = m.group(2).strip()
        if img:
            return (f'<figure class="wp-block-image size-large aligncenter" style="margin:25px auto; text-align:center;">'
                    f'<img src="{img["src"]}" alt="{alt}" loading="lazy" style="border-radius:4px; max-width:100%; height:auto;"/>'
                    f'<figcaption style="font-size:12px; color:#666; margin-top:6px;">{img["credit"]}</figcaption></figure>')
        return f'<p style="text-align:center; color:#999;"><em>[Press Photo: {alt}]</em></p>'

    content = re.sub(r'\s*', img_replacer, content, flags=re.DOTALL)
    
    if byline:
        content = f'<p class="editorial-byline" style="color:#444; font-weight:bold; font-size:13px; border-bottom:2px solid #111; padding-bottom:6px; margin-bottom:20px;">✍️ By {byline} | The Seoul Journal Desk</p>\n' + content
        
    tags = [t.strip() for t in tags_s.split(",") if t.strip()][:10]
    return {"title": title or "Global News Report", "slug": slug, "meta": meta, "content": content, "tags": tags}


def seo_score(parsed):
    c, t, m = parsed["content"], parsed["title"], parsed["meta"]
    checks = [
        ("Premium Title Validity",  len(t) >= 20),
        ("Meta Snippet Capacity",   len(m) >= 70),
        ("Text Content Mass",       len(c) >= 1000),
        ("Structural Control Max",  len(c) <= 1800),
        ("H2 Semantic Core",        c.count("<h2") >= 3),
        ("H3 Granular Breakdowns",  c.count("<h3") >= 1),
        ("Visual Asset Embedding",  "<img" in c and 'alt="' in c),
        ("Analytics Matrix Table",  c.count("<table") >= 1),
        ("External Trust Node",     c.count('target="_blank"') >= 3),
        ("Internal Domain Footprint", c.count("theseouljournal.com") >= 3),
        ("Byline Verification",     "byline" in c.lower() or "By " in c),
        ("SEO Meta Tags 8+",        len(parsed.get("tags", [])) >= 8),
        ("Outlook Framework Case",  "outlook" in c.lower() or "conclusion" in c.lower()),
    ]
    score = round(sum(100/len(checks) for _, ok in checks if ok))
    passed = sum(1 for _, ok in checks if ok)
    
    print(f"  ┌─ Editorial Quality Audit ({passed}/{len(checks)})", flush=True)
    for name, ok in checks:
        print(f"  │ {'✅' if ok else '❌'} {name}", flush=True)
    print(f"  └─ Compliance Score: {score} {'🎉' if score >= 90 else '⚠️'}", flush=True)
    return score


def get_cat_id(slug, name):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    try:
        r = requests.get(f"{WP_URL}/wp-json/wp/v2/categories?slug={slug}",
                         headers={"Authorization": f"Basic {auth}"}, timeout=10)
        data = r.json()
        if data: return data[0]["id"]
        
        r2 = requests.post(f"{WP_URL}/wp-json/wp/v2/categories",
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
            json={"name": name, "slug": slug}, timeout=10)
        return r2.json().get("id", 1)
    except: return 1


def post_to_wp(parsed, cat_id):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    tag_ids = []
    for tag in parsed.get("tags", [])[:10]:
        try:
            r = requests.post(f"{WP_URL}/wp-json/wp/v2/tags",
                headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
                json={"name": tag}, timeout=10)
            if r.status_code in [200, 201]:
                tag_ids.append(r.json()["id"])
            elif r.status_code == 400:
                sr = requests.get(f"{WP_URL}/wp-json/wp/v2/tags?search={requests.utils.quote(tag)}",
                                  headers={"Authorization": f"Basic {auth}"}, timeout=10)
                if sr.json(): tag_ids.append(sr.json()[0]["id"])
        except Exception as e:
            print(f"     ⚠️ Tag binding exception: {e}")

    try:
        r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts",
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
            json={"title": parsed["title"], "content": parsed["content"],
                  "status": "publish", "categories": [cat_id], "tags": tag_ids,
                  **({"slug": parsed["slug"]} if parsed.get("slug") else {}),
                  "meta": {"rank_math_description": parsed["meta"]}}, timeout=30)
        r.raise_for_status()
        print(f"  🔗 Bound slug: {r.json().get('slug','')}")
        return r.json().get("id"), r.json().get("link", "")
    except Exception as e:
        print(f"  ❌ WordPress Core Publishing Refused: {e}")
        return None, None


def run_daily():
    print(f"\n{'═'*55}")
    print(f"  📰 The Seoul Journal Newsroom Engine (Qwen Core)")
    print(f"  Deployment Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Scale: 9 Sections x {ARTICLES_PER_SECTION} Wire Feeds = {9*ARTICLES_PER_SECTION} Global Postings")
    print(f"{'═'*55}")
    
    for sec in SECTIONS:
        if sec["id"] is None:
            sec["id"] = get_cat_id(sec["slug"], sec["name"])
        print(f"  {sec['name']:18s} → Category ID: {sec['id']}")
        
    results = []
    used_reporters = []
    
    for si, section in enumerate(SECTIONS):
        print(f"\n  📌 Current Desk: [{section['name']}]")
        news_items = get_news_items(section, ARTICLES_PER_SECTION)
        
        for ai, news in enumerate(news_items):
            if ai > 0:
                gap = POST_GAP_MIN * 60 + random.randint(-30, 60)
                print(f"  ⏳ Waiting for API limits buffer ({gap//60}m)...")
                time.sleep(gap)

            choices = [r for r in REPORTERS if r["name"] != (used_reporters[-1]["name"] if used_reporters else None)]
            reporter = random.choice(choices)
            used_reporters.append(reporter)

            print(f"\n  [Desk Run {si+1}/9] [{ai+1}/{ARTICLES_PER_SECTION}] {section['name']} — {reporter['name']}")
            print(f"  🎙️ Source Feed: {news['title'][:50]}")
            print(f"  🧠 Engineering Prose via Qwen Engine...")

            raw = call_qwen(build_prompt(news, section, reporter))
            if not raw: continue
            
            parsed = process_content(raw)
            score = seo_score(parsed)

            if score < 80:
                print("  🔄 Underperforming Quality Index. Running Revision Audit...")
                raw2 = call_qwen(build_prompt(news, section, reporter))
                if raw2:
                    parsed2 = process_content(raw2)
                    score2 = seo_score(parsed2)
                    if score2 > score: parsed, score = parsed2, score2

            pid, purl = post_to_wp(parsed, section["id"])
            if pid:
                print(f"  ✅ [Broadcast Success] ID: {pid} | Index Score: {score}")
                print(f"  🔗 Live URL: {purl}")
                results.append({"section": section["name"], "reporter": reporter["name"],
                                "title": parsed["title"], "url": purl, "score": score,
                                "time": datetime.now().strftime("%H:%M")})
                                
        if si < len(SECTIONS)-1:
            gap = SECTION_GAP_MIN * 60 + random.randint(-60, 120)
            print(f"\n  ⏰ Moving to subsequent Editorial Desk in {gap//60} minutes...")
            time.sleep(gap)
            
    print(f"\n  ✅ Daily Batch Distribution Terminated Successfully: {len(results)} Articles Posted.")
    return results


if __name__ == "__main__":
    results = run_daily()
    fname = f"news_en_{datetime.now().strftime('%Y%m%d')}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  📁 Local Archive Update Finalized: {fname}")
