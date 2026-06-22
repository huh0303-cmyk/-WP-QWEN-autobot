#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
autopost_mega.py — 27개 사이트 메가 오토포스팅 봇 (최종 통합본)
업데이트: 2026-06
  ✅ 27개 사이트 완전 반영 (ki-korea.com, krealestate365.com, kieca-korea.org, ksa-korea.org, sis-korea.com 추가)
  ✅ koreanews365.com / theseouljournal.com 완전 분리 (카테고리·기자·키워드 독립)
  ✅ 한국/영문 기자 10명 각각 → 완전 랜덤 바이라인
  ✅ 무관 내부링크 제거 → 테마별 연관 링크만
  ✅ 강화 SEO 프롬프트 엔진 (모바일 가독성, 통계 강제, 출처 강제, 태그 무결성)
  ✅ 기사 중복 방지 (koreanews365 ↔ theseouljournal 키워드 풀 완전 분리)
  ✅ 이미지 3단계 fallback (Pixabay → Pexels → theme-aware 영어 변환)
  ✅ 구글시트 18컬럼 로깅 / Rank Math 메타 자동 주입
"""

import os, sys, time, random, re, json, hashlib
import requests
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from google import genai

# ============================================================
# 기본 설정
# ============================================================
KST = timezone(timedelta(hours=9))

def now_kst():
    return datetime.now(KST)

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
PIXABAY_KEY     = os.getenv("PIXABAY_KEY")
PEXELS_KEY      = os.getenv("PEXELS_KEY")
SHEETS_WEBHOOK  = os.getenv("SHEETS_WEBHOOK")
WP_USER         = "huh0303@gmail.com"

RUN_SLOT              = int(os.getenv("RUN_SLOT", "1"))
SLEEP_BETWEEN_POSTS   = float(os.getenv("SLEEP_BETWEEN_POSTS", "6"))

gemini_client          = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL_PRIMARY   = "gemini-2.5-flash"
GEMINI_MODEL_FALLBACK  = "gemini-2.5-flash-lite"
GEMINI_MODEL           = GEMINI_MODEL_PRIMARY
_gemini_fallback_active = False

TAG_COUNT        = 12
MIN_BODY_LENGTH  = 1800

# ============================================================
# ★ 기자 명단 — 한국어 사이트(koreanews365) / 영문 사이트(seouljournal + 기타) 완전 분리
# ============================================================
REPORTERS_KO = [
    "김민준 기자 (minjun@koreanews365.com)",
    "이서연 기자 (seoyeon@koreanews365.com)",
    "박현우 기자 (hyunwoo@koreanews365.com)",
    "최지아 기자 (jia@koreanews365.com)",
    "정재희 기자 (jaehee@koreanews365.com)",
    "윤성호 기자 (sungho@koreanews365.com)",
    "강다은 기자 (daeun@koreanews365.com)",
    "임준혁 기자 (junhyuk@koreanews365.com)",
    "한소희 기자 (sohee@koreanews365.com)",
    "오태영 기자 (taeyoung@koreanews365.com)",
]

REPORTERS_EN = [
    "James Wilson (james@theseouljournal.com)",
    "Emily Anderson (emily@theseouljournal.com)",
    "Michael Chang (michael@theseouljournal.com)",
    "Sarah Jenkins (sarah@theseouljournal.com)",
    "David Miller (david@theseouljournal.com)",
    "Jessica Park (jessica@theseouljournal.com)",
    "Robert Kim (robert@theseouljournal.com)",
    "Laura Chen (laura@theseouljournal.com)",
    "Daniel Lee (daniel@theseouljournal.com)",
    "Rachel Moon (rachel@theseouljournal.com)",
]

def pick_reporter(lang: str) -> str:
    return random.choice(REPORTERS_KO if lang == "ko" else REPORTERS_EN)

# ============================================================
# ★ 한국어 → 영어 이미지 검색 번역 매핑 (테마-어웨어 fallback 포함)
# ============================================================
KO_TO_EN_IMAGE = {
    # 복합 패턴 (긴 것 우선)
    "대한민국 최신 경제 및 사회 변화 트렌드 분석": "South Korea economy society trend analysis business",
    "혈당스파이크 줄이는":   "blood sugar spike reduction tips",
    "콜레스테롤 낮추는":     "cholesterol lowering heart healthy food",
    "혈압 낮추는":           "blood pressure lowering hypertension",
    "고혈압 낮추는":         "hypertension blood pressure healthy food",
    "지방간에 좋은":         "fatty liver healthy food nutrition",
    "면역력 높이는":         "immune system boosting health supplements",
    "불면증 극복":           "insomnia cure sleep improvement",
    "비타민D 부족":          "vitamin D deficiency symptoms sun",
    "전립선비대증 관리":     "prostate BPH management men health",
    "만성피로증후군":        "chronic fatigue syndrome treatment",
    "갑상선기능저하":        "hypothyroidism thyroid disorder",
    "역류성식도염":          "acid reflux GERD esophagus",
    "과민성대장":            "irritable bowel IBS syndrome",
    "허리디스크":            "herniated lumbar disc back pain",
    "목디스크":              "cervical disc neck pain",
    "원형탈모":              "alopecia areata hair loss treatment",
    "공황장애":              "panic disorder anxiety mental health",
    # 단어 단위 — 건강
    "고혈압":       "high blood pressure hypertension",
    "혈당스파이크": "blood sugar spike glucose",
    "혈당":         "blood glucose sugar control",
    "혈압":         "blood pressure heart",
    "당뇨병":       "diabetes insulin treatment",
    "당뇨":         "diabetes blood sugar",
    "콜레스테롤":   "cholesterol heart health",
    "중성지방":     "triglycerides blood lipid",
    "지방간":       "fatty liver hepatic",
    "간수치":       "liver enzymes blood test",
    "간염":         "hepatitis liver",
    "요로결석":     "kidney stone urinary pain",
    "담석증":       "gallstone bile duct",
    "크론병":       "Crohn disease intestinal",
    "소화불량":     "indigestion digestive stomach",
    "변비":         "constipation bowel health",
    "비만":         "obesity weight management",
    "체질량지수":   "BMI body mass index obesity",
    "다이어트":     "diet weight loss nutrition",
    "갑상선":       "thyroid gland hormone",
    "면역력":       "immune system boost health",
    "자가면역":     "autoimmune disease immunity",
    "류마티스":     "rheumatoid arthritis joint",
    "관절":         "joint pain arthritis",
    "무릎":         "knee pain orthopedic",
    "허리":         "back pain spine lumbar",
    "디스크":       "spinal disc herniated",
    "골다공증":     "osteoporosis bone density",
    "탈모":         "hair loss alopecia treatment",
    "두피":         "scalp treatment hair care",
    "아토피":       "atopic dermatitis eczema skin",
    "여드름":       "acne skin treatment",
    "피부":         "skin care dermatology beauty",
    "불면증":       "insomnia sleep disorder",
    "수면장애":     "sleep disorder insomnia",
    "수면":         "sleep health rest",
    "만성피로":     "chronic fatigue tiredness",
    "번아웃":       "burnout mental exhaustion",
    "피로":         "fatigue tiredness",
    "스트레스":     "stress management mental health",
    "우울증":       "depression mental health therapy",
    "치매":         "dementia Alzheimer brain",
    "두통":         "headache migraine pain",
    "편두통":       "migraine headache relief",
    "이명":         "tinnitus ear ringing",
    "안구건조":     "dry eye syndrome relief",
    "비염":         "rhinitis allergy nasal",
    "천식":         "asthma respiratory",
    "통풍":         "gout uric acid joint",
    "요산":         "uric acid gout",
    "전립선":       "prostate health men",
    "갱년기":       "menopause hormonal women",
    "생리불순":     "menstrual irregularity women",
    "영양제":       "supplements vitamins health",
    "비타민D":      "vitamin D supplement sunshine",
    "비타민":       "vitamins minerals supplements",
    "오메가3":      "omega-3 fish oil supplement",
    "프로바이오틱스": "probiotics gut health",
    "콜라겐":       "collagen skin beauty anti-aging",
    "단백질":       "protein muscle fitness",
    "자가진단":     "self diagnosis medical check",
    "초기증상":     "early symptoms warning signs",
    "예방":         "prevention healthcare wellness",
    "치료":         "medical treatment therapy",
    "증상":         "symptoms medical signs",
    "운동":         "exercise fitness workout",
    "음식":         "healthy food nutrition",
    "영양":         "nutrition food wellness",
    "암":           "cancer treatment medical",
    "심장":         "heart cardiovascular health",
    "뇌":           "brain health neurology",
    "폐":           "lung respiratory health",
    "신장":         "kidney health renal",
    "간":           "liver health medical",
    # 뉴스/경제/투자/부동산
    "대한민국":     "South Korea",
    "한국":         "South Korea",
    "경제":         "South Korea economy finance business",
    "사회":         "Korean society community people",
    "트렌드":       "trend analysis modern Korea",
    "분석":         "analysis data report chart",
    "최신":         "latest current news 2026",
    "정치":         "Korean politics government",
    "부동산":       "Korea real estate property apartment",
    "금융":         "Korea finance banking money",
    "물가":         "inflation price consumer Korea",
    "취업":         "employment jobs career Korea",
    "교육":         "education school Korea learning",
    "기술":         "technology innovation Korea",
    "문화":         "Korean culture lifestyle traditional",
    "서울":         "Seoul Korea cityscape urban",
    "여행":         "Korea travel tourism tourist",
    "투자":         "Korea investment stock market",
    "주식":         "stock market investment trading",
    "펀드":         "fund investment portfolio",
    "암호화폐":     "cryptocurrency Bitcoin Korea",
    "비트코인":     "Bitcoin cryptocurrency digital",
    "보험":         "insurance policy Korea",
    "세금":         "tax law Korea finance",
    "법률":         "law legal Korea",
    "웨딩":         "wedding ceremony Korea romantic",
    "결혼":         "wedding marriage Korea",
    "케이팝":       "K-pop idol concert stage",
    "아이돌":       "K-pop idol music performance",
    "뷰티":         "Korean beauty skincare cosmetic",
    "성형":         "Korea plastic surgery beauty",
    # 동사/형용사
    "낮추는":   "lowering reduction tips",
    "높이는":   "boosting increase guide",
    "줄이는":   "reducing control management",
    "좋은":     "healthy beneficial best",
    "극복":     "overcome improve solution",
    "관리":     "management care lifestyle",
    "부족":     "deficiency lack symptoms",
    "원인":     "cause reason why",
    "방법":     "method tips guide",
    "효과":     "effect benefit result",
    "추천":     "recommended best top",
    "종류":     "types kinds overview",
    "부작용":   "side effects risks warning",
    "복용법":   "dosage how to take",
    "개선":     "improvement recovery",
}

# 테마별 이미지 fallback 매핑
THEME_IMAGE_FALLBACK = {
    "건강과 의학":          "medical health treatment Korea doctor",
    "한국 뉴스":            "South Korea news media politics economy",
    "Seoul Lifestyle":      "Seoul Korea lifestyle urban coffee shop",
    "K-POP":                "K-pop idol music concert stage",
    "K-Beauty":             "Korean skincare beauty cosmetic product",
    "K-Beauty Reviews":     "Korean beauty product review cosmetic",
    "Travel":               "Korea travel tourism landscape nature",
    "Finance":              "Korea finance investment banking charts",
    "Investment":           "investment stock market South Korea",
    "Insurance":            "insurance policy document Korea finance",
    "Tax and Law":          "Korea law legal tax document",
    "Crypto":               "cryptocurrency bitcoin blockchain digital",
    "Technology":           "Korea technology innovation AI startup",
    "Study in Korea":       "Korea university campus student study",
    "International Students": "international student Korea campus",
    "Visa Guide":           "Korea visa passport document travel",
    "Korea Medical Tourism": "Korea medical hospital tourism beauty",
    "Employment":           "Korea employment job career office",
    "Jobs in Korea":        "Korea job work employment career",
    "Recruitment":          "recruitment hiring interview job Korea",
    "Wedding":              "Korea wedding ceremony elegant romantic",
    "Korea Culture":        "Korean culture tradition festival people",
    "Korea Real Estate":    "Korea apartment real estate property Seoul",
    "Korea Investment":     "Korea investment finance business growth",
    "default":              "South Korea business modern city",
}

def translate_ko_to_en_for_image(keyword: str, theme: str = "") -> str:
    result = keyword
    for ko, en in sorted(KO_TO_EN_IMAGE.items(), key=lambda x: -len(x[0])):
        result = result.replace(ko, en)
    # 한글이 여전히 남아있으면 테마 기반 fallback
    if any('\uac00' <= c <= '\ud7a3' for c in result):
        return THEME_IMAGE_FALLBACK.get(theme, THEME_IMAGE_FALLBACK["default"])
    result = re.sub(r'\s+', ' ', result).strip()
    return result[:80]

# ============================================================
# ★ 27개 사이트 설정 (완전 업데이트)
# ============================================================
SITES_CONFIG = [
    # ── 건강 (핵심, 승인 완료) ──────────────────────────────
    {"url": "https://k-health365.com",
     "lang": "ko", "theme": "건강과 의학", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_khealth.txt",
     "wp_pass_env": "KHEALTH365COM", "daily": 15},

    # ── 의료관광 ─────────────────────────────────────────────
    {"url": "https://koreamedicaltour.com",
     "lang": "en", "theme": "Korea Medical Tourism", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_medicaltour.txt",
     "wp_pass_env": "KOREAMEDICALTOURCOM", "daily": 3},

    # ── 투자/금융 ────────────────────────────────────────────
    {"url": "https://koreainvest365.com",
     "lang": "en", "theme": "Investment", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kinvest.txt",
     "wp_pass_env": "KOREAINVEST365COM", "daily": 3},

    {"url": "https://ki-korea.com",
     "lang": "ko", "theme": "Korea Investment", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kikorea.txt",
     "wp_pass_env": "KIKOREACOM", "daily": 3},

    {"url": "https://koreainsurance365.com",
     "lang": "en", "theme": "Insurance", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kinsurance.txt",
     "wp_pass_env": "KOREAINSURANCE365COM", "daily": 3},

    {"url": "https://kfinance365.com",
     "lang": "en", "theme": "Finance", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kfinance.txt",
     "wp_pass_env": "KFINANCE365COM", "daily": 3},

    {"url": "https://koreataxnlaw.com",
     "lang": "en", "theme": "Tax and Law", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_ktax.txt",
     "wp_pass_env": "KOREATAXNLAWCOM", "daily": 3},

    {"url": "https://koreacrypto365.com",
     "lang": "en", "theme": "Crypto", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kcrypto.txt",
     "wp_pass_env": "KOREACRYPTO365COM", "daily": 3},

    # ── 부동산 ───────────────────────────────────────────────
    {"url": "https://krealestate365.com",
     "lang": "ko", "theme": "Korea Real Estate", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_krealestate.txt",
     "wp_pass_env": "KREALESTATE365COM", "daily": 3},

    # ── 테크 ─────────────────────────────────────────────────
    {"url": "https://ktech365.com",
     "lang": "en", "theme": "Technology", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_ktech.txt",
     "wp_pass_env": "KTECH365COM", "daily": 3},

    # ── K-뷰티 ────────────────────────────────────────────────
    {"url": "https://kskin365.com",
     "lang": "en", "theme": "K-Beauty", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kskin.txt",
     "wp_pass_env": "KSKIN365COM", "daily": 3},

    {"url": "https://oliveyoungkorea.com",
     "lang": "en", "theme": "K-Beauty Reviews", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_oliveyoung.txt",
     "wp_pass_env": "OLIVEYOUNGKOREACOM", "daily": 3},

    # ── K-POP ─────────────────────────────────────────────────
    {"url": "https://kworld365.com",
     "lang": "en", "theme": "K-POP", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kworld.txt",
     "wp_pass_env": "KWORLD365COM", "daily": 5},

    # ── 여행 ─────────────────────────────────────────────────
    {"url": "https://k-trip365.com",
     "lang": "en", "theme": "Travel", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_ktrip.txt",
     "wp_pass_env": "KTRIP365COM", "daily": 3},

    # ── 비자 ─────────────────────────────────────────────────
    {"url": "https://k-visa365.com",
     "lang": "en", "theme": "Visa Guide", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kvisa.txt",
     "wp_pass_env": "KVISA365COM", "daily": 3},

    # ── 웨딩 ─────────────────────────────────────────────────
    {"url": "https://koreawedding365.com",
     "lang": "en", "theme": "Wedding", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kwedding.txt",
     "wp_pass_env": "KOREAWEDDING365COM", "daily": 3},

    # ── 유학 ─────────────────────────────────────────────────
    {"url": "https://kstudy365.com",
     "lang": "en", "theme": "Study in Korea", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kstudy365.txt",
     "wp_pass_env": "KSTUDY365COM", "daily": 3},

    {"url": "https://studyinkorea365.com",
     "lang": "en", "theme": "International Students", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_studyinkorea365.txt",
     "wp_pass_env": "STUDYINKOREA365COM", "daily": 3},

    # ── 유학 관련 교육기관 ──────────────────────────────────
    {"url": "https://kieca-korea.org",
     "lang": "en", "theme": "International Students", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kieca.txt",
     "wp_pass_env": "KIECAKOREAORG", "daily": 2},

    {"url": "https://ksa-korea.org",
     "lang": "en", "theme": "Study in Korea", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_ksaKorea.txt",
     "wp_pass_env": "KSAKOREAORG", "daily": 2},

    {"url": "https://sis-korea.com",
     "lang": "en", "theme": "International Students", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_sisKorea.txt",
     "wp_pass_env": "SISKOREACOM", "daily": 2},

    # ── 취업 ─────────────────────────────────────────────────
    {"url": "https://jobkorea365.com",
     "lang": "en", "theme": "Employment", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_jobkorea365.txt",
     "wp_pass_env": "JOBKOREA365COM", "daily": 3},

    {"url": "https://jobinkorea365.com",
     "lang": "en", "theme": "Jobs in Korea", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_jobinkorea365.txt",
     "wp_pass_env": "JOBINKOREA365COM", "daily": 3},

    {"url": "https://jobkoreaglobal.com",
     "lang": "en", "theme": "Recruitment", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_jobkoreaglobal.txt",
     "wp_pass_env": "JOBKOREAGLOBALCOM", "daily": 3},

    # ── 문화 ─────────────────────────────────────────────────
    {"url": "https://korea365.org",
     "lang": "en", "theme": "Korea Culture", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_korea365.txt",
     "wp_pass_env": "KOREA365ORG", "daily": 4},

    # ── 신문 (한글/영문 완전 분리) ──────────────────────────
    {"url": "https://koreanews365.com",
     "lang": "ko", "theme": "한국 뉴스", "mode": "news",
     "keywords_file": ".github/workflows/keywords_koreanews.txt",
     "wp_pass_env": "KOREANEWS365COM", "daily": 5},

    {"url": "https://theseouljournal.com",
     "lang": "en", "theme": "Seoul Lifestyle", "mode": "news_en",
     "keywords_file": ".github/workflows/keywords_seouljournal.txt",
     "wp_pass_env": "THESEOULJOURNALCOM", "daily": 5},
]

# ============================================================
# ★ 테마별 연관 외부 권위 링크 (무관 링크 완전 제거)
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
        ("한국은행", "https://www.bok.or.kr"),
    ],
    "Seoul Lifestyle": [
        ("Seoul Metropolitan Government", "https://english.seoul.go.kr"),
        ("Visit Korea", "https://english.visitkorea.or.kr"),
        ("Korea Tourism Organization", "https://www.knto.or.kr"),
        ("Korea.net", "https://www.korea.net"),
    ],
    "Finance": [
        ("Bank of Korea", "https://www.bok.or.kr/eng"),
        ("Financial Services Commission", "https://www.fsc.go.kr/eng"),
        ("Korea Exchange", "https://global.krx.co.kr"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "Investment": [
        ("Bank of Korea", "https://www.bok.or.kr/eng"),
        ("Korea Exchange", "https://global.krx.co.kr"),
        ("Invest Korea", "https://www.investkorea.org"),
        ("Financial Services Commission", "https://www.fsc.go.kr/eng"),
    ],
    "Korea Investment": [
        ("한국거래소", "https://global.krx.co.kr"),
        ("한국투자공사", "https://www.kic.kr"),
        ("기획재정부", "https://www.moef.go.kr"),
        ("금융감독원", "https://www.fss.or.kr"),
        ("한국은행", "https://www.bok.or.kr"),
    ],
    "Insurance": [
        ("Financial Services Commission", "https://www.fsc.go.kr/eng"),
        ("National Health Insurance Service", "https://www.nhis.or.kr/english"),
        ("Financial Supervisory Service", "https://www.fss.or.kr/eng"),
    ],
    "Tax and Law": [
        ("National Tax Service", "https://www.nts.go.kr/english"),
        ("Ministry of Justice Korea", "https://www.moj.go.kr/moj/index.do"),
        ("Korea Legislation Research Institute", "https://elaw.klri.re.kr"),
    ],
    "Crypto": [
        ("Financial Services Commission", "https://www.fsc.go.kr/eng"),
        ("Bank of Korea", "https://www.bok.or.kr/eng"),
        ("Financial Intelligence Unit", "https://www.kofiu.go.kr"),
    ],
    "Technology": [
        ("Ministry of Science and ICT", "https://www.msit.go.kr/eng"),
        ("NIPA", "https://www.nipa.kr/home/eng"),
        ("KISA", "https://www.kisa.or.kr/eng"),
    ],
    "K-Beauty": [
        ("Ministry of Food and Drug Safety", "https://www.mfds.go.kr/eng"),
        ("Korea Cosmetic Association", "https://www.kcia.or.kr"),
        ("Visit Korea", "https://english.visitkorea.or.kr"),
    ],
    "K-Beauty Reviews": [
        ("Ministry of Food and Drug Safety", "https://www.mfds.go.kr/eng"),
        ("Korea Cosmetic Association", "https://www.kcia.or.kr"),
        ("Visit Korea", "https://english.visitkorea.or.kr"),
    ],
    "K-POP": [
        ("Korea.net", "https://www.korea.net"),
        ("Korean Culture and Information Service", "https://www.kocis.go.kr"),
        ("Ministry of Culture Sports and Tourism", "https://www.mcst.go.kr/eng"),
    ],
    "Travel": [
        ("Visit Korea", "https://english.visitkorea.or.kr"),
        ("Korea Tourism Organization", "https://www.knto.or.kr"),
        ("Seoul Metropolitan Government", "https://english.seoul.go.kr"),
    ],
    "Visa Guide": [
        ("HiKorea Immigration", "https://www.hikorea.go.kr"),
        ("Ministry of Justice Korea", "https://www.moj.go.kr/moj/index.do"),
        ("Korean e-Government", "https://www.gov.kr/portal/foreigner"),
    ],
    "Korea Medical Tourism": [
        ("Korea Health Industry Development Institute", "https://www.khidi.or.kr/eps"),
        ("Ministry of Health and Welfare", "https://www.mohw.go.kr/eng"),
        ("Visit Korea", "https://english.visitkorea.or.kr"),
    ],
    "Wedding": [
        ("Visit Korea", "https://english.visitkorea.or.kr"),
        ("Korea.net", "https://www.korea.net"),
        ("Seoul Metropolitan Government", "https://english.seoul.go.kr"),
    ],
    "Study in Korea": [
        ("Study in Korea NIIED", "https://www.studyinkorea.go.kr"),
        ("Ministry of Education Korea", "https://english.moe.go.kr"),
        ("NIIED", "https://www.niied.go.kr/eng"),
    ],
    "International Students": [
        ("Study in Korea NIIED", "https://www.studyinkorea.go.kr"),
        ("HiKorea Immigration", "https://www.hikorea.go.kr"),
        ("Ministry of Education Korea", "https://english.moe.go.kr"),
    ],
    "Employment": [
        ("Ministry of Employment and Labor", "https://www.moel.go.kr/english"),
        ("Work24", "https://www.work24.go.kr"),
        ("HRD Korea", "https://www.hrdkorea.or.kr/eng"),
    ],
    "Jobs in Korea": [
        ("Ministry of Employment and Labor", "https://www.moel.go.kr/english"),
        ("Work24", "https://www.work24.go.kr"),
        ("HRD Korea", "https://www.hrdkorea.or.kr/eng"),
    ],
    "Recruitment": [
        ("Ministry of Employment and Labor", "https://www.moel.go.kr/english"),
        ("HRD Korea", "https://www.hrdkorea.or.kr/eng"),
        ("Korea Employment Information Service", "https://www.keis.or.kr/eng"),
    ],
    "Korea Culture": [
        ("Korea.net", "https://www.korea.net"),
        ("Korean Culture and Information Service", "https://www.kocis.go.kr"),
        ("National Museum of Korea", "https://www.museum.go.kr/site/eng"),
    ],
    "Korea Real Estate": [
        ("한국부동산원", "https://www.reb.or.kr"),
        ("국토교통부", "https://www.molit.go.kr"),
        ("통계청", "https://kostat.go.kr"),
        ("부동산공시가격알리미", "https://www.realtyprice.kr"),
    ],
}

def get_authority_links(theme: str) -> list:
    return EXTERNAL_AUTHORITY_LINKS.get(theme, [
        ("Korea.net", "https://www.korea.net"),
        ("Visit Korea", "https://english.visitkorea.or.kr"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ])

# ============================================================
# ★ koreanews365 / theseouljournal 완전 독립 키워드 풀
# ============================================================
# 한국어 신문 — 경제·정치·사회·기술 중심
NEWS_KO_FALLBACK = [
    ("한국 부동산 정책 동향 2026", "최근 부동산 정책 변화와 시장 영향을 심층 분석합니다."),
    ("한국은행 기준금리 결정 배경", "기준금리 결정 배경과 향후 경제 전망을 다룹니다."),
    ("코스피·코스닥 시황 주간 분석", "최근 국내 증시 동향과 주요 이슈를 정리합니다."),
    ("반도체 수출 실적 역대 최고치", "반도체 산업 수출 동향과 글로벌 경쟁력을 분석합니다."),
    ("청년 주거지원 정책 2026 총정리", "청년층 대상 주거 지원 정책의 핵심 내용을 정리합니다."),
    ("국민연금 개혁안 핵심 쟁점 분석", "국민연금 개혁 논의의 주요 쟁점을 살펴봅니다."),
    ("K-배터리 차세대 기술 개발 현황", "국내 배터리 산업의 기술 혁신과 시장 동향을 다룹니다."),
    ("한국 인공지능 스타트업 생태계", "국내 AI 스타트업 생태계의 최신 흐름을 분석합니다."),
    ("저출산 대책 예산 집행 현황", "저출산 문제 해결을 위한 정부 예산 정책을 정리합니다."),
    ("탄소중립 2050 정책 추진 현황", "탄소중립 목표 달성을 위한 국내 정책 현황을 다룹니다."),
    ("K-푸드 글로벌 수출 신기록", "한국 식품의 해외 수출 트렌드를 분석합니다."),
    ("가상자산 법안 국회 통과 영향", "디지털 자산 관련 입법 동향을 정리합니다."),
    ("소비자물가지수 상승률 분석", "최근 물가 상승률과 향후 전망을 살펴봅니다."),
    ("청년 창업 정부 지원 프로그램 안내", "청년 창업가를 위한 정부 지원 프로그램을 소개합니다."),
    ("자율주행 레벨4 시범 운행 확대", "국내 자율주행 기술 시범사업 현황을 다룹니다."),
    ("필수의료 강화 정책 방향 분석", "필수의료 강화를 위한 정책 방향을 분석합니다."),
    ("방산 수출 역대 최고 기록 배경", "방위산업 수출 호조의 배경을 분석합니다."),
    ("AI 반도체 팹리스 육성 전략", "AI 반도체 설계 산업 육성 정책을 다룹니다."),
    ("국내 OTT 플랫폼 시장 점유율", "OTT 플랫폼 간 경쟁 구도와 시장 변화를 살펴봅니다."),
    ("외국인 직접투자 유치 현황 분석", "한국 내 외국인 투자 동향과 유망 섹터를 다룹니다."),
]

# 영문 서울 저널 — 라이프스타일·문화·취업·유학 중심
NEWS_EN_FALLBACK = [
    ("Living in Seoul as an Expat in 2026", "A practical guide for foreigners settling in Seoul."),
    ("Best Neighborhoods to Live in Seoul for Foreigners", "Top Seoul neighborhoods ranked by expat-friendliness."),
    ("How to Open a Bank Account in Korea as a Foreigner", "Step-by-step guide to Korean banking for foreigners."),
    ("Korean Work Culture Explained for International Professionals", "What to expect when working in a Korean company."),
    ("Street Food Culture in Seoul: A Complete Guide", "Exploring Seoul's best street food scenes and markets."),
    ("How to Get an E-7 Visa for Skilled Workers in Korea", "Detailed walkthrough of the E-7 visa application process."),
    ("Top Korean Language Schools in Seoul 2026", "Comparing the best Korean language programs for expats."),
    ("Dating and Social Life in Seoul as a Foreigner", "Honest insights into social life for foreigners in Korea."),
    ("Korea's National Health Insurance for Foreigners", "What foreign residents need to know about Korean healthcare."),
    ("Hiking Trails Near Seoul: Weekend Guide", "The best hiking spots within 1 hour of Seoul city center."),
    ("How to Find an Apartment in Seoul Without an Agent", "DIY apartment hunting guide for expats in Seoul."),
    ("K-beauty Skincare Routine: What Actually Works", "Science-backed Korean skincare tips verified by dermatologists."),
    ("Korean Food for Beginners: 15 Dishes to Try First", "The ultimate starter guide to Korean cuisine."),
    ("Working Holiday Visa Korea 2026 Guide", "Complete guide to applying for a Korean working holiday visa."),
    ("Cafes and Co-working Spaces in Seoul 2026", "Best spots to work remotely in Seoul for digital nomads."),
    ("Korean Traditional Festivals You Should Attend", "Cultural events and traditional festivals not to miss in Korea."),
    ("How to Use Seoul Public Transport Like a Local", "Complete guide to buses, metro, and KTX for newcomers."),
    ("Cost of Living in Seoul 2026: Honest Breakdown", "Realistic monthly budget breakdown for expats in Seoul."),
    ("Best Day Trips from Seoul in 2026", "Top destinations within 2 hours of Seoul for weekend trips."),
    ("Understanding Korean Visa Categories: F, E, D Series", "Clear explanation of Korean visa types for foreigners."),
]

# 사용된 뉴스 제목 추적 (같은 실행 내 중복 방지)
_used_news_titles: set = set()

# ============================================================
# ★ 뉴스 사이트 크로스런 중복 방지 — WP REST API 최근 제목 조회
# ============================================================
_wp_recent_titles_cache: dict = {}  # site_url → set of recent titles

def fetch_recent_wp_titles(site_url: str, wp_pass: str, count: int = 30) -> set:
    """WP REST API로 최근 발행 제목 count개를 가져와 소문자 set으로 반환"""
    cached = _wp_recent_titles_cache.get(site_url)
    if cached is not None:
        return cached
    titles = set()
    try:
        r = requests.get(
            f"{site_url}/wp-json/wp/v2/posts",
            auth=(WP_USER, wp_pass),
            params={"per_page": count, "orderby": "date", "order": "desc",
                    "_fields": "title", "status": "publish"},
            timeout=12
        )
        if r.status_code == 200:
            for post in r.json():
                raw = post.get("title", {})
                t = raw.get("rendered", "") if isinstance(raw, dict) else str(raw)
                t = re.sub(r'<[^>]+>', '', t).strip().lower()
                if t:
                    titles.add(t)
        print(f"   📋 {site_url} 최근 제목 {len(titles)}개 로드")
    except Exception as e:
        print(f"   ⚠️ WP 제목 조회 실패 ({site_url}): {e}")
    _wp_recent_titles_cache[site_url] = titles
    return titles

def is_title_duplicate_across_news_sites(title: str) -> bool:
    """두 뉴스 사이트(koreanews365, theseouljournal) 캐시에서 제목 중복 검사"""
    t_lower = title.strip().lower()
    for cached in _wp_recent_titles_cache.values():
        if t_lower in cached:
            return True
    # 현재 실행 내 메모리 추적도 함께 검사
    if t_lower in {x.lower() for x in _used_news_titles}:
        return True
    return False

def preload_news_site_titles(sites_config: list, wp_user: str):
    """실행 시작 시 두 뉴스 사이트 제목 사전 로드"""
    for site in sites_config:
        if site.get("mode") in ("news", "news_en"):
            wp_pass = os.getenv(site["wp_pass_env"], "")
            if wp_pass:
                fetch_recent_wp_titles(site["url"], wp_pass, count=50)

def crawl_rss_news(lang: str = "ko") -> tuple:
    """RSS 크롤링 — lang에 따라 다른 풀 사용, 실행 내·크로스런 중복 방지"""
    global _used_news_titles
    fallback_pool = NEWS_KO_FALLBACK if lang == "ko" else NEWS_EN_FALLBACK

    def _is_dup(title: str) -> bool:
        """현재 실행 메모리 + WP 캐시(크로스런) 양쪽 모두 검사"""
        t_l = title.strip().lower()
        if t_l in {x.lower() for x in _used_news_titles}:
            return True
        for cached in _wp_recent_titles_cache.values():
            if t_l in cached:
                return True
        return False

    # RSS 크롤링 (한국어만)
    if lang == "ko":
        try:
            res = requests.get("https://fs.khan.co.kr/rss/rssdata/total_news.xml", timeout=10)
            soup = BeautifulSoup(res.text, 'xml')
            items = soup.find_all('item')
            candidates = []
            for it in items:
                t = it.title.text.strip() if it.title else ""
                d = it.description.text.strip() if it.description else ""
                if t and len(t) >= 5 and not _is_dup(t):
                    candidates.append((t, d))
            if candidates:
                chosen = random.choice(candidates)
                _used_news_titles.add(chosen[0])
                return chosen
            elif items:
                print(f"   ⚠️ RSS 후보 전부 중복 — fallback 사용")
        except Exception as e:
            print(f"   ⚠️ RSS 크롤링 실패: {e}")

    # fallback — 크로스런+실행내 중복 모두 제외한 미사용 항목 우선
    unused = [x for x in fallback_pool if not _is_dup(x[0])]
    pool = unused if unused else fallback_pool  # 모두 소진 시 재사용 허용
    chosen = random.choice(pool)
    _used_news_titles.add(chosen[0])
    return chosen

# ============================================================
# ★ 제목 스타일 (후킹성 5패턴 × 한/영)
# ============================================================
TITLE_STYLES_KO = [
    "숫자 리스트형 (예: '○○하는 5가지 방법', '몰랐던 7가지 사실') — 구체적인 숫자로 신뢰감과 호기심 동시 자극",
    "경고·주의형 (예: '○○ 모르고 하면 손해보는 이유', '이것만 모르면 100% 후회') — 손실 회피 심리 자극",
    "질문형 (예: '○○ 진짜 효과 있을까?', '당신도 혹시 ○○ 하고 있나요?') — 독자 자기 점검 유도",
    "비교·반전형 (예: '○○ vs △△, 정답은 따로 있다', '다들 잘못 알고 있는 ○○ 진실') — 통념 파괴 클릭 유도",
    "긴급·시기형 (예: '지금 안 하면 늦는 ○○', '2026년 꼭 알아야 할 ○○ 총정리') — 타이밍 긴박감 조성",
]
TITLE_STYLES_EN = [
    "Number/List style (e.g. '7 Things Nobody Tells You About X', '5 Mistakes to Avoid') — specific count builds trust",
    "Warning style (e.g. 'Why You're Losing Money on X', 'Stop Making This X Mistake') — loss aversion click trigger",
    "Question style (e.g. 'Is X Really Worth It in 2026?', 'Are You Making This X Mistake?') — self-check engagement",
    "Comparison/Contrarian style (e.g. 'X vs Y: Here's the Real Answer', 'What Nobody Tells You About X') — myth-busting",
    "Urgency style (e.g. 'Why X Matters More Than Ever in 2026', 'Don't Wait to Learn This About X') — FOMO trigger",
]

def pick_title_style(lang: str) -> str:
    return random.choice(TITLE_STYLES_KO if lang == "ko" else TITLE_STYLES_EN)

# ============================================================
# ★ 보완된 최종 SEO 프롬프트 생성 (블로그 / 뉴스 / 영문뉴스)
# ============================================================
def make_seo_prompt(keyword: str, theme: str, lang: str, mode: str = "blog") -> str:
    reporter    = pick_reporter(lang)
    tag_lang    = "영어로" if lang == "en" else "한국어로"
    title_style = pick_title_style(lang)
    is_medical  = ("건강" in theme or "의학" in theme or "medical" in theme.lower()
                   or "beauty" in theme.lower())
    ext_links   = get_authority_links(theme)
    ext_sample  = random.sample(ext_links, min(3, len(ext_links)))
    ext_hint    = ", ".join(f"{n}({u})" for n, u in ext_sample)

    # ── 뉴스 모드 (한국어 신문) ───────────────────────────────
    if mode == "news":
        return f"""당신은 주요 일간지의 시니어 취재기자입니다.
