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
    """Sum indexed URL counts reported by the Search Console Sitemaps API.

    These are sitemap-reported indexed counts (not a guarantee of all indexed
    URLs). Return None when access/API data is unavailable; never invent zero.
    """
    endpoint = "https://www.googleapis.com/webmasters/v3/sites/" + quote(prop, safe="") + "/sitemaps"
    try:
        response = requests.get(endpoint, headers=h, timeout=25)
        if response.status_code != 200:
            return None
        entries = response.json().get("sitemap", [])
        counts = []
        for item in entries:
            for content in item.get("contents", []):
                indexed = content.get("indexed")
                if indexed is not None:
                    try:
                        counts.append(int(indexed))
                    except (TypeError, ValueError):
                        pass
        return sum(counts) if counts else None
    except (requests.RequestException, ValueError, TypeError):
        return None

def content_metadata(url, platform):
    """Return published content count and latest publish date using lightweight public endpoints."""
    try:
        if platform in {"wordpress", "newsroom"}:
            endpoint = url.rstrip("/") + "/wp-json/wp/v2/posts?per_page=1&orderby=date&order=desc&_fields=id,date"
            r = requests.get(endpoint, timeout=25)
            if r.ok:
                total = int(r.headers["X-WP-Total"]) if "X-WP-Total" in r.headers else None
                items = r.json()
                latest = (items[0].get("date") or "")[:10] if items else None
                return {"content_count": total, "latest_publish_date": latest or None}
        elif platform == "blogspot":
            # Blogger's public JSON feed is readable without OAuth for public blogs.
            endpoint = url.rstrip("/") + "/feeds/posts/summary?alt=json&max-results=1&orderby=published"
            r = requests.get(endpoint, timeout=25)
            if r.ok:
                feed = r.json().get("feed", {})
                total = feed.get("openSearch$totalResults", {}).get("$t")
                entries = feed.get("entry", [])
                latest = None
                if entries:
                    for item in entries[0].get("published", []):
                        latest = item.get("$t", "")[:10]
                return {"content_count": int(total) if total is not None else None,
                        "latest_publish_date": latest or None}
        return {"content_count": None, "latest_publish_date": None}
    except Exception:
        return {"content_count": None, "latest_publish_date": None}


def content_count(url, platform):
    # Compatibility wrapper for existing callers.
    return content_metadata(url, platform).get("content_count")



def blogger_access_token():
    """Read Blogger API credentials separately from Search Console credentials."""
    values = {
        "client_id": os.getenv("BLOGGER_GOOGLE_CLIENT_ID") or os.getenv("GOOGLE_METRICS_CLIENT_ID"),
        "client_secret": os.getenv("BLOGGER_GOOGLE_CLIENT_SECRET") or os.getenv("GOOGLE_METRICS_CLIENT_SECRET"),
        "refresh_token": os.getenv("BLOGGER_GOOGLE_REFRESH_TOKEN") or os.getenv("GOOGLE_METRICS_REFRESH_TOKEN"),
        "grant_type": "refresh_token",
    }
    if not all(values.values()):
        return None, "BLOGGER_AND_GOOGLE_METRICS_OAUTH_SECRETS_MISSING"
    try:
        response = requests.post("https://oauth2.googleapis.com/token", data=values, timeout=20)
        response.raise_for_status()
        return response.json().get("access_token"), None
    except (requests.RequestException, ValueError):
        return None, "BLOGGER_OAUTH_REFRESH_FAILED"


