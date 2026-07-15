import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://kskin365.com")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]

log = {}

r = requests.post(f"{base}/wp-json/wp/v2/settings", auth=(WP_USER, pw),
                   json={"title": "Kskin365", "description": "Korean Skincare & K-Beauty Guide"}, timeout=25)
log["settings_update"] = {"status": r.status_code, "body": r.text[:300]}

r2 = requests.get(f"{base}/wp-json/wp/v2/widgets", auth=(WP_USER, pw), timeout=25)
log["widgets_status"] = r2.status_code
widgets = r2.json() if r2.status_code == 200 else []
log["widgets_found"] = [{"id": w.get("id"), "idBase": w.get("id_base"),
                          "content": str(w.get("instance", {}).get("raw", {}).get("content", ""))[:100]}
                         for w in widgets]

target = None
for w in widgets:
    content = str(w.get("instance", {}).get("raw", {}).get("content", ""))
    if "free shipping" in content.lower() or w.get("id") == "block-14":
        target = w
        break

if target:
    del_r = requests.delete(f"{base}/wp-json/wp/v2/widgets/{target['id']}", auth=(WP_USER, pw),
                             params={"force": "true"}, timeout=25)
    log["widget_delete"] = {"id": target["id"], "status": del_r.status_code}
else:
    log["widget_delete"] = "타겟 위젯 못찾음"

with open("kskin365_fix_result.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print(json.dumps(log, ensure_ascii=False, indent=2)[:3000])
