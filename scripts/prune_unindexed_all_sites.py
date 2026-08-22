#!/usr/bin/env python3
"""2026-08-22 사용자 지시 — 26개 활성 사이트 전체에서, 진짜 구글 색인된 글만
남기고 나머지는 비공개 전환한다.

정확도가 생명이라 사이트맵 API의 'indexed' 카운트(오늘 하루 종일 부정확한 걸
확인함)는 절대 안 쓰고, urlInspection API로 글 하나하나 실제 verdict를 확인한다.
조회 실패/에러/quota소진 등 불확실한 경우는 안전하게 건드리지 않는다
([[feedback_never_hide_indexed_posts]] 원칙 — 색인된 걸 실수로 비공개
처리하느니 차라리 저품질 글을 안 건드리는 쪽이 훨씬 안전).
"""
import os
import sys
import time
import json

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from daily_site_traffic import get_gsc_token, gsc_get  # noqa: E402
from site_registry import ACTIVE_SITES  # noqa: E402

WP_USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
SLEEP_BETWEEN_INSPECT = 1.1
RESULTS_PATH = "prune_unindexed_result.json"


def inspect(token, prop, url, max_retries=3):
    for attempt in range(max_retries):
        r = requests.post(
            "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"inspectionUrl": url, "siteUrl": prop}, timeout=30)
        if r.status_code == 200:
            s = r.json().get("inspectionResult", {}).get("indexStatusResult", {})
            return {"ok": True, "verdict": s.get("verdict"), "coverageState": s.get("coverageState")}
        if r.status_code == 429:
            time.sleep(5 * (attempt + 1))
            continue
        return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:150]}"}
    return {"ok": False, "error": "429 재시도 소진"}


def fetch_posts(site_url):
    posts = []
    page = 1
    while True:
        r = requests.get(f"{site_url}/wp-json/wp/v2/posts",
                          params={"status": "publish", "per_page": 100, "page": page,
                                   "_fields": "id,link"},
                          headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        if r.status_code == 400 and "rest_post_invalid_page_number" in r.text:
            break
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return posts


def set_private(site_url, pw, post_id):
    r = requests.post(f"{site_url}/wp-json/wp/v2/posts/{post_id}",
                       auth=(WP_USER, pw), json={"status": "private"}, timeout=30)
    return r.status_code in (200, 201)


def main():
    token = get_gsc_token()
    accessible_resp = gsc_get(token, "/sites")
    accessible = {s.get("siteUrl") for s in accessible_resp.json().get("siteEntry", [])} \
        if accessible_resp.status_code == 200 else set()

    all_results = {}
    for site_url, env_key, lifecycle in ACTIVE_SITES:
        domain = site_url.replace("https://", "")
        pw = os.environ.get(env_key, "")
        if not pw:
            print(f"\n=== {domain}: {env_key} 시크릿 없음, 스킵 ===")
            continue

        domain_property = f"sc-domain:{domain}"
        prop = site_url if site_url in accessible else (domain_property if domain_property in accessible else None)
        if not prop:
            print(f"\n=== {domain}: GSC 속성 없음, 스킵 ===")
            continue

        try:
            posts = fetch_posts(site_url)
        except Exception as e:
            print(f"\n=== {domain}: 글목록 조회 실패({e}), 스킵 ===")
            continue

        print(f"\n=== {domain}: 공개글 {len(posts)}개, urlInspection 시작 ===")
        indexed = kept_unsure = made_private = failed = 0
        for p in posts:
            res = inspect(token, prop, p["link"])
            time.sleep(SLEEP_BETWEEN_INSPECT)
            if not res["ok"]:
                kept_unsure += 1
                continue
            if res["verdict"] == "PASS":
                indexed += 1
                continue
            # 확실히 미색인으로 판정된 경우만 비공개 전환
            ok = set_private(site_url, pw, p["id"])
            if ok:
                made_private += 1
            else:
                failed += 1

        summary = {"total_posts": len(posts), "indexed_kept_public": indexed,
                   "unsure_left_alone": kept_unsure, "made_private": made_private,
                   "private_failed": failed}
        all_results[domain] = summary
        print(f"    결과: {summary}")

        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)

    print("\n\n=== 전체 요약 ===")
    print(json.dumps(all_results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
