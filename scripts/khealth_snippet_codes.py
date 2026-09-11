import os, requests, json
USER = "huh0303@gmail.com"
PW = os.environ["KHEALTH365COM"]
BASE = "https://k-health365.com/wp-json/code-snippets/v1"
targets = [7, 15, 16, 19, 24, 25, 26, 29]
for sid in targets:
    r = requests.get(f"{BASE}/snippets/{sid}", auth=(USER, PW), timeout=30)
    if r.status_code == 200:
        s = r.json()
        print(f"=== id={sid} name={s.get('name')!r} ===")
        print(s.get("code", "")[:800])
        print()
