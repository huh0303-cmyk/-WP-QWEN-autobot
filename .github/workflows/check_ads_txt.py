#!/usr/bin/env python3
"""
27개 전체 사이트 ads.txt 상태 일괄 점검 스크립트.
- http/https 리다이렉트 상태 확인
- ads.txt 존재 여부 및 상태 코드 확인
- AdSense publisher ID 포함 여부 확인
- www / non-www 두 버전 모두 체크
"""

import requests
import concurrent.futures
import sys
from datetime import datetime

PUBLISHER_ID = "pub-3456727916386941"

DOMAINS = [
    "k-health365.com",
    "koreamedicaltour.com",
    "koreainvest365.com",
    "ki-korea.com",
    "koreainsurance365.com",
    "kfinance365.com",
    "koreataxnlaw.com",
    "koreacrypto365.com",
    "krealestate365.com",
    "ktech365.com",
    "kskin365.com",
    "oliveyoungkorea.com",
    "kworld365.com",
    "k-trip365.com",
    "k-visa365.com",
    "koreawedding365.com",
    "kstudy365.com",
    "studyinkorea365.com",
    "kieca-korea.org",
    "ksa-korea.org",
    "sis-korea.com",
    "jobkorea365.com",
    "jobinkorea365.com",
    "jobkoreaglobal.com",
    "korea365.org",
    "koreanews365.com",
    "theseouljournal.com",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Mediapartners-Google/2.1; +http://www.google.com/bot.html)"
}

TIMEOUT = 15


def check_url(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        return {
            "ok": True,
            "status_code": r.status_code,
            "final_url": r.url,
            "redirected": r.url != url,
            "has_publisher_id": PUBLISHER_ID in r.text,
            "body_snippet": r.text.strip()[:200],
        }
    except requests.exceptions.RequestException as e:
        return {"ok": False, "error": str(e)[:150]}


def check_domain(domain):
    result = {"domain": domain}
    variants = [
        f"https://{domain}/ads.txt",
        f"https://www.{domain}/ads.txt",
        f"http://{domain}/ads.txt",
    ]
    for url in variants:
        r = check_url(url)
        result[url] = r
    return result


def analyze(result):
    lines = []
    any_success = False
    for url, r in result.items():
        if url == "domain":
            continue
        if not r.get("ok"):
            lines.append(f"    ❌ {url} -> 접속 실패: {r.get('error')}")
            continue
        code = r["status_code"]
        if code == 200 and r["has_publisher_id"]:
            lines.append(f"    ✅ {url} -> 200 OK, publisher ID 확인됨" + (f" (리다이렉트됨: {r['final_url']})" if r["redirected"] else ""))
            any_success = True
        elif code == 200 and not r["has_publisher_id"]:
            lines.append(f"    ⚠️ {url} -> 200 OK 이지만 publisher ID({PUBLISHER_ID})가 파일 내용에 없음! 내용: {r['body_snippet']!r}")
        else:
            lines.append(f"    ❌ {url} -> HTTP {code}" + (f" (리다이렉트: {r['final_url']})" if r["redirected"] else ""))
    status = "OK" if any_success else "FAIL"
    return status, lines


def main():
    print(f"ads.txt 점검 시작: {datetime.now().isoformat()}")
    print(f"확인할 Publisher ID: {PUBLISHER_ID}")
    print(f"대상 사이트: {len(DOMAINS)}개\n")
    print("=" * 100)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(check_domain, d): d for d in DOMAINS}
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda x: DOMAINS.index(x["domain"]))

    ok_count = 0
    fail_domains = []

    for result in results:
        status, lines = analyze(result)
        mark = "✅" if status == "OK" else "❌"
        print(f"\n{mark} {result['domain']}  [{status}]")
        for line in lines:
            print(line)
        if status == "OK":
            ok_count += 1
        else:
            fail_domains.append(result["domain"])

    print("\n" + "=" * 100)
    print(f"결과 요약: 정상 {ok_count}개 / 문제 {len(fail_domains)}개 (총 {len(results)}개)")
    if fail_domains:
        print("\n⚠️ 여전히 문제 있는 사이트:")
        for d in fail_domains:
            print(f"  - {d}")

    sys.exit(1 if fail_domains else 0)


if __name__ == "__main__":
    main()
