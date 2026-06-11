#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordPress AI 자동 포스팅 봇 - 랜덤 시간 + 멀티사이트 최종본
실행: python autopost_bot.py
"""

import os, json, time, random, requests, base64, re
from datetime import datetime

# ══════════════════════════════════════════════
#  ★ 설정 - 여기만 수정 ★
# ══════════════════════════════════════════════
CONFIG = {
    "gemini_api_key":  "AQ.Ab8RN6Je6ngXK-4cSMxL05o3jlfF06RNHJtwz3XlPdB6zqLFbA",
    "gemini_model":    "gemini-2.5-flash",
    "pexels_api_key":  "41q16JQ0qBM123kTUgEk2YKAfK3e43l6NCErWoWn0Fv41Zmdfub0XAs8",
    "pixabay_api_key": "u_g0pmau3m85",
    "min_chars":       2000,
    "max_chars":       3000,
    "daily_limit":     10,   # 사이트당 하루 10개

    # ── 랜덤 시간 설정 ──────────────────────────
    # 오전 7시 ~ 오후 11시 사이, 포스팅간 최소 간격(분)
    "random_start_hour": 7,
    "random_end_hour":   23,
    "min_gap_minutes":   45,   # 너무 붙지 않게 최소 45분 간격

    # ── 사이트 목록 (계속 추가 가능) ────────────
    "sites": [
        {
            "url":           "https://k-health365.com",
            "username":      "huh0303@gmail.com",
            "app_password":  "db&AwT@eriy^EtVEeKjMMc4r",
            "theme":         "건강/의료",
            "adsense":       True,
            "category_id":   964,
            "keywords_file": "keywords_health.txt",
            "internal_links": [
                ("비타민D 결핍 증상",   "/비타민d-결핍-증상/"),
                ("고혈압 관리법",       "/고혈압-관리법-2026/"),
                ("면역력 강화 식품",    "/면역력-강화-식품/"),
                ("오메가3 효능",        "/오메가3-효능/"),
                ("마그네슘 효능",       "/마그네슘-효능-부작용/"),
                ("프로바이오틱스 효능", "/프로바이오틱스-유산균-차이/"),
                ("루테인 효능",         "/루테인-지아잔틴-차이/"),
                ("콜라겐 효능",         "/콜라겐-효능-종류/"),
                ("비타민C 효능",        "/비타민c-고용량-효과/"),
                ("건강기능식품 추천",   "/가성비-영양제-추천-2026/"),
            ],
        },
        {
            "url":           "https://kworld365.com",
            "username":      "huh0303@gmail.com",
            "app_password":  "ehuPXC)n2o3o7joWm3k4Nh3g",
            "theme":         "생활/혜택/정부지원",
            "adsense":       False,
            "category_id":   1,    # ← kworld365.com 카테고리 ID로 변경
            "keywords_file": "keywords_world.txt",
            "internal_links": [
                ("청년수당 신청방법",    "/청년수당-신청방법/"),
                ("실업급여 조건",        "/실업급여-조건-금액/"),
                ("주거급여 신청",        "/주거급여-신청자격/"),
                ("종합소득세 신고",      "/종합소득세-신고방법/"),
                ("근로장려금 신청",      "/근로장려금-신청방법/"),
                ("자녀장려금 조건",      "/자녀장려금-조건/"),
                ("국민연금 수령나이",    "/국민연금-수령나이-조회/"),
                ("청년도약계좌 신청",    "/청년도약계좌-신청/"),
                ("정부지원금 총정리",    "/정부지원금-2026-총정리/"),
                ("두루누리 사회보험",    "/두루누리-사회보험/"),
            ],
        },
        # ── 3번째 사이트 추가 예시 ──────────────────
        # {
        #     "url":           "https://koreataxnlaw.com",
        #     "username":      "huh0303@gmail.com",
        #     "app_password":  "여기에_앱패스워드",
        #     "theme":         "세금/법률",
        #     "adsense":       False,
        #     "category_id":   1,
        #     "keywords_file": "keywords_tax.txt",
        #     "internal_links": [...],
        # },
    ]
}
# ══════════════════════════════════════════════


def gen_random_times(n, start_h=7, end_h=23, min_gap=45):
    """n개 포스팅 시간을 완전 랜덤으로 생성 (최소 간격 준수)"""
    used, times, tries = [], [], 0
    while len(times) < n and tries < 1000:
        tries += 1
        h = start_h + random.randint(0, end_h - start_h - 1)
        m = random.randint(0, 59)
        total = h * 60 + m
        if total > end_h * 60:
            continue
        if all(abs(total - u) >= min_gap for u in used):
            used.append(total)
            times.append(total)
    times.sort()
    return times  # 분 단위 절대값 반환


def wait_until(target_minutes):
    """지정된 시각(오늘 기준 분 단위)까지 대기"""
    now = datetime.now()
    now_min = now.hour * 60 + now.minute
    diff = target_minutes - now_min
    if diff > 0:
        print(f"  ⏰ {target_minutes//60:02d}:{target_minutes%60:02d} 까지 {diff}분 대기 중...")
        time.sleep(diff * 60)


def build_prompt(keyword, theme, min_c, max_c, site_url, internal_links):
    links_html = "\n".join(
        [f'   - <a href="{site_url}{path}">{anchor}</a>'
         for anchor, path in random.sample(internal_links, min(7, len(internal_links)))])
    return f"""당신은 한국 최고의 SEO 전문 블로거입니다.
