import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

out = []
for site_url in ["https://jobkoreaglobal.com", "https://koreamedicaltour.com", "https://kworld365.com"]:
    site = next(s for s in SITES_CONFIG if s["url"] == site_url)
    pw = os.getenv(site["wp_pass_env"], "")
    r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                      params={"per_page": 5, "orderby": "date", "order": "desc",
                              "status": "publish", "_fields": "id,title,content,date"}, timeout=25)
    for p in r.json():
        content = p.get("content", {}).get("rendered", "")
        img_count = len(re.findall(r'<img[\s>]', content, re.IGNORECASE))
        img_srcs = re.findall(r'<img[^>]+src="([^"]+)"', content, re.IGNORECASE)
        out.append({
            "site": site_url, "id": p["id"], "date": p.get("date"),
            "title": p["title"]["rendered"][:40], "img_count": img_count,
            "img_srcs_sample": img_srcs[:2]
        })

with open("img_check_result.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False, indent=2))
