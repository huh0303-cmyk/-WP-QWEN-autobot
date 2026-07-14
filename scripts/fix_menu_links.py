import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

REQUIRED = {
    "about": "About Us",
    "contact": "Contact Us",
    "disclaimer": "Disclaimer",
    "privacy-policy": "Privacy Policy",
}

TARGETS = [
    "https://koreamedicaltour.com", "https://k-trip365.com", "https://k-visa365.com",
    "https://koreawedding365.com", "https://jobkoreaglobal.com",
    "https://koreacrypto365.com", "https://kskin365.com", "https://studyinkorea365.com",
    "https://kieca-korea.org", "https://koreanews365.com",
]

log = []

for site_url in TARGETS:
    site = next((s for s in SITES_CONFIG if s["url"] == site_url), None)
    if not site:
        continue
    pw = os.getenv(site["wp_pass_env"], "")
    base = site_url
    entry = {"site": base, "added": [], "errors": []}

    try:
        rl = requests.get(f"{base}/wp-json/wp/v2/menu-locations", auth=(WP_USER, pw), timeout=20)
        locs = rl.json() if rl.status_code == 200 else {}
        primary = locs.get("primary") or next(iter(locs.values()), None)
        menu_id = primary.get("menu") if primary else None
        if not menu_id:
            entry["errors"].append("no_primary_menu")
            log.append(entry)
            continue

        rp = requests.get(f"{base}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                           params={"per_page": 50, "_fields": "id,title,slug,link"}, timeout=25)
        pages = rp.json() if rp.status_code == 200 else []

        rmi = requests.get(f"{base}/wp-json/wp/v2/menu-items", auth=(WP_USER, pw),
                            params={"menus": menu_id, "per_page": 100}, timeout=25)
        existing = rmi.json() if rmi.status_code == 200 else []
        existing_urls = [it.get("url", "").rstrip("/") for it in existing]

        for slug, label in REQUIRED.items():
            page_match = [p for p in pages if p.get("slug", "").rstrip("/") == slug or
                          slug.replace("-", " ") in p["title"]["rendered"].strip().lower()]
            if not page_match:
                entry["errors"].append(f"{slug}:page_not_found")
                continue
            page_link = page_match[0]["link"].rstrip("/")
            if page_link in existing_urls:
                continue  # 이미 이 메뉴에 있음

            mi = requests.post(f"{base}/wp-json/wp/v2/menu-items", auth=(WP_USER, pw),
                                json={"title": label, "url": page_match[0]["link"],
                                      "menus": menu_id, "status": "publish"}, timeout=25)
            if mi.status_code in (200, 201):
                entry["added"].append(slug)
            else:
                entry["errors"].append(f"{slug}:{mi.status_code}:{mi.text[:100]}")
    except Exception as e:
        entry["errors"].append(str(e))

    log.append(entry)
    print(entry)

with open("fix_menu_result.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
