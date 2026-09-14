#!/usr/bin/env python3
import os, requests, json

WP_USER = "huh0303@gmail.com"
WP_PASS = os.getenv("WP_REAL_PASSWORD", "")
SITE = "https://koreacrypto365.com"

s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0"})
s.post(f"{SITE}/wp-login.php", data={"log": WP_USER, "pwd": WP_PASS,
       "wp-submit": "Log In", "redirect_to": f"{SITE}/wp-admin/", "testcookie": "1"}, timeout=25)

r = s.get(f"{SITE}/wp-admin/admin.php?page=rank-math-redirections&url=ethereum-staking", timeout=25)
import re
m = re.search(r'"restNonce":"([a-f0-9]+)"', r.text)
nonce = m.group(1) if m else None
print("nonce:", nonce)

r2 = s.get(f"{SITE}/wp-json/rankmath/v1", headers={"X-WP-Nonce": nonce}, timeout=15)
print("index status:", r2.status_code)
d = r2.json()
related = [k for k in d.get("routes", {}).keys() if "404" in k.lower() or "redirect" in k.lower()]
print("related routes with nonce:", related)
print("total routes:", len(d.get("routes", {})))

with open("diag_nonce_routes_result.json", "w", encoding="utf-8") as f:
    json.dump({"nonce": nonce, "related": related, "all_routes": list(d.get("routes", {}).keys())}, f, ensure_ascii=False, indent=2)
