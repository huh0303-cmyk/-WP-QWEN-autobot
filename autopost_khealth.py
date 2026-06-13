#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
k-health365.com 전용 자동 포스팅 봇
- 11개 카테고리, 1라운드 실행 후 종료 (GitHub Actions용)
- 내부링크 7개, 외부링크 6개
- SEO 90점+ 한국어
실행: python autopost_khealth.py
"""

import os, json, time, random, requests, base64, re
from datetime import datetime

# ══════════════════════════════════════════
#  ★ 설정
# ══════════════════════════════════════════
GEMINI_API_KEY = "AQ.Ab8RN6L1RxG7CUO1FSFAl9E53oOM934QWAA3AqcFIWpA3Q7h5g"
GEMINI_MODEL   = "gemini-2.5-flash"
PEXELS_KEY     = "41q16JQ0qBM123kTUgEk2YKAfK3e43l6NCErWoWn0Fv41Zmdfub0XAs8"
PIXABAY_KEY    = "u_g0pmau3m85"
INDEXNOW_KEY   = "khealth365indexnow2024"

WP_URL      = "https://k-health365.com"
WP_USER     = "huh0303@gmail.com"
WP_PASS     = "i5p8 ircP SdL6 4wCY Vq1e fxq8"

# 카테고리 간 간격: 2분 ± 20초 랜덤 (테스트용 단축)
POST_GAP_BASE_MIN  = 2
POST_GAP_RAND_MIN  = 0

# ── 11개 카테고리 ──────────────────────────
CATEGORIES = [
    {"name": "K건강기능식품", "slug": "health-supplements",       "id": None,
     "theme": "건강기능식품 성분 분석과 영양제 선택 가이드",
     "kw_hint": ["영양제","건강기능식품","비타민","미네랄","프로바이오틱스"]},

    {"name": "K건강정보",    "slug": "health",                    "id": 964,
     "theme": "만성질환 정보, 건강관리, 질병 예방 케어 가이드",
     "kw_hint": ["건강정보","만성질환","고혈압","당뇨","면역력"]},

    {"name": "K금융",        "slug": "finance",                   "id": None,
     "theme": "한국형 금융 상품 및 자산 관리 기초 지식",
     "kw_hint": ["재테크","금융상품","주식","펀드","절세"]},

    {"name": "K보험",        "slug": "insurance",                 "id": None,
     "theme": "외국인/국내 거주자 필수 실손 및 건강보험 안내",
     "kw_hint": ["건강보험","실손보험","보험료","보험비교","의료비"]},

    {"name": "K뷰티-K웰니스","slug": "kbeauty-wellness",          "id": None,
     "theme": "K뷰티, 웰니스 트렌드 및 피부/성형 토탈 케어",
     "kw_hint": ["스킨케어","피부관리","K뷰티","웰니스","성형"]},

    {"name": "K세금-K법",    "slug": "tax-law",                   "id": None,
     "theme": "한국 생활 속 필수 세금 및 법률 가이드",
     "kw_hint": ["소득세","부가세","세금신고","법률","법인설립"]},

    {"name": "K여행",        "slug": "trip",                      "id": None,
     "theme": "한국 여행 패키지, 호텔예약, 관광 안내",
     "kw_hint": ["한국여행","서울여행","제주도","관광지","호텔"]},

    {"name": "K유학",        "slug": "study",                     "id": None,
     "theme": "한국 대학 입학, 어학당 프로그램 및 유학 생활 가이드",
     "kw_hint": ["한국유학","대학입학","어학당","장학금","비자"]},

    {"name": "K의료관광",    "slug": "medical-tour",              "id": None,
     "theme": "K-의료 서비스 안내 및 병원 예약 지원 정보",
     "kw_hint": ["의료관광","성형외과","피부과","병원","의료비"]},

    {"name": "K취업",        "slug": "jobs",                      "id": None,
     "theme": "한국 내 취업 시장 정보 및 취업 절차, 비자 가이드",
     "kw_hint": ["취업","이력서","면접","연봉","비자"]},

    {"name": "VISA",         "slug": "visa-total-care",           "id": None,
     "theme": "한국 비자 종류별 신청 자격, 서류 및 발급 절차",
     "kw_hint": ["비자신청","D2비자","E7비자","체류","외국인등록"]},
]

# ── 내부링크 20개 사이트 ────────────────────
INTERNAL_SITES = [
    ("koreamedicaltour.com",  "한국 의료관광"),
    ("kskin365.com",          "K뷰티 스킨케어"),
    ("korea365.org",          "한국 생활 가이드"),
    ("jobinkorea365.com",     "한국 취업 정보"),
    ("jobkorea365.com",       "한국 커리어"),
    ("jobkoreaglobal.com",    "글로벌 취업"),
    ("kstudy365.com",         "한국 유학"),
    ("studyinkorea.com",      "Study in Korea"),
    ("kfinance365.com",       "한국 금융"),
    ("koreainvest365.com",    "한국 투자"),
    ("koreataxlaw.com",       "한국 세금 법률"),
    ("k-trip365.com",         "한국 여행"),
    ("k-visa365.com",         "한국 비자"),
    ("koreacrypto365.com",    "한국 크립토"),
    ("koreainsurance365.com", "한국 보험"),
    ("koreanews365.com",      "한국 뉴스"),
    ("koreawedding365.com",   "한국 웨딩"),
    ("ktech365.com",          "한국 테크"),
    ("kworld365.com",         "한국 생활 혜택"),
    ("oliveyoungkorea.com",   "올리브영 K뷰티"),
]

# ── 권위 외부링크 풀 ────────────────────────
EXTERNAL_LINKS = [
    ("https://www.mfds.go.kr",              "식품의약품안전처"),
    ("https://www.nih.gov",                 "미국 국립보건원(NIH)"),
    ("https://pubmed.ncbi.nlm.nih.gov",     "PubMed 의학 논문"),
    ("https://www.who.int",                 "세계보건기구(WHO)"),
    ("https://www.nhs.uk",                  "영국 NHS"),
    ("https://www.health.kr",               "의약품 정보"),
    ("https://www.kdca.go.kr",              "질병관리청"),
    ("https://nhis.or.kr",                  "국민건강보험공단"),
    ("https://www.hira.or.kr",              "건강보험심사평가원"),
    ("https://www.mohw.go.kr",              "보건복지부"),
]
# ══════════════════════════════════════════


def get_category_id(slug):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    try:
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/categories?slug={slug}&per_page=1",
            headers={"Authorization": f"Basic {auth}"}, timeout=10)
        data = r.json()
        if data and isinstance(data, list):
            return data[0]["id"]
    except Exception:
        pass
    return 1


def init_category_ids():
    print("  카테고리 ID 조회 중...", flush=True)
    for cat in CATEGORIES:
        if cat["id"] is None:
            cat["id"] = get_category_id(cat["slug"])
        print(f"  {cat['name']:15s} → ID: {cat['id']}", flush=True)


def build_keyword(cat):
    hints = cat["kw_hint"]
    day = datetime.now().timetuple().tm_yday
    base = hints[day % len(hints)]
    suffixes = ["효능 완벽 정리", "추천 TOP5", "2026년 최신 가이드",
                "주의사항과 복용법", "전문가 조언", "올바른 선택법",
                "부작용과 대처법", "비교 분석", "핵심 정보"]
    return f"{base} {suffixes[(day + CATEGORIES.index(cat)) % len(suffixes)]}"


def build_prompt(keyword, cat):
    int_links = random.sample(INTERNAL_SITES, 7)
    int_html  = "\n".join([
        f'   - <a href="https://{domain}/" title="{anchor}">{anchor}</a>'
        for domain, anchor in int_links])

    ext_links = random.sample(EXTERNAL_LINKS, 6)
    ext_html  = "\n".join([
        f'   - <a href="{url}" target="_blank" rel="nofollow noopener">{name}</a>'
        for url, name in ext_links])

    return f"""당신은 한국 최고의 SEO 전문 블로거이자 건강/의료 전문 작가입니다.