주제: '{keyword}'에 대해 엄격한 신문기사체 뉴스 기사를 작성하세요.

[필수 지침 — 하나라도 빠지면 SEO 품질 감점]
1. 문체: '했다', '밝혔다', '조사됐다'로 끝나는 6하원칙 기사체. 마크다운 금지.
2. 바이라인: 기사 맨 위 첫 줄 '◇ {reporter}' 삽입.
3. 분량: HTML(h2,h3,p,strong,ul,li)만 사용해 최소 1,800자 이상.
4. ★ 모바일 가독성 강제: 모든 <p> 태그는 2~3문장 이하. 각 단락 사이 반드시 완전한 줄바꿈(<p> 분리). 빽빽한 텍스트 블록 절대 금지.
5. ★ 통계·수치 3개 이상 필수: "%", "만 명", "억 원", "년" 등 구체적 숫자 표기. 막연한 표현("많은", "대부분") 금지.
6. ★ 출처 괄호 명시: 통계 옆 "(통계청, 2026)", "(한국은행 발표)" 형식 필수.
7. ★ 테마 전용 내부링크 자리: 본문 내 최소 4개 내부링크 앵커 배치. 현재 테마 '{theme}'과 완전히 일치하는 주제만 사용. 무관 테마 링크 절대 금지.
8. ★ 권위 기관 3회 이상 언급: {ext_hint} 중 최소 3곳.
9. E-E-A-T 전문가 인용구 1개 이상.
10. h2 최소 3개.
11. 제목 스타일: {title_style} → 출력 첫 줄 'TITLE:' 로 시작.
12. ★ META_DESC: 본문 끝 'META_DESC:' 로 시작, 정확히 130~140자(한글).
13. FAQ: 'FAQ_START' ~ 'FAQ_END' 블록, Q:/A: 형식 3문항.
14. ★ TAGS: 'TAGS:' 로 시작, {TAG_COUNT}개 {tag_lang} 키워드. 각 태그 최대 3단어·15자 이내. 첫 번째는 반드시 '{keyword}'.
    {'[주의] 의학·질병 관련 태그 시 "#증상 가격", "#증상 효능" 같은 무의미 조합 절대 금지. "원인", "치료법", "예방법", "관리" 등으로 조합.' if is_medical else '주제 문맥에 완벽히 일치하는 자연스러운 키워드만.'}
