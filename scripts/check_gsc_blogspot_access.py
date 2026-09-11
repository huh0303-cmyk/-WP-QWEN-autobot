#!/usr/bin/env python3
"""One-off: check which GSC properties the existing service account can
access, to see whether any of the 33 Blogspot blogs are already verified
there (root-causing why Blogspot posts show zero Google visibility)."""
import json
import os
import time
import jwt
import requests

GSC_KEY_JSON = os.environ["GSC_SERVICE_ACCOUNT_JSON"]


def get_token():
    key_data = json.loads(GSC_KEY_JSON)
    now = int(time.time())
    payload = {
        "iss": key_data["client_email"],
        "scope": "https://www.googleapis.com/auth/webmasters.readonly",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now, "exp": now + 3600,
    }
    token = jwt.encode(payload, key_data["private_key"], algorithm="RS256")
    r = requests.post("https://oauth2.googleapis.com/token",
                       data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                             "assertion": token}, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]


token = get_token()
r = requests.get("https://www.googleapis.com/webmasters/v3/sites",
                  headers={"Authorization": f"Bearer {token}"}, timeout=20)
print("STATUS:", r.status_code)
data = r.json()
entries = data.get("siteEntry", [])
print("TOTAL ACCESSIBLE PROPERTIES:", len(entries))
for e in entries:
    print(e.get("siteUrl"), "|", e.get("permissionLevel"))
blogspot = [e for e in entries if "blogspot" in e.get("siteUrl", "")]
print("\nBLOGSPOT PROPERTIES FOUND:", len(blogspot))
for e in blogspot:
    print(e)
