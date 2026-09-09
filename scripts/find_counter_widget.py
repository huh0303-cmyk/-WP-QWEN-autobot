#!/usr/bin/env python3
"""One-off: find the widget containing the oversized uagb-counter star icon."""
import os
import requests
from requests.auth import HTTPBasicAuth

WP_USER = "huh0303@gmail.com"
pw = os.environ["KTRIP365COM"]
auth = HTTPBasicAuth(WP_USER, pw)
base = "https://k-trip365.com/wp-json/wp/v2"

r = requests.get(f"{base}/widgets", auth=auth, params={"per_page": 100, "context": "edit"}, timeout=30)
print("status:", r.status_code)
widgets = r.json()
for w in widgets:
    content = ""
    if isinstance(w.get("content"), dict):
        content = w["content"].get("raw", "") or w["content"].get("rendered", "")
    elif isinstance(w.get("content"), str):
        content = w["content"]
    instance_raw = str(w.get("instance", ""))
    if "uagb-counter" in content or "uagb/counter" in content or "counter" in str(w.get("id_base", "")):
        print("=== MATCH ===")
        print("id:", w.get("id"))
        print("id_base:", w.get("id_base"))
        print("sidebar (via _links or separate call needed)")
        print("content:", content[:2000])
        print("---")
