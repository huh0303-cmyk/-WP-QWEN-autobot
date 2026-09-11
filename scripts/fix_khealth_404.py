#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_khealth_404.py
k-health365.com 404 오류 완전 해결
1. Rank Math 404 모니터에서 목록 수집
2. 삭제된 글 → 홈으로 301 리다이렉트
3. 이미지 SEO — 모든 글 이미지 ALT 태그 자동 추가
4. bbPress/BuddyPress 페이지 noindex 처리
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
print("k-health365.com 404 오류 완전 해결")
print("="*60)
sys.stdout.flush()

result = {
    "redirects_added": 0,
    "images_fixed": 0,
    "posts_processed": 0,
    "errors": 0
}

# ── 1. 현재 404 URL 목록 수집 (Rank Math 404 Monitor) ────
print("\n[1] 404 URL 목록 수집")
# Rank Math REST API로 404 목록 조회
try:
    r404 = requests.get(
        f"{SITE}/wp-json/rankmath/v1/404",
        auth=auth, timeout=15
    )
    print(f"  Rank Math 404 API: HTTP {r404.status_code}")
    if r404.status_code == 200:
        urls_404 = r404.json()
        print(f"  404 URL 수: {len(urls_404)}")
except Exception as e:
    print(f"  404 API 없음: {e}")
    urls_404 = []

# ── 2. WP 리다이렉션 플러그인 or Rank Math로 301 설정 ────
print("\n[2] 404 URL → 301 리다이렉트 설정")

# 기본 404 URL 패턴 (GSC에서 확인된 98개)
# post-숫자, 숫자 슬러그 형태가 대부분
common_404_slugs = [
    "post-5", "post-67", "post-88", "post-116",
    "post/", "page/2", "page/3",
]

# Rank Math Redirection API
for slug in common_404_slugs:
    url_404 = f"{SITE}/{slug}/"
    try:
        r = requests.post(
            f"{SITE}/wp-json/rankmath/v1/redirections",
            auth=auth,
            json={
                "sources": [{"pattern": f"/{slug}/", "comparison": "exact"}],
                "destination": SITE,
                "type": "301",
                "status": "active"
            },
            timeout=10
        )
        if r.status_code in (200, 201):
            result["redirects_added"] += 1
            print(f"  ✅ 301 설정: /{slug}/ → 홈")
        else:
            print(f"  ⚠️ {slug}: HTTP {r.status_code}")
    except Exception as e:
        print(f"  ⚠️ {slug}: {e}")
    time.sleep(0.3)

# ── 3. 전체 글 이미지 ALT 태그 자동 추가 ─────────────────
print("\n[3] 이미지 ALT 태그 자동 추가 (Image SEO)")

def fix_image_alts(html_content, title, focus_kw):
    """이미지 ALT 태그 없는 것 자동 추가"""
    fixed = 0
    
    def replace_img(match):
        nonlocal fixed
        img_tag = match.group(0)
        
        # 이미 alt 있으면 건드리지 않음
        if re.search(r'alt=["\'][^"\']*["\']', img_tag, re.IGNORECASE):
            # alt가 비어있으면 수정
            empty_alt = re.search(r'alt=["\']["\']', img_tag)
            if empty_alt:
                alt_text = focus_kw or title[:30]
                new_img = re.sub(r'alt=["\']["\']', f'alt="{alt_text}"', img_tag)
                fixed += 1
                return new_img
            return img_tag
        
        # alt 없으면 추가
        alt_text = focus_kw or title[:30]
        # src에서 파일명 추출해서 alt 보강
        src_match = re.search(r'src=["\']([^"\']+)["\']', img_tag)
        if src_match:
            src = src_match.group(1)
            filename = src.split('/')[-1].split('.')[0]
            filename = re.sub(r'[-_\d]', ' ', filename).strip()
            if filename and len(filename) > 3:
                alt_text = f"{focus_kw or title[:20]} - {filename[:20]}"
        
        new_img = img_tag.rstrip('>').rstrip('/') + f' alt="{alt_text}">'
        fixed += 1
        return new_img
    
    new_html = re.sub(r'<img[^>]*>', replace_img, html_content, flags=re.IGNORECASE)
    return new_html, fixed

# 전체 글 처리
page = 1
total_img_fixed = 0

