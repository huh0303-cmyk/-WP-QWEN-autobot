#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordPress AI 자동 포스팅 봇 - 23개 사이트 MEGA 버전 (거미줄 크로스 체인 모델)
실행: python autopost_mega.py
가독성: 모바일 가독성을 위해 모든 문장 사이 공백 라인 주입 및 극단적 짧은 문단 구조화 적용
"""

import os, json, time, random, requests, base64, re, threading
from datetime import datetime, date
from sites_config import SITES
from keywords_all import KEYWORDS

# ── 기자 풀 (랜덤 선택) ──────────────────────
REPORTER_POOL_KR = ["전문기자 김윤서", "전문기자 이현수", "수석기자 김상준", "전문기자 박지아", "전문기자 정도윤"]
REPORTER_POOL_EN = ["Sarah Mitchell", "James Anderson", "Emily Carter", "David Thompson", "Rachel Bennett"]

def pick_reporter(lang="en"):
    return random.choice(REPORTER_POOL_KR if lang == "ko" else REPORTER_POOL_EN)


# ══════════════════════════════════════════════
#  ★ API 키 및 네트워크 인프라 설정 ★
# ══════════════════════════════════════════════
GEMINI_API_KEY  = "AQ.Ab8RN6L1RxG7CUO1FSFAl9E53oOM934QWAA3AqcFIWpA3Q7h5g"
GEMINI_MODEL    = "gemini-2.5-flash"
PEXELS_KEY      = "41q16JQ0qBM123kTUgEk2YKAfK3e43l6NCErWoWn0Fv41Zmdfub0XAs8"
PIXABAY_KEY     = "u_g0pmau3m85"
INDEXNOW_KEY    = "khealth365indexnow2024"

SHEETS_WEBHOOK  = os.getenv("SHEETS_WEBHOOK", "")

WP_USERNAME     = "huh0303@gmail.com"
WP_PASSWORDS    = {
    "k-health365.com":        "A3sK VQud Xday 1ait Zl0d ZAA2",
    "koreamedicaltour.com":   "MSqZ PAhu UpBL 2B1W cDle 4DEO",
    "kskin365.com":           "ZvM8 0Dj7 ByPL R27O DKia Hubg",
    "korea365.org":           "g536 KsvK qiCY 9Ye0 U6pe bywR",
    "jobinkorea365.com":      "PwYU 4sif FfeH dY5k Uv7v GnVM",
    "jobkorea365.com":        "sOcf 8Xaz rQUs IcxC 5i81 1rcx",
    "jobkoreaglobal.com":     "36sf v54W wgkA fvpy 8AUO aEc4",
    "kstudy365.com":          "NCaa GAnM 7Qhp Ffz4 8B4X wa2s",
    "studyinkorea.com":       "8W0N v0jD 1fJG Ypem noib DcB7",
    "kfinance365.com":        "uCiL hIUs klO6 JBUi bf5E 7UPv",
    "koreainvest365.com":     "8uqi uG9A LpXU EceZ rBAW 6P6P",
    "koreataxlaw.com":        "ta5e DgxP y7oa KlhT izMZ qWef",
    "k-trip365.com":          "m2FO M7Ss zPcI rMtD u4CR MV0l",
    "k-visa365.com":          "WjiG VmQm 2Ly9 bqU6 zQRF A7CF",
    "koreacrypto365.com":     "ZQHo B2XY VpyM p3oM nwnO Yh3M",
    "koreainsurance365.com":  "q42y V0tO f0lV IhHe g9e8 dEr3",
    "koreanews365.com":       "d3fv cScN Ruvf AUiO Drae 6WuX",
    "koreawedding365.com":    "jPcA SAAa UdT4 nByC qnVi J2lV",
    "ktech365.com":           "lYyP q7wY 0P7J 7BOv G6w8 F3dC",
    "kworld365.com":          "M0zy T8Vv 56mH 8HbP ueP9 KEDU",
    "oliveyoungkorea.com":    "Aemu VCSZ l4nf xHq3 tgyE NIkb",
    "theseouljournal.com":    "Z7S7 97p2 vEBC gTxe sVDb hnMY",
}

# 🕸️ 상호 거미줄 연동을 위한 전체 도메인 자산 정의
ALL_DOMAINS_KR = ["k-health365.com", "koreanews365.com"]
ALL_DOMAINS_EN = [
    "kworld365.com", "koreamedicaltour.com", "kskin365.com", "korea365.org",
    "jobinkorea365.com", "jobkorea365.com", "jobkoreaglobal.com", "kstudy365.com",
    "studyinkorea.com", "kfinance365.com", "koreainvest365.com", "koreataxlaw.com",
    "k-trip365.com", "k-visa365.com", "koreacrypto365.com", "koreainsurance365.com",
    "koreawedding365.com", "ktech365.com", "oliveyoungkorea.com", "theseouljournal.com"
]

DAILY_LIMIT     = 10
MIN_CHARS_EN    = 1800
MAX_CHARS_EN    = 2800
MIN_CHARS_KO    = 2000
MAX_CHARS_KO    = 3000
RANDOM_START_H  = 7
RANDOM_END_H    = 23
MIN_GAP_MIN     = 30

# ══════════════════════════════════════════════

def gen_random_times(n):
    used, times, tries = [], [], 0
    while len(times) < n and tries < 2000:
        tries += 1
        h = RANDOM_START_H + random.randint(0, RANDOM_END_H - RANDOM_START_H - 1)
        m = random.randint(0, 59)
        m = max(0, min(59, m + random.randint(-3, 3)))
        total = h * 60 + m
        if all(abs(total - u) >= MIN_GAP_MIN for u in used):
            used.append(total)
            times.append(total)
    times.sort()
    return times


def get_domain(url):
    return url.replace("https://","").replace("http://","").rstrip("/")


def build_prompt_en(keyword, theme, site_url, internal_refs, min_c, max_c, is_adsense, style):
    domain = get_domain(site_url)
    
    # 내 사이트 내부 글 링크 3개 구성
    internal_html = "\n".join([
        f'   - <a href="https://{domain}/{ref.lower().replace(" ", "-")}/">{ref}</a>'
        for ref in random.sample(internal_refs, min(3, len(internal_refs)))])
    
    # 🕸️ 타 도메인으로 뻗어나가는 영어 자산 거미줄 링크 백링크 2개 무작위 선출
    other_en_domains = [d for d in ALL_DOMAINS_EN if d != domain]
    network_targets = random.sample(other_en_domains, 2)
    network_links_guide = (
        f"   - Link 1: https://{network_targets[0]} (Anchor text must be highly relevant keyword)\n"
        f"   - Link 2: https://{network_targets[1]} (Anchor text must be highly relevant keyword)"
    )

    magazine_note = "Write in a professional magazine style with a compelling narrative." if style=="magazine" else ""
    news_note = "Write as a news-style article with a clear who/what/when/where/why structure." if style=="news" else ""

    adsense_note = """
