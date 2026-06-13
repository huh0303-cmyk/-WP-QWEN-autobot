#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
koreanews365.com 한국어 뉴스봇
- 9개 섹션 × 3개 = 하루 27개, 1라운드 실행 후 종료 (GitHub Actions용)
- Gemini로 리라이팅, 1000~1500자 신문 기사체
- 기자풀 10명 (한국 5 + 외국 5, 영미식 성)
"""

import os, json, time, random, requests, base64, re
from datetime import datetime
import xml.etree.ElementTree as ET

GEMINI_API_KEY = "AQ.Ab8RN6L1RxG7CUO1FSFAl9E53oOM934QWAA3AqcFIWpA3Q7h5g"
GEMINI_MODEL   = "gemini-2.5-flash"
PEXELS_KEY     = "41q16JQ0qBM123kTUgEk2YKAfK3e43l6NCErWoWn0Fv41Zmdfub0XAs8"
PIXABAY_KEY    = "u_g0pmau3m85"

WP_URL  = "https://koreanews365.com"
WP_USER = "huh0303@gmail.com"
WP_PASS = "dqn2 VR2L WaR0 sJmq GHeh fgYG"

# ── 기자 풀 (한국 5명 + 외국 5명, 영미식 성) ──────────
REPORTERS = [
    {"name": "김민수", "title": "정치·경제 전문기자"},
    {"name": "박지아", "title": "사회·문화 전문기자"},
    {"name": "이현우", "title": "국제·외교 전문기자"},
    {"name": "최서연", "title": "K컬처·라이프 전문기자"},
    {"name": "정도윤", "title": "산업·IT 전문기자"},
    {"name": "Sarah Mitchell",  "title": "Senior Political Correspondent"},
    {"name": "James Anderson",  "title": "Business & Economy Reporter"},
    {"name": "Emily Carter",    "title": "Culture & Lifestyle Editor"},
    {"name": "David Thompson",  "title": "International Affairs Correspondent"},
    {"name": "Rachel Bennett",  "title": "Technology & Innovation Reporter"},
]

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

ARTICLES_PER_SECTION = 3
POST_GAP_MIN = 8
SECTION_GAP_MIN = 15


def fetch_rss(url):
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
                desc = re.sub(r'<[^>]+>', '', desc)[:500]
                items.append({"title": title, "desc": desc, "link": link})
        return items
    except Exception:
        return []


def get_news_items(section, count=5):
    all_items = []
    for rss_url in section["rss"]:
        items = fetch_rss(rss_url)
        all_items.extend(items)
    seen = set()
    unique = []
    for item in all_items:
        if item["title"] not in seen:
            seen.add(item["title"])
            unique.append(item)
    return random.sample(unique, min(count, len(unique))) if unique else []


def build_news_prompt(news_item, section, reporter):
    return f"""당신은 {reporter['name']} 기자({reporter['title']})입니다.
아래 뉴스를 바탕으로 완전히 새로운 독창적인 신문 기사를 작성하세요.
절대 원문을 그대로 복사하지 마세요. 완전히 새로운 문장으로 재작성하세요.

[원본 뉴스 제목]: {news_item['title']}
[원본 내용 요약]: {news_item['desc'][:300]}
[섹션]: {section['name']}
[기자]: {reporter['name']} ({reporter['title']})

══════════════════════════
[GEMS 신문기사 작성 지침]
══════════════════════════

1. 분량 및 형식
- 본문 1000~1500자 (반드시 준수, 진짜 신문 기사처럼 간결하고 핵심만)
- 제목: 원본과 다른 새로운 헤드라인, 핵심 키워드 포함 (40~60자)
- 첫 100자 이내(리드문)에 5W1H 핵심 내용 요약
- H2 3개 이상, H3 각 1~2개

2. 신문 기사체 원칙
- 객관적, 사실 기반, 육하원칙
- 통계·수치 3개 이상 (출처 명시)
- 전문가 또는 관계자 인용 (창작 가능)
- 모든 문단은 2~3문장 이내로 짧게, 문단 사이 빈 줄 유지 (모바일 가독성)

