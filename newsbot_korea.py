#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
koreanews365.com 대한민국 정통 인터넷 신문 뉴스봇 (Qwen Mega 버전)
- 9개 섹션 × 3개 = 하루 27개, 1라운드 실행 후 종료 (GitHub Actions 분산 스케줄용)
- Qwen 무료 API 인프라를 활용한 실시간 시사 논평 및 언론사 기사체 리라이팅
- 모바일 독자 최적화: 모든 문장 단위 극단적 분절 및 강제 여백 주입
"""

import os, json, time, random, requests, base64, re
from datetime import datetime
import xml.etree.ElementTree as ET

# ══════════════════════════════════════════════
#  ★ 100% 무료 API 인프라 및 워드프레스 기본 설정 ★
# ══════════════════════════════════════════════
# 무료 Qwen API (DashScope 또는 HuggingFace/Sambanova 등 API 엔드포인트 연동)
QWEN_API_KEY   = "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"
QWEN_MODEL     = "qwen-2.5-72b-instruct"  # 혹은 상황에 맞게 llama-3.3-70b-versatile, qwen-plus 등 지정 가능
QWEN_API_URL   = "https://api.groq.com/openai/v1/chat/completions" # 대표님 계정 인프라 엔드포인트 커스텀 고정

PEXELS_KEY     = "41q16JQ0qBM123kTUgEk2YKAfK3e43l6NCErWoWn0Fv41Zmdfub0XAs8"
PIXABAY_KEY    = "u_g0pmau3m85"

WP_URL  = "https://koreanews365.com"
WP_USER = "huh0303@gmail.com"
WP_PASS = "dqn2 VR2L WaR0 sJmq GHeh fgYG"

# ── 한국 언론사 전문 기자단 풀 (10명 명단 및 데스크 직책 유지) ──────────
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
POST_GAP_MIN = 3       # Qwen 무료 API 레이트 리밋 우회를 위한 안정적 최소 대기
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
단순 문장 복사는 엄격히 금지하며, 대한민국 메이저 언론사의 정통 신문 기사체 명조풍 톤앤매너를 유지하십시오.

[원본 출처 헤드라인]: {news_item['title']}
[원본 사건 요약 정보]: {news_item['desc'][:300]}
[배정 섹션 데스크]: {section['name']}
[취재 및 작성 기자]: {reporter['name']} ({reporter['title']})

══════════════════════════
[GEMS 대한민국 정통 언론사 기사 지침]
══════════════════════════

1. 스마트폰 모바일 가독성 극대화 (★최우선 필수)
- 모바일 화면 가독성을 위해 본문의 모든 문장은 극도로 짧고 간결하게 끊어 쳐야 합니다.
- 하나의 문단(<p> 태그) 내부에는 오직 딱 1개의 문장만 배치하는 것을 원칙으로 하며, 최대 2개 문장을 넘지 마십시오.
- 문단과 문단 사이에는 독자의 시각적 여백 확보를 위해 반드시 본문 HTML 코드 상에 '명확한 한 줄 이상의 공백 빈 줄'을 무조건 배치하십시오.

2. 신문 기사체 구조화 구성
- 본문 분량은 공백 제외 최소 1,200자 ~ 1,600자 내외의 묵직한 볼륨으로 구성하십시오.
- 기사의 헤드라인(TITLE)은 원본과 완전히 다르게 창작하되, 독자의 이목을 끄는 세련된 언론사 스타일로 도출하십시오. (40~60자 내외)
- 첫 번째 문단(리드문)에 육하원칙(5W1H)에 기반한 사건의 핵심 요약을 100자 이내로 정밀 배치하십시오.
- 본문의 논리적 입체감을 위해 H2 태그 3개 이상, H3 태그를 단락별로 각 1~2개씩 짜임새 있게 배치하십시오. (H1 태그는 사용 금지)
- 기사의 신뢰성을 확보하기 위해 정확한 수치 데이터나 통계 지표를 3개 이상 본문 중에 인용하십시오.

3. 거미줄 네트워크 하이퍼링크 구조
- 외부 공신력 링크: 공공기관, 정부부처, 혹은 글로벌 싱크탱크 공식 웹사이트 주소 연결 링크를 3개 이상 포함하십시오. (target="_blank" 속성 필수)
- 자매 네트워크 거미줄 링크: 본문 하단이나 자연스러운 문맥에 자매 건강 전문 플랫폼인 'k-health365.com'의 메인 허브나 관련 카테고리로 연결되는 백링크 하이퍼링크를 최소 1개 이상 앵커 텍스트를 정교하게 다듬어 포함하십시오.

4. 필수 기사 구성 요소
- 기사 요약 정리용 깔끔한 HTML 표(Table)를 1개 이상 반드시 구현하십시오.
- 이미지 배치 마커를 본문 중 적절한 위치 2곳에 정확히 삽입하십시오: - 기사 마무리는 반드시 향후 파급 효과와 시장 흐름을 짚어주는 '전망 및 시사점' 섹션으로 끝맺음하십시오.
- 기사 상단 영역에 바이라인을 명확히 삽입하십시오: [출력 형식 가이드라인]
첫째줄: TITLE: [창작된 뉴스 제목]
둘째줄: 셋째줄: 넷째줄: 다섯째줄: 여섯째줄부터: 본문 HTML 소스 코드 (상기 모바일 분절 가독성 빈 줄 규칙을 철저히 엄수할 것)"""


