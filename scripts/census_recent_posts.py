#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
census_recent_posts.py
─────────────────────────────────────────────────────────────
27개 사이트의 "최근 발행 글" 전수조사. 사이트마다 최근 N개 글의
제목/발행일/SEO점수/링크를 가져와서 한눈에 볼 수 있는 리포트를 만든다.
자동 발행이 실제로 잘 돌고 있는지(사이트별 최근 발행일이 너무 오래됐는지,
SEO 점수가 낮은 글이 섞여 있는지) 확인하는 용도.

필요 환경변수: 사이트별 WP 비밀번호(예: KHEALTH365COM) — daily_rankmath_check.py,
publish_watchdog.py 등 기존 스크립트와 동일한 이름 사용.
"""
import os
import json
import requests
from datetime import datetime, timezone, timedelta

WP_USER = "huh0303@gmail.com"
KST = timezone(timedelta(hours=9))
POSTS_PER_SITE = 5
LOW_SEO_THRESHOLD = 80

SITES = [
    ("https://k-health365.com",        "KHEALTH365COM"),
    ("https://koreamedicaltour.com",   "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com",     "KOREAINVEST365COM"),
    ("https://ki-korea.com",           "KIKOREACOM"),
    ("https://koreainsurance365.com",  "KOREAINSURANCE365COM"),
    ("https://kfinance365.com",        "KFINANCE365COM"),
    ("https://koreataxnlaw.com",       "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com",     "KOREACRYPTO365COM"),
    ("https://krealestate365.com",     "KREALESTATE365COM"),
    ("https://ktech365.com",           "KTECH365COM"),
    ("https://oliveyoungkorea.com",    "OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com",          "KWORLD365COM"),
    ("https://k-trip365.com",          "KTRIP365COM"),
    ("https://k-visa365.com",          "KVISA365COM"),
    ("https://koreawedding365.com",    "KOREAWEDDING365COM"),
    ("https://kstudy365.com",          "KSTUDY365COM"),
    ("https://studyinkorea365.com",    "STUDYINKOREA365COM"),
    ("https://kieca-korea.org",        "KIECAKOREAORG"),
    ("https://ksa-korea.org",          "KSAKOREAORG"),
    ("https://sis-korea.com",          "SISKOREACOM"),
    ("https://jobkorea365.com",        "JOBKOREA365COM"),
    ("https://jobinkorea365.com",      "JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com",     "JOBKOREAGLOBALCOM"),
    ("https://korea365.org",           "KOREA365ORG"),
    ("https://koreanews365.com",       "KOREANEWS365COM"),
    ("https://theseouljournal.com",    "THESEOULJOURNALCOM"),
]


def log(msg):
    print(msg, flush=True)


def check_site(site_url, secret_name):
    pw = os.environ.get(secret_name)
    if not pw:
        return {"site": site_url, "status": "시크릿없음", "posts": []}

    auth = requests.auth.HTTPBasicAuth(WP_USER, pw)
    try:
        r = requests.get(
            f"{site_url}/wp-json/wp/v2/posts", auth=auth,
            params={"per_page": POSTS_PER_SITE, "orderby": "date", "order": "desc",
                    "status": "publish", "_fields": "id,date,link,title,meta"},
            timeout=20,
        )
    except Exception as e:
        return {"site": site_url, "status": f"오류: {str(e)[:150]}", "posts": []}

    if r.status_code != 200:
        return {"site": site_url, "status": f"HTTP {r.status_code}", "posts": []}

    items = r.json()
    if not items:
        return {"site": site_url, "status": "발행글없음", "posts": []}

    posts = []
    for p in items:
        title = p.get("title", {}).get("rendered", "")
        score = p.get("meta", {}).get("rank_math_seo_score")
        posts.append({
            "title": title[:70],
            "date": p.get("date", ""),
            "link": p.get("link", ""),
            "seo_score": score,
        })

    latest_date = posts[0]["date"]
    try:
        latest_dt = datetime.fromisoformat(latest_date)
        days_since = (datetime.now() - latest_dt).days
    except Exception:
        days_since = None

    return {"site": site_url, "status": "정상", "posts": posts,
            "latest_date": latest_date, "days_since_latest": days_since}


def main():
    checked_at = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    results = []
    for site_url, secret_name in SITES:
        result = check_site(site_url, secret_name)
        results.append(result)
        if result["status"] != "정상":
            log(f"[{site_url}] ⚠️ {result['status']}")
        else:
            low_seo = [p for p in result["posts"] if isinstance(p["seo_score"], (int, float)) and p["seo_score"] < LOW_SEO_THRESHOLD]
            flag = f" ⚠️SEO낮은글{len(low_seo)}건" if low_seo else ""
            stale = f" ⚠️최근발행 {result['days_since_latest']}일 전" if (result.get("days_since_latest") or 0) >= 2 else ""
            log(f"[{site_url}] 최근 {len(result['posts'])}건 (최신: {result['latest_date']}){flag}{stale}")
            for p in result["posts"]:
                log(f"   - ({p['date'][:10]}, SEO {p['seo_score']}) {p['title']}")

    # 요약
    no_access = [r["site"] for r in results if r["status"] == "시크릿없음"]
    errors = [r["site"] for r in results if r["status"] not in ("정상", "시크릿없음")]
    stale_sites = [r["site"] for r in results if r.get("days_since_latest") is not None and r["days_since_latest"] >= 2]

    log("\n" + "=" * 60)
    log(f"전체 {len(SITES)}개 사이트 중 정상 {len(SITES) - len(no_access) - len(errors)}개")
    if no_access:
        log(f"⚠️ 시크릿 없음 {len(no_access)}개: {', '.join(no_access)}")
    if errors:
        log(f"⚠️ 조회 오류 {len(errors)}개: {', '.join(errors)}")
    if stale_sites:
        log(f"⚠️ 최근 발행이 2일 이상 지난 사이트 {len(stale_sites)}개: {', '.join(stale_sites)}")

    with open("census_recent_posts_result.json", "w", encoding="utf-8") as f:
        json.dump({"checked_at": checked_at, "results": results}, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
