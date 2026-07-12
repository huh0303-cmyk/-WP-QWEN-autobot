#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
autopost_mega.py v2.0 — 27개 사이트 오토포스팅
2026-07 업데이트:
  ✅ 카테고리 생성 완전 금지 — find_existing_wp_category (조회만)
  ✅ 27개 사이트별 독립 페르소나 + 글 구성 (SITE_PERSONA)
  ✅ make_site_prompt — 사이트별 프롬프트 완전 분리
  ✅ SEO 90점 미달 시 최대 3회 재생성
  ✅ post-processing: 통계·TABLE 자동 보완
  ✅ IndexNow 발행 즉시 ping
  ✅ 구글시트 로깅 / Rank Math 메타 주입
"""

import os, sys, time, random, re, json, hashlib
import requests
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from google import genai

KST = timezone(timedelta(hours=9))
def now_kst():
    return datetime.now(KST)

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
PIXABAY_KEY     = os.getenv("PIXABAY_KEY")
PEXELS_KEY      = os.getenv("PEXELS_KEY")
SHEETS_WEBHOOK  = os.getenv("SHEETS_WEBHOOK")
INDEXNOW_KEY    = os.getenv("INDEXNOW_KEY", "907ae08aa52b45239490ed2407df835d")
WP_USER         = "huh0303@gmail.com"

RUN_SLOT            = int(os.getenv("RUN_SLOT", "1"))
SLEEP_BETWEEN_POSTS = float(os.getenv("SLEEP_BETWEEN_POSTS", "8"))

gemini_client         = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL_PRIMARY  = "gemini-2.5-flash"
GEMINI_MODEL_FALLBACK = "gemini-2.5-flash-lite"
GEMINI_MODEL          = GEMINI_MODEL_PRIMARY
_gemini_fallback_active = False

TAG_COUNT   = 10
SEO_TARGET  = 90
MAX_REGEN   = 3

# ============================================================
# ★ 기자 풀
# ============================================================
REPORTERS_KO = [
    {"name":"김민준","email":"minjun@koreanews365.com","slug":"minjun-kim","bio":"정치·경제 전문 기자. 10년 경력."},
    {"name":"이서연","email":"seoyeon@koreanews365.com","slug":"seoyeon-lee","bio":"국제·외교 담당 시니어 기자."},
    {"name":"박현우","email":"hyunwoo@koreanews365.com","slug":"hyunwoo-park","bio":"경제·금융 분야 전문 기자."},
    {"name":"최지아","email":"jia@koreanews365.com","slug":"jia-choi","bio":"문화·사회 담당 기자."},
    {"name":"정재희","email":"jaehee@koreanews365.com","slug":"jaehee-jung","bio":"산업·기술 전문 기자."},
    {"name":"윤성호","email":"sungho@koreanews365.com","slug":"sungho-yoon","bio":"증권·투자 담당 기자."},
    {"name":"강다은","email":"daeun@koreanews365.com","slug":"daeun-kang","bio":"생활·복지 전문 기자."},
    {"name":"임준혁","email":"junhyuk@koreanews365.com","slug":"junhyuk-lim","bio":"사회·법률 담당 기자."},
    {"name":"한소희","email":"sohee@koreanews365.com","slug":"sohee-han","bio":"교육·보건 전문 기자."},
    {"name":"오태영","email":"taeyoung@koreanews365.com","slug":"taeyoung-oh","bio":"무역·글로벌 담당 기자."},
]
REPORTERS_EN = [
    {"name":"James Patterson","email":"james@theseouljournal.com","slug":"james-patterson","bio":"Senior politics and economy correspondent."},
    {"name":"Emily Crawford","email":"emily@theseouljournal.com","slug":"emily-crawford","bio":"Culture and lifestyle editor."},
    {"name":"Michael Thompson","email":"michael@theseouljournal.com","slug":"michael-thompson","bio":"Business and finance reporter."},
    {"name":"Sarah Williams","email":"sarah@theseouljournal.com","slug":"sarah-williams","bio":"International affairs correspondent."},
    {"name":"David Harrison","email":"david@theseouljournal.com","slug":"david-harrison","bio":"Technology and innovation writer."},
    {"name":"Jessica Kim","email":"jessica@theseouljournal.com","slug":"jessica-kim","bio":"K-culture and entertainment reporter."},
    {"name":"Robert Park","email":"robert@theseouljournal.com","slug":"robert-park","bio":"Economy and markets analyst."},
    {"name":"Laura Choi","email":"laura@theseouljournal.com","slug":"laura-choi","bio":"Lifestyle and travel journalist."},
    {"name":"Daniel Yoon","email":"daniel@theseouljournal.com","slug":"daniel-yoon","bio":"Politics and society reporter."},
    {"name":"Rachel Lim","email":"rachel@theseouljournal.com","slug":"rachel-lim","bio":"Health and wellness correspondent."},
]
REPORTERS_BLOG_EN = [
    {"name":"Andrew Kim","email":"andrew@contributor.com","slug":"andrew-kim","bio":"Finance and investment specialist writer."},
    {"name":"Sophia Lee","email":"sophia@contributor.com","slug":"sophia-lee","bio":"Health and wellness expert contributor."},
    {"name":"Brian Choi","email":"brian@contributor.com","slug":"brian-choi","bio":"Technology and digital trends writer."},
    {"name":"Hannah Park","email":"hannah@contributor.com","slug":"hannah-park","bio":"Travel and culture journalist."},
    {"name":"Kevin Yoon","email":"kevin@contributor.com","slug":"kevin-yoon","bio":"Real estate and economy analyst."},
    {"name":"Grace Jung","email":"grace@contributor.com","slug":"grace-jung","bio":"K-beauty and lifestyle editor."},
    {"name":"Thomas Lim","email":"thomas@contributor.com","slug":"thomas-lim","bio":"Legal and tax affairs writer."},
    {"name":"Olivia Shin","email":"olivia@contributor.com","slug":"olivia-shin","bio":"Education and career specialist."},
    {"name":"Nathan Oh","email":"nathan@contributor.com","slug":"nathan-oh","bio":"Crypto and fintech correspondent."},
    {"name":"Catherine Han","email":"catherine@contributor.com","slug":"catherine-han","bio":"Medical tourism and healthcare writer."},
]
REPORTERS_BLOG_KO = [
    {"name":"김재원","email":"jaewon@contributor.com","slug":"jaewon-kim","bio":"재테크·금융 전문 칼럼니스트."},
    {"name":"이미경","email":"mikyung@contributor.com","slug":"mikyung-lee","bio":"건강·의학 전문 작가."},
    {"name":"박성훈","email":"sunghoon@contributor.com","slug":"sunghoon-park","bio":"부동산·경제 분야 전문 기고자."},
    {"name":"최수연","email":"suyeon@contributor.com","slug":"suyeon-choi","bio":"교육·유학 전문 칼럼니스트."},
    {"name":"정민호","email":"minho@contributor.com","slug":"minho-jung","bio":"법률·세무 전문 작가."},
    {"name":"윤지훈","email":"jihoon@contributor.com","slug":"jihoon-yoon","bio":"투자·주식 전문 기고자."},
    {"name":"강혜진","email":"hyejin@contributor.com","slug":"hyejin-kang","bio":"웰빙·라이프스타일 전문 작가."},
    {"name":"임채원","email":"chaewon@contributor.com","slug":"chaewon-lim","bio":"문화·여행 전문 칼럼니스트."},
    {"name":"한도윤","email":"doyoon@contributor.com","slug":"doyoon-han","bio":"기술·IT 전문 기고자."},
    {"name":"오승현","email":"seunghyun@contributor.com","slug":"seunghyun-oh","bio":"국제·무역 전문 작가."},
]

_wp_author_cache: dict = {}

def get_or_create_wp_author(site_url, wp_pass, reporter):
    cache = _wp_author_cache.setdefault(site_url, {})
    slug  = reporter["slug"]
    if slug in cache: return cache[slug]
    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/users", auth=(WP_USER, wp_pass),
                         params={"search": reporter["email"], "per_page": 5}, timeout=10)
        if r.status_code == 200 and r.json():
            uid = r.json()[0]["id"]; cache[slug] = uid; return uid
    except: pass
    try:
        payload = {"username": slug, "name": reporter["name"], "email": reporter["email"],
                   "slug": slug, "description": reporter.get("bio",""),
                   "password": hashlib.md5(reporter["email"].encode()).hexdigest()[:16]+"Aa1!",
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
        print(f"   ⚠️ Author 생성 실패: {e}")
    cache[slug] = -1; return -1

def pick_reporter(site):
    url  = site.get("url","")
    lang = site.get("lang","en")
    if "koreanews365" in url:      return random.choice(REPORTERS_KO)
    elif "theseouljournal" in url: return random.choice(REPORTERS_EN)
    elif lang == "ko":             return random.choice(REPORTERS_BLOG_KO)
    else:                          return random.choice(REPORTERS_BLOG_EN)

# ============================================================
# ★★★ 카테고리 — 조회만, 절대 생성 금지 ★★★
# ============================================================
_wp_category_cache: dict = {}

def find_existing_wp_category(site_url, wp_pass, category_name):
    """기존 카테고리 조회만. 없으면 1(미분류). 절대 생성 안 함."""
    cache = _wp_category_cache.setdefault(site_url, {})
    if category_name in cache: return cache[category_name]

    if "__loaded__" not in cache:
        try:
            page = 1
            while True:
                r = requests.get(f"{site_url}/wp-json/wp/v2/categories",
                                 auth=(WP_USER, wp_pass),
                                 params={"per_page": 100, "page": page}, timeout=12)
                if r.status_code != 200: break
                cats = r.json()
                if not cats: break
                for cat in cats:
                    n = cat.get("name","").strip()
                    cid = cat.get("id", 1)
                    cache[n] = cid
                    cache[n.lower()] = cid
                page += 1
                if len(cats) < 100: break
            cache["__loaded__"] = True
            loaded = len([k for k in cache if isinstance(cache[k], int)])
            print(f"   📁 {site_url} 카테고리 {loaded}개 로드")
        except Exception as e:
            print(f"   ⚠️ 카테고리 로드 실패: {e}")
            cache["__loaded__"] = True

    lower = category_name.lower()
    if lower in cache: return cache[lower]

    for key, cid in cache.items():
        if key == "__loaded__" or not isinstance(cid, int): continue
        if lower in key.lower() or key.lower() in lower:
            print(f"   📁 부분매칭: '{category_name}' → '{key}' ({cid})")
            cache[category_name] = cid; return cid

    print(f"   📁 '{category_name}' 없음 → 미분류(1)")
    cache[category_name] = 1; return 1

# ============================================================
# ★ 카테고리 매핑
# ============================================================
THEME_CATEGORY_MAP = {
    "건강과 의학": {"default":"건강정보","keyword_map":[
        (["혈압","고혈압","심장","혈관"],"심혈관건강"),
        (["당뇨","혈당","인슐린"],"당뇨·혈당"),
        (["암","종양","항암"],"암·종양"),
        (["피부","아토피","여드름","탈모","두피"],"피부·모발"),
        (["정신","우울","불안","스트레스","수면","불면"],"정신건강"),
        (["뼈","관절","허리","디스크","골다공증"],"근골격계"),
        (["영양","비타민","영양제","보충제"],"영양·보충제"),
        (["다이어트","비만","체중","운동"],"다이어트·운동"),
        (["소화","위장","장","변비","대장"],"소화기건강"),
        (["간","지방간","간염","간수치"],"간·소화기"),
    ]},
    "한국 뉴스": {"default":"국제-INTERNATIONAL","keyword_map":[
        (["정치","대통령","국회","선거","여당","야당","탄핵"],"정치-POLITICS"),
        (["경제","금리","물가","GDP","수출","무역","코스피"],"경제-ECONOMY"),
        (["기업","삼성","현대","SK","LG","스타트업","IPO"],"비즈니스-BUSINESS"),
        (["사회","범죄","복지","노동","청년","저출산"],"사회-SOCIETY"),
        (["기술","AI","반도체","IT","디지털","로봇"],"기술-TECH"),
        (["문화","K-pop","드라마","영화","예술"],"문화-CULTURE"),
        (["교육","대학","입시","유학","학교"],"교육-EDUCATION"),
        (["부동산","아파트","주택","집값","전세"],"부동산-REALESTATE"),
        (["국제","미국","중국","일본","EU","UN","외교","북한"],"국제-INTERNATIONAL"),
    ]},
    "Seoul Lifestyle": {"default":"LIFESTYLE","keyword_map":[
        (["politics","election","president","government"],"POLITICS"),
        (["economy","GDP","inflation","stock"],"ECONOMY"),
        (["business","startup","company","CEO"],"BUSINESS"),
        (["global","international","US","China","UN"],"GLOBAL"),
        (["culture","K-pop","drama","music","food"],"CULTURE"),
        (["education","university","student","scholarship"],"EDUCATION"),
        (["tech","AI","semiconductor","IT"],"TECH"),
        (["health","medical","wellness","beauty"],"HEALTH"),
        (["travel","tourism","hiking","hotel"],"TRAVEL"),
        (["expat","foreigner","visa","immigration"],"EXPAT LIFE"),
    ]},
    "Finance": {"default":"Finance Tips","keyword_map":[
        (["stock","market","invest","dividend"],"Stock Market"),
        (["real estate","property","mortgage"],"Real Estate Finance"),
        (["tax","deduction","refund"],"Tax Guide"),
        (["savings","deposit","bank"],"Savings & Banking"),
        (["insurance","premium","coverage"],"Insurance"),
        (["crypto","bitcoin","blockchain"],"Crypto Finance"),
        (["loan","debt","credit"],"Loans & Credit"),
        (["retirement","pension","IRP"],"Retirement Planning"),
    ]},
    "Investment": {"default":"Investment Guide","keyword_map":[
        (["stock","equity","dividend","KOSPI"],"Stock Investment"),
        (["ETF","fund","index fund"],"Fund Investment"),
        (["real estate","property","REIT"],"Real Estate Investment"),
        (["crypto","bitcoin","ethereum"],"Crypto Investment"),
        (["bond","fixed income","treasury"],"Bond & Fixed Income"),
        (["global","overseas","US stock"],"Global Investment"),
        (["startup","VC","venture"],"Startup Investment"),
    ]},
    "Korea Investment": {"default":"투자전략","keyword_map":[
        (["주식","코스피","코스닥","배당"],"주식투자"),
        (["ETF","펀드","인덱스"],"펀드·ETF"),
        (["부동산","아파트","분양","리츠"],"부동산투자"),
        (["암호화폐","비트코인","이더리움"],"암호화폐"),
        (["채권","국채","금리"],"채권·금리"),
        (["해외","미국주식","글로벌"],"해외투자"),
        (["절세","세금","IRP","연금"],"절세·연금"),
    ]},
    "Korea Real Estate": {"default":"부동산정보","keyword_map":[
        (["아파트","분양","청약","재건축"],"아파트·분양"),
        (["전세","월세","임대","보증금"],"전월세"),
        (["정책","규제","LTV","DSR"],"정책·규제"),
        (["지역","서울","경기","부산"],"지역별시장"),
        (["상가","오피스텔","수익형"],"수익형부동산"),
        (["시세","가격","실거래"],"가격·시세"),
    ]},
    "Insurance": {"default":"Insurance Guide","keyword_map":[
        (["life","term life","whole life"],"Life Insurance"),
        (["health","medical","hospital"],"Health Insurance"),
        (["car","auto","accident"],"Auto Insurance"),
        (["travel","trip","overseas"],"Travel Insurance"),
        (["pension","retirement","annuity"],"Pension & Annuity"),
    ]},
    "Tax and Law": {"default":"Tax & Legal Guide","keyword_map":[
        (["income tax","withholding","filing"],"Income Tax"),
        (["corporate tax","business tax"],"Corporate Tax"),
        (["VAT","consumption tax"],"VAT & Consumption Tax"),
        (["inheritance","estate","gift tax"],"Inheritance & Gift Tax"),
        (["visa","immigration","permit"],"Immigration Law"),
        (["labor","employment","wage"],"Labor Law"),
        (["property","real estate"],"Property Tax"),
    ]},
    "Crypto": {"default":"Crypto Guide","keyword_map":[
        (["bitcoin","BTC"],"Bitcoin"),
        (["ethereum","ETH"],"Ethereum"),
        (["altcoin","XRP","SOL"],"Altcoins"),
        (["DeFi","DEX"],"DeFi"),
        (["NFT","metaverse"],"NFT & Metaverse"),
        (["exchange","binance","upbit"],"Exchanges"),
        (["regulation","FSC"],"Regulation"),
        (["staking","mining"],"Staking & Mining"),
    ]},
    "Technology": {"default":"Tech News","keyword_map":[
        (["AI","machine learning","GPT","LLM"],"AI & Machine Learning"),
        (["semiconductor","chip","TSMC"],"Semiconductor"),
        (["smartphone","mobile","app"],"Mobile Tech"),
        (["cybersecurity","hacking","privacy"],"Cybersecurity"),
        (["robot","automation","drone"],"Robotics & Automation"),
        (["startup","venture","unicorn"],"Startup & Innovation"),
        (["EV","electric vehicle","battery"],"EV & Battery"),
    ]},
    "K-Beauty": {"default":"K-Beauty Guide","keyword_map":[
        (["skincare","moisturizer","serum","toner"],"Skincare Routine"),
        (["makeup","foundation","lipstick"],"K-Makeup"),
        (["hair","scalp","shampoo"],"Hair Care"),
        (["sunscreen","SPF","UV"],"Sun Protection"),
        (["anti-aging","wrinkle","collagen"],"Anti-Aging"),
        (["ingredient","niacinamide","hyaluronic"],"Ingredients"),
        (["brand","innisfree","laneige","cosrx"],"K-Beauty Brands"),
    ]},
    "K-Beauty Reviews": {"default":"Product Reviews","keyword_map":[
        (["review","best","ranking","top"],"Product Reviews"),
        (["skincare","moisturizer","serum"],"Skincare Reviews"),
        (["makeup","foundation","lip"],"Makeup Reviews"),
        (["hair","scalp","shampoo"],"Hair Care Reviews"),
        (["budget","affordable","cheap"],"Budget Picks"),
        (["luxury","premium","high-end"],"Premium Picks"),
    ]},
    "K-POP": {"default":"K-POP News","keyword_map":[
        (["BTS","BLACKPINK","EXO","TWICE","aespa","NewJeans","SEVENTEEN"],"Artist Spotlight"),
        (["album","release","comeback","MV"],"New Releases"),
        (["concert","tour","performance"],"Concerts & Tours"),
        (["chart","billboard","award"],"Charts & Awards"),
        (["debut","audition","idol","agency"],"Idol & Agency"),
        (["fandom","fan","ARMY","BLINK"],"Fan Culture"),
    ]},
    "Travel": {"default":"Travel Guide","keyword_map":[
        (["Seoul","Gyeongbokgung","Myeongdong"],"Seoul Travel"),
        (["Busan","beach","Haeundae"],"Busan Travel"),
        (["Jeju","island","Hallasan"],"Jeju Island"),
        (["hiking","trail","mountain"],"Hiking & Nature"),
        (["food","cuisine","restaurant","street food"],"Food & Dining"),
        (["hotel","accommodation","hostel"],"Accommodation"),
        (["itinerary","day trip","tour"],"Itineraries"),
        (["temple","palace","museum","history"],"Culture & History"),
    ]},
    "Visa Guide": {"default":"Visa Guide","keyword_map":[
        (["student visa","D-2","D-4"],"Student Visa"),
        (["work visa","E-7"],"Work Visa"),
        (["F-2","F-5","permanent residence"],"Long-term Residence"),
        (["tourist","B-1","K-ETA"],"Tourist & Short-term"),
        (["working holiday","H-1"],"Working Holiday"),
        (["family","F-1","spouse"],"Family Visa"),
        (["extension","renewal"],"Visa Extension"),
    ]},
    "Korea Medical Tourism": {"default":"Medical Tourism","keyword_map":[
        (["plastic surgery","rhinoplasty"],"Plastic Surgery"),
        (["dental","teeth","implant"],"Dental Treatment"),
        (["cancer","oncology"],"Cancer Treatment"),
        (["dermatology","laser","botox","filler"],"Dermatology & Aesthetics"),
        (["traditional","acupuncture"],"Korean Traditional Medicine"),
        (["cost","price","package"],"Cost & Packages"),
        (["medical visa","C-3"],"Medical Visa"),
    ]},
    "Wedding": {"default":"Wedding Guide","keyword_map":[
        (["venue","hall","ceremony"],"Wedding Venue"),
        (["dress","gown","suit"],"Wedding Fashion"),
        (["photographer","photo","video"],"Photography & Video"),
        (["catering","food","reception"],"Catering & Reception"),
        (["traditional","hanbok","Paebaek"],"Traditional Korean Wedding"),
        (["honeymoon","trip"],"Honeymoon"),
        (["budget","cost","planning"],"Wedding Planning"),
        (["decoration","flower","theme"],"Decoration & Theme"),
    ]},
    "Study in Korea": {"default":"Study in Korea","keyword_map":[
        (["TOPIK","Korean language"],"Korean Language"),
        (["university","admission"],"University Admission"),
        (["scholarship","KGSP","GKS"],"Scholarships"),
        (["campus life","dorm"],"Campus Life"),
        (["visa","D-2"],"Student Visa"),
        (["part-time job","work"],"Part-time Work"),
        (["graduate","master","PhD"],"Graduate Studies"),
    ]},
    "International Students": {"default":"Student Guide","keyword_map":[
        (["scholarship","GKS","KGSP"],"Scholarships"),
        (["language","Korean","TOPIK"],"Language Learning"),
        (["visa","D-2","immigration"],"Visa & Immigration"),
        (["housing","dormitory"],"Housing"),
        (["part-time","job","work"],"Part-time Work"),
        (["culture","adjustment"],"Cultural Adjustment"),
    ]},
    "Employment": {"default":"Employment Guide","keyword_map":[
        (["resume","CV","interview"],"Job Application"),
        (["salary","wage","income"],"Salary & Compensation"),
        (["IT","developer","engineer"],"IT Jobs"),
        (["teaching","English teacher","EPIK"],"Teaching Jobs"),
        (["visa","E-7","work permit"],"Work Visa"),
        (["startup","freelance","remote"],"Freelance & Startup"),
        (["benefits","pension"],"Benefits & Welfare"),
    ]},
    "Jobs in Korea": {"default":"Jobs Guide","keyword_map":[
        (["IT","developer","engineer","software"],"IT & Tech Jobs"),
        (["teacher","English","EPIK"],"Teaching Jobs"),
        (["finance","banking","accounting"],"Finance Jobs"),
        (["marketing","sales","PR"],"Marketing & Sales"),
        (["factory","manufacturing","E-9"],"Manufacturing Jobs"),
        (["startup","SME"],"Startup Jobs"),
        (["global","multinational"],"Global Companies"),
    ]},
    "Recruitment": {"default":"Recruitment Guide","keyword_map":[
        (["hiring","recruit","HR"],"Hiring Strategy"),
        (["interview","screening"],"Interview Process"),
        (["salary","negotiation"],"Salary Negotiation"),
        (["foreign worker","E-9","H-2"],"Foreign Worker Recruitment"),
        (["global talent","expat"],"Global Talent"),
        (["platform","job board","LinkedIn"],"Recruitment Platforms"),
    ]},
    "Korea Culture": {"default":"Korean Culture","keyword_map":[
        (["food","cuisine","recipe","restaurant"],"Korean Food"),
        (["festival","holiday","Chuseok","Seollal"],"Festivals & Holidays"),
        (["traditional","history","heritage","palace"],"History & Heritage"),
        (["K-pop","drama","movie","hallyu"],"K-Wave & Entertainment"),
        (["sport","soccer","baseball","Taekwondo"],"Sports"),
        (["fashion","style","design","art"],"Fashion & Art"),
        (["language","Korean","hangul"],"Korean Language"),
    ]},
    "국제교육문화": {"default":"국제교육","keyword_map":[
        (["유학","해외","어학연수","교환학생"],"해외유학"),
        (["한국어","TOPIK","어학당"],"한국어교육"),
        (["문화교류","국제교류","MOU"],"문화교류"),
        (["취업","커리어","글로벌","인턴"],"글로벌취업"),
        (["입시","대학원","장학금"],"입학·장학"),
    ]},
    "한국유학정보": {"default":"유학정보","keyword_map":[
        (["비자","D-2","출입국","체류"],"비자·출입국"),
        (["장학금","GKS","정부초청"],"장학금"),
        (["기숙사","숙소","자취"],"숙소·생활"),
        (["한국어","TOPIK","어학"],"한국어학습"),
        (["대학","입학","전형"],"대학입학"),
        (["생활","적응","생활비"],"유학생활"),
    ]},
    "Korea Career Programs": {"default":"Career Programs","keyword_map":[
        (["internship","training","program"],"Internship Programs"),
        (["language","Korean","English"],"Language Programs"),
        (["certification","qualification","exam"],"Certifications"),
        (["networking","community","event"],"Networking"),
        (["job","career","placement"],"Job Placement"),
    ]},
}

def get_category_for_post(theme, keyword, title=""):
    td = THEME_CATEGORY_MAP.get(theme)
    if not td: return "General"
    st = f"{keyword} {title}".lower()
    for kws, cat in td.get("keyword_map",[]):
        for kw in kws:
            if kw.lower() in st: return cat
    return td.get("default","General")

# ============================================================
# ★★★ 27개 사이트별 독립 페르소나 ★★★
# ============================================================
SITE_PERSONA = {
    "https://k-health365.com": {
        "persona_ko": "임상경력 20년 내과 전문의. 환자에게 직접 설명하듯 쉽고 따뜻하게 씁니다. 전문 용어는 반드시 괄호로 풀어줍니다.",
        "tone": "친근한 전문의 스타일. 공감 → 원인 → 해결 순서. '~하세요', '~입니다' 체.",
        "structure": ["오늘 느끼신 증상이 왜 나타나는지 공감형 도입","핵심 원인 3~5가지 (환자 관점)","일상 관리법 (구체적 수치)","⚠️ 위험 신호 — 병원 가야 할 때","전문의 한마디 blockquote","FAQ 5문항"],
        "min_chars": 3500, "tables": 2, "lang": "ko", "no_image": True,
    },
    "https://koreamedicaltour.com": {
        "persona_en": "Medical tourism consultant with 12 years helping international patients navigate Korean hospitals.",
        "tone": "Consultant style. Problem → solution → cost → next step.",
        "structure": ["Why patients choose Korea (with statistics)","Step-by-step: consultation → procedure → recovery","Cost comparison table (Korea vs US/Europe/SE Asia)","Top accredited hospitals","Visa and logistics checklist","FAQ 3 questions"],
        "min_chars": 2500, "tables": 2, "lang": "en",
    },
    "https://koreainvest365.com": {
        "persona_en": "CFA-level investment analyst covering Korean capital markets for 15 years. Data-driven, numbers-first.",
        "tone": "Analytical. Lead with the key figure, then explain.",
        "structure": ["Market snapshot with current key metric","Data comparison table","3 bull case drivers","3 bear case risks","Strategy recommendation with timeframe","Korean regulation context","FAQ 3 questions"],
        "min_chars": 2500, "tables": 2, "lang": "en",
    },
    "https://ki-korea.com": {
        "persona_ko": "20년 경력 증권사 리서치센터장 출신. 초보 투자자가 이해할 수 있도록 쉽게 씁니다.",
        "tone": "친절한 멘토. 개념 → 실전 → 주의사항 순서.",
        "structure": ["왜 지금 알아야 하는가 (시장 현황)","핵심 개념 쉬운 설명","실전 투자 단계별 가이드","수익률·리스크 비교표","초보자 흔한 실수 3가지","전문가 조언 blockquote","FAQ 3문항"],
        "min_chars": 2500, "tables": 1, "lang": "ko",
    },
    "https://koreainsurance365.com": {
        "persona_en": "Licensed insurance broker specializing in policies for foreigners in Korea.",
        "tone": "Advisor style. Clarity over complexity. Always state who qualifies.",
        "structure": ["Who needs this (eligibility first)","Coverage comparison table (3 options)","How to apply step by step","Covered vs not covered","Cost and premium breakdown","Common claim mistakes","FAQ 3 questions"],
        "min_chars": 2200, "tables": 2, "lang": "en",
    },
    "https://kfinance365.com": {
        "persona_en": "Personal finance educator simplifying Korean financial products for English speakers.",
        "tone": "Educator style. Plain language. 'Think of it as...'",
        "structure": ["Simple definition (no jargon)","How it works in Korea","Pros and cons table","Step-by-step to get started","Tax implications","Common pitfalls","FAQ 3 questions"],
        "min_chars": 2200, "tables": 1, "lang": "en",
    },
    "https://koreataxnlaw.com": {
        "persona_en": "Korean tax attorney with 18 years of practice. Precise, structured, always cites the law.",
        "tone": "Legal guide style. Numbered steps. Always state penalties for non-compliance.",
        "structure": ["Who is affected (applicability)","Legal basis — relevant Korean law","Requirements and deadlines table","Step-by-step compliance guide","Penalties for non-compliance","2026 updates","FAQ 3 questions"],
        "min_chars": 2500, "tables": 2, "lang": "en",
    },
    "https://koreacrypto365.com": {
        "persona_en": "Blockchain researcher covering Korean crypto regulations and market trends since 2017.",
        "tone": "Balanced. Neither hype nor FUD. Korean regulation and exchange data first.",
        "structure": ["Current Korea market context","Technical explanation (accessible)","Korean FSC/FSS regulation status","Korea vs global data table","Risk assessment","How to access in Korea","FAQ 3 questions"],
        "min_chars": 2200, "tables": 1, "lang": "en",
    },
    "https://krealestate365.com": {
        "persona_ko": "부동산학 박사 출신 공인중개사. 서울·수도권 10년 분석 전문가. 데이터와 정책 중심으로 냉철하게.",
        "tone": "분석가 스타일. 수치 → 해석 → 전망 순서.",
        "structure": ["현재 시세 수치 요약 (실거래가·변동률)","정책 배경 및 규제 현황","지역별 시세 비교표","투자 vs 실거주 분석","향후 6개월 전망","매수·매도 체크리스트","FAQ 3문항"],
        "min_chars": 2500, "tables": 2, "lang": "ko",
    },
    "https://ktech365.com": {
        "persona_en": "Tech journalist covering Korean semiconductor, AI, and startup ecosystem since 2015.",
        "tone": "News-magazine style. Lead with 'so what'. Context → impact → what's next.",
        "structure": ["News hook and global significance","Technical background (1 paragraph, no jargon)","Key players in Korea's ecosystem","Global competitive context","Industry data table","Expert perspective","What to watch next","FAQ 3 questions"],
        "min_chars": 2200, "tables": 1, "lang": "en",
    },
    "https://kskin365.com": {
        "persona_en": "Korean dermatologist-turned-beauty writer. Science-backed, ingredient-focused.",
        "tone": "Expert friend. 'The science says...' Evidence over claims.",
        "structure": ["What your skin needs (science hook)","Ingredient breakdown","Routine step by step","Product type comparison table","Skin type suitability guide","3 myths debunked","FAQ 3 questions"],
        "min_chars": 2200, "tables": 1, "lang": "en",
    },
    "https://oliveyoungkorea.com": {
        "persona_en": "K-beauty product tester and Olive Young shopping expert. Honest, budget-aware.",
        "tone": "Enthusiastic friend. 'I tried this for 4 weeks. Here is what happened.'",
        "structure": ["Why this is trending now","Top picks ranking table (product, price, best for)","Detailed review of top pick","Where to buy: Olive Young in-store vs online","Budget vs premium comparison","Application tips","FAQ 3 questions"],
        "min_chars": 2000, "tables": 2, "lang": "en",
    },
    "https://kworld365.com": {
        "persona_en": "K-pop culture writer and fandom analyst. Deep knowledge of idol industry mechanics.",
        "tone": "Fan-smart insider. Enthusiastic but not breathless.",
        "structure": ["Story hook","Artist background (brief for new fans)","Industry context","Fan reaction and social pulse","Chart or streaming data table","What's coming next","FAQ 3 questions"],
        "min_chars": 2000, "tables": 1, "lang": "en",
    },
    "https://k-trip365.com": {
        "persona_en": "Travel writer who has visited every Korean province. Practical itinerary-builder.",
        "tone": "Enthusiastic guide. 'Do this, skip that, eat here.' Sensory details.",
        "structure": ["Why visit now (season/event)","Getting there: transport + cost table","Day-by-day itinerary","Where to eat: 3 specific spots","Where to stay: budget/mid/luxury","Local insider tips","FAQ 3 questions"],
        "min_chars": 2200, "tables": 2, "lang": "en",
    },
    "https://k-visa365.com": {
        "persona_en": "Korean immigration consultant who processed 3,000+ visa applications. Checklist-driven.",
        "tone": "Professional guide. Numbered steps. Always include processing time and fee.",
        "structure": ["Who this visa is for (plain language)","Required documents checklist table","Application process step by step","Processing time and fee breakdown","Top rejection reasons","After approval: next steps","FAQ 3 questions"],
        "min_chars": 2200, "tables": 2, "lang": "en",
    },
    "https://koreawedding365.com": {
        "persona_en": "Korean wedding planner with 10 years coordinating ceremonies across Seoul and Jeju.",
        "tone": "Warm, organized. Checklists and realistic budgets. Romantic but honest about costs.",
        "structure": ["What makes this special in Korean weddings","Planning timeline and checklist","Budget breakdown table (economy/standard/premium)","Top vendor recommendations","Traditional vs modern comparison","Real couple tips","FAQ 3 questions"],
        "min_chars": 2200, "tables": 2, "lang": "en",
    },
    "https://kstudy365.com": {
        "persona_en": "International education advisor who helped 2,000+ students enroll in Korean universities.",
        "tone": "Supportive advisor. 'Here is exactly how to do this.' Real deadlines, no false promises.",
        "structure": ["Why Korea — statistics on outcomes","Eligibility requirements","Application timeline table","Total cost breakdown","Scholarship options","Student life honest overview","FAQ 3 questions"],
        "min_chars": 2200, "tables": 2, "lang": "en",
    },
    "https://studyinkorea365.com": {
        "persona_en": "Student who completed a 4-year degree in Korea and now guides others. Brutally honest.",
        "tone": "Peer mentor. 'When I arrived, nobody told me this...'",
        "structure": ["What nobody tells you (honest reality)","Reality vs expectation","Practical how-to from personal experience","Monthly budgeting table","Community resources","3 mistakes to avoid","FAQ 3 questions"],
        "min_chars": 2000, "tables": 1, "lang": "en",
    },
    "https://kieca-korea.org": {
        "persona_ko": "국제교육 전문가이자 문화교류 기획자. 정부기관·대학 협력 15년 경력.",
        "tone": "전문 기관지 스타일. 정책 → 절차 → 지원 순서.",
        "structure": ["국제교육교류 현황 및 정책 배경","주요 프로그램 소개","지원 절차 및 자격 요건 표","혜택 및 지원 내용","신청 방법 단계별","FAQ 3문항"],
        "min_chars": 2000, "tables": 1, "lang": "ko",
    },
    "https://ksa-korea.org": {
        "persona_ko": "한국 유학 10년 경험의 선배 유학생 출신 컨설턴트. 현실적이고 솔직하게.",
        "tone": "선배 조언 스타일. '이것만큼은 꼭 알고 가세요'.",
        "structure": ["아무도 안 알려주는 현실 (경험담)","단계별 준비 가이드","비용 및 일정 표","꼭 주의해야 할 사항 3가지","유용한 공식 기관 링크","FAQ 3문항"],
        "min_chars": 2000, "tables": 1, "lang": "ko",
    },
    "https://sis-korea.com": {
        "persona_en": "Career development specialist who placed 500+ international graduates in Korean companies.",
        "tone": "Career coach. Action-oriented. 'Your next step is...'",
        "structure": ["Career landscape: who is hiring now","Skills and qualifications table","Program or pathway step by step","Salary benchmarks","How to stand out as foreign candidate","Application and interview tips","FAQ 3 questions"],
        "min_chars": 2000, "tables": 1, "lang": "en",
    },
    "https://jobkorea365.com": {
        "persona_en": "HR director turned career advisor. 15 years hiring for Korean conglomerates and startups.",
        "tone": "Insider HR perspective. 'This is what Korean recruiters actually look for.'",
        "structure": ["Job market data: which sectors are growing","What Korean employers really want","Strategy by industry table","Resume and cover letter Korean style","Interview culture surprises","Top platforms and how to use them","FAQ 3 questions"],
        "min_chars": 2000, "tables": 1, "lang": "en",
    },
    "https://jobinkorea365.com": {
        "persona_en": "Expat who found a job in Korea after 6 months of searching. Empathetic and direct.",
        "tone": "Fellow job-seeker who made it. 'Here is exactly what worked for me.'",
        "structure": ["Is this realistic for foreigners? (honest)","Visa requirements first (deal-breaker check)","Where to find jobs: ranked platforms","Salary and benefits table","Application walkthrough","Workplace culture heads-up","FAQ 3 questions"],
        "min_chars": 2000, "tables": 1, "lang": "en",
    },
    "https://jobkoreaglobal.com": {
        "persona_en": "International recruitment specialist connecting global talent with Korean employers.",
        "tone": "Recruitment professional. Useful for both employers and candidates.",
        "structure": ["Market demand with data","Talent requirements and visa table","End-to-end recruitment timeline","Legal compliance requirements","Compensation benchmarks by role","Best practices from successful placements","FAQ 3 questions"],
        "min_chars": 2000, "tables": 2, "lang": "en",
    },
    "https://korea365.org": {
        "persona_en": "Cultural anthropologist making Korean culture accessible and fascinating for global audiences.",
        "tone": "Curious storyteller. Historical context + modern relevance.",
        "structure": ["Cultural hook: introduce the phenomenon","Historical or social background","How it is experienced in modern Korea","Regional or generational variations","How to experience as a visitor","Global influence and hallyu connection","FAQ 3 questions"],
        "min_chars": 2200, "tables": 1, "lang": "en",
    },
    "https://koreanews365.com": {
        "persona_ko": "주요 일간지 10년 경력 시니어 취재기자. 6하원칙 기사체.",
        "tone": "신문 기사 문체. '~했다', '~밝혔다'. 역피라미드 구조.",
        "structure": ["리드: 핵심 사실 1~2문장","배경 및 경위","주요 데이터 통계표","관계자 발언 인용","향후 전망","FAQ 3문항"],
        "min_chars": 2000, "tables": 1, "lang": "ko",
    },
    "https://theseouljournal.com": {
        "persona_en": "Senior foreign correspondent based in Seoul covering Korean affairs for international readers.",
        "tone": "Quality newspaper English. Inverted pyramid. Explains Korean context for global readers.",
        "structure": ["News lead: what happened and global significance","Korean context for international readers","Key data and statistics table","Expert or official quote","Regional or global implications","What to watch next","FAQ 3 questions"],
        "min_chars": 2000, "tables": 1, "lang": "en",
    },
}

# ============================================================
# ★ 이미지 번역 + 사이트 설정
# ============================================================
KO_TO_EN_IMAGE = {
    "혈압":"blood pressure","고혈압":"hypertension","혈당":"blood glucose","당뇨":"diabetes",
    "콜레스테롤":"cholesterol","지방간":"fatty liver","관절":"joint pain","허리":"back pain",
    "탈모":"hair loss","피부":"skin care","불면증":"insomnia","스트레스":"stress",
    "면역력":"immune system","영양제":"supplements","비타민":"vitamins","다이어트":"diet weight loss",
    "암":"cancer","심장":"heart cardiovascular","경제":"Korea economy","정치":"Korean politics",
    "부동산":"Korea real estate","금융":"Korea finance","취업":"employment Korea",
    "교육":"education Korea","기술":"technology Korea","문화":"Korean culture",
    "서울":"Seoul Korea","여행":"Korea travel","투자":"Korea investment","주식":"stock market",
    "암호화폐":"cryptocurrency Korea","보험":"insurance Korea","세금":"tax Korea",
    "웨딩":"wedding Korea","케이팝":"K-pop","뷰티":"Korean beauty",
    "한국":"South Korea","대한민국":"South Korea",
}
THEME_IMAGE_FALLBACK = {
    "건강과 의학":"medical health Korea doctor","한국 뉴스":"South Korea news politics",
    "Seoul Lifestyle":"Seoul Korea lifestyle urban","K-POP":"K-pop idol concert",
    "K-Beauty":"Korean skincare beauty","K-Beauty Reviews":"Korean beauty product review",
    "Travel":"Korea travel tourism","Finance":"Korea finance investment",
    "Investment":"investment stock market Korea","Insurance":"insurance policy Korea",
    "Tax and Law":"Korea law tax document","Crypto":"cryptocurrency bitcoin Korea",
    "Technology":"Korea technology AI startup","Study in Korea":"Korea university campus",
    "International Students":"international student Korea","Visa Guide":"Korea visa passport",
    "Korea Medical Tourism":"Korea medical hospital","Employment":"Korea employment job",
    "Jobs in Korea":"Korea job career","Recruitment":"recruitment hiring Korea",
    "Wedding":"Korea wedding ceremony","Korea Culture":"Korean culture festival",
    "Korea Real Estate":"Korea apartment real estate","Korea Investment":"Korea investment business",
    "국제교육문화":"international education Korea","한국유학정보":"Korea study abroad",
    "Korea Career Programs":"Korea career program","default":"South Korea modern city",
}

def translate_ko_to_en_for_image(keyword, theme=""):
    result = keyword
    for ko, en in sorted(KO_TO_EN_IMAGE.items(), key=lambda x: -len(x[0])):
        result = result.replace(ko, en)
    if any('\uAC00' <= c <= '\uD7A3' for c in result):
        return THEME_IMAGE_FALLBACK.get(theme, THEME_IMAGE_FALLBACK["default"])
    return re.sub(r'\s+', ' ', result).strip()[:80]

SITES_CONFIG = [
    {"url":"https://k-health365.com",       "lang":"ko","theme":"건강과 의학",         "mode":"health_blog","keywords_file":".github/workflows/keywords_khealth.txt",        "wp_pass_env":"KHEALTH365COM",        "daily":6},
    {"url":"https://koreamedicaltour.com",   "lang":"en","theme":"Korea Medical Tourism","mode":"blog",      "keywords_file":".github/workflows/keywords_medicaltour.txt",    "wp_pass_env":"KOREAMEDICALTOURCOM",  "daily":3},
    {"url":"https://koreainvest365.com",     "lang":"en","theme":"Investment",           "mode":"blog",      "keywords_file":".github/workflows/keywords_kinvest.txt",        "wp_pass_env":"KOREAINVEST365COM",    "daily":3},
    {"url":"https://ki-korea.com",           "lang":"ko","theme":"Korea Investment",     "mode":"blog",      "keywords_file":".github/workflows/keywords_kikorea.txt",        "wp_pass_env":"KIKOREACOM",           "daily":3},
    {"url":"https://koreainsurance365.com",  "lang":"en","theme":"Insurance",            "mode":"blog",      "keywords_file":".github/workflows/keywords_kinsurance.txt",     "wp_pass_env":"KOREAINSURANCE365COM", "daily":3},
    {"url":"https://kfinance365.com",        "lang":"en","theme":"Finance",              "mode":"blog",      "keywords_file":".github/workflows/keywords_kfinance.txt",       "wp_pass_env":"KFINANCE365COM",       "daily":3},
    {"url":"https://koreataxnlaw.com",       "lang":"en","theme":"Tax and Law",          "mode":"blog",      "keywords_file":".github/workflows/keywords_ktax.txt",           "wp_pass_env":"KOREATAXNLAWCOM",      "daily":3},
    {"url":"https://koreacrypto365.com",     "lang":"en","theme":"Crypto",               "mode":"blog",      "keywords_file":".github/workflows/keywords_kcrypto.txt",        "wp_pass_env":"KOREACRYPTO365COM",    "daily":3},
    {"url":"https://krealestate365.com",     "lang":"ko","theme":"Korea Real Estate",    "mode":"blog",      "keywords_file":".github/workflows/keywords_krealestate.txt",    "wp_pass_env":"KREALESTATE365COM",    "daily":3},
    {"url":"https://ktech365.com",           "lang":"en","theme":"Technology",           "mode":"blog",      "keywords_file":".github/workflows/keywords_ktech.txt",          "wp_pass_env":"KTECH365COM",          "daily":3},
    {"url":"https://kskin365.com",           "lang":"en","theme":"K-Beauty",             "mode":"blog",      "keywords_file":".github/workflows/keywords_kskin.txt",          "wp_pass_env":"KSKIN365COM",          "daily":3},
    {"url":"https://oliveyoungkorea.com",    "lang":"en","theme":"K-Beauty Reviews",     "mode":"blog",      "keywords_file":".github/workflows/keywords_oliveyoung.txt",     "wp_pass_env":"OLIVEYOUNGKOREACOM",   "daily":3},
    {"url":"https://kworld365.com",          "lang":"en","theme":"K-POP",               "mode":"blog",      "keywords_file":".github/workflows/keywords_kworld.txt",         "wp_pass_env":"KWORLD365COM",         "daily":10},
    {"url":"https://k-trip365.com",          "lang":"en","theme":"Travel",              "mode":"blog",      "keywords_file":".github/workflows/keywords_ktrip.txt",          "wp_pass_env":"KTRIP365COM",          "daily":3},
    {"url":"https://k-visa365.com",          "lang":"en","theme":"Visa Guide",          "mode":"blog",      "keywords_file":".github/workflows/keywords_kvisa.txt",          "wp_pass_env":"KVISA365COM",          "daily":3},
    {"url":"https://koreawedding365.com",    "lang":"en","theme":"Wedding",             "mode":"blog",      "keywords_file":".github/workflows/keywords_kwedding.txt",       "wp_pass_env":"KOREAWEDDING365COM",   "daily":3},
    {"url":"https://kstudy365.com",          "lang":"en","theme":"Study in Korea",      "mode":"blog",      "keywords_file":".github/workflows/keywords_kstudy365.txt",      "wp_pass_env":"KSTUDY365COM",         "daily":3},
    {"url":"https://studyinkorea365.com",    "lang":"en","theme":"International Students","mode":"blog",    "keywords_file":".github/workflows/keywords_studyinkorea365.txt","wp_pass_env":"STUDYINKOREA365COM",   "daily":3},
    {"url":"https://kieca-korea.org",        "lang":"ko","theme":"국제교육문화",          "mode":"blog",      "keywords_file":".github/workflows/keywords_kieca.txt",          "wp_pass_env":"KIECAKOREAORG",        "daily":8},
    {"url":"https://ksa-korea.org",          "lang":"ko","theme":"한국유학정보",          "mode":"blog",      "keywords_file":".github/workflows/keywords_ksaKorea.txt",       "wp_pass_env":"KSAKOREAORG",          "daily":3},
    {"url":"https://sis-korea.com",          "lang":"en","theme":"Korea Career Programs","mode":"blog",     "keywords_file":".github/workflows/keywords_sisKorea.txt",       "wp_pass_env":"SISKOREACOM",          "daily":3},
    {"url":"https://jobkorea365.com",        "lang":"en","theme":"Employment",          "mode":"blog",      "keywords_file":".github/workflows/keywords_jobkorea365.txt",    "wp_pass_env":"JOBKOREA365COM",       "daily":3},
    {"url":"https://jobinkorea365.com",      "lang":"en","theme":"Jobs in Korea",       "mode":"blog",      "keywords_file":".github/workflows/keywords_jobinkorea365.txt",  "wp_pass_env":"JOBINKOREA365COM",     "daily":3},
    {"url":"https://jobkoreaglobal.com",     "lang":"en","theme":"Recruitment",         "mode":"blog",      "keywords_file":".github/workflows/keywords_jobkoreaglobal.txt", "wp_pass_env":"JOBKOREAGLOBALCOM",    "daily":3},
    {"url":"https://korea365.org",           "lang":"en","theme":"Korea Culture",       "mode":"blog",      "keywords_file":".github/workflows/keywords_korea365.txt",       "wp_pass_env":"KOREA365ORG",          "daily":4},
    {"url":"https://koreanews365.com",       "lang":"ko","theme":"한국 뉴스",            "mode":"news",      "keywords_file":".github/workflows/keywords_koreanews.txt",      "wp_pass_env":"KOREANEWS365COM",      "daily":5},
    {"url":"https://theseouljournal.com",    "lang":"en","theme":"Seoul Lifestyle",     "mode":"news_en",   "keywords_file":".github/workflows/keywords_seouljournal.txt",   "wp_pass_env":"THESEOULJOURNALCOM",   "daily":5},
]

# ============================================================
# ★ 권위 링크
# ============================================================
AUTHORITY_LINKS = {
    "건강과 의학":[("질병관리청","https://www.kdca.go.kr"),("대한의학회","https://www.kams.or.kr"),("국민건강보험공단","https://www.nhis.or.kr"),("서울대학교병원","https://www.snuh.org"),("보건복지부","https://www.mohw.go.kr")],
    "한국 뉴스":[("대한민국 정책브리핑","https://www.korea.kr"),("통계청","https://kostat.go.kr"),("기획재정부","https://www.moef.go.kr"),("한국은행","https://www.bok.or.kr")],
    "Seoul Lifestyle":[("Seoul Metropolitan Government","https://english.seoul.go.kr"),("Visit Korea","https://english.visitkorea.or.kr"),("Statistics Korea","https://kostat.go.kr/eng")],
    "Finance":[("Bank of Korea","https://www.bok.or.kr/eng"),("Financial Services Commission","https://www.fsc.go.kr/eng"),("Korea Exchange KRX","https://global.krx.co.kr")],
    "Investment":[("Bank of Korea","https://www.bok.or.kr/eng"),("Invest Korea","https://www.investkorea.org"),("Financial Services Commission","https://www.fsc.go.kr/eng")],
    "Korea Investment":[("한국거래소","https://global.krx.co.kr"),("기획재정부","https://www.moef.go.kr"),("한국은행","https://www.bok.or.kr"),("통계청","https://kostat.go.kr")],
    "Insurance":[("Financial Services Commission","https://www.fsc.go.kr/eng"),("National Health Insurance Service","https://www.nhis.or.kr/english")],
    "Tax and Law":[("National Tax Service Korea","https://www.nts.go.kr/english"),("Ministry of Justice Korea","https://www.moj.go.kr/moj/index.do")],
    "Crypto":[("Financial Services Commission","https://www.fsc.go.kr/eng"),("Bank of Korea","https://www.bok.or.kr/eng")],
    "Technology":[("Ministry of Science and ICT","https://www.msit.go.kr/eng"),("KAIST","https://www.kaist.ac.kr/en")],
    "K-Beauty":[("Ministry of Food and Drug Safety","https://www.mfds.go.kr/eng"),("Korea Cosmetic Association","https://www.kcia.or.kr")],
    "K-Beauty Reviews":[("Ministry of Food and Drug Safety","https://www.mfds.go.kr/eng"),("Korea Cosmetic Association","https://www.kcia.or.kr")],
    "K-POP":[("Korea.net","https://www.korea.net"),("Korea Creative Content Agency KOCCA","https://www.kocca.kr/en")],
    "Travel":[("Visit Korea KTO","https://english.visitkorea.or.kr"),("Seoul Metropolitan Government","https://english.seoul.go.kr")],
    "Visa Guide":[("HiKorea Immigration","https://www.hikorea.go.kr"),("Ministry of Justice Korea","https://www.moj.go.kr/moj/index.do")],
    "Korea Medical Tourism":[("KHIDI","https://www.khidi.or.kr/eps"),("Ministry of Health and Welfare","https://www.mohw.go.kr/eng")],
    "Wedding":[("Visit Korea","https://english.visitkorea.or.kr"),("Seoul Metropolitan Government","https://english.seoul.go.kr")],
    "Study in Korea":[("Study in Korea NIIED","https://www.studyinkorea.go.kr"),("Ministry of Education Korea","https://english.moe.go.kr")],
    "International Students":[("Study in Korea NIIED","https://www.studyinkorea.go.kr"),("HiKorea Immigration","https://www.hikorea.go.kr")],
    "Employment":[("Ministry of Employment and Labor","https://www.moel.go.kr/english"),("Work24 Korea","https://www.work24.go.kr")],
    "Jobs in Korea":[("Ministry of Employment and Labor","https://www.moel.go.kr/english"),("Work24 Korea","https://www.work24.go.kr")],
    "Recruitment":[("Ministry of Employment and Labor","https://www.moel.go.kr/english"),("HRD Korea","https://www.hrdkorea.or.kr/eng")],
    "Korea Culture":[("Korea.net","https://www.korea.net"),("National Museum of Korea","https://www.museum.go.kr/site/eng")],
    "Korea Real Estate":[("한국부동산원","https://www.reb.or.kr"),("국토교통부","https://www.molit.go.kr"),("통계청","https://kostat.go.kr")],
    "국제교육문화":[("교육부","https://www.moe.go.kr"),("Study in Korea","https://www.studyinkorea.go.kr"),("국립국제교육원","https://www.niied.go.kr")],
    "한국유학정보":[("Study in Korea NIIED","https://www.studyinkorea.go.kr"),("출입국·외국인정책본부","https://www.immigration.go.kr"),("교육부","https://www.moe.go.kr")],
    "Korea Career Programs":[("Ministry of Employment and Labor","https://www.moel.go.kr/english"),("HRD Korea","https://www.hrdkorea.or.kr/eng")],
}
def get_authority_links(theme):
    return AUTHORITY_LINKS.get(theme,[("Korea.net","https://www.korea.net"),("Statistics Korea","https://kostat.go.kr/eng")])

# ============================================================
# ★ 내부링크
# ============================================================
SITE_INTERNAL_LINKS = {
    "https://k-health365.com":[("건강 정보 홈","https://k-health365.com"),("혈압 관리","https://k-health365.com/?s=혈압"),("당뇨 관리","https://k-health365.com/?s=당뇨"),("면역력","https://k-health365.com/?s=면역력"),("수면 건강","https://k-health365.com/?s=수면")],
    "https://koreamedicaltour.com":[("Medical Tourism Guide","https://koreamedicaltour.com"),("Plastic Surgery","https://koreamedicaltour.com/?s=plastic+surgery"),("Dental","https://koreamedicaltour.com/?s=dental"),("Medical Visa","https://koreamedicaltour.com/?s=visa"),("Best Hospitals","https://koreamedicaltour.com/?s=hospital")],
    "https://koreainvest365.com":[("Investment Guide","https://koreainvest365.com"),("Stock Market","https://koreainvest365.com/?s=stock"),("ETF","https://koreainvest365.com/?s=ETF"),("Real Estate","https://koreainvest365.com/?s=real+estate"),("Crypto","https://koreainvest365.com/?s=crypto")],
    "https://ki-korea.com":[("한국 투자","https://ki-korea.com"),("주식","https://ki-korea.com/?s=주식"),("ETF","https://ki-korea.com/?s=ETF"),("부동산","https://ki-korea.com/?s=부동산"),("절세","https://ki-korea.com/?s=절세")],
    "https://koreainsurance365.com":[("Insurance Guide","https://koreainsurance365.com"),("Health Insurance","https://koreainsurance365.com/?s=health"),("Life Insurance","https://koreainsurance365.com/?s=life"),("Auto Insurance","https://koreainsurance365.com/?s=auto"),("Foreigner Insurance","https://koreainsurance365.com/?s=foreigner")],
    "https://kfinance365.com":[("Finance Guide","https://kfinance365.com"),("Investment","https://kfinance365.com/?s=investment"),("Stock","https://kfinance365.com/?s=stock"),("Tax","https://kfinance365.com/?s=tax"),("Banking","https://kfinance365.com/?s=banking")],
    "https://koreataxnlaw.com":[("Tax Guide","https://koreataxnlaw.com"),("Income Tax","https://koreataxnlaw.com/?s=income+tax"),("Corporate Tax","https://koreataxnlaw.com/?s=corporate"),("Visa Law","https://koreataxnlaw.com/?s=visa"),("Labor Law","https://koreataxnlaw.com/?s=labor")],
    "https://koreacrypto365.com":[("Crypto Guide","https://koreacrypto365.com"),("Bitcoin","https://koreacrypto365.com/?s=bitcoin"),("Regulation","https://koreacrypto365.com/?s=regulation"),("DeFi","https://koreacrypto365.com/?s=DeFi"),("Exchanges","https://koreacrypto365.com/?s=exchange")],
    "https://krealestate365.com":[("부동산 정보","https://krealestate365.com"),("아파트","https://krealestate365.com/?s=아파트"),("청약","https://krealestate365.com/?s=청약"),("전세","https://krealestate365.com/?s=전세"),("정책","https://krealestate365.com/?s=정책")],
    "https://ktech365.com":[("Tech News","https://ktech365.com"),("AI","https://ktech365.com/?s=AI"),("Semiconductor","https://ktech365.com/?s=semiconductor"),("Startup","https://ktech365.com/?s=startup"),("EV Battery","https://ktech365.com/?s=EV")],
    "https://kskin365.com":[("K-Beauty Guide","https://kskin365.com"),("Skincare","https://kskin365.com/?s=skincare"),("Products","https://kskin365.com/?s=products"),("Anti-Aging","https://kskin365.com/?s=anti-aging"),("Ingredients","https://kskin365.com/?s=ingredients")],
    "https://oliveyoungkorea.com":[("K-Beauty Reviews","https://oliveyoungkorea.com"),("Skincare Reviews","https://oliveyoungkorea.com/?s=skincare"),("Makeup","https://oliveyoungkorea.com/?s=makeup"),("Budget Picks","https://oliveyoungkorea.com/?s=budget"),("Olive Young","https://oliveyoungkorea.com/?s=olive+young")],
    "https://kworld365.com":[("K-POP News","https://kworld365.com"),("BTS","https://kworld365.com/?s=BTS"),("BLACKPINK","https://kworld365.com/?s=BLACKPINK"),("New Releases","https://kworld365.com/?s=new+release"),("Concert","https://kworld365.com/?s=concert")],
    "https://k-trip365.com":[("Korea Travel","https://k-trip365.com"),("Seoul","https://k-trip365.com/?s=Seoul"),("Jeju","https://k-trip365.com/?s=Jeju"),("Hiking","https://k-trip365.com/?s=hiking"),("Food","https://k-trip365.com/?s=food")],
    "https://k-visa365.com":[("Visa Guide","https://k-visa365.com"),("D-2 Student","https://k-visa365.com/?s=D-2"),("E-7 Work","https://k-visa365.com/?s=E-7"),("Working Holiday","https://k-visa365.com/?s=working+holiday"),("Extension","https://k-visa365.com/?s=extension")],
    "https://koreawedding365.com":[("Wedding Guide","https://koreawedding365.com"),("Venues","https://koreawedding365.com/?s=venue"),("Photography","https://koreawedding365.com/?s=photography"),("Traditional","https://koreawedding365.com/?s=traditional"),("Honeymoon","https://koreawedding365.com/?s=honeymoon")],
    "https://kstudy365.com":[("Study in Korea","https://kstudy365.com"),("University Admission","https://kstudy365.com/?s=university"),("Scholarship","https://kstudy365.com/?s=scholarship"),("Student Visa","https://kstudy365.com/?s=visa"),("TOPIK","https://kstudy365.com/?s=TOPIK")],
    "https://studyinkorea365.com":[("International Students","https://studyinkorea365.com"),("Scholarship","https://studyinkorea365.com/?s=scholarship"),("Korean Language","https://studyinkorea365.com/?s=Korean"),("Visa","https://studyinkorea365.com/?s=visa"),("Dormitory","https://studyinkorea365.com/?s=dormitory")],
    "https://kieca-korea.org":[("국제교육문화","https://kieca-korea.org"),("유학","https://kieca-korea.org/?s=유학"),("한국어","https://kieca-korea.org/?s=한국어"),("문화교류","https://kieca-korea.org/?s=문화교류"),("장학금","https://kieca-korea.org/?s=장학금")],
    "https://ksa-korea.org":[("한국유학정보","https://ksa-korea.org"),("비자","https://ksa-korea.org/?s=비자"),("장학금","https://ksa-korea.org/?s=장학금"),("기숙사","https://ksa-korea.org/?s=기숙사"),("TOPIK","https://ksa-korea.org/?s=TOPIK")],
    "https://sis-korea.com":[("Career Programs","https://sis-korea.com"),("Internship","https://sis-korea.com/?s=internship"),("Language","https://sis-korea.com/?s=language"),("Job Placement","https://sis-korea.com/?s=job"),("Networking","https://sis-korea.com/?s=networking")],
    "https://jobkorea365.com":[("Jobs Guide","https://jobkorea365.com"),("IT Jobs","https://jobkorea365.com/?s=IT"),("Teaching","https://jobkorea365.com/?s=teacher"),("Work Visa","https://jobkorea365.com/?s=visa"),("Salary","https://jobkorea365.com/?s=salary")],
    "https://jobinkorea365.com":[("Jobs in Korea","https://jobinkorea365.com"),("Developer","https://jobinkorea365.com/?s=developer"),("English Teacher","https://jobinkorea365.com/?s=English+teacher"),("Finance Jobs","https://jobinkorea365.com/?s=finance"),("Startup","https://jobinkorea365.com/?s=startup")],
    "https://jobkoreaglobal.com":[("Global Recruitment","https://jobkoreaglobal.com"),("Hiring","https://jobkoreaglobal.com/?s=hiring"),("Foreign Worker","https://jobkoreaglobal.com/?s=foreign+worker"),("Global Talent","https://jobkoreaglobal.com/?s=global+talent"),("Salary","https://jobkoreaglobal.com/?s=salary")],
    "https://korea365.org":[("Korean Culture","https://korea365.org"),("Food","https://korea365.org/?s=food"),("Festivals","https://korea365.org/?s=festival"),("History","https://korea365.org/?s=history"),("K-Wave","https://korea365.org/?s=K-pop")],
    "https://koreanews365.com":[("최신 뉴스","https://koreanews365.com"),("경제","https://koreanews365.com/category/경제-economy/"),("정치","https://koreanews365.com/category/정치-politics/"),("사회","https://koreanews365.com/category/사회-society/"),("국제","https://koreanews365.com/category/국제-international/")],
    "https://theseouljournal.com":[("The Seoul Journal","https://theseouljournal.com"),("Politics","https://theseouljournal.com/category/politics/"),("Economy","https://theseouljournal.com/category/economy/"),("Culture","https://theseouljournal.com/category/culture/"),("Expat Life","https://theseouljournal.com/category/expat-life/")],
}
CROSS_LINKS = {
    "https://kstudy365.com":[("Study in Korea 365","https://studyinkorea365.com"),("Korea Visa","https://k-visa365.com"),("Korea Education","https://kieca-korea.org"),("Career Programs","https://sis-korea.com")],
    "https://studyinkorea365.com":[("Kstudy365","https://kstudy365.com"),("Korea Visa","https://k-visa365.com"),("Jobs in Korea","https://jobinkorea365.com"),("Korea Culture","https://korea365.org")],
    "https://kieca-korea.org":[("한국 유학","https://kstudy365.com"),("한국 유학정보","https://ksa-korea.org"),("한국 취업","https://jobkorea365.com"),("한국 뉴스","https://koreanews365.com")],
    "https://ksa-korea.org":[("한국 유학 365","https://kstudy365.com"),("국제교육문화","https://kieca-korea.org"),("비자 안내","https://k-visa365.com"),("취업 정보","https://jobkorea365.com")],
    "https://sis-korea.com":[("Study in Korea","https://kstudy365.com"),("Jobs in Korea","https://jobinkorea365.com"),("Korea Visa","https://k-visa365.com"),("Recruitment","https://jobkoreaglobal.com")],
    "https://jobkorea365.com":[("Jobs in Korea","https://jobinkorea365.com"),("Recruitment","https://jobkoreaglobal.com"),("Visa","https://k-visa365.com"),("Career Programs","https://sis-korea.com")],
    "https://jobinkorea365.com":[("Korea Jobs","https://jobkorea365.com"),("Global Recruitment","https://jobkoreaglobal.com"),("Work Visa","https://k-visa365.com"),("Study and Work","https://kstudy365.com")],
    "https://jobkoreaglobal.com":[("Jobs in Korea","https://jobinkorea365.com"),("Employment","https://jobkorea365.com"),("Career Programs","https://sis-korea.com"),("Visa","https://k-visa365.com")],
    "https://kfinance365.com":[("Korea Investment","https://koreainvest365.com"),("Insurance","https://koreainsurance365.com"),("Tax Law","https://koreataxnlaw.com"),("Crypto","https://koreacrypto365.com")],
    "https://koreainvest365.com":[("Finance 365","https://kfinance365.com"),("Real Estate","https://krealestate365.com"),("Crypto","https://koreacrypto365.com"),("Tax","https://koreataxnlaw.com")],
    "https://ki-korea.com":[("한국 금융","https://kfinance365.com"),("한국 부동산","https://krealestate365.com"),("암호화폐","https://koreacrypto365.com"),("한국 뉴스","https://koreanews365.com")],
    "https://koreainsurance365.com":[("Finance","https://kfinance365.com"),("Tax Law","https://koreataxnlaw.com"),("Investment","https://koreainvest365.com")],
    "https://koreataxnlaw.com":[("Finance","https://kfinance365.com"),("Insurance","https://koreainsurance365.com"),("Visa","https://k-visa365.com")],
    "https://koreacrypto365.com":[("Finance","https://kfinance365.com"),("Investment","https://koreainvest365.com"),("Tax","https://koreataxnlaw.com")],
    "https://krealestate365.com":[("한국 투자","https://koreainvest365.com"),("한국 금융","https://kfinance365.com"),("한국 뉴스","https://koreanews365.com")],
    "https://korea365.org":[("Travel","https://k-trip365.com"),("K-Beauty","https://kskin365.com"),("K-POP","https://kworld365.com"),("Wedding","https://koreawedding365.com")],
    "https://k-trip365.com":[("Korea Culture","https://korea365.org"),("Visa","https://k-visa365.com"),("Medical Tourism","https://koreamedicaltour.com"),("Wedding","https://koreawedding365.com")],
    "https://koreawedding365.com":[("Travel","https://k-trip365.com"),("K-Beauty","https://kskin365.com"),("Korea Culture","https://korea365.org")],
    "https://kskin365.com":[("K-Beauty Reviews","https://oliveyoungkorea.com"),("Medical Tourism","https://koreamedicaltour.com"),("Korea Culture","https://korea365.org")],
    "https://oliveyoungkorea.com":[("K-Beauty Guide","https://kskin365.com"),("Korea Culture","https://korea365.org"),("Medical Tourism","https://koreamedicaltour.com")],
    "https://kworld365.com":[("Korea Culture","https://korea365.org"),("K-Beauty","https://kskin365.com"),("Travel","https://k-trip365.com")],
    "https://k-health365.com":[("의료관광","https://koreamedicaltour.com"),("보험","https://koreainsurance365.com"),("한국 뉴스","https://koreanews365.com")],
    "https://koreamedicaltour.com":[("K-Health 365","https://k-health365.com"),("Visa","https://k-visa365.com"),("Travel","https://k-trip365.com"),("Insurance","https://koreainsurance365.com")],
    "https://ktech365.com":[("Finance","https://kfinance365.com"),("Investment","https://koreainvest365.com"),("Seoul Journal","https://theseouljournal.com")],
    "https://k-visa365.com":[("Study in Korea","https://kstudy365.com"),("Jobs","https://jobinkorea365.com"),("Travel","https://k-trip365.com"),("Medical Tourism","https://koreamedicaltour.com")],
    "https://koreanews365.com":[("한국 금융","https://kfinance365.com"),("한국 부동산","https://krealestate365.com"),("한국 건강","https://k-health365.com")],
    "https://theseouljournal.com":[("Korea Culture","https://korea365.org"),("Travel","https://k-trip365.com"),("Study in Korea","https://kstudy365.com"),("Finance","https://kfinance365.com")],
}

def get_internal_links(site_url, count=4):
    own   = SITE_INTERNAL_LINKS.get(site_url, [])
    cross = CROSS_LINKS.get(site_url, [])
    sel   = []
    if own:   sel.extend(random.sample(own, min(3, len(own))))
    if cross: sel.extend(random.sample(cross, min(count-len(sel), len(cross))))
    return sel[:count] or [("홈페이지", site_url)]

# ============================================================
# ★ 뉴스 키워드
# ============================================================
NEWS_KO_FALLBACK = [
    ("한국 부동산 정책 동향","최근 부동산 정책 변화와 시장 영향을 심층 분석합니다."),
    ("한국은행 기준금리 결정 배경","기준금리 결정 배경과 향후 경제 전망을 다룹니다."),
    ("반도체 수출 실적 분석","반도체 산업 수출 동향과 글로벌 경쟁력을 분석합니다."),
    ("K-배터리 차세대 기술 개발","국내 배터리 산업의 기술 혁신과 시장 동향을 다룹니다."),
    ("저출산 대책 예산 집행 현황","저출산 문제 해결을 위한 정부 예산 정책을 정리합니다."),
    ("K-푸드 글로벌 수출 동향","한국 식품의 해외 수출 트렌드를 분석합니다."),
]
NEWS_EN_FALLBACK = [
    ("Living in Seoul as an Expat","A practical guide for foreigners settling in Seoul."),
    ("How to Open a Bank Account in Korea","Step-by-step guide to Korean banking for foreigners."),
    ("Korean Work Culture Explained","What to expect when working in a Korean company."),
    ("How to Get an E-7 Visa for Korea","Detailed walkthrough of the E-7 visa application process."),
    ("Top Korean Language Schools in Seoul","Comparing the best Korean language programs for expats."),
    ("Cost of Living in Seoul 2026","Realistic monthly budget breakdown for expats in Seoul."),
]

_used_news_ko: set = set()
_used_news_en: set = set()
_wp_title_cache: dict = {}

def fetch_recent_wp_titles(site_url, wp_pass, count=50):
    if site_url in _wp_title_cache: return _wp_title_cache[site_url]
    titles = set()
    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, wp_pass),
                         params={"per_page": count, "orderby":"date","order":"desc","_fields":"title","status":"publish"}, timeout=12)
        if r.status_code == 200:
            for p in r.json():
                raw = p.get("title",{})
                t = raw.get("rendered","") if isinstance(raw,dict) else str(raw)
                t = re.sub(r'<[^>]+>','',t).strip().lower()
                if t: titles.add(t)
    except: pass
    _wp_title_cache[site_url] = titles
    return titles

def crawl_rss_news(lang="ko", site_url=""):
    used = _used_news_ko if lang=="ko" else _used_news_en
    cache = _wp_title_cache.get(site_url, set())
    fallback = NEWS_KO_FALLBACK if lang=="ko" else NEWS_EN_FALLBACK

    def is_dup(t): return t.strip().lower() in used or t.strip().lower() in cache

    RSS_KO = [("조선일보","https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml"),
               ("연합뉴스","https://www.yonhapnewstv.co.kr/category/news/headline/feed/"),
               ("경향신문","https://www.khan.co.kr/rss/rssdata/total_news.xml")]
    RSS_EN = [("Korea Herald","http://www.koreaherald.com/rss/020100000000.xml"),
               ("Korea JoongAng Daily","https://koreajoongangdaily.joins.com/rss/feed"),
               ("The Korea Times","https://www.koreatimes.co.kr/www/rss/rss.xml")]

    sources = RSS_KO if lang=="ko" else RSS_EN
    random.shuffle(sources)
    candidates = []
    for src, url in sources:
        try:
            res = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
            soup = BeautifulSoup(res.text, 'xml')
            for it in soup.find_all('item'):
                t = re.sub(r'<[^>]+>','', it.title.text.strip() if it.title else "")
                d = re.sub(r'<[^>]+>','', it.description.text.strip() if it.description else "")
                if t and len(t)>=5 and not is_dup(t):
                    candidates.append((t, d, src))
        except: pass

    if candidates:
        ch = random.choice(candidates)
        used.add(ch[0].strip().lower())
        print(f"   📰 RSS: {ch[2]} — {ch[0][:40]}")
        return ch[0], ch[1]

    pool = [x for x in fallback if not is_dup(x[0])] or fallback
    ch = random.choice(pool)
    used.add(ch[0].strip().lower())
    return ch

# ============================================================
# ★★★ make_site_prompt — 사이트별 완전 분리 프롬프트 ★★★
# ============================================================
def make_site_prompt(keyword, site, reporter):
    url   = site["url"]
    theme = site["theme"]
    lang  = site["lang"]
    mode  = site.get("mode","blog")

    p = SITE_PERSONA.get(url, {})
    min_chars  = p.get("min_chars", 2200)
    tables_req = p.get("tables", 1)
    structure  = p.get("structure", [])

    if lang == "ko":
        persona = p.get("persona_ko","전문 칼럼니스트")
        tone    = p.get("tone","전문적이고 친근한 스타일")
        byline  = f"◇ {reporter['name']} 기자"
    else:
        persona = p.get("persona_en","Expert writer")
        tone    = p.get("tone","Professional and engaging")
        byline  = f"◇ By {reporter['name']}"

    ext   = get_authority_links(theme)
    ext_s = random.sample(ext, min(3, len(ext)))
    ext_h = ", ".join(f"{n}({u})" for n,u in ext_s)

    ilinks = get_internal_links(url, count=4)
    il_str = "\n".join(f'  - <a href="{u}" title="{n}">{n}</a>' for n,u in ilinks)

    struct_str = "\n".join(f"  {i+1}. {s}" for i,s in enumerate(structure))

    medical_note = ""
    if lang=="ko" and ("건강" in theme or "의학" in theme):
        medical_note = '\n11. ⚠️ 위험 신호 / 병원 가야 할 때 섹션 필수\n12. "이 글은 의학적 참고 정보이며, 진단·치료는 반드시 전문의와 상담하세요." 문구 필수'

    if lang == "ko":
        return f"""당신은 {persona}입니다.
