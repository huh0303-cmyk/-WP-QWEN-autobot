#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordPress AI 자동 포스팅 봇 - 23개 사이트 MEGA 버전
실행: python autopost_mega.py
결과: Google Sheets 자동 업로드 + 로컬 JSON 저장
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
#  ★ API 키 설정 ★
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
    internal_html = "\n".join([
        f'   - <a href="https://{domain}/{ref.lower().replace(" ", "-")}/">{ref}</a>'
        for ref in random.sample(internal_refs, min(4, len(internal_refs)))])

    magazine_note = "Write in a magazine/editorial style with compelling narrative." if style=="magazine" else ""
    news_note = "Write as a news-style article with clear who/what/when/where/why structure." if style=="news" else ""

    adsense_note = """
CRITICAL - Google AdSense Policy Compliance:
- No misleading health claims without scientific backing
- No adult, gambling, or drug-related content
- No clickbait or sensationalist language
- All medical info must cite authoritative sources
- Content must be original and high quality
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

1. SEO STRUCTURE
- Target Google SEO score: 90+
- Total body length: 2500+ characters (strictly required)
- TITLE: avoid plain listing - combine click-worthy angles like "Effects", "Side Effects", "Expert Insight" (50-60 chars, include focus keyword near the start, include a number e.g. Top 5 / 2026)
- Use H2 (main sections) and H3 (sub-sections) tags to make the structure clear (no H1 - WordPress adds it)
- Include the focus keyword within the first 100 characters of the body
- 4+ internal links - weave these naturally into the body where relevant:
{internal_html}
   (add 1-2 more internal links with keyword-rich anchor text to related posts on {domain})

2. MEDICAL/EXPERT AUTHORITY (E-E-A-T)
- Maintain a doctorate-level, evidence-based tone
- Cite research/statistics with years
- 5+ external authority links (cite stats/tables with sources), from:
  * https://www.nih.gov, https://pubmed.ncbi.nlm.nih.gov
  * https://www.who.int, https://www.nhs.uk
  * https://www.mfds.go.kr, https://www.statista.com
  * https://www.bloomberg.com, https://www.reuters.com

3. MOBILE READABILITY (REQUIRED)
- Keep every paragraph short (2-3 sentences max)
- Separate every paragraph with its own <p> tag (blank line between paragraphs)

4. REQUIRED SECTIONS
- Must include "Dosage/Usage", "Precautions", and "Conclusion" sections
- 2+ HTML <table> tags, 2+ <ul> lists, 1+ <ol> list
- 8-12 <strong> emphasis tags
- 3 images:
  <!-- IMAGE: [english search query] -->
  <!-- ALT: [descriptive alt text] -->
- FAQ section with 5 Q&A pairs (<!-- SCHEMA_FAQ --> at start, H3 for questions)
- At the end of the post:
  - A "Related Keywords" section: 4-5 related keywords as a <ul>, each linked to one of the internal links above
  - A line starting with "Tags:" followed by exactly 12 comma-separated noun tags

[OUTPUT FORMAT - STRICTLY FOLLOW]
Line 1: TITLE: [title]
Line 2: <!-- META_DESCRIPTION: [120 char meta description in English] -->
Line 3: <!-- TAGS: tag1, tag2, ..., tag12 (exactly 12, comma-separated) -->
Line 4+: Full HTML body (NO <h1> tag, WordPress adds it)

Write the complete post now. Focus keyword: {keyword}"""


def build_prompt_ko(keyword, style="news"):
    return f"""당신은 의학/시사 박사 톤을 유지하는 한국 최고의 시사 저널리스트입니다.
아래 [GEMS SEO 및 가독성 최적화 지침]을 100% 만족하는 워드프레스 뉴스 기사를 작성하세요.

[주제어]: {keyword}
[스타일]: 신문 기사체 (객관적, 사실 기반, 육하원칙)

══════════════════════════
[GEMS SEO 및 가독성 최적화 지침]
══════════════════════════

1. SEO 구조화 원칙
- 구글 SEO 점수 90점 이상 필수
- 본문 총 어휘수 2500자 이상 (반드시 준수)
- 제목: 단순 나열 금지, 주제어 포함, 뉴스 헤드라인 형식 (40~60자)
- H2(주요 목차), H3(세부 내용) 태그로 구조화 (H1 사용 금지, WordPress가 자동 추가)
- 글의 첫 100자 이내에 핵심 주제어 반드시 포함
- 내부링크 4개 이상: 관련기사를 본문에 자연스럽게 언급하며 koreanews365.com 링크 삽입

2. 전문성 유지
- 박사 톤, 근거 중심 (통계/수치 데이터 5개 이상, 출처 명시)
- 전문가 인용 또는 공식 발표 내용 포함
- 외부링크 5개 이상: 정부기관, 언론사, 공식 통계 (본문에 자연스럽게 삽입, target="_blank")

3. 모바일 가독성 규칙 (필수)
- 모든 문단은 짧게 끊어 작성 (2~3문장 이내)
- 모든 문단(<p>) 사이에 빈 줄을 둘 것

4. 실천 가이드 (필수 포함 항목)
- '배경', '주요 내용', '전망 및 시사점' 항목 반드시 포함
- 표(Table) 1개 이상
- 이미지 3곳: <!-- IMAGE: 영어검색어 --> <!-- ALT: 한국어설명 -->
- FAQ 5쌍 (<!-- SCHEMA_FAQ --> 태그로 시작)
- 글 마지막에:
  - "관련 키워드 5개" 섹션: 내부링크로 연결한 ul 목록
  - 라벨: 로 시작하는 줄에, 쉼표로 연결된 명사 태그값 12개 단어 제시

[출력 형식]
첫째줄: TITLE: [제목]
둘째줄: <!-- META_DESCRIPTION: [영어 120자 내외 메타디스크립션] -->
셋째줄: <!-- TAGS: 태그1, 태그2, ... (정확히 12개, 쉼표로 구분) -->
넷째줄부터: 본문 HTML

주제어: {keyword}"""


