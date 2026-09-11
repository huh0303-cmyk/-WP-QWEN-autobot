#!/usr/bin/env python3
"""
k-health365.com 색인 1개 원인 완전 재진단
- 실제 HTML에서 noindex 확인
- 실제 robots.txt 내용
- 실제 sitemap 내용
- WP REST로 글 메타 실제 확인
- 모든 결과를 파일로 저장
"""
import os, requests, re, json, base64, time

WP_USER  = "huh0303@gmail.com"
SITE     = "https://k-health365.com"
pw       = os.getenv("KHEALTH365COM","")
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

if not pw: print("NO PW"); exit(1)
base = f"{SITE}/wp-json/wp/v2"
auth = (WP_USER, pw)

result = {}
issues = []

print("="*60)
print("k-health365.com 색인 원인 완전 재진단")
print("="*60)

# 1. robots.txt
print("\n[1] robots.txt")
r = requests.get(f"{SITE}/robots.txt", timeout=10)
result["robots_txt_status"] = r.status_code
result["robots_txt"] = r.text
print(f"  HTTP {r.status_code}")
print(f"  내용:\n{r.text}")
if "Disallow: /" in r.text and "Disallow: /wp-admin" not in r.text:
    issues.append("🔴 robots.txt 전체 차단!")
elif "noindex" in r.text.lower():
    issues.append("🔴 robots.txt에 noindex!")

# 2. 홈페이지 HTML
print("\n[2] 홈페이지 HTML 분석")
r2 = requests.get(SITE, timeout=15,
                  headers={"User-Agent":"Mozilla/5.0 (compatible; Googlebot/2.1)"},
                  allow_redirects=True)
result["home_status"] = r2.status_code
result["home_url"]    = r2.url
html = r2.text
print(f"  HTTP {r2.status_code} | URL: {r2.url}")
print(f"  X-Robots-Tag: {r2.headers.get('X-Robots-Tag','없음')}")

# meta robots 추출
all_meta = re.findall(r'<meta[^>]+>', html, re.IGNORECASE)
for m in all_meta:
    if 'robot' in m.lower() or 'noindex' in m.lower():
        print(f"  meta: {m}")
        if 'noindex' in m.lower():
            issues.append(f"🔴 홈페이지 noindex 태그: {m}")

# canonical
canonical = re.findall(r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE)
print(f"  canonical: {canonical}")
result["home_canonical"] = canonical

# head 전체에서 noindex 검색
if 'noindex' in html[:5000].lower():
    head_noindex = re.findall(r'.{0,50}noindex.{0,50}', html[:5000], re.IGNORECASE)
    print(f"  ⚠️ head에 noindex 발견: {head_noindex[:3]}")
    issues.append(f"🔴 홈 head에 noindex: {head_noindex[0] if head_noindex else ''}")
else:
    print(f"  ✅ head에 noindex 없음")

# 3. 실제 글 5개 URL 직접 확인
print("\n[3] 실제 글 URL 직접 확인")
r3 = requests.get(f"{base}/posts", auth=auth,
                  params={"per_page":5,"status":"publish","_fields":"id,slug,link,meta"},
                  timeout=15)
noindex_posts = []
if r3.status_code == 200:
    for p in r3.json():
        link = p.get("link","")
        pid  = p.get("id")
        meta = p.get("meta",{}) or {}
        rm_robots = meta.get("rank_math_robots",[])
        
        # 실제 URL 접근해서 HTML 확인
        try:
            rp = requests.get(link, timeout=10,
                             headers={"User-Agent":"Googlebot/2.1"})
            ph = rp.text[:3000]
            
            # robots meta 확인
            post_robots = re.findall(
                r'<meta[^>]*name=["\']robots["\'][^>]*content=["\']([^"\']+)["\']',
                ph, re.IGNORECASE
            )
            xrobots = rp.headers.get("X-Robots-Tag","없음")
            has_noindex = any("noindex" in v.lower() for v in post_robots)
            has_noindex_x = "noindex" in xrobots.lower()
            
            icon = "🔴" if (has_noindex or has_noindex_x) else "✅"
            print(f"  {icon} [{pid}] {link[:50]}")
            print(f"       HTML robots={post_robots} | X-Robots={xrobots} | DB robots={rm_robots}")
            
            if has_noindex or has_noindex_x:
                noindex_posts.append({"id":pid,"url":link,"robots":post_robots,"x_robots":xrobots})
                issues.append(f"🔴 글 [{pid}] noindex: {post_robots}")
        except Exception as e:
            print(f"  ⚠️ [{pid}] {e}")

