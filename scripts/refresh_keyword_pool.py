#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
refresh_keyword_pool.py
─────────────────────────────────────────────────────────────
2026-08-22: koreainvest365.com 키워드 풀이 19개뿐이라 발행 이력 대비
너무 작아서 제목 중복 스킵이 빈발함(실사용자 테스트로 확인). 사용자 지시:
"키워드가 가장 중요해.. 지금 다시 리서치해서 가장 핫한 키워드로... 이건
매주 일요일마다 재검색해서 키워드 pool을 업데이트해줘."

2026-08-22 2차 수정 — 더 심각한 문제 발견: 처음 50개를 만들 때 사이트 자체의
"새 키워드끼리만" 중복 체크했고, 그 사이트에 이미 발행된 실제 글 제목과는
대조하지 않아서 50개 중 19개(38%)가 이미 쓴 주제와 겹쳤음(실사용자 재현—
"Korea money market fund"는 기존 발행 제목과 완전히 동일했음). 그리고 사용자
지시: "황금키워드가 진짜 다양해야해.. 50개 항상 유지하고 랜덤하게 고르게..
비슷비슷한 사이트에서 유사한 글이 나왔을 가능성 있어.. 안전장치 잘 해줘.
황금키워드가 겹치지 않는게 첫째, 글내용도 절대 겹치지 않게."

그래서 이번엔 25개 사이트(뉴스 2개 제외 — koreanews365/theseouljournal은
RSS 기반이라 이 스크립트 대상이 아님) 전체를 대상으로, 매 갱신마다:
1) 25개 사이트 전체의 실제 발행 이력 제목을 WP REST(공개 GET, 인증 불필요)로
   가져와 "전체 네트워크 코퍼스"를 만든다 — 사이트 자기 자신의 과거 글뿐
   아니라 다른 24개 사이트의 과거 글과도 겹치는지 함께 확인한다(주제가
   인접한 사이트끼리 같은 얘기를 쓰는 사고 방지).
2) Gemini 검색그라운딩으로 새 키워드 후보를 받고, 위 코퍼스와 어간(stemming)
   기반 단어중복도로 겹치는 후보는 버린다.
3) 버려서 50개에 못 미치면 추가 리서치를 다시 요청(최대 3라운드)하고, 그래도
   부족하면 기존 파일에서 코퍼스와 안 겹치는 항목만 살려서 채운다 — 어떤
   경우에도 항상 정확히 50개를 유지한다.

2026-08-22 3차 수정 — 사용자 지시: "지침을 분명히 줬잖아.. 모든 Gemini →
GPT로." 검색그라운딩을 Gemini(google_search 툴)로만 짜놨던 게 바로 이
스크립트가 실제로 못 돌아가는 원인이었음(GEMINI_API_KEY가 월 지출한도
초과 상태 — 8/2부터 미해결). OpenAI Responses API의 web_search 툴로
교체(실사용 테스트로 응답 형식 확인 완료) — 이제 OPENAI_API_KEY가 1순위,
Gemini 검색그라운딩은 OPENAI_API_KEY가 아예 없을 때만 쓰는 최후 폴백으로
격하(autopost_mega.py의 텍스트/이미지 생성과 동일한 원칙).

