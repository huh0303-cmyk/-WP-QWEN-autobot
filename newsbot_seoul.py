#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
theseouljournal.com English international news bot
- 9 sections x 3 articles = 27/day, single round (for GitHub Actions)
- Gemini rewriting, 1000-1500 chars, real newspaper style
- Reporter pool: 10 (5 Western + 5 Korean-American names)
"""

import os, json, time, random, requests, base64, re
from datetime import datetime
import xml.etree.ElementTree as ET

GEMINI_API_KEY = "AQ.Ab8RN6L1RxG7CUO1FSFAl9E53oOM934QWAA3AqcFIWpA3Q7h5g"
GEMINI_MODEL   = "gemini-2.5-flash"
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
POST_GAP_MIN = 8
SECTION_GAP_MIN = 15


def fetch_rss(url):
    try:
        r = requests.get(url, timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SeoulJournal/1.0)"})
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


def get_news_items(section, count=5):
    all_items = []
    for url in section["rss"]:
        all_items.extend(fetch_rss(url))
    seen, unique = set(), []
    for item in all_items:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique.append(item)
    return random.sample(unique, min(count, len(unique))) if unique else [
        {"title": f"Latest {section['name']} News 2026",
         "desc": f"Analysis of the latest developments in {section['name']}.",
         "link": ""} for _ in range(count)]


def build_prompt(news, section, reporter):
    return f"""You are {reporter['name']}, {reporter['title']} at The Seoul Journal.
Rewrite the following news into a completely original article. Never copy the original text - write entirely new sentences.

[ORIGINAL HEADLINE]: {news['title']}
[ORIGINAL SUMMARY]: {news['desc'][:300]}
[SECTION]: {section['name']}
[BYLINE]: {reporter['name']}, {reporter['title']}

══════════════════════════
[GEMS Newspaper Writing Guidelines]
══════════════════════════

1. Length & Format
- Body: 1000-1500 characters (strictly follow - real newspaper-brief length, concise)
- Title: new original headline with keyword, 50-60 chars
- Lead paragraph within the first 100 characters: 5W1H summary
- 3+ H2 headings, 1-2 H3 under each

2. Newspaper Style Principles
- Objective, fact-based, inverted-pyramid structure
- 3+ statistics or data points with sources/years
- Expert or official quote (can be created)
- Every paragraph short (2-3 sentences max), with a blank line between paragraphs (mobile readability)

3. Links
- 3 external authoritative links (target="_blank")
- 3 internal links to https://theseouljournal.com/category/{section['slug']}/ or related Seoul Journal articles

4. Required Elements
- 1+ comparison/data table
- 10 tags: <!-- TAGS: tag1, tag2, ..., tag10 (exactly 10) -->
- 2 images: <!-- IMAGE: query --> <!-- ALT: description -->
- Conclusion section with outlook/implications
- <!-- BYLINE: {reporter['name']}, {reporter['title']} -->