def collect_blogger_pageviews(portfolio, now):
    """Read Blogger native pageview totals through Blogger API v3 when exposed.

    The old /api/blog-visits/{site_key} endpoint does not exist (HTTP 404), so
    it was never a valid visitor source. Never fabricate visitor counts.
    """
    try:
        history = json.loads(PAGEVIEWS_HIST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        history = {"days": {}}
    history.setdefault("days", {})
    today = now.date().isoformat()
    previous = history["days"].get((now.date() - dt.timedelta(days=1)).isoformat(), {})
    access_token, token_error = blogger_access_token()
    current, rows = {}, []
    for blog in portfolio.get("channels", []):
        url = str(blog.get("blogspot") or "").rstrip("/")
        site_key = str(blog.get("site_key") or "").strip()
        blog_id = str(blog.get("destination_id") or "").strip()
        row = {"key": site_key or url, "site_key": site_key, "url": url,
               "title": blog.get("title") or url, "total_pageviews": None,
               "daily_pageviews": None, "status": token_error or "BLOGGER_VIEWS_UNAVAILABLE",
               "checked_at": None, "history": []}
        if access_token and blog_id:
            try:
                response = requests.get(
                    "https://www.googleapis.com/blogger/v3/blogs/" + quote(blog_id, safe=""),
                    params={"view": "ADMIN"},
                    headers={"Authorization": "Bearer " + access_token}, timeout=20)
                if response.ok:
                    payload = response.json()
                    views = payload.get("views") or {}
                    total = views.get("total") or views.get("allTime")
                    if isinstance(total, (int, float)) and total >= 0:
                        total = int(total)
                        row["total_pageviews"] = total
                        row["checked_at"] = now.isoformat()
                        old = previous.get(site_key or url)
                        if old is not None and total >= int(old):
                            row["daily_pageviews"] = total - int(old)
                            row["status"] = "OK"
                        elif old is not None:
                            row["status"] = "COUNTER_RESET_BASELINE_REQUIRED"
                        else:
                            row["status"] = "BASELINE_PENDING"
                        current[site_key or url] = total
                    else:
                        row["status"] = "BLOGGER_API_NO_VIEW_TOTAL"
                else:
                    row["status"] = "BLOGGER_API_HTTP_" + str(response.status_code)
            except (requests.RequestException, ValueError, TypeError):
                row["status"] = "BLOGGER_API_REQUEST_FAILED"
        elif not blog_id:
            row["status"] = "BLOG_ID_MISSING"
        rows.append(row)
    if current:
        history["days"][today] = current
    for old_day in sorted(history["days"])[:-60]:
        del history["days"][old_day]
    PAGEVIEWS_HIST.parent.mkdir(parents=True, exist_ok=True)
    PAGEVIEWS_HIST.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    dates = sorted(history["days"])[-30:]
    for row in rows:
        key = row["key"]
        series = []
        for day in dates:
            total = history["days"].get(day, {}).get(key)
            prev_day = (dt.date.fromisoformat(day) - dt.timedelta(days=1)).isoformat()
            old = history["days"].get(prev_day, {}).get(key)
            daily = int(total)-int(old) if total is not None and old is not None and int(total)>=int(old) else None
            series.append({"date": day, "daily_pageviews": daily, "total_pageviews": total})
        row["history"] = series
    return {"generated_at": now.isoformat(),
            "source": "Blogger API v3 Blog resource views (when exposed); missing totals remain unavailable",
            "history_days": dates, "blogs": rows}

def one(h, props, platform, url, display_name, ref, prev_hist):
    row = {"site": url.split("://", 1)[-1].rstrip("/"), "url": url,
           "platform": platform, "display_name": display_name or url.split("://", 1)[-1].rstrip("/"),
           "status": "OK"}
    prop = prop_for(url, props)
    row["gsc_property"] = prop
    day = ref.isoformat()
    before = (ref - dt.timedelta(days=1)).isoformat()
    content_meta = content_metadata(url, platform)
    row["content"] = content_meta.get("content_count")
    row["latest_publish_date"] = content_meta.get("latest_publish_date")
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
    # The CONTROL WordPress group includes both canonical WordPress newsrooms.
    # The Seoul Journal Blogspot property remains a distinct Blogspot destination.
    wp25_sites = {s.rstrip("/") for s in WP25}
    targets = [("wordpress", s.rstrip("/"),
                "한국신문 Koreanews24" if "koreanews365.com" in s.lower() else s.split("://", 1)[-1].rstrip("/"))
               for s in WP25 if "ksa-korea.org" not in s.lower() and "theseouljournal.com" not in s.lower()]
    targets += [("blogspot", item["blogspot"].rstrip("/"), item["blogspot"].rstrip("/").split("://", 1)[-1])
                for item in blogger_portfolio["channels"]]
    targets += [("tistory", item["url"].rstrip("/"), item.get("current_label", item.get("title", item["url"])))
                for item in tistory_portfolio["sites"] if item.get("launch_enabled")]
    targets += [("naver", "https://blog.naver.com/" + str(room.get("destination_id", "")).strip(),
                 room.get("name", room.get("destination_id", "")))
                for room in rooms.get("rooms", [])
                if room.get("platform") == "naver" and room.get("enabled") and room.get("destination_id")]
    targets += [("newsroom", item["url"].rstrip("/"), item.get("name", item.get("url", ""))) for item in hub.get("sites", [])
                if item.get("platform") == "wordpress" and item.get("url", "").rstrip("/") not in wp25_sites
                and "ksa-korea.org" not in item.get("url", "").lower()
                and "theseouljournal.com" not in item.get("url", "").lower()]
    # Retired destinations: exclude from dashboard inventory without deleting any site content.
    targets = [t for t in targets if "ksa-korea.org" not in t[1].lower()
               and "theseouljournal.com" not in t[1].lower()
               and "theseouljournal.blogspot.com" not in t[1].lower()
               and "ksa-korea.blogspot.com" not in t[1].lower()]
    # Only one newsroom is active in the control-room inventory.
    newsroom_targets = [t for t in targets if t[0] == "newsroom"]
    if newsroom_targets:
        chosen = next((t for t in newsroom_targets if "koreanews365.com" in t[1].lower()), newsroom_targets[0])
        targets = [t for t in targets if t[0] != "newsroom"]
        targets.append((chosen[0], chosen[1], "한국신문 Koreanews24"))
    targets = list(dict.fromkeys(targets))
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
