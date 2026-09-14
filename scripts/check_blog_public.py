#!/usr/bin/env python3
import os, requests, json, base64

WP_USER = "huh0303@gmail.com"
SITE    = "https://k-health365.com"
pw      = os.getenv("KHEALTH365COM","")
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

if not pw: print("NO PW"); exit(1)
base = f"{SITE}/wp-json/wp/v2"
auth = (WP_USER, pw)

print("=== blog_public 완전 확인 ===")
r = requests.get(f"{base}/settings", auth=auth, timeout=10)
print(f"HTTP: {r.status_code}")
settings = r.json()

# 모든 설정값 출력
for k,v in settings.items():
    if any(x in k.lower() for x in ['public','index','robot','blog','search']):
        print(f"  {k}: {v!r}")

print(f"\nblog_public raw: {settings.get('blog_public')!r}")
print(f"type: {type(settings.get('blog_public'))}")

# robots.txt 실제 내용
r2 = requests.get(f"{SITE}/robots.txt", timeout=10)
print(f"\n=== robots.txt (HTTP {r2.status_code}) ===")
print(r2.text)

# 홈페이지 X-Robots-Tag 헤더
r3 = requests.get(SITE, timeout=10, headers={"User-Agent":"Googlebot/2.1"})
print(f"\n=== 홈페이지 헤더 ===")
print(f"X-Robots-Tag: {r3.headers.get('X-Robots-Tag','없음')}")
print(f"HTTP: {r3.status_code}")

# 결과 저장
result = {
    "blog_public": settings.get("blog_public"),
    "blog_public_type": str(type(settings.get("blog_public"))),
    "robots_txt": r2.text,
    "x_robots": r3.headers.get("X-Robots-Tag","없음"),
    "all_public_settings": {k:v for k,v in settings.items()
                             if any(x in k.lower() for x in ['public','index','robot','blog','search'])}
}
if GH_TOKEN:
    content = __import__('base64').b64encode(__import__('json').dumps(result,ensure_ascii=False).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "blog_public_check.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",headers=gh_h,timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"check: blog_public","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                 headers=gh_h,json=payload,timeout=15)
    print("\n저장 완료")
