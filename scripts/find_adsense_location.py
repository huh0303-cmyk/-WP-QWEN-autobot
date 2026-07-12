#!/usr/bin/env python3
"""글 본문 vs 헤더 중 어디에 중복이 있는지 정확히 찾기"""
import os, requests, re, json, base64

WP_USER = "huh0303@gmail.com"
PUB_ID  = "ca-pub-3456727916386941"
GH_TOKEN= os.getenv("GH_PAT","")
GH_REPO = os.getenv("GITHUB_REPOSITORY","")

SITES = [
    ("https://k-health365.com",     "KHEALTH365COM"),
    ("https://koreamedicaltour.com","KOREAMEDICALTOURCOM"),
    ("https://kfinance365.com",     "KFINANCE365COM"),
    ("https://k-trip365.com",       "KTRIP365COM"),
]

result = {}

for site_url, env_key in SITES:
    pw = os.getenv(env_key,"")
    if not pw: continue
    domain = site_url.replace("https://","")
    auth   = (WP_USER, pw)
    base   = f"{site_url}/wp-json/wp/v2"

    print(f"\n{'='*50}")
    print(f"{domain}")

    # 1. 실제 페이지 HTML에서 위치 파악
    r = requests.get(site_url, timeout=12,
                    headers={"User-Agent":"Mozilla/5.0 Chrome/120"})
    html = r.text
    total = html.count(PUB_ID)
    print(f"  전체 HTML: {total}개")

    # head 섹션과 body 섹션 분리
    head_match = re.search(r'<head[^>]*>(.*?)</head>', html, re.DOTALL|re.IGNORECASE)
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL|re.IGNORECASE)

    head_count = 0
    body_count = 0
    if head_match:
        head_count = head_match.group(1).count(PUB_ID)
    if body_match:
        body_count = body_match.group(1).count(PUB_ID)

    print(f"  <head>: {head_count}개")
    print(f"  <body>: {body_count}개 ← 글 본문/위젯 영역")

    # 2. 글 본문에 직접 들어있는지 확인
    if body_count > 0:
        # 최근 글 3개 본문 확인
        r2 = requests.get(f"{base}/posts", auth=auth,
                         params={"per_page":3,"status":"publish","_fields":"id,title,content"},
                         timeout=15)
        if r2.status_code == 200:
            for p in r2.json():
                body = p.get("content",{}).get("rendered","")
                if PUB_ID in body:
                    title = re.sub(r'<[^>]+>','',p.get("title",{}).get("rendered",""))
                    print(f"  🔴 글 본문에 발견! [{p['id']}] {title[:40]}")

    result[domain] = {"total":total,"head":head_count,"body":body_count}

# 저장
if GH_TOKEN:
    content = base64.b64encode(json.dumps(result,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "adsense_location_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",headers=gh_h,timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"check: 애드센스 위치","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",headers=gh_h,json=payload,timeout=15)

print("\n완료")
