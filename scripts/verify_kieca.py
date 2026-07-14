import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://kieca-korea.org")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]

out = []
for slug in ["contact", "about"]:
    r = requests.get(f"{base}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                      params={"slug": slug}, timeout=20)
    m = r.json()
    if m:
        content = m[0].get("content", {}).get("rendered", "")
        out.append({"slug": slug, "has_lorem": "Lorem ipsum" in content, "preview": content[:200]})

with open("kieca_verify.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2))
