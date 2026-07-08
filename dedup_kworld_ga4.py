#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kworld365.com footer-1 위젯영역에 중복 삽입된 GA4 커스텀 HTML 위젯 정리 (1개만 남김)"""
import os
import requests

WP_USER = "huh0303@gmail.com"
SITE_URL = "https://kworld365.com"
WP_PASS = os.getenv("KWORLD365COM", "")


def main():
    if not WP_PASS:
        print("❌ 비밀번호 없음")
        return

    r = requests.get(f"{SITE_URL}/wp-json/wp/v2/widgets",
                     auth=(WP_USER, WP_PASS),
                     params={"sidebar": "footer-1"}, timeout=20)
    print(f"HTTP {r.status_code}")
    if r.status_code != 200:
        print(r.text[:300])
        return

    widgets = r.json()
    ga4_widgets = [w for w in widgets if w.get("id_base") == "custom_html"
                   and "gtag" in str(w.get("rendered", "")) + str(w.get("instance", {}))]
    print(f"GA4 관련 커스텀 HTML 위젯 {len(ga4_widgets)}개 발견")
    for w in ga4_widgets:
        print(f"  - id: {w.get('id')}")

    if len(ga4_widgets) <= 1:
        print("중복 없음, 정리할 것 없음")
        return

    # 첫 번째만 남기고 나머지 삭제
    for w in ga4_widgets[1:]:
        wid = w.get("id")
        dr = requests.delete(f"{SITE_URL}/wp-json/wp/v2/widgets/{wid}",
                             auth=(WP_USER, WP_PASS), params={"force": True}, timeout=15)
        print(f"삭제 {wid}: HTTP {dr.status_code}")


if __name__ == "__main__":
    main()
