#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import time
import random
import requests
import base64
import re
from datetime import datetime
import xml.etree.ElementTree as ET
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 1. 시스템 설정 및 시크릿 연동
# ==========================================

# AI 엔진 API 설정
QWEN_API_KEY   = os.environ.get("QWEN_API_KEY")
QWEN_MODEL     = "qwen-2.5-72b-instruct"
QWEN_API_URL   = "https://api.groq.com/openai/v1/chat/completions"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 이미지 API 설정
PEXELS_KEY     = os.environ.get("PEXELS_KEY")
PIXABAY_KEY    = os.environ.get("PIXABAY_KEY")

# 워드프레스 설정
WP_URL  = "https://theseouljournal.com"
WP_USER = "huh0303@gmail.com"
WP_PASS = os.environ.get("WP_PASS")

# 구글 시트 설정
SPREADSHEET_ID = "1SYxMJxmiQNnmiG5dElH-kVKuR5Ly17CI07xmY_Xm0Bw"
GCP_SA_KEY_JSON = os.environ.get("GCP_SA_KEY") # 구글 서비스 계정 JSON 문자열

# 발행 스케줄 설정
ARTICLES_PER_SECTION = 3
POST_GAP_MIN = 3
SECTION_GAP_MIN = 5

# ==========================================
# 2. 가상 기자단 데이터 (요청 반영)
# ==========================================
# 랜덤 인물 사진 API (randomuser.me)를 활용한 가상 프로필 사진 url 포함
REPORTERS = [
    # 서양계 이름 (5명)
    {
        "name": "Sarah Mitchell",
        "title": "Senior Political Correspondent",
        "photo": "https://randomuser.me/api/portraits/women/44.jpg"
    },
    {
        "name": "James Anderson",
        "title": "Business & Economy Reporter",
        "photo": "https://randomuser.me/api/portraits/men/32.jpg"
    },
    {
        "name": "Emily Carter",
        "title": "Culture & Lifestyle Editor",
        "photo": "https://randomuser.me/api/portraits/women/65.jpg"
    },
    {
        "name": "David Thompson",
        "title": "International Affairs Correspondent",
        "photo": "https://randomuser.me/api/portraits/men/55.jpg"
    },
    {
        "name": "Rachel Bennett",
        "title": "Technology & Innovation Reporter",
        "photo": "https://randomuser.me/api/portraits/women/68.jpg"
    },
    # 한국계 이름 (5명)
    {
        "name": "Sarah Kim",
        "title": "Seoul City Desk Correspondent",
        "photo": "https://randomuser.me/api/portraits/women/43.jpg"
    },
    {
        "name": "James Park",
        "title": "Financial Markets Reporter",
        "photo": "https://randomuser.me/api/portraits/men/41.jpg"
    },
    {
        "name": "Emily Choi",
        "title": "K-Pop & Entertainment Editor",
        "photo": "https://randomuser.me/api/portraits/women/50.jpg"
    },
    {
        "name": "David Lee",
        "title": "North Korea Affairs Analyst",
        "photo": "https://randomuser.me/api/portraits/men/52.jpg"
    },
    {
        "name": "Rachel Yoon",
        "title": "Industry & Tech Correspondent",
        "photo": "https://randomuser.me/api/portraits/women/55.jpg"
    },
]

# 카테고리 및 RSS 소스 설정
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

# ==========================================
# 3. 핵심 유틸리티 함수
# ==========================================

