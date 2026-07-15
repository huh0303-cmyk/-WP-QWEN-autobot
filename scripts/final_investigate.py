import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

out = {}

MENU_SITES = ["https://koreacrypto365.com", "https://kskin365.com", "https://k-visa365.com",
              "https://studyinkorea365.com", "https://kieca-korea.org", "https://koreanews365.com"]

for site_url in MENU_SITES:
    site = next((s for s in SITES_CONFIG if s["url"] == site_url), None)
    pw = os.getenv(site["wp_pass_env"], "")
    entry = {}
    rl = requests.get(f"{site_url}/wp-json/wp/v2/menu-locations", auth=(WP_USER, pw), timeout=20)
    locs = rl.json() if rl.status_code == 200 else {}
    entry["locations_raw"] = locs
    for loc_name, loc in locs.items():
        menu_id = loc.get("menu")
        if not menu_id:
            continue
        rmi = requests.get(f"{site_url}/wp-json/wp/v2/menu-items", auth=(WP_USER, pw),
                            params={"menus": menu_id, "per_page": 100}, timeout=25)
        items = rmi.json() if rmi.status_code == 200 else []
        entry[f"{loc_name}_menu_{menu_id}_items"] = [
            {"title": it.get("title", {}).get("rendered"), "url": it.get("url")} for it in items]
    out[site_url] = entry

site = next(s for s in SITES_CONFIG if s["url"] == "https://k-trip365.com")
pw = os.getenv(site["wp_pass_env"], "")
r = requests.get("https://k-trip365.com/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                  params={"per_page": 30, "status": "publish", "orderby": "date", "order": "desc",
                          "_fields": "id,title,date,content"}, timeout=30)
posts = r.json() if r.status_code == 200 else []
broken = []
for p in posts:
    title = p["title"]["rendered"].strip()
    if re.search(r'^\s*◇', title):
        broken.append({"id": p["id"], "title": title, "date": p.get("date")})
out["ktrip365_broken"] = broken

with open("final_investigate_result.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2)[:4000])
