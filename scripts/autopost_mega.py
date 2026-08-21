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

import os, sys, time, random, re, json, hashlib, base64
import requests
from email.utils import parsedate_to_datetime
from pathlib import Path
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from google import genai
from google.genai import types as genai_types
from news_source_registry import get_enabled_rss_sources

KST = timezone(timedelta(hours=9))
def now_kst():
    return datetime.now(KST)

NEWSROOM_DAILY_MIN = 3
NEWSROOM_DAILY_MAX = 10

def newsroom_daily_target(site_url, day=None):
    """Stable per-site target for one KST day; changes automatically next day."""
    day = day or now_kst().date()
    seed = hashlib.sha256(f"{site_url}|{day.isoformat()}".encode()).digest()
    return NEWSROOM_DAILY_MIN + int.from_bytes(seed[:4], "big") % 8

def count_published_today(site_url, wp_pass):
    """Count posts published since KST midnight; fail closed on API errors."""
    midnight = datetime.combine(now_kst().date(), datetime.min.time(), tzinfo=KST)
    after_utc = midnight.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        response = requests.get(
            f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, wp_pass),
            params={"status":"publish", "after":after_utc, "per_page":1, "_fields":"id"},
            timeout=12,
        )
        response.raise_for_status()
        return int(response.headers.get("X-WP-Total", len(response.json())))
    except Exception as exc:
        print(f"  NEWSROOM DAILY GATE: publication count unavailable ({exc})")
        return None

GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
PIXABAY_KEY     = os.getenv("PIXABAY_KEY")
PEXELS_KEY      = os.getenv("PEXELS_KEY")
SHEETS_WEBHOOK  = os.getenv("SHEETS_WEBHOOK")
INDEXNOW_KEY    = os.getenv("INDEXNOW_KEY", "907ae08aa52b45239490ed2407df835d")
WP_USER         = "huh0303@gmail.com"

RUN_SLOT            = int(os.getenv("RUN_SLOT", "1"))
SLEEP_BETWEEN_POSTS = float(os.getenv("SLEEP_BETWEEN_POSTS", "8"))

gemini_client         = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL_PRIMARY  = "gemini-2.5-flash-lite"
GEMINI_MODEL_FALLBACK = "gemini-2.5-flash"
GEMINI_MODEL          = GEMINI_MODEL_PRIMARY
_gemini_fallback_active = False
# 나노바나나(Nano Banana) — Pixabay/Pexels 검색이 실패했을 때 인포그래픽 카드 대신
# 프롬프트로 실제 사진풍 이미지를 생성하는 폴백 (다른 파이프라인들과 동일한 모델 목록)
GEMINI_IMAGE_MODELS = ["gemini-2.5-flash-image", "gemini-2.5-flash-image-preview"]

TAG_COUNT   = 10
# 2026-08-17 사용자 지시: "SEO점수 80점 이상, 두번시도 해서 안되면 발행하지 말것"
# — 예전 90/3회(4번 시도)보다 기준은 낮췄지만 시도 횟수를 줄여 ChatGPT 전환 후
# 비용을 통제. 80점도 여전히 하드 게이트(미달이면 발행 자체 스킵, process_one 참고).
SEO_TARGET  = 80
MAX_REGEN   = 1

# ============================================================
# ★ 기자 풀
# ============================================================
# ============================================================
# ★ 2026-07-24 재개편: k-health365.com 외 26개 사이트는 구글 애드센스 승인이 목표.
#   "동일 운영자가 굴리는 사이트 네트워크"처럼 보이면 승인에 불리하므로,
#   3명 공유 방식을 폐기하고 27개 사이트 전부 서로 다른 고유 필자로 배정.
#   (사이트 내부에서 매번 랜덤으로 바뀌던 예전 방식의 문제 — 필자가 안 바뀌는 것 —
#    도 동시에 해결: 사이트당 1명, 그 사이트 안에서는 항상 동일 인물 고정)
# ============================================================
AUTHOR_BY_SITE_DEF = {
    "k-health365.com": {
        "name": "K-Health Editorial Desk",
        "email": "editor@k-health365.com",
        "slug": "k-health365-com-desk",
        "bio": "K-Health Editorial Desk. Source-checked information within this site's stated editorial scope."
    },
    "koreamedicaltour.com": {
        "name": "Korea Medical Tourism Desk",
        "email": "editor@koreamedicaltour.com",
        "slug": "koreamedicaltour-com-desk",
        "bio": "Korea Medical Tourism Desk. Source-checked information within this site's stated editorial scope."
    },
    "koreainvest365.com": {
        "name": "Korea Capital Markets Desk",
        "email": "editor@koreainvest365.com",
        "slug": "koreainvest365-com-desk",
        "bio": "Korea Capital Markets Desk. Source-checked information within this site's stated editorial scope."
    },
    "ki-korea.com": {
        "name": "Invest Korea Entry Desk",
        "email": "editor@ki-korea.com",
        "slug": "ki-korea-com-desk",
        "bio": "Invest Korea Entry Desk. Source-checked information within this site's stated editorial scope."
    },
    "koreainsurance365.com": {
        "name": "Korea Insurance Guide Desk",
        "email": "editor@koreainsurance365.com",
        "slug": "koreainsurance365-com-desk",
        "bio": "Korea Insurance Guide Desk. Source-checked information within this site's stated editorial scope."
    },
    "kfinance365.com": {
        "name": "Korea Personal Finance Desk",
        "email": "editor@kfinance365.com",
        "slug": "kfinance365-com-desk",
        "bio": "Korea Personal Finance Desk. Source-checked information within this site's stated editorial scope."
    },
    "koreataxnlaw.com": {
        "name": "Korea Tax and Compliance Desk",
        "email": "editor@koreataxnlaw.com",
        "slug": "koreataxnlaw-com-desk",
        "bio": "Korea Tax and Compliance Desk. Source-checked information within this site's stated editorial scope."
    },
    "koreacrypto365.com": {
        "name": "Korea Digital Asset Policy Desk",
        "email": "editor@koreacrypto365.com",
        "slug": "koreacrypto365-com-desk",
        "bio": "Korea Digital Asset Policy Desk. Source-checked information within this site's stated editorial scope."
    },
    "krealestate365.com": {
        "name": "Korea Housing Desk",
        "email": "editor@krealestate365.com",
        "slug": "krealestate365-com-desk",
        "bio": "Korea Housing Desk. Source-checked information within this site's stated editorial scope."
    },
    "ktech365.com": {
        "name": "Korea Technology Industry Desk",
        "email": "editor@ktech365.com",
        "slug": "ktech365-com-desk",
        "bio": "Korea Technology Industry Desk. Source-checked information within this site's stated editorial scope."
    },
    "kskin365.com": {
        "name": "Retired Site",
        "email": "editor@kskin365.com",
        "slug": "kskin365-com-desk",
        "bio": "Retired Site. Source-checked information within this site's stated editorial scope."
    },
    "oliveyoungkorea.com": {
        "name": "Olive Young Shopping Guide Desk",
        "email": "editor@oliveyoungkorea.com",
        "slug": "oliveyoungkorea-com-desk",
        "bio": "Olive Young Shopping Guide Desk. Source-checked information within this site's stated editorial scope."
    },
    "kworld365.com": {
        "name": "Korean Entertainment Brief Desk",
        "email": "editor@kworld365.com",
        "slug": "kworld365-com-desk",
        "bio": "Korean Entertainment Brief Desk. Source-checked information within this site's stated editorial scope."
    },
    "k-trip365.com": {
        "name": "Korea Independent Travel Desk",
        "email": "editor@k-trip365.com",
        "slug": "k-trip365-com-desk",
        "bio": "Korea Independent Travel Desk. Source-checked information within this site's stated editorial scope."
    },
    "k-visa365.com": {
        "name": "Korea Immigration Procedure Desk",
        "email": "editor@k-visa365.com",
        "slug": "k-visa365-com-desk",
        "bio": "Korea Immigration Procedure Desk. Source-checked information within this site's stated editorial scope."
    },
    "koreawedding365.com": {
        "name": "Korea Wedding Planning Desk",
        "email": "editor@koreawedding365.com",
        "slug": "koreawedding365-com-desk",
        "bio": "Korea Wedding Planning Desk. Source-checked information within this site's stated editorial scope."
    },
    "kstudy365.com": {
        "name": "Korea University Admissions Desk",
        "email": "editor@kstudy365.com",
        "slug": "kstudy365-com-desk",
        "bio": "Korea University Admissions Desk. Source-checked information within this site's stated editorial scope."
    },
    "studyinkorea365.com": {
        "name": "International Student Life Desk",
        "email": "editor@studyinkorea365.com",
        "slug": "studyinkorea365-com-desk",
        "bio": "International Student Life Desk. Source-checked information within this site's stated editorial scope."
    },
    "kieca-korea.org": {
        "name": "KIECA 국제교육시장 편집 데스크",
        "email": "editor@kieca-korea.org",
        "slug": "kieca-korea-org-desk",
        "bio": "KIECA 국제교육시장 편집 데스크. Source-checked information within this site's stated editorial scope."
    },
    "ksa-korea.org": {
        "name": "한국유학 준비정보 편집 데스크",
        "email": "editor@ksa-korea.org",
        "slug": "ksa-korea-org-desk",
        "bio": "한국유학 준비정보 편집 데스크. Source-checked information within this site's stated editorial scope."
    },
    "sis-korea.com": {
        "name": "Korea International Programs Desk",
        "email": "editor@sis-korea.com",
        "slug": "sis-korea-com-desk",
        "bio": "Korea International Programs Desk. Source-checked information within this site's stated editorial scope."
    },
    "jobkorea365.com": {
        "name": "Korea Employment Rules Desk",
        "email": "editor@jobkorea365.com",
        "slug": "jobkorea365-com-desk",
        "bio": "Korea Employment Rules Desk. Source-checked information within this site's stated editorial scope."
    },
    "jobinkorea365.com": {
        "name": "Korea Job Search Desk",
        "email": "editor@jobinkorea365.com",
        "slug": "jobinkorea365-com-desk",
        "bio": "Korea Job Search Desk. Source-checked information within this site's stated editorial scope."
    },
    "jobkoreaglobal.com": {
        "name": "Korea Global Hiring Desk",
        "email": "editor@jobkoreaglobal.com",
        "slug": "jobkoreaglobal-com-desk",
        "bio": "Korea Global Hiring Desk. Source-checked information within this site's stated editorial scope."
    },
    "korea365.org": {
        "name": "Korea Newcomer Guide Desk",
        "email": "editor@korea365.org",
        "slug": "korea365-org-desk",
        "bio": "Korea Newcomer Guide Desk. Source-checked information within this site's stated editorial scope."
    },
    "koreanews365.com": {
        "name": "한국신문 편집국",
        "email": "editor@koreanews365.com",
        "slug": "koreanews365-com-desk",
        "bio": "한국신문 편집국. 공식 자료와 복수 출처를 확인해 보도합니다."
    },
    "theseouljournal.com": {
        "name": "SJ Editor",
        "email": "editor@theseouljournal.com",
        "slug": "theseouljournal-com-desk",
        "bio": "The Seoul Journal editorial desk. Source-checked reporting with Korea and Asia in context."
    }
}
AUTHOR_BY_SITE = AUTHOR_BY_SITE_DEF
_DEFAULT_AUTHOR_KO = AUTHOR_BY_SITE_DEF["k-health365.com"]
_DEFAULT_AUTHOR_EN = AUTHOR_BY_SITE_DEF["koreamedicaltour.com"]

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
    """사이트 URL에 매칭되는 고정 필자를 반환. 매칭 실패 시 언어 기준 기본값."""
    url  = site.get("url","")
    lang = site.get("lang","en")
    for domain, author in AUTHOR_BY_SITE.items():
        if domain in url:
            return author
    return _DEFAULT_AUTHOR_KO if lang == "ko" else _DEFAULT_AUTHOR_EN

# ============================================================
# ★★★ 카테고리 — 조회만, 절대 생성 금지 ★★★
# ============================================================
_wp_category_cache: dict = {}

def load_site_categories(site_url, wp_pass):
    """사이트에 실제 존재하는 카테고리 전체를 (id, name) 리스트로 로드 (캐싱)."""
    cache = _wp_category_cache.setdefault(site_url, {})
    if "__all__" in cache:
        return cache["__all__"]
    all_cats = []
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
                n = cat.get("name", "").strip()
                cid = cat.get("id", 1)
                if n:
                    all_cats.append((cid, n))
            page += 1
            if len(cats) < 100: break
    except Exception as e:
        print(f"   ⚠️ 카테고리 로드 실패: {e}")
    cache["__all__"] = all_cats
    print(f"   📁 {site_url} 실제 카테고리 {len(all_cats)}개: {[n for _,n in all_cats]}")
    return all_cats


# ★ 카테고리 자동매칭이 어려운(공백없는 복합어 등) 카테고리에 한해 수동 힌트 제공.
#   여기 없는 카테고리는 기존 어간/슬라이딩윈도우 매칭 로직만 사용.
CATEGORY_HINTS = {
    "https://k-health365.com": {
        "건강영양성분소개": ["영양", "성분", "효능", "보충제", "비타민", "미네랄", "홍삼", "오메가",
                        "프로바이오틱스", "콜라겐", "항산화", "식품", "부작용", "섭취"],
        "질병별대처법": ["관절염", "당뇨", "고혈압", "신장", "방광", "심장", "질환", "증상", "치료",
                    "환자", "통증", "탈모", "암", "뇌", "혈관", "소화", "위염", "질병"],
    },
}


