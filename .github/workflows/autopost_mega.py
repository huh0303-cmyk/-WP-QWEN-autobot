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
    "콜레스테롤 낮추는":     "cholesterol lowering heart healthy",
    "혈압 낮추는":           "blood pressure lowering hypertension",
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
    "혈당스파이크":"blood sugar spike glucose",
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
    # 긴 패턴 먼저 매칭해야 정확도 향상
    for ko, en in sorted(KO_TO_EN_IMAGE.items(), key=lambda x: -len(x[0])):
        result = result.replace(ko, en)
    # 한글 잔존 시 테마 기반 fallback
    if any('\uac00' <= c <= '\ud7a3' for c in result):
        if any(w in keyword for w in ["경제","사회","트렌드","뉴스","정치","금융","부동산"]):
            return "South Korea economy society business news"
        elif any(w in keyword for w in ["음식","요리","식품","맛집","건강식"]):
            return "healthy Korean food nutrition diet"
        else:
            return "medical health treatment Korea"
    # 연속 공백 정리 및 길이 제한
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
    {"url": "https://koreataxnlaw.com",      "lang": "en", "theme": "Tax and Law",          "mode": "blog", "keywords_file": ".github/workflows/keywords_ktax.txt",            "wp_pass_env": "KOREATAXNLAWCOM",     "daily": 3},
    {"url": "https://koreacrypto365.com",    "lang": "en", "theme": "Crypto",               "mode": "blog", "keywords_file": ".github/workflows/keywords_kcrypto.txt",         "wp_pass_env": "KOREACRYPTO365COM",   "daily": 3},
    {"url": "https://ktech365.com",          "lang": "en", "theme": "Technology",           "mode": "blog", "keywords_file": ".github/workflows/keywords_ktech.txt",           "wp_pass_env": "KTECH365COM",         "daily": 3},
    {"url": "https://kskin365.com",          "lang": "en", "theme": "K-Beauty",             "mode": "blog", "keywords_file": ".github/workflows/keywords_kskin.txt",           "wp_pass_env": "KSKIN365COM",         "daily": 3},
    {"url": "https://oliveyoungkorea.com",   "lang": "en", "theme": "K-Beauty Reviews",     "mode": "blog", "keywords_file": ".github/workflows/keywords_oliveyoung.txt",      "wp_pass_env": "OLIVEYOUNGKOREACOM",  "daily": 3},
    {"url": "https://kworld365.com",         "lang": "en", "theme": "K-POP",                "mode": "blog", "keywords_file": ".github/workflows/keywords_kworld.txt",          "wp_pass_env": "KWORLD365COM",        "daily": 5},
    {"url": "https://k-trip365.com",         "lang": "en", "theme": "Travel",               "mode": "blog", "keywords_file": ".github/workflows/keywords_ktrip.txt",           "wp_pass_env": "KTRIP365COM",         "daily": 3},
    {"url": "https://k-visa365.com",         "lang": "en", "theme": "Visa Guide",           "mode": "blog", "keywords_file": ".github/workflows/keywords_kvisa.txt",           "wp_pass_env": "KVISA365COM",         "daily": 3},
    {"url": "https://koreawedding365.com",   "lang": "en", "theme": "Wedding",              "mode": "blog", "keywords_file": ".github/workflows/keywords_kwedding.txt",        "wp_pass_env": "KOREAWEDDING365COM",  "daily": 3},
    {"url": "https://kstudy365.com",         "lang": "en", "theme": "Study in Korea",       "mode": "blog", "keywords_file": ".github/workflows/keywords_kstudy365.txt",       "wp_pass_env": "KSTUDY365COM",        "daily": 3},
    {"url": "https://studyinkorea365.com",   "lang": "en", "theme": "International Students","mode": "blog","keywords_file": ".github/workflows/keywords_studyinkorea365.txt",  "wp_pass_env": "STUDYINKOREA365COM",  "daily": 3},
    {"url": "https://jobkorea365.com",       "lang": "en", "theme": "Employment",           "mode": "blog", "keywords_file": ".github/workflows/keywords_jobkorea365.txt",     "wp_pass_env": "JOBKOREA365COM",      "daily": 3},
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
    "K-POP": [("Korea.net","https://www.korea.net"),("Korean Culture and Information Service","https://www.kocis.go.kr")],
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

# ★ RSS 크롤링 실패 시 사용할 다양한 뉴스 키워드 풀 (고정 반복 방지)
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
    """RSS 피드에서 최신 뉴스 제목을 가져오되, 실패 시 다양한 키워드 풀에서 랜덤 선택 (고정 반복 방지)"""
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
        print(f"  ⚠️ RSS 크롤링 실패, 키워드 풀에서 대체 선택: {e}")
    # ★ RSS 실패 시 매번 다른 키워드 선택 (고정 반복 방지)
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

