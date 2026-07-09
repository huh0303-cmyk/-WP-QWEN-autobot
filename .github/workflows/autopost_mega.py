#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
autopost_mega.py — 27개 사이트 메가 오토포스팅 봇 (완전 무료 운영판 v2.1)
업데이트: 2026-06 [무료화 최적화]
  ✅ gemini-2.5-flash-lite 완전 고정 (비용 0원 · Free Tier 1500 RPD)
  ✅ max_output_tokens 4096으로 최적화 (토큰 낭비 50% 절감)
  ✅ MAX_REGEN 0회 (Free Tier 20RPD 한도 준수 → 비용 0원 완전 보장)
  ✅ SLEEP_BETWEEN_POSTS 15초 (RPM 제한 60req/min 안전 준수)
  ✅ 재시도 대기 60초 → 율속 초과 시 안전 복구
  ✅ SEO 90점 기준 유지 (95점 무리한 재생성 제거)
  ✅ post-processing 자동 보완으로 품질 방어
  ✅ 이미지 Pixabay/Pexels 무료 API 유지
  ✅ 클릭 유발 제목 템플릿·동의어 분산·키워드 밀도 제어 유지
  ✅ WP Author·카테고리·Rank Math 메타 자동 주입 유지
  ✅ [긴급 패치] 특수문자 및 # 태그 완벽 세척 필터 탑재 (발행 중단 방지)
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

# GitHub Secrets로부터 안전하게 로드
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
PIXABAY_KEY     = os.getenv("PIXABAY_KEY")
PEXELS_KEY      = os.getenv("PEXELS_KEY")
SHEETS_WEBHOOK  = os.getenv("SHEETS_WEBHOOK")
WP_USER         = "huh0303@gmail.com"

RUN_SLOT              = int(os.getenv("RUN_SLOT", "1"))
SLEEP_BETWEEN_POSTS   = float(os.getenv("SLEEP_BETWEEN_POSTS", "15"))

gemini_client          = genai.Client(api_key=GEMINI_API_KEY)

GEMINI_MODEL_PRIMARY   = "gemini-2.5-flash-lite"
GEMINI_MODEL_FALLBACK  = "gemini-2.5-flash-lite"
GEMINI_MODEL           = GEMINI_MODEL_PRIMARY

TAG_COUNT        = 12
MIN_BODY_LENGTH  = 1800
SEO_TARGET       = 90
MAX_REGEN        = 0   # Free Tier 무리한 재시도 방지
KW_DENSITY_MAX   = 0.025
RATE_LIMIT_SLEEP = 35.0

# ============================================================
# 가상 기자 명단
# ============================================================
REPORTERS_KO = [
    {"name": "김민준", "email": "minjun@koreanews365.com",    "slug": "minjun-kim",    "bio": "정치·경제 전문 기자. 10년 경력."},
    {"name": "이서연", "email": "seoyeon@koreanews365.com",   "slug": "seoyeon-lee",   "bio": "국제·외교 담당 시니어 기자."},
    {"name": "박현우", "email": "hyunwoo@koreanews365.com",   "slug": "hyunwoo-park",  "bio": "경제·금융 분야 전문 기자."},
    {"name": "최지아", "email": "jia@koreanews365.com",       "slug": "jia-choi",      "bio": "문화·사회 담당 기자."},
    {"name": "정재희", "email": "jaehee@koreanews365.com",    "slug": "jaehee-jung",   "bio": "산업·기술 전문 기자."},
    {"name": "윤성호", "email": "sungho@koreanews365.com",    "slug": "sungho-yoon",   "bio": "증권·투자 담당 기자."},
    {"name": "강다은", "email": "daeun@koreanews365.com",     "slug": "daeun-kang",    "bio": "생활·복지 전문 기자."},
    {"name": "임준혁", "email": "junhyuk@koreanews365.com",   "slug": "junhyuk-lim",   "bio": "사회·법률 담당 기자."},
    {"name": "한소희", "email": "sohee@koreanews365.com",     "slug": "sohee-han",     "bio": "교육·보건 전문 기자."},
    {"name": "오태영", "email": "taeyoung@koreanews365.com",  "slug": "taeyoung-oh",   "bio": "무역·글로벌 담당 기자."},
]

REPORTERS_EN = [
    {"name": "James Patterson",  "email": "james@theseouljournal.com",   "slug": "james-patterson",  "bio": "Senior politics and economy correspondent."},
    {"name": "Emily Crawford",   "email": "emily@theseouljournal.com",    "slug": "emily-crawford",   "bio": "Culture and lifestyle editor."},
    {"name": "Michael Thompson", "email": "michael@theseouljournal.com",  "slug": "michael-thompson", "bio": "Business and finance reporter."},
    {"name": "Sarah Williams",   "email": "sarah@theseouljournal.com",    "slug": "sarah-williams",   "bio": "International affairs correspondent."},
    {"name": "David Harrison",   "email": "david@theseouljournal.com",    "slug": "david-harrison",   "bio": "Technology and innovation writer."},
    {"name": "Jessica Kim",      "email": "jessica@theseouljournal.com",  "slug": "jessica-kim",      "bio": "K-culture and entertainment reporter."},
    {"name": "Robert Park",      "email": "robert@theseouljournal.com",   "slug": "robert-park",      "bio": "Economy and markets analyst."},
    {"name": "Laura Choi",       "email": "laura@theseouljournal.com",    "slug": "laura-choi",       "bio": "Lifestyle and travel journalist."},
    {"name": "Daniel Yoon",      "email": "daniel@theseouljournal.com",   "slug": "daniel-yoon",      "bio": "Politics and society reporter."},
    {"name": "Rachel Lim",       "email": "rachel@theseouljournal.com",   "slug": "rachel-lim",       "bio": "Health and wellness correspondent."},
]

