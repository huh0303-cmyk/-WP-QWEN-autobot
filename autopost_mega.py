#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordPress AI 자동 포스팅 봇 - HIGH-END MEGA 3중 백업 및 완벽 SEO 시스템
[실시간 구글 스프레드시트 업데이트 연동 버전]
- 1차 LLM: Groq Qwen-2.5-72b-instruct
- 2차 LLM: Google Gemini 2.5 Flash (통신 및 한도 초과 백업)
- 3차 LLM: 내장형 도메인 박사 정적 HTML 생성 시스템 (무조건 발행 보장)
- 이미지 백업: Pixabay API 우선 검색 -> 실패 시 Pexels API 백업 호출
- 루프 보장: SEO 평가 스코어 80점 미만 시 최대 3회 자동 재작성 및 피드백 루프 작동
- 실시간 동기화: 발행 성공/실패 여부와 SEO 점수를 지정된 구글 시트 웹훅으로 실시간 전송
"""

import os
import json
import time
import random
import requests
import base64
import re
import threading
from datetime import datetime, date

# OpenAI 라이브러리 안전 로드 및 초기화 오류 원천 차단
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# 데이터 구조 선로드 (환경에 맞게 파일이 없다면 예외처리 가동)
try:
    from sites_config import SITES
    from keywords_all import KEYWORDS
except ImportError:
    # 모듈이 없을 경우를 대비한 하드코딩 기본 샘플 데이터셋 제공
    SITES = [
        {"url": "https://k-health365.com", "lang": "ko", "theme": "건강 및 의학 보건 정보", "keywords_file": "health_kw.txt", "category_id": 964, "style": "news"},
        {"url": "https://koreanews365.com", "lang": "ko", "theme": "시사 종합 및 라이프 뉴스", "keywords_file": "news_kw.txt", "category_id": 1, "style": "news"},
        {"url": "https://theseouljournal.com", "lang": "en", "theme": "Korean culture, business, and daily life guide", "keywords_file": "seoul_kw.txt", "category_id": 1, "style": "blog"}
    ]
    KEYWORDS = {
        "health_kw.txt": "오메가3 고르는법\n비타민D 하루권장량\n고혈압 낮추는 방법",
        "news_kw.txt": "2026년 부동산 전망\n청년도약계좌 조건",
        "seoul_kw.txt": "Seoul travel itinerary\nK-beauty skincare routine"
    }

# ══════════════════════════════════════════════
#  ★ 인프라 자산 인코딩 및 보안 변수 선언 ★
# ══════════════════════════════════════════════
QWEN_API_KEY    = os.environ.get("QWEN_API_KEY", "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")
OPENAI_API_KEY  = os.environ.get("OPENAI_API_KEY", QWEN_API_KEY) # 내부 OpenAI 엔진용 우회 처리
QWEN_MODEL      = "qwen-2.5-72b-instruct"
QWEN_API_URL    = "https://api.groq.com/openai/v1/chat/completions"

GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "AIzaSyD-Your-Actual-Gemini-Key-Here")
GEMINI_MODEL    = "gemini-2.5-flash"

PIXABAY_KEY     = os.environ.get("PIXABAY_KEY", "u_g0pmau3m85")
PEXELS_KEY      = os.environ.get("PEXELS_KEY", "41q16JQ0qBM123kTUgEk2YKAfK3e43l6NCErWoWn0Fv41Zmdfub0XAs8")
INDEXNOW_KEY    = "khealth365indexnow2024"

# 제공해주신atutobot 구글 스프레드시트와 연결된 Apps Script 웹훅 URL 앱 주소 입력
SHEETS_WEBHOOK  = os.environ.get("SHEETS_WEBHOOK", "https://script.google.com/macros/s/YOUR_APPS_SCRIPT_DEPLOY_ID/exec")

WP_USERNAME     = "huh0303@gmail.com"
WP_PASS_DEFAULT = "A3sK VQud Xday 1ait Zl0d ZAA2"

WP_PASSWORDS = {
    "k-health365.com":        os.environ.get("WP_PASS_HEALTH", "A3sK VQud Xday 1ait Zl0d ZAA2"),
    "koreanews365.com":       os.environ.get("WP_PASS_NEWS", "MSqZ PAhu UpBL 2B1W cDle 4DEO"),
    "theseouljournal.com":    os.environ.get("WP_PASS_JOURNAL", "Z7S7 97p2 vEBC gTxe sVDb hnMY"),
}

DAILY_LIMIT     = 10
MIN_GAP_MIN     = 30

REPORTER_POOL_KR = ["전문기자 김윤서", "전문기자 이현수", "수석기자 김상준", "전문기자 박지아", "전문기자 정도윤"]
REPORTER_POOL_EN = ["Sarah Mitchell", "James Anderson", "Emily Carter", "David Thompson", "Rachel Bennett"]

# OpenAI 클라이언트 안전 초기화 (에러 원인 제거)
client_qwen = None
if OpenAI is not None and OPENAI_API_KEY:
    try:
        client_qwen = OpenAI(api_key=OPENAI_API_KEY)
    except Exception:
        client_qwen = None

def get_domain(url):
    return url.replace("https://", "").replace("http://", "").rstrip("/")

ALL_DOMAINS_EN = [get_domain(s["url"]) for s in SITES if s.get("lang") == "en"]

def pick_reporter(lang="en"):
    return random.choice(REPORTER_POOL_KR if lang == "ko" else REPORTER_POOL_EN)

# ══════════════════════════════════════════════
#  ★ 구글 스프레드시트 실시간 전송 커넥터 ★
# ══════════════════════════════════════════════
def send_to_google_sheets_live(row_data):
    if not SHEETS_WEBHOOK or "YOUR_APPS_SCRIPT_DEPLOY_ID" in SHEETS_WEBHOOK:
        return
    try:
        response = requests.post(SHEETS_WEBHOOK, json=row_data, timeout=12)
        if response.status_code == 200:
            print("      📊 [구글 시트] 실시간 진행 상황 업데이트 완료.")
    except Exception as e:
        print(f"      ⚠️ [구글 시트] 실시간 통신 장애 발생: {e}")

# ══════════════════════════════════════════════
#  ★ 고성능 2단계 이미지 인프라 백업 엔진 ★
# ══════════════════════════════════════════════
def get_image_backup_system(query):
    try:
        url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={requests.utils.quote(query)}&image_type=photo&orientation=horizontal&per_page=5&safesearch=true"
        r = requests.get(url, timeout=10)
        hits = r.json().get("hits", [])
        if hits:
            p = random.choice(hits)
            return {"src": p["webformatURL"], "credit": 'Image from <a href="https://pixabay.com" target="_blank">Pixabay</a>'}
    except Exception:
        pass

    try:
        url = f"https://api.pexels.com/v1/search?query={query}&per_page=5&orientation=landscape"
        r = requests.get(url, headers={"Authorization": PEXELS_KEY}, timeout=10)
        photos = r.json().get("photos", [])
        if photos:
            p = random.choice(photos)
            return {"src": p["src"]["large2x"] or p["src"]["large"], "credit": f'Photo by {p["photographer"]} on <a href="{p["url"]}" target="_blank">Pexels</a>'}
    except Exception:
        pass

    return {}

# ══════════════════════════════════════════════
#  ★ 3단계 분기 보장형 고성능 글쓰기 엔진 ★
# ══════════════════════════════════════════════
def call_writer_triple_engine(prompt, keyword, lang="ko", theme=""):
    # 1차 엔진: Qwen API 호출
    try:
        headers = {"Authorization": f"Bearer {QWEN_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": QWEN_MODEL,
            "messages": [
                {"role": "system", "content": "You are a master of WordPress SEO content generation, maximizing mobile layouts with extensive paragraph splitting."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7, "max_tokens": 4096
        }
        r = requests.post(QWEN_API_URL, headers=headers, json=payload, timeout=50)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"      ❌ [1차 엔진: Qwen] 실패: {e} -> 2차 Gemini 시스템으로 인계합니다.")

    # 2차 엔진: Gemini API 호출
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096}
        }
        r = requests.post(url, json=payload, timeout=50)
        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"      ❌ [2차 엔진: Gemini] 실패: {e} -> 3차 정적 복구 시스템 강제 조립 개시.")

    # 3차 엔진: 최종 안전 백업 가동
    return generate_fallback_static_html(keyword, lang, theme)


def generate_fallback_static_html(keyword, lang, theme):
    title = f"TITLE: {keyword}에 대한 아무도 모르는 역대급 비밀 및 필수 관리 지침 가이드"
    if lang != "ko":
        title = f"TITLE: The Ultimate Master Guide to {keyword} - Critical Insights Revealed"
    
    return f"{title}\n\n<p>안녕하세요. {theme} 전문 임상 분석 데이터를 기반으로 신뢰할 수 있는 가이드를 전해드리는 전문 연구 지표 블로그입니다.</p><h2>1. {keyword} 핵심 배경</h2><p>우리가 느끼는 미세한 변화는 정밀하게 계산된 누적 결과물입니다.</p>"

# ══════════════════════════════════════════════
#  ★ 본문 파싱 및 SEO 정밀 스코어링 시스템 ★
# ══════════════════════════════════════════════
def process_content_layout(raw, site_url):
    raw = raw.strip()
    raw = re.sub(r'^```[a-zA-Z]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw)
    raw = raw.strip()

    lines = raw.split("\n")
    title, meta, tags_str, content = "", "", "", raw

    for i, line in enumerate(lines):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip().strip('`"\' ')
        if "META_DESCRIPTION:" in line:
            meta = line.split("META_DESCRIPTION:")[-1].replace("-->", "").strip()
        if "TAGS:" in line:
            tags_str = line.split("TAGS:")[-1].replace("-->", "").strip()
        if title:
            content = "\n".join(lines[i+1:])
            break

    def img_replacer(m):
        query_text = m.group(1).strip()
        alt_text = m.group(2).strip() if len(m.groups()) > 1 else query_text
        img = get_image_backup_system(query_text)
        if img:
            return (f'\n\n<figure class="wp-block-image size-large aligncenter">'
                    f'<img src="{img["src"]}" alt="{alt_text}" loading="lazy" style="max-width:100%;height:auto;border-radius:8px;"/>'
                    f'<figcaption style="text-align:center;font-size:13px;color:#666;">{img["credit"]}</figcaption></figure>\n\n')
        return f'\n\n<p><em>[Image Reference: {alt_text}]</em></p>\n\n'

    content = re.sub(r']+),?\s*([^-->]*)\s*-->', img_replacer, content, flags=re.IGNORECASE)
    content = re.sub(r'\[Image:\s*([^\]]+)\]', img_replacer, content, flags=re.IGNORECASE)

    if "SCHEMA_FAQ" in content and "<script" not in content:
        content += '\n<script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}</script>'

    if not meta:
        meta = f"Professional comprehensive overview report highlighting critical guidelines on {title}."

    tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else ["AI포스팅", "웰니스뉴스"]

    return {"title": title or "Auto Generated Post", "content": content, "meta": meta, "tags": tags}


def calculate_seo_score(parsed, keyword, lang="ko"):
    c, t, m = parsed["content"], parsed["title"], parsed["meta"]
    first_word = keyword.split()[0].lower()
    
    checks = [
        ("제목 키워드 포함", first_word in t.lower()),
        ("메타 설명문 충분성", len(m) >= 40),
        ("본문 최소 볼륨", len(c) >= 2200),
        ("H2 대분류 배치(3개이상)", c.count("<h2") >= 3),
        ("H3 소분류 세분화(3개이상)", c.count("<h3") >= 3),
        ("미디어 소스 이미지 바인딩", "<img" in c),
        ("데이터 요약 HTML 테이블", c.count("<table") >= 1),
        ("강조 태그 활용성", c.count("<strong>") >= 5),
        ("FAQ 아키텍처 수립", "faq" in c.lower() or "자주 묻는" in c),
        ("아웃바운드 신뢰 링크", "href=" in c)
    ]
    
    passed_count = sum(1 for _, ok in checks if ok)
    score = int((passed_count / len(checks)) * 100)
    return score, checks

# ══════════════════════════════════════════════
#  ★ 워드프레스 포스팅 커넥터 메인 루틴 ★
# ══════════════════════════════════════════════
def get_tag_ids(site_url, auth_token, tags):
    tag_ids = []
    for tag in tags[:8]:
        try:
            r = requests.post(f"{site_url.rstrip('/')}/wp-json/wp/v2/tags",
                              headers={"Authorization": f"Basic {auth_token}", "Content-Type": "application/json"},
                              json={"name": tag}, timeout=10)
            if r.status_code in [200, 201]:
                tag_ids.append(r.json().get("id"))
            elif r.status_code == 400:
                sr = requests.get(f"{site_url.rstrip('/')}/wp-json/wp/v2/tags?search={requests.utils.quote(tag)}",
                                  headers={"Authorization": f"Basic {auth_token}"}, timeout=10)
                if sr.json():
                    tag_ids.append(sr.json()[0]["id"])
        except Exception:
            pass
    return tag_ids


def post_to_wordpress_platform(site, parsed, keyword):
    domain = get_domain(site["url"])
    pwd = WP_PASSWORDS.get(domain, WP_PASS_DEFAULT)
    auth = base64.b64encode(f"{WP_USERNAME}:{pwd}".encode()).decode()

    tag_ids = get_tag_ids(site["url"], auth, parsed.get("tags", []))
    
    url = f"{site['url'].rstrip('/')}/wp-json/wp/v2/posts"
    payload = {
        "title": parsed["title"],
        "content": parsed["content"],
        "status": "publish",
        "categories": [site.get("category_id", 1)],
        "tags": tag_ids,
        "meta": {
            "rank_math_focus_keyword": keyword,
            "rank_math_description":   parsed["meta"],
            "_yoast_wpseo_focuskw":    keyword,
            "_yoast_wpseo_metadesc":   parsed["meta"],
        }
    }
    try:
        r = requests.post(url, headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"}, json=payload, timeout=30)
        if r.status_code in [200, 201]:
            return r.json().get("id"), r.json().get("link"), "success"
        return None, None, f"HTTP Error {r.status_code}"
    except Exception as e:
        return None, None, str(e)


def run_indexnow(site_url, post_url):
    host = get_domain(site_url)
    endpoints = ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]
    for ep in endpoints:
        try:
            requests.post(ep, json={
                "host": host, "key": INDEXNOW_KEY,
                "keyLocation": f"{site_url}/{INDEXNOW_KEY}.txt",
                "urlList": [post_url]
            }, timeout=10)
        except:
            pass


def build_seo_prompt_studio(keyword, site, lang="ko"):
    reporter = pick_reporter(lang)
    if lang == "ko":
        return f"당신은 {site['theme']} 최고 권위 전문가이자 수석기자 {reporter}입니다. [포커스 주제어]: {keyword}에 관한 구글 상위 노출용 HTML 블로그 글을 작성하세요. 스마트폰 가독성을 위해 한 문단(<p>태그 블록) 내부에는 무조건 단 1개의 문장만 넣고, 문단 사이마다 소스코드상 명확한 빈 줄 공백 개행을 두어야 합니다. H2 태그 4개 이상, H3 태그 5개 이상, 데이터 요약 표(Table) 2개 이상을 반드시 포함하고 최하단에는 FAQ 5쌍을 배치하세요. 첫 줄에 TITLE: [제목] 형태로 출력하고 다음 줄은 비운 뒤 HTML 본문만 출력하세요."
    else:
        return f"You are {reporter}, an expert in {site['theme']}. Write an SEO-optimized WordPress article matching Google standards for [FOCUS KEYWORD]: {keyword}. Every paragraph (<p> block) MUST contain exactly ONE sentence with explicit empty line spaces between them. Include 4+ <h2>, 5+ <h3>, 2+ structured tables, and 5 FAQ Q&As. Line 1 MUST read exactly: TITLE: [Your Title]."

# ══════════════════════════════════════════════
#  ★ 코어 코디네이터 오토포스팅 프로세스 루프 ★
# ══════════════════════════════════════════════
def process_single_site_automation(site, results_list, lock):
    domain = get_domain(site["url"])
    lang = site.get("lang", "ko")
    
    raw_kw = KEYWORDS.get(site["keywords_file"], "")
    all_kws = [l.strip() for l in raw_kw.strip().split("\n") if l.strip()]
    if not all_kws:
        return

    target_kws = all_kws[:min(len(all_kws), 2)]
    
    print(f"\n[🚀 오토 엔진 가동] 대상 도메인: {domain} ({lang.upper()})")

    for idx, kw in enumerate(target_kws):
        print(f"   └─> ({idx+1}/{len(target_kws)}) 핵심 검색어 빌딩: '{kw}'")
        
        prompt = build_seo_prompt_studio(kw, site, lang)
        
        attempt = 1
        max_attempts = 3
        final_parsed = None
        final_score = 0
        
        while attempt <= max_attempts:
            raw_output = call_writer_triple_engine(prompt, kw, lang, site["theme"])
            if not raw_output:
                attempt += 1
                continue
                
            parsed = process_content_layout(raw_output, site["url"])
            score, check_list = calculate_seo_score(parsed, kw, lang)
            
            if score >= 80:
                final_parsed = parsed
                final_score = score
                break
            else:
                prompt += "\n\n[품질 미달 피드백] Table, Bold, 구조화 개수 요건 및 모바일 가독성 개행을 대폭 강화하여 다시 작성하십시오."
                final_parsed = parsed
                final_score = score
                attempt += 1
                time.sleep(3)
        
        if final_parsed:
            pid, purl, status_msg = post_to_wordpress_platform(site, final_parsed, kw)
            if pid:
                run_indexnow(site["url"], purl)
                print(f"      ✅ [발행 성공] 포스트 ID: {pid} -> 점수: {final_score}점 | {purl}")
                status_log = "✅ SUCCESS"
            else:
                print(f"      ❌ [워드프레스 인젝션 실패] 원인: {status_msg}")
                status_log = f"❌ WP_FAIL ({status_msg})"
        else:
            status_log = "❌ CRITICAL_LLM_FAIL"
            purl = ""

        # 스프레드시트 실시간 전송용 가공 로우 데이터 생성
        row_payload = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "domain": domain,
            "keyword": kw,
            "title": final_parsed["title"] if final_parsed else "생성 실패",
            "seo_score": final_score,
            "status": status_log,
            "url": purl
        }

        # 🎯 지정해주신 시트로 실시간 전송 트리거 가동
        send_to_google_sheets_live(row_payload)

        with lock:
            results_list.append(row_payload)


def main():
    print(f"\n{'═'*60}\n  🕸️ MEGA BOT SYSTEM V3 (실시간 구글 시트 스트리밍 탑재)\n{'═'*60}")
    results = []
    global_lock = threading.Lock()
    threads = []

    for site in SITES:
        t = threading.Thread(target=process_single_site_automation, args=(site, results, global_lock))
        threads.append(t)
        t.start()
        time.sleep(2)

    for t in threads:
        t.join()

    output_filename = f"report_execution_{date.today().strftime('%Y%m%d')}.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
