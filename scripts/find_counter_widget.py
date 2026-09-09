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
print("total widgets:", len(widgets) if isinstance(widgets, list) else widgets)
if isinstance(widgets, list):
    for w in widgets:
        print("id:", w.get("id"), "| id_base:", w.get("id_base"), "| sidebar:", w.get("sidebar"))

print("=== template parts ===")
r2 = requests.get(f"{base}/template-parts", auth=auth, params={"per_page": 50, "context": "edit"}, timeout=30)
print("tp status:", r2.status_code)
tps = r2.json()
if isinstance(tps, list):
    for tp in tps:
        content = tp.get("content", {}).get("raw", "") if isinstance(tp.get("content"), dict) else str(tp.get("content"))
        if "uagb" in content.lower() or "counter" in content.lower():
            print("=== TEMPLATE PART MATCH ===")
            print("id/slug:", tp.get("id"), tp.get("slug"), tp.get("area"))
            print(content[:3000])
else:
    print(tps)

print("=== templates (in case sidebar baked into a page template) ===")
r3 = requests.get(f"{base}/templates", auth=auth, params={"per_page": 50, "context": "edit"}, timeout=30)
print("t status:", r3.status_code)
ts = r3.json()
if isinstance(ts, list):
    for t in ts:
        content = t.get("content", {}).get("raw", "") if isinstance(t.get("content"), dict) else str(t.get("content"))
        if "uagb" in content.lower() or "counter" in content.lower():
            print("=== TEMPLATE MATCH ===", t.get("slug"))
