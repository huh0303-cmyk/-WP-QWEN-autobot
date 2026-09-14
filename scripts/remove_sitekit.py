#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""6개 사이트에서 Google Site Kit 플러그인 비활성화 후 완전 삭제"""
import os
import requests

WP_USER = "huh0303@gmail.com"
PLUGIN_SLUG = "google-site-kit/google-site-kit"

TARGET_SITES = [
    {"url": "https://ki-korea.com",        "wp_pass_env": "KIKOREACOM"},
    {"url": "https://krealestate365.com",  "wp_pass_env": "KREALESTATE365COM"},
    {"url": "https://ktech365.com",        "wp_pass_env": "KTECH365COM"},
    {"url": "https://k-visa365.com",       "wp_pass_env": "KVISA365COM"},
    {"url": "https://koreawedding365.com", "wp_pass_env": "KOREAWEDDING365COM"},
    {"url": "https://ksa-korea.org",       "wp_pass_env": "KSAKOREAORG"},
]


def main():
    lines = []
    def log(m):
        print(m); lines.append(m)

    for site in TARGET_SITES:
        url = site["url"]
        wp_pass = os.getenv(site["wp_pass_env"], "")
        if not wp_pass:
            log(f"🌐 {url} → 비밀번호 없음")
            continue

        # 1) 비활성화
        r1 = requests.post(f"{url}/wp-json/wp/v2/plugins/{PLUGIN_SLUG}",
                           auth=(WP_USER, wp_pass), json={"status": "inactive"}, timeout=20)
        if r1.status_code not in (200, 201):
            log(f"🌐 {url} → 비활성화 실패 (HTTP {r1.status_code}): {r1.text[:150]}")
            continue
        log(f"🌐 {url} → ✅ 비활성화 완료")

        # 2) 완전 삭제
        r2 = requests.delete(f"{url}/wp-json/wp/v2/plugins/{PLUGIN_SLUG}",
                             auth=(WP_USER, wp_pass), timeout=20)
        if r2.status_code in (200, 201):
            log(f"🌐 {url} → ✅ 완전 삭제 완료")
        else:
            log(f"🌐 {url} → ⚠️ 삭제 실패 (HTTP {r2.status_code}): {r2.text[:150]} (비활성화는 됨)")

    with open("remove_sitekit_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
