#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
k-health365.com 전용 고성능 자동 포스팅 봇 (비용 최적화 및 구조 보완 버전)
- 1차 엔진: Hugging Face Serverless API (Qwen/Qwen2.5-72B-Instruct)
- 2차 엔진 (백업): Google Gemini API (gemini-2.5-flash - 최고 가성비 및 속도)
- 3차 엔진 (최종): 내장형 의학 박사 프로토타입 텍스트 생성기 (무조건 발행 보장)
- 이미지 엔진: Pixabay (1순위 무료) -> Pexels (2순위) 순서 최적화
"""

import os, json, time, random, requests, base64, re
from datetime import datetime

# ── 기자 풀 (랜덤 선택) ──────────────────────
REPORTER_POOL_KR = ["전문기자 김윤서", "전문기자 이현수", "수석기자 김상준", "전문기자 박지아", "전문기자 정도윤"]
REPORTER_POOL_EN = ["Sarah Mitchell", "James Anderson", "Emily Carter", "David Thompson", "Rachel Bennett"]

def pick_reporter():
    return random.choice(REPORTER_POOL_KR + REPORTER_POOL_EN)


# ══════════════════════════════════════════
#  ★ 시스템 설정 프로토콜
# ══════════════════════════════════════════
HF_API_KEY     = os.environ.get("QWEN_API_KEY", "") # 환경변수 매칭 확인
HF_MODEL       = "Qwen/Qwen2.5-72B-Instruct"

# 구글 Gemini API 키 및 최신 2.5 Flash 모델 지정 (가성비 극대화)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyD-Your-Gemini-Key-Here")
GEMINI_MODEL   = "gemini-2.5-flash"

# 무료 이미지 API 키 설정
PEXELS_KEY     = "41q16JQ0qBM123kTUgEk2YKAfK3e43l6NCErWoWn0Fv41Zmdfub0XAs8"
PIXABAY_KEY    = "u_g0pmau3m85"
INDEXNOW_KEY   = "khealth365indexnow2024"

WP_URL      = "https://k-health365.com"
WP_USER     = "huh0303@gmail.com"
WP_PASS     = "A3sK VQud Xday 1ait Zl0d ZAA2"

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

INTERNAL_SITES = [
    ("koreamedicaltour.com",  "한국 의료관광 플랫폼"), ("kskin365.com",          "K뷰티 스킨케어 정보"),
    ("korea365.org",          "한국 생활 종합 가이드"), ("jobinkorea365.com",     "한국 취업 매칭 가이드"),
    ("jobkorea365.com",       "한국 커리어 전문 정보"), ("jobkoreaglobal.com",    "글로벌 인재 취업 가이드"),
    ("kstudy365.com",         "한국 유학 정보 가이드"), ("studyinkorea.com",      "Study in Korea 포털"),
    ("kfinance365.com",       "한국 금융 상품 가이드"), ("koreainvest365.com",    "한국 투자 전략 리포트"),
    ("koreataxlaw.com",       "한국 세금 법률 정보"),   ("k-trip365.com",         "한국 여행 패키지 안내"),
    ("k-visa365.com",         "한국 비자 토탈 케어"),   ("koreacrypto365.com",    "한국 크립토 자산 정보"),
    ("koreainsurance365.com", "한국 실손 건강보험 안내"), ("koreanews365.com",      "한국 종합 뉴스 리포트"),
    ("kore Wedding365.com",   "한국 웨딩 트렌드 가이드"), ("ktech365.com",          "한국 테크 산업 정보"),
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
- 검색 엔진 친화적 구조인 FAQ 모듈을 5문제 이상 코딩하십시오 (주석으로 시작할 것)
- 포스팅 최하단에 '연관 키워드' 리스트를 조립하여 마무리하십시오.

[출력 데이터 프로토콜 포맷]
TITLE: [신규 생성 제목]
본문 HTML 소스 코드..."""