def report_to_sheet(section, original_title, status, details=""):
    """구글 시트에 작업 상황을 실시간으로 보고합니다."""
    try:
        if not GCP_SA_KEY_JSON: return
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(json.loads(GCP_SA_KEY_JSON), scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([now, section, original_title, status, details])
    except Exception as e:
        print(f"❌ 구글 시트 보고 실패: {e}")

def fetch_rss(url):
    """RSS 피드에서 최신 뉴스 아이템을 수집합니다."""
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 SeoulJournalBot/2.5"})
        root = ET.fromstring(r.content)
        items = []
        for item in root.findall(".//item")[:10]:
            title = item.findtext("title","").strip()
            desc  = re.sub(r'<[^>]+>','',item.findtext("description",""))[:500]
            if title and len(title) > 5: items.append({"title":title,"desc":desc})
        return items
    except: return []

def get_news_items(section, count=3):
    """카테고리별 RSS 소스에서 중복되지 않은 뉴스 아이템을 가져옵니다."""
    all_items = []
    for url in section["rss"]: all_items.extend(fetch_rss(url))
    seen, unique = set(), []
    for item in all_items:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique.append(item)
    return random.sample(unique, min(count, len(unique))) if unique else [{"title": f"Latest {section['name']} Global Update 2026", "desc": "In-depth analysis."}]

def build_prompt(news, section, reporter):
    """AI 엔진에 전달할 프롬프트를 구성합니다. (짧고 자극적인 제목 강조)"""
    return f"""You are {reporter['name']}, {reporter['title']} at The Seoul Journal (theseouljournal.com).
Rewrite the following news source into a highly sensational, clickable, and authoritative global journalistic article.
The article must be written completely in professional English.

[SOURCE HEADLINE]: {news['title']}
[SOURCE SUMMARY]: {news['desc'][:300]}
[EDITORIAL DESK]: {section['name']}

1. Critical Mobile Readability & Structure
- Every single sentence must be kept extremely short, punchy, and distinct.
- Each paragraph (<p> tag) must contain exactly ONE sentence.
- You MUST insert a clear blank line (empty newline) between every single paragraph.

2. Article Architecture
- Length: 1200-1600 characters.
- Headline (TITLE): High-clicking, sensationalized, and VERY SHORT English SEO headline (max 60 chars).
- Lead Sentence: Summarize with massive hook within the first 100 characters.
- Subsection Breakdown: 3+ H2 headings, 1-2 H3. No H1 tags.
- Quantitative Validation: 3+ statistics with sources/years.

3. Links
- Authority Backlinks: 3+ external hyperlinks (target="_blank").
- Strategic Native Link: Naturally integrate a link to 'k-health365.com' primary domain or category.

4. Compulsory Elements
- 1+ structured HTML data table summarizing key elements.
- Insert exactly 2 image placeholders inside the body content using this exact format: [IMAGE: search_keyword | alt_text]
- End with 'Outlook and Implications' segment.

Output Structure Required:
TITLE: [Sensational Short Headline Here]
SLUG: [url-friendly-slug]
META_DESCRIPTION: [SEO Meta Summary]
TAGS: [8-10 comma-separated tags]

[HTML Content Body]"""

# ==========================================
# 4. AI 및 미디어 엔진 체계
# ==========================================

def call_qwen(prompt):
    """1순위 AI: Qwen 호출"""
    if not QWEN_API_KEY: return None
    headers = {"Authorization": f"Bearer {QWEN_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": QWEN_MODEL, "messages": [{"role": "system", "content": "You are the Editor-in-Chief of an elite international English newspaper."}, {"role": "user", "content": prompt}], "temperature": 0.65, "max_tokens": 4096
    }
    try:
        r = requests.post(QWEN_API_URL, headers=headers, json=payload, timeout=60)
        time.sleep(2)
        return r.json()["choices"][0]["message"]["content"]
    except: return None

def call_gemini(prompt):
    """2순위 AI: Gemini 백업 호출"""
    if not GEMINI_API_KEY: return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.65, "maxOutputTokens": 4096}}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        return r.json()['candidates'][0]['content']['parts'][0]['text']
    except: return None

