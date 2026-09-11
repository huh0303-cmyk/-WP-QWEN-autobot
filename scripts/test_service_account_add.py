#!/usr/bin/env python3
"""Test whether the existing GSC_SERVICE_ACCOUNT_JSON service account can
add a NEW Search Console property (not just read ones it's already been
granted access to) - if yes, we can register all 33 Blogspot blogs
without any human browser login at all."""
import json
import os
import time
import jwt
import requests

GSC_KEY_JSON = os.environ["GSC_SERVICE_ACCOUNT_JSON"]
TEST_SITE = "https://k-trip365.blogspot.com/"


def get_token():
    key_data = json.loads(GSC_KEY_JSON)
    now = int(time.time())
    payload = {
        "iss": key_data["client_email"],
        "scope": "https://www.googleapis.com/auth/webmasters",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now, "exp": now + 3600,
    }
    token = jwt.encode(payload, key_data["private_key"], algorithm="RS256")
    r = requests.post("https://oauth2.googleapis.com/token",
                       data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                             "assertion": token}, timeout=20)
    r.raise_for_status()
    return r.json()["access_token"], key_data["client_email"]


token, sa_email = get_token()
print("service account email:", sa_email)
headers = {"Authorization": f"Bearer {token}"}

add_resp = requests.put(
    f"https://www.googleapis.com/webmasters/v3/sites/{requests.utils.quote(TEST_SITE, safe='')}",
    headers=headers, timeout=20,
)
print("add property status:", add_resp.status_code)
print(add_resp.text[:1000])