출력 순서: TITLE → 본문HTML → META_DESC → FAQ_START~FAQ_END → TAGS"""

    # ── 영문 뉴스 모드 (The Seoul Journal) ──────────────────
    if mode == "news_en":
        return f"""You are a senior staff writer at an English-language newspaper based in Seoul.
Topic: Write a professional English news/feature article about '{keyword}' ({theme}).

[MANDATORY RULES — every rule must be followed]
1. Style: Journalistic English, inverted pyramid structure. No markdown.
2. Byline: First line of article must be '◇ By {reporter}'.
3. Length: Minimum 1,800 characters using HTML only (h2, h3, p, strong, ul, li).
4. ★ Mobile readability: Every <p> tag must contain maximum 2~3 sentences. Force full paragraph breaks between all sections. No dense text walls.
5. ★ Statistics (minimum 3): Include specific numbers (%, figures, dates, costs). No vague phrases like "many" or "most".
6. ★ Source citations: Cite sources in parentheses after statistics (e.g. "(Statistics Korea, 2026)", "(Ministry of Health)").
7. ★ Theme-exclusive internal links: Place minimum 4 internal link anchors in body text. Use ONLY topics strictly related to '{theme}'. Never mix unrelated themes.
8. ★ Authority sources (minimum 3 mentions): {ext_hint}
9. E-E-A-T: Include at least 1 expert quote or attributed statement.
10. Minimum 3 h2 headings.
11. Title style: {title_style} → Output first line starting with 'TITLE:'.
12. ★ META_DESC: After body, start with 'META_DESC:', exactly 130~155 characters in English.
13. FAQ: 'FAQ_START' ~ 'FAQ_END' block, Q:/A: format, 3 questions.
14. ★ TAGS: Start with 'TAGS:', {TAG_COUNT} English keywords. Max 3 words per tag. First tag must be '{keyword}'.
Output order: TITLE → body HTML → META_DESC → FAQ_START~FAQ_END → TAGS"""

    # ── 블로그 모드 (한/영 공통) ─────────────────────────────
    persona = ("의학박사 및 임상 전문의" if is_medical
               else "해당 분야 15년 경력 최고 전문 자문위원")
    persona_en = ("medical doctor and clinical specialist" if is_medical
                  else "senior industry expert with 15 years of experience")
    p = persona if lang == "ko" else persona_en

    if lang == "ko":
        return f"""당신은 {p}이자 구글 SEO 최고 전문 콘텐츠 라이터입니다.
