#!/usr/bin/env python3
"""25개 블로그 색인 정리.

- 뉴스 2개는 제외.
- kskin365.com / oliveyoungkorea.com 은 사용자 지시대로 기존 공개글 전부 비공개.
- 나머지 블로그는 Google Search Console URL Inspection API로 공개글을 하나씩 검사.
- verdict == PASS 인 글만 공개 유지.
- PASS가 아닌 확인된 비색인 글은 WordPress status=private 로 전환.
- API 오류/쿼터/권한 문제처럼 판정이 불확실한 글은 건드리지 않는다.
- 삭제는 하지 않는다.
"""

import json
import os
import sys
import time
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_registry import ACTIVE_SITES  # noqa: E402
from daily_site_traffic import get_gsc_token, gsc_get  # noqa: E402

WP_USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
RESULTS_PATH = "prune_unindexed_result.json"
NEWS_DOMAINS = {"koreanews365.com", "theseouljournal.com"}
FULL_RESET_DOMAINS = {"kskin365.com", "oliveyoungkorea.com"}


def fetch_posts(site_url):
    posts, page = [], 1
    while True:
        r = requests.get(
            f"{site_url}/wp-json/wp/v2/posts",
            params={"status": "publish", "per_page": 100, "page": page, "_fields": "id,link,title"},
            headers={"User-Agent": "Mozilla/5.0"}, timeout=35,
        )
        if r.status_code == 400 and "rest_post_invalid_page_number" in r.text:
            break
        if r.status_code != 200:
            raise RuntimeError(f"글목록 HTTP {r.status_code}: {r.text[:180]}")
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return posts


def title_of(post):
    t = post.get("title") or ""
    return t.get("rendered", "") if isinstance(t, dict) else str(t)


def set_private(site_url, pw, post_id):
    r = requests.post(
        f"{site_url}/wp-json/wp/v2/posts/{post_id}",
        auth=(WP_USER, pw), json={"status": "private"}, timeout=35,
    )
    return r.status_code in (200, 201), r.status_code, r.text[:180]


def inspect_url(token, prop, url, retries=3):
    for attempt in range(retries):
        r = requests.post(
            "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"inspectionUrl": url, "siteUrl": prop}, timeout=30,
        )
        if r.status_code == 200:
            s = r.json().get("inspectionResult", {}).get("indexStatusResult", {})
            return {
                "ok": True,
                "verdict": s.get("verdict"),
                "coverageState": s.get("coverageState"),
                "indexingState": s.get("indexingState"),
                "robotsTxtState": s.get("robotsTxtState"),
                "lastCrawlTime": s.get("lastCrawlTime"),
            }
        if r.status_code == 429:
            time.sleep(5 * (attempt + 1))
            continue
        return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:180]}"}
    return {"ok": False, "error": "429 재시도 소진"}


def property_for(domain, site_url, accessible):
    prefix = site_url.rstrip("/") + "/"
    domain_prop = f"sc-domain:{domain}"
    if prefix in accessible:
        return prefix
    if domain_prop in accessible:
        return domain_prop
    # 일부 등록은 https://domain 형식으로 슬래시 없이 저장된 경우 방어
    if site_url in accessible:
        return site_url
    return None


def save(data):
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    results = {}
    token = get_gsc_token()
    resp = gsc_get(token, "/sites")
    if resp.status_code != 200:
        raise RuntimeError(f"GSC 사이트 목록 실패 HTTP {resp.status_code}: {resp.text[:180]}")
    accessible = {x.get("siteUrl") for x in resp.json().get("siteEntry", []) if x.get("siteUrl")}

    targets = [row for row in ACTIVE_SITES if row[0].replace("https://", "").rstrip("/") not in NEWS_DOMAINS]
    print(f"대상 블로그 {len(targets)}개 / 뉴스 2개 제외")

    for site_url, env_key, lifecycle in targets:
        site_url = site_url.rstrip("/")
        domain = site_url.replace("https://", "").rstrip("/")
        pw = os.getenv(env_key, "").strip()
        if not pw:
            results[domain] = {"status": "SKIP_NO_SECRET", "secret": env_key}
            save(results)
            print(f"SKIP {domain}: {env_key} 없음")
            continue

        try:
            posts = fetch_posts(site_url)
        except Exception as e:
            results[domain] = {"status": "FETCH_FAILED", "error": str(e)}
            save(results)
            print(f"FAIL {domain}: {e}")
            continue

        prop = property_for(domain, site_url, accessible)
        if domain not in FULL_RESET_DOMAINS and not prop:
            results[domain] = {"status": "SKIP_NO_GSC_PROPERTY", "total_public_before": len(posts)}
            save(results)
            print(f"SKIP {domain}: GSC property 접근 없음")
            continue

        summary = {
            "status": "OK",
            "mode": "FULL_RESET" if domain in FULL_RESET_DOMAINS else "GSC_URL_INSPECTION",
            "gsc_property": prop,
            "total_public_before": len(posts),
            "indexed_kept": 0,
            "made_private": 0,
            "inspection_uncertain_kept": 0,
            "private_failed": 0,
            "items": [],
        }
        print(f"\n=== {domain}: 공개 {len(posts)}개 / {summary['mode']} ===")

        for post in posts:
            title = title_of(post)
            url = post.get("link")

            if domain in FULL_RESET_DOMAINS:
                decision = "PRIVATE_FULL_RESET"
                inspection = None
            else:
                inspection = inspect_url(token, prop, url)
                if not inspection.get("ok"):
                    decision = "KEEP_UNCERTAIN"
                elif inspection.get("verdict") == "PASS":
                    decision = "KEEP_INDEXED"
                else:
                    decision = "PRIVATE_UNINDEXED"

            item = {"id": post["id"], "url": url, "title": title, "decision": decision, "inspection": inspection}

            if decision.startswith("PRIVATE"):
                ok, code, detail = set_private(site_url, pw, post["id"])
                if ok:
                    summary["made_private"] += 1
                    print(f"PRIVATE {domain} #{post['id']} {title[:80]}")
                else:
                    summary["private_failed"] += 1
                    item["private_http"] = code
                    item["private_error"] = detail
                    print(f"PRIVATE FAIL {domain} #{post['id']} HTTP {code}")
            elif decision == "KEEP_INDEXED":
                summary["indexed_kept"] += 1
                print(f"KEEP INDEXED {domain} #{post['id']} {title[:80]}")
            else:
                summary["inspection_uncertain_kept"] += 1
                print(f"KEEP UNCERTAIN {domain} #{post['id']} {inspection.get('error')}")

            summary["items"].append(item)
            save(results | {domain: summary})
            time.sleep(1.05)

        results[domain] = summary
        save(results)

    totals = {
        "sites_processed": sum(1 for x in results.values() if x.get("status") == "OK"),
        "sites_skipped_or_failed": sum(1 for x in results.values() if x.get("status") != "OK"),
        "public_before": sum(x.get("total_public_before", 0) for x in results.values()),
        "indexed_kept": sum(x.get("indexed_kept", 0) for x in results.values()),
        "made_private": sum(x.get("made_private", 0) for x in results.values()),
        "uncertain_kept": sum(x.get("inspection_uncertain_kept", 0) for x in results.values()),
        "private_failed": sum(x.get("private_failed", 0) for x in results.values()),
    }
    results["_TOTALS"] = totals
    save(results)
    print("\n=== 전체 요약 ===")
    print(json.dumps(totals, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
