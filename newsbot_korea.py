#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
koreanews365.com 한국어 뉴스봇
- 한국 메이저 신문 RSS 수집
- 9개 섹션 × 3개 = 하루 27개
- Gemini로 리라이팅
- 가상 기자: 김민수, 박지아, 이현우, 최서연, 정도윤
- 24시간 자동 발행
"""

import os, json, time, random, requests, base64, re
from datetime import datetime
import xml.etree.ElementTree as ET

GEMINI_API_KEY = "AQ.Ab8RN6Je6ngXK-4cSMxL05o3jlfF06RNHJtwz3XlPdB6zqLFbA"
GEMINI_MODEL   = "gemini-2.5-flash"
PEXELS_KEY     = "41q16JQ0qBM123kTUgEk2YKAfK3e43l6NCErWoWn0Fv41Zmdfub0XAs8"
PIXABAY_KEY    = "u_g0pmau3m85"

WP_URL  = "https://koreanews365.com"
WP_USER = "huh0303@gmail.com"
WP_PASS = "dqn2 VR2L WaR0 sJmq GHeh fgYG"

# 가상 기자진
REPORTERS = [
    {"name": "김민수", "title": "정치·경제 전문기자"},
    {"name": "박지아", "title": "사회·문화 전문기자"},
    {"name": "이현우", "title": "국제·외교 전문기자"},
    {"name": "최서연", "title": "K컬처·라이프 전문기자"},
    {"name": "정도윤", "title": "산업·IT 전문기자"},
]

# 9개 섹션 (카테고리 슬러그는 WP에서 생성 후 ID 조회)
SECTIONS = [
    {"name": "정치",   "slug": "politics",  "id": None,
     "rss": ["https://www.chosun.com/arc/outboundfeeds/rss/category/politics/",
             "https://rss.joins.com/joins_politics_list.xml"]},
    {"name": "경제",   "slug": "economy",   "id": None,
     "rss": ["https://www.chosun.com/arc/outboundfeeds/rss/category/economy/",
             "https://rss.joins.com/joins_money_list.xml"]},
    {"name": "사회",   "slug": "society",   "id": None,
     "rss": ["https://www.chosun.com/arc/outboundfeeds/rss/category/national/",
             "https://rss.joins.com/joins_society_list.xml"]},
    {"name": "군사·안보","slug": "military", "id": None,
     "rss": ["https://www.chosun.com/arc/outboundfeeds/rss/category/national/",
             "https://rss.joins.com/joins_politics_list.xml"]},
    {"name": "외교·국제","slug": "international","id": None,
     "rss": ["https://www.chosun.com/arc/outboundfeeds/rss/category/international/",
             "https://rss.joins.com/joins_world_list.xml"]},
    {"name": "K-Culture","slug": "k-culture","id": None,
     "rss": ["https://www.chosun.com/arc/outboundfeeds/rss/category/entertainment/",
             "https://rss.joins.com/joins_culture_list.xml"]},
    {"name": "K-헬스",  "slug": "k-health-news","id": None,
     "rss": ["https://www.chosun.com/arc/outboundfeeds/rss/category/life/",
             "https://rss.joins.com/joins_living_list.xml"]},
    {"name": "K-뷰티",  "slug": "k-beauty-news","id": None,
     "rss": ["https://www.chosun.com/arc/outboundfeeds/rss/category/life/",
             "https://rss.joins.com/joins_living_list.xml"]},
    {"name": "IT·과학", "slug": "tech-science","id": None,
     "rss": ["https://www.chosun.com/arc/outboundfeeds/rss/category/it-science/",
             "https://rss.joins.com/joins_it_list.xml"]},
]

ARTICLES_PER_SECTION = 5
POST_GAP_MIN = 8   # 섹션 내 기사 간격(분)
SECTION_GAP_MIN = 15  # 섹션 간 간격(분)


def fetch_rss(url):
    """RSS 피드에서 기사 목록 가져오기"""
    try:
        r = requests.get(url, timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"})
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = []
        for item in root.findall(".//item")[:10]:
            title = item.findtext("title", "").strip()
            desc  = item.findtext("description", "").strip()
            link  = item.findtext("link", "").strip()
            if title and len(title) > 5:
                # HTML 태그 제거
                desc = re.sub(r'<[^>]+>', '', desc)[:500]
                items.append({"title": title, "desc": desc, "link": link})
        return items
    except Exception as e:
        return []


def get_news_items(section, count=5):
    """섹션별 뉴스 수집"""
    all_items = []
    for rss_url in section["rss"]:
        items = fetch_rss(rss_url)
        all_items.extend(items)
    # 중복 제거 후 랜덤 선택
    seen = set()
    unique = []
    for item in all_items:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique.append(item)
    return random.sample(unique, min(count, len(unique))) if unique else []


def build_news_prompt(news_item, section, reporter):
    return f"""당신은 {reporter['name']} 기자({reporter['title']})입니다.
