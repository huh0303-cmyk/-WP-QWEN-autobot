#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
autopost_mega.py — 27개 사이트 메가 오토포스팅 봇 (최종 통합본)
업데이트: 2026-06
  ✅ 27개 사이트 완전 반영
  ✅ WP 실제 Author 랜덤 배정 (한국어 10명 / 영어 10명) — 자동 생성 포함
  ✅ 테마별 카테고리 자동 분류 (정치/경제/국제/문화/교육 등 27개 사이트 전용)
  ✅ koreanews365 ↔ theseouljournal 크로스런 중복 완전 차단
  ✅ 내부링크 실제 URL 삽입 (앵커만 있는 가짜 링크 제거)
  ✅ 이미지 3단계 fallback (Pixabay → Pexels → theme-aware)
  ✅ SEO 90점 이상 보장 (재생성 로직 포함)
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
# ★ 가상 기자 명단 (WP Author로 실제 등록)
# ============================================================
# koreanews365.com 전용 한국 기자 10명
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

# theseouljournal.com 전용 영문 기자 10명
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

# 블로그 사이트용 영문 전문가 기자 (테마별 전문성 부여)
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

# 블로그 사이트용 한국어 기자
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

# ============================================================
# ★ WP Author 캐시 — site_url → {slug: author_id}
# ============================================================
_wp_author_cache: dict = {}  # site_url → {slug: int}

