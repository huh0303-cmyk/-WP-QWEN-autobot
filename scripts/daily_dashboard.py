#!/usr/bin/env python3
"""Daily dashboard: GSC clicks across the managed web portfolio. Runs 07:00 KST.
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
EXCLUDE = ("theseouljournal.com",)
OUT = ROOT / "docs" / "dashboard.json"
HIST = ROOT / "data" / "dashboard_history.json"
PAGEVIEWS_HIST = ROOT / "data" / "blogger_pageviews_history.json"
EMPTY = dict(clicks=None, clicks_delta=None, impressions=None, impressions_delta=None,
             cumulative=None, cumulative_delta=None, cumulative_impressions=None,
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
    """Return unavailable: Search Console's sitemap API no longer provides
    reliable indexed-page totals. Avoid dozens of obsolete API requests on
    every dashboard refresh; never fabricate index counts.
    """
    return None

def content_count(url, platform):
    try:
        if platform in {"wordpress", "newsroom"}:
            r = requests.get(url.rstrip("/") + "/wp-json/wp/v2/posts?per_page=1&_fields=id", timeout=25)
            return int(r.headers["X-WP-Total"]) if r.ok and "X-WP-Total" in r.headers else None
        if platform == "blogspot":
            r = requests.get(url.rstrip("/") + "/feeds/posts/summary?alt=json&max-results=0", timeout=25)
            return int(r.json()["feed"]["openSearch$totalResults"]["$t"]) if r.ok else None
        return None
    except Exception:
        return None



def blogger_access_token():
    """Read Blogger API credentials separately from Search Console credentials."""
    values = {
        "client_id": os.getenv("BLOGGER_GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("BLOGGER_GOOGLE_CLIENT_SECRET"),
        "refresh_token": os.getenv("BLOGGER_GOOGLE_REFRESH_TOKEN"),
        "grant_type": "refresh_token",
    }
    if not all(values.values()):
        return None, "BLOGGER_OAUTH_SECRETS_MISSING"
    try:
        response = requests.post("https://oauth2.googleapis.com/token", data=values, timeout=20)
        response.raise_for_status()
        return response.json().get("access_token"), None
    except (requests.RequestException, ValueError):
        return None, "BLOGGER_OAUTH_REFRESH_FAILED"


def collect_blogger_pageviews(portfolio, now):
    """Collect official Blogger API ALL-time pageviews and derive daily deltas from snapshots.

    A daily delta is shown only when the previous calendar day's cumulative total exists.
    Missing API data is never converted to zero. History is retained for a 30-day chart.
    """
    try:
        history = json.loads(PAGEVIEWS_HIST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        history = {"days": {}}
    history.setdefault("days", {})
    today = now.date().isoformat()
    previous_day = (now.date() - dt.timedelta(days=1)).isoformat()
    previous = history["days"].get(previous_day, {})
    access, auth_error = blogger_access_token()
    channels = portfolio.get("channels", [])
    current = {}
    rows = []
    headers = {"Authorization": "Bearer " + access} if access else {}
    for blog in channels:
        url = str(blog.get("blogspot") or "").rstrip("/")
        key = str(blog.get("destination_id") or "").strip()
        row = {
            "key": key or url, "url": url, "title": blog.get("title") or url,
            "total_pageviews": None, "daily_pageviews": None,
            "status": auth_error or "NOT_COLLECTED", "checked_at": None,
            "history": [],
        }
        if access and key:
            try:
                response = requests.get(
                    "https://www.googleapis.com/blogger/v3/blogs/" + key + "/pageviews",
                    headers=headers, params={"range": "ALL"}, timeout=20,
                )
                response.raise_for_status()
                payload = response.json()
                counts = payload.get("counts", [])
                total = next(
                    (int(item["count"]) for item in counts
                     if str(item.get("timeRange", "")).upper() in {"ALL", "ALL_TIME"}
                     and item.get("count") is not None),
                    None,
                )
                if total is None:
                    row["status"] = "TOTAL_PAGEVIEWS_NOT_RETURNED"
                else:
                    row["total_pageviews"] = total
                    row["checked_at"] = now.isoformat()
                    old = previous.get(row["key"])
                    if old is not None and total >= int(old):
                        row["daily_pageviews"] = total - int(old)
                        row["status"] = "OK"
                    elif old is not None:
                        row["status"] = "COUNTER_RESET_BASELINE_REQUIRED"
                    else:
                        row["status"] = "BASELINE_PENDING"
                    current[row["key"]] = total
            except (requests.RequestException, ValueError, TypeError, KeyError):
                row["status"] = "API_ERROR"
        rows.append(row)

    # Persist a dated cumulative snapshot even when only some blogs succeeded.
    # Failed API requests are not recorded as zero.
    if current:
        history["days"][today] = current
    for old_day in sorted(history["days"])[:-60]:
        del history["days"][old_day]
    PAGEVIEWS_HIST.parent.mkdir(parents=True, exist_ok=True)
    PAGEVIEWS_HIST.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    dates = sorted(history.get("days", {}))[-30:]
    for row in rows:
        key = row["key"]
        series = []
        for day in dates:
            day_values = history["days"].get(day, {})
            prev_day = (dt.date.fromisoformat(day) - dt.timedelta(days=1)).isoformat()
            current_total = day_values.get(key)
            prior_total = history["days"].get(prev_day, {}).get(key)
            daily = int(current_total) - int(prior_total) if current_total is not None and prior_total is not None and int(current_total) >= int(prior_total) else None
            series.append({"date": day, "daily_pageviews": daily})
        row["history"] = series
    return {
        "generated_at": now.isoformat(),
        "source": "Blogger API v3 pageviews range=ALL; daily values are differences between consecutive cumulative snapshots",
        "history_days": dates,
        "blogs": rows,
    }

def one(h, props, platform, url, display_name, ref, prev_hist):
    row = {"site": url.split("://", 1)[-1].rstrip("/"), "url": url,
           "platform": platform, "display_name": display_name or url.split("://", 1)[-1].rstrip("/"),
           "status": "OK"}
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
    if not days:
        # GSC returns no rows when the property/date has no reportable data.
        # Do not turn that absence into a fake numeric zero that sorts as a real result.
        row.update(EMPTY)
        row["status"] = "NO_DATA"
        return row
    d = {r["keys"][0]: r["clicks"] for r in days}
    # Search Analytics omits dates with no returned data. A missing date is
    # not proof of zero clicks; keep daily rank metric unavailable in that case.
    has_day = day in d
    row["clicks"] = int(d[day]) if has_day else None
    row["clicks_delta"] = int(d[day] - d.get(before, 0)) if has_day else None
    if not has_day:
        row["status"] = "NO_DATA"
    tot = gsc(h, prop, {"startDate": (ref - dt.timedelta(days=480)).isoformat(), "endDate": day,
                        "dataState": "all"})
    row["cumulative"] = int(sum(r["clicks"] for r in tot)) if tot is not None else None
    row["cumulative_delta"] = row["clicks"] if row["cumulative"] is not None and has_day else None
    # 노출수: 클릭이 너무 작아 순위 변별이 안 되므로 함께 수집한다 (같은 GSC 응답의 impressions 필드).
    im = {r["keys"][0]: r.get("impressions", 0) for r in days}
    row["impressions"] = int(im[day]) if has_day else None
    row["impressions_delta"] = int(im[day] - im.get(before, 0)) if has_day else None
    row["cumulative_impressions"] = int(sum(r.get("impressions", 0) for r in tot)) if tot is not None else None
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
    ref = now.date() - dt.timedelta(days=3)  # GSC 2–3 day lag: use a settled reporting day
    h = {"Authorization": "Bearer " + token(), "Content-Type": "application/json"}
    ents = requests.get("https://www.googleapis.com/webmasters/v3/sites", headers=h, timeout=30).json().get("siteEntry", [])
    props = {e["siteUrl"] for e in ents if e.get("permissionLevel") != "siteUnverifiedUser"}
    blogger_portfolio = json.loads((ROOT / "config" / "blogger_portfolio.json").read_text(encoding="utf-8"))
    tistory_portfolio = json.loads((ROOT / "config" / "tistory_portfolio.json").read_text(encoding="utf-8"))
    rooms = json.loads((ROOT / "config" / "automation_rooms.json").read_text(encoding="utf-8"))
    hub = json.loads((ROOT / "config" / "automation_hub_sites.json").read_text(encoding="utf-8"))

    # Build inventory from canonical registries. Display labels never determine identity.
    # Exclude only the exact newsroom domain theseouljournal.com; keep its separate
    # Blogger property theseouljournal.blogspot.com in the 33-blog Blogger inventory.
    targets = [("wordpress", s.rstrip("/"), s.split("://", 1)[-1].rstrip("/")) for s in WP25]
    targets += [("blogspot", item["blogspot"].rstrip("/"), item["blogspot"].rstrip("/").split("://", 1)[-1])
                for item in blogger_portfolio["channels"]]
    targets += [("tistory", item["url"].rstrip("/"), item.get("current_label", item.get("title", item["url"])))
                for item in tistory_portfolio["sites"] if item.get("launch_enabled")]
    targets += [("naver", "https://blog.naver.com/" + str(room.get("destination_id", "")).strip(),
                 room.get("name", room.get("destination_id", "")))
                for room in rooms.get("rooms", [])
                if room.get("platform") == "naver" and room.get("enabled") and room.get("destination_id")]
    targets += [("newsroom", item["url"].rstrip("/"), item.get("name", item.get("url", ""))) for item in hub.get("sites", [])
                if item.get("platform") == "wordpress"
                and item.get("url", "").rstrip("/") == "https://koreanews365.com"]
    targets = list(dict.fromkeys(targets))
    targets = [t for t in targets if t[1].split("://", 1)[-1].split("/", 1)[0].lower() not in EXCLUDE]
    hist = json.loads(HIST.read_text(encoding="utf-8")) if HIST.exists() else {}
    prev_dates = sorted(k for k in hist if k < ref.isoformat())
    prev = hist[prev_dates[-1]] if prev_dates else {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        rows = list(ex.map(lambda t: one(h, props, t[0], t[1], t[2], ref, prev), targets))
    rows.sort(key=lambda r: (r["clicks"] is None, -(r["clicks"] or 0), -(r["impressions"] or 0), r["site"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    blogger_pageviews = collect_blogger_pageviews(blogger_portfolio, now)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_at": now.isoformat(), "reference_date": ref.isoformat(),
        "blogger_pageviews": blogger_pageviews,
        "basis": "매일 07:00 KST 갱신 · GSC 검색 클릭·노출 기준일은 3일 전(GSC 지연 반영) · 클릭수는 사이트 방문자 수가 아님 · 색인수는 GSC 사이트맵 보고값이며 노출 페이지 수가 아님.",
        "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    hist[ref.isoformat()] = {r["site"]: {"content": r["content"], "google_indexed": r.get("google_indexed")} for r in rows}
    for k in sorted(hist)[:-60]:
        del hist[k]
    HIST.write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")
    print("rows", len(rows), "ok", sum(r["status"] == "OK" for r in rows), "gsc_access", sum(bool(r.get("gsc_property")) for r in rows), "platforms", {p: sum(r["platform"] == p for r in rows) for p in sorted({r["platform"] for r in rows})}, "ref", ref)


if __name__ == "__main__":
    main()
