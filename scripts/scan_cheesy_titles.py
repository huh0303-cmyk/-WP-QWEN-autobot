import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

CHEESY_PATTERNS = [
    r"^unlocking\b", r"^unlock your\b", r"^discover the\b", r"^discovering\b",
    r"^unveiling\b", r"^exploring the\b", r"^dive into\b", r"^the ultimate guide\b",
    r"^언락", r"^잠금해제",
]


def scan_site(site):
    site_url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": site_url, "error": "no_password"}

    posts, page = [], 1
    while True:
        try:
            r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                              params={"per_page": 50, "page": page, "status": "publish",
                                      "_fields": "id,title,meta"}, timeout=35)
        except Exception as e:
            return {"site": site_url, "error": str(e), "total_posts": len(posts)}
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 50:
            break
        page += 1

    cheesy = []
    for p in posts:
        title = p["title"]["rendered"].strip()
        for pat in CHEESY_PATTERNS:
            if re.search(pat, title, re.IGNORECASE):
                cheesy.append({"id": p["id"], "title": title})
                break

    return {"site": site_url, "total_posts": len(posts), "cheesy_count": len(cheesy), "cheesy_titles": cheesy}


if __name__ == "__main__":
    results = [scan_site(s) for s in SITES_CONFIG]
    with open("cheesy_title_scan.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    tot = 0
    for r in results:
        c = r.get("cheesy_count", 0)
        tot += c
        err = r.get("error", "")
        print(f"{r['site']:32s} 글수{r.get('total_posts',0):>4d} 구린제목{c:>3d} {err[:30]}")
    print(f"\n전체 구린제목 합계: {tot}")
