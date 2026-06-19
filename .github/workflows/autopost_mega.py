import os
import sys
import time
import random
import requests
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from google import genai

KST = timezone(timedelta(hours=9))

def now_kst():
    return datetime.now(KST)

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
GEMINI_MODEL_PRIMARY  = "gemini-2.5-flash"
GEMINI_MODEL_FALLBACK = "gemini-2.5-flash-lite"
GEMINI_MODEL = GEMINI_MODEL_PRIMARY
_gemini_fallback_active = False

REPORTERS = [
    "김민준 기자 (minjun@kworld365.com)", "이서연 기자 (seoyeon@kworld365.com)",
    "박현우 기자 (hyunwoo@kworld365.com)", "최지아 기자 (jia@kworld365.com)",
    "정재희 기자 (jaehee@kworld365.com)", "James Wilson (james@kworld365.com)",
    "Emily Anderson (emily@kworld365.com)", "Michael Chang (michael@kworld365.com)",
    "Sarah Jenkins (sarah@kworld365.com)", "David Miller (david@kworld365.com)"
]

HEALTH_CATEGORIES = [2, 3, 4, 5, 6]
TAG_COUNT = 12
MIN_BODY_LENGTH = 1800

# ============================================================
# ★ 수정1: 한국어 → 영어 이미지 검색 번역 매핑
# ============================================================
KO_TO_EN_IMAGE = {
    # 건강 증상
    "요로결석": "kidney stone urinary",
    "초기증상": "early symptoms medical",
    "면역력": "immune system health",
    "영양제": "health supplements vitamins",
    "크론병": "Crohn disease gut",
    "비만": "obesity overweight",
    "체질량지수": "BMI body mass index",
    "혈당스파이크": "blood sugar spike glucose",
    "혈압": "blood pressure",
    "당뇨": "diabetes blood sugar",
    "갑상선": "thyroid gland",
    "콜레스테롤": "cholesterol heart",
    "소화불량": "indigestion digestion",
    "변비": "constipation digestive",
    "피부": "skin care",
    "탈모": "hair loss",
    "수면": "sleep health",
    "스트레스": "stress relief mental health",
    "비타민": "vitamins supplements",
    "프로바이오틱스": "probiotics gut health",
    "관절": "joint pain arthritis",
    "허리": "back pain spine",
    "두통": "headache migraine",
    "불면증": "insomnia sleep disorder",
    "다이어트": "diet weight loss",
    "운동": "exercise fitness",
    "영양": "nutrition healthy food",
    "암": "cancer treatment medical",
    "심장": "heart health cardiology",
    "뇌": "brain health neurology",
    # 뉴스/사회
    "대한민국": "South Korea",
    "경제": "Korea economy finance",
    "사회": "Korean society people",
    "트렌드": "trend analysis",
    "분석": "data analysis report",
    "최신": "latest news",
    "정치": "Korea politics government",
    "기술": "Korea technology innovation",
    "금융": "Korea finance banking",
    "부동산": "Korea real estate",
    "취업": "Korea employment jobs",
    "교육": "Korea education school",
    "문화": "Korean culture tradition",
    "한국": "South Korea",
    "서울": "Seoul Korea city",
    "음식": "Korean food cuisine",
    "여행": "Korea travel tourism",
}

def translate_ko_to_en_for_image(keyword: str) -> str:
    """한국어 키워드를 이미지 검색용 영어로 변환"""
    result = keyword
    for ko, en in KO_TO_EN_IMAGE.items():
        result = result.replace(ko, en)
    # 여전히 한글이 남아있으면 일반 Korea medical 키워드 반환
    if any('\uac00' <= c <= '\ud7a3' for c in result):
        # 주제 추측: health 사이트면 medical, news면 Korea news
        return "Korea health medical"
    return result.strip()