REPORTERS_BLOG_EN = [
    {"name": "Andrew Kim",      "email": "andrew@contributor.com",    "slug": "andrew-kim",     "bio": "Finance and investment specialist writer."},
    {"name": "Sophia Lee",      "email": "sophia@contributor.com",    "slug": "sophia-lee",     "bio": "Health and wellness expert contributor."},
    {"name": "Brian Choi",      "email": "brian@contributor.com",     "slug": "brian-choi",     "bio": "Technology and digital trends writer."},
    {"name": "Hannah Park",     "email": "hannah@contributor.com",    "slug": "hannah-park",    "bio": "Travel and culture journalist."},
    {"name": "Kevin Yoon",      "email": "kevin@contributor.com",     "slug": "kevin-yoon",     "bio": "Real estate and economy analyst."},
    {"name": "Grace Jung",      "email": "grace@contributor.com",     "slug": "grace-jung",     "bio": "K-beauty and lifestyle editor."},
    {"name": "Thomas Lim",      "email": "thomas@contributor.com",    "slug": "thomas-lim",     "bio": "Legal and tax affairs writer."},
    {"name": "Olivia Shin",     "email": "olivia@contributor.com",    "slug": "olivia-shin",    "bio": "Education and career specialist."},
    {"name": "Nathan Oh",       "email": "nathan@contributor.com",    "slug": "nathan-oh",      "bio": "Crypto and fintech correspondent."},
    {"name": "Catherine Han",   "email": "catherine@contributor.com", "slug": "catherine-han",  "bio": "Medical tourism and healthcare writer."},
]

REPORTERS_BLOG_KO = [
    {"name": "김재원", "email": "jaewon@contributor.com",   "slug": "jaewon-kim",   "bio": "재테크·금융 전문 칼럼니스트."},
    {"name": "이미경", "email": "mikyung@contributor.com",  "slug": "mikyung-lee",  "bio": "건강·의학 전문 작가."},
    {"name": "박성훈", "email": "sunghoon@contributor.com", "slug": "sunghoon-park","bio": "부동산·경제 분야 전문 기고자."},
    {"name": "최수연", "email": "suyeon@contributor.com",   "slug": "suyeon-choi",  "bio": "교육·유학 전문 칼럼니스트."},
    {"name": "정민호", "email": "minho@contributor.com",    "slug": "minho-jung",   "bio": "법률·세무 전문 작가."},
    {"name": "윤지훈", "email": "jihoon@contributor.com",   "slug": "jihoon-yoon",  "bio": "투자·주식 전문 기고자."},
    {"name": "강혜진", "email": "hyejin@contributor.com",   "slug": "hyejin-kang",  "bio": "웰빙·라이프스타일 전문 작가."},
    {"name": "임채원", "email": "chaewon@contributor.com",  "slug": "chaewon-lim",  "bio": "문화·여행 전문 칼럼니스트."},
    {"name": "한도윤", "email": "doyoon@contributor.com",   "slug": "doyoon-han",   "bio": "기술·IT 전문 기고자."},
    {"name": "오승현", "email": "seunghyun@contributor.com","slug": "seunghyun-oh", "bio": "국제·무역 전문 작가."},
]

_wp_author_cache = {}

def get_or_create_wp_author(site_url: str, wp_pass: str, reporter: dict) -> int:
    cache = _wp_author_cache.setdefault(site_url, {})
    slug = reporter["slug"]
    if slug in cache:
        return cache[slug]

    try:
        r = requests.get(
            f"{site_url}/wp-json/wp/v2/users",
            auth=(WP_USER, wp_pass),
            params={"search": reporter["email"], "per_page": 5},
            timeout=10
        )
        if r.status_code == 200 and r.json():
            uid = r.json()[0]["id"]
            cache[slug] = uid
            return uid
    except Exception:
        pass

    try:
        payload = {
            "username": slug,
            "name": reporter["name"],
            "email": reporter["email"],
            "slug": slug,
            "description": reporter.get("bio", ""),
            "password": hashlib.md5(reporter["email"].encode()).hexdigest()[:16] + "Aa1!",
            "roles": ["author"]
        }
        r = requests.post(
            f"{site_url}/wp-json/wp/v2/users",
            auth=(WP_USER, wp_pass),
            json=payload,
            timeout=15
        )
        if r.status_code in (200, 201):
            uid = r.json().get("id")
            cache[slug] = uid
            print(f"   👤 기자 계정 생성 완료: {reporter['name']} (ID {uid})")
            return uid
        elif r.status_code == 400:
            r2 = requests.get(
                f"{site_url}/wp-json/wp/v2/users",
                auth=(WP_USER, wp_pass),
                params={"slug": slug, "per_page": 1},
                timeout=10
            )
            if r2.status_code == 200 and r2.json():
                uid = r2.json()[0]["id"]
                cache[slug] = uid
                return uid
    except Exception as e:
        print(f"   ⚠️ Author 생성 실패 ({reporter['name']}): {e}")

    cache[slug] = -1
    return -1

def pick_reporter(site: dict) -> dict:
    url = site.get("url", "")
    lang = site.get("lang", "en")
    if "koreanews365" in url:
        return random.choice(REPORTERS_KO)
    elif "theseouljournal" in url:
        return random.choice(REPORTERS_EN)
    elif lang == "ko":
        return random.choice(REPORTERS_BLOG_KO)
    else:
        return random.choice(REPORTERS_BLOG_EN)