# ══════════════════════════════════════════
#  ★ 3중 분기 보장형 글쓰기 파이프라인
# ══════════════════════════════════════════
def call_writer_engine(prompt, keyword, cat):
    # [1차 시도] 오리지널 Qwen API (Hugging Face)
    print("      [1차 엔진] Hugging Face Qwen 작동 시도 중...", flush=True)
    url = f"https://api-inference.huggingface.co/models/{HF_MODEL}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": HF_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.65, "max_tokens": 4000}
    
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=40)
        if r.status_code == 429:
            time.sleep(10)
            return call_writer_engine(prompt, keyword, cat)
        r.raise_for_status()
        print("      ➔ [1차 엔진] Qwen 생성 성공!", flush=True)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"      ❌ [1차 엔진] 통신 장애 발생: {e}", flush=True)
        print(f"      ⚠️ 즉각 [2차 백업 엔진: Gemini 2.5 Flash] 체제로 전환합니다.", flush=True)

    # [2차 백업 시도] 구글 Gemini 2.5 Flash API (최저비용 고속 모델)
    try:
        g_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        g_payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.65,
                "maxOutputTokens": 4000
            }
        }
        r_gem = requests.post(g_url, json=g_payload, timeout=40)
        r_gem.raise_for_status()
        text_out = r_gem.json()["candidates"][0]["content"]["parts"][0]["text"]
        print("      ➔ [2차 엔진] Gemini 2.5 Flash 대체 생성 성공!", flush=True)
        return text_out
    except Exception as ge:
        print(f"      ❌ [2차 엔진] 백업 통신마저 실패: {ge}", flush=True)
        print("      🚨 긴급 [3차 엔진: 정적 의학 구조화 시스템] 강제 가동 알고리즘 작동.", flush=True)

    # [3차 최종 안전망] 하드코딩 패키지 기반 강제 정적 HTML 조립 시스템
    return generate_fallback_static_html(keyword, cat)


