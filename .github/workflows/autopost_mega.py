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
# ★ 한국어 → 영어 이미지 검색 번역 매핑
# ============================================================
KO_TO_EN_IMAGE = {
    # ── 복합 패턴 (긴 것 우선 매칭) ─────────────────────────
    "대한민국 최신 경제 및 사회 변화 트렌드 분석": "South Korea economy society trend analysis business",
    "혈당스파이크 줄이는":   "blood sugar spike reduction tips",
    "콜레스테롤 낮추는":      "cholesterol lowering heart healthy",
    "혈압 낮추는":            "blood pressure lowering hypertension",
    "고혈압 낮추는":         "hypertension blood pressure healthy food",
    "지방간에 좋은":         "fatty liver healthy food nutrition",
    "면역력 높이는":         "immune system boosting health supplements",
    "불면증 극복":           "insomnia cure sleep improvement",
    "비타민D 부족":          "vitamin D deficiency symptoms",
    "전립선비대증 관리":     "prostate BPH management men health",
    "만성피로증후군":        "chronic fatigue syndrome treatment",
    "갑상선기능저하":        "hypothyroidism thyroid disorder",
    "역류성식도염":          "acid reflux GERD esophagus",
    "과민성대장":            "irritable bowel IBS syndrome",
    "허리디스크":            "herniated lumbar disc back pain",
    "목디스크":              "cervical disc neck pain",
    "원형탈모":              "alopecia areata hair loss",
    "공황장애":              "panic disorder anxiety mental",
    # ── 단어 단위 ────────────────────────────────────────────
    "고혈압":      "high blood pressure hypertension",
    "혈당스파이크": "blood sugar spike glucose",
    "혈당":        "blood glucose sugar control",
    "혈압":        "blood pressure heart",
    "당뇨병":      "diabetes insulin treatment",
    "당뇨":        "diabetes blood sugar",
    "콜레스테롤":  "cholesterol heart health",
    "중성지방":    "triglycerides blood lipid",
    "지방간":      "fatty liver hepatic",
    "간수치":      "liver enzymes blood test",
    "간염":        "hepatitis liver",
    "요로결석":    "kidney stone urinary pain",
    "담석증":      "gallstone bile duct",
    "크론병":      "Crohn disease intestinal",
    "소화불량":    "indigestion digestive",
    "변비":        "constipation bowel",
    "비만":        "obesity weight management",
    "체질량지수":  "BMI body mass index obesity",
    "다이어트":    "diet weight loss nutrition",
    "갑상선":      "thyroid gland hormone",
    "면역력":      "immune system boost health",
    "자가면역":    "autoimmune disease immunity",
    "류마티스":    "rheumatoid arthritis joint",
    "관절":        "joint pain arthritis",
    "무릎":        "knee pain orthopedic",
    "허리":        "back pain spine lumbar",
    "디스크":      "spinal disc herniated",
    "골다공증":    "osteoporosis bone density",
    "탈모":        "hair loss alopecia treatment",
    "두피":        "scalp treatment hair care",
    "아토피":      "atopic dermatitis eczema",
    "여드름":      "acne skin treatment",
    "피부":        "skin care dermatology",
    "불면증":      "insomnia sleep disorder",
    "수면장애":    "sleep disorder insomnia",
    "수면":        "sleep health rest",
    "만성피로":    "chronic fatigue tiredness",
    "번아웃":      "burnout mental exhaustion",
    "피로":        "fatigue tiredness",
    "스트레스":    "stress management mental health",
    "우울증":      "depression mental health",
    "치매":        "dementia Alzheimer brain",
    "두통":        "headache pain",
    "편두통":      "migraine headache",
    "이명":        "tinnitus ear ringing",
    "안구건조":    "dry eye syndrome",
    "비염":        "rhinitis allergy nasal",
    "천식":        "asthma respiratory",
    "통풍":        "gout uric acid joint",
    "요산":        "uric acid gout",
    "전립선":      "prostate health men",
    "갱년기":      "menopause hormonal women",
    "생리불순":    "menstrual irregularity women",
    "영양제":      "supplements vitamins health",
    "비타민D":     "vitamin D supplement",
    "비타민":      "vitamins minerals supplements",
    "오메가3":     "omega-3 fish oil supplement",
    "프로바이오틱스": "probiotics gut health",
    "콜라겐":      "collagen skin beauty",
    "단백질":      "protein muscle fitness",
    "자가진단":    "self diagnosis medical check",
    "초기증상":    "early symptoms warning signs",
    "예방":        "prevention healthcare",
    "치료":        "medical treatment therapy",
    "증상":        "symptoms medical signs",
    "운동":        "exercise fitness workout",
    "음식":        "healthy food nutrition",
    "영양":        "nutrition food",
    "암":          "cancer treatment medical",
    "심장":        "heart cardiovascular",
    "뇌":          "brain health neurology",
    "폐":          "lung respiratory",
    "신장":        "kidney health renal",
    "간":          "liver health medical",
    # ── 동사/형용사 패턴 ─────────────────────────────────────
    "낮추는":      "lowering reduction",
    "높이는":      "boosting increase",
    "줄이는":      "reducing control",
    "좋은":        "healthy beneficial",
    "극복":        "overcome improve",
    "관리":        "management care",
    "부족":        "deficiency lack",
    "원인":        "cause reason",
    "방법":        "method tips",
    "효과":        "effect benefit",
    "추천":        "recommended best",
    "종류":        "types kinds",
    "부작용":      "side effects risks",
    "복용법":      "dosage how to take",
    "개선":        "improvement",
    # ── 뉴스/경제 ────────────────────────────────────────────
    "대한민국":    "South Korea",
    "한국":        "South Korea",
    "경제":        "economy finance business",
    "사회":        "society community people",
    "트렌드":      "trend analysis modern",
    "분석":        "analysis data report",
    "최신":        "latest current news",
    "정치":        "politics government Korea",
    "부동산":      "real estate property Korea",
    "금융":        "finance banking money",
    "물가":        "inflation price consumer",
    "취업":        "employment jobs career",
    "교육":        "education school learning",
    "기술":        "technology innovation",
    "문화":        "Korean culture lifestyle",
    "서울":        "Seoul Korea cityscape",
    "여행":        "Korea travel tourism",
}