def make_seo_prompt(keyword, theme, lang, mode="blog"):
    reporter      = random.choice(REPORTERS)
    tag_lang      = "영어로" if lang == "en" else "한국어로"
    title_style   = pick_title_style(lang)

    if mode == "news":
        return f"""
당신은 주요 일간지의 시니어 취재기자입니다.
주제: '{keyword}'에 대해 엄격한 신문기사체 기사를 작성하세요.

[필수 지침 — 구글 품질 가이드라인 강제 준수, 하나라도 빠지면 안 됨]
1. 문체: '했다', '밝혔다', '조사됐다'로 끝나는 6하원칙 기사체. 마크다운 금지.
2. 바이라인: 기사 맨 위에 '◇ {reporter}' 한 줄 삽입.
3. 분량: HTML(h2,h3,p,strong,ul,li)만 사용해 최소 1800자 이상.
4. ★ 통계/수치 강제: 본문 안에 구체적인 숫자·통계·비율·금액을 최소 3개 이상 명시적으로 포함 (예: "23% 증가", "약 150만 명", "2024년 대비 12.5%p 상승" 등 막연한 표현 금지, 반드시 숫자로 표기).
5. ★ 출처 강제: 통계 옆에 출처 기관명을 괄호로 명시 (예: "(통계청, 2026)", "(한국은행 발표)").
6. ★ 내부 링크 강제: 본문 중간에 자연스러운 문맥으로 최소 4개 이상의 내부 링크 자리를 위해 관련 주제를 언급 (시스템이 자동으로 링크 삽입할 수 있도록 키워드성 문구 포함).
7. ★ 외부 권위 링크 강제: 정부기관·통계청·연구기관 등 공신력 있는 기관명을 본문에 최소 3회 이상 언급.
8. E-E-A-T: 전문가 인터뷰 인용구 최소 1개 포함.
9. 구조: h2 최소 3개, 단락은 3~4문장 이내.
10. 제목 스타일: {title_style} / 출력 첫 줄에 'TITLE:' 로 시작하는 제목 한 줄.
11. ★ 메타 디스크립션: 본문 끝에 'META_DESC:' 로 시작, 정확히 130~140자 (한글 기준) 분량으로 작성. 너무 짧거나 길면 안 됨.
12. FAQ: META_DESC 다음 'FAQ_START' ~ 'FAQ_END' 블록에 Q:/A: 형식 3문항.
13. ★ 태그: FAQ_END 다음 'TAGS:' 로 시작, {TAG_COUNT}개 {tag_lang} 키워드. 각 태그는 최대 3단어(약 15자) 이내로 짧고 핵심적으로 작성. 첫 번째는 반드시 '{keyword}'.
출력 순서: TITLE → 본문HTML → META_DESC → FAQ_START~FAQ_END → TAGS
"""
    persona = "의학 박사" if "건강" in theme or "medical" in theme.lower() else "산업 분야 최고 전문 자문위원"
    return f"""
당신은 {persona}이자 15년 경력의 SEO 콘텐츠 마스터 프로라이터입니다.
주제: '{keyword}' ({theme}) / 언어: {lang}

[필수 지침 — 구글 애드센스 품질 평가 90점 이상, 아래 조건은 전부 강제 적용]
1. HTML 전용: h2,h3,p,ul,li,ol,strong,table,tr,td 태그만. 마크다운 금지.
2. 분량: 최소 1800자 이상, 깊이 있는 상세 내용.
3. 키워드: 첫 단락 문두에 '{keyword}' 배치, 전체 10회 이상 자연스럽게 삽입.
4. 구조: h2 최소 5개, h3 최소 4개, ul/li 리스트 3개 이상, 비교 table 1개 이상.
5. ★ 통계/수치 강제: 본문 안에 구체적인 숫자·통계·비율·금액·기간을 최소 3개 이상 명시적으로 포함. 막연한 표현("많은", "대부분") 대신 반드시 숫자로 표기 (예: "73%의 응답자", "평균 450,000원", "최근 5년간").
6. ★ 출처 강제: 통계 옆에 출처를 괄호로 명시 (예: "(KOSIS, 2026)", "(NIH 연구결과)", "(보건복지부 자료)").
7. ★ 내부 링크 강제: 본문 중간 자연스러운 문맥에서 관련 주제 최소 4곳 이상 언급하여 내부 링크 삽입이 가능하도록 구성.
8. ★ 외부 권위 링크 강제: 정부기관·학회·국제기구 등 공신력 있는 기관명을 본문에 최소 3회 이상 언급.
9. E-E-A-T: 전문가 인용 또는 실제 경험 기반 디테일(가격대, 기간, 절차 등) 최소 2곳 포함.
10. 단락: 3~4문장 이내로 짧게 끊기.
11. 제목 스타일: {title_style} / 출력 첫 줄에 'TITLE:' 로 시작하는 제목 한 줄.
12. ★ 메타 디스크립션: 본문 끝에 'META_DESC:' 로 시작, 정확히 130~140자(영문은 130~155자) 분량으로 작성. 너무 짧거나 길면 안 됨.
13. FAQ: META_DESC 다음 'FAQ_START' ~ 'FAQ_END' 블록에 Q:/A: 형식 3문항.
14. ★ 태그: FAQ_END 다음 'TAGS:' 로 시작, {TAG_COUNT}개 {tag_lang} 키워드. 각 태그는 최대 3단어(약 15자) 이내로 짧고 핵심적으로 작성 (긴 구문 금지). 첫 번째는 반드시 '{keyword}'.
출력 순서: TITLE → 본문HTML → META_DESC → FAQ_START~FAQ_END → TAGS
"""