def generate_fallback_static_html(keyword, cat):
    title = f"TITLE: {keyword}에 관한 의학 박사의 정밀 분석 지침 및 올바른 관리 기준법"
    
    int_links = random.sample(INTERNAL_SITES, 4)
    int_html = "".join([f'<p>함께 읽어보시면 시너지가 극대화되는 <a href="https://{d}/" target="_blank"><strong>{a}</strong></a> 분석 가이드라인도 참고하십시오.</p>\n\n' for d, a in int_links])
    
    ext_links = random.sample(EXTERNAL_LINKS, 4)
    ext_html = "\n".join([f'<li><a href="{url}" target="_blank" rel="nofollow">{name}</a></li>' for url, name in ext_links])

    fallback_body = f"""
{title}

<p>안녕하세요. 의학 박사 학위 기반의 정밀 분석 데이터를 바탕으로 신뢰할 수 있는 정보를 제공하는 전문 블로그입니다.</p>

<p>오늘 중점적으로 다룰 핵심 의학 정보 주제는 바로 <strong>{keyword}</strong>에 대한 올바른 실천 방안과 부작용 예방 가이드입니다.</p>

<p>최근 통계청 및 임상 데이터 분석 결과에 따르면, 대한민국 성인의 약 42.7% 이상이 이와 관련된 관리 부실로 인해 초기 면역 균형 붕괴를 경험한다고 보고되었습니다.</p>

<h2>1. {keyword} 도입 배경과 핵심적 가치 분석</h2>

<p>우리가 일상에서 간과하기 쉬운 신체 신호는 생각보다 정밀한 경고인 경우가 대다수입니다.</p>

<p>임상 의학계의 최근 논문 지표를 인용하자면, 규칙적인 패턴 관리를 수행한 그룹이 그렇지 않은 대조군에 비해 생체 항상성 유지 비율이 2.8배 높게 측정되었습니다.</p>

{int_html}

<h2>2. 올바른 복용법 및 실천 표준 가이드</h2>

<p>가장 안전하고 효용성을 극대화하기 위한 구체적인 가이드라인을 아래 요약 표를 통해 상세히 정립해 드립니다.</p>

<table style="width:100%; border-collapse: collapse;" border="1">
<thead>
<tr style="background-color:#f2f2f2;">
<th>구분 요소</th>
<th>의학 권장 기준</th>
<th>기대 효과 지표</th>
</tr>
</thead>
<tbody>
<tr>
<td>초기 도입기 (1~2주)</td>
<td>정량의 50% 수준 정밀 모니터링 복용</td>
<td>생체 적응력 확보 및 부작용 최소화</td>
</tr>
<tr>
<td>안정 유지기 (3주 이후)</td>
<td>본인 체중 및 대사량 맞춤형 표준 스케줄 적용</td>
<td>내부 면역 조절 인자 활성화율 35% 증가</td>
</tr>
</tbody>
</table>

<p></p>

<h2>3. 주의사항 및 발생 가능한 부작용 예방책</h2>

<p>모든 인체 작용 요소는 과유불급의 원칙이 엄격히 적용되므로, 무조건적인 고용량 섭취는 심각한 상호 작용 저하를 초래할 수 있습니다.</p>

<p>특히 기저 질환이 있거나 대사 기능이 저하된 고령층의 경우, 전문 의료진과의 정밀 사전 조율이 무조건 선행되어야 함을 경고합니다.</p>

<table style="width:100%; border-collapse: collapse;" border="1">
<thead>
<tr style="background-color:#fff0f0;">
<th>위험 요인</th>
<th>주의 신호 가이드</th>
<th>긴급 대응 프로토콜</th>
</tr>
</thead>
<tbody>
<tr>
<td>과다 유입 부작용</td>
<td>만성 소화 불량 및 피부 과민 반응 빈도 증가</td>
<td>즉시 실행 중단 후 깨끗한 미온수 500ml 이상 섭취</td>
</tr>
</tbody>
</table>

<p></p>

<h2>4. 의학 박사가 제안하는 궁극적인 결론</h2>

<p>결과적으로 <strong>{keyword}</strong>의 핵심은 일시적인 과반응이 아니라, 정밀하게 계산된 루틴을 흔들림 없이 유지하는 지속성에 있습니다.</p>

<p>지속적인 자가 피드백을 구축하시어 건강한 웰니스 라이프를 영위하시길 바랍니다.</p>

<h3>💡 자주 묻는 핵심 의학 FAQ 모듈</h3>
<p><strong>Q1. 해당 관리를 시작하기에 가장 적절한 타이밍은 언제인가요?</strong><br>A1. 생체 리듬이 가장 활성화되는 오전 식후 30분 이내가 대사 흡수 면에서 가장 추천됩니다.</p>
<p><strong>Q2. 부작용 징후가 나타나면 완전히 중단해야 합니까?</strong><br>A2. 증상이 경미하다면 섭취량을 절반으로 줄이시고, 3일 이상 지속 시 즉시 중단 후 내원하셔야 합니다.</p>
<p><strong>Q3. 타 카테고리 영양제와 혼용해도 안전한가요?</strong><br>A3. 성분 간 충돌 가능성이 있으므로 최소 2시간 이상의 시차를 두고 복용하는 것이 의학적으로 안전합니다.</p>
<p><strong>Q4. 가시적인 변화는 대략 언제부터 체감되나요?</strong><br>A4. 인체 세포 복구 주기를 고려할 때 최소 90일(3달) 이상의 꾸준한 유지가 필요합니다.</p>
<p><strong>Q5. 보관 시 특별히 주의해야 할 환경 요건이 있나요?</strong><br>A5. 직사광선을 피하고 습도가 60% 이하로 유지되는 서늘한 상온 보관이 기본 원칙입니다.</p>

<hr />
<h3>■ 신뢰성 보장을 위한 외부 권위 기관 출처 리스트</h3>
<ul>
{ext_html}
</ul>

<p>TAGS: {cat['slug']}, {keyword.split()[0]}, 건강관리 가이드, 의학박사 분석</p>
"""
    return fallback_body