# ============================================================
# 22개 사이트 설정
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
     "keywords_file": ".github/workflows/keywords_studyinkorea365.txt", "wp_pass_env": "STUDYINKOREA365COM", "daily": 3},
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
    "Finance": [("Bank of Korea", "https://www.bok.or.kr/eng"), ("Financial Services Commission", "https://www.fsc.go.kr/eng"), ("Korea Exchange", "https://global.krx.co.kr")],
    "Investment": [("Bank of Korea", "https://www.bok.or.kr/eng"), ("Korea Exchange", "https://global.krx.co.kr"), ("Invest Korea", "https://www.investkorea.org")],
    "Tax and Law": [("National Tax Service", "https://www.nts.go.kr/english"), ("Ministry of Justice Korea", "https://www.moj.go.kr/moj/index.do"), ("Korea Legislation Research Institute", "https://elaw.klri.re.kr")],
    "Jobs in Korea": [("Ministry of Employment and Labor", "https://www.moel.go.kr/english"), ("HRD Korea", "https://www.hrdkorea.or.kr/eng"), ("Work24", "https://www.work24.go.kr")],
    "Employment": [("Ministry of Employment and Labor", "https://www.moel.go.kr/english"), ("Work24", "https://www.work24.go.kr")],
    "Recruitment": [("Ministry of Employment and Labor", "https://www.moel.go.kr/english"), ("HRD Korea", "https://www.hrdkorea.or.kr/eng")],
    "Study in Korea": [("Study in Korea (NIIED)", "https://www.studyinkorea.go.kr"), ("Ministry of Education Korea", "https://english.moe.go.kr"), ("NIIED", "https://www.niied.go.kr/eng")],
    "International Students": [("Study in Korea (NIIED)", "https://www.studyinkorea.go.kr"), ("HiKorea (Immigration)", "https://www.hikorea.go.kr")],
    "Visa Guide": [("HiKorea (Immigration)", "https://www.hikorea.go.kr"), ("Ministry of Justice Korea", "https://www.moj.go.kr/moj/index.do")],
    "Korea Medical Tourism": [("Korea Health Industry Development Institute", "https://www.khidi.or.kr/eps"), ("Visit Korea", "https://english.visitkorea.or.kr")],
    "K-Beauty": [("Visit Korea", "https://english.visitkorea.or.kr"), ("Korea.net", "https://www.korea.net")],
    "K-Beauty Reviews": [("Visit Korea", "https://english.visitkorea.or.kr"), ("Korea.net", "https://www.korea.net")],
    "Travel": [("Visit Korea", "https://english.visitkorea.or.kr"), ("Korea Tourism Organization", "https://www.knto.or.kr")],
    "Korea Culture": [("Korea.net", "https://www.korea.net"), ("Korean Culture and Information Service", "https://www.kocis.go.kr")],
    "Crypto": [("Financial Services Commission", "https://www.fsc.go.kr/eng"), ("Bank of Korea", "https://www.bok.or.kr/eng")],
    "Insurance": [("Financial Services Commission", "https://www.fsc.go.kr/eng"), ("National Health Insurance Service", "https://www.nhis.or.kr/english")],
    "Wedding": [("Visit Korea", "https://english.visitkorea.or.kr"), ("Korea.net", "https://www.korea.net")],
    "Technology": [("Ministry of Science and ICT", "https://www.msit.go.kr/eng"), ("NIPA", "https://www.nipa.kr/home/eng")],
    "K-POP": [("Korea.net", "https://www.korea.net"), ("Korean Culture and Information Service", "https://www.kocis.go.kr")],
    "Seoul Lifestyle": [("Seoul Metropolitan Government", "https://english.seoul.go.kr"), ("Visit Korea", "https://english.visitkorea.or.kr")],
}

# ============================================================
# 슬롯 분배
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
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(res.text, 'xml')
        items = soup.find_all('item')
        if items:
            chosen = random.choice(items)
            return chosen.title.text, chosen.description.text
    except Exception:
        pass
    return "대한민국 최신 경제 및 사회 변화 트렌드 분석", "최신 주요 시사 이슈 및 정책 변화에 대한 심층 기사입니다."

