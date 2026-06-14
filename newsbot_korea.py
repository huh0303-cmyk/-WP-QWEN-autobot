#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
koreanews365.com 대한민국 정통 인터넷 신문 뉴스봇 (무중단 안정성 최우선 버전)
- 이미지가 있으면 삽입, 에러 나거나 없으면 없는 대로 [보도사진] 텍스트 대체 후 무조건 발행
- 9개 섹션 × 3개 = 하루 27개 자동 송고 및 예외 차단
"""

import os, json, time, random, requests, base64, re
from datetime import datetime
import xml.etree.ElementTree as ET

# ══════════════════════════════════════════════
#   ★ API 인프라 및 워드프레스 설정 ★
# ══════════════════════════════════════════════
QWEN_API_KEY   = os.environ.get("QWEN_API_KEY", "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")
QWEN_MODEL     = "qwen-2.5-72b-instruct"
QWEN_API_URL   = "https://api.groq.com/openai/v1/chat/completions"

PEXELS_KEY     = os.environ.get("PEXELS_KEY", "41q16JQ0qBM123kTUgEk2YKAfK3e43l6NCErWoWn0Fv41Zmdfub0XAs8")
PIXABAY_KEY    = os.environ.get("PIXABAY_KEY", "u_g0pmau3m85")

WP_URL  = "https://koreanews365.com"
WP_USER = os.environ.get("WP_USER", "huh0303@gmail.com")
WP_PASS = os.environ.get("WP_PASS", "dqn2 VR2L WaR0 sJmq GHeh fgYG")

# ── 한국 언론사 전문 기자단 풀 ──────────
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
    {"name": "K-IHealth",  "slug": "k-health-news","id": None,
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
POST_GAP_MIN = 3       
SECTION_GAP_MIN = 5

# ──────────────────────────────────────────────

def fetch_rss(url):
    try:
        r = requests.get(url, timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NewsPaperBot/2.5"})
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


def get_news_items(section, count=3):
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
    return f"""당신은 대한민국 권위 있는 인터넷 종합 일간지 'koreanews365.com'의 {reporter['name']} {reporter['title']}입니다.
제공된 소스 뉴스를 바탕으로, 날카로운 통찰력과 객관적 서술이 돋보이는 독창적인 단독 기사를 작성하십시오.

[원본 출처 헤드라인]: {news_item['title']}
[원본 사건 요약 정보]: {news_item['desc'][:300]}
[배정 섹션 데스크]: {section['name']}
[취재 및 작성 기자]: {reporter['name']} ({reporter['title']})

══════════════════════════
[GEMS 대한민국 정통 언론사 기사 지침]
══════════════════════════
1. 스마트폰 모바일 가독성 극대화 (★최우선 필수)
- 하나의 문단(<p> 태그) 내부에는 오직 딱 1개의 문장만 배치하며 문단과 문단 사이에는 무조건 빈 줄 공백을 배치하십시오.
2. 신문 기사체 구조화 구성
- 본문 분량은 최소 1,200자 ~ 1,600자 내외로 무겁게 구성하십시오.
- 본문의 논리적 입체감을 위해 H2 태그 3개 이상, H3 태그를 단락별로 짜임새 있게 배치하십시오.
3. 필수 기사 구성 요소 및 이미지 마커
- 기사 요약 정리용 깔끔한 HTML 표(Table)를 1개 이상 반드시 구현하십시오.
- **중요**: 이미지 배치를 위해 본문 중 가장 흐름이 자연스러운 위치 2곳에 정확히 `[IMAGE: 이미지검색어]` 형태의 마커를 삽입하십시오.
- 기사 마무리는 반드시 '전망 및 시사점' 섹션으로 끝맺음하십시오.

