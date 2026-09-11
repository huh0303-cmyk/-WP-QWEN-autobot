#!/usr/bin/env python3
"""One-off: list all code-snippets plugin entries on k-trip365.com to find
what's overriding the homepage <title>/meta description with wrong
(health-institute) text."""
import os
import requests

USER = "huh0303@gmail.com"
PW = os.environ["KTRIP365COM"]
BASE = "https://k-trip365.com/wp-json/code-snippets/v1"

r = requests.get(f"{BASE}/snippets", auth=(USER, PW), params={"per_page": 100}, timeout=30)
r.raise_for_status()
data = r.json()
snippets = data if isinstance(data, list) else data.get("data", data.get("items", []))
print(f"TOTAL SNIPPETS: {len(snippets)}")
for s in snippets:
    name = s.get("name", "")
    active = s.get("active")
    code = s.get("code", "")
    flag = "건강정보" in code or "health" in code.lower() or "title" in code.lower() or "description" in code.lower()
    print(f"--- id={s.get('id')} active={active} name={name!r} flagged={flag} ---")
    if flag:
        print(code[:2000])
        print("...")
