import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, build_diverse_title

site = next(s for s in SITES_CONFIG if s["url"] == "https://jobkoreaglobal.com")
pw = os.getenv(site["wp_pass_env"], "")

manual_keywords = {
    607: "Growth Hacker Jobs in Korea",
    592: "Private Equity Jobs in Korea for Foreigners",
    570: "Bilingual Project Manager Roles in Tech",
    549: "Cross-Border Trade Careers in Korea",
    542: "WTO Korea Representative Jobs",
}

log = []
for pid, kw in manual_keywords.items():
    new_title = build_diverse_title(kw, "en", site_url=site["url"])
    r = requests.patch(f"{site['url']}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw),
                        json={"title": new_title}, timeout=20)
    log.append({"id": pid, "keyword": kw, "new": new_title, "status": r.status_code})

with open("manual_fix_result.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print(json.dumps(log, ensure_ascii=False, indent=2))
