import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://kskin365.com")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]

out = {}

r = requests.get(f"{base}/wp-json", timeout=20)
out["site_root_status"] = r.status_code
if r.status_code == 200:
    d = r.json()
    out["site_name"] = d.get("name")
    out["site_description"] = d.get("description")
    out["namespaces"] = d.get("namespaces", [])

r2 = requests.get(f"{base}/wp-json/wp/v2/settings", auth=(WP_USER, pw), timeout=20)
out["settings_status"] = r2.status_code
out["settings"] = r2.json() if r2.status_code == 200 else r2.text[:300]

r3 = requests.get(base, timeout=25)
html = r3.text
idx = html.lower().find("free shipping")
out["free_shipping_context"] = html[max(0, idx-400):idx+400] if idx >= 0 else "못찾음"

idx2 = html.lower().find("k-beauty original")
out["kbeauty_original_context"] = html[max(0, idx2-300):idx2+300] if idx2 >= 0 else "못찾음"

out["woocommerce_active_guess"] = any("wc" in n.lower() for n in out.get("namespaces", []))

with open("kskin365_banner_check.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2)[:3000])