def pick_best_category(site_url, wp_pass, keyword, title=""):
    """
    사이트에 이미 존재하는 카테고리 중에서만 고른다. 새로 생성하지 않는다.
    'Uncategorized'/'미분류'는 후보에서 제외(진짜 fallback 카테고리가 따로 있음:
    'Etc'/'기타' 등). 매칭되는 게 없으면 그 fallback 카테고리로 보낸다.
    """
    cats = load_site_categories(site_url, wp_pass)
    if not cats:
        return 1  # 사이트에 카테고리 정보 자체를 못 가져왔을 때만 최후수단

    real = [(cid, n) for cid, n in cats if n.strip().lower() not in ("uncategorized", "미분류")]
    if not real:
        return cats[0][0]

    # ★ 키워드 파일에 명시된 카테고리 태그가 있으면 최우선으로 사용 (2026-07-22)
    #   (기존엔 이 정보 자체가 없어서 매번 눈먼 텍스트매칭/AI호출에 의존했음)
    hint = _last_keyword_category.get(site_url)
    if hint:
        hint_norm = re.sub(r'[\s/,\-]+', '', hint.strip().lower())
        for cid, n in real:
            if re.sub(r'[\s/,\-]+', '', n.strip().lower()) == hint_norm:
                return cid

    etc_cat = None
    for cid, n in real:
        if n.strip().lower() in ("etc", "기타", "etc.", "other", "others"):
            etc_cat = (cid, n)

    st = f"{keyword} {title}".lower()
    st_words = [w for w in re.split(r'[\s/,\-]+', st) if len(w) > 2]
    # 공백을 없앤 전체 텍스트도 준비 (한글 복합어 카테고리명 매칭용)
    st_nospace = re.sub(r'[\s/,\-]+', '', st)

    best, best_score = None, 0
    for cid, name in real:
        if etc_cat and cid == etc_cat[0]:
            continue  # etc는 최후수단이므로 매칭 후보에서 제외
        cat_words = [w for w in re.split(r'[\s/,\-]+', name.lower()) if len(w) > 2]
        score = 0
        for cw in cat_words:
            stem = cw[:5] if len(cw) > 5 else cw  # 어간(앞 5글자)으로 단복수/변형 흡수
            for sw in st_words:
                if sw.startswith(stem) or stem.startswith(sw[:5]):
                    score += 1
                    break
        # ★ 한글 복합어(공백 없이 붙은 카테고리명, 예: '건강영양성분소개') 대응:
        #   단어 분리가 안 되므로, 카테고리명에서 2글자 슬라이딩 윈도우를 뽑아
        #   본문 키워드/제목(공백 제거본) 안에 등장하는지 직접 확인
        name_nospace = re.sub(r'[\s/,\-]+', '', name.lower())
        if len(name_nospace) >= 2:
            chunks = [name_nospace[i:i+2] for i in range(len(name_nospace)-1)]
            for ch in chunks:
                if len(ch) == 2 and ch in st_nospace:
                    score += 1
        if name.strip().lower() in st:
            score += 10
        # ★ 수동 힌트 사전 매칭 (있으면 강한 가점)
        hints = CATEGORY_HINTS.get(site_url, {}).get(name, [])
        for h in hints:
            if h.lower() in st:
                score += 3
        if score > best_score:
            best, best_score = (cid, name), score

    # ★ 단어/힌트 매칭으로 확신 있는 결과(score>=3)를 못 찾으면, Gemini에게
    #   딱 카테고리 이름만 보여주고 골라달라고 짧게 물어봄(의미적 매칭).
    #   토큰 몇 십 개 수준의 초경량 호출이라 비용 부담 거의 없음.
    if (not best or best_score < 3) and len(real) - (1 if etc_cat else 0) >= 1:
        try:
            candidates = [n for cid2, n in real if not (etc_cat and cid2 == etc_cat[0])]
            cand_str = ", ".join(candidates)
            gprompt = (f"다음 글 제목/키워드를 아래 카테고리 중 하나로 분류해줘. "
                       f"카테고리 이름만 정확히 그대로 한 단어(구)로만 답해. 애매하면 가장 가까운 것.\n"
                       f"카테고리 목록: {cand_str}\n"
                       f"제목/키워드: {title} {keyword}\n"
                       f"답(카테고리 이름만):")
            resp = gemini_client.models.generate_content(
                model=GEMINI_MODEL_FALLBACK, contents=gprompt,
                config={"temperature":0.1,"max_output_tokens":300,
                        "thinking_config":{"thinking_budget":0}})
            # ★ 버그수정(2026-07-22): max_output_tokens=20이 너무 작아서
            #   gemini-2.5-flash가 내부 thinking 토큰만 쓰다가 실제 답변 텍스트가
            #   None으로 나오던 문제. thinking 끄고 토큰 여유를 넉넉히 줌.
            picked = (resp.text or "").strip().strip('."\'')
            for cid2, n in real:
                if n.strip().lower() == picked.lower():
                    best, best_score = (cid2, n), 99
                    break
        except Exception as e:
            print(f"   ⚠️ 카테고리 AI분류 실패(무시하고 계속): {e}")

    if best and best_score > 0:
        return best[0]
    if etc_cat:
        return etc_cat[0]
    return real[0][0]

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
    "한국 뉴스": {"default":"글로벌 (GLOBAL)","keyword_map":[
        (["정치","대통령","국회","선거","여당","야당","탄핵"],"정치 (POLITICS)"),
        (["경제","금리","물가","GDP","수출","무역","코스피","기업","삼성","현대","SK","LG"],"경제 (ECONOMY)"),
        (["사회","범죄","복지","노동","청년","저출산"],"사회 (SOCIETY)"),
        (["문화","K-pop","드라마","영화"],"문화 (CULTURE)"),
        (["금융","주가","증시","은행"],"금융 (FINANCE)"),
        (["부동산","아파트","주택","집값","전세"],"부동산 (REAL ESTATE)"),
        (["국방","군사","군대","국방부"],"국방 (MILITARY)"),
        (["예술","미술","전시"],"예술 (ART)"),
        (["스포츠","야구","축구","올림픽"],"스포츠 (SPORTS)"),
        (["국제","미국","중국","일본","EU","UN","외교","북한"],"글로벌 (GLOBAL)"),
    ]},
    "Seoul Lifestyle": {"default":"Global","keyword_map":[
        (["politics","election","president","government"],"POLITICS"),
        (["economy","GDP","inflation","stock"],"ECONOMY"),
        (["business","startup","company","CEO"],"Economy"),
        (["global","international","US","China","UN"],"Global"),
        (["culture","K-pop","drama","music","food"],"Culture"),
        (["tech","AI","semiconductor","IT"],"Economy"),
        (["finance","stock","bank","market"],"Finance"),
        (["property","housing","real estate"],"Real Estate"),
        (["military","defense","army","navy"],"Military"),
        (["art","museum","exhibition"],"Art"),
        (["sports","baseball","football","Olympics"],"Sports"),
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
        "persona_ko": "K-Health 건강정보 편집 데스크. 질병관리청·보건복지부·의학회·대학병원 자료를 바탕으로 일반 독자가 이해할 수 있는 건강 정보를 정리합니다.",
        "scope": "근거 기반 질환 예방·증상 이해·일상 관리와 진료가 필요한 위험 신호",
        "tone": "차분하고 따뜻한 설명체. 단정적 진단이나 치료 보장 없이 사실·한계·다음 행동을 분명히 제시합니다.",
        "structure": [
            "독자가 겪는 상황과 핵심 질문",
            "공식 자료에 근거한 원인과 위험요인",
            "생활관리 방법과 주의점",
            "진료가 필요한 위험 신호",
            "공식 출처와 확인일",
            "핵심 요약",
            "FAQ"
        ],
        "min_chars": 3500,
        "tables": 1,
        "lang": "ko",
        "cta": "관련 건강정보 더 보기"
    },
    "https://koreamedicaltour.com": {
        "persona_en": "Korea Medical Tourism editorial desk producing neutral, source-checked guidance for international patients considering care in South Korea.",
        "scope": "The complete Korea medical-tourism journey for foreign patients: provider selection, consultation, estimated costs, visas, travel, interpretation, treatment logistics, recovery, and complaint channels",
        "tone": "Calm, practical and patient-centered. Never claim personal patient experience, clinical credentials, guaranteed outcomes, or undisclosed hospital endorsement.",
        "structure": [
            "Who this pathway is for",
            "How to verify hospitals and clinicians",
            "Consultation and estimate process",
            "Visa, travel and interpreter logistics",
            "Treatment and recovery planning",
            "Costs, consent, risks and complaint channels",
            "Official sources and checked date",
            "FAQ"
        ],
        "min_chars": 2600,
        "tables": 1,
        "lang": "en",
        "cta": "Use the checklist to prepare questions for licensed providers"
    },
    "https://koreainvest365.com": {
        "persona_en": "Korea Capital Markets editorial desk.",
        "scope": "Korean listed stocks, ETFs, market structure and official market data for international investors",
        "tone": "Evidence-led market brief with dated figures, clear uncertainty and no personalized investment recommendation.",
        "structure": [
            "Market question",
            "Current official data",
            "Drivers",
            "Risks",
            "Access and regulation for foreign investors",
            "Source list and data date",
            "FAQ"
        ],
        "min_chars": 2400,
        "tables": 1,
        "lang": "en",
        "cta": "Read the next Korea market brief"
    },
    "https://ki-korea.com": {
        "persona_en": "Invest Korea Entry editorial desk.",
        "scope": "Foreign direct investment and business establishment in Korea",
        "tone": "Plain, procedural and institution-focused. No invented executive experience or return promises.",
        "structure": [
            "Who the route fits",
            "Investment structure options",
            "Registration process",
            "Costs and timeline",
            "Incentives and limits",
            "Official contacts and checked date",
            "FAQ"
        ],
        "min_chars": 2400,
        "tables": 1,
        "lang": "en",
        "cta": "Download the official-agency checklist"
    },
    "https://koreainsurance365.com": {
        "persona_en": "Korea Insurance Guide editorial desk.",
        "scope": "Insurance eligibility, enrollment, coverage and claims for foreign residents in Korea",
        "tone": "Careful comparison language with exclusions and source dates stated before conclusions.",
        "structure": [
            "Eligibility",
            "Coverage terms",
            "Exclusions",
            "Enrollment",
            "Claims",
            "Official sources and checked date",
            "FAQ"
        ],
        "min_chars": 2300,
        "tables": 1,
        "lang": "en",
        "cta": "Compare policy documents before applying"
    },
    "https://kfinance365.com": {
        "persona_en": "Korea Personal Finance editorial desk.",
        "scope": "Everyday banking, cards, remittance, credit and household finance for foreign residents in Korea",
        "tone": "Step-by-step consumer guidance using plain English and dated fees or limits.",
        "structure": [
            "Consumer situation",
            "Available options",
            "Fees and requirements",
            "Step-by-step process",
            "Common problems",
            "Official sources and checked date",
            "FAQ"
        ],
        "min_chars": 2300,
        "tables": 1,
        "lang": "en",
        "cta": "Continue to the next banking guide"
    },
    "https://koreataxnlaw.com": {
        "persona_en": "Korea Tax and Compliance editorial desk.",
        "scope": "Tax filing and basic legal compliance for foreign residents and foreign-owned small businesses in Korea",
        "tone": "Precise, cautious and source-led. Information only, never a substitute for professional advice.",
        "structure": [
            "Who is affected",
            "Rule and effective date",
            "Documents and deadlines",
            "Filing process",
            "Penalties and exceptions",
            "Official source links",
            "When to obtain professional advice"
        ],
        "min_chars": 2500,
        "tables": 1,
        "lang": "en",
        "cta": "Verify the current rule with the responsible authority"
    },
    "https://koreacrypto365.com": {
        "persona_en": "Korea Digital Asset Policy editorial desk.",
        "scope": "Korean crypto regulation, licensed exchanges, consumer protection and market-policy developments",
        "tone": "Neutral regulatory briefing. No trader persona, price prediction, hype or token promotion.",
        "structure": [
            "Policy development",
            "Who it affects",
            "Exchange and access rules",
            "Consumer risks",
            "What changed and when",
            "Primary sources",
            "FAQ"
        ],
        "min_chars": 2200,
        "tables": 1,
        "lang": "en",
        "cta": "Follow official regulatory updates"
    },
    "https://krealestate365.com": {
        "persona_en": "Korea Housing editorial desk.",
        "scope": "Jeonse, monthly rent and home purchase procedures for foreign residents in Korea",
        "tone": "Practical housing guide based on official transaction and tenancy information.",
        "structure": [
            "Housing situation",
            "Contract type",
            "Costs and deposits",
            "Verification checklist",
            "Signing and reporting steps",
            "Risk and dispute channels",
            "Official sources"
        ],
        "min_chars": 2400,
        "tables": 1,
        "lang": "en",
        "cta": "Use the contract-verification checklist"
    },
    "https://ktech365.com": {
        "persona_en": "Korea Technology Industry editorial desk.",
        "scope": "Korean semiconductors, AI infrastructure and technology-industry policy",
        "tone": "Concise technical explainer with specifications, primary announcements and explicit uncertainty.",
        "structure": [
            "What happened",
            "Technical context",
            "Korean organizations involved",
            "Evidence and specifications",
            "Industry implications",
            "What remains unknown",
            "Primary sources"
        ],
        "min_chars": 2200,
        "tables": 1,
        "lang": "en",
        "cta": "Read the related technology explainer"
    },
    "https://kskin365.com": {
        "persona_en": "Retired site.",
        "scope": "No new content",
        "tone": "No publication.",
        "structure": [],
        "min_chars": 0,
        "tables": 0,
        "lang": "en",
        "cta": ""
    },
    "https://oliveyoungkorea.com": {
        "persona_en": "Olive Young Shopping Guide editorial desk.",
        "scope": "Ingredient-led product selection, availability and shopping logistics at Olive Young for international shoppers",
        "tone": "Useful and upbeat but evidence-based. Never claim personal testing, results or sponsorship without records.",
        "structure": [
            "Shopping need",
            "Ingredient and product-type criteria",
            "Current availability and price-check method",
            "How to compare labels",
            "Who should avoid it",
            "Purchase logistics",
            "Sources and checked date"
        ],
        "min_chars": 2200,
        "tables": 1,
        "lang": "en",
        "cta": "Check the current label and store listing"
    },
    "https://kworld365.com": {
        "persona_en": "Korean Entertainment Brief editorial desk.",
        "scope": "Verified K-pop releases, charts, tours and agency announcements",
        "tone": "Fan-friendly but factual. Separate confirmed announcements from commentary and rumor.",
        "structure": [
            "Confirmed update",
            "Artist context",
            "Chart or release data",
            "Agency source",
            "What is confirmed",
            "What remains unconfirmed",
            "Next scheduled milestone"
        ],
        "min_chars": 1500,
        "max_chars": 2000,
        "tables": 0,
        "lang": "en",
        "cta": "See the related verified entertainment brief"
    },
    "https://k-trip365.com": {
        "persona_en": "Korea Independent Travel editorial desk.",
        "scope": "Public-transport-based Korea itineraries, admission logistics and seasonal travel planning",
        "tone": "Friendly and concrete without invented visits or personal experiences.",
        "structure": [
            "Who the route suits",
            "Transport route",
            "Timed itinerary",
            "Current costs and reservations",
            "Accessibility and seasonal cautions",
            "Official links and checked date"
        ],
        "min_chars": 2200,
        "tables": 1,
        "lang": "en",
        "cta": "Save the route checklist"
    },
    "https://k-visa365.com": {
        "persona_en": "Korea Immigration Procedure editorial desk.",
        "scope": "Official Korea visa eligibility, documents, application and status procedures",
        "tone": "Formal, document-first and explicit about rule dates and authority.",
        "structure": [
            "Visa purpose",
            "Eligibility",
            "Documents",
            "Application steps",
            "Fees and processing",
            "Rejection or change scenarios",
            "Official source and checked date"
        ],
        "min_chars": 2400,
        "tables": 1,
        "lang": "en",
        "cta": "Confirm the current requirement on HiKorea or the embassy"
    },
    "https://koreawedding365.com": {
        "persona_en": "Korea Wedding Planning editorial desk.",
        "scope": "Cross-cultural wedding registration, ceremony planning, budgets and marriage-visa document coordination in Korea",
        "tone": "Respectful and practical. No invented couples, planner career or guaranteed visa outcome.",
        "structure": [
            "Couple's planning situation without fabricated story",
            "Legal registration",
            "Ceremony options",
            "Budget framework",
            "Timeline",
            "Marriage-visa document handoff",
            "Official sources"
        ],
        "min_chars": 2300,
        "tables": 1,
        "lang": "en",
        "cta": "Use the wedding and document timeline"
    },
    "https://kstudy365.com": {
        "persona_en": "Korea University Admissions editorial desk.",
        "scope": "Degree admissions, eligibility, application schedules and scholarships at Korean universities",
        "tone": "Supportive but procedural, using university and government sources only.",
        "structure": [
            "Applicant profile",
            "Eligibility",
            "Application calendar",
            "Documents",
            "Tuition and scholarships",
            "Decision and enrollment",
            "Official sources"
        ],
        "min_chars": 2300,
        "tables": 1,
        "lang": "en",
        "cta": "Check the university's current admissions notice"
    },
    "https://studyinkorea365.com": {
        "persona_en": "International Student Life editorial desk.",
        "scope": "Practical student life after admission in Korea: housing, budgeting, campus services and daily administration",
        "tone": "Peer-friendly practical guidance without claiming personal student experience.",
        "structure": [
            "New-student situation",
            "First-month tasks",
            "Housing and budget",
            "Campus services",
            "Daily administration",
            "Problem-solving contacts",
            "Official sources"
        ],
        "min_chars": 2200,
        "tables": 1,
        "lang": "en",
        "cta": "Save the arrival checklist"
    },
    "https://kieca-korea.org": {
        "persona_ko": "KIECA 국제교육시장 편집 데스크.",
        "scope": "한국 대학을 위한 외국인 유학생 유치시장·국제교육 협력 동향",
        "tone": "공공성 중심의 정책·시장 보고서체. 확인되지 않은 협회 실적이나 개인 경력을 주장하지 않습니다.",
        "structure": [
            "시장 변화",
            "국가별 동향",
            "한국 대학에 미치는 영향",
            "운영 체크포인트",
            "공식 통계와 기준일",
            "향후 과제"
        ],
        "min_chars": 2300,
        "tables": 1,
        "lang": "ko",
        "cta": "관련 국제교육시장 보고서 보기"
    },
    "https://ksa-korea.org": {
        "persona_ko": "한국유학 준비정보 편집 데스크.",
        "scope": "해외 지원자를 위한 한국 유학 서류·일정·비자 준비",
        "tone": "친절한 절차 안내체. 협회 권위나 상담 실적을 과장하지 않습니다.",
        "structure": [
            "지원자 상황",
            "준비 일정",
            "필요 서류",
            "학교 지원",
            "비자 연결",
            "주의사항",
            "공식 출처"
        ],
        "min_chars": 2200,
        "tables": 1,
        "lang": "ko",
        "cta": "한국유학 준비 체크리스트 보기"
    },
    "https://sis-korea.com": {
        "persona_en": "Korea International Programs directory editorial desk.",
        "scope": "International schools and short-term academic programs in Korea",
        "tone": "Neutral directory and program-information style; never imply official school affiliation.",
        "structure": [
            "Program type",
            "Eligibility",
            "Curriculum or activities",
            "Dates and costs",
            "Application",
            "Accreditation checks",
            "Official program source"
        ],
        "min_chars": 2100,
        "tables": 1,
        "lang": "en",
        "cta": "Verify details with the program provider"
    },
    "https://jobkorea365.com": {
        "persona_en": "Korea Employment Rules editorial desk.",
        "scope": "Korean employment conditions, labor rules, salary data and workplace rights for foreign workers",
        "tone": "Practical rights-and-data explainer without invented HR credentials.",
        "structure": [
            "Worker situation",
            "Current labor rule",
            "Salary or hours data",
            "Rights and duties",
            "Problem resolution",
            "Official source and checked date",
            "FAQ"
        ],
        "min_chars": 2300,
        "tables": 1,
        "lang": "en",
        "cta": "Check the official labor guidance"
    },
    "https://jobinkorea365.com": {
        "persona_en": "Korea Job Search editorial desk.",
        "scope": "Job-search channels, applications, interviews and work-visa compatibility for foreign candidates",
        "tone": "Actionable job-search guide without invented placement stories or recruiter experience.",
        "structure": [
            "Candidate goal",
            "Visa compatibility checkpoint",
            "Where to search",
            "Application materials",
            "Interview process",
            "Scam warning",
            "Official resources"
        ],
        "min_chars": 2300,
        "tables": 1,
        "lang": "en",
        "cta": "Use the job-search checklist"
    },
    "https://jobkoreaglobal.com": {
        "persona_en": "Korea Global Hiring editorial desk.",
        "scope": "Employer-facing international recruitment, sponsorship workflow and onboarding compliance in Korea",
        "tone": "Formal employer operations guide; never present the site as a licensed recruiter unless verified.",
        "structure": [
            "Employer need",
            "Role and sponsorship fit",
            "Recruitment process",
            "Compliance",
            "Compensation framework",
            "Onboarding",
            "Official resources"
        ],
        "min_chars": 2300,
        "tables": 1,
        "lang": "en",
        "cta": "Verify recruiter and sponsorship requirements"
    },
    "https://korea365.org": {
        "persona_en": "Korea Newcomer Guide editorial desk.",
        "scope": "Essential public services, daily administration and cultural orientation for newcomers to Korea",
        "tone": "Neutral public-information style without claiming nonprofit or government status.",
        "structure": [
            "Newcomer task",
            "What is required",
            "Step-by-step",
            "Cost and timing",
            "Common obstacle",
            "Official service link",
            "Related next task"
        ],
        "min_chars": 2200,
        "tables": 1,
        "lang": "en",
        "cta": "Continue through the newcomer checklist"
    },
    "https://koreanews365.com": {
        "persona_ko": "Koreanews365 한국신문 편집국. 별도 계약 없이 활용 가능한 CC BY 뉴스와 공공·1차 자료를 모니터링하고, 복수 출처 확인과 독자적 해설을 더해 한국어 기사를 제작합니다.",
        "scope": "한국 독자를 위한 국내외 속보·정치·경제·사회 주요 뉴스. Global Voices·VOA의 이용 가능한 공개 피드와 정부·공공기관 원문을 취재 단서로 사용하며 주간 기사의 30% 이상은 자체 취재·독자 분석 기사로 구성",
        "tone": "한국 인터넷신문 기사체. 사실·타사 보도·편집국 분석을 명확히 구분하고 역피라미드 구조로 씁니다. 원문을 문장 단위로 치환하는 기사 세탁은 금지합니다.",
        "structure": [
            "제목과 리드: 새로 확인한 핵심 사실",
            "발생 시점·장소·주체",
            "복수 출처 대조",
            "공식 자료 또는 자체 분석",
            "독자에게 미치는 영향",
            "확인된 사실과 미확인 사항",
            "원문 출처 링크·작성 시각·수정 이력"
        ],
        "min_chars": 2000,
        "tables": 1,
        "lang": "ko",
        "cta": ""
    },
    "https://theseouljournal.com": {
        "persona_en": "The Seoul Journal English News Desk. It monitors no-contact CC BY feeds, eligible VOA material, and primary public records, then produces original English reporting, context and analysis.",
        "scope": "English-language world, business, technology, and Asia or Korea news built from Global Voices, eligible VOA leads, and primary government records. Source headlines are leads, never text to disguise or substitute.",
        "tone": "Professional English newspaper style. Distinguish sourced facts, direct quotations and newsroom analysis. Never imitate a source article paragraph by paragraph.",
        "structure": [
            "Original headline and concise lede",
            "What happened and when",
            "Facts confirmed across multiple sources",
            "Primary-source or official-record context",
            "Why it matters internationally and to Asia or Korea",
            "What remains unconfirmed",
            "Linked source note, publication time and correction record"
        ],
        "min_chars": 1500,
        "max_chars": 2000,
        "tables": 0,
        "lang": "en",
        "cta": ""
    }
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
    "파킨슨":"senior patient doctor consultation","치매":"senior patient doctor consultation",
    "뇌졸중":"senior patient doctor consultation","알츠하이머":"senior patient doctor consultation",
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

_IMAGE_QUERY_CACHE = {}

def ai_translate_keyword_for_image(keyword, theme=""):
    """KO_TO_EN_IMAGE 사전에 없는 키워드를 AI로 구체적인 영어 이미지 검색어(2~5단어)로 변환.
    사전 커버리지가 낮아(30여개) 대부분의 키워드가 테마 뭉뚱그림 폴백으로 빠지며
    (예: '홍삼 효능과 부작용' → 'medical health Korea doctor' 같은 무관한 사진) 발생하던
    이미지-본문 미스매치를 막기 위한 안전망."""
    cache_key = keyword.strip()
    if cache_key in _IMAGE_QUERY_CACHE:
        return _IMAGE_QUERY_CACHE[cache_key]
    try:
        prompt = (
            "Translate the following Korean blog topic into a short, CONCRETE English "
            "stock-photo search query (2-5 words, concrete nouns only, no explanation, "
            "no quotes, no punctuation).\n"
            "IMPORTANT: free stock-photo libraries (Pixabay/Pexels) do not have photos of "
            "specific disease symptoms, so never describe a symptom literally (e.g. NOT "
            "'tremor hands', NOT 'shaking hands') — a lone body-part word like 'hands' will "
            "match unrelated stock photos (e.g. handwashing) instead of anything medical. "
            "For any specific disease/symptom topic, describe a safe, genuinely photographable "
            "scene instead: a patient consulting a doctor, an elderly person in a clinic, a "
            "medical checkup — something a stock library actually has and that will still read "
            "as relevant next to the article.\n"
            f"Topic: {keyword}\n"
            f"Category: {theme}\n"
            "Query:"
        )
        text = generate_content_gemini(prompt)
        q = text.strip().strip('"').strip("'").split("\n")[0].strip()
        q = re.sub(r'^(Query|query)[:\s]*', '', q).strip()
        q = re.sub(r'[^A-Za-z0-9 \-]', '', q).strip()
        if q and not any('\uAC00' <= c <= '\uD7A3' for c in q):
            q = re.sub(r'\s+', ' ', q)[:80]
            _IMAGE_QUERY_CACHE[cache_key] = q
            return q
    except Exception as e:
        print(f"  ⚠️ 이미지 검색어 AI 번역 실패({keyword}): {e}")
    return None

def translate_ko_to_en_for_image(keyword, theme=""):
    result = keyword
    for ko, en in sorted(KO_TO_EN_IMAGE.items(), key=lambda x: -len(x[0])):
        result = result.replace(ko, en)
    if any('\uAC00' <= c <= '\uD7A3' for c in result):
        # 사전에 없는 키워드 → 테마로 뭉뚱그리기 전에 AI 번역으로 주제 특정성 유지 시도
        ai_q = ai_translate_keyword_for_image(keyword, theme)
        if ai_q:
            return ai_q
        return THEME_IMAGE_FALLBACK.get(theme, THEME_IMAGE_FALLBACK["default"])
    return re.sub(r'\s+', ' ', result).strip()[:80]

SITES_CONFIG = [
    # 2026-08-17: 폭탄발행(7월 74건) 이후 회복 위해 이틀에 1건으로 감속(사용자 지시).
    # publish_every_n_days가 있으면 get_slot_posts()가 이 주기를 지켜서 격일에만 1건 반환.
    {"url":"https://k-health365.com",       "lang":"ko","theme":"건강과 의학",         "mode":"health_blog","keywords_file":"data/keywords/keywords_khealth.txt",        "wp_pass_env":"KHEALTH365COM",        "daily":1,"publish_every_n_days":1},
    {"url":"https://koreamedicaltour.com",   "lang":"en","theme":"Korea Medical Tourism","mode":"blog",      "keywords_file":"data/keywords/keywords_medicaltour.txt",    "wp_pass_env":"KOREAMEDICALTOURCOM",  "daily":1,"publish_every_n_days":1},
    {"url":"https://koreainvest365.com",     "lang":"en","theme":"Investment",           "mode":"blog",      "keywords_file":"data/keywords/keywords_kinvest.txt",        "wp_pass_env":"KOREAINVEST365COM",    "daily":1,"publish_every_n_days":1},
    {"url":"https://ki-korea.com",           "lang":"en","theme":"Korea Investment",     "mode":"blog",      "keywords_file":"data/keywords/keywords_kikorea.txt",        "wp_pass_env":"KIKOREACOM",           "daily":1,"publish_every_n_days":1},
    {"url":"https://koreainsurance365.com",  "lang":"en","theme":"Insurance",            "mode":"blog",      "keywords_file":"data/keywords/keywords_kinsurance.txt",     "wp_pass_env":"KOREAINSURANCE365COM", "daily":1,"publish_every_n_days":1},
    {"url":"https://kfinance365.com",        "lang":"en","theme":"Finance",              "mode":"blog",      "keywords_file":"data/keywords/keywords_kfinance.txt",       "wp_pass_env":"KFINANCE365COM",       "daily":1,"publish_every_n_days":1},
    {"url":"https://koreataxnlaw.com",       "lang":"en","theme":"Tax and Law",          "mode":"blog",      "keywords_file":"data/keywords/keywords_ktax.txt",           "wp_pass_env":"KOREATAXNLAWCOM",      "daily":1,"publish_every_n_days":1},
    {"url":"https://koreacrypto365.com",     "lang":"en","theme":"Crypto",               "mode":"blog",      "keywords_file":"data/keywords/keywords_kcrypto.txt",        "wp_pass_env":"KOREACRYPTO365COM",    "daily":1,"publish_every_n_days":1},
    {"url":"https://krealestate365.com",     "lang":"en","theme":"Korea Real Estate",    "mode":"blog",      "keywords_file":"data/keywords/keywords_krealestate.txt",    "wp_pass_env":"KREALESTATE365COM",    "daily":1,"publish_every_n_days":1},
    {"url":"https://ktech365.com",           "lang":"en","theme":"Technology",           "mode":"blog",      "keywords_file":"data/keywords/keywords_ktech.txt",          "wp_pass_env":"KTECH365COM",          "daily":1,"publish_every_n_days":1},
    {"url":"https://kskin365.com",           "lang":"en","theme":"K-Beauty",             "mode":"blog",      "keywords_file":"data/keywords/keywords_kskin.txt",          "wp_pass_env":"KSKIN365COM",          "daily":1,"publish_every_n_days":1},
    {"url":"https://oliveyoungkorea.com",    "lang":"en","theme":"K-Beauty Reviews",     "mode":"blog",      "keywords_file":"data/keywords/keywords_oliveyoung.txt",     "wp_pass_env":"OLIVEYOUNGKOREACOM",   "daily":1,"publish_every_n_days":1},
    {"url":"https://kworld365.com",          "lang":"en","theme":"K-POP",               "mode":"blog",      "keywords_file":"data/keywords/keywords_kworld.txt",         "wp_pass_env":"KWORLD365COM",         "daily":1,"publish_every_n_days":1},
    {"url":"https://k-trip365.com",          "lang":"en","theme":"Travel",              "mode":"blog",      "keywords_file":"data/keywords/keywords_ktrip.txt",          "wp_pass_env":"KTRIP365COM",          "daily":1,"publish_every_n_days":1},
    {"url":"https://k-visa365.com",          "lang":"en","theme":"Visa Guide",          "mode":"blog",      "keywords_file":"data/keywords/keywords_kvisa.txt",          "wp_pass_env":"KVISA365COM",          "daily":1,"publish_every_n_days":1},
    {"url":"https://koreawedding365.com",    "lang":"en","theme":"Wedding",             "mode":"blog",      "keywords_file":"data/keywords/keywords_kwedding.txt",       "wp_pass_env":"KOREAWEDDING365COM",   "daily":1,"publish_every_n_days":1},
    {"url":"https://kstudy365.com",          "lang":"en","theme":"Study in Korea",      "mode":"blog",      "keywords_file":"data/keywords/keywords_kstudy365.txt",      "wp_pass_env":"KSTUDY365COM",         "daily":1,"publish_every_n_days":1},
    {"url":"https://studyinkorea365.com",    "lang":"en","theme":"International Students","mode":"blog",    "keywords_file":"data/keywords/keywords_studyinkorea365.txt","wp_pass_env":"STUDYINKOREA365COM",   "daily":1,"publish_every_n_days":1},
    {"url":"https://kieca-korea.org",        "lang":"ko","theme":"국제교육문화",          "mode":"blog",      "keywords_file":"data/keywords/keywords_kieca.txt",          "wp_pass_env":"KIECAKOREAORG",        "daily":1,"publish_every_n_days":1},
    {"url":"https://ksa-korea.org",          "lang":"ko","theme":"한국유학정보",          "mode":"blog",      "keywords_file":"data/keywords/keywords_ksaKorea.txt",       "wp_pass_env":"KSAKOREAORG",          "daily":1,"publish_every_n_days":1},
    {"url":"https://sis-korea.com",          "lang":"en","theme":"Korea Career Programs","mode":"blog",     "keywords_file":"data/keywords/keywords_sisKorea.txt",       "wp_pass_env":"SISKOREACOM",          "daily":1,"publish_every_n_days":1},
    {"url":"https://jobkorea365.com",        "lang":"en","theme":"Employment",          "mode":"blog",      "keywords_file":"data/keywords/keywords_jobkorea365.txt",    "wp_pass_env":"JOBKOREA365COM",       "daily":1,"publish_every_n_days":1},
    {"url":"https://jobinkorea365.com",      "lang":"en","theme":"Jobs in Korea",       "mode":"blog",      "keywords_file":"data/keywords/keywords_jobinkorea365.txt",  "wp_pass_env":"JOBINKOREA365COM",     "daily":1,"publish_every_n_days":1},
    {"url":"https://jobkoreaglobal.com",     "lang":"en","theme":"Recruitment",         "mode":"blog",      "keywords_file":"data/keywords/keywords_jobkoreaglobal.txt", "wp_pass_env":"JOBKOREAGLOBALCOM",    "daily":1,"publish_every_n_days":1},
    {"url":"https://korea365.org",           "lang":"en","theme":"Korea Culture",       "mode":"blog",      "keywords_file":"data/keywords/keywords_korea365.txt",       "wp_pass_env":"KOREA365ORG",          "daily":1,"publish_every_n_days":1},
    {"url":"https://koreanews365.com",       "lang":"ko","theme":"한국 뉴스",            "mode":"news",      "keywords_file":"data/keywords/keywords_koreanews.txt",      "wp_pass_env":"KOREANEWS365COM",      "daily":1,"publish_every_n_days":1},
    {"url":"https://theseouljournal.com",    "lang":"en","theme":"Seoul Lifestyle",     "mode":"news_en",   "keywords_file":"data/keywords/keywords_seouljournal.txt",   "wp_pass_env":"THESEOULJOURNALCOM",   "daily":1,"publish_every_n_days":1},
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
# ★★★ 실제 글 기반 "관련 글" 블록 — 코드가 직접 삽입 (AI 지시에 의존하지 않음) ★★★
# GSC에서 내부링크 669개가 전부 홈페이지로만 잡힌 원인:
#   1) 기존 SITE_INTERNAL_LINKS가 실제 글이 아닌 "?s=검색어" 검색결과 URL이었음
#   2) 프롬프트로 AI에게 "자연스럽게 삽입해줘" 요청만 했을 뿐 강제되지 않았음
# → 발행 직전 코드가 WP REST API로 실제 최근 글 목록을 가져와
#   진짜 permalink로 "관련 글" 박스를 무조건 본문 끝에 삽입한다.
# ============================================================
_wp_posts_cache: dict = {}

def fetch_recent_wp_posts(site_url, wp_pass, count=30):
    """실제 발행된 글의 (제목, permalink) 목록을 가져와 캐싱."""
    if site_url in _wp_posts_cache: return _wp_posts_cache[site_url]
    posts = []
    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, wp_pass),
                         params={"per_page": count, "orderby":"date", "order":"desc",
                                 "_fields":"title,link", "status":"publish"}, timeout=12)
        if r.status_code == 200:
            for p in r.json():
                raw = p.get("title", {})
                t = raw.get("rendered", "") if isinstance(raw, dict) else str(raw)
                t = re.sub(r'<[^>]+>', '', t).strip()
                link = p.get("link", "")
                if t and link:
                    posts.append((t, link))
    except: pass
    _wp_posts_cache[site_url] = posts
    return posts

