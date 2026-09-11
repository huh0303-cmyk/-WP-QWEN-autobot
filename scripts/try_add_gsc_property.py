#!/usr/bin/env python3
"""Try to add one Blogspot blog as a Search Console property using the
real Google-account OAuth refresh token (BLOGGER_GOOGLE_REFRESH_TOKEN),
not the GSC service account. Blogger-owned blogs under the same Google
account can auto-verify in Search Console, but only if this refresh
token's original consent included the webmasters scope. If not, this
will fail with an insufficient-scope error and a human OAuth re-consent
is unavoidable."""
import os
import requests

TEST_SITE = "https://k-trip365.blogspot.com/"


def access_token():
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": os.environ["BLOGGER_GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["BLOGGER_GOOGLE_CLIENT_SECRET"],
            "refresh_token": os.environ["BLOGGER_GOOGLE_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    print("token refresh status:", r.status_code)
    body = r.json()
    print("granted scope:", body.get("scope"))
    r.raise_for_status()
    return body["access_token"]


token = access_token()
headers = {"Authorization": f"Bearer {token}"}

# list what this token can already see
list_resp = requests.get("https://www.googleapis.com/webmasters/v3/sites", headers=headers, timeout=20)
print("list sites status:", list_resp.status_code)
print(list_resp.text[:1000])

add_resp = requests.put(
    f"https://www.googleapis.com/webmasters/v3/sites/{requests.utils.quote(TEST_SITE, safe='')}",
    headers=headers, timeout=20,
)
print("add property status:", add_resp.status_code)
print(add_resp.text[:1000])
