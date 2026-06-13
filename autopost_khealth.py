#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
k-health365.com 전용 고성능 자동 포스팅 봇 (GitHub Actions 수동 트리거 최적화 버전)
- 글쓰기 엔진: Hugging Face Serverless API (Qwen/Qwen2.5-72B-Instruct) -> 100% 무료
- 가독성 지침: 모바일 가독성 최적화를 위해 모든 문장 사이 공백 라인 주입 및 짧은 문단 구조화
- 작동 방식: 11개 카테고리 전체를 완전 순환하며 카테고리당 1개씩 총 11개 글 발행 후 즉시 종료
"""

import os, json, time, random, requests, base64, re
from datetime import datetime

# ── 기자 풀 (랜덤 선택) ──────────────────────
REPORTER_POOL_KR = ["전문기자 김윤서", "전문기자 이현수", "수석기자 김상준", "전문기자 박지아", "전문기자 정도윤"]
REPORTER_POOL_EN = ["Sarah Mitchell", "James Anderson", "Emily Carter", "David Thompson", "Rachel Bennett"]

def pick_reporter():
    return random.choice(REPORTER_POOL_KR + REPORTER_POOL_EN)


# ══════════════════════════════════════════
#  ★ 시스템 설정 프로토콜 (무료 Qwen API 탑재)
# ══════════════════════════════════════════
HF_API_KEY     = "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"  
HF_MODEL       = "Qwen/Qwen2.5-72B-Instruct"

PEXELS_KEY     = "41q16JQ0qBM123kTUgEk2YKAfK3e43l6NCErWoWn0Fv41Zmdfub0XAs8"
PIXABAY_KEY    = "u_g0pmau3m85"
INDEXNOW_KEY   = "khealth365indexnow2024"

WP_URL      = "https://k-health365.com"
WP_USER     = "huh0303@gmail.com"
WP_PASS     = "A3sK VQud Xday 1ait Zl0d ZAA2"

# GitHub Actions 단발성 트리거용 카테고리 간 대기 시간 밀리초 조정 (10초 단축형 설정)
POST_GAP_SECONDS = 10

# ── 11개 맞춤형 카테고리 테이블 ──────────
CATEGORIES = [
    {"name": "K건강기능식품", "slug": "health-supplements", "id": None, "theme": "건강기능식품 성분 분석과 영양제 선택 가이드", "kw_hint": ["영양제","건강기능식품","비타민","미네랄","프로바이오틱스"]},
    {"name": "K건강정보",    "slug": "health",             "id": 964,  "theme": "만성질환 정보, 건강관리, 질병 예방 케어 가이드", "kw_hint": ["건강정보","만성질환","고혈압","당뇨","면역력"]},
    {"name": "K금융",        "slug": "finance",            "id": None, "theme": "한국형 금융 상품 및 자산 관리 기초 지식", "kw_hint": ["재테크","금융상품","주식","펀드","절세"]},
    {"name": "K보험",        "slug": "insurance",          "id": None, "theme": "외국인/국내 거주자 필수 실손 및 건강보험 안내", "kw_hint": ["건강보험","실손보험","보험료","보험비교","의료비"]},
    {"name": "K뷰티-K웰니스","slug": "kbeauty-wellness",   "id": None, "theme": "K뷰티, 웰니스 트렌드 및 피부/성형 토탈 케어", "kw_hint": ["스킨케어","피부관리","K뷰티","웰니스","성형"]},
    {"name": "K세금-K법",    "slug": "tax-law",            "id": None, "theme": "한국 생활 속 필수 세금 및 법률 가이드", "kw_hint": ["소득세","부가세","세금신고","법률","법인설립"]},
    {"name": "K여행",        "slug": "trip",               "id": None, "theme": "한국 여행 패키지, 호텔예약, 관광 안내", "kw_hint": ["한국여행","서울여행","제주도","관광지","호텔"]},
    {"name": "K유학",        "slug": "study",              "id": None, "theme": "한국 대학 입학, 어학당 프로그램 및 유학 생활 가이드", "kw_hint": ["한국유학","대학입학","어학당","장학금","비자"]},
    {"name": "K의료관광",    "slug": "medical-tour",       "id": None, "theme": "K-의료 서비스 안내 및 병원 예약 지원 정보", "kw_hint": ["의료관광","성형외과","피부과","병원","의료비"]},
    {"name": "K취업",        "slug": "jobs",               "id": None, "theme": "한국 내 취업 시장 정보 및 취업 절차, 비자 가이드", "kw_hint": ["취업","이력서","면접","연봉","비자"]},
    {"name": "VISA",         "slug": "visa-total-care",    "id": None, "theme": "한국 비자 종류별 신청 자격, 서류 및 발급 절차", "kw_hint": ["비자신청","D2비자","E7비자","체류","외국인등록"]},
]

# ── 내부 자산 네트워크 교차 연결 시스템 ──────────
INTERNAL_SITES = [
    ("koreamedicaltour.com",  "한국 의료관광 플랫폼"), ("kskin365.com",          "K뷰티 스킨케어 정보"),
    ("korea365.org",          "한국 생활 종합 가이드"), ("jobinkorea365.com",     "한국 취업 매칭 가이드"),
    ("jobkorea365.com",       "한국 커리어 전문 정보"), ("jobkoreaglobal.com",    "글로벌 인재 취업 가이드"),
    ("kstudy365.com",         "한국 유학 정보 가이드"), ("studyinkorea.com",      "Study in Korea 포털"),
    ("kfinance365.com",       "한국 금융 상품 가이드"), ("koreainvest365.com",    "한국 투자 전략 리포트"),
    ("koreataxlaw.com",       "한국 세금 법률 정보"),   ("k-trip365.com",         "한국 여행 패키지 안내"),
    ("k-visa365.com",         "한국 비자 토탈 케어"),   ("koreacrypto365.com",    "한국 크립토 자산 정보"),
    ("koreainsurance365.com", "한국 실손 건강보험 안내"), ("koreanews365.com",      "한국 종합 뉴스 리포트"),
    ("koreawedding365.com",   "한국 웨딩 트렌드 가이드"), ("ktech365.com",          "한국 테크 산업 정보"),
    ("kworld365.com",         "Kworld365 한국 혜택 케어"), ("oliveyoungkorea.com",   "올리브영 K뷰티 트렌드"),
    ("k-health365.com",       "K-Health365 건강 정보")
]

EXTERNAL_LINKS = [
    ("https://www.mfds.go.kr", "식품의약품안전처"), ("https://www.nih.gov", "미국 국립보건원(NIH)"),
    ("https://pubmed.ncbi.nlm.nih.gov", "PubMed 의학 논문"), ("https://www.who.int", "세계보건기구(WHO)"),
    ("https://www.kdca.go.kr", "질병관리청"), ("https://nhis.or.kr", "국민건강보험공단")
]


def get_category_id(slug):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    try:
        r = requests.get(f"{WP_URL}/wp-json/wp/v2/categories?slug={slug}&per_page=1",
                         headers={"Authorization": f"Basic {auth}"}, timeout=10)
        data = r.json()
        if data and isinstance(data, list):
            return data[0]["id"]
    except Exception:
        pass
    return 1


def init_category_ids():
    print("  [시스템] 워드프레스 카테고리 데이터 동기화 개시...", flush=True)
    for cat in CATEGORIES:
        if cat["id"] is None:
            cat["id"] = get_category_id(cat["slug"])
        print(f"  - {cat['name']:15s} 설정 완료 (ID: {cat['id']})", flush=True)


def build_keyword(cat):
    hints = cat["kw_hint"]
    day = datetime.now().timetuple().tm_yday
    base = hints[day % len(hints)]
    suffixes = ["핵심 가이드라인", "추천 요소 분석", "부작용 예방 가이드", "전문 의료진 정밀 분석", "올바른 관리 기준법"]
    return f"{base} {suffixes[(day + CATEGORIES.index(cat)) % len(suffixes)]}"


def build_prompt(keyword, cat):
    int_links = random.sample(INTERNAL_SITES, 4)
    int_html  = "\n".join([f'   - <a href="https://{domain}/" title="{anchor}" target="_blank">{anchor}</a>' for domain, anchor in int_links])
    ext_links = random.sample(EXTERNAL_LINKS, 4)
    ext_html  = "\n".join([f'   - <a href="{url}" target="_blank" rel="nofollow noopener">{name}</a>' for url, name in ext_links])

    return f"""당신은 최고 권위의 '의학 박사' 페르소나를 가지고 전문 의료 지식을 전달하는 대한민국 최고 수준의 블로거입니다.
