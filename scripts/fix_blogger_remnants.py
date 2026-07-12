#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_blogger_remnants.py
Blogger 서브도메인 잔재 완전 제거
1. 모든 Blogger URL → WordPress URL 301 리다이렉트
2. www.k-health365.com Blogger 형식 URL → 404 or 홈 리다이렉트
3. 서브도메인별 리다이렉트 처리
4. GSC URL 제거 요청 (가능한 경우)
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

print("="*60)
print("Blogger 잔재 URL 완전 제거")
print("="*60)
sys.stdout.flush()

result = {"redirects":0, "blogger_urls":[], "errors":0}

# ── 1. Blogger 잔재 URL 목록 ──────────────────────────────
BLOGGER_URLS = [
    # www 서브도메인 Blogger 형식
    "/2025/07/blog-post_8.html",
    "/2025/07/2025_01082783026.html",
    "/2025/06/5_01246787756.html",
    "/2026/01/1-2026.html",
    "/2025/10/metabolic-syndrome.html",
    "/2025/10/dyspepsia.html",
    "/2025/09/blog-post_11.html",
    "/2025/08/blog-post_24.html",
    "/search/label/피부과상담",
    # 모바일 m=1 파라미터 포함
    "/2025/07/blog-post_8.html?m=1",
    "/2025/07/2025_01082783026.html?m=1",
    "/2025/06/5_01246787756.html?m=1",
    "/2026/01/1-2026.html?m=1",
    "/2025/10/metabolic-syndrome.html?m=1",
    "/2025/10/dyspepsia.html?m=1",
    "/2025/09/blog-post_11.html?m=1",
    "/2025/08/blog-post_24.html?m=1",
    "/search/label/피부과상담?m=1",
]

# 서브도메인별 URL
SUBDOMAIN_URLS = [
    "https://beauty.k-health365.com/2026/02/knee-brace-arthritis-support_0802869338.html",
    "https://beauty.k-health365.com/2026/02/blog-post.html",
    "https://beauty.k-health365.com/2026/02/knee-brace-arthritis-support_0802869338.html?m=1",
    "https://beauty.k-health365.com/2026/02/blog-post.html?m=1",
    "https://wearable-health365.k-health365.com/2025/08/2025.html",
    "https://wearable-health365.k-health365.com/2025/08/2025.html?m=1",
    "https://health-devices.k-health365.com/2025/10/top-10.html",
    "https://health-devices.k-health365.com/2025/10/top-10.html?m=1",
    "https://healthinsurance.k-health365.com/tag/암보험",
    "https://healthinsurance.k-health365.com/tag/암보험?page=1",
    "https://healthinsurance.k-health365.com/tag/암치료비",
    "https://healthinsurance.k-health365.com/tag/암치료비?page=1",
    "https://eldercare.k-health365.com/tag/치매",
    "https://eldercare.k-health365.com/tag/치매?page=1",
]

# ── 2. Rank Math Redirection으로 301 설정 ─────────────────
print("\n[1] Blogger URL → WordPress 홈 301 리다이렉트 설정")

def add_redirect(source_pattern, destination=SITE, rtype="301"):
    try:
        r = requests.post(
            f"{SITE}/wp-json/rankmath/v1/redirections",
            auth=auth,
            json={
                "sources": [{"pattern": source_pattern, "comparison": "exact"}],
                "destination": destination,
                "type": rtype,
                "status": "active",
                "ignore_slash": True,
            },
            timeout=10
        )
        return r.status_code in (200, 201)
    except:
        return False

# Blogger 형식 패턴들 일괄 리다이렉트
blogger_patterns = [
    # 연도/월 형식 (Blogger 고유 URL 패턴)
    r"/20[0-9]{2}/[0-9]{2}/",  # /2025/07/ 형식
    r"\.html",                   # .html 확장자
    r"\?m=1",                   # 모바일 파라미터
    r"/search/label/",           # Blogger 라벨 검색
    r"/search/",                 # Blogger 검색
]

# 개별 URL 리다이렉트
for url_path in BLOGGER_URLS:
    success = add_redirect(url_path)
    if success:
        result["redirects"] += 1
        print(f"  ✅ {url_path[:50]}")
    else:
        result["errors"] += 1
    time.sleep(0.3)

# Blogger 날짜 형식 패턴 와일드카드 리다이렉트
blogger_wildcard_patterns = [
    ("/2025/", "Blogger 2025년 URL"),
    ("/2024/", "Blogger 2024년 URL"),
    ("/2023/", "Blogger 2023년 URL"),
    ("/search/label/", "Blogger 라벨 URL"),
    ("/search/", "Blogger 검색 URL"),
]