def build_related_links_html(site_url, wp_pass, lang, exclude_title=""):
    """
    같은 사이트의 실제 글 2~3개(무작위) + (30% 확률로) 클러스터 내
    형제 사이트 1개를 '관련 글' 박스로 만들어 반환. 전부 실제 permalink.
    """
    posts = fetch_recent_wp_posts(site_url, wp_pass, count=30)
    posts = [p for p in posts if p[0].strip().lower() != exclude_title.strip().lower()]
    if not posts:
        return ""  # 그 사이트 첫 글이면 관련글 없음 — 자연스러운 상태

    own_sel = random.sample(posts, min(3, len(posts)))
    heading = "관련 글" if lang == "ko" else "Related Articles"
    items = "".join(f'<li><a href="{link}">{title}</a></li>' for title, link in own_sel)

    # 사이트 간 링크는 매번 넣지 않고 ~30%만 (기계적 패턴 방지, 클러스터 내부만)
    if random.random() < 0.3:
        cross = CROSS_LINKS.get(site_url, [])
        if cross:
            cname, curl = random.choice(cross)
            items += f'<li><a href="{curl}">{cname}</a></li>'

    return (f'<div class="related-links" style="margin:32px 0;padding:20px;'
            f'background:#f7f9fb;border-radius:10px;">'
            f'<h3 style="margin-top:0;">{heading}</h3>'
            f'<ul style="margin:0;padding-left:20px;">{items}</ul></div>')

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