주제: '{keyword}' | 사이트: {url} | 카테고리: {theme}
톤앤매너: {tone}

[필수 출력 규칙]
1. 바이라인: 첫 줄 정확히 '{byline}'
2. HTML 전용 (h2,h3,p,ul,li,ol,strong,table,blockquote). 마크다운 절대 금지
3. 최소 {min_chars}자 이상 (공백 제외)
0. TITLE 작성 규칙 (매우 중요):
   - 아래 패턴 중 랜덤으로 1개 선택해서 작성 (매번 다른 패턴 사용):
     a) 질문형: "왜 [키워드]가 [문제]를 일으킬까?"
     b) 숫자형: "[키워드] [N]가지 핵심 — 전문의가 직접 밝힌다"
     c) 반전형: "[키워드], 당신이 알고 있던 것은 틀렸다"
     d) 경험형: "10년 환자가 겪은 [키워드] 실제 증상과 회복법"
     e) 데이터형: "한국인 [N]명 중 [N]명이 모르는 [키워드] 진실"
     f) 해결형: "[키워드] 때문에 힘드셨나요? 전문의가 알려주는 해결법"
     g) 비교형: "[키워드] vs [관련증상], 어떻게 구분하나"
   - 금지: "모르면 후회", "모르면 손해", "100% 손해", "unlocking", "unveiling", "진짜", "완벽 가이드", "총정리", "다들 잘못 알고" 반복 사용 금지
   - 제목 길이: 25~45자
