import json, os, time
import jwt
import requests

GSC_KEY_JSON = os.environ["GSC_SERVICE_ACCOUNT_JSON"]


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
    return r.json()["access_token"]


token = get_token()
headers = {"Authorization": f"Bearer {token}"}
r = requests.get("https://www.googleapis.com/webmasters/v3/sites", headers=headers, timeout=20)
print("STATUS:", r.status_code)
for e in r.json().get("siteEntry", []):
    if "blogspot" in e.get("siteUrl", "") or "trip365" in e.get("siteUrl", ""):
        print(e)

# also try the sitemap submit + a URL inspection to see if it actually returns real data now
inspect = requests.post(
    "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect",
    headers={**headers, "Content-Type": "application/json"},
    json={"inspectionUrl": "https://k-trip365.blogspot.com/", "siteUrl": "https://k-trip365.blogspot.com/"},
    timeout=20,
)
print("INSPECT STATUS:", inspect.status_code)
print(inspect.text[:1500])