[OUTPUT FORMAT - STRICTLY FOLLOW]
Line 1: TITLE: [title]
Line 2: <!-- SLUG: [english slug, lowercase, words separated by hyphens, 5-8 words] -->
Line 3: <!-- META_DESCRIPTION: [120 char meta description] -->
Line 4: <!-- TAGS: tag1, tag2, ..., tag10 -->
Line 5: <!-- BYLINE: {reporter['name']}, {reporter['title']} -->
Line 6+: Full HTML body (no h1 tag)"""


def call_gemini(prompt):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent")
    try:
        r = requests.post(url,
            headers={"Content-Type":"application/json",
                     "x-goog-api-key":GEMINI_API_KEY},
            json={"contents":[{"parts":[{"text":prompt}]}],
                  "generationConfig":{"temperature":0.7,"maxOutputTokens":8192}},
            timeout=120)
        r.raise_for_status()
        time.sleep(6)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"  ❌ Gemini: {e}")
        time.sleep(15)
        return None


def get_image(query):
    try:
        r = requests.get(
            f"https://api.pexels.com/v1/search?query={query}&per_page=5&orientation=landscape",
            headers={"Authorization":PEXELS_KEY},timeout=10)
        photos=r.json().get("photos",[])
        if photos:
            p=random.choice(photos)
            return{"src":p["src"]["large"],"credit":f'Photo by {p["photographer"]} on Pexels'}
    except: pass
    try:
        r=requests.get(
            f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={requests.utils.quote(query)}"
            f"&image_type=photo&per_page=5&safesearch=true",timeout=10)
        hits=r.json().get("hits",[])
        if hits:
            p=random.choice(hits)
            return{"src":p["webformatURL"],"credit":"Image from Pixabay"}
    except: pass
    return{}


def process_content(raw):
    raw = raw.strip()
    raw = re.sub(r'^```[a-zA-Z]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw)
    raw = raw.strip()

    lines=raw.strip().split("\n")
    title=slug=meta=tags_s=byline=""
    content=raw
    for i,line in enumerate(lines):
        if line.startswith("TITLE:"):
            title=line.replace("TITLE:","").strip()
            title=re.sub(r'^```[a-zA-Z]*\s*','',title)
            title=title.strip('`"\' ')
        if "SLUG:" in line:
            slug=line.split("SLUG:")[-1].replace("-->", "").strip()
            slug=re.sub(r'[^a-z0-9\-]', '', slug.lower().replace(" ", "-"))
            slug=re.sub(r'-+', '-', slug).strip('-')
        if "META_DESCRIPTION:" in line: meta=line.split("META_DESCRIPTION:")[-1].replace("-->","").strip()
        if "TAGS:" in line: tags_s=line.split("TAGS:")[-1].replace("-->","").strip()
        if "BYLINE:" in line: byline=line.split("BYLINE:")[-1].replace("-->","").strip()
        if title and meta:
            content="\n".join(lines[i+1:])
            break
    def img_replacer(m):
        img=get_image(m.group(1).strip())
        alt=m.group(2).strip()
        if img:
            return(f'<figure class="wp-block-image size-large">'
                   f'<img src="{img["src"]}" alt="{alt}" loading="lazy"/>'
                   f'<figcaption>{img["credit"]}</figcaption></figure>')
        return f'<p><em>[Image: {alt}]</em></p>'
    content=re.sub(r'<!-- IMAGE: (.+?) -->\s*<!-- ALT: (.+?) -->',img_replacer,content,flags=re.DOTALL)
    if byline:
        content=f'<p style="color:#666;font-size:13px;border-bottom:1px solid #eee;padding-bottom:8px;margin-bottom:16px">✍️ By {byline} | The Seoul Journal</p>\n'+content
    tags=[t.strip() for t in tags_s.split(",") if t.strip()][:10]
    return{"title":title or "News Article","slug":slug,"meta":meta,"content":content,"tags":tags}


def seo_score(parsed):
    c, t, m = parsed["content"], parsed["title"], parsed["meta"]
    checks = [
        ("Title length 20+",        len(t) >= 20),
        ("Meta desc 80+ chars",      len(m) >= 80),
        ("Body 1000+ chars",         len(c) >= 1000),
        ("Body under 1700 chars",    len(c) <= 1700),
        ("H2 3+",                    c.count("<h2") >= 3),
        ("H3 1+",                    c.count("<h3") >= 1),
        ("Image + ALT",              "<img" in c and 'alt="' in c),
        ("Table 1+",                 c.count("<table") >= 1),
        ("External links 3+",        c.count('target="_blank"') >= 3),
        ("Internal links 3+",        c.count("theseouljournal.com") >= 3),
        ("Byline present",           "byline" in c.lower() or "By " in c),
        ("Tags 8+",                  len(parsed.get("tags", [])) >= 8),
        ("Outlook/Conclusion",        "outlook" in c.lower() or "conclusion" in c.lower()),
    ]
    score = round(sum(100/len(checks) for _, ok in checks if ok))
    passed = sum(1 for _, ok in checks if ok)
    print(f"  ┌─ Quality check ({passed}/{len(checks)}) ──────────────", flush=True)
    for name, ok in checks:
        print(f"  │ {'✅' if ok else '❌'} {name}", flush=True)
    print(f"  └─ Score: {score} {'🎉' if score >= 90 else '⚠️'}", flush=True)
    return score


def get_cat_id(slug, name):
    auth=base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    try:
        r=requests.get(f"{WP_URL}/wp-json/wp/v2/categories?slug={slug}",
            headers={"Authorization":f"Basic {auth}"},timeout=10)
        data=r.json()
        if data: return data[0]["id"]
        r2=requests.post(f"{WP_URL}/wp-json/wp/v2/categories",
            headers={"Authorization":f"Basic {auth}","Content-Type":"application/json"},
            json={"name":name,"slug":slug},timeout=10)
        return r2.json().get("id",1)
    except: return 1


def post_to_wp(parsed, cat_id):
    auth=base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    tag_ids=[]
    for tag in parsed.get("tags",[])[:10]:
        try:
            r=requests.post(f"{WP_URL}/wp-json/wp/v2/tags",
                headers={"Authorization":f"Basic {auth}","Content-Type":"application/json"},
                json={"name":tag},timeout=10)
            if r.status_code in[200,201]: tag_ids.append(r.json()["id"])
            elif r.status_code==400:
                sr=requests.get(f"{WP_URL}/wp-json/wp/v2/tags?search={requests.utils.quote(tag)}",
                    headers={"Authorization":f"Basic {auth}"},timeout=10)
                if sr.json(): tag_ids.append(sr.json()[0]["id"])
            else:
                print(f"     ⚠️ tag '{tag}' failed: {r.status_code} {r.text[:120]}")
        except Exception as e:
            print(f"     ⚠️ tag '{tag}' error: {e}")
    print(f"  🏷️  Tags registered: {len(tag_ids)}/{len(parsed.get('tags',[])[:10])} (IDs: {tag_ids})")
    try:
        r=requests.post(f"{WP_URL}/wp-json/wp/v2/posts",
            headers={"Authorization":f"Basic {auth}","Content-Type":"application/json"},
            json={"title":parsed["title"],"content":parsed["content"],
                  "status":"publish","categories":[cat_id],"tags":tag_ids,
                  **({"slug": parsed["slug"]} if parsed.get("slug") else {}),
                  "meta":{"rank_math_description":parsed["meta"]}},timeout=30)
        r.raise_for_status()
        print(f"  🔗 slug: {r.json().get('slug','')}")
        return r.json().get("id"),r.json().get("link","")
    except Exception as e:
        print(f"  ❌ WP: {e}")
        return None,None


def run_daily():
    print(f"\n{'═'*55}")
    print(f"  📰 The Seoul Journal news bot starting")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  9 sections x {ARTICLES_PER_SECTION} = {9*ARTICLES_PER_SECTION} articles")
    print(f"{'═'*55}")
    for sec in SECTIONS:
        if sec["id"] is None:
            sec["id"]=get_cat_id(sec["slug"],sec["name"])
        print(f"  {sec['name']:15s} → ID: {sec['id']}")
    results=[]
    used_reporters=[]
    for si,section in enumerate(SECTIONS):
        print(f"\n  📌 [{section['name']}]")
        news_items=get_news_items(section,ARTICLES_PER_SECTION)
        for ai,news in enumerate(news_items):
            if ai>0:
                gap=POST_GAP_MIN*60+random.randint(-60,120)
                time.sleep(gap)

            choices = [r for r in REPORTERS if r["name"] != (used_reporters[-1]["name"] if used_reporters else None)]
            reporter = random.choice(choices)
            used_reporters.append(reporter)

            print(f"\n  [{si+1}/9][{ai+1}/{ARTICLES_PER_SECTION}] {section['name']} — {reporter['name']}")
            print(f"  📰 {news['title'][:50]}")
            print(f"  🧠 Generating with Gemini...")

            raw=call_gemini(build_prompt(news,section,reporter))
            if not raw: continue
            parsed=process_content(raw)
            score=seo_score(parsed)

            if score < 80:
                print("  🔄 Below 80, regenerating...", flush=True)
                raw2=call_gemini(build_prompt(news,section,reporter))
                if raw2:
                    parsed2=process_content(raw2)
                    score2=seo_score(parsed2)
                    if score2 > score:
                        parsed, score = parsed2, score2
                if score < 80:
                    print(f"  ⚠️ Still {score} after retry, publishing best result", flush=True)

            print(f"  📄 {parsed['title'][:55]}")
            pid,purl=post_to_wp(parsed,section["id"])
            if pid:
                print(f"  ✅ ID:{pid} score:{score} → {purl}")
                results.append({"section":section["name"],"reporter":reporter["name"],
                                "title":parsed["title"],"url":purl,"score":score,
                                "time":datetime.now().strftime("%H:%M")})
        if si<len(SECTIONS)-1:
            gap=SECTION_GAP_MIN*60+random.randint(-120,180)
            time.sleep(gap)
    print(f"\n  ✅ Done: {len(results)} articles")
    return results


if __name__ == "__main__":
    results = run_daily()
    fname = f"news_en_{datetime.now().strftime('%Y%m%d')}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  📁 Saved: {fname}")