아래 조건을 100% 만족하는 완성된 WordPress 블로그 포스트를 HTML로 작성하세요.

[포커스 키워드]: {keyword}
[카테고리]: {cat['name']} — {cat['theme']}
[목표 글자수]: 2000~3000자 (반드시 준수)
[언어]: 한국어

[Google AdSense 정책 — 필수 준수]
- 허위·과장 의학 정보 금지, 반드시 근거 기반 작성
- 저작권·성인·도박 관련 표현 절대 금지
- 전문가 조언 권고 문구 포함

[SEO 90점+ 달성 필수 조건]

① 제목: 포커스 키워드 앞쪽 포함, 숫자 포함(TOP5/3가지/2026년), 50~60자
② 메타디스크립션: 120~155자, 키워드 1회, 행동유도 문구 포함
③ 목차(TOC): 앵커링크 포함 목차를 본문 시작 전 삽입
④ H2 6개이상, 각 H2 아래 H3 2~3개
⑤ 키워드 밀도 1~2%, 공신력 있는 데이터/수치 5개이상
⑥ 내부링크 7개 — 아래 링크를 본문 자연스러운 위치에 삽입:
{int_html}
⑦ 외부링크 6개 — 아래 링크를 본문에 자연스럽게 삽입:
{ext_html}
⑧ 표(Table) 2개이상 (비교표, 성분표, 복용량표 등)
⑨ ul 목록 2개이상, ol 목록 1개이상
⑩ <strong> 강조 8~12개
⑪ 이미지 3곳:
   <!-- IMAGE: 영어검색어 -->
   <!-- ALT: 한국어 이미지 설명 -->
