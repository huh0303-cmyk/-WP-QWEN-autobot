#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kworld365.com 애드센스 필수 페이지(About/Contact/Privacy/Disclaimer) 존재 확인"""
import os, requests

WP_USER = "huh0303@gmail.com"
SITE_URL = "https://kworld365.com"
WP_PASS = os.getenv("KWORLD365COM", "")

REQUIRED_KEYWORDS = {
    "About":      ["about", "소개"],
    "Contact":    ["contact", "문의"],
    "Privacy":    ["privacy", "개인정보"],
    "Disclaimer": ["disclaimer", "면책"],
}

def main():
    lines = []
    def log(m):
        print(m); lines.append(m)

    if not WP_PASS:
        log("❌ KWORLD365COM 비밀번호 없음")
        with open("check_kworld_pages_results.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return

    r = requests.get(f"{SITE_URL}/wp-json/wp/v2/pages",
                     auth=(WP_USER, WP_PASS),
                     params={"per_page": 100, "status": "publish", "_fields": "id,title,link,slug,status"},
                     timeout=20)
    log(f"HTTP {r.status_code}")
    pages = r.json() if r.status_code == 200 else []
    log(f"발행된 페이지 총 {len(pages)}개:\n")
    for p in pages:
        t = p.get("title", {}).get("rendered", "")
        log(f"  - {t} → {p.get('link')} (slug: {p.get('slug')})")

    log("\n필수 4페이지 체크:")
    for name, kws in REQUIRED_KEYWORDS.items():
        found = None
        for p in pages:
            t = p.get("title", {}).get("rendered", "").lower()
            s = p.get("slug", "").lower()
            if any(k in t or k in s for k in kws):
                found = p.get("link")
                break
        status = f"✅ 있음 ({found})" if found else "❌ 없음"
        log(f"  {name}: {status}")

    with open("check_kworld_pages_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

if __name__ == "__main__":
    main()