def call_qwen(prompt):
    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": QWEN_MODEL,
        "messages": [
            {"role": "system", "content": "당신은 대한민국 최고의 디지털 언론사 수석 논설위원이자 SEO 테크니컬 마스터입니다."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.65,
        "max_tokens": 4096
    }
    try:
        r = requests.post(QWEN_API_URL, headers=headers, json=payload, timeout=100)
        r.raise_for_status()
        time.sleep(4)  # 무료 API 안정적 가동을 위한 버퍼 대기
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"  ❌ Qwen API 통신 오류: {e}")
        time.sleep(12)
        return None


def get_image(query):
    try:
        r = requests.get(
            f"https://api.pexels.com/v1/search?query={query}&per_page=5&orientation=landscape",
            headers={"Authorization": PEXELS_KEY}, timeout=10)
        photos = r.json().get("photos", [])
        if photos:
            p = random.choice(photos)
            return {"src": p["src"]["large"], "credit": f'사진출처: Pexels / 촬영: {p["photographer"]}'}
    except: pass
    try:
        r = requests.get(
            f"https://pixabay.com/api/?key={PIXABAY_KEY}"
            f"&q={requests.utils.quote(query)}&image_type=photo&per_page=5&safesearch=true",
            timeout=10)
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
                    f'<img src="{img["src"]}" alt="{alt}" loading="lazy" style="border-radius:6px; max-width:100%; height:auto;"/>'
                    f'<figcaption style="font-size:12px; color:#777; margin-top:5px;">{img["credit"]}</figcaption></figure>')
        return f'<p style="text-align:center; color:#888;"><em>[보도사진: {alt}]</em></p>'

    content = re.sub(r'\s*', img_replacer, content, flags=re.DOTALL)

    if byline:
        content = f'<p class="byline" style="color:#555; font-weight:bold; font-size:14px; border-bottom:2px solid #222; padding-bottom:6px; margin-bottom:20px;">✍️ {byline}</p>\n' + content

    tags = [t.strip() for t in tags_s.split(",") if t.strip()][:10]
    return {"title": title or "인터넷 종합 뉴스", "slug": slug, "meta": meta, "content": content, "tags": tags}


def seo_score(parsed):
    c, t, m = parsed["content"], parsed["title"], parsed["meta"]
    checks = [
        ("헤드라인 매칭성",        len(t) >= 15),
        ("메타 데이터 요약",        len(m) >= 60),
        ("기사 분량 기준 충족",    len(c) >= 1000),
        ("단락 입체 구조화(H2)",    c.count("<h2") >= 3),
        ("단락 상세 구조화(H3)",    c.count("<h3") >= 1),
        ("시각 보도자료(디스플레이)","<img" in c and 'alt="' in c),
        ("브리핑 요약 표(Table)",   c.count("<table") >= 1),
        ("아웃바운드 공식 링크",    c.count('target="_blank"') >= 3),
        ("취재 기자 바이라인 검증", "byline" in c.lower() or "wp-block-image" in c),
        ("핵심 색인 태그(10개)",     len(parsed.get("tags", [])) >= 8),
        ("전망 및 시사점 브리핑",    "전망" in c or "시사점" in c),
    ]
    score = round(sum(100/len(checks) for _, ok in checks if ok))
    passed = sum(1 for _, ok in checks if ok)
    
    print(f"  ┌─ 신문사 기사 품질 검증 시스템 ({passed}/{len(checks)})", flush=True)
    for name, ok in checks:
        print(f"  │ {'✅' if ok else '❌'} {name}", flush=True)
    print(f"  └─ 통과 점수: {score}점", flush=True)
    return score


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
        except Exception as e:
            print(f"     ⚠️ 태그 예외 처리: {e}")

    try:
        r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts",
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
            json={"title": parsed["title"], "content": parsed["content"],
                  "status": "publish", "categories": [cat_id], "tags": tag_ids,
                  **({"slug": parsed["slug"]} if parsed.get("slug") else {}),
                  "meta": {"rank_math_description": parsed["meta"]}}, timeout=30)
        r.raise_for_status()
        return r.json().get("id"), r.json().get("link", "")
    except Exception as e:
        print(f"  ❌ 워드프레스 뉴스 발행 실패: {e}")
        return None, None