def translate_ko_to_en_for_image(keyword: str) -> str:
    """한국어 키워드 → 이미지 검색용 영어 (긴 패턴 우선 매칭)"""
    import re as _re2
    result = keyword
    for ko, en in sorted(KO_TO_EN_IMAGE.items(), key=lambda x: -len(x[0])):
        result = result.replace(ko, en)
    if any('\uac00' <= c <= '\ud7a3' for c in result):
        if any(w in keyword for w in ["경제","사회","트렌드","뉴스","정치","금융","부동산"]):
            return "South Korea economy society business news"
        elif any(w in keyword for w in ["음식","요리","식품","맛집","건강식"]):
            return "healthy Korean food nutrition diet"
        else:
            return "medical health treatment Korea"
    result = _re2.sub(r'\s+', ' ', result).strip()
    return result[:80]

# ============================================================
# 22개 사이트 설정
# ============================================================
SITES_CONFIG = [
    {"url": "https://k-health365.com",      "lang": "ko", "theme": "건강과 의학",          "mode": "blog", "keywords_file": ".github/workflows/keywords_khealth.txt",        "wp_pass_env": "KHEALTH365COM",       "daily": 15},
    {"url": "https://koreamedicaltour.com",  "lang": "en", "theme": "Korea Medical Tourism","mode": "blog", "keywords_file": ".github/workflows/keywords_medicaltour.txt",     "wp_pass_env": "KOREAMEDICALTOURCOM", "daily": 3},
    {"url": "https://koreainvest365.com",    "lang": "en", "theme": "Investment",           "mode": "blog", "keywords_file": ".github/workflows/keywords_kinvest.txt",         "wp_pass_env": "KOREAINVEST365COM",   "daily": 3},
    {"url": "https://koreainsurance365.com", "lang": "en", "theme": "Insurance",            "mode": "blog", "keywords_file": ".github/workflows/keywords_kinsurance.txt",      "wp_pass_env": "KOREAINSURANCE365COM","daily": 3},
    {"url": "https://kfinance365.com",       "lang": "en", "theme": "Finance",              "mode": "blog", "keywords_file": ".github/workflows/keywords_kfinance.txt",        "wp_pass_env": "KFINANCE365COM",      "daily": 3},
    {"url": "https://koreataxnlaw.com",      "lang": "en", "theme": "Tax and Law",          "mode": "blog", "keywords_file": ".github/workflows/keywords_ktax.txt",             "wp_pass_env": "KOREATAXNLAWCOM",     "daily": 3},
    {"url": "https://koreacrypto365.com",    "lang": "en", "theme": "Crypto",               "mode": "blog", "keywords_file": ".github/workflows/keywords_kcrypto.txt",         "wp_pass_env": "KOREACRYPTO365COM",   "daily": 3},
    {"url": "https://ktech365.com",          "lang": "en", "theme": "Technology",           "mode": "blog", "keywords_file": ".github/workflows/keywords_ktech.txt",            "wp_pass_env": "KTECH365COM",         "daily": 3},
    {"url": "https://kskin365.com",          "lang": "en", "theme": "K-Beauty",              "mode": "blog", "keywords_file": ".github/workflows/keywords_kskin.txt",            "wp_pass_env": "KSKIN365COM",         "daily": 3},
    {"url": "https://oliveyoungkorea.com",   "lang": "en", "theme": "K-Beauty Reviews",     "mode": "blog", "keywords_file": ".github/workflows/keywords_oliveyoung.txt",      "wp_pass_env": "OLIVEYOUNGKOREACOM",  "daily": 3},
    {"url": "https://kworld365.com",         "lang": "en", "theme": "K-POP",                "mode": "blog", "keywords_file": ".github/workflows/keywords_kworld.txt",          "wp_pass_env": "KWORLD365COM",        "daily": 5},
    {"url": "https://k-trip365.com",         "lang": "en", "theme": "Travel",               "mode": "blog", "keywords_file": ".github/workflows/keywords_ktrip.txt",            "wp_pass_env": "KTRIP365COM",         "daily": 3},
    {"url": "https://k-visa365.com",         "lang": "en", "theme": "Visa Guide",           "mode": "blog", "keywords_file": ".github/workflows/keywords_kvisa.txt",            "wp_pass_env": "KVISA365COM",         "daily": 3},
    {"url": "https://koreawedding365.com",   "lang": "en", "theme": "Wedding",              "mode": "blog", "keywords_file": ".github/workflows/keywords_kwedding.txt",        "wp_pass_env": "KOREAWEDDING365COM",  "daily": 3},
    {"url": "https://kstudy365.com",         "lang": "en", "theme": "Study in Korea",       "mode": "blog", "keywords_file": ".github/workflows/keywords_kstudy365.txt",       "wp_pass_env": "KSTUDY365COM",        "daily": 3},
    {"url": "https://studyinkorea365.com",   "lang": "en", "theme": "International Students","mode": "blog","keywords_file": ".github/workflows/keywords_studyinkorea365.txt",  "wp_pass_env": "STUDYINKOREA365COM",  "daily": 3},
    {"url": "https://jobkorea365.com",       "lang": "en", "theme": "Employment",           "mode": "blog", "keywords_file": ".github/workflows/keywords_jobkorea365.txt",      "wp_pass_env": "JOBKOREA365COM",      "daily": 3},
    {"url": "https://jobinkorea365.com",     "lang": "en", "theme": "Jobs in Korea",        "mode": "blog", "keywords_file": ".github/workflows/keywords_jobinkorea365.txt",   "wp_pass_env": "JOBINKOREA365COM",    "daily": 3},
    {"url": "https://jobkoreaglobal.com",    "lang": "en", "theme": "Recruitment",          "mode": "blog", "keywords_file": ".github/workflows/keywords_jobkoreaglobal.txt",  "wp_pass_env": "JOBKOREAGLOBALCOM",   "daily": 3},
    {"url": "https://korea365.org",          "lang": "en", "theme": "Korea Culture",        "mode": "blog", "keywords_file": ".github/workflows/keywords_korea365.txt",        "wp_pass_env": "KOREA365ORG",         "daily": 4},
    {"url": "https://koreanews365.com",      "lang": "ko", "theme": "한국 뉴스",            "mode": "news", "keywords_file": ".github/workflows/keywords_koreanews.txt",       "wp_pass_env": "KOREANEWS365COM",     "daily": 5},
    {"url": "https://theseouljournal.com",   "lang": "en", "theme": "Seoul Lifestyle",      "mode": "blog", "keywords_file": ".github/workflows/keywords_seouljournal.txt",    "wp_pass_env": "THESEOULJOURNALCOM",  "daily": 5},
]

