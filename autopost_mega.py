#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordPress AI 자동 포스팅 봇 - 22개 사이트 MEGA 버전 (Qwen API 최적화 모델)
실행: python autopost_mega.py
가독성: 모바일 가독성을 위해 모든 문장 사이 공백 라인 주입 및 극단적 짧은 문단 구조화 적용
업데이트: 클릭을 부르는 후킹성 타이포 썸네일 랜덤 생성 알고리즘 탑재
"""

import os
import json
import time
import random
import requests
import base64
import re
import threading
from datetime import datetime, date

# 데이터 구조 선로드
from sites_config import SITES
from keywords_all import KEYWORDS

# ══════════════════════════════════════════════
#  ★ 인프라 핵심 도메인 파싱 및 내부 매칭 유틸리티 ★
# ══════════════════════════════════════════════
def get_domain(url):
    """URL에서 프로토콜과 슬래시를 제거하여 순수 도메인만 추출"""
    return url.replace("https://", "").replace("http://", "").rstrip("/")

# sites_config.py에서 터지던 로직을 가장 안전한 이곳 메인 인프라 영역으로 회수
ALL_DOMAINS_EN = [get_domain(s["url"]) for s in SITES if s.get("lang") == "en"]

# ── 기자 풀 (랜덤 선택) ──────────────────────
REPORTER_POOL_KR = ["전문기자 김윤서", "전문기자 이현수", "수석기자 김상준", "전문기자 박지아", "전문기자 정도윤"]
REPORTER_POOL_EN = ["Sarah Mitchell", "James Anderson", "Emily Carter", "David Thompson", "Rachel Bennett"]

def pick_reporter(lang="en"):
    return random.choice(REPORTER_POOL_KR if lang == "ko" else REPORTER_POOL_EN)

# ══════════════════════════════════════════════
#  ★ Qwen API 인프라 및 보안 자산 연동 변수 ★
# ══════════════════════════════════════════════
QWEN_API_KEY   = os.environ.get("QWEN_API_KEY", "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")
QWEN_MODEL     = "qwen-2.5-72b-instruct"
QWEN_API_URL   = "https://api.groq.com/openai/v1/chat/completions"

PEXELS_KEY     = os.environ.get("PEXELS_KEY", "41q16JQ0qBM123kTUgEk2YKAfK3e43l6NCErWoWn0Fv41Zmdfub0XAs8")
PIXABAY_KEY    = os.environ.get("PIXABAY_KEY", "u_g0pmau3m85")
INDEXNOW_KEY   = "khealth365indexnow2024"

SHEETS_WEBHOOK  = os.getenv("SHEETS_WEBHOOK", "")

WP_USERNAME     = "huh0303@gmail.com"
WP_PASSWORDS    = {
    "k-health365.com":        os.environ.get("WP_PASS", "A3sK VQud Xday 1ait Zl0d ZAA2"),
    "koreanews365.com":       os.environ.get("WP_PASS", "MSqZ PAhu UpBL 2B1W cDle 4DEO"),
    "kskin365.com":           os.environ.get("WP_PASS", "ZvM8 0Dj7 ByPL R27O DKia Hubg"),
    "korea365.org":           os.environ.get("WP_PASS", "g536 KsvK qiCY 9Ye0 U6pe bywR"),
    "jobinkorea365.com":      os.environ.get("WP_PASS", "PwYU 4sif FfeH dY5k Uv7v GnVM"),
    "jobkorea365.com":        os.environ.get("WP_PASS", "sOcf 8Xaz rQUs IcxC 5i81 1rcx"),
    "jobkoreaglobal.com":     os.environ.get("WP_PASS", "36sf v54W wgkA fvpy 8AUO aEc4"),
    "kstudy365.com":          os.environ.get("WP_PASS", "NCaa GAnM 7Qhp Ffz4 8B4X wa2s"),
    "studyinkorea.com":       os.environ.get("WP_PASS", "8W0N v0jD 1fJG Ypem noib DcB7"),
    "kfinance365.com":        os.environ.get("WP_PASS", "uCiL hIUs klO6 JBUi bf5E 7UPv"),
    "koreainvest365.com":     os.environ.get("WP_PASS", "8uqi uG9A LpXU EceZ rBAW 6P6P"),
    "koreataxlaw.com":        os.environ.get("WP_PASS", "ta5e DgxP y7oa KlhT izMZ qWef"),
    "k-trip365.com":          os.environ.get("WP_PASS", "m2FO M7Ss zPcI rMtD u4CR MV0l"),
    "k-visa365.com":          os.environ.get("WP_PASS", "WjiG VmQm 2Ly9 bqU6 zQRF A7CF"),
    "koreacrypto365.com":     os.environ.get("WP_PASS", "ZQHo B2XY VpyM p3oM nwnO Yh3M"),
    "koreainsurance365.com":  os.environ.get("WP_PASS", "q42y V0tO f0lV IhHe g9e8 dEr3"),
    "koreanews365.com":       os.environ.get("WP_PASS", "d3fv cScN Ruvf AUiO Drae 6WuX"),
    "koreavedding365.com":    os.environ.get("WP_PASS", "jPcA SAAa UdT4 nByC qnVi J2lV"),
    "ktech365.com":           os.environ.get("WP_PASS", "lYyP q7wY 0P7J 7BOv G6w8 F3dC"),
    "kworld365.com":          os.environ.get("WP_PASS", "M0zy T8Vv 56mH 8HbP ueP9 KEDU"),
    "oliveyoungkorea.com":    os.environ.get("WP_PASS", "Aemu VCSZ l4nf xHq3 tgyE NIkb"),
    "theseouljournal.com":    os.environ.get("WP_PASS", "Z7S7 97p2 vEBC gTxe sVDb hnMY"),
}

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


def build_network_links_guide(current_url):
    """현재 도메인을 제외한 타 도메인 백링크 매칭용 안전 가이드 생성기"""
    domain = get_domain(current_url)
    other_en_domains = [d for d in ALL_DOMAINS_EN if d != domain]
    
    network_targets = random.sample(other_en_domains, min(2, len(other_en_domains)))
    
    network_links_list = [
        f"   - Link {i+1}: https://{tgt} (Anchor text must be highly relevant keyword)"
        for i, tgt in enumerate(network_targets)
    ]
    
    if network_links_list:
        return "\n".join(network_links_list)
    else:
        return "   - No internal network links required for this post."


def build_prompt_en(keyword, theme, site_url, internal_refs, min_c, max_c, is_adsense, style):
    domain = get_domain(site_url)
    reporter = pick_reporter("en")
    
    internal_html = "\n".join([
        f'   - <a href="https://{domain}/{ref.lower().replace(" ", "-")}/">{ref}</a>'
        for ref in random.sample(internal_refs, min(3, len(internal_refs)))])
    
    network_links_guide = build_network_links_guide(site_url)

    thumbnail_styles = [
        f"A bold, neon-lit cyberpunk digital signage featuring the short punchy text '{keyword}' in high-contrast pink and cyan, perfect for mobile scrolling.",
        f"A premium minimalist magazine cover design with ultra-bold typography reading '{keyword}' in a modern serif font, high-end commercial style.",
        f"A sleek 3D tech gadget mockup screen displaying '{keyword}' as a trending status bar topic, with futuristic abstract lighting.",
        f"A retro-vintage analog terminal screen casting a bright green glow with the text '{keyword}' typed inside a flashing cursor box.",
        f"An isometric data visualization grid where light-streaks form the large, readable keyword '{keyword}' in a dynamic corporate environment."
    ]
    selected_thumb_style = random.choice(thumbnail_styles)

    return f"""You are {reporter}, a doctorate-level expert in {theme}.