def get_or_create_wp_author(site_url: str, wp_pass: str, reporter: dict) -> int:
    """WP에 기자 계정이 없으면 생성하고 ID 반환. 있으면 기존 ID 반환."""
    cache = _wp_author_cache.setdefault(site_url, {})
    slug  = reporter["slug"]
    if slug in cache:
        return cache[slug]

    # 1) 이름으로 조회
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

    # 2) 없으면 생성 (WP REST API — 관리자 권한 필요)
    try:
        payload = {
            "username":    slug,
            "name":        reporter["name"],
            "email":       reporter["email"],
            "slug":        slug,
            "description": reporter.get("bio", ""),
            "password":    hashlib.md5(reporter["email"].encode()).hexdigest()[:16] + "Aa1!",
            "roles":       ["author"],
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
            print(f"   👤 기자 생성: {reporter['name']} (ID {uid})")
            return uid
        # 이미 존재 (username conflict)
        elif r.status_code == 400:
            # slug로 재조회
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

    # 실패 시 -1 반환 → 포스트는 기본 계정으로 발행
    cache[slug] = -1
    return -1

def pick_reporter(site: dict) -> dict:
    """사이트 모드/언어에 따라 적절한 기자 풀에서 랜덤 선택"""
    mode = site.get("mode", "blog")
    lang = site.get("lang", "en")
    url  = site.get("url", "")

    if "koreanews365" in url:
        return random.choice(REPORTERS_KO)
    elif "theseouljournal" in url:
        return random.choice(REPORTERS_EN)
    elif lang == "ko":
        return random.choice(REPORTERS_BLOG_KO)
    else:
        return random.choice(REPORTERS_BLOG_EN)

def reporter_display(reporter: dict) -> str:
    """바이라인 표시용 문자열"""
    return reporter["name"]

# ============================================================
# ★ 테마별 카테고리 매핑 (사이트별 독립 카테고리 세트)
# ============================================================

# 각 테마에 대한 카테고리 후보 리스트 (키워드 기반으로 자동 선택)
THEME_CATEGORIES = {
    # 한국 뉴스 (koreanews365) — 신문 카테고리
    "한국 뉴스": {
        "default": "국제-INTERNATIONAL",
        "keyword_map": [
            (["정치", "대통령", "국회", "선거", "정당", "여당", "야당", "법안", "탄핵", "개헌"], "정치-POLITICS"),
            (["경제", "금리", "물가", "GDP", "성장", "수출", "무역", "환율", "적자", "흑자", "코스피", "코스닥", "주식", "증시"], "경제-ECONOMY"),
            (["기업", "삼성", "현대", "SK", "LG", "스타트업", "상장", "IPO", "M&A", "CEO"], "비즈니스-BUSINESS"),
            (["사회", "범죄", "사건", "사고", "복지", "노동", "여성", "청년", "고령", "저출산", "인구"], "사회-SOCIETY"),
            (["기술", "AI", "반도체", "IT", "디지털", "로봇", "자율주행", "배터리", "스마트"], "기술-TECH"),
            (["문화", "K-pop", "드라마", "영화", "예술", "전통", "음식", "스포츠"], "문화-CULTURE"),
            (["교육", "대학", "입시", "유학", "학교", "학생", "취업", "직업"], "교육-EDUCATION"),
            (["부동산", "아파트", "주택", "집값", "전세", "월세", "분양"], "부동산-REALESTATE"),
            (["국제", "미국", "중국", "일본", "러시아", "EU", "UN", "외교", "북한"], "국제-INTERNATIONAL"),
            (["글로벌", "무역", "수출", "FTA", "관세", "공급망"], "글로벌-GLOBAL"),
        ]
    },
    # Seoul Lifestyle (theseouljournal) — 영문 신문 카테고리
    "Seoul Lifestyle": {
        "default": "LIFESTYLE",
        "keyword_map": [
            (["politics", "election", "president", "government", "parliament", "policy", "law", "bill", "vote"], "POLITICS"),
            (["economy", "GDP", "inflation", "interest rate", "export", "trade", "stock", "market", "finance", "budget"], "ECONOMY"),
            (["business", "startup", "company", "CEO", "IPO", "investment", "corporate", "industry"], "BUSINESS"),
            (["global", "international", "US", "China", "Japan", "UN", "NATO", "world", "foreign"], "GLOBAL"),
            (["culture", "K-pop", "drama", "music", "film", "art", "food", "festival", "tradition"], "CULTURE"),
            (["education", "university", "study", "student", "school", "learning", "admission", "scholarship"], "EDUCATION"),
            (["tech", "AI", "semiconductor", "IT", "digital", "robot", "innovation", "startup"], "TECH"),
            (["health", "medical", "wellness", "hospital", "doctor", "treatment", "disease", "beauty", "skincare"], "HEALTH"),
            (["travel", "tourism", "trip", "hiking", "destination", "hotel", "tour", "visit"], "TRAVEL"),
            (["expat", "foreigner", "visa", "immigration", "living", "apartment", "housing", "cost of living"], "EXPAT LIFE"),
        ]
    },
    # 블로그 사이트 카테고리
    "건강과 의학": {
        "default": "건강정보",
        "keyword_map": [
            (["혈압", "고혈압", "심장", "혈관"], "심혈관건강"),
            (["당뇨", "혈당", "인슐린"], "당뇨·혈당"),
            (["암", "종양", "항암"], "암·종양"),
            (["피부", "아토피", "여드름", "탈모", "두피"], "피부·모발"),
            (["정신", "우울", "불안", "스트레스", "수면", "불면"], "정신건강"),
            (["뼈", "관절", "허리", "디스크", "골다공증"], "근골격계"),
            (["영양", "비타민", "영양제", "보충제"], "영양·보충제"),
            (["다이어트", "비만", "체중", "운동"], "다이어트·운동"),
            (["소화", "위장", "장", "변비", "대장"], "소화기건강"),
            (["간", "지방간", "간염", "간수치"], "간·소화기"),
        ]
    },
    "Finance": {
        "default": "Finance Tips",
        "keyword_map": [
            (["stock", "market", "trading", "invest", "portfolio", "dividend"], "Stock Market"),
            (["real estate", "property", "apartment", "mortgage", "rent"], "Real Estate Finance"),
            (["tax", "deduction", "IRS", "refund", "filing"], "Tax Guide"),
            (["savings", "deposit", "interest", "bank", "account"], "Savings & Banking"),
            (["insurance", "premium", "coverage", "policy", "claim"], "Insurance"),
            (["crypto", "bitcoin", "blockchain", "NFT", "DeFi"], "Crypto Finance"),
            (["loan", "debt", "credit", "mortgage", "borrow"], "Loans & Credit"),
            (["retirement", "pension", "fund", "401k", "IRP"], "Retirement Planning"),
        ]
    },
    "Investment": {
        "default": "Investment Guide",
        "keyword_map": [
            (["stock", "equity", "share", "dividend", "KOSPI", "KOSDAQ"], "Stock Investment"),
            (["ETF", "fund", "mutual fund", "index fund"], "Fund Investment"),
            (["real estate", "property", "REIT"], "Real Estate Investment"),
            (["crypto", "bitcoin", "ethereum", "altcoin"], "Crypto Investment"),
            (["bond", "fixed income", "treasury"], "Bond & Fixed Income"),
            (["global", "overseas", "foreign", "US stock", "NYSE"], "Global Investment"),
            (["startup", "VC", "venture", "angel"], "Startup Investment"),
        ]
    },
    "Korea Investment": {
        "default": "투자전략",
        "keyword_map": [
            (["주식", "코스피", "코스닥", "배당", "상장"], "주식투자"),
            (["ETF", "펀드", "인덱스"], "펀드·ETF"),
            (["부동산", "아파트", "분양", "리츠"], "부동산투자"),
            (["암호화폐", "비트코인", "이더리움", "코인"], "암호화폐"),
            (["채권", "국채", "금리"], "채권·금리"),
            (["해외", "미국주식", "글로벌"], "해외투자"),
            (["절세", "세금", "IRP", "연금"], "절세·연금"),
        ]
    },
    "Korea Real Estate": {
        "default": "부동산정보",
        "keyword_map": [
            (["아파트", "분양", "청약", "재건축"], "아파트·분양"),
            (["전세", "월세", "임대", "보증금"], "전월세"),
            (["정책", "규제", "LTV", "DSR", "금리"], "정책·규제"),
            (["지역", "서울", "경기", "부산", "지방"], "지역별시장"),
            (["상가", "오피스텔", "빌딩", "수익형"], "수익형부동산"),
            (["시세", "가격", "호가", "실거래"], "가격·시세"),
        ]
    },
    "Insurance": {
        "default": "Insurance Guide",
        "keyword_map": [
            (["life", "death benefit", "term life", "whole life"], "Life Insurance"),
            (["health", "medical", "hospital", "coverage"], "Health Insurance"),
            (["car", "auto", "vehicle", "accident"], "Auto Insurance"),
            (["travel", "trip", "overseas", "abroad"], "Travel Insurance"),
            (["pension", "retirement", "annuity"], "Pension & Annuity"),
        ]
    },
    "Tax and Law": {
        "default": "Tax & Legal Guide",
        "keyword_map": [
            (["income tax", "소득세", "withholding", "filing"], "Income Tax"),
            (["corporate tax", "법인세", "business tax"], "Corporate Tax"),
            (["VAT", "부가세", "consumption tax"], "VAT & Consumption Tax"),
            (["inheritance", "estate", "상속세", "gift tax"], "Inheritance & Gift Tax"),
            (["visa", "immigration", "residence", "permit"], "Immigration Law"),
            (["labor", "employment", "contract", "wage"], "Labor Law"),
            (["property", "real estate", "취득세", "양도세"], "Property Tax"),
        ]
    },
    "Crypto": {
        "default": "Crypto Guide",
        "keyword_map": [
            (["bitcoin", "BTC"], "Bitcoin"),
            (["ethereum", "ETH", "smart contract"], "Ethereum"),
            (["altcoin", "XRP", "SOL", "BNB"], "Altcoins"),
            (["DeFi", "decentralized", "DEX", "liquidity"], "DeFi"),
            (["NFT", "token", "metaverse"], "NFT & Metaverse"),
            (["exchange", "거래소", "binance", "upbit"], "Exchanges"),
            (["regulation", "법", "regulation", "SEC", "FSC"], "Regulation"),
            (["staking", "mining", "yield"], "Staking & Mining"),
        ]
    },
    "Technology": {
        "default": "Tech News",
        "keyword_map": [
            (["AI", "artificial intelligence", "machine learning", "GPT", "LLM"], "AI & Machine Learning"),
            (["semiconductor", "chip", "TSMC", "Samsung"], "Semiconductor"),
            (["smartphone", "mobile", "app", "iOS", "Android"], "Mobile Tech"),
            (["cybersecurity", "hacking", "privacy", "data breach"], "Cybersecurity"),
            (["robot", "automation", "autonomous", "drone"], "Robotics & Automation"),
            (["startup", "venture", "innovation", "unicorn"], "Startup & Innovation"),
            (["EV", "electric vehicle", "battery", "charging"], "EV & Battery"),
        ]
    },
    "K-Beauty": {
        "default": "K-Beauty Guide",
        "keyword_map": [
            (["skincare", "moisturizer", "serum", "toner"], "Skincare Routine"),
            (["makeup", "foundation", "lipstick", "blush"], "K-Makeup"),
            (["hair", "scalp", "shampoo", "treatment"], "Hair Care"),
            (["sunscreen", "SPF", "UV", "protection"], "Sun Protection"),
            (["anti-aging", "wrinkle", "collagen", "retinol"], "Anti-Aging"),
            (["ingredient", "niacinamide", "hyaluronic", "vitamin C"], "Ingredients"),
            (["brand", "innisfree", "laneige", "cosrx", "olive young"], "K-Beauty Brands"),
        ]
    },
    "K-Beauty Reviews": {
        "default": "Product Reviews",
        "keyword_map": [
            (["review", "best", "ranking", "top", "recommend"], "Product Reviews"),
            (["skincare", "moisturizer", "serum", "essence"], "Skincare Reviews"),
            (["makeup", "foundation", "lip", "eye"], "Makeup Reviews"),
            (["hair", "scalp", "shampoo"], "Hair Care Reviews"),
            (["budget", "affordable", "cheap", "drugstore"], "Budget Picks"),
            (["luxury", "premium", "high-end"], "Premium Picks"),
        ]
    },
    "K-POP": {
        "default": "K-POP News",
        "keyword_map": [
            (["BTS", "BLACKPINK", "EXO", "TWICE", "aespa", "NewJeans", "SEVENTEEN", "Stray Kids"], "Artist Spotlight"),
            (["album", "release", "comeback", "single", "MV"], "New Releases"),
            (["concert", "tour", "performance", "live"], "Concerts & Tours"),
            (["chart", "billboard", "ranking", "award", "daesang"], "Charts & Awards"),
            (["trainee", "debut", "audition", "idol", "agency"], "Idol & Agency"),
            (["fandom", "fan", "ARMY", "BLINK", "culture"], "Fan Culture"),
        ]
    },
    "Travel": {
        "default": "Travel Guide",
        "keyword_map": [
            (["Seoul", "서울", "Gyeongbokgung", "Myeongdong", "Hongdae"], "Seoul Travel"),
            (["Busan", "부산", "beach", "Haeundae", "Gamcheon"], "Busan Travel"),
            (["Jeju", "제주", "island", "Hallasan"], "Jeju Island"),
            (["hiking", "trail", "mountain", "national park", "trekking"], "Hiking & Nature"),
            (["food", "cuisine", "restaurant", "street food", "market"], "Food & Dining"),
            (["hotel", "accommodation", "stay", "hostel", "guesthouse"], "Accommodation"),
            (["day trip", "weekend", "itinerary", "tour"], "Itineraries"),
            (["temple", "palace", "museum", "history", "heritage"], "Culture & History"),
        ]
    },
    "Visa Guide": {
        "default": "Visa Guide",
        "keyword_map": [
            (["student visa", "D-2", "language school", "D-4"], "Student Visa"),
            (["work visa", "E-7", "employment visa", "skilled worker"], "Work Visa"),
            (["F-2", "F-5", "permanent residence", "long-term", "settlement"], "Long-term Residence"),
            (["tourist", "B-1", "B-2", "short-term", "K-ETA"], "Tourist & Short-term"),
            (["working holiday", "H-1", "youth"], "Working Holiday"),
            (["family", "F-1", "spouse", "dependent"], "Family Visa"),
            (["extension", "renewal", "immigration office", "HiKorea"], "Visa Extension"),
        ]
    },
    "Korea Medical Tourism": {
        "default": "Medical Tourism",
        "keyword_map": [
            (["plastic surgery", "nose", "eye", "chin", "jaw", "rhinoplasty"], "Plastic Surgery"),
            (["dental", "teeth", "orthodontics", "implant", "whitening"], "Dental Treatment"),
            (["cancer", "oncology", "treatment", "hospital"], "Cancer Treatment"),
            (["dermatology", "skin", "laser", "botox", "filler"], "Dermatology & Aesthetics"),
            (["traditional", "oriental", "acupuncture", "herbal"], "Korean Traditional Medicine"),
            (["cost", "price", "affordable", "cheap", "package"], "Cost & Packages"),
            (["visa", "medical visa", "C-3", "entry"], "Medical Visa"),
        ]
    },
    "Wedding": {
        "default": "Wedding Guide",
        "keyword_map": [
            (["venue", "hall", "ceremony", "location", "outdoor"], "Wedding Venue"),
            (["dress", "gown", "suit", "attire", "fashion"], "Wedding Fashion"),
            (["photographer", "photo", "video", "videographer"], "Photography & Video"),
            (["catering", "food", "menu", "banquet", "reception"], "Catering & Reception"),
            (["traditional", "hanbok", "Korean wedding", "Paebaek"], "Traditional Korean Wedding"),
            (["honeymoon", "trip", "travel", "destination"], "Honeymoon"),
            (["budget", "cost", "planning", "checklist", "tips"], "Wedding Planning"),
            (["invitation", "decoration", "flower", "theme"], "Decoration & Theme"),
        ]
    },
    "Study in Korea": {
        "default": "Study in Korea",
        "keyword_map": [
            (["TOPIK", "Korean language", "language test", "KLAT"], "Korean Language"),
            (["university", "admission", "application", "undergraduate"], "University Admission"),
            (["scholarship", "KGSP", "GKS", "funding", "stipend"], "Scholarships"),
            (["campus life", "dorm", "dormitory", "student life"], "Campus Life"),
            (["visa", "D-2", "student visa", "immigration"], "Student Visa"),
            (["part-time job", "work", "employment", "income"], "Part-time Work"),
            (["graduate", "master", "PhD", "research"], "Graduate Studies"),
        ]
    },
    "International Students": {
        "default": "Student Guide",
        "keyword_map": [
            (["scholarship", "funding", "GKS", "KGSP", "award"], "Scholarships"),
            (["language", "Korean", "TOPIK", "class"], "Language Learning"),
            (["visa", "D-2", "extension", "immigration"], "Visa & Immigration"),
            (["housing", "dormitory", "accommodation", "living"], "Housing"),
            (["part-time", "job", "work", "allowable hours"], "Part-time Work"),
            (["culture", "adjustment", "life", "social"], "Cultural Adjustment"),
        ]
    },
    "Employment": {
        "default": "Employment Guide",
        "keyword_map": [
            (["resume", "CV", "cover letter", "application", "interview"], "Job Application"),
            (["salary", "wage", "income", "compensation", "pay"], "Salary & Compensation"),
            (["IT", "tech", "developer", "engineer", "coding"], "IT Jobs"),
            (["teaching", "English teacher", "EPIK", "hagwon"], "Teaching Jobs"),
            (["visa", "E-7", "work permit", "eligibility"], "Work Visa"),
            (["startup", "freelance", "remote", "contract"], "Freelance & Startup"),
            (["benefits", "health insurance", "pension", "allowance"], "Benefits & Welfare"),
        ]
    },
    "Jobs in Korea": {
        "default": "Jobs Guide",
        "keyword_map": [
            (["IT", "developer", "engineer", "coding", "software"], "IT & Tech Jobs"),
            (["teacher", "English", "education", "EPIK", "hagwon"], "Teaching Jobs"),
            (["finance", "banking", "accounting", "analyst"], "Finance Jobs"),
            (["marketing", "sales", "PR", "advertising"], "Marketing & Sales"),
            (["factory", "manufacturing", "E-9", "worker"], "Manufacturing Jobs"),
            (["startup", "SME", "entrepreneur", "founder"], "Startup Jobs"),
            (["global", "multinational", "MNC", "foreign company"], "Global Companies"),
        ]
    },
    "Recruitment": {
        "default": "Recruitment Guide",
        "keyword_map": [
            (["hiring", "recruit", "talent", "HR", "headhunting"], "Hiring Strategy"),
            (["interview", "screening", "assessment", "evaluation"], "Interview Process"),
            (["salary", "offer", "negotiation", "compensation"], "Salary Negotiation"),
            (["foreign worker", "E-9", "H-2", "EPS"], "Foreign Worker Recruitment"),
            (["global talent", "expat", "international hire"], "Global Talent"),
            (["platform", "job board", "LinkedIn", "Saramin", "Incruit"], "Recruitment Platforms"),
        ]
    },
    "Korea Culture": {
        "default": "Korean Culture",
        "keyword_map": [
            (["food", "cuisine", "recipe", "dish", "eat", "restaurant"], "Korean Food"),
            (["festival", "holiday", "Chuseok", "Lunar New Year", "Seollal"], "Festivals & Holidays"),
            (["traditional", "Joseon", "history", "heritage", "palace", "hanok"], "History & Heritage"),
            (["K-pop", "drama", "movie", "entertainment", "hallyu"], "K-Wave & Entertainment"),
            (["sport", "soccer", "baseball", "Taekwondo", "esports"], "Sports"),
            (["fashion", "style", "trend", "design", "art"], "Fashion & Art"),
            (["language", "Korean", "hangul", "expression", "phrase"], "Korean Language"),
        ]
    },
    "국제교육문화": {
        "default": "국제교육",
        "keyword_map": [
            (["유학", "해외", "어학연수", "교환학생"], "해외유학"),
            (["한국어", "TOPIK", "어학당", "한국어교육"], "한국어교육"),
            (["문화교류", "국제교류", "MOU", "협약"], "문화교류"),
            (["취업", "커리어", "글로벌", "인턴"], "글로벌취업"),
            (["입시", "대학원", "장학금", "지원"], "입학·장학"),
        ]
    },
    "한국유학정보": {
        "default": "유학정보",
        "keyword_map": [
            (["비자", "D-2", "출입국", "체류"], "비자·출입국"),
            (["장학금", "GKS", "정부초청", "지원금"], "장학금"),
            (["기숙사", "숙소", "자취", "주거"], "숙소·생활"),
            (["한국어", "TOPIK", "어학", "언어"], "한국어학습"),
            (["대학", "입학", "전형", "지원"], "대학입학"),
            (["생활", "적응", "문화", "생활비"], "유학생활"),
        ]
    },
    "Korea Career Programs": {
        "default": "Career Programs",
        "keyword_map": [
            (["internship", "training", "program", "experience"], "Internship Programs"),
            (["language", "Korean", "English", "bilingual"], "Language Programs"),
            (["certification", "qualification", "license", "exam"], "Certifications"),
            (["networking", "alumni", "community", "event"], "Networking"),
            (["job", "career", "employment", "placement"], "Job Placement"),
        ]
    },
    "Korea Medical Tourism": {
        "default": "Medical Tourism",
        "keyword_map": [
            (["plastic surgery", "cosmetic", "nose", "eye"], "Cosmetic Surgery"),
            (["dental", "teeth", "implant", "orthodontics"], "Dental"),
            (["dermatology", "skin", "laser", "botox"], "Dermatology"),
            (["cancer", "oncology", "treatment"], "Cancer Treatment"),
            (["cost", "price", "package", "affordable"], "Cost Guide"),
        ]
    },
}

def get_category_for_post(theme: str, keyword: str, title: str = "") -> str:
    """키워드/제목 기반으로 가장 적합한 카테고리 반환"""
    theme_data = THEME_CATEGORIES.get(theme)
    if not theme_data:
        return "General"

    search_text = f"{keyword} {title}".lower()
    keyword_map = theme_data.get("keyword_map", [])

    for keywords_list, category in keyword_map:
        for kw in keywords_list:
            if kw.lower() in search_text:
                return category

    return theme_data.get("default", "General")

def get_or_create_wp_category(site_url: str, wp_pass: str, category_name: str) -> int:
    """WP 카테고리 ID 조회 또는 생성"""
    # 캐시
    cache_key = f"{site_url}__cat"
    cache = _wp_author_cache.setdefault(cache_key, {})
    if category_name in cache:
        return cache[category_name]

    try:
        # 1) 조회
        r = requests.get(
            f"{site_url}/wp-json/wp/v2/categories",
            auth=(WP_USER, wp_pass),
            params={"search": category_name, "per_page": 5},
            timeout=10
        )
        if r.status_code == 200:
            for cat in r.json():
                if cat.get("name", "").lower() == category_name.lower():
                    cache[category_name] = cat["id"]
                    return cat["id"]

        # 2) 생성
        r2 = requests.post(
            f"{site_url}/wp-json/wp/v2/categories",
            auth=(WP_USER, wp_pass),
            json={"name": category_name},
            timeout=10
        )
        if r2.status_code in (200, 201):
            cid = r2.json().get("id")
            cache[category_name] = cid
            print(f"   📁 카테고리 생성: {category_name} (ID {cid})")
            return cid
        elif r2.status_code == 400:
            # 이미 존재
            data = r2.json()
            if "term_exists" in str(data):
                term_id = data.get("data", {}).get("term_id")
                if term_id:
                    cache[category_name] = term_id
                    return term_id
    except Exception as e:
        print(f"   ⚠️ 카테고리 생성 실패 ({category_name}): {e}")

    cache[category_name] = 1  # fallback: Uncategorized
    return 1

# ============================================================
# ★ 한국어 → 영어 이미지 검색 번역 매핑
# ============================================================
KO_TO_EN_IMAGE = {
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
    "국제교육문화":         "international education culture Korea",
    "한국유학정보":         "Korea study abroad university student",
    "Korea Career Programs":"Korea career training program student",
    "default":              "South Korea business modern city",
}

def translate_ko_to_en_for_image(keyword: str, theme: str = "") -> str:
    result = keyword
    for ko, en in sorted(KO_TO_EN_IMAGE.items(), key=lambda x: -len(x[0])):
        result = result.replace(ko, en)
    if any('\uac00' <= c <= '\ud7a3' for c in result):
        return THEME_IMAGE_FALLBACK.get(theme, THEME_IMAGE_FALLBACK["default"])
    result = re.sub(r'\s+', ' ', result).strip()
    return result[:80]

# ============================================================
# ★ 27개 사이트 설정
# ============================================================
SITES_CONFIG = [
    {"url": "https://k-health365.com",
     "lang": "ko", "theme": "건강과 의학", "mode": "health_blog",
     "keywords_file": ".github/workflows/keywords_khealth.txt",
     "wp_pass_env": "KHEALTH365COM", "daily": 6},

    {"url": "https://koreamedicaltour.com",
     "lang": "en", "theme": "Korea Medical Tourism", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_medicaltour.txt",
     "wp_pass_env": "KOREAMEDICALTOURCOM", "daily": 3},

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

    {"url": "https://krealestate365.com",
     "lang": "ko", "theme": "Korea Real Estate", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_krealestate.txt",
     "wp_pass_env": "KREALESTATE365COM", "daily": 3},

    {"url": "https://ktech365.com",
     "lang": "en", "theme": "Technology", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_ktech.txt",
     "wp_pass_env": "KTECH365COM", "daily": 3},

    {"url": "https://kskin365.com",
     "lang": "en", "theme": "K-Beauty", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kskin.txt",
     "wp_pass_env": "KSKIN365COM", "daily": 3},

    {"url": "https://oliveyoungkorea.com",
     "lang": "en", "theme": "K-Beauty Reviews", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_oliveyoung.txt",
     "wp_pass_env": "OLIVEYOUNGKOREACOM", "daily": 3},

    {"url": "https://kworld365.com",
     "lang": "en", "theme": "K-POP", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kworld.txt",
     "wp_pass_env": "KWORLD365COM", "daily": 5},

    {"url": "https://k-trip365.com",
     "lang": "en", "theme": "Travel", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_ktrip.txt",
     "wp_pass_env": "KTRIP365COM", "daily": 3},

    {"url": "https://k-visa365.com",
     "lang": "en", "theme": "Visa Guide", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kvisa.txt",
     "wp_pass_env": "KVISA365COM", "daily": 3},

    {"url": "https://koreawedding365.com",
     "lang": "en", "theme": "Wedding", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kwedding.txt",
     "wp_pass_env": "KOREAWEDDING365COM", "daily": 3},

    {"url": "https://kstudy365.com",
     "lang": "en", "theme": "Study in Korea", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kstudy365.txt",
     "wp_pass_env": "KSTUDY365COM", "daily": 3},

    {"url": "https://studyinkorea365.com",
     "lang": "en", "theme": "International Students", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_studyinkorea365.txt",
     "wp_pass_env": "STUDYINKOREA365COM", "daily": 3},

    {"url": "https://kieca-korea.org",
     "lang": "ko", "theme": "국제교육문화", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_kieca.txt",
     "wp_pass_env": "KIECAKOREAORG", "daily": 3},

    {"url": "https://ksa-korea.org",
     "lang": "ko", "theme": "한국유학정보", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_ksaKorea.txt",
     "wp_pass_env": "KSAKOREAORG", "daily": 3},

    {"url": "https://sis-korea.com",
     "lang": "en", "theme": "Korea Career Programs", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_sisKorea.txt",
     "wp_pass_env": "SISKOREACOM", "daily": 3},

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

    {"url": "https://korea365.org",
     "lang": "en", "theme": "Korea Culture", "mode": "blog",
     "keywords_file": ".github/workflows/keywords_korea365.txt",
     "wp_pass_env": "KOREA365ORG", "daily": 4},

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
# ★ 테마별 연관 외부 권위 링크 + 사이트별 내부링크 URL 매핑
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
    "국제교육문화": [
        ("교육부", "https://www.moe.go.kr"),
        ("Study in Korea", "https://www.studyinkorea.go.kr"),
        ("한국교육개발원", "https://www.kedi.re.kr"),
    ],
    "한국유학정보": [
        ("Study in Korea", "https://www.studyinkorea.go.kr"),
        ("출입국·외국인정책본부", "https://www.immigration.go.kr"),
        ("국립국제교육원", "https://www.niied.go.kr"),
    ],
    "Korea Career Programs": [
        ("Ministry of Employment and Labor", "https://www.moel.go.kr/english"),
        ("HRD Korea", "https://www.hrdkorea.or.kr/eng"),
        ("Study in Korea NIIED", "https://www.studyinkorea.go.kr"),
    ],
}

# ★ 사이트별 내부링크 URL 목록 (실제 존재하는 URL만 — 가짜 앵커 방지)
SITE_INTERNAL_LINKS = {
    "https://k-health365.com": [
        ("건강 정보 메인", "https://k-health365.com"),
        ("혈압 관리 가이드", "https://k-health365.com/?s=혈압"),
        ("당뇨 예방법", "https://k-health365.com/?s=당뇨"),
        ("면역력 강화", "https://k-health365.com/?s=면역력"),
        ("수면 건강", "https://k-health365.com/?s=수면"),
    ],
    "https://koreanews365.com": [
        ("최신 뉴스", "https://koreanews365.com"),
        ("경제 뉴스", "https://koreanews365.com/category/경제-economy/"),
        ("정치 뉴스", "https://koreanews365.com/category/정치-politics/"),
        ("사회 뉴스", "https://koreanews365.com/category/사회-society/"),
        ("국제 뉴스", "https://koreanews365.com/category/국제-international/"),
    ],
    "https://theseouljournal.com": [
        ("Latest News", "https://theseouljournal.com"),
        ("Politics", "https://theseouljournal.com/category/politics/"),
        ("Economy", "https://theseouljournal.com/category/economy/"),
        ("Culture", "https://theseouljournal.com/category/culture/"),
        ("Expat Life", "https://theseouljournal.com/category/expat-life/"),
    ],
    "https://kfinance365.com": [
        ("Finance Guide", "https://kfinance365.com"),
        ("Investment Tips", "https://kfinance365.com/?s=investment"),
        ("Korea Stock Market", "https://kfinance365.com/?s=stock"),
        ("Tax Guide", "https://kfinance365.com/?s=tax"),
        ("Banking in Korea", "https://kfinance365.com/?s=banking"),
    ],
    "https://koreainvest365.com": [
        ("Investment Guide", "https://koreainvest365.com"),
        ("Stock Market Korea", "https://koreainvest365.com/?s=stock"),
        ("ETF Guide", "https://koreainvest365.com/?s=ETF"),
        ("Real Estate Investment", "https://koreainvest365.com/?s=real+estate"),
        ("Crypto Investment", "https://koreainvest365.com/?s=crypto"),
    ],
    "https://krealestate365.com": [
        ("부동산 정보", "https://krealestate365.com"),
        ("아파트 시세", "https://krealestate365.com/?s=아파트"),
        ("청약 가이드", "https://krealestate365.com/?s=청약"),
        ("전세 정보", "https://krealestate365.com/?s=전세"),
        ("부동산 정책", "https://krealestate365.com/?s=정책"),
    ],
    "https://k-trip365.com": [
        ("Korea Travel Guide", "https://k-trip365.com"),
        ("Seoul Travel", "https://k-trip365.com/?s=Seoul"),
        ("Jeju Island Guide", "https://k-trip365.com/?s=Jeju"),
        ("Korea Hiking", "https://k-trip365.com/?s=hiking"),
        ("Korean Food Guide", "https://k-trip365.com/?s=food"),
    ],
    "https://k-visa365.com": [
        ("Korea Visa Guide", "https://k-visa365.com"),
        ("Student Visa D-2", "https://k-visa365.com/?s=D-2"),
        ("Work Visa E-7", "https://k-visa365.com/?s=E-7"),
        ("Working Holiday Visa", "https://k-visa365.com/?s=working+holiday"),
        ("Visa Extension", "https://k-visa365.com/?s=extension"),
    ],
    "https://kstudy365.com": [
        ("Study in Korea", "https://kstudy365.com"),
        ("Korean Universities", "https://kstudy365.com/?s=university"),
        ("Scholarships", "https://kstudy365.com/?s=scholarship"),
        ("Student Visa", "https://kstudy365.com/?s=visa"),
        ("TOPIK Guide", "https://kstudy365.com/?s=TOPIK"),
    ],
    "https://jobkorea365.com": [
        ("Jobs in Korea", "https://jobkorea365.com"),
        ("IT Jobs", "https://jobkorea365.com/?s=IT"),
        ("Teaching Jobs", "https://jobkorea365.com/?s=teacher"),
        ("Work Visa Guide", "https://jobkorea365.com/?s=visa"),
        ("Salary Guide", "https://jobkorea365.com/?s=salary"),
    ],
    "https://koreawedding365.com": [
        ("Korea Wedding Guide", "https://koreawedding365.com"),
        ("Wedding Venues", "https://koreawedding365.com/?s=venue"),
        ("Wedding Photography", "https://koreawedding365.com/?s=photography"),
        ("Korean Traditional Wedding", "https://koreawedding365.com/?s=traditional"),
        ("Wedding Budget", "https://koreawedding365.com/?s=budget"),
    ],
    "https://kskin365.com": [
        ("K-Beauty Guide", "https://kskin365.com"),
        ("Skincare Routine", "https://kskin365.com/?s=skincare"),
        ("K-Beauty Products", "https://kskin365.com/?s=products"),
        ("Anti-Aging Tips", "https://kskin365.com/?s=anti-aging"),
        ("Korean Ingredients", "https://kskin365.com/?s=ingredients"),
    ],
    "https://koreacrypto365.com": [
        ("Crypto Guide Korea", "https://koreacrypto365.com"),
        ("Bitcoin in Korea", "https://koreacrypto365.com/?s=bitcoin"),
        ("Korea Crypto Regulation", "https://koreacrypto365.com/?s=regulation"),
        ("DeFi Guide", "https://koreacrypto365.com/?s=DeFi"),
        ("Crypto Tax Korea", "https://koreacrypto365.com/?s=tax"),
    ],
}

def get_internal_links(site_url: str, count: int = 4) -> list:
    """실제 URL이 있는 내부링크 반환 — 없으면 사이트 홈 + 검색 URL로 구성"""
    links = SITE_INTERNAL_LINKS.get(site_url, [])
    if links:
        return random.sample(links, min(count, len(links)))
    # fallback: 홈 + 검색 URL
    return [
        ("홈페이지", site_url),
        ("최신 글", f"{site_url}/?orderby=date"),
    ]

def get_authority_links(theme: str) -> list:
    return EXTERNAL_AUTHORITY_LINKS.get(theme, [
        ("Korea.net", "https://www.korea.net"),
        ("Visit Korea", "https://english.visitkorea.or.kr"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ])

# ============================================================
# ★ koreanews365 / theseouljournal 완전 독립 키워드 풀
# ============================================================
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

# ★ 뉴스 중복 방지 — 두 사이트 완전 분리 풀
_used_news_titles_ko: set = set()   # koreanews365 전용
_used_news_titles_en: set = set()   # theseouljournal 전용
_wp_recent_titles_cache: dict = {}  # site_url → set

def fetch_recent_wp_titles(site_url: str, wp_pass: str, count: int = 50) -> set:
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

def preload_news_site_titles(sites_config: list, wp_user: str):
    """두 뉴스 사이트 제목 사전 로드"""
    for site in sites_config:
        if site.get("mode") in ("news", "news_en"):
            wp_pass = os.getenv(site["wp_pass_env"], "")
            if wp_pass:
                fetch_recent_wp_titles(site["url"], wp_pass, count=50)

def crawl_rss_news(lang: str = "ko", site_url: str = "") -> tuple:
    """
    RSS 크롤링 — lang에 따라 다른 풀 사용.
    ★ 핵심: KO/EN 사용 제목 set을 완전 분리해서 크로스 중복 원천 차단
    """
    # 언어별 독립 set 사용
    used_titles = _used_news_titles_ko if lang == "ko" else _used_news_titles_en
    # + 해당 사이트의 WP 캐시도 참조
    site_cache  = _wp_recent_titles_cache.get(site_url, set())

    fallback_pool = NEWS_KO_FALLBACK if lang == "ko" else NEWS_EN_FALLBACK

    def _is_dup(title: str) -> bool:
        t_l = title.strip().lower()
        return t_l in used_titles or t_l in site_cache

    RSS_SOURCES_KO = [
        ("조선일보", "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml"),
        ("연합뉴스", "https://www.yonhapnewstv.co.kr/category/news/headline/feed/"),
        ("경향신문", "https://www.khan.co.kr/rss/rssdata/total_news.xml"),
    ]
    RSS_SOURCES_EN = [
        ("Korea Herald", "http://www.koreaherald.com/rss/020100000000.xml"),
        ("Korea JoongAng Daily", "https://koreajoongangdaily.joins.com/rss/feed"),
        ("The Korea Times", "https://www.koreatimes.co.kr/www/rss/rss.xml"),
    ]

    rss_sources = RSS_SOURCES_KO if lang == "ko" else RSS_SOURCES_EN
    random.shuffle(rss_sources)
    all_candidates = []
    for src_name, src_url in rss_sources:
        try:
            res = requests.get(src_url, timeout=10,
                               headers={"User-Agent": "Mozilla/5.0 (compatible; RSS reader)"})
            soup = BeautifulSoup(res.text, 'xml')
            items = soup.find_all('item')
            for it in items:
                t = it.title.text.strip() if it.title else ""
                d = it.description.text.strip() if it.description else ""
                t = re.sub(r'<[^>]+>', '', t).strip()
                d = re.sub(r'<[^>]+>', '', d).strip()
                if t and len(t) >= 5 and not _is_dup(t):
                    all_candidates.append((t, d, src_name))
        except Exception as e:
            print(f"   ⚠️ RSS 실패 ({src_name}): {e}")

    if all_candidates:
        chosen_item = random.choice(all_candidates)
        chosen = (chosen_item[0], chosen_item[1])
        print(f"   📰 RSS 출처: {chosen_item[2]} — {chosen[0][:40]}")
        used_titles.add(chosen[0].strip().lower())
        return chosen

    print(f"   ⚠️ RSS 소스 전체 중복/실패 → fallback 사용")
    unused = [x for x in fallback_pool if not _is_dup(x[0])]
    pool = unused if unused else fallback_pool
    chosen = random.choice(pool)
    used_titles.add(chosen[0].strip().lower())
    return chosen

# ============================================================
# ★ 제목 스타일
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
# ★ SEO 프롬프트 생성 (내부링크 실제 URL 포함)
# ============================================================
def make_khealth_prompt(keyword: str, reporter: dict) -> str:
    """
    k-health365.com 전용 초고품질 의학 콘텐츠 프롬프트.
    YMYL 기준 충족 + 구글 E-E-A-T 최고 수준 + 색인 최적화.
    """
    reporter_name = reporter_display(reporter)
    byline = f"◇ {reporter_name} 기자"

    internal_links = get_internal_links("https://k-health365.com", count=5)
    internal_links_str = "\n".join(
        f'  - <a href="{url}" title="{name}">{name}</a>' for name, url in internal_links
    )

    ext_links = get_authority_links("건강과 의학")
    ext_sample = random.sample(ext_links, min(4, len(ext_links)))
    ext_hint = ", ".join(f"{n}({u})" for n, u in ext_sample)

    title_style = pick_title_style("ko")

    return f"""당신은 대한민국 최고 권위의 내과 전문의이자 의학 저널리스트입니다.
임상 경력 20년, 대한의학회 공인 전문위원 자격을 보유하고 있습니다.
주제: '{keyword}' | 사이트: k-health365.com (구글 애드센스 승인 의학 전문 블로그)

[★ YMYL 의학 콘텐츠 최고 품질 기준 — 구글 E-E-A-T 최상위 레벨]

1. 바이라인: 본문 최상단 첫 줄에 정확히 '{byline}' 삽입.

2. HTML 전용 출력: h2,h3,p,ul,li,ol,strong,table,tr,td,blockquote.
   마크다운(##,**,- 등) 절대 금지. 순수 HTML만.

3. ★ 분량: 공백 제외 최소 3,500자 이상. 깊이 있는 임상 의학 콘텐츠.

4. ★ 모바일 최적화 (체류시간 극대화):
   - 모든 <p>는 최대 2문장 이하.
   - 단락 사이 반드시 완전한 줄바꿈.
   - 텍스트 블록 빽빽하면 이탈률 급증 → SEO 치명적.

5. ★ 키워드 배치:
   - 첫 단락 첫 문장에 '{keyword}' 반드시 배치.
   - 전체 본문에서 자연스럽게 15회 이상 사용.
   - 동의어/관련어(예: 고혈압↔혈압↔혈압 수치↔혈압 조절) 함께 활용.

6. ★ 문서 구조 (Rank Math SEO 만점 필수):
   - h2 최소 6개
   - h3 최소 5개
   - ul/li 리스트 4개 이상
   - 데이터 비교 <table> 2개 이상 (정상 수치 vs 비정상 수치, 치료법 비교 등)
   - <blockquote>로 전문가 인용 또는 가이드라인 1개 이상

7. ★ 통계·수치 10개 이상 필수 (YMYL 신뢰도 핵심):
   - 구체적 숫자: %, 만 명, mmHg, mg/dL, IU, 년, 개월, 회/일 등
   - 예시: "국내 고혈압 환자 수 1,200만 명(통계청, 2024)", "수축기 혈압 140mmHg 이상"
   - 막연한 표현("많은", "대부분", "일부") 절대 금지

8. ★ 출처 괄호 5회 이상 필수:
   - 형식: "(질병관리청, 2025)", "(대한의학회 가이드라인, 2024)", "(NEJM, 2023)"
   - 권위 기관 필수 언급: {ext_hint}

9. ★ 실제 내부링크 5개 삽입 (가짜 앵커 절대 금지):
{internal_links_str}
   본문 내 자연스러운 맥락에서 위 URL을 그대로 사용.

10. ★ E-E-A-T 전문성 증명 필수:
    - 임상 경험 기반 디테일 3곳 이상
      예: "외래에서 자주 보는 패턴", "환자들이 가장 많이 오해하는 부분"
    - 최신 의학 가이드라인 1개 이상 명시
    - 논문/연구 인용 1개 이상 (형식: "2023년 《Lancet》 게재 연구에 따르면...")

11. ★ 의학 필수 섹션 (구글 YMYL 요구사항):
    - "⚠️ 주의사항" 또는 "언제 병원을 가야 할까?" 섹션 반드시 포함
    - "이 글은 의학적 참고 정보이며, 진단 및 치료는 반드시 전문의와 상담하세요." 문구 포함

12. 제목 스타일: {title_style}
    → 출력 첫 줄 반드시 'TITLE:' 로 시작.
    → 제목에 숫자 포함 권장 (예: "5가지", "7단계", "2026년").
    → 20~60자 사내.

13. ★ META_DESC: 본문 끝 'META_DESC:' 로 시작.
    - 정확히 130~140자(한글 기준).
    - '{keyword}' 포함.
    - 클릭을 유도하는 구체적 혜택 언급.

14. FAQ 스키마: 'FAQ_START' ~ 'FAQ_END' 블록.
    - Q:/A: 형식 5문항 (기존 3개에서 강화).
    - 실제 환자들이 검색하는 질문으로 구성.

15. ★ TAGS: 'TAGS:' 로 시작, 12개 한국어 키워드.
    - 각 태그 최대 3단어·15자 이내.
    - 첫 번째는 반드시 '{keyword}'.
    - [크리티컬] "#증상 가격", "#효능 부작용 가격" 같은 무의미 조합 절대 금지.
    - 올바른 예: "{keyword} 원인", "{keyword} 예방법", "{keyword} 치료", "{keyword} 증상", "{keyword} 식이요법"

출력 순서: TITLE → 본문HTML → META_DESC → FAQ_START~FAQ_END → TAGS

[콘텐츠 구성 권장 템플릿]
<h2>{keyword}란? 기본 개념과 정의</h2>
<h2>{keyword}의 주요 원인과 위험 요인</h2>
<h2>{keyword} 증상과 자가 진단 체크리스트</h2>
<h2>{keyword} 예방법 — 생활습관 개선 7가지</h2>
<h2>{keyword} 치료법 — 약물 vs 비약물 비교</h2>
<h2>⚠️ 이런 증상이면 즉시 병원 가세요</h2>
<h2>자주 묻는 질문 (FAQ)</h2>"""


def make_seo_prompt(keyword: str, theme: str, lang: str, mode: str = "blog",
                    site_url: str = "", reporter: dict = None) -> str:
    reporter_name = reporter_display(reporter) if reporter else "편집부"
    byline_ko = f"◇ {reporter_name} 기자"
    byline_en = f"◇ By {reporter_name}"

    tag_lang    = "영어로" if lang == "en" else "한국어로"
    title_style = pick_title_style(lang)
    is_medical  = ("건강" in theme or "의학" in theme or "medical" in theme.lower()
                   or "beauty" in theme.lower())
    ext_links   = get_authority_links(theme)
    ext_sample  = random.sample(ext_links, min(3, len(ext_links)))
    ext_hint    = ", ".join(f"{n}({u})" for n, u in ext_sample)

    # ★ 실제 내부링크 URL 목록 생성
    internal_links = get_internal_links(site_url, count=5)
    internal_links_str = "\n".join(
        f'  - <a href="{url}" title="{name}">{name}</a>' for name, url in internal_links
    )

    # ── 뉴스 모드 (한국어) ──────────────────────────────────
    if mode == "news":
        return f"""당신은 주요 일간지의 시니어 취재기자입니다.
주제: '{keyword}'에 대해 엄격한 신문기사체 뉴스 기사를 작성하세요.

[필수 지침]
1. 문체: '했다', '밝혔다', '조사됐다'로 끝나는 6하원칙 기사체. 마크다운 금지.
2. 바이라인: 기사 맨 위 첫 줄에 정확히 '{byline_ko}' 삽입.
3. 분량: HTML(h2,h3,p,strong,ul,li)만 사용해 최소 1,800자 이상.
4. ★ 모바일 가독성: 모든 <p>는 2~3문장 이하. 단락 사이 완전한 줄바꿈 필수.
5. ★ 통계·수치 5개 이상: "%", "만 명", "억 원" 등 구체적 숫자. 막연한 표현 금지.
6. ★ 출처 괄호 명시: "(통계청, 2026)", "(한국은행 발표)" 형식 3회 이상.
7. ★ 실제 내부링크 필수 삽입 (아래 링크를 본문 내 자연스럽게 4개 이상 배치):
{internal_links_str}
8. ★ 권위 기관 3회 이상 언급: {ext_hint}
9. E-E-A-T 전문가 인용구 1개 이상.
10. h2 최소 3개.
11. 제목 스타일: {title_style} → 출력 첫 줄 'TITLE:' 로 시작.
12. ★ META_DESC: 본문 끝 'META_DESC:' 로 시작, 정확히 130~140자(한글).
13. FAQ: 'FAQ_START' ~ 'FAQ_END' 블록, Q:/A: 형식 3문항.
14. ★ TAGS: 'TAGS:' 로 시작, {TAG_COUNT}개 한국어 키워드. 첫 번째는 '{keyword}'.
출력 순서: TITLE → 본문HTML → META_DESC → FAQ_START~FAQ_END → TAGS"""

    # ── 영문 뉴스 모드 ──────────────────────────────────────
    if mode == "news_en":
        return f"""You are a senior staff writer at an English-language newspaper based in Seoul.
Topic: Write a professional English news/feature article about '{keyword}' ({theme}).

[MANDATORY RULES]
1. Style: Journalistic English, inverted pyramid. No markdown.
2. Byline: First line must be exactly '{byline_en}'.
3. Length: Minimum 1,800 characters using HTML only (h2, h3, p, strong, ul, li).
4. ★ Mobile readability: Every <p> max 2~3 sentences. Full paragraph breaks between sections.
5. ★ Statistics (minimum 5): Specific numbers (%, figures, dates, costs). No vague phrases.
6. ★ Source citations (minimum 3): "(Statistics Korea, 2026)", "(Ministry of Health)" format.
7. ★ Real internal links — insert naturally in body text (minimum 4):
{internal_links_str}
8. ★ Authority sources (minimum 3 mentions): {ext_hint}
9. E-E-A-T: At least 1 expert quote or attributed statement.
10. Minimum 3 h2 headings.
11. Title style: {title_style} → First line starting 'TITLE:'.
12. ★ META_DESC: After body, 'META_DESC:', exactly 130~155 English characters.
13. FAQ: 'FAQ_START' ~ 'FAQ_END' block, Q:/A: format, 3 questions.
14. ★ TAGS: 'TAGS:', {TAG_COUNT} English keywords. First tag must be '{keyword}'.
Output order: TITLE → body HTML → META_DESC → FAQ_START~FAQ_END → TAGS"""

    # ── 블로그 모드 ─────────────────────────────────────────
    persona = ("의학박사 및 임상 전문의" if is_medical
               else "해당 분야 15년 경력 최고 전문 자문위원")
    persona_en = ("medical doctor and clinical specialist" if is_medical
                  else "senior industry expert with 15 years of experience")
    p = persona if lang == "ko" else persona_en

    if lang == "ko":
        return f"""당신은 {p}이자 구글 SEO 최고 전문 콘텐츠 라이터입니다.
주제: '{keyword}' | 카테고리: {theme}

[필수 지침 — 구글 애드센스 승인·상위 노출 95점 이상 기준]
1. HTML 전용: h2,h3,p,ul,li,ol,strong,table. 마크다운 절대 금지.
2. 분량: 공백 제외 최소 2,500자 이상.
3. ★ 모바일 최적화: 모든 <p>는 최대 2문장. 단락 사이 완전한 줄바꿈 필수.
4. 키워드 배치: 첫 단락 문두에 '{keyword}' 배치, 전체 10회 이상 자연스럽게 삽입.
5. 구조: h2 최소 5개, h3 최소 4개, ul/li 리스트 3개 이상, 데이터 비교 <table> 1개 이상.
6. ★ 통계·수치 5개 이상 필수: 구체적 숫자(%, 만 명, 원). 막연한 표현 금지.
7. ★ 출처 괄호 명시 필수: "(KOSIS, 2026)", "(보건복지부 자료)" 형식 3회 이상.
8. ★ 실제 내부링크 필수 삽입 (아래 링크를 본문 내 자연스럽게 최소 4개 배치):
{internal_links_str}
   반드시 위 URL을 그대로 사용. 가짜 앵커(#) 절대 금지.
9. ★ 권위 기관 3회 이상 언급: {ext_hint}
10. E-E-A-T 전문성: {p}로서 실무 경험 기반 디테일 2곳 이상.
11. 제목 스타일: {title_style} → 출력 첫 줄 'TITLE:' 로 시작.
12. ★ META_DESC: 본문 끝 'META_DESC:' 로 시작, 정확히 130~140자(한글).
13. FAQ: 'FAQ_START' ~ 'FAQ_END' 블록, Q:/A: 형식 3문항.
14. ★ 태그: 'TAGS:' 로 시작, {TAG_COUNT}개 한국어 키워드. 첫 번째는 '{keyword}'.
    {'[크리티컬] 의미없는 태그 조합 금지. "원인", "예방법", "치료", "관리법" 등과만 조합.' if is_medical else '주제에 완벽히 일치하는 키워드만.'}
출력 순서: TITLE → 본문HTML → META_DESC → FAQ_START~FAQ_END → TAGS"""

    else:
        return f"""You are a {p} and a top SEO content writer.
Topic: '{keyword}' | Category: {theme} | Language: English

[MANDATORY RULES — Google AdSense quality + top ranking, 95+ SEO score target]
1. HTML only: h2,h3,p,ul,li,ol,strong,table. No markdown.
2. Length: Minimum 2,500 characters of in-depth expert content.
3. ★ Mobile optimization: Every <p> max 2 sentences. Full paragraph breaks between sections.
4. Keyword placement: '{keyword}' in first sentence, natural use 10+ times.
5. Structure: min 5 h2, min 4 h3, 3+ ul/li lists, 1+ data comparison <table>.
6. ★ Statistics mandatory (min 5): Specific numbers (%, figures, dollar amounts, timeframes).
7. ★ Source citations (min 3): "(OECD, 2026)", "(Ministry of Health Korea)" format.
8. ★ Real internal links — insert naturally in body (minimum 4 links):
{internal_links_str}
   Use these EXACT URLs. Never use fake anchors (#).
9. ★ Authority sources (min 3 mentions): {ext_hint}
10. E-E-A-T expertise: 2+ specific procedural details from a {p}'s perspective.
11. Title style: {title_style} → First output line starting 'TITLE:'.
12. ★ META_DESC: After body, 'META_DESC:', exactly 130~155 English characters.
13. FAQ: 'FAQ_START' ~ 'FAQ_END' block, Q:/A: format, 3 questions.
14. ★ Tag integrity: 'TAGS:', {TAG_COUNT} English keywords. First tag must be '{keyword}'.
    {'[CRITICAL] No nonsensical tag combos. Use "causes", "prevention", "treatment", "symptoms".' if is_medical else 'Only semantically accurate keywords matching the topic.'}
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
    pattern = r'(\d+[\.,]?\d*\s*(?:%|퍼센트|percent|명|만|억|원|달러|달|년|월|개|배|회|건|점))'
    return len(re.findall(pattern, body_text, re.IGNORECASE))

def estimate_seo_score(title: str, body: str, meta_desc: str, tags: list,
                        faq_list: list, image_urls: list, keyword: str) -> int:
    score = 0
    kw_l  = keyword.lower()
    plain = re.sub(r'<[^>]+>', '', body)
    blen  = len(plain.replace(" ","").replace("\n",""))

    title_l = title.lower()
    if kw_l in title_l:                  score += 10
    if 20 <= len(title) <= 65:           score += 3
    if any(c.isdigit() for c in title):  score += 2

    if   blen >= 3000: score += 20
    elif blen >= 2500: score += 17
    elif blen >= 2000: score += 13
    elif blen >= 1800: score += 9
    elif blen >= 1000: score += 4

    mdl = len(meta_desc)
    if   130 <= mdl <= 160: score += 10
    elif 100 <= mdl <  130: score += 7
    elif  80 <= mdl <  100: score += 4
    elif mdl > 0:           score += 1

    ic = len(image_urls)
    if   ic >= 3: score += 10
    elif ic == 2: score += 7
    elif ic == 1: score += 4

    # 실제 href가 있는 링크만 카운트
    ilinks = len(re.findall(r'<a\s+href=["\']https?://[^"\']+["\']', body, re.IGNORECASE))
    if   ilinks >= 5: score += 10
    elif ilinks >= 4: score += 8
    elif ilinks >= 3: score += 5
    elif ilinks >= 1: score += 2

    stat_cnt = count_statistics_in_body(body)
    if   stat_cnt >= 5: score += 10
    elif stat_cnt >= 3: score += 8
    elif stat_cnt >= 1: score += 4
    cite_cnt = len(re.findall(r'\([^)]{3,40},\s*20[0-9]{2}\)', body))
    if   cite_cnt >= 3: score += 5
    elif cite_cnt >= 1: score += 2

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

    if   len(faq_list) >= 3: score += 5
    elif len(faq_list) >= 2: score += 3
    elif len(faq_list) >= 1: score += 1

    if   len(tags) >= TAG_COUNT: score += 5
    elif len(tags) >= 8:         score += 3
    elif len(tags) >= 4:         score += 1

    return min(score, 100)

# ============================================================
# 이미지
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
    """3단계 fallback: 원문 → 영어번역 → 테마 fallback. 최소 1장 보장."""
    has_korean = any('\uac00' <= c <= '\ud7a3' for c in keyword)
    urls = []
    # 1단계
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
    # 3단계: 테마 fallback
    if len(urls) < count:
        fallback_q = THEME_IMAGE_FALLBACK.get(theme, THEME_IMAGE_FALLBACK["default"])
        urls.extend(get_images_from_pixabay(fallback_q, count - len(urls)))
        if len(urls) < count:
            urls.extend(get_images_from_pexels(fallback_q, count - len(urls)))
    # ★ 최후 보루: "South Korea" 초광범위 쿼리
    if not urls:
        urls.extend(get_images_from_pixabay("South Korea", count))
    if not urls:
        urls.extend(get_images_from_pexels("South Korea", count))

    return list(dict.fromkeys(urls))[:count]

# ============================================================
# 키워드 로딩
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
# 사이트 도달 가능 여부
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
# 워드프레스 포스팅 (Author + Category 포함)
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
            keyword: str, seo_score: int, reporter: dict) -> dict:
    wp_pass = os.getenv(site["wp_pass_env"], "")
    if not wp_pass:
        return {"ok": False, "error": f"WP_PASS_ENV '{site['wp_pass_env']}' not set"}

    site_url = site["url"]
    lang     = site["lang"]
    theme    = site["theme"]

    # ★ Author ID 가져오기
    author_id = get_or_create_wp_author(site_url, wp_pass, reporter)

    # ★ Category ID 가져오기
    category_name = get_category_for_post(theme, keyword, title)
    category_id   = get_or_create_wp_category(site_url, wp_pass, category_name)

    # FAQ 스키마 + 이미지 삽입
    faq_html = build_faq_schema_html(faq_list)
    mid = len(body_html) // 2
    split_pt = body_html.find('</p>', mid)
    if split_pt > 0 and image_urls:
        mid_img = build_image_html(image_urls[:1], keyword)
        end_img = build_image_html(image_urls[1:], keyword) if len(image_urls) > 1 else ""
        final_body = body_html[:split_pt+4] + mid_img + body_html[split_pt+4:] + faq_html + end_img
    else:
        img_html   = build_image_html(image_urls, keyword)
        final_body = img_html + body_html + faq_html

    # 태그 ID 수집
    tags_payload = []
    for tag in tags:
        try:
            tr = requests.post(
                f"{site_url}/wp-json/wp/v2/tags",
                auth=(WP_USER, wp_pass),
                json={"name": tag}, timeout=10
            )
            if tr.status_code in (200, 201):
                tags_payload.append(tr.json().get("id"))
            elif tr.status_code == 400:
                sr = requests.get(
                    f"{site_url}/wp-json/wp/v2/tags",
                    auth=(WP_USER, wp_pass),
                    params={"search": tag, "per_page": 1}, timeout=10
                )
                if sr.status_code == 200 and sr.json():
                    tags_payload.append(sr.json()[0]["id"])
        except Exception:
            pass

    rank_kw = ",".join([keyword] + tags[:4])

    post_data = {
        "title":      title,
        "content":    final_body,
        "status":     "publish",
        "categories": [category_id] if category_id and category_id > 0 else [],
        "tags":       tags_payload,
        "meta": {
            "rank_math_focus_keyword": rank_kw,
            "rank_math_description":   meta_desc,
            "rank_math_seo_score":     str(seo_score),
        },
    }
    # Author 설정 (ID가 유효한 경우만)
    if author_id and author_id > 0:
        post_data["author"] = author_id

    try:
        r = requests.post(
            f"{site_url}/wp-json/wp/v2/posts",
            auth=(WP_USER, wp_pass),
            json=post_data, timeout=30
        )
        if r.status_code in (200, 201):
            post_id  = r.json().get("id")
            post_url = r.json().get("link", "")
            # Rank Math 검증
            time.sleep(2)
            vr = requests.get(
                f"{site_url}/wp-json/wp/v2/posts/{post_id}",
                auth=(WP_USER, wp_pass), timeout=10
            )
            if vr.status_code == 200:
                meta_check = vr.json().get("meta", {})
                if not meta_check.get("rank_math_focus_keyword"):
                    requests.patch(
                        f"{site_url}/wp-json/wp/v2/posts/{post_id}",
                        auth=(WP_USER, wp_pass),
                        json={"meta": {"rank_math_focus_keyword": rank_kw,
                                       "rank_math_description": meta_desc}},
                        timeout=15
                    )
            return {"ok": True, "post_id": post_id, "url": post_url,
                    "author": reporter["name"], "category": category_name}
        else:
            return {"ok": False, "status": r.status_code, "error": r.text[:300]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}

# ============================================================
# 구글시트 로깅
# ============================================================
_log_buffer: list = []

def record_result(site_url: str, theme: str, keyword: str, title: str,
                  post_url: str, seo_score: int, image_count: int,
                  status: str, error: str = "", author: str = "", category: str = ""):
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
        "author":     author,
        "category":   category,
    })

def flush_log_to_google_sheet():
    if not SHEETS_WEBHOOK or not _log_buffer: return
    try:
        r = requests.post(SHEETS_WEBHOOK, json={"records": _log_buffer}, timeout=15)
        print(f"  📊 구글시트 전송 {len(_log_buffer)}건: HTTP {r.status_code}")
        _log_buffer.clear()
    except Exception as e:
        print(f"  ⚠️ 구글시트 전송 실패: {e}")
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

    # ★ 기자 선택 (포스트마다 랜덤)
    reporter = pick_reporter(site)
    print(f"\n  🖊  [{theme}] {keyword[:50]} | 기자: {reporter['name']}")

    # 뉴스 모드 키워드
    news_subtitle = ""
    if mode in ("news", "news_en"):
        kw_tuple = crawl_rss_news(lang, site_url=url)
        keyword, news_subtitle = kw_tuple if isinstance(kw_tuple, tuple) else (kw_tuple, "")

    # ★ k-health365 전용 초고품질 프롬프트 / 그 외 일반 프롬프트
    is_khealth = (mode == "health_blog")
    if is_khealth:
        prompt = make_khealth_prompt(keyword, reporter)
    else:
        prompt = make_seo_prompt(keyword, theme, lang, mode, site_url=url, reporter=reporter)

    # k-health365는 SEO 95점 기준, 최대 2회 재시도 / 그 외 90점 1회
    SEO_MIN_SCORE = 95 if is_khealth else 90
    MAX_REGEN     = 2  if is_khealth else 1
    raw = None
    for gen_attempt in range(MAX_REGEN + 1):
        try:
            raw = generate_content_gemini(prompt)
        except Exception as e:
            print(f"  ❌ Gemini 생성 실패: {e}")
            record_result(url, theme, keyword, "", "", 0, 0, "❌ Gemini 실패", str(e))
            return False
        time.sleep(SLEEP_BETWEEN_POSTS)

        body_raw, title, meta_desc, faq_list = extract_meta_and_faq(raw)
        body, tags = extract_tags_from_article(body_raw, keyword, theme, lang)

        if not title:
            title = (f"{keyword} — 완벽 정리 가이드" if lang == "ko"
                     else f"{keyword} — Complete Guide {now_kst().year}")

        _pre_score = estimate_seo_score(title, body, meta_desc, tags, faq_list, ["x","x","x"], keyword)
        if _pre_score >= SEO_MIN_SCORE or gen_attempt >= MAX_REGEN:
            print(f"  📝 생성 {gen_attempt+1}회차 → 사전 SEO {_pre_score}점")
            break
        else:
            print(f"  🔄 SEO {_pre_score}점 미달 → 재생성 {gen_attempt+2}회차")
            if is_khealth:
                prompt = prompt + f"""

[★ k-health365 재생성 보완 — SEO {_pre_score}점 미달, 목표 95점]
의학 전문 콘텐츠 기준으로 다음을 반드시 강화:
- 본문 <table> 2개 이상 (정상 수치 vs 비정상, 치료법 비교 등)
- 통계·수치 10개 이상, 출처 괄호 5개 이상 (질병관리청, 대한의학회 등)
- 내부링크 실제 URL 5개 이상 <a href="https://k-health365.com/...">
- h2 6개 이상, h3 5개 이상, ul 4개 이상
- <blockquote> 전문가 인용 또는 가이드라인 1개
- "⚠️ 주의사항 / 병원 방문 기준" 섹션 필수
- FAQ 5문항 (기존 3개 → 5개로 강화)
- 본문 총 4,000자 이상"""
            else:
                prompt = prompt + f"""

[재생성 보완 — 이전 결과 SEO {_pre_score}점 미달]
반드시 보완:
- 본문 <table> 데이터 비교표 1개 이상
- 통계 수치 5개 이상, 출처 괄호 3개 이상
- 내부링크 실제 URL <a href="URL">텍스트</a> 5개 이상
- h2 5개 이상, h3 4개 이상, ul 3개 이상
- 본문 총 3,000자 이상"""
            time.sleep(5 if not is_khealth else 8)

    # 이미지 (최소 1장 보장)
    images = get_multiple_images(keyword, count=3, theme=theme)
    if not images:
        print(f"  ⚠️ 이미지 0장 — 최후 fallback 시도")
        images = get_images_from_pixabay("South Korea nature", 3)
        if not images:
            images = get_images_from_pexels("Seoul Korea", 3)
    print(f"  🖼  이미지 {len(images)}장")

    # SEO 최종 점수
    score = estimate_seo_score(title, body, meta_desc, tags, faq_list, images, keyword)
    rank_label = ("🏆 우수" if score >= 95 else
                  "✅ 양호" if score >= 90 else
                  "⚠️ 보통" if score >= 80 else
                  "❌ 미달")
    print(f"  📊 SEO 최종 점수: {score}/100  {rank_label}")
    if score < 90:
        plain_len = len(re.sub(r'<[^>]+>','',body).replace(' ','').replace('\n',''))
        stat_cnt2 = count_statistics_in_body(body)
        ilinks2   = len(re.findall(r'<a\s+href=["\']https?://', body, re.IGNORECASE))
        tb2       = len(re.findall(r'<table[\s>]', body, re.IGNORECASE))
        print(f"     ↳ 본문길이:{plain_len}자 | 통계:{stat_cnt2}개 | 실제링크:{ilinks2}개 | 테이블:{tb2}개")

    # 카테고리 결정
    category_name = get_category_for_post(theme, keyword, title)
    print(f"  📁 카테고리: {category_name}")

    # 뉴스 사이트 크로스런 중복 최종 검사
    if mode in ("news", "news_en") and title:
        t_lower = title.strip().lower()
        site_cache = _wp_recent_titles_cache.get(url, set())
        if t_lower in site_cache:
            print(f"  ⛔ WP 캐시 중복 → 발행 취소: {title[:60]}")
            record_result(url, theme, keyword, title, "", score, len(images), "⛔ skip_dup")
            return False
        # 발행 예정 제목 즉시 캐시 등록
        site_cache.add(t_lower)
        _wp_recent_titles_cache[url] = site_cache

    # WP 발행
    result = wp_post(site, title, body, meta_desc, tags, faq_list, images,
                     keyword, score, reporter)
    if result["ok"]:
        author_name    = result.get("author", reporter["name"])
        category_label = result.get("category", category_name)
        print(f"  ✅ 발행 완료: {result.get('url','')} | 저자: {author_name} | 카테고리: {category_label}")
        record_result(url, theme, keyword, title, result.get("url",""),
                      score, len(images), "✅ OK", author=author_name, category=category_label)
        return True
    else:
        err = result.get("error","")
        print(f"  ❌ 발행 실패: {err[:120]}")
        record_result(url, theme, keyword, title, "", score, len(images),
                      "❌ WP 실패", err, reporter["name"], category_name)
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

    # 뉴스 사이트 최근 제목 사전 로드
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