CRITICAL - Google AdSense Policy Compliance:
- No misleading health claims without scientific backing
- No adult, gambling, or drug-related content
- All medical info must cite authoritative sources
""" if is_adsense else ""

    return f"""You are a doctorate-level, world-class SEO content writer and expert in {theme}.
Write a complete, publish-ready WordPress blog post following the [GEMS SEO & Readability Guidelines] below.

[FOCUS KEYWORD]: {keyword}
[TOPIC/NICHE]: {theme}
[LANGUAGE]: English
{magazine_note}{news_note}{adsense_note}

══════════════════════════
[GEMS SEO & Readability Guidelines]
══════════════════════════

1. MOBILE FIRST LAYOUT & READABILITY (★CRITICAL)
- To ensure optimal layout on smartphone screens, you MUST format the content with extreme fragmentation.
- A single paragraph (<p> block element) MUST contain only 1 sentence, or a maximum of 2 sentences.
- You MUST leave a clear, explicit empty line space between every single paragraph in the output HTML.

2. SEO SPIDERWEB LINKING STRUCTURE (★NETWORK EXPANSION)
- Target Google SEO score: 90+
- Total body length: 2500+ characters (strictly required)
- TITLE: 50-60 chars, include focus keyword near the start, include a number (e.g., 2026 / Top 5)
- Include the focus keyword within the first 100 characters of the body.
- 3+ Internal Links (Inject naturally within appropriate anchor words):
{internal_html}
- 2+ Cross-Network Web Backlinks (Inject these specific sister network URLs naturally with keyword-rich anchors into the body text to form a powerful domain web):
{network_links_guide}