아래 지정된 핵심 가이드라인을 완벽히 충족하여 워드프레스 포스팅 본문 HTML 코드를 생성하십시오.

[포커스 키워드]: {keyword}
[지정 카테고리]: {cat['name']} — {cat['theme']}

══════════════════════════
[구글 SEO 및 모바일 가독성 필독 규칙]
══════════════════════════

1. 모바일 기기 레이아웃 절대 우선 규칙 (★최우선 지침)
- 스마트폰 스크롤 독자를 위해 문장 구성을 극도로 쪼개야 합니다.
- 하나의 문단(<p> 태그 블록) 안에는 무조건 1문장 혹은 최대 2문장까지만 배치하십시오.
- 하나의 문단이 끝나면 다음 문단으로 넘어가기 전, 소스 코드상에 반드시 완벽한 빈 줄 공백이 생성되도록 구조화하십시오.

2. 의학 박사 전문 어조 및 데이터 입증
- 모든 문장은 신뢰감 있고 차분한 의학 박사 톤앤매너를 유지하십시오.
- 신뢰도 증명을 위해 정확한 통계 수치나 정밀 데이터 매칭을 본문 내에 3개 이상 반드시 인용하십시오.
- 타겟 키워드는 도입부 첫 100자 이내에 반드시 자연스럽게 출현해야 합니다.