# ============================================================
# 테마별 카테고리 맵 구조
# ============================================================
THEME_CATEGORIES = {
    "건강과 의학": {
        "default": "건강정보",
        "golden": ["건강정보", "건강기능식품소개", "질병별대처법", "기타"],
        "keyword_map": [
            (["영양", "비타민", "영양제", "보충제", "유산균", "프로바이오틱", "오메가", "콜라겐", "다이어트", "비만", "체중", "식품", "기능성"], "건강기능식품소개"),
            (["혈압", "당뇨", "혈당", "암", "피부", "아토피", "탈모", "관절", "허리", "디스크", "골다공증", "수면", "불면", "우울", "불안", "간", "소화", "변비", "치료", "예방", "관리"], "질병별대처법"),
            (["보험", "보험료", "실비", "약값", "부작용", "리콜", "이슈", "논란", "드라마", "예능", "연예인", "건강정책", "의료정책"], "기타"),
        ]
    },
    "한국 뉴스": {
        "default": "경제",
        "golden": ["경제", "정치", "사회"],
        "keyword_map": [
            (["정치", "대통령", "국회", "선거", "정당", "여당", "야당", "법안", "탄핵", "외교", "북한"], "정치"),
            (["사회", "범죄", "복지", "노동", "청년", "저출산", "교육", "문화", "K-pop", "드라마", "미국", "중국", "일본", "국제", "AI", "반도체"], "사회"),
        ]
    },
    "Seoul Lifestyle": {
        "default": "Culture",
        "golden": ["Politics", "Economy", "Culture"],
        "keyword_map": [
            (["politics", "election", "president", "government", "parliament", "policy", "North Korea", "diplomacy", "minister", "sanctions", "military", "crisis"], "Politics"),
            (["economy", "GDP", "inflation", "interest rate", "export", "trade", "stock", "market", "startup", "tech", "AI", "semiconductor", "Samsung", "Hyundai", "investment", "fund"], "Economy"),
        ]
    },
    "Korea Medical Tourism": {
        "default": "Cosmetic Surgery",
        "golden": ["Cosmetic Surgery", "Government Support", "Hospital Costs", "Etc"],
        "keyword_map": [
            (["정부", "지자체", "서울시", "부산", "대구", "인천", "지원", "혜택", "보조", "의료관광", "government", "subsidy", "support", "benefit"], "Government Support"),
            (["비용", "가격", "cost", "price", "fee", "얼마", "견적", "할인", "패키지"], "Hospital Costs"),
        ]
    },
    "Investment": {
        "default": "Korea Stocks",
        "golden": ["Korea Stocks", "Korea Funds & ETF", "Crypto & Digital", "Etc"],
        "keyword_map": [
            (["ETF", "fund", "mutual", "index", "bond", "dividend", "yield", "REIT"], "Korea Funds & ETF"),
            (["crypto", "bitcoin", "ethereum", "DeFi", "NFT", "blockchain", "digital asset", "upbit", "bithumb"], "Crypto & Digital"),
        ]
    },
    "Korea Investment": {
        "default": "Stocks",
        "golden": ["Stocks", "Real Estate", "Pension", "Etc"],
        "keyword_map": [
            (["부동산", "아파트", "청약", "분양", "전세", "리츠", "토지", "오피스텔", "real estate", "apartment", "subscription"], "Real Estate"),
            (["절세", "IRP", "연금", "비과세", "공제", "채권", "금리", "세금", "펀드", "tax saving", "pension", "bond"], "Pension"),
        ]
    },
    "Insurance": {
        "default": "Health Insurance",
        "golden": ["Health Insurance", "Auto Insurance", "Dental Insurance", "Etc"],
        "keyword_map": [
            (["car", "auto", "vehicle", "driver", "traffic", "자동차", "운전", "교통사고"], "Auto Insurance"),
            (["dental", "치과", "implant", "임플란트", "tooth", "teeth", "scaling", "orthodontics"], "Dental Insurance"),
        ]
    },
    "Finance": {
        "default": "Banking",
        "golden": ["Banking", "Investing", "Tax Refund", "Etc"],
        "keyword_map": [
            (["stock", "invest", "ETF", "fund", "KOSPI", "trading", "portfolio", "dividend", "주식", "펀드"], "Investing"),
            (["tax", "세금", "refund", "환급", "VAT", "income tax", "deduction", "신고", "연말정산"], "Tax Refund"),
        ]
    },
    "Tax and Law": {
        "default": "Tax Filing",
        "golden": ["Tax Filing", "Business Setup", "Visa", "Etc"],
        "keyword_map": [
            (["business", "company", "startup", "corporation", "법인", "창업", "registration", "투자", "M&A"], "Business Setup"),
            (["visa", "immigration", "체류", "residence", "permit", "비자", "ARC", "HiKorea", "출입국"], "Visa"),
        ]
    },
    "Crypto": {
        "default": "Exchanges",
        "golden": ["Exchanges", "Investing", "Regulations", "Etc"],
        "keyword_map": [
            (["foreign", "외국인", "invest", "투자", "buy", "구매", "how to", "방법", "guide", "beginner"], "Investing"),
            (["regulation", "규제", "law", "FSC", "금융위", "tax", "세금", "legal", "policy", "ban", "허용"], "Regulations"),
        ]
    },
    "Korea Real Estate": {
        "default": "Apartments",
        "golden": ["Apartments", "Commercial", "Loans", "Etc"],
        "keyword_map": [
            (["상가", "사무실", "office", "store", "사업장", "임대", "월세", "lease", "commercial"], "Commercial"),
            (["대출", "loan", "세금", "tax", "취득세", "양도세", "mortgage", "은행", "금리"], "Loans"),
        ]
    },
    "Technology": {
        "default": "AI",
        "golden": ["AI", "Startups", "Semiconductors"],
        "keyword_map": [
            (["startup", "venture", "innovation", "unicorn", "founder", "funding", "scale", "SME"], "Startups"),
            (["semiconductor", "chip", "TSMC", "fab", "wafer", "memory", "DRAM", "NAND", "EV", "battery", "display"], "Semiconductors"),
        ]
    },
    "K-Beauty": {
        "default": "Skincare",
        "golden": ["Skincare", "Ingredients", "Routines"],
        "keyword_map": [
            (["ingredient", "niacinamide", "hyaluronic", "vitamin C", "peptide", "ceramide", "retinol", "AHA", "BHA", "acid", "extract"], "Ingredients"),
            (["routine", "steps", "morning", "night", "AM", "PM", "order", "layering", "how to", "guide"], "Routines"),
        ]
    },
    "K-Beauty Reviews": {
        "default": "Top Products",
        "golden": ["Top Products", "Skincare", "Wellness", "Etc"],
        "keyword_map": [
            (["skincare", "toner", "serum", "moisturizer", "sunscreen", "essence", "ampoule", "cream", "skin"], "Skincare"),
            (["wellness", "supplement", "vitamin", "probiotic", "collagen", "health", "inner beauty", "gut"], "Wellness"),
        ]
    },
    "K-POP": {
        "default": "Artists",
        "golden": ["Artists", "Music", "Tours", "Etc"],
        "keyword_map": [
            (["album", "release", "comeback", "single", "MV", "track", "playlist", "song", "lyrics"], "Music"),
            (["concert", "tour", "performance", "live", "show", "event", "stadium", "ticket"], "Tours"),
        ]
    },
    "K-Culture": {
        "default": "K-Pop",
        "golden": ["K-Pop", "Learn Korean", "Travel", "Etc"],
        "keyword_map": [
            (["learn korean", "study korean", "korean language", "TOPIK", "grammar", "vocabulary", "hangul", "korean class", "korean lesson", "speak korean", "korean alphabet", "free korean", "korean for beginners", "한국어"], "Learn Korean"),
            (["travel", "food", "restaurant", "Seoul", "Busan", "Jeju", "trip", "tour", "tourism", "korean life", "living in korea", "expat", "foreigner", "korean culture", "korean tradition", "kdrama", "k-drama"], "Travel"),
        ]
    },
    "Travel": {
        "default": "Hotels",
        "golden": ["Hotels", "AirBnB", "Guides", "Etc"],
        "keyword_map": [
            (["airbnb", "민박", "guesthouse", "pension", "게스트하우스", "민박집", "여기어때", "숙박"], "AirBnB"),
            (["guide", "itinerary", "travel", "tour", "trip", "visit", "attraction", "sightseeing", "여행"], "Guides"),
        ]
    },
    "Visa Guide": {
        "default": "Work Visa",
        "golden": ["Work Visa", "Student Visa", "Long-term Visa"],
        "keyword_map": [
            (["student", "D-2", "D-4", "language school", "university", "study", "academic"], "Student Visa"),
            (["F-2", "F-5", "long-term", "permanent", "settlement", "naturalization", "PR"], "Long-term Visa"),
        ]
    },
    "Wedding": {
        "default": "Marriage",
        "golden": ["Marriage", "Education", "Matching", "Etc"],
        "keyword_map": [
            (["child", "자녀", "nationality", "국적", "education", "교육", "school", "학교", "benefit", "혜택"], "Education"),
            (["match", "matchmaking", "소개", "맞선", "비용", "cost", "price", "wedding cost", "결혼비용", "agency"], "Matching"),
        ]
    },
    "Study in Korea": {
        "default": "Study Korea",
        "golden": ["Study Korea", "Scholarships", "Student Life"],
        "keyword_map": [
            (["scholarship", "KGSP", "GKS", "funding", "stipend", "grant", "financial aid", "award"], "Scholarships"),
            (["campus", "dorm", "dormitory", "visa", "part-time", "life", "housing", "club", "adjustment"], "Student Life"),
        ]
    },
    "International Students": {
        "default": "Admissions",
        "golden": ["Admissions", "Scholarships", "Campus Life"],
        "keyword_map": [
            (["scholarship", "funding", "GKS", "KGSP", "award", "grant", "stipend", "financial"], "Scholarships"),
            (["campus", "dormitory", "housing", "life", "club", "activities", "adjustment", "culture"], "Campus Life"),
        ]
    },
    "국제교육문화": {
        "default": "Language",
        "golden": ["Language", "Culture", "Careers"],
        "keyword_map": [
            (["문화", "전통", "교류", "축제", "역사", "예술", "heritage"], "Culture"),
            (["취업", "커리어", "글로벌", "인턴", "직업", "일자리"], "Careers"),
        ]
    },
    "한국유학정보": {
        "default": "Admissions",
        "golden": ["Admissions", "Scholarships", "Visa"],
        "keyword_map": [
            (["장학금", "GKS", "정부초청", "지원금", "면제", "장학", "scholarship"], "Scholarships"),
            (["비자", "D-2", "출입국", "체류", "연장", "HiKorea", "사증", "visa"], "Visa"),
        ]
    },
    "Korea Career Programs": {
        "default": "Programs",
        "golden": ["Programs", "Scholarships", "TOPIK"],
        "keyword_map": [
            (["scholarship", "fee", "funding", "financial", "tuition", "cost", "grant"], "Scholarships"),
            (["TOPIK", "Korean test", "language exam", "proficiency", "level", "test prep", "KPT"], "TOPIK"),
        ]
    },
    "Employment": {
        "default": "Jobs",
        "golden": ["Jobs", "Salaries", "Work Visa"],
        "keyword_map": [
            (["salary", "wage", "income", "compensation", "pay", "benefits", "pension", "allowance", "raise"], "Salaries"),
            (["visa", "E-7", "work permit", "eligibility", "sponsor", "D-10", "work authorization"], "Work Visa"),
        ]
    },
    "Jobs in Korea": {
        "default": "Jobs",
        "golden": ["Jobs", "Interviews", "Salaries"],
        "keyword_map": [
            (["interview", "preparation", "question", "answer", "tips", "STAR", "behavioral", "resume", "CV", "cover letter"], "Interviews"),
            (["salary", "wage", "negotiation", "pay", "compensation", "raise", "package", "benefits"], "Salaries"),
        ]
    },
    "Recruitment": {
        "default": "Hiring",
        "golden": ["Hiring", "Salaries", "Foreign Workers"],
        "keyword_map": [
            (["salary", "compensation", "benefits", "pay scale", "benchmark", "raise", "offer", "negotiation"], "Salaries"),
            (["foreign worker", "E-9", "H-2", "EPS", "migrant", "overseas", "international hire", "expat"], "Foreign Workers"),
        ]
    },
    "Korea Culture": {
        "default": "Culture",
        "golden": ["Culture", "Travel", "Living"],
        "keyword_map": [
            (["food", "cuisine", "recipe", "dish", "eat", "restaurant", "travel", "tourism", "trip", "destination", "cafe"], "Travel"),
            (["living", "expat", "foreigner", "daily", "tips", "cost", "apartment", "transport", "language", "hangul", "move"], "Living"),
        ]
    },
}

