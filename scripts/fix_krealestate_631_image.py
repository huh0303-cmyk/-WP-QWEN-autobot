#!/usr/bin/env python3
"""One-off: remove the garbled-text AI featured image from krealestate365.com post 631.
Not wired into any schedule; delete this file after use.
"""
import os
import requests
from requests.auth import HTTPBasicAuth

WP_USER = "huh0303@gmail.com"
WP_PASS = os.environ["KREALESTATE365COM"]
BASE = "https://krealestate365.com/wp-json/wp/v2"
POST_ID = 631

auth = HTTPBasicAuth(WP_USER, WP_PASS)
r = requests.post(f"{BASE}/posts/{POST_ID}", auth=auth, json={"featured_media": 0}, timeout=30)
print("update post:", r.status_code, r.text[:300])

r2 = requests.get(f"{BASE}/posts/{POST_ID}", params={"_fields": "featured_media"}, timeout=20)
print("verify featured_media now:", r2.json())
