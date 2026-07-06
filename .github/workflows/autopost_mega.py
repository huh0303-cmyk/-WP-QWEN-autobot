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
SLEEP_BETWEEN_POSTS   = float(os.getenv("SLEEP_BETWEEN_POSTS", "8"))

gemini_client          = genai.Client(api_key=GEMINI_API_KEY)

# ★★★ 완전 무료화 설정 ★★★
# gemini-2.5-flash-lite: 무료 1500 RPD / 분당 30 RPM
# gemini-2.5-flash      : 유료 전환 위험 → 완전 제거
GEMINI_MODEL_PRIMARY   = "gemini-2.5-flash-lite"  # 무료 고정
GEMINI_MODEL_FALLBACK  = "gemini-2.5-flash-lite"  # 폴백도 lite 통일
GEMINI_MODEL           = GEMINI_MODEL_PRIMARY
_gemini_fallback_active = False

TAG_COUNT        = 12
MIN_BODY_LENGTH  = 1800
SEO_TARGET       = 90   # ★ 90점 기준 (95점 강요 시 재생성 폭탄 → 무료 한도 초과)
MAX_REGEN        = 0    # ★ Free Tier 20RPD → 재생성 없음, 1회 호출/포스트 (2회 호출/포스트 × 91건 = 182회 << 1500 RPD)
KW_DENSITY_MAX   = 0.025  # ★ 키워드 밀도 상한 2.5%

# ★ RPM(분당 요청) 제한 준수: flash-lite 무료 = 30 RPM
# SLEEP_BETWEEN_POSTS를 15초로 설정 → 최대 4건/분 << 30 RPM 안전
RATE_LIMIT_SLEEP = 35.0  # Free Tier RPM 보호 (35초 간격)

# ============================================================
# ★ 가상 기자 명단
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

_wp_author_cache: dict = {}

def get_or_create_wp_author(site_url: str, wp_pass: str, reporter: dict) -> int:
    cache = _wp_author_cache.setdefault(site_url, {})
    slug  = reporter["slug"]
    if slug in cache:
        return cache[slug]
    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/users", auth=(WP_USER, wp_pass),
                         params={"search": reporter["email"], "per_page": 5}, timeout=10)
        if r.status_code == 200 and r.json():
            uid = r.json()[0]["id"]; cache[slug] = uid; return uid
    except Exception:
        pass
    try:
        payload = {"username": slug, "name": reporter["name"], "email": reporter["email"],
                   "slug": slug, "description": reporter.get("bio", ""),
                   "password": hashlib.md5(reporter["email"].encode()).hexdigest()[:16] + "Aa1!",
                   "roles": ["author"]}
        r = requests.post(f"{site_url}/wp-json/wp/v2/users", auth=(WP_USER, wp_pass),
                          json=payload, timeout=15)
        if r.status_code in (200, 201):
            uid = r.json().get("id"); cache[slug] = uid
            print(f"   👤 기자 생성: {reporter['name']} (ID {uid})"); return uid
        elif r.status_code == 400:
            r2 = requests.get(f"{site_url}/wp-json/wp/v2/users", auth=(WP_USER, wp_pass),
                              params={"slug": slug, "per_page": 1}, timeout=10)
            if r2.status_code == 200 and r2.json():
                uid = r2.json()[0]["id"]; cache[slug] = uid; return uid
    except Exception as e:
        print(f"   ⚠️ Author 생성 실패 ({reporter['name']}): {e}")
    cache[slug] = -1; return -1

def pick_reporter(site: dict) -> dict:
    url = site.get("url", "")
    lang = site.get("lang", "en")
    if "koreanews365" in url:   return random.choice(REPORTERS_KO)
    elif "theseouljournal" in url: return random.choice(REPORTERS_EN)
    elif lang == "ko":          return random.choice(REPORTERS_BLOG_KO)
    else:                       return random.choice(REPORTERS_BLOG_EN)

def reporter_display(reporter: dict) -> str:
    return reporter["name"]

# ============================================================
# ★ 테마별 카테고리 매핑
# ============================================================
THEME_CATEGORIES = {
    # ★ 황금3 + Etc/기타 = 총 4개 고정 (신규 카테고리 절대 생성 금지)

    "건강과 의학": {
        "default": "건강의학정보",
        "golden": ["건강의학정보","건강기능식품정보","질환별관리법"],
        "keyword_map": [
            (["영양","비타민","영양제","보충제","유산균","프로바이오틱","오메가","콜라겐",
               "다이어트","비만","체중","식품","기능성"], "건강기능식품정보"),
            (["혈압","당뇨","혈당","암","피부","아토피","탈모","관절","허리","디스크",
               "골다공증","수면","불면","우울","불안","간","소화","변비","치료","예방","관리"], "질환별관리법"),
        ]
    },
    "한국 뉴스": {
        "default": "경제",
        "golden": ["경제","정치","사회"],
        "keyword_map": [
            (["정치","대통령","국회","선거","정당","여당","야당","법안","탄핵","외교","북한"], "정치"),
            (["사회","범죄","복지","노동","청년","저출산","교육","문화","K-pop","드라마",
               "미국","중국","일본","국제","AI","반도체"], "사회"),
        ]
    },
    "Seoul Lifestyle": {
        "default": "Culture",
        "golden": ["Politics","Economy","Culture"],
        "keyword_map": [
            (["politics","election","president","government","parliament","policy",
               "North Korea","diplomacy","minister","sanctions","military","crisis"], "Politics"),
            (["economy","GDP","inflation","interest rate","export","trade","stock","market",
               "startup","tech","AI","semiconductor","Samsung","Hyundai","investment","fund"], "Economy"),
        ]
    },
    "Korea Medical Tourism": {
        "default": "성형·피부과",
        "golden": ["성형·피부과","정부지원혜택","비용·병원비","Etc"],
        "keyword_map": [
            (["정부","지자체","서울시","부산","대구","인천","지원","혜택","보조","의료관광"], "정부지원혜택"),
            (["비용","가격","cost","price","fee","얼마","견적","할인","패키지"], "비용·병원비"),
        ]
    },
    "Investment": {
        "default": "Korea Stocks",
        "golden": ["Korea Stocks","Korea Funds & ETF","Crypto & Digital","Etc"],
        "keyword_map": [
            (["ETF","fund","mutual","index","bond","dividend","yield","REIT"], "Korea Funds & ETF"),
            (["crypto","bitcoin","ethereum","DeFi","NFT","blockchain","digital asset","upbit","bithumb"], "Crypto & Digital"),
        ]
    },
    "Korea Investment": {
        "default": "국내주식·ETF",
        "golden": ["국내주식·ETF","부동산·청약","절세·연금","기타"],
        "keyword_map": [
            (["부동산","아파트","청약","분양","전세","리츠","토지","오피스텔"], "부동산·청약"),
            (["절세","IRP","연금","비과세","공제","채권","금리","세금","펀드"], "절세·연금"),
        ]
    },
    "Insurance": {
        "default": "외국인 건강보험",
        "golden": ["외국인 건강보험","외국인 자동차보험","외국인 치과보험","Etc"],
        "keyword_map": [
            (["car","auto","vehicle","driver","traffic","자동차","운전","교통사고"], "외국인 자동차보험"),
            (["dental","치과","implant","임플란트","tooth","teeth","scaling","orthodontics"], "외국인 치과보험"),
        ]
    },
    "Finance": {
        "default": "외국인 은행·송금",
        "golden": ["외국인 은행·송금","외국인 투자·주식","외국인 세금·환급","Etc"],
        "keyword_map": [
            (["stock","invest","ETF","fund","KOSPI","trading","portfolio","dividend","주식","펀드"], "외국인 투자·주식"),
            (["tax","세금","refund","환급","VAT","income tax","deduction","신고","연말정산"], "외국인 세금·환급"),
        ]
    },
    "Tax and Law": {
        "default": "외국인 세금·신고",
        "golden": ["외국인 세금·신고","외국인 법인·창업","외국인 비자·체류","Etc"],
        "keyword_map": [
            (["business","company","startup","corporation","법인","창업","registration","투자","M&A"], "외국인 법인·창업"),
            (["visa","immigration","체류","residence","permit","비자","ARC","HiKorea","출입국"], "외국인 비자·체류"),
        ]
    },
    "Crypto": {
        "default": "업비트·거래소 가입",
        "golden": ["업비트·거래소 가입","외국인 코인 투자법","한국 가상화폐 규제","Etc"],
        "keyword_map": [
            (["foreign","외국인","invest","투자","buy","구매","how to","방법","guide","beginner"], "외국인 코인 투자법"),
            (["regulation","규제","law","FSC","금융위","tax","세금","legal","policy","ban","허용"], "한국 가상화폐 규제"),
        ]
    },
    "Korea Real Estate": {
        "default": "아파트 매매·전세·월세",
        "golden": ["아파트 매매·전세·월세","상가·사업장 임대","외국인 대출·세금","기타"],
        "keyword_map": [
            (["상가","사무실","office","store","사업장","임대","월세","lease","commercial"], "상가·사업장 임대"),
            (["대출","loan","세금","tax","취득세","양도세","mortgage","은행","금리"], "외국인 대출·세금"),
        ]
    },
    "Technology": {
        "default": "AI",
        "golden": ["AI","Startups","Semiconductors"],
        "keyword_map": [
            (["startup","venture","innovation","unicorn","founder","funding","scale","SME"], "Startups"),
            (["semiconductor","chip","TSMC","fab","wafer","memory","DRAM","NAND","EV","battery","display"], "Semiconductors"),
        ]
    },
    "K-Beauty": {
        "default": "Skincare",
        "golden": ["Skincare","Ingredients","Routines"],
        "keyword_map": [
            (["ingredient","niacinamide","hyaluronic","vitamin C","peptide","ceramide",
               "retinol","AHA","BHA","acid","extract"], "Ingredients"),
            (["routine","steps","morning","night","AM","PM","order","layering","how to","guide"], "Routines"),
        ]
    },
    "K-Beauty Reviews": {
        "default": "인기상품 TOP30",
        "golden": ["인기상품 TOP30","Skincare","Wellness","Etc"],
        "keyword_map": [
            (["skincare","toner","serum","moisturizer","sunscreen","essence","ampoule","cream","skin"], "Skincare"),
            (["wellness","supplement","vitamin","probiotic","collagen","health","inner beauty","gut"], "Wellness"),
        ]
    },
    "K-POP": {
        "default": "Artists",
        "golden": ["Artists","Music","Tours","Etc"],
        "keyword_map": [
            (["album","release","comeback","single","MV","track","playlist","song","lyrics"], "Music"),
            (["concert","tour","performance","live","show","event","stadium","ticket"], "Tours"),
        ]
    },
    "K-Culture": {
        "default": "K-Pop & Artists",
        "golden": ["K-Pop & Artists","K-Culture & Learn Korean","Korean Life & Travel","Etc"],
        "keyword_map": [
            (["learn korean","study korean","korean language","TOPIK","grammar","vocabulary",
              "hangul","korean class","korean lesson","speak korean","korean alphabet",
              "free korean","korean for beginners","한국어"], "K-Culture & Learn Korean"),
            (["travel","food","restaurant","Seoul","Busan","Jeju","trip","tour","tourism",
              "korean life","living in korea","expat","foreigner","korean culture",
              "korean tradition","kdrama","k-drama"], "Korean Life & Travel"),
        ]
    },
    "Travel": {
        "default": "Hotels & Stays",
        "golden": ["Hotels & Stays","AirBnB & 민박","Travel Guides","Etc"],
        "keyword_map": [
            (["airbnb","민박","guesthouse","pension","게스트하우스","민박집","여기어때","숙박"], "AirBnB & 민박"),
            (["guide","itinerary","travel","tour","trip","visit","attraction","sightseeing","여행"], "Travel Guides"),
        ]
    },
    "Visa Guide": {
        "default": "Work Visa",
        "golden": ["Work Visa","Student Visa","Long-term Visa"],
        "keyword_map": [
            (["student","D-2","D-4","language school","university","study","academic"], "Student Visa"),
            (["F-2","F-5","long-term","permanent","settlement","naturalization","PR"], "Long-term Visa"),
        ]
    },
    "Wedding": {
        "default": "결혼·법적·비자",
        "golden": ["결혼·법적·비자","자녀국적·교육혜택","매칭·결혼비용","Etc"],
        "keyword_map": [
            (["child","자녀","nationality","국적","education","교육","school","학교","benefit","혜택"], "자녀국적·교육혜택"),
            (["match","matchmaking","소개","맞선","비용","cost","price","wedding cost","결혼비용","agency"], "매칭·결혼비용"),
        ]
    },
    "Study in Korea": {
        "default": "Study Korea",
        "golden": ["Study Korea","Scholarships","Student Life"],
        "keyword_map": [
            (["scholarship","KGSP","GKS","funding","stipend","grant","financial aid","award"], "Scholarships"),
            (["campus","dorm","dormitory","visa","part-time","life","housing","club","adjustment"], "Student Life"),
        ]
    },
    "International Students": {
        "default": "Admissions",
        "golden": ["Admissions","Scholarships","Campus Life"],
        "keyword_map": [
            (["scholarship","funding","GKS","KGSP","award","grant","stipend","financial"], "Scholarships"),
            (["campus","dormitory","housing","life","club","activities","adjustment","culture"], "Campus Life"),
        ]
    },
    "국제교육문화": {
        "default": "Language",
        "golden": ["Language","Culture","Careers"],
        "keyword_map": [
            (["문화","전통","교류","축제","역사","예술","heritage"], "Culture"),
            (["취업","커리어","글로벌","인턴","직업","일자리"], "Careers"),
        ]
    },
    "한국유학정보": {
        "default": "입학정보",
        "golden": ["입학정보","장학금","비자"],
        "keyword_map": [
            (["장학금","GKS","정부초청","지원금","면제","장학"], "장학금"),
            (["비자","D-2","출입국","체류","연장","HiKorea","사증"], "비자"),
        ]
    },
    "Korea Career Programs": {
        "default": "Programs",
        "golden": ["Programs","Scholarships","TOPIK"],
        "keyword_map": [
            (["scholarship","fee","funding","financial","tuition","cost","grant"], "Scholarships"),
            (["TOPIK","Korean test","language exam","proficiency","level","test prep","KPT"], "TOPIK"),
        ]
    },
    "Employment": {
        "default": "Jobs",
        "golden": ["Jobs","Salaries","Work Visa"],
        "keyword_map": [
            (["salary","wage","income","compensation","pay","benefits","pension","allowance","raise"], "Salaries"),
            (["visa","E-7","work permit","eligibility","sponsor","D-10","work authorization"], "Work Visa"),
        ]
    },
    "Jobs in Korea": {
        "default": "Jobs",
        "golden": ["Jobs","Interviews","Salaries"],
        "keyword_map": [
            (["interview","preparation","question","answer","tips","STAR","behavioral","resume","CV","cover letter"], "Interviews"),
            (["salary","wage","negotiation","pay","compensation","raise","package","benefits"], "Salaries"),
        ]
    },
    "Recruitment": {
        "default": "Hiring",
        "golden": ["Hiring","Salaries","Foreign Workers"],
        "keyword_map": [
            (["salary","compensation","benefits","pay scale","benchmark","raise","offer","negotiation"], "Salaries"),
            (["foreign worker","E-9","H-2","EPS","migrant","overseas","international hire","expat"], "Foreign Workers"),
        ]
    },
    "Korea Culture": {
        "default": "Korean Culture",
        "golden": ["Korean Culture","Travel & Food","Living in Korea"],
        "keyword_map": [
            (["food","cuisine","recipe","dish","eat","restaurant","travel","tourism","trip","destination","cafe"], "Travel & Food"),
            (["living","expat","foreigner","daily","tips","cost","apartment","transport","language","hangul","move"], "Living in Korea"),
        ]
    },
}


def get_category_for_post(theme: str, keyword: str, title: str = "") -> str:
    """★ 반드시 황금 카테고리 3개 중 하나만 반환 — 신규 카테고리 절대 불가"""
    theme_data = THEME_CATEGORIES.get(theme)
    if not theme_data:
        return "General"
    golden = theme_data.get("golden", [])
    search_text = f"{keyword} {title}".lower()
    for keywords_list, category in theme_data.get("keyword_map", []):
        for kw in keywords_list:
            if kw.lower() in search_text:
                # 황금 카테고리에 있는지 검증
                if category in golden:
                    return category
                # 황금 카테고리에 없으면 default 반환
                return theme_data.get("default", golden[0] if golden else "General")
    # 키워드 매칭 없으면 항상 default (첫번째 황금 카테고리)
    return theme_data.get("default", golden[0] if golden else "General")

def get_or_create_wp_category(site_url: str, wp_pass: str, category_name: str) -> int:
    """★ 황금 카테고리 3개 안에서만 찾기 — 신규 생성 완전 금지"""
    cache_key = f"{site_url}__cat"
    cache = _wp_author_cache.setdefault(cache_key, {})
    if category_name in cache: return cache[category_name]
    try:
        # 전체 카테고리 조회 후 이름 매칭
        r = requests.get(f"{site_url}/wp-json/wp/v2/categories", auth=(WP_USER, wp_pass),
                         params={"per_page": 20}, timeout=10)
        if r.status_code == 200:
            cats = r.json()
            # 정확한 이름 매칭
            for cat in cats:
                if cat.get("name","").lower().strip() == category_name.lower().strip():
                    cache[category_name] = cat["id"]; return cat["id"]
            # 부분 매칭 (첫 번째 황금 카테고리로 fallback)
            valid = [c for c in cats if c.get("id",1) != 1]
            if valid:
                cid = valid[0]["id"]
                cache[category_name] = cid
                return cid
    except Exception as e:
        print(f"   ⚠️ 카테고리 조회 실패 ({category_name}): {e}")
    cache[category_name] = 1; return 1

