#!/usr/bin/env python3
import os, requests, json, base64

WP_USER  = "huh0303@gmail.com"
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

SITES = [
    ("https://kworld365.com",   "KWORLD365COM"),
    ("https://kieca-korea.org", "KIECAKOREAORG"),
]

results = {}
for site_url, env_key in SITES:
    pw = os.getenv(env_key,"")
    info = {"pw_exists": bool(pw), "rest_status": 0, "post_count": 0, "publish_test": "", "error": ""}

    if not pw:
        info["error"] = "Secret없음"
        results[site_url] = info
        continue

    base = f"{site_url}/wp-json/wp/v2"
    auth = (WP_USER, pw)

    try:
        r = requests.get(f"{base}/posts?per_page=5&status=publish&_fields=id,title,date",
                         auth=auth, timeout=15)
        info["rest_status"] = r.status_code
        if r.status_code == 200:
            posts = r.json()
            info["post_count"] = len(posts)
            info["recent_posts"] = [
                {"id": p["id"], "title": p.get("title",{}).get("rendered","")[:50],
                 "date": p.get("date","")[:10]} for p in posts
            ]
    except Exception as e:
        info["error"] = str(e)[:100]

    try:
        r2 = requests.post(f"{base}/posts", auth=auth,
                           json={"title":"[TEST DELETE]","content":"test","status":"draft"},
                           timeout=15)
        info["publish_test"] = f"HTTP {r2.status_code}"
        if r2.status_code in (200,201):
            pid = r2.json().get("id")
            requests.delete(f"{base}/posts/{pid}", auth=auth,
                           params={"force":"true"}, timeout=10)
            info["publish_test"] += f" OK (id={pid} deleted)"
        else:
            info["publish_test"] += f" ERR: {r2.text[:100]}"
    except Exception as e:
        info["publish_test"] = str(e)[:100]

    results[site_url] = info

# GitHub에 결과 저장
if GH_TOKEN:
    content = base64.b64encode(json.dumps(results, ensure_ascii=False, indent=2).encode()).decode()
    gh_h = {"Authorization": f"token {GH_TOKEN}", "Content-Type": "application/json"}
    path = "debug_kworld_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}", headers=gh_h, timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"debug: kworld kieca 진단 결과","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                 headers=gh_h, json=payload, timeout=15)
    print("결과 저장 완료")

for site, info in results.items():
    print(f"\n{site}")
    for k,v in info.items():
        print(f"  {k}: {v}")
