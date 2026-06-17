import os
import sys
import time
import random
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

# ============================================================
# 환경 변수 및 설정
# ============================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PIXABAY_KEY    = os.getenv("PIXABAY_KEY")
PEXELS_KEY     = os.getenv("PEXELS_KEY")
SHEETS_WEBHOOK = os.getenv("SHEETS_WEBHOOK")  # 구글 시트 연결 웹훅 주소
WP_USER        = "huh0303@gmail.com"

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# 10인 가상 기자단 풀
REPORTERS = [
    "김민준 기자 (minjun@kworld365.com)", "이서연 기자 (seoyeon@kworld365.com)",
    "박현우 기자 (hyunwoo@kworld365.com)", "최지아 기자 (jia@kworld365.com)",
    "정재희 기자 (jaehee@kworld365.com)", "James Wilson (james@kworld365.com)",
    "Emily Anderson (emily@kworld365.com)", "Michael Chang (michael@kworld365.com)",
    "Sarah Jenkins (sarah@kworld365.com)", "David Miller (david@kworld365.com)"
]

HEALTH_CATEGORIES = [2, 3, 4, 5, 6]

# 글 끝에 붙일 태그 개수 (사용자 요구: 정확히 12개)
TAG_COUNT = 12

# ============================================================
# ✅ 도메인 오타 수정: koreavedding365.com → koreawedding365.com
#    (사용자가 제시한 22개 정확한 도메인 목록 기준으로 전체 재검증 완료)
# ============================================================
SITES_CONFIG = [
    {"url": "https://k-health365.com",      "type": "hub",  "lang": "ko", "theme": "건강과 의학", "keywords_file": ".github/workflows/keywords_khealth.txt", "wp_pass_env": "K_HEALTH365COM"},
    {"url": "https://koreanews365.com",      "type": "news", "lang": "ko", "theme": "한국 뉴스",   "keywords_file": ".github/workflows/keywords_koreanews.txt", "wp_pass_env": "KOREANEWS365COM"},
    {"url": "https://theseouljournal.com",   "type": "global","lang": "en", "theme": "Seoul Lifestyle", "keywords_file": ".github/workflows/keywords_seouljournal.txt", "wp_pass_env": "THESEOULJOURNALCOM"},
    {"url": "https://koreamedicaltour.com",  "type": "global","lang": "en", "theme": "Korea Medical Tourism", "keywords_file": ".github/workflows/keywords_medicaltour.txt", "wp_pass_env": "KOREAMEDICALTOURCOM"},
    {"url": "https://kskin365.com",          "type": "global","lang": "en", "theme": "K-Beauty",   "keywords_file": ".github/workflows/keywords_kskin.txt", "wp_pass_env": "KSKIN365COM"},
    {"url": "https://korea365.org",          "type": "global","lang": "en", "theme": "Korea Culture", "keywords_file": ".github/workflows/keywords_korea365.txt", "wp_pass_env": "KOREA365ORG"},
    {"url": "https://jobinkorea365.com",     "type": "global","lang": "en", "theme": "Jobs in Korea", "keywords_file": ".github/workflows/keywords_jobinkorea365.txt", "wp_pass_env": "JOBINKOREA365COM"},
    {"url": "https://jobkorea365.com",       "type": "global","lang": "en", "theme": "Employment", "keywords_file": ".github/workflows/keywords_jobkorea365.txt", "wp_pass_env": "JOBKOREA365COM"},
    {"url": "https://jobkoreaglobal.com",    "type": "global","lang": "en", "theme": "Recruitment", "keywords_file": ".github/workflows/keywords_jobkoreaglobal.txt", "wp_pass_env": "JOBKOREAGLOBALCOM"},
    {"url": "https://kstudy365.com",         "type": "global","lang": "en", "theme": "Study in Korea", "keywords_file": ".github/workflows/keywords_kstudy365.txt", "wp_pass_env": "KSTUDY365COM"},
    {"url": "https://studyinkorea365.com",   "type": "global","lang": "en", "theme": "International Students", "keywords_file": ".github/workflows/keywords_koreanews.txt", "wp_pass_env": "STUDYINKOREA365COM"},
    {"url": "https://kfinance365.com",       "type": "global","lang": "en", "theme": "Finance",    "keywords_file": ".github/workflows/keywords_kfinance.txt", "wp_pass_env": "KFINANCE365COM"},
    {"url": "https://koreainvest365.com",    "type": "global","lang": "en", "theme": "Investment", "keywords_file": ".github/workflows/keywords_kinvest.txt", "wp_pass_env": "KOREAINVEST365COM"},
    {"url": "https://koreataxnlaw.com",      "type": "global","lang": "en", "theme": "Tax and Law", "keywords_file": ".github/workflows/keywords_ktax.txt", "wp_pass_env": "KOREATAXNLAW365COM"},
    {"url": "https://k-trip365.com",         "type": "global","lang": "en", "theme": "Travel",     "keywords_file": ".github/workflows/keywords_ktrip.txt", "wp_pass_env": "KTRIP365COM"},
    {"url": "https://k-visa365.com",         "type": "global","lang": "en", "theme": "Visa Guide", "keywords_file": ".github/workflows/keywords_kvisa.txt", "wp_pass_env": "KVISA365COM"},
    {"url": "https://koreacrypto365.com",    "type": "global","lang": "en", "theme": "Crypto",     "keywords_file": ".github/workflows/keywords_kcrypto.txt", "wp_pass_env": "KOREACRYPTO365COM"},
    {"url": "https://koreainsurance365.com", "type": "global","lang": "en", "theme": "Insurance",  "keywords_file": ".github/workflows/keywords_kinsurance.txt", "wp_pass_env": "KOREAINSURANCE365COM"},
    {"url": "https://koreawedding365.com",   "type": "global","lang": "en", "theme": "Wedding",    "keywords_file": ".github/workflows/keywords_kwedding.txt", "wp_pass_env": "KOREAWEDDING365COM"},
    {"url": "https://ktech365.com",          "type": "global","lang": "en", "theme": "Technology", "keywords_file": ".github/workflows/keywords_ktech.txt", "wp_pass_env": "KTECH365COM"},
    {"url": "https://kworld365.com",         "type": "global","lang": "en", "theme": "K-POP",      "keywords_file": ".github/workflows/keywords_kworld.txt", "wp_pass_env": "KWORLD365COM"},
    {"url": "https://oliveyoungkorea.com",   "type": "global","lang": "en", "theme": "K-Beauty Reviews", "keywords_file": ".github/workflows/keywords_oliveyoung.txt", "wp_pass_env": "OLIVEYOUNGKOREACOM"},
]