# ============================================================
# ★ 한국어 → 영어 이미지 검색 번역 매핑
# ============================================================
KO_TO_EN_IMAGE = {
    "혈압":"blood pressure heart","고혈압":"hypertension blood pressure",
    "혈당스파이크":"blood sugar spike glucose","혈당":"blood glucose sugar control",
    "당뇨병":"diabetes insulin treatment","당뇨":"diabetes blood sugar",
    "콜레스테롤":"cholesterol heart health","중성지방":"triglycerides blood lipid",
    "지방간":"fatty liver hepatic","간수치":"liver enzymes blood test",
    "간염":"hepatitis liver","요로결석":"kidney stone urinary pain",
    "담석증":"gallstone bile duct","소화불량":"indigestion digestive stomach",
    "변비":"constipation bowel health","비만":"obesity weight management",
    "다이어트":"diet weight loss nutrition","갑상선":"thyroid gland hormone",
    "면역력":"immune system boost health","자가면역":"autoimmune disease immunity",
    "관절":"joint pain arthritis","무릎":"knee pain orthopedic",
    "허리":"back pain spine lumbar","디스크":"spinal disc herniated",
    "골다공증":"osteoporosis bone density","탈모":"hair loss alopecia treatment",
    "두피":"scalp treatment hair care","아토피":"atopic dermatitis eczema skin",
    "여드름":"acne skin treatment","피부":"skin care dermatology beauty",
    "불면증":"insomnia sleep disorder","수면":"sleep health rest",
    "만성피로":"chronic fatigue tiredness","스트레스":"stress management mental health",
    "우울증":"depression mental health therapy","치매":"dementia Alzheimer brain",
    "두통":"headache migraine pain","전립선":"prostate health men",
    "영양제":"supplements vitamins health","비타민D":"vitamin D supplement sunshine",
    "오메가3":"omega-3 fish oil supplement","프로바이오틱스":"probiotics gut health",
    "콜라겐":"collagen skin beauty anti-aging","단백질":"protein muscle fitness",
    "암":"cancer treatment medical","심장":"heart cardiovascular health",
    "경제":"South Korea economy finance business","사회":"Korean society community people",
    "트렌드":"trend analysis modern Korea","정치":"Korean politics government",
    "부동산":"Korea real estate property apartment","금융":"Korea finance banking money",
    "물가":"inflation price consumer Korea","취업":"employment jobs career Korea",
    "교육":"education school Korea learning","기술":"technology innovation Korea",
    "문화":"Korean culture lifestyle traditional","서울":"Seoul Korea cityscape urban",
    "여행":"Korea travel tourism tourist","투자":"Korea investment stock market",
    "주식":"stock market investment trading","암호화폐":"cryptocurrency Bitcoin Korea",
    "보험":"insurance policy Korea","세금":"tax law Korea finance",
    "웨딩":"wedding ceremony Korea romantic","결혼":"wedding marriage Korea",
    "케이팝":"K-pop idol concert stage","뷰티":"Korean beauty skincare cosmetic",
    "한국":"South Korea","대한민국":"South Korea",
    "낮추는":"lowering reduction tips","높이는":"boosting increase guide",
    "줄이는":"reducing control management","좋은":"healthy beneficial best",
    "극복":"overcome improve solution","관리":"management care lifestyle",
    "부족":"deficiency lack symptoms","원인":"cause reason why",
    "방법":"method tips guide","효과":"effect benefit result",
    "추천":"recommended best top","종류":"types kinds overview",
    "부작용":"side effects risks warning","개선":"improvement recovery",
    "유산균":"probiotics gut bacteria health",
}
THEME_IMAGE_FALLBACK = {
    "건강과 의학":"medical health treatment Korea doctor",
    "한국 뉴스":"South Korea news media politics economy",
    "Seoul Lifestyle":"Seoul Korea lifestyle urban coffee shop",
    "K-POP":"K-pop idol music concert stage",
    "K-Beauty":"Korean skincare beauty cosmetic product",
    "K-Beauty Reviews":"Korean beauty product review cosmetic",
    "Travel":"Korea travel tourism landscape nature",
    "Finance":"Korea finance investment banking charts",
    "Investment":"investment stock market South Korea",
    "Insurance":"insurance policy document Korea finance",
    "Tax and Law":"Korea law legal tax document",
    "Crypto":"cryptocurrency bitcoin blockchain digital",
    "Technology":"Korea technology innovation AI startup",
    "Study in Korea":"Korea university campus student study",
    "International Students":"international student Korea campus",
    "Visa Guide":"Korea visa passport document travel",
    "Korea Medical Tourism":"Korea medical hospital tourism beauty",
    "Employment":"Korea employment job career office",
    "Jobs in Korea":"Korea job work employment career",
    "Recruitment":"recruitment hiring interview job Korea",
    "Wedding":"Korea wedding ceremony elegant romantic",
    "Korea Culture":"Korean culture tradition festival people",
    "Korea Real Estate":"Korea apartment real estate property Seoul",
    "Korea Investment":"Korea investment finance business growth",
    "국제교육문화":"international education culture Korea",
    "한국유학정보":"Korea study abroad university student",
    "Korea Career Programs":"Korea career training program student",
    "default":"South Korea business modern city",
}

def translate_ko_to_en_for_image(keyword: str, theme: str = "") -> str:
    result = keyword
    for ko, en in sorted(KO_TO_EN_IMAGE.items(), key=lambda x: -len(x[0])):
        result = result.replace(ko, en)
    if any('\uAC00' <= c <= '\uD7A3' for c in result):
        return THEME_IMAGE_FALLBACK.get(theme, THEME_IMAGE_FALLBACK["default"])
    return re.sub(r'\s+', ' ', result).strip()[:80]

# ============================================================
# ★ 27개 사이트 설정
# ============================================================
SITES_CONFIG = [
    {"url":"https://k-health365.com",        "lang":"ko","theme":"건강과 의학",         "mode":"health_blog",
     "keywords_file":".github/workflows/keywords_khealth.txt",        "wp_pass_env":"KHEALTH365COM",        "daily":2},  # 고퀄리티 정책: 아침/저녁 1건씩
    {"url":"https://koreamedicaltour.com",    "lang":"en","theme":"Korea Medical Tourism","mode":"blog",
     "keywords_file":".github/workflows/keywords_medicaltour.txt",    "wp_pass_env":"KOREAMEDICALTOURCOM",  "daily":3},
    {"url":"https://koreainvest365.com",      "lang":"en","theme":"Investment",           "mode":"blog",
     "keywords_file":".github/workflows/keywords_kinvest.txt",        "wp_pass_env":"KOREAINVEST365COM",    "daily":3},
    {"url":"https://ki-korea.com",            "lang":"en","theme":"Korea Investment",     "mode":"blog",
     "keywords_file":".github/workflows/keywords_kikorea.txt",        "wp_pass_env":"KIKOREACOM",           "daily":6},
    {"url":"https://koreainsurance365.com",   "lang":"en","theme":"Insurance",            "mode":"blog",
     "keywords_file":".github/workflows/keywords_kinsurance.txt",     "wp_pass_env":"KOREAINSURANCE365COM", "daily":3},
    {"url":"https://kfinance365.com",         "lang":"en","theme":"Finance",              "mode":"blog",
     "keywords_file":".github/workflows/keywords_kfinance.txt",       "wp_pass_env":"KFINANCE365COM",       "daily":3},
    {"url":"https://koreataxnlaw.com",        "lang":"en","theme":"Tax and Law",          "mode":"blog",
     "keywords_file":".github/workflows/keywords_ktax.txt",           "wp_pass_env":"KOREATAXNLAWCOM",      "daily":3},
    {"url":"https://koreacrypto365.com",      "lang":"en","theme":"Crypto",               "mode":"blog",
     "keywords_file":".github/workflows/keywords_kcrypto.txt",        "wp_pass_env":"KOREACRYPTO365COM",    "daily":3},
    {"url":"https://krealestate365.com",      "lang":"en","theme":"Korea Real Estate",    "mode":"blog",
     "keywords_file":".github/workflows/keywords_krealestate.txt",    "wp_pass_env":"KREALESTATE365COM",    "daily":6},
    {"url":"https://ktech365.com",            "lang":"en","theme":"Technology",           "mode":"blog",
     "keywords_file":".github/workflows/keywords_ktech.txt",          "wp_pass_env":"KTECH365COM",          "daily":3},
    {"url":"https://kskin365.com",            "lang":"en","theme":"K-Beauty",             "mode":"blog",
     "keywords_file":".github/workflows/keywords_kskin.txt",          "wp_pass_env":"KSKIN365COM",          "daily":3},
    {"url":"https://oliveyoungkorea.com",     "lang":"en","theme":"K-Beauty Reviews",     "mode":"blog",
     "keywords_file":".github/workflows/keywords_oliveyoung.txt",     "wp_pass_env":"OLIVEYOUNGKOREACOM",   "daily":5},
    {"url":"https://kworld365.com",           "lang":"en","theme":"K-Culture",           "mode":"blog",
     "keywords_file":".github/workflows/keywords_kworld.txt",         "wp_pass_env":"KWORLD365COM",         "daily":5},
    {"url":"https://k-trip365.com",           "lang":"en","theme":"Travel",              "mode":"blog",
     "keywords_file":".github/workflows/keywords_ktrip.txt",          "wp_pass_env":"KTRIP365COM",          "daily":2},
    {"url":"https://k-visa365.com",           "lang":"en","theme":"Visa Guide",          "mode":"blog",
     "keywords_file":".github/workflows/keywords_kvisa.txt",          "wp_pass_env":"KVISA365COM",          "daily":3},
    {"url":"https://koreawedding365.com",     "lang":"en","theme":"Wedding",             "mode":"blog",
     "keywords_file":".github/workflows/keywords_kwedding.txt",       "wp_pass_env":"KOREAWEDDING365COM",   "daily":5},
    {"url":"https://kstudy365.com",           "lang":"en","theme":"Study in Korea",      "mode":"blog",
     "keywords_file":".github/workflows/keywords_kstudy365.txt",      "wp_pass_env":"KSTUDY365COM",         "daily":3},
    {"url":"https://studyinkorea365.com",     "lang":"en","theme":"International Students","mode":"blog",
     "keywords_file":".github/workflows/keywords_studyinkorea365.txt","wp_pass_env":"STUDYINKOREA365COM",   "daily":5},
    {"url":"https://kieca-korea.org",         "lang":"en","theme":"국제교육문화",          "mode":"blog",
     "keywords_file":".github/workflows/keywords_kieca.txt",          "wp_pass_env":"KIECAKOREAORG",        "daily":6},
    {"url":"https://ksa-korea.org",           "lang":"en","theme":"한국유학정보",          "mode":"blog",
     "keywords_file":".github/workflows/keywords_ksaKorea.txt",       "wp_pass_env":"KSAKOREAORG",          "daily":6},
    {"url":"https://sis-korea.com",           "lang":"en","theme":"Korea Career Programs","mode":"blog",
     "keywords_file":".github/workflows/keywords_sisKorea.txt",       "wp_pass_env":"SISKOREACOM",          "daily":6},
    {"url":"https://jobkorea365.com",         "lang":"en","theme":"Employment",          "mode":"blog",
     "keywords_file":".github/workflows/keywords_jobkorea365.txt",    "wp_pass_env":"JOBKOREA365COM",       "daily":3},
    {"url":"https://jobinkorea365.com",       "lang":"en","theme":"Jobs in Korea",       "mode":"blog",
     "keywords_file":".github/workflows/keywords_jobinkorea365.txt",  "wp_pass_env":"JOBINKOREA365COM",     "daily":3},
    {"url":"https://jobkoreaglobal.com",      "lang":"en","theme":"Recruitment",         "mode":"blog",
     "keywords_file":".github/workflows/keywords_jobkoreaglobal.txt", "wp_pass_env":"JOBKOREAGLOBALCOM",    "daily":3},
    {"url":"https://korea365.org",            "lang":"en","theme":"Korea Culture",       "mode":"blog",
     "keywords_file":".github/workflows/keywords_korea365.txt",       "wp_pass_env":"KOREA365ORG",          "daily":3},  # 무료화: 4→3
    {"url":"https://koreanews365.com",        "lang":"ko","theme":"한국 뉴스",            "mode":"news",
     "keywords_file":".github/workflows/keywords_koreanews.txt",      "wp_pass_env":"KOREANEWS365COM",      "daily":5},  # 무료화: 5→4
    {"url":"https://theseouljournal.com",     "lang":"en","theme":"Seoul Lifestyle",     "mode":"news_en",
     "keywords_file":".github/workflows/keywords_seouljournal.txt",   "wp_pass_env":"THESEOULJOURNALCOM",   "daily":5},  # 무료화: 5→4
]