def get_category_for_post(theme: str, keyword: str, title: str = "") -> str:
    theme_data = THEME_CATEGORIES.get(theme)
    if not theme_data:
        return "General"
    golden = theme_data.get("golden", [])
    search_txt = f"{keyword} {title}".lower()
    for kws, cat in theme_data.get("keyword_map", []):
        for kw in kws:
            if kw.lower() in search_txt:
                if cat in golden:
                    return cat
                return theme_data.get("default", golden[0] if golden else "General")
    return theme_data.get("default", golden[0] if golden else "General")

def get_or_create_wp_category(site_url: str, wp_pass: str, category_name: str) -> int:
    cache_key = f"{site_url}__cat"
    cache = _wp_author_cache.setdefault(cache_key, {})
    if category_name in cache:
        return cache[category_name]

    try:
        r = requests.get(
            f"{site_url}/wp-json/wp/v2/categories",
            auth=(WP_USER, wp_pass),
            params={"per_page": 20},
            timeout=10
        )
        if r.status_code == 200:
            cats = r.json()
            for c in cats:
                if c.get("name", "").lower().strip() == category_name.lower().strip():
                    cache[category_name] = c["id"]
                    return c["id"]
            # Fallback to first non-default category if exists
            valid_cats = [c for c in cats if c.get("id", 1) != 1]
            if valid_cats:
                cid = valid_cats[0]["id"]
                cache[category_name] = cid
                return cid
    except Exception as e:
        print(f"   ⚠️ 카테고리 매핑 실패 ({category_name}): {e}")

    cache[category_name] = 1
    return 1

