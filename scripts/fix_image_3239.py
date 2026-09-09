#!/usr/bin/env python3
"""One-off: remove garbled-text featured image on koreainvest365.com post 3239."""
import os
import requests
from requests.auth import HTTPBasicAuth

WP_USER = "huh0303@gmail.com"
pw = os.environ["KOREAINVEST365COM"]
auth = HTTPBasicAuth(WP_USER, pw)
base = "https://koreainvest365.com/wp-json/wp/v2"
r = requests.post(f"{base}/posts/3239", auth=auth, json={"featured_media": 0}, timeout=30)
print("update:", r.status_code)
r2 = requests.get(f"{base}/posts/3239", params={"_fields": "featured_media"}, timeout=20)
print("verify:", r2.json())
