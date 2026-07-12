#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diagnose_khealth_index.py
k-health365.com 색인 1개 원인 정밀 진단
"""
import os, requests, re, json, base64, time, sys

WP_USER  = "huh0303@gmail.com"
SITE     = "https://k-health365.com"
pw       = os.getenv("KHEALTH365COM","")
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

if not pw: print("NO PW"); exit(1)
base = f"{SITE}/wp-json/wp/v2"
auth = (WP_USER, pw)

result = {}

print("="*60)
print("k-health365.com 색인 1개 원인 정밀 진단")
print("="*60)
sys.stdout.flush()

# ── 1. blog_public 확인 ──────────────────────────────────
print("\n[1] blog_public (검색엔진 노출 설정)")
r = requests.get(f"{base}/settings", auth=auth, timeout=10)
if r.status_code == 200:
    s = r.json()
    bp = s.get("blog_public")
    result["blog_public"] = bp
    print(f"  blog_public = {bp}")
    if bp is False or bp == 0:
        print(f"  🔴 치명적! 검색엔진 차단 상태 → 즉시 수정")
        # 즉시 수정
        r2 = requests.post(f"{base}/settings", auth=auth,
                           json={"blog_public": True}, timeout=10)
        print(f"  수정 결과: HTTP {r2.status_code}")
    else:
        print(f"  ✅ 정상")
sys.stdout.flush()

# ── 2. robots.txt 확인 ───────────────────────────────────
print("\n[2] robots.txt 확인")
try:
    r = requests.get(f"{SITE}/robots.txt", timeout=10,
                     headers={"User-Agent":"Googlebot/2.1"})
    result["robots_txt_status"] = r.status_code
    result["robots_txt"] = r.text[:500]
    print(f"  HTTP {r.status_code}")
    print(f"  내용:\n{r.text[:300]}")
    if "Disallow: /" in r.text and "User-agent: *" in r.text:
        print(f"  🔴 치명적! robots.txt가 전체 차단 중!")
    elif "Disallow: /wp-admin" in r.text:
        print(f"  ✅ 정상 (wp-admin만 차단)")
except Exception as e:
    print(f"  오류: {e}")
sys.stdout.flush()

# ── 3. 홈페이지 canonical 확인 ───────────────────────────
print("\n[3] 홈페이지 canonical/noindex 확인")
try:
    r = requests.get(SITE, timeout=10,
                     headers={"User-Agent":"Googlebot/2.1"})
    result["homepage_status"] = r.status_code
    html = r.text[:5000]

    # noindex 확인
    noindex_match = re.findall(r'<meta[^>]*noindex[^>]*>', html, re.IGNORECASE)
    canonical_match = re.findall(r'<link[^>]*canonical[^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE)

    result["homepage_noindex"] = bool(noindex_match)
    result["homepage_canonical"] = canonical_match

    print(f"  HTTP {r.status_code}")
    if noindex_match:
        print(f"  🔴 홈페이지에 noindex 태그 발견: {noindex_match}")
    else:
        print(f"  ✅ noindex 없음")

    if canonical_match:
        print(f"  canonical: {canonical_match[0]}")
    else:
        print(f"  ⚠️ canonical 없음")

    # X-Robots-Tag 헤더 확인
    xrobots = r.headers.get("X-Robots-Tag","없음")
    result["x_robots_tag"] = xrobots
    print(f"  X-Robots-Tag: {xrobots}")
    if "noindex" in xrobots.lower():
        print(f"  🔴 X-Robots-Tag에 noindex!")

except Exception as e:
    print(f"  오류: {e}")
sys.stdout.flush()

# ── 4. 최근 글 10개 noindex/canonical 확인 ───────────────
print("\n[4] 최근 발행 글 10개 메타 확인")
r = requests.get(f"{base}/posts", auth=auth,
                 params={"per_page":10,"status":"publish",
                         "_fields":"id,slug,link,meta"},
                 timeout=15)
post_issues = []
if r.status_code == 200:
    posts = r.json()
    for p in posts:
        pid   = p.get("id")
        slug  = p.get("slug","")
        link  = p.get("link","")
        meta  = p.get("meta",{}) or {}

        rm_robots   = meta.get("rank_math_robots",[])
        rm_meta     = meta.get("rank_math_seo_score","")
        rm_focus    = meta.get("rank_math_focus_keyword","")
        rm_desc     = meta.get("rank_math_description","")

        has_noindex = "noindex" in str(rm_robots).lower()
        has_focus   = bool(rm_focus)
        has_desc    = bool(rm_desc)

        status_icon = "🔴" if has_noindex else "✅"
        print(f"  {status_icon} [{pid}] {slug[:35]:35s} | robots={rm_robots} | focus={'✅' if has_focus else '❌'} | desc={'✅' if has_desc else '❌'}")

        if has_noindex:
            post_issues.append({"id":pid,"slug":slug,"robots":rm_robots})

result["post_noindex_count"] = len(post_issues)
result["post_issues"] = post_issues
sys.stdout.flush()

# ── 5. 전체 글 noindex 재확인 ────────────────────────────
print("\n[5] 전체 글 noindex 전수 재확인")
page = 1
total = noindex = index = no_focus = no_desc = 0
while True:
    r = requests.get(f"{base}/posts", auth=auth,
                     params={"per_page":100,"page":page,"status":"publish",
                             "_fields":"id,meta"}, timeout=30)
    if r.status_code != 200 or not r.json(): break
    posts = r.json()
    for p in posts:
        total += 1
        meta = p.get("meta",{}) or {}
        robots = str(meta.get("rank_math_robots",[])).lower()
        if "noindex" in robots: noindex += 1
        else: index += 1
        if not meta.get("rank_math_focus_keyword"): no_focus += 1
        if not meta.get("rank_math_description"):   no_desc  += 1
    if len(posts) < 100: break
    page += 1

print(f"  총 {total}개 | index:{index} | noindex:{noindex}")
print(f"  focus keyword 없음: {no_focus}개")
print(f"  meta description 없음: {no_desc}개")
result.update({"total":total,"index":index,"noindex":noindex,
               "no_focus":no_focus,"no_desc":no_desc})

if no_focus > total * 0.5:
    print(f"  ⚠️ 절반 이상 focus keyword 없음 → Rank Math 메타 미적용 문제")
sys.stdout.flush()

# ── 6. Rank Math 설정 확인 ───────────────────────────────
print("\n[6] Rank Math 설정 확인")
try:
    r = requests.get(f"{SITE}/wp-json/rankmath/v1/settings",
                     auth=auth, timeout=10)
    print(f"  Rank Math REST API: HTTP {r.status_code}")
    if r.status_code == 200:
        rm = r.json()
        titles = rm.get("titles",{})
        # 태그 설정
        tag_robots = titles.get("post_tag",{}).get("robots",[])
        post_robots = titles.get("post",{}).get("robots",[])
        print(f"  태그 아카이브 robots: {tag_robots}")
        print(f"  글(post) robots: {post_robots}")
        result["rm_tag_robots"]  = tag_robots
        result["rm_post_robots"] = post_robots

        if "noindex" in str(post_robots).lower():
            print(f"  🔴 글 자체에 noindex 설정됨! → 즉시 수정 필요")
        if "noindex" not in str(tag_robots).lower():
            print(f"  ⚠️ 태그 noindex 미설정 → 태그 아카이브가 색인됨")
except Exception as e:
    print(f"  Rank Math API 없음: {e}")
sys.stdout.flush()

# ── 7. 사이트맵 내용 확인 ────────────────────────────────
print("\n[7] 사이트맵 확인")
for sm_url in [f"{SITE}/sitemap_index.xml", f"{SITE}/post-sitemap.xml"]:
    try:
        r = requests.get(sm_url, auth=auth, timeout=10)
        print(f"  {sm_url.split('/')[-1]}: HTTP {r.status_code} / {len(r.text)}bytes")
        if r.status_code == 200:
            # URL 수 카운트
            url_count = r.text.count("<url>") + r.text.count("<sitemap>")
            print(f"    URL/sitemap 수: {url_count}개")
    except Exception as e:
        print(f"  오류: {e}")

# ── 8. 핵심 진단 요약 ────────────────────────────────────
print("\n" + "="*60)
print("진단 요약")
print("="*60)
issues = []

if result.get("blog_public") is False:
    issues.append("🔴 [치명] blog_public=False → 검색엔진 전체 차단")
if result.get("homepage_noindex"):
    issues.append("🔴 [치명] 홈페이지 noindex 태그")
if "noindex" in str(result.get("x_robots_tag","")).lower():
    issues.append("🔴 [치명] X-Robots-Tag noindex")
if result.get("noindex",0) > 0:
    issues.append(f"🔴 글 {result['noindex']}개 noindex")
if result.get("no_focus",0) > result.get("total",1) * 0.3:
    issues.append(f"⚠️ focus keyword 없는 글 {result.get('no_focus')}개 ({result.get('no_focus',0)*100//max(result.get('total',1),1)}%)")
if result.get("no_desc",0) > result.get("total",1) * 0.3:
    issues.append(f"⚠️ meta description 없는 글 {result.get('no_desc')}개")

if issues:
    for issue in issues:
        print(f"  {issue}")
else:
    print("  글 자체 문제 없음 → 크롤링 품질/속도 문제 또는 구글 재크롤링 대기 중")

# GitHub 저장
if GH_TOKEN:
    content = base64.b64encode(json.dumps(result,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "khealth_diagnosis.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                      headers=gh_h, timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"diagnosis: khealth 색인1개 원인","content":content}
    if sha: payload["sha"] = sha
    r2 = requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                      headers=gh_h, json=payload, timeout=15)
    print(f"\n결과 저장: {'✅' if 'content' in r2.json() else '❌'}")