# ============================================================
# ✅ 외부 권위 사이트 (구글 E-E-A-T / 애드센스 점수용 아웃바운드 링크)
#    테마별로 분류 — 실제 도달 가능한 권위 도메인만 사용
# ============================================================
EXTERNAL_AUTHORITY_LINKS = {
    "건강과 의학": [
        ("질병관리청", "https://www.kdca.go.kr"),
        ("대한의학회", "https://www.kams.or.kr"),
        ("WHO", "https://www.who.int"),
        ("국민건강보험공단", "https://www.nhis.or.kr"),
        ("식품의약품안전처", "https://www.mfds.go.kr"),
        ("PubMed", "https://pubmed.ncbi.nlm.nih.gov"),
    ],
    "한국 뉴스": [
        ("대한민국 정책브리핑", "https://www.korea.kr"),
        ("통계청", "https://kostat.go.kr"),
        ("기획재정부", "https://www.moef.go.kr"),
        ("연합뉴스", "https://www.yna.co.kr"),
    ],
    "default_en": [
        ("Korea.net", "https://www.korea.net"),
        ("Visit Korea", "https://english.visitkorea.or.kr"),
        ("Invest Korea", "https://www.investkorea.org"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
        ("Ministry of Justice Korea", "https://www.moj.go.kr/moj/index.do"),
        ("Wikipedia", "https://en.wikipedia.org"),
    ],
    "Finance": [
        ("Bank of Korea", "https://www.bok.or.kr/eng"),
        ("Financial Services Commission", "https://www.fsc.go.kr/eng"),
        ("Korea Exchange", "https://global.krx.co.kr"),
    ],
    "Investment": [
        ("Bank of Korea", "https://www.bok.or.kr/eng"),
        ("Korea Exchange", "https://global.krx.co.kr"),
        ("Invest Korea", "https://www.investkorea.org"),
    ],
    "Tax and Law": [
        ("National Tax Service", "https://www.nts.go.kr/english"),
        ("Ministry of Justice Korea", "https://www.moj.go.kr/moj/index.do"),
        ("Korea Legislation Research Institute", "https://elaw.klri.re.kr"),
    ],
    "Jobs in Korea": [
        ("Ministry of Employment and Labor", "https://www.moel.go.kr/english"),
        ("HRD Korea", "https://www.hrdkorea.or.kr/eng"),
        ("Work24", "https://www.work24.go.kr"),
    ],
    "Employment": [
        ("Ministry of Employment and Labor", "https://www.moel.go.kr/english"),
        ("Work24", "https://www.work24.go.kr"),
    ],
    "Recruitment": [
        ("Ministry of Employment and Labor", "https://www.moel.go.kr/english"),
        ("HRD Korea", "https://www.hrdkorea.or.kr/eng"),
    ],
    "Study in Korea": [
        ("Study in Korea (NIIED)", "https://www.studyinkorea.go.kr"),
        ("Ministry of Education Korea", "https://english.moe.go.kr"),
        ("NIIED", "https://www.niied.go.kr/eng"),
    ],
    "International Students": [
        ("Study in Korea (NIIED)", "https://www.studyinkorea.go.kr"),
        ("HiKorea (Immigration)", "https://www.hikorea.go.kr"),
    ],
    "Visa Guide": [
        ("HiKorea (Immigration)", "https://www.hikorea.go.kr"),
        ("Ministry of Justice Korea", "https://www.moj.go.kr/moj/index.do"),
    ],
    "Korea Medical Tourism": [
        ("Korea Health Industry Development Institute", "https://www.khidi.or.kr/eps"),
        ("Visit Korea", "https://english.visitkorea.or.kr"),
    ],
    "K-Beauty": [
        ("Visit Korea", "https://english.visitkorea.or.kr"),
        ("Korea.net", "https://www.korea.net"),
    ],
    "K-Beauty Reviews": [
        ("Visit Korea", "https://english.visitkorea.or.kr"),
        ("Korea.net", "https://www.korea.net"),
    ],
    "Travel": [
        ("Visit Korea", "https://english.visitkorea.or.kr"),
        ("Korea Tourism Organization", "https://www.knto.or.kr"),
    ],
    "Korea Culture": [
        ("Korea.net", "https://www.korea.net"),
        ("Korean Culture and Information Service", "https://www.kocis.go.kr"),
    ],
    "Crypto": [
        ("Financial Services Commission", "https://www.fsc.go.kr/eng"),
        ("Bank of Korea", "https://www.bok.or.kr/eng"),
    ],
    "Insurance": [
        ("Financial Services Commission", "https://www.fsc.go.kr/eng"),
        ("National Health Insurance Service", "https://www.nhis.or.kr/english"),
    ],
    "Wedding": [
        ("Visit Korea", "https://english.visitkorea.or.kr"),
        ("Korea.net", "https://www.korea.net"),
    ],
    "Technology": [
        ("Ministry of Science and ICT", "https://www.msit.go.kr/eng"),
        ("NIPA", "https://www.nipa.kr/home/eng"),
    ],
    "K-POP": [
        ("Korea.net", "https://www.korea.net"),
        ("Korean Culture and Information Service", "https://www.kocis.go.kr"),
    ],
    "Seoul Lifestyle": [
        ("Seoul Metropolitan Government", "https://english.seoul.go.kr"),
        ("Visit Korea", "https://english.visitkorea.or.kr"),
    ],
}


def load_keyword(filename, fallback):
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                keywords = [l.strip() for l in f if l.strip()]
            if keywords:
                return random.choice(keywords)
    except Exception:
        pass
    return fallback


def crawl_rss_news():
    try:
        res = requests.get("https://fs.khan.co.kr/rss/rssdata/total_news.xml", timeout=10)
        soup = BeautifulSoup(res.text, 'xml')
        items = soup.find_all('item')
        if items:
            chosen = random.choice(items)
            return chosen.title.text, chosen.description.text
    except Exception:
        pass
    return "대한민국 최신 경제 및 사회 변화 트렌드 분석", "최신 주요 시사 이슈 및 정책 변화에 대한 심층 기사입니다."


def make_seo_prompt(keyword, theme, lang, mode="blog"):
    reporter = random.choice(REPORTERS)
    tag_lang = "영어로" if lang == "en" else "한국어로"

    if mode == "news":
        return f"""
        당신은 주요 일간지의 시니어 취재기자입니다.
        주제: '{keyword}'에 대해 엄격한 신문기사체 기사를 작성하세요.

        [필수 지침]
        1. 문체: 절대 블로그 형식을 쓰지 마십시오. '했다', '밝혔다', '조사됐다'로 끝나는 6하원칙 기사체여야 합니다.
        2. 바이라인: 기사 맨 위에 반드시 '◇ {reporter}'를 한 줄 삽입하십시오.
        3. 분량 및 구조: HTML 태그(h2, h3, p, strong)만 사용해 1500자 내외로 명확하고 간결하게 작성하세요. 마크다운 금지.
        4. 내용: 첫 단락에 핵심 리드문을 작성하고, 전문적인 인터뷰 인용구나 통계 수치를 가상으로 포함하여 신뢰도를 극대화하십시오.
        5. 태그 매칭: 기사 본문이 모두 끝난 다음, 반드시 새로운 줄에 'TAGS:' 라는 단어로 시작하는 줄을 추가하고,
           그 뒤에 정확히 {TAG_COUNT}개의 연관 핵심 키워드 단어를 {tag_lang} 추출하여 쉼표(,)로만 연결해 한 줄로 출력하세요.
           예시 형식: TAGS: 키워드1,키워드2,키워드3
        """

    persona = "의학 박사" if "건강" in theme or "medical" in theme.lower() else "산업 분야 최고 전문 자문위원"
    return f"""
    당신은 {persona}이자 15년 경력의 SEO 콘텐츠 마스터 프로라이터입니다.
    주제: '{keyword}' ({theme})
    언어: {lang}

    [구글 애드센스 평가 고득점 핵심 지침]
    1. HTML 전용: 오직 h2, h3, p, ul, li, ol, strong 태그만 사용하고 마크다운(*)은 절대 쓰지 마세요.
    2. 키워드 최적화: 첫 단락 문두에 '{keyword}'를 무조건 배치하고, 전체 글에 자연스럽게 10회 이상 분산 삽입하세요.
    3. 구조 다각화: h2 태그 최소 4개 이상, h3 태그 최소 4개 이상 배치하고, 가독성을 위한 불릿 포인트(ul/li) 리스트를 3개 이상 쪼개어 구성하세요.
    4. 정보량: 깊이 있고 유용한 가치를 주기 위해 상세한 설명글로만 가득 채우십시오.
    5. 태그 매칭: 본문이 모두 끝난 다음, 반드시 새로운 줄에 'TAGS:' 라는 단어로 시작하는 줄을 추가하고,
       그 뒤에 정확히 {TAG_COUNT}개의 연관 핵심 키워드 단어를 {tag_lang} 추출하여 쉼표(,)로만 연결해 한 줄로 출력하세요.
       예시 형식: TAGS: 키워드1,키워드2,키워드3
    """


def extract_tags_from_article(article_text, fallback_keyword):
    """
    Gemini 응답 본문 끝의 'TAGS: ...' 라인을 찾아 분리한다.
    - 본문(article_body): TAGS 라인을 제거한 순수 HTML
    - tags(list[str]): 정확히 TAG_COUNT개로 보정된 태그 리스트
    """
    lines = article_text.strip().split("\n")
    tags = []
    body_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("TAGS:"):
            raw = stripped.split(":", 1)[1] if ":" in stripped else ""
            tags = [t.strip() for t in raw.split(",") if t.strip()]
        else:
            body_lines.append(line)

    article_body = "\n".join(body_lines).strip()

    # 태그가 비었거나 개수가 부족/과다하면 보정
    if not tags:
        tags = [fallback_keyword]

    # 중복 제거 (순서 유지)
    seen = set()
    deduped = []
    for t in tags:
        key = t.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(t)
    tags = deduped

    if len(tags) > TAG_COUNT:
        tags = tags[:TAG_COUNT]
    elif len(tags) < TAG_COUNT:
        # 부족하면 fallback_keyword 변형으로 채움 (워드프레스 태그 개수 요건 보장)
        i = 1
        while len(tags) < TAG_COUNT:
            filler = f"{fallback_keyword} {i}" if i > 1 else fallback_keyword
            if filler.lower() not in seen:
                tags.append(filler)
                seen.add(filler.lower())
            i += 1

    return article_body, tags


def get_or_create_tag_ids(site_url, wp_pass, tag_names):
    """
    워드프레스 REST API로 태그 이름들을 실제 tag term ID로 변환.
    이미 존재하면 검색해서 ID를 가져오고, 없으면 새로 생성한다.
    """
    tag_ids = []
    for name in tag_names:
        try:
            # 1. 기존 태그 검색
            search_res = requests.get(
                f"{site_url}/wp-json/wp/v2/tags",
                params={"search": name, "per_page": 5},
                auth=(WP_USER, wp_pass),
                timeout=10
            )
            existing = None
            if search_res.status_code == 200:
                for t in search_res.json():
                    if t.get("name", "").strip().lower() == name.strip().lower():
                        existing = t
                        break

            if existing:
                tag_ids.append(existing["id"])
                continue

            # 2. 없으면 신규 생성
            create_res = requests.post(
                f"{site_url}/wp-json/wp/v2/tags",
                json={"name": name},
                auth=(WP_USER, wp_pass),
                timeout=10
            )
            if create_res.status_code in (200, 201):
                tag_ids.append(create_res.json()["id"])
            elif create_res.status_code == 400:
                # 이미 존재하는데 검색에서 못 찾은 케이스 (슬러그 충돌 등) → 재검색
                data = create_res.json()
                existing_id = data.get("data", {}).get("term_id") or data.get("term_id")
                if existing_id:
                    tag_ids.append(existing_id)
        except Exception as e:
            print(f"  ⚠️ 태그 처리 실패 ({name}): {e}")
            continue

    return tag_ids


def get_multiple_images(keyword, count=3):
    urls = []
    try:
        q = keyword.encode('ascii', 'ignore').decode().strip() or "korea"
        url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={requests.utils.quote(q)}&image_type=photo&per_page=10&safesearch=true"
        res = requests.get(url, timeout=10).json()
        if res.get("hits"):
            hits = random.sample(res["hits"], min(count, len(res["hits"])))
            for h in hits:
                urls.append(h["webformatURL"])
    except Exception:
        pass
    return urls


def upload_to_wp_media(site_url, wp_pass, img_url, keyword, idx):
    try:
        img_data = requests.get(img_url, timeout=10).content
        filename = f"seo-{keyword.replace(' ', '-')}-{idx}.jpg"
        headers = {"Content-Disposition": f"attachment; filename={filename}", "Content-Type": "image/jpeg"}
        res = requests.post(f"{site_url}/wp-json/wp/v2/media", data=img_data, headers=headers, auth=(WP_USER, wp_pass), timeout=20)
        if res.status_code == 201:
            return res.json().get("id")
    except Exception:
        pass
    return None


def build_spider_web_links(keyword, current_url, lang, link_count=6):
    """
    ✅ 내부(사이트간) 거미줄 링크 강화: 기존 4개 → 6개로 확대
    """
    others = [s for s in SITES_CONFIG if s['url'] != current_url]
    selected = random.sample(others, k=min(link_count, len(others)))
    html = "<div style='margin-top:30px; background:#f9f9f9; padding:15px; border-left:4px solid #0066cc;'>"
    html += f"<h4>🔗 {keyword} 연관 인기 가이드</h4><ul style='list-style:none; padding-left:0;'>"
    for s in selected:
        anchor = f"✨ [{s['theme']}] {keyword} 관련 연관 분석" if lang == 'ko' else f"✨ {keyword} Extensive Industry Report"
        html += f"<li style='margin-bottom:8px;'><a href='{s['url']}/?s={requests.utils.quote(keyword)}' target='_blank' rel='noopener'>{anchor}</a></li>"
    html += "</ul></div>"
    return html


def build_related_search_links(keyword, lang):
    """내부 검색 연관어 (사이트 내부용, 외부링크와는 별개)"""
    words = [f"{keyword} 효능", f"{keyword} 부작용", f"{keyword} 가격", f"{keyword} 추천", f"{keyword} 비교"] if lang == 'ko' else [f"{keyword} cost", f"{keyword} review", f"{keyword} comparison", f"{keyword} guide", f"best {keyword}"]
    html = "<div style='margin-top:20px; border-top:1px dashed #ccc; padding-top:15px;'>"
    html += "<strong>💡 연관 검색어 바로가기: </strong> "
    links = []
    for w in words:
        links.append(f"<a href='?s={requests.utils.quote(w)}' style='color:#555; text-decoration:underline; margin-right:10px;'>#{w}</a>")
    html += ", ".join(links) + "</div>"
    return html


def build_external_authority_links(theme, lang, link_count=4):
    """
    ✅ 신규 추가: 구글 E-E-A-T / 애드센스 점수 향상을 위한 권위 외부링크 블록.
    테마별로 매칭되는 정부기관/공신력있는 기관 사이트로 아웃바운드 링크를 건다.
    """
    pool = EXTERNAL_AUTHORITY_LINKS.get(theme)
    if not pool:
        pool = EXTERNAL_AUTHORITY_LINKS.get("default_en" if lang == "en" else "한국 뉴스", [])
    if not pool:
        return ""

    selected = random.sample(pool, k=min(link_count, len(pool)))
    label = "📚 참고자료 및 공식 출처" if lang == "ko" else "📚 References & Official Sources"
    html = "<div style='margin-top:25px; background:#eef5ff; padding:15px; border-left:4px solid #1a73e8;'>"
    html += f"<h4>{label}</h4><ul style='padding-left:20px;'>"
    for name, url in selected:
        html += f"<li><a href='{url}' target='_blank' rel='nofollow noopener'>{name}</a></li>"
    html += "</ul></div>"
    return html


def log_to_google_sheet(site_url, title, tag_count=None, status="success"):
    if not SHEETS_WEBHOOK:
        return
    try:
        payload = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "site": site_url,
            "title": title,
            "tag_count": tag_count,
            "status": status,
        }
        requests.post(SHEETS_WEBHOOK, json=payload, timeout=10)
        print(f"📊 구글 스프레드시트 전송 완료: {title}")
    except Exception:
        print("⚠️ 구글 스프레드시트 전송 실패")


