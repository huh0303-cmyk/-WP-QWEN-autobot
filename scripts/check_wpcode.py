#!/usr/bin/env python3
import os, requests, json, base64

WP_USER = "huh0303@gmail.com"
pw      = os.getenv("KHEALTH365COM","")
SITE    = "https://k-health365.com"
auth    = (WP_USER, pw)
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

# WPCode API 엔드포인트 탐색
endpoints = [
    f"{SITE}/wp-json/wpcode/v1/snippets",
    f"{SITE}/wp-json/wpcode/v1/",
    f"{SITE}/wp-json/code-snippets/v1/snippets",
    f"{SITE}/wp-json/wpcode/v1/headers",
]

print("WPCode API 탐색:")
for ep in endpoints:
    try:
        r = requests.get(ep, auth=auth, timeout=8)
        print(f"  {r.status_code} {ep}")
        if r.status_code == 200:
            print(f"  응답: {str(r.json())[:200]}")
    except Exception as e:
        print(f"  오류: {e} | {ep}")

# WPCode 헤더/푸터 옵션 키 확인 (wp_options)
print("\nWP Settings에서 WPCode 관련 키:")
r = requests.get(f"{SITE}/wp-json/wp/v2/settings", auth=auth, timeout=10)
if r.status_code == 200:
    settings = r.json()
    for k,v in settings.items():
        if any(x in k.lower() for x in ["wpcode","code_snippet","header","footer","script"]):
            print(f"  {k}: {str(v)[:100]}")

result = {"endpoints_found": []}
if GH_TOKEN:
    content = base64.b64encode(json.dumps(result).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "wpcode_api_check.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                     headers=gh_h, timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"check: wpcode api","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                headers=gh_h, json=payload, timeout=15)
print("완료")
