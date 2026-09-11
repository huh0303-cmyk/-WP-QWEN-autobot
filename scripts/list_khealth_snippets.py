import os, requests
USER = "huh0303@gmail.com"
PW = os.environ["KHEALTH365COM"]
BASE = "https://k-health365.com/wp-json/code-snippets/v1"
r = requests.get(f"{BASE}/snippets", auth=(USER, PW), params={"per_page": 100}, timeout=30)
r.raise_for_status()
data = r.json()
snippets = data if isinstance(data, list) else data.get("data", data.get("items", []))
print("TOTAL:", len(snippets))
for s in snippets:
    print(s.get("id"), s.get("active"), "|", s.get("name"))
