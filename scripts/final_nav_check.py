import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

REQUIRED = ["about", "contact", "disclaimer", "privacy-policy"]


def check_site(site):
    site_url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": site_url, "error": "no_password"}

    try:
        r = requests.get(site_url, timeout=25)
        home_html = r.text.lower() if r.status_code == 200 else ""
    except Exception as e:
        return {"site": site_url, "error": str(e)}

    nav_missing = [slug for slug in REQUIRED if f'/{slug}/' not in home_html]
    return {"site": site_url, "nav_missing": nav_missing}


if __name__ == "__main__":
    results = [check_site(s) for s in SITES_CONFIG]
    with open("final_nav_check.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    for r in results:
        err = r.get("error", "")
        missing = r.get("nav_missing", [])
        mark = "✅" if not missing and not err else "⚠️"
        print(f"{r['site']:32s} {mark} 누락:{missing} {err[:30]}")