result["noindex_posts_found"] = noindex_posts

# 4. WP 설정 전체 확인
print("\n[4] WP 설정 전체 확인")
r4 = requests.get(f"{base}/settings", auth=auth, timeout=10)
settings = r4.json() if r4.status_code==200 else {}
bp = settings.get("blog_public")
print(f"  blog_public: {bp!r}")
if bp is False or bp == 0:
    issues.append("🔴🔴🔴 blog_public=False — 검색엔진 완전 차단!")
result["blog_public"] = bp
result["wp_settings_keys"] = list(settings.keys())[:20]

# 5. Rank Math 전체 설정
print("\n[5] Rank Math 설정")
try:
    r5 = requests.get(f"{SITE}/wp-json/rankmath/v1/settings", auth=auth, timeout=10)
    if r5.status_code == 200:
        rm = r5.json()
        titles = rm.get("titles",{})
        post_robots = titles.get("post",{}).get("robots",[])
        tag_robots  = titles.get("post_tag",{}).get("robots",[])
        home_robots = rm.get("general",{}).get("robots",[]) if "general" in rm else []
        
        print(f"  글(post) robots: {post_robots}")
        print(f"  태그 robots:     {tag_robots}")
        print(f"  홈 robots:       {home_robots}")
        
        if "noindex" in str(post_robots).lower():
            issues.append(f"🔴🔴🔴 Rank Math post 전체에 noindex 설정됨!")
        if "noindex" not in str(tag_robots).lower():
            issues.append("⚠️ Rank Math 태그 noindex 미설정")
            
        result["rm_post_robots"] = post_robots
        result["rm_tag_robots"]  = tag_robots
    else:
        print(f"  Rank Math REST: HTTP {r5.status_code}")
except Exception as e:
    print(f"  ⚠️ {e}")

# 6. 전체 글 noindex 전수 재확인
print("\n[6] 전체 글 noindex DB값 전수 확인")
page = 1; total = 0; noindex_db = 0; no_focus = 0; no_desc = 0
while True:
    r6 = requests.get(f"{base}/posts", auth=auth,
                      params={"per_page":100,"page":page,"status":"publish",
                              "_fields":"id,meta"}, timeout=30)
    if r6.status_code != 200 or not r6.json(): break
    posts = r6.json()
    for p in posts:
        total += 1
        meta = p.get("meta",{}) or {}
        robots = str(meta.get("rank_math_robots",[])).lower()
        if "noindex" in robots: noindex_db += 1
        if not meta.get("rank_math_focus_keyword"): no_focus += 1
        if not meta.get("rank_math_description"):   no_desc += 1
    if len(posts) < 100: break
    page += 1

print(f"  총 {total}개 | noindex(DB): {noindex_db} | focus없음: {no_focus} | desc없음: {no_desc}")
result.update({"total_posts":total,"noindex_db":noindex_db,"no_focus":no_focus,"no_desc":no_desc})

if no_focus > total * 0.5:
    issues.append(f"🔴 focus keyword 없는 글 {no_focus}/{total}개 ({no_focus*100//total}%)")
if no_desc > total * 0.5:
    issues.append(f"🔴 meta desc 없는 글 {no_desc}/{total}개 ({no_desc*100//total}%)")

# 7. 최종 진단
print(f"\n{'='*60}")
print(f"진단 결과 — 색인 1개 원인")
print(f"{'='*60}")
if issues:
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
else:
    print(f"  ✅ 기술적 문제 없음 → 구글 재크롤링 대기 or 콘텐츠 품질")

result["issues"] = issues
result["issue_count"] = len(issues)

# GitHub 저장
if GH_TOKEN:
    content = base64.b64encode(json.dumps(result,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "khealth_final_diagnosis.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                     headers=gh_h, timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"diagnosis: khealth 최종 재진단","content":content}
    if sha: payload["sha"] = sha
    r7 = requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                     headers=gh_h, json=payload, timeout=15)
    print(f"\n결과 저장: {'✅' if 'content' in r7.json() else '❌'}")