# ============================================================
# 프롬프트
# ============================================================
TITLE_STYLES_KO = [
    "숫자 리스트형: 구체적인 숫자를 넣어 호기심을 자극 (예: '○○하는 5가지 방법', '몰랐던 7가지 사실')",
    "경고/주의형: 손해나 실수를 암시해 클릭을 유도 (예: '○○ 모르고 하면 손해보는 이유', '이것 모르면 100% 후회')",
    "질문형: 독자가 스스로에게 묻게 만드는 질문 (예: '○○ 진짜 효과 있을까?', '당신도 ○○ 하고 있나요?')",
    "비교/반전형: 통념을 깨거나 비교하는 구조 (예: '○○ vs △△, 정답은 따로 있다', '다들 잘못 알고 있는 ○○')",
    "긴급/시급형: 시기나 타이밍을 강조 (예: '지금 안 하면 늦는 ○○', '2026년 꼭 알아야 할 ○○')",
]
TITLE_STYLES_EN = [
    "Number/List style: spark curiosity with a specific count (e.g. '7 Things Nobody Tells You About X', '5 Mistakes to Avoid With X')",
    "Warning style: hint at a loss or mistake to drive clicks (e.g. 'Why You're Losing Money on X', 'The X Mistake Everyone Makes')",
    "Question style: a question readers ask themselves (e.g. 'Is X Really Worth It?', 'Are You Making This X Mistake?')",
    "Comparison/contrarian style: challenge assumptions (e.g. 'X vs Y: Here's the Real Answer', 'What Nobody Tells You About X')",
    "Urgency style: emphasize timing (e.g. 'Why X Matters More Than Ever in 2026', 'Don't Wait to Learn This About X')",
]

def pick_title_style(lang):
    return random.choice(TITLE_STYLES_KO if lang == "ko" else TITLE_STYLES_EN)

def make_seo_prompt(keyword, theme, lang, mode="blog"):
    reporter = random.choice(REPORTERS)
    tag_lang = "영어로" if lang == "en" else "한국어로"
    title_style = pick_title_style(lang)

    if mode == "news":
        return f"""
당신은 주요 일간지의 시니어 취재기자입니다.
주제: '{keyword}'에 대해 엄격한 신문기사체 기사를 작성하세요.

[필수 지침 - 구글 애드센스 품질 평가 90점 이상 목표]
1. 문체: 절대 블로그 형식을 쓰지 마십시오. '했다', '밝혔다', '조사됐다'로 끝나는 6하원칙 기사체여야 합니다.
2. 바이라인: 기사 맨 위에 반드시 '◇ {reporter}'를 한 줄 삽입하십시오.
3. 분량: HTML 태그(h2, h3, p, strong, ul, li)만 사용해 최소 1800자 이상, 정보가 충실한 기사로 작성하세요. 마크다운 금지.
4. 신뢰성(E-E-A-T): 첫 단락에 핵심 리드문을 작성하고, 전문가 인터뷰 인용구, 구체적 통계 수치, 발표 기관명을 포함해 신뢰도를 극대화하십시오.
5. 구조: h2 소제목 최소 3개, 단락은 3~4문장 이내로 짧게 끊어 가독성을 높이십시오.
6. 제목 스타일: {title_style}
   출력 맨 첫 줄에 'TITLE:' 로 시작하는 줄을 추가하고 그 뒤에 지어낸 제목 하나만 적으세요.
7. 메타 디스크립션: 기사 본문이 끝난 직후 새로운 줄에 'META_DESC:' 로 시작하는 줄을 추가하고, 120자 이내의 검색결과용 요약문을 작성하세요.
8. FAQ: META_DESC 다음 줄에 'FAQ_START' 를 적고, 이어서 이 기사와 관련된 자주 묻는 질문 3개를 'Q: 질문' / 'A: 답변' 형식으로 각 줄에 작성한 뒤 'FAQ_END' 로 마무리하세요.
9. 태그: FAQ_END 다음 새로운 줄에 'TAGS:' 로 시작하는 줄을 추가하고, 정확히 {TAG_COUNT}개의 연관 핵심 키워드를 {tag_lang} 추출해 쉼표(,)로만 연결해 한 줄로 출력하세요. 이때 메인 키워드인 '{keyword}' 자체를 태그 목록의 첫 번째 항목으로 반드시 포함하세요.

출력 순서: TITLE: ... → [기사 본문 HTML] → META_DESC: ... → FAQ_START ~ FAQ_END → TAGS: ...
"""

    persona = "의학 박사" if "건강" in theme or "medical" in theme.lower() else "산업 분야 최고 전문 자문위원"
    return f"""
당신은 {persona}이자 15년 경력의 SEO 콘텐츠 마스터 프로라이터입니다.
주제: '{keyword}' ({theme})
언어: {lang}

[구글 애드센스 품질 평가 90점 이상 목표 - 필수 지침]
1. HTML 전용: 오직 h2, h3, p, ul, li, ol, strong, table, tr, td 태그만 사용하고 마크다운(*)은 절대 쓰지 마세요.
2. 분량: 최소 1800자 이상, 깊이 있고 실질적 가치를 주는 상세한 설명으로 가득 채우십시오.
3. 키워드 최적화: 첫 단락 문두에 '{keyword}'를 무조건 배치하고, 전체 글에 자연스럽게 10회 이상 분산 삽입하세요.
4. 구조 다각화: h2 태그 최소 5개 이상, h3 태그 최소 4개 이상 배치하고, ul/li 리스트 3개 이상, 비교 표(table) 최소 1개 포함하세요.
5. E-E-A-T 신뢰성 강화: 구체적인 수치, 통계, 공신력 있는 기관명을 본문 중 최소 2회 이상 자연스럽게 인용하세요.
6. 가독성: 한 단락은 3~4문장 이내로 짧게 끊어 작성하세요.
7. 제목 스타일: {title_style}
   출력 맨 첫 줄에 'TITLE:' 로 시작하는 줄을 추가하고 그 뒤에 지어낸 제목 하나만 적으세요.
8. 메타 디스크립션: 본문이 모두 끝난 후 새로운 줄에 'META_DESC:' 로 시작하는 줄을 추가하고, 120자 이내로 검색결과에 노출될 매력적인 요약문을 작성하세요.
9. FAQ 스키마: META_DESC 다음 줄에 'FAQ_START' 를 적고, 이 주제와 관련된 독자들이 자주 묻는 질문 3개를 'Q: 질문' / 'A: 답변' 형식으로 한 줄씩 작성한 뒤 'FAQ_END' 로 마무리하세요.
10. 태그: FAQ_END 다음 새로운 줄에 'TAGS:' 로 시작하는 줄을 추가하고, 정확히 {TAG_COUNT}개의 연관 핵심 키워드를 {tag_lang} 추출해 쉼표(,)로만 연결해 한 줄로 출력하세요. 이때 메인 키워드인 '{keyword}' 자체를 태그 목록의 첫 번째 항목으로 반드시 포함하세요.

출력 순서: TITLE: ... → [본문 HTML] → META_DESC: ... → FAQ_START ~ FAQ_END → TAGS: ...
"""

