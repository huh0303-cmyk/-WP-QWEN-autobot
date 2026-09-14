#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_fake_personas_27sites.py
─────────────────────────────────────────────────────────────
27개 사이트 전체 발행글에서 실존 확인이 안 되는 특정 개인의 전문가 사칭
(의사/교수/변호사/세무사/공인중개사 등 + 소속기관 인용) 패턴을 탐지하고,
Gemini로 "그 부분만" 기관명 인용으로 안전하게 재작성한다.
(fix_fake_personas.py의 k-health365 전용 로직을 27개 사이트로 확장)

안전장치:
- 재작성은 매칭된 문장 주변만 최소 수정하도록 강하게 지시, 나머지 본문은 그대로 유지
- 재작성 후 길이가 원문 대비 ±20% 벗어나면 "이상치"로 보고 자동 반영하지 않고 로그만 남김
- 재작성 후에도 패턴이 남아있으면 스킵
- APPLY_FIX=False로 실행하면 탐지/재작성 결과만 로그로 남기고 실제 반영은 안 함
"""
import os
import re
import sys
import json
import time
import requests

# Windows 로컬 콘솔(cp949 등)에서 이모지/한글 출력 시 죽지 않도록 UTF-8 강제
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

APPLY_FIX = os.environ.get("APPLY_FIX", "true").lower() != "false"

WP_USER = "huh0303@gmail.com"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

SITES = [
    ("https://k-health365.com", "KHEALTH365COM"),
    ("https://koreamedicaltour.com", "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com", "KOREAINVEST365COM"),
    ("https://ki-korea.com", "KIKOREACOM"),
    ("https://koreainsurance365.com", "KOREAINSURANCE365COM"),
    ("https://kfinance365.com", "KFINANCE365COM"),
    ("https://koreataxnlaw.com", "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com", "KOREACRYPTO365COM"),
    ("https://krealestate365.com", "KREALESTATE365COM"),
    ("https://ktech365.com", "KTECH365COM"),
    ("https://kskin365.com", "KSKIN365COM"),
    ("https://oliveyoungkorea.com", "OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com", "KWORLD365COM"),
    ("https://k-trip365.com", "KTRIP365COM"),
    ("https://k-visa365.com", "KVISA365COM"),
    ("https://koreawedding365.com", "KOREAWEDDING365COM"),
    ("https://kstudy365.com", "KSTUDY365COM"),
    ("https://studyinkorea365.com", "STUDYINKOREA365COM"),
    ("https://kieca-korea.org", "KIECAKOREAORG"),
    ("https://ksa-korea.org", "KSAKOREAORG"),
    ("https://sis-korea.com", "SISKOREACOM"),
    ("https://jobkorea365.com", "JOBKOREA365COM"),
    ("https://jobinkorea365.com", "JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com", "JOBKOREAGLOBALCOM"),
    ("https://korea365.org", "KOREA365ORG"),
    ("https://koreanews365.com", "KOREANEWS365COM"),
    ("https://theseouljournal.com", "THESEOULJOURNALCOM"),
]

# ── 한글 패턴: 이름+직함, 기관+직함 ─────────────────────────────
NAME_TITLE_PATTERN = re.compile(
    r'[가-힣]{2,4}\s*(교수|원장|대표\s*변호사|변호사|세무사|공인중개사|재무설계사|박사)')
INSTITUTION_EXPERT_PATTERN = re.compile(
    r'[가-힣]{2,12}(대학교병원|대학병원|병원|법률사무소|세무법인|공인중개사사무소|회계법인)'
    r'\s*[가-힣]{0,8}\s*(전문의|변호사|세무사|대표|원장)')
FAKE_EXPERIENCE_PATTERN = re.compile(r'(임상경력|경력|근무경력)\s*\d{1,2}\s*년')

# ── 영문 패턴: Dr./Attorney/특정 경력 연차 주장 ──────────────────
EN_DR_NAME_PATTERN = re.compile(r'\bDr\.\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b')
EN_TITLE_NAME_PATTERN = re.compile(
    r'\b(Attorney|CPA|Esq\.?|Realtor)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b')
EN_EXPERIENCE_PATTERN = re.compile(
    r'\b\d{1,2}[\s-]years?\s+of\s+experience\s+as\s+an?\s+[a-zA-Z\s]{3,30}\b', re.IGNORECASE)

ALL_PATTERNS = [NAME_TITLE_PATTERN, INSTITUTION_EXPERT_PATTERN, FAKE_EXPERIENCE_PATTERN,
                EN_DR_NAME_PATTERN, EN_TITLE_NAME_PATTERN, EN_EXPERIENCE_PATTERN]


def log(msg):
    print(msg, flush=True)


def find_matches(html):
    matches = set()
    for pat in ALL_PATTERNS:
        matches |= set(m.group(0) for m in pat.finditer(html))
    return matches


def fetch_all_posts(site_url, pw):
    posts = []
    page = 1
    while True:
        r = requests.get(f"{site_url}/wp-json/wp/v2/posts",
                          auth=(WP_USER, pw),
                          params={"per_page": 50, "page": page, "status": "publish",
                                  "_fields": "id,title,link,content"},
                          timeout=25)
        if r.status_code != 200:
            break
        batch = r.json()
        if not isinstance(batch, list) or not batch:
            break
        posts.extend(batch)
        if len(batch) < 50:
            break
        page += 1
    return posts


def gemini_rewrite(html, matches, lang_hint):
    if lang_hint == "ko":
        instr = ('"대한의학회에 따르면", "관련 기관 가이드라인에 의하면", '
                  '"국내 대형 로펌/세무법인 사례에 따르면" 등 기관명 기반 인용으로')
    else:
        instr = ('phrases like "according to industry guidelines", '
                  '"based on official government resources", "per professional association standards"')
    prompt = f"""아래는 블로그 글의 HTML 본문입니다.
