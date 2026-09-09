"""Use the existing Google Metrics grant without transferring its credentials."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import urlparse
import requests
from core_metrics_report import KST, previous_day, delta


def refresh(report, history):
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

    def inspect(row):
        if row["platform"] != "blogger":
            return row
        url = row["url"].rstrip("/")
        host = urlparse(url).hostname
        candidates = [url + "/", url, "sc-domain:" + host]
        candidates += ["sc-domain:" + host.split(".", 1)[1]] if host.endswith(".k-health365.com") else []
        prop = next((p for p in candidates if p in props), None)
        if not prop or row.get("total_posts") is None:
            return row
        counts = {"indexed": 0, "unindexed": 0, "unknown": 0}
        urls = row.get("published_urls", [])
        if len(urls) != row["total_posts"]:
            return row
        for post in urls:
            try:
                r = requests.post("https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
                    headers=headers, json={"inspectionUrl": post, "siteUrl": prop}, timeout=25)
                r.raise_for_status()
                verdict = r.json()["inspectionResult"]["indexStatusResult"].get("verdict")
                counts["indexed" if verdict == "PASS" else "unindexed" if verdict in ("NEUTRAL", "FAIL") else "unknown"] += 1
            except (requests.RequestException, KeyError, ValueError):
                counts["unknown"] += 1
        row.update(indexed=counts["indexed"] if counts["unknown"] < len(urls) or not urls else None,
            index_unknown=counts["unknown"], index_unindexed=counts["unindexed"], index_total=len(urls),
            index_partial=bool(counts["unknown"]), index_checked_at=datetime.now(KST).isoformat())
        previous = old.get(url, {})
        row["indexed_delta"] = None if row["index_partial"] or previous.get("index_partial") else delta(row["indexed"], previous.get("indexed"))
        if not counts["unknown"]:
            row["errors"] = [e for e in row.get("errors", []) if e != "Google 색인 조회 권한 연결 필요"]
        return row

    with ThreadPoolExecutor(max_workers=4) as pool:
        report["records"] = list(pool.map(inspect, report["records"]))
    return report
