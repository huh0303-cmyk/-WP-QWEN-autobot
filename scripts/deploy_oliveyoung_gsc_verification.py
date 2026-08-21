#!/usr/bin/env python3
"""oliveyoungkorea.com에 Google Search Console HTML 파일 인증
(google69a694c17e369dee.html)을 Code Snippets로 서빙한다. FTP/파일 접근 없이
WordPress 훅으로 정적 파일처럼 동작하게 만드는 표준 우회 방식."""
import os

import requests

SITE = "https://oliveyoungkorea.com"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PASSWORD = os.getenv("OLIVEYOUNGKOREACOM", "").strip()
FILENAME = "google69a694c17e369dee.html"
NAME = "GSC verification file serve"

PHP = f"""
add_action('init', function () {{
    if ($_SERVER['REQUEST_URI'] === '/{FILENAME}' || strpos($_SERVER['REQUEST_URI'], '/{FILENAME}?') === 0) {{
        header('Content-Type: text/html; charset=utf-8');
        echo 'google-site-verification: {FILENAME}';
        exit;
    }}
}}, 1);
"""


def call(method, path, **kwargs):
    r = requests.request(method, f"{SITE}/wp-json/code-snippets/v1/{path}",
                          auth=(USER, PASSWORD), timeout=45, **kwargs)
    r.raise_for_status()
    return r.json() if r.content else {}


def main():
    if not PASSWORD:
        raise SystemExit("Missing OLIVEYOUNGKOREACOM secret")
    payload = {"name": NAME, "desc": f"Serves /{FILENAME} for GSC ownership verification.",
               "code": PHP, "scope": "global", "active": True, "priority": 1,
               "tags": ["gsc", "verification"]}
    existing = call("GET", "snippets", params={"per_page": 100})
    matches = existing if isinstance(existing, list) else existing.get("data", existing.get("items", []))
    matches = [s for s in matches if s.get("name") == NAME]
    if matches:
        result = call("POST", f"snippets/{matches[0]['id']}", json=payload)
        action = "updated"
    else:
        result = call("POST", "snippets", json=payload)
        action = "created"
    if not result.get("active", False):
        raise SystemExit(f"Snippet not active: {result}")
    print(f"{action}: {NAME}")

    check = requests.get(f"{SITE}/{FILENAME}", timeout=20)
    print(f"검증: GET /{FILENAME} -> {check.status_code}")
    print(f"본문: {check.text[:200]}")


if __name__ == "__main__":
    main()
