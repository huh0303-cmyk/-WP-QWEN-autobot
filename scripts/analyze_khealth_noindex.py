#!/usr/bin/env python3
import os, requests, re, json, base64

WP_USER = "huh0303@gmail.com"
SITE    = "https://k-health365.com"
pw      = os.getenv("KHEALTH365COM","")
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

if not pw: print("NO PW"); exit(1)

base = f"{SITE}/wp-json/wp/v2"
auth = (WP_USER, pw)

# 1. Rank Math 전체 설정에서 noindex 원인 파악
print("=== Rank Math 설정 확인 ===")
r = requests.get(f"{base}/settings", auth=auth, timeout=10)
if r.status_code == 200:
    settings = r.json()
    for k,v in settings.items():
        if any(x in k.lower() for x in ["noindex","robot","rank_math","blog_public"]):
            print(f"  {k}: {v}")

# 2. 실제 발행 글 중 noindex 있는 것 카운트
print("\n=== 글 noindex 상태 전수 확인 ===")
page = 1
total = noindex_count = index_count = 0
noindex_samples = []
while True:
    r = requests.get(f"{base}/posts", auth=auth,
                     params={"per_page":100,"page":page,"status":"publish",
                             "_fields":"id,slug,meta"}, timeout=30)
    if r.status_code != 200 or not r.json(): break
    posts = r.json()
    for p in posts:
        total += 1
        meta = p.get("meta",{}) or {}
        robots = meta.get("rank_math_robots",[])
        robots_str = str(robots).lower()
        if "noindex" in robots_str:
            noindex_count += 1
            if len(noindex_samples) < 5:
                noindex_samples.append({"id":p["id"],"slug":p["slug"],"robots":robots})
        else:
            index_count += 1
    if len(posts) < 100: break
    page += 1

print(f"총 {total}개 | index: {index_count} | noindex: {noindex_count}")
if noindex_samples:
    print("noindex 샘플:")
    for s in noindex_samples:
        print(f"  [{s['id']}] {s['slug'][:50]} | {s['robots']}")

# 3. 태그/카테고리 아카이브 페이지 확인 (이게 475개의 주요 원인일 가능성)
print("\n=== 태그/카테고리 수 확인 ===")
rt = requests.get(f"{base}/tags?per_page=1", auth=auth, timeout=10)
rc = requests.get(f"{base}/categories?per_page=1", auth=auth, timeout=10)
tag_total = int(rt.headers.get("X-WP-Total", 0)) if rt.status_code==200 else 0
cat_total = int(rc.headers.get("X-WP-Total", 0)) if rc.status_code==200 else 0
print(f"태그 수: {tag_total}개 → 태그 아카이브 페이지 {tag_total}개")
print(f"카테고리 수: {cat_total}개")
print(f"\n⚠️  태그 {tag_total}개가 전부 색인되면 thin content 대량 발생")
print(f"    Rank Math에서 태그 페이지 noindex 설정 필요")

# 결과 저장
result = {
    "total_posts": total,
    "index_posts": index_count,
    "noindex_posts": noindex_count,
    "tag_count": tag_total,
    "cat_count": cat_total,
    "noindex_samples": noindex_samples
}
if GH_TOKEN:
    content = base64.b64encode(json.dumps(result,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "khealth_noindex_analysis.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",headers=gh_h,timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"analysis: khealth noindex 원인","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                 headers=gh_h,json=payload,timeout=15)
    print("\n결과 저장 완료")