Write a complete, publish-ready WordPress blog post following the [GEMS SEO & Readability Guidelines].

[FOCUS KEYWORD]: {keyword}
[TOPIC/NICHE]: {theme}
[LANGUAGE]: English

══════════════════════════
[IMAGE GENERATION CRITICAL DIRECTIVE]
══════════════════════════
- Your first image MUST be a featured thumbnail.
- You MUST design the image search query to produce text on the image.
- Use this exact style concept for the FIRST image query: "{selected_thumb_style}"
- Ensure the word '{keyword}' is explicitly stated in the query as the core visual anchor.

══════════════════════════
[GEMS SEO & Readability Guidelines]
══════════════════════════

1. MOBILE FIRST LAYOUT & READABILITY (★CRITICAL)
- To ensure optimal layout on smartphone screens, you MUST format the content with extreme fragmentation.
- A single paragraph (<p> block element) MUST contain only 1 sentence.
- You MUST leave a clear, explicit empty line space between every single paragraph in the output HTML.

2. SEO SPIDERWEB LINKING STRUCTURE
- Total body length: 2500+ characters (strictly required)
- TITLE: 50-60 chars, include focus keyword near the start, must be highly clickable and catchy!
- Include the focus keyword within the first 100 characters of the body.
- 3+ Internal Links: {internal_html}
- 2+ Cross-Network Web Backlinks: {network_links_guide}