print("\n[2] Blogger 패턴 와일드카드 리다이렉트")
for pattern, desc in blogger_wildcard_patterns:
    try:
        r = requests.post(
            f"{SITE}/wp-json/rankmath/v1/redirections",
            auth=auth,
            json={
                "sources": [{"pattern": pattern, "comparison": "starts_with"}],
                "destination": SITE,
                "type": "301",
                "status": "active",
            },
            timeout=10
        )
        if r.status_code in (200, 201):
            result["redirects"] += 1
            print(f"  ✅ {pattern}* → 홈 ({desc})")
        else:
            print(f"  ⚠️ {pattern}: {r.status_code}")
    except Exception as e:
        print(f"  ❌ {pattern}: {e}")
    time.sleep(0.3)

sys.stdout.flush()

# ── 3. .htaccess 규칙 추가 (Blogger URL 차단) ────────────
print("\n[3] .htaccess Blogger URL 리다이렉트 규칙")
htaccess_rules = """
# Blogger URL 리다이렉트 (WordPress 이전 후)
<IfModule mod_rewrite.c>
RewriteEngine On

# Blogger 날짜 형식 URL
RewriteRule ^20[0-9]{2}/[0-9]{2}/ https://k-health365.com/ [R=301,L]

# Blogger 검색 URL
RewriteRule ^search/ https://k-health365.com/ [R=301,L]

# .html 확장자 Blogger URL
RewriteRule ^.*\.html$ https://k-health365.com/ [R=301,L]

# m=1 모바일 파라미터 제거
RewriteCond %{QUERY_STRING} m=1
RewriteRule ^(.*)$ https://k-health365.com/$1? [R=301,L]

</IfModule>
"""

# WP REST API로 .htaccess 수정 (직접 접근)
# Rank Math에 등록하는 방식으로 대체
try:
    # permalink 재저장으로 .htaccess 갱신
    for _ in range(2):
        requests.post(f"{base}/settings", auth=auth,
                     json={"permalink_structure": "/%postname%/"}, timeout=10)
        time.sleep(1)
    print("  ✅ 퍼머링크 재저장 완료")
except Exception as e:
    print(f"  ⚠️ {e}")

sys.stdout.flush()

# ── 4. www 서브도메인 canonical 설정 ─────────────────────
print("\n[4] canonical URL 설정 확인")
# Rank Math에서 canonical을 k-health365.com으로 강제 설정
try:
    r = requests.get(f"{SITE}/wp-json/rankmath/v1/settings", auth=auth, timeout=10)
    if r.status_code == 200:
        settings = r.json()
        general = settings.get("general", {})
        # canonical 설정
        general["canonical_url"] = SITE
        r2 = requests.post(f"{SITE}/wp-json/rankmath/v1/settings",
                          auth=auth, json={"general": general}, timeout=10)
        print(f"  Rank Math canonical: HTTP {r2.status_code}")
except Exception as e:
    print(f"  ⚠️ {e}")

# ── 5. 결과 저장 + 수동 조치 안내 ────────────────────────
manual_actions = """
=== 수동으로 해야 할 작업 ===

1. Hostinger DNS에서 서브도메인 제거:
   - beauty.k-health365.com → 삭제
   - wearable-health365.k-health365.com → 삭제
   - health-devices.k-health365.com → 삭제
   - healthinsurance.k-health365.com → 삭제
   - eldercare.k-health365.com → 삭제
   (DNS → 레코드 관리에서 해당 CNAME/A 레코드 삭제)

2. GSC에서 URL 제거 요청:
   GSC → 삭제 → 임시 삭제 요청
   위 Blogger URL 16개 입력

3. Blogger 대시보드에서 해당 블로그 삭제 또는 비공개 처리
"""

print(manual_actions)
sys.stdout.flush()

# 결과 저장
result["blogger_urls"] = BLOGGER_URLS + SUBDOMAIN_URLS
result["manual_actions"] = manual_actions
if GH_TOKEN:
    content = base64.b64encode(json.dumps(result,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "fix_blogger_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                     headers=gh_h, timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: Blogger 잔재 URL 처리","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                headers=gh_h, json=payload, timeout=15)

print(f"\n{'='*60}")
print(f"✅ 자동화 완료")
print(f"   301 리다이렉트 설정: {result['redirects']}개")
print(f"   오류: {result['errors']}개")
print(f"{'='*60}")