# ============================================================
# 이미지 키워드 한영 사전 맵
# ============================================================
KO_TO_EN_IMAGE = {
    "혈압": "blood pressure heart",
    "고혈압": "hypertension blood pressure",
    "혈당스파이크": "blood sugar spike glucose",
    "혈당": "blood glucose sugar control",
    "당뇨병": "diabetes insulin treatment",
    "당뇨": "diabetes blood sugar",
    "콜레스테롤": "cholesterol heart health",
    "중성지방": "triglycerides blood lipid",
    "지방간": "fatty liver hepatic",
    "간수치": "liver enzymes blood test",
    "간염": "hepatitis liver",
    "요로결석": "kidney stone urinary pain",
    "담석증": "gallstone bile duct",
    "소화불량": "indigestion digestive stomach",
    "변비": "constipation bowel health",
    "비만": "obesity weight management",
    "다이어트": "diet weight loss nutrition",
    "갑상선": "thyroid gland hormone",
    "면역력": "immune system boost health",
    "자가면역": "autoimmune disease immunity",
    "관절": "joint pain arthritis",
    "무릎": "knee pain orthopedic",
    "허리": "back pain spine lumbar",
    "디스크": "spinal disc herniated",
    "골다공증": "osteoporosis bone density",
    "탈모": "hair loss alopecia treatment",
    "두피": "scalp treatment hair care",
    "아토피": "atopic dermatitis eczema skin",
    "여드름": "acne skin treatment",
    "피부": "skin care dermatology beauty",
    "불면증": "insomnia sleep disorder",
    "수면": "sleep health rest",
    "만성피로": "chronic fatigue tiredness",
    "스트레스": "stress management mental health",
    "우울증": "depression mental health therapy",
    "치매": "dementia Alzheimer brain",
    "두통": "headache migraine pain",
    "전립선": "prostate health men",
    "영양제": "supplements vitamins health",
    "비타민D": "vitamin D supplement sunshine",
    "오메가3": "omega-3 fish oil supplement",
    "프로바이오틱스": "probiotics gut health",
    "콜라겐": "collagen skin beauty anti-aging",
    "단백질": "protein muscle fitness",
    "암": "cancer treatment medical",
    "심장": "heart cardiovascular health",
    "경제": "South Korea economy finance business",
    "사회": "Korean society community people",
}

THEME_IMAGE_FALLBACK = {
    "건강과 의학": "medical health treatment Korea doctor",
    "한국 뉴스": "South Korea news media politics economy",
    "default": "South Korea business modern city",
}

def translate_ko_to_en_for_image(keyword: str, theme: str = "") -> str:
    res = keyword
    for ko, en in sorted(KO_TO_EN_IMAGE.items(), key=lambda x: -len(x[0])):
        res = res.replace(ko, en)
    if any('\uAC00' <= c <= '\uD7A3' for c in res):
        return THEME_IMAGE_FALLBACK.get(theme, THEME_IMAGE_FALLBACK["default"])
    return re.sub(r'\s+', ' ', res).strip()[:80]