# ============================================================
# 파싱
# ============================================================
def extract_meta_and_faq(text):
    """
    ★ 제목 추출 로직 강화:
    1순위: 'TITLE:' 줄 (정상 케이스)
    2순위: '**TITLE:**' 같은 마크다운 볼드로 감싼 경우도 인식
    3순위: TITLE: 자체가 없으면 본문 첫 <h1>...</h1> 내용을 제목으로 사용
    4순위: 그래도 없으면 빈 문자열 반환 (publish_post의 fallback이 처리)
    """
    import re as _re3
    title = ""; meta_desc = ""; faq_list = []
    lines = text.split("\n"); out_lines = []
    in_faq = False; cur_q = None
    for line in lines:
        s = line.strip()
        # ── TITLE 인식 강화: 'TITLE:', '**TITLE:**', '## TITLE:' 등 모두 처리 ──
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

    # ── ★ TITLE: 자체가 없었던 경우 → 본문의 첫 <h1> 태그에서 추출 ──
    if not title or len(title) < 8:
        body_text = "\n".join(out_lines)
        h1_match = _re3.search(r'<h1[^>]*>(.*?)</h1>', body_text, _re3.DOTALL | _re3.IGNORECASE)
        if h1_match:
            extracted = _re3.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
            extracted = extracted.strip('"').strip("'").strip("*").strip()
            if len(extracted) >= 8:
                title = extracted
                # 본문에서 중복되지 않도록 h1은 그대로 두되 제목으로도 사용
        # h1도 없으면 첫 번째 비어있지 않은 텍스트 줄을 시도 (최후 수단)
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
    """★ 태그를 강제로 최대 3단어/20자 이내로 자름 (긴 구문 태그 방지)"""
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

    # ★ 메인 키워드를 제외한 나머지 태그는 길이 강제 제한 (3단어/20자)
    kk = fallback_keyword.strip().lower()
    tags = [t for t in tags if t.strip().lower() != kk]
    tags = [_truncate_tag(t) for t in tags]
    tags.insert(0, fallback_keyword)  # 메인 키워드는 원문 그대로 유지

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

# ============================================================
# ★ 이미지 검색 (한국어 자동 번역 fallback 포함)
# ============================================================
def is_site_reachable(site_url, timeout=8):
    """★ 디버그 강화: 실패 원인을 정확히 출력 (DNS/타임아웃/연결거부/SSL 등 구분)"""
    try:
        r = requests.head(f"{site_url}/wp-json/", timeout=timeout, allow_redirects=True)
        # HTTP 상태코드가 뭐가 됐든(403, 404 포함) 일단 "서버에 도달은 했다"는 의미이므로 reachable로 간주
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
    """한국어 키워드 → 영어 번역 후 이미지 검색. Pixabay 우선, Pexels 보충."""
    has_korean = any('\uac00' <= c <= '\ud7a3' for c in keyword)
    q = keyword.encode('ascii','ignore').decode().strip()
    urls = []

    if has_korean or not q:
        en_query = translate_ko_to_en_for_image(keyword)
        print(f"  🔄 이미지 검색 번역: '{keyword}' → '{en_query}'")
        urls += get_images_from_pixabay(en_query, count)
        if len(urls) < count:
            urls += get_images_from_pexels(en_query, count - len(urls))
    else:
        urls += get_images_from_pixabay(q, count)
        if len(urls) < count:
            urls += get_images_from_pexels(q, count - len(urls))

    # 최종 fallback
    if len(urls) < count:
        fb = "Korea lifestyle people"
        urls += get_images_from_pixabay(fb, count - len(urls))
        if len(urls) < count:
            urls += get_images_from_pexels(fb, count - len(urls))

    return urls[:count]

