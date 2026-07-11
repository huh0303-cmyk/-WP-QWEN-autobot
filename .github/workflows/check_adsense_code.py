#!/usr/bin/env python3
"""k-health365.com WPCode 스니펫 목록 확인"""
import os, requests, json, base64, re

WP_USER  = "huh0303@gmail.com"
SITE     = "https://k-health365.com"
pw       = os.getenv("KHEALTH365COM","")
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

auth = (WP_USER, pw)
if not pw: exit(1)

result = {}

# 1. 실제 사이트 HTML에서 애드센스 확인
print("=== 실제 HTML 확인 ===")
r = requests.get(SITE, timeout=15,
                headers={"User-Agent":"Mozilla/5.0 Chrome/120"})
html = r.text
pub_id = re.findall(r'ca-pub-\d+', html)
ads_script = re.findall(r'<script[^>]*pagead[^>]*>', html, re.IGNORECASE)
print(f"HTTP: {r.status_code}")
print(f"Publisher ID 발견: {pub_id}")
print(f"AdSense script: {ads_script}")

result["html_pub_id"] = pub_id
result["html_ads_script"] = ads_script

# 2. WPCode 스니펫 목록
print("\n=== WPCode 스니펫 목록 ===")
for ep in [
    f"{SITE}/wp-json/wpcode/v1/snippets",
    f"{SITE}/wp-json/wpcode/v1/snippets?per_page=20",
]:
    r2 = requests.get(ep, auth=auth, timeout=10)
    print(f"  {ep}")
    print(f"  HTTP: {r2.status_code}")
    if r2.status_code == 200:
        data = r2.json()
        items = data if isinstance(data, list) else data.get("items", data.get("snippets",[]))
        print(f"  스니펫 수: {len(items)}")
        for item in items[:10]:
            name = item.get("title") or item.get("name","")
            active = item.get("active") or item.get("status","")
            loc = item.get("location") or item.get("insert_location","")
            code_preview = str(item.get("code","") or item.get("snippet_code",""))[:80]
            print(f"    [{item.get('id')}] {name} | {active} | {loc}")
            print(f"         {code_preview}")
        result["snippets"] = items
        break
    else:
        print(f"  응답: {r2.text[:100]}")

# 3. WP Options에서 WPCode 설정 확인
print("\n=== WP Settings WPCode 관련 ===")
r3 = requests.get(f"{SITE}/wp-json/wp/v2/settings", auth=auth, timeout=10)
if r3.status_code == 200:
    settings = r3.json()
    wpcode_keys = {k:v for k,v in settings.items()
                   if any(x in k.lower() for x in ["wpcode","snippet","header_code","footer_code"])}
    print(f"  WPCode 관련 키: {list(wpcode_keys.keys())}")
    for k,v in wpcode_keys.items():
        print(f"  {k}: {str(v)[:100]}")
    result["wpcode_settings"] = wpcode_keys

# GitHub 저장
if GH_TOKEN:
    content = base64.b64encode(json.dumps(result,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "adsense_code_check.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                     headers=gh_h, timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"check: adsense code location","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                headers=gh_h, json=payload, timeout=15)
print("\n완료")
