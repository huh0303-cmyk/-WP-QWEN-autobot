#!/usr/bin/env python3
import os
import requests
from requests.auth import HTTPBasicAuth

USER = "huh0303@gmail.com"
PW = os.environ["KHEALTH365COM"]
BASE = "https://k-health365.com/wp-json/wp/v2"

r = requests.get(f"{BASE}/plugins", auth=HTTPBasicAuth(USER, PW), params={"per_page": 100}, timeout=30)
print("STATUS:", r.status_code)
if r.status_code == 200:
    for p in r.json():
        print(p.get("status"), "|", p.get("plugin"), "|", p.get("name"))
else:
    print(r.text[:500])
