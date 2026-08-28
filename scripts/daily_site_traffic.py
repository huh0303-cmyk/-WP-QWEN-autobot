#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
daily_site_traffic.py
─────────────────────────────────────────────────────────────
27개 사이트의 WordPress footer 방문자 카운터를 하루 1회 수집하고,
Google Search Console 검색 클릭/노출/색인 정보는 보조 지표로 함께 기록한다.

중요:
- "일일방문자수"는 더 이상 GSC 클릭수가 아니다.
- 각 사이트에 배포된 /wp-json/site-stats/v1/visitors 의 yesterday_count를
  사용하므로 아침 리포트에는 전날 00:00~23:59 KST의 확정 방문자수가 들어간다.
- 증감은 전날 방문자수 - 전전날 방문자수로 계산한다.
- 누적방문자수(total)도 함께 기록한다.
- GSC 클릭수는 gsc_clicks/clicks 필드로 별도 유지하여 기존 소비 코드와 호환한다.
"""
import json
import os
import time
from datetime import date, datetime, timedelta, timezone

import requests

GSC_KEY_JSON = os.environ.get("GSC_SERVICE_ACCOUNT_JSON", "")
SHEETS_WEBHOOK = os.environ.get("SHEETS_WEBHOOK", "")
SHEET_ID = os.environ.get("SHEET_ID", "")
KST = timezone(timedelta(hours=9))

SITES = [
    "https://k-health365.com/",
    "https://koreamedicaltour.com/",
    "https://koreainvest365.com/",
    "https://ki-korea.com/",
    "https://koreainsurance365.com/",
    "https://kfinance365.com/",
    "https://koreataxnlaw.com/",
    "https://koreacrypto365.com/",
    "https://krealestate365.com/",
    "https://ktech365.com/",
    "https://kskin365.com/",
    "https://oliveyoungkorea.com/",
    "https://kworld365.com/",
    "https://k-trip365.com/",
    "https://k-visa365.com/",
    "https://koreawedding365.com/",
    "https://kstudy365.com/",
    "https://studyinkorea365.com/",
    "https://kieca-korea.org/",
    "https://ksa-korea.org/",
    "https://sis-korea.com/",
    "https://jobkorea365.com/",
    "https://jobinkorea365.com/",
    "https://jobkoreaglobal.com/",
    "https://korea365.org/",
    "https://koreanews365.com/",
    "https://theseouljournal.com/",
]

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

RESULT_PATH = "daily_site_traffic_result.json"


def log(msg):
    print(msg, flush=True)


def get_footer_visitor_stats(site_url):
    """Footer 카운터와 같은 WordPress option 값을 공개 REST에서 읽는다.

    리포트 기준값은 yesterday_count(전날 확정치)다. 현재 시각의 today count는
    하루 중간값이라 일일 비교에는 쓰지 않는다.
    """
    try:
        url = site_url.rstrip("/") + "/wp-json/site-stats/v1/visitors"
        r = requests.get(url, headers=BROWSER_HEADERS, timeout=15)
        if r.status_code != 200:
            return None, f"visitor API HTTP {r.status_code}"
        data = r.json()
        y_count = int(data.get("yesterday_count", 0) or 0)
        total = int(data.get("total", 0) or 0)
        y_date = data.get("yesterday_date")

        # 전전날 값은 endpoint 구버전에는 없을 수 있으므로 None 허용.
        dby_raw = data.get("day_before_yesterday_count")
        dby_count = int(dby_raw) if dby_raw is not None else None
        delta = y_count - dby_count if dby_count is not None else None

        return {
            "date": y_date,
            "daily_visitors": y_count,
            "visitor_delta": delta,
            "total_visitors": total,
            "today_live": int(data.get("count", 0) or 0),
        }, None
    except Exception as e:
        return None, f"visitor API 예외: {str(e)[:160]}"


def get_published_post_count(site_url):
    """Read the public WordPress count without downloading post bodies."""
    try:
        url = site_url.rstrip("/") + "/wp-json/wp/v2/posts"
        r = requests.get(url, params={"per_page": 1, "_fields": "id"}, headers=BROWSER_HEADERS, timeout=15)
        if r.status_code != 200:
            return None, f"posts API HTTP {r.status_code}"
        return int(r.headers.get("X-WP-Total", 0)), None
    except Exception as e:
        return None, f"posts API 예외: {str(e)[:160]}"


def derive_index_metrics(indexed, submitted, previous_indexed=None):
    """Derive dashboard values only from official sitemap counts."""
    if indexed is None or submitted is None:
        return {"unindexed": None, "index_rate": None, "recent_index_increase": None}
    unindexed = max(int(submitted) - int(indexed), 0)
    rate = round((int(indexed) / int(submitted)) * 100, 2) if int(submitted) > 0 else None
    increase = None if previous_indexed is None else int(indexed) - int(previous_indexed)
    return {"unindexed": unindexed, "index_rate": rate, "recent_index_increase": increase}


def load_previous_index_counts(path=RESULT_PATH):
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        return {
            row["domain"]: row.get("sitemap_indexed")
            for row in payload.get("records", [])
            if row.get("domain") and row.get("sitemap_indexed") is not None
        }
    except (OSError, ValueError, TypeError):
        return {}


def get_gsc_token():
    import jwt

    key_data = json.loads(GSC_KEY_JSON)
    now = int(time.time())
    payload = {
        "iss": key_data["client_email"],
        "scope": "https://www.googleapis.com/auth/webmasters.readonly",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }
    assertion = jwt.encode(payload, key_data["private_key"], algorithm="RS256")
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def gsc_get(token, endpoint):
    return requests.get(
        f"https://www.googleapis.com/webmasters/v3{endpoint}",
        headers={"Authorization": f"Bearer {token}"}, timeout=15,
    )


def gsc_post(token, endpoint, body):
    return requests.post(
        f"https://www.googleapis.com/webmasters/v3{endpoint}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body, timeout=20,
    )


def latest_daily_stats(token, site_url, window_days=10):
    """GSC는 2~3일 지연되므로 3일 전까지의 가장 최근 확정 검색 통계."""
    # GitHub runner는 UTC다. 05:20 KST 실행 시 date.today()를 쓰면 한국 날짜보다
    # 하루 전을 기준으로 조회할 수 있으므로 반드시 KST 날짜를 사용한다.
    end = datetime.now(KST).date() - timedelta(days=3)
    start = end - timedelta(days=window_days)
    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": ["date"],
        "rowLimit": window_days + 1,
    }
    endpoint = f"/sites/{requests.utils.quote(site_url, safe='')}/searchAnalytics/query"
    r = gsc_post(token, endpoint, body)
    if r.status_code != 200:
        return None, f"GSC HTTP {r.status_code}: {r.text[:120]}"
    rows = r.json().get("rows", [])
    if not rows:
        return None, "최근 GSC 데이터 없음"
    rows.sort(key=lambda x: x["keys"][0])
    latest = rows[-1]
    return {
        "date": latest["keys"][0],
        "clicks": latest.get("clicks", 0),
        "impressions": latest.get("impressions", 0),
        "ctr": round(latest.get("ctr", 0) * 100, 2),
        "position": round(latest.get("position", 0), 1),
    }, None


def get_index_coverage(token, site_url):
    """Return sitemap-reported counts; this is not a URL Inspection census."""
    encoded = requests.utils.quote(site_url, safe="")
    r = gsc_get(token, f"/sites/{encoded}/sitemaps")
    if r.status_code != 200:
        return None, f"사이트맵 목록 HTTP {r.status_code}"
    sitemaps = r.json().get("sitemap", [])
    if not sitemaps:
        return None, "제출된 사이트맵 없음"

    total_indexed = 0
    total_submitted = 0
    found = False
    for sm in sitemaps:
        path = sm.get("path", "")
        if not path:
            continue
        r2 = gsc_get(token, f"/sites/{encoded}/sitemaps/{requests.utils.quote(path, safe='')}" )
        if r2.status_code != 200:
            continue
        for c in r2.json().get("contents", []):
            found = True
            total_indexed += int(c.get("indexed", 0) or 0)
            total_submitted += int(c.get("submitted", 0) or 0)
    if not found:
        return None, "사이트맵 색인 데이터 없음"
    return {
        "sitemap_indexed": total_indexed,
        "sitemap_submitted": total_submitted,
        # Compatibility alias for older history readers. Never label this as an
        # exact URL Inspection count in a dashboard.
        "indexed": total_indexed,
    }, None


WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


def weekday_kr(date_str):
    if not date_str:
        return ""
    y, m, d = (int(x) for x in date_str.split("-"))
    return WEEKDAY_KR[date(y, m, d).weekday()]


def fmt_delta(v):
    if v is None:
        return ""
    return f"+{v}" if v >= 0 else str(v)


def send_to_sheets(records):
    if SHEETS_WEBHOOK:
        try:
            r = requests.post(
                SHEETS_WEBHOOK,
                json={"type": "site_traffic_daily", "records": records},
                timeout=20,
            )
            log(f"📊 구글시트 웹훅 전송 {len(records)}건 HTTP {r.status_code}")
        except Exception as e:
            log(f"⚠️ 구글시트 웹훅 실패: {e}")

    import gsheets_direct
    if not SHEET_ID or not gsheets_direct.has_credentials():
        log("⚠️ SHEET_ID 또는 GOOGLE_OAUTH_* 없음 — 시트 직접 쓰기 스킵")
        return

    try:
        now = datetime.now(KST)
        report_date = records[0].get("date") if records else None
        date_label = report_date or now.strftime("%Y-%m-%d")
        date_label = f"{date_label}-{weekday_kr(date_label)}"
        domains = [s.rstrip("/").replace("https://", "") for s in SITES]
        values_by_domain = {
            r["domain"]: [
                r.get("daily_visitors"),
                fmt_delta(r.get("visitor_delta")),
                r.get("total_visitors"),
                r.get("sitemap_indexed"),
                r.get("sitemap_submitted"),
                r.get("unindexed"),
                r.get("index_rate"),
                fmt_delta(r.get("recent_index_increase")),
                r.get("total_posts"),
                r.get("gsc_clicks"),
                r.get("impressions"),
                r.get("ctr"),
                r.get("position"),
                r.get("gsc_date"),
                r.get("status"),
            ]
            for r in records
        }
        gsheets_direct.append_dated_metric_columns(
            SHEET_ID,
            "27개사이트_트래픽",
            domains,
            date_label,
            [
                "일일방문자수", "증감", "누적방문자", "사이트맵 보고 색인수", "사이트맵 제출URL수",
                "미색인수", "색인율(%)", "최근 색인 증가", "총 발행글",
                "GSC클릭", "GSC노출", "GSC CTR(%)", "GSC평균순위", "GSC기준일",
                "오류/연결상태",
            ],
            values_by_domain,
        )
        log(f"📊 시트 갱신 완료 — {date_label} / footer 방문자 기준")
    except Exception as e:
        log(f"⚠️ 구글시트 직접 쓰기 실패: {e}")


def main():
    token = None
    accessible = set()
    if GSC_KEY_JSON:
        try:
            token = get_gsc_token()
            resp = gsc_get(token, "/sites")
            if resp.status_code == 200:
                accessible = {s.get("siteUrl") for s in resp.json().get("siteEntry", [])}
            log(f"✅ GSC 연결: 접근 가능 {len(accessible)}개")
        except Exception as e:
            log(f"⚠️ GSC 연결 실패 — 방문자 수집은 계속: {e}")
            token = None
    else:
        log("⚠️ GSC_SERVICE_ACCOUNT_JSON 없음 — 방문자 수집만 진행")

    checked_at = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    previous_indexed = load_previous_index_counts()
    records = []

    for i, site_url in enumerate(SITES, 1):
        domain = site_url.rstrip("/").replace("https://", "")
        row = {
            "domain": domain,
            "date": "",
            "weekday": "",
            "daily_visitors": None,
            "visitor_delta": None,
            "total_visitors": None,
            "today_live": None,
            "gsc_clicks": None,
            "clicks": None,
            "impressions": None,
            "ctr": None,
            "position": None,
            "gsc_date": "",
            "indexed": None,
            "sitemap_indexed": None,
            "sitemap_submitted": None,
            "unindexed": None,
            "index_rate": None,
            "recent_index_increase": None,
            "total_posts": None,
            "gsc_property": "",
            "status": "",
            "errors": [],
            "checked_at": checked_at,
        }

        visitor, visitor_err = get_footer_visitor_stats(site_url)
        if visitor:
            row.update(visitor)
            row["weekday"] = weekday_kr(row["date"])
        else:
            row["errors"].append(visitor_err or "방문자 API 실패")

        post_count, post_err = get_published_post_count(site_url)
        row["total_posts"] = post_count
        if post_err:
            row["errors"].append(post_err)

        if token:
            domain_property = f"sc-domain:{domain}"
            if site_url in accessible:
                query_site = site_url
            elif domain_property in accessible:
                query_site = domain_property
            else:
                query_site = None

            if query_site:
                row["gsc_property"] = query_site
                stats, stats_err = latest_daily_stats(token, query_site)
                if stats:
                    row["gsc_clicks"] = stats["clicks"]
                    row["clicks"] = stats["clicks"]  # 기존 코드 호환
                    row["impressions"] = stats["impressions"]
                    row["ctr"] = stats["ctr"]
                    row["position"] = stats["position"]
                    row["gsc_date"] = stats["date"]
                elif stats_err:
                    row["errors"].append(stats_err)
                coverage, coverage_err = get_index_coverage(token, query_site)
                if coverage:
                    row["sitemap_indexed"] = coverage["sitemap_indexed"]
                    row["sitemap_submitted"] = coverage["sitemap_submitted"]
                    row["indexed"] = coverage["sitemap_indexed"]  # history compatibility
                    row.update(derive_index_metrics(
                        coverage["sitemap_indexed"], coverage["sitemap_submitted"],
                        previous_indexed.get(domain),
                    ))
                elif coverage_err:
                    row["errors"].append(coverage_err)
            else:
                row["errors"].append("GSC 속성 연결 필요")
        else:
            row["errors"].append("GSC 연결 필요")

        row["status"] = "정상" if not row["errors"] else " | ".join(row["errors"])
        if visitor:
            log(
                f"[{i:02d}/{len(SITES)}] {domain}: 전일 {row['daily_visitors']} "
                f"({fmt_delta(row['visitor_delta']) or '비교없음'}) / 누적 {row['total_visitors']} "
                f"/ GSC 클릭 {row['gsc_clicks']} · 노출 {row['impressions']} "
                f"· CTR {row['ctr']}% · 평균순위 {row['position']}"
            )
        else:
            log(f"[{i:02d}/{len(SITES)}] {domain}: {row['status']}")

        records.append(row)
        with open(RESULT_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {"checked_at": checked_at, "records": records, "partial": i < len(SITES)},
                f, ensure_ascii=False, indent=2,
            )
        time.sleep(0.2)

    send_to_sheets(records)

    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {"checked_at": checked_at, "records": records, "partial": False},
            f, ensure_ascii=False, indent=2,
        )
    log("✅ 완료 — 일일방문자수는 footer 카운터 전일 확정값 기준")


if __name__ == "__main__":
    main()
