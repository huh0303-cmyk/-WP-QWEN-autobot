#!/usr/bin/env python3
"""Daily dashboard: WP + Blogspot in one ranking. Runs 07:00 KST, no AI/tokens.
Metrics per site (reference day = day before yesterday KST, so GSC data is more settled):
 1 day-before-yesterday search clicks (daily traffic proxy) + delta vs three days ago
 2 cumulative clicks (GSC, all available history) + delta (= reference-day clicks)
 3 content count (WP REST / Blogspot feed) + delta vs previous snapshot
 4 GSC sitemap indexed URL count + delta vs previous snapshot (not search impressions)
"""
import datetime as dt
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gsc_unified_ranking import WP25

ROOT = Path(__file__).resolve().parents[1]
KST = dt.timezone(dt.timedelta(hours=9))
EXCLUDE = ("theseouljournal",)
OUT = ROOT / "docs" / "dashboard.json"
HIST = ROOT / "data" / "dashboard_history.json"
EMPTY = dict(visitors=None, visitors_delta=None, cumulative=None, cumulative_delta=None,
             google_indexed=None, google_indexed_delta=None, google_indexed_status="GSC_INDEX_COUNT_UNAVAILABLE")


def token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_METRICS_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_METRICS_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_METRICS_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


def gsc(h, prop, body):
    u = "https://www.googleapis.com/webmasters/v3/sites/" + quote(prop, safe="") + "/searchAnalytics/query"
    r = requests.post(u, headers=h, json=body, timeout=40)
    return r.json().get("rows", []) if r.status_code == 200 else None


def prop_for(url, props):
    exact = url.rstrip("/") + "/"
    if exact in props:
        return exact
    host = url.split("://", 1)[-1].split("/", 1)[0].lower()
    m = [p for p in props if p.startswith("sc-domain:") and (host == p[10:] or host.endswith("." + p[10:]))]
    return max(m, key=len) if m else None


def indexed_sitemap_count(h, prop):
    """Return indexed web-URL counts reported for submitted GSC sitemaps.
    This is the GSC sitemap count, not pages with impressions. Missing or
    unsupported counts remain None rather than being fabricated as zero.
    """
    try:
        encoded_prop = quote(prop, safe="")
        r = requests.get(
            "https://www.googleapis.com/webmasters/v3/sites/" + encoded_prop + "/sitemaps",
            headers=h, timeout=30,
        )
        if r.status_code != 200:
            return None
        total = 0
        submitted_total = 0
        found = False
        for sm in r.json().get("sitemap", []):
            path = sm.get("path")
            if not path:
                continue
            detail = requests.get(
                "https://www.googleapis.com/webmasters/v3/sites/" + encoded_prop
                + "/sitemaps/" + quote(path, safe=""),
                headers=h, timeout=30,
            )
            if detail.status_code != 200:
                continue
            for item in detail.json().get("contents", []):
                if str(item.get("type", "")).lower() != "web":
                    continue
                submitted_total += int(item.get("submitted", 0) or 0)
                count = item.get("indexed")
                if count is None:
                    continue
                total += int(count)
                found = True
        # Search Console deprecated the sitemap contents[].indexed field.
        # In current responses it can appear as 0 for every site even when
        # the site has hundreds of submitted URLs. Never present that as a
        # real indexed-page count; the aggregate Page indexing report has no
        # supported API endpoint.
        if not found or (total == 0 and submitted_total > 0):
            return None
        return total
    except (requests.RequestException, ValueError, TypeError):
        return None


def content_count(url, platform):
    try:
        if platform == "wordpress":
            r = requests.get(url.rstrip("/") + "/wp-json/wp/v2/posts?per_page=1&_fields=id", timeout=25)
            return int(r.headers["X-WP-Total"]) if r.ok and "X-WP-Total" in r.headers else None
        r = requests.get(url.rstrip("/") + "/feeds/posts/summary?alt=json&max-results=0", timeout=25)
        return int(r.json()["feed"]["openSearch$totalResults"]["$t"]) if r.ok else None
    except Exception:
        return None


