#!/usr/bin/env python3
"""One-off: trash the older of two near-duplicate 'Seoul central...by subway' posts on k-trip365.com."""
import os
import requests
from requests.auth import HTTPBasicAuth

WP_USER = "huh0303@gmail.com"
pw = os.environ["KTRIP365COM"]
auth = HTTPBasicAuth(WP_USER, pw)
base = "https://k-trip365.com/wp-json/wp/v2"

r = requests.delete(f"{base}/posts/4731", auth=auth, timeout=30)
print("delete 4731:", r.status_code, r.json().get("status") if r.ok else r.text[:200])