EXTERNAL_AUTHORITY_LINKS = {
    "건강과 의학": [("질병관리청","https://www.kdca.go.kr"),("대한의학회","https://www.kams.or.kr"),("WHO","https://www.who.int"),("국민건강보험공단","https://www.nhis.or.kr"),("식품의약품안전처","https://www.mfds.go.kr"),("PubMed","https://pubmed.ncbi.nlm.nih.gov")],
    "한국 뉴스": [("대한민국 정책브리핑","https://www.korea.kr"),("통계청","https://kostat.go.kr"),("기획재정부","https://www.moef.go.kr"),("연합뉴스","https://www.yna.co.kr")],
    "default_en": [("Korea.net","https://www.korea.net"),("Visit Korea","https://english.visitkorea.or.kr"),("Invest Korea","https://www.investkorea.org"),("Statistics Korea","https://kostat.go.kr/eng"),("Ministry of Justice Korea","https://www.moj.go.kr/moj/index.do"),("Wikipedia","https://en.wikipedia.org")],
    "Finance": [("Bank of Korea","https://www.bok.or.kr/eng"),("Financial Services Commission","https://www.fsc.go.kr/eng"),("Korea Exchange","https://global.krx.co.kr")],
    "Investment": [("Bank of Korea","https://www.bok.or.kr/eng"),("Korea Exchange","https://global.krx.co.kr"),("Invest Korea","https://www.investkorea.org")],
    "Tax and Law": [("National Tax Service","https://www.nts.go.kr/english"),("Ministry of Justice Korea","https://www.moj.go.kr/moj/index.do"),("Korea Legislation Research Institute","https://elaw.klri.re.kr")],
    "Jobs in Korea": [("Ministry of Employment and Labor","https://www.moel.go.kr/english"),("HRD Korea","https://www.hrdkorea.or.kr/eng"),("Work24","https://www.work24.go.kr")],
    "Employment": [("Ministry of Employment and Labor","https://www.moel.go.kr/english"),("Work24","https://www.work24.go.kr")],
    "Recruitment": [("Ministry of Employment and Labor","https://www.moel.go.kr/english"),("HRD Korea","https://www.hrdkorea.or.kr/eng")],
    "Study in Korea": [("Study in Korea (NIIED)","https://www.studyinkorea.go.kr"),("Ministry of Education Korea","https://english.moe.go.kr"),("NIIED","https://www.niied.go.kr/eng")],
    "International Students": [("Study in Korea (NIIED)","https://www.studyinkorea.go.kr"),("HiKorea (Immigration)","https://www.hikorea.go.kr")],
    "Visa Guide": [("HiKorea (Immigration)","https://www.hikorea.go.kr"),("Ministry of Justice Korea","https://www.moj.go.kr/moj/index.do")],
    "Korea Medical Tourism": [("Korea Health Industry Development Institute","https://www.khidi.or.kr/eps"),("Visit Korea","https://english.visitkorea.or.kr")],
    "K-Beauty": [("Visit Korea","https://english.visitkorea.or.kr"),("Korea.net","https://www.korea.net")],
    "K-Beauty Reviews": [("Visit Korea","https://english.visitkorea.or.kr"),("Korea.net","https://www.korea.net")],
    "Travel": [("Visit Korea","https://english.visitkorea.or.kr"),("Korea Tourism Organization","https://www.knto.or.kr")],
    "Korea Culture": [("Korea.net","https://www.korea.net"),("Korean Culture and Information Service","https://www.kocis.go.kr")],
    "Crypto": [("Financial Services Commission","https://www.fsc.go.kr/eng"),("Bank of Korea","https://www.bok.or.kr/eng")],
    "Insurance": [("Financial Services Commission","https://www.fsc.go.kr/eng"),("National Health Insurance Service","https://www.nhis.or.kr/english")],
    "Wedding": [("Visit Korea","https://english.visitkorea.or.kr"),("Korea.net","https://www.korea.net")],
    "Technology": [("Ministry of Science and ICT","https://www.msit.go.kr/eng"),("NIPA","https://www.nipa.kr/home/eng")],
    "K-POP": [("Korea.net","https://www.korea.net"), "Korean Culture and Information Service","https://www.kocis.go.kr"],
    "Seoul Lifestyle": [("Seoul Metropolitan Government","https://english.seoul.go.kr"),("Visit Korea","https://english.visitkorea.or.kr")],
}