아래 뉴스를 바탕으로 완전히 새로운 독창적인 기사를 작성하세요.
절대 원문을 그대로 복사하지 마세요. 완전히 새로운 문장으로 재작성하세요.

[원본 뉴스 제목]: {news_item['title']}
[원본 내용 요약]: {news_item['desc'][:300]}
[섹션]: {section['name']}
[기자]: {reporter['name']} ({reporter['title']})
[목표 글자수]: 1500~2500자

[기사 작성 조건]
① 제목: 원본과 다른 새로운 헤드라인, 핵심 키워드 포함, 40~60자
② 메타디스크립션: 120~155자 요약
③ 리드문: 첫 문단에 5W1H 핵심 내용
④ H2 4개이상, H3 각 2개이상
⑤ 통계·수치 3개이상 (출처 명시)
⑥ 전문가 또는 관계자 인용 (창작 가능)
⑦ 외부링크 3개: 정부기관·공식사이트
⑧ 내부링크 3개: koreanews365.com 관련 기사
⑨ 표(Table) 1개이상
⑩ 태그 8개: <!-- TAGS: 태그1, 태그2, ... -->
⑪ 이미지 2곳: <!-- IMAGE: 영어검색어 --> <!-- ALT: 한국어설명 -->
⑫ 기사 마무리: 전망 및 시사점
⑬ 바이라인: <!-- BYLINE: {reporter['name']} {reporter['title']} -->

