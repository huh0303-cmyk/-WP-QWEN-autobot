#!/usr/bin/env python3
"""One-off test: can the existing GSC_SERVICE_ACCOUNT_JSON add a brand-new
Search Console property (Search Console API sites.add), not just read
already-registered ones? Read-only audits use webmasters.readonly; this
requests the full webmasters scope and reports the raw API result honestly
- success or failure - for exactly one test URL. Not wired into any
schedule; delete after use.
"""
import json, os, sys, time
import requests

GSC_JSON = os.environ["GSC_SERVICE_ACCOUNT_JSON"]
TEST_SITE = sys.argv[1] if len(sys.argv) > 1 else "https://k-health365.blogspot.com/"

def token():
    import jwt
    key = json.loads(GSC_JSON)
    now = int(time.time())
    assertion = jwt.encode(
        {"iss": key["client_email"], "scope": "https://www.googleapis.com/auth/webmasters",
         "aud": "https://oauth2.googleapis.com/token", "iat": now, "exp": now + 3600},
        key["private_key"], algorithm="RS256",
    )
    r = requests.post("https://oauth2.googleapis.com/token",
                       data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
                       timeout=20)
    r.raise_for_status()
    return r.json()["access_token"]

def main():
    tok = token()
    r = requests.put(f"https://www.googleapis.com/webmasters/v3/sites/{TEST_SITE}",
                      headers={"Authorization": f"Bearer {tok}"}, timeout=20)
    print("service_account_email:", json.loads(GSC_JSON)["client_email"])
    print("test_site:", TEST_SITE)
    print("http_status:", r.status_code)
    print("response_body:", r.text[:1000])

if __name__ == "__main__":
    main()