# ============================================================
# 슬롯 분배
# ============================================================
def split_daily_into_slots(daily, num_slots=3):
    base = daily // num_slots
    rem  = daily % num_slots
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

NEWS_FALLBACK_KEYWORDS = [
    ("한국 부동산 정책 동향", "최근 부동산 정책 변화와 시장 영향을 심층 분석합니다."),
    ("한국은행 기준금리 전망", "기준금리 결정 배경과 향후 경제 전망을 다룹니다."),
    ("국내 주식시장 시황 분석", "최근 국내 증시 동향과 주요 이슈를 정리합니다."),
    ("반도체 수출 실적 리포트", "반도체 산업 수출 동향과 글로벌 경쟁력을 분석합니다."),
    ("청년 주거지원 정책 총정리", "청년층 대상 주거 지원 정책의 핵심 내용을 정리합니다."),
    ("국민연금 개혁안 핵심", "국민연금 개혁 논의의 주요 쟁점을 살펴봅니다."),
    ("K-배터리 기술 개발 현황", "국내 배터리 산업의 기술 혁신과 시장 동향을 다룹니다."),
    ("한국 인공지능 스타트업", "국내 AI 스타트업 생태계의 최신 흐름을 분석합니다."),
    ("국내 저출산 대책 예산", "저출산 문제 해결을 위한 정부 예산 정책을 정리합니다."),
    ("기후변화 대응 탄소중립", "탄소중립 목표 달성을 위한 국내 정책 현황을 다룹니다."),
    ("K-푸드 전세계 수출 현황", "한국 식품의 해외 수출 트렌드를 분석합니다."),
    ("디지털 자산 법안 통과", "디지털 자산 관련 입법 동향을 정리합니다."),
    ("국내 물가 동향 및 전망", "최근 물가 상승률과 향후 전망을 살펴봅니다."),
    ("청년 창업 지원 프로그램", "청년 창업가를 위한 정부 지원 프로그램을 소개합니다."),
    ("자율주행 자동차 시범 운행", "국내 자율주행 기술 시범사업 현황을 다룹니다."),
    ("의료 개혁 및 필수의료 지원", "필수의료 강화를 위한 정책 방향을 분석합니다."),
    ("전세사기 피해자 지원 대책", "전세사기 피해 구제 정책의 핵심을 정리합니다."),
    ("국내 방산 수출 역대 최고", "방위산업 수출 호조의 배경을 분석합니다."),
    ("AI 반도체 팹리스 육성", "AI 반도체 설계 산업 육성 정책을 다룹니다."),
    ("국내 OTT 시장 점유율 경쟁", "OTT 플랫폼 간 경쟁 구도와 시장 변화를 살펴봅니다."),
]