def one(h, props, platform, url, ref, prev_hist):
    row = {"site": url.split("://", 1)[-1].rstrip("/"), "url": url, "platform": platform, "status": "OK"}
    prop = prop_for(url, props)
    row["gsc_property"] = prop
    day = ref.isoformat()
    before = (ref - dt.timedelta(days=1)).isoformat()
    row["content"] = content_count(url, platform)
    p = prev_hist.get(row["site"], {})
    if row["content"] is not None and p.get("content") is not None:
        row["content_delta"] = row["content"] - p["content"]
    else:
        row["content_delta"] = None
    if not prop:
        row.update(EMPTY)
        row["status"] = "NO_GSC_ACCESS"
        return row
    days = gsc(h, prop, {"startDate": (ref - dt.timedelta(days=10)).isoformat(), "endDate": day,
                         "dimensions": ["date"], "dataState": "all", "rowLimit": 20})
    if days is None:
        row.update(EMPTY)
        row["status"] = "QUERY_ERROR"
        return row
    d = {r["keys"][0]: r["clicks"] for r in days}
    row["visitors"] = int(d.get(day, 0))
    row["visitors_delta"] = int(d.get(day, 0) - d.get(before, 0))
    tot = gsc(h, prop, {"startDate": (ref - dt.timedelta(days=480)).isoformat(), "endDate": day,
                        "dataState": "all"})
    row["cumulative"] = int(sum(r["clicks"] for r in tot)) if tot else 0
    row["cumulative_delta"] = row["visitors"]
    row["google_indexed"] = indexed_sitemap_count(h, prop)
    row["google_indexed_status"] = "OK" if row["google_indexed"] is not None else "GSC_INDEX_COUNT_UNAVAILABLE"
    previous_indexed = p.get("google_indexed", p.get("google_pages"))
    if row["google_indexed"] is not None and previous_indexed is not None:
        row["google_indexed_delta"] = row["google_indexed"] - previous_indexed
    else:
        row["google_indexed_delta"] = None
    return row


def main():
    now = dt.datetime.now(KST)
    ref = now.date() - dt.timedelta(days=2)
    h = {"Authorization": "Bearer " + token(), "Content-Type": "application/json"}
    ents = requests.get("https://www.googleapis.com/webmasters/v3/sites", headers=h, timeout=30).json().get("siteEntry", [])
    props = {e["siteUrl"] for e in ents if e.get("permissionLevel") != "siteUnverifiedUser"}
    portfolio = json.loads((ROOT / "config" / "blogger_portfolio.json").read_text(encoding="utf-8"))
    targets = [("wordpress", s) for s in WP25] + [("blogspot", c["blogspot"].rstrip("/")) for c in portfolio["channels"]]
    targets = [t for t in targets if not any(x in t[1] for x in EXCLUDE)]
    hist = json.loads(HIST.read_text(encoding="utf-8")) if HIST.exists() else {}
    prev_dates = sorted(k for k in hist if k < ref.isoformat())
    prev = hist[prev_dates[-1]] if prev_dates else {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        rows = list(ex.map(lambda t: one(h, props, t[0], t[1], ref, prev), targets))
    rows.sort(key=lambda r: (r["visitors"] is None, -(r["visitors"] or 0), r["site"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_at": now.isoformat(), "reference_date": ref.isoformat(),
        "basis": "매일 07:00 KST 갱신 · 방문 통계 기준일은 그저께(2일 전) · 방문자 대체 지표는 GSC 검색 클릭 · 색인수는 GSC 사이트맵 보고값이며 노출 페이지 수가 아님.",
        "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    hist[ref.isoformat()] = {r["site"]: {"content": r["content"], "google_indexed": r.get("google_indexed")} for r in rows}
    for k in sorted(hist)[:-60]:
        del hist[k]
    HIST.write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")
    print("rows", len(rows), "ok", sum(r["status"] == "OK" for r in rows), "ref", ref)


if __name__ == "__main__":
    main()