def _title_dup_key(t):
    # 완전히 똑같은 제목만 잡던 걸 앞 20자 기준 fuzzy 매칭으로 강화
    # (2026-08-03: 중복 제목 125건이 대부분 살짝 다른 표현이라 exact match로는 못 잡았음)
    return re.sub(r'\s+', '', t[:20].lower())

def fetch_recent_wp_titles(site_url, wp_pass, count=None):
    if site_url in _wp_title_cache: return _wp_title_cache[site_url]
    titles = set()
    try:
        page = 1
        while True:
            r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, wp_pass),
                             params={"per_page": 100, "page": page, "orderby":"date","order":"desc",
                                     "_fields":"title,content","status":"publish"}, timeout=15)
            if r.status_code != 200: break
            batch = r.json()
            if not isinstance(batch, list) or not batch: break
            for p in batch:
                raw = p.get("title",{})
                t = raw.get("rendered","") if isinstance(raw,dict) else str(raw)
                t = re.sub(r'<[^>]+>','',t).strip().lower()
                if t:
                    titles.add(t)
                    titles.add(_title_dup_key(t))
                content = p.get("content", {}).get("rendered", "") if isinstance(p.get("content"), dict) else ""
                for href in re.findall(r'href=["\'](https?://[^"\']+)', content, re.IGNORECASE):
                    titles.add("source:" + href.split("#", 1)[0].rstrip("/"))
            if len(batch) < 100: break
            page += 1
    except: pass
    _wp_title_cache[site_url] = titles
    return titles

def crawl_rss_news(lang="ko", site_url=""):
    used = _used_news_ko if lang=="ko" else _used_news_en
    cache = _wp_title_cache.get(site_url, set())
    fallback = NEWS_KO_FALLBACK if lang=="ko" else NEWS_EN_FALLBACK

    def is_dup(t): return t.strip().lower() in used or t.strip().lower() in cache

    # Only no-contact CC/public/primary feeds from news_source_registry are eligible.
    sources = get_enabled_rss_sources(lang)
    if not sources:
        print(f"   NEWS SOURCE GATE: no rights-cleared RSS source for lang={lang}")
        return "", "", None, ""
    random.shuffle(sources)
    candidates = []
    for src, url in sources:
        try:
            res = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"})
            soup = BeautifulSoup(res.text, 'xml')
            for it in soup.find_all('item'):
                t = re.sub(r'<[^>]+>','', it.title.text.strip() if it.title else "")
                d = re.sub(r'<[^>]+>','', it.description.text.strip() if it.description else "")
                link = it.link.text.strip() if it.link else ""
                raw_date = (it.pubDate.text.strip() if it.pubDate else "") or (it.find("dc:date").text.strip() if it.find("dc:date") else "")
                recent = True
                if raw_date:
                    try:
                        published = parsedate_to_datetime(raw_date) if "," in raw_date else datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                        if published.tzinfo is None: published = published.replace(tzinfo=timezone.utc)
                        recent = datetime.now(timezone.utc) - published.astimezone(timezone.utc) <= timedelta(hours=72)
                    except Exception:
                        recent = False
                source_key = "source:" + link.split("#", 1)[0].rstrip("/") if link else ""
                if t and len(t)>=5 and recent and not is_dup(t) and (not source_key or source_key not in cache):
                    candidates.append((t, d, src, link))
        except: pass

    if candidates:
        ch = random.choice(candidates)
        used.add(ch[0].strip().lower())
        print(f"   📰 RSS: {ch[2]} — {ch[0][:40]}")
        return ch

    print(f"   NEWS SOURCE GATE: no eligible story published within 72 hours for lang={lang}")
    return "", "", None, ""

# ============================================================
# ★ 구성표 숫자 랜덤화 — "FAQ 5문항"처럼 매번 똑같은 개수로 고정돼 있으면
#   그 자체가 AI/자동화 패턴으로 읽힌다(사용자 피드백, 2026-08-19). 범위 표현
#   ("3~5가지")은 이미 매번 달라질 여지가 있으니 건드리지 않고, 단일 고정
#   숫자("5문항","4 questions","3가지")만 원래 값 근처(±2)에서 다시 뽑는다.
# ============================================================
_STRUCT_COUNT_RE = re.compile(r'(?<![~\-\d])(\d+)(\s*(?:가지|개|문항|questions|reasons|tips|ways))\b')

def randomize_structure_counts(structure):
    def repl(m):
        orig = int(m.group(1))
        suffix = m.group(2)
        lo, hi = max(2, orig - 2), orig + 2
        return f"{random.randint(lo, hi)}{suffix}"
    return [_STRUCT_COUNT_RE.sub(repl, item) for item in structure]

# ============================================================
# ★★★ make_site_prompt — 사이트별 완전 분리 프롬프트 ★★★
# ============================================================
def make_site_prompt(keyword, site, reporter, tag_count=None):
    url   = site["url"]
    theme = site["theme"]
    lang  = site["lang"]
    mode  = site.get("mode","blog")
    tag_count = tag_count or TAG_COUNT

    p = SITE_PERSONA.get(url, {})
    min_chars  = p.get("min_chars", 2200)
    tables_req = p.get("tables", 1)
    structure  = randomize_structure_counts(p.get("structure", []))
    scope      = p.get("scope", theme)

    if lang == "ko":
        persona = p.get("persona_ko","전문 칼럼니스트")
        tone    = p.get("tone","전문적이고 친근한 스타일")
    else:
        persona = p.get("persona_en","Expert writer")
        tone    = p.get("tone","Professional and engaging")

    ext   = get_authority_links(theme)
    ext_s = random.sample(ext, min(3, len(ext)))
    ext_h = ", ".join(f"{n}({u})" for n,u in ext_s)

    ilinks = get_internal_links(url, count=4)
    il_str = "\n".join(f'  - <a href="{u}" title="{n}">{n}</a>' for n,u in ilinks)

    struct_str = "\n".join(f"  {i+1}. {s}" for i,s in enumerate(structure))

    medical_note = ""
    if lang=="ko" and ("건강" in theme or "의학" in theme):
        medical_note = '\n- ⚠️ "위험 신호 / 병원 가야 할 때" 섹션 필수\n- "이 글은 의학적 참고 정보이며, 진단·치료는 반드시 전문의와 상담하세요." 문구 필수'

    # 참고: 제목(TITLE)과 바이라인은 AI 출력에 의존하지 않고 코드가 별도로 확정 생성/삽입한다
    # (반복 패턴·형식 오류 방지). 그래서 프롬프트에서 관련 지시를 넣지 않아 토큰도 절약한다.

    # ★ 뉴스모드(news/news_en)는 keyword가 RSS 헤드라인 "문장 전체"라서, 블로그용
    #   "keyword를 첫 문장에 포함 + 10회 반복" / "TAGS 첫번째=keyword" 지시를 그대로 쓰면
    #   헤드라인이 본문 첫 문장·태그에 통째로 복붙되는 문제가 생긴다(제보로 확인됨).
    #   뉴스모드는 별도 지시문을 쓴다.
    is_news = mode in ("news", "news_en")
    news_integrity_note = ""
    if is_news:
        news_integrity_note = (
            "\n- NEWSROOM RULE: use the source headline only as a reporting lead. Do not copy, translate, spin, or paraphrase the source article paragraph by paragraph. Build the article from independently verified facts, primary records, and at least one additional source. Keep direct quotations short, exact, attributed, and necessary. Never bypass a paywall. Clearly label analysis and unresolved claims."
            if lang != "ko" else
            "\n- 편집국 규칙: 타사 헤드라인은 취재 단서로만 사용합니다. 원문 기사를 문단별로 복사·번역·단어 치환·재서술하지 않습니다. 공식 원문과 최소 1개의 추가 출처로 사실을 독립 확인하고, 직접 인용은 짧고 정확하게 출처를 표시합니다. 유료벽을 우회하지 않으며 분석과 미확인 주장을 명확히 구분합니다."
        )
        if lang == "ko":
            return f"""[한국신문 뉴스룸 전용]\n역할: {persona}\n취재 단서: {keyword}\n편집 범위: {scope}\n
- HTML은 p, h2, blockquote, ul, li만 사용한다.
- 본문은 공백 제외 1,500~2,000자이며 2,000자를 절대 넘기지 않는다.
- 역피라미드 구조: 핵심 사실 리드, 확인된 경위, 배경·맥락, 영향, 미확인 사항.
- 첫 문단은 2~3문장, 각 문단은 1~3문장으로 짧게 쓴다. 소제목은 최대 2개다.
- 표, FAQ, 체크리스트, 상담 CTA, 결론 요약을 쓰지 않는다.
- '알아보겠습니다·추천·꿀팁·총정리·도움이 되셨다면' 같은 블로그 표현과 독자 질문을 금지한다.
- 간결한 신문 기사체를 사용하고 과장, 감탄, 지어낸 인용·수치·인명·날짜·반응을 금지한다.
- RSS 원문을 문단별로 번역·치환·재서술하지 않는다. 과거 연도와 수치를 현재 값으로 바꾸지 않는다.
- 정보가 부족하면 억지로 늘리지 말고 확인된 범위의 짧은 기사로 쓴다.
- 끝에 META_DESC: 100~140자와 TAGS: 짧은 명사 6~10개를 쓴다. FAQ와 TITLE은 출력하지 않는다."""
        return f"""[THE SEOUL JOURNAL NEWSROOM ONLY]\nRole: {persona}\nReporting lead: {keyword}\nEditorial scope: {scope}\n
- Use only p, h2, blockquote, ul and li HTML tags.
- Body length is 1,500–2,000 characters excluding spaces; never exceed 2,000.
- Use an inverted pyramid: concise lede, verified developments, context, significance, unresolved facts.
- Write a 2–3 sentence lede and 1–3 sentence paragraphs. Use no more than two subheads.
- No tables, FAQ, checklist, CTA or summary conclusion.
- Ban blog language such as 'in this article', 'let's explore', 'tips', 'ultimate guide' and reader questions.
- Use restrained newspaper prose. Never invent quotes, figures, dates, witnesses or reactions.
- Do not translate, spin or paraphrase a source article paragraph by paragraph. Preserve historical dates exactly.
- If facts are thin, write a shorter verified brief instead of padding.
- End with META_DESC: 120–155 characters and TAGS: 6–10 short nouns. Do not output FAQ or TITLE."""

    if lang == "ko":
        keyword_rule = ("- 사건 소개: 이 헤드라인이 다루는 사건을 첫 문장에서 소개하되, "
                         "헤드라인 문장을 그대로 반복하지 말고 다른 표현으로 풀어서 쓸 것. "
                         "본문 전체에서 사건의 핵심 인물/기관/장소명을 자연스럽게 반복 언급"
                         if is_news else
                         f"- 키워드: '{keyword}'를 첫 문장에 자연스럽게 포함. 이후엔 억지로 "
                         f"반복 횟수를 채우지 말고, 대명사/유의어/줄인 표현으로 자연스럽게 바꿔써도 됨 "
                         f"(같은 단어를 기계적으로 반복하면 검색엔진이 스팸으로 판단할 수 있음)")
        tags_line = (f"TAGS: ({tag_count}개 한국어, 쉼표로 구분된 짧은 명사/키워드만. "
                     "문장·특수기호·구분선 금지)"
                     if is_news else
                     f"TAGS: ({tag_count}개 한국어, 첫번째='{keyword}')")
    else:
        keyword_rule = ("- Intro: introduce the event this headline covers in the first sentence, "
                         "in your own words — do not repeat the headline sentence verbatim. "
                         "Naturally repeat the key people/organizations/places involved throughout"
                         if is_news else
                         f"- Keyword: include '{keyword}' naturally in the first sentence. After that, "
                         f"don't force a repetition count — use pronouns, synonyms, or shortened phrasing "
                         f"instead (mechanically repeating the exact same phrase reads as spam to both "
                         f"readers and search engines)")
        tags_line = (f"TAGS: ({tag_count} English tags, comma-separated short nouns/keywords only. "
                     "No full sentences, symbols, or section dividers)"
                     if is_news else
                     f"TAGS: ({tag_count} English tags, first='{keyword}')")

    if lang == "ko":
        return f"""[역할]
너는 {persona}야. 톤앤매너는 '{tone}'로, {url} 사이트의 '{theme}' 카테고리 독자를 대상으로 글을 쓴다.

[지식/자료]
- 이 사이트의 단일 편집 범위(절대 이탈 금지): '{scope}'\n- 위 범위 안에서 다룰 주제: '{keyword}'
- 권위 있는 인용 출처(정부기관/대학교만 사용): {ext_h}
- 본문에 자연스럽게 녹여 넣을 내부링크 4개:
{il_str}

[제약 — 반드시 지킬 것]
- 형식: HTML 태그만 사용(h2,h3,p,ul,li,ol,strong,table,blockquote). 마크다운 절대 금지
- 분량: 최소 {min_chars}자 이상(공백 제외)
- 문장: 모든 <p>는 2문장 이하로 짧고 간결하게. 단락 사이 줄바꿈 필수
- 문체(글 전체에 적용 — 도입부만이 아니라 소제목·본문·마무리 전부): 질문을 던지기보다
  현상을 짚어주는 담담한 존댓말, 전문 기자가 리포트를 쓰듯 신뢰감 있고 객관적인 태도.
  불필요한 수식어를 걷어내고 정보의 본질에 집중해서 서술.
- 물음표 사용 금지: 본문 어디에도(소제목 포함) "~인가요?/~일까요?/~하시나요?/~해보셨나요?" 같은
  의문문을 쓰지 말 것. FAQ_START~FAQ_END 섹션의 질문(Q:)에만 예외적으로 허용.
  h2/h3 소제목은 반드시 명사구나 평서문으로 쓸 것 (예: "왜 중요할까요?" 금지 → "~의 역할"로 대체)
  느낌표는 전체 글에서 1개 이하.
- 절대 쓰지 말 것 — "이것 몰랐죠?/알고 계셨나요?" 류 충격 유도, "충격적인 사실/~%나 된다는 사실"
  같은 통계 충격요법, "오늘은 ~에 대해 함께 알아보겠습니다/알아보아요" 같은 글 소개용 메타 문장,
  "우리 몸은 정말 신비롭죠" 류의 막연한 감탄 필러, "이 글을 통해 궁금증을 모두 해소하시길
  바랍니다" 같은 마무리성 문장을 서론에 두는 것, "현대 사회에서/현대인들에게" 같은 거창한 서두,
  "그 중요성이 점점 커지고 있습니다" 같은 상투구, "~에 좋아요/추천합니다"처럼 근거 없이
  주관적으로 끝내는 문장, "~임/~함"체 문어체.
- 도입부 구성 순서: 현상 진단 → 배경 설명 → 이 글에서 다룰 방향 제시.
  예시(이렇게 고쳐 쓸 것):
    (금지) "전기세, 조금만 신경 써도 눈에 띄게 줄일 수 있다는 사실, 알고 계셨나요?"
    (사용) "가전제품을 효율적으로 관리하는 것만으로도 불필요하게 낭비되는 전력을 상당 부분 줄일 수 있습니다."
    (금지) "역류성 식도염, 그냥 속 쓰린 거라고 넘기면 안 되는 이유가 있습니다."
    (사용) "역류성 식도염을 단순한 속 쓰림으로 여겨 방치하면 더 큰 질환으로 이어질 위험이 있습니다."
    (금지 소제목) "내 몸의 든든한 방패, 셀레늄! 왜 중요할까요?"
    (사용 소제목) "셀레늄의 역할과 항산화 작용"
  마무리는 "오늘부터 시작해 보세요" 식 강요 대신 "작은 변화가 큰 결과로 이어질 수 있습니다"처럼
  담백하게 격려하는 정도로.
- 전문용어: 등장할 때마다 괄호로 쉽게 풀어서 설명할 것
{keyword_rule}{news_integrity_note}
- 통계/출처: 실제로 근거 있는 수치나 기관명을 알고 있을 때만 "(KOSIS, 2026)" 같은 형식으로
  자연스럽게 인용. 억지로 개수를 채우려고 애매하거나 지어낸 수치를 넣지 말 것 —
  근거 없는 통계보다 통계가 아예 없는 게 낫다.
- 연도: 본문에 2024·2025·2023 등 과거 연도 절대 금지. 연도가 필요하면 반드시 2026만 사용, 확실하지 않으면 연도 자체를 생략
- 표: 실제로 항목을 비교/정리하는 게 독자에게 유용한 주제일 때는 <table>을 쓸 것
  (thead/tbody/tr/th/td 완전 구조). 이 글의 주제라면 대부분 비교표(원인별/유형별/
  단계별/전후 비교 등)를 최소 1개는 자연스럽게 만들 수 있다 — 정말 표로 정리할
  항목이 하나도 없는 극히 예외적인 경우만 생략하고, 그럴 때도 <table> 대신 잘
  구조화된 <ul> 목록으로 핵심 정보를 정리할 것(구조 없이 문단으로만 끝내지 말 것).
- META_DESC 글자수는 타협 불가 항목이다 — 반드시 130~140자(공백 포함) 사이여야
  하며, 120자 미만이거나 150자를 넘으면 실패로 간주된다. 짧게 쓰고 끝내지 말고
  '{keyword}' 관련 구체적인 이유/이점을 한 문장 더 보태서라도 130자를 채울 것.
- 위 내부링크 4개를 본문 흐름에 자연스럽게 삽입{medical_note}
- FAQ는 본문(본문HTML) 안에 절대 작성하지 말 것. 아래 구성표에 "FAQ"가 언급되어 있어도
  그건 이 글에 FAQ가 필요하다는 표시일 뿐, 실제 질문·답변은 반드시 FAQ_START~FAQ_END
  섹션에서만 작성한다. 본문에 "자주 묻는 질문"이나 "FAQ" 같은 소제목, Q&A 형식을
  직접 쓰면 발행 시 시스템이 추가하는 FAQ 박스와 겹쳐서 같은 내용이 두 번 노출된다.

[이 사이트 전용 글 구성 — 반드시 이 순서로. 목록의 "FAQ"는 본문이 아니라
FAQ_START~FAQ_END에서 작성하라는 뜻]
{struct_str}

[출력 형식]
본문HTML → META_DESC: (정확히 130~140자, '{keyword}' 포함) → FAQ_START~FAQ_END (Q:/A: 형식) → {tags_line}
(TITLE 줄은 쓰지 않아도 된다 — 제목은 별도 시스템이 생성한다)"""

    else:
        return f"""[ROLE]
You are {persona}. Write in a '{tone}' tone for readers of the '{theme}' category on {url}.

[KNOWLEDGE / SOURCES]
- Single-site editorial scope (never leave this subject): '{scope}'\n- Topic to cover within that scope: '{keyword}'
- Authoritative sources to cite (Korean gov/university only): {ext_h}
- 4 internal links to weave naturally into the body:
{il_str}

[CONSTRAINTS — must follow]
- Format: HTML tags only (h2,h3,p,ul,li,ol,strong,table,blockquote). No markdown whatsoever
- Length: minimum {min_chars} characters
- Sentences: every <p> max 2 sentences, short and concise. Clear paragraph breaks between sections
- Opening: start with a concrete fact or situation related to the topic, stated plainly.
  Never use — rhetorical questions ("Have you ever wondered...?", "Did you know...?",
  "What if I told you..."), especially chained back-to-back; shock-stat openers
  ("a staggering X%", "surprisingly, X% of..."); throat-clearing meta-sentences about
  the article itself ("In this article, we'll explore...", "Today, let's dive into...");
  vague filler sentences ("Navigating the complexities of X can seem daunting, yet...",
  "In today's fast-paced world...", "its importance is only growing"); or wrap-up-style sentences placed in the intro
  ("By the end of this article, you'll..."). Max 1 exclamation point in the whole piece.
- Opening structure: diagnose the situation → give context → state what this piece covers
  (never lead with a question). Rewrite like this:
    (banned) "Have you ever wondered how much you could save by managing your appliances better?"
    (use) "Managing household appliances more efficiently can meaningfully cut wasted electricity."
    (banned) "Acid reflux — just some heartburn, right? Actually, there's a reason not to ignore it."
    (use) "Dismissing acid reflux as ordinary heartburn can let it develop into a more serious condition."
  Keep the overall voice closer to a calm, factual news reporter than a hype blogger.
- Jargon: explain any technical term in parentheses when first used
{keyword_rule}
- Statistics/citations: only cite a figure or source (e.g. "(OECD, 2026)") when you actually
  have something grounded to reference. Don't pad the piece with vague or invented numbers just
  to hit a count — no statistic beats a fabricated one.
- Years: never write 2024, 2025, 2023, or any past year anywhere in the body. If a year is needed, use ONLY 2026 — if unsure, omit the year entirely
- Tables: use a <table> (full thead/tbody/tr/th/td structure) whenever the topic can support
  a side-by-side comparison (by type/stage/option/before-after/cost, etc.) — most topics here
  can. Only skip it in the rare case there's truly nothing to compare, and even then replace it
  with a well-structured <ul> summarizing the key points (never end a section with plain
  paragraphs only when a list or table would organize it better).
- META_DESC length is non-negotiable — it must be 130-155 characters, not shorter. If your first
  draft is short, add one more concrete reason/benefit related to '{keyword}' rather than
  stopping early.
- Weave the 4 internal links above naturally into the body{medical_note}
- Never write the FAQ inside the article body itself. If the structure list below mentions
  "FAQ", that only marks that this article needs one — the actual questions/answers belong
  exclusively in the FAQ_START~FAQ_END section. Writing an "FAQ" or "Frequently Asked
  Questions" heading with Q&A pairs directly in the body will duplicate the FAQ box the
  system appends automatically at publish time.

[THIS SITE'S UNIQUE STRUCTURE — follow exactly in order. Where the list says "FAQ", that
belongs in FAQ_START~FAQ_END, not the body]
{struct_str}

[OUTPUT FORMAT — write ONLY these parts, back to back, with nothing else]
1. The article body itself, written directly in HTML tags (do not write the words "body" or "HTML" anywhere as a label/header — just start straight in with the first <h2> or <p>)
2. Then the line: META_DESC: (exactly 130~155 English chars, include '{keyword}')
3. Then FAQ_START ~ FAQ_END (Q:/A: format)
4. Then {tags_line}
Do not write a TITLE line (a separate system generates the title). Do not restate or reference these instructions anywhere in your answer — output only the final content."""

