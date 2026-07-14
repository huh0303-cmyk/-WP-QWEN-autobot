import os, sys, re, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

AI_CLICHE_PATTERNS = [
    r"in today'?s fast-paced world", r"in the ever-evolving", r"navigating the (complex|dynamic)",
    r"whether you'?re a .* or a", r"it'?s no secret that", r"in conclusion,",
    r"as an ai", r"i don'?t have (personal|access)", r"i cannot provide",
    r"certainly!\s*here is", r"sure,\s*here is", r"^\s*◇\s*by\s",
    r"현대 사회에서", r"빠르게 변화하는 시대", r"결론적으로 말씀드리면", r"저는 ai로서",
]
BROKEN_TITLE_PATTERNS = [
    r"\bin\s*\?$", r"\bfor\s*\?$", r"\bin$", r"\bfor\s*and\s*beyond$",
    r"^\s*◇", r"^sure,", r"^certainly!",
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
                                      "_fields": "id,title,content,link,date"}, timeout=35)
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

    broken_titles = []
    cliche_hits = []
    for p in posts:
        title = p["title"]["rendered"]
        content = p.get("content", {}).get("rendered", "")
        plain = re.sub(r'<[^>]+>', ' ', content).lower()

        for pat in BROKEN_TITLE_PATTERNS:
            if re.search(pat, title.strip(), re.IGNORECASE):
                broken_titles.append({"id": p["id"], "title": title, "link": p.get("link")})
                break

        for pat in AI_CLICHE_PATTERNS:
            if re.search(pat, plain, re.IGNORECASE):
                cliche_hits.append({"id": p["id"], "title": title[:50], "pattern": pat})
                break

    return {
        "site": site_url,
        "total_posts": len(posts),
        "broken_title_count": len(broken_titles),
        "broken_titles": broken_titles,
        "cliche_count": len(cliche_hits),
        "cliche_hits": cliche_hits[:20],
    }


if __name__ == "__main__":
    results = [scan_site(s) for s in SITES_CONFIG]
    with open("full_audit_scan.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    tot_posts = 0
    for r in results:
        err = r.get("error", "")
        tp = r.get("total_posts", 0)
        tot_posts += tp
        print(f"{r['site']:32s} 글수{tp:>4d} 깨진제목{r.get('broken_title_count',0):>3d} AI티{r.get('cliche_count',0):>3d} {err[:30]}")
    print(f"\n전체 총 글 수: {tot_posts}")