기존 파일은 항상 data/keywords/_backup_YYYYMMDD/에 백업 후 교체(기존
27개 사이트 삭제작업 원칙과 동일 — 조사 결과를 덮어쓰기 전에 항상 보존).
"""
import datetime
import os
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation_hub.golden_keyword_mentions import parse_mention_rows, rank_mentioned_keywords

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_SEARCH_MODEL = os.environ.get("OPENAI_SEARCH_MODEL", "gpt-4o-mini")
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = os.environ.get("KEYWORD_RESEARCH_MODEL", "gemini-2.5-flash")
MAX_ROUNDS = 3  # 부족분을 다시 채우려는 최대 리서치 재시도 횟수

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ============================================================
# 25개 사이트(뉴스 2개 제외) — autopost_mega.py SITES_CONFIG/SITE_PERSONA와
# 동일 내용. publish_scheduler.py와 같은 관례로 무거운 종속성을 피하려고
# autopost_mega.py를 직접 import하지 않고 필요한 값만 독립적으로 유지.
# ============================================================
TARGETS = [
    {"url": "https://k-health365.com", "file": "data/keywords/keywords_khealth.txt",
     "domain_desc": "Korean health information: nutrients/supplements, disease coping "
                     "methods, and general wellness — written in Korean for a Korean "
                     "reader audience",
     "categories": ["건강영양성분소개", "질병별대처법", "건강정보"], "lang": "ko"},
    {"url": "https://koreamedicaltour.com", "file": "data/keywords/keywords_medicaltour.txt",
     "domain_desc": "Korea medical tourism for international patients: cosmetic surgery, "
                     "hospital costs, visas and government support",
     "categories": ["Cosmetic Surgery", "Government Support", "Hospital Costs"], "lang": "en"},
    {"url": "https://koreainvest365.com", "file": "data/keywords/keywords_kinvest.txt",
     "domain_desc": "South Korea investing: KOSPI/Kosdaq stocks, ETFs and funds, and "
                     "crypto/digital-asset policy — for an international investor audience",
     "categories": ["Korea Stocks", "Korea Funds & ETF", "Crypto & Digital"], "lang": "en"},
    {"url": "https://ki-korea.com", "file": "data/keywords/keywords_kikorea.txt",
     "domain_desc": "Foreign direct investment and business establishment in Korea "
                     "(corporate/FDI entry, not personal stock investing)",
     "categories": ["Investment Structures", "Registration Process", "Incentives & Support"], "lang": "en"},
    {"url": "https://koreainsurance365.com", "file": "data/keywords/keywords_kinsurance.txt",
     "domain_desc": "Insurance eligibility, enrollment, coverage and claims for foreign "
                     "residents in Korea",
     "categories": ["Auto Insurance", "Dental Insurance", "Health Insurance", "Travel Insurance"], "lang": "en"},
    {"url": "https://kfinance365.com", "file": "data/keywords/keywords_kfinance.txt",
     "domain_desc": "Everyday banking, cards, remittance and credit for foreign residents "
                     "in Korea (NOT stock investing)",
     "categories": ["Banking", "Cards & Credit", "Remittance", "Tax Refund"], "lang": "en"},
    {"url": "https://koreataxnlaw.com", "file": "data/keywords/keywords_ktax.txt",
     "domain_desc": "Tax filing and basic legal compliance for foreign residents and "
                     "foreign-owned small businesses in Korea",
     "categories": ["Business Setup", "Tax Filing", "Visa"], "lang": "en"},
    {"url": "https://koreacrypto365.com", "file": "data/keywords/keywords_kcrypto.txt",
     "domain_desc": "Korean crypto regulation, licensed exchanges and market-policy — "
                     "neutral regulatory briefing, never trading/price-prediction hype",
     "categories": ["Exchanges", "Investing", "Regulations"], "lang": "en"},
    {"url": "https://krealestate365.com", "file": "data/keywords/keywords_krealestate.txt",
     "domain_desc": "Jeonse, monthly rent and home purchase procedures for foreign "
                     "residents in Korea",
     "categories": ["Apartments", "Commercial", "Loans"], "lang": "en"},
    {"url": "https://ktech365.com", "file": "data/keywords/keywords_ktech.txt",
     "domain_desc": "Korean semiconductors, AI infrastructure and technology-industry policy",
     "categories": ["AI", "Semiconductors", "Startups"], "lang": "en"},
    {"url": "https://oliveyoungkorea.com", "file": "data/keywords/keywords_oliveyoung.txt",
     "domain_desc": "Ingredient-led K-beauty product selection and shopping at Olive Young "
                     "for international shoppers",
     "categories": ["Skincare", "Top Products", "Wellness", "Makeup"], "lang": "en"},
    {"url": "https://kworld365.com", "file": "data/keywords/keywords_kworld.txt",
     "domain_desc": "Verified K-pop releases, charts, tours and agency announcements",
     "categories": ["K-Pop Releases", "Charts & Rankings", "Tours & Concerts", "Agency & Idol News"], "lang": "en"},
    {"url": "https://k-trip365.com", "file": "data/keywords/keywords_ktrip.txt",
     "domain_desc": "Public-transport-based Korea itineraries and seasonal travel planning",
     "categories": ["Transport & Admission", "Itineraries", "Seasonal Travel", "Stays & Lodging"], "lang": "en"},
    {"url": "https://k-visa365.com", "file": "data/keywords/keywords_kvisa.txt",
     "domain_desc": "Official Korea visa eligibility, documents and application procedures",
     "categories": ["Long-term Visa", "Student Visa", "Work Visa", "Immigration Policy Updates"], "lang": "en"},
    {"url": "https://koreawedding365.com", "file": "data/keywords/keywords_kwedding.txt",
     "domain_desc": "Cross-cultural wedding registration, ceremony planning and "
                     "marriage-visa document coordination in Korea",
     "categories": ["Legal Registration", "Visa & Documents", "Ceremony Planning", "Budget"], "lang": "en"},
    {"url": "https://kstudy365.com", "file": "data/keywords/keywords_kstudy365.txt",
     "domain_desc": "Degree admissions and scholarships at Korean universities "
                     "(pre-admission focus, not life after enrolling)",
     "categories": ["Admissions", "Scholarships", "Application Process"], "lang": "en"},
    {"url": "https://studyinkorea365.com", "file": "data/keywords/keywords_studyinkorea365.txt",
     "domain_desc": "Practical student life AFTER admission in Korea: housing, budgeting, "
                     "campus services (not admissions itself)",
     "categories": ["Campus Life", "Housing & Budget", "Student Visa & Work"], "lang": "en"},
    {"url": "https://kieca-korea.org", "file": "data/keywords/keywords_kieca.txt",
     "domain_desc": "국제교육시장: 한국 대학을 위한 외국인 유학생 유치시장과 국제교육 협력 동향(기관/정책 리포트체)",
     "categories": ["Careers", "Culture", "Language"], "lang": "ko"},
    {"url": "https://ksa-korea.org", "file": "data/keywords/keywords_ksaKorea.txt",
     "domain_desc": "해외 지원자를 위한 한국 유학 서류·일정·비자 준비",
     "categories": ["Admissions", "Scholarships", "Visa"], "lang": "ko"},
    {"url": "https://sis-korea.com", "file": "data/keywords/keywords_sisKorea.txt",
     "domain_desc": "International schools and short-term academic programs in Korea "
                     "(directory-style, never implies official affiliation)",
     "categories": ["Applications", "Programs", "Scholarships"], "lang": "en"},
    {"url": "https://jobkorea365.com", "file": "data/keywords/keywords_jobkorea365.txt",
     "domain_desc": "Korean employment conditions, labor rules and salary data for "
                     "foreign workers (rights/rules focus)",
     "categories": ["Jobs", "Salaries", "Work Visa"], "lang": "en"},
    {"url": "https://jobinkorea365.com", "file": "data/keywords/keywords_jobinkorea365.txt",
     "domain_desc": "Job-search channels, applications and interviews for foreign "
                     "candidates (job-seeker focus, not employer-facing)",
     "categories": ["Job Search", "Interviews", "Visa Compatibility"], "lang": "en"},
    {"url": "https://jobkoreaglobal.com", "file": "data/keywords/keywords_jobkoreaglobal.txt",
     "domain_desc": "Employer-facing international recruitment and sponsorship compliance "
                     "in Korea (B2B, not job-seeker facing)",
     "categories": ["Hiring", "Sponsorship", "Compliance", "Foreign Workers", "Salaries", "Onboarding"], "lang": "en"},
    {"url": "https://korea365.org", "file": "data/keywords/keywords_korea365.txt",
     # 2026-09-04 CEO: this is the one site in the network built as a broad
     # "Korea life A-Z" portal (not locked to one vertical like the other 32
     # sites), so it should be the one that actually rides today's biggest
     # viral moment IN Korea daily life — a Chuseok train-ticket booking
     # crunch, a KBO/Son Heung-min match affecting commute or bar/restaurant
     # crowds, a public holiday travel surge — turned into a practical
     # newcomer-relevant angle (how to book, what to expect, what changes for
     # you). Never partisan political commentary or approval-rating takes —
     # that would break this site's neutral newcomer-service brand; that
     # kind of coverage belongs on koreanews365.com instead.
     "domain_desc": "Essential public services and daily administration for newcomers "
                     "to Korea (general newcomer guide, not government-affiliated) — "
                     "actively prioritize whatever is most talked-about in Korea RIGHT "
                     "NOW that has a practical daily-life angle for a resident/newcomer "
                     "(holiday travel/ticketing surges, a major sports match changing "
                     "transit or crowds, a seasonal service rush), turned into concrete "
                     "how-to guidance. Do not cover partisan politics, election polling, "
                     "or named politicians — that is out of scope for this site.",
     "categories": ["Culture", "Living", "Travel", "Etc"], "lang": "en"},
]

PROMPT_TMPL = """Search the web right now for what is actually trending TODAY ({today}) in
this topic area: {domain}.

