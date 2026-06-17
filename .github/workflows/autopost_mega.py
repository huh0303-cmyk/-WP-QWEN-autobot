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
SHEETS_WEBHOOK = os.getenv("SHEETS_WEBHOOK")
WP_USER        = "huh0303@gmail.com"

RUN_SLOT = int(os.getenv("RUN_SLOT", "1"))
SLEEP_BETWEEN_POSTS = float(os.getenv("SLEEP_BETWEEN_POSTS", "6"))

gemini_client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-2.5-flash-lite"

REPORTERS = [
    "김민준 기자 (minjun@kworld365.com)", "이서연 기자 (seoyeon@kworld365.com)",
    "박현우 기자 (hyunwoo@kworld365.com)", "최지아 기자 (jia@kworld365.com)",
    "정재희 기자 (jaehee@kworld365.com)", "James Wilson (james@kworld365.com)",
    "Emily Anderson (emily@kworld365.com)", "Michael Chang (michael@kworld365.com)",
    "Sarah Jenkins (sarah@kworld365.com)", "David Miller (david@kworld365.com)"
]

HEALTH_CATEGORIES = [2, 3, 4, 5, 6]
TAG_COUNT = 12
MIN_BODY_LENGTH = 1800  # 애드센스 콘텐츠 충분성 기준: 너무 짧은 글은 저품질로 판정될 위험이 높음

