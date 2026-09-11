#!/usr/bin/env python3
"""
nuke_all_tags.py
k-health365.com 태그 완전 삭제
- 글에서 태그 연결 해제
- 태그 자체 삭제
- Rank Math 태그 noindex 설정
"""
import os, requests, time, sys, json, base64

WP_USER  = "huh0303@gmail.com"
SITE     = "https://k-health365.com"
pw       = os.getenv("KHEALTH365COM","")
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

if not pw: print("NO PW"); exit(1)
base = f"{SITE}/wp-json/wp/v2"
auth = (WP_USER, pw)

print("="*55)
print("k-health365.com 태그 완전 삭제")
print("="*55)
sys.stdout.flush()

# ── 1. 전체 글에서 태그 연결 해제 ────────────────────────
print("\n[1] 전체 글 태그 연결 해제")
page = 1; posts_cleared = 0
while True:
    try:
        r = requests.get(f"{base}/posts", auth=auth,
                        params={"per_page":50,"page":page,"status":"publish",
                                "_fields":"id,tags"}, timeout=20)
        if r.status_code != 200 or not r.json(): break
        posts = r.json()
    except: break

    for p in posts:
        if p.get("tags"):
            try:
                requests.post(f"{base}/posts/{p['id']}", auth=auth,
                             json={"tags":[]}, timeout=10)
                posts_cleared += 1
            except: pass
            time.sleep(0.1)

    if posts_cleared % 50 == 0 and posts_cleared > 0:
        print(f"  태그 해제: {posts_cleared}개 글...")
        sys.stdout.flush()
    if len(posts) < 50: break
    page += 1
    time.sleep(0.3)

print(f"  ✅ {posts_cleared}개 글 태그 해제 완료")
sys.stdout.flush()

# ── 2. 태그 전체 삭제 ────────────────────────────────────
print("\n[2] 태그 전체 삭제")
tag_deleted = 0
page = 1
while True:
    try:
        r = requests.get(f"{base}/tags", auth=auth,
                        params={"per_page":100,"page":page,
                                "_fields":"id,name,count"}, timeout=20)
        if r.status_code != 200 or not r.json(): break
        tags = r.json()
    except: break

    for tag in tags:
        try:
            rd = requests.delete(f"{base}/tags/{tag['id']}",
                                auth=auth, params={"force":"true"}, timeout=10)
            if rd.status_code in (200,201,204): tag_deleted += 1
        except: pass
        time.sleep(0.05)

    if tag_deleted % 500 == 0 and tag_deleted > 0:
        print(f"  삭제 중: {tag_deleted}개...")
        sys.stdout.flush()
    if len(tags) < 100: break
    page += 1
    time.sleep(0.2)

print(f"  ✅ 태그 {tag_deleted}개 삭제 완료")
sys.stdout.flush()

# ── 3. 남은 태그 수 확인 ─────────────────────────────────
r = requests.get(f"{base}/tags?per_page=1", auth=auth, timeout=10)
remaining = int(r.headers.get("X-WP-Total",0)) if r.status_code==200 else 0
print(f"\n  남은 태그: {remaining}개")

# ── 4. Rank Math 태그/작성자/날짜 noindex ─────────────────
print("\n[3] Rank Math 태그 noindex 강제 설정")
try:
    r = requests.get(f"{SITE}/wp-json/rankmath/v1/settings", auth=auth, timeout=10)
    if r.status_code == 200:
        s = r.json()
        titles = s.get("titles",{})
        for key in ["post_tag","author","date","search"]:
            if key not in titles: titles[key] = {}
            titles[key]["robots"]   = ["noindex","follow"]
            titles[key]["sitemap"]  = 0
        r2 = requests.post(f"{SITE}/wp-json/rankmath/v1/settings",
                          auth=auth, json={"titles":titles}, timeout=15)
        print(f"  Rank Math: HTTP {r2.status_code} {'✅' if r2.status_code==200 else '⚠️'}")
    else:
        print(f"  Rank Math REST 없음 ({r.status_code})")
except Exception as e:
    print(f"  ⚠️ {e}")

# ── 5. 퍼머링크 재저장 ───────────────────────────────────
print("\n[4] 퍼머링크 재저장")
for _ in range(3):
    requests.post(f"{base}/settings", auth=auth,
                 json={"permalink_structure":"/%postname%/"}, timeout=10)
    time.sleep(1)
print("  ✅ 완료")

# 결과 저장
result = {"posts_cleared":posts_cleared,"tags_deleted":tag_deleted,"remaining":remaining}
if GH_TOKEN:
    content = base64.b64encode(json.dumps(result,ensure_ascii=False).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "nuke_tags_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                     headers=gh_h,timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: 태그 완전삭제","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                headers=gh_h,json=payload,timeout=15)

print(f"\n{'='*55}")
print(f"✅ 태그 완전 삭제 완료")
print(f"   글 태그 해제:  {posts_cleared}개")
print(f"   태그 삭제:     {tag_deleted}개")
print(f"   남은 태그:     {remaining}개")
print(f"{'='*55}")