Collect current evidence first. Identify repeatedly mentioned proper nouns and concrete
noun phrases across four separate discovery surfaces: newspapers, Naver, Google, and
other media. Then attach a practical {lang_label} SEO phrase to each observed noun.

Priority sources include Naver News, Chosun Ilbo, Hankyoreh, CNN and The New York Times,
plus other reputable national newspapers, broadcasters and specialist media relevant to
the topic. Count only items whose publication date is exactly {today}. Collect at least
{count} distinct noun clusters, with one output row for every independent mention.

Rules:
- Collect multiple independent mentions for each noun; do not treat syndicated copies at
  the same URL as separate evidence.
- Surface must be exactly newspaper, naver, google, or media. "naver" means a result
  observed through Naver News/Search; "google" means Google News/Search/Trends.
- Cluster aliases and near-identical headlines into one underlying event, entity, policy,
  accident, season or issue before proposing a search phrase.
- Validate each idea using observable Google/Naver trend signals and GSC demand when those
  signals are available. Never invent unavailable evidence.
- Apply this locked 100-point rubric: GSC demand 25, media repetition 20,
  Google/Naver trend 20, site fit 15, actionable intent 10, official source 10.
- Keep only ideas that can credibly reach 70/100. Prefer 80+, and rank 90+ first.
- Policy, accident, medical, finance, legal and visa/immigration topics require a current
  official source; without one, omit the idea regardless of its apparent popularity.