def publish_post(site, keyword, theme, lang, mode, category_ids):
    """
    공통 발행 로직:
    1. Gemini로 본문 + TAGS 생성
    2. 본문/태그 분리
    3. 이미지 업로드
    4. 태그 이름 → 태그 ID 변환 (실제 워드프레스 tags 필드에 들어가도록)
    5. 내부 거미줄 링크 + 외부 권위 링크 삽입
    6. 포스트 발행
    """
    wp_pass = os.getenv(site['wp_pass_env'])
    if not wp_pass:
        print(f"⏭️  {site['url']} - 비밀번호 환경변수 없음, 스킵")
        return False

    prompt = make_seo_prompt(keyword, theme, lang, mode)
    try:
        res = gemini_client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        raw_text = res.text if res.text else ""
    except Exception as e:
        print(f"  ❌ Gemini 생성 실패 ({site['url']}): {e}")
        return False

    if len(raw_text) < 300:
        print(f"  ⚠️ 본문이 너무 짧음, 스킵: {site['url']}")
        return False

    article_body, tag_names = extract_tags_from_article(raw_text, keyword)

    # 링크 블록 삽입 (내부 거미줄 + 내부 검색 연관어 + 외부 권위 링크)
    article_body += build_spider_web_links(keyword, site['url'], lang)
    article_body += build_related_search_links(keyword, lang)
    article_body += build_external_authority_links(theme, lang)

    # 이미지 업로드
    img_urls = get_multiple_images(keyword, 3)
    media_ids = []
    for idx, url in enumerate(img_urls):
        mid = upload_to_wp_media(site['url'], wp_pass, url, keyword, idx)
        if mid:
            media_ids.append(mid)

    # ✅ 태그 이름 → 실제 워드프레스 태그 ID로 변환
    tag_ids = get_or_create_tag_ids(site['url'], wp_pass, tag_names)

    if lang == 'ko':
        title = f"[속보] {keyword}" if mode == "news" else f"{keyword} 정보 완벽 정리"
    else:
        title = f"The Essential Guide to {keyword}"

    payload = {
        "title": title,
        "content": article_body,
        "categories": category_ids,
        "status": "publish",
    }
    if tag_ids:
        payload["tags"] = tag_ids
    if media_ids:
        payload["featured_media"] = media_ids[0]

    try:
        res_post = requests.post(f"{site['url']}/wp-json/wp/v2/posts", json=payload, auth=(WP_USER, wp_pass), timeout=20)
    except Exception as e:
        print(f"  ❌ 포스팅 요청 실패 ({site['url']}): {e}")
        return False

    if res_post.status_code == 201:
        print(f"✅ {site['url']} 발행 완료 — 태그 {len(tag_ids)}개 적용: {title}")
        log_to_google_sheet(site['url'], title, tag_count=len(tag_ids), status="success")
        return True
    else:
        print(f"❌ {site['url']} 발행 실패 (status={res_post.status_code}): {res_post.text[:200]}")
        log_to_google_sheet(site['url'], title, tag_count=len(tag_ids), status=f"fail_{res_post.status_code}")
        return False


def run():
    print("🚀 [시트 연동 모드] 릴레이 발행 및 구글 시트 동시 기록을 시작합니다.")

    # 1. 메인 허브 사이트 (k-health365.com)
    site = SITES_CONFIG[0]
    keyword = load_keyword(site['keywords_file'], "체지방 감소 식품")
    publish_post(site, keyword, site['theme'], site['lang'], "blog", [random.choice(HEALTH_CATEGORIES)])

    # 2. 한국 뉴스 신문사 사이트
    site = SITES_CONFIG[1]
    ref_title, ref_desc = crawl_rss_news()
    publish_post(site, ref_title, site['theme'], 'ko', "news", [1])

    # 3. 글로벌 네트워크 사이트 중 무작위 1개
    global_site_idx = random.randint(2, len(SITES_CONFIG) - 1)
    site = SITES_CONFIG[global_site_idx]
    keyword = load_keyword(site['keywords_file'], site['theme'])
    publish_post(site, keyword, site['theme'], site['lang'], "blog", [1])


if __name__ == "__main__":
    run()