이 본문 안에 실존 확인이 되지 않는 특정 개인(가상의 교수/원장/전문의/변호사/세무사 등)이
특정 기관 소속으로 인용되거나, 근거 없는 경력 연차가 주장된 부분이 있습니다.
발견된 패턴: {', '.join(list(matches)[:8])}

**지시사항 (매우 중요):**
1. 위 패턴이 포함된 문장만 찾아서, 특정 개인 이름/소속/경력연차를 지어내는 대신
   {instr} 바꾸세요.
2. 그 외 나머지 본문은 단 한 글자도 바꾸지 마세요. HTML 구조, 다른 문장, 문단 순서 전부 원본 그대로 유지.
3. 출력은 전체 수정된 HTML 본문만 출력하세요. 설명, 주석, 마크다운 코드블록 표시 없이 순수 HTML만.

원본 본문:
{html}
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    try:
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=60)
        r.raise_for_status()
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        log(f"   ⚠️ Gemini 오류: {e}")
        return None


def process_site(site_url, pw, lang_hint):
    posts = fetch_all_posts(site_url, pw)
    flagged = []
    for p in posts:
        html = p.get("content", {}).get("rendered", "")
        matches = find_matches(html)
        if matches:
            flagged.append((p, matches))

    result = {"site": site_url, "total_posts": len(posts), "flagged": len(flagged),
              "fixed": [], "skipped": [], "failed": []}

    for p, matches in flagged:
        title = re.sub(r'<[^>]+>', '', p.get("title", {}).get("rendered", ""))
        html = p.get("content", {}).get("rendered", "")
        new_html = gemini_rewrite(html, matches, lang_hint)
        time.sleep(1.5)

        if not new_html:
            result["failed"].append({"id": p["id"], "title": title, "reason": "gemini_error"})
            continue

        old_len, new_len = len(html), len(new_html)
        ratio = new_len / old_len if old_len else 0
        if ratio < 0.8 or ratio > 1.2:
            result["skipped"].append({"id": p["id"], "title": title,
                                       "reason": f"length_ratio_{ratio:.0%}"})
            continue

        remaining = find_matches(new_html)
        if remaining:
            result["skipped"].append({"id": p["id"], "title": title,
                                       "reason": f"pattern_remains: {list(remaining)[:3]}"})
            continue

        if APPLY_FIX:
            up = requests.post(f"{site_url}/wp-json/wp/v2/posts/{p['id']}",
                                auth=(WP_USER, pw),
                                json={"content": new_html}, timeout=30)
            if up.status_code in (200, 201):
                result["fixed"].append({"id": p["id"], "title": title})
            else:
                result["failed"].append({"id": p["id"], "title": title,
                                          "reason": f"http_{up.status_code}"})
        else:
            result["fixed"].append({"id": p["id"], "title": title, "dry_run": True})

    return result


def main():
    if not GEMINI_API_KEY:
        log("❌ GEMINI_API_KEY 없음")
        raise SystemExit(1)

    all_results = []
    for site_url, env_key in SITES:
        pw = os.environ.get(env_key, "")
        if not pw:
            log(f"⚠️  {site_url} — Secret 없음, 스킵")
            continue
        lang_hint = "en" if site_url not in (
            "https://k-health365.com", "https://ki-korea.com",
            "https://krealestate365.com", "https://koreanews365.com") else "ko"

        log(f"🔍 {site_url} 검사 중...")
        result = process_site(site_url, pw, lang_hint)
        all_results.append(result)
        log(f"   전체 {result['total_posts']}건 / 탐지 {result['flagged']}건 / "
            f"수정 {len(result['fixed'])} / 스킵 {len(result['skipped'])} / "
            f"실패 {len(result['failed'])}")

    with open("fix_fake_personas_27sites_result.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    total_flagged = sum(r["flagged"] for r in all_results)
    total_fixed = sum(len(r["fixed"]) for r in all_results)
    log(f"\n전체 요약: 탐지 {total_flagged}건 / 수정 {total_fixed}건 "
        f"(APPLY_FIX={APPLY_FIX})")


if __name__ == "__main__":
    main()