while True:
    try:
        r = requests.get(f"{base}/posts", auth=auth,
                         params={"per_page": 20, "page": page, "status": "publish",
                                 "_fields": "id,title,content,meta"},
                         timeout=30)
        if r.status_code != 200 or not r.json():
            break
        posts = r.json()
    except Exception as e:
        print(f"  ⚠️ {e}"); break

    for p in posts:
        pid   = p.get("id")
        t_obj = p.get("title", {})
        title = re.sub(r'<[^>]+>', '', t_obj.get("rendered","") if isinstance(t_obj,dict) else "").strip()
        b_obj = p.get("content", {})
        body  = b_obj.get("rendered","") if isinstance(b_obj, dict) else ""
        meta  = p.get("meta", {}) or {}
        focus = meta.get("rank_math_focus_keyword","") or title[:20]

        # 이미지가 있는 글만 처리
        if '<img' not in body:
            result["posts_processed"] += 1
            continue

        new_body, img_fixed = fix_image_alts(body, title, focus)

        if img_fixed > 0:
            try:
                rp = requests.post(
                    f"{base}/posts/{pid}", auth=auth,
                    json={"content": new_body},
                    timeout=15
                )
                if rp.status_code in (200, 201):
                    total_img_fixed += img_fixed
                    if total_img_fixed % 50 == 0:
                        print(f"  이미지 ALT 추가: 누적 {total_img_fixed}개...")
                        sys.stdout.flush()
            except: pass
            time.sleep(0.2)

        result["posts_processed"] += 1
        time.sleep(0.1)

    if len(posts) < 20: break
    page += 1
    time.sleep(0.5)

result["images_fixed"] = total_img_fixed
print(f"  ✅ 이미지 ALT 추가: {total_img_fixed}개")
sys.stdout.flush()

# ── 4. bbPress/BuddyPress 페이지 noindex ─────────────────
print("\n[4] bbPress/BuddyPress/포럼 페이지 noindex")
# 이 플러그인들이 활성화된 경우 해당 URL noindex 처리
# Rank Math에서 해당 post type noindex 설정
bp_types = ["topic", "reply", "forum", "bp-member", "bp-group"]
for pt in bp_types:
    try:
        r = requests.get(
            f"{SITE}/wp-json/rankmath/v1/settings",
            auth=auth, timeout=8
        )
        if r.status_code == 200:
            settings = r.json()
            titles = settings.get("titles", {})
            if pt not in titles:
                titles[pt] = {}
            titles[pt]["robots"] = ["noindex", "follow"]
            requests.post(
                f"{SITE}/wp-json/rankmath/v1/settings",
                auth=auth, json={"titles": titles}, timeout=10
            )
    except: pass

print("  ✅ 포럼 페이지 noindex 설정 시도 완료")

# ── 5. 홈페이지 + 주요 페이지 강제 색인 요청 ─────────────
print("\n[5] 주요 페이지 IndexNow 재제출")
INDEXNOW_KEY = "907ae08aa52b45239490ed2407df835d"

# 건강 카테고리 페이지들
priority_urls = [
    SITE,
    f"{SITE}/category/심혈관건강/",
    f"{SITE}/category/당뇨·혈당/",
    f"{SITE}/category/영양·보충제/",
    f"{SITE}/category/다이어트·운동/",
    f"{SITE}/category/정신건강/",
    f"{SITE}/category/피부·모발/",
    f"{SITE}/category/근골격계/",
    f"{SITE}/category/소화기건강/",
    f"{SITE}/category/건강정보/",
]

# 최근 글 50개 추가
try:
    r = requests.get(f"{base}/posts", auth=auth,
                     params={"per_page": 50, "status": "publish", "_fields": "link"},
                     timeout=20)
    if r.status_code == 200:
        for p in r.json():
            if p.get("link"): priority_urls.append(p["link"])
except: pass

payload = {
    "host": "k-health365.com",
    "key": INDEXNOW_KEY,
    "keyLocation": f"{SITE}/{INDEXNOW_KEY}.txt",
    "urlList": priority_urls[:200]
}
for ep in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow",
           "https://searchadvisor.naver.com/indexnow"]:
    try:
        r2 = requests.post(ep, json=payload,
                          headers={"Content-Type":"application/json"}, timeout=10)
        print(f"  {ep.split('/')[2]}: HTTP {r2.status_code}")
    except: pass

print(f"  ✅ {len(priority_urls)}개 URL 재제출")

# 결과 저장
if GH_TOKEN:
    content = base64.b64encode(json.dumps(result,ensure_ascii=False,indent=2).encode()).decode()
    gh_h = {"Authorization":f"token {GH_TOKEN}","Content-Type":"application/json"}
    path = "fix_khealth_404_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                      headers=gh_h, timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload2 = {"message":"result: khealth 404수정+이미지ALT","content":content}
    if sha: payload2["sha"] = sha
    requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                 headers=gh_h, json=payload2, timeout=15)

print(f"\n{'='*60}")
print(f"✅ 완료")
print(f"   301 리다이렉트:  {result['redirects_added']}개")
print(f"   이미지 ALT:      {result['images_fixed']}개")
print(f"   처리 글:         {result['posts_processed']}개")
print(f"{'='*60}")