- Convert the verified signal into this site's practical intent (cost, method, eligibility,
  schedule, comparison or precautions) instead of copying a news headline.
- Never copy headline wording or article text.
- Each keyword is a short search-style phrase (3-6 words), not a full sentence, and must
  contain the observed noun or its unambiguous canonical spelling.
- Ground them in what's actually happening right now (specific companies, specific policy
  developments, specific product names, specific market/regulatory events) — not vague
  evergreen phrases like "how to invest in Korea".
- No two keywords should be near-duplicates of each other.
{avoid_block}
- Output one row PER OBSERVED MENTION. Repeating the same noun on separate sourced rows
  is required so code can count it. Use exactly seven tab-separated fields:
  keyword<TAB>category<TAB>noun<TAB>surface<TAB>outlet<TAB>YYYY-MM-DD<TAB>source_url
  Category must be exactly one of: {categories}. source_url must be the actual result URL.
- CRITICAL: every row for the same noun cluster must repeat the noun field with exactly
  the same canonical spelling. Do not output a noun seen on only one surface.
- Example structure (format only, do not reuse its facts):
  Example noun practical guide<TAB>{example_category}<TAB>Example Noun<TAB>newspaper<TAB>Outlet A<TAB>{today}<TAB>https://example.com/a
  Example noun practical guide<TAB>{example_category}<TAB>Example Noun<TAB>naver<TAB>Outlet B<TAB>{today}<TAB>https://example.com/b