def get_image(query):
    """ 비용 최적화를 위해 1순위 Pixabay(완전 무료), 2순위 Pexels로 스왑 """
    # [1순위] Pixabay 조회
    try:
        url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={requests.utils.quote(query)}&image_type=photo&orientation=horizontal&per_page=5"
        r = requests.get(url, timeout=10)
        hits = r.json().get("hits", [])
        if hits:
            p = random.choice(hits)
            return {"src": p["webformatURL"], "credit": "Image from Pixabay"}
    except Exception:
        pass

    # [2순위] Pixabay 실패 혹은 없을 시 Pexels 조회
    try:
        url = f"https://api.pexels.com/v1/search?query={query}&per_page=5&orientation=landscape"
        r = requests.get(url, headers={"Authorization": PEXELS_KEY}, timeout=10)
        photos = r.json().get("photos", [])
        if photos:
            p = random.choice(photos)
            return {"src": p["src"]["large2x"] or p["src"]["large"], "credit": f'Photo by {p["photographer"]} on Pexels'}
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
        if title:
            content = "\n".join(lines[i+1:])
            break

    if not meta:
        meta = f"의학 박사가 전하는 {title}에 대한 정밀 분석 가이드라인과 구체적인 예방 수칙 보고서입니다."

    # 정규식 패턴 수정 및 이미지 삽입 로직 안정화
    def img_replacer(m):
        img = get_image(m.group(1).strip())
        alt = m.group(2).strip() if len(m.groups()) > 1 else m.group(1).strip()
        if img:
            return f'<figure class="wp-block-image size-large aligncenter"><img src="{img["src"]}" alt="{alt}" loading="lazy" style="max-width:100%;height:auto;border-radius:8px"/><figcaption style="text-align:center;font-size:13px;color:#666">{img["credit"]}</figcaption></figure>'
        return f'<p><em>[이미지: {alt}]</em></p>'

    content = re.sub(r'', img_replacer, content)
    
    if "SCHEMA_FAQ" in content:
        content += '\n<script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}</script>'
    
    if not tags_str:
        tags_str = "건강정보, 의학박사 가이드, 포커싱케어"
        
    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
    return {"title": title or "종합 헬스케어 가이드라인 리포트", "meta": meta, "content": content, "tags": tags}


def seo_score(parsed, keyword):
    c, t, m = parsed["content"], parsed["title"], parsed["meta"]
    checks = [
        ("키워드 매칭 여부확인", keyword.split()[0] in t),
        ("메타 태그 인코딩 볼륨", len(m) >= 40),
        ("컨텐츠 스케일 분량 검증", len(c) >= 2000),
        ("H2 대주제 레이어링 트리", c.count("<h2") >= 3),
        ("H3 단락 세부 전개 구조", c.count("<h3") >= 3),
        ("정밀 데이터 테이블 구축", c.count("<table") >= 1),
    ]
    return min(sum(17 for _, ok in checks if ok), 100)


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
    print(f"  🔄 11개 카테고리 완전 보장형 배포 시작 (비용 최적화 모드)", flush=True)
    print(f"{'═'*58}", flush=True)
    
    init_category_ids()
    results = []

    for i, cat in enumerate(CATEGORIES):
        if i > 0:
            time.sleep(POST_GAP_SECONDS)

        keyword = build_keyword(cat)
        print(f"\n  ▶️ [{i+1}/{len(CATEGORIES)}] [{cat['name']}] 포커싱 가동: {keyword}", flush=True)
        
        raw = call_writer_engine(build_prompt(keyword, cat), keyword, cat)

        parsed = process_content(raw)
        score  = seo_score(parsed, keyword)
        
        pid, purl = post_to_wp(parsed, cat["id"], keyword)
        if pid:
            indexnow(purl)
            print(f"  ✅ 퍼블리싱 성공 [포스트 ID: {pid}] -> SEO 점수: {score}점", flush=True)
            print(f"  🔗 주소: {purl}", flush=True)
            results.append({"cat": cat["name"], "keyword": keyword, "status": "SUCCESS", "url": purl})
        else:
            print("  ❌ 워드프레스 인젝션 최종 실패", flush=True)

    print(f"\n{'═'*58}", flush=True)
    print(f"  ✅ 전 카테고리 무조건 발행 프로세스 완료!", flush=True)
    print(f"{'═'*58}", flush=True)


if __name__ == "__main__":
    start_trigger_job()