def upload_to_wp_media(site_url, wp_pass, img_url, keyword, idx, alt_text=""):
    try:
        img_data = requests.get(img_url, timeout=10).content
        filename = f"seo-{keyword.encode('ascii','ignore').decode().replace(' ','-')}-{idx}.jpg"
        headers  = {"Content-Disposition": f"attachment; filename={filename}", "Content-Type": "image/jpeg"}
        res = requests.post(f"{site_url}/wp-json/wp/v2/media", data=img_data, headers=headers, auth=(WP_USER, wp_pass), timeout=20)
        if res.status_code == 201:
            media_id = res.json().get("id")
            if media_id and alt_text:
                try:
                    requests.post(f"{site_url}/wp-json/wp/v2/media/{media_id}",
                                  json={"alt_text": alt_text, "caption": alt_text},
                                  auth=(WP_USER, wp_pass), timeout=10)
                except: pass
            return media_id
    except: pass
    return None

# ============================================================
# 링크 빌더
# ============================================================
def build_spider_web_links(keyword, current_url, lang, link_count=6):
    others   = [s for s in SITES_CONFIG if s['url'] != current_url]
    selected = random.sample(others, k=min(link_count, len(others)))
    html = "<div style='margin-top:30px;background:#f9f9f9;padding:15px;border-left:4px solid #0066cc;'>"
    html += f"<h4>🔗 {keyword} 연관 인기 가이드</h4><ul style='list-style:none;padding-left:0;'>"
    for s in selected:
        anchor = f"✨ [{s['theme']}] {keyword} 관련 연관 분석" if lang=='ko' else f"✨ {keyword} Extensive Industry Report"
        html += f"<li style='margin-bottom:8px;'><a href='{s['url']}/?s={requests.utils.quote(keyword)}' target='_blank' rel='noopener'>{anchor}</a></li>"
    html += "</ul></div>"
    return html

def build_related_search_links(keyword, lang):
    words = [f"{keyword} 효능",f"{keyword} 부작용",f"{keyword} 가격",f"{keyword} 추천",f"{keyword} 비교"] if lang=='ko' \
            else [f"{keyword} cost",f"{keyword} review",f"{keyword} comparison",f"{keyword} guide",f"best {keyword}"]
    html  = "<div style='margin-top:20px;border-top:1px dashed #ccc;padding-top:15px;'><strong>💡 연관 검색어: </strong>"
    links = [f"<a href='?s={requests.utils.quote(w)}' style='color:#555;text-decoration:underline;margin-right:10px;'>#{w}</a>" for w in words]
    return html + ", ".join(links) + "</div>"

def build_external_authority_links(theme, lang, link_count=4):
    pool = EXTERNAL_AUTHORITY_LINKS.get(theme) or \
           EXTERNAL_AUTHORITY_LINKS.get("default_en" if lang=="en" else "한국 뉴스", [])
    if not pool: return ""
    selected = random.sample(pool, k=min(link_count, len(pool)))
    label    = "📚 참고자료 및 공식 출처" if lang=="ko" else "📚 References & Official Sources"
    html  = f"<div style='margin-top:25px;background:#eef5ff;padding:15px;border-left:4px solid #1a73e8;'><h4>{label}</h4><ul style='padding-left:20px;'>"
    for name, url in selected:
        html += f"<li><a href='{url}' target='_blank' rel='nofollow noopener'>{name}</a></li>"
    return html + "</ul></div>"

def build_faq_html_and_schema(faq_list, lang):
    if not faq_list: return "", ""
    label = "❓ 자주 묻는 질문" if lang=="ko" else "❓ Frequently Asked Questions"
    html  = f"<div style='margin-top:30px;'><h2>{label}</h2>"
    schema_items = []
    for q, a in faq_list:
        html += f"<h3>{q}</h3><p>{a}</p>"
        qe = q.replace('"','\\"'); ae = a.replace('"','\\"')
        schema_items.append('{"@type":"Question","name":"%s","acceptedAnswer":{"@type":"Answer","text":"%s"}}' % (qe,ae))
    html += "</div>"
    schema = '<script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[%s]}</script>' % ",".join(schema_items)
    return html, schema