def call_gemini(prompt):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent")
    try:
        r = requests.post(url,
            headers={"Content-Type": "application/json",
                     "x-goog-api-key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 0.75,
                                       "maxOutputTokens": 8192,
                                       "topP": 0.9}},
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
    title, meta, tags_str, content = "", "", "", raw

    for i, line in enumerate(lines):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
            title = re.sub(r'^```[a-zA-Z]*\s*', '', title)
            title = title.strip('`"\' ')
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

    content = re.sub(r'<!-- IMAGE: (.+?) -->\s*<!-- ALT: (.+?) -->',
                     img_replacer, content, flags=re.DOTALL)

    if "SCHEMA_FAQ" in content:
        content += ('\n<script type="application/ld+json">'
                    '{"@context":"https://schema.org","@type":"FAQPage",'
                    '"mainEntity":[]}</script>')

    tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

    return {
        "title":   title or "Auto Generated Post",
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
        ("Internal links 4+",       c.count(domain) >= 4),
        ("Strong tags 8+",          c.count("<strong>") >= 8),
        ("Tags 10+",                len(parsed.get("tags",[])) >= 10),
        ("Required sections",       any(k in c.lower() for k in required_sections) or any(k in c for k in required_sections)),
        ("Related keywords section", "related keyword" in c.lower() or "관련 키워드" in c or "연관 키워드" in c),
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
                headers={"Authorization": f"Basic {auth}",
                         "Content-Type": "application/json"},
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
        except: pass

    try:
        r = requests.post(url,
            headers={"Authorization": f"Basic {auth}",
                     "Content-Type": "application/json"},
            json={
                "title":      parsed["title"],
                "content":    parsed["content"],
                "status":     "publish",
                "categories": [site.get("category_id", 1)],
                "tags":       tag_ids,
                "meta": {
                    "rank_math_focus_keyword": keyword,
                    "rank_math_description":   parsed["meta"],
                    "_yoast_wpseo_focuskw":    keyword,
                    "_yoast_wpseo_metadesc":   parsed["meta"],
                }
            }, timeout=30)
        r.raise_for_status()
        pid  = r.json().get("id")
        purl = r.json().get("link", "")
        return pid, purl, "success"
    except Exception as e:
        err = str(e)
        try:
            err += " | " + e.response.text[:200]
        except: pass
        return None, None, err


def send_to_sheets(row_data):
    if not SHEETS_WEBHOOK:
        return
    try:
        requests.post(SHEETS_WEBHOOK, json=row_data, timeout=10)
    except: pass


def indexnow(site_url, post_url):
    host = get_domain(site_url)
    for ep in ["https://api.indexnow.org/indexnow",
               "https://www.bing.com/indexnow"]:
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
    lang   = site.get("lang", "en")
    style  = site.get("style", "blog")

    all_kws = load_or_create_keywords(site["keywords_file"])
    if not all_kws:
        print(f"  ⚠️  {domain}: 키워드 파일 없음")
        return

    today_kws  = get_today_keywords(all_kws, DAILY_LIMIT)
    rand_times = gen_random_times(DAILY_LIMIT)
    internal_refs = random.sample(all_kws, min(7, len(all_kws)))

    min_c = MIN_CHARS_KO if lang == "ko" else MIN_CHARS_EN
    max_c = MAX_CHARS_KO if lang == "ko" else MAX_CHARS_EN

    print(f"\n{'─'*55}")
    print(f"  📌 {domain} [{site['theme'][:40]}]")
    print(f"  오늘 키워드 {len(today_kws)}개 | 랜덤 발행 시간:")
    for i, (kw, t) in enumerate(zip(today_kws, rand_times)):
        print(f"     {i+1:2d}. {t//60:02d}:{t%60:02d}  {kw}")

    for i, (kw, target_min) in enumerate(zip(today_kws, rand_times)):
        print(f"\n  ⏰ [{domain}] 예약시각 {target_min//60:02d}:{target_min%60:02d} → 즉시 실행")
        print(f"\n  [{domain}] [{i+1}/{DAILY_LIMIT}] {kw}")
        print(f"  🧠 Gemini 생성 중...")

        if lang == "ko":
            prompt = build_prompt_ko(kw, style)
        else:
            prompt = build_prompt_en(
                kw, site["theme"], site["url"], internal_refs,
                min_c, max_c, site.get("adsense", False), style)

        raw = call_gemini(prompt)
        if not raw:
            row = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "site": domain, "keyword": kw,
                "status": "❌ FAIL", "reason": "Gemini error",
                "seo_score": 0, "post_url": ""
            }
            with lock: results_list.append(row)
            send_to_sheets(row)
            continue

        parsed = process_content(raw, site["url"])
        score, checks, passed = seo_score(parsed, kw, site["url"], lang)

        print(f"  📄 {parsed['title'][:60]}")
        print(f"  📏 {len(parsed['content'])}자 | SEO: {score}점 ({passed}/{len(checks)})")
        print(f"  🏷️  태그: {', '.join(parsed['tags'][:5])}")

        if score < 80:
            print(f"  🔄 SEO {score}점 < 80점 → 재생성...")
            raw2 = call_gemini(prompt)
            if raw2:
                parsed2 = process_content(raw2, site["url"])
                score2, checks2, passed2 = seo_score(parsed2, kw, site["url"], lang)
                if score2 > score:
                    parsed, score, checks, passed = parsed2, score2, checks2, passed2
            if score < 80:
                print(f"  ⚠️ 재생성 후에도 {score}점, 최선의 결과로 발간 진행")

        pid, purl, status = post_to_wp(site, parsed, kw)

        if pid:
            indexnow(site["url"], purl)
            print(f"  ✅ 발행 완료! ID:{pid} SEO:{score}점")
            print(f"  🔗 {purl}")
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
        with lock:
            results_list.append(row)
        send_to_sheets(row)

        time.sleep(3)