- No numbering, no headers, no explanation, no markdown — just the raw lines.
"""


# ============================================================
# ★ 네트워크 전체 발행이력 코퍼스 — 25개 사이트 전부의 실제 발행 제목을
#   모아서, 새 키워드가 "이 사이트"뿐 아니라 "인접 주제의 다른 사이트"와도
#   겹치는 글을 쓰게 되는 걸 막는다. 공개 REST GET이라 인증 불필요.
# ============================================================
def fetch_published_titles(site_url, timeout=15):
    titles = []
    try:
        page = 1
        while True:
            r = requests.get(
                f"{site_url}/wp-json/wp/v2/posts",
                params={"per_page": 100, "page": page, "_fields": "title", "status": "publish"},
                timeout=timeout,
            )
            if r.status_code != 200:
                break
            batch = r.json()
            if not isinstance(batch, list) or not batch:
                break
            for p in batch:
                t = re.sub(r"<[^>]+>", "", p.get("title", {}).get("rendered", "")).strip()
                if t:
                    titles.append(t)
            if len(batch) < 100:
                break
            page += 1
    except Exception as e:
        print(f"    ⚠️ {site_url} 발행이력 조회 실패({e}) — 이 사이트는 코퍼스에서 제외")
    return titles


_STOPWORDS = {"for", "the", "a", "an", "and", "of", "to", "in", "on", "how", "what",
              "is", "are", "your", "you", "this", "that", "with"}


def _stem(w):
    w = w.lower()
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]
    return w


def _sig_words(text):
    return {_stem(w) for w in re.findall(r"[a-zA-Z가-힣0-9]+", text.lower()) if w not in _STOPWORDS}


def overlaps_corpus(keyword, corpus_norms, corpus_wordsets):
    kw_norm = re.sub(r"[^a-z0-9가-힣]+", "", keyword.lower())
    kw_words = _sig_words(keyword)
    for t_norm in corpus_norms:
        if kw_norm and kw_norm in t_norm:
            return True
    if len(kw_words) >= 2:
        for t_words in corpus_wordsets:
            common = kw_words & t_words
            if len(common) >= max(2, len(kw_words) - 1):
                return True
    return False


def build_network_corpus(all_titles_by_site):
    norms, wordsets = [], []
    for titles in all_titles_by_site.values():
        for t in titles:
            norms.append(re.sub(r"[^a-z0-9가-힣]+", "", t.lower()))
            wordsets.append(_sig_words(t))
    return norms, wordsets


def parse_lines(text, valid_categories):
    """2026-08-22 실사용 테스트로 확인: gpt-4o-mini의 web_search 출력은
    "keyword<TAB>category" 지시를 거의 안 지키고 한 줄에 키워드만 던지는
    경우가 대부분이었다(탭 없으면 전부 버리던 예전 로직 탓에 다수 사이트가
    "후보 0개"로 나온 원인). 탭이 있으면 그대로 쓰고, 없으면 키워드만
    받아서 category=None으로 두고 호출부가 라운드로빈으로 배정하게 한다."""
    lines = []
    for raw in text.strip().split("\n"):
        raw = raw.strip()
        raw = re.sub(r'^[-*\d.\)\s]+', '', raw)  # "1. ", "- " 같은 목록기호 제거
        if not raw:
            continue
        if "\t" in raw:
            kw, cat = raw.split("\t", 1)
            kw, cat = kw.strip(), cat.strip()
            if cat not in valid_categories:
                cat = None
        else:
            kw, cat = raw, None
        if not kw or len(kw) < 3 or len(kw) > 80:
            continue
        lines.append((kw, cat))
    seen = set()
    deduped = []
    for kw, cat in lines:
        k = kw.lower()
        if k in seen:
            continue
        seen.add(k)
        deduped.append((kw, cat))
    return deduped


def _extract_responses_text(data):
    """OpenAI Responses API 응답에서 실제 텍스트만 뽑아낸다. 실사용 테스트로
    확인한 형식: output 배열 안에 type=web_search_call(검색 자체) 항목과
    type=message(최종 답변) 항목이 섞여 있고, message.content[].type=
    output_text.text가 실제 결과."""
    chunks = []
    for item in data.get("output", []):
        if item.get("type") != "message":
            continue
        for c in item.get("content", []):
            if c.get("type") == "output_text" and c.get("text"):
                chunks.append(c["text"])
    return "\n".join(chunks)


def call_openai_search(prompt):
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    body = {"model": OPENAI_SEARCH_MODEL, "tools": [{"type": "web_search"}], "input": prompt}
    last_err = None
    for attempt in range(3):
        try:
            r = requests.post(OPENAI_RESPONSES_URL, headers=headers, json=body, timeout=90)
            if r.status_code == 429 or r.status_code >= 500:
                last_err = f"{r.status_code}: {r.text[:200]}"
                time.sleep(min(10 * (2 ** attempt), 60))
                continue
            r.raise_for_status()
            text = _extract_responses_text(r.json())
            if text.strip():
                return text
            last_err = "empty output_text"
        except Exception as e:
            last_err = str(e)[:200]
        time.sleep(3)
    raise RuntimeError(f"OpenAI 웹서치 리서치 실패: {last_err}")


def call_gemini(client, prompt):
    from google.genai import types as genai_types
    try:
        resp = client.models.generate_content(
            model=MODEL, contents=prompt,
            config=genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
                temperature=0.9,
            ),
        )
        return resp.text, True
    except Exception as e:
        print(f"    ⚠️ 검색 그라운딩 실패({e}) → 모델 자체 지식으로 폴백")
        resp = client.models.generate_content(
            model=MODEL, contents=prompt,
            config={"temperature": 0.9, "max_output_tokens": 4096},
        )
        return resp.text, False


def call_search_llm(client, prompt):
    """2026-08-22: OpenAI(웹서치 툴)가 1순위, Gemini 검색그라운딩은
    OPENAI_API_KEY가 아예 없을 때만 쓰는 최후 폴백 — autopost_mega.py의
    텍스트/이미지 생성 라우팅과 동일한 원칙."""
    if OPENAI_API_KEY:
        try:
            return call_openai_search(prompt), True
        except Exception as e:
            print(f"    ⚠️ OpenAI 웹서치 실패({e}) → Gemini 폴백 시도")
    if client is not None:
        return call_gemini(client, prompt)
    raise RuntimeError("OPENAI_API_KEY도 GEMINI_API_KEY도 사용 불가")


def research_one_site(client, target, today_str, corpus_norms, corpus_wordsets):
    categories_str = " / ".join(target["categories"])
    lang_label = "Korean" if target["lang"] == "ko" else "English"
    accepted = []
    accepted_lower = set()
    # 2026-08-22: web_search 모델이 "2026 minimum wage and overtime pay/regulations/
    # updates..."처럼 살짝만 다른 문구를 수십 개 뱉는 경우가 실사용 테스트로 확인됨 —
    # 정확히 같은 문자열이 아니라서 accepted_lower만으론 못 걸러진다. 코퍼스 중복
    # 체크와 같은 어간(stemming) 방식으로 "이미 채택한 것들끼리"도 함께 확인한다.
    accepted_norms, accepted_wordsets = [], []
    cat_rr = 0  # 카테고리 미지정 후보를 라운드로빈으로 배정하기 위한 카운터
    grounded_any = False
    avoid_block = ""

    for round_i in range(MAX_ROUNDS):
        need = 50 - len(accepted)
        if need <= 0:
            break
        prompt = PROMPT_TMPL.format(
            today=today_str, domain=target["domain_desc"], count=min(15, need),
            categories=categories_str, example_category=target["categories"][0],
            lang_label=lang_label, avoid_block=avoid_block,
        )
        text, grounded = call_search_llm(client, prompt)
        grounded_any = grounded_any or grounded
        mention_rows = parse_mention_rows(text, target["categories"], observed_on=today_str)
        ranked_mentions = rank_mentioned_keywords(mention_rows, minimum_surfaces=2)
        candidates = [(kw, cat) for kw, cat, _metrics in ranked_mentions]

        for kw, cat in candidates:
            kl = kw.lower()
            if kl in accepted_lower:
                continue
            if overlaps_corpus(kw, corpus_norms + accepted_norms, corpus_wordsets + accepted_wordsets):
                continue
            if cat is None:
                cat = target["categories"][cat_rr % len(target["categories"])]
                cat_rr += 1
            accepted.append((kw, cat))
            accepted_lower.add(kl)
            accepted_norms.append(re.sub(r"[^a-z0-9가-힣]+", "", kl))
            accepted_wordsets.append(_sig_words(kw))
            if len(accepted) >= 50:
                break

        print(
            f"    라운드 {round_i+1}: 출처행 {len(mention_rows)}개, "
            f"2개 이상 출처군 명사 {len(candidates)}개 → 누적 채택 {len(accepted)}개"
        )
        if len(accepted) >= 50:
            break
        # 다음 라운드에서 같은 키워드를 또 제안받지 않도록 힌트 추가
        recent_sample = ", ".join(kw for kw, _ in accepted[-15:])
        avoid_block = (f"- Already used this round, do NOT repeat these or close variants: "
                        f"{recent_sample}\n" if recent_sample else "")
        time.sleep(2)

    return accepted[:50], grounded_any


def main():
    if not OPENAI_API_KEY and not GEMINI_API_KEY:
        print("❌ OPENAI_API_KEY, GEMINI_API_KEY 둘 다 없음")
        sys.exit(1)
    client = None
    if GEMINI_API_KEY:
        from google import genai as _genai
        client = _genai.Client(api_key=GEMINI_API_KEY)
    if OPENAI_API_KEY:
        print(f"검색 엔진: OpenAI({OPENAI_SEARCH_MODEL}) 1순위" +
              (", Gemini 폴백 가능" if client else ""))
    else:
        print("검색 엔진: Gemini만 사용 가능(OPENAI_API_KEY 없음)")
    today = datetime.datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    backup_dir = f"data/keywords/_backup_{today.strftime('%Y%m%d')}"

    print(f"=== 네트워크 전체({len(TARGETS)}개 사이트) 발행이력 코퍼스 수집 중 ===")
    all_titles_by_site = {}
    for target in TARGETS:
        titles = fetch_published_titles(target["url"])
        all_titles_by_site[target["url"]] = titles
        print(f"  {target['url']}: {len(titles)}건")
    corpus_norms, corpus_wordsets = build_network_corpus(all_titles_by_site)
    print(f"  네트워크 전체 코퍼스: 제목 {len(corpus_norms)}건\n")

    any_updated = False
    for target in TARGETS:
        path = target["file"]
        print(f"=== {path} 리서치 시작 ({today_str} 기준) ===")
        try:
            accepted, grounded_any = research_one_site(client, target, today_str, corpus_norms, corpus_wordsets)
        except Exception as e:
            print(f"  ❌ 리서치 실패({e}) — 이 사이트만 스킵, 기존 파일 유지\n")
            continue

        fresh_count = len(accepted)
        if fresh_count < 10:
            print(
                f"  ❌ 오늘자 교차출처 명사 {fresh_count}개 < 최소 10개 — "
                "기존 파일 유지(과거 키워드로 성공 위장 금지)"
            )
            continue

        if len(accepted) < 50:
            # 부족분은 기존 파일에서 코퍼스와 안 겹치는 항목만 살려서 채운다.
            # 항상 정확히 50개를 유지하기 위함(사용자 지시: "50개 항상 유지").
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    old_lines = [l.rstrip("\n") for l in f if l.strip()]
                accepted_lower = {kw.lower() for kw, _ in accepted}
                for old in old_lines:
                    if len(accepted) >= 50:
                        break
                    if "\t" not in old:
                        continue
                    kw, cat = old.split("\t", 1)
                    if kw.lower() in accepted_lower or cat not in target["categories"]:
                        continue
                    if overlaps_corpus(kw, corpus_norms, corpus_wordsets):
                        continue
                    accepted.append((kw, cat))
                    accepted_lower.add(kw.lower())
                print(f"    부족분을 기존 파일에서 {len(accepted)}개까지 보충")

        if len(accepted) < 25:
            print(f"  ❌ 최종 {len(accepted)}개 < 최소 25개 — 신뢰 못 함, 이번 갱신 스킵(기존 파일 유지)")
            continue

        os.makedirs(backup_dir, exist_ok=True)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                old_content = f.read()
            backup_path = os.path.join(backup_dir, os.path.basename(path))
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write(old_content)

        with open(path, "w", encoding="utf-8") as f:
            for kw, cat in accepted:
                f.write(f"{kw}\t{cat}\n")
        tag = "검색 그라운딩" if grounded_any else "모델 지식 폴백"
        print(
            f"  ✅ {len(accepted)}개 키워드로 교체 완료 "
            f"[오늘자 교차출처 명사 {fresh_count}개, {tag}]\n"
        )
        any_updated = True

    if not any_updated:
        print("\n⚠️ 갱신된 파일 없음")
        sys.exit(1)


if __name__ == "__main__":
    main()