⑫ FAQ 7쌍 (<!-- SCHEMA_FAQ --> 태그로 시작)
⑬ CTA(Call To Action) 2곳:
   - 본문 중간: 관련 서비스/정보 클릭 유도
   - 맺음말: 행동 유도 + 키워드 재언급
⑭ 태그 8개: <!-- TAGS: 태그1, 태그2, ... -->

[출력 형식 — 반드시 준수]
첫째줄: TITLE: [제목]
둘째줄: <!-- META_DESCRIPTION: [메타디스크립션] -->
셋째줄: <!-- TAGS: 태그1, 태그2, 태그3, 태그4, 태그5, 태그6, 태그7, 태그8 -->
넷째줄부터: 본문 HTML (<h1> 태그 사용 금지)

지금 바로 작성하세요. 키워드: {keyword}"""


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
        time.sleep(6)   # ★ Gemini 성공 후 6초 대기 (분당 10회 유지)
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"    ❌ Gemini: {e}", flush=True)
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
                    "credit": f'Photo by {p["photographer"]} on Pexels'}
    except Exception:
        pass
    try:
        r = requests.get(
            f"https://pixabay.com/api/?key={PIXABAY_KEY}"
            f"&q={requests.utils.quote(query)}&image_type=photo"
            f"&orientation=horizontal&per_page=8&safesearch=true", timeout=10)
        hits = r.json().get("hits", [])
        if hits:
            p = random.choice(hits)
            return {"src": p["webformatURL"], "credit": "Image from Pixabay"}
    except Exception:
        pass
    return {}


def process_content(raw):
    lines = raw.strip().split("\n")
    title, meta, tags_str, content = "", "", "", raw
    for i, line in enumerate(lines):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        if "META_DESCRIPTION:" in line:
            meta = line.split("META_DESCRIPTION:")[-1].replace("-->", "").strip()
        if "TAGS:" in line:
            tags_str = line.split("TAGS:")[-1].replace("-->", "").strip()
        if title and meta:
            content = "\n".join(lines[i+1:])
            break

    def img_replacer(m):
        img = get_image(m.group(1).strip())
        alt = m.group(2).strip()
        if img:
            return (f'<figure class="wp-block-image size-large aligncenter">'
                    f'<img src="{img["src"]}" alt="{alt}" loading="lazy" '
                    f'style="max-width:100%;height:auto;border-radius:8px"/>'
                    f'<figcaption style="text-align:center;font-size:13px;color:#666">'
                    f'{img["credit"]}</figcaption></figure>')
        return f'<p><em>[이미지: {alt}]</em></p>'

    content = re.sub(r'<!-- IMAGE: (.+?) -->\s*<!-- ALT: (.+?) -->',
                     img_replacer, content, flags=re.DOTALL)

    if "SCHEMA_FAQ" in content:
        content += ('\n<script type="application/ld+json">'
                    '{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}'
                    '</script>')

    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
    return {"title": title or "자동생성 포스트", "meta": meta,
            "content": content, "tags": tags}


def seo_score(parsed, keyword):
    c, t, m = parsed["content"], parsed["title"], parsed["meta"]
    checks = [
        ("제목에 키워드",         keyword.split()[0] in t),
        ("메타디스크립션 120자+", len(m) >= 120),
        ("본문 2000자 이상",      len(c) >= 2000),
        ("H2 5개 이상",          c.count("<h2") >= 5),
        ("H3 8개 이상",          c.count("<h3") >= 8),
        ("이미지+ALT",           "<img" in c and 'alt="' in c),
        ("테이블 2개 이상",      c.count("<table") >= 2),
        ("FAQ 포함",             "FAQ" in c or "자주 묻는" in c),
        ("외부링크 6개 이상",    c.count('href="http') >= 6),
        ("내부링크 5개 이상",    c.count('k-health365.com') + c.count('.com/') >= 5),
        ("Strong 8개 이상",      c.count("<strong>") >= 8),
        ("태그 5개 이상",        len(parsed.get("tags", [])) >= 5),
        ("TOC 포함",             "toc" in c.lower() or "목차" in c),
        ("CTA 포함",             "지금" in c or "바로" in c or "확인" in c),
    ]
    score = sum(7 for _, ok in checks if ok)
    passed = sum(1 for _, ok in checks if ok)
    print(f"  ┌─ SEO 체크 ({passed}/{len(checks)}) ──────────────", flush=True)
    for name, ok in checks:
        print(f"  │ {'✅' if ok else '❌'} {name}", flush=True)
    final = min(score, 100)
    print(f"  └─ 점수: {final}점 {'🎉' if final >= 90 else '⚠️'}", flush=True)
    return final


def get_tag_ids(tags):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    ids = []
    for tag in tags[:8]:
        try:
            r = requests.post(
                f"{WP_URL}/wp-json/wp/v2/tags",
                headers={"Authorization": f"Basic {auth}",
                         "Content-Type": "application/json"},
                json={"name": tag}, timeout=10)
            if r.status_code in [200, 201]:
                ids.append(r.json()["id"])
            elif r.status_code == 400:
                sr = requests.get(
                    f"{WP_URL}/wp-json/wp/v2/tags?search={requests.utils.quote(tag)}",
                    headers={"Authorization": f"Basic {auth}"}, timeout=10)
                res = sr.json()
                if res:
                    ids.append(res[0]["id"])
        except Exception:
            pass
    return ids


def post_to_wp(parsed, cat_id, keyword):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    tag_ids = get_tag_ids(parsed.get("tags", []))
    try:
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/posts",
            headers={"Authorization": f"Basic {auth}",
                     "Content-Type": "application/json"},
            json={
                "title":      parsed["title"],
                "content":    parsed["content"],
                "status":     "publish",
                "categories": [cat_id],
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
        return pid, purl
    except Exception as e:
        print(f"  ❌ WP 오류: {e}", flush=True)
        try:
            print(f"     {e.response.text[:200]}", flush=True)
        except Exception:
            pass
        return None, None


def indexnow(post_url):
    for ep in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try:
            requests.post(ep, json={
                "host": "k-health365.com", "key": INDEXNOW_KEY,
                "keyLocation": f"{WP_URL}/{INDEXNOW_KEY}.txt",
                "urlList": [post_url]
            }, timeout=10)
        except Exception:
            pass


def run_round(round_num, results):
    print(f"\n{'═'*58}", flush=True)
    print(f"  🔄 ROUND {round_num} 시작 — {datetime.now().strftime('%H:%M:%S')}", flush=True)
    print(f"  카테고리 {len(CATEGORIES)}개 × 15분 간격", flush=True)
    print(f"{'═'*58}", flush=True)

    for i, cat in enumerate(CATEGORIES):
        if i > 0:
            gap = POST_GAP_BASE_MIN * 60 + random.randint(-POST_GAP_RAND_MIN, POST_GAP_RAND_MIN) * 60
            print(f"\n  ⏳ {gap//60}분 {gap%60}초 후 다음 카테고리...", flush=True)
            time.sleep(gap)

        keyword = build_keyword(cat)
        print(f"\n  ─── [{i+1}/{len(CATEGORIES)}] [{cat['name']}] {keyword} ───", flush=True)
        print(f"  🧠 Gemini 생성 중...", flush=True)

        raw = call_gemini(build_prompt(keyword, cat))
        if not raw:
            print(f"  ❌ 생성 실패", flush=True)
            results.append({"round": round_num, "cat": cat["name"],
                            "keyword": keyword, "status": "FAIL",
                            "time": datetime.now().strftime("%H:%M")})
            continue

        parsed  = process_content(raw)
        score   = seo_score(parsed, keyword)

        if score < 72:
            print("  🔄 재생성...", flush=True)
            raw2 = call_gemini(build_prompt(keyword, cat))
            if raw2:
                parsed = process_content(raw2)
                score  = seo_score(parsed, keyword)

        pid, purl = post_to_wp(parsed, cat["id"], keyword)
        if pid:
            indexnow(purl)
            print(f"  ✅ 발행! ID:{pid} SEO:{score}점", flush=True)
            print(f"  🔗 {purl}", flush=True)
            results.append({"round": round_num, "cat": cat["name"],
                            "keyword": keyword, "title": parsed["title"],
                            "status": "OK", "seo": score,
                            "post_id": pid, "url": purl,
                            "time": datetime.now().strftime("%H:%M")})
        else:
            results.append({"round": round_num, "cat": cat["name"],
                            "keyword": keyword, "status": "FAIL",
                            "time": datetime.now().strftime("%H:%M")})

    ok   = sum(1 for r in results if r.get("status") == "OK" and r.get("round") == round_num)
    fail = sum(1 for r in results if r.get("status") == "FAIL" and r.get("round") == round_num)
    avg  = sum(r.get("seo", 0) for r in results if r.get("round") == round_num) // max(ok, 1)
    print(f"\n  ✅ ROUND {round_num} 완료: 성공 {ok}개 / 실패 {fail}개 / 평균 SEO {avg}점", flush=True)


if __name__ == "__main__":
    print(f"\n{'═'*58}", flush=True)
    print(f"  🤖 k-health365.com 전용 자동 포스팅 봇", flush=True)
    print(f"  시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"  카테고리: {len(CATEGORIES)}개 (1라운드 실행 후 종료)", flush=True)
    print(f"{'═'*58}", flush=True)

    init_category_ids()
    results = []
    run_round(1, results)

    fname = f"khealth_result_{datetime.now().strftime('%Y%m%d')}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n  📁 결과 저장: {fname}", flush=True)