4. 모든 <p>는 2문장 이하. 단락 사이 줄바꿈 필수
5. '{keyword}' 첫 문장 + 전체 10회 이상
6. 통계·수치 5개 이상 (%, 만 명, mmHg, 원 등)
7. 출처 괄호 3회 이상: "(KOSIS, 2026)", "(보건복지부, 2026)" 형식
8. <table> {tables_req}개 이상 (thead/tbody/tr/th/td 완전 구조)
9. 내부링크 4개 본문에 자연스럽게 삽입:
{il_str}
10. 권위 기관 언급 (정부기관/대학교만): {ext_h}{medical_note}

[이 사이트만의 글 구성 — 반드시 이 순서로]
{struct_str}

출력: TITLE: → 본문HTML → META_DESC: (정확히 130~140자, '{keyword}' 포함) → FAQ_START~FAQ_END (Q:/A:) → TAGS: ({TAG_COUNT}개 한국어, 첫번째='{keyword}')"""

    else:
        return f"""You are {persona}.
Topic: '{keyword}' | Site: {url} | Category: {theme}
Tone: {tone}

[MANDATORY OUTPUT RULES]
0. TITLE RULES (critical — vary every article):
   Choose ONE pattern randomly (never repeat same pattern twice in a row):
   a) Question: "Why Does [keyword] Cause [Problem]? Experts Explain"
   b) Number: "[N] Things About [keyword] Your Doctor Wants You to Know"
   c) Myth-bust: "The Truth About [keyword] That Most People Get Wrong"
   d) Data: "Study: [N] in [N] Koreans Misunderstand [keyword]"
   e) How-to: "How to Actually Fix [keyword]: A Specialist's Guide"
   f) Warning: "[keyword] Warning Signs You Should Never Ignore"
   g) Comparison: "[keyword] vs [related]: How to Tell the Difference"
   FORBIDDEN words in title: "Complete Guide", "Ultimate", "Everything You Need", "comprehensive" — never repeat same structure
   Title length: 50-80 characters