3. 완벽한 구조화 요건
- 본문 텍스트 전체 분량은 HTML 요소 포함 공백 제외 최소 2,500자 이상 확보하십시오.
- 신규 제목(TITLE:)은 클릭율을 극대화할 수 있도록 매력적으로 구성하십시오 (45~60자 내외).
- H2 태그 5개 이상, H3 태그 8개 이상을 레이어별로 고르게 배치하십시오 (H1 태그 절대 사용 금지).
- 본문 중간에 체류시간 증대를 위한 정밀 데이터 요약 표(Table)를 2개 이상 구축하십시오.
- 아래 내부 자산 링크 리스트를 본문 문맥 속에 자연스러운 앵커 텍스트로 융합하여 삽입하십시오:
{int_html}
- 본문 최하단 영역에 외부 권위 기관 출처 링크를 배너 형태로 조립하십시오:
{ext_html}

4. 고정 메커니즘 템플릿
- '복용법', '주의사항', '결론' 테마의 소제목을 단락 내에 무조건 구축하십시오.
- 가독성 하이라이트를 위해 핵심 키워드군에 <strong> 태그를 8~12개 지정하십시오.
- 본문 중단에 아래 규격의 무료 이미지 배치용 마커 태그 3개를 생성하십시오:
  - 검색 엔진 친화적 구조인 FAQ 모듈을 5문제 이상 코딩하십시오 (주석으로 시작할 것)
- 포스팅 최하단에 '연관 키워드' 리스트를 조립하여 마무리하십시오.

