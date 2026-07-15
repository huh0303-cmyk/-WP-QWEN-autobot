import os, sys, json, re, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

SUSPICIOUS_PATTERNS = [
    "free shipping", "add to cart", "shop now", "sale ends", "% off",
    "lorem ipsum", "sample product", "demo content", "just another wordpress",
    "coming soon", "under construction", "hello world",
]


def check_site(site):
    site_url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": site_url, "error": "no_password"}

    result = {"site": site_url}
    try:
        r = requests.get(f"{site_url}/wp-json", timeout=20)
        if r.status_code == 200:
            d = r.json()
            result["site_name"] = d.get("name")
            result["site_description"] = d.get("description")
    except Exception as e:
        result["settings_error"] = str(e)

    try:
        rh = requests.get(site_url, timeout=25)
        html = rh.text
        result["home_status"] = rh.status_code
    except Exception as e:
        result["home_error"] = str(e)
        html = ""

    hits = []
    low = html.lower()
    for pat in SUSPICIOUS_PATTERNS:
        if pat in low:
            idx = low.find(pat)
            hits.append({"pattern": pat, "context": html[max(0, idx-100):idx+150]})
    result["suspicious_hits"] = hits

    name = (result.get("site_name") or "").lower()
    desc = (result.get("site_description") or "").lower()
    domain_root = site_url.replace("https://", "").split(".")[0].lower()
    result["title_looks_generic"] = (
        "just another" in desc or desc.strip() == "" or
        name in ("hello world", "") or
        (domain_root in desc and len(desc) < 25)
    )

    return result


if __name__ == "__main__":
    results = [check_site(s) for s in SITES_CONFIG]
    with open("theme_demo_scan.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    for r in results:
        err = r.get("home_error", r.get("error", ""))
        hits = r.get("suspicious_hits", [])
        flag = "⚠️" if hits or err else "✅"
        print(f"{flag} {r['site']:32s} 제목:'{r.get('site_name')}' / 태그:'{r.get('site_description')}' 의심:{len(hits)} {err[:30]}")
