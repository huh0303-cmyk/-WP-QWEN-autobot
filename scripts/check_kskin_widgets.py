import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://kskin365.com")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]

r = requests.get(f"{base}/wp-json/wp/v2/widgets", auth=(WP_USER, pw), timeout=25)
widgets = r.json() if r.status_code == 200 else []

out = []
for w in widgets:
    instance = w.get("instance", {}) or {}
    raw = instance.get("raw", {}) if isinstance(instance, dict) else {}
    content = raw.get("content", "") if isinstance(raw, dict) else ""
    rendered = w.get("rendered", "")
    out.append({
        "id": w.get("id"),
        "id_base": w.get("id_base"),
        "sidebar": w.get("sidebar"),
        "content_raw": content,
        "rendered_preview": rendered[:400],
    })

with open("kskin365_all_widgets.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2)[:6000])