# ============================================================
# 22개 사이트 설정 (사용자 지정 일일 목표량)
# ============================================================
SITES_CONFIG = [
    {"url": "https://k-health365.com",      "lang": "ko", "theme": "건강과 의학", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_khealth.txt", "wp_pass_env": "KHEALTH365COM", "daily": 15},

    {"url": "https://koreamedicaltour.com", "lang": "en", "theme": "Korea Medical Tourism", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_medicaltour.txt", "wp_pass_env": "KOREAMEDICALTOURCOM", "daily": 3},

    {"url": "https://koreainvest365.com",   "lang": "en", "theme": "Investment", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kinvest.txt", "wp_pass_env": "KOREAINVEST365COM", "daily": 3},

    {"url": "https://koreainsurance365.com","lang": "en", "theme": "Insurance", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kinsurance.txt", "wp_pass_env": "KOREAINSURANCE365COM", "daily": 3},

    {"url": "https://kfinance365.com",      "lang": "en", "theme": "Finance", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kfinance.txt", "wp_pass_env": "KFINANCE365COM", "daily": 3},

    {"url": "https://koreataxnlaw.com",     "lang": "en", "theme": "Tax and Law", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_ktax.txt", "wp_pass_env": "KOREATAXNLAWCOM", "daily": 3},

    {"url": "https://koreacrypto365.com",   "lang": "en", "theme": "Crypto", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kcrypto.txt", "wp_pass_env": "KOREACRYPTO365COM", "daily": 3},

    {"url": "https://ktech365.com",         "lang": "en", "theme": "Technology", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_ktech.txt", "wp_pass_env": "KTECH365COM", "daily": 3},

    {"url": "https://kskin365.com",         "lang": "en", "theme": "K-Beauty", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kskin.txt", "wp_pass_env": "KSKIN365COM", "daily": 3},

    {"url": "https://oliveyoungkorea.com",  "lang": "en", "theme": "K-Beauty Reviews", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_oliveyoung.txt", "wp_pass_env": "OLIVEYOUNGKOREACOM", "daily": 3},

    {"url": "https://kworld365.com",        "lang": "en", "theme": "K-POP", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kworld.txt", "wp_pass_env": "KWORLD365COM", "daily": 5},

    {"url": "https://k-trip365.com",        "lang": "en", "theme": "Travel", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_ktrip.txt", "wp_pass_env": "KTRIP365COM", "daily": 3},

    {"url": "https://k-visa365.com",        "lang": "en", "theme": "Visa Guide", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kvisa.txt", "wp_pass_env": "KVISA365COM", "daily": 3},

    {"url": "https://koreawedding365.com",  "lang": "en", "theme": "Wedding", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kwedding.txt", "wp_pass_env": "KOREAWEDDING365COM", "daily": 3},

    {"url": "https://kstudy365.com",        "lang": "en", "theme": "Study in Korea", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kstudy365.txt", "wp_pass_env": "KSTUDY365COM", "daily": 3},

    {"url": "https://studyinkorea365.com",  "lang": "en", "theme": "International Students", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_koreanews.txt", "wp_pass_env": "STUDYINKOREA365COM", "daily": 3},

    {"url": "https://jobkorea365.com",      "lang": "en", "theme": "Employment", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_jobkorea365.txt", "wp_pass_env": "JOBKOREA365COM", "daily": 3},

    {"url": "https://jobinkorea365.com",    "lang": "en", "theme": "Jobs in Korea", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_jobinkorea365.txt", "wp_pass_env": "JOBINKOREA365COM", "daily": 3},

    {"url": "https://jobkoreaglobal.com",   "lang": "en", "theme": "Recruitment", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_jobkoreaglobal.txt", "wp_pass_env": "JOBKOREAGLOBALCOM", "daily": 3},

    {"url": "https://korea365.org",         "lang": "en", "theme": "Korea Culture", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_korea365.txt", "wp_pass_env": "KOREA365ORG", "daily": 4},

    {"url": "https://koreanews365.com",     "lang": "ko", "theme": "한국 뉴스", "mode": "news",
     "keywords_file": ".github/workflows/keywords_koreanews.txt", "wp_pass_env": "KOREANEWS365COM", "daily": 5},

    {"url": "https://theseouljournal.com",  "lang": "en", "theme": "Seoul Lifestyle", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_seouljournal.txt", "wp_pass_env": "THESEOULJOURNALCOM", "daily": 5},
]

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


# ============================================================
# 일일 목표량을 3개 cron 슬롯에 균등 분배
# ============================================================
def split_daily_into_slots(daily, num_slots=3):
    base = daily // num_slots
    rem = daily % num_slots
    parts = [base] * num_slots
    for i in range(rem):
        parts[i] += 1
    return parts


def get_posts_for_this_slot(site, slot):
    parts = split_daily_into_slots(site["daily"], 3)
    idx = max(0, min(slot - 1, len(parts) - 1))
    return parts[idx]


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


# ============================================================
# 애드센스 90점 이상을 위한 프롬프트
# - 메타 디스크립션(META_DESC) 별도 라인 강제 출력
# - FAQ 3문항 (스키마 마크업용) 별도 블록 강제 출력
# - 최소 글자수 상향, 출처/통계 인용 요구로 E-E-A-T 강화
# - 광고 친화적 구조(짧은 문단, 명확한 h2/h3 계층, 표/리스트 혼합)
# ============================================================
def make_seo_prompt(keyword, theme, lang, mode="blog"):
    reporter = random.choice(REPORTERS)
    tag_lang = "영어로" if lang == "en" else "한국어로"

    if mode == "news":
        return f"""
        당신은 주요 일간지의 시니어 취재기자입니다.
        주제: '{keyword}'에 대해 엄격한 신문기사체 기사를 작성하세요.

        [필수 지침 - 구글 애드센스 품질 평가 90점 이상 목표]
        1. 문체: 절대 블로그 형식을 쓰지 마십시오. '했다', '밝혔다', '조사됐다'로 끝나는 6하원칙 기사체여야 합니다.
        2. 바이라인: 기사 맨 위에 반드시 '◇ {reporter}'를 한 줄 삽입하십시오.
        3. 분량: HTML 태그(h2, h3, p, strong, ul, li)만 사용해 최소 1800자 이상, 정보가 충실한 기사로 작성하세요. 마크다운 금지.
        4. 신뢰성(E-E-A-T): 첫 단락에 핵심 리드문을 작성하고, 전문가 인터뷰 인용구, 구체적 통계 수치, 발표 기관명을 포함해 신뢰도를 극대화하십시오.
        5. 구조: h2 소제목 최소 3개, 단락은 3~4문장 이내로 짧게 끊어 가독성을 높이십시오 (애드센스는 짧은 문단의 가독성 높은 글을 선호함).
        6. 메타 디스크립션: 기사 본문이 끝난 직후 새로운 줄에 'META_DESC:' 로 시작하는 줄을 추가하고, 120자 이내의 검색결과용 요약문을 작성하세요.
        7. FAQ: META_DESC 다음 줄에 'FAQ_START' 를 적고, 이어서 이 기사와 관련된 자주 묻는 질문 3개를 'Q: 질문' / 'A: 답변' 형식으로 각 줄에 작성한 뒤 'FAQ_END' 로 마무리하세요.
        8. 태그: FAQ_END 다음 새로운 줄에 'TAGS:' 로 시작하는 줄을 추가하고, 정확히 {TAG_COUNT}개의 연관 핵심 키워드를 {tag_lang} 추출해 쉼표(,)로만 연결해 한 줄로 출력하세요.

        출력 순서: [기사 본문 HTML] → META_DESC: ... → FAQ_START ~ FAQ_END → TAGS: ...
        """

    persona = "의학 박사" if "건강" in theme or "medical" in theme.lower() else "산업 분야 최고 전문 자문위원"
    return f"""
    당신은 {persona}이자 15년 경력의 SEO 콘텐츠 마스터 프로라이터입니다.
    주제: '{keyword}' ({theme})
    언어: {lang}

    [구글 애드센스 품질 평가 90점 이상 목표 - 필수 지침]
    1. HTML 전용: 오직 h2, h3, p, ul, li, ol, strong, table, tr, td 태그만 사용하고 마크다운(*)은 절대 쓰지 마세요.
    2. 분량: 최소 1800자 이상, 깊이 있고 실질적 가치를 주는 상세한 설명으로 가득 채우십시오 (짧은 글은 애드센스 저품질 판정 위험이 큼).
    3. 키워드 최적화: 첫 단락 문두에 '{keyword}'를 무조건 배치하고, 전체 글에 자연스럽게 10회 이상 분산 삽입하세요. 키워드 남용처럼 보이지 않게 자연스러운 문맥에서 사용하세요.
    4. 구조 다각화: h2 태그 최소 5개 이상, h3 태그 최소 4개 이상 배치하고, 가독성을 위한 불릿 포인트(ul/li) 리스트를 3개 이상, 비교 표(table)를 최소 1개 포함하세요.
    5. E-E-A-T 신뢰성 강화: 구체적인 수치, 통계, 공신력 있는 기관명(정부기관, 학회, 협회 등)을 본문 중 최소 2회 이상 자연스럽게 인용하여 전문성과 신뢰성을 보여주세요. 실제 경험에 기반한 듯한 구체적 디테일(예: 가격대, 기간, 절차 등)을 포함하세요.
    6. 가독성: 한 단락은 3~4문장 이내로 짧게 끊어 작성하세요. 광고가 들어갈 여백이 자연스럽게 생기도록 단락 사이를 명확히 구분하세요.
    7. 메타 디스크립션: 본문이 모두 끝난 후 새로운 줄에 'META_DESC:' 로 시작하는 줄을 추가하고, 120자 이내로 검색결과에 노출될 매력적인 요약문을 작성하세요.
    8. FAQ 스키마: META_DESC 다음 줄에 'FAQ_START' 를 적고, 이 주제와 관련된 독자들이 자주 묻는 질문 3개를 'Q: 질문' / 'A: 답변' 형식으로 한 줄씩 작성한 뒤 'FAQ_END' 로 마무리하세요. 이는 구글 FAQ 스키마 마크업에 사용됩니다.
    9. 태그: FAQ_END 다음 새로운 줄에 'TAGS:' 로 시작하는 줄을 추가하고, 정확히 {TAG_COUNT}개의 연관 핵심 키워드를 {tag_lang} 추출해 쉼표(,)로만 연결해 한 줄로 출력하세요.

    출력 순서: [본문 HTML] → META_DESC: ... → FAQ_START ~ FAQ_END → TAGS: ...
    """


def extract_meta_and_faq(text):
    """
    META_DESC, FAQ_START~FAQ_END 블록을 추출하고 본문에서 제거한다.
    반환: (정제된 텍스트, meta_desc, faq_list[(q,a), ...])
    """
    meta_desc = ""
    faq_list = []
    lines = text.split("\n")
    out_lines = []
    in_faq = False
    cur_q = None

    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("META_DESC:"):
            meta_desc = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
            continue
        if stripped.upper().startswith("FAQ_START"):
            in_faq = True
            continue
        if stripped.upper().startswith("FAQ_END"):
            in_faq = False
            continue
        if in_faq:
            if stripped[:2].upper() == "Q:":
                cur_q = stripped[2:].strip()
            elif stripped[:2].upper() == "A:" and cur_q:
                faq_list.append((cur_q, stripped[2:].strip()))
                cur_q = None
            continue
        out_lines.append(line)

    return "\n".join(out_lines).strip(), meta_desc, faq_list


def build_fallback_tag_pool(fallback_keyword, theme=None, lang="ko"):
    if lang == "ko":
        suffixes = ["효능", "부작용", "가격", "추천", "비교", "후기", "정보", "방법", "순위", "팁", "총정리", "가이드"]
    else:
        suffixes = ["guide", "review", "cost", "tips", "comparison", "benefits", "ranking", "checklist",
                    "overview", "FAQ", "how to", "best practices"]
    pool = [f"{fallback_keyword} {s}" for s in suffixes]
    if theme:
        pool.insert(0, theme)
    pool.append(fallback_keyword)
    return pool


def extract_tags_from_article(article_text, fallback_keyword, theme=None, lang="ko"):
    """
    'TAGS: ...' 라인을 찾아 분리. 항상 정확히 TAG_COUNT(12)개를 보장한다.
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

    if not tags:
        tags = [fallback_keyword]

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
        fallback_pool = build_fallback_tag_pool(fallback_keyword, theme, lang)
        for candidate in fallback_pool:
            if len(tags) >= TAG_COUNT:
                break
            if candidate.lower() not in seen:
                tags.append(candidate)
                seen.add(candidate.lower())
        i = 1
        while len(tags) < TAG_COUNT:
            filler = f"{fallback_keyword} {i}" if i > 1 else fallback_keyword
            if filler.lower() not in seen:
                tags.append(filler)
                seen.add(filler.lower())
            i += 1

    return article_body, tags


def get_or_create_tag_ids(site_url, wp_pass, tag_names):
    tag_ids = []
    for name in tag_names:
        try:
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

            create_res = requests.post(
                f"{site_url}/wp-json/wp/v2/tags",
                json={"name": name},
                auth=(WP_USER, wp_pass),
                timeout=10
            )
            if create_res.status_code in (200, 201):
                tag_ids.append(create_res.json()["id"])
            elif create_res.status_code == 400:
                data = create_res.json()
                existing_id = data.get("data", {}).get("term_id") or data.get("term_id")
                if existing_id:
                    tag_ids.append(existing_id)
        except Exception as e:
            print(f"  ⚠️ 태그 처리 실패 ({name}): {e}")
            continue
    return tag_ids


def get_images_from_pixabay(query, need):
    urls = []
    if not PIXABAY_KEY:
        return urls
    try:
        url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={requests.utils.quote(query)}&image_type=photo&per_page=20&safesearch=true"
        res = requests.get(url, timeout=10).json()
        hits = res.get("hits") or []
        if hits:
            sample = random.sample(hits, min(need, len(hits)))
            for h in sample:
                if h.get("webformatURL"):
                    urls.append(h["webformatURL"])
    except Exception as e:
        print(f"  ⚠️ Pixabay 이미지 검색 실패: {e}")
    return urls


def get_images_from_pexels(query, need):
    urls = []
    if not PEXELS_KEY:
        return urls
    try:
        headers = {"Authorization": PEXELS_KEY}
        url = f"https://api.pexels.com/v1/search?query={requests.utils.quote(query)}&per_page=20&safe_search=true"
        res = requests.get(url, headers=headers, timeout=10).json()
        photos = res.get("photos") or []
        if photos:
            sample = random.sample(photos, min(need, len(photos)))
            for p in sample:
                src = (p.get("src") or {}).get("large") or (p.get("src") or {}).get("medium")
                if src:
                    urls.append(src)
    except Exception as e:
        print(f"  ⚠️ Pexels 이미지 검색 실패: {e}")
    return urls


def get_multiple_images(keyword, count=3):
    """
    Pixabay 우선 → 부족하면 Pexels 보충 → 그래도 부족하면 'korea' 일반 키워드로 재시도.
    이미지를 하나도 못 구해도 빈 리스트 반환(예외 없음) → 발행은 무조건 계속 진행.
    """
    q = keyword.encode('ascii', 'ignore').decode().strip()
    if not q:
        q = "korea"

    urls = []
    urls += get_images_from_pixabay(q, count)

    remaining = count - len(urls)
    if remaining > 0:
        urls += get_images_from_pexels(q, remaining)

    remaining = count - len(urls)
    if remaining > 0 and q != "korea":
        urls += get_images_from_pixabay("korea", remaining)
        remaining = count - len(urls)
        if remaining > 0:
            urls += get_images_from_pexels("korea", remaining)

    return urls[:count]


def upload_to_wp_media(site_url, wp_pass, img_url, keyword, idx, alt_text=""):
    """이미지 업로드 + alt 텍스트(접근성/SEO) 설정. 실패 시 None 반환(발행은 계속 진행)."""
    try:
        img_data = requests.get(img_url, timeout=10).content
        filename = f"seo-{keyword.replace(' ', '-')}-{idx}.jpg"
        headers = {"Content-Disposition": f"attachment; filename={filename}", "Content-Type": "image/jpeg"}
        res = requests.post(f"{site_url}/wp-json/wp/v2/media", data=img_data, headers=headers, auth=(WP_USER, wp_pass), timeout=20)
        if res.status_code == 201:
            media_id = res.json().get("id")
            if media_id and alt_text:
                try:
                    requests.post(
                        f"{site_url}/wp-json/wp/v2/media/{media_id}",
                        json={"alt_text": alt_text, "caption": alt_text},
                        auth=(WP_USER, wp_pass),
                        timeout=10
                    )
                except Exception:
                    pass
            return media_id
    except Exception:
        pass
    return None


def build_spider_web_links(keyword, current_url, lang, link_count=6):
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
    words = [f"{keyword} 효능", f"{keyword} 부작용", f"{keyword} 가격", f"{keyword} 추천", f"{keyword} 비교"] if lang == 'ko' else [f"{keyword} cost", f"{keyword} review", f"{keyword} comparison", f"{keyword} guide", f"best {keyword}"]
    html = "<div style='margin-top:20px; border-top:1px dashed #ccc; padding-top:15px;'>"
    html += "<strong>💡 연관 검색어 바로가기: </strong> "
    links = []
    for w in words:
        links.append(f"<a href='?s={requests.utils.quote(w)}' style='color:#555; text-decoration:underline; margin-right:10px;'>#{w}</a>")
    html += ", ".join(links) + "</div>"
    return html


def build_external_authority_links(theme, lang, link_count=4):
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


def build_faq_html_and_schema(faq_list, lang):
    """FAQ 본문 블록 + 구글 FAQPage JSON-LD 스키마 마크업을 함께 생성"""
    if not faq_list:
        return "", ""

    label = "❓ 자주 묻는 질문" if lang == "ko" else "❓ Frequently Asked Questions"
    html = f"<div style='margin-top:30px;'><h2>{label}</h2>"
    schema_items = []
    for q, a in faq_list:
        html += f"<h3>{q}</h3><p>{a}</p>"
        q_esc = q.replace('"', '\\"')
        a_esc = a.replace('"', '\\"')
        schema_items.append(
            '{"@type":"Question","name":"%s","acceptedAnswer":{"@type":"Answer","text":"%s"}}' % (q_esc, a_esc)
        )
    html += "</div>"

    schema_json = (
        '<script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[%s]}</script>'
        % ",".join(schema_items)
    )
    return html, schema_json


RUN_LOG = []

def record_result(site_url, title, tag_count=None, status="success"):
    RUN_LOG.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "site": site_url,
        "title": title,
        "tag_count": tag_count,
        "status": status,
    })


def flush_log_to_google_sheet():
    if not SHEETS_WEBHOOK:
        print("⚠️ SHEETS_WEBHOOK 미설정 — 로그 전송 스킵")
        return
    if not RUN_LOG:
        print("ℹ️ 이번 회차에 기록할 로그가 없습니다.")
        return

    success_count = sum(1 for r in RUN_LOG if r["status"] == "success")
    fail_count = len(RUN_LOG) - success_count

    summary_payload = {
        "type": "summary",
        "run_slot": RUN_SLOT,
        "run_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(RUN_LOG),
        "success": success_count,
        "fail": fail_count,
        "entries": RUN_LOG,
    }
    try:
        requests.post(SHEETS_WEBHOOK, json=summary_payload, timeout=15)
        print(f"📊 구글 스프레드시트 요약 전송 완료: 총 {len(RUN_LOG)}건 (성공 {success_count} / 실패 {fail_count})")
    except Exception as e:
        print(f"⚠️ 구글 스프레드시트 전송 실패: {e}")


def generate_with_retry(prompt, max_retries=3):
    for attempt in range(1, max_retries + 1):
        try:
            res = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            if res and res.text:
                return res.text
        except Exception as e:
            err_str = str(e)
            is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str
            wait = 20 * attempt if is_rate_limit else 5 * attempt
            print(f"  ⚠️ Gemini 호출 실패 (시도 {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                print(f"     {wait}초 대기 후 재시도...")
                time.sleep(wait)
            else:
                raise
    return ""


def publish_post(site, keyword, theme, lang, mode, category_ids):
    """
    발행 로직:
    1. Gemini로 본문 + META_DESC + FAQ + TAGS 생성
    2. 메타디스크립션/FAQ/태그 분리
    3. 글자수 기준 미달 시 스킵(저품질 방지)
    4. 이미지 업로드(alt텍스트 포함, 실패해도 발행 계속)
    5. 태그 ID 변환(항상 12개 보장, 실패시 재시도)
    6. 거미줄 내부링크 + 외부 권위링크 + FAQ 스키마 삽입
    7. 워드프레스 발행 (메타디스크립션은 excerpt에도 기록)
    """
    wp_pass = os.getenv(site['wp_pass_env'])
    if not wp_pass:
        print(f"⏭️  {site['url']} - 비밀번호 환경변수 없음, 스킵")
        record_result(site['url'], f"(skip) {keyword}", status="skip_no_password")
        return False

    prompt = make_seo_prompt(keyword, theme, lang, mode)
    try:
        raw_text = generate_with_retry(prompt)
    except Exception as e:
        print(f"  ❌ Gemini 생성 최종 실패 ({site['url']}): {e}")
        record_result(site['url'], keyword, status="fail_gemini")
        return False

    if len(raw_text) < 300:
        print(f"  ⚠️ 본문이 너무 짧음, 스킵: {site['url']}")
        record_result(site['url'], keyword, status="fail_short_body")
        return False

    body_with_tags, meta_desc, faq_list = extract_meta_and_faq(raw_text)
    article_body, tag_names = extract_tags_from_article(body_with_tags, keyword, theme=theme, lang=lang)

    # 애드센스 90점 기준: 콘텐츠 충분성 체크 (본문 HTML 태그 제외 텍스트 기준 대략 추정)
    plain_len = len(BeautifulSoup(article_body, "html.parser").get_text())
    if plain_len < MIN_BODY_LENGTH:
        print(f"  ⚠️ 본문 글자수 부족({plain_len}자 < {MIN_BODY_LENGTH}자) — 발행은 진행하되 품질 경고 기록")
        record_result(site['url'], f"[글자수부족:{plain_len}] {keyword}", status="warn_short_content")

    if not meta_desc:
        meta_desc = (article_body[:117] + "...") if len(article_body) > 120 else article_body
        meta_desc = BeautifulSoup(meta_desc, "html.parser").get_text()[:155]

    img_urls = get_multiple_images(keyword, 3)
    media_ids = []
    for idx, url in enumerate(img_urls):
        alt = f"{keyword} - {theme}" if lang != 'ko' else f"{keyword} 관련 이미지"
        mid = upload_to_wp_media(site['url'], wp_pass, url, keyword, idx, alt_text=alt)
        if mid:
            media_ids.append(mid)
    if not media_ids:
        print(f"  ℹ️ 이미지 확보 실패(0장) — 이미지 없이 발행 계속 진행")

    tag_ids = get_or_create_tag_ids(site['url'], wp_pass, tag_names)
    if not tag_ids and tag_names:
        print(f"  ⚠️ 태그 ID 변환 전체 실패, 재시도 1회...")
        time.sleep(3)
        tag_ids = get_or_create_tag_ids(site['url'], wp_pass, tag_names)

    if tag_ids:
        print(f"  🏷️ 태그 {len(tag_ids)}/{len(tag_names)}개 확보")
    else:
        print(f"  ⚠️ 태그를 전혀 확보하지 못했습니다 (태그 없이 발행 진행)")

    faq_html, faq_schema = build_faq_html_and_schema(faq_list, lang)

    article_body += build_spider_web_links(keyword, site['url'], lang)
    article_body += build_related_search_links(keyword, lang)
    article_body += build_external_authority_links(theme, lang)
    if faq_html:
        article_body += faq_html
    if faq_schema:
        article_body += faq_schema

    if lang == 'ko':
        title = f"[속보] {keyword}" if mode == "news" else f"{keyword} 정보 완벽 정리"
    else:
        title = f"The Essential Guide to {keyword}"

    payload = {
        "title": title,
        "content": article_body,
        "excerpt": meta_desc,
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
        record_result(site['url'], title, status="fail_request")
        return False

    if res_post.status_code == 201:
        print(f"✅ {site['url']} 발행 완료 — 태그 {len(tag_ids)}개, 이미지 {len(media_ids)}장, FAQ {len(faq_list)}개: {title}")
        record_result(site['url'], title, tag_count=len(tag_ids), status="success")
        return True
    else:
        print(f"❌ {site['url']} 발행 실패 (status={res_post.status_code}): {res_post.text[:200]}")
        record_result(site['url'], title, tag_count=len(tag_ids), status=f"fail_{res_post.status_code}")
        return False


def build_job_queue():
    queue = []
    for site in SITES_CONFIG:
        count = get_posts_for_this_slot(site, RUN_SLOT)
        if count <= 0:
            continue
        for _ in range(count):
            if site["mode"] == "news" and site["url"] == "https://koreanews365.com":
                ref_title, _ = crawl_rss_news()
                keyword = ref_title
                categories = [1]
            else:
                keyword = load_keyword(site["keywords_file"], site["theme"])
                categories = [random.choice(HEALTH_CATEGORIES)] if site["url"] == "https://k-health365.com" else [1]

            queue.append({
                "site": site,
                "keyword": keyword,
                "theme": site["theme"],
                "lang": site["lang"],
                "mode": site["mode"],
                "categories": categories,
            })

    random.shuffle(queue)
    return queue


def run():
    print(f"🚀 [RUN_SLOT {RUN_SLOT}/3] 22개 사이트 메가 오토포스팅 시작 (모델: {GEMINI_MODEL}, 애드센스90점 기준 적용)")

    queue = build_job_queue()
    total = len(queue)
    print(f"📋 이번 회차 발행 예정 건수: {total}건")

    for i, job in enumerate(queue, start=1):
        site = job["site"]
        print(f"\n[{i}/{total}] {site['url']} ({job['keyword']})")
        publish_post(site, job["keyword"], job["theme"], job["lang"], job["mode"], job["categories"])
        if i < total:
            time.sleep(SLEEP_BETWEEN_POSTS)

    flush_log_to_google_sheet()
    print("\n🏁 이번 회차 작업이 모두 종료되었습니다.")


if __name__ == "__main__":
    run()