def crawl_rss_news():
    try:
        res = requests.get("https://fs.khan.co.kr/rss/rssdata/total_news.xml", timeout=10)
        soup = BeautifulSoup(res.text, 'xml')
        items = soup.find_all('item')
        if items:
            chosen = random.choice(items)
            title = chosen.title.text.strip() if chosen.title else ""
            desc  = chosen.description.text.strip() if chosen.description else ""
            if title and len(title) >= 5:
                return title, desc
    except Exception as e:
        print(f"   ⚠️ RSS 크롤링 실패, 키워드 풀에서 대체 선택: {e}")
    return random.choice(NEWS_FALLBACK_KEYWORDS)

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

# ============================================================
# ★ 보완 완료된 최종 프롬프트 생성 함수 (복사 영역)
# ============================================================
def make_seo_prompt(keyword, theme, lang, mode="blog"):
    reporter      = random.choice(REPORTERS)
    tag_lang      = "영어로" if lang == "en" else "한국어로"
    title_style   = pick_title_style(lang)

    # 테마 분석 기반 의학 조건 설정
    is_medical = "건강" in theme or "medical" in theme.lower()

    if mode == "news":
        return f"""
당신은 주요 일간지의 시니어 취재기자입니다.
주제: '{keyword}'에 대해 엄격한 신문기사체 기사를 작성하세요.

[필수 지침 — 구글 품질 가이드라인 강제 준수, 하나라도 빠지면 안 됨]
1. 문체: '했다', '밝혔다', '조사됐다'로 끝나는 6하원칙 기사체. 마크다운 금지.
2. 바이라인: 기사 맨 위에 '◇ {reporter}' 한 줄 삽입.
3. 분량: HTML(h2,h3,p,strong,ul,li)만 사용해 최소 1800자 이상.
4. ★ 모바일 가독성 강제 최적화: 모바일 가독성을 위해 모든 문장 사이에 반드시 한 줄 이상의 공백(<br> 또는 완벽히 분리된 <p> 태그)을 두고, 문단을 극도로 짧게(한 단락에 2~3문장 이내) 쪼개어 배치하세요. 텍스트 블록이 빽빽하게 뭉치면 절대 안 됩니다.
5. ★ 통계/수치 강제: 본문 안에 구체적인 숫자·통계·비율·금액을 최소 3개 이상 명시적으로 포함 (예: "23% 증가", "약 150만 명", "2024년 대비 12.5%p 상승" 등 막연한 표현 금지, 반드시 숫자로 표기).
6. ★ 출처 강제: 통계 옆에 출처 기관명을 괄호로 명시 (예: "(통계청, 2026)", "(한국은행 발표)").
7. ★ 카테고리 일치 내부 링크 수립: 본문 중간 자연스러운 문맥으로 최소 4개 이상의 내부 링크 자리를 마련하되, 반드시 현재 카테고리인 '{theme}'와 어울리는 유기적인 주제로만 한정하세요. 전혀 관련 없는 다른 허브 테마(예: 웨딩, 뷰티, K-POP, 투자 등)를 섞어 쓰는 스팸성 링크 배열은 절대 금지합니다.
8. ★ 외부 권위 링크 강제: 정부기관·통계청·연구기관 등 공신력 있는 기관명을 본문에 최소 3회 이상 언급.
9. E-E-A-T: 전문가 인터뷰 인용구 최소 1개 포함.
10. 구조: h2 최소 3개.
11. 제목 스타일: {title_style} / 출력 첫 줄에 'TITLE:' 로 시작하는 제목 한 줄.
12. ★ 메타 디스크립션: 본문 끝에 'META_DESC:' 로 시작, 정확히 130~140자 (한글 기준) 분량으로 작성. 너무 짧거나 길면 안 됨.
13. FAQ: META_DESC 다음 'FAQ_START' ~ 'FAQ_END' 블록에 Q:/A: 형식 3문항.
14. ★ 태그 생성 알고리즘 제어: FAQ_END 다음 'TAGS:' 로 시작, {TAG_COUNT}개 {tag_lang} 키워드. 각 태그는 최대 3단어(약 15자) 이내로 짧고 핵심적으로 작성. 첫 번째는 반드시 '{keyword}'.
    - {'[주의] 의학/질병 관련 키워드이므로 태그 조합 시 "#증상 효능", "#증상 가격" 같이 의미가 맞지 않는 무작위 자동조합은 절대 배제하세요. 대신 "원인", "치료법", "관리", "검사" 등의 단어로 매칭할 것.' if is_medical else '문맥상 완벽히 일치하는 자연스러운 키워드로만 조율할 것.'}
출력 순서: TITLE → 본문HTML → META_DESC → FAQ_START~FAQ_END → TAGS
"""

    persona = "의학 박사" if is_medical else "산업 분야 최고 전문 자문위원"
    
    return f"""
당신은 {persona}이자 15년 경력의 글로벌 최고 권위 SEO 콘텐츠 마스터 프로라이터입니다.
주제: '{keyword}' ({theme}) / 언어: {lang}

[필수 지침 — 구글 애드센스 품질 평가 및 구글 상위 노출 95점 이상 획득 기준]
1. HTML 전용: h2,h3,p,ul,li,ol,strong,table,tr,td 태그만. 마크다운(##, **, - 등) 절대 금지.
2. 분량: 공백 제외 최소 2500자 이상의 깊이 있고 전문성이 고도로 집중된 상세 내용.
3. ★ 모바일 독자 최적화 레이아웃 (체류 시간 증대): 모바일 가독성을 완벽하게 보장하기 위해 '모든 문장 사이에 반드시 한 줄 이상의 빈 줄 공백(<br> 또는 완전한 단락 공백)'을 삽입하고, 한 문단(<p>)은 '최대 2문장 이하'로 매우 짧게 동강 내어 구성하세요. 텍스트가 빽빽하면 품질 점수가 깎입니다.
4. 키워드: 첫 단락 문두에 '{keyword}' 배치, 전체 10회 이상 자연스럽게 삽입.
5. 구조: h2 최소 5개, h3 최소 4개, ul/li 리스트 3개 이상, 정밀 데이터 비교 table 1개 이상.
6. ★ 통계/수치 강제: 본문 안에 구체적인 숫자·통계·비율·금액·기간을 최소 3개 이상 명시적으로 포함. 막연한 표현("많은", "대부분") 대신 반드시 숫자로 표기 (예: "73%의 응답자", "평균 450,000원", "최근 5년간").
7. ★ 출처 강제: 통계 옆에 출처를 괄호로 명시 (예: "(KOSIS, 2026)", "(NIH 연구결과)", "(보건복지부 자료)").
8. ★ 단일 테마 컨텍스트 유지 (중요): 본문 중간 자연스러운 문맥에서 내부 링크 삽입이 가능하도록 관련 키워드를 배치하되, 반드시 현재 도메인 테마인 '{theme}' 카테고리에 완벽하게 종속되는 내용이어야 합니다. 하단 링크 섹션이나 본문 내에 서로 다른 도메인 카테고리(예: K-Beauty, 뷰티 리뷰, 웨딩, 취업 등)의 키워드를 무작위 스팸 형태로 섞는 행위를 완벽히 금지합니다.
9. ★ 외부 권위 링크 강제: 정부기관·학회·국제기구 등 공신력 있는 기관명을 본문에 최소 3회 이상 언급.
10. E-E-A-T 기반 실제 경험: {persona}로서의 실무/임상 전문성을 입증할 수 있는 디테일한 진행 절차, 실제 기간, 실질적 비용대 등의 예시를 최소 2곳 이상 반영할 것.
11. 제목 스타일: {title_style} / 출력 첫 줄에 'TITLE:' 로 시작하는 제목 한 줄.
12. ★ 메타 디스크립션: 본문 끝에 'META_DESC:' 로 시작, 정확히 130~140자(영문은 130~155자) 분량으로 작성. 너무 짧거나 길면 안 됨.
13. FAQ: META_DESC 다음 'FAQ_START' ~ 'FAQ_END' 블록에 Q:/A: 형식 3문항.
14. ★ 태그 조합 무결성 검증: FAQ_END 다음 'TAGS:' 로 시작, {TAG_COUNT}개 {tag_lang} 키워드. 각 태그는 최대 3단어(약 15자) 이내로 짧고 핵심적으로 작성 (긴 구문 절대 금지). 첫 번째는 반드시 '{keyword}'.
    - {'[크리티컬 감점 예방] 의학/질병 관련 글이므로 "#공황장애 증상 가격", "#공황장애 증상 효능" 처럼 문맥에 맞지 않는 조잡한 태그 조합을 생성하지 마십시오. 대신 "원인", "치료법", "예방", "체크리스트" 등과 조합하세요.' if is_medical else '주제 문맥에 완벽히 일치하는 전문 키워드로만 세팅하세요.'}
출력 순서: TITLE → 본문HTML → META_DESC → FAQ_START~FAQ_END → TAGS
"""