# ============================================================
# ★ SEO 점수 계산 (개선)
# ============================================================
def estimate_seo_score(keyword, title, plain_len, meta_desc, img_count, faq_count, tag_count,
                       rank_math_applied, internal_links=0, external_links=0, stat_count=0):
    """
    ★ 강화된 SEO 점수 (100점 만점)
    - 제목 키워드 포함:        10점
    - 본문 길이:               15점
    - 메타 디스크립션(130~140자 정확히): 15점
    - 이미지 2~3장:            15점
    - 내부 링크 4개 이상:       10점  ★ 신규
    - 외부 링크 3개 이상:       10점  ★ 신규
    - 통계/수치 3개 이상:       10점  ★ 신규
    - FAQ:                     5점
    - 태그:                    5점
    - Rank Math 반영:          5점
    """
    score = 0
    if keyword.lower() in title.lower():
        score += 10
    if plain_len >= MIN_BODY_LENGTH:
        score += 15
    elif plain_len >= 1200:
        score += 9
    elif plain_len >= 800:
        score += 4

    # ★ 메타 디스크립션: 130~140자(한글) / 130~155자(영문) 정확히 맞아야 만점
    if meta_desc:
        mlen = len(meta_desc)
        if 130 <= mlen <= 155:
            score += 15
        elif 100 <= mlen <= 170:
            score += 9
        else:
            score += 4

    score += min(15, img_count * 5)  # 이미지 장당 5점, 최대 3장

    # ★ 내부 링크 (4개 이상 만점)
    score += min(10, int(10 * internal_links / 4)) if internal_links else 0

    # ★ 외부 링크 (3개 이상 만점)
    score += min(10, int(10 * external_links / 3)) if external_links else 0

    # ★ 통계/수치 포함 여부 (본문 내 숫자 패턴 개수 기반, 3개 이상 만점)
    score += min(10, int(10 * stat_count / 3)) if stat_count else 0

    score += min(5, faq_count * 2)
    if TAG_COUNT > 0:
        score += min(5, int(5 * tag_count / TAG_COUNT))
    if rank_math_applied:
        score += 5

    return min(100, score)

def count_statistics_in_body(html_body: str) -> int:
    """본문에서 통계/수치 패턴 개수를 추정 (숫자+%, 숫자+명/원/년 등)"""
    import re as _re4
    plain = _re4.sub(r'<[^>]+>', ' ', html_body)
    patterns = [
        r'\d+[.,]?\d*\s*%',                    # 23%, 12.5%
        r'\d+[.,]?\d*\s*(명|개|원|건|배|회)',     # 150만 명, 3배
        r'\d{4}년',                               # 2026년
        r'\d+[.,]?\d*\s*(percent|million|billion|times)',  # 영문 통계
    ]
    count = 0
    for p in patterns:
        count += len(_re4.findall(p, plain))
    return count

# ============================================================
# ★ 로그 및 구글시트 전송 (컬럼 완전 개편 + 3회 재시도)
# 컬럼 순서: 기록시각 | 사이트 | 키워드 | 제목 | 모델 | 이미지수 | 이미지출처 | 글자수 | SEO점수 | 태그수 | RankMath | 상태 | 회차 | URL | 오류메시지
# ============================================================
RUN_LOG = []

def record_result(site_url, title, keyword="", model="", tag_count=0,
                   img_count=0, img_source="", plain_len=0,
                   internal_links=0, external_links=0, faq_count=0,
                   rank_math_applied=False, seo_score=0,
                   status="success", post_url="", error_msg=""):
    RUN_LOG.append({
        "기록시각":   now_kst().strftime("%Y-%m-%d %H:%M:%S"),
        "사이트":     site_url,
        "키워드":     keyword,
        "제목":       title,
        "모델":       model,
        "SEO점수":    seo_score,
        "글자수":     plain_len,
        "이미지수":   img_count,
        "이미지출처": img_source,
        "내부링크수": internal_links,
        "외부링크수": external_links,
        "태그수":     tag_count,
        "FAQ수":      faq_count,
        "RankMath":   "✅ 적용" if rank_math_applied else "❌ 미적용",
        "상태":       status,
        "회차":       RUN_SLOT,
        "URL":        post_url,
        "오류메시지": error_msg,
    })

