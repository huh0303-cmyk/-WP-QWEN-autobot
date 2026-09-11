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


def collect(baseline_date="", cutoff_stamp=None):
    stamp = cutoff_stamp or datetime.now(KST).isoformat()
    day = stamp[:10]
    history = read("data/core_metrics_history.json")
    prior = previous_day(history, day)
    audits = read("index_audit_manifest.json").get("sites", {})
    blogger_headers = oauth()
    from site_registry import SITES
    wp_urls = [s[0].rstrip("/") for s in SITES]
    blogs = read("config/blogger_portfolio.json").get("channels", [])

    def wp(url):
        row = {"url": url, "platform": "news" if any(n in url for n in ["koreanews365.com", "theseouljournal.com"]) else "wordpress", "errors": []}
        try:
            v = get(url + "/wp-json/site-stats/v1/visitors").json()
            if v.get("date") == day:
                row.update(today_visitors=number(v.get("count")), total_visitors=number(v.get("total")),
                           today_delta=delta(number(v.get("count")), number(v.get("yesterday_count"))), total_delta=number(v.get("count")), visitor_checked_at=datetime.now(KST).isoformat())
            else:
                row["errors"].append("방문 기준일 불일치")
        except Exception:
            row["errors"].append("방문 수집 실패")
        try:
            from core_metrics_gsc import published_wordpress_urls
            from core_metrics_header import publication_counts
            posts = published_wordpress_urls(url, with_dates=True)
            row["published_urls"] = [post["link"] for post in posts]
            row.update(publication_counts(posts, stamp, "date_gmt"))
            row["total_posts"] = len(row["published_urls"])
            row["posts_checked_at"] = datetime.now(KST).isoformat()
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
        urls, published_posts = [], []
        try:
            endpoint = "https://www.googleapis.com/blogger/v3/blogs/" + str(blog["destination_id"])
            params = {"maxResults": 500, "fetchBodies": "false", "status": "live", "fields": "items(url,published),nextPageToken"}
            while True:
                result = get(endpoint + "/posts", headers=blogger_headers, params=params).json()
                published_posts.extend(result.get("items", []))
                urls.extend(x["url"] for x in result.get("items", []))
                if not result.get("nextPageToken"):
                    break
                params["pageToken"] = result["nextPageToken"]
            from core_metrics_header import publication_counts
            row.update(publication_counts(published_posts, stamp, "published"))
            row.update(total_posts=len(urls), posts_checked_at=datetime.now(KST).isoformat())
            pv = get(endpoint + "/pageviews", headers=blogger_headers, params={"range": "all"}).json()
            row["total_visitors"] = next((number(c.get("count")) for c in pv.get("counts", []) if c.get("timeRange", "").upper() in {"ALL", "ALL_TIME"}), None)
            row["visitor_checked_at"] = datetime.now(KST).isoformat()
        except Exception:
            row["errors"].append("Blogger API 수집 실패·권한 확인")
        row["published_urls"] = urls
        row.update(indexed=None, indexed_delta=None, index_partial=True)
        if row.get("total_visitors") is None:
            row["errors"].append("Blogger 누적 조회수 API 값 미확인")
        return row

    with ThreadPoolExecutor(max_workers=8) as pool:
        records = list(pool.map(wp, wp_urls)) + list(pool.map(blogger, blogs))
    for row in records:
        old = prior.get(row["url"], {})
        row["posts_delta"] = delta(row.get("total_posts"), old.get("total_posts"))
        if row["platform"] == "blogger":
            row["indexed_delta"] = None if row.get("index_partial") or old.get("index_partial") else delta(row.get("indexed"), old.get("indexed"))
        row["comparison_date"] = (datetime.fromisoformat(day).date() - timedelta(days=1)).isoformat() if old else None
    from core_metrics_policy import classify
    result = {"generated_at": stamp, "records": records, "paid_ai_used": False, **classify(stamp, baseline_date)}
    from core_metrics_header import header_summary
    result["daily_header"] = header_summary(records, stamp, read("budget_state.json"))
    history.setdefault("days", {})[day] = result
    return result, history


def format_metric(row, key, change):
    value, difference = row.get(key), row.get(change)
    if key == "indexed" and row.get("index_partial"):
        confirmed = row.get("index_confirmed", value)
        return "미확인" + (f" ({confirmed:,}개 확인)" if confirmed is not None else "")
    if value is None:
        return "미확인"
    if difference is None:
        return f"{value:,} (비교자료 없음)"
    if difference == 0:
        return f"{value:,} (+0)"
    color = "#1d4ed8" if difference > 0 else "#dc2626"
    return f'{value:,} <span style="color:{color};font-weight:700">({difference:+,})</span>'