# ============================================================
# 파싱 함수
# ============================================================
def extract_meta_and_faq(text):
    title = ""
    meta_desc = ""
    faq_list = []
    lines = text.split("\n")
    out_lines = []
    in_faq = False
    cur_q = None

    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("TITLE:"):
            title = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
            continue
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

    title = title.strip('"').strip("'").strip("*").strip()
    return "\n".join(out_lines).strip(), title, meta_desc, faq_list

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

    keyword_key = fallback_keyword.strip().lower()
    tags = [t for t in tags if t.strip().lower() != keyword_key]
    tags.insert(0, fallback_keyword)

    seen = set()
    deduped = []
    for t in tags:
        key = t.strip().lower()
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
            if candidate.strip().lower() not in seen:
                tags.append(candidate)
                seen.add(candidate.strip().lower())
        i = 1
        while len(tags) < TAG_COUNT:
            filler = f"{fallback_keyword} {i}" if i > 1 else fallback_keyword
            if filler.strip().lower() not in seen:
                tags.append(filler)
                seen.add(filler.strip().lower())
            i += 1

    return article_body, tags

# ============================================================
# ★ 수정1 적용: 이미지 검색 (한국어 fallback 포함)
# ============================================================
def is_site_reachable(site_url, timeout=8):
    try:
        requests.head(f"{site_url}/wp-json/", timeout=timeout)
        return True
    except Exception:
        return False

