import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

CLICHE_TITLE_PATTERNS = [
    r'\bunlocking\b', r'\bunlock your\b', r'\bunveiling\b', r'\bdiscover the\b',
    r'\bthe ultimate guide\b', r'\bdive into\b', r'\beverything you need to know\b',
    r'\bmaster the art\b', r'\belevate your\b',
]

results = []
for site in SITES_CONFIG:
    site_url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        results.append({"site": site_url, "error": "no_password"})
        continue

    posts, page = [], 1
    fetch_error = None
    while True:
        try:
            r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                              params={"per_page": 50, "page": page, "status": "publish",
                                      "_fields": "id,title,link,meta"}, timeout=35)
        except Exception as e:
            fetch_error = str(e)
            break
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 50:
            break
        page += 1

    if fetch_error:
        results.append({"site": site_url, "error": fetch_error, "total_posts": len(posts)})
        continue

    hits = []
    for p in posts:
        title = p["title"]["rendered"]
        for pat in CLICHE_TITLE_PATTERNS:
            if re.search(pat, title, re.IGNORECASE):
                hits.append({"id": p["id"], "title": title, "pattern": pat})
                break
    results.append({"site": site_url, "total_posts": len(posts), "cliche_title_count": len(hits), "hits": hits})

with open("scan_cliche_titles.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

tot = 0
for r in results:
    err = r.get("error", "")
    c = r.get("cliche_title_count", 0)
    tot += c
    print(f"{r['site']:32s} 총글{r.get('total_posts',0):>4d} 클리셰제목{c:>3d} {err[:30]}")
print("\n전체 클리셰 제목:", tot)