# ============================================================
# 파싱 및 나머지 유틸리티 함수들 (기존 유지)
# ============================================================
def extract_meta_and_faq(text):
    import re as _re3
    title = ""; meta_desc = ""; faq_list = []
    lines = text.split("\n"); out_lines = []
    in_faq = False; cur_q = None
    for line in lines:
        s = line.strip()
        s_clean = s.lstrip('#').lstrip('*').strip()
        if s_clean.upper().startswith("TITLE:"):
            title = s_clean.split(":",1)[1].strip() if ":" in s_clean else ""
            continue
        if s_clean.upper().startswith("META_DESC:"):
            meta_desc = s_clean.split(":",1)[1].strip() if ":" in s_clean else ""
            continue
        if s.upper().startswith("FAQ_START"):
            in_faq = True; continue
        if s.upper().startswith("FAQ_END"):
            in_faq = False; continue
        if in_faq:
            if s[:2].upper() == "Q:": cur_q = s[2:].strip()
            elif s[:2].upper() == "A:" and cur_q:
                faq_list.append((cur_q, s[2:].strip())); cur_q = None
            continue
        out_lines.append(line)

    title = title.strip('"').strip("'").strip("*").strip()

    if not title or len(title) < 8:
        body_text = "\n".join(out_lines)
        h1_match = _re3.search(r'<h1[^>]*>(.*?)</h1>', body_text, _re3.DOTALL | _re3.IGNORECASE)
        if h1_match:
            extracted = _re3.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
            extracted = extracted.strip('"').strip("'").strip("*").strip()
            if len(extracted) >= 8:
                title = extracted
        if not title:
            for ol in out_lines:
                plain = _re3.sub(r'<[^>]+>', '', ol).strip()
                if len(plain) >= 10:
                    title = plain[:120]
                    break

    return "\n".join(out_lines).strip(), title, meta_desc, faq_list

