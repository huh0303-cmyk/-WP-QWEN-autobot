#!/usr/bin/env python3
"""One-off: from a GitHub Actions runner, reproduce the 403 on
koreanews365.com's /wp-json/wp/v2/posts and list active plugins/snippets
that might be blocking Actions runner IPs specifically."""
import os
import requests
from requests.auth import HTTPBasicAuth

USER = "huh0303@gmail.com"
PW = os.environ["KOREANEWS365COM"]

r = requests.get(
    "https://koreanews365.com/wp-json/wp/v2/posts",
    params={"per_page": 50, "orderby": "date", "order": "desc", "status": "publish",
            "_fields": "id,title,content,link"},
    timeout=20,
)
print("REPRO STATUS:", r.status_code)
print("headers:", dict(r.headers))
print("body:", r.text[:500])

print("\n--- plugins ---")
p = requests.get("https://koreanews365.com/wp-json/wp/v2/plugins", auth=HTTPBasicAuth(USER, PW), timeout=20)
print("plugins status:", p.status_code)
if p.status_code == 200:
    for item in p.json():
        print(item.get("status"), "|", item.get("plugin"), "|", item.get("name"))