[출력 형식]
첫째줄: TITLE: [제목]
둘째줄: <!-- META_DESCRIPTION: [요약] -->
셋째줄: <!-- TAGS: 태그1, 태그2, 태그3, 태그4, 태그5, 태그6, 태그7, 태그8 -->
넷째줄: <!-- BYLINE: {reporter['name']} {reporter['title']} -->
다섯째줄부터: 본문 HTML"""


def call_gemini(prompt):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent")
    try:
        r = requests.post(url,
            headers={"Content-Type": "application/json",
                     "x-goog-api-key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 0.7,
                                       "maxOutputTokens": 8192}},
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
            headers={"Authorization": PEXELS_KEY}, timeout=10)
        photos = r.json().get("photos", [])
        if photos:
            p = random.choice(photos)
            return {"src": p["src"]["large"], "credit": f'Photo by {p["photographer"]} on Pexels'}
    except: pass
    try:
        r = requests.get(
            f"https://pixabay.com/api/?key={PIXABAY_KEY}"
            f"&q={requests.utils.quote(query)}&image_type=photo&per_page=5&safesearch=true",
            timeout=10)
        hits = r.json().get("hits", [])
        if hits:
            p = random.choice(hits)
            return {"src": p["webformatURL"], "credit": "Image from Pixabay"}
    except: pass
    return {}


def process_content(raw):
    lines  = raw.strip().split("\n")
    title  = ""
    meta   = ""
    tags_s = ""
    byline = ""
    content= raw

    for i, line in enumerate(lines):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
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
            return (f'<figure class="wp-block-image size-large">'
                    f'<img src="{img["src"]}" alt="{alt}" loading="lazy"/>'
                    f'<figcaption>{img["credit"]}</figcaption></figure>')
        return f'<p><em>[이미지: {alt}]</em></p>'

    content = re.sub(r'<!-- IMAGE: (.+?) -->\s*<!-- ALT: (.+?) -->',
                     img_replacer, content, flags=re.DOTALL)

    # 바이라인 추가
    if byline:
        content = f'<p class="byline" style="color:#666;font-size:13px;border-bottom:1px solid #eee;padding-bottom:8px;margin-bottom:16px">✍️ {byline}</p>\n' + content

    tags = [t.strip() for t in tags_s.split(",") if t.strip()]
    return {"title": title or "뉴스 기사", "meta": meta, "content": content, "tags": tags}


def get_cat_id(slug):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    try:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/categories?slug={slug}",
            headers={"Authorization": f"Basic {auth}"}, timeout=10)
        data = r.json()
        if data:
            return data[0]["id"]
        # 없으면 생성
        r2 = requests.post(
            f"{WP_URL}/wp-json/wp/v2/categories",
            headers={"Authorization": f"Basic {auth}",
                     "Content-Type": "application/json"},
            json={"name": slug, "slug": slug}, timeout=10)
        return r2.json().get("id", 1)
    except: return 1


def post_to_wp(parsed, cat_id):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    # 태그 등록
    tag_ids = []
    for tag in parsed.get("tags", [])[:8]:
        try:
            r = requests.post(f"{WP_URL}/wp-json/wp/v2/tags",
                headers={"Authorization": f"Basic {auth}",
                         "Content-Type": "application/json"},
                json={"name": tag}, timeout=10)
            if r.status_code in [200,201]:
                tag_ids.append(r.json()["id"])
            elif r.status_code == 400:
                sr = requests.get(
                    f"{WP_URL}/wp-json/wp/v2/tags?search={requests.utils.quote(tag)}",
                    headers={"Authorization": f"Basic {auth}"}, timeout=10)
                if sr.json(): tag_ids.append(sr.json()[0]["id"])
        except: pass

    try:
        r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts",
            headers={"Authorization": f"Basic {auth}",
                     "Content-Type": "application/json"},
            json={"title": parsed["title"], "content": parsed["content"],
                  "status": "publish", "categories": [cat_id],
                  "tags": tag_ids,
                  "meta": {"rank_math_description": parsed["meta"]}},
            timeout=30)
        r.raise_for_status()
        return r.json().get("id"), r.json().get("link","")
    except Exception as e:
        print(f"  ❌ WP 오류: {e}")
        return None, None


def run_daily():
    print(f"\n{'═'*55}")
    print(f"  📰 koreanews365.com 뉴스봇 시작")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  9개 섹션 × 5개 = 45개 기사")
    print(f"{'═'*55}")

    # 카테고리 ID 초기화
    for sec in SECTIONS:
        if sec["id"] is None:
            sec["id"] = get_cat_id(sec["slug"])
        print(f"  {sec['name']:10s} → 카테고리 ID: {sec['id']}")

    results = []
    reporter_idx = 0

    for sec_i, section in enumerate(SECTIONS):
        print(f"\n\n  📌 섹션: [{section['name']}]")

        # RSS에서 뉴스 수집
        news_items = get_news_items(section, ARTICLES_PER_SECTION)
        if not news_items:
            print(f"  ⚠️  뉴스 수집 실패, 키워드 기반으로 대체")
            news_items = [{"title": f"{section['name']} 최신 동향 2026",
                          "desc": f"{section['name']} 분야의 최신 동향과 이슈를 분석합니다.",
                          "link": ""}
                         for _ in range(ARTICLES_PER_SECTION)]

        for art_i, news in enumerate(news_items):
            if art_i > 0:
                gap = POST_GAP_MIN * 60 + random.randint(-60, 120)
                print(f"\n  ⏳ {gap//60}분 대기...")
                time.sleep(gap)

            reporter = REPORTERS[reporter_idx % len(REPORTERS)]
            reporter_idx += 1

            print(f"\n  [{sec_i+1}/9] [{art_i+1}/5] {section['name']}")
            print(f"  📰 원본: {news['title'][:50]}")
            print(f"  ✍️  기자: {reporter['name']}")
            print(f"  🧠 Gemini 리라이팅 중...")

            raw = call_gemini(build_news_prompt(news, section, reporter))
            if not raw:
                continue

            parsed = process_content(raw)
            print(f"  📄 {parsed['title'][:55]}")

            pid, purl = post_to_wp(parsed, section["id"])
            if pid:
                print(f"  ✅ 발행! ID:{pid}")
                print(f"  🔗 {purl}")
                results.append({"section": section["name"], "reporter": reporter["name"],
                                "title": parsed["title"], "url": purl,
                                "time": datetime.now().strftime("%H:%M")})

        # 섹션 간 대기
        if sec_i < len(SECTIONS)-1:
            gap = SECTION_GAP_MIN * 60 + random.randint(-120, 180)
            print(f"\n  ⏰ 다음 섹션까지 {gap//60}분 대기...")
            time.sleep(gap)

    print(f"\n{'═'*55}")
    print(f"  ✅ 완료: {len(results)}개 기사 발행")
    print(f"{'═'*55}")
    return results


if __name__ == "__main__":
    while True:
        results = run_daily()
        fname = f"news_ko_{datetime.now().strftime('%Y%m%d')}.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        # 다음 라운드 6시간 후
        gap = 360 * 60 + random.randint(-1800, 1800)
        print(f"\n  ⏰ 다음 라운드: {gap//3600}시간 후")
        time.sleep(gap)
