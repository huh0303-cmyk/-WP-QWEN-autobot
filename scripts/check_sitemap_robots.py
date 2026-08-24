#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_sitemap_robots.py

k-health365.com을 제외한 26개 사이트의 sitemap_index.xml / robots.txt 상태를 점검하고,
문제가 있으면 자동 복구를 시도합니다 (setup_sites.py의 검증된 로직 재사용).

  1) sitemap_index.xml: 200 응답 + 본문에 "sitemap" 포함 확인
     실패 시 -> 퍼머링크 재저장(/%postname%/)으로 사이트맵 재생성 시도
  2) robots.txt: 200 응답 + "allow" 포함(전체 차단 아님) 확인
     실패 시 -> Rank Math robots.txt API로 정상 콘텐츠 재설정 시도

삭제는 하지 않는 점검+자동복구 스크립트입니다.
"""
import os, json, requests

WP_USER = "huh0303@gmail.com"

SITES = [
    ("https://koreamedicaltour.com",   "KOREAMEDICALTOURCOM"),
    ("https://koreainvest365.com",     "KOREAINVEST365COM"),
    ("https://ki-korea.com",           "KIKOREACOM"),
    ("https://koreainsurance365.com",  "KOREAINSURANCE365COM"),
    ("https://kfinance365.com",        "KFINANCE365COM"),
    ("https://koreataxnlaw.com",       "KOREATAXNLAWCOM"),
    ("https://koreacrypto365.com",     "KOREACRYPTO365COM"),
    ("https://krealestate365.com",     "KREALESTATE365COM"),
    ("https://ktech365.com",           "KTECH365COM"),
    ("https://oliveyoungkorea.com",    "OLIVEYOUNGKOREACOM"),
    ("https://kworld365.com",          "KWORLD365COM"),
    ("https://k-trip365.com",          "KTRIP365COM"),
    ("https://k-visa365.com",          "KVISA365COM"),
    ("https://koreawedding365.com",    "KOREAWEDDING365COM"),
    ("https://kstudy365.com",          "KSTUDY365COM"),
    ("https://studyinkorea365.com",    "STUDYINKOREA365COM"),
    ("https://kieca-korea.org",        "KIECAKOREAORG"),
    ("https://ksa-korea.org",          "KSAKOREAORG"),
    ("https://sis-korea.com",          "SISKOREACOM"),
    ("https://jobkorea365.com",        "JOBKOREA365COM"),
    ("https://jobinkorea365.com",      "JOBINKOREA365COM"),
    ("https://jobkoreaglobal.com",     "JOBKOREAGLOBALCOM"),
    ("https://korea365.org",           "KOREA365ORG"),
    ("https://koreanews365.com",       "KOREANEWS365COM"),
    ("https://theseouljournal.com",    "THESEOULJOURNALCOM"),
]

ROBOTS_CONTENT = (
    "User-agent: *\n"
    "Allow: /\n"
    "Disallow: /wp-admin/\n"
    "Allow: /wp-admin/admin-ajax.php\n"
)


def auth(pw):
    return requests.auth.HTTPBasicAuth(WP_USER, pw)


def check_sitemap(site_url, pw):
    try:
        r = requests.get(f"{site_url}/sitemap_index.xml", timeout=10,
                          headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200 and "sitemap" in r.text.lower():
            return True, None
        issue = f"HTTP {r.status_code}" if r.status_code != 200 else "sitemap 키워드 없음"
    except Exception as e:
        issue = str(e)

    # 자동복구 시도: 퍼머링크 재저장
    try:
        requests.post(f"{site_url}/wp-json/wp/v2/settings", auth=auth(pw),
                      json={"permalink_structure": "/%postname%/"}, timeout=10)
        r2 = requests.get(f"{site_url}/sitemap_index.xml", timeout=10,
                           headers={"User-Agent": "Mozilla/5.0"})
        if r2.status_code == 200 and "sitemap" in r2.text.lower():
            return True, f"자동복구됨 (기존문제: {issue})"
    except Exception:
        pass
    return False, issue


def check_robots(site_url, pw):
    try:
        r = requests.get(f"{site_url}/robots.txt", timeout=10,
                          headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200 and "allow" in r.text.lower() and "disallow: /\n" not in r.text.lower().replace(" ", ""):
            return True, None
        issue = f"HTTP {r.status_code}" if r.status_code != 200 else "전체차단 의심 또는 allow 없음"
    except Exception as e:
        issue = str(e)

    # 자동복구 시도: Rank Math robots.txt API
    try:
        r2 = requests.post(f"{site_url}/wp-json/rankmath/v1/updateRobotsTxt", auth=auth(pw),
                           json={"robots_txt": ROBOTS_CONTENT}, timeout=10)
        if r2.status_code in (200, 201):
            return True, f"자동복구됨 (기존문제: {issue})"
    except Exception:
        pass
    return False, issue


def main():
    results = []
    for site_url, secret_name in SITES:
        pw = os.environ.get(secret_name, "")
        if not pw:
            print(f"⚠️  {site_url} — Secret 없음, 스킵")
            continue

        sitemap_ok, sitemap_note = check_sitemap(site_url, pw)
        robots_ok, robots_note = check_robots(site_url, pw)

        rec = {
            "site": site_url,
            "sitemap_ok": sitemap_ok, "sitemap_note": sitemap_note,
            "robots_ok": robots_ok, "robots_note": robots_note,
        }
        results.append(rec)
        s_icon = "✅" if sitemap_ok else "❌"
        r_icon = "✅" if robots_ok else "❌"
        print(f"{s_icon} sitemap / {r_icon} robots — {site_url}"
              + (f"  [sitemap: {sitemap_note}]" if sitemap_note else "")
              + (f"  [robots: {robots_note}]" if robots_note else ""))

    bad_sitemap = [r["site"] for r in results if not r["sitemap_ok"]]
    bad_robots = [r["site"] for r in results if not r["robots_ok"]]

    print("\n" + "=" * 60)
    print(f"전체 {len(results)}개 사이트 점검 완료")
    print(f"sitemap 문제(자동복구 실패): {len(bad_sitemap)}개 -> {bad_sitemap}")
    print(f"robots.txt 문제(자동복구 실패): {len(bad_robots)}개 -> {bad_robots}")

    with open("check_sitemap_robots_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
