#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_khealth_meta.py
k-health365.com 전체 글 Rank Math 메타 일괄 수정
1. blog_public = True 강제
2. focus keyword 없는 글 → slug에서 키워드 추출하여 주입
3. meta description 없는 글 → 제목 기반 자동 생성
4. robots = index,follow 강제
"""
import os, requests, re, time, sys, json, base64

WP_USER  = "huh0303@gmail.com"
SITE     = "https://k-health365.com"
pw       = os.getenv("KHEALTH365COM","")
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

if not pw: print("NO PW"); exit(1)
base = f"{SITE}/wp-json/wp/v2"
auth = (WP_USER, pw)

print("="*60)
print("k-health365.com Rank Math 메타 일괄 수정")
print("="*60)
sys.stdout.flush()

# ── 1. blog_public = True ────────────────────────────────
print("\n[1] blog_public = True 강제 설정")
for _ in range(3):
    r = requests.post(f"{base}/settings", auth=auth,
                      json={"blog_public": True}, timeout=10)
    if r.status_code == 200:
        bp = r.json().get("blog_public")
        print(f"  ✅ blog_public = {bp}")
        break
    time.sleep(2)
sys.stdout.flush()

# ── 2. 전체 글 메타 일괄 수정 ────────────────────────────
print("\n[2] 전체 글 Rank Math 메타 일괄 수정")

def slug_to_keyword(slug):
    """슬러그에서 키워드 추출"""
    # 불필요한 단어 제거
    stop = {'the','a','an','in','on','at','to','for','of','and','or',
            'is','are','was','were','be','been','being','have','has',
            'had','do','does','did','will','would','could','should',
            'may','might','must','can','that','this','with','from',
            'your','our','how','what','why','when','where','who',
            'complete','guide','best','top','tips','ways','list',
            'everything','about','know','understanding','introduction',
            'beginners','advanced','ultimate','comprehensive','essential'}
    words = re.sub(r'[-_]', ' ', slug).split()
    keywords = [w for w in words if w.lower() not in stop and len(w) > 2]
    return ' '.join(keywords[:4]) if keywords else slug.replace('-', ' ')[:30]

def make_meta_desc(title, keyword, lang='ko'):
    """제목과 키워드로 메타 디스크립션 생성"""
    if lang == 'ko':
        templates = [
            f"{keyword}에 대한 완전한 가이드입니다. 전문가가 검증한 최신 정보와 실용적인 조언을 확인하세요.",
            f"{title}. 건강 전문가가 알려주는 핵심 정보와 일상에서 바로 실천할 수 있는 방법을 소개합니다.",
            f"{keyword} 관련 최신 의학 정보와 생활 속 실천 방법을 전문의 수준으로 쉽게 설명합니다.",
        ]
    else:
        templates = [
            f"Complete guide to {keyword}. Expert-verified information and practical tips you need to know in 2026.",
            f"{title}. Discover evidence-based insights and actionable advice from health professionals.",
        ]
    import random
    desc = random.choice(templates)
    return desc[:140] if lang=='ko' else desc[:155]

page = 1
total = fixed_focus = fixed_desc = fixed_robots = already_ok = errors = 0

while True:
    try:
        r = requests.get(f"{base}/posts", auth=auth,
                         params={"per_page": 50, "page": page,
                                 "status": "publish",
                                 "_fields": "id,slug,title,meta,lang"},
                         timeout=30)
        if r.status_code != 200 or not r.json():
            break
        posts = r.json()
    except Exception as e:
        print(f"  ⚠️ 페이지 {page} 오류: {e}")
        break

    for p in posts:
        total += 1
        pid   = p.get("id")
        slug  = p.get("slug","")
        title_obj = p.get("title",{})
        title = title_obj.get("rendered","") if isinstance(title_obj,dict) else str(title_obj)
        title = re.sub(r'<[^>]+>','',title).strip()
        meta  = p.get("meta",{}) or {}

        focus   = meta.get("rank_math_focus_keyword","")
        desc    = meta.get("rank_math_description","")
        robots  = meta.get("rank_math_robots",[])

        needs_update = False
        patch = {}

        # focus keyword 없으면 slug에서 추출
        if not focus:
            kw = slug_to_keyword(slug)
            if kw:
                patch["rank_math_focus_keyword"] = kw
                fixed_focus += 1
                needs_update = True
        else:
            kw = focus

        # meta description 없으면 생성
        if not desc:
            # 한국어 사이트
            new_desc = make_meta_desc(title, kw or slug_to_keyword(slug), lang='ko')
            patch["rank_math_description"] = new_desc
            fixed_desc += 1
            needs_update = True

        # robots 확인 (noindex면 수정)
        if "noindex" in str(robots).lower():
            patch["rank_math_robots"] = ["index", "follow"]
            fixed_robots += 1
            needs_update = True

        if needs_update:
            try:
                r2 = requests.post(
                    f"{base}/posts/{pid}",
                    auth=auth,
                    json={"meta": patch},
                    timeout=15
                )
                if r2.status_code in (200, 201):
                    if total % 20 == 0:
                        print(f"  진행: {total}개 처리 | focus:{fixed_focus} desc:{fixed_desc} robots:{fixed_robots}")
                        sys.stdout.flush()
                else:
                    errors += 1
            except Exception as e:
                errors += 1
            time.sleep(0.15)
        else:
            already_ok += 1

    if len(posts) < 50:
        break
    page += 1
    time.sleep(0.5)

print(f"\n  완료: 총 {total}개")
print(f"  focus 추가: {fixed_focus}개")
print(f"  desc 추가:  {fixed_desc}개")
print(f"  robots 수정: {fixed_robots}개")
print(f"  이미 정상:  {already_ok}개")
print(f"  오류:       {errors}개")
sys.stdout.flush()

# ── 3. 퍼머링크 재저장 ────────────────────────────────────
print("\n[3] 퍼머링크 재저장")
for _ in range(2):
    requests.post(f"{base}/settings", auth=auth,
                  json={"permalink_structure": "/%postname%/"}, timeout=10)
    time.sleep(1)
print("  ✅ 완료")

# ── 4. IndexNow로 전체 URL 재제출 ─────────────────────────
print("\n[4] IndexNow 전체 URL 재제출")
INDEXNOW_KEY = "907ae08aa52b45239490ed2407df835d"
all_urls = []
page = 1
while True:
    r = requests.get(f"{base}/posts", auth=auth,
                     params={"per_page":100,"page":page,"status":"publish","_fields":"link"},
                     timeout=20)
    if r.status_code != 200 or not r.json(): break
    posts = r.json()
    for p in posts:
        if p.get("link"): all_urls.append(p["link"])
    if len(posts) < 100: break
    page += 1

submitted = 0
for i in range(0, len(all_urls), 100):
    batch = all_urls[i:i+100]
    payload = {
        "host": "k-health365.com",
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE}/{INDEXNOW_KEY}.txt",
        "urlList": batch
    }
    for ep in ["https://api.indexnow.org/indexnow","https://www.bing.com/indexnow",
                "https://searchadvisor.naver.com/indexnow"]:
        try:
            r2 = requests.post(ep, json=payload,
                              headers={"Content-Type":"application/json"}, timeout=10)
            if r2.status_code in (200,202):
                submitted += len(batch)
                break
        except: pass
    time.sleep(0.3)

print(f"  IndexNow 제출: {submitted}개 URL")

# 결과 저장
result = {
    "total": total, "fixed_focus": fixed_focus,
    "fixed_desc": fixed_desc, "fixed_robots": fixed_robots,
    "already_ok": already_ok, "errors": errors,
    "indexnow_submitted": submitted
}
if GH_TOKEN:
    content = base64.b64encode(json.dumps(result,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "fix_khealth_meta_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                      headers=gh_h, timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: khealth 메타 일괄 수정","content":content}
    if sha: payload["sha"] = sha
    r2 = requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                      headers=gh_h, json=payload, timeout=15)
    print(f"\n결과 저장: {'✅' if 'content' in r2.json() else '❌'}")

print(f"\n{'='*60}")
print(f"✅ 완료")
print(f"{'='*60}")
