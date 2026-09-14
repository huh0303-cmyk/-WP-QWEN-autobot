#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""리디렉션 추가/저장 폼 구조를 확인하기 위한 1회성 진단."""
import os, requests

WP_USER = "huh0303@gmail.com"
WP_PASS = os.getenv("WP_REAL_PASSWORD", "")
SITE = "https://koreacrypto365.com"

s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0"})
s.post(
    f"{SITE}/wp-login.php",
    data={"log": WP_USER, "pwd": WP_PASS, "wp-submit": "Log In",
          "redirect_to": f"{SITE}/wp-admin/", "testcookie": "1"},
    timeout=25,
)

r = s.get(f"{SITE}/wp-admin/admin.php?page=rank-math-redirections&url=ethereum-staking", timeout=25)
with open("redir_add_page.html", "w", encoding="utf-8") as f:
    f.write(r.text)
print("status:", r.status_code, "len:", len(r.text))

# 폼 태그와 input/nonce 관련 라인만 추려서 출력 (로그로도 확인)
import re
for m in re.finditer(r'<(form|input|select|textarea)[^>]*>', r.text, re.IGNORECASE):
    tag = m.group(0)
    if any(k in tag.lower() for k in ["nonce", "name=", "action=", "redirect", "source", "url", "destination"]):
        print(tag[:200])
