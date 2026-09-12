import os
import requests

SITE = "https://koreanews365.com"
AUTH = ("huh0303@gmail.com", os.environ["KOREANEWS365COM"])

css = open("koreanews_masthead_v2.css", encoding="utf-8").read()

payload = {
    "name": "KN365 mobile category bar + newsprint masthead (2026-09-12)",
    "desc": "Always-visible horizontal category strip on mobile + newsprint-style masthead background.",
    "code": css,
    "scope": "site-css",
    "active": True,
    "priority": 20,
    "tags": ["kn365", "masthead", "2026-09-12"],
}

for attempt in range(3):
    r = requests.post(f"{SITE}/wp-json/code-snippets/v1/snippets", auth=AUTH, json=payload, timeout=25)
    print(attempt, r.status_code, r.text[:300])
    if r.status_code in (200, 201):
        break
