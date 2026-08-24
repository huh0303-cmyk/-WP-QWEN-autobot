#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resolve_duplicate_titles.py
─────────────────────────────────────────────────────────────
27개 사이트 전체 발행글 중 "중복 제목"(제목 앞 20자 기준, 공백/대소문자 무시)
글을 찾아, 같은 그룹 안에서 RankMath SEO 점수가 가장 낮은 것부터 삭제
대상으로 표시한다. 단, 사이트당 최소 MIN_KEEP_PER_SITE개는 항상 남긴다
(2026-08-03 사용자 지시: "최소 게시글 수 사이트당 15~20개 남겨줘").

읽기 전용(공개 REST 데이터만 사용) — 실제 삭제는 이 스크립트가 만든
duplicate_titles_manifest.json을 apply_duplicate_deletion.py가 읽어서
각 사이트 비밀번호로 수행한다 (조사/실행 분리 - image audit와 동일 패턴).
"""
import html as _html
import json
import re
import sys
import time

import requests

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SITES = [
    "https://k-health365.com", "https://koreamedicaltour.com", "https://koreainvest365.com",
    "https://ki-korea.com", "https://koreainsurance365.com", "https://kfinance365.com",
    "https://koreataxnlaw.com", "https://koreacrypto365.com", "https://krealestate365.com",
    "https://ktech365.com", "https://oliveyoungkorea.com",
    "https://kworld365.com", "https://k-trip365.com", "https://k-visa365.com",
    "https://koreawedding365.com", "https://kstudy365.com", "https://studyinkorea365.com",
    "https://kieca-korea.org", "https://ksa-korea.org", "https://sis-korea.com",
    "https://jobkorea365.com", "https://jobinkorea365.com", "https://jobkoreaglobal.com",
    "https://korea365.org", "https://koreanews365.com", "https://theseouljournal.com",
]

MIN_KEEP_PER_SITE = 15
MANIFEST_PATH = "duplicate_titles_manifest.json"


def strip_tags(s):
    return re.sub(r'<[^>]+>', '', s or '').strip()


def dup_key(title):
    return re.sub(r'\s+', '', title[:20].lower())


def fetch_all_posts(site_url):
    posts = []
    page = 1
    while True:
        try:
            r = requests.get(
                f"{site_url}/wp-json/wp/v2/posts",
                params={"per_page": 100, "page": page, "status": "publish",
                        "_fields": "id,title,link,date,meta"},
                timeout=25,
            )
        except Exception as e:
            print(f"  ⚠️ 요청 실패: {e}")
            break
        if r.status_code != 200:
            break
        try:
            batch = r.json()
        except Exception:
            break
        if not isinstance(batch, list) or not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        time.sleep(0.1)
    return posts


def main():
    manifest = []
    summary = {}

    for site_url in SITES:
        dom = site_url.replace("https://", "")
        posts = fetch_all_posts(site_url)
        if not posts:
            print(f"⚠️ {dom}: 조회 실패, 스킵")
            continue

        groups = {}
        for p in posts:
            title = strip_tags(_html.unescape(p.get("title", {}).get("rendered", "")))
            score = p.get("meta", {}).get("rank_math_seo_score") or 0
            try:
                score = int(score)
            except (TypeError, ValueError):
                score = 0
            key = dup_key(title)
            groups.setdefault(key, []).append({
                "id": p["id"], "title": title, "link": p.get("link", ""),
                "date": p.get("date", ""), "seo_score": score,
            })

        # 그룹 안에서 SEO 점수 가장 높은 것 1개만 남기고 나머지를 삭제 후보로
        candidates = []
        for key, items in groups.items():
            if len(items) < 2:
                continue
            items.sort(key=lambda x: (-x["seo_score"], x["date"]), reverse=False)
            # sort: 점수 높은 순(내림차순), 동점이면 날짜 무관 - 위에서 -score로 이미 처리
            items.sort(key=lambda x: -x["seo_score"])
            keep, drop = items[0], items[1:]
            candidates.extend(drop)

        # 최소 보유 개수 방어: 삭제 후보가 너무 많아 사이트 전체가 MIN_KEEP_PER_SITE
        # 밑으로 내려가면, 점수 낮은 순으로 자르지 않고 "삭제 후보 중 점수 높은 것부터"
        # 제외해서 사이트에 남는 글을 최소한 지킨다.
        total = len(posts)
        max_deletable = max(0, total - MIN_KEEP_PER_SITE)
        if len(candidates) > max_deletable:
            candidates.sort(key=lambda x: -x["seo_score"])  # 점수 높은 것부터 제외
            skipped = candidates[max_deletable:]
            candidates = candidates[:max_deletable]
            print(f"  ℹ️ {dom}: 최소 {MIN_KEEP_PER_SITE}개 보존을 위해 {len(skipped)}건은 삭제 대상에서 제외")

        for c in candidates:
            manifest.append({"site": site_url, "post_id": c["id"], "title": c["title"],
                              "link": c["link"], "seo_score": c["seo_score"]})

        summary[dom] = {"total_posts": total, "delete_candidates": len(candidates),
                          "remaining_after": total - len(candidates)}
        print(f"✅ {dom}: {total}건 중 중복 삭제후보 {len(candidates)}건 → 남는 글 {total - len(candidates)}건")

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    total_delete = len(manifest)
    print("\n" + "=" * 60)
    print(f"전체 삭제 후보: {total_delete}건 (최소 보유선 {MIN_KEEP_PER_SITE}개/사이트 적용됨)")
    print(f"매니페스트 저장: {MANIFEST_PATH}")
    with open("duplicate_titles_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
