#!/usr/bin/env python3
"""One-off: remove garbled AI-text featured images found in a recent sweep.
Not wired into any schedule; delete this file after use.
"""
import os
import requests
from requests.auth import HTTPBasicAuth

WP_USER = "huh0303@gmail.com"

TARGETS = [
    ("kfinance365.com", 3935, "KFINANCE365COM"),
    ("koreataxnlaw.com", 3982, "KOREATAXNLAWCOM"),
    ("koreacrypto365.com", 3294, "KOREACRYPTO365COM"),
    ("koreacrypto365.com", 3296, "KOREACRYPTO365COM"),
]

for domain, post_id, secret_name in TARGETS:
    pw = os.environ[secret_name]
    auth = HTTPBasicAuth(WP_USER, pw)
    base = f"https://{domain}/wp-json/wp/v2"
    r = requests.post(f"{base}/posts/{post_id}", auth=auth, json={"featured_media": 0}, timeout=30)
    print(domain, post_id, "update:", r.status_code)
    r2 = requests.get(f"{base}/posts/{post_id}", params={"_fields": "featured_media"}, timeout=20)
    print(domain, post_id, "verify:", r2.json())
