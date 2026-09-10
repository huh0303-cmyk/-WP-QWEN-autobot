"""Use the existing Google Metrics grant without transferring its credentials."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import urlparse
from collections import Counter
from itertools import zip_longest
import requests
from core_metrics_report import KST, previous_day, delta


def published_wordpress_urls(url):
    urls, page, expected = [], 1, None
    while True:
        response = requests.get(url + "/wp-json/wp/v2/posts", params={
            "status": "publish", "per_page": 100, "page": page, "_fields": "id,link"}, timeout=30)
        response.raise_for_status()
        total = int(response.headers["X-WP-Total"])
        if expected is not None and total != expected:
            raise ValueError("Publication inventory changed during collection")
        expected = total
        urls.extend(post["link"] for post in response.json())
        if len(urls) >= expected:
            break
        if not response.json():
            raise ValueError("Incomplete publication inventory")
        page += 1
    if len(set(urls)) != expected:
        raise ValueError("Incomplete or duplicate publication inventory")
    return urls


def unavailable(row, reason):
    row.update(indexed=None, indexed_delta=None, index_partial=True,
               index_checked_at=None, index_total=row.get("total_posts"),
               index_unknown=row.get("total_posts"), index_unindexed=None)
    row.setdefault("errors", []).append(reason)
    return row


def refresh(report, history):
    deadline = time.monotonic() + 12 * 60
    response = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_METRICS_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_METRICS_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_METRICS_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=30)
    response.raise_for_status()
    headers = {"Authorization": "Bearer " + response.json()["access_token"]}
    response = requests.get("https://www.googleapis.com/webmasters/v3/sites", headers=headers, timeout=30)
    response.raise_for_status()
    props = {p["siteUrl"] for p in response.json().get("siteEntry", [])}
    old = previous_day(history, report["generated_at"][:10])

    def prepare(row):
        if time.monotonic() >= deadline:
            return unavailable(row, "Google 응답 지연 · 다음 집계에서 재확인")
        url = row["url"].rstrip("/")
        host = urlparse(url).hostname
        candidates = [url + "/", url, "sc-domain:" + host]
        candidates += ["sc-domain:" + host.split(".", 1)[1]] if host.endswith(".k-health365.com") else []
        prop = next((p for p in candidates if p in props), None)
        if not prop:
            return unavailable(row, "Google 색인 조회 권한 연결 필요")
        if row["platform"] in ("wordpress", "news"):
            try:
                row["published_urls"] = published_wordpress_urls(url)
                row["total_posts"] = len(row["published_urls"])
                row["posts_checked_at"] = datetime.now(KST).isoformat()
                row["posts_delta"] = delta(row["total_posts"], old.get(url, {}).get("total_posts"))
            except (requests.RequestException, ValueError, KeyError):
                return unavailable(row, "색인 검사 대상 글 목록 수집 실패")
        if row.get("total_posts") is None:
            return unavailable(row, "색인 검사 대상 글 수 미확인")
        urls = row.get("published_urls", [])
        if len(urls) != row["total_posts"]:
            unavailable(row, "색인 검사 대상 글 목록 불완전")
            return None
        return row, prop, urls

    def inspect_post(task):
        index, prop, post = task
        if time.monotonic() >= deadline:
            return index, "unknown", "Google 응답 지연 · 검사 시간 한도"
        try:
            r = requests.post("https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
                headers=headers, json={"inspectionUrl": post, "siteUrl": prop}, timeout=25)
            r.raise_for_status()
            status = r.json()["inspectionResult"]["indexStatusResult"]
            verdict = status.get("verdict")
            return (index, "indexed" if verdict == "PASS" else "unindexed" if verdict in ("NEUTRAL", "FAIL") else "unknown",
                    status.get("coverageState") or "Google 판정 미확인")
        except requests.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "unknown"
            return index, "unknown", f"Google 검사 요청 실패 (HTTP {code})"
        except requests.Timeout:
            return index, "unknown", "Google 검사 응답 시간 초과"
        except (requests.RequestException, KeyError, ValueError):
            return index, "unknown", "검사 요청 실패"

    with ThreadPoolExecutor(max_workers=8) as pool:
        prepared = [item for item in pool.map(prepare, report["records"]) if isinstance(item, tuple)]
    counts_by_site = [Counter(indexed=0, unindexed=0, unknown=0) for _ in prepared]
    reasons_by_site = [Counter() for _ in prepared]
    # Interleave one URL per site before submitting the next URL from any site.
    # Large WordPress inventories must not exhaust the deadline ahead of Blogger.
    with ThreadPoolExecutor(max_workers=12) as pool:
        for index, bucket, reason in pool.map(inspect_post, fair_inspection_tasks(prepared)):
            counts_by_site[index][bucket] += 1
            reasons_by_site[index][reason] += 1
    for index, (row, prop, urls) in enumerate(prepared):
        url = row["url"].rstrip("/")
        counts, reasons = counts_by_site[index], reasons_by_site[index]
        row.update(indexed=counts["indexed"] if counts["unknown"] < len(urls) or not urls else None,
            index_unknown=counts["unknown"], index_unindexed=counts["unindexed"], index_total=len(urls),
            index_partial=bool(counts["unknown"]), index_checked_at=datetime.now(KST).isoformat(),
            index_source="Google URL Inspection API · published posts only", index_reasons=dict(reasons), index_property=prop)
        previous = old.get(url, {})
        row["indexed_delta"] = None if row["index_partial"] or previous.get("index_partial") else delta(row["indexed"], previous.get("indexed"))
        if not counts["unknown"]:
            row["errors"] = [e for e in row.get("errors", []) if e not in ("Google 색인 조회 권한 연결 필요", "Google 색인 최신 확인 필요")]
        print(f"INDEX_CHECK {url} total={len(urls)} indexed={counts['indexed']} unknown={counts['unknown']}", flush=True)
    return report


def fair_inspection_tasks(prepared):
    batches = [[(index, prop, post) for post in urls]
               for index, (_, prop, urls) in enumerate(prepared)]
    for round_ in zip_longest(*batches):
        yield from (task for task in round_ if task is not None)