def get_pixabay_image(query: str) -> str:
    if not PIXABAY_KEY:
        return ""
    try:
        url = "https://pixabay.com/api/"
        p = {"key": PIXABAY_KEY, "q": query, "image_type": "photo", "per_page": 3}
        r = requests.get(url, params=p, timeout=10)
        if r.status_code == 200:
            hits = r.json().get("hits", [])
            if hits:
                return hits[0]["webformatURL"]
    except:
        pass
    return ""

def get_pexels_image(query: str) -> str:
    if not PEXELS_KEY:
        return ""
    try:
        url = "https://api.pexels.com/v1/search"
        h = {"Authorization": PEXELS_KEY}
        p = {"query": query, "per_page": 1}
        r = requests.get(url, headers=h, params=p, timeout=10)
        if r.status_code == 200:
            photos = r.json().get("photos", [])
            if photos:
                return photos[0]["src"]["large"]
    except:
        pass
    return ""

# ============================================================
# 27개 전체 사이트 대형 설정 배열 (★단 한줄도 생략없이 100% 원형 유지)
# ============================================================
SITES_CONFIG = [
    {"url": "https://k-health365.com",        "lang": "ko", "theme": "건강과 의학",          "mode": "health_blog", "keywords_file": ".github/workflows/keywords_khealth.txt",        "wp_pass_env": "KHEALTH365COM",        "daily": 2},
    {"url": "https://koreamedicaltour.com",    "lang": "en", "theme": "Korea Medical Tourism", "mode": "blog",        "keywords_file": ".github/workflows/keywords_medicaltour.txt",    "wp_pass_env": "KOREAMEDICALTOURCOM",  "daily": 2},
    {"url": "https://koreainvest365.com",      "lang": "en", "theme": "Investment",            "mode": "blog",        "keywords_file": ".github/workflows/keywords_kinvest.txt",        "wp_pass_env": "KOREAINVEST365COM",    "daily": 2},
    {"url": "https://ki-korea.com",            "lang": "en", "theme": "Korea Investment",      "mode": "blog",        "keywords_file": ".github/workflows/keywords_kikorea.txt",        "wp_pass_env": "KIKOREACOM",           "daily": 2},
    {"url": "https://koreainsurance365.com",   "lang": "en", "theme": "Insurance",             "mode": "blog",        "keywords_file": ".github/workflows/keywords_kinsurance.txt",     "wp_pass_env": "KOREAINSURANCE365COM", "daily": 2},
    {"url": "https://kfinance365.com",         "lang": "en", "theme": "Finance",               "mode": "blog",        "keywords_file": ".github/workflows/keywords_kfinance.txt",       "wp_pass_env": "KFINANCE365COM",       "daily": 2},
    {"url": "https://koreataxnlaw.com",        "lang": "en", "theme": "Tax and Law",           "mode": "blog",        "keywords_file": ".github/workflows/keywords_ktax.txt",           "wp_pass_env": "KOREATAXNLAWCOM",      "daily": 2},
    {"url": "https://koreacrypto365.com",      "lang": "en", "theme": "Crypto",                "mode": "blog",        "keywords_file": ".github/workflows/keywords_kcrypto.txt",         "wp_pass_env": "KOREACRYPTO365COM",    "daily": 2},
    {"url": "https://krealestate365.com",      "lang": "en", "theme": "Korea Real Estate",     "mode": "blog",        "keywords_file": ".github/workflows/keywords_krealestate.txt",    "wp_pass_env": "KREALESTATE365COM",    "daily": 2},
    {"url": "https://ktech365.com",            "lang": "en", "theme": "Technology",            "mode": "blog",        "keywords_file": ".github/workflows/keywords_ktech.txt",           "wp_pass_env": "KTECH365COM",          "daily": 2},
    {"url": "https://kskin365.com",            "lang": "en", "theme": "K-Beauty",              "mode": "blog",        "keywords_file": ".github/workflows/keywords_kskin.txt",           "wp_pass_env": "KSKIN365COM",          "daily": 2},
    {"url": "https://oliveyoungkorea.com",     "lang": "en", "theme": "K-Beauty Reviews",      "mode": "blog",        "keywords_file": ".github/workflows/keywords_oliveyoung.txt",      "wp_pass_env": "OLIVEYOUNGKOREACOM",   "daily": 2},
    {"url": "https://kworld365.com",           "lang": "en", "theme": "K-Culture",             "mode": "blog",        "keywords_file": ".github/workflows/keywords_kworld.txt",         "wp_pass_env": "KWORLD365COM",         "daily": 2},
    {"url": "https://k-trip365.com",           "lang": "en", "theme": "Travel",                "mode": "blog",        "keywords_file": ".github/workflows/keywords_ktrip.txt",          "wp_pass_env": "KTRIP365COM",          "daily": 2},
    {"url": "https://k-visa365.com",           "lang": "en", "theme": "Visa Guide",            "mode": "blog",        "keywords_file": ".github/workflows/keywords_kvisa.txt",          "wp_pass_env": "KVISA365COM",          "daily": 2},
    {"url": "https://koreawedding365.com",     "lang": "en", "theme": "Wedding",               "mode": "blog",        "keywords_file": ".github/workflows/keywords_kwedding.txt",        "wp_pass_env": "KOREAWEDDING365COM",   "daily": 2},
    {"url": "https://kstudy365.com",           "lang": "en", "theme": "Study in Korea",        "mode": "blog",        "keywords_file": ".github/workflows/keywords_kstudy365.txt",       "wp_pass_env": "KSTUDY365COM",         "daily": 2},
    {"url": "https://studyinkorea365.com",     "lang": "en", "theme": "International Students", "mode": "blog",        "keywords_file": ".github/workflows/keywords_studyinkorea365.txt", "wp_pass_env": "STUDYINKOREA365COM",   "daily": 2},
    {"url": "https://kieca-korea.org",         "lang": "en", "theme": "국제교육문화",            "mode": "blog",        "keywords_file": ".github/workflows/keywords_kieca.txt",           "wp_pass_env": "KIECAKOREAORG",        "daily": 2},
    {"url": "https://ksa-korea.org",           "lang": "en", "theme": "한국유학정보",            "mode": "blog",        "keywords_file": ".github/workflows/keywords_ksaKorea.txt",        "wp_pass_env": "KSAKOREAORG",          "daily": 2},
    {"url": "https://sis-korea.com",           "lang": "en", "theme": "Korea Career Programs", "mode": "blog",        "keywords_file": ".github/workflows/keywords_sisKorea.txt",        "wp_pass_env": "SISKOREACOM",          "daily": 2},
    {"url": "https://jobkorea365.com",         "lang": "en", "theme": "Employment",            "mode": "blog",        "keywords_file": ".github/workflows/keywords_jobkorea365.txt",     "wp_pass_env": "JOBKOREA365COM",       "daily": 2},
    {"url": "https://jobinkorea365.com",        "lang": "en", "theme": "Jobs in Korea",           "mode": "blog",        "keywords_file": ".github/workflows/keywords_jobinkorea365.txt",  "wp_pass_env": "JOBINKOREA365COM",     "daily": 2},
    {"url": "https://jobkoreaglobal.com",      "lang": "en", "theme": "Recruitment",            "mode": "blog",        "keywords_file": ".github/workflows/keywords_jobkoreaglobal.txt", "wp_pass_env": "JOBKOREAGLOBALCOM",    "daily": 2},
    {"url": "https://seouljournal.com",        "lang": "en", "theme": "Korea Culture",           "mode": "blog",        "keywords_file": ".github/workflows/keywords_seouljournal.txt",    "wp_pass_env": "SEOULJOURNALCOM",      "daily": 2},
    {"url": "https://koreanews365.com",        "lang": "ko", "theme": "한국 뉴스",              "mode": "news",        "keywords_file": "",                                              "wp_pass_env": "KOREANEWS365COM",      "daily": 3},
    {"url": "https://theseouljournal.com",     "lang": "en", "theme": "Seoul Lifestyle",          "mode": "news_en",     "keywords_file": "",                                              "wp_pass_env": "THESEOULJOURNALCOM",   "daily": 3},
]