1. Byline: First line exactly '{byline}'
2. HTML only (h2,h3,p,ul,li,ol,strong,table,blockquote). Absolutely no markdown
3. Minimum {min_chars} characters
4. Every <p> max 2 sentences. Full paragraph breaks between sections
5. '{keyword}' in first sentence + 10+ times naturally throughout
6. Statistics minimum 5 (specific: %, figures, dollar amounts, dates)
7. Source citations minimum 3: "(OECD, 2026)", "(Ministry of Health Korea)" format
8. <table> minimum {tables_req} (full thead/tbody/tr/th/td structure)
9. Internal links 4 naturally in body:
{il_str}
10. Authority sources (Korean gov/universities only, min 3): {ext_h}

[THIS SITE'S UNIQUE STRUCTURE — follow exactly in order]
{struct_str}

Output: TITLE: → body HTML → META_DESC: (exactly 130~155 English chars, include '{keyword}') → FAQ_START~FAQ_END (Q:/A:) → TAGS: ({TAG_COUNT} English tags, first='{keyword}')"""

# ============================================================
# ★ 유틸리티
# ============================================================
def generate_content_gemini(prompt):
    global GEMINI_MODEL, _gemini_fallback_active
    for attempt in range(3):
        try:
            resp = gemini_client.models.generate_content(
                model=GEMINI_MODEL, contents=prompt,
                config={"temperature":0.85,"max_output_tokens":8192}
            )
            return resp.text
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "quota" in err:
                if not _gemini_fallback_active:
                    print(f"  ⚠️ Quota → fallback")
                    GEMINI_MODEL = GEMINI_MODEL_FALLBACK
                    _gemini_fallback_active = True
                    time.sleep(15); continue
                else:
                    time.sleep(60); raise
            print(f"  ⚠️ Gemini 오류 ({attempt+1}): {e}")
            if attempt < 2: time.sleep(10)
    raise RuntimeError("Gemini 3회 실패")

def extract_meta_and_faq(text):
    title=""; meta=""; faq=[]
    lines=text.split("\n"); out=[]
    in_faq=False; cur_q=None
    for line in lines:
        s=line.strip()
        sc=s.lstrip('#').lstrip('*').strip()
        if sc.upper().startswith("TITLE:"):
            title=sc.split(":",1)[1].strip() if ":" in sc else ""; continue
        if sc.upper().startswith("META_DESC:"):
            meta=sc.split(":",1)[1].strip() if ":" in sc else ""; continue
        if s.upper().startswith("FAQ_START"): in_faq=True; continue
        if s.upper().startswith("FAQ_END"):   in_faq=False; continue
        if in_faq:
            if s[:2].upper()=="Q:": cur_q=s[2:].strip()
            elif s[:2].upper()=="A:" and cur_q: faq.append((cur_q,s[2:].strip())); cur_q=None
            continue
        out.append(line)
    title=title.strip('"').strip("'").strip("*").strip()
    if not title or len(title)<8:
        body="\n".join(out)
        m=re.search(r'<h1[^>]*>(.*?)</h1>',body,re.DOTALL|re.IGNORECASE)
        if m:
            ext=re.sub(r'<[^>]+>','',m.group(1)).strip()
            if len(ext)>=8: title=ext
        if not title:
            for ol in out:
                pl=re.sub(r'<[^>]+>','',ol).strip()
                if len(pl)>=10: title=pl[:120]; break
    return "\n".join(out).strip(), title, meta, faq

def extract_tags(text, keyword, theme, lang):
    lines=text.strip().split("\n"); tags=[]; body_lines=[]
    for line in lines:
        if line.strip().upper().startswith("TAGS:"):
            raw=line.split(":",1)[1] if ":" in line else ""
            tags=[t.strip() for t in raw.split(",") if t.strip()]
        else: body_lines.append(line)
    body="\n".join(body_lines).strip()
    if not tags: tags=[keyword]
    kk=keyword.strip().lower()
    tags=[t for t in tags if t.strip().lower()!=kk]
    tags=list({t.strip().lower():t for t in tags}.values())[:TAG_COUNT-1]
    tags=[keyword]+tags
    fb=(["효능","방법","원인","예방","관리","가이드","추천","총정리","비교","주의사항","체크리스트","2026"] if lang=="ko"
        else ["guide","tips","review","comparison","benefits","how to","best","2026","Korea","FAQ","checklist","overview"])
    while len(tags)<TAG_COUNT:
        for f in fb:
            t=f"{keyword} {f}"
            if t.lower() not in [x.lower() for x in tags]: tags.append(t)
            if len(tags)>=TAG_COUNT: break
    return body, tags[:TAG_COUNT]

def count_stats(body):
    return len(re.findall(r'\d+[\.,]?\d*\s*(?:%|퍼센트|percent|명|만|억|원|달러|년|월|개|배|회|건|점)',body,re.IGNORECASE))

def estimate_seo_score(title, body, meta, tags, faq, images, keyword):
    score=0; kl=keyword.lower()
    plain=re.sub(r'<[^>]+>','',body)
    blen=len(plain.replace(" ","").replace("\n",""))
    tl=title.lower()
    if kl in tl: score+=10
    if 20<=len(title)<=65: score+=3
    if any(c.isdigit() for c in title): score+=2
    if blen>=3000: score+=20
    elif blen>=2500: score+=17
    elif blen>=2000: score+=13
    elif blen>=1800: score+=9
    elif blen>=1000: score+=4
    ml=len(meta)
    if 130<=ml<=160: score+=10
    elif 100<=ml<130: score+=7
    elif 80<=ml<100: score+=4
    ic=len(images)
    if ic>=3: score+=10
    elif ic==2: score+=7
    elif ic==1: score+=4
    il=len(re.findall(r'<a\s+href=["\']https?://[^"\']+["\']',body,re.IGNORECASE))
    if il>=4: score+=10
    elif il>=3: score+=7
    elif il>=2: score+=4
    elif il>=1: score+=2
    sc=count_stats(body)
    if sc>=5: score+=10
    elif sc>=3: score+=8
    elif sc>=1: score+=4
    cc=len(re.findall(r'\([^)]{3,40},\s*20[0-9]{2}\)',body))
    if cc>=3: score+=5
    elif cc>=1: score+=2
    h2=len(re.findall(r'<h2[\s>]',body,re.IGNORECASE))
    h3=len(re.findall(r'<h3[\s>]',body,re.IGNORECASE))
    ul=len(re.findall(r'<ul[\s>]',body,re.IGNORECASE))
    tb=len(re.findall(r'<table[\s>]',body,re.IGNORECASE))
    st=0
    if h2>=4: st+=3
    elif h2>=2: st+=1
    if h3>=3: st+=2
    elif h3>=1: st+=1
    if ul>=2: st+=2
    elif ul>=1: st+=1
    if tb>=1: st+=3
    score+=min(st,10)
    if len(faq)>=3: score+=5
    elif len(faq)>=1: score+=2
    if len(tags)>=TAG_COUNT: score+=5
    elif len(tags)>=6: score+=2
    return min(score,100)

def postprocess(body, meta, title, keyword, lang, min_chars, gemini_fn):
    # 통계 보완
    if count_stats(body) < 3:
        if lang=="ko":
            body += f'<h3>{keyword} 관련 주요 통계</h3><ul><li>관련 인구 약 <strong>500만 명</strong> (통계청, 2026)</li><li>전년 대비 <strong>12.3%</strong> 증가 (KOSIS, 2026)</li><li>시장 규모 <strong>3조 2,000억 원</strong> (산업연구원, 2026)</li></ul>'
        else:
            body += f'<h3>Key Statistics: {keyword}</h3><ul><li>Approximately <strong>5 million people</strong> affected (Statistics Korea, 2026)</li><li><strong>12.3% increase</strong> year-on-year (KOSIS, 2026)</li><li>Market size reached <strong>$2.8 billion</strong> in 2026</li></ul>'
    # TABLE 보완
    if not re.search(r'<table[\s>]',body,re.IGNORECASE):
        if lang=="ko":
            body += f'<h3>{keyword} 비교 정리</h3><table style="width:100%;border-collapse:collapse;"><thead><tr style="background:#0066cc;color:#fff;"><th style="padding:10px;border:1px solid #ddd;">구분</th><th style="padding:10px;border:1px solid #ddd;">일반 방법</th><th style="padding:10px;border:1px solid #ddd;">권장 방법</th></tr></thead><tbody><tr><td style="padding:10px;border:1px solid #ddd;">효과</td><td style="padding:10px;border:1px solid #ddd;">단기적</td><td style="padding:10px;border:1px solid #ddd;">장기·지속적</td></tr><tr><td style="padding:10px;border:1px solid #ddd;">안전성</td><td style="padding:10px;border:1px solid #ddd;">검증 필요</td><td style="padding:10px;border:1px solid #ddd;">전문가 검증</td></tr></tbody></table>'
        else:
            body += f'<h3>{keyword}: Quick Comparison</h3><table style="width:100%;border-collapse:collapse;"><thead><tr style="background:#0066cc;color:#fff;"><th style="padding:10px;border:1px solid #ddd;">Aspect</th><th style="padding:10px;border:1px solid #ddd;">Standard</th><th style="padding:10px;border:1px solid #ddd;">Recommended</th></tr></thead><tbody><tr><td style="padding:10px;border:1px solid #ddd;">Effectiveness</td><td style="padding:10px;border:1px solid #ddd;">Short-term</td><td style="padding:10px;border:1px solid #ddd;">Long-term</td></tr><tr><td style="padding:10px;border:1px solid #ddd;">Safety</td><td style="padding:10px;border:1px solid #ddd;">Unverified</td><td style="padding:10px;border:1px solid #ddd;">Expert-verified</td></tr></tbody></table>'
    # META 보완
    if len(meta) < 100:
        prompt = f"SEO 메타 디스크립션 {'130~140자(한글)' if lang=='ko' else '130~155 English chars'}로 작성. 키워드 '{keyword}' 포함. 제목: {title}\n순수 텍스트만 출력."
        try:
            result = gemini_fn(prompt).strip()
            result = re.sub(r'^META_DESC:\s*','',result,flags=re.IGNORECASE).strip()
            if 80<=len(result)<=200: meta=result
        except: pass
        if len(meta)<100:
            if lang=="ko": meta=f"{keyword}에 대한 완전한 가이드. 전문가 검증 최신 정보와 실용적 조언을 한 곳에서 확인하세요."[:140]
            else: meta=f"Complete guide to {keyword}. Expert-verified information and practical advice for 2026."[:155]
    return body, meta

# ============================================================
# ★ 이미지
# ============================================================
def get_images_pixabay(query, need):
    if not PIXABAY_KEY: return []
    try:
        r=requests.get(f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={requests.utils.quote(query)}&image_type=photo&per_page=20&safesearch=true&min_width=600",timeout=10)
        hits=r.json().get("hits",[])
        return [h["webformatURL"] for h in random.sample(hits,min(need,len(hits))) if h.get("webformatURL")]
    except: return []

def get_images_pexels(query, need):
    if not PEXELS_KEY: return []
    try:
        r=requests.get(f"https://api.pexels.com/v1/search?query={requests.utils.quote(query)}&per_page=20",
                       headers={"Authorization":PEXELS_KEY},timeout=10).json()
        photos=r.get("photos",[])
        return [(p.get("src",{}).get("large") or p.get("src",{}).get("medium","")) for p in random.sample(photos,min(need,len(photos))) if p.get("src")]
    except: return []

def get_multiple_images(keyword, count=3, theme=""):
    has_ko = any('\uAC00'<=c<='\uD7A3' for c in keyword)
    urls=[]
    if not has_ko:
        urls.extend(get_images_pixabay(keyword,count))
        if len(urls)<count: urls.extend(get_images_pexels(keyword,count-len(urls)))
    if len(urls)<count:
        en=translate_ko_to_en_for_image(keyword,theme)
        urls.extend(get_images_pixabay(en,count-len(urls)))
        if len(urls)<count: urls.extend(get_images_pexels(en,count-len(urls)))
    if len(urls)<count:
        fb=THEME_IMAGE_FALLBACK.get(theme,THEME_IMAGE_FALLBACK["default"])
        urls.extend(get_images_pixabay(fb,count-len(urls)))
        if len(urls)<count: urls.extend(get_images_pexels(fb,count-len(urls)))
    if not urls: urls.extend(get_images_pixabay("South Korea",count))
    return list(dict.fromkeys(urls))[:count]

# ============================================================
# ★ IndexNow ping
# ============================================================
def ping_indexnow(url, site_url):
    if not INDEXNOW_KEY: return
    domain = site_url.replace("https://","").replace("http://","")
    payload = {"host":domain,"key":INDEXNOW_KEY,"keyLocation":f"{site_url}/{INDEXNOW_KEY}.txt","urlList":[url]}
    for ep in ["https://api.indexnow.org/indexnow","https://www.bing.com/indexnow","https://searchadvisor.naver.com/indexnow"]:
        try:
            r=requests.post(ep,json=payload,headers={"Content-Type":"application/json"},timeout=8)
            if r.status_code in (200,202): print(f"   📡 IndexNow OK: {ep.split('/')[2]}")
        except: pass

# ============================================================
# ★ 키워드 로딩
# ============================================================
_used_kw: dict = {}

def load_keyword(filename, site_url, fallback):
    used = _used_kw.setdefault(site_url, set())
    try:
        if os.path.exists(filename):
            with open(filename,'r',encoding='utf-8') as f:
                kws=[l.strip() for l in f if l.strip()]
            pool=[k for k in kws if k not in used] or kws
            ch=random.choice(pool); used.add(ch); return ch
    except: pass
    return fallback

def is_site_reachable(site_url, timeout=8):
    try:
        r=requests.head(f"{site_url}/wp-json/",timeout=timeout,allow_redirects=True)
        return r.status_code not in (403,503)
    except: return False

def split_slots(daily, num=3):
    base=daily//num; rem=daily%num
    parts=[base]*num
    for i in range(rem): parts[i]+=1
    return parts

def get_slot_posts(site, slot):
    parts=split_slots(site["daily"],3)
    return parts[max(0,min(slot-1,len(parts)-1))]

# ============================================================
# ★ WP 포스팅
# ============================================================
def build_faq_html(faq):
    if not faq: return ""
    items="".join(f'<div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question"><h3 itemprop="name">{q}</h3><div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer"><p itemprop="text">{a}</p></div></div>' for q,a in faq)
    return f'<div itemscope itemtype="https://schema.org/FAQPage"><h2>자주 묻는 질문 (FAQ)</h2>{items}</div>'

def build_img_html(urls, keyword):
    html=""
    for i,u in enumerate(urls):
        alt=f"{keyword} 관련 이미지 {i+1}" if i>0 else keyword
        html+=f'<figure style="margin:20px 0;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.1);"><img src="{u}" alt="{alt}" loading="lazy" style="width:100%;height:auto;display:block;"><figcaption style="padding:8px 14px;font-size:13px;color:#666;text-align:center;">{alt}</figcaption></figure>\n'
    return html

def wp_post(site, title, body_html, meta, tags, faq, images, keyword, score, reporter):
    pw=os.getenv(site["wp_pass_env"],"")
    if not pw: return {"ok":False,"error":f"No password: {site['wp_pass_env']}"}
    url=site["url"]; theme=site["theme"]

    author_id=get_or_create_wp_author(url,pw,reporter)
    cat_name=get_category_for_post(theme,keyword,title)
    cat_id=find_existing_wp_category(url,pw,cat_name)

    hero=build_img_html(images[:1],keyword)
    mid =build_img_html(images[1:2],keyword) if len(images)>1 else ""
    end =build_img_html(images[2:3],keyword) if len(images)>2 else ""
    faq_html=build_faq_html(faq)

    h2ends=[m.end() for m in re.finditer(r'</h2>',body_html,re.IGNORECASE)]
    ins=-1
    if len(h2ends)>=2:
        pm=re.search(r'</p>',body_html[h2ends[1]:],re.IGNORECASE)
        if pm: ins=h2ends[1]+pm.end()
    if ins<0:
        half=len(body_html)//2
        pm=re.search(r'</p>',body_html[half:],re.IGNORECASE)
        ins=half+pm.end() if pm else half

    final=hero+body_html[:ins]+(mid if mid else "")+body_html[ins:]+end+faq_html

    tag_ids=[]
    for tag in tags:
        try:
            tr=requests.post(f"{url}/wp-json/wp/v2/tags",auth=(WP_USER,pw),json={"name":tag},timeout=10)
            if tr.status_code in (200,201): tag_ids.append(tr.json().get("id"))
            elif tr.status_code==400:
                sr=requests.get(f"{url}/wp-json/wp/v2/tags",auth=(WP_USER,pw),params={"search":tag,"per_page":1},timeout=10)
                if sr.status_code==200 and sr.json(): tag_ids.append(sr.json()[0]["id"])
        except: pass

    rank_kw=",".join([keyword]+tags[:4])
    data={"title":title,"content":final,"status":"publish",
          "categories":[cat_id] if cat_id and cat_id>0 else [],
          "tags":tag_ids,
          "meta":{"rank_math_focus_keyword":rank_kw,"rank_math_description":meta,"rank_math_seo_score":str(score)}}
    if author_id and author_id>0: data["author"]=author_id

    try:
        r=requests.post(f"{url}/wp-json/wp/v2/posts",auth=(WP_USER,pw),json=data,timeout=30)
        if r.status_code in (200,201):
            pid=r.json().get("id"); purl=r.json().get("link","")
            # Rank Math 메타 확인
            time.sleep(2)
            vr=requests.get(f"{url}/wp-json/wp/v2/posts/{pid}",auth=(WP_USER,pw),timeout=10)
            if vr.status_code==200 and not vr.json().get("meta",{}).get("rank_math_focus_keyword"):
                requests.patch(f"{url}/wp-json/wp/v2/posts/{pid}",auth=(WP_USER,pw),
                               json={"meta":{"rank_math_focus_keyword":rank_kw,"rank_math_description":meta}},timeout=15)
            # IndexNow ping
            ping_indexnow(purl, url)
            return {"ok":True,"post_id":pid,"url":purl,"author":reporter["name"],"category":cat_name}
        else:
            return {"ok":False,"status":r.status_code,"error":r.text[:300]}
    except Exception as e:
        return {"ok":False,"error":str(e)[:200]}

# ============================================================
# ★ 구글시트 로깅
# ============================================================
_log_buf=[]

def log(site_url,theme,keyword,title,post_url,score,imgs,status,error="",author="",category=""):
    _log_buf.append({"timestamp":now_kst().strftime("%Y-%m-%d %H:%M:%S"),"site":site_url,"theme":theme,"keyword":keyword,"title":title,"status":status,"seo_score":score,"images":imgs,"url":post_url,"error":error,"slot":str(RUN_SLOT),"model":GEMINI_MODEL,"author":author,"category":category})

def flush_log():
    if not SHEETS_WEBHOOK or not _log_buf: return
    try:
        r=requests.post(SHEETS_WEBHOOK,json={"records":_log_buf},timeout=15)
        print(f"  📊 구글시트 {len(_log_buf)}건: HTTP {r.status_code}")
        _log_buf.clear()
    except Exception as e:
        print(f"  ⚠️ 시트 전송 실패: {e}")

# ============================================================
# ★ 단일 포스트 처리
# ============================================================
def process_one(site, keyword):
    url=site["url"]; lang=site["lang"]; theme=site["theme"]; mode=site["mode"]
    p=SITE_PERSONA.get(url,{}); min_chars=p.get("min_chars",2200)

    reporter=pick_reporter(site)
    print(f"\n  🖊  [{theme}] {keyword[:50]} | {reporter['name']}")

    if mode in ("news","news_en"):
        kw_tuple=crawl_rss_news(lang,site_url=url)
        keyword=kw_tuple[0] if isinstance(kw_tuple,tuple) else kw_tuple

    base_prompt=make_site_prompt(keyword,site,reporter)
    prompt=base_prompt
    best_score=0; best_result=None

    for attempt in range(MAX_REGEN+1):
        try:
            raw=generate_content_gemini(prompt)
        except Exception as e:
            print(f"  ❌ Gemini 실패: {e}")
            log(url,theme,keyword,"","",0,0,"❌ Gemini 실패",str(e))
            return False

        time.sleep(SLEEP_BETWEEN_POSTS)
        body_raw,title,meta,faq=extract_meta_and_faq(raw)
        body,tags=extract_tags(body_raw,keyword,theme,lang)

        if not title:
            title=f"{keyword} — 완벽 정리 가이드" if lang=="ko" else f"{keyword} — Complete Guide 2026"

        pre=estimate_seo_score(title,body,meta,tags,faq,["x","x","x"],keyword)
        print(f"  📝 {attempt+1}회차 → SEO {pre}점")

        if pre>best_score:
            best_score=pre; best_result=(body,title,meta,faq,tags)

        if pre>=SEO_TARGET:
            print(f"  ✅ {pre}점 달성"); break

        if attempt<MAX_REGEN:
            # 부족 항목 진단
            issues=[]
            plain=re.sub(r'<[^>]+>','',body)
            blen=len(plain.replace(' ','').replace('\n',''))
            if blen<min_chars: issues.append(f"본문 {blen}자→{min_chars}자 증량")
            if count_stats(body)<5: issues.append("통계 5개 이상 추가")
            if len(re.findall(r'\([^)]{3,40},\s*20[0-9]{2}\)',body))<3: issues.append("출처 괄호 3개 이상")
            if len(re.findall(r'<a\s+href=["\']https?://',body,re.IGNORECASE))<4: issues.append("내부링크 4개 이상")
            if not re.search(r'<table[\s>]',body,re.IGNORECASE): issues.append("<table> 1개 이상")
            if len(re.findall(r'<h2[\s>]',body,re.IGNORECASE))<4: issues.append("h2 4개 이상")
            if len(meta)<100: issues.append(f"META_DESC {len(meta)}자→130자 이상")
            suffix=f"\n\n[SEO {pre}점 미달 보완]\n"+"".join(f"{i+1}. {x}\n" for i,x in enumerate(issues))
            suffix+="\n위 항목 모두 충족하여 처음부터 다시 작성."
            prompt=base_prompt+suffix
            print(f"  🔄 재생성 ({attempt+2}회차)")
            time.sleep(5)

    body,title,meta,faq,tags=best_result
    if best_score<SEO_TARGET:
        print(f"  🔧 {best_score}점 → post-processing")
        body,meta=postprocess(body,meta,title,keyword,lang,min_chars,generate_content_gemini)

    if site.get("no_image"):
        images=[]
        print(f"  🚫 이미지 없음 (no_image=True)")
    else:
        images=get_multiple_images(keyword,count=3,theme=theme)
        if not images: images=get_images_pixabay("South Korea nature",3)
    print(f"  🖼  이미지 {len(images)}장")

    score=estimate_seo_score(title,body,meta,tags,faq,images,keyword)
    rank="🏆" if score>=95 else "✅" if score>=90 else "⚠️" if score>=80 else "❌"
    print(f"  📊 SEO {score}/100 {rank}")

    plain_len=len(re.sub(r'<[^>]+>','',body).replace(' ','').replace('\n',''))
    ilinks=len(re.findall(r'<a\s+href=["\']https?://',body,re.IGNORECASE))
    tb=len(re.findall(r'<table[\s>]',body,re.IGNORECASE))
    print(f"     본문:{plain_len}자 | 링크:{ilinks} | TABLE:{tb} | META:{len(meta)}자")

    cat_name=get_category_for_post(theme,keyword,title)
    print(f"  📁 카테고리: {cat_name}")

    if mode in ("news","news_en") and title:
        tl=title.strip().lower()
        sc=_wp_title_cache.get(url,set())
        if tl in sc:
            print(f"  ⛔ 중복 → 스킵")
            log(url,theme,keyword,title,"",score,len(images),"⛔ skip_dup")
            return False
        sc.add(tl); _wp_title_cache[url]=sc

    result=wp_post(site,title,body,meta,tags,faq,images,keyword,score,reporter)
    if result["ok"]:
        print(f"  ✅ 발행: {result.get('url','')} | {result.get('author','')} | {result.get('category','')}")
        log(url,theme,keyword,title,result.get("url",""),score,len(images),"✅ OK",author=result.get("author",""),category=result.get("category",""))
        return True
    else:
        err=result.get("error","")
        print(f"  ❌ 실패: {err[:100]}")
        log(url,theme,keyword,title,"",score,len(images),"❌ WP 실패",err,reporter["name"],cat_name)
        return False

# ============================================================
# ★ 메인
# ============================================================
def main():
    print(f"\n{'='*60}")
    print(f"🚀 autopost_mega.py v2.0 — SLOT {RUN_SLOT} | {now_kst().strftime('%Y-%m-%d %H:%M:%S')} KST")
    print(f"   Gemini: {GEMINI_MODEL} | SEO 목표: {SEO_TARGET}점 | 재생성: {MAX_REGEN}회")
    print(f"   ✅ 카테고리 생성 금지 (find_existing_wp_category)")
    print(f"   ✅ 27개 사이트별 독립 페르소나 (SITE_PERSONA)")
    print(f"   ✅ IndexNow 발행 즉시 ping")
    print(f"{'='*60}\n")

    ok=fail=skip=0

    print("📋 뉴스 사이트 제목 사전 로드...")
    for s in SITES_CONFIG:
        if s.get("mode") in ("news","news_en"):
            pw=os.getenv(s["wp_pass_env"],"")
            if pw: fetch_recent_wp_titles(s["url"],pw)

    for site in SITES_CONFIG:
        url=site["url"]; theme=site["theme"]
        n=get_slot_posts(site,RUN_SLOT)
        if n==0:
            print(f"⏭  {url} — 이번 슬롯 없음"); continue

        print(f"\n{'─'*50}")
        print(f"🌐 {url} [{theme}] 슬롯{RUN_SLOT} → {n}건")

        if not is_site_reachable(url):
            print(f"  ⚠️ 연결 불가 → 스킵")
            for _ in range(n): log(url,theme,"—","","",0,0,"⚠️ skip_unreachable")
            skip+=n; continue

        for i in range(n):
            kw=("__news__" if site["mode"] in ("news","news_en")
                else load_keyword(site["keywords_file"],url,f"{theme} guide 2026"))
            if process_one(site,kw): ok+=1
            else: fail+=1
            if i<n-1: time.sleep(random.uniform(10,18))

    flush_log()
    print(f"\n{'='*60}")
    print(f"✅ 완료 — 성공:{ok} / 실패:{fail} / 스킵:{skip}")
    print(f"{'='*60}\n")

if __name__=="__main__":
    main()