def report_html(result):
    raw_stamp = result.get("scheduled_for") if result.get("report_kind") == "daily_0700" else result["generated_at"]
    try:
        stamp = datetime.fromisoformat(raw_stamp).astimezone(KST)
        period = "오전" if stamp.hour < 12 else "오후"
        display_stamp = f"{stamp.year}년 {stamp.month}월 {stamp.day}일 {period} {stamp.hour % 12 or 12}시 {stamp.minute:02}분 (KST) 기준"
        day = stamp.date().isoformat()
    except (ValueError, TypeError):
        display_stamp, day = str(raw_stamp), ""
    summary = result.get("daily_header", {})
    count = summary.get("published_today")
    change = summary.get("published_delta")
    total_label = f"{count:,}건" if count is not None else "미확인"
    if change is None:
        delta_label = "증감 미확인"
    else:
        color = "#1d4ed8" if change > 0 else "#dc2626" if change < 0 else "#475569"
        delta_label = f'<span style="color:{color}">{change:+,}건</span>'
    estimate = summary.get("recorded_estimate_usd")
    cost_change = summary.get("estimated_cost_delta_usd")
    cost_label = f"${estimate:,.4f}" if estimate is not None else "미집계"
    cost_delta = "증감 미확인"
    if cost_change is not None:
        cost_color = "#1d4ed8" if cost_change > 0 else "#dc2626" if cost_change < 0 else "#475569"
        cost_delta = f'<span style="color:{cost_color}">{cost_change:+,.4f} USD</span>'
    header_line = f'<span class="metrics-daily-totals" style="display:inline-block;font-size:18px;line-height:1.6;margin-left:12px">(당일 총발행 {total_label} ({delta_label}) · API 예상 총비용 {cost_label} ({cost_delta}, 기록분))</span>'
    parts = ["<h2>통제실 네 가지 핵심 통계</h2>",
             f'<p class="metrics-reference-time" data-date="{day}" style="font-size:clamp(22px,3vw,32px);font-weight:800;line-height:1.4;color:#0f172a;padding:16px;background:#eff6ff;border:2px solid #93c5fd;border-radius:12px">{html.escape(display_stamp)} {header_line}</p>',
             "<p>고정 기준: 매일 KST 07:00 수집. 일일 방문: 전날 07:00부터 오늘 07:00까지 누적 조회수 증가분. 일일 증감: 직전 24시간 증가분 대비. 나머지 증감: 전날 07:00 정기 저장값 대비. WP·Blogger 원천 조회수이며 고유 방문자 수와 다를 수 있습니다. 미확인은 0이 아닙니다.</p>",
             "<p>Google 색인은 공개 발행 글 URL의 검사 결과입니다. 카테고리·태그 등을 포함하는 GSC 전체 페이지 수와 다릅니다. 전체 URL 검사가 완료돼야 색인 글수를 확정합니다. 검사 실패·시간 초과는 미확인으로 표시합니다. Google 결과에는 반영 지연이 있을 수 있습니다.</p>"]
    label = "07:00 정기 집계" if result.get("report_kind") == "daily_0700" else "임시 점검 자료 · 07:00 정기 비교 기준으로 사용하지 않음"
    parts.insert(2, "<p>" + label + " · 실제 API 확인 시각은 각 항목에 기록</p>")
    if not result.get("policy_version"):
        parts[3] = "<p>기존 임시 집계: 일일 방문은 당일 현재 조회수, 증감은 어제 하루와 비교한 값입니다. 새 07:00 고정 비교 자료가 생성되면 교체됩니다. 누적·색인·총글의 실제 확인 시각은 각 항목에 표시합니다.</p>"
    notes = [summary.get("scope", "WP·Blogspot·뉴스룸 60개 합계"), summary.get("period", "KST 당일 00:00~기준 시각"), summary.get("api_cost_note", "실제 API 청구액 미연동")]
    if summary.get("recorded_estimate_usd") is not None:
        notes.append(f"글쓰기·이미지 포함 기록 예상액 ${summary['recorded_estimate_usd']:.4f} · 실제 총비용 아님")
    if count is None and summary.get("expected_sites"):
        notes.append(f"발행일 수집 {summary['covered_sites']}/{summary['expected_sites']}개 사이트 · 확인된 발행 {summary['confirmed_published_today']}건")
    parts.insert(3, '<p class="metrics-header-notes">' + html.escape(" / ".join(notes)) + "</p>")
    for platform, title in [("wordpress", "WordPress 25개"), ("blogger", "Blogspot 33개"), ("news", "뉴스룸 2개 · 별도")]:
        rows = sorted((r for r in result["records"] if r["platform"] == platform),
                      key=lambda r: (r.get("today_visitors") is None, -(r.get("today_visitors") or 0), r["url"]))
        parts.append(f"<h3>{title} · 수집 대상 {len(rows)}개</h3><p>오늘 방문 내림차순 · 같은 수치는 공동 순위 · 미확인은 맨 아래</p><div style='overflow-x:auto'><table border='1' cellpadding='6' style='border-collapse:collapse;width:100%;font-size:13px'><tr><th>순위</th><th>사이트</th><th>일일 방문자수(증감)</th><th>누적 방문자수(증감)</th><th>총 발행 글(증감)</th><th>Google 색인 발행 글수(증감)</th><th>확인 필요</th></tr>")
        previous, rank = None, 0
        for position, r in enumerate(rows, 1):
            count = r.get("today_visitors")
            if count is not None and count != previous:
                rank = position
            previous = count
            url = html.escape(r["url"], quote=True)
            site = f'<a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a>' if r["url"].startswith("https://") else url
            values = [str(rank) if count is not None else "—", site] + [format_metric(r, k, d) for k, d in [("today_visitors", "today_delta"), ("total_visitors", "total_delta"), ("total_posts", "posts_delta"), ("indexed", "indexed_delta")]]
            if r.get("index_partial") and r.get("indexed") is not None:
                values[-1] += " · 일부 확인"
            details = list(r.get("errors", []))
            if r.get("index_confirmed") is not None and r.get("index_partial"):
                details.append(f"확인된 색인 {r['index_confirmed']}개 · 전체 수치는 검사 완료 전 미확인")
            if r.get("index_total") is not None:
                details.append(f"검사 대상 {r['index_total']}글 · 미색인 {r.get('index_unindexed') if r.get('index_unindexed') is not None else '미확인'} · 확인 실패 {r.get('index_unknown') if r.get('index_unknown') is not None else '미확인'}")
            if r.get("visitor_checked_at"):
                details.append("조회수 확인 " + r["visitor_checked_at"])
            if r.get("posts_checked_at"):
                details.append("공개 글 확인 " + r["posts_checked_at"])
            if r.get("index_checked_at"):
                details.append("색인 확인 " + r["index_checked_at"])
            values.append(html.escape(" / ".join(details)))
            parts.append("<tr>" + "".join("<td>" + v + "</td>" for v in values) + "</tr>")
        parts.append("</table></div>")
    return "".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", action="store_true")
    parser.add_argument("--refresh-index", action="store_true")
    parser.add_argument("--baseline-date", default="")
    parser.add_argument("--refresh-header", action="store_true")
    parser.add_argument("--render-only", action="store_true")
    args = parser.parse_args()
    if args.refresh_header:
        result = read("data/core_metrics_latest.json")
        measured, _ = collect(cutoff_stamp=result["generated_at"])
        result["daily_header"] = measured["daily_header"]
        history = read("data/core_metrics_history.json")
        history.setdefault("days", {})[result["generated_at"][:10]] = result
    elif args.render_only:
        result, history = read("data/core_metrics_latest.json"), read("data/core_metrics_history.json")
    elif args.refresh_index:
        from core_metrics_gsc import refresh
        result = refresh(read("data/core_metrics_latest.json"), read("data/core_metrics_history.json"))
        history = read("data/core_metrics_history.json")
        history.setdefault("days", {})[result["generated_at"][:10]] = result
    else:
        result, history = collect(args.baseline_date)
    duplicate_daily = False
    if args.refresh_index:
        from core_metrics_policy import apply_comparisons, freeze
        daily_history = read("data/core_metrics_daily_history.json")
        apply_comparisons(result, daily_history)
        history["days"][result["generated_at"][:10]] = result
        saved = freeze(daily_history, result)
        duplicate_daily = result.get("report_kind") == "daily_0700" and not saved
        if saved:
            for name, value in [("core_metrics_daily_history.json", daily_history), ("core_metrics_daily_latest.json", result)]:
                (ROOT / "data" / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, value in [("core_metrics_latest.json", result), ("core_metrics_history.json", history)]:
        path = ROOT / "data" / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    content = report_html(result)
    (ROOT / "data/core_metrics_report.html").write_text(content, encoding="utf-8")
    print(json.dumps({"records": len(result["records"]), "coverage": {k: sum(r.get(k) is not None for r in result["records"]) for k in ["today_visitors", "total_visitors", "total_posts", "indexed"]}}))
    if args.email and not duplicate_daily:
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