[출력 데이터 프로토콜 포맷]
TITLE: [신규 생성 제목]
본문 HTML 소스 코드..."""


def call_writer_engine(prompt):
    url = f"https://api-inference.huggingface.co/models/{HF_MODEL}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": HF_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.65, "max_tokens": 4000}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        if r.status_code == 429:
            time.sleep(25)
            return call_writer_engine(prompt)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"    ❌ 글쓰기 엔지 통신 중단: {e}", flush=True)
        return None


def get_image(query):
    try:
        r = requests.get(f"https://api.pexels.com/v1/search?query={query}&per_page=5&orientation=landscape",
                         headers={"Authorization": PEXELS_KEY}, timeout=10)
        photos = r.json().get("photos", [])
        if photos:
            p = random.choice(photos)
            return {"src": p["src"]["large2x"] or p["src"]["large"], "credit": f'Photo by {p["photographer"]} on Pexels'}
    except Exception:
        pass
    try:
        r = requests.get(f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={requests.utils.quote(query)}&image_type=photo&orientation=horizontal&per_page=5", timeout=10)
        hits = r.json().get("hits", [])
        if hits:
            p = random.choice(hits)
            return {"src": p["webformatURL"], "credit": "Image from Pixabay"}
    except Exception:
        pass
    return {}


def process_content(raw):
    raw = raw.strip().replace("```html", "").replace("```", "").strip()
    lines = raw.split("\n")
    title, meta, tags_str, content = "", "", "", raw
    for i, line in enumerate(lines):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip().strip('`"\' ')
        if "META_DESCRIPTION_EN:" in line:
            meta = line.split("META_DESCRIPTION_EN:")[-1].replace("-->", "").strip()
        if "TAGS:" in line:
            tags_str = line.split("TAGS:")[-1].replace("-->", "").strip()
        if title and meta:
            content = "\n".join(lines[i+1:])
            break

    def img_replacer(m):
        img = get_image(m.group(1).strip())
        alt = m.group(2).strip()
        if img:
            return f'<figure class="wp-block-image size-large aligncenter"><img src="{img["src"]}" alt="{alt}" loading="lazy" style="max-width:100%;height:auto;border-radius:8px"/><figcaption style="text-align:center;font-size:13px;color:#666">{img["credit"]}</figcaption></figure>'
        return f'<p><em>[이미지: {alt}]</em></p>'

    content = re.sub(r'\s*', img_replacer, content, flags=re.DOTALL)
    if "SCHEMA_FAQ" in content:
        content += '\n<script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}</script>'
    
    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
    return {"title": title or "종합 헬스케어 가이드라인 리포트", "meta": meta, "content": content, "tags": tags}


def seo_score(parsed, keyword):
    c, t, m = parsed["content"], parsed["title"], parsed["meta"]
    checks = [
        ("키워드 매칭 여부확인", keyword.split()[0] in t),
        ("메타 태그 인코딩 볼륨", len(m) >= 80),
        ("컨텐츠 스케일 분량 검증", len(c) >= 2300),
        ("H2 대주제 레이어링 트리", c.count("<h2") >= 5),
        ("H3 단락 세부 전개 구조", c.count("<h3") >= 8),
        ("정밀 데이터 테이블 구축", c.count("<table") >= 2),
        ("상호 보완 내부 자산 구조", c.count('.com/') >= 3 or c.count('.org/') >= 1),
    ]
    return min(sum(15 for _, ok in checks if ok), 100)


def get_tag_ids(tags):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    ids = []
    for tag in tags[:6]:
        try:
            r = requests.post(f"{WP_URL}/wp-json/wp/v2/tags", headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"}, json={"name": tag}, timeout=10)
            if r.status_code in [200, 201]:
                ids.append(r.json()["id"])
            elif r.status_code == 400:
                sr = requests.get(f"{WP_URL}/wp-json/wp/v2/tags?search={requests.utils.quote(tag)}", headers={"Authorization": f"Basic {auth}"}, timeout=10)
                if sr.json(): ids.append(sr.json()[0]["id"])
        except Exception:
            pass
    return ids


def post_to_wp(parsed, cat_id, keyword):
    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    tag_ids = get_tag_ids(parsed.get("tags", []))
    try:
        r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
            json={
                "title": parsed["title"], "content": parsed["content"], "status": "publish", "categories": [cat_id], "tags": tag_ids,
                "meta": {"rank_math_focus_keyword": keyword, "rank_math_description": parsed["meta"], "_yoast_wpseo_focuskw": keyword, "_yoast_wpseo_metadesc": parsed["meta"]}
            }, timeout=30)
        r.raise_for_status()
        return r.json().get("id"), r.json().get("link", "")
    except Exception as e:
        print(f"  ❌ 워드프레스 통신 실패 엔드포인트 거부: {e}", flush=True)
        return None, None


def indexnow(post_url):
    for ep in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try: requests.post(ep, json={"host": "k-health365.com", "key": INDEXNOW_KEY, "keyLocation": f"{WP_URL}/{INDEXNOW_KEY}.txt", "urlList": [post_url]}, timeout=10)
        except Exception: pass


def start_trigger_job():
    print(f"\n{'═'*58}", flush=True)
    print(f"  🔄 GitHub Actions 수동 트리거 활성화 — 11개 카테고리 완전 배포 시작", flush=True)
    print(f"{'═'*58}", flush=True)
    
    init_category_ids()
    results = []

    for i, cat in enumerate(CATEGORIES):
        if i > 0:
            time.sleep(POST_GAP_SECONDS)

        keyword = build_keyword(cat)
        print(f"\n  ▶️ [{i+1}/{len(CATEGORIES)}] [{cat['name']}] 포커싱 가동: {keyword}", flush=True)
        
        raw = call_writer_engine(build_prompt(keyword, cat))
        if not raw:
            print("  ❌ 엔진 처리 지연으로 스킵 처리", flush=True)
            continue

        parsed = process_content(raw)
        score  = seo_score(parsed, keyword)
        
        pid, purl = post_to_wp(parsed, cat["id"], keyword)
        if pid:
            indexnow(purl)
            print(f"  ✅ 퍼블리싱 성공 [포스트 ID: {pid}] -> SEO 점수: {score}점", flush=True)
            print(f"  🔗 주소: {purl}", flush=True)
            results.append({"cat": cat["name"], "keyword": keyword, "status": "SUCCESS", "url": purl})
        else:
            print("  ❌ 워드프레스 인젝션 실패", flush=True)

    print(f"\n{'═'*58}", flush=True)
    print(f"  ✅ GitHub Actions 수동 트리거 전 카테고리 발행 프로세스 정상 완료!", flush=True)
    print(f"{'═'*58}", flush=True)


if __name__ == "__main__":
    start_trigger_job()