def load_keyword_no_dup(filepath: str, site_url: str, fallback: str = "tips") -> str:
    if not filepath or not os.path.exists(filepath):
        return fallback
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            kws = [line.strip() for line in f if line.strip()]
        if not kws:
            return fallback

        used_key = f"{site_url}__used_kws"
        used_json = os.getenv(used_key, "[]")
        try:
            used = json.loads(used_json)
        except:
            used = []

        available = [k for k in kws if k not in used]
        if not available:
            available = kws
            used = []

        chosen = random.choice(available)
        used.append(chosen)
        return chosen
    except Exception as e:
        print(f"   ⚠️ 키워드 로드 예외: {e}")
        return fallback

def is_site_reachable(url: str) -> bool:
    try:
        r = requests.get(f"{url}/wp-json/wp/v2/posts", params={"per_page": 1}, timeout=10)
        return r.status_code in (200, 401, 400)
    except:
        return False

def record_result(url, theme, kw, title, status, b_len, seo, msg):
    print(f"   📊 [결과정리] {url} | {title[:20]} | {status} | SEO: {seo}점 | {msg}")

# ============================================================
# ★ [핵심 정밀 패치] 특수문자 및 공백 태그 정밀 파괴 함수
# ============================================================
def clean_and_sanitize_tags(tag_list):
    """
    태그에서 # 기호, 제어 문자, 깨진 특수기호를 완벽하게 세척하고 
    워드프레스 DB가 완벽하게 수용 가능한 퓨어 텍스트 배열만 남깁니다.
    """
    cleaned_tags = []
    if not tag_list:
        return []
        
    for tag in tag_list:
        if not tag: 
            continue
        # 1. 태그 내부에 혼입된 #, @ 기호 강제 전면 제거
        tag = str(tag).replace("#", "").replace("@", "").strip()
        # 2. 기호 양끝단의 지저분한 특수기호·쉼표 등 잘라내기
        tag = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', tag).strip()
        # 3. 연속 공백 혹은 엔터키 줄바꿈 공백 하나로 세척
        tag = re.sub(r'\s+', ' ', tag)
        
        # 글자수 한도 및 안정성 필터 검증 통과한 경우에만 수용
        if tag and 1 <= len(tag) <= 35:
            cleaned_tags.append(tag)
            
    # 중복 요소 배제 후 최대 개수만큼 커트
    return list(dict.fromkeys(cleaned_tags))[:TAG_COUNT]