def print_summary(results):
    ok   = [r for r in results if "OK" in r["status"]]
    fail = [r for r in results if "FAIL" in r["status"]]
    avg_seo = sum(r["seo_score"] for r in ok) // max(len(ok), 1)

    print(f"\n{'═'*60}")
    print(f"  📊 오늘의 포스팅 결과 요약")
    print(f"{'═'*60}")
    print(f"  ✅ 성공: {len(ok)}개   ❌ 실패: {len(fail)}개")
    print(f"  🎯 평균 SEO 점수: {avg_seo}점")
    print(f"\n  사이트별 결과:")
    sites_done = {}
    for r in results:
        s = r["site"]
        if s not in sites_done:
            sites_done[s] = {"ok":0,"fail":0}
        if "OK" in r["status"]:
            sites_done[s]["ok"] += 1
        else:
            sites_done[s]["fail"] += 1
    for s, v in sites_done.items():
        icon = "✅" if v["fail"]==0 else ("⚠️" if v["ok"]>0 else "❌")
        print(f"  {icon} {s}: 성공 {v['ok']}개 / 실패 {v['fail']}개")

    if fail:
        print(f"\n  ❌ 실패 목록:")
        for r in fail:
            print(f"     {r['site']} | {r['keyword']} | {r['reason'][:60]}")
    print(f"{'═'*60}\n")


def main():
    print(f"\n{'═'*60}")
    print(f"  🤖 WordPress AI 자동 포스팅 봇 - MEGA 버전")
    print(f"  모델: {GEMINI_MODEL}")
    print(f"  시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  사이트: {len(SITES)}개 | 사이트당 {DAILY_LIMIT}개 | 총 {len(SITES)*DAILY_LIMIT}개/일")
    print(f"{'═'*60}")

    no_pwd = [get_domain(s["url"]) for s in SITES
              if not WP_PASSWORDS.get(get_domain(s["url"]),"")] 
    if no_pwd:
        print(f"\n  ⚠️  Application Password 미설정 사이트 ({len(no_pwd)}개):")
        for d in no_pwd:
            print(f"     - {d}")
        print(f"  → WP_PASSWORDS 딕셔너리에 입력 후 재실행")

    results = []
    lock    = threading.Lock()

    for site in SITES:
        domain = get_domain(site["url"])
        if not WP_PASSWORDS.get(domain, ""):
            print(f"\n  ⏭️  {domain} 건너뜀 (비밀번호 없음)")
            continue
        process_site(site, results, lock)

    today = date.today().strftime("%Y%m%d")
    rfile = f"result_{today}.json"
    with open(rfile, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    cfile = f"result_{today}.csv"
    with open(cfile, "w", encoding="utf-8-sig") as f:
        cols = ["date","site","keyword","title","status","seo_score",
                "chars","tags","post_url","reason"]
        f.write(",".join(cols)+"\n")
        for r in results:
            row = [str(r.get(c,"")).replace(",","；").replace("\n"," ") for c in cols]
            f.write(",".join(row)+"\n")

    print_summary(results)
    print(f"  📁 JSON: {rfile}")
    print(f"  📊 CSV:  {cfile}  ← 구글시트에 바로 임포트 가능\n")


if __name__ == "__main__":
    main()