3. REQUIRED SECTIONS & EXPERT AUTHORITY
- Maintain an authoritative, doctorate-level, evidence-based tone.
- Must include "Dosage/Usage", "Precautions", and "Conclusion" sections.
- 5+ external authority links from (.gov, .org, or global press networks like Bloomberg/Reuters).
- 2+ HTML <table> tags, 2+ <ul> lists, 1+ <ol> list, 8-12 <strong> emphasis tags.
- 3 images formatted precisely as: and - FAQ section with 5 Q&A pairs (preceded by )

[OUTPUT FORMAT]
Line 1: TITLE: [title]
Line 2: Line 3: Line 4: Line 5+: Full HTML body (NO <h1> tag, clean fragmented paragraph spaces)"""


def build_prompt_ko(keyword, style="news", is_news_site=False):
    # 🕸️ 한국어 사이트간 거미줄 매칭 구조화
    # k-health365.com과 koreanews365.com이 서로를 본문에서 크로스 링킹하도록 설계
    if is_news_site:
        current_domain = "koreanews365.com"
        sister_domain = "k-health365.com"
        anchor_hint = "건강 정보 및 의학 전문 포털 k-health365.com"
    else:
        current_domain = "k-health365.com"
        sister_domain = "koreanews365.com"
        anchor_hint = "종합 시사 뉴스 전문 플랫폼 koreanews365.com"

    tone_style = "의학 박사 학위 소지자이자 건강 보건 전문 평론가"
    if is_news_site:
        tone_style = "깊이 있는 통찰력을 갖춘 대한민국 최고의 시사 종합 저널리스트"

    return f"""당신은 {tone_style}입니다.
아래 [GEMS SEO 및 모바일 거미줄 가독성 지침]을 100% 충족하는 워드프레스 본문용 HTML 기사를 작성하세요.

[주제어]: {keyword}
[스타일]: 신문 기사 및 객관적 사실 기반 논평체 (육하원칙 준수, 신뢰도 높은 명조풍 톤앤매너)

══════════════════════════
[GEMS SEO 및 모바일 거미줄 가독성 지침]
══════════════════════════

1. 모바일 독자 최적화 레이아웃 (★최우선 필수 지침)
- 모바일 가독성을 위해 모든 문장은 극도로 짧게 끊어서 배치해야 합니다.
- 하나의 문단(<p> 태그) 내부에는 무조건 단 1개의 문장만 넣거나, 최대 2개 문장까지만 허용합니다.
- 문단과 문단 사이에는 반드시 본문 소스코드 상에 명확하게 '한 줄 이상의 공백 빈 줄'을 두어 시각적 여백을 확보하십시오.

2. 거미줄 네트워크 링크 시스템 (★SEO Link Graph)
- 구글의 최신 검색엔진 알고리즘 최적화를 위해 본문 내용 전개 중 적절한 맥락에 아래 2종류의 링크 시스템을 완벽히 구축하십시오.
- 내부링크 매칭: 현재 사이트 도메인인 {current_domain} 내부의 가상 서브 주소 형태 2개 이상을 유기적인 키워드에 하이퍼링크 처리하십시오.
- 네트워크 거미줄 링크 백링크: 본문 하단 혹은 문맥상 자연스러운 곳에 자매 네트워크인 {sister_domain}의 메인 주소 또는 핵심 카테고리 주소로 연결되는 아웃바운드 하이퍼링크를 최소 1개 이상 앵커 텍스트로 자연스럽게 심어주십시오. (예시 앵커: {anchor_hint})