# ============================================================
# ★ 유틸리티
# ============================================================
def generate_content_gemini(prompt):
    # 2026-08-17: OPENAI_API_KEY가 있으면 ChatGPT로 라우팅 — 27개 사이트 글쓰기
    # 엔진 "대수술" 결정. 이미지(Pixabay/Pexels)는 그대로 유지, 텍스트만 교체.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from openai_text import openai_available, openai_generate_text
        if openai_available():
            return openai_generate_text(prompt, temperature=0.85, max_retries=3)
    except ImportError:
        pass

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

def strip_code_fences(text):
    """Gemini가 가끔 응답을 ```html ... ``` 코드블록으로 감싸서 반환하는 경우,
    발행 전 이를 제거한다 (그대로 두면 본문 맨 위에 '```html' 텍스트가 그대로 노출됨)."""
    t = text.strip()
    t = re.sub(r'^```[a-zA-Z]*\s*\n', '', t)
    t = re.sub(r'\n```\s*$', '', t)
    t = t.strip()
    t = "\n".join(l for l in t.split("\n") if l.strip() not in ("```", "```html", "```HTML"))
    return t

def extract_meta_and_faq(text):
    text = strip_code_fences(text)
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

# ============================================================
# ★★★ 제목 다양화 — AI에게 "부탁"하지 않고 코드가 직접 22개 템플릿 중 랜덤 선택 ★★★
# 문제: 기존엔 프롬프트로 "패턴 7개 중 골라서 절대 반복하지 마라"고 지시만 했는데,
#      AI가 실제로는 "How to Actually X: A Specialist's Guide" 류로 계속 수렴함
#      → 반복 패턴은 구글이 "찍어낸 AI 콘텐츠"로 인식해 색인에 불리
# 해결: AI 지시에 의존하지 않고, 코드가 22개 템플릿 중 매번 진짜 랜덤으로 뽑아
#      키워드만 채워 넣는 방식으로 강제 (내부링크 수정과 동일한 원칙)
# ============================================================
TITLE_TEMPLATES_KO = [
    "{keyword}, 이것부터 확인하세요",
    "{keyword} 관리, 이 {n}가지만 지켜도 달라집니다",
    "{keyword}에 대해 알아두면 좋은 것들",
    "{keyword}, 어디서부터 시작해야 할까",
    "{keyword} 제대로 준비하는 법",
    "놓치기 쉬운 {keyword} 체크포인트",
    "{keyword}, 실제로는 이렇게 진행됩니다",
    "{keyword} 하기 전에 알아두면 좋은 것들",
    "{keyword}, 핵심만 짚어드립니다",
    "{keyword}, 얼마나 준비해야 할까",
    "{keyword}에서 자주 나오는 질문 {n}가지",
    "{keyword} 첫걸음 — 순서대로 정리",
    "{keyword}, 쉽게 풀어드립니다",
    "{year}년 {keyword}, 이렇게 달라졌습니다",
    "{keyword}의 실제 비용 — 미리 알아야 할 것들",
    "{keyword} 시작 전에 꼭 읽어야 할 글",
    "{keyword}에서 놓치기 쉬운 부분들",
    "외국인을 위한 {keyword} 실전 가이드",
    "{keyword} 입문 — 처음이라면 꼭 알아야 할 것",
    "{keyword} 준비할 때 헷갈리는 부분 정리",
    "{year}년 달라진 {keyword}, 무엇이 바뀌었나",
    "{keyword} 궁금증, 하나씩 풀어봅니다",
    "{keyword}, 순서대로 따라 하면 됩니다",
    "{keyword} 고를 때 살펴봐야 할 {n}가지",
    "{keyword}, 요즘 이렇게 준비합니다",
    "{keyword} 관련 자주 헷갈리는 부분",
    "{keyword}, 시간과 비용을 아끼는 방법",
    "{keyword} 살펴보기 — 알아두면 유용한 정보",
    "{keyword} 계획하고 계신가요? 이것부터",
    "{keyword}, 현지에서 실제로 겪는 것들",
]
TITLE_TEMPLATES_EN = [
    "{keyword}: Where to Start",
    "{n} Things to Check Before {keyword}",
    "A Practical Look at {keyword}",
    "{keyword}, Step by Step",
    "Getting {keyword} Right the First Time",
    "{keyword} Checklist You Shouldn't Skip",
    "How {keyword} Actually Works",
    "{keyword}: What to Prepare First",
    "{keyword}, Explained Simply",
    "How Much Should You Budget for {keyword}?",
    "{n} Questions People Ask About {keyword}",
    "{keyword} 101: Where First-Timers Should Begin",
    "{keyword} Made Simple",
    "{keyword} in {year}: What's Changed",
    "The Real Cost of {keyword} — What to Expect",
    "Before You Try {keyword}, Read This First",
    "{keyword}: Details That Are Easy to Miss",
    "A Practical Look at {keyword} for International Readers",
    "{keyword}: A Beginner's Starting Point",
    "{keyword} — Common Points of Confusion, Cleared Up",
    "How {keyword} Has Changed in {year}",
    "{keyword} Q&A: Answers From the Field",
    "{keyword}, Broken Down Step by Step",
    "{n} Things to Look For When Choosing {keyword}",
    "How People Are Approaching {keyword} This Year",
    "{keyword}: Frequently Confused Points",
    "Save Time and Money on {keyword}",
    "{keyword}: A Closer Look",
    "Planning for {keyword}? Start Here",
    "{keyword}, From Someone Who's Been There",
]
_last_title_idx: dict = {}  # 사이트별 직전 사용 인덱스 (연속 반복 방지)
_recent_titles_global: list = []  # 전체 사이트 공통 — 최근 사용된 템플릿 인덱스(언어별) 기록해 교차 사이트 반복도 줄임
_GLOBAL_RECENT_MAX = 6

def build_diverse_title(keyword, lang, site_url=""):
    pool = TITLE_TEMPLATES_KO if lang == "ko" else TITLE_TEMPLATES_EN
    prev = _last_title_idx.get(site_url, -1)
    recent_global = {i for (l, i) in _recent_titles_global if l == lang}
    candidates = [i for i in range(len(pool)) if i != prev and i not in recent_global]
    if not candidates:
        candidates = [i for i in range(len(pool)) if i != prev]
    if not candidates:
        candidates = list(range(len(pool)))
    idx = random.choice(candidates)
    _last_title_idx[site_url] = idx
    _recent_titles_global.append((lang, idx))
    while len(_recent_titles_global) > _GLOBAL_RECENT_MAX:
        _recent_titles_global.pop(0)
    n = random.choice([3, 4, 5, 6, 7, 8, 9])
    year = str(datetime.now().year)
    return pool[idx].format(keyword=keyword, n=n, year=year)

def sanitize_tag(t, lang):
    """AI가 TAGS: 줄에 문장 전체·구분선(═══ 등)·잘린 조각을 그대로 흘려보내는
    문제(제보로 확인됨) 방지용 필터. 짧은 명사/키워드가 아니면 버린다."""
    t = t.strip().strip('"\'')
    if not t:
        return ""
    max_len = 18 if lang == "ko" else 30
    if len(t) > max_len:
        return ""
    if re.search(r'[═■□▶◆※▪…]', t):
        return ""
    if re.search(r'[.!?…]$', t):
        return ""
    if re.search(r'[,\n]', t):
        return ""
    return t