def flush_log_to_google_sheet():
    """★ 구글시트 전송 — 3회 재시도, 컬럼 완전 정렬"""
    if not SHEETS_WEBHOOK:
        print("⚠️ SHEETS_WEBHOOK 미설정 — 로그 전송 스킵")
        return
    if not RUN_LOG:
        print("ℹ️ 이번 회차에 기록할 로그가 없습니다.")
        return

    success_count = sum(1 for r in RUN_LOG if r["상태"] == "success")
    fail_count    = len(RUN_LOG) - success_count

    payload = {
        "type":     "summary",
        "run_slot": RUN_SLOT,
        "run_time": now_kst().strftime("%Y-%m-%d %H:%M:%S"),
        "total":    len(RUN_LOG),
        "success":  success_count,
        "fail":     fail_count,
        "columns":  ["기록시각","회차","사이트","키워드","제목","모델","SEO점수","글자수","이미지수","이미지출처","내부링크수","외부링크수","태그수","FAQ수","RankMath","상태","URL","오류메시지"],
        "entries":  RUN_LOG,
    }

    last_error = None
    for attempt in range(1, 4):
        try:
            res = requests.post(SHEETS_WEBHOOK, json=payload, timeout=20)
            if res.status_code in (200, 201, 302):
                print(f"📊 구글 스프레드시트 전송 완료: 총 {len(RUN_LOG)}건 (성공 {success_count} / 실패 {fail_count})")
                return
            else:
                last_error = f"HTTP {res.status_code}: {res.text[:200]}"
                print(f"  ⚠️ 시트 전송 시도 {attempt}/3 — 응답코드 {res.status_code}")
        except Exception as e:
            last_error = str(e)
            print(f"  ⚠️ 시트 전송 시도 {attempt}/3 실패: {e}")
        if attempt < 3:
            time.sleep(5 * attempt)
    print(f"  ❌ 구글 스프레드시트 최종 전송 실패: {last_error}")

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
            res = gemini_client.models.generate_content(model=model, contents=prompt)
            if res and res.text: return res.text
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
            print(f"  🔄 {GEMINI_MODEL_PRIMARY} 한도 소진 → {GEMINI_MODEL_FALLBACK} 전환")
            _gemini_fallback_active = True
            GEMINI_MODEL = GEMINI_MODEL_FALLBACK
            try:
                res = gemini_client.models.generate_content(model=GEMINI_MODEL_FALLBACK, contents=prompt)
                if res and res.text: return res.text
            except Exception as e2:
                last_exception = e2

    if last_exception: raise last_exception
    return ""

# ============================================================
# 태그 ID 변환
# ============================================================
def get_or_create_tag_ids(site_url, wp_pass, tag_names):
    tag_ids = []
    for name in tag_names:
        try:
            sr = requests.get(f"{site_url}/wp-json/wp/v2/tags", params={"search": name, "per_page": 5},
                              auth=(WP_USER, wp_pass), timeout=10)
            existing = None
            if sr.status_code == 200:
                for t in sr.json():
                    if t.get("name","").strip().lower() == name.strip().lower():
                        existing = t; break
            if existing: tag_ids.append(existing["id"]); continue
            cr = requests.post(f"{site_url}/wp-json/wp/v2/tags", json={"name": name},
                               auth=(WP_USER, wp_pass), timeout=10)
            if cr.status_code in (200,201):
                tag_ids.append(cr.json()["id"])
            elif cr.status_code == 400:
                d = cr.json()
                eid = d.get("data",{}).get("term_id") or d.get("term_id")
                if eid: tag_ids.append(eid)
        except Exception as e:
            print(f"  ⚠️ 태그 처리 실패 ({name}): {e}")
    return tag_ids