3. 전문성 구현 및 필수 조건
- 본문 전체 분량은 HTML 코드를 포함하여 공백 제외 최소 2,500자 이상으로 묵직하게 채우십시오.
- 기사 전개 시 공신력을 높여주는 정확한 수치나 통계 지표 데이터를 최소 3개 이상 반드시 포함시키십시오.
- H2 태그 5개 이상, H3 태그 8개 이상을 사용하여 단락을 입체적으로 구조화하십시오 (H1 태그 절대 금지).
- 정부 기관 및 공식 기구 등의 신뢰성 높은 외부 출처 링크를 5개 이상 연동하십시오.
- 2개 이상의 요약 데이터 표(Table)와 핵심 어휘 <strong> 태그 강조 처리를 진행하십시오.
- 이미지 마커 3곳 삽입: - FAQ 5쌍 모듈(주석으로 시작)을 본문 내에 구성하십시오.

[출력 형식]
첫째줄: TITLE: [제목]
둘째줄: 셋째줄: 넷째줄: 다섯째줄부터: 본문 HTML 소스 코드 (상기 모바일 분절 가독성 규칙 철저히 이행)"""


def call_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    try:
        r = requests.post(url,
            headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 0.75, "maxOutputTokens": 8192, "topP": 0.9}},
            timeout=120)
        r.raise_for_status()
        time.sleep(6)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"    ❌ Gemini: {e}")
        time.sleep(15)
        return None


def get_image(query):
    try:
        r = requests.get(
            f"https://api.pexels.com/v1/search?query={query}&per_page=8&orientation=landscape",
            headers={"Authorization": PEXELS_KEY}, timeout=10)
        photos = r.json().get("photos", [])
        if photos:
            p = random.choice(photos)
            return {"src": p["src"]["large2x"] or p["src"]["large"],
                    "credit": f'Photo by {p["photographer"]} on <a href="{p["url"]}">Pexels</a>'}
    except: pass
    try:
        r = requests.get(
            f"https://pixabay.com/api/?key={PIXABAY_KEY}"
            f"&q={requests.utils.quote(query)}&image_type=photo"
            f"&orientation=horizontal&per_page=8&safesearch=true", timeout=10)
        hits = r.json().get("hits", [])
        if hits:
            p = random.choice(hits)
            return {"src": p["webformatURL"],
                    "credit": 'Image from <a href="https://pixabay.com">Pixabay</a>'}
    except: pass
    return {}


def process_content(raw, site_url):
    raw = raw.strip()
    raw = re.sub(r'^```[a-zA-Z]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw)
    raw = raw.strip()

    lines = raw.strip().split("\n")
    title, slug, meta, tags_str, content = "", "", "", "", raw

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
            tags_str = line.split("TAGS:")[-1].replace("-->","").strip()
        if title and meta:
            content = "\n".join(lines[i+1:])
            break

    def img_replacer(m):
        img = get_image(m.group(1).strip())
        alt = m.group(2).strip()
        if img:
            return (f'<figure class="wp-block-image size-large aligncenter">'
                    f'<img src="{img["src"]}" alt="{alt}" loading="lazy" '
                    f'style="max-width:100%;height:auto;border-radius:8px;"/>'
                    f'<figcaption style="text-align:center;font-size:13px;'
                    f'color:#666;">{img["credit"]}</figcaption></figure>')
        return f'<p><em>[Image: {alt}]</em></p>'

    content = re.sub(r'\s*',
                     img_replacer, content, flags=re.DOTALL)

    if "SCHEMA_FAQ" in content:
        content += ('\n<script type="application/ld+json">'
                    '{"@context":"[https://schema.org](https://schema.org)","@type":"FAQPage",'
                    '"mainEntity":[]}</script>')

    tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

    return {
        "title":   title or "Auto Generated Post",
        "slug":    slug,
        "meta":    meta,
        "content": content,
        "tags":    tags,
    }


def seo_score(parsed, keyword, site_url, lang="en"):
    c, t, m = parsed["content"], parsed["title"], parsed["meta"]
    domain = get_domain(site_url)
    if lang == "ko":
        required_sections = ["배경", "주요 내용", "전망"]
    else:
        required_sections = ["dosage", "precaution", "conclusion"]
    checks = [
        ("Keyword in title",         keyword.split()[0].lower() in t.lower()),
        ("Meta desc 100+ chars",     len(m) >= 100),
        ("Content 2500+ chars",      len(c) >= 2500),
        ("H2 tags 5+",              c.count("<h2") >= 5),
        ("H3 tags 8+",              c.count("<h3") >= 8),
        ("Images inserted",         "<img" in c),
        ("ALT text present",        'alt="' in c),
        ("Tables 2+",               c.count("<table") >= 2),
        ("FAQ section",             "faq" in c.lower() or "FAQ" in c),
        ("External links 5+",       c.count('target="_blank"') >= 5),
        ("Internal/Network links",  c.count("href=") >= 3),
        ("Strong tags 8+",          c.count("<strong>") >= 8),
        ("Tags 10+",                len(parsed.get("tags",[])) >= 10),
        ("Required sections",       any(k in c.lower() for k in required_sections) or any(k in c for k in required_sections)),
    ]
    score = round(sum(7 for _, ok in checks if ok) * 100 / (7*len(checks)))
    passed = sum(1 for _, ok in checks if ok)
    return score, checks, passed


def post_to_wp(site, parsed, keyword):
    domain = get_domain(site["url"])
    pwd    = WP_PASSWORDS.get(domain, "")
    if not pwd:
        return None, None, "No password configured"

    url  = f"{site['url'].rstrip('/')}/wp-json/wp/v2/posts"
    auth = base64.b64encode(f"{WP_USERNAME}:{pwd}".encode()).decode()

    tag_ids = []
    for tag in parsed.get("tags", [])[:12]:
        try:
            r = requests.post(
                f"{site['url'].rstrip('/')}/wp-json/wp/v2/tags",
                headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
                json={"name": tag}, timeout=10)
            if r.status_code in [200, 201]:
                tag_ids.append(r.json().get("id"))
            elif r.status_code == 400:
                sr = requests.get(
                    f"{site['url'].rstrip('/')}/wp-json/wp/v2/tags?search={requests.utils.quote(tag)}",
                    headers={"Authorization": f"Basic {auth}"}, timeout=10)
                results = sr.json()
                if results:
                    tag_ids.append(results[0]["id"])
        except Exception as e:
            print(f"     ⚠️ tag '{tag}' error: {e}")

    try:
        r = requests.post(url,
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
            json={
                "title":      parsed["title"],
                "content":    parsed["content"],
                "status":     "publish",
                "categories": [site.get("category_id", 1)],
                "tags":       tag_ids,
                **({"slug": parsed["slug"]} if parsed.get("slug") else {}),
                "meta": {
                    "rank_math_focus_keyword": keyword,
                    "rank_math_description":   parsed["meta"],
                    "_yoast_wpseo_focuskw":    keyword,
                    "_yoast_wpseo_metadesc":   parsed["meta"],
                }
            }, timeout=30)
        r.raise_for_status()
        return r.json().get("id"), r.json().get("link", ""), "success"
    except Exception as e:
        err = str(e)
        try: err += " | " + e.response.text[:200]
        except: pass
        return None, None, err


def send_to_sheets(row_data):
    if not SHEETS_WEBHOOK:
        return
    try: requests.post(SHEETS_WEBHOOK, json=row_data, timeout=10)
    except: pass


def indexnow(site_url, post_url):
    host = get_domain(site_url)
    for ep in ["[https://api.indexnow.org/indexnow](https://api.indexnow.org/indexnow)", "[https://www.bing.com/indexnow](https://www.bing.com/indexnow)"]:
        try:
            requests.post(ep, json={
                "host": host, "key": INDEXNOW_KEY,
                "keyLocation": f"{site_url}/{INDEXNOW_KEY}.txt",
                "urlList": [post_url]
            }, timeout=10)
        except: pass


def load_or_create_keywords(filename):
    if os.path.exists(filename):
        with open(filename, encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip()]
    raw = KEYWORDS.get(filename, "")
    lines = [l.strip() for l in raw.strip().split("\n") if l.strip()]
    if lines:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    return lines


def get_today_keywords(all_kws, daily_limit):
    day_of_year = date.today().timetuple().tm_yday
    start = ((day_of_year - 1) * daily_limit) % max(len(all_kws), 1)
    result = []
    for i in range(daily_limit):
        result.append(all_kws[(start + i) % len(all_kws)])
    return result


def process_site(site, results_list, lock):
    domain = get_domain(site["url"])
    
    # 🌎 지출 지침에 맞게 도메인 언어 실시간 분류 인젝션
    if domain == "k-health365.com":
        lang = "ko"
        is_news_site = False
    elif domain == "koreanews365.com":
        lang = "ko"
        is_news_site = True
    else:
        lang = "en"
        is_news_site = False

    style = site.get("style", "blog")

    all_kws = load_or_create_keywords(site["keywords_file"])
    if not all_kws: return

    today_kws  = get_today_keywords(all_kws, DAILY_LIMIT)
    rand_times = gen_random_times(DAILY_LIMIT)
    internal_refs = random.sample(all_kws, min(7, len(all_kws)))

    min_c = MIN_CHARS_KO if lang == "ko" else MIN_CHARS_EN
    max_c = MAX_CHARS_KO if lang == "ko" else MAX_CHARS_EN

    print(f"\n🕸️ 거미줄 스케줄러 가동: {domain} [언어: {lang.upper()}]")

    for i, (kw, target_min) in enumerate(zip(today_kws, rand_times)):
        print(f"  [{domain}] [{i+1}/{DAILY_LIMIT}] {kw}")

        # 언어별 프롬프트 빌더 매칭
        if lang == "ko":
            prompt = build_prompt_ko(kw, style, is_news_site=is_news_site)
        else:
            prompt = build_prompt_en(kw, site["theme"], site["url"], internal_refs, min_c, max_c, site.get("adsense", False), style)

        raw = call_gemini(prompt)
        if not raw:
            row = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "site": domain, "keyword": kw, "status": "❌ FAIL", "reason": "Gemini error", "seo_score": 0, "post_url": ""}
            with lock: results_list.append(row)
            send_to_sheets(row)
            continue

        parsed = process_content(raw, site["url"])
        score, checks, passed = seo_score(parsed, kw, site["url"], lang)

        if score < 80:
            raw2 = call_gemini(prompt)
            if raw2:
                parsed2 = process_content(raw2, site["url"])
                score2, checks2, passed2 = seo_score(parsed2, kw, site["url"], lang)
                if score2 > score:
                    parsed, score, checks, passed = parsed2, score2, checks2, passed2

        pid, purl, status = post_to_wp(site, parsed, kw)

        if pid:
            indexnow(site["url"], purl)
            print(f"  ✅ 크로스 링크 발행 완료! ID:{pid} SEO:{score}점 -> {purl}")
        else:
            print(f"  ❌ 발행 실패: {status[:80]}")

        row = {
            "date":      datetime.now().strftime("%Y-%m-%d %H:%M"),
            "site":      domain,
            "keyword":   kw,
            "title":     parsed["title"][:80],
            "status":    "✅ OK" if pid else "❌ FAIL",
            "reason":    "" if pid else status[:100],
            "seo_score": score,
            "post_id":   str(pid or ""),
            "post_url":  purl or "",
            "chars":     len(parsed["content"]),
            "tags":      ", ".join(parsed["tags"][:5]),
        }
        with lock: results_list.append(row)
        send_to_sheets(row)
        time.sleep(3)


def main():
    print(f"\n{'═'*60}\n  🕸️ 네트워크 체인 링크 거미줄 오토포스팅 가동\n{'═'*60}")
    results = []
    lock    = threading.Lock()

    for site in SITES:
        domain = get_domain(site["url"])
        if not WP_PASSWORDS.get(domain, ""): continue
        process_site(site, results, lock)

    today = date.today().strftime("%Y%m%d")
    with open(f"result_{today}.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
