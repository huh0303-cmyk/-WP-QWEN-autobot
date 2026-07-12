#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_dummy_posts.py
k-health365.com 더미 슬러그 전수조사 + 영구 삭제
- post-숫자, post/ 형태 슬러그
- 본문 없는 글
- 제목 없는 글
- 슬러그가 숫자만인 글
"""
import os, requests, time, re

WP_USER = "huh0303@gmail.com"
SITE    = "https://k-health365.com"
pw      = os.getenv("KHEALTH365COM", "")

if not pw:
    print("❌ NO PASSWORD"); exit(1)

base = f"{SITE}/wp-json/wp/v2"
auth = (WP_USER, pw)

print("=" * 60)
print("k-health365.com 더미 슬러그 전수조사")
print("=" * 60)

# ── 전체 글 수집 ──────────────────────────────────────────
all_posts = []
page = 1
while True:
    r = requests.get(f"{base}/posts", auth=auth,
                     params={"per_page": 100, "page": page,
                             "status": "publish,draft,trash",
                             "_fields": "id,slug,title,status,date,content"},
                     timeout=30)
    if r.status_code != 200 or not r.json():
        break
    posts = r.json()
    all_posts.extend(posts)
    print(f"  페이지 {page}: {len(posts)}개 (누적 {len(all_posts)}개)")
    if len(posts) < 100:
        break
    page += 1
    time.sleep(0.3)

print(f"\n총 {len(all_posts)}개 글 조회 완료\n")

# ── 더미 판별 기준 ────────────────────────────────────────
def is_dummy(post):
    slug    = post.get("slug", "")
    title   = post.get("title", {})
    title_r = title.get("rendered", "") if isinstance(title, dict) else str(title)
    title_r = re.sub(r'<[^>]+>', '', title_r).strip()
    content = post.get("content", {})
    body    = content.get("rendered", "") if isinstance(content, dict) else ""
    body_plain = re.sub(r'<[^>]+>', '', body).strip()

    reasons = []

    # 1. post-숫자 슬러그
    if re.match(r'^post-\d+$', slug):
        reasons.append(f"더미슬러그(post-숫자): {slug}")

    # 2. 슬러그가 숫자만
    if re.match(r'^\d+$', slug):
        reasons.append(f"숫자슬러그: {slug}")

    # 3. 슬러그가 'post' 단독
    if slug in ('post', 'posts'):
        reasons.append(f"post 단독슬러그")

    # 4. 제목 없음 또는 'Auto Draft'
    if not title_r or title_r in ('Auto Draft', 'auto-draft', ''):
        reasons.append("제목없음")

    # 5. 본문 100자 미만
    if len(body_plain) < 100:
        reasons.append(f"본문너무짧음({len(body_plain)}자)")

    return reasons

# ── 분류 ─────────────────────────────────────────────────
dummy_posts  = []
normal_posts = []

for p in all_posts:
    reasons = is_dummy(p)
    if reasons:
        dummy_posts.append((p, reasons))
    else:
        normal_posts.append(p)

print(f"정상 글: {len(normal_posts)}개")
print(f"더미/문제 글: {len(dummy_posts)}개")
print()

# ── 더미 목록 출력 ────────────────────────────────────────
print("=== 삭제 대상 목록 ===")
for p, reasons in dummy_posts:
    pid   = p.get("id")
    slug  = p.get("slug","")
    title = p.get("title",{})
    title_r = title.get("rendered","") if isinstance(title,dict) else ""
    title_r = re.sub(r'<[^>]+>','',title_r).strip()[:40]
    status = p.get("status","")
    print(f"  [{pid}] slug={slug:20s} | title={title_r:30s} | {status} | 이유: {', '.join(reasons)}")

print()

# ── 영구 삭제 실행 ────────────────────────────────────────
print("=== 영구 삭제 실행 ===")
deleted  = 0
failed   = 0
skipped  = 0

for p, reasons in dummy_posts:
    pid    = p.get("id")
    slug   = p.get("slug","")
    status = p.get("status","")

    # 이미 trash 상태면 force=true로 완전 삭제
    # publish/draft 상태면 먼저 trash 후 완전 삭제
    try:
        r = requests.delete(
            f"{base}/posts/{pid}",
            auth=auth,
            params={"force": "true"},
            timeout=15
        )
        if r.status_code in (200, 201, 204, 410):
            print(f"  ✅ 삭제 [{pid}] {slug}")
            deleted += 1
        else:
            print(f"  ❌ 실패 [{pid}] {slug}: HTTP {r.status_code} {r.text[:80]}")
            failed += 1
    except Exception as e:
        print(f"  ⚠️ [{pid}] {e}")
        failed += 1
    time.sleep(0.3)

print()
print("=" * 60)
print(f"✅ 삭제 완료: {deleted}개")
print(f"❌ 실패: {failed}개")
print(f"정상 글 보존: {len(normal_posts)}개")
print("=" * 60)
