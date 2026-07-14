import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

site = next(s for s in SITES_CONFIG if s["url"] == "https://theseouljournal.com")
pw = os.getenv(site["wp_pass_env"], "")
base = site["url"]

out = {}
for slug in ["disclaimer", "contact", "about", "privacy-policy"]:
    r = requests.get(f"{base}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                      params={"slug": slug}, timeout=20)
    m = r.json()
    if m:
        pid = m[0]["id"]
        out[slug] = {
            "id": pid,
            "edit_link": f"{base}/wp-admin/post.php?post={pid}&action=elementor"
        }

with open("seoul_journal_edit_links.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2))
