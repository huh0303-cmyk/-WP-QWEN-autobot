import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, build_diverse_title

site = next(s for s in SITES_CONFIG if s["url"] == "https://koreamedicaltour.com")
pw = os.getenv(site["wp_pass_env"], "")
new_title = build_diverse_title("Busan Medical Tourism Benefits", "en", site_url=site["url"])
r = requests.patch(f"{site['url']}/wp-json/wp/v2/posts/984", auth=(WP_USER, pw),
                    json={"title": new_title}, timeout=20)
result = {"new_title": new_title, "status": r.status_code}
with open("fix_last_cheesy_result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False)
print(result)
