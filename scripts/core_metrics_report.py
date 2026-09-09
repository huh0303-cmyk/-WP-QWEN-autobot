"""Read-only four-metric collection. No text, image, voice or other paid AI calls."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import html
import json
import os
from pathlib import Path
import smtplib
from email.message import EmailMessage
import requests

ROOT = Path(__file__).resolve().parents[1]
KST = timezone(timedelta(hours=9))


def read(name, default=None):
    try:
        return json.loads((ROOT / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {} if default is None else default


def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def delta(current, previous):
    return current - previous if current is not None and previous is not None else None


def oauth():
    data = {"client_id": os.getenv("BLOGGER_GOOGLE_CLIENT_ID"), "client_secret": os.getenv("BLOGGER_GOOGLE_CLIENT_SECRET"),
            "refresh_token": os.getenv("BLOGGER_GOOGLE_REFRESH_TOKEN"), "grant_type": "refresh_token"}
    if not all(data.values()):
        return {}
    r = requests.post("https://oauth2.googleapis.com/token", data=data, timeout=20)
    if not r.ok:
        return {}
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def get(url, **kwargs):
    for attempt in range(2):
        try:
            response = requests.get(url, timeout=20, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException:
            if attempt:
                raise


def previous_day(history, day):
    key = (datetime.fromisoformat(day).date() - timedelta(days=1)).isoformat()
    return {r["url"]: r for r in history.get("days", {}).get(key, {}).get("records", [])}


def collect():
    stamp = datetime.now(KST).isoformat()
    day = stamp[:10]
    history = read("data/core_metrics_history.json")
    prior = previous_day(history, day)
    audits = read("index_audit_manifest.json").get("sites", {})
    native = read("data/blogger_traffic_latest.json")
    blogger_headers = oauth()
    index_headers, properties = {}, set()
    if os.getenv("GSC_SERVICE_ACCOUNT_JSON"):
        try:
            from audit_gsc_post_index import token, properties as list_properties
            t = token()
            index_headers = {"Authorization": "Bearer " + t}
            properties = list_properties(t)
        except Exception:
            pass
    from site_registry import SITES
    wp_urls = [s[0].rstrip("/") for s in SITES]
    blogs = read("config/blogger_portfolio.json").get("channels", [])

    def wp(url):
        row = {"url": url, "platform": "news" if any(n in url for n in ["koreanews365.com", "theseouljournal.com"]) else "wordpress", "errors": []}
        try:
            v = get(url + "/wp-json/site-stats/v1/visitors").json()
            if v.get("date") == day:
                row.update(today_visitors=number(v.get("count")), total_visitors=number(v.get("total")),
                           today_delta=delta(number(v.get("count")), number(v.get("yesterday_count"))), total_delta=number(v.get("count")), visitor_checked_at=stamp)
            else:
                row["errors"].append("방문 기준일 불일치")
        except Exception:
            row["errors"].append("방문 수집 실패")
        try:
            p = get(url + "/wp-json/wp/v2/posts", params={"per_page": 1, "_fields": "id", "status": "publish"})
            row["total_posts"] = number(p.headers.get("X-WP-Total"))
            row["posts_checked_at"] = stamp
        except Exception:
            row["errors"].append("총 발행 글 수집 실패")
        e = audits.get(url) or audits.get(url + "/") or {}
        s = e.get("summary", {})
        row.update(indexed=number(s.get("indexed")) if e.get("audited_at") and not (s.get("unknown") and not s.get("indexed") and not s.get("unindexed")) else None,
                   indexed_delta=None if s.get("unknown") or e.get("error") else number(s.get("indexed_delta")),
                   index_unknown=s.get("unknown"), index_total=s.get("total_published"), index_unindexed=s.get("unindexed"),
                   index_partial=bool(s.get("unknown")), index_checked_at=e.get("audited_at"), index_comparison_at=s.get("comparison_at"))
        if e.get("error") or not e.get("audited_at"):
            row["errors"].append("Google 색인 최신 확인 필요")
        return row

    def blogger(blog):
        url = blog["blogspot"].rstrip("/")
        row = {"url": url, "platform": "blogger", "name": blog.get("title"), "errors": [], "visitor_basis": "Blogger 자체 조회수"}
        v = native.get("sites", {}).get(url, {})
        if native.get("generated_at", "")[:10] == day:
            row.update(today_visitors=number(v.get("today")), today_delta=number(v.get("today_delta")), total_visitors=number(v.get("total")), total_delta=number(v.get("total_delta")), visitor_checked_at=native["generated_at"])
        else:
            row["errors"].append("오늘 Blogger 관리자 통계 갱신 필요")
        urls = []
        try:
            endpoint = "https://www.googleapis.com/blogger/v3/blogs/" + str(blog["destination_id"])
            params = {"maxResults": 500, "fetchBodies": "false", "status": "live", "fields": "items(url),nextPageToken"}
            while True:
                result = get(endpoint + "/posts", headers=blogger_headers, params=params).json()
                urls.extend(x["url"] for x in result.get("items", []))
                if not result.get("nextPageToken"):
                    break
                params["pageToken"] = result["nextPageToken"]
            row.update(total_posts=len(urls), posts_checked_at=stamp)
            if row.get("total_visitors") is None:
                pv = get(endpoint + "/pageviews", headers=blogger_headers, params={"range": "all"}).json()
                row["total_visitors"] = next((number(c.get("count")) for c in pv.get("counts", []) if c.get("timeRange", "").lower() == "all"), None)
                row["visitor_checked_at"] = stamp
        except Exception:
            row["errors"].append("Blogger API 수집 실패·권한 확인")
        row["published_urls"] = urls
        from urllib.parse import urlparse
        prop = next((p for p in (url + "/", url, "sc-domain:" + urlparse(url).netloc) if p in properties), None)
        if prop and row.get("total_posts") is not None:
            counts = {"indexed": 0, "unindexed": 0, "unknown": 0}
            for post_url in urls:
                try:
                    r = requests.post("https://searchconsole.googleapis.com/v1/urlInspection/index:inspect", headers=index_headers,
                                      json={"inspectionUrl": post_url, "siteUrl": prop}, timeout=20)
                    r.raise_for_status()
                    result = r.json()["inspectionResult"]["indexStatusResult"]
                    verdict = result.get("verdict")
                    counts["indexed" if verdict == "PASS" else "unindexed" if verdict in ("NEUTRAL", "FAIL") else "unknown"] += 1
                except Exception:
                    counts["unknown"] += 1
            row.update(indexed=counts["indexed"] if counts["unknown"] < len(urls) or not urls else None,
                       index_unknown=counts["unknown"], index_unindexed=counts["unindexed"], index_total=len(urls),
                       index_partial=bool(counts["unknown"]), index_checked_at=stamp)
        else:
            row["errors"].append("Google 색인 조회 권한 연결 필요")
        return row

    with ThreadPoolExecutor(max_workers=8) as pool:
        records = list(pool.map(wp, wp_urls)) + list(pool.map(blogger, blogs))
    for row in records:
        old = prior.get(row["url"], {})
        row["posts_delta"] = delta(row.get("total_posts"), old.get("total_posts"))
        if row["platform"] == "blogger":
            row["indexed_delta"] = None if row.get("index_partial") or old.get("index_partial") else delta(row.get("indexed"), old.get("indexed"))
        row["comparison_date"] = (datetime.fromisoformat(day).date() - timedelta(days=1)).isoformat() if old else None
    result = {"generated_at": stamp, "records": records, "paid_ai_used": False}
    history.setdefault("days", {})[day] = result
    return result, history


def format_metric(row, key, change):
    value, difference = row.get(key), row.get(change)
    if value is None:
        return "미확인"
    return f"{value:,} ({difference:+,})" if difference is not None else f"{value:,} (비교자료 없음)"


def report_html(result):
    parts = ["<h2>통제실 네 가지 핵심 통계</h2>", "<p>기준: " + html.escape(result["generated_at"]) + "</p>",
             "<p>오늘 방문 증감: 오늘 현재−어제 하루. 누적 방문 증감: 오늘 증가. 총글 증감: 전날 저장값 대비. 색인 증감: 이전 확인값 대비. Blogger 방문은 자체 조회수입니다. 미확인 값은 0이 아닙니다.</p>"]
    for platform, title in [("wordpress", "WordPress 25개"), ("blogger", "Blogspot 33개"), ("news", "뉴스룸 2개 · 별도")]:
        rows = [r for r in result["records"] if r["platform"] == platform]
        parts.append(f"<h3>{title} · 수집 대상 {len(rows)}개</h3><table border='1' cellpadding='6' style='border-collapse:collapse'><tr><th>사이트</th><th>오늘 방문(증감)</th><th>누적 방문(증감)</th><th>총 발행 글(증감)</th><th>Google 색인(증감)</th><th>확인 필요</th></tr>")
        for r in rows:
            values = [html.escape(r["url"])] + [format_metric(r, k, d) for k, d in [("today_visitors", "today_delta"), ("total_visitors", "total_delta"), ("total_posts", "posts_delta"), ("indexed", "indexed_delta")]]
            values.append(html.escape(" / ".join(r.get("errors", [])) + (f" · 색인 미확인 {r['index_unknown']}개" if r.get("index_unknown") else "")))
            parts.append("<tr>" + "".join("<td>" + v + "</td>" for v in values) + "</tr>")
        parts.append("</table>")
    return "".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", action="store_true")
    parser.add_argument("--refresh-index", action="store_true")
    args = parser.parse_args()
    if args.refresh_index:
        from core_metrics_gsc import refresh
        result = refresh(read("data/core_metrics_latest.json"), read("data/core_metrics_history.json"))
        history = read("data/core_metrics_history.json")
        history.setdefault("days", {})[result["generated_at"][:10]] = result
    else:
        result, history = collect()
    for name, value in [("core_metrics_latest.json", result), ("core_metrics_history.json", history)]:
        path = ROOT / "data" / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    content = report_html(result)
    (ROOT / "data/core_metrics_report.html").write_text(content, encoding="utf-8")
    print(json.dumps({"records": len(result["records"]), "coverage": {k: sum(r.get(k) is not None for r in result["records"]) for k in ["today_visitors", "total_visitors", "total_posts", "indexed"]}}))
    if args.email:
        password = os.environ.get("GMAIL_APP_PASSWORD")
        if not password:
            raise RuntimeError("Email credential missing; report saved but not sent")
        msg = EmailMessage()
        msg["Subject"] = "[통제실] " + result["generated_at"][:10] + " 방문·누적·총글·Google 색인 및 증감"
        msg["From"] = msg["To"] = "huh0303@gmail.com"
        msg.set_content("통제실 네 가지 핵심 통계입니다. HTML 표를 확인해 주세요. 미확인은 0이 아닙니다.")
        msg.add_alternative(content, subtype="html")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
            smtp.login("huh0303@gmail.com", password)
            smtp.send_message(msg)
        print("EMAIL_SENT")


if __name__ == "__main__":
    main()
