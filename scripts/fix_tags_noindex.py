#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_tags_noindex.py
1. Rank Math 태그 아카이브 → noindex 설정
2. 글 없는 태그(empty tags) 전부 삭제
3. 사용된 태그도 과도하게 많으면 정리
"""
import os, requests, time, sys, json, base64

WP_USER  = "huh0303@gmail.com"
SITE     = "https://k-health365.com"
pw       = os.getenv("KHEALTH365COM","")
GH_TOKEN = os.getenv("GH_PAT","")
GH_REPO  = os.getenv("GITHUB_REPOSITORY","")

if not pw: print("NO PW"); exit(1)

base = f"{SITE}/wp-json/wp/v2"
auth = (WP_USER, pw)

print("="*60)
print("k-health365.com 태그 정리 + Rank Math noindex 설정")
print("="*60)
sys.stdout.flush()

# ── 1. Rank Math 태그 noindex 설정 ───────────────────────
print("\n[1] Rank Math 태그 아카이브 noindex 설정")

# Rank Math REST API 시도
rm_endpoints = [
    f"{SITE}/wp-json/rankmath/v1/settings",
]
rm_ok = False
for ep in rm_endpoints:
    try:
        r = requests.get(ep, auth=auth, timeout=10)
        if r.status_code == 200:
            settings = r.json()
            titles = settings.get("titles", {})

            # 태그/작성자/날짜 noindex
            for key in ["post_tag", "author", "date", "search"]:
                if key not in titles:
                    titles[key] = {}
                titles[key]["robots"] = ["noindex", "follow"]
                titles[key]["advanced_robots"] = {}

            r2 = requests.post(ep, auth=auth,
                               json={"titles": titles}, timeout=15)
            if r2.status_code in (200, 201):
                print(f"  ✅ Rank Math REST API — 태그/작성자/날짜 noindex 설정 완료")
                rm_ok = True
            else:
                print(f"  ⚠️ Rank Math 설정 실패: {r2.status_code}")
            break
    except Exception as e:
        print(f"  📍 {ep}: {e}")

if not rm_ok:
    # WP Options 직접 수정 (rank_math_titles)
    print("  → Rank Math REST 없음. WP Options 방식 시도")
    try:
        # rank_math_titles 옵션 읽기
        r = requests.get(f"{base}/settings", auth=auth, timeout=10)
        if r.status_code == 200:
            settings = r.json()
            rm_titles_key = next((k for k in settings if 'rank_math_titles' in k), None)
            if rm_titles_key:
                current = settings[rm_titles_key]
                print(f"  현재 rank_math_titles: {str(current)[:100]}")
    except: pass

# ── 2. 빈 태그(글 없는 태그) 전부 삭제 ──────────────────
print("\n[2] 빈 태그 삭제")
page = 1
empty_deleted = 0
has_posts_count = 0
all_tags_count = 0

while True:
    try:
        r = requests.get(f"{base}/tags", auth=auth,
                         params={"per_page": 100, "page": page,
                                 "orderby": "count", "order": "asc",
                                 "_fields": "id,name,count"},
                         timeout=20)
        if r.status_code != 200 or not r.json():
            break
        tags = r.json()
        all_tags_count += len(tags)

        for tag in tags:
            if tag.get("count", 0) == 0:
                # 빈 태그 삭제
                try:
                    rd = requests.delete(
                        f"{base}/tags/{tag['id']}",
                        auth=auth,
                        params={"force": "true"},
                        timeout=10
                    )
                    if rd.status_code in (200, 201, 204):
                        empty_deleted += 1
                        if empty_deleted % 50 == 0:
                            print(f"  삭제 진행: {empty_deleted}개...")
                            sys.stdout.flush()
                except Exception as e:
                    pass
                time.sleep(0.05)
            else:
                has_posts_count += 1

        if len(tags) < 100:
            break
        page += 1
        time.sleep(0.2)

    except Exception as e:
        print(f"  ⚠️ {e}")
        break

print(f"  빈 태그 삭제: {empty_deleted}개")
print(f"  글 있는 태그 보존: {has_posts_count}개")
sys.stdout.flush()

# ── 3. 남은 태그 수 확인 ─────────────────────────────────
print("\n[3] 최종 태그 수 확인")
r = requests.get(f"{base}/tags?per_page=1", auth=auth, timeout=10)
remaining = int(r.headers.get("X-WP-Total", 0)) if r.status_code == 200 else 0
print(f"  남은 태그: {remaining}개 (삭제 전: {all_tags_count + empty_deleted}개)")

# ── 4. 사이트맵 재생성을 위한 퍼머링크 재저장 ──────────
print("\n[4] 퍼머링크 재저장 (사이트맵 갱신)")
for _ in range(2):
    requests.post(f"{base}/settings", auth=auth,
                  json={"permalink_structure": "/%postname%/"}, timeout=10)
    time.sleep(1)
print("  ✅ 완료")

# 결과 저장
result = {
    "rm_noindex_set": rm_ok,
    "empty_tags_deleted": empty_deleted,
    "tags_with_posts": has_posts_count,
    "tags_remaining": remaining
}
if GH_TOKEN:
    content = base64.b64encode(json.dumps(result, ensure_ascii=False, indent=2).encode()).decode()
    gh_h = {"Authorization": f"token {GH_TOKEN}", "Content-Type": "application/json"}
    path = "fix_tags_result.json"
    rg = requests.get(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                      headers=gh_h, timeout=10)
    sha = rg.json().get("sha","") if rg.status_code==200 else ""
    payload = {"message":"result: 태그 정리 완료","content":content}
    if sha: payload["sha"] = sha
    r2 = requests.put(f"https://api.github.com/repos/{GH_REPO}/contents/{path}",
                      headers=gh_h, json=payload, timeout=15)
    print(f"\n결과 커밋: {'✅' if 'content' in r2.json() else '❌'}")

print(f"\n{'='*60}")
print(f"✅ 완료")
print(f"  빈 태그 삭제: {empty_deleted}개")
print(f"  남은 태그: {remaining}개")
print(f"  Rank Math noindex: {'설정됨' if rm_ok else '수동 설정 필요'}")
print(f"{'='*60}")