# ============================================================
# ★ Rank Math PATCH 재시도
# ============================================================
def try_register_and_patch_rank_math(site_url, wp_pass, post_id, rank_math_meta):
    try:
        pr = requests.post(f"{site_url}/wp-json/wp/v2/posts/{post_id}",
                           json={"meta": rank_math_meta},
                           auth=(WP_USER, wp_pass), timeout=15)
        if pr.status_code == 200:
            pm = pr.json().get("meta", {}) or {}
            if pm.get("rank_math_focus_keyword") == rank_math_meta.get("rank_math_focus_keyword"):
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
        print(f"⏭️  {site['url']} — Secret '{site['wp_pass_env']}' 없음, 스킵")
        record_result(site['url'], f"(skip) {keyword}", keyword=keyword,
                      status="skip_no_password", error_msg=f"Secret {site['wp_pass_env']} not found")
        return False

    if not is_site_reachable(site['url']):
        time.sleep(5)
        if not is_site_reachable(site['url']):
            print(f"⏭️  {site['url']} — 사이트 응답 없음, 스킵")
            record_result(site['url'], f"(skip) {keyword}", keyword=keyword,
                          status="skip_unreachable", error_msg="site unreachable")
            return False

    prompt = make_seo_prompt(keyword, theme, lang, mode)
    try:
        raw_text   = generate_with_retry(prompt)
        used_model = GEMINI_MODEL
    except Exception as e:
        print(f"  ❌ Gemini 생성 최종 실패 ({site['url']}): {e}")
        record_result(site['url'], keyword, keyword=keyword, model=GEMINI_MODEL,
                      status="fail_gemini", error_msg=str(e)[:200])
        return False

    if len(raw_text) < 300:
        print(f"  ⚠️ 본문 너무 짧음, 스킵")
        record_result(site['url'], keyword, keyword=keyword, model=used_model,
                      status="fail_short_body", error_msg="raw_text < 300 chars")
        return False

    body_with_tags, gemini_title, meta_desc, faq_list = extract_meta_and_faq(raw_text)
    article_body,   tag_names                          = extract_tags_from_article(body_with_tags, keyword, theme=theme, lang=lang)

    plain_len = len(BeautifulSoup(article_body, "html.parser").get_text())
    if plain_len < MIN_BODY_LENGTH:
        print(f"  ⚠️ 본문 글자수 부족({plain_len}자 < {MIN_BODY_LENGTH}자) — 발행 진행")

    if not meta_desc:
        plain_for_meta = BeautifulSoup(article_body, "html.parser").get_text()
        meta_desc = (plain_for_meta[:137] + "...") if len(plain_for_meta) > 140 else plain_for_meta
    # ★ 메타 디스크립션 길이 강제 보정: 130~140자(한글) 범위 벗어나면 자르기/패딩
    if len(meta_desc) > 155:
        meta_desc = meta_desc[:152] + "..."

    # ★ 이미지 검색 (한국어 자동 번역)
    img_urls  = get_multiple_images(keyword, 3)
    media_ids = []; img_source = "none"
    for idx, url in enumerate(img_urls):
        alt = f"{keyword} - {theme}" if lang != 'ko' else f"{keyword} 관련 이미지"
        mid = upload_to_wp_media(site['url'], wp_pass, url, keyword, idx, alt_text=alt)
        if mid:
            media_ids.append(mid)
            if img_source == "none": img_source = "pixabay/pexels"
    if not media_ids:
        print(f"  ℹ️ 이미지 0장 — 이미지 없이 발행 진행")
    else:
        print(f"  🖼️ 이미지 {len(media_ids)}장 업로드 완료")

    tag_ids = get_or_create_tag_ids(site['url'], wp_pass, tag_names)
    if not tag_ids and tag_names:
        print(f"  ⚠️ 태그 ID 변환 실패, 재시도 1회...")
        time.sleep(3)
        tag_ids = get_or_create_tag_ids(site['url'], wp_pass, tag_names)
    print(f"  🏷️ 태그 {len(tag_ids)}/{len(tag_names)}개 확보 (메인: {tag_names[0]})")

    faq_html, faq_schema = build_faq_html_and_schema(faq_list, lang)
    article_body += build_spider_web_links(keyword, site['url'], lang)
    article_body += build_related_search_links(keyword, lang)
    article_body += build_external_authority_links(theme, lang)
    if faq_html:   article_body += faq_html
    if faq_schema: article_body += faq_schema

    if gemini_title and len(gemini_title) >= 8:
        title = gemini_title
        if keyword.lower() not in title.lower(): title = f"{title} ({keyword})"
    else:
        title = f"[속보] {keyword}" if (lang=='ko' and mode=='news') else \
                (f"{keyword} 정보 완벽 정리" if lang=='ko' else f"The Essential Guide to {keyword}")

    focus_keywords = [keyword] + [t for t in tag_names[1:5] if t.lower() != keyword.lower()]
    rank_math_meta = {
        "rank_math_focus_keyword": ",".join(focus_keywords),
        "rank_math_description":   meta_desc,
    }

    payload = {
        "title": title, "content": article_body, "excerpt": meta_desc,
        "categories": category_ids, "status": "publish", "meta": rank_math_meta,
    }
    if tag_ids:   payload["tags"]           = tag_ids
    if media_ids: payload["featured_media"] = media_ids[0]

    res_post = None; last_post_exception = None
    for post_attempt in range(1, 4):
        try:
            res_post = requests.post(f"{site['url']}/wp-json/wp/v2/posts", json=payload,
                                     auth=(WP_USER, wp_pass), timeout=25)
            break
        except Exception as e:
            last_post_exception = e
            err_str = str(e)
            is_transient = any(x in err_str for x in ["Name or service not known","Temporary failure",
                                                        "NewConnectionError","ConnectionError","Timeout","timed out"])
            if post_attempt < 3 and is_transient:
                wait = 8 * post_attempt
                print(f"  ⚠️ 포스팅 요청 실패 (시도 {post_attempt}/3): {e} — {wait}초 대기")
                time.sleep(wait)
            else:
                print(f"  ❌ 포스팅 최종 실패 ({site['url']}): {e}")
                record_result(site['url'], title, keyword=keyword, model=used_model,
                              tag_count=len(tag_ids), img_count=len(media_ids), img_source=img_source,
                              plain_len=plain_len, seo_score=0, status="fail_request", error_msg=str(e)[:200])
                return False

    if res_post is None:
        record_result(site['url'], title, keyword=keyword, model=used_model,
                      status="fail_request", error_msg=str(last_post_exception)[:200])
        return False

    if res_post.status_code == 403 and "Checking your browser" in res_post.text:
        print(f"  ⚠️ WAF 403 — 15초 대기 후 1회 재시도")
        time.sleep(15)
        try:
            res_post = requests.post(f"{site['url']}/wp-json/wp/v2/posts", json=payload,
                                     auth=(WP_USER, wp_pass), timeout=25)
        except Exception as e:
            print(f"  ❌ 재시도 실패: {e}")
            record_result(site['url'], title, keyword=keyword, model=used_model,
                          status="fail_request", error_msg=str(e)[:200])
            return False

    if res_post.status_code == 201:
        post_data     = res_post.json()
        post_id       = post_data.get("id")
        post_url      = post_data.get("link", "")
        returned_meta = post_data.get("meta", {}) or {}

        rank_math_applied = (returned_meta.get("rank_math_focus_keyword") == rank_math_meta["rank_math_focus_keyword"])
        if not rank_math_applied and post_id:
            rank_math_applied = try_register_and_patch_rank_math(site['url'], wp_pass, post_id, rank_math_meta)

        # ★ 내부/외부 링크 수 계산
        import re as _re
        _pat = _re.compile(r'href=[^>]*https?://([^"\' >]+)')
        all_links      = _pat.findall(article_body)
        _network_hosts = set(s['url'].replace('https://','').rstrip('/') for s in SITES_CONFIG)
        int_link_count = sum(1 for h in all_links if any(h.startswith(nh) for nh in _network_hosts))
        ext_link_count = sum(1 for h in all_links if not any(h.startswith(nh) for nh in _network_hosts))

        stat_count = count_statistics_in_body(article_body)
        seo_score = estimate_seo_score(keyword, title, plain_len, meta_desc,
                                       img_count=len(media_ids), faq_count=len(faq_list),
                                       tag_count=len(tag_ids), rank_math_applied=rank_math_applied,
                                       internal_links=int_link_count, external_links=ext_link_count,
                                       stat_count=stat_count)

        rm_label = "Rank Math ✅" if rank_math_applied else "Rank Math ❌"
        print(f"✅ {site['url']} 발행 완료 — 태그 {len(tag_ids)}개, 이미지 {len(media_ids)}장, "
              f"FAQ {len(faq_list)}개, {rm_label}, SEO {seo_score}점, 모델:{used_model}")
        print(f"   제목: {title}")

        if not rank_math_applied:
            print(f"  ⚠️ [진단] Rank Math 미반영 → functions.php에 register_post_meta 코드 추가 필요")

        record_result(
            site['url'], title, keyword=keyword, model=used_model,
            tag_count=len(tag_ids), img_count=len(media_ids), img_source=img_source,
            plain_len=plain_len, internal_links=int_link_count,
            external_links=ext_link_count, faq_count=len(faq_list),
            rank_math_applied=rank_math_applied,
            seo_score=seo_score, status="success", post_url=post_url
        )
        return True
    else:
        err = res_post.text[:300]
        print(f"❌ {site['url']} 발행 실패 (HTTP {res_post.status_code}): {err}")
        if res_post.status_code == 403:
            print(f"  🔍 응답 헤더: {dict(res_post.headers)}")
        record_result(
            site['url'], title, keyword=keyword, model=used_model,
            tag_count=len(tag_ids), img_count=len(media_ids), img_source=img_source,
            plain_len=plain_len, seo_score=0,
            status=f"fail_{res_post.status_code}", error_msg=err
        )
        return False

# ============================================================
# 작업 큐 빌드 및 실행
# ============================================================
def build_job_queue():
    queue = []
    for site in SITES_CONFIG:
        count = get_posts_for_this_slot(site, RUN_SLOT)
        if count <= 0: continue
        for _ in range(count):
            if site["mode"] == "news" and site["url"] == "https://koreanews365.com":
                ref_title, _ = crawl_rss_news()
                keyword       = ref_title
                categories    = [1]
            else:
                keyword    = load_keyword(site["keywords_file"], site["theme"])
                categories = [random.choice(HEALTH_CATEGORIES)] if site["url"] == "https://k-health365.com" else [1]
            queue.append({"site": site, "keyword": keyword, "theme": site["theme"],
                          "lang": site["lang"], "mode": site["mode"], "categories": categories})
    random.shuffle(queue)
    return queue

def run():
    print(f"🚀 [RUN_SLOT {RUN_SLOT}/3] 22개 사이트 메가 오토포스팅 시작 (모델: {GEMINI_MODEL}, 애드센스90점 기준)")
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