3. REQUIRED SECTIONS & EXPERT AUTHORITY
- 5+ external authority links.
- 2+ HTML <table> tags, 2+ <ul> lists, 1+ <ol> list, 8-12 <strong> emphasis tags.
- 3 images formatted precisely as: (The FIRST image query must incorporate the custom thumbnail style defined above)
- FAQ section with 5 Q&A pairs (preceded by )

[OUTPUT FORMAT]
Line 1: TITLE: [title]
Line 2: Line 3: Line 4: Line 5+: Full HTML body (NO <h1> tag, clean fragmented paragraph spaces with blank lines)"""


def build_prompt_ko(keyword, style="news", is_news_site=False):
    reporter = pick_reporter("ko")
    if is_news_site:
        current_domain = "koreanews365.com"
        sister_domain = "k-health365.com"
    else:
        current_domain = "k-health365.com"
        sister_domain = "koreanews365.com"

    thumbnail_styles_ko = [
        f"A modern social media card design with bold, glowing neon font displaying '{keyword}' as a trending news headline.",
        f"A highly-stylized digital smartphone screen mock-up showing a break-news notification with the text '{keyword}'.",
        f"A minimalist corporate presentation slide with a large, clean bold heading that says '{keyword}' in high contrast color.",
        f"A futuristic holograph interface projects the primary focus word '{keyword}' with dynamic cyber background.",
        f"An editorial newspaper layout concept where the central headline boldly reads '{keyword}' in a premium retro look."
    ]
    selected_thumb_style_ko = random.choice(thumbnail_styles_ko)

    tone_style = "의학 박사 학위 소지자이자 건강 보건 전문 평론가"
    if is_news_site:
        tone_style = "깊이 있는 통찰력을 갖춘 대한민국 최고의 시사 종합 저널리스트"

    return f"""당신은 {tone_style}인 {reporter}입니다.
아래 지침을 100% 충족하는 워드프레스 본문용 HTML 기사를 작성하세요.

[주제어]: {keyword}

══════════════════════════
[썸네일 이미지 자동 텍스트 디자인 지침]
══════════════════════════
- 본문에 삽입될 첫 번째 이미지 마커는 반드시 SNS 및 포털 클릭률을 폭발시키는 후킹성 타이포 썸네일이어야 합니다.
- 첫 번째 이미지의 영문 검색 쿼리 지시어는 무조건 다음 설정을 반영하여 작성하십시오: "{selected_thumb_style_ko}"
- 쿼리 내부에 핵심 단어인 '{keyword}'가 텍스트 형태로 선명하게 강조되도록 유도하십시오.

══════════════════════════
[GEMS SEO 및 모바일 거미줄 가독성 지침]
══════════════════════════

1. 모바일 독자 최적화 레이아웃 (★최우선 필수 지침)
- 모든 문장은 극도로 짧게 끊어서 배치해야 합니다.
- 하나의 문단(<p> 태그) 내부에는 무조건 단 1개의 문장만 넣습니다.
- 문단과 문단 사이에는 반드시 본문 소스코드 상에 명확하게 '한 줄 이상의 공백 빈 줄'을 두십시오.

