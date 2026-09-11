#!/usr/bin/env python3
"""색인 요청할 상위 글 목록 추출 — 품질 높은 순"""
import os, requests, re, json, base64

WP_USER = "huh0303@gmail.com"
SITE    = "https://k-health365.com"
pw      = os.getenv("KHEALTH365COM","")
GH_TOKEN= os.getenv("GH_PAT","")
GH_REPO = os.getenv("GITHUB_REPOSITORY","")

if not pw: exit(1)
base = f"{SITE}/wp-json/wp/v2"
auth = (WP_USER, pw)

def plain(html):
    return re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',html or '')).strip()

def score(title, body, meta_desc, focus_kw, char_cnt):
    s = 0
    if char_cnt >= 3000: s += 30
    elif char_cnt >= 2000: s += 20
    elif char_cnt >= 1500: s += 10
    if title and 15 <= len(title) <= 60: s += 15
    if meta_desc and len(meta_desc) >= 100: s += 15
    if focus_kw: s += 10
    h2 = len(re.findall(r'<h2[\s>]', body, re.IGNORECASE))
    tb = len(re.findall(r'<table[\s>]', body, re.IGNORECASE))
    if h2 >= 4: s += 15
    elif h2 >= 2: s += 8
    if tb >= 1: s += 10
    stats = len(re.findall(r'\d+[\.,]?\d*\s*(?:%|명|만|억|원|mmHg|mg)', body))
    if stats >= 5: s += 10
    elif stats >= 2: s += 5
    return min(s, 100)

# 전체 글 수집 + 점수 계산
all_posts = []
page = 1
while True:
    r = requests.get(f"{base}/posts", auth=auth,
                     params={"per_page":50,"page":page,"status":"publish",
                             "_fields":"id,slug,title,content,link,meta,date"},
                     timeout=30)
    if r.status_code != 200 or not r.json(): break
    posts = r.json()
    for p in posts:
        t = plain(p.get("title",{}).get("rendered","") if isinstance(p.get("title"),dict) else "")
        b = p.get("content",{}).get("rendered","") if isinstance(p.get("content"),dict) else ""
        meta = p.get("meta",{}) or {}
        desc = meta.get("rank_math_description","") or ""
        focus= meta.get("rank_math_focus_keyword","") or ""
        chars = len(plain(b).replace(' ','').replace('\n',''))
        sc = score(t, b, desc, focus, chars)
        all_posts.append({
            "id": p["id"],
            "title": t[:60],
            "url": p.get("link",""),
            "chars": chars,
            "score": sc,
            "focus": focus[:20] if focus else "",
            "date": p.get("date","")[:10],
        })
    if len(posts) < 50: break
    page += 1

# 점수 높은 순 정렬
all_posts.sort(key=lambda x: (-x["score"], -x["chars"]))

print("="*70)
print(f"색인 요청 우선순위 — 상위 {min(50,len(all_posts))}개")
print("="*70)
print(f"\n총 {len(all_posts)}개 글 분석 완료\n")
print(f"{'순위':>3} {'점수':>4} {'글자':>5} {'URL'}")
print("─"*70)
for i, p in enumerate(all_posts[:50], 1):
    print(f"{i:>3}. {p['score']:>3}점 {p['chars']:>5}자 | {p['url']}")

# GitHub 저장
if GH_TOKEN:
    result = {"total": len(all_posts), "top50": all_posts[:50]}
    content = base64.b64encode(json.dumps(result,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "khealth_top_posts.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                     headers=gh_h, timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: 색인요청 우선순위 목록","content":content}
    if sha: payload["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                headers=gh_h, json=payload, timeout=15)
    print(f"\n저장 완료")