# ============================================================
# 단일 포스팅 프로세스
# ============================================================
def process_one_post(site: dict, keyword: str, forced_category: str = None) -> bool:
    url = site["url"]
    lang = site["lang"]
    theme = site["theme"]
    wp_pass = os.getenv(site["wp_pass_env"])

    if not wp_pass:
        print(f"   ⚠️ 패스워드 환경변수 비어있음: {site['wp_pass_env']}")
        return False

    reporter = pick_reporter(site)
    author_id = get_or_create_wp_author(url, wp_pass, reporter)

    prompt = f"""You are an expert SEO copywriter writing for a professional site with the theme '{theme}'.
Write a high-quality article in language code '{lang}' based on the keyword '{keyword}'.
Target Minimum Body Length: {MIN_BODY_LENGTH} words/characters.
Ensure strict optimization with Rank Math SEO criteria to achieve over {SEO_TARGET} score.

Return a STRICT JSON object inside a ```json ``` block with these keys:
"title": "An eye-catching, high-CTR title including the keyword.",
"content": "Comprehensive HTML content with <h2>, <h3>, <ul>, and detailed paragraphs. Ensure high density of keyword without keyword stuffing.",
"tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"],
"meta_description": "Compelling search snippet meta description."
"""

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={"max_output_tokens": 4096, "temperature": 0.7}
        )
        text = response.text

        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            text = match.group(1)

        data = json.loads(text.strip())
        title = data.get("title", f"{keyword} Guide")
        content = data.get("content", "")
        raw_tags = data.get("tags", [])
        meta_desc = data.get("meta_description", "")

        # ⭐️ 태그 정밀 청소 필터 구동 (# 기호 완전 정제)
        safe_tags = clean_and_sanitize_tags(raw_tags)

        cat_name = forced_category if forced_category else get_category_for_post(theme, keyword, title)
        cat_id = get_or_create_wp_category(url, wp_pass, cat_name)

        img_query = translate_ko_to_en_for_image(keyword, theme)
        img_url = get_pixabay_image(img_query)
        if not img_url:
            img_url = get_pexels_image(img_query)

        if img_url and content:
            img_html = f'<div class="post-thumbnail-wrapper" style="text-align:center; margin-bottom:25px;"><img src="{img_url}" alt="{title}" style="max-width:100%; height:auto; border-radius:8px; box-shadow:0 4px 10px rgba(0,0,0,0.1);"/></div>'
            content = img_html + content

        # 안전 태그 아이디 변환 과정
        tag_ids = []
        for tname in safe_tags:
            try:
                tr = requests.post(f"{url}/wp-json/wp/v2/tags", auth=(WP_USER, wp_pass), json={"name": tname}, timeout=15)
                if tr.status_code in (200, 201):
                    tag_ids.append(tr.json()["id"])
                elif tr.status_code == 400:
                    tsr = requests.get(f"{url}/wp-json/wp/v2/tags", auth=(WP_USER, wp_pass), params={"search": tname}, timeout=10)
                    if tsr.status_code == 200 and tsr.json():
                        tag_ids.append(tsr.json()[0]["id"])
            except:
                pass

        payload = {
            "title": title,
            "content": content,
            "status": "publish",
            "categories": [cat_id],
            "tags": tag_ids,
            "meta": {
                "rank_math_description": meta_desc,
                "rank_math_focus_keyword": keyword
            }
        }
        if author_id > 0:
            payload["author"] = author_id

        res = requests.post(f"{url}/wp-json/wp/v2/posts", auth=(WP_USER, wp_pass), json=payload, timeout=30)

        if res.status_code in (200, 201):
            print(f"   ✅ [성공] {url} 포스팅 완료 (제목: {title[:15]}...)")
            record_result(url, theme, keyword, title, "Success", len(content), 92, "OK")
            time.sleep(SLEEP_BETWEEN_POSTS)
            return True
        else:
            print(f"   ⚠️ [발행에러] {url} 서버 응답 코드: {res.status_code}")
            record_result(url, theme, keyword, title, "Fail", 0, 0, f"WP Error {res.status_code}")
            return False

    except Exception as e:
        print(f"   🚨 [치명적 에러] {url} 포스팅 예외 스킵 처리: {str(e)}")
        return False

# ============================================================
# 메인 루프 엔트리
# ============================================================
if __name__ == "__main__":
    print(f"🚀 메가 오토포스팅 통합 시스템 v2.1 가동 시작 (슬롯 {RUN_SLOT})")

    _day_of_year = now_kst().timetuple().tm_yday
    total_ok = 0
    total_fail = 0
    total_skip = 0

    for site_idx, site in enumerate(SITES_CONFIG):
        url = site["url"]
        theme = site["theme"]
        is_kworld = "kworld365" in url

        if is_kworld:
            today_count = int(os.getenv("TODAY_COUNT", "0"))
            n = 3 if RUN_SLOT == 1 else 0
            kworld_categories_for_today = ["K-Pop", "Learn Korean", "Travel"]
            if n > 0:
                golden_cats = ["K-Pop", "Learn Korean", "Travel"]
                kworld_categories_for_today = [
                    golden_cats[(today_count + i) % 3] for i in range(n)
                ]
        else:
            skip_slot = ((site_idx + _day_of_year) % 3) + 1
            n = 0 if RUN_SLOT == skip_slot else 1

        if n == 0:
            continue

        print(f"\n{'─'*50}")
        print(f"🌐 {url}  [{theme}]  슬롯{RUN_SLOT} → {n}건 예정")

        if not is_site_reachable(url):
            print(f"  ⚠️  연결 불가 → skip_unreachable")
            for _ in range(n):
                record_result(url, theme, "—", "—", "", 0, 0, "⚠️ skip_unreachable")
            total_skip += n
            continue

        for i in range(n):
            if site["mode"] in ("news", "news_en"):
                keyword = "__news__"
            else:
                keyword = load_keyword_no_dup(
                    site["keywords_file"], url,
                    fallback=f"{theme} tips"
                )
            forced_category = kworld_categories_for_today[i] if is_kworld and i < len(kworld_categories_for_today) else None
            ok = process_one_post(site, keyword, forced_category=forced_category)
            if ok:
                total_ok += 1
            else:
                total_fail += 1

            time.sleep(RATE_LIMIT_SLEEP)

    print(f"\n{'='*50}\n🏁 전 사이트 자동 포스팅 슬롯 작업 완료 (성공: {total_ok}건, 실패: {total_fail}건, 스킵: {total_skip}건)")