2. 거미줄 네트워크 링크 시스템
- 내부링크 매칭: 현재 사이트 도메인인 {current_domain} 내부 서브 주소 2개 하이퍼링크 처리.
- 네트워크 백링크: 자매 네트워크인 {sister_domain}의 주소로 연결되는 아웃바운드 링크 1개 이상 배치.

3. 전문성 구현 및 후킹성 타이틀
- TITLE(제목)은 단순 정보 나열이 아닌, "2026년 충격", "아무도 모르는 Top 5", "당신이 몰랐던 비밀" 등 모바일 유저가 즉시 클릭하고 싶게 만드는 강력한 어그로/후킹성 문구로 조형하십시오.
- 본문 전체 분량은 공백 제외 최소 2,500자 이상.
- H2 태그 5개 이상, H3 태그 8개 이상 구조화 (H1 태그 절대 금지).
- 2개 이상의 요약 데이터 표(Table)와 <strong> 태그 강조 처리.
- 이미지 마커 3곳 삽입: - FAQ 5쌍 모듈(주석으로 시작)을 구성하십시오.

[출력 형식]
첫째줄: TITLE: [제목]
둘째줄: 셋째줄: 넷째줄: 다섯째줄부터: 본문 HTML 소스 코드"""


def call_qwen(prompt):
    headers = {"Authorization": f"Bearer {QWEN_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": QWEN_MODEL,
        "messages": [
            {"role": "system", "content": "You are a master of WordPress SEO content generation, maximizing mobile layouts with extensive paragraph splitting."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7, "max_tokens": 4096
    }
    try:
        r = requests.post(QWEN_API_URL, headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        time.sleep(5)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"    ❌ Qwen 인프라 API 통신 오류: {e}")
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

    content = re.sub(r'', img_replacer, content, flags=re.DOTALL | re.IGNORECASE)

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
    if lang == "ko":
        required_sections = ["배경", "주요 내용", "전망"]
    else:
        required_sections = ["dosage", "precaution", "conclusion"]
    checks = [
        ("Keyword in title",         keyword.split()[0].lower() in t.lower()),
        ("Meta desc 100+ chars",     len(m) >= 100),
        ("Content 2500+ chars",      len(c) >= 2500),
        ("H2 tags 5+",               c.count("<h2") >= 5),
        ("H3 tags 8+",               c.count("<h3") >= 8),
        ("Images inserted",          "<img" in c),
        ("ALT text present",          'alt="' in c),
        ("Tables 2+",               c.count("<table") >= 2),
        ("FAQ section",              "faq" in c.lower() or "FAQ" in c),
        ("External links 5+",       c.count('target="_blank"') >= 5),
        ("Internal/Network links",  c.count("href=") >= 3),
        ("Strong tags 8+",          c.count("<strong>") >= 8),
        ("Tags 10+",                len(parsed.get("tags",[])) >= 10),
        ("Required sections",        any(k in c.lower() for k in required_sections) or any(k in c for k in required_sections)),
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
            print(f"      ⚠️ tag '{tag}' error: {e}")

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
    lang = site["lang"]
    is_news_site = (domain == "koreanews365.com")
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

        if lang == "ko":
            prompt = build_prompt_ko(kw, style, is_news_site=is_news_site)
        else:
            prompt = build_prompt_en(kw, site["theme"], site["url"], internal_refs, min_c, max_c, site.get("adsense", False), style)

        raw = call_qwen(prompt)
        if not raw:
            row = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "site": domain, "keyword": kw, "status": "❌ FAIL", "reason": "Qwen API error", "seo_score": 0, "post_url": ""}
            with lock: results_list.append(row)
            send_to_sheets(row)
            continue

        parsed = process_content(raw, site["url"])
        score, checks, passed = seo_score(parsed, kw, site["url"], lang)

        if score < 80:
            raw2 = call_qwen(prompt)
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