def generate_local_fallback(news, section):
    """3순위: 로컬 엔진 폴백 (기사 발행 보장)"""
    title = f"BREAKING: Global {section['name']} Gearing for Massive Shift"
    content = f"""<p>The global landscape shifts intensely following recent reports.</p><h2>Unveiling Impacts</h2><p>According to current 2026 intelligence, immediate actions are being deployed universal.</p><table><tr><th>Metric</th><th>Value</th></tr><tr><td>Urgency Index</td><td>Critical</td></tr></table><p>Discover advanced welfare measures through <a href="https://k-health365.com" target="_blank">k-health365.com</a> today.</p>"""
    return f"TITLE: {title}\nSLUG: local-{section['slug']}\nMETA_DESCRIPTION: Global update.\nTAGS: global\n\n{content}"

def get_image(query):
    """이미지 검색 (Pixabay ➡️ Pexels 순서)"""
    # 1순위: Pixabay
    if PIXABAY_KEY:
        try:
            r = requests.get(f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={requests.utils.quote(query)}&image_type=photo&per_page=5", timeout=10)
            hits = r.json().get("hits", [])
            if hits: return {"src": random.choice(hits)["webformatURL"], "credit": "via Pixabay"}
        except: pass
    # 2순위: Pexels
    if PEXELS_KEY:
        try:
            r = requests.get(f"https://api.pexels.com/v1/search?query={query}&per_page=5", headers={"Authorization":PEXELS_KEY}, timeout=10)
            photos = r.json().get("photos", [])
            if photos: p = random.choice(photos); return {"src": p["src"]["large"], "credit": f'by {p["photographer"]} on Pexels'}
        except: pass
    return {}

# ==========================================
# 5. 콘텐츠 가공 및 발행
# ==========================================

def process_content(raw, reporter):
    """AI 생성 콘텐츠 파싱, 이미지 치환, 바이라인(사진포함) 삽입"""
    raw = raw.strip()
    raw = re.sub(r'^```[a-zA-Z]*\n?|```$', '', raw) # 코드 블록 제거
    lines = raw.split("\n")
    title = slug = meta = tags_s = ""
    
    for line in lines:
        if line.startswith("TITLE:"): title = line.replace("TITLE:", "").strip().strip('`"\' ')
        elif line.startswith("SLUG:"): slug = line.replace("SLUG:", "").strip()
        elif line.startswith("META_DESCRIPTION:"): meta = line.replace("META_DESCRIPTION:", "").strip()
        elif line.startswith("TAGS:"): tags_s = line.replace("TAGS:", "").strip()

    # 순수 본문 추출
    content_lines = [l for l in lines if not any(l.startswith(prefix) for prefix in ["TITLE:", "SLUG:", "META_DESCRIPTION:", "TAGS:"])]
    content = "\n".join(content_lines).strip()

    # 이미지 플레이스홀더 치환
    def img_replacer(m):
        query, alt = m.group(1).strip(), m.group(2).strip()
        img = get_image(query)
        if img: return f'<figure class="wp-block-image size-large" style="margin:25px 0; text-align:center;"><img src="{img["src"]}" alt="{alt}" style="border-radius:4px;"/><figcaption style="font-size:12px; color:#666;">{img["credit"]}</figcaption></figure>'
        return f'<p style="text-align:center; color:#999;"><em>[Visual: {alt}]</em></p>'
    content = re.sub(r'\[IMAGE:\s*([^|]+)\s*\|\s*([^\]]+)\]', img_replacer, content)
    
    # --- 중요: 가상 기자 바이라인(동그란 사진 포함) HTML 삽입 ---
    byline_html = f"""
    <div class="sj-byline" style="display: flex; align-items: center; border-bottom: 2px solid #111; padding-bottom: 10px; margin-bottom: 20px;">
        <img src="{reporter['photo']}" alt="{reporter['name']}" style="width: 50px; height: 50px; border-radius: 50%; margin-right: 15px; border: 1px solid #ddd; object-fit: cover; aspect-ratio: 1/1;"/>
        <div>
            <div style="font-weight: bold; font-size: 15px; color: #111;">By {reporter['name']}</div>
            <div style="font-size: 12px; color: #666;">{reporter['title']} | The Seoul Journal Desk</div>
        </div>
    </div>
    """
    content = byline_html + content
    
    tags = [t.strip() for t in tags_s.split(",") if t.strip()][:10]
    return {"title": title or "Global Report", "slug": slug, "meta": meta, "content": content, "tags": tags}

def post_to_wp(parsed, cat_id):
    """워드프레스 REST API를 통해 기사를 최종 발행합니다."""
    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    tag_ids = []
    # 태그 처리
    for tag in parsed.get("tags", []):
        try:
            r = requests.post(f"{WP_URL}/wp-json/wp/v2/tags", headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"}, json={"name": tag}, timeout=10)
            if r.status_code in [200, 201]: tag_ids.append(r.json()["id"])
            elif r.status_code == 400:
                sr = requests.get(f"{WP_URL}/wp-json/wp/v2/tags?search={requests.utils.quote(tag)}", headers={"Authorization": f"Basic {auth}"}, timeout=10)
                if sr.json(): tag_ids.append(sr.json()[0]["id"])
        except: pass
    # 포스팅 처리
    try:
        payload = {"title": parsed["title"], "content": parsed["content"], "status": "publish", "categories": [cat_id], "tags": tag_ids, "meta": {"rank_math_description": parsed["meta"]}}
        if parsed.get("slug"): payload["slug"] = parsed["slug"]
        r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"}, json=payload, timeout=30)
        return r.json().get("id"), r.json().get("link", "")
    except: return None, None

# ==========================================
# 6. 메인 컨트롤러
# ==========================================

def run_daily():
    print("🚀 [Autobot-서울저널] 시스템 가동")
    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    
    # 카테고리 ID 획득/생성
    for sec in SECTIONS:
        try:
            r = requests.get(f"{WP_URL}/wp-json/wp/v2/categories?slug={sec['slug']}", headers={"Authorization": f"Basic {auth}"}, timeout=10)
            if r.json(): sec["id"] = r.json()[0]["id"]
            else:
                r2 = requests.post(f"{WP_URL}/wp-json/wp/v2/categories", headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"}, json={"name": sec["name"], "slug": sec["slug"]}, timeout=10)
                sec["id"] = r2.json().get("id", 1)
        except: sec["id"] = 1

    last_reporter_name = None
    
    for si, section in enumerate(SECTIONS):
        news_items = get_news_items(section, ARTICLES_PER_SECTION)
        
        for ai, news in enumerate(news_items):
            if ai > 0: time.sleep(POST_GAP_MIN * 60)
            
            # --- 중요: 기자 랜덤 배정 (이름/사진 데이터 포함) ---
            choices = [r for r in REPORTERS if r["name"] != last_reporter_name]
            reporter = random.choice(choices)
            last_reporter_name = reporter["name"]
            
            print(f" 📰 기사 생성 중: {news['title']} (Cat: {section['name']}, Reporter: {reporter['name']})")
            
            # 1. AI 호출 (Qwen ➡️ Gemini ➡️ 로컬)
            engine = "Qwen"
            raw = call_qwen(build_prompt(news, section, reporter))
            if not raw:
                engine = "Gemini"; raw = call_gemini(build_prompt(news, section, reporter))
            if not raw:
                engine = "LocalFallback"; raw = generate_local_fallback(news, section)
            
            # 2. 파싱 및 가공 (사진 포함 바이라인 삽입)
            parsed = process_content(raw, reporter)
            
            # 3. 발행
            pid, purl = post_to_wp(parsed, section["id"])
            
            # 4. 시트 보고
            if pid: report_to_sheet(section["name"], news["title"], f"Success ({engine})", purl)
            else: report_to_sheet(section["name"], news["title"], f"Failed ({engine})", "WP API Error")
            
        if si < len(SECTIONS)-1: time.sleep(SECTION_GAP_MIN * 60)
    print("🏁 시스템 종료")

if __name__ == "__main__":
    run_daily()
