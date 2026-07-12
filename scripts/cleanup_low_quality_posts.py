#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cleanup_low_quality_posts.py

k-health365.com (또는 지정 사이트)의 저품질/대량생산 글을 찾아서
정리(휴지통 이동 또는 영구삭제)하는 스크립트.

★ 안전장치: 기본값은 DRY_RUN = True 입니다.
   먼저 실행해서 삭제 대상 목록을 눈으로 확인한 뒤,
   확실할 때만 DRY_RUN = False 로 바꿔서 다시 실행하세요.

실행 위치: GitHub Actions (Hostinger WAF가 GitHub Actions IP는 막지 않음)
필요한 GitHub Secret: KHEALTH365COM (형식: "wp_username:application_password")
"""

import os
import re
import sys
import base64
import requests
from datetime import datetime, timedelta

# ============ 설정 (여기만 확인/수정) ============

SITE_URL = "https://k-health365.com"
SECRET_ENV_NAME = "KHEALTH365COM"   # GitHub Secret 이름 (기존 명명규칙 그대로)

DRY_RUN = True   # ★★★ True = 목록만 보여줌 (삭제 안 함) / False = 실제 삭제 실행

# 삭제 방식: "trash" (휴지통, 복구 가능) 권장 / "delete" (영구삭제, 복구 불가)
DELETE_MODE = "trash"

# 1) 제목 없이 자동 슬러그로 발행된 글 패턴 (post-63, post-115 등)
GENERIC_SLUG_PATTERN = re.compile(r"^post-\d+$")

# 2) 대량 몰아치기 발행 감지: 같은 날짜에 N초 이내로 연속 발행된 글들을
#    "burst 발행"으로 간주. 값이 클수록 더 많이 잡힘.
BURST_GAP_SECONDS = 120          # 같은 그룹으로 볼 발행 간격(초)
BURST_MIN_GROUP_SIZE = 15        # 이 개수 이상 몰려있으면 "대량 몰아치기"로 판단

# 3) (선택) 특정 기간 통째로 정리하고 싶으면 여기에 직접 지정
#    예: "2026-07-01" 하루 전체를 강제로 검토 대상에 포함
FORCE_INCLUDE_DATE_RANGE = None
# FORCE_INCLUDE_DATE_RANGE = ("2026-07-01T00:00:00", "2026-07-01T23:59:59")

# 4) 유지할 카테고리 slug (여기 없는 카테고리 글은 별도로만 "참고 표시", 자동삭제는 안 함)
KEEP_CATEGORY_SLUGS = {"health-info", "health-supplements", "health-functional-food"}

# ================================================


def get_auth_header():
    cred = os.environ.get(SECRET_ENV_NAME)
    if not cred:
        print(f"[오류] 환경변수 {SECRET_ENV_NAME} 이(가) 없습니다. "
              f"GitHub Actions Secrets에 등록되어 있는지 확인하세요.")
        sys.exit(1)
    token = base64.b64encode(cred.encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {token}"}


def fetch_all_posts(headers):
    """전체 게시물을 페이지네이션으로 모두 가져옴 (기본 status만; 필요시 draft 포함 가능)"""
    posts = []
    page = 1
    per_page = 100
    while True:
        url = f"{SITE_URL}/wp-json/wp/v2/posts"
        params = {"per_page": per_page, "page": page, "orderby": "date", "order": "asc",
                  "_fields": "id,date,slug,title,link,categories,content"}
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code == 400:
            # 마지막 페이지를 넘어가면 400이 오는 경우가 있음
            break
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        posts.extend(batch)
        total_pages = int(resp.headers.get("X-WP-TotalPages", "1"))
        if page >= total_pages:
            break
        page += 1
    return posts


def fetch_categories(headers):
    url = f"{SITE_URL}/wp-json/wp/v2/categories"
    params = {"per_page": 100}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    cat_map = {}
    for c in resp.json():
        cat_map[c["id"]] = c["slug"]
    return cat_map


def detect_burst_groups(posts):
    """발행시각 기준 정렬 후, 짧은 간격으로 몰려있는 그룹을 찾아냄"""
    parsed = []
    for p in posts:
        try:
            dt = datetime.fromisoformat(p["date"])
        except Exception:
            continue
        parsed.append((dt, p))
    parsed.sort(key=lambda x: x[0])

    burst_ids = set()
    group = []

    def flush_group():
        if len(group) >= BURST_MIN_GROUP_SIZE:
            for _, gp in group:
                burst_ids.add(gp["id"])

    prev_dt = None
    for dt, p in parsed:
        if prev_dt is None or (dt - prev_dt) <= timedelta(seconds=BURST_GAP_SECONDS):
            group.append((dt, p))
        else:
            flush_group()
            group = [(dt, p)]
        prev_dt = dt
    flush_group()

    return burst_ids


def is_generic_slug(post):
    return bool(GENERIC_SLUG_PATTERN.match(post.get("slug", "")))


def is_thin_content(post, min_chars=300):
    content_html = post.get("content", {}).get("rendered", "")
    text_only = re.sub(r"<[^>]+>", "", content_html).strip()
    return len(text_only) < min_chars


def in_forced_range(post):
    if not FORCE_INCLUDE_DATE_RANGE:
        return False
    start, end = FORCE_INCLUDE_DATE_RANGE
    return start <= post["date"] <= end


def main():
    headers = get_auth_header()

    print(f"[1/4] {SITE_URL} 카테고리 목록 조회 중...")
    cat_map = fetch_categories(headers)

    print(f"[2/4] {SITE_URL} 전체 게시물 조회 중... (시간이 걸릴 수 있습니다)")
    posts = fetch_all_posts(headers)
    print(f"      총 {len(posts)}개 게시물 확인됨")

    print(f"[3/4] 대량 몰아치기(burst) 발행 그룹 탐지 중 "
          f"(간격 {BURST_GAP_SECONDS}초 이내, {BURST_MIN_GROUP_SIZE}개 이상)...")
    burst_ids = detect_burst_groups(posts)
    print(f"      burst 발행으로 감지된 게시물: {len(burst_ids)}개")

    candidates = []
    for p in posts:
        reasons = []
        if is_generic_slug(p):
            reasons.append("제목없음(자동슬러그)")
        if p["id"] in burst_ids:
            reasons.append("대량몰아치기발행")
        if is_thin_content(p):
            reasons.append("본문분량부족(<300자)")
        if in_forced_range(p):
            reasons.append("지정기간강제포함")

        if reasons:
            title = p.get("title", {}).get("rendered", "(제목없음)")
            candidates.append({
                "id": p["id"],
                "title": title,
                "slug": p["slug"],
                "date": p["date"],
                "link": p["link"],
                "reasons": reasons,
            })

    print(f"\n[4/4] 삭제 후보: 총 {len(candidates)}개 / 전체 {len(posts)}개\n")
    print("=" * 100)
    for c in candidates:
        print(f"ID {c['id']:>6} | {c['date']} | {', '.join(c['reasons']):<30} | {c['title'][:50]}")
        print(f"           └─ {c['link']}")
    print("=" * 100)

    if not candidates:
        print("\n삭제 대상이 없습니다. 조건을 조정해보세요.")
        return

    if DRY_RUN:
        print(f"\n★ DRY RUN 모드입니다. 실제로 삭제되지 않았습니다.")
        print(f"★ 위 목록을 확인 후, 스크립트 상단의 DRY_RUN = False 로 바꿔서 다시 실행하면")
        print(f"★ '{DELETE_MODE}' 방식으로 {len(candidates)}개 게시물이 처리됩니다.")
        return

    print(f"\n실제 삭제를 시작합니다 (모드: {DELETE_MODE})...")
    force = (DELETE_MODE == "delete")
    success, fail = 0, 0
    for c in candidates:
        url = f"{SITE_URL}/wp-json/wp/v2/posts/{c['id']}"
        params = {"force": "true"} if force else {}
        resp = requests.delete(url, headers=headers, params=params, timeout=30)
        if resp.status_code in (200, 201):
            success += 1
            print(f"  ✓ 처리완료: ID {c['id']} - {c['title'][:40]}")
        else:
            fail += 1
            print(f"  ✗ 실패: ID {c['id']} - status {resp.status_code} - {resp.text[:200]}")

    print(f"\n완료: 성공 {success}개, 실패 {fail}개")


if __name__ == "__main__":
    main()