def extract_tags(text, keyword, theme, lang, is_news=False, tag_count=None):
    TAG_COUNT = tag_count or globals()["TAG_COUNT"]
    lines=text.strip().split("\n"); tags=[]; body_lines=[]
    for line in lines:
        if line.strip().upper().startswith("TAGS:"):
            raw=line.split(":",1)[1] if ":" in line else ""
            tags=[t.strip() for t in raw.split(",") if t.strip()]
        else: body_lines.append(line)
    body="\n".join(body_lines).strip()

    tags=[sanitize_tag(t, lang) for t in tags]
    tags=[t for t in tags if t]
    kk=keyword.strip().lower()
    tags=[t for t in tags if t.strip().lower()!=kk]
    tags=list({t.strip().lower():t for t in tags}.values())

    # ★ 뉴스모드는 keyword가 RSS 헤드라인 문장 전체라, 블로그모드처럼
    #   keyword 자체나 "keyword 효능/방법" 식 조합을 태그로 강제하면 헤드라인이
    #   그대로(혹은 헤드라인+접미어 형태로) 태그에 박힌다. 뉴스모드는 AI가 만든
    #   (검증 통과한) 태그만 쓰고, 모자라면 테마 기반 범용 태그로 채운다.
    if is_news:
        fb = (["한국","뉴스","2026","속보","이슈","정치","경제","사회","국제","문화"] if lang == "ko"
              else ["Korea","News","2026","Breaking","Update","Politics","Economy","Society","World","Culture"])
        tags = tags[:TAG_COUNT] if len(tags) > TAG_COUNT else tags
        for f in fb:
            if len(tags) >= TAG_COUNT: break
            if f.lower() not in [x.lower() for x in tags]: tags.append(f)
        return body, tags[:TAG_COUNT]

    tags=tags[:TAG_COUNT-1]
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
    if ic>=1: score+=10
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
    # ★ 연도 강제 치환: AI 프롬프트 지시만으론 보장 안 되므로 코드가 이중으로 강제
    #   2023/2024/2025 → 2026 (단어 경계 기준, 다른 4자리 숫자는 건드리지 않음)
    #   (title은 build_diverse_title()이 이미 항상 현재연도만 쓰므로 별도 처리 불필요)
    body = re.sub(r'\b(2023|2024|2025)\b', '2026', body)
    meta = re.sub(r'\b(2023|2024|2025)\b', '2026', meta)

    # ★ 2026-08-14 제거: 통계/표가 부족하면 지어낸 가짜 수치("약 500만 명", "12.3%
    #   증가", "3조 2,000억 원" 등)와 매번 똑같은 템플릿 표를 강제로 붙여넣던 로직을
    #   삭제했다. 사용자 지시("애드센스가 좋아할 구조로") + 근거 없는 통계가 27개
    #   사이트 수백 개 글에 토씨 하나 안 틀리고 반복되는 게 오히려 스팸/저품질
    #   신호로 잡힐 수 있음 — 통계나 표가 부족하면 그냥 없이 발행하는 게 낫다.

    # META 보완
    if len(meta) < 100:
        prompt = f"SEO 메타 디스크립션 {'130~140자(한글)' if lang=='ko' else '130~155 English chars'}로 작성. 키워드 '{keyword}' 포함. 제목: {title}\n순수 텍스트만 출력."
        try:
            result = gemini_fn(prompt).strip()
            result = re.sub(r'^META_DESC:\s*','',result,flags=re.IGNORECASE).strip()
            if 80<=len(result)<=200: meta=result
        except: pass
        if len(meta)<100:
            # ★ "전문가 검증"은 실제로 검증한 적 없는 근거 없는 신뢰 주장이라 제거—
            #   최후 폴백은 담백한 사실 서술로만 채운다.
            if lang=="ko": meta=f"{keyword}에 대해 알아두면 좋은 내용을 정리했습니다."[:140]
            else: meta=f"A practical look at {keyword} — what's worth knowing."[:155]
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
    # ★ 검색어에 테마 맥락을 붙여 관련성 낮은 스톡사진이 걸릴 확률을 줄임
    #   (예: "노안 예방" 단독 검색 → 엉뚱한 결과 / "presbyopia eye health Korea" → 훨씬 관련성 높음)
    theme_ctx = {
        "건강과 의학": "health Korea", "Korea Medical Tourism": "medical Korea",
        "Investment": "finance Korea", "Korea Investment": "finance Korea",
        "Insurance": "insurance Korea", "Finance": "finance Korea",
        "Tax and Law": "business Korea", "Crypto": "cryptocurrency finance",
        "Korea Real Estate": "real estate Korea", "Technology": "technology Korea",
        "K-Beauty": "skincare beauty", "K-Beauty Reviews": "skincare beauty",
        "K-POP": "Korea culture", "Travel": "Korea travel", "Visa Guide": "Korea immigration",
        "Wedding": "wedding Korea", "Study in Korea": "university Korea students",
        "International Students": "university Korea students", "국제교육문화": "education Korea",
        "Recruitment": "office work Korea", "Employment": "office work Korea",
        "Seoul Lifestyle": "Seoul Korea lifestyle", "Korea Culture": "Korea culture",
    }
    ctx = theme_ctx.get(theme, "Korea")

    def with_ctx(q):
        return q if ctx.lower() in q.lower() else f"{q} {ctx}"

    urls=[]
    if not has_ko:
        q = with_ctx(keyword)
        urls.extend(get_images_pixabay(q,count))
        if len(urls)<count: urls.extend(get_images_pexels(q,count-len(urls)))
    if len(urls)<count:
        en=with_ctx(translate_ko_to_en_for_image(keyword,theme))
        urls.extend(get_images_pixabay(en,count-len(urls)))
        if len(urls)<count: urls.extend(get_images_pexels(en,count-len(urls)))
    # ★ 주의: 예전엔 여기서 못 채운 나머지 슬롯을 THEME_IMAGE_FALLBACK(주제 뭉뚱그림 검색어,
    #   예: "medical health Korea doctor")로 억지로 채웠음. 그 결과 한 글에 키워드에 맞는
    #   사진 1~2장 + 본문과 무관한 범용 사진 1장이 섞여 들어가는 문제가 있었음
    #   (사용자 피드백: "이럴때는 이미지가 없는게 차라리 낫음").
    #   → 이제 키워드 특정 검색(위 두 단계)에서 못 찾은 슬롯은 억지로 채우지 않고
    #   빈 채로 반환. 호출부가 부족한 만큼 인포그래픽 카드로 대체하거나, 그마저
    #   실패하면 그냥 이미지 없이 발행한다.
    return list(dict.fromkeys(urls))[:count]

# ============================================================
# ★ 이미지-본문 관련성 실시간 검증 (2026-08-19 사용자 지시: "alt값 안 맞으면
#   그냥 패싱" — 예전엔 발행 후 audit_image_relevance.py가 나중에 훑어서
#   찾아냈는데, 그건 이미 공개된 상태로 한참 방치된다는 뜻이었다. 이제는
#   발행 전에 같은 Gemini Vision 판정을 그 자리에서 돌려서, 안 맞으면 그
#   이미지를 버리고(패싱) 나노바나나→인포그래픽 폴백 체인으로 넘어간다.
# ============================================================
def _download_image_bytes(url):
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        ctype = r.headers.get("Content-Type", "")
        if r.status_code == 200 and ctype.startswith("image"):
            return r.content, ctype.split(";")[0].strip()
    except Exception:
        pass
    return None, None

def _classify_image_relevance(image_bytes, mime_type, title, keyword):
    prompt = (
        "You are QA-checking whether a stock photo actually matches a blog article's topic.\n"
        f"Article title: {title}\n"
        f"Article focus keyword/subject: {keyword}\n"
        "Look at the attached image. Does it visually and topically relate to this SPECIFIC "
        "subject (not just a vaguely-similar generic photo of the same broad category)? "
        "Respond with exactly one word: RELEVANT or MISMATCH."
    )
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key:
        try:
            encoded = base64.b64encode(image_bytes).decode("ascii")
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                json={
                    "model": os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini"),
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded}"}},
                    ]}],
                    "max_tokens": 10,
                },
                timeout=60,
            )
            response.raise_for_status()
            verdict = response.json()["choices"][0]["message"]["content"].strip().upper()
            return verdict.startswith("RELEVANT")
        except Exception as e:
            print(f"  ⚠️ OpenAI 이미지 관련성 판정 실패, Gemini 재시도: {e}")
    try:
        resp = gemini_client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type), prompt],
            config={"temperature": 0.0, "max_output_tokens": 10},
        )
        return (resp.text or "").strip().upper().startswith("RELEVANT")
    except Exception as e:
        print(f"  ⚠️ 이미지 관련성 판정 실패(안전상 사용 금지): {e}")
        return False  # 판정 실패 이미지는 공개 글에 사용하지 않음

def filter_relevant_images(urls, title, keyword):
    kept = []
    for u in urls:
        img_bytes, mime = _download_image_bytes(u)
        if not img_bytes:
            continue
        if _classify_image_relevance(img_bytes, mime, title, keyword):
            kept.append(u)
        else:
            print(f"  🚫 이미지 관련성 불일치로 패싱: {u[:80]}")
    return kept

# ============================================================
# ★ 최종 안전망: 사진 검색(Pixabay/Pexels)이 모두 실패했을 때
#   본문 주제와 무관한 사진("South Korea nature" 등) 대신,
#   키워드를 그대로 텍스트로 담은 인포그래픽 카드를 생성해 사용.
#   → 이미지-본문 미스매치를 원천 차단(카드에 실제 키워드가 박혀있으므로 항상 100% 관련)
# ============================================================
INFOGRAPHIC_THEME_COLORS = {
    "건강과 의학":("#0F5132","#D1E7DD"), "Korea Medical Tourism":("#0F5132","#D1E7DD"),
    "Investment":("#1B2A4A","#D6E4FF"), "Korea Investment":("#1B2A4A","#D6E4FF"),
    "Insurance":("#1B2A4A","#D6E4FF"), "Finance":("#1B2A4A","#D6E4FF"),
    "Tax and Law":("#332D26","#EFE6D8"), "Crypto":("#3D1B5C","#E9DDF5"),
    "Korea Real Estate":("#4A2E13","#F1E4D3"), "Technology":("#0B2545","#D6E9FF"),
    "K-Beauty":("#7A1F4D","#FBE1EE"), "K-Beauty Reviews":("#7A1F4D","#FBE1EE"),
    "K-POP":("#4B0F6B","#EBD9F7"), "Travel":("#0B4F6C","#D3EEF7"),
    "Visa Guide":("#1B2A4A","#D6E4FF"), "Wedding":("#7A1F4D","#FBE1EE"),
    "Study in Korea":("#0B2545","#D6E9FF"), "International Students":("#0B2545","#D6E9FF"),
    "국제교육문화":("#0B2545","#D6E9FF"), "한국유학정보":("#0B2545","#D6E9FF"),
    "Recruitment":("#332D26","#EFE6D8"), "Employment":("#332D26","#EFE6D8"),
    "Jobs in Korea":("#332D26","#EFE6D8"), "Seoul Lifestyle":("#0B4F6C","#D3EEF7"),
    "Korea Culture":("#4B0F6B","#EBD9F7"), "한국 뉴스":("#1B2A4A","#D6E4FF"),
    "default":("#26313F","#DCE3EA"),
}
_KR_FONT_PATH = "/tmp/_kuac_nanumgothic_bold.ttf"
_FONT_CACHE = {}

def _get_card_font(size):
    if size in _FONT_CACHE: return _FONT_CACHE[size]
    from PIL import ImageFont
    if not os.path.exists(_KR_FONT_PATH):
        try:
            r = requests.get(
                "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-Bold.ttf",
                timeout=15)
            if r.status_code == 200:
                with open(_KR_FONT_PATH, "wb") as f: f.write(r.content)
        except Exception as e:
            print(f"  ⚠️ 폰트 다운로드 실패: {e}")
    try:
        font = ImageFont.truetype(_KR_FONT_PATH, size)
    except Exception:
        font = ImageFont.load_default()
    _FONT_CACHE[size] = font
    return font

