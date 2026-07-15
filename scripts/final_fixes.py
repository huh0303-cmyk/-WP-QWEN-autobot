import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, build_diverse_title

log = {}


def get_pw(url):
    site = next(s for s in SITES_CONFIG if s["url"] == url)
    return site, os.getenv(site["wp_pass_env"], "")


SLUG_FIX_SITES = ["https://koreacrypto365.com", "https://k-visa365.com",
                   "https://studyinkorea365.com", "https://kieca-korea.org"]
log["slug_fix"] = []
for site_url in SLUG_FIX_SITES:
    site, pw = get_pw(site_url)
    entry = {"site": site_url}
    r = requests.get(f"{site_url}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                      params={"slug": "privacy-policy-2"}, timeout=20)
    m = r.json()
    if not m:
        entry["error"] = "privacy-policy-2 페이지 못찾음"
        log["slug_fix"].append(entry)
        continue
    pid = m[0]["id"]
    pr = requests.patch(f"{site_url}/wp-json/wp/v2/pages/{pid}", auth=(WP_USER, pw),
                         json={"slug": "privacy-policy"}, timeout=25)
    new_link = pr.json().get("link") if pr.status_code in (200, 201) else None
    entry["rename_status"] = pr.status_code
    entry["new_link"] = new_link

    old_url_frag = "privacy-policy-2"
    updated_items = []
    rmi = requests.get(f"{site_url}/wp-json/wp/v2/menu-items", auth=(WP_USER, pw),
                        params={"per_page": 100}, timeout=25)
    items = rmi.json() if rmi.status_code == 200 else []
    for it in items:
        if old_url_frag in (it.get("url") or ""):
            up = requests.patch(f"{site_url}/wp-json/wp/v2/menu-items/{it['id']}",
                                 auth=(WP_USER, pw), json={"url": new_link}, timeout=20)
            updated_items.append({"id": it["id"], "status": up.status_code})
    entry["menu_items_updated"] = updated_items
    log["slug_fix"].append(entry)


site_url = "https://kskin365.com"
site, pw = get_pw(site_url)
r = requests.put(f"{site_url}/wp-json/wp/v2/menus/412", auth=(WP_USER, pw),
                  json={"locations": ["primary"]}, timeout=25)
log["kskin365_location_fix"] = {"status": r.status_code, "body": r.text[:300]}


site_url = "https://k-trip365.com"
site, pw = get_pw(site_url)
BROKEN_IDS = {4388: "Brian Choi", 4386: "Catherine Han"}
log["ktrip365_title_fix"] = []
for pid, reporter_name in BROKEN_IDS.items():
    r2 = requests.get(f"{site_url}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw),
                       params={"_fields": "id,content,meta"}, timeout=25)
    p = r2.json()
    content = p.get("content", {}).get("rendered", "")
    meta_obj = p.get("meta", {}) or {}
    keyword = meta_obj.get("rank_math_focus_keyword", "")
    if not keyword or len(keyword) < 4:
        plain = re.sub(r'<[^>]+>', ' ', content)
        keyword = re.sub(r'\s+', ' ', plain).strip()[:40] or "Korea travel guide"
    new_title = build_diverse_title(keyword.split(",")[0].strip(), "en", site_url=site_url)
    pr2 = requests.patch(f"{site_url}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw),
                          json={"title": new_title}, timeout=25)
    log["ktrip365_title_fix"].append({"id": pid, "new_title": new_title, "status": pr2.status_code})

with open("final_fixes_result.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print(json.dumps(log, ensure_ascii=False, indent=2))