def run_daily():
    print(f"\n{'═'*55}")
    print(f"  📰 koreanews365.com Qwen 미디어 통합 봇 구동")
    print(f"  시스템 가동 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  규모: 9개 섹션 × {ARTICLES_PER_SECTION}개 송고 = 총 {9*ARTICLES_PER_SECTION}개 단독 보도 기사")
    print(f"{'═'*55}")

    for sec in SECTIONS:
        if sec["id"] is None:
            sec["id"] = get_cat_id(sec["slug"])

    results = []
    used_reporters = []

    for sec_i, section in enumerate(SECTIONS):
        print(f"\n\n  📌 편집국 데스크 배정 섹션: [{section['name']}]")
        news_items = get_news_items(section, ARTICLES_PER_SECTION)
        
        if not news_items:
            news_items = [{"title": f"{section['name']} 부문 심층 분석 기획 리포트",
                          "desc": f"2026년 {section['name']} 지형의 핵심 쟁점 및 중장기 리스크를 분석 보도합니다.",
                          "link": ""} for _ in range(ARTICLES_PER_SECTION)]

        for art_i, news in enumerate(news_items):
            if art_i > 0:
                gap = POST_GAP_MIN * 60 + random.randint(-30, 60)
                print(f"  ⏳ 무료 서버 동시성 우회 대기 ({gap//60}분)...")
                time.sleep(gap)

            choices = [r for r in REPORTERS if r["name"] != (used_reporters[-1]["name"] if used_reporters else None)]
            reporter = random.choice(choices)
            used_reporters.append(reporter)

            print(f"\n  [송고공정 {sec_i+1}/9] [{art_i+1}/{ARTICLES_PER_SECTION}] {section['name']} 데스크")
            print(f"  🎙️ 속보 소스: {news['title'][:45]}")
            print(f"  ✍️  당직 취재기자: {reporter['name']} {reporter['title']}")

            raw = call_qwen(build_news_prompt(news, section, reporter))
            if not raw: continue

            parsed = process_content(raw)
            score = seo_score(parsed)

            if score < 80:
                print("  🔄 품질 점수 보완을 위한 원고 재편집(Re-Generation)...")
                raw2 = call_qwen(build_news_prompt(news, section, reporter))
                if raw2:
                    parsed2 = process_content(raw2)
                    score2 = seo_score(parsed2)
                    if score2 > score: parsed, score = parsed2, score2

            pid, purl = post_to_wp(parsed, section["id"])
            if pid:
                print(f"  ✅ [송고 완료] ID:{pid} | 매체품질:{score}점")
                print(f"  🔗 발행 링크: {purl}")
                results.append({"section": section["name"], "reporter": reporter["name"],
                                "title": parsed["title"], "url": purl, "score": score,
                                "time": datetime.now().strftime("%H:%M")})

        if sec_i < len(SECTIONS)-1:
            gap = SECTION_GAP_MIN * 60 + random.randint(-60, 120)
            print(f"\n  ⏰ 다음 섹션 원고 마감 대기 ({gap//60}분)...")
            time.sleep(gap)

    return results


if __name__ == "__main__":
    results = run_daily()
    fname = f"news_ko_{datetime.now().strftime('%Y%m%d')}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n  📁 인덱싱 메타 데이터 로컬 백업 완료: {fname}")