def generate_infographic_card(keyword, theme, lang):
    """사진 검색 완전 실패 시, 키워드 텍스트를 담은 카드 이미지를 생성해 반환(로컬 파일 경로)."""
    from PIL import Image, ImageDraw
    import textwrap
    W, H = 1200, 630
    fg, bg = INFOGRAPHIC_THEME_COLORS.get(theme, INFOGRAPHIC_THEME_COLORS["default"])
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 14], fill=fg)
    draw.rectangle([0, H - 14, W, H], fill=fg)

    title_font = _get_card_font(64)
    label_font = _get_card_font(30)

    has_ko = any('\uAC00' <= c <= '\uD7A3' for c in keyword)
    wrap_width = 14 if has_ko else 22
    lines = textwrap.wrap(keyword, width=wrap_width)[:4]

    total_h = len(lines) * 78
    y = (H - total_h) // 2 - 20
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        w = bbox[2] - bbox[0]
        draw.text(((W - w) // 2, y), line, font=title_font, fill=fg)
        y += 78

    badge = theme if theme else ("한대협 KUAC" if lang == "ko" else "KUAC Network")
    bbox = draw.textbbox((0, 0), badge, font=label_font)
    w = bbox[2] - bbox[0]
    draw.text(((W - w) // 2, H - 70), badge, font=label_font, fill=fg)

    path = f"/tmp/infographic_{hashlib.md5(keyword.encode()).hexdigest()[:10]}.png"
    img.save(path, "PNG")
    return path

_uploaded_media_ids = {}

def upload_local_image_to_wp(site_url, pw, filepath, filename):
    try:
        with open(filepath, "rb") as f:
            data = f.read()
        r = requests.post(f"{site_url}/wp-json/wp/v2/media", auth=(WP_USER, pw),
                           headers={"Content-Disposition": f'attachment; filename="{filename}.png"',
                                    "Content-Type": "image/png"}, data=data, timeout=30)
        if r.status_code in (200, 201):
            media = r.json()
            source_url = media.get("source_url")
            if source_url and media.get("id"):
                _uploaded_media_ids[source_url] = media["id"]
            return source_url
        print(f"  ⚠️ 인포그래픽 업로드 실패 {r.status_code}: {r.text[:150]}")
    except Exception as e:
        print(f"  ⚠️ 인포그래픽 업로드 오류: {e}")
    return None

def ensure_featured_media(site_url, pw, image_url, title):
    if not image_url:
        return 0
    if image_url in _uploaded_media_ids:
        media_id = _uploaded_media_ids[image_url]
    else:
        try:
            image = requests.get(image_url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
            image.raise_for_status()
            mime = image.headers.get("Content-Type", "image/jpeg").split(";", 1)[0]
            extension = ".png" if "png" in mime else ".webp" if "webp" in mime else ".jpg"
            filename = "news-" + hashlib.md5(image_url.encode()).hexdigest()[:12] + extension
            uploaded = requests.post(
                f"{site_url}/wp-json/wp/v2/media", auth=(WP_USER, pw),
                headers={"Content-Disposition": f'attachment; filename="{filename}"', "Content-Type": mime},
                data=image.content, timeout=35,
            )
            uploaded.raise_for_status()
            media_id = uploaded.json().get("id", 0)
        except Exception as e:
            print(f"  ⚠️ 대표이미지 업로드 실패: {e}")
            return 0
    if media_id:
        try:
            requests.post(
                f"{site_url}/wp-json/wp/v2/media/{media_id}", auth=(WP_USER, pw),
                json={"alt_text": title, "caption": ""}, timeout=15,
            ).raise_for_status()
        except Exception as e:
            print(f"  ⚠️ 대표이미지 alt 저장 실패: {e}")
    return media_id

# ============================================================
# ★ 나노바나나(Gemini 2.5 Flash Image) — 스톡사진 실패 시 1차 폴백
#   기존엔 스톡사진 실패 → 곧바로 텍스트 인포그래픽 카드였는데, 실제 사진처럼
#   보이는 이미지가 나을 때가 많아 카드보다 먼저 시도한다. 카드는 이마저
#   실패했을 때의 최종 안전망으로 유지.
# ============================================================
def gemini_generate_image(prompt, out_path, max_retries=3):
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    last_err = None
    for attempt in range(max_retries):
        for model in GEMINI_IMAGE_MODELS:
            url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                   f"{model}:generateContent?key={GEMINI_API_KEY}")
            try:
                r = requests.post(url, json=body, timeout=90)
                if r.status_code != 200:
                    last_err = f"{r.status_code}: {r.text[:150]}"
                    continue
                parts = r.json()["candidates"][0]["content"]["parts"]
                for part in parts:
                    inline = part.get("inlineData") or part.get("inline_data")
                    if inline and inline.get("data"):
                        with open(out_path, "wb") as f:
                            f.write(base64.b64decode(inline["data"]))
                        return True
                last_err = "응답에 이미지 데이터 없음"
            except Exception as e:
                last_err = str(e)
        wait = min(4 * (2 ** attempt), 30)
        time.sleep(wait)
    print(f"  ⚠️ 나노바나나 이미지 생성 최종 실패: {last_err}")
    return False

def get_fallback_nanobanana_image(site_url, pw, keyword, theme, lang):
    try:
        en_concept = translate_ko_to_en_for_image(keyword, theme) if lang == "ko" else keyword
        prompt = (f"A realistic, editorial-style photograph representing '{en_concept}'. "
                  "Natural lighting, no text or logos in the image, no watermarks, "
                  "suitable as a blog article header photo, high quality, 16:9 composition.")
        path = f"/tmp/nanobanana_{hashlib.md5(keyword.encode()).hexdigest()[:10]}.png"
        if not gemini_generate_image(prompt, path):
            return []
        fname = "nanobanana-" + re.sub(r'[^a-zA-Z0-9]+', '-', keyword)[:40].strip('-')
        url = upload_local_image_to_wp(site_url, pw, path, fname or "nanobanana")
        return [url] if url else []
    except Exception as e:
        print(f"  ⚠️ 나노바나나 폴백 실패: {e}")
        return []

def get_fallback_infographic_image(site_url, pw, keyword, theme, lang):
    try:
        path = generate_infographic_card(keyword, theme, lang)
        fname = "infographic-" + re.sub(r'[^a-zA-Z0-9]+', '-', keyword)[:40].strip('-')
        url = upload_local_image_to_wp(site_url, pw, path, fname or "infographic")
        return [url] if url else []
    except Exception as e:
        print(f"  ⚠️ 인포그래픽 생성 실패: {e}")
        return []

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

_PLACEHOLDER_SECTIONS = {"추가", "add", "tbd", "todo", "n/a", "etc", "기타", "misc", "other", "others"}
_last_keyword_category = {}  # site_url -> 이번에 뽑힌 키워드의 카테고리 힌트 (있으면)

def _keyword_recently_covered(keyword, site_url):
    """키워드가 이 사이트에 최근 발행된 글 제목(최대 50개, fetch_recent_wp_titles로
    캐싱됨) 안에 이미 등장하는지 확인. 부분 문자열 매칭이라 "갑상선기능저하증"처럼
    제목 템플릿에 그대로 들어가는 한국어/영어 키워드 모두에서 잘 잡힌다."""
    titles = _wp_title_cache.get(site_url)
    if not titles:
        return False
    kw = keyword.strip().lower()
    if not kw:
        return False
    return any(kw in t for t in titles)

def load_keyword(filename, site_url, fallback):
    """
    2026-07-22: keywords_*.txt 포맷을 '# 카테고리' 주석 방식에서
    '키워드<TAB>카테고리명' 명시적 태그 방식으로 변경.
    - 예전 방식은 주석 줄을 실제 키워드로 잘못 뽑아버리는 사고(load_keyword 오염 버그)로
      이어졌고, 설령 그 버그를 막아도 카테고리 정보 자체가 통째로 유실되어
      pick_best_category()가 영어 카테고리명 vs 한글 키워드를 억지로 매칭해야 했음
      (예: kieca-korea.org 글의 18%가 전부 'Etc'로 잘못 분류됨).
    - 새 포맷은 탭으로 카테고리를 명시하므로 '#'이 파일에 아예 없어 원천적으로
      안전하고, 카테고리 정보도 유실되지 않는다.
    - 탭이 없는 줄(기존 파일과 100% 호환)은 그냥 키워드로만 취급.
    """
    used = _used_kw.setdefault(site_url, set())
    _last_keyword_category.pop(site_url, None)
    try:
        if os.path.exists(filename):
            entries = []  # (keyword, category_or_None)
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith('#'):
                        continue
                    if '\t' in s:
                        kw_part, cat_part = s.split('\t', 1)
                        kw_part = kw_part.strip()
                        cat_part = cat_part.strip()
                        cat = cat_part if (cat_part and cat_part.lower() not in _PLACEHOLDER_SECTIONS) else None
                        entries.append((kw_part, cat))
                    else:
                        entries.append((s, None))
            if entries:
                # ★ 2026-07-28: 프로세스 내 used셋만으론 실행(=워크플로우) 간
                #   중복을 못 막음 — 매 실행마다 프로세스가 새로 뜨면서 used가
                #   초기화되어, "갑상선기능저하증"이 이틀 안에 3편, "4th generation
                #   K-pop groups"가 당일 2편 나오는 등 사이트 안 주제 재탕이
                #   반복됐음(실사이트 감사로 확인). 실제 WP에 이미 발행된 최근
                #   제목(fetch_recent_wp_titles, main()에서 전체 사이트 사전로드)에
                #   키워드가 이미 등장하면 이번 회차 후보에서 제외해 재발행을 막는다.
                fresh = [e for e in entries
                         if e[0] not in used and not _keyword_recently_covered(e[0], site_url)]
                pool = fresh or [e for e in entries if e[0] not in used] or entries
                ch = random.choice(pool)
                used.add(ch[0])
                if ch[1]:
                    _last_keyword_category[site_url] = ch[1]
                return ch[0]
    except Exception:
        pass
    return fallback

_PLACEHOLDER_KEYWORDS = {"추가", "add", "tbd", "todo", "n/a"}

def sanitize_keyword(kw, fallback):
    """
    2026-07-22: keywords_*.txt의 '#카테고리명' 주석 줄이 load_keyword()에 그대로
    뽑혀서 제목/본문/이미지alt/태그에 '#'이 그대로 노출되는 사고가 있었음.
    load_keyword() 자체는 주석 줄을 걸러내도록 고쳤지만, 혹시 모를 재발(수동으로
    키워드 파일에 '#'를 다시 넣거나, 다른 경로로 오염된 keyword가 들어오는 경우)에
    대비해 사용 직전에 한 번 더 방어적으로 검증한다.
    """
    if not isinstance(kw, str):
        return fallback
    kw = kw.strip()
    if kw.startswith('#'):
        kw = kw.lstrip('#').strip()
    if not kw or kw.lower() in _PLACEHOLDER_KEYWORDS:
        return fallback
    return kw

AI_LEAK_PATTERNS = [
    r'<p>\s*body\s*HTML\s*</p>',
    r'(?<![a-zA-Z])body\s+HTML(?![a-zA-Z])',
    r'\[OUTPUT FORMAT[^\]]*\]',
    r'\[THIS SITE.?S UNIQUE STRUCTURE[^\]]*\]',
    r'^\s*TITLE:\s*$',
    r'as an AI language model',
    r"I('m| am) an AI",
    r'I cannot browse the internet',
    r'I do not have (real-time|access to real-time)',
]

def strip_hash_artifacts(text):
    """발행 직전 최종 방어선: 본문/제목/메타/태그에 '# 단어' 형태로 남은
    주석·플레이스홀더 잔재를 제거한다. hex color(#eee, #fff 등)나 '#1' 같은
    숫자 목록 표기는 '#' 뒤에 한글/영문자가 바로 붙는 패턴이 아니므로 건드리지 않는다.
    또한 프롬프트의 [OUTPUT FORMAT] 지시문이나 'body HTML' 같은 라벨을 AI가
    그대로 본문에 echo해버리는 사고("AI 흔적")를 발행 직전에 강제로 제거한다."""
    if not isinstance(text, str) or not text:
        return text
    text = re.sub(r'#[ \t]+(?=[가-힣A-Za-z])', '', text)
    for pat in AI_LEAK_PATTERNS:
        text = re.sub(pat, '', text, flags=re.IGNORECASE | re.MULTILINE)
    return text

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

_PUBLISH_GAP_STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "data", "publish_gap_state.json")


def _load_publish_gap_state():
    try:
        with open(_PUBLISH_GAP_STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_publish_gap_state(state):
    os.makedirs(os.path.dirname(_PUBLISH_GAP_STATE_PATH), exist_ok=True)
    with open(_PUBLISH_GAP_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_slot_posts(site, slot):
    # 2026-08-04: 하루 3슬롯(고정 3앵커 ±60분) → 하루 1회 완전랜덤시각으로
    # 변경(publish_scheduler.py 참고). 이제 슬롯이 1개뿐이라 분할 없이
    # 그 사이트의 하루치(daily=1)를 그대로 반환.
    # 2026-08-17: publish_every_n_days가 있으면 "정확히 N일마다"가 아니라
    # 매번 목표간격±1일 랜덤 목표를 새로 뽑아서 다음 발행일을 정한다 —
    # 정확히 이틀마다 딱딱 맞춰 발행하는 것 자체가 봇처럼 보이는 패턴이라서
    # (사용자 지시: "발행시간도 랜덤으로 해야해 - AI흔적 최소").
    # 마지막 발행일은 data/publish_gap_state.json에 사이트별로 저장(git 커밋 필요).
    every_n = site.get("publish_every_n_days")
    if every_n and every_n > 1:
        state = _load_publish_gap_state()
        url = site["url"]
        rec = state.get(url, {})
        today = now_kst().date()
        last_str = rec.get("last_published")
        target_gap = rec.get("target_gap")
        if target_gap is None:
            target_gap = random.randint(max(1, every_n - 1), every_n + 1)
        if last_str:
            last_date = __import__("datetime").date.fromisoformat(last_str)
            days_since = (today - last_date).days
        else:
            days_since = target_gap  # 기록 없으면 오늘 발행 허용

        if days_since < target_gap:
            state[url] = {"last_published": last_str, "target_gap": target_gap}
            _save_publish_gap_state(state)
            return 0

        # 오늘 발행 허용 — 다음 목표간격을 새로 랜덤 추첨해서 저장
        next_gap = random.randint(max(1, every_n - 1), every_n + 1)
        state[url] = {"last_published": today.isoformat(), "target_gap": next_gap}
        _save_publish_gap_state(state)
    return site["daily"]

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

def build_cta_html(site_url, lang):
    """
    사이트별 CTA(상담신청/구매유도 등)를 독자가 실제로 보는 박스로 코드가
    매 글마다 확정 삽입. 실제 이커머스 연동은 없으므로 이메일 상담 중심으로
    구성하고, '판매제품' 언급이 있는 사이트는 안내 문구만 자연스럽게 추가한다.
    """
    p = SITE_PERSONA.get(site_url, {})
    cta_desc = p.get("cta", "")
    if not cta_desc:
        return ""
    email = "huh0303@gmail.com"
    if lang == "ko":
        title = "문의 및 상담 신청"
        body = (f"이 글의 내용과 관련해 개인 맞춤 상담이 필요하시면 언제든 편하게 문의해 주세요.<br>"
                f'<strong>이메일:</strong> <a href="mailto:{email}">{email}</a>')
    else:
        title = "Get in Touch"
        body = (f"Have questions about your specific situation? Reach out anytime for a personal consultation.<br>"
                f'<strong>Email:</strong> <a href="mailto:{email}">{email}</a>')
    return (f'<div class="cta-box" style="margin:28px 0;padding:20px 24px;'
            f'background:#eef4ff;border:1px solid #c7d9f5;border-radius:8px;">'
            f'<h3 style="margin-top:0;font-size:1rem;">{title}</h3>'
            f'<p style="margin:0;">{body}</p></div>')


def build_author_bio_html(site_url, lang, reporter, keyword=""):
    """
    구글 EEAT(전문성) 신호 강화: 페르소나(숨은 AI지시)를 독자가 실제로 보는
    '저자 소개' 박스로 코드가 매 글마다 확정적으로 삽입. AI 의존 없음.
    """
    p = SITE_PERSONA.get(site_url, {})
    bio = p.get("persona_ko" if lang == "ko" else "persona_en", "")
    if not bio:
        return ""
    name = reporter.get("name", "")
    label = "이 글을 쓴 사람" if lang == "ko" else "About the Author"
    disclaimer = ("이 글은 정보 제공을 목적으로 하며, 개인의 상황에 따라 다를 수 있습니다."
                  if lang == "ko" else
                  "This article is for informational purposes; individual circumstances may vary.")
    return (f'<div class="author-bio" style="margin:32px 0;padding:20px 24px;'
            f'background:#f5f6f8;border-left:4px solid #4a5568;border-radius:6px;">'
            f'<h3 style="margin-top:0;font-size:1rem;">{label}: {name}</h3>'
            f'<p style="margin:0 0 8px 0;">{bio}</p>'
            f'<p style="margin:0;font-size:0.85em;color:#666;">{disclaimer}</p></div>')


def wp_post(site, title, body_html, meta, tags, faq, images, keyword, score, reporter):
    pw=os.getenv(site["wp_pass_env"],"")
    if not pw: return {"ok":False,"error":f"No password: {site['wp_pass_env']}"}
    url=site["url"]; theme=site["theme"]

    author_id=get_or_create_wp_author(url,pw,reporter)
    cat_name=get_category_for_post(theme,keyword,title)
    cat_id=0
    if site.get("mode") in ("news", "news_en"):
        wanted = re.sub(r'[\s/,\-]+', '', cat_name.lower())
        for existing_id, existing_name in load_site_categories(url, pw):
            if re.sub(r'[\s/,\-]+', '', existing_name.lower()) == wanted:
                cat_id = existing_id
                break
    if not cat_id:
        cat_id=pick_best_category(url,pw,keyword,title)

    hero=build_img_html(images[:1],keyword)
    mid =build_img_html(images[1:2],keyword) if len(images)>1 else ""
    end =build_img_html(images[2:3],keyword) if len(images)>2 else ""
    is_newsroom = site.get("mode") in ("news", "news_en")
    faq_html="" if is_newsroom else build_faq_html(faq)

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

    cta_html = "" if is_newsroom else build_cta_html(url, site.get("lang","ko"))
    final += cta_html

    author_bio_html = "" if is_newsroom else build_author_bio_html(url, site.get("lang","ko"), reporter, keyword)
    final += author_bio_html

    related_html = build_related_links_html(url, pw, site.get("lang","ko"), exclude_title=title)
    final += related_html

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
    # ★ 발행 시각: 실제 스크립트 실행 시각 그대로 찍히던 걸 KST 기준 ±2시간 랜덤으로 변경
    #   (하루 3번 고정 시각에 실행되다 보니 매번 똑같은 시각처럼 보이던 문제 해결)
    # ★ 2026-07-24 수정: jitter가 +(미래)로 나오면 WP가 status=publish를 무시하고
    #   강제로 future(예약)로 바꿔버려 "발행 안 됨" 버그의 근본 원인이었음.
    #   과거 방향으로만 흔들어서 절대 미래 시각이 되지 않도록 수정.
    jitter_min = random.randint(-120, 0)
    target_kst = now_kst() + timedelta(minutes=jitter_min)
    if target_kst > now_kst():
        target_kst = now_kst()
    target_gmt = target_kst - timedelta(hours=9)
    date_str     = target_kst.strftime("%Y-%m-%dT%H:%M:%S")
    date_gmt_str = target_gmt.strftime("%Y-%m-%dT%H:%M:%S")

    data={"title":title,"content":final,"status":"publish",
          "date":date_str,"date_gmt":date_gmt_str,
          "comment_status":"closed","ping_status":"closed",
          "categories":[cat_id] if cat_id and cat_id>0 else [],
          "tags":tag_ids,
          "meta":{"rank_math_focus_keyword":rank_kw,"rank_math_description":meta,"rank_math_seo_score":str(score)}}
    featured_media_id = ensure_featured_media(url, pw, images[0] if images else "", title)
    if featured_media_id:
        data["featured_media"] = featured_media_id
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
    if not _log_buf: return
    Path("newsroom_publish_result.json").write_text(
        json.dumps({"records": _log_buf}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not SHEETS_WEBHOOK: return
    try:
        r=requests.post(SHEETS_WEBHOOK,json={"records":_log_buf},timeout=15)
        print(f"  📊 구글시트 {len(_log_buf)}건: HTTP {r.status_code}")
        _log_buf.clear()
    except Exception as e:
        print(f"  ⚠️ 시트 전송 실패: {e}")

# ============================================================
# ★ 단일 포스트 처리
# ============================================================
def build_news_headline(keyword, lang):
    """뉴스 모드(koreanews365/theseouljournal) 전용: RSS에서 가져온 헤드라인은
    이미 완성된 문장이므로, 일반 키워드용 22개 제목 템플릿("Rethinking {keyword}:
    A Fresh Perspective for 2026" 등)에 그대로 끼워 넣으면 "Rethinking Outgoing
    Irish ambassador reflects on 4 years in Korea: A Fresh Perspective for 2026"
    처럼 말이 안 되는 제목이 나온다. 대신 같은 의미를 다른 표현으로 재작성한
    짧고 임팩트 있는 헤드라인을 별도 생성한다(원문 그대로 복사도 방지)."""
    try:
        if lang == "ko":
            prompt = ("다음 뉴스 헤드라인을 같은 의미로, 다른 표현을 사용해 신문 기사 톤으로 "
                       "짧고 임팩트 있게 재작성하세요. 90자 이내, 따옴표 없이, 설명 없이 헤드라인만.\n"
                       f"원문: {keyword}\n헤드라인:")
        else:
            prompt = ("Rewrite this news headline in fresh, punchy, professional news style "
                       "(same meaning, different wording, under 90 characters, no quotes, "
                       "headline only, no explanation).\n"
                       f"Original: {keyword}\nHeadline:")
        text = generate_content_gemini(prompt)
        headline = text.strip().split("\n")[0].strip().strip('"').strip("'").strip()
        headline = re.sub(r'^(headline|헤드라인)[:\s]*', '', headline, flags=re.IGNORECASE).strip()
        if headline and 8 <= len(headline) <= 160:
            if lang != "ko" or re.search(r"[가-힣]", headline):
                return headline
            translated = generate_content_gemini(
                "Translate this headline into concise, natural Korean newspaper Korean. "
                "Return only the Korean headline, no explanation:\n" + headline
            ).strip().strip('"').strip("'")
            if re.search(r"[가-힣]", translated):
                return translated[:90]
    except Exception as e:
        print(f"  ⚠️ 뉴스 헤드라인 재작성 실패: {e}")
    return keyword  # 실패 시 RSS 원본 헤드라인 그대로 사용(템플릿 왜곡보다 안전)

def process_one(site, keyword):
    url=site["url"]; lang=site["lang"]; theme=site["theme"]; mode=site["mode"]
    quality_target = 70 if mode in ("news", "news_en") else SEO_TARGET
    p=SITE_PERSONA.get(url,{}); min_chars=p.get("min_chars",2200); max_chars=p.get("max_chars")

    reporter=pick_reporter(site)
    print(f"\n  🖊  [{theme}] {keyword[:50]} | {reporter['name']}")

    news_source = None
    news_source_url = None
    news_source_summary = None
    if mode in ("news","news_en"):
        kw_tuple=crawl_rss_news(lang,site_url=url)
        keyword=kw_tuple[0] if isinstance(kw_tuple,tuple) else kw_tuple
        if not keyword:
            print("  NEWS SOURCE GATE: no licensed/approved story lead; skipping")
            return False
        if isinstance(kw_tuple,tuple) and len(kw_tuple)>=3:
            news_source=kw_tuple[2]
        if isinstance(kw_tuple,tuple) and len(kw_tuple)>=2:
            news_source_summary=kw_tuple[1]
        if isinstance(kw_tuple,tuple) and len(kw_tuple)>=4:
            news_source_url=kw_tuple[3]

    # 2026-08-19 사용자 지시: 태그 개수도 매번 10개 고정이면 패턴이 보이니 10~13개로 랜덤화
    tag_count = random.randint(10, 13)
    base_prompt=make_site_prompt(keyword,site,reporter,tag_count=tag_count)
    if mode in ("news", "news_en"):
        base_prompt += (
            "\n\nSOURCE LEAD FOR FACTUAL GROUNDING:\n"
            f"- Publisher: {news_source or 'Primary-source lead'}\n"
            f"- Source URL: {news_source_url or 'not supplied'}\n"
            f"- Feed summary: {news_source_summary or 'No summary supplied'}\n"
            "Use only facts supported by this lead or clearly identified primary records. "
            "Do not invent quotations, statistics, witnesses, dates, locations, reactions, or additional sources. "
            "If the available facts are limited, write a concise brief rather than padding the article."
        )
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
        body,tags=extract_tags(body_raw,keyword,theme,lang,is_news=(mode in ("news","news_en")),tag_count=tag_count)

        # AI가 만든 제목은 버리고, 코드가 22개 템플릿 중 랜덤으로 뽑아 무조건 교체
        # (반복 패턴이 구글에 "AI 대량생산"으로 보이는 문제 해결)
        # ★ 단, 뉴스 모드는 keyword가 이미 완성된 RSS 헤드라인이므로 템플릿을
        #   덧씌우면 "Rethinking [완성된 문장]: A Fresh Perspective for 2026" 처럼
        #   말이 안 되는 제목이 됨 → 뉴스 전용 헤드라인 재작성 함수 사용
        if mode in ("news", "news_en"):
            title = build_news_headline(keyword, lang)
        else:
            title=build_diverse_title(keyword,lang,site_url=url)

        pre=estimate_seo_score(title,body,meta,tags,faq,["x","x","x"],keyword)
        print(f"  📝 {attempt+1}회차 → SEO {pre}점")

        if pre>best_score:
            best_score=pre; best_result=(body,title,meta,faq,tags)

        if pre>=quality_target:
            print(f"  ✅ {pre}점 달성"); break

        if attempt<MAX_REGEN:
            # 부족 항목 진단
            issues=[]
            plain=re.sub(r'<[^>]+>','',body)
            blen=len(plain.replace(' ','').replace('\n',''))
            if blen<min_chars: issues.append(f"본문 {blen}자→{min_chars}자 증량")
            if max_chars and blen>max_chars: issues.append(f"본문 {blen}자→{max_chars}자 이하로 축약")
            if mode not in ("news", "news_en"):
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
    newsroom_len=len(re.sub(r'<[^>]+>','',body).replace(' ','').replace('\n',''))
    if mode in ("news","news_en") and max_chars and newsroom_len>max_chars:
        print(f"  ⛔ 뉴스 본문 {newsroom_len}자 > {max_chars}자 → 발행 스킵")
        return False

    # ★ 발행 직전 최종 방어선: '#' 잔재 강제 제거 (재발 방지 안전장치)
    title = strip_hash_artifacts(title)
    body = strip_hash_artifacts(body)
    meta = strip_hash_artifacts(meta)
    if faq:
        faq = [(strip_hash_artifacts(q), strip_hash_artifacts(a)) for q, a in faq]
    if tags:
        tags = [strip_hash_artifacts(t) for t in tags]

    # ★ 뉴스모드 출처 표기(2026-08-03 사용자 지시): 언론사 등록 요건상 타 언론
    #   보도를 재가공했으면 출처를 밝혀야 함. AI 프롬프트 지시에만 의존하면
    #   누락되거나 표현이 매번 달라질 수 있어, 실제 RSS 원문 출처가 있을 때만
    #   코드가 본문 끝에 고정 문구를 확정 삽입한다(제목/의학디스클레이머와 동일 원칙).
    if mode in ("news","news_en") and news_source:
        safe_url = news_source_url if news_source_url and news_source_url.startswith(("http://","https://")) else ""
        if safe_url and lang=="ko":
            source_label = f'<a href="{safe_url}" rel="nofollow noopener" target="_blank">{news_source} 원문</a>'
        elif safe_url:
            source_label = f'<a href="{safe_url}" rel="nofollow noopener" target="_blank">original {news_source} report</a>'
        else:
            source_label = news_source
        if lang=="ko":
            body += f'<p><em>출처: {source_label}. 헤드라인과 공개 사실을 참고했으며, 본문은 Koreanews365 편집국이 독자적으로 작성했습니다.</em></p>'
        else:
            body += f'<p><em>Source: {source_label}. The source headline and public facts were used as leads; this article was independently written by The Seoul Journal.</em></p>'

    if best_score<quality_target and mode not in ("news", "news_en"):
        print(f"  🔧 {best_score}점 → post-processing")
        body,meta=postprocess(body,meta,title,keyword,lang,min_chars,generate_content_gemini)

    if site.get("no_image"):
        images=[]
        print(f"  🚫 이미지 없음 (no_image=True)")
    else:
        images=get_multiple_images(keyword,count=2,theme=theme)
        if images:
            images = filter_relevant_images(images, title, keyword)
        if not images:
            print(f"  ⚠️ 사진 검색 완전 실패(또는 관련성 불일치로 전부 패싱) → 나노바나나(Gemini 이미지 생성)로 대체 시도")
            pw_for_img = os.getenv(site["wp_pass_env"], "")
            images = get_fallback_nanobanana_image(url, pw_for_img, keyword, theme, lang)
            if not images:
                print(f"  ⚠️ 나노바나나도 실패 → 주제 일치 인포그래픽 카드로 대체")
                images = get_fallback_infographic_image(url, pw_for_img, keyword, theme, lang)
            if not images:
                # ★ 인포그래픽 생성마저 실패해도 "South Korea nature" 같은 본문과
                #   무관한 범용 사진으로 억지로 채우지 않는다. 관련 없는 이미지보다
                #   이미지가 없는 편이 낫다는 판단(사용자 피드백).
                print(f"  🚫 인포그래픽 대체도 실패 → 이미지 없이 발행")
                images=[]
    print(f"  🖼  이미지 {len(images)}장")

    score=estimate_seo_score(title,body,meta,tags,faq,images,keyword)
    # The generic blog score does not measure newsroom-specific safeguards.
    # Credit a story only after it has a named, linked, <=72-hour source lead;
    # source-URL duplication was already rejected in crawl_rss_news().
    if mode in ("news", "news_en") and news_source and news_source_url:
        score=min(100, score + 10)
    rank="🏆" if score>=95 else "✅" if score>=90 else "⚠️" if score>=80 else "❌"
    print(f"  📊 SEO {score}/100 {rank}")

    plain_len=len(re.sub(r'<[^>]+>','',body).replace(' ','').replace('\n',''))
    ilinks=len(re.findall(r'<a\s+href=["\']https?://',body,re.IGNORECASE))
    tb=len(re.findall(r'<table[\s>]',body,re.IGNORECASE))
    print(f"     본문:{plain_len}자 | 링크:{ilinks} | TABLE:{tb} | META:{len(meta)}자")

    # ★ 2026-08-04 사용자 지시("SEO 90점 이상만 올려"): 예전엔 SEO_TARGET(90)을
    #   재생성 목표로만 쓰고, MAX_REGEN 다 써도 90 미달이면 postprocess로 보정만
    #   하고 그냥 발행했음. 이제는 하드 게이트 — 90 미달이면 발행 자체를 스킵.
    #   (주의: 이 score는 이 스크립트 자체 추정치이고, WP에 저장되는
    #   rank_math_seo_score도 이 값을 그대로 씀 — RankMath 플러그인이 REST로
    #   만든 글을 다시 분석해서 갱신해주는 게 아니라서, 실제 RankMath 분석
    #   점수와는 다를 수 있음. 그래도 현재 유일하게 있는 사전 품질 신호라
    #   이걸 게이트로 쓴다.)
    if score < quality_target:
        print(f"  ⛔ 품질점수 {score}점 < 뉴스/콘텐츠 목표 {quality_target}점 → 발행 스킵")
        log(url,theme,keyword,title,"",score,len(images),"⛔ skip_low_seo")
        return False

    cat_name=get_category_for_post(theme,keyword,title)
    print(f"  📁 카테고리: {cat_name}")

    # ★ 2026-08-03: 예전엔 뉴스모드 2개 사이트만 중복 제목을 걸렀음(그것도 완전
    #   일치만). 실제로는 27개 사이트 전체에서 살짝 다른 표현의 중복 제목이
    #   125건 쌓였던 게 확인돼서, 전체 사이트 + fuzzy(앞 20자) 매칭으로 강화.
    if title:
        tl=title.strip().lower()
        tl_key=_title_dup_key(title)
        sc=_wp_title_cache.get(url,set())
        if tl in sc or tl_key in sc:
            print(f"  ⛔ 중복(유사 제목 포함) → 스킵")
            log(url,theme,keyword,title,"",score,len(images),"⛔ skip_dup")
            return False
        sc.add(tl); sc.add(tl_key); _wp_title_cache[url]=sc

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
    # Global publication freeze: index/quality recovery takes priority.
    # Publishing stays disabled unless a future reviewed workflow explicitly opts in.
    if os.getenv("WP_AUTOPUBLISH_ENABLED", "false").strip().lower() != "true":
        print("⛔ WordPress 자동발행 전면 중지: WP_AUTOPUBLISH_ENABLED=true가 아니므로 종료합니다.")
        print("   현재 운영 모드: 색인·품질 감사 우선 / 신규 발행 금지")
        return
    print(f"\n{'='*60}")
    print(f"🚀 autopost_mega.py v2.0 — SLOT {RUN_SLOT} | {now_kst().strftime('%Y-%m-%d %H:%M:%S')} KST")
    print(f"   Gemini: {GEMINI_MODEL} | SEO 목표: {SEO_TARGET}점 | 재생성: {MAX_REGEN}회")
    print(f"   ✅ 카테고리 생성 금지 — 기존 카테고리 중에서만 매칭 (pick_best_category)")
    print(f"   ✅ 27개 사이트별 독립 페르소나 (SITE_PERSONA)")
    print(f"   ✅ IndexNow 발행 즉시 ping")
    print(f"{'='*60}\n")

    ok=fail=skip=0

    # ★ 2026-07-28: 예전엔 뉴스모드 2개 사이트만 최근 제목을 미리 불러왔음.
    #   블로그모드 26개 사이트는 이 캐시가 없어 load_keyword()의 중복주제
    #   방지(_keyword_recently_covered)가 작동하지 않았다 — 전체 사이트로 확장.
    print("📋 전체 사이트 최근 발행 제목 사전 로드 (중복 주제 방지)...")
    for s in SITES_CONFIG:
        pw=os.getenv(s["wp_pass_env"],"")
        if pw: fetch_recent_wp_titles(s["url"],pw)

    # 2026-08-17: 특정 사이트 하나만 지금 바로 글 1건 발행하고 싶을 때
    # (예: k-health365.com 단발 테스트) 슬롯 로직을 무시하고 강제 발행.
    target_site_url = os.getenv("TARGET_SITE_URL", "").strip()
    # 2026-08-19: 27개 사이트가 하루 한 순간에 몰려서 발행되면 "같은 운영자가
    # 굴리는 네트워크"라는 신호를 구글에 그대로 주는 꼴이라(사용자 지적),
    # publish_scheduler.py가 사이트마다 각자 다른 랜덤 시각을 잡아 이 스크립트를
    # 사이트 하나씩 개별 디스패치한다. TARGET_SITE_URL(강제발행, n=1로 슬롯 무시)과
    # 달리 이건 get_slot_posts의 주기/페이싱 로직은 그대로 존중하고 대상 사이트만 좁힌다.
    site_filter_url = os.getenv("SITE_FILTER_URL", "").strip()

    for site in SITES_CONFIG:
        url=site["url"]; theme=site["theme"]
        if site_filter_url and url != site_filter_url:
            continue
        if target_site_url:
            if url != target_site_url:
                continue
            n = 1
        else:
            n=get_slot_posts(site,RUN_SLOT)
            if n==0:
                print(f"⏭  {url} — 이번 슬롯 없음"); continue

        if site["mode"] in ("news", "news_en"):
            daily_target = newsroom_daily_target(url)
            published_today = count_published_today(url, os.getenv(site["wp_pass_env"], ""))
            if published_today is None:
                print(f"⏭  {url} — 오늘 발행량 확인 실패, 안전 중지")
                skip += n
                continue
            print(f"  🗓️ 오늘 발행 {published_today}/{daily_target}건 (3~10건 자동 선정)")
            if published_today >= daily_target:
                print(f"⏭  {url} — 오늘의 무작위 발행 목표 달성")
                skip += n
                continue

        print(f"\n{'─'*50}")
        print(f"🌐 {url} [{theme}] 슬롯{RUN_SLOT} → {n}건")

        if not is_site_reachable(url):
            print(f"  ⚠️ 연결 불가 → 스킵")
            for _ in range(n): log(url,theme,"—","","",0,0,"⚠️ skip_unreachable")
            skip+=n; continue

        for i in range(n):
            kw=("__news__" if site["mode"] in ("news","news_en")
                else load_keyword(site["keywords_file"],url,f"{theme} guide 2026"))
            if site["mode"] not in ("news","news_en"):
                kw=sanitize_keyword(kw, f"{theme} guide 2026")
            if process_one(site,kw): ok+=1
            else: fail+=1
            if i<n-1: time.sleep(random.uniform(10,18))

    flush_log()
    print(f"\n{'='*60}")
    print(f"✅ 완료 — 성공:{ok} / 실패:{fail} / 스킵:{skip}")
    print(f"{'='*60}\n")

if __name__=="__main__":
    main()