아래 조건을 100% 만족하는 WordPress 블로그 포스트를 HTML로 작성하세요.

[포커스 키워드]: {keyword}
[블로그 테마]: {theme}
[목표 글자수]: {min_c}~{max_c}자 (반드시 준수)

[AdSense 정책]
- 허위·과장 정보 금지, 근거 기반 작성
- 저작권·성인·도박 관련 표현 금지

[SEO 90점+ 조건 - 전부 포함]
① 제목: 키워드 앞쪽 포함, 숫자 포함(TOP5/3가지/2026), 50~60자
② 메타디스크립션: 120~155자, 키워드 포함, 행동유도 문구
③ H2 6개이상, 각 H2 아래 H3 2~3개
④ 키워드밀도 1~2%, 데이터/수치 5개이상
⑤ 내부링크 7개 - 아래 링크를 본문에 자연스럽게 삽입:
{links_html}
⑥ 외부링크 6개 - 아래 링크를 본문에 자연스럽게 삽입:
   - https://www.mfds.go.kr (식품의약품안전처)
   - https://www.nih.gov (미국 국립보건원)
   - https://pubmed.ncbi.nlm.nih.gov (PubMed 논문)
   - https://www.who.int (세계보건기구)
   - https://www.nhs.uk (영국 NHS)
   - https://www.health.kr (의약품 정보)
⑦ 표(Table) 2개이상
⑧ ul 목록 2개이상, ol 목록 1개이상
⑨ <strong> 강조 8~12개
⑩ 이미지 3곳: <!-- IMAGE: 영어검색어 --> <!-- ALT: 한국어설명 --> 형식
⑪ FAQ 7쌍: <!-- SCHEMA_FAQ --> 태그로 시작
⑫ 목차(TOC): 본문 앞에 앵커링크 포함 목차 삽입
⑬ 맺음말: 요약 + 행동유도 + 키워드 재언급

[출력 형식]
첫째줄: TITLE: [제목]
둘째줄: <!-- META_DESCRIPTION: [메타디스크립션] -->
셋째줄부터: 본문 HTML (h1 태그 제외)

