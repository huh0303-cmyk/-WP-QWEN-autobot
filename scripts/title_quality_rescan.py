import os, sys, re, json, requests
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER

BROKEN_PATTERNS = [
    r'^\s*◇', r'^\s*by\s+[a-z]+\s+[a-z]+\s*$', r'\bin\s*\?$', r'\bfor\s*\?$',
    r'^sure,', r'^certainly!', r'^\s*기자\s*$',
]


def check_site(site):
    site_url = site["url"]
    pw = os.getenv(site["wp_pass_env"], "")
    if not pw:
        return {"site": site_url, "error": "no_password"}

    try:
        r = requests.get(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                          params={"per_page": 30, "status": "publish", "orderby": "date",
                                  "order": "desc", "_fields": "id,title,date"}, timeout=35)
    except Exception as e:
        return {"site": site_url, "error": str(e)}
    if r.status_code != 200:
        return {"site": site_url, "error": f"status_{r.status_code}"}

    posts = r.json()
    broken = []
    titles = []
    for p in posts:
        title = p["title"]["rendered"].strip()
        titles.append(title)
        for pat in BROKEN_PATTERNS:
            if re.search(pat, title, re.IGNORECASE):
                broken.append({"id": p["id"], "title": title, "date": p.get("date")})
                break

    starts = Counter(" ".join(t.split()[:2]).lower() for t in titles)
    repeated_starts = {k: v for k, v in starts.items() if v >= 4}

    return {"site": site_url, "broken_titles": broken, "repeated_starts": repeated_starts,
            "sample_titles": titles[:10]}


if __name__ == "__main__":
    results = [check_site(s) for s in SITES_CONFIG]
    with open("title_quality_rescan.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    for r in results:
        err = r.get("error", "")
        b = r.get("broken_titles", [])
        rep = r.get("repeated_starts", {})
        flag = "⚠️" if b or rep or err else "✅"
        print(f"{flag} {r['site']:32s} 깨진제목:{len(b)} 반복시작:{rep} {err[:30]}")