[출력 형식 가이드라인]
첫째줄: TITLE: [창작된 뉴스 제목]
둘째줄: META_DESCRIPTION: [검색최적화용 요약문]
셋째줄: SLUG: [영문 슬러그 주소]
넷째줄: TAGS: [쉼표로 구분된 태그 8~10개]
다섯째줄: BYLINE: {reporter['name']} {reporter['title']}
여섯째줄부터: 본문 HTML 소스 코드"""


def call_qwen(prompt):
    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": QWEN_MODEL,
        "messages": [
            {"role": "system", "content": "당신은 대한민국 최고의 디지털 언론사 수석 논설위원이자 SEO 마스터입니다."},
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
        print(f"   ❌ Qwen API 통신 오류: {e}")
        time.sleep(12)
        return None


def get_image(query):
    # API가 에러나거나 이미지가 없으면 빈 딕셔너리를 던져 텍스트 마커가 정상 작동하도록 차단막 구축
    try:
        r = requests.get(
            f"https://api.pexels.com/v1/search?query={query}&per_page=5&orientation=landscape",
            headers={"Authorization": PEXELS_KEY}, timeout=8)
        photos = r.json().get("photos", [])
        if photos:
            p = random.choice(photos)
            return {"src": p["src"]["large"], "credit": f'사진출처: Pexels / 촬영: {p["photographer"]}'}
    except: pass
    
    try:
        r = requests.get(
            f"https://pixabay.com/api/?key={PIXABAY_KEY}"
            f"&q={requests.utils.quote(query)}&image_type=photo&per_page=5&safesearch=true",
            timeout=8)
        hits = r.json().get("hits", [])
        if hits:
            p = random.choice(hits)
            return {"src": p["webformatURL"], "credit": "이미지 출처: Pixabay 공유 라이선스"}
    except: pass
    return {}


def process_content(raw):
    raw = raw.strip()
    raw = re.sub(r'^```[a-zA-Z]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw)
    raw = raw.strip()

    lines  = raw.strip().split("\n")
    title, slug, meta, tags_s, byline, content = "", "", "", "", "", raw

    for i, line in enumerate(lines):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip().strip('`"\' ')
        elif line.startswith("SLUG:"):
            slug = line.replace("SLUG:", "").strip()
            slug = re.sub(r'[^a-z0-9\-]', '', slug.lower().replace(" ", "-"))
            slug = re.sub(r'-+', '-', slug).strip('-')
        elif line.startswith("META_DESCRIPTION:"):
            meta = line.replace("META_DESCRIPTION:", "").strip()
        elif line.startswith("TAGS:"):
            tags_s = line.replace("TAGS:", "").strip()
        elif line.startswith("BYLINE:"):
            byline = line.replace("BYLINE:", "").strip()
        
        if title and meta and (i > 3):
            content = "\n".join(lines[i+1:])
            break

    # 이미지 서칭 결과 유무와 전혀 무관하게 정형화 처리 (★핵심 수정코드)
    def img_replacer(m):
        query = m.group(1).strip()
        img = get_image(query)
        if img and img.get("src"):
            return (f'<figure class="wp-block-image size-large aligncenter" style="margin:25px auto; text-align:center;">'
                    f'<img src="{img["src"]}" alt="{query}" loading="lazy" style="border-radius:6px; max-width:100%; height:auto;"/>'
                    f'<figcaption style="font-size:12px; color:#777; margin-top:5px;">{img["credit"]}</figcaption></figure>')
        # 이미지가 없으면 무시하고 텍스트 문구로 대체하여 깨짐 없이 통과
        return f'<p style="text-align:center; color:#888; margin:20px 0;"><em>[보도사진: {query}]</em></p>'

    content = re.sub(r'\[IMAGE:\s*([^\]]+)\]', img_replacer, content)

    if byline:
        content = f'<p class="byline" style="color:#555; font-weight:bold; font-size:14px; border-bottom:2px solid #222; padding-bottom:6px; margin-bottom:20px;">✍️ {byline}</p>\n' + content

    tags = [t.strip() for t in tags_s.split(",") if t.strip()][:10]
    return {"title": title or "인터넷 종합 뉴스", "slug": slug, "meta": meta, "content": content, "tags": tags}


def get_cat_id(slug):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    try:
        r = requests.get(f"{WP_URL}/wp-json/wp/v2/categories?slug={slug}",
                         headers={"Authorization": f"Basic {auth}"}, timeout=10)
        data = r.json()
        if data: return data[0]["id"]
        
        r2 = requests.post(f"{WP_URL}/wp-json/wp/v2/categories",
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
            json={"name": slug, "slug": slug}, timeout=10)
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
        except Exception: pass

    try:
        payload = {
            "title": parsed["title"], 
            "content": parsed["content"],
            "status": "publish", 
            "categories": [cat_id], 
            "tags": tag_ids,
            "meta": {"rank_math_description": parsed["meta"]}
        }
        if parsed.get("slug"):
            payload["slug"] = parsed["slug"]

        r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts",
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
            json=payload, timeout=30)
        r.raise_for_status()
        return r.json().get("id"), r.json().get("link", "")
    except Exception as e:
        print(f"  ❌ 워드프레스 뉴스 발행 실패: {e}")
        return None, None


def run_daily():
    print(f"\n📰 미디어 통합 자동화 봇 발행 가동 시작")
    
    for sec in SECTIONS:
        if sec["id"] is None:
            sec["id"] = get_cat_id(sec["slug"])

    results = []
    used_reporters = []

    for sec_i, section in enumerate(SECTIONS):
        news_items = get_news_items(section, ARTICLES_PER_SECTION)
        if not news_items:
            news_items = [{"title": f"{section['name']} 부문 심층 분석 리포트",
                          "desc": f"2026년 {section['name']} 지형의 핵심 쟁점을 분석 보도합니다.", "link": ""}]

        for art_i, news in enumerate(news_items):
            if art_i > 0:
                time.sleep(POST_GAP_MIN * 60)

            choices = [r for r in REPORTERS if r["name"] != (used_reporters[-1]["name"] if used_reporters else None)]
            reporter = random.choice(choices)
            used_reporters.append(reporter)

            raw = call_qwen(build_news_prompt(news, section, reporter))
            if not raw: continue

            parsed = process_content(raw)
            pid, purl = post_to_wp(parsed, section["id"])
            
            if pid:
                print(f"  ✅ [송고 완료] ID:{pid} | 링크: {purl}")
                results.append({
                    "section": section["name"], 
                    "reporter": reporter["name"],
                    "title": parsed["title"], 
                    "url": purl,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                })

    return results


if __name__ == "__main__":
    results = run_daily()
    fname = f"news_ko_{datetime.now().strftime('%Y%m%d')}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