주제: '{keyword}' | 카테고리: {theme}

[필수 지침 — 구글 애드센스 승인·상위 노출 95점 이상 기준, 하나라도 빠지면 감점]
1. HTML 전용: h2,h3,p,ul,li,ol,strong,table,tr,td. 마크다운(##,**,- 등) 절대 금지.
2. 분량: 공백 제외 최소 2,500자 이상 깊이 있는 전문 콘텐츠.
3. ★ 모바일 최적화 (체류 시간 극대화): 모든 <p>는 최대 2문장 이하. 단락 사이 완전한 줄바꿈 필수. 텍스트 블록이 빽빽하면 이탈률 급상승 → SEO 감점.
4. 키워드 배치: 첫 단락 문두에 '{keyword}' 배치, 전체 10회 이상 자연스럽게 삽입.
5. 구조: h2 최소 5개, h3 최소 4개, ul/li 리스트 3개 이상, 데이터 비교 <table> 1개 이상.
6. ★ 통계·수치 3개 이상 필수: 구체적 숫자(%, 만 명, 원, 기간). "많은", "대부분" 같은 막연한 표현 금지.
7. ★ 출처 괄호 명시 필수: 통계 옆 "(KOSIS, 2026)", "(보건복지부 자료)" 형식.
8. ★ 단일 테마 유지 (스팸 방지): 내부링크 앵커 최소 4개 배치. 반드시 현재 테마 '{theme}'에만 종속. 무관 테마(예: 웨딩·뷰티·K-POP 등) 링크 절대 금지.
9. ★ 권위 기관 3회 이상 언급: {ext_hint}
10. E-E-A-T 전문성 증명: {p}로서 실무·임상 경험 기반 디테일 2곳 이상 반영.
11. 제목 스타일: {title_style} → 출력 첫 줄 'TITLE:' 로 시작.
12. ★ META_DESC: 본문 끝 'META_DESC:' 로 시작, 정확히 130~140자(한글). 짧거나 길면 감점.
13. FAQ: 'FAQ_START' ~ 'FAQ_END' 블록, Q:/A: 형식 3문항.
14. ★ 태그 무결성: 'TAGS:' 로 시작, {TAG_COUNT}개 한국어 키워드. 각 태그 최대 3단어·15자 이내.
    첫 번째는 반드시 '{keyword}'.
    {'[크리티컬] "#증상 가격", "#효능 부작용 가격" 같은 무의미 자동조합 금지. "원인", "예방법", "치료", "관리법", "체크리스트" 등과만 조합.' if is_medical else '주제 문맥에 완벽히 일치하는 전문 키워드만.'}
출력 순서: TITLE → 본문HTML → META_DESC → FAQ_START~FAQ_END → TAGS"""

    else:  # lang == "en"
        return f"""You are a {p} and a top SEO content writer.
Topic: '{keyword}' | Category: {theme} | Language: English

[MANDATORY RULES — Google AdSense quality + top ranking, 95+ SEO score target]
1. HTML only: h2,h3,p,ul,li,ol,strong,table,tr,td. No markdown (##,**,- etc).
2. Length: Minimum 2,500 characters of in-depth expert content.
3. ★ Mobile optimization (maximize dwell time): Every <p> max 2 sentences. Full paragraph breaks between all sections. Dense text walls = high bounce rate = SEO penalty.
4. Keyword placement: '{keyword}' in first sentence, natural use 10+ times throughout.
5. Structure: min 5 h2, min 4 h3, 3+ ul/li lists, 1+ data comparison <table>.
6. ★ Statistics mandatory (min 3): Specific numbers (%, figures, dollar amounts, timeframes). No vague phrases.
7. ★ Source citations: After statistics, cite in parentheses: "(OECD, 2026)", "(Ministry of Health Korea)".
8. ★ Single theme discipline (anti-spam): Min 4 internal link anchors, ONLY topics within '{theme}'. Never mix unrelated themes (wedding, beauty, K-POP etc).
9. ★ Authority sources (min 3 mentions): {ext_hint}
10. E-E-A-T expertise proof: Include 2+ specific procedural details, costs, or timelines from a {p}'s perspective.
11. Title style: {title_style} → First output line starting 'TITLE:'.
12. ★ META_DESC: After body, 'META_DESC:' prefix, exactly 130~155 English characters.
13. FAQ: 'FAQ_START' ~ 'FAQ_END' block, Q:/A: format, 3 questions.
14. ★ Tag integrity: 'TAGS:' prefix, {TAG_COUNT} English keywords. Max 3 words each. First tag must be '{keyword}'.
    {'[CRITICAL] No nonsensical combos like "#symptoms price", "#effects dosage cost". Use "causes", "prevention", "treatment", "symptoms", "checklist".' if is_medical else 'Only semantically accurate expert keywords matching the topic context.'}
Output order: TITLE → body HTML → META_DESC → FAQ_START~FAQ_END → TAGS"""

# ============================================================
# 파싱 / 태그 / 유틸리티
# ============================================================
def extract_meta_and_faq(text: str):
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
        if s.upper().startswith("FAQ_START"): in_faq = True; continue
        if s.upper().startswith("FAQ_END"):   in_faq = False; continue
        if in_faq:
            if s[:2].upper() == "Q:": cur_q = s[2:].strip()
            elif s[:2].upper() == "A:" and cur_q:
                faq_list.append((cur_q, s[2:].strip())); cur_q = None
            continue
        out_lines.append(line)
    title = title.strip('"').strip("'").strip("*").strip()
    if not title or len(title) < 8:
        body_text = "\n".join(out_lines)
        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', body_text, re.DOTALL | re.IGNORECASE)
        if h1_match:
            ext = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip().strip('"').strip("'").strip("*").strip()
            if len(ext) >= 8: title = ext
        if not title:
            for ol in out_lines:
                plain = re.sub(r'<[^>]+>', '', ol).strip()
                if len(plain) >= 10: title = plain[:120]; break
    return "\n".join(out_lines).strip(), title, meta_desc, faq_list

def build_fallback_tag_pool(kw: str, theme: str = None, lang: str = "ko") -> list:
    s = (["효능","부작용","추천","비교","후기","방법","원인","예방","관리","총정리","가이드","체크리스트"]
         if lang == "ko" else
         ["guide","review","tips","comparison","benefits","prevention","checklist","overview","FAQ","how to","best","2026"])
    pool = [f"{kw} {x}" for x in s]
    if theme: pool.insert(0, theme)
    pool.append(kw)
    return pool

def _truncate_tag(tag: str, max_words: int = 3, max_chars: int = 20) -> str:
    words = tag.strip().split()
    if len(words) > max_words: tag = " ".join(words[:max_words])
    if len(tag) > max_chars:   tag = tag[:max_chars].rstrip()
    return tag

def extract_tags_from_article(article_text: str, fallback_keyword: str,
                               theme: str = None, lang: str = "ko"):
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
    if len(tags) > TAG_COUNT: tags = tags[:TAG_COUNT]
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

def count_statistics_in_body(body_text: str) -> int:
    """본문 내 구체적 통계 수치 개수 카운트 (SEO 점수 반영용)"""
    pattern = r'(\d+[\.,]?\d*\s*(?:%|퍼센트|percent|명|만|억|원|달러|달|년|월|개|배|회|건|점))'
    return len(re.findall(pattern, body_text, re.IGNORECASE))

def estimate_seo_score(title: str, body: str, meta_desc: str, tags: list,
                        faq_list: list, image_urls: list, keyword: str) -> int:
    """
    구글 SEO 90점 이상 보장 기준 — Rank Math 90+ 항목별 배점
    총 100점 만점 / 정상 실행 시 90점 이상 달성 목표
    """
    score = 0
    kw_l  = keyword.lower()
    plain = re.sub(r'<[^>]+>', '', body)
    blen  = len(plain.replace(" ","").replace("\n",""))

    # [A] 제목 최적화 (15점)
    title_l = title.lower()
    if kw_l in title_l:                  score += 10
    if 20 <= len(title) <= 65:           score += 3
    if any(c.isdigit() for c in title):  score += 2

    # [B] 본문 길이 (20점)
    if   blen >= 3000: score += 20
    elif blen >= 2500: score += 17
    elif blen >= 2000: score += 13
    elif blen >= 1800: score += 9
    elif blen >= 1000: score += 4

    # [C] 메타 디스크립션 (10점)
    mdl = len(meta_desc)
    if   130 <= mdl <= 160: score += 10
    elif 100 <= mdl <  130: score += 7
    elif  80 <= mdl <  100: score += 4
    elif mdl > 0:           score += 1

    # [D] 이미지 (10점)
    ic = len(image_urls)
    if   ic >= 3: score += 10
    elif ic == 2: score += 7
    elif ic == 1: score += 4

    # [E] 내부 링크 구조 (10점)
    ilinks = len(re.findall(r'<a\s+href=["\'][^"\']*["\']', body, re.IGNORECASE))
    if   ilinks >= 5: score += 10
    elif ilinks >= 4: score += 8
    elif ilinks >= 3: score += 5
    elif ilinks >= 1: score += 2

    # [F] 통계·수치·출처 (15점) — E-E-A-T 핵심
    stat_cnt = count_statistics_in_body(body)
    if   stat_cnt >= 5: score += 10
    elif stat_cnt >= 3: score += 8
    elif stat_cnt >= 1: score += 4
    cite_cnt = len(re.findall(r'\([^)]{3,40},\s*20[0-9]{2}\)', body))
    if   cite_cnt >= 3: score += 5
    elif cite_cnt >= 1: score += 2

    # [G] 구조 완성도 h2/h3/ul/table (10점)
    h2_c  = len(re.findall(r'<h2[\s>]', body, re.IGNORECASE))
    h3_c  = len(re.findall(r'<h3[\s>]', body, re.IGNORECASE))
    ul_c  = len(re.findall(r'<ul[\s>]', body, re.IGNORECASE))
    tb_c  = len(re.findall(r'<table[\s>]', body, re.IGNORECASE))
    st = 0
    if h2_c >= 5:  st += 3
    elif h2_c >= 3: st += 2
    if h3_c >= 4:  st += 2
    elif h3_c >= 2: st += 1
    if ul_c >= 3:  st += 2
    elif ul_c >= 1: st += 1
    if tb_c >= 1:  st += 3
    score += min(st, 10)

    # [H] FAQ 스키마 (5점)
    if   len(faq_list) >= 3: score += 5
    elif len(faq_list) >= 2: score += 3
    elif len(faq_list) >= 1: score += 1

    # [I] 태그 품질 (5점)
    if   len(tags) >= TAG_COUNT: score += 5
    elif len(tags) >= 8:         score += 3
    elif len(tags) >= 4:         score += 1

    return min(score, 100)

# ============================================================
def get_images_from_pixabay(query: str, need: int) -> list:
    urls = []
    if not PIXABAY_KEY: return urls
    try:
        url = (f"https://pixabay.com/api/?key={PIXABAY_KEY}"
               f"&q={requests.utils.quote(query)}&image_type=photo"
               f"&per_page=20&safesearch=true&min_width=600")
        res = requests.get(url, timeout=10)
        data = res.json()
        hits = data.get("hits") or []
        if hits:
            for h in random.sample(hits, min(need, len(hits))):
                if h.get("webformatURL"): urls.append(h["webformatURL"])
    except Exception as e:
        print(f"  ⚠️ Pixabay 실패: {e}")
    return urls

def get_images_from_pexels(query: str, need: int) -> list:
    urls = []
    if not PEXELS_KEY: return urls
    try:
        headers = {"Authorization": PEXELS_KEY}
        url = (f"https://api.pexels.com/v1/search"
               f"?query={requests.utils.quote(query)}&per_page=20&safe_search=true")
        res = requests.get(url, headers=headers, timeout=10).json()
        photos = res.get("photos") or []
        if photos:
            for p in random.sample(photos, min(need, len(photos))):
                src = (p.get("src") or {}).get("large") or (p.get("src") or {}).get("medium")
                if src: urls.append(src)
    except Exception as e:
        print(f"  ⚠️ Pexels 실패: {e}")
    return urls

def get_multiple_images(keyword: str, count: int = 3, theme: str = "") -> list:
    """3단계 fallback: 원문 → 영어번역 → 테마 fallback"""
    has_korean = any('\uac00' <= c <= '\ud7a3' for c in keyword)
    urls = []
    # 1단계: 원문(영어) 또는 번역
    if not has_korean:
        urls.extend(get_images_from_pixabay(keyword, count))
        if len(urls) < count:
            urls.extend(get_images_from_pexels(keyword, count - len(urls)))
    # 2단계: 한국어 → 영어 번역
    if len(urls) < count:
        en_query = translate_ko_to_en_for_image(keyword, theme)
        urls.extend(get_images_from_pixabay(en_query, count - len(urls)))
        if len(urls) < count:
            urls.extend(get_images_from_pexels(en_query, count - len(urls)))
    # 3단계: 테마 기반 fallback
    if len(urls) < count:
        fallback_q = THEME_IMAGE_FALLBACK.get(theme, THEME_IMAGE_FALLBACK["default"])
        urls.extend(get_images_from_pixabay(fallback_q, count - len(urls)))
        if len(urls) < count:
            urls.extend(get_images_from_pexels(fallback_q, count - len(urls)))
    return list(dict.fromkeys(urls))[:count]

# ============================================================
# 키워드 로딩 + 중복 방지
# ============================================================
_used_keywords_per_site: dict = {}

def load_keyword_no_dup(filename: str, site_url: str, fallback: str) -> str:
    global _used_keywords_per_site
    used = _used_keywords_per_site.setdefault(site_url, set())
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                keywords = [l.strip() for l in f if l.strip()]
            unused = [k for k in keywords if k not in used]
            pool = unused if unused else keywords
            chosen = random.choice(pool)
            used.add(chosen)
            return chosen
    except Exception:
        pass
    return fallback

# ============================================================
# 사이트 도달 가능 여부 확인
# ============================================================
def is_site_reachable(site_url: str, timeout: int = 8) -> bool:
    try:
        r = requests.head(f"{site_url}/wp-json/", timeout=timeout, allow_redirects=True)
        if r.status_code in (200, 301, 302, 404):
            return True
        hdrs = {k.lower(): v for k, v in r.headers.items()}
        deny = hdrs.get('x-deny-reason', '')
        print(f"    🔍 reachability HTTP {r.status_code} deny={deny}")
        return r.status_code not in (403, 503)
    except requests.exceptions.ConnectionError as e:
        print(f"    🔍 ConnectionError: {str(e)[:120]}")
    except requests.exceptions.Timeout:
        print(f"    🔍 Timeout")
    except requests.exceptions.SSLError as e:
        print(f"    🔍 SSLError: {str(e)[:80]}")
    except Exception as e:
        print(f"    🔍 {type(e).__name__}: {str(e)[:80]}")
    return False

# ============================================================
# 슬롯 분배
# ============================================================
def split_daily_into_slots(daily: int, num_slots: int = 3) -> list:
    base = daily // num_slots
    rem  = daily % num_slots
    parts = [base] * num_slots
    for i in range(rem): parts[i] += 1
    return parts

def get_posts_for_this_slot(site: dict, slot: int) -> int:
    parts = split_daily_into_slots(site["daily"], 3)
    idx = max(0, min(slot - 1, len(parts) - 1))
    return parts[idx]

# ============================================================
# Gemini 콘텐츠 생성
# ============================================================
def generate_content_gemini(prompt: str) -> str:
    global GEMINI_MODEL, _gemini_fallback_active
    for attempt in range(3):
        try:
            resp = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={"temperature": 0.85, "max_output_tokens": 8192}
            )
            return resp.text
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "resource_exhausted" in err or "quota" in err:
                if not _gemini_fallback_active:
                    print(f"  ⚠️ Gemini quota 초과 → fallback 모델 전환")
                    GEMINI_MODEL = GEMINI_MODEL_FALLBACK
                    _gemini_fallback_active = True
                    time.sleep(15)
                    continue
                else:
                    print(f"  ❌ Gemini fallback도 quota 초과. 대기 60초")
                    time.sleep(60)
                    raise
            print(f"  ⚠️ Gemini 오류 (attempt {attempt+1}): {e}")
            if attempt < 2: time.sleep(10)
    raise RuntimeError("Gemini 3회 연속 실패")

# ============================================================
# 워드프레스 포스팅
# ============================================================
def build_faq_schema_html(faq_list: list) -> str:
    if not faq_list: return ""
    items = "".join(
        f'<div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">'
        f'<h3 itemprop="name">{q}</h3>'
        f'<div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">'
        f'<p itemprop="text">{a}</p></div></div>'
        for q, a in faq_list
    )
    return (f'<div itemscope itemtype="https://schema.org/FAQPage">'
            f'<h2>자주 묻는 질문 (FAQ)</h2>{items}</div>')

def build_image_html(image_urls: list, keyword: str) -> str:
    html = ""
    for i, u in enumerate(image_urls):
        alt = f"{keyword} 관련 이미지 {i+1}" if i > 0 else keyword
        html += f'<figure><img src="{u}" alt="{alt}" loading="lazy" style="max-width:100%;height:auto;border-radius:8px;margin:16px 0;"></figure>\n'
    return html

def wp_post(site: dict, title: str, body_html: str, meta_desc: str,
            tags: list, faq_list: list, image_urls: list,
            keyword: str, seo_score: int) -> dict:
    wp_pass = os.getenv(site["wp_pass_env"], "")
    if not wp_pass:
        return {"ok": False, "error": f"WP_PASS_ENV '{site['wp_pass_env']}' not set"}

    # FAQ 스키마 + 이미지 삽입
    faq_html   = build_faq_schema_html(faq_list)
    img_html   = build_image_html(image_urls, keyword)
    # 이미지: 본문 중간 + 끝 배치
    mid = len(body_html) // 2
    split_pt = body_html.find('</p>', mid)
    if split_pt > 0 and image_urls:
        mid_img = build_image_html(image_urls[:1], keyword)
        end_img = build_image_html(image_urls[1:], keyword) if len(image_urls) > 1 else ""
        final_body = body_html[:split_pt+4] + mid_img + body_html[split_pt+4:] + faq_html + end_img
    else:
        final_body = img_html + body_html + faq_html

    tags_payload = []
    for tag in tags:
        try:
            tr = requests.post(
                f"{site['url']}/wp-json/wp/v2/tags",
                auth=(WP_USER, wp_pass),
                json={"name": tag}, timeout=10
            )
            if tr.status_code in (200, 201):
                tags_payload.append(tr.json().get("id"))
            elif tr.status_code == 400:
                # 이미 존재하는 태그 → ID 조회
                sr = requests.get(
                    f"{site['url']}/wp-json/wp/v2/tags",
                    auth=(WP_USER, wp_pass),
                    params={"search": tag, "per_page": 1}, timeout=10
                )
                if sr.status_code == 200 and sr.json():
                    tags_payload.append(sr.json()[0]["id"])
        except Exception:
            pass

    rank_kw = ",".join([keyword] + tags[:4])
    post_data = {
        "title":   title,
        "content": final_body,
        "status":  "publish",
        "meta": {
            "rank_math_focus_keyword":  rank_kw,
            "rank_math_description":    meta_desc,
            "rank_math_seo_score":      str(seo_score),
        },
        "tags": tags_payload,
    }

    try:
        r = requests.post(
            f"{site['url']}/wp-json/wp/v2/posts",
            auth=(WP_USER, wp_pass),
            json=post_data, timeout=30
        )
        if r.status_code in (200, 201):
            post_id  = r.json().get("id")
            post_url = r.json().get("link", "")
            # Rank Math 검증 + PATCH 재시도
            time.sleep(2)
            vr = requests.get(
                f"{site['url']}/wp-json/wp/v2/posts/{post_id}",
                auth=(WP_USER, wp_pass), timeout=10
            )
            if vr.status_code == 200:
                meta_check = vr.json().get("meta", {})
                if not meta_check.get("rank_math_focus_keyword"):
                    requests.patch(
                        f"{site['url']}/wp-json/wp/v2/posts/{post_id}",
                        auth=(WP_USER, wp_pass),
                        json={"meta": {"rank_math_focus_keyword": rank_kw,
                                       "rank_math_description": meta_desc}},
                        timeout=15
                    )
            return {"ok": True, "post_id": post_id, "url": post_url}
        else:
            return {"ok": False, "status": r.status_code,
                    "error": r.text[:300]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}

# ============================================================
# 구글시트 로깅 (18컬럼)
# ============================================================
_log_buffer: list = []

def record_result(site_url: str, theme: str, keyword: str, title: str,
                  post_url: str, seo_score: int, image_count: int,
                  status: str, error: str = ""):
    _log_buffer.append({
        "timestamp": now_kst().strftime("%Y-%m-%d %H:%M:%S"),
        "site":       site_url,
        "theme":      theme,
        "keyword":    keyword,
        "title":      title,
        "status":     status,
        "seo_score":  seo_score,
        "images":     image_count,
        "url":        post_url,
        "error":      error,
        "slot":       str(RUN_SLOT),
        "model":      GEMINI_MODEL,
    })

def flush_log_to_google_sheet():
    if not SHEETS_WEBHOOK or not _log_buffer: return
    try:
        r = requests.post(
            SHEETS_WEBHOOK,
            json={"records": _log_buffer},
            timeout=15
        )
        print(f"  📊 구글시트 전송 {len(_log_buffer)}건: HTTP {r.status_code}")
        _log_buffer.clear()
    except Exception as e:
        print(f"  ⚠️ 구글시트 전송 실패: {e}")
    # 실패해도 재시도 1회
    if _log_buffer:
        try:
            time.sleep(3)
            r = requests.post(SHEETS_WEBHOOK, json={"records": _log_buffer}, timeout=15)
            if r.status_code < 300: _log_buffer.clear()
        except Exception:
            pass

# ============================================================
# 단일 포스트 처리
# ============================================================
def process_one_post(site: dict, keyword: str) -> bool:
    url   = site["url"]
    lang  = site["lang"]
    theme = site["theme"]
    mode  = site["mode"]

    print(f"\n  🖊  [{theme}] {keyword[:50]}")

    # 뉴스 모드: 키워드 = RSS/fallback에서 가져온 (제목, 서브제목)
    news_subtitle = ""
    if mode in ("news", "news_en"):
        kw_tuple = crawl_rss_news(lang)
        keyword, news_subtitle = kw_tuple if isinstance(kw_tuple, tuple) else (kw_tuple, "")

    # 프롬프트 생성
    prompt = make_seo_prompt(keyword, theme, lang, mode)

    # Gemini 생성 (SEO 90점 미달 시 최대 1회 재시도)
    SEO_MIN_SCORE = 90   # 이 점수 미만이면 재생성
    MAX_REGEN     = 1    # 최대 재시도 횟수
    raw = None
    for gen_attempt in range(MAX_REGEN + 1):
        try:
            raw = generate_content_gemini(prompt)
        except Exception as e:
            print(f"  ❌ Gemini 생성 실패: {e}")
            record_result(url, theme, keyword, "", "", 0, 0, "❌ Gemini 실패", str(e))
            return False
        time.sleep(SLEEP_BETWEEN_POSTS)

        # 파싱
        body_raw, title, meta_desc, faq_list = extract_meta_and_faq(raw)
        body, tags = extract_tags_from_article(body_raw, keyword, theme, lang)

        if not title:
            title = (f"{keyword} — 완벽 정리 가이드" if lang == "ko"
                     else f"{keyword} — Complete Guide {now_kst().year}")

        # 임시 점수 계산 (이미지 미포함)
        _pre_score = estimate_seo_score(title, body, meta_desc, tags, faq_list, ["x","x","x"], keyword)
        if _pre_score >= SEO_MIN_SCORE or gen_attempt >= MAX_REGEN:
            print(f"  📝 생성 {gen_attempt+1}회차 → 본문 사전 SEO {_pre_score}점")
            break
        else:
            print(f"  🔄 SEO {_pre_score}점 미달({SEO_MIN_SCORE}점 기준) → 재생성 시도 {gen_attempt+2}회차")
            # 재생성 시 프롬프트에 보완 지시 추가
            prompt = prompt + f"""

[재생성 보완 지시 — 이전 결과가 SEO {_pre_score}점으로 기준 미달]
아래 항목을 반드시 보완하여 재작성하세요:
- 본문 <table> 데이터 비교표 반드시 1개 이상 포함
- 통계 수치(%, 만 명, 원 등) 최소 5개 이상, 출처 괄호 3개 이상
- 내부링크 앵커 <a href="URL">텍스트</a> 형식 5개 이상
- h2 5개 이상, h3 4개 이상, ul 3개 이상
- 본문 총 3,000자 이상"""
            time.sleep(5)

    # 이미지
    images = get_multiple_images(keyword, count=3, theme=theme)
    print(f"  🖼  이미지 {len(images)}장")

    # SEO 점수 (이미지 포함 최종)
    score = estimate_seo_score(title, body, meta_desc, tags, faq_list, images, keyword)
    rank_label = ("🏆 우수" if score >= 95 else
                  "✅ 양호" if score >= 90 else
                  "⚠️ 보통" if score >= 80 else
                  "❌ 미달")
    print(f"  📊 SEO 최종 점수: {score}/100  {rank_label}")
    if score < 90:
        plain_len = len(re.sub(r'<[^>]+>','',body).replace(' ','').replace('\n',''))
        stat_cnt2 = count_statistics_in_body(body)
        ilinks2   = len(re.findall(r'<a\s+href=', body, re.IGNORECASE))
        tb2       = len(re.findall(r'<table[\s>]', body, re.IGNORECASE))
        print(f"     ↳ 본문길이:{plain_len}자 | 통계수치:{stat_cnt2}개 | 내부링크:{ilinks2}개 | 테이블:{tb2}개")

    # WP 발행 직전 — 뉴스 사이트는 최종 생성 제목으로 크로스런 중복 재검사
    if mode in ("news", "news_en") and title:
        t_lower = title.strip().lower()
        is_cross_dup = False
        for cached in _wp_recent_titles_cache.values():
            if t_lower in cached:
                is_cross_dup = True
                break
        if is_cross_dup:
            print(f"  ⛔ 크로스런 제목 중복 감지 → 발행 취소: {title[:60]}")
            record_result(url, theme, keyword, title, "", score, len(images),
                          "⛔ skip_cross_dup")
            return False
        # 발행 성공 예정 제목을 캐시에 즉시 등록 (다음 포스트 방어)
        for site_url_key in _wp_recent_titles_cache:
            _wp_recent_titles_cache[site_url_key].add(t_lower)
        _used_news_titles.add(title)

    # WP 발행
    result = wp_post(site, title, body, meta_desc, tags, faq_list, images, keyword, score)
    if result["ok"]:
        print(f"  ✅ 발행 완료: {result.get('url','')}")
        record_result(url, theme, keyword, title, result.get("url",""),
                      score, len(images), "✅ OK")
        return True
    else:
        err = result.get("error","")
        print(f"  ❌ 발행 실패: {err[:120]}")
        record_result(url, theme, keyword, title, "", score, len(images),
                      "❌ WP 실패", err)
        return False

# ============================================================
# 메인 실행
# ============================================================
def main():
    print(f"\n{'='*60}")
    print(f"🚀 autopost_mega.py 시작 — SLOT {RUN_SLOT} | {now_kst().strftime('%Y-%m-%d %H:%M:%S')} KST")
    print(f"   Gemini 모델: {GEMINI_MODEL}")
    print(f"{'='*60}\n")

    total_ok = total_fail = total_skip = 0

    # ★ 뉴스 사이트 크로스런 중복 방지 — 실행 시작 시 최근 발행 제목 50개 사전 로드
    print("📋 뉴스 사이트 최근 제목 사전 로드 중...")
    preload_news_site_titles(SITES_CONFIG, WP_USER)

    for site in SITES_CONFIG:
        url   = site["url"]
        theme = site["theme"]
        n     = get_posts_for_this_slot(site, RUN_SLOT)
        if n == 0:
            print(f"⏭  {url} — 이번 슬롯 발행 없음")
            continue

        print(f"\n{'─'*50}")
        print(f"🌐 {url}  [{theme}]  슬롯{RUN_SLOT} → {n}건 예정")

        # 도달 가능 여부 확인
        if not is_site_reachable(url):
            print(f"  ⚠️  연결 불가 → skip_unreachable")
            for _ in range(n):
                record_result(url, theme, "—", "—", "", 0, 0, "⚠️ skip_unreachable")
            total_skip += n
            continue

        for i in range(n):
            # 뉴스 모드는 crawl 내에서 키워드 결정
            if site["mode"] in ("news", "news_en"):
                keyword = "__news__"
            else:
                keyword = load_keyword_no_dup(
                    site["keywords_file"], url,
                    fallback=f"{theme} tips 2026"
                )
            ok = process_one_post(site, keyword)
            if ok: total_ok += 1
            else:  total_fail += 1
            if i < n - 1: time.sleep(random.uniform(8, 14))

    flush_log_to_google_sheet()

    print(f"\n{'='*60}")
    print(f"✅ 완료 — 성공 {total_ok} / 실패 {total_fail} / 스킵 {total_skip}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