def build_fallback_tag_pool(kw, theme=None, lang="ko"):
    s = ["효능","부작용","가격","추천","비교","후기","정보","방법","순위","팁","총정리","가이드"] if lang=="ko" \
        else ["guide","review","cost","tips","comparison","benefits","ranking","checklist","overview","FAQ","how to","best practices"]
    pool = [f"{kw} {x}" for x in s]
    if theme: pool.insert(0, theme)
    pool.append(kw)
    return pool

def _truncate_tag(tag: str, max_words: int = 3, max_chars: int = 20) -> str:
    words = tag.strip().split()
    if len(words) > max_words:
        tag = " ".join(words[:max_words])
    if len(tag) > max_chars:
        tag = tag[:max_chars].rstrip()
    return tag

def extract_tags_from_article(article_text, fallback_keyword, theme=None, lang="ko"):
    lines = article_text.strip().split("\n")
    tags = []; body_lines = []
    for line in lines:
        s = line.strip()
        if s.upper().startswith("TAGS:"):
            raw = s.split(":",1)[1] if ":" in s else ""
            tags = [t.strip() for t in raw.split(",") if t.strip()]
        else:
            body_lines.append(line)
    article_body = "\n".join(body_lines).strip()
    if not tags: tags = [fallback_keyword]

    kk = fallback_keyword.strip().lower()
    tags = [t for t in tags if t.strip().lower() != kk]
    tags = [_truncate_tag(t) for t in tags]
    tags.insert(0, fallback_keyword)

    seen = set(); deduped = []
    for t in tags:
        k = t.strip().lower()
        if k and k not in seen: seen.add(k); deduped.append(t)
    tags = deduped
    if len(tags) > TAG_COUNT:
        tags = tags[:TAG_COUNT]
    elif len(tags) < TAG_COUNT:
        for c in build_fallback_tag_pool(fallback_keyword, theme, lang):
            c = _truncate_tag(c)
            if len(tags) >= TAG_COUNT: break
            if c.strip().lower() not in seen: tags.append(c); seen.add(c.strip().lower())
        i = 1
        while len(tags) < TAG_COUNT:
            f = f"{fallback_keyword} {i}" if i > 1 else fallback_keyword
            if f.strip().lower() not in seen: tags.append(f); seen.add(f.strip().lower())
            i += 1
    return article_body, tags

