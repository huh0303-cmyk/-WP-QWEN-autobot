#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
daily_site_traffic.py
─────────────────────────────────────────────────────────────
27개 사이트의 구글 서치콘솔(Search Console) 검색 클릭수/노출수를 매일
확인해서 구글시트로 보낸다. (진짜 "전체 방문자수"가 아니라 "구글 검색을
통해 들어온 클릭수" — 사이트가 살아있고 검색 유입이 잘 되는지 확인하는
용도)

서치콘솔 데이터는 보통 2~3일 지연돼서 나오기 때문에, "어제" 날짜를
바로 조회하지 않고 최근 10일 구간을 조회한 뒤 실제로 데이터가 채워진
가장 최근 날짜를 그 사이트의 "최신 값"으로 사용한다.

필요 환경변수:
    GSC_SERVICE_ACCOUNT_JSON  - 서치콘솔 서비스 계정 키 (이미 다른 스크립트에서 사용 중)
    SHEETS_WEBHOOK            - 구글시트 전송 웹훅 (이미 다른 스크립트에서 사용 중)
"""
import os
import sys
import json
import time
import requests
from datetime import date, timedelta, datetime, timezone

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


def log(msg):
    print(msg, flush=True)


def get_gsc_token():
    import jwt  # PyJWT

    key_data = json.loads(GSC_KEY_JSON)
    now = int(time.time())
    payload = {
        "iss": key_data["client_email"],
        "scope": "https://www.googleapis.com/auth/webmasters.readonly",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
    }
    token = jwt.encode(payload, key_data["private_key"], algorithm="RS256")
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": token},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def gsc_get(token, endpoint):
    r = requests.get(
        f"https://www.googleapis.com/webmasters/v3{endpoint}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    return r


def gsc_post(token, endpoint, body):
    r = requests.post(
        f"https://www.googleapis.com/webmasters/v3{endpoint}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=20,
    )
    return r


def latest_daily_stats(token, site_url, window_days=10):
    end = date.today()
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
        return None, f"HTTP {r.status_code}: {r.text[:150]}"
    rows = r.json().get("rows", [])
    if not rows:
        return None, "최근 10일간 데이터 없음(신규 사이트이거나 검색 유입 없음)"
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
    """제출된 사이트맵들의 색인(indexed)/제출(submitted) URL 수를 합산해서 반환.
    sitemap_index.xml처럼 다른 사이트맵을 가리키기만 하는 인덱스형은 자체
    contents가 비어있는 게 보통이라, list()로 실제 등록된 사이트맵 전부를
    가져와 각각의 contents를 더한다."""
    encoded = requests.utils.quote(site_url, safe="")
    r = gsc_get(token, f"/sites/{encoded}/sitemaps")
    if r.status_code != 200:
        return None, f"사이트맵 목록 조회 실패 HTTP {r.status_code}"
    sitemaps = r.json().get("sitemap", [])
    if not sitemaps:
        return None, "제출된 사이트맵 없음"

    total_indexed = 0
    total_submitted = 0
    found_contents = False
    for sm in sitemaps:
        path = sm.get("path", "")
        enc_path = requests.utils.quote(path, safe="")
        r2 = gsc_get(token, f"/sites/{encoded}/sitemaps/{enc_path}")
        if r2.status_code != 200:
            continue
        for c in r2.json().get("contents", []):
            found_contents = True
            total_indexed += int(c.get("indexed", 0) or 0)
            total_submitted += int(c.get("submitted", 0) or 0)

    if not found_contents:
        return None, "사이트맵 처리 대기 중(색인 데이터 아직 없음)"
    return {"indexed": total_indexed, "submitted_urls": total_submitted}, None


WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


def weekday_kr(date_str):
    if not date_str:
        return ""
    y, m, d = (int(x) for x in date_str.split("-"))
    return WEEKDAY_KR[date(y, m, d).weekday()]


def send_to_sheets(records):
    if not SHEETS_WEBHOOK:
        log("⚠️ SHEETS_WEBHOOK 없음 — 웹훅 전송 스킵")
    else:
        try:
            r = requests.post(SHEETS_WEBHOOK, json={"type": "site_traffic_daily", "records": records}, timeout=20)
            log(f"📊 구글시트 웹훅 전송 완료 ({len(records)}건) HTTP {r.status_code}")
        except Exception as e:
            log(f"⚠️ 구글시트 웹훅 전송 실패: {e}")

    # 웹훅(Apps Script)이 site_traffic_daily 타입을 실제로는 어느 탭에도 기록하지
    # 않는 것으로 확인되어, 같은 스프레드시트에 Sheets API로 직접 쓴다.
    import gsheets_direct
    if not SHEET_ID or not gsheets_direct.has_credentials():
        log("⚠️ SHEET_ID 또는 GOOGLE_OAUTH_* 시크릿 없음 — 시트 직접 쓰기 스킵")
        return
    try:
        header = ["도메인", "날짜", "요일", "일일방문자수", "색인수"]
        rows = [[r["domain"], r["date"], r["weekday"], r["clicks"], r["indexed"]] for r in records]
        gsheets_direct.replace_tab_rows(SHEET_ID, "27개사이트_트래픽", header, rows)
        log(f"📊 구글시트 직접 쓰기 완료 ({len(rows)}행) — 탭: 27개사이트_트래픽")
    except Exception as e:
        log(f"⚠️ 구글시트 직접 쓰기 실패: {e}")


def main():
    if not GSC_KEY_JSON:
        log("❌ GSC_SERVICE_ACCOUNT_JSON 없음")
        raise SystemExit(1)

    token = get_gsc_token()
    log("✅ GSC 토큰 발급 성공")

    accessible_resp = gsc_get(token, "/sites")
    accessible = set()
    if accessible_resp.status_code == 200:
        accessible = {s.get("siteUrl") for s in accessible_resp.json().get("siteEntry", [])}
    log(f"접근 가능한 GSC 사이트: {len(accessible)}개 / 전체 {len(SITES)}개")
    log(f"[디버그] 실제 접근 가능 사이트 URL 목록: {sorted(accessible)}")

    checked_at = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    records = []
    no_access = []

    # 시트에 사이트당 한 줄씩(27줄), 왼쪽부터 도메인 - 날짜 - 요일 - 방문자수(클릭) -
    # 색인수 순서로 열이 채워지도록 필드 순서를 고정한다(딕셔너리 순서 = 시트 열 순서 가정).
    base_row = {"domain": "", "date": "", "weekday": "", "clicks": "", "indexed": "",
                "impressions": "", "status": "", "checked_at": ""}

    for i, site_url in enumerate(SITES, 1):
        domain = site_url.rstrip("/").replace("https://", "")
        row = dict(base_row, domain=domain, checked_at=checked_at)

        # 같은 사이트라도 서치콘솔에 "URL 접두어(https://...)"가 아니라
        # "도메인 속성(sc-domain:...)"으로 등록돼 있을 수 있어서 둘 다 확인한다.
        domain_property = f"sc-domain:{domain}"
        if site_url in accessible:
            query_site = site_url
        elif domain_property in accessible:
            query_site = domain_property
        else:
            no_access.append(domain)
            row["status"] = "권한없음"
            records.append(row)
            continue

        stats, err = latest_daily_stats(token, query_site)
        if err:
            log(f"  [{i}/{len(SITES)}] {domain}: {err}")
            row["status"] = err
        else:
            row.update(date=stats["date"], weekday=weekday_kr(stats["date"]),
                       clicks=stats["clicks"], impressions=stats["impressions"], status="정상")

        coverage, cov_err = get_index_coverage(token, query_site)
        if coverage:
            row["indexed"] = coverage["indexed"]
        log(f"  [{i}/{len(SITES)}] {domain}: 클릭 {row['clicks']} / 색인 {row['indexed']}"
            f"{'' if coverage else f' ({cov_err})'}")

        records.append(row)
        time.sleep(0.3)

    if no_access:
        log(f"\n⚠️ GSC 권한 없는 사이트 {len(no_access)}개: {', '.join(no_access)}")

    send_to_sheets(records)
    log("완료")


if __name__ == "__main__":
    main()
