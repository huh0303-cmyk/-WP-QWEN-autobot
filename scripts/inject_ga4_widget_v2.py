#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inject_ga4_widget.py (실제 삽입판)
─────────────────────────────────────────────────────────────
각 사이트의 사용 가능한 위젯 영역 중 "footer" 계열을 최우선으로,
없으면 "sidebar"/"right-sidebar" 등을 골라 커스텀 HTML 위젯으로
GA4 추적 코드를 삽입합니다.

환경변수 TEST_ONLY=true 로 두면 kworld365.com 한 곳에만 적용합니다.
"""

import os
import requests

WP_USER = "huh0303@gmail.com"
GA4_MEASUREMENT_ID = os.getenv("GA4_MEASUREMENT_ID", "")
TEST_ONLY = os.getenv("TEST_ONLY", "false").lower() == "true"

SITES = [
    {"url": "https://k-health365.com",        "wp_pass_env": "KHEALTH365COM"},
    {"url": "https://koreamedicaltour.com",   "wp_pass_env": "KOREAMEDICALTOURCOM"},
    {"url": "https://koreainvest365.com",     "wp_pass_env": "KOREAINVEST365COM"},
    {"url": "https://ki-korea.com",           "wp_pass_env": "KIKOREACOM"},
    {"url": "https://koreainsurance365.com",  "wp_pass_env": "KOREAINSURANCE365COM"},
    {"url": "https://kfinance365.com",        "wp_pass_env": "KFINANCE365COM"},
    {"url": "https://koreataxnlaw.com",       "wp_pass_env": "KOREATAXNLAWCOM"},
    {"url": "https://koreacrypto365.com",     "wp_pass_env": "KOREACRYPTO365COM"},
    {"url": "https://krealestate365.com",     "wp_pass_env": "KREALESTATE365COM"},
    {"url": "https://ktech365.com",           "wp_pass_env": "KTECH365COM"},
    {"url": "https://kskin365.com",           "wp_pass_env": "KSKIN365COM"},
    {"url": "https://oliveyoungkorea.com",    "wp_pass_env": "OLIVEYOUNGKOREACOM"},
    {"url": "https://kworld365.com",          "wp_pass_env": "KWORLD365COM"},
    {"url": "https://k-trip365.com",          "wp_pass_env": "KTRIP365COM"},
    {"url": "https://k-visa365.com",          "wp_pass_env": "KVISA365COM"},
    {"url": "https://koreawedding365.com",    "wp_pass_env": "KOREAWEDDING365COM"},
    {"url": "https://kstudy365.com",          "wp_pass_env": "KSTUDY365COM"},
    {"url": "https://studyinkorea365.com",    "wp_pass_env": "STUDYINKOREA365COM"},
    {"url": "https://kieca-korea.org",        "wp_pass_env": "KIECAKOREAORG"},
    {"url": "https://ksa-korea.org",          "wp_pass_env": "KSAKOREAORG"},
    {"url": "https://sis-korea.com",          "wp_pass_env": "SISKOREACOM"},
    {"url": "https://jobkorea365.com",        "wp_pass_env": "JOBKOREA365COM"},
    {"url": "https://jobinkorea365.com",      "wp_pass_env": "JOBINKOREA365COM"},
    {"url": "https://jobkoreaglobal.com",     "wp_pass_env": "JOBKOREAGLOBALCOM"},
    {"url": "https://korea365.org",           "wp_pass_env": "KOREA365ORG"},
    {"url": "https://koreanews365.com",       "wp_pass_env": "KOREANEWS365COM"},
    {"url": "https://theseouljournal.com",    "wp_pass_env": "THESEOULJOURNALCOM"},
]

GA4_SNIPPET = f"""<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_MEASUREMENT_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA4_MEASUREMENT_ID}');
</script>"""


def pick_sidebar(sidebars):
    ids = [s.get("id") for s in sidebars if s.get("id") != "wp_inactive_widgets"]
    footer_ids = [i for i in ids if "footer" in i.lower()]
    if footer_ids:
        return sorted(footer_ids)[0]
    sidebar_ids = [i for i in ids if "sidebar" in i.lower()]
    if sidebar_ids:
        return sorted(sidebar_ids)[0]
    return ids[0] if ids else None


def inject_site(site_url, wp_pass):
    r = requests.get(f"{site_url}/wp-json/wp/v2/sidebars", auth=(WP_USER, wp_pass), timeout=15)
    if r.status_code != 200:
        return f"❌ 위젯영역 조회 실패 (HTTP {r.status_code})"
    sidebars = r.json()
    target = pick_sidebar(sidebars)
    if not target:
        return "❌ 사용 가능한 위젯영역 없음"

    payload = {
        "id_base": "custom_html",
        "sidebar": target,
        "instance": {
            "raw": {
                "title": "",
                "content": GA4_SNIPPET,
            }
        },
    }
    wr = requests.post(f"{site_url}/wp-json/wp/v2/widgets",
                       auth=(WP_USER, wp_pass), json=payload, timeout=20)
    if wr.status_code in (200, 201):
        return f"✅ 삽입 완료 (위젯영역: {target})"
    return f"❌ 삽입 실패 (HTTP {wr.status_code}): {wr.text[:150]}"


def main():
    lines = []
    def log(m):
        print(m); lines.append(m)

    if not GA4_MEASUREMENT_ID:
        log("❌ GA4_MEASUREMENT_ID 환경변수가 없습니다.")
        with open("inject_ga4_results.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return

    log(f"{'='*60}")
    log(f"🔧 GA4 코드 위젯 삽입 {'(TEST_ONLY: kworld365.com만)' if TEST_ONLY else '(27개 사이트 전체)'}")
    log(f"   측정 ID: {GA4_MEASUREMENT_ID}")
    log(f"{'='*60}")

    targets = [s for s in SITES if "kworld365" in s["url"]] if TEST_ONLY else SITES

    for site in targets:
        url = site["url"]
        wp_pass = os.getenv(site["wp_pass_env"], "")
        if not wp_pass:
            log(f"🌐 {url} → 비밀번호 없음")
            continue
        result = inject_site(url, wp_pass)
        log(f"🌐 {url} → {result}")

    with open("inject_ga4_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