def get_images_from_pixabay(query, need):
    urls = []
    if not PIXABAY_KEY:
        return urls
    try:
        url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={requests.utils.quote(query)}&image_type=photo&per_page=20&safesearch=true"
        res_raw = requests.get(url, timeout=10)
        try:
            res = res_raw.json()
        except Exception:
            return urls
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
    ★ 수정1: 한국어 키워드 → 영어 번역 후 재시도 로직 추가
    Pixabay 우선 → 부족하면 Pexels 보충
    한국어 키워드면 영어 번역본으로 재시도
    그래도 부족하면 'korea' 일반 키워드로 재시도
    """
    # 1차: 원본 키워드로 시도 (ASCII 변환)
    q = keyword.encode('ascii', 'ignore').decode().strip()

    urls = []

    # 한국어가 포함된 경우 바로 영어 번역으로 시작
    has_korean = any('\uac00' <= c <= '\ud7a3' for c in keyword)
    if has_korean or not q:
        en_query = translate_ko_to_en_for_image(keyword)
        print(f"  🔄 한국어 키워드 이미지 검색 → 영어 변환: '{keyword}' → '{en_query}'")
        urls += get_images_from_pixabay(en_query, count)
        if len(urls) < count:
            urls += get_images_from_pexels(en_query, count - len(urls))
    else:
        # 영어 키워드: 원본으로 시도
        urls += get_images_from_pixabay(q, count)
        if len(urls) < count:
            urls += get_images_from_pexels(q, count - len(urls))

    # 2차 fallback: 여전히 부족하면 'korea' 일반 키워드
    if len(urls) < count:
        fallback_q = "Korea lifestyle people"
        urls += get_images_from_pixabay(fallback_q, count - len(urls))
        if len(urls) < count:
            urls += get_images_from_pexels(fallback_q, count - len(urls))

    return urls[:count]

def upload_to_wp_media(site_url, wp_pass, img_url, keyword, idx, alt_text=""):
    try:
        img_data = requests.get(img_url, timeout=10).content
        filename = f"seo-{keyword.encode('ascii','ignore').decode().replace(' ', '-')}-{idx}.jpg"
        headers = {"Content-Disposition": f"attachment; filename={filename}", "Content-Type": "image/jpeg"}
        res = requests.post(f"{site_url}/wp-json/wp/v2/media", data=img_data, headers=headers, auth=(WP_USER, wp_pass), timeout=20)
        if res.status_code == 201:
            media_id = res.json().get("id")
            if media_id and alt_text:
                try:
                    requests.post(
                        f"{site_url}/wp-json/wp/v2/media/{media_id}",
                        json={"alt_text": alt_text, "caption": alt_text},
                        auth=(WP_USER, wp_pass), timeout=10
                    )
                except Exception:
                    pass
            return media_id
    except Exception:
        pass
    return None

# ============================================================
# 링크 빌더
# ============================================================
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

# ============================================================
# ★ 수정3: SEO 점수 계산 개선
# ============================================================
def estimate_seo_score(keyword, title, plain_len, meta_desc, img_count, faq_count, tag_count, rank_math_applied):
    score = 0
    kw_lower = keyword.lower()
    title_lower = title.lower()

    # 제목에 키워드 포함 (15점)
    if kw_lower in title_lower:
        score += 15

    # 본문 길이 (20점)
    if plain_len >= MIN_BODY_LENGTH:
        score += 20
    elif plain_len >= 1200:
        score += 12
    elif plain_len >= 800:
        score += 6

    # 메타 디스크립션 (15점)
    if meta_desc:
        if 50 <= len(meta_desc) <= 155:
            score += 15
        elif len(meta_desc) > 0:
            score += 8

    # 이미지 (15점: 장당 5점, 최대 3장)
    score += min(15, img_count * 5)

    # FAQ 스키마 (10점)
    score += min(10, faq_count * 4)

    # 태그 12개 충족 (10점)
    if TAG_COUNT > 0:
        score += min(10, int(10 * tag_count / TAG_COUNT))

    # ★ Rank Math 메타필드 실제 반영 (15점)
    if rank_math_applied:
        score += 15

    return min(100, score)

# ============================================================
# 로그 및 구글시트
# ============================================================
RUN_LOG = []

def record_result(site_url, title, keyword="", tag_count=None, img_count=0, faq_count=0,
                   plain_len=0, rank_math_applied=False, seo_score=None, status="success"):
    RUN_LOG.append({
        "date": now_kst().strftime("%Y-%m-%d %H:%M:%S"),
        "site": site_url,
        "keyword": keyword,
        "title": title,
        "tag_count": tag_count,
        "img_count": img_count,
        "faq_count": faq_count,
        "body_length": plain_len,
        "rank_math_applied": rank_math_applied,
        "seo_score": seo_score,
        "status": status,
    })

# ============================================================
# ★ 수정4: 구글시트 전송 (3회 재시도 + 상세 로그)
# ============================================================
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
        "run_time": now_kst().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(RUN_LOG),
        "success": success_count,
        "fail": fail_count,
        "entries": RUN_LOG,
    }

    last_error = None
    for attempt in range(1, 4):  # ★ 3회 재시도
        try:
            res = requests.post(
                SHEETS_WEBHOOK,
                json=summary_payload,
                timeout=20
            )
            if res.status_code in (200, 201, 302):
                print(f"📊 구글 스프레드시트 요약 전송 완료: 총 {len(RUN_LOG)}건 (성공 {success_count} / 실패 {fail_count})")
                return
            else:
                last_error = f"HTTP {res.status_code}: {res.text[:200]}"
                print(f"  ⚠️ 시트 전송 시도 {attempt}/3 — 응답 코드 {res.status_code}")
        except Exception as e:
            last_error = str(e)
            print(f"  ⚠️ 시트 전송 시도 {attempt}/3 실패: {e}")

        if attempt < 3:
            wait = 5 * attempt
            print(f"     {wait}초 대기 후 재시도...")
            time.sleep(wait)

    print(f"  ❌ 구글 스프레드시트 전송 최종 실패: {last_error}")

# ============================================================
# Gemini 호출
# ============================================================
def generate_with_retry(prompt, max_retries=3):
    global GEMINI_MODEL, _gemini_fallback_active

    model = GEMINI_MODEL_FALLBACK if _gemini_fallback_active else GEMINI_MODEL_PRIMARY
    GEMINI_MODEL = model

    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            res = gemini_client.models.generate_content(
                model=model,
                contents=prompt,
            )
            if res and res.text:
                return res.text
        except Exception as e:
            last_exception = e
            err_str = str(e)
            is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str
            wait = 20 * attempt if is_rate_limit else 5 * attempt
            print(f"  ⚠️ Gemini 호출 실패 ({model}, 시도 {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                print(f"     {wait}초 대기 후 재시도...")
                time.sleep(wait)

    if not _gemini_fallback_active and model == GEMINI_MODEL_PRIMARY:
        err_str = str(last_exception) if last_exception else ""
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            print(f"  🔄 {GEMINI_MODEL_PRIMARY} 일일 한도 소진 → 이후 전체 작업을 {GEMINI_MODEL_FALLBACK}로 전환")
            _gemini_fallback_active = True
            GEMINI_MODEL = GEMINI_MODEL_FALLBACK
            try:
                res = gemini_client.models.generate_content(
                    model=GEMINI_MODEL_FALLBACK,
                    contents=prompt,
                )
                if res and res.text:
                    return res.text
            except Exception as e2:
                last_exception = e2

    if last_exception:
        raise last_exception
    return ""

# ============================================================
# 태그 ID 변환
# ============================================================
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

# ============================================================
# ★ 수정2: Rank Math 메타필드 — register_post_meta 자동 시도
# ============================================================
def try_register_and_patch_rank_math(site_url, wp_pass, post_id, rank_math_meta):
    """
    1단계: PATCH로 메타필드 업데이트 시도
    2단계: 응답 확인 후 반영 여부 판단
    반환: True(반영됨) / False(미반영)
    """
    try:
        patch_res = requests.post(
            f"{site_url}/wp-json/wp/v2/posts/{post_id}",
            json={"meta": rank_math_meta},
            auth=(WP_USER, wp_pass),
            timeout=15
        )
        if patch_res.status_code == 200:
            patched_meta = patch_res.json().get("meta", {}) or {}
            focus_kw = rank_math_meta.get("rank_math_focus_keyword", "")
            if patched_meta.get("rank_math_focus_keyword") == focus_kw:
                return True
    except Exception as e:
        print(f"  ⚠️ Rank Math PATCH 실패: {e}")
    return False

# ============================================================
# 포스팅 메인
# ============================================================
def publish_post(site, keyword, theme, lang, mode, category_ids):
    wp_pass = os.getenv(site['wp_pass_env'])
    if not wp_pass:
        print(f"⏭️  {site['url']} - 비밀번호 환경변수 없음, 스킵")
        record_result(site['url'], f"(skip) {keyword}", keyword=keyword, status="skip_no_password")
        return False

    if not is_site_reachable(site['url']):
        time.sleep(5)
        if not is_site_reachable(site['url']):
            print(f"⏭️  {site['url']} - 사이트 응답 없음(DNS/네트워크), 이번 회차 스킵")
            record_result(site['url'], f"(skip) {keyword}", keyword=keyword, status="skip_unreachable")
            return False

    prompt = make_seo_prompt(keyword, theme, lang, mode)
    try:
        raw_text = generate_with_retry(prompt)
        used_model = GEMINI_MODEL
    except Exception as e:
        print(f"  ❌ Gemini 생성 최종 실패 ({site['url']}): {e}")
        record_result(site['url'], keyword, keyword=keyword, status="fail_gemini")
        return False

    if len(raw_text) < 300:
        print(f"  ⚠️ 본문이 너무 짧음, 스킵: {site['url']}")
        record_result(site['url'], keyword, keyword=keyword, status="fail_short_body")
        return False

    body_with_tags, gemini_title, meta_desc, faq_list = extract_meta_and_faq(raw_text)
    article_body, tag_names = extract_tags_from_article(body_with_tags, keyword, theme=theme, lang=lang)

    plain_len = len(BeautifulSoup(article_body, "html.parser").get_text())
    if plain_len < MIN_BODY_LENGTH:
        print(f"  ⚠️ 본문 글자수 부족({plain_len}자 < {MIN_BODY_LENGTH}자) — 발행 진행, 품질 경고 기록")

    if not meta_desc:
        meta_desc = (article_body[:117] + "...") if len(article_body) > 120 else article_body
        meta_desc = BeautifulSoup(meta_desc, "html.parser").get_text()[:155]

    # ★ 수정1 적용: 이미지 검색 (한국어 자동 번역)
    img_urls = get_multiple_images(keyword, 3)
    media_ids = []
    for idx, url in enumerate(img_urls):
        alt = f"{keyword} - {theme}" if lang != 'ko' else f"{keyword} 관련 이미지"
        mid = upload_to_wp_media(site['url'], wp_pass, url, keyword, idx, alt_text=alt)
        if mid:
            media_ids.append(mid)
    if not media_ids:
        print(f"  ℹ️ 이미지 확보 실패(0장) — 이미지 없이 발행 계속 진행")
    else:
        print(f"  🖼️ 이미지 {len(media_ids)}장 확보 완료")

    tag_ids = get_or_create_tag_ids(site['url'], wp_pass, tag_names)
    if not tag_ids and tag_names:
        print(f"  ⚠️ 태그 ID 변환 전체 실패, 재시도 1회...")
        time.sleep(3)
        tag_ids = get_or_create_tag_ids(site['url'], wp_pass, tag_names)

    if tag_ids:
        print(f"  🏷️ 태그 {len(tag_ids)}/{len(tag_names)}개 확보 (메인 키워드 포함: {tag_names[0]})")
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

    if gemini_title and len(gemini_title) >= 8:
        title = gemini_title
        if keyword.lower() not in title.lower():
            title = f"{title} ({keyword})"
    else:
        if lang == 'ko':
            title = f"[속보] {keyword}" if mode == "news" else f"{keyword} 정보 완벽 정리"
        else:
            title = f"The Essential Guide to {keyword}"

    focus_keywords = [keyword] + [t for t in tag_names[1:5] if t.lower() != keyword.lower()]
    rank_math_meta = {
        "rank_math_focus_keyword": ",".join(focus_keywords),
        "rank_math_description": meta_desc,
    }

    payload = {
        "title": title,
        "content": article_body,
        "excerpt": meta_desc,
        "categories": category_ids,
        "status": "publish",
        "meta": rank_math_meta,
    }
    if tag_ids:
        payload["tags"] = tag_ids
    if media_ids:
        payload["featured_media"] = media_ids[0]

    res_post = None
    last_post_exception = None
    for post_attempt in range(1, 4):
        try:
            res_post = requests.post(
                f"{site['url']}/wp-json/wp/v2/posts", json=payload,
                auth=(WP_USER, wp_pass), timeout=25
            )
            break
        except Exception as e:
            last_post_exception = e
            err_str = str(e)
            is_transient = any(x in err_str for x in [
                "Name or service not known", "Temporary failure in name resolution",
                "NewConnectionError", "ConnectionError", "Timeout", "timed out"
            ])
            if post_attempt < 3 and is_transient:
                wait = 8 * post_attempt
                print(f"  ⚠️ 포스팅 요청 실패 (시도 {post_attempt}/3): {e}")
                print(f"     {wait}초 대기 후 재시도...")
                time.sleep(wait)
                continue
            else:
                print(f"  ❌ 포스팅 요청 최종 실패 ({site['url']}): {e}")
                record_result(site['url'], title, keyword=keyword, plain_len=plain_len, status="fail_request")
                return False

    if res_post is None:
        record_result(site['url'], title, keyword=keyword, plain_len=plain_len, status="fail_request")
        return False

    if res_post.status_code == 403 and "Checking your browser" in res_post.text:
        print(f"  ⚠️ WAF/봇챌린지 403 — 15초 대기 후 1회 재시도")
        time.sleep(15)
        try:
            res_post = requests.post(
                f"{site['url']}/wp-json/wp/v2/posts", json=payload,
                auth=(WP_USER, wp_pass), timeout=25
            )
        except Exception as e:
            print(f"  ❌ 포스팅 재시도 실패 ({site['url']}): {e}")
            record_result(site['url'], title, keyword=keyword, plain_len=plain_len, status="fail_request")
            return False

    if res_post.status_code == 201:
        post_data = res_post.json()
        post_id   = post_data.get("id")
        returned_meta = post_data.get("meta", {}) or {}

        # ★ 수정2: Rank Math 메타필드 반영 확인 + PATCH 재시도
        rank_math_applied = (
            returned_meta.get("rank_math_focus_keyword") == rank_math_meta["rank_math_focus_keyword"]
        )

        if not rank_math_applied and post_id:
            rank_math_applied = try_register_and_patch_rank_math(
                site['url'], wp_pass, post_id, rank_math_meta
            )

        # ★ 수정3: 개선된 SEO 점수
        seo_score = estimate_seo_score(
            keyword, title, plain_len, meta_desc,
            img_count=len(media_ids), faq_count=len(faq_list),
            tag_count=len(tag_ids), rank_math_applied=rank_math_applied
        )

        if rank_math_applied:
            print(f"✅ {site['url']} 발행 완료 — 태그 {len(tag_ids)}개, 이미지 {len(media_ids)}장, "
                  f"FAQ {len(faq_list)}개, Rank Math ✅ 반영, SEO추정 {seo_score}점, 모델:{used_model}: {title}")
        else:
            print(f"✅ {site['url']} 발행 완료 — 태그 {len(tag_ids)}개, 이미지 {len(media_ids)}장, "
                  f"FAQ {len(faq_list)}개, SEO추정 {seo_score}점, 모델:{used_model}: {title}")
            print(f"  ⚠️ [진단] Rank Math 메타필드 미반영 → 해당 사이트 functions.php에 register_post_meta 코드 추가 필요")

        record_result(
            site['url'], title, keyword=keyword, tag_count=len(tag_ids),
            img_count=len(media_ids), faq_count=len(faq_list), plain_len=plain_len,
            rank_math_applied=rank_math_applied, seo_score=seo_score, status="success"
        )
        return True
    else:
        print(f"❌ {site['url']} 발행 실패 (status={res_post.status_code}): {res_post.text[:1500]}")
        if res_post.status_code == 403:
            print(f"  🔍 [진단] 응답 헤더: {dict(res_post.headers)}")
        record_result(
            site['url'], title, keyword=keyword, tag_count=len(tag_ids),
            plain_len=plain_len, status=f"fail_{res_post.status_code}"
        )
        return False

# ============================================================
# 작업 큐 빌드 및 실행
# ============================================================
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

    # ★ 수정4: 구글시트 3회 재시도 전송
    flush_log_to_google_sheet()
    print("\n🏁 이번 회차 작업이 모두 종료되었습니다.")

if __name__ == "__main__":
    run()
