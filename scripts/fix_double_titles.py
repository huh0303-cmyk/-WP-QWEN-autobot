import os, sys, re, json, traceback, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import SITES_CONFIG, WP_USER, build_diverse_title

log = []
try:
    site = next(s for s in SITES_CONFIG if s["url"] == "https://jobkoreaglobal.com")
    pw = os.getenv(site["wp_pass_env"], "")

    r = requests.get(f"{site['url']}/wp-json/wp/v2/posts", auth=(WP_USER, pw),
                      params={"per_page": 47, "status": "publish", "_fields": "id,title"}, timeout=30)
    posts = r.json()

    fixed = 0
    for p in posts:
        title = p["title"]["rendered"]
        if len(title) > 90:
            core = title
            for junk in ["3 Mistakes People Make With ", "A Practical Look at ", "The Real Cost of ",
                         "Cross-Border Trade Korea Careers: ", "The Truth About ", "Behind the Scenes: What ",
                         "How to Actually Handle ", "WTO Korea Representative: "]:
                core = core.replace(junk, "")
            for junk in [" for International Patients", " — What to Expect", " That Most People Get Wrong",
                         " Actually Involves", ": A Specialist&#8217;s Guide", " Warning Signs You Should Never Ignore",
                         " 101: What First-Timers Should Know"]:
                core = core.replace(junk, "")
            core = re.sub(r'^(Are You |Is |Don\'t |Stop )', '', core)
            core = re.split(r'[?:]', core)[0].strip()
            core = re.sub(r'\(.*?\)', '', core).strip()
            if len(core) > 60:
                core = core[:60].rsplit(' ', 1)[0]

            new_title = build_diverse_title(core, "en", site_url=site["url"])
            rr = requests.patch(f"{site['url']}/wp-json/wp/v2/posts/{p['id']}", auth=(WP_USER, pw),
                                 json={"title": new_title}, timeout=20)
            log.append({"id": p["id"], "old": title, "keyword": core, "new": new_title, "status": rr.status_code})
            fixed += 1

    log.append({"summary": f"총 {fixed}개 수정"})
except Exception as e:
    log.append({"fatal_error": str(e), "traceback": traceback.format_exc()})

with open("fix_double_result.json", "w", encoding="utf-8") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print(json.dumps(log, ensure_ascii=False, indent=2))
