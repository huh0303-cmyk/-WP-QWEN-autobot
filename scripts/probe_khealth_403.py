import os, requests
from requests.auth import HTTPBasicAuth
USER = "huh0303@gmail.com"
PW = os.environ["KHEALTH365COM"]
BASE = "https://k-health365.com/wp-json/code-snippets/v1"
r = requests.post(f"{BASE}/snippets", auth=HTTPBasicAuth(USER, PW),
                   json={"name":"probe","code":"// noop","scope":"global","active":False}, timeout=30)
print("STATUS:", r.status_code)
print("HEADERS:", dict(r.headers))
print("BODY:", r.text[:1000])
