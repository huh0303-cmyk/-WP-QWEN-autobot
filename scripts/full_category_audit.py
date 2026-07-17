import os, sys, json, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, pick_best_category


def check_site(site):
    site_url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": site_url, "error": "no_password"}

    try:
        rc = requests.get(f"{site_url}/wp-json/wp/v2/categories", auth=(WP_USER, pw),
                           params={"per_page": 100}, timeout=20)
        cat_map = {c["id"]: c["name"] for c in rc.json()} if rc.status_code == 200 else {}

        r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                          params={"per_page": 20, "orderby": "date", "order": "desc",
                                  "_fields": "id,title,categories,meta"}, timeout=35)
    except Exception as e:
        return {"site": site_url, "error": str(e)}
    if r.status_code != 200:
        return {"site": site_url, "error": f"status_{r.status_code}"}

    posts = r.json()
    mismatches = []
    dist = {}
    for p in posts:
        title = p["title"]["rendered"]
        meta_obj = p.get("meta", {}) or {}
        kw = meta_obj.get("rank_math_focus_keyword", "") or title
        recommended = pick_best_category(site_url, pw, kw.split(",")[0].strip(), title)
        assigned = p.get("categories", [])
        assigned_names = [cat_map.get(c, f"?{c}") for c in assigned]
        for n in assigned_names:
            dist[n] = dist.get(n, 0) + 1
        if recommended not in assigned:
            mismatches.append({
                "id": p["id"], "title": title[:45],
                "assigned": assigned_names,
                "recommended": cat_map.get(recommended, f"?{recommended}")
            })

    return {"site": site_url, "total_checked": len(posts), "distribution": dist,
            "mismatch_count": len(mismatches), "mismatches": mismatches}


if __name__ == "__main__":
    results = [check_site(s) for s in SITES_CONFIG]
    with open("full_category_audit.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    for r in results:
        err = r.get("error", "")
        mc = r.get("mismatch_count", 0)
        flag = "⚠️" if mc or err else "✅"
        print(f"{flag} {r['site']:32s} 불일치:{mc}/{r.get('total_checked',0)} {err[:30]}")
