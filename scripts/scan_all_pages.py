import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

REQUIRED = ["about", "contact", "disclaimer", "privacy-policy"]
MIN_LEN = 600

results = []
for site in SITES_CONFIG:
    site_url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        results.append({"site": site_url, "error": "no_password"})
        continue

    site_result = {"site": site_url, "pages": {}}
    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/pages", auth=(WP_USER, pw),
                          params={"per_page": 100, "_fields": "id,title,link,content,slug,status"}, timeout=30)
        pages = r.json() if r.status_code == 200 else []
    except Exception as e:
        results.append({"site": site_url, "error": str(e)})
        continue

    for slug in REQUIRED:
        matches = [p for p in pages if p.get("slug", "").rstrip("/") == slug or
                   p["title"]["rendered"].strip().lower().replace(" ", "-") == slug]
        if not matches:
            title_key = slug.replace("-", " ")
            matches = [p for p in pages if title_key in p["title"]["rendered"].strip().lower()]

        if not matches:
            site_result["pages"][slug] = {"exists": False}
            continue

        p = matches[0]
        content = p.get("content", {}).get("rendered", "")
        plain = re.sub(r'<[^>]+>', ' ', content)
        plain = re.sub(r'\s+', ' ', plain).strip()
        site_result["pages"][slug] = {
            "exists": True, "id": p["id"], "link": p.get("link"),
            "text_len": len(plain),
            "too_short": len(plain) < MIN_LEN,
            "has_lorem": "lorem ipsum" in content.lower(),
            "has_correct_email": "huh0303@gmail.com" in content,
        }

    results.append(site_result)

with open("all_pages_scan3.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

for r in results:
    if "error" in r:
        print(r["site"], "ERROR:", r["error"]); continue
    issues = []
    for slug, info in r["pages"].items():
        if not info.get("exists"):
            issues.append(f"{slug}:없음")
        else:
            if info["too_short"]: issues.append(f"{slug}:짧음({info['text_len']}자)")
            if info["has_lorem"]: issues.append(f"{slug}:LOREM")
            if not info["has_correct_email"]: issues.append(f"{slug}:이메일없음")
    print(r["site"], "|", (", ".join(issues) if issues else "정상"))
