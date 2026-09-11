#!/usr/bin/env python3
"""GSC 색인 요청할 URL 목록 — 품질 높은 순 50개"""
import os, requests, re, json, base64

WP_USER  = "huh0303@gmail.com"
SITE     = "https://k-health365.com"
pw       = os.getenv("KHEALTH365COM","")
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

if not pw: exit(1)
base = f"{SITE}/wp-json/wp/v2"
auth = (WP_USER, pw)

def plain(html): return re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',html or '')).strip()

def score(title, body, desc, focus):
    s = 0
    chars = len(plain(body).replace(' ','').replace('\n',''))
    if chars >= 3000: s += 30
    elif chars >= 2000: s += 20
    elif chars >= 1500: s += 10
    if 15 <= len(title) <= 60: s += 15
    if desc and len(desc) >= 100: s += 15
    if focus: s += 10
    h2 = len(re.findall(r'<h2[\s>]',body,re.IGNORECASE))
    tb = len(re.findall(r'<table[\s>]',body,re.IGNORECASE))
    if h2 >= 4: s += 15
    elif h2 >= 2: s += 8
    if tb >= 1: s += 10
    nums = len(re.findall(r'\d+[\.,]?\d*\s*(?:%|명|만|억|원|mmHg)',body))
    if nums >= 5: s += 5
    return min(s,100), chars

all_posts = []
page = 1
while True:
    r = requests.get(f"{base}/posts", auth=auth,
                     params={"per_page":50,"page":page,"status":"publish",
                             "_fields":"id,title,content,link,meta,date"},
                     timeout=30)
    if r.status_code != 200 or not r.json(): break
    for p in r.json():
        t  = plain(p.get("title",{}).get("rendered","") if isinstance(p.get("title"),dict) else "")
        b  = p.get("content",{}).get("rendered","") if isinstance(p.get("content"),dict) else ""
        m  = p.get("meta",{}) or {}
        sc, chars = score(t, b, m.get("rank_math_description","") or "", m.get("rank_math_focus_keyword","") or "")
        all_posts.append({
            "id": p["id"], "title": t[:55], "url": p.get("link",""),
            "score": sc, "chars": chars, "date": p.get("date","")[:10]
        })
    if len(r.json()) < 50: break
    page += 1

all_posts.sort(key=lambda x: (-x["score"], -x["chars"]))

# 저장
if GH_TOKEN:
    out = {"total": len(all_posts), "posts": all_posts[:50]}
    content = base64.b64encode(json.dumps(out,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "khealth_index_urls.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                     headers=gh_h, timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: GSC 색인요청 URL 목록","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                headers=gh_h, json=payload, timeout=15)

print(f"총 {len(all_posts)}개 분석 완료")
print(f"상위 50개 저장됨")
for i, p in enumerate(all_posts[:50],1):
    print(f"{i:>2}. [{p['score']}점/{p['chars']}자] {p['url']}")
    print(f"     {p['title']}")