3. 링크
- 외부링크 3개: 정부기관·공식사이트 (target="_blank")
- 내부링크 3개: koreanews365.com 관련 기사 (예: https://koreanews365.com/category/{section['slug']}/)

4. 구성요소
- 표(Table) 1개 이상
- 태그 10개: <!-- TAGS: 태그1, 태그2, ... -->
- 이미지 2곳: <!-- IMAGE: 영어검색어 --> <!-- ALT: 한국어설명 -->
- 기사 마무리: '전망 및 시사점' 섹션
- 바이라인: <!-- BYLINE: {reporter['name']} {reporter['title']} -->

[출력 형식]
첫째줄: TITLE: [제목]
둘째줄: <!-- SLUG: [영어 슬러그, 소문자, 단어는 하이픈으로 연결, 5~8단어] -->
셋째줄: <!-- META_DESCRIPTION: [영어 120자 내외 요약] -->
넷째줄: <!-- TAGS: 태그1, 태그2, ..., 태그10 (정확히 10개) -->
다섯째줄: <!-- BYLINE: {reporter['name']} {reporter['title']} -->
여섯째줄부터: 본문 HTML (h1 태그 사용 금지)"""


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
    raw = raw.strip()
    raw = re.sub(r'^```[a-zA-Z]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw)
    raw = raw.strip()

    lines  = raw.strip().split("\n")
    title  = ""
    slug   = ""
    meta   = ""
    tags_s = ""
    byline = ""
    content= raw

    for i, line in enumerate(lines):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
            title = re.sub(r'^```[a-zA-Z]*\s*', '', title)
            title = title.strip('`"\' ')
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
            return (f'<figure class="wp-block-image size-large">'
                    f'<img src="{img["src"]}" alt="{alt}" loading="lazy"/>'
                    f'<figcaption>{img["credit"]}</figcaption></figure>')
        return f'<p><em>[이미지: {alt}]</em></p>'

    content = re.sub(r'<!-- IMAGE: (.+?) -->\s*<!-- ALT: (.+?) -->',
                     img_replacer, content, flags=re.DOTALL)

    if byline:
        content = f'<p class="byline" style="color:#666;font-size:13px;border-bottom:1px solid #eee;padding-bottom:8px;margin-bottom:16px">✍️ {byline}</p>\n' + content

    tags = [t.strip() for t in tags_s.split(",") if t.strip()][:10]
    return {"title": title or "뉴스 기사", "slug": slug, "meta": meta, "content": content, "tags": tags}


def seo_score(parsed):
    c, t, m = parsed["content"], parsed["title"], parsed["meta"]
    checks = [
        ("제목 존재",              len(t) >= 20),
        ("메타디스크립션 80자+",  len(m) >= 80),
        ("본문 1000자 이상",      len(c) >= 1000),
        ("본문 1700자 이하",      len(c) <= 1700),
        ("H2 3개 이상",           c.count("<h2") >= 3),
        ("H3 1개 이상",           c.count("<h3") >= 1),
        ("이미지+ALT",            "<img" in c and 'alt="' in c),
        ("테이블 1개 이상",       c.count("<table") >= 1),
        ("외부링크 3개 이상",     c.count('target="_blank"') >= 3),
        ("내부링크 3개 이상",     c.count("koreanews365.com") >= 3),
        ("바이라인",              "byline" in c.lower()),
        ("태그 8개 이상",         len(parsed.get("tags", [])) >= 8),
        ("전망 섹션",             "전망" in c or "시사점" in c),
    ]
    score = round(sum(100/len(checks) for _, ok in checks if ok))
    passed = sum(1 for _, ok in checks if ok)
    print(f"  ┌─ 품질 체크 ({passed}/{len(checks)}) ──────────────", flush=True)
    for name, ok in checks:
        print(f"  │ {'✅' if ok else '❌'} {name}", flush=True)
    print(f"  └─ 점수: {score}점 {'🎉' if score >= 90 else '⚠️'}", flush=True)
    return score


def get_cat_id(slug):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    try:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/categories?slug={slug}",
            headers={"Authorization": f"Basic {auth}"}, timeout=10)
        data = r.json()
        if data:
            return data[0]["id"]
        r2 = requests.post(
            f"{WP_URL}/wp-json/wp/v2/categories",
            headers={"Authorization": f"Basic {auth}",
                     "Content-Type": "application/json"},
            json={"name": slug, "slug": slug}, timeout=10)
        return r2.json().get("id", 1)
    except: return 1


def post_to_wp(parsed, cat_id):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    tag_ids = []
    for tag in parsed.get("tags", [])[:10]:
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
            else:
                print(f"     ⚠️ 태그 '{tag}' 실패: {r.status_code} {r.text[:120]}")
        except Exception as e:
            print(f"     ⚠️ 태그 '{tag}' 오류: {e}")
    print(f"  🏷️  태그 등록: {len(tag_ids)}/{len(parsed.get('tags',[])[:10])} (IDs: {tag_ids})")

    try:
        r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts",
            headers={"Authorization": f"Basic {auth}",
                     "Content-Type": "application/json"},
            json={"title": parsed["title"], "content": parsed["content"],
                  "status": "publish", "categories": [cat_id],
                  "tags": tag_ids,
                  **({"slug": parsed["slug"]} if parsed.get("slug") else {}),
                  "meta": {"rank_math_description": parsed["meta"]}},
            timeout=30)
        r.raise_for_status()
        print(f"  🔗 슬러그: {r.json().get('slug','')}")
        return r.json().get("id"), r.json().get("link","")
    except Exception as e:
        print(f"  ❌ WP 오류: {e}")
        return None, None


def run_daily():
    print(f"\n{'═'*55}")
    print(f"  📰 koreanews365.com 뉴스봇 시작")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  9개 섹션 × {ARTICLES_PER_SECTION}개 = {9*ARTICLES_PER_SECTION}개 기사")
    print(f"{'═'*55}")

    for sec in SECTIONS:
        if sec["id"] is None:
            sec["id"] = get_cat_id(sec["slug"])
        print(f"  {sec['name']:10s} → 카테고리 ID: {sec['id']}")

    results = []
    used_reporters = []

    for sec_i, section in enumerate(SECTIONS):
        print(f"\n\n  📌 섹션: [{section['name']}]")

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

            # 직전 글과 다른 기자를 랜덤 선택 (가능한 경우)
            choices = [r for r in REPORTERS if r["name"] != (used_reporters[-1]["name"] if used_reporters else None)]
            reporter = random.choice(choices)
            used_reporters.append(reporter)

            print(f"\n  [{sec_i+1}/9] [{art_i+1}/{ARTICLES_PER_SECTION}] {section['name']}")
            print(f"  📰 원본: {news['title'][:50]}")
            print(f"  ✍️  기자: {reporter['name']}")
            print(f"  🧠 Gemini 리라이팅 중...")

            raw = call_gemini(build_news_prompt(news, section, reporter))
            if not raw:
                continue

            parsed = process_content(raw)
            score = seo_score(parsed)

            if score < 80:
                print("  🔄 80점 미만 → 재생성...", flush=True)
                raw2 = call_gemini(build_news_prompt(news, section, reporter))
                if raw2:
                    parsed2 = process_content(raw2)
                    score2 = seo_score(parsed2)
                    if score2 > score:
                        parsed, score = parsed2, score2
                if score < 80:
                    print(f"  ⚠️ 재생성 후에도 {score}점, 최선의 결과로 발행", flush=True)

            print(f"  📄 {parsed['title'][:55]}")

            pid, purl = post_to_wp(parsed, section["id"])
            if pid:
                print(f"  ✅ 발행! ID:{pid} 품질:{score}점")
                print(f"  🔗 {purl}")
                results.append({"section": section["name"], "reporter": reporter["name"],
                                "title": parsed["title"], "url": purl, "score": score,
                                "time": datetime.now().strftime("%H:%M")})

        if sec_i < len(SECTIONS)-1:
            gap = SECTION_GAP_MIN * 60 + random.randint(-120, 180)
            print(f"\n  ⏰ 다음 섹션까지 {gap//60}분 대기...")
            time.sleep(gap)

    print(f"\n{'═'*55}")
    print(f"  ✅ 완료: {len(results)}개 기사 발행")
    print(f"{'═'*55}")
    return results


if __name__ == "__main__":
    results = run_daily()
    fname = f"news_ko_{datetime.now().strftime('%Y%m%d')}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  📁 결과 저장: {fname}")
