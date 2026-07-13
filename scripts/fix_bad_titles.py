import os, sys, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, build_diverse_title

site = next(s for s in SITES_CONFIG if s["url"] == "https://jobinkorea365.com")
pw = os.getenv(site["wp_pass_env"], "")

fixes = {
    250: "Caregiver Certification: Your Ticket to In-Demand Jobs",
    247: "High-Demand, High-Paying Jobs Abroad for International Talent",
}

for pid, clean_title in fixes.items():
    new_title = build_diverse_title(clean_title.split(":")[0].split(",")[0], "en", site_url=site["url"])
    r = requests.patch(f"{site['url']}/wp-json/wp/v2/posts/{pid}", auth=(WP_USER, pw),
                        json={"title": new_title}, timeout=20)
    print(pid, "->", new_title, "| status:", r.status_code)