def is_site_reachable(site_url, timeout=8):
    try:
        r = requests.head(f"{site_url}/wp-json/", timeout=timeout, allow_redirects=True)
        return True
    except requests.exceptions.ConnectionError as e:
        print(f"    🔍 [reachability] ConnectionError: {str(e)[:200]}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"    🔍 [reachability] Timeout: {str(e)[:200]}")
        return False
    except requests.exceptions.SSLError as e:
        print(f"    🔍 [reachability] SSLError: {str(e)[:200]}")
        return False
    except Exception as e:
        print(f"    🔍 [reachability] {type(e).__name__}: {str(e)[:200]}")
        return False

def get_images_from_pixabay(query, need):
    urls = []
    if not PIXABAY_KEY: return urls
    try:
        url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={requests.utils.quote(query)}&image_type=photo&per_page=20&safesearch=true"
        res_raw = requests.get(url, timeout=10)
        try: res = res_raw.json()
        except: return urls
        hits = res.get("hits") or []
        if hits:
            sample = random.sample(hits, min(need, len(hits)))
            for h in sample:
                if h.get("webformatURL"): urls.append(h["webformatURL"])
    except Exception as e:
        print(f"  ⚠️ Pixabay 이미지 검색 실패: {e}")
    return urls

def get_images_from_pexels(query, need):
    urls = []
    if not PEXELS_KEY: return urls
    try:
        headers = {"Authorization": PEXELS_KEY}
        url = f"https://api.pexels.com/v1/search?query={requests.utils.quote(query)}&per_page=20&safe_search=true"
        res = requests.get(url, headers=headers, timeout=10).json()
        photos = res.get("photos") or []
        if photos:
            sample = random.sample(photos, min(need, len(photos)))
            for p in sample:
                src = (p.get("src") or {}).get("large") or (p.get("src") or {}).get("medium")
                if src: urls.append(src)
    except Exception as e:
        print(f"  ⚠️ Pexels 이미지 검색 실패: {e}")
    return urls

def get_multiple_images(keyword, count=3):
    has_korean = any('\uac00' <= c <= '\ud7a3' for c in keyword)
    q = keyword.encode('ascii','ignore').decode().strip()
    urls = []
    if has_korean or not q:
        en_query = translate_ko_to_en_for_image(keyword)
        urls.extend(get_images_from_pixabay(en_query, count))
        if len(urls) < count:
            urls.extend(get_images_from_pexels(en_query, count - len(urls)))
    else:
        urls.extend(get_images_from_pixabay(keyword, count))
        if len(urls) < count:
            urls.extend(get_images_from_pexels(keyword, count - len(urls)))
    return list(dict.fromkeys(urls))[:count]