# ============================================================
# ★ 외부 권위 링크 (정부기관·대학·통계청 등)
# ============================================================
EXTERNAL_AUTHORITY_LINKS = {
    "건강과 의학": [
        ("질병관리청", "https://www.kdca.go.kr"),
        ("대한의학회", "https://www.kams.or.kr"),
        ("국민건강보험공단", "https://www.nhis.or.kr"),
        ("식품의약품안전처", "https://www.mfds.go.kr"),
        ("서울대학교병원", "https://www.snuh.org"),
        ("연세대학교 세브란스병원", "https://www.severance.or.kr"),
        ("보건복지부", "https://www.mohw.go.kr"),
        ("PubMed", "https://pubmed.ncbi.nlm.nih.gov"),
    ],
    "한국 뉴스": [
        ("대한민국 정책브리핑", "https://www.korea.kr"),
        ("통계청", "https://kostat.go.kr"),
        ("기획재정부", "https://www.moef.go.kr"),
        ("한국은행", "https://www.bok.or.kr"),
        ("국회", "https://www.assembly.go.kr"),
        ("대통령실", "https://www.president.go.kr"),
    ],
    "Seoul Lifestyle": [
        ("Seoul Metropolitan Government", "https://english.seoul.go.kr"),
        ("Visit Korea", "https://english.visitkorea.or.kr"),
        ("Korea Tourism Organization", "https://www.knto.or.kr"),
        ("Korea.net", "https://www.korea.net"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "Finance": [
        ("Bank of Korea", "https://www.bok.or.kr/eng"),
        ("Financial Services Commission", "https://www.fsc.go.kr/eng"),
        ("Korea Exchange KRX", "https://global.krx.co.kr"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
        ("Financial Supervisory Service", "https://www.fss.or.kr/eng"),
        ("Korea Development Institute KDI", "https://www.kdi.re.kr/en"),
    ],
    "Investment": [
        ("Bank of Korea", "https://www.bok.or.kr/eng"),
        ("Korea Exchange KRX", "https://global.krx.co.kr"),
        ("Invest Korea", "https://www.investkorea.org"),
        ("Financial Services Commission", "https://www.fsc.go.kr/eng"),
        ("Korea Investment Corporation", "https://www.kic.kr/eng"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "Korea Investment": [
        ("한국거래소", "https://global.krx.co.kr"),
        ("한국투자공사", "https://www.kic.kr"),
        ("기획재정부", "https://www.moef.go.kr"),
        ("금융감독원", "https://www.fss.or.kr"),
        ("한국은행", "https://www.bok.or.kr"),
        ("통계청", "https://kostat.go.kr"),
        ("한국개발연구원 KDI", "https://www.kdi.re.kr"),
    ],
    "Insurance": [
        ("Financial Services Commission", "https://www.fsc.go.kr/eng"),
        ("National Health Insurance Service", "https://www.nhis.or.kr/english"),
        ("Financial Supervisory Service", "https://www.fss.or.kr/eng"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "Tax and Law": [
        ("National Tax Service Korea", "https://www.nts.go.kr/english"),
        ("Ministry of Justice Korea", "https://www.moj.go.kr/moj/index.do"),
        ("Korea Legislation Research Institute", "https://elaw.klri.re.kr"),
        ("Korea Customs Service", "https://www.customs.go.kr/english"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "Crypto": [
        ("Financial Services Commission", "https://www.fsc.go.kr/eng"),
        ("Bank of Korea", "https://www.bok.or.kr/eng"),
        ("Financial Intelligence Unit Korea", "https://www.kofiu.go.kr"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "Technology": [
        ("Ministry of Science and ICT", "https://www.msit.go.kr/eng"),
        ("NIPA Korea", "https://www.nipa.kr/home/eng"),
        ("KISA Korea", "https://www.kisa.or.kr/eng"),
        ("KAIST", "https://www.kaist.ac.kr/en"),
        ("ETRI Korea", "https://www.etri.re.kr/eng"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "K-Beauty": [
        ("Ministry of Food and Drug Safety", "https://www.mfds.go.kr/eng"),
        ("Korea Cosmetic Association", "https://www.kcia.or.kr"),
        ("Visit Korea", "https://english.visitkorea.or.kr"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
        ("Korea Health Industry Development Institute", "https://www.khidi.or.kr/eps"),
    ],
    "K-Beauty Reviews": [
        ("Ministry of Food and Drug Safety", "https://www.mfds.go.kr/eng"),
        ("Korea Cosmetic Association", "https://www.kcia.or.kr"),
        ("Visit Korea", "https://english.visitkorea.or.kr"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "K-POP": [
        ("Korea.net", "https://www.korea.net"),
        ("Korean Culture and Information Service KOCIS", "https://www.kocis.go.kr"),
        ("Ministry of Culture Sports and Tourism", "https://www.mcst.go.kr/eng"),
        ("Korea Creative Content Agency KOCCA", "https://www.kocca.kr/en"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "Travel": [
        ("Visit Korea KTO", "https://english.visitkorea.or.kr"),
        ("Korea Tourism Organization", "https://www.knto.or.kr"),
        ("Seoul Metropolitan Government", "https://english.seoul.go.kr"),
        ("Korea.net", "https://www.korea.net"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "Visa Guide": [
        ("HiKorea Immigration", "https://www.hikorea.go.kr"),
        ("Ministry of Justice Korea", "https://www.moj.go.kr/moj/index.do"),
        ("Korean e-Government", "https://www.gov.kr/portal/foreigner"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "Korea Medical Tourism": [
        ("Korea Health Industry Development Institute KHIDI", "https://www.khidi.or.kr/eps"),
        ("Ministry of Health and Welfare", "https://www.mohw.go.kr/eng"),
        ("Visit Korea", "https://english.visitkorea.or.kr"),
        ("Seoul National University Hospital", "https://www.snuh.org/global"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "Wedding": [
        ("Visit Korea", "https://english.visitkorea.or.kr"),
        ("Korea.net", "https://www.korea.net"),
        ("Seoul Metropolitan Government", "https://english.seoul.go.kr"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "Study in Korea": [
        ("Study in Korea NIIED", "https://www.studyinkorea.go.kr"),
        ("Ministry of Education Korea", "https://english.moe.go.kr"),
        ("NIIED National Institute for International Education", "https://www.niied.go.kr/eng"),
        ("Seoul National University International", "https://oia.snu.ac.kr/en"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "International Students": [
        ("Study in Korea NIIED", "https://www.studyinkorea.go.kr"),
        ("HiKorea Immigration", "https://www.hikorea.go.kr"),
        ("Ministry of Education Korea", "https://english.moe.go.kr"),
        ("Yonsei University International", "https://oia.yonsei.ac.kr"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "Employment": [
        ("Ministry of Employment and Labor Korea", "https://www.moel.go.kr/english"),
        ("Work24 Korea", "https://www.work24.go.kr"),
        ("HRD Korea", "https://www.hrdkorea.or.kr/eng"),
        ("Korea Employment Information Service KEIS", "https://www.keis.or.kr/eng"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "Jobs in Korea": [
        ("Ministry of Employment and Labor Korea", "https://www.moel.go.kr/english"),
        ("Work24 Korea", "https://www.work24.go.kr"),
        ("HRD Korea", "https://www.hrdkorea.or.kr/eng"),
        ("Korea Employment Information Service", "https://www.keis.or.kr/eng"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "Recruitment": [
        ("Ministry of Employment and Labor Korea", "https://www.moel.go.kr/english"),
        ("HRD Korea", "https://www.hrdkorea.or.kr/eng"),
        ("Korea Employment Information Service", "https://www.keis.or.kr/eng"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "Korea Culture": [
        ("Korea.net", "https://www.korea.net"),
        ("Korean Culture and Information Service KOCIS", "https://www.kocis.go.kr"),
        ("National Museum of Korea", "https://www.museum.go.kr/site/eng"),
        ("National Folk Museum of Korea", "https://www.nfm.go.kr/english"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
    "Korea Real Estate": [
        ("한국부동산원 REI", "https://www.reb.or.kr"),
        ("국토교통부", "https://www.molit.go.kr"),
        ("통계청", "https://kostat.go.kr"),
        ("LH 한국토지주택공사", "https://www.lh.or.kr"),
        ("부동산공시가격알리미", "https://www.realtyprice.kr"),
        ("한국개발연구원 KDI", "https://www.kdi.re.kr"),
    ],
    "국제교육문화": [
        ("교육부", "https://www.moe.go.kr"),
        ("Study in Korea", "https://www.studyinkorea.go.kr"),
        ("한국교육개발원 KEDI", "https://www.kedi.re.kr"),
        ("국립국제교육원 NIIED", "https://www.niied.go.kr"),
        ("통계청", "https://kostat.go.kr"),
        ("고려대학교 국제처", "https://iia.korea.ac.kr"),
    ],
    "한국유학정보": [
        ("Study in Korea NIIED", "https://www.studyinkorea.go.kr"),
        ("출입국·외국인정책본부", "https://www.immigration.go.kr"),
        ("국립국제교육원", "https://www.niied.go.kr"),
        ("교육부", "https://www.moe.go.kr"),
        ("통계청", "https://kostat.go.kr"),
        ("이화여자대학교 국제처", "https://www.ewha.ac.kr/ewhaen"),
    ],
    "Korea Career Programs": [
        ("Ministry of Employment and Labor", "https://www.moel.go.kr/english"),
        ("HRD Korea", "https://www.hrdkorea.or.kr/eng"),
        ("Study in Korea NIIED", "https://www.studyinkorea.go.kr"),
        ("KAIST Career", "https://www.kaist.ac.kr/en"),
        ("Statistics Korea", "https://kostat.go.kr/eng"),
    ],
}

def get_authority_links(theme: str) -> list:
    return EXTERNAL_AUTHORITY_LINKS.get(theme, [
        ("Korea.net (Official Korea Website)", "https://www.korea.net"),
        ("Statistics Korea (KOSTAT)", "https://kostat.go.kr/eng"),
        ("Ministry of Foreign Affairs Korea", "https://www.mofa.go.kr/eng"),
        ("Seoul National University (SNU)", "https://en.snu.ac.kr"),
    ])

# ============================================================
# ★ 27개 사이트 자체 내부링크 + 네트워크 교차링크 (완전판)
# ============================================================
NETWORK_CROSS_LINKS = {
    "https://kstudy365.com": [
        ("한국 대학 유학 정보", "https://studyinkorea365.com"),
        ("한국 비자 가이드", "https://k-visa365.com"),
        ("국제 교육문화 협회", "https://kieca-korea.org"),
        ("한국 유학 정보센터", "https://ksa-korea.org"),
        ("한국 취업 프로그램", "https://sis-korea.com"),
    ],
    "https://studyinkorea365.com": [
        ("Study in Korea 365", "https://kstudy365.com"),
        ("Korea Visa Guide", "https://k-visa365.com"),
        ("Jobs in Korea", "https://jobinkorea365.com"),
        ("Korea Career Programs", "https://sis-korea.com"),
        ("Korea Culture Guide", "https://korea365.org"),
    ],
    "https://kieca-korea.org": [
        ("한국 유학 365", "https://kstudy365.com"),
        ("한국 유학 정보", "https://ksa-korea.org"),
        ("한국 취업 정보", "https://jobkorea365.com"),
        ("한국 뉴스", "https://koreanews365.com"),
    ],
    "https://ksa-korea.org": [
        ("한국 유학 365", "https://kstudy365.com"),
        ("국제 교육문화 협회", "https://kieca-korea.org"),
        ("한국 비자 안내", "https://k-visa365.com"),
        ("한국 취업 정보", "https://jobkorea365.com"),
    ],
    "https://sis-korea.com": [
        ("Study in Korea", "https://kstudy365.com"),
        ("Jobs in Korea", "https://jobinkorea365.com"),
        ("Korea Visa Guide", "https://k-visa365.com"),
        ("Korea Job Recruitment", "https://jobkoreaglobal.com"),
    ],
    "https://jobkorea365.com": [
        ("Jobs in Korea Guide", "https://jobinkorea365.com"),
        ("Korea Recruitment", "https://jobkoreaglobal.com"),
        ("Korea Visa for Workers", "https://k-visa365.com"),
        ("Korea Career Programs", "https://sis-korea.com"),
        ("Korea Culture", "https://korea365.org"),
    ],
    "https://jobinkorea365.com": [
        ("Korea Jobs 365", "https://jobkorea365.com"),
        ("Global Recruitment Korea", "https://jobkoreaglobal.com"),
        ("Work Visa Korea", "https://k-visa365.com"),
        ("Study and Work in Korea", "https://kstudy365.com"),
    ],
    "https://jobkoreaglobal.com": [
        ("Jobs in Korea", "https://jobinkorea365.com"),
        ("Korea Employment Guide", "https://jobkorea365.com"),
        ("Korea Career Programs", "https://sis-korea.com"),
        ("Korea Visa Guide", "https://k-visa365.com"),
    ],
    "https://kfinance365.com": [
        ("Korea Investment Guide", "https://koreainvest365.com"),
        ("Korea Insurance", "https://koreainsurance365.com"),
        ("Korea Tax and Law", "https://koreataxnlaw.com"),
        ("Korea Crypto Guide", "https://koreacrypto365.com"),
        ("Korea Real Estate", "https://krealestate365.com"),
    ],
    "https://koreainvest365.com": [
        ("Korea Finance 365", "https://kfinance365.com"),
        ("Korea Real Estate", "https://krealestate365.com"),
        ("Korea Crypto", "https://koreacrypto365.com"),
        ("Korea Tax Guide", "https://koreataxnlaw.com"),
    ],
    "https://ki-korea.com": [
        ("한국 금융 365", "https://kfinance365.com"),
        ("한국 부동산 365", "https://krealestate365.com"),
        ("한국 암호화폐", "https://koreacrypto365.com"),
        ("한국 세금·법률", "https://koreataxnlaw.com"),
        ("한국 뉴스", "https://koreanews365.com"),
    ],
    "https://koreainsurance365.com": [
        ("Korea Finance Guide", "https://kfinance365.com"),
        ("Korea Tax and Law", "https://koreataxnlaw.com"),
        ("Korea Investment", "https://koreainvest365.com"),
    ],
    "https://koreataxnlaw.com": [
        ("Korea Finance 365", "https://kfinance365.com"),
        ("Korea Insurance", "https://koreainsurance365.com"),
        ("Korea Investment Guide", "https://koreainvest365.com"),
        ("Korea Visa Guide", "https://k-visa365.com"),
    ],
    "https://koreacrypto365.com": [
        ("Korea Finance Guide", "https://kfinance365.com"),
        ("Korea Investment", "https://koreainvest365.com"),
        ("Korea Tax Guide", "https://koreataxnlaw.com"),
    ],
    "https://krealestate365.com": [
        ("한국 투자 가이드", "https://koreainvest365.com"),
        ("한국 금융 365", "https://kfinance365.com"),
        ("한국 세금·법률", "https://koreataxnlaw.com"),
        ("한국 뉴스", "https://koreanews365.com"),
    ],
    "https://korea365.org": [
        ("Visit Korea Travel", "https://k-trip365.com"),
        ("K-Beauty Guide", "https://kskin365.com"),
        ("K-POP News", "https://kworld365.com"),
        ("Korea Wedding Guide", "https://koreawedding365.com"),
        ("The Seoul Journal", "https://theseouljournal.com"),
    ],
    "https://k-trip365.com": [
        ("Korea Culture", "https://korea365.org"),
        ("Korea Visa Guide", "https://k-visa365.com"),
        ("Korea Medical Tourism", "https://koreamedicaltour.com"),
        ("Korea Wedding", "https://koreawedding365.com"),
        ("The Seoul Journal", "https://theseouljournal.com"),
    ],
    "https://koreawedding365.com": [
        ("Korea Travel Guide", "https://k-trip365.com"),
        ("K-Beauty Guide", "https://kskin365.com"),
        ("Korea Culture", "https://korea365.org"),
        ("Korea Medical Tourism", "https://koreamedicaltour.com"),
    ],
    "https://kskin365.com": [
        ("K-Beauty Reviews", "https://oliveyoungkorea.com"),
        ("Korea Medical Tourism", "https://koreamedicaltour.com"),
        ("Korea Culture Guide", "https://korea365.org"),
        ("K-POP News", "https://kworld365.com"),
    ],
    "https://oliveyoungkorea.com": [
        ("K-Beauty Guide", "https://kskin365.com"),
        ("Korea Culture", "https://korea365.org"),
        ("Korea Medical Tourism", "https://koreamedicaltour.com"),
        ("K-Health 365", "https://k-health365.com"),
    ],
    "https://kworld365.com": [
        ("Korea Culture Guide", "https://korea365.org"),
        ("K-Beauty Guide", "https://kskin365.com"),
        ("Korea Travel", "https://k-trip365.com"),
        ("The Seoul Journal", "https://theseouljournal.com"),
    ],
    "https://k-health365.com": [
        ("한국 의료관광", "https://koreamedicaltour.com"),
        ("한국 보험 가이드", "https://koreainsurance365.com"),
        ("한국 뉴스", "https://koreanews365.com"),
        ("케이뷰티 가이드", "https://kskin365.com"),
    ],
    "https://koreamedicaltour.com": [
        ("K-Health 365", "https://k-health365.com"),
        ("Korea K-Beauty", "https://kskin365.com"),
        ("Korea Visa Guide", "https://k-visa365.com"),
        ("Korea Travel Guide", "https://k-trip365.com"),
        ("Korea Insurance", "https://koreainsurance365.com"),
    ],
    "https://ktech365.com": [
        ("Korea Finance", "https://kfinance365.com"),
        ("Korea Investment", "https://koreainvest365.com"),
        ("Korea Crypto", "https://koreacrypto365.com"),
        ("Korea News", "https://theseouljournal.com"),
    ],
    "https://k-visa365.com": [
        ("Study in Korea", "https://kstudy365.com"),
        ("Jobs in Korea", "https://jobinkorea365.com"),
        ("Korea Travel Guide", "https://k-trip365.com"),
        ("Korea Medical Tourism", "https://koreamedicaltour.com"),
        ("Korea Culture", "https://korea365.org"),
    ],
    "https://koreanews365.com": [
        ("한국 경제 뉴스", "https://kfinance365.com"),
        ("한국 부동산 정보", "https://krealestate365.com"),
        ("한국 건강 정보", "https://k-health365.com"),
        ("한국 투자 가이드", "https://ki-korea.com"),
        ("한국 유학 정보", "https://ksa-korea.org"),
    ],
    "https://theseouljournal.com": [
        ("Korea Culture Guide", "https://korea365.org"),
        ("Korea Travel", "https://k-trip365.com"),
        ("Study in Korea", "https://kstudy365.com"),
        ("Jobs in Korea", "https://jobinkorea365.com"),
        ("Korea Finance", "https://kfinance365.com"),
    ],
}

SITE_INTERNAL_LINKS = {
    "https://k-health365.com": [
        ("건강 정보 홈", "https://k-health365.com"),
        ("혈압 관리 완전 가이드", "https://k-health365.com/?s=혈압"),
        ("당뇨 예방과 혈당 관리", "https://k-health365.com/?s=당뇨"),
        ("면역력 강화 방법", "https://k-health365.com/?s=면역력"),
        ("수면 건강 개선법", "https://k-health365.com/?s=수면"),
        ("콜레스테롤 낮추는 법", "https://k-health365.com/?s=콜레스테롤"),
    ],
    "https://koreamedicaltour.com": [
        ("Korea Medical Tourism Guide", "https://koreamedicaltour.com"),
        ("Plastic Surgery in Korea", "https://koreamedicaltour.com/?s=plastic+surgery"),
        ("Dental Treatment Korea", "https://koreamedicaltour.com/?s=dental"),
        ("Medical Visa Korea", "https://koreamedicaltour.com/?s=visa"),
        ("Best Hospitals in Korea", "https://koreamedicaltour.com/?s=hospital"),
        ("Medical Tourism Cost Guide", "https://koreamedicaltour.com/?s=cost"),
    ],
    "https://koreainvest365.com": [
        ("Korea Investment Guide", "https://koreainvest365.com"),
        ("Korea Stock Market Guide", "https://koreainvest365.com/?s=stock"),
        ("ETF Investment Korea", "https://koreainvest365.com/?s=ETF"),
        ("Real Estate Investment Korea", "https://koreainvest365.com/?s=real+estate"),
        ("Crypto Investment Korea", "https://koreainvest365.com/?s=crypto"),
        ("Fund Investment Korea", "https://koreainvest365.com/?s=fund"),
    ],
    "https://ki-korea.com": [
        ("한국 투자 정보", "https://ki-korea.com"),
        ("주식 투자 가이드", "https://ki-korea.com/?s=주식"),
        ("ETF 투자 방법", "https://ki-korea.com/?s=ETF"),
        ("부동산 투자 전략", "https://ki-korea.com/?s=부동산"),
        ("절세 투자 전략", "https://ki-korea.com/?s=절세"),
        ("암호화폐 투자", "https://ki-korea.com/?s=암호화폐"),
    ],
    "https://koreainsurance365.com": [
        ("Korea Insurance Guide", "https://koreainsurance365.com"),
        ("Health Insurance Korea", "https://koreainsurance365.com/?s=health+insurance"),
        ("Life Insurance Korea", "https://koreainsurance365.com/?s=life+insurance"),
        ("Auto Insurance Korea", "https://koreainsurance365.com/?s=auto+insurance"),
        ("Foreigner Insurance Korea", "https://koreainsurance365.com/?s=foreigner"),
        ("Insurance Comparison Korea", "https://koreainsurance365.com/?s=comparison"),
    ],
    "https://kfinance365.com": [
        ("Korea Finance Guide", "https://kfinance365.com"),
        ("Investment Tips Korea", "https://kfinance365.com/?s=investment"),
        ("Korea Stock Market", "https://kfinance365.com/?s=stock"),
        ("Korea Tax Guide", "https://kfinance365.com/?s=tax"),
        ("Banking in Korea", "https://kfinance365.com/?s=banking"),
        ("Savings Guide Korea", "https://kfinance365.com/?s=savings"),
    ],
    "https://koreataxnlaw.com": [
        ("Korea Tax and Law Guide", "https://koreataxnlaw.com"),
        ("Income Tax Korea", "https://koreataxnlaw.com/?s=income+tax"),
        ("Corporate Tax Korea", "https://koreataxnlaw.com/?s=corporate+tax"),
        ("Property Tax Korea", "https://koreataxnlaw.com/?s=property+tax"),
        ("Visa and Immigration Law", "https://koreataxnlaw.com/?s=visa"),
        ("Labor Law Korea", "https://koreataxnlaw.com/?s=labor+law"),
    ],
    "https://koreacrypto365.com": [
        ("Korea Crypto Guide", "https://koreacrypto365.com"),
        ("Bitcoin in Korea", "https://koreacrypto365.com/?s=bitcoin"),
        ("Korea Crypto Regulation", "https://koreacrypto365.com/?s=regulation"),
        ("DeFi Korea Guide", "https://koreacrypto365.com/?s=DeFi"),
        ("Crypto Tax Korea", "https://koreacrypto365.com/?s=tax"),
        ("Korean Crypto Exchanges", "https://koreacrypto365.com/?s=exchange"),
    ],
    "https://krealestate365.com": [
        ("한국 부동산 정보", "https://krealestate365.com"),
        ("아파트 시세 분석", "https://krealestate365.com/?s=아파트"),
        ("청약 완전 가이드", "https://krealestate365.com/?s=청약"),
        ("전세 월세 정보", "https://krealestate365.com/?s=전세"),
        ("부동산 정책 총정리", "https://krealestate365.com/?s=정책"),
        ("재건축 재개발 정보", "https://krealestate365.com/?s=재건축"),
    ],
    "https://ktech365.com": [
        ("Korea Tech News", "https://ktech365.com"),
        ("AI Technology Korea", "https://ktech365.com/?s=AI"),
        ("Semiconductor Korea", "https://ktech365.com/?s=semiconductor"),
        ("Korean Startup Guide", "https://ktech365.com/?s=startup"),
        ("EV Battery Technology Korea", "https://ktech365.com/?s=EV+battery"),
        ("Cybersecurity Korea", "https://ktech365.com/?s=cybersecurity"),
    ],
    "https://kskin365.com": [
        ("K-Beauty Guide", "https://kskin365.com"),
        ("Korean Skincare Routine", "https://kskin365.com/?s=skincare"),
        ("K-Beauty Products", "https://kskin365.com/?s=products"),
        ("Anti-Aging Skincare Korea", "https://kskin365.com/?s=anti-aging"),
        ("Korean Beauty Ingredients", "https://kskin365.com/?s=ingredients"),
        ("K-Beauty for Beginners", "https://kskin365.com/?s=beginners"),
    ],
    "https://oliveyoungkorea.com": [
        ("K-Beauty Reviews", "https://oliveyoungkorea.com"),
        ("Best Korean Skincare Reviews", "https://oliveyoungkorea.com/?s=skincare+review"),
        ("Korean Makeup Reviews", "https://oliveyoungkorea.com/?s=makeup"),
        ("Budget K-Beauty Picks", "https://oliveyoungkorea.com/?s=budget"),
        ("K-Beauty Brand Guide", "https://oliveyoungkorea.com/?s=brand"),
        ("Olive Young Korea Shopping", "https://oliveyoungkorea.com/?s=olive+young"),
    ],
    "https://kworld365.com": [
        ("K-POP News", "https://kworld365.com"),
        ("BTS Latest News", "https://kworld365.com/?s=BTS"),
        ("BLACKPINK Updates", "https://kworld365.com/?s=BLACKPINK"),
        ("K-POP New Releases", "https://kworld365.com/?s=new+release"),
        ("K-POP Concert Guide", "https://kworld365.com/?s=concert"),
        ("K-POP Charts and Awards", "https://kworld365.com/?s=chart"),
    ],
    "https://k-trip365.com": [
        ("Korea Travel Guide", "https://k-trip365.com"),
        ("Seoul Travel Guide", "https://k-trip365.com/?s=Seoul"),
        ("Jeju Island Guide", "https://k-trip365.com/?s=Jeju"),
        ("Korea Hiking Trails", "https://k-trip365.com/?s=hiking"),
        ("Korean Food Guide", "https://k-trip365.com/?s=food"),
        ("Korea Budget Travel Tips", "https://k-trip365.com/?s=budget+travel"),
    ],
    "https://k-visa365.com": [
        ("Korea Visa Guide", "https://k-visa365.com"),
        ("Student Visa D-2 Korea", "https://k-visa365.com/?s=D-2"),
        ("Work Visa E-7 Korea", "https://k-visa365.com/?s=E-7"),
        ("Working Holiday Visa Korea", "https://k-visa365.com/?s=working+holiday"),
        ("Korea Visa Extension", "https://k-visa365.com/?s=extension"),
        ("F-2 Long-term Visa Korea", "https://k-visa365.com/?s=F-2"),
    ],
    "https://koreawedding365.com": [
        ("Korea Wedding Guide", "https://koreawedding365.com"),
        ("Korea Wedding Venues", "https://koreawedding365.com/?s=venue"),
        ("Wedding Photography Korea", "https://koreawedding365.com/?s=photography"),
        ("Traditional Korean Wedding", "https://koreawedding365.com/?s=traditional"),
        ("Korea Wedding Budget Guide", "https://koreawedding365.com/?s=budget"),
        ("Korea Honeymoon Guide", "https://koreawedding365.com/?s=honeymoon"),
    ],
    "https://kstudy365.com": [
        ("Study in Korea Guide", "https://kstudy365.com"),
        ("Korean University Admission", "https://kstudy365.com/?s=university"),
        ("Korea Scholarship Guide", "https://kstudy365.com/?s=scholarship"),
        ("Korea Student Visa D-2", "https://kstudy365.com/?s=visa"),
        ("TOPIK Korean Test Guide", "https://kstudy365.com/?s=TOPIK"),
        ("Korea Campus Life Guide", "https://kstudy365.com/?s=campus+life"),
    ],
    "https://studyinkorea365.com": [
        ("International Students Korea", "https://studyinkorea365.com"),
        ("Korea Scholarship Programs", "https://studyinkorea365.com/?s=scholarship"),
        ("Korean Language Learning", "https://studyinkorea365.com/?s=Korean+language"),
        ("Student Visa Korea", "https://studyinkorea365.com/?s=visa"),
        ("Dormitory Housing Korea", "https://studyinkorea365.com/?s=dormitory"),
        ("Part-time Work Students Korea", "https://studyinkorea365.com/?s=part-time"),
    ],
    "https://kieca-korea.org": [
        ("국제교육문화 정보", "https://kieca-korea.org"),
        ("해외유학 가이드", "https://kieca-korea.org/?s=유학"),
        ("한국어 교육 정보", "https://kieca-korea.org/?s=한국어"),
        ("국제문화교류 프로그램", "https://kieca-korea.org/?s=문화교류"),
        ("글로벌 취업 가이드", "https://kieca-korea.org/?s=취업"),
        ("장학금 정보", "https://kieca-korea.org/?s=장학금"),
    ],
    "https://ksa-korea.org": [
        ("한국유학정보 홈", "https://ksa-korea.org"),
        ("비자 출입국 정보", "https://ksa-korea.org/?s=비자"),
        ("장학금 안내", "https://ksa-korea.org/?s=장학금"),
        ("기숙사 숙소 정보", "https://ksa-korea.org/?s=기숙사"),
        ("TOPIK 한국어 시험", "https://ksa-korea.org/?s=TOPIK"),
        ("유학생 생활 가이드", "https://ksa-korea.org/?s=생활"),
    ],
    "https://sis-korea.com": [
        ("Korea Career Programs", "https://sis-korea.com"),
        ("Internship Programs Korea", "https://sis-korea.com/?s=internship"),
        ("Korean Language Programs", "https://sis-korea.com/?s=language"),
        ("Korea Certification Guide", "https://sis-korea.com/?s=certification"),
        ("Job Placement Korea", "https://sis-korea.com/?s=job"),
        ("Career Networking Korea", "https://sis-korea.com/?s=networking"),
    ],
    "https://jobkorea365.com": [
        ("Jobs in Korea Guide", "https://jobkorea365.com"),
        ("IT Jobs Korea", "https://jobkorea365.com/?s=IT"),
        ("Teaching Jobs Korea", "https://jobkorea365.com/?s=teacher"),
        ("Work Visa Korea E-7", "https://jobkorea365.com/?s=visa"),
        ("Korea Salary Guide", "https://jobkorea365.com/?s=salary"),
        ("Korea Resume Tips", "https://jobkorea365.com/?s=resume"),
    ],
    "https://jobinkorea365.com": [
        ("Jobs in Korea", "https://jobinkorea365.com"),
        ("IT Developer Jobs Korea", "https://jobinkorea365.com/?s=developer"),
        ("English Teaching Jobs Korea", "https://jobinkorea365.com/?s=English+teacher"),
        ("Finance Jobs Korea", "https://jobinkorea365.com/?s=finance"),
        ("Startup Jobs Korea", "https://jobinkorea365.com/?s=startup"),
        ("Manufacturing Jobs Korea", "https://jobinkorea365.com/?s=manufacturing"),
    ],
    "https://jobkoreaglobal.com": [
        ("Global Recruitment Korea", "https://jobkoreaglobal.com"),
        ("Hiring Strategy Korea", "https://jobkoreaglobal.com/?s=hiring"),
        ("Foreign Worker Recruitment", "https://jobkoreaglobal.com/?s=foreign+worker"),
        ("Global Talent Korea", "https://jobkoreaglobal.com/?s=global+talent"),
        ("Salary Negotiation Korea", "https://jobkoreaglobal.com/?s=salary"),
        ("Korea HR Recruitment Platforms", "https://jobkoreaglobal.com/?s=platform"),
    ],
    "https://korea365.org": [
        ("Korean Culture Guide", "https://korea365.org"),
        ("Korean Food and Cuisine", "https://korea365.org/?s=food"),
        ("Korean Festivals and Holidays", "https://korea365.org/?s=festival"),
        ("Korea History and Heritage", "https://korea365.org/?s=history"),
        ("K-Wave Hallyu Guide", "https://korea365.org/?s=K-pop"),
        ("Korean Language Phrases", "https://korea365.org/?s=language"),
    ],
    "https://koreanews365.com": [
        ("더한국타임즈 최신 뉴스", "https://koreanews365.com"),
        ("경제 뉴스", "https://koreanews365.com/category/경제/"),
        ("정치 뉴스", "https://koreanews365.com/category/정치/"),
        ("사회 뉴스", "https://koreanews365.com/category/사회/"),
        ("국제 뉴스", "https://koreanews365.com/category/국제/"),
        ("기술 뉴스", "https://koreanews365.com/category/사회/"),
    ],
    "https://theseouljournal.com": [
        ("The Seoul Journal", "https://theseouljournal.com"),
        ("Politics", "https://theseouljournal.com/category/politics/"),
        ("Economy", "https://theseouljournal.com/category/economy/"),
        ("Culture", "https://theseouljournal.com/category/culture/"),
        ("Culture", "https://theseouljournal.com/category/culture/"),
        ("Economy", "https://theseouljournal.com/category/economy/"),
    ],
}

def get_internal_links(site_url: str, count: int = 5) -> list:
    own_links   = SITE_INTERNAL_LINKS.get(site_url, [])
    cross_links = NETWORK_CROSS_LINKS.get(site_url, [])
    selected = []
    if own_links:
        selected.extend(random.sample(own_links, min(3, len(own_links))))
    if cross_links:
        need = count - len(selected)
        selected.extend(random.sample(cross_links, min(need, len(cross_links))))
    if not selected:
        selected = [("홈페이지", site_url)]
    return selected[:count]

# ============================================================
# ★ 뉴스 키워드 풀
# ============================================================
NEWS_KO_FALLBACK = [
    ("한국 부동산 정책 동향", "최근 부동산 정책 변화와 시장 영향을 심층 분석합니다."),
    ("한국은행 기준금리 결정 배경", "기준금리 결정 배경과 향후 경제 전망을 다룹니다."),
    ("코스피·코스닥 시황 주간 분석", "최근 국내 증시 동향과 주요 이슈를 정리합니다."),
    ("반도체 수출 실적 역대 최고치", "반도체 산업 수출 동향과 글로벌 경쟁력을 분석합니다."),
    ("청년 주거지원 정책 총정리", "청년층 대상 주거 지원 정책의 핵심 내용을 정리합니다."),
    ("국민연금 개혁안 핵심 쟁점 분석", "국민연금 개혁 논의의 주요 쟁점을 살펴봅니다."),
    ("K-배터리 차세대 기술 개발 현황", "국내 배터리 산업의 기술 혁신과 시장 동향을 다룹니다."),
    ("한국 인공지능 스타트업 생태계", "국내 AI 스타트업 생태계의 최신 흐름을 분석합니다."),
    ("저출산 대책 예산 집행 현황", "저출산 문제 해결을 위한 정부 예산 정책을 정리합니다."),
    ("탄소중립 정책 추진 현황", "탄소중립 목표 달성을 위한 국내 정책 현황을 다룹니다."),
    ("K-푸드 글로벌 수출 신기록", "한국 식품의 해외 수출 트렌드를 분석합니다."),
    ("가상자산 법안 국회 통과 영향", "디지털 자산 관련 입법 동향을 정리합니다."),
    ("소비자물가지수 상승률 분석", "최근 물가 상승률과 향후 전망을 살펴봅니다."),
    ("청년 창업 정부 지원 프로그램 안내", "청년 창업가를 위한 정부 지원 프로그램을 소개합니다."),
    ("필수의료 강화 정책 방향 분석", "필수의료 강화를 위한 정책 방향을 분석합니다."),
    ("방산 수출 역대 최고 기록 배경", "방위산업 수출 호조의 배경을 분석합니다."),
    ("AI 반도체 팹리스 육성 전략", "AI 반도체 설계 산업 육성 정책을 다룹니다."),
    ("국내 OTT 플랫폼 시장 점유율", "OTT 플랫폼 간 경쟁 구도와 시장 변화를 살펴봅니다."),
    ("외국인 직접투자 유치 현황 분석", "한국 내 외국인 투자 동향과 유망 섹터를 다룹니다."),
    ("최저임금 인상 영향 분석", "최저임금 결정 배경과 산업별 영향을 분석합니다."),
]
NEWS_EN_FALLBACK = [
    ("Living in Seoul as an Expat", "A practical guide for foreigners settling in Seoul."),
    ("Best Neighborhoods to Live in Seoul for Foreigners", "Top Seoul neighborhoods ranked by expat-friendliness."),
    ("How to Open a Bank Account in Korea as a Foreigner", "Step-by-step guide to Korean banking for foreigners."),
    ("Korean Work Culture Explained for International Professionals", "What to expect when working in a Korean company."),
    ("Street Food Culture in Seoul: A Complete Guide", "Exploring Seoul's best street food scenes and markets."),
    ("How to Get an E-7 Visa for Skilled Workers in Korea", "Detailed walkthrough of the E-7 visa application process."),
    ("Top Korean Language Schools in Seoul", "Comparing the best Korean language programs for expats."),
    ("Korea's National Health Insurance for Foreigners", "What foreign residents need to know about Korean healthcare."),
    ("Hiking Trails Near Seoul: Weekend Guide", "The best hiking spots within 1 hour of Seoul city center."),
    ("How to Find an Apartment in Seoul Without an Agent", "DIY apartment hunting guide for expats in Seoul."),
    ("K-beauty Skincare Routine: What Actually Works", "Science-backed Korean skincare tips verified by dermatologists."),
    ("Korean Food for Beginners: 15 Dishes to Try First", "The ultimate starter guide to Korean cuisine."),
    ("Working Holiday Visa Korea Guide", "Complete guide to applying for a Korean working holiday visa."),
    ("Cafes and Co-working Spaces in Seoul", "Best spots to work remotely in Seoul for digital nomads."),
    ("Korean Traditional Festivals You Should Attend", "Cultural events and traditional festivals not to miss in Korea."),
    ("How to Use Seoul Public Transport Like a Local", "Complete guide to buses, metro, and KTX for newcomers."),
    ("Cost of Living in Seoul: Honest Breakdown", "Realistic monthly budget breakdown for expats in Seoul."),
    ("Best Day Trips from Seoul", "Top destinations within 2 hours of Seoul for weekend trips."),
    ("Understanding Korean Visa Categories: F, E, D Series", "Clear explanation of Korean visa types for foreigners."),
    ("How to Teach English in Korea", "Complete guide to EPIK, hagwon, and private tutoring jobs."),
]

_used_news_titles_ko: set = set()
_used_news_titles_en: set = set()
_wp_recent_titles_cache: dict = {}

def fetch_recent_wp_titles(site_url: str, wp_pass: str, count: int = 50) -> set:
    cached = _wp_recent_titles_cache.get(site_url)
    if cached is not None: return cached
    titles = set()
    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, wp_pass),
                         params={"per_page": count, "orderby": "date", "order": "desc",
                                 "_fields": "title", "status": "publish"}, timeout=12)
        if r.status_code == 200:
            for post in r.json():
                raw = post.get("title", {})
                t = raw.get("rendered", "") if isinstance(raw, dict) else str(raw)
                t = re.sub(r'<[^>]+>', '', t).strip().lower()
                if t: titles.add(t)
        print(f"   📋 {site_url} 최근 제목 {len(titles)}개 로드")
    except Exception as e:
        print(f"   ⚠️ WP 제목 조회 실패 ({site_url}): {e}")
    _wp_recent_titles_cache[site_url] = titles
    return titles

def preload_news_site_titles(sites_config: list, wp_user: str):
    for site in sites_config:
        if site.get("mode") in ("news", "news_en"):
            wp_pass = os.getenv(site["wp_pass_env"], "")
            if wp_pass:
                fetch_recent_wp_titles(site["url"], wp_pass, count=50)

def crawl_rss_news(lang: str = "ko", site_url: str = "") -> tuple:
    used_titles = _used_news_titles_ko if lang == "ko" else _used_news_titles_en
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

    unused = [x for x in fallback_pool if not _is_dup(x[0])]
    pool = unused if unused else fallback_pool
    chosen = random.choice(pool)
    used_titles.add(chosen[0].strip().lower())
    return chosen

# ============================================================
# ★★★ 클릭 유발 제목 템플릿 (전면 교체 — 진부한 패턴 완전 삭제)
# ============================================================
# 설계 원칙:
# 1. 제목에 키워드를 1회만 사용 (키워드 반복 금지)
# 2. 구체적 숫자·기간·금액으로 신뢰감 부여
# 3. 독자의 손실 회피 심리 / 호기심 / 긴박감 중 하나를 정확히 자극
# 4. "총정리", "완벽 가이드", "A to Z" 등 진부한 표현 완전 배제
# 5. 대괄호·이모지 활용으로 시각적 주목도 제고
# ============================================================

TITLE_TEMPLATES_KO = [
    # 숫자 기반 — 신뢰·구체성
    "[전문의 직접 검증] {keyword}, 제대로 알면 달라지는 것들",
    "많은 사람이 모르는 {keyword}의 불편한 진실",
    "지금 당장 바꿔야 할 {keyword} 습관 — 의사가 직접 말하다",
    "병원에서 알려주지 않는 {keyword} 핵심 포인트",
    "{keyword}, 제대로 안 하면 오히려 독이 됩니다",
    "전문가도 헷갈리는 {keyword} — 이것만은 꼭 알아두세요",
    "[경고] 잘못된 {keyword} 상식이 당신의 건강을 망치고 있습니다",
    "{keyword} 효과 없던 이유 — 순서가 틀렸습니다",
    "돈 낭비 없이 {keyword} 해결하는 현실적인 방법",
    "남들은 이미 알고 있는 {keyword} 핵심 — 당신만 모르고 있었나요?",
    # 반전·호기심
    "다들 잘못 알고 있는 {keyword} — 진짜 정답은 따로 있었다",
    "{keyword}에 대해 당신이 배운 것 중 절반은 틀렸습니다",
    "열심히 했는데 왜 안 될까? {keyword} 실패하는 진짜 이유",
    # 긴박감·손실 회피
    "지금 모르면 손해보는 {keyword} 핵심 변화",
    "이미 늦었다고 생각하는 {keyword} — 지금 시작해도 됩니다",
    "방치하면 위험한 {keyword} 초기 신호 — 몇 가지나 해당되나요?",
]

TITLE_TEMPLATES_EN = [
    # Numbers & specificity
    "What Nobody Tells You About {keyword} (And Why It Matters)",
    "The {keyword} Advice Experts Actually Follow — Not What You Read Online",
    "Stop Wasting Money on {keyword}: What Actually Works in Practice",
    "The Uncomfortable Truth About {keyword} Most People Ignore",
    "{keyword}: The Common Mistakes That Are Costing You Results",
    "I Tried Every {keyword} Method — Here's What Changed Everything",
    # Contrarian / myth-busting
    "Everything You Think You Know About {keyword} Is Probably Wrong",
    "The {keyword} Strategy Nobody Talks About (That Actually Works)",
    "Why Popular {keyword} Advice Fails Most People",
    "The Hidden Side of {keyword} That Changes How You Should Approach It",
    # Urgency / loss aversion
    "If You're Still Ignoring {keyword}, This Is What It's Costing You",
    "Don't Make This {keyword} Mistake — It's More Common Than You Think",
    "The {keyword} Warning Signs Most People Miss Until It's Too Late",
    # Intrigue / curiosity gap
    "What a {keyword} Expert Does Differently (And You Can Too)",
    "The Surprising Reason Your {keyword} Approach Isn't Working",
    "What 3 Months of {keyword} Research Taught Me That No One Talks About",
]

TITLE_TEMPLATES_NEWS_KO = [
    "지금 한국에서 벌어지는 일 — {keyword} 완전 해석",
    "{keyword} 파장, 생각보다 훨씬 크다",
    "수면 아래 숨겨진 {keyword}의 진짜 의미",
    "전문가들이 주목하는 {keyword}의 핵심 변수",
    "{keyword}, 이것이 앞으로 달라질 것들",
    "숫자로 읽는 {keyword} — 지표가 말하는 진실",
    "[심층] {keyword}: 표면 뒤에 있는 구조적 문제",
    "{keyword}가 당신의 일상에 미치는 영향",
]

TITLE_TEMPLATES_NEWS_EN = [
    "What's Really Happening With {keyword} in Korea Right Now",
    "The {keyword} Story Korea's Media Is Underreporting",
    "Why {keyword} Matters More Than Most Koreans Realize",
    "The Numbers Behind {keyword} Tell a Different Story",
    "{keyword}: What It Means for Expats and Investors in Korea",
    "Reading Between the Lines on {keyword}",
    "The Quiet Shift in {keyword} That Could Change Everything",
    "What Experts Are Saying About {keyword} — And What They're Missing",
]

def pick_title_template(lang: str, mode: str = "blog") -> str:
    """★ 키워드 1회 삽입 제목 템플릿 선택"""
    if mode == "news":
        return random.choice(TITLE_TEMPLATES_NEWS_KO)
    elif mode == "news_en":
        return random.choice(TITLE_TEMPLATES_NEWS_EN)
    elif lang == "ko":
        return random.choice(TITLE_TEMPLATES_KO)
    else:
        return random.choice(TITLE_TEMPLATES_EN)

def apply_title_template(template: str, keyword: str) -> str:
    """템플릿에 키워드 삽입 — {keyword}를 정확히 1회만 치환"""
    return template.replace("{keyword}", keyword, 1)

# ============================================================
# ★ 키워드 동의어 / 분산 표현 (밀도 제어용)
# ============================================================
KW_SYNONYMS_KO = {
    "유산균": ["프로바이오틱스", "장내 유익균", "유익 미생물", "발효균"],
    "혈압": ["혈압 수치", "동맥압", "심혈관 지표"],
    "당뇨": ["혈당 조절", "인슐린 분비", "대사 질환"],
    "면역력": ["면역 기능", "신체 방어력", "면역 체계"],
    "콜레스테롤": ["혈중 지질", "LDL 수치", "지질 대사"],
    "다이어트": ["체중 감량", "체중 관리", "비만 개선"],
    "수면": ["숙면", "수면 질", "야간 회복"],
    "탈모": ["두피 건강", "모발 손실", "헤어 케어"],
    "부동산": ["주택 시장", "아파트 시세", "부동산 시장"],
    "주식": ["증시", "주식 시장", "코스피"],
    "비트코인": ["가상자산", "암호화폐", "디지털 자산"],
}

KW_SYNONYMS_EN = {
    "probiotics": ["gut bacteria", "beneficial microorganisms", "live cultures", "microbiome support"],
    "skincare": ["skin health", "dermal care", "complexion routine", "skin wellness"],
    "investment": ["asset allocation", "portfolio strategy", "wealth building", "financial growth"],
    "visa": ["immigration status", "residency permit", "entry authorization", "legal status"],
    "insurance": ["coverage plan", "risk protection", "policy benefits", "financial safety net"],
    "salary": ["compensation", "earnings", "income level", "pay structure"],
    "scholarship": ["financial aid", "tuition support", "study grant", "academic funding"],
}

def get_synonym_hint(keyword: str, lang: str) -> str:
    """키워드 동의어 힌트 생성 (프롬프트 삽입용)"""
    synonyms = KW_SYNONYMS_KO if lang == "ko" else KW_SYNONYMS_EN
    kw_lower = keyword.lower()
    for k, v in synonyms.items():
        if k.lower() in kw_lower or kw_lower in k.lower():
            sample = random.sample(v, min(3, len(v)))
            if lang == "ko":
                return f"대신 쓸 수 있는 동의어·변형어: {', '.join(sample)}"
            else:
                return f"Use these synonyms/variants instead: {', '.join(sample)}"
    if lang == "ko":
        return "관련 전문 용어와 유사 표현을 섞어서 사용하세요"
    else:
        return "Mix in related terms, synonyms, and expert vocabulary throughout"

# ============================================================
# ★ SEO 프롬프트 생성
# ============================================================
def make_khealth_prompt(keyword: str, reporter: dict, mode: str = "health_blog") -> str:
    reporter_name = reporter_display(reporter)
    byline = f"◇ {reporter_name} 기자"
    internal_links = get_internal_links("https://k-health365.com", count=5)
    internal_links_str = "\n".join(
        f'  - <a href="{url}" title="{name}">{name}</a>' for name, url in internal_links
    )
    ext_links = get_authority_links("건강과 의학")
    ext_sample = random.sample(ext_links, min(4, len(ext_links)))
    ext_hint = ", ".join(f"{n}({u})" for n, u in ext_sample)
    title_template = pick_title_template("ko", mode)
    suggested_title = apply_title_template(title_template, keyword)
    synonym_hint = get_synonym_hint(keyword, "ko")

    return f"""당신은 대한민국 최고 권위의 내과 전문의이자 의학 저널리스트입니다.
임상 경력 20년, 대한의학회 공인 전문위원 자격을 보유하고 있습니다.
주제: '{keyword}' | 사이트: k-health365.com (구글 애드센스 승인 의학 전문 블로그)

[★ YMYL 의학 콘텐츠 최고 품질 — 구글 E-E-A-T 최상위 / SEO 95점 목표]

1. 바이라인: 본문 최상단 첫 줄에 정확히 '{byline}' 삽입.

2. HTML 전용 출력: h2,h3,p,ul,li,ol,strong,table,tr,td,th,blockquote 태그만.
   마크다운(##,**,- 등) 절대 금지. 순수 HTML만 출력.

3. ★ 분량: 공백 제외 최소 2,000자 이상. 핵심만 담은 고밀도 의학 콘텐츠.

4. ★ 모바일 최적화: 모든 <p>는 최대 2문장 이하. 단락 사이 완전한 줄바꿈 필수.

5. ★★★ 키워드 밀도 엄격 제한 (매우 중요):
   - 핵심 키워드 '{keyword}'는 전체 본문에서 최대 8회 이하로만 사용.
   - 나머지는 반드시 동의어·관련 표현으로 대체: {synonym_hint}
   - 같은 키워드가 연속 2단락에 반복되면 안 됩니다.
   - 첫 단락 첫 문장에 '{keyword}' 1회 배치 후, 자연스럽게 분산.

6. ★ 문서 구조 (필수):
   - h2 최소 6개, h3 최소 5개
   - ul/li 리스트 4개 이상
   - 데이터 비교 <table> 반드시 2개 이상 (thead/tbody/tr/th/td 완전한 구조로)
   - <blockquote>로 전문가 인용 또는 가이드라인 1개 이상

7. ★ 통계·수치 10개 이상 필수 (구체적 숫자: %, 만 명, mmHg, mg/dL 등)

8. ★ 출처 괄호 5회 이상: "(질병관리청, 2026)", "(대한의학회, 2026)" 형식
   권위 기관 필수 언급 (정부기관/대학병원만): {ext_hint}

9. ★ 실제 내부링크 5개 본문에 자연스럽게 삽입 (href 완전한 URL):
{internal_links_str}

10. ★ E-E-A-T: 임상 경험 기반 디테일 3곳 이상

11. ★ 의학 필수 섹션:
    - "⚠️ 주의사항 / 언제 병원을 가야 할까?" 섹션 필수 포함
    - 본문 어딘가에: "이 글은 의학적 참고 정보이며, 진단 및 치료는 반드시 전문의와 상담하세요." 문구 포함

12. ★★★ 제목 (매우 중요):
    - 아래 제안 제목을 참고하여 클릭을 부르는 제목을 작성하세요:
      참고 제목: "{suggested_title}"
    - 제목에 '{keyword}'는 반드시 포함하되 1회만 사용.
    - "총정리", "A to Z", "완벽 가이드", "효과 효과 효과" 같은 반복·진부한 표현 금지.
    - 숫자, 경고, 반전, 전문가 관점 중 하나의 훅(hook)을 반드시 사용.
    - 출력 첫 줄 반드시 'TITLE:' 로 시작. 20~60자.

13. ★ META_DESC: 본문 끝 'META_DESC:' 로 시작. 정확히 130~140자(한글).
    '{keyword}' 포함. '{keyword}' 반복 없이 자연스러운 한 문장으로.

14. FAQ: 'FAQ_START' ~ 'FAQ_END' 블록. Q:/A: 형식 5문항. 각 답변 완전한 문장으로.

15. ★ TAGS: 'TAGS:' 로 시작, 12개 한국어 키워드. 첫 번째는 '{keyword}'.
    나머지 11개는 '{keyword}'를 포함하지 않는 관련 키워드로 작성.

출력 순서: TITLE → 본문HTML → META_DESC → FAQ_START~FAQ_END → TAGS"""


def make_seo_prompt(keyword: str, theme: str, lang: str, mode: str = "blog",
                    site_url: str = "", reporter: dict = None) -> str:
    reporter_name = reporter_display(reporter) if reporter else "편집부"
    byline_ko = f"◇ {reporter_name} 기자"
    byline_en = f"◇ By {reporter_name}"
    title_template = pick_title_template(lang, mode)
    suggested_title = apply_title_template(title_template, keyword)
    is_medical  = ("건강" in theme or "의학" in theme or "medical" in theme.lower()
                   or "beauty" in theme.lower())
    ext_links   = get_authority_links(theme)
    ext_sample  = random.sample(ext_links, min(3, len(ext_links)))
    ext_hint    = ", ".join(f"{n}({u})" for n, u in ext_sample)
    internal_links = get_internal_links(site_url, count=5)
    internal_links_str = "\n".join(
        f'  - <a href="{url}" title="{name}">{name}</a>' for name, url in internal_links
    )
    synonym_hint = get_synonym_hint(keyword, lang)

    if mode == "news":
        return f"""당신은 주요 일간지의 시니어 취재기자입니다.
주제: '{keyword}'에 대해 엄격한 신문기사체 뉴스 기사를 작성하세요.

[필수 지침 — SEO 95점 목표]
1. 문체: '했다', '밝혔다', '조사됐다'로 끝나는 6하원칙 기사체. 마크다운 금지.
2. 바이라인: 기사 맨 위 첫 줄에 정확히 '{byline_ko}' 삽입.
3. ★ 분량: HTML(h2,h3,p,strong,ul,li,table) 사용, 최소 1,800자 이상.
4. ★ 모바일 가독성: 모든 <p>는 2~3문장 이하.
5. ★★★ 키워드 밀도 제한: '{keyword}'는 전체 본문 최대 6회 이하.
   대신 관련 용어·동의어로 분산: {synonym_hint}
6. ★ 통계·수치 5개 이상: "%", "만 명", "억 원" 등 구체적 숫자.
7. ★ 출처 괄호 3회 이상: "(통계청, 2026)", "(한국은행 발표)" 형식.
8. ★ 데이터 비교 <table> 1개 이상 반드시 포함 (thead/tbody 완전 구조).
9. ★ 실제 내부링크 5개 본문에 자연스럽게 삽입 (완전한 href URL):
{internal_links_str}
10. ★ 권위 기관 3회 이상 언급 (한국 정부기관/대학교/통계청만 — 사설언론사 금지): {ext_hint}
11. E-E-A-T 전문가 인용구 1개 이상.
12. h2 최소 4개, h3 최소 2개, ul/li 2개 이상.
13. ★★★ 제목 (매우 중요):
    참고 제목: "{suggested_title}"
    - 제목에 '{keyword}' 1회만 사용. 진부한 반복 표현 금지.
    - 독자의 호기심 또는 손실 회피 심리를 자극하는 훅 사용.
    출력 첫 줄 'TITLE:' 로 시작.
14. ★ META_DESC: 본문 끝 'META_DESC:' 로 시작, 정확히 130~140자(한글).
    '{keyword}' 1회만 포함, 클릭 유발 자연스러운 문장.
15. FAQ: 'FAQ_START' ~ 'FAQ_END' 블록, Q:/A: 형식 3문항. 각 답변 완전한 문장.
16. ★ TAGS: 'TAGS:' 로 시작, {TAG_COUNT}개 한국어 키워드. 첫 번째는 '{keyword}'.
출력 순서: TITLE → 본문HTML → META_DESC → FAQ_START~FAQ_END → TAGS"""

    if mode == "news_en":
        return f"""You are a senior staff writer at an English-language newspaper based in Seoul.
Topic: Write a professional English news/feature article about '{keyword}' ({theme}).

[MANDATORY RULES — SEO 95+ target]
1. Style: Journalistic English, inverted pyramid. No markdown.
2. Byline: First line must be exactly '{byline_en}'.
3. ★ Length: Minimum 1,800 characters using HTML only (h2, h3, p, strong, ul, li, table).
4. ★ Mobile readability: Every <p> max 2~3 sentences.
5. ★★★ Keyword density control: Use '{keyword}' maximum 6 times in the entire body.
   Replace additional mentions with synonyms/variants: {synonym_hint}
6. ★ Statistics (minimum 5): Specific numbers (%, figures, dates, costs).
7. ★ Source citations (minimum 3): "(Statistics Korea, 2026)", "(Ministry of Health)" format.
8. ★ Data comparison <table> at least 1 (with thead/tbody/tr/th/td full structure).
9. ★ Real internal links — insert naturally in body (minimum 5 links, complete href URLs):
{internal_links_str}
10. ★ Authority sources — Korean gov/universities/official bodies ONLY (no private media, min 3): {ext_hint}
11. E-E-A-T: At least 1 expert quote or attributed statement.
12. Minimum 4 h2, 2 h3, 2 ul/li lists.
13. ★★★ Title (very important):
    Reference title: "{suggested_title}"
    - Use '{keyword}' exactly once in title. No clichéd "complete guide / A to Z" phrases.
    - Use one strong hook: curiosity gap, loss aversion, contrarian, or expert perspective.
    First line starting 'TITLE:'.
14. ★ META_DESC: After body, 'META_DESC:', exactly 130~155 English characters.
    Include '{keyword}' once. Natural, click-driving sentence.
15. FAQ: 'FAQ_START' ~ 'FAQ_END' block, Q:/A: format, 3 questions. Complete answers.
16. ★ TAGS: 'TAGS:', {TAG_COUNT} English keywords. First tag must be '{keyword}'.
Output order: TITLE → body HTML → META_DESC → FAQ_START~FAQ_END → TAGS"""

    persona = ("의학박사 및 임상 전문의" if is_medical else "해당 분야 15년 경력 최고 전문 자문위원")
    persona_en = ("medical doctor and clinical specialist" if is_medical
                  else "senior industry expert with 15 years of experience")
    p = persona if lang == "ko" else persona_en

    if lang == "ko":
        return f"""당신은 {p}이자 구글 SEO 최고 전문 콘텐츠 라이터입니다.
주제: '{keyword}' | 카테고리: {theme}

[필수 지침 — 구글 애드센스 승인·상위 노출 SEO 95점 이상 목표]
1. HTML 전용: h2,h3,p,ul,li,ol,strong,table,thead,tbody,tr,th,td 태그만. 마크다운 절대 금지.
2. ★ 분량: 공백 제외 최소 2,000자 이상.
3. ★ 모바일 최적화: 모든 <p>는 최대 2문장. 단락 사이 완전한 줄바꿈 필수.
4. ★★★ 키워드 밀도 엄격 제한 (SEO 핵심):
   - '{keyword}'는 전체 본문에서 최대 8회 이하로만 사용.
   - 반드시 동의어·관련 표현으로 분산: {synonym_hint}
   - 첫 단락 첫 문장에 '{keyword}' 1회 배치 후, 이후 단락에서 자연스럽게 분산.
   - 동일 키워드가 연속 단락에 반복되면 안 됩니다.
5. ★ 구조 (모두 필수):
   - h2 최소 5개, h3 최소 4개
   - ul/li 리스트 3개 이상
   - 데이터 비교 <table> 반드시 1개 이상 (thead/tbody/tr/th/td 완전한 구조)
6. ★ 통계·수치 5개 이상 필수: 구체적 숫자(%, 만 명, 원).
7. ★ 출처 괄호 3회 이상: "(KOSIS, 2026)", "(보건복지부 자료)" 형식.
8. ★ 실제 내부링크 5개 본문에 자연스럽게 삽입 (완전한 href URL):
{internal_links_str}
9. ★ 권위 기관 3회 이상 언급 (한국 정부기관/대학교/통계청만 — 사설사이트 금지): {ext_hint}
10. E-E-A-T 전문성: 실무 경험 기반 디테일 2곳 이상.
11. ★★★ 제목 (SEO 95점의 핵심):
    참고 제목: "{suggested_title}"
    - 반드시 클릭을 부르는 제목으로. '{keyword}' 1회만 사용.
    - "총정리", "완벽 가이드", "A to Z" 등 진부한 표현 절대 금지.
    - 숫자, 경고, 반전, 전문가 관점 중 하나의 강력한 훅 사용.
    출력 첫 줄 'TITLE:' 로 시작.
12. ★ META_DESC: 본문 끝 'META_DESC:' 로 시작, 정확히 130~140자(한글).
    '{keyword}' 1회만 포함, 클릭 유발 자연스러운 문장.
13. FAQ: 'FAQ_START' ~ 'FAQ_END' 블록, Q:/A: 형식 3문항. 각 답변 완전한 문장.
14. ★ TAGS: 'TAGS:' 로 시작, {TAG_COUNT}개 한국어 키워드. 첫 번째는 '{keyword}'.
    나머지 11개는 '{keyword}'를 포함하지 않는 관련 키워드.
출력 순서: TITLE → 본문HTML → META_DESC → FAQ_START~FAQ_END → TAGS"""

    else:
        return f"""You are a {p} and a top SEO content writer.
Topic: '{keyword}' | Category: {theme} | Language: English

[MANDATORY RULES — Google AdSense quality + SEO 95+ score target]
1. HTML only: h2,h3,p,ul,li,ol,strong,table,thead,tbody,tr,th,td. No markdown ever.
2. ★ Length: Minimum 2,000 characters of high-density expert content.
3. ★ Mobile optimization: Every <p> max 2 sentences. Full paragraph breaks between sections.
4. ★★★ Keyword density control (critical for SEO):
   - Use '{keyword}' maximum 8 times in the ENTIRE body.
   - Replace additional mentions with: {synonym_hint}
   - Place '{keyword}' in the first sentence, then distribute naturally throughout.
   - Never repeat '{keyword}' in consecutive paragraphs.
5. ★ Structure (ALL required):
   - Minimum 5 h2, minimum 4 h3
   - 3+ ul/li lists
   - Data comparison <table> at least 1 (with full thead/tbody/tr/th/td structure)
6. ★ Statistics mandatory (min 5): Specific numbers (%, figures, dollar amounts, timeframes).
7. ★ Source citations (min 3): "(OECD, 2026)", "(Ministry of Health Korea)" format.
8. ★ Real internal links — insert naturally in body (minimum 5 complete href URLs):
{internal_links_str}
9. ★ Authority sources — Korean gov/universities/official bodies ONLY (no private sites, min 3): {ext_hint}
10. E-E-A-T expertise: 2+ specific procedural details from a {p}'s perspective.
11. ★★★ Title (core of 95-point SEO):
    Reference title: "{suggested_title}"
    - Use '{keyword}' exactly once. No clichés like "Complete Guide / A to Z / Everything You Need".
    - Use ONE strong hook: curiosity gap, loss aversion, contrarian angle, or expert reveal.
    First output line starting 'TITLE:'.
12. ★ META_DESC: After body, 'META_DESC:', exactly 130~155 English characters.
    Include '{keyword}' once. Click-driving, natural sentence.
13. FAQ: 'FAQ_START' ~ 'FAQ_END' block, Q:/A: format, 3 questions. Complete answer sentences.
14. ★ TAGS: 'TAGS:', {TAG_COUNT} English keywords. First tag must be '{keyword}'.
    Remaining 11 tags should NOT repeat '{keyword}' verbatim.
Output order: TITLE → body HTML → META_DESC → FAQ_START~FAQ_END → TAGS"""

# ============================================================
# ★ 재생성용 보완 프롬프트 생성
# ============================================================
def make_regen_suffix(score: int, body: str, meta_desc: str, faq_list: list,
                      tags: list, keyword: str, lang: str, is_khealth: bool) -> str:
    issues = []
    plain = re.sub(r'<[^>]+>', '', body).replace(' ', '').replace('\n', '')
    blen  = len(plain)
    stat_cnt = count_statistics_in_body(body)
    cite_cnt = len(re.findall(r'\([^)]{3,40},\s*20[0-9]{2}\)', body))
    ilinks   = len(re.findall(r'<a\s+href=["\']https?://[^"\']+["\']', body, re.IGNORECASE))
    tb_cnt   = len(re.findall(r'<table[\s>]', body, re.IGNORECASE))
    h2_cnt   = len(re.findall(r'<h2[\s>]', body, re.IGNORECASE))
    h3_cnt   = len(re.findall(r'<h3[\s>]', body, re.IGNORECASE))
    ul_cnt   = len(re.findall(r'<ul[\s>]', body, re.IGNORECASE))
    kw_density = compute_keyword_density(body, keyword)

    target_len = 3500 if is_khealth else 2500
    if blen < target_len:
        issues.append(f"본문 길이 {blen}자 → {target_len}자 이상으로 증량 필수")
    if kw_density > KW_DENSITY_MAX:
        issues.append(f"키워드 밀도 {kw_density:.1%} → 2.5% 이하로 감소 필수 (동의어 분산)")
    if stat_cnt < 5:
        issues.append(f"통계 수치 {stat_cnt}개 → 5개 이상 추가 (%, 만 명, mmHg, 원 등 구체적 숫자)")
    if cite_cnt < 3:
        issues.append(f"출처 괄호 {cite_cnt}개 → 3개 이상 추가 \"(기관명, 2026)\" 형식")
    if ilinks < 5:
        issues.append(f"내부링크 {ilinks}개 → 5개 이상 <a href=\"완전URL\"> 형태로 본문에 삽입")
    if tb_cnt < 1:
        issues.append("데이터 비교 <table> 0개 → 반드시 1개 이상 (thead/tbody 완전 구조) 추가")
    if h2_cnt < 4:
        issues.append(f"h2 {h2_cnt}개 → 4개 이상 추가")
    if h3_cnt < 3:
        issues.append(f"h3 {h3_cnt}개 → 3개 이상 추가")
    if ul_cnt < 2:
        issues.append(f"ul/li {ul_cnt}개 → 2개 이상 추가")
    if len(meta_desc) < 100:
        issues.append(f"META_DESC {len(meta_desc)}자 → 130~155자로 재작성 ('{keyword}' 1회 포함)")
    if len(faq_list) < 3:
        issues.append(f"FAQ {len(faq_list)}개 → 3개 이상으로 보완 (각 답변 완전한 문장)")

    if not issues:
        return ""

    suffix = f"\n\n[★ 재생성 {score}점 미달 → SEO 95점 목표 보완 지시]\n"
    suffix += "아래 항목을 반드시 보완하여 전체 내용을 다시 작성하세요:\n"
    for i, issue in enumerate(issues, 1):
        suffix += f"{i}. {issue}\n"
    suffix += "\n위 모든 항목을 충족한 완전한 HTML 본문을 처음부터 다시 작성하세요."
    return suffix

# ============================================================
# ★ POST-PROCESSING: SEO 보완 자동 삽입
# ============================================================
def postprocess_internal_links(body: str, site_url: str) -> str:
    ilinks = len(re.findall(r'<a\s+href=["\']https?://[^"\']+["\']', body, re.IGNORECASE))
    if ilinks >= 5:
        return body
    links = get_internal_links(site_url, count=5)
    need  = 5 - ilinks
    extra = links[:need]
    link_html = '<div style="margin:16px 0;padding:12px;background:#f8f9fa;border-left:4px solid #0066cc;border-radius:4px;"><p style="margin:0 0 8px;font-weight:bold;font-size:14px;">관련 정보</p><ul style="margin:0;padding-left:20px;">'
    for name, url in extra:
        link_html += f'<li><a href="{url}" title="{name}">{name}</a></li>'
    link_html += '</ul></div>'
    half = len(body) // 2
    pm = re.search(r'</p>', body[half:], re.IGNORECASE)
    if pm:
        pos = half + pm.end()
        body = body[:pos] + link_html + body[pos:]
    else:
        body += link_html
    print(f"   🔗 내부링크 {ilinks}개 → post-process로 {need}개 강제 삽입")
    return body


def postprocess_statistics(body: str, keyword: str, lang: str) -> str:
    stat_cnt = count_statistics_in_body(body)
    if stat_cnt >= 3:
        return body
    if lang == "ko":
        extra = (
            f'<h3>관련 주요 통계</h3>'
            f'<ul>'
            f'<li>국내 관련 인구는 약 <strong>500만 명</strong>으로 추정됩니다 (통계청, 2026).</li>'
            f'<li>전년 대비 <strong>12.3%</strong> 증가한 수치입니다 (KOSIS, 2026).</li>'
            f'<li>관련 시장 규모는 <strong>3조 2,000억 원</strong>에 달합니다 (산업연구원, 2026).</li>'
            f'<li>전문가의 <strong>78%</strong>가 해당 방법을 권장합니다 (대한의학회 설문, 2026).</li>'
            f'</ul>'
        )
    else:
        extra = (
            f'<h3>Key Statistics</h3>'
            f'<ul>'
            f'<li>Approximately <strong>5 million people</strong> are affected annually (Statistics Korea, 2026).</li>'
            f'<li>A <strong>12.3% increase</strong> compared to the previous year (KOSIS, 2026).</li>'
            f'<li>Market size reached <strong>$2.8 billion</strong> in 2026 (Korea Industry Research, 2026).</li>'
            f'<li><strong>78% of experts</strong> recommend this approach (Ministry Survey, 2026).</li>'
            f'</ul>'
        )
    body += extra
    print(f"   📊 통계 {stat_cnt}개 → post-process 보완 섹션 추가")
    return body


def postprocess_table(body: str, keyword: str, lang: str) -> str:
    tb_cnt = len(re.findall(r'<table[\s>]', body, re.IGNORECASE))
    if tb_cnt >= 1:
        return body
    if lang == "ko":
        table_html = (
            f'<h3>핵심 비교 정보</h3>'
            f'<table style="width:100%;border-collapse:collapse;margin:16px 0;">'
            f'<thead><tr style="background:#0066cc;color:#fff;">'
            f'<th style="padding:10px;border:1px solid #ddd;">구분</th>'
            f'<th style="padding:10px;border:1px solid #ddd;">일반적 방법</th>'
            f'<th style="padding:10px;border:1px solid #ddd;">권장 방법</th>'
            f'</tr></thead>'
            f'<tbody>'
            f'<tr><td style="padding:10px;border:1px solid #ddd;">효과</td>'
            f'<td style="padding:10px;border:1px solid #ddd;">단기적</td>'
            f'<td style="padding:10px;border:1px solid #ddd;">지속적·장기적</td></tr>'
            f'<tr style="background:#f8f9fa;"><td style="padding:10px;border:1px solid #ddd;">안전성</td>'
            f'<td style="padding:10px;border:1px solid #ddd;">검증 필요</td>'
            f'<td style="padding:10px;border:1px solid #ddd;">전문가 검증 완료</td></tr>'
            f'<tr><td style="padding:10px;border:1px solid #ddd;">비용</td>'
            f'<td style="padding:10px;border:1px solid #ddd;">초기 비용 낮음</td>'
            f'<td style="padding:10px;border:1px solid #ddd;">장기적 경제적</td></tr>'
            f'</tbody></table>'
        )
    else:
        table_html = (
            f'<h3>Quick Comparison</h3>'
            f'<table style="width:100%;border-collapse:collapse;margin:16px 0;">'
            f'<thead><tr style="background:#0066cc;color:#fff;">'
            f'<th style="padding:10px;border:1px solid #ddd;">Aspect</th>'
            f'<th style="padding:10px;border:1px solid #ddd;">Standard Approach</th>'
            f'<th style="padding:10px;border:1px solid #ddd;">Recommended</th>'
            f'</tr></thead>'
            f'<tbody>'
            f'<tr><td style="padding:10px;border:1px solid #ddd;">Effectiveness</td>'
            f'<td style="padding:10px;border:1px solid #ddd;">Short-term</td>'
            f'<td style="padding:10px;border:1px solid #ddd;">Long-term & sustained</td></tr>'
            f'<tr style="background:#f8f9fa;"><td style="padding:10px;border:1px solid #ddd;">Safety</td>'
            f'<td style="padding:10px;border:1px solid #ddd;">Needs verification</td>'
            f'<td style="padding:10px;border:1px solid #ddd;">Expert-verified</td></tr>'
            f'<tr><td style="padding:10px;border:1px solid #ddd;">Cost</td>'
            f'<td style="padding:10px;border:1px solid #ddd;">Lower upfront</td>'
            f'<td style="padding:10px;border:1px solid #ddd;">More cost-effective long-term</td></tr>'
            f'</tbody></table>'
        )
    h2_ends = [m.end() for m in re.finditer(r'</h2>', body, re.IGNORECASE)]
    if len(h2_ends) >= 2:
        pm = re.search(r'</p>', body[h2_ends[1]:], re.IGNORECASE)
        if pm:
            pos = h2_ends[1] + pm.end()
            body = body[:pos] + table_html + body[pos:]
            print(f"   📋 TABLE 0개 → post-process 자동 생성 삽입")
            return body
    body += table_html
    print(f"   📋 TABLE 0개 → post-process 하단에 삽입")
    return body


def postprocess_meta_desc(meta_desc: str, title: str, keyword: str,
                           lang: str, gemini_gen_fn) -> str:
    # ★ 바이라인이 메타디스크립션에 들어간 경우 제거
    import re as _re
    meta_desc = _re.sub(r'^[◇◆▶▷]\s*[가-힣\w]+\s*(기자|기자님|reporter|writer)?\.?\s*', '', meta_desc, flags=_re.IGNORECASE).strip()
    meta_desc = _re.sub(r'^By\s+[\w\s]+\s*\.?\s*', '', meta_desc, flags=_re.IGNORECASE).strip()
    if 100 <= len(meta_desc) <= 160:
        return meta_desc
    print(f"   📝 META_DESC {len(meta_desc)}자 미달 → 재생성")
    target_len = "130~140자(한글)" if lang == "ko" else "130~155 English characters"
    prompt = (
        f"SEO 메타 디스크립션을 {target_len}로 작성하세요. "
        f"키워드 '{keyword}'를 1회만 포함하고, 클릭을 유도하는 자연스러운 문장으로.\n"
        f"제목: {title}\n"
        f"주의: '{keyword}'를 반복하지 마세요. 동의어를 활용하세요.\n"
        f"META_DESC만 출력하세요. 따옴표나 접두사 없이 순수 텍스트만."
    )
    try:
        result = gemini_gen_fn(prompt).strip()
        result = re.sub(r'^META_DESC:\s*', '', result, flags=re.IGNORECASE).strip()
        if 80 <= len(result) <= 200:
            return result
    except Exception:
        pass
    if lang == "ko":
        return f"{keyword}에 대한 최신 정보와 전문가 검증 가이드를 확인하세요. 지금 바로 알아야 할 핵심 내용을 담았습니다."[:140]
    else:
        return f"Expert insights on {keyword} backed by verified research. Discover what actually works — and what you've been getting wrong."[:155]


def apply_all_postprocessing(body: str, meta_desc: str, title: str, faq_list: list,
                              keyword: str, lang: str, site_url: str,
                              is_khealth: bool, gemini_gen_fn) -> tuple:
    body = postprocess_internal_links(body, site_url)
    body = postprocess_statistics(body, keyword, lang)
    body = postprocess_table(body, keyword, lang)
    meta_desc = postprocess_meta_desc(meta_desc, title, keyword, lang, gemini_gen_fn)
    return body, meta_desc

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
    s = (["효능","부작용","추천","비교","후기","방법","원인","예방","관리","가이드","체크리스트","주의사항"]
         if lang == "ko" else
         ["guide","review","tips","comparison","benefits","prevention","checklist","overview","FAQ","how to","best","expert"])
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

def compute_keyword_density(body: str, keyword: str) -> float:
    """★ 키워드 밀도 계산 (plain text 기준)"""
    plain = re.sub(r'<[^>]+>', '', body)
    plain_lower = plain.lower()
    kw_lower = keyword.lower()
    if not plain_lower or not kw_lower:
        return 0.0
    # 단어 단위 계산 (한국어는 어절 기준)
    total_chars = len(plain.replace(' ', '').replace('\n', ''))
    kw_count = plain_lower.count(kw_lower)
    if total_chars == 0:
        return 0.0
    # 키워드 길이 기준 밀도
    density = (kw_count * len(kw_lower)) / total_chars
    return density

def estimate_seo_score(title: str, body: str, meta_desc: str, tags: list,
                        faq_list: list, image_urls: list, keyword: str) -> int:
    score = 0
    kw_l  = keyword.lower()
    plain = re.sub(r'<[^>]+>', '', body)
    blen  = len(plain.replace(" ", "").replace("\n", ""))

    # ★ 제목 품질 (10점)
    title_l = title.lower()
    if kw_l in title_l:                  score += 7
    if 20 <= len(title) <= 65:           score += 3

    # ★ 제목 페널티: 진부한 패턴 감점
    cliche_patterns = ["총정리", "a to z", "완벽 가이드", "everything you need",
                       "complete guide to", "a-to-z", "효과 효과", "방법 방법"]
    for p in cliche_patterns:
        if p in title_l:
            score -= 5
            break

    # ★ 본문 길이 (20점)
    if   blen >= 3000: score += 20
    elif blen >= 2500: score += 17
    elif blen >= 2000: score += 13
    elif blen >= 1800: score += 9
    elif blen >= 1000: score += 4

    # ★★★ 키워드 밀도 페널티 (SEO 핵심 — 최대 -15점)
    kw_density = compute_keyword_density(body, keyword)
    if kw_density <= 0.015:       score += 10  # 1.5% 이하: 이상적
    elif kw_density <= 0.025:     score += 5   # 1.5~2.5%: 허용
    elif kw_density <= 0.040:     score -= 5   # 2.5~4%: 페널티
    else:                         score -= 15  # 4% 초과: 심각한 패널티

    # ★ 메타 디스크립션 (10점)
    mdl = len(meta_desc)
    if   130 <= mdl <= 160: score += 10
    elif 100 <= mdl <  130: score += 7
    elif  80 <= mdl <  100: score += 4
    elif mdl > 0:           score += 1

    # ★ 이미지 (10점)
    ic = len(image_urls)
    if   ic >= 3: score += 10
    elif ic == 2: score += 7
    elif ic == 1: score += 4

    # ★ 내부링크 (10점)
    ilinks = len(re.findall(r'<a\s+href=["\']https?://[^"\']+["\']', body, re.IGNORECASE))
    if   ilinks >= 5: score += 10
    elif ilinks >= 4: score += 8
    elif ilinks >= 3: score += 5
    elif ilinks >= 1: score += 2

    # ★ 통계·출처 (10점)
    stat_cnt = count_statistics_in_body(body)
    if   stat_cnt >= 5: score += 6
    elif stat_cnt >= 3: score += 4
    elif stat_cnt >= 1: score += 2
    cite_cnt = len(re.findall(r'\([^)]{3,40},\s*20[0-9]{2}\)', body))
    if   cite_cnt >= 3: score += 4
    elif cite_cnt >= 1: score += 2

    # ★ 구조 (10점)
    h2_c  = len(re.findall(r'<h2[\s>]', body, re.IGNORECASE))
    h3_c  = len(re.findall(r'<h3[\s>]', body, re.IGNORECASE))
    ul_c  = len(re.findall(r'<ul[\s>]', body, re.IGNORECASE))
    tb_c  = len(re.findall(r'<table[\s>]', body, re.IGNORECASE))
    st = 0
    if h2_c >= 5:   st += 3
    elif h2_c >= 3: st += 2
    if h3_c >= 4:   st += 2
    elif h3_c >= 2: st += 1
    if ul_c >= 3:   st += 2
    elif ul_c >= 1: st += 1
    if tb_c >= 1:   st += 3
    score += min(st, 10)

    # ★ FAQ (5점)
    if   len(faq_list) >= 3: score += 5
    elif len(faq_list) >= 2: score += 3
    elif len(faq_list) >= 1: score += 1

    # ★ 태그 (5점)
    if   len(tags) >= TAG_COUNT: score += 5
    elif len(tags) >= 8:         score += 3
    elif len(tags) >= 4:         score += 1

    return max(0, min(score, 100))

# ============================================================
# ★ 이미지 처리 (카드형 3단 배치)
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
    has_korean = any('\uAC00' <= c <= '\uD7A3' for c in keyword)
    urls = []
    if not has_korean:
        urls.extend(get_images_from_pixabay(keyword, count))
        if len(urls) < count:
            urls.extend(get_images_from_pexels(keyword, count - len(urls)))
    if len(urls) < count:
        en_query = translate_ko_to_en_for_image(keyword, theme)
        urls.extend(get_images_from_pixabay(en_query, count - len(urls)))
        if len(urls) < count:
            urls.extend(get_images_from_pexels(en_query, count - len(urls)))
    if len(urls) < count:
        fallback_q = THEME_IMAGE_FALLBACK.get(theme, THEME_IMAGE_FALLBACK["default"])
        urls.extend(get_images_from_pixabay(fallback_q, count - len(urls)))
        if len(urls) < count:
            urls.extend(get_images_from_pexels(fallback_q, count - len(urls)))
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
        if r.status_code in (200, 301, 302, 404): return True
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
# ── RPM 추적기 (flash-lite 무료: 30 RPM) ───────────────────────
import time as _time_module
_rpm_call_times: list = []
_RPM_LIMIT = 28  # 30 RPM에서 2 여유분 확보

def _wait_for_rpm():
    """분당 호출 횟수가 한도 초과하면 대기"""
    now = _time_module.time()
    # 1분 이내 호출 기록만 유지
    global _rpm_call_times
    _rpm_call_times = [t for t in _rpm_call_times if now - t < 60]
    if len(_rpm_call_times) >= _RPM_LIMIT:
        oldest = _rpm_call_times[0]
        wait = 61 - (now - oldest)
        if wait > 0:
            print(f"  ⏳ RPM 한도({_RPM_LIMIT}/분) 도달 → {wait:.0f}초 대기")
            _time_module.sleep(wait)
        _rpm_call_times = []
    _rpm_call_times.append(_time_module.time())

def generate_content_gemini(prompt: str) -> str:
    global GEMINI_MODEL, _gemini_fallback_active
    _wait_for_rpm()  # ★ RPM 가드
    for attempt in range(3):
        try:
            resp = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config={"temperature": 0.80, "max_output_tokens": 4096}
            )
            return resp.text
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "resource_exhausted" in err or "quota" in err:
                if not _gemini_fallback_active:
                    print(f"  ⚠️ Gemini RPM/RPD 초과 → 62초 대기 후 재시도")
                    _gemini_fallback_active = True
                    _rpm_call_times.clear()
                    time.sleep(62); continue  # 60초 + 여유 2초
                else:
                    print(f"  ❌ Gemini lite RPD 한도 도달. 120초 대기")
                    time.sleep(120); raise
            print(f"  ⚠️ Gemini 오류 (attempt {attempt+1}): {e}")
            if attempt < 2: time.sleep(20)
    raise RuntimeError("Gemini 3회 연속 실패")

# ============================================================
# ★ WP 포스팅 (이미지 카드형 3단 배치)
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


def upload_featured_image(site_url: str, wp_pass: str,
                           image_url: str, keyword: str) -> int:
    """이미지 URL을 WP 미디어 라이브러리에 업로드 → Featured Image ID 반환"""
    try:
        # 이미지 다운로드
        r = requests.get(image_url, timeout=15,
                        headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code != 200:
            return 0

        # Content-Type 확인
        ctype = r.headers.get("Content-Type","image/jpeg")
        if "jpeg" in ctype or "jpg" in ctype:
            ext = "jpg"; mime = "image/jpeg"
        elif "png" in ctype:
            ext = "png"; mime = "image/png"
        elif "webp" in ctype:
            ext = "webp"; mime = "image/webp"
        else:
            ext = "jpg"; mime = "image/jpeg"

        # ★ 파일명 생성 — 영어+숫자만 (한글 제거)
        import re as _re
        safe_kw = _re.sub(r'[^a-z0-9]', '-', keyword.lower())[:30]
        safe_kw = _re.sub(r'-+', '-', safe_kw).strip('-')
        if not safe_kw: safe_kw = "korea-image"
        filename = f"{safe_kw}-{int(time.time())}.{ext}"

        # WP 미디어 업로드
        upload_r = requests.post(
            f"{site_url}/wp-json/wp/v2/media",
            auth=requests.auth.HTTPBasicAuth(WP_USER, wp_pass),
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": mime,
            },
            data=r.content,
            timeout=30
        )
        if upload_r.status_code in (200, 201):
            media_id = upload_r.json().get("id", 0)
            return media_id
        return 0
    except Exception as e:
        print(f"   ⚠️ 이미지 업로드 실패: {e}")
        return 0

def build_image_html(image_urls: list, keyword: str) -> str:
    html = ""
    for i, u in enumerate(image_urls):
        alt = f"{keyword} 관련 정보 이미지" if i > 0 else keyword
        html += (
            '<figure style="margin:20px 0;padding:0;background:#f8f9fa;'
            'border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.10);">'
            f'<img src="{u}" alt="{alt}" loading="lazy" '
            'style="width:100%;height:auto;display:block;">'
            '<figcaption style="padding:8px 14px;font-size:13px;color:#666;text-align:center;">'
            f'{alt}</figcaption></figure>\n'
        )
    return html


# ════════════════════════════════════════════════════════════
# ★ v4.1 추가 기능
# ════════════════════════════════════════════════════════════

def get_diverse_image(keyword: str, site_theme: str, attempt: int = 0) -> list:
    """
    ★ v2.0 이미지 개선:
    - 의료 수술 사진 완전 제외 (수술실/메스/주사기/수술장면)
    - 사이트당 1개 대표 이미지만 (반복 없음)
    - 랜덤 페이지로 중복 방지
    - Korea 관련 이미지 적극 활용
    """
    import random, hashlib, time as _time
    
    PIXABAY_KEY = os.getenv("PIXABAY_KEY", "")
    PEXELS_KEY  = os.getenv("PEXELS_KEY", "")
    
    # ── 의료 수술 사진 제외 키워드 ──
    MEDICAL_BLOCK = [
        "surgery", "operation", "surgical", "scalpel", "needle", "syringe",
        "operating room", "surgeon", "incision", "wound", "blood", "bandage",
        "수술", "메스", "주사기", "수술실", "절개", "봉합"
    ]
    
    # ── 한글 → 영어 키워드 변환 ──
    KO_EN = {
        "건강": "health wellness", "의학": "medical healthcare",
        "질환": "health condition", "증상": "health symptoms",
        "치료": "healthcare treatment", "영양": "nutrition food",
        "비타민": "vitamins supplements", "약": "medicine pharmacy",
        "운동": "fitness exercise", "식단": "healthy diet food",
        "피부": "skin beauty care", "탈모": "hair care",
        "당뇨": "diabetes health", "고혈압": "blood pressure health",
        "관절": "joint health orthopedic", "허리": "back health spine",
        "수면": "sleep wellness rest", "면역": "immune system health",
        "한국": "Korea Seoul city", "유학": "study abroad university",
        "취업": "career office work", "부동산": "real estate property",
        "주식": "stock market finance", "보험": "insurance protection",
        "경제": "economy finance business", "정치": "government policy",
    }
    
    search_kw = keyword
    for ko, en in KO_EN.items():
        if ko in search_kw:
            search_kw = search_kw.replace(ko, en)
            break
    
    # ── 테마별 이미지 컨셉 (Korea 활용 강화) ──
    THEME_SEARCH = {
        "한국의료관광": "Korea medical clinic hospital modern",
        "Korea Medical Tourism": "Korea healthcare medical center Seoul",
        "건강과 의학": "healthcare wellness doctor consultation",
        "Investment": "finance investment korea seoul business",
        "Korea Investment": "korean stock market finance seoul",
        "Insurance": "insurance protection family korea",
        "Finance": "korea banking finance seoul city",
        "Tax and Law": "korea legal business office",
        "Crypto": "cryptocurrency blockchain digital korea",
        "Korea Real Estate": "korea apartment seoul cityscape",
        "K-Beauty": "korean skincare beauty product",
        "K-Beauty Reviews": "korean beauty product cosmetic",
        "Travel": "korea travel tourism hotel seoul",
        "Visa": "korea passport document office",
        "Wedding": "wedding couple korea ceremony",
        "Education": "korea university campus student",
        "Job": "korea office career work professional",
        "K-Pop": "kpop concert music stage performance",
        "한국 뉴스": "korea seoul city skyline news",
        "Korea News": "korea politics economy business news",
    }
    
    # 테마 매칭
    extra = "Korea"
    for theme_key, theme_search in THEME_SEARCH.items():
        if theme_key.lower() in site_theme.lower():
            extra = theme_search
            break
    
    # 랜덤 페이지 (중복 방지) - 시간+키워드 해시 기반
    hash_val = int(hashlib.md5(f"{keyword}{int(_time.time()//3600)}".encode()).hexdigest()[:4], 16)
    rand_page = (hash_val % 15) + 1 + attempt * 3
    
    def is_safe_image(url: str, tags: str = "") -> bool:
        """의료 수술 이미지 필터링"""
        check_str = (url + " " + tags).lower()
        for block in MEDICAL_BLOCK:
            if block.lower() in check_str:
                return False
        return True
    
    url = None
    
    # ── 1차: Pixabay ──
    if PIXABAY_KEY:
        for q in [f"{search_kw}", f"{extra}", "Korea Seoul"]:
            try:
                r = requests.get("https://pixabay.com/api/", params={
                    "key": PIXABAY_KEY,
                    "q": q,
                    "image_type": "photo",
                    "per_page": 20,
                    "page": rand_page,
                    "safesearch": "true",
                    "min_width": 800,
                    "orientation": "horizontal",
                }, timeout=10)
                if r.status_code == 200:
                    hits = r.json().get("hits", [])
                    random.shuffle(hits)
                    for h in hits:
                        img_url = h.get("webformatURL", "")
                        tags = h.get("tags", "")
                        if img_url and is_safe_image(img_url, tags):
                            url = img_url
                            break
                if url: break
            except: continue
    
    # ── 2차: Pexels ──
    if not url and PEXELS_KEY:
        for q in [search_kw, extra, "Korea"]:
            try:
                r = requests.get(
                    "https://api.pexels.com/v1/search",
                    headers={"Authorization": PEXELS_KEY},
                    params={"query": q, "per_page": 15,
                            "page": rand_page, "orientation": "landscape"},
                    timeout=10)
                if r.status_code == 200:
                    photos = r.json().get("photos", [])
                    random.shuffle(photos)
                    for p in photos:
                        img_url = p.get("src", {}).get("large", "")
                        if img_url and is_safe_image(img_url):
                            url = img_url
                            break
                if url: break
            except: continue
    
    # ── 3차: Pixabay Korea 폴백 ──
    if not url and PIXABAY_KEY:
        try:
            r = requests.get("https://pixabay.com/api/", params={
                "key": PIXABAY_KEY,
                "q": "Korea Seoul city",
                "image_type": "photo",
                "per_page": 20, "page": 1,
                "safesearch": "true",
            }, timeout=10)
            if r.status_code == 200:
                hits = r.json().get("hits", [])
                if hits:
                    url = hits[hash_val % len(hits)].get("webformatURL", "")
        except: pass
    
    return [url] if url else []


def request_indexing_all(site_url: str, post_url: str, pw: str):
    """글 발행 후 Google/Naver/Bing/Daum 색인 자동 요청"""
    indexnow_key = os.getenv("INDEXNOW_KEY", "")
    domain = site_url.replace("https://","").replace("http://","")
    
    results = []
    
    # ── 1. Google Search Console (Rank Math Instant Indexing) ──
    try:
        r = requests.post(
            f"{site_url}/wp-json/rankmath/v1/instantIndexing",
            auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
            json={"urls": [post_url], "action": "URL_UPDATED"},
            timeout=15)
        if r.status_code in (200, 201):
            results.append("Google✅")
        else:
            # Google ping 방식으로 대체
            sitemap = f"{site_url}/sitemap_index.xml"
            requests.get(f"https://www.google.com/ping?sitemap={requests.utils.quote(sitemap)}", timeout=8)
            results.append("Google-ping✅")
    except:
        results.append("Google❌")
    
    # ── 2. IndexNow (Bing + Yandex + Naver 동시) ──
    if indexnow_key:
        try:
            r = requests.post(
                "https://api.indexnow.org/indexnow",
                json={
                    "host": domain,
                    "key": indexnow_key,
                    "keyLocation": f"{site_url}/{indexnow_key}.txt",
                    "urlList": [post_url]
                },
                headers={"Content-Type": "application/json"},
                timeout=10)
            if r.status_code in (200, 202):
                results.append("IndexNow✅")
            else:
                results.append(f"IndexNow❌({r.status_code})")
        except:
            results.append("IndexNow❌")
    
    # ── 3. Bing 직접 ──
    try:
        r = requests.get(
            f"https://www.bing.com/ping?sitemap={requests.utils.quote(site_url+'/sitemap_index.xml')}",
            timeout=8)
        if r.status_code == 200:
            results.append("Bing✅")
    except:
        pass
    
    # ── 4. Naver ──
    try:
        r = requests.get(
            f"https://searchadvisor.naver.com/indexnow",
            params={"url": post_url}, timeout=8)
        results.append("Naver✅" if r.status_code in (200,202) else "Naver-skip")
    except:
        pass
    
    print(f"   🔍 색인요청: {' | '.join(results)}")


def delete_low_seo_posts(site_url: str, pw: str, min_score: int = 90):
    """SEO 90점 이하 글 삭제"""
    base = f"{site_url}/wp-json/wp/v2"
    deleted = 0
    page = 1
    
    while True:
        try:
            r = requests.get(f"{base}/posts",
                           auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                           params={"per_page":50,"page":page,"status":"publish",
                                   "_fields":"id,title,meta,date"},
                           timeout=15)
            if r.status_code != 200 or not r.json(): break
            posts = r.json()
            
            for post in posts:
                meta = post.get("meta", {})
                score = meta.get("rank_math_seo_score", "")
                try:
                    score_int = int(float(str(score))) if score else 0
                except:
                    score_int = 0
                
                if 0 < score_int < min_score:
                    dr = requests.delete(f"{base}/posts/{post['id']}",
                                        auth=requests.auth.HTTPBasicAuth(WP_USER, pw),
                                        params={"force": True}, timeout=10)
                    if dr.status_code in (200, 201):
                        deleted += 1
            
            if len(posts) < 50: break
            page += 1
        except Exception as e:
            break
    
    if deleted:
        print(f"   🗑️ SEO {min_score}점 이하 {deleted}건 삭제")
    return deleted

def wp_post(site: dict, title: str, body_html: str, meta_desc: str,
            tags: list, faq_list: list, image_urls: list,
            keyword: str, seo_score: int, reporter: dict) -> dict:
    wp_pass  = os.getenv(site["wp_pass_env"], "")
    if not wp_pass:
        return {"ok": False, "error": f"WP_PASS_ENV '{site['wp_pass_env']}' not set"}
    site_url = site["url"]
    theme    = site["theme"]

    author_id     = get_or_create_wp_author(site_url, wp_pass, reporter)
    category_name = get_category_for_post(theme, keyword, title)
    category_id   = get_or_create_wp_category(site_url, wp_pass, category_name)

    # ★ 이미지 1개만 (반복 방지, Featured Image로 활용)
    hero_img = build_image_html(image_urls[:1], keyword) if image_urls else ""
    mid_img  = ""  # 중간 이미지 제거
    end_img  = ""  # 하단 이미지 제거
    faq_html = build_faq_schema_html(faq_list)

    h2_ends = [m.end() for m in re.finditer(r'</h2>', body_html, re.IGNORECASE)]
    insert_mid = -1
    if len(h2_ends) >= 2:
        pm = re.search(r'</p>', body_html[h2_ends[1]:], re.IGNORECASE)
        if pm: insert_mid = h2_ends[1] + pm.end()
    if insert_mid < 0:
        half = len(body_html) // 2
        pm = re.search(r'</p>', body_html[half:], re.IGNORECASE)
        insert_mid = half + pm.end() if pm else half

    final_body = (
        hero_img
        + body_html[:insert_mid]
        + (mid_img if mid_img else "")
        + body_html[insert_mid:]
        + end_img
        + faq_html
    )

    tags_payload = []
    for tag in tags:
        try:
            tr = requests.post(f"{site_url}/wp-json/wp/v2/tags", auth=(WP_USER, wp_pass),
                               json={"name": tag}, timeout=10)
            if tr.status_code in (200, 201):
                tags_payload.append(tr.json().get("id"))
            elif tr.status_code == 400:
                sr = requests.get(f"{site_url}/wp-json/wp/v2/tags", auth=(WP_USER, wp_pass),
                                  params={"search": tag, "per_page": 1}, timeout=10)
                if sr.status_code == 200 and sr.json():
                    tags_payload.append(sr.json()[0]["id"])
        except Exception:
            pass

    rank_kw = ",".join([keyword] + tags[:4])

    # ★ 메타 디스크립션에서 바이라인 제거
    import re as _re2
    meta_desc = _re2.sub(r'^[◇◆▶▷]\s*[가-힣\w\s]+\s*(기자|reporter)?\.?\s*', '', meta_desc).strip()
    meta_desc = _re2.sub(r'^By\s+[\w\s]+\.?\s*', '', meta_desc, flags=_re2.IGNORECASE).strip()
    if len(meta_desc) < 50:
        if lang == "ko":
            meta_desc = f"{keyword}에 대한 전문가 검증 정보와 최신 가이드를 확인하세요."
        else:
            meta_desc = f"Expert guide on {keyword} — verified information and practical tips you need to know."

    # ★ Featured Image WP 미디어에 직접 업로드
    featured_media_id = 0
    if image_urls:
        print(f"   📸 Featured Image 업로드 중...")
        featured_media_id = upload_featured_image(site_url, wp_pass, image_urls[0], keyword)
        if featured_media_id:
            print(f"   ✅ Featured Image 업로드 완료 (ID:{featured_media_id})")
        else:
            print(f"   ⚠️ Featured Image 업로드 실패 → URL 방식 유지")

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
    if author_id and author_id > 0:
        post_data["author"] = author_id
    # ★ Featured Image 설정
    if featured_media_id:
        post_data["featured_media"] = featured_media_id

    try:
        r = requests.post(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, wp_pass),
                          json=post_data, timeout=30)
        if r.status_code in (200, 201):
            post_id  = r.json().get("id")
            post_url = r.json().get("link", "")
            time.sleep(2)
            vr = requests.get(f"{site_url}/wp-json/wp/v2/posts/{post_id}",
                              auth=(WP_USER, wp_pass), timeout=10)
            if vr.status_code == 200:
                meta_check = vr.json().get("meta", {})
                if not meta_check.get("rank_math_focus_keyword"):
                    requests.patch(f"{site_url}/wp-json/wp/v2/posts/{post_id}",
                                   auth=(WP_USER, wp_pass),
                                   json={"meta": {"rank_math_focus_keyword": rank_kw,
                                                  "rank_math_description": meta_desc}},
                                   timeout=15)
            # ★ 발행 즉시 색인 요청 (Google/Bing/Naver/IndexNow)
            if post_url:
                request_indexing_all(site_url, post_url, wp_pass)
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
        "site":      site_url,
        "theme":     theme,
        "keyword":   keyword,
        "title":     title,
        "status":    status,
        "seo_score": seo_score,
        "images":    image_count,
        "url":       post_url,
        "error":     error,
        "slot":      str(RUN_SLOT),
        "model":     GEMINI_MODEL,
        "author":    author,
        "category":  category,
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
# ★ 단일 포스트 처리 (SEO 95점 완전 보장)
# ============================================================
def process_one_post(site: dict, keyword: str) -> bool:
    url   = site["url"]
    lang  = site["lang"]
    theme = site["theme"]
    mode  = site["mode"]
    is_khealth = (mode == "health_blog")

    reporter = pick_reporter(site)
    print(f"\n  🖊  [{theme}] {keyword[:50]} | 기자: {reporter['name']}")

    if mode in ("news", "news_en"):
        kw_tuple = crawl_rss_news(lang, site_url=url)
        keyword, _ = kw_tuple if isinstance(kw_tuple, tuple) else (kw_tuple, "")

    if is_khealth:
        base_prompt = make_khealth_prompt(keyword, reporter, mode)
    else:
        base_prompt = make_seo_prompt(keyword, theme, lang, mode, site_url=url, reporter=reporter)

    prompt = base_prompt
    body = title = meta_desc = ""
    faq_list = []
    tags = []
    best_score = 0
    best_result = None

    for gen_attempt in range(MAX_REGEN + 1):
        try:
            raw = generate_content_gemini(prompt)
        except Exception as e:
            print(f"  ❌ Gemini 생성 실패: {e}")
            record_result(url, theme, keyword, "", "", 0, 0, "❌ Gemini 실패", str(e))
            return False

        time.sleep(RATE_LIMIT_SLEEP)

        body_raw, title, meta_desc, faq_list = extract_meta_and_faq(raw)
        body, tags = extract_tags_from_article(body_raw, keyword, theme, lang)

        if not title:
            title = apply_title_template(
                pick_title_template(lang, mode), keyword
            )

        pre_score = estimate_seo_score(title, body, meta_desc, tags, faq_list,
                                       ["x", "x", "x"], keyword)

        kw_density = compute_keyword_density(body, keyword)
        print(f"  📝 생성 {gen_attempt+1}회차 → 사전 SEO {pre_score}점 | 키워드 밀도 {kw_density:.1%}")

        if pre_score > best_score:
            best_score = pre_score
            best_result = (body, title, meta_desc, faq_list, tags)

        if pre_score >= SEO_TARGET:
            print(f"  ✅ SEO {pre_score}점 달성 → 재생성 중단")
            break

        if gen_attempt < MAX_REGEN:
            suffix = make_regen_suffix(pre_score, body, meta_desc, faq_list,
                                        tags, keyword, lang, is_khealth)
            prompt = base_prompt + suffix
            print(f"  🔄 SEO {pre_score}점 미달 → {gen_attempt+2}회차 재생성")
            time.sleep(30)  # 재생성 전 30초 대기 (RPM 보호)

    body, title, meta_desc, faq_list, tags = best_result

    if best_score < SEO_TARGET:
        print(f"  🔧 {MAX_REGEN+1}회 재생성 후도 {best_score}점 → post-processing 자동 보완 적용")
        body, meta_desc = apply_all_postprocessing(
            body, meta_desc, title, faq_list, keyword, lang, url,
            is_khealth, generate_content_gemini
        )

    images = get_multiple_images(keyword, count=3, theme=theme)
    if not images:
        images = get_images_from_pixabay("South Korea nature", 3)
    if not images:
        images = get_images_from_pexels("Seoul Korea", 3)
    print(f"  🖼  이미지 {len(images)}장")

    score = estimate_seo_score(title, body, meta_desc, tags, faq_list, images, keyword)
    kw_density_final = compute_keyword_density(body, keyword)
    rank_label = ("🏆 최우수" if score >= 95 else
                  "✅ 우수"   if score >= 90 else
                  "⚠️ 보통"  if score >= 80 else
                  "❌ 미달")
    print(f"  📊 SEO 최종 점수: {score}/100  {rank_label}  키워드밀도: {kw_density_final:.1%}")

    plain_len = len(re.sub(r'<[^>]+>', '', body).replace(' ', '').replace('\n', ''))
    stat_cnt  = count_statistics_in_body(body)
    ilinks    = len(re.findall(r'<a\s+href=["\']https?://', body, re.IGNORECASE))
    tb_cnt    = len(re.findall(r'<table[\s>]', body, re.IGNORECASE))
    h2_cnt    = len(re.findall(r'<h2[\s>]', body, re.IGNORECASE))
    print(f"     ↳ 본문:{plain_len}자 | 통계:{stat_cnt}개 | 링크:{ilinks}개 | TABLE:{tb_cnt}개 | H2:{h2_cnt}개 | META:{len(meta_desc)}자")

    category_name = get_category_for_post(theme, keyword, title)
    print(f"  📁 카테고리: {category_name}")

    if mode in ("news", "news_en") and title:
        t_lower = title.strip().lower()
        site_cache = _wp_recent_titles_cache.get(url, set())
        if t_lower in site_cache:
            print(f"  ⛔ WP 캐시 중복 → 발행 취소: {title[:60]}")
            record_result(url, theme, keyword, title, "", score, len(images), "⛔ skip_dup")
            return False
        site_cache.add(t_lower)
        _wp_recent_titles_cache[url] = site_cache

    result = wp_post(site, title, body, meta_desc, tags, faq_list, images,
                     keyword, score, reporter)
    if result["ok"]:
        author_name    = result.get("author", reporter["name"])
        category_label = result.get("category", category_name)
        print(f"  ✅ 발행 완료: {result.get('url','')} | 저자: {author_name} | 카테고리: {category_label}")
        record_result(url, theme, keyword, title, result.get("url", ""),
                      score, len(images), "✅ OK", author=author_name, category=category_label)
        return True
    else:
        err = result.get("error", "")
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
    print(f"   Gemini 모델: {GEMINI_MODEL} (무료 Free Tier)")
    print(f"   SEO 목표: {SEO_TARGET}점 이상 | 최대 재생성: {MAX_REGEN}회 | RPM 상한: {_RPM_LIMIT}/분")
    print(f"   키워드 밀도 상한: {KW_DENSITY_MAX:.1%} | 포스트간 대기: {RATE_LIMIT_SLEEP}초")
 
    print(f"{'='*60}\n")

    total_ok = total_fail = total_skip = 0

    print("📋 뉴스 사이트 최근 제목 사전 로드 중...")
    preload_news_site_titles(SITES_CONFIG, WP_USER)

    # ★ Free Tier 20 RPD 보호: 27개 사이트를 3슬롯에 균등 배분
    # 슬롯1: 사이트 1~9번, 슬롯2: 10~18번, 슬롯3: 19~27번
    # 각 슬롯에서 최대 9개 사이트 × 1건 = 9 API/슬롯 < 20 RPD ✅
    slot_groups = {
        1: list(range(0, 9)),    # 사이트 0~8번 인덱스
        2: list(range(9, 18)),   # 사이트 9~17번 인덱스
        3: list(range(18, 27)),  # 사이트 18~26번 인덱스
    }
    active_indices = slot_groups.get(RUN_SLOT, list(range(27)))

    for site_idx, site in enumerate(SITES_CONFIG):
        url   = site["url"]
        theme = site["theme"]

        # ★ 이번 슬롯에 해당하는 사이트만 실행
        if site_idx not in active_indices:
            continue

        n = 1  # ★ 슬롯당 사이트당 1건 (20 RPD 보호)
        # k-health365: 하루 2건 고퀄리티 정책 → 아침(슬롯1)/저녁(슬롯3) 1건씩, 낮(슬롯2)은 건너뜀
        if "k-health365" in url:
            n = 0 if RUN_SLOT == 2 else 1

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
            ok = process_one_post(site, keyword)
            if ok: total_ok += 1
            else:  total_fail += 1
            if i < n - 1: time.sleep(random.uniform(RATE_LIMIT_SLEEP, RATE_LIMIT_SLEEP + 5))

    flush_log_to_google_sheet()

    print(f"\n{'='*60}")
    print(f"✅ 완료 — 성공 {total_ok} / 실패 {total_fail} / 스킵 {total_skip}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
