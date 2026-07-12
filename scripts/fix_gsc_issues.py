#!/usr/bin/env python3
import os, requests, re, json, base64, time

WP_USER  = "huh0303@gmail.com"
SITE     = "https://k-health365.com"
pw       = os.getenv("KHEALTH365COM","")
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

if not pw: exit(1)
base_api = f"{SITE}/wp-json/wp/v2"
auth     = (WP_USER, pw)

# ── 404 URL 98개 + Blogger URL 16개 모두 리다이렉트 설정 ──
# Rank Math Redirection API로 전부 등록

# 패턴 1: www.k-health365.com Blogger 날짜 URL
blogger_prefixes = [
    "/2025/06/", "/2025/07/", "/2025/08/", "/2025/09/",
    "/2025/10/", "/2025/11/", "/2025/12/",
    "/2026/01/", "/2026/02/", "/2026/03/",
    "/search/label/", "/search/",
    "/form/",  # newsletter-form 404
]

# 서브도메인 전체
subdomains = [
    "https://beauty.k-health365.com",
    "https://wearable-health365.k-health365.com",
    "https://health-devices.k-health365.com",
    "https://healthinsurance.k-health365.com",
    "https://eldercare.k-health365.com",
    "https://www.k-health365.com",
    "https://sleep-health.k-health365.com",
    "https://nutrition-supplements.k-health365.com",
]

added = 0
failed = 0

print("="*55)
print("404 + Blogger URL 리다이렉트 일괄 설정")
print("="*55)

# 1. Blogger 날짜 패턴 → 홈 301 (starts_with)
print("\n[1] Blogger 날짜 패턴 와일드카드 리다이렉트")
for prefix in blogger_prefixes:
    try:
        r = requests.post(
            f"{SITE}/wp-json/rankmath/v1/redirections",
            auth=auth,
            json={
                "sources": [{"pattern": prefix, "comparison": "starts_with"}],
                "destination": SITE,
                "type": "301",
                "status": "active",
            },
            timeout=10
        )
        if r.status_code in (200,201):
            added += 1
            print(f"  ✅ {prefix}* → 홈")
        else:
            # 이미 존재하면 OK
            if "already" in r.text.lower() or r.status_code == 400:
                print(f"  ⚠️ 이미 존재: {prefix}")
                added += 1
            else:
                failed += 1
                print(f"  ❌ {prefix}: {r.status_code}")
    except Exception as e:
        print(f"  ❌ {prefix}: {e}")
    time.sleep(0.3)

# 2. ?m=1 모바일 파라미터 리다이렉트
print("\n[2] m=1 파라미터 리다이렉트")
try:
    r = requests.post(
        f"{SITE}/wp-json/rankmath/v1/redirections",
        auth=auth,
        json={
            "sources": [{"pattern": "?m=1", "comparison": "contains"}],
            "destination": SITE,
            "type": "301",
            "status": "active",
        },
        timeout=10
    )
    if r.status_code in (200,201,400):
        print(f"  ✅ ?m=1 → 홈")
        added += 1
except Exception as e:
    print(f"  ❌ {e}")

# 3. newsletter-form 404
print("\n[3] newsletter-form 404 처리")
try:
    r = requests.post(
        f"{SITE}/wp-json/rankmath/v1/redirections",
        auth=auth,
        json={
            "sources": [{"pattern": "/form/newsletter-form/", "comparison": "exact"}],
            "destination": SITE,
            "type": "301",
            "status": "active",
        },
        timeout=10
    )
    if r.status_code in (200,201,400):
        print(f"  ✅ /form/newsletter-form/ → 홈")
        added += 1
except Exception as e:
    print(f"  ❌ {e}")

# 4. .html 확장자 패턴
print("\n[4] .html 확장자 Blogger URL 처리")
try:
    r = requests.post(
        f"{SITE}/wp-json/rankmath/v1/redirections",
        auth=auth,
        json={
            "sources": [{"pattern": ".html", "comparison": "contains"}],
            "destination": SITE,
            "type": "301",
            "status": "active",
        },
        timeout=10
    )
    if r.status_code in (200,201,400):
        print(f"  ✅ *.html → 홈")
        added += 1
except Exception as e:
    print(f"  ❌ {e}")

# 5. 현재 리다이렉션 목록 확인
print("\n[5] 등록된 리다이렉션 현황")
try:
    r = requests.get(
        f"{SITE}/wp-json/rankmath/v1/redirections",
        auth=auth, timeout=10
    )
    if r.status_code == 200:
        rd_list = r.json()
        total_rd = len(rd_list) if isinstance(rd_list, list) else rd_list.get("total",0)
        print(f"  총 리다이렉션: {total_rd}개")
except: pass

# 6. GSC URL 삭제 API (가능한 경우)
print("\n[6] IndexNow로 올바른 URL 재제출 (구글에 새 URL 알림)")
INDEXNOW_KEY = "907ae08aa52b45239490ed2407df835d"

# 현재 보존된 글 URL 수집
good_urls = []
page = 1
while True:
    r = requests.get(f"{base_api}/posts", auth=auth,
                    params={"per_page":100,"page":page,"status":"publish","_fields":"link"},
                    timeout=20)
    if r.status_code != 200 or not r.json(): break
    for p in r.json():
        if p.get("link"): good_urls.append(p["link"])
    if len(r.json()) < 100: break
    page += 1

# IndexNow 제출
for i in range(0, len(good_urls), 100):
    batch = good_urls[i:i+100]
    payload = {
        "host": "k-health365.com",
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE}/{INDEXNOW_KEY}.txt",
        "urlList": batch
    }
    for ep in ["https://api.indexnow.org/indexnow",
                "https://www.bing.com/indexnow",
                "https://searchadvisor.naver.com/indexnow"]:
        try:
            r2 = requests.post(ep, json=payload,
                              headers={"Content-Type":"application/json"}, timeout=10)
            if r2.status_code in (200,202):
                break
        except: pass
    time.sleep(0.3)

print(f"  ✅ {len(good_urls)}개 URL IndexNow 재제출")

# 결과 저장
result = {"redirects_added":added,"redirects_failed":failed,"indexnow_urls":len(good_urls)}
if GH_TOKEN:
    content = base64.b64encode(json.dumps(result,ensure_ascii=False).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "gsc_fix_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                     headers=gh_h, timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload2 = {"message":"result: GSC 404+Blogger 처리","content":content}
    if sha: payload2["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                headers=gh_h, json=payload2, timeout=15)

print(f"\n{'='*55}")
print(f"✅ 완료 | 리다이렉트:{added} | IndexNow:{len(good_urls)}개")
print(f"{'='*55}")