키워드: {keyword}"""


def call_gemini(prompt):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{CONFIG['gemini_model']}:generateContent")
    try:
        r = requests.post(url,
            headers={"Content-Type": "application/json",
                     "x-goog-api-key": CONFIG["gemini_api_key"]},
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 0.75, "maxOutputTokens": 8192, "topP": 0.9}},
            timeout=120)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"  ❌ Gemini 오류: {e}")
        return None


def get_image(query):
    try:
        r = requests.get(
            f"https://api.pexels.com/v1/search?query={query}&per_page=5&orientation=landscape",
            headers={"Authorization": CONFIG["pexels_api_key"]}, timeout=10)
        photos = r.json().get("photos", [])
        if photos:
            p = random.choice(photos)
            return {"src": p["src"]["large"], "credit": f'Photo by {p["photographer"]} on Pexels'}
    except: pass
    try:
        r = requests.get(
            f"https://pixabay.com/api/?key={CONFIG['pixabay_api_key']}"
            f"&q={requests.utils.quote(query)}&image_type=photo&orientation=horizontal"
            f"&per_page=5&safesearch=true", timeout=10)
        hits = r.json().get("hits", [])
        if hits:
            p = random.choice(hits)
            return {"src": p["webformatURL"], "credit": "Photo from Pixabay"}
    except: pass
    return {}


def process_content(raw):
    lines = raw.strip().split("\n")
    title, meta, content = "", "", raw
    for i, line in enumerate(lines):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        if "META_DESCRIPTION:" in line:
            meta = line.split("META_DESCRIPTION:")[-1].replace("-->", "").strip()
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
    if "SCHEMA_FAQ" in content:
        content += ('\n<script type="application/ld+json">'
                    '{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}'
                    '</script>')
    return {"title": title or "자동생성 포스트", "meta": meta, "content": content}


def seo_score(parsed, keyword, site_url):
    c, t, m = parsed["content"], parsed["title"], parsed["meta"]
    domain = site_url.replace("https://","").replace("http://","").rstrip("/")
    checks = [
        ("제목에 키워드",          keyword in t),
        ("메타디스크립션 120자+",  len(m) >= 120),
        ("본문 2000자 이상",       len(c) >= 2000),
        ("H2 태그 5개+",          c.count("<h2") >= 5),
        ("H3 태그 8개+",          c.count("<h3") >= 8),
        ("이미지+ALT",            "<img" in c and 'alt="' in c),
        ("테이블 2개+",           c.count("<table") >= 2),
        ("FAQ 포함",              "FAQ" in c or "자주 묻는" in c),
        ("외부링크 6개+",         c.count('href="http') >= 6),
        ("내부링크 7개+",         c.count(domain) >= 7),
        ("Bold 강조",             "<strong>" in c),
        ("키워드 밀도",           0.003 <= c.count(keyword)/max(len(c),1) <= 0.025),
    ]
    score = sum(8 for _, ok in checks if ok)
    print("  ┌─ SEO 체크 ────────────────────")
    for name, ok in checks:
        print(f"  │ {'✅' if ok else '❌'} {name}")
    final = min(score, 100)
    print(f"  └─ 점수: {final}점  {'🎉' if final >= 90 else '⚠️ 재생성'}")
    return final


def post_to_wp(site, parsed, keyword):
    url  = f"{site['url'].rstrip('/')}/wp-json/wp/v2/posts"
    auth = base64.b64encode(
        f"{site['username']}:{site['app_password']}".encode()).decode()
    try:
        r = requests.post(url,
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
            json={"title": parsed["title"], "content": parsed["content"],
                  "status": "publish", "categories": [site.get("category_id", 1)],
                  "meta": {"rank_math_focus_keyword": keyword,
                           "rank_math_description":   parsed["meta"]}},
            timeout=30)
        r.raise_for_status()
        pid  = r.json().get("id")
        purl = r.json().get("link", "")
        print(f"  ✅ 발행 완료!  ID: {pid}")
        print(f"  🔗 {purl}")
        return pid, purl
    except Exception as e:
        print(f"  ❌ WordPress 오류: {e}")
        try: print(f"     응답: {e.response.text[:300]}")
        except: pass
        return None, None


def indexnow(site_url, post_url):
    key  = "khealth365indexnow2024"
    host = site_url.replace("https://","").replace("http://","").rstrip("/")
    for ep in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try:
            requests.post(ep, json={"host": host, "key": key,
                "keyLocation": f"{site_url}/{key}.txt", "urlList": [post_url]}, timeout=10)
        except: pass


def load_keywords(filename):
    if os.path.exists(filename):
        with open(filename, encoding="utf-8") as f:
            return [l.strip() for l in f if l.strip()]
    return []


def main():
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n{'━'*60}")
    print(f"  🤖 WordPress AI 자동 포스팅 봇 (랜덤 시간)")
    print(f"  시작: {now_str}")
    print(f"  사이트: {len(CONFIG['sites'])}개 | 사이트당 {CONFIG['daily_limit']}개/일")
    print(f"{'━'*60}")

    all_results = []

    for site in CONFIG["sites"]:
        keywords = load_keywords(site["keywords_file"])
        if not keywords:
            print(f"\n⚠️  {site['keywords_file']} 파일 없음, 건너뜀")
            continue

        today_kws = keywords[:CONFIG["daily_limit"]]

        # 랜덤 발행 시간 생성
        rand_times = gen_random_times(
            len(today_kws),
            start_h=CONFIG["random_start_hour"],
            end_h=CONFIG["random_end_hour"],
            min_gap=CONFIG["min_gap_minutes"]
        )

        print(f"\n📌 [{site['url']}] {site['theme']}")
        print(f"   오늘 키워드 {len(today_kws)}개 | 랜덤 시간 배정:")
        for i, (kw, t) in enumerate(zip(today_kws, rand_times)):
            print(f"   {i+1:2d}. {t//60:02d}:{t%60:02d}  {kw}")

        for i, (kw, target_min) in enumerate(zip(today_kws, rand_times)):

            # 예약 시간까지 대기
            wait_until(target_min)

            print(f"\n  ─── [{i+1}/{len(today_kws)}] {kw} ───")
            print(f"  🕐 발행시각: {target_min//60:02d}:{target_min%60:02d}")
            print(f"  🧠 Gemini 2.5 Flash 생성 중... (30~90초)")

            raw = call_gemini(build_prompt(
                kw, site["theme"], CONFIG["min_chars"], CONFIG["max_chars"],
                site["url"], site["internal_links"]))
            if not raw:
                continue

            parsed = process_content(raw)
            print(f"  📄 {parsed['title']}")
            print(f"  📏 {len(parsed['content'])}자")

            score = seo_score(parsed, kw, site["url"])
            if score < 72:
                print("  🔄 재생성 중...")
                raw2 = call_gemini(build_prompt(
                    kw, site["theme"], CONFIG["min_chars"], CONFIG["max_chars"],
                    site["url"], site["internal_links"]))
                if raw2:
                    parsed = process_content(raw2)
                    score  = seo_score(parsed, kw, site["url"])

            pid, purl = post_to_wp(site, parsed, kw)
            if pid:
                indexnow(site["url"], purl)
                all_results.append({
                    "site": site["url"], "keyword": kw, "post_id": pid,
                    "url": purl, "seo": score,
                    "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

    # 결과 저장
    rfile = f"result_{datetime.now().strftime('%Y%m%d')}.json"
    with open(rfile, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    avg = sum(r["seo"] for r in all_results) // max(len(all_results), 1)
    print(f"\n{'━'*60}")
    print(f"  🎉 완료!  발행: {len(all_results)}개 | 평균 SEO: {avg}점")
    print(f"  📁 결과: {rfile}")
    print(f"{'━'*60}\n")


if __name__ == "__main__":
    main()
