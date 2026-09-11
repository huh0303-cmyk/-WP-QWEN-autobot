#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gsc_sitemap_manager.py
1. 모든 사이트 http:// 사이트맵 삭제
2. https:// 사이트맵 3개 제출
3. 서비스 계정이 없는 사이트 목록 출력
"""
import os, json, sys, time, base64, requests

# GSC 인증
KEY_JSON = os.getenv("GSC_SERVICE_ACCOUNT_JSON","")
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","huh0303-cmyk/-WP-QWEN-autobot")

if not KEY_JSON:
    print("❌ GSC_SERVICE_ACCOUNT_JSON 없음"); sys.exit(1)

key_data = json.loads(KEY_JSON)

# JWT 토큰 직접 생성
import time as time_mod
import json as json_mod

def get_gsc_token():
    import jwt  # PyJWT
    now = int(time_mod.time())
    payload = {
        "iss":   key_data["client_email"],
        "scope": "https://www.googleapis.com/auth/webmasters",
        "aud":   "https://oauth2.googleapis.com/token",
        "iat":   now,
        "exp":   now + 3600,
    }
    private_key = key_data["private_key"]
    token = jwt.encode(payload, private_key, algorithm="RS256")
    
    r = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion":  token
        },
        timeout=15
    )
    if r.status_code == 200:
        return r.json().get("access_token")
    else:
        print(f"❌ 토큰 발급 실패: {r.text[:200]}")
        return None

ACCESS_TOKEN = get_gsc_token()
if not ACCESS_TOKEN:
    sys.exit(1)

print(f"✅ GSC 토큰 발급 성공")

def gsc_request(method, endpoint, data=None):
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type":  "application/json"
    }
    base = "https://www.googleapis.com/webmasters/v3"
    url  = f"{base}{endpoint}"
    if method == "GET":
        r = requests.get(url, headers=headers, timeout=15)
    elif method == "DELETE":
        r = requests.delete(url, headers=headers, timeout=15)
    elif method == "PUT":
        r = requests.put(url, headers=headers, json=data, timeout=15)
    return r

SITES = [
    "https://k-health365.com/",
    "https://koreamedicaltour.com/",
    "https://koreainvest365.com/",
    "https://ki-korea.com/",
    "https://koreainsurance365.com/",
    "https://kfinance365.com/",
    "https://koreataxnlaw.com/",
    "https://koreacrypto365.com/",
    "https://krealestate365.com/",
    "https://ktech365.com/",
    "https://kskin365.com/",
    "https://oliveyoungkorea.com/",
    "https://kworld365.com/",
    "https://k-trip365.com/",
    "https://k-visa365.com/",
    "https://koreawedding365.com/",
    "https://kstudy365.com/",
    "https://studyinkorea365.com/",
    "https://kieca-korea.org/",
    "https://ksa-korea.org/",
    "https://sis-korea.com/",
    "https://jobkorea365.com/",
    "https://jobinkorea365.com/",
    "https://jobkoreaglobal.com/",
    "https://korea365.org/",
    "https://koreanews365.com/",
    "https://theseouljournal.com/",
]

# 접근 가능한 사이트 먼저 확인
r = gsc_request("GET", "/sites")
if r.status_code != 200:
    print(f"❌ GSC 사이트 목록 조회 실패: HTTP {r.status_code}")
    print(f"   {r.text[:300]}")
    print("\n⚠️  Search Console API가 활성화되지 않았거나")
    print("   서비스 계정이 GSC에 추가되지 않은 것 같습니다.")
    print("\n필요한 조치:")
    print("1. https://console.cloud.google.com/apis/library/searchconsole.googleapis.com?project=gen-lang-client-0252428095")
    print("   → Search Console API '사용 설정' 클릭")
    print("\n2. 각 GSC 사이트에 아래 이메일 추가 (소유자 권한):")
    print("   gsc-api@gen-lang-client-0252428095.iam.gserviceaccount.com")
    sys.exit(0)

accessible = {s.get("siteUrl"): s.get("permissionLevel") 
              for s in r.json().get("siteEntry", [])}
print(f"\n접근 가능한 GSC 사이트: {len(accessible)}개")
for url, perm in accessible.items():
    print(f"  ✅ {url} ({perm})")

results = {"deleted": [], "submitted": [], "no_access": [], "errors": []}

print(f"\n{'='*60}")
print("사이트맵 정리 시작")
print("="*60)

for site_url in SITES:
    domain = site_url.rstrip("/")
    print(f"\n🌐 {domain}")
    
    # 접근 권한 확인
    if site_url not in accessible and domain not in [k.rstrip("/") for k in accessible]:
        print(f"  ⚠️  GSC 접근 권한 없음 → 수동 추가 필요")
        results["no_access"].append(domain)
        continue
    
    encoded = requests.utils.quote(site_url, safe="")
    
    # 기존 사이트맵 조회
    r = gsc_request("GET", f"/sites/{encoded}/sitemaps")
    if r.status_code != 200:
        print(f"  ❌ 사이트맵 조회 실패: {r.status_code}")
        results["errors"].append(domain)
        continue
    
    sitemaps = r.json().get("sitemap", [])
    print(f"  현재 사이트맵 {len(sitemaps)}개:")
    
    for sm in sitemaps:
        sm_url = sm.get("path", "")
        sm_type = sm.get("type","")
        pending = sm.get("isPending", False)
        print(f"    - {sm_url} ({sm_type})")
        
        # http:// 사이트맵 삭제
        if sm_url.startswith("http://"):
            enc_sm = requests.utils.quote(sm_url, safe="")
            rd = gsc_request("DELETE", f"/sites/{encoded}/sitemaps/{enc_sm}")
            if rd.status_code in (200, 204):
                print(f"    🗑️  삭제 완료: {sm_url}")
                results["deleted"].append(sm_url)
            else:
                print(f"    ❌ 삭제 실패: HTTP {rd.status_code}")
            time.sleep(0.5)
    
    # https:// 사이트맵 제출
    sitemaps_to_submit = [
        f"{domain}/sitemap_index.xml",
        f"{domain}/post-sitemap.xml",
        f"{domain}/page-sitemap.xml",
    ]
    
    for sm_url in sitemaps_to_submit:
        enc_sm = requests.utils.quote(sm_url, safe="")
        rs = gsc_request("PUT", f"/sites/{encoded}/sitemaps/{enc_sm}")
        if rs.status_code in (200, 204):
            print(f"  ✅ 제출: {sm_url}")
            results["submitted"].append(sm_url)
        else:
            print(f"  ⚠️  제출 실패 {sm_url}: HTTP {rs.status_code}")
        time.sleep(0.3)
    
    time.sleep(1)

# 결과 저장
print(f"\n{'='*60}")
print(f"✅ 완료")
print(f"  http 사이트맵 삭제: {len(results['deleted'])}개")
print(f"  https 사이트맵 제출: {len(results['submitted'])}개")
print(f"  GSC 접근 없는 사이트: {len(results['no_access'])}개")

if results["no_access"]:
    print(f"\n⚠️  아래 사이트는 GSC에 서비스 계정 추가 필요:")
    print(f"   이메일: gsc-api@gen-lang-client-0252428095.iam.gserviceaccount.com")
    for s in results["no_access"]:
        print(f"   - {s}")

# GitHub에 결과 커밋
if GH_TOKEN:
    content = base64.b64encode(json.dumps(results, ensure_ascii=False, indent=2).encode()).decode()
    gh_h = {"Authorization": f"token {GH_TOKEN}", "Content-Type": "application/json"}
    path = "gsc_sitemap_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}", headers=gh_h, timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: GSC 사이트맵 정리","content":content}
    if sha: payload["sha"] = sha
    r2 = requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                      headers=gh_h, json=payload, timeout=15)
    print(f"\n결과 커밋: {'✅' if 'content' in r2.json() else '❌'}")
