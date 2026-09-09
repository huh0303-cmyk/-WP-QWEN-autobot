#!/usr/bin/env python3
"""One-off: trash the wrong-language (Korean) post on koreawedding365.com (EN site)."""
import os
import requests
from requests.auth import HTTPBasicAuth

WP_USER = "huh0303@gmail.com"
pw = os.environ["KOREAWEDDING365COM"]
auth = HTTPBasicAuth(WP_USER, pw)
base = "https://koreawedding365.com/wp-json/wp/v2"

r = requests.delete(f"{base}/posts/866", auth=auth, timeout=30)
print("delete 866:", r.status_code, r.json().get("status") if r.ok else r.text[:200])
