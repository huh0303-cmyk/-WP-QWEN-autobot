#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
theseouljournal.com 영어 국제뉴스봇
- CNN, BBC, Reuters, AP 등 RSS 수집
- 9개 섹션 × 3개 = 하루 27개
- Gemini로 영어 리라이팅
- 가상 기자: Sarah Kim, James Park, Emily Choi, David Lee, Rachel Yoon
"""

import os, json, time, random, requests, base64, re
from datetime import datetime
import xml.etree.ElementTree as ET

GEMINI_API_KEY = "AQ.Ab8RN6Je6ngXK-4cSMxL05o3jlfF06RNHJtwz3XlPdB6zqLFbA"
GEMINI_MODEL   = "gemini-2.5-flash"
PEXELS_KEY     = "41q16JQ0qBM123kTUgEk2YKAfK3e43l6NCErWoWn0Fv41Zmdfub0XAs8"
PIXABAY_KEY    = "u_g0pmau3m85"

WP_URL  = "https://theseouljournal.com"
WP_USER = "huh0303@gmail.com"
WP_PASS = "SY4UJX)NyT5Ukg(sdSz$q%zg"

REPORTERS = [
    {"name": "Sarah Kim",    "title": "Senior Political Correspondent"},
    {"name": "James Park",   "title": "Business & Economy Reporter"},
    {"name": "Emily Choi",   "title": "Culture & Lifestyle Editor"},
    {"name": "David Lee",    "title": "International Affairs Correspondent"},
    {"name": "Rachel Yoon",  "title": "Technology & Innovation Reporter"},
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

ARTICLES_PER_SECTION = 5
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
Rewrite the following news into a completely original article. Never copy the original text.

[ORIGINAL HEADLINE]: {news['title']}
[ORIGINAL SUMMARY]: {news['desc'][:300]}
[SECTION]: {section['name']}
[BYLINE]: {reporter['name']}, {reporter['title']}
[TARGET LENGTH]: 1500-2500 characters

[REQUIREMENTS]
1. Title: New original headline with keyword, 50-60 chars
2. Meta description: 120-155 chars with CTA
3. Lead paragraph: 5W1H summary
4. 4+ H2 headings, 2+ H3 under each
5. 3+ statistics or data points with sources
6. Expert quote (can be created)
7. 3 external authoritative links
8. 3 internal links to theseouljournal.com
9. 1+ comparison table
10. 8 tags: <!-- TAGS: tag1, tag2, ... -->
11. 2 images: <!-- IMAGE: query --> <!-- ALT: description -->
12. Conclusion with outlook
13. <!-- BYLINE: {reporter['name']}, {reporter['title']} -->

[OUTPUT FORMAT]
Line 1: TITLE: [title]
Line 2: <!-- META_DESCRIPTION: [description] -->
Line 3: <!-- TAGS: tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8 -->
Line 4: <!-- BYLINE: {reporter['name']}, {reporter['title']} -->
Line 5+: Full HTML body (no h1 tag)"""


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
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"  ❌ Gemini: {e}")
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
    lines=raw.strip().split("\n")
    title=meta=tags_s=byline=content=""
    content=raw
    for i,line in enumerate(lines):
        if line.startswith("TITLE:"): title=line.replace("TITLE:","").strip()
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
    tags=[t.strip() for t in tags_s.split(",") if t.strip()]
    return{"title":title or "News Article","meta":meta,"content":content,"tags":tags}


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
    for tag in parsed.get("tags",[])[:8]:
        try:
            r=requests.post(f"{WP_URL}/wp-json/wp/v2/tags",
                headers={"Authorization":f"Basic {auth}","Content-Type":"application/json"},
                json={"name":tag},timeout=10)
            if r.status_code in[200,201]: tag_ids.append(r.json()["id"])
            elif r.status_code==400:
                sr=requests.get(f"{WP_URL}/wp-json/wp/v2/tags?search={requests.utils.quote(tag)}",
                    headers={"Authorization":f"Basic {auth}"},timeout=10)
                if sr.json(): tag_ids.append(sr.json()[0]["id"])
        except: pass
    try:
        r=requests.post(f"{WP_URL}/wp-json/wp/v2/posts",
            headers={"Authorization":f"Basic {auth}","Content-Type":"application/json"},
            json={"title":parsed["title"],"content":parsed["content"],
                  "status":"publish","categories":[cat_id],"tags":tag_ids,
                  "meta":{"rank_math_description":parsed["meta"]}},timeout=30)
        r.raise_for_status()
        return r.json().get("id"),r.json().get("link","")
    except Exception as e:
        print(f"  ❌ WP: {e}")
        return None,None


def run_daily():
    print(f"\n{'═'*55}")
    print(f"  📰 The Seoul Journal 뉴스봇 시작")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'═'*55}")
    for sec in SECTIONS:
        if sec["id"] is None:
            sec["id"]=get_cat_id(sec["slug"],sec["name"])
        print(f"  {sec['name']:15s} → ID: {sec['id']}")
    results=[]
    reporter_idx=0
    for si,section in enumerate(SECTIONS):
        print(f"\n  📌 [{section['name']}]")
        news_items=get_news_items(section,ARTICLES_PER_SECTION)
        for ai,news in enumerate(news_items):
            if ai>0:
                gap=POST_GAP_MIN*60+random.randint(-60,120)
                time.sleep(gap)
            reporter=REPORTERS[reporter_idx%len(REPORTERS)]
            reporter_idx+=1
            print(f"\n  [{si+1}/9][{ai+1}/5] {section['name']} — {reporter['name']}")
            print(f"  📰 {news['title'][:50]}")
            raw=call_gemini(build_prompt(news,section,reporter))
            if not raw: continue
            parsed=process_content(raw)
            print(f"  📄 {parsed['title'][:55]}")
            pid,purl=post_to_wp(parsed,section["id"])
            if pid:
                print(f"  ✅ ID:{pid} → {purl}")
                results.append({"section":section["name"],"reporter":reporter["name"],
                                "title":parsed["title"],"url":purl,
                                "time":datetime.now().strftime("%H:%M")})
        if si<len(SECTIONS)-1:
            gap=SECTION_GAP_MIN*60+random.randint(-120,180)
            time.sleep(gap)
    print(f"\n  ✅ 완료: {len(results)}개")
    return results


if __name__ == "__main__":
    while True:
        results=run_daily()
        fname=f"news_en_{datetime.now().strftime('%Y%m%d')}.json"
        with open(fname,"w",encoding="utf-8") as f:
            json.dump(results,f,ensure_ascii=False,indent=2)
        gap=360*60+random.randint(-1800,1800)
        print(f"\n  ⏰ 다음 라운드: {gap//3600}시간 후")
        time.sleep(gap)
