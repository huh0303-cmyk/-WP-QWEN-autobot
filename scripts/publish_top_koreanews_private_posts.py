#!/usr/bin/env python3
"""비공개(private) 상태인 koreanews365.com 글들을 SEO 잠재력 기준으로 채점해서
상위 N개를 공개(publish)로 전환한다. 사용자 지시(2026-08-21)로 1회성 실행."""
import json
import os
import re
import sys

import requests

USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PW = os.getenv("KOREANEWS365COM", "").strip()
BASE = "https://koreanews365.com/wp-json/wp/v2"
TOP_N = int(sys.argv[1]) if len(sys.argv) > 1 else 30


def fetch_private_posts():
    rows = []
    page = 1
    while True:
        r = requests.get(
            f"{BASE}/posts", auth=(USER, PW), timeout=40,
            params={"context": "edit", "status": "private", "per_page": 100, "page": page,
                    "_fields": "id,date,slug,link,title,excerpt,content,categories"},
        )
        if r.status_code == 400 and "rest_post_invalid_page_number" in r.text:
            break
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if page >= int(r.headers.get("X-WP-TotalPages", "1")):
            break
        page += 1
    return rows


def strip_tags(html):
    return re.sub(r"<[^>]+>", " ", html or "")


def score_post(p):
    title = p["title"]["raw"]
    content_text = strip_tags(p["content"]["raw"])
    word_count = len(content_text.split())

    # 1) 콘텐츠 깊이 (최대 40점) — 너무 짧은 글(스팸/썸네일용)은 SEO에 불리
    depth_score = min(word_count / 15, 40)

    # 2) 제목 길이 (최대 20점) — 너무 짧거나(<15자) 너무 길면(>70자) 감점
    tlen = len(title)
    if 20 <= tlen <= 60:
        title_score = 20
    elif 15 <= tlen < 20 or 60 < tlen <= 70:
        title_score = 12
    else:
        title_score = 4

    # 3) 카테고리 분류 여부 (10점) — 미분류 글은 사이트 구조상 불리
    cat_score = 10 if p.get("categories") else 0

    # 4) 제목에 연도/구체적 고유명사 존재 여부(간이 휴리스틱, 10점) —
    #    "속보", "오늘의" 같은 뻔한 제목보다 구체적 주제가 검색엔진에 유리
    specific_score = 10 if re.search(r"[0-9]{2,4}|[A-Z][a-z]{2,}", title) else 3

    return round(depth_score + title_score + cat_score + specific_score, 1), word_count


def main():
    if not PW:
        print("ERROR: KOREANEWS365COM 환경변수(앱 비밀번호) 없음", file=sys.stderr)
        sys.exit(1)

    posts = fetch_private_posts()
    print(f"비공개 글 총 {len(posts)}개 발견")

    scored = []
    for p in posts:
        s, wc = score_post(p)
        scored.append({"id": p["id"], "title": p["title"]["raw"], "score": s,
                        "word_count": wc, "link": p["link"]})
    scored.sort(key=lambda x: x["score"], reverse=True)

    top = scored[:TOP_N]
    print(f"\n상위 {len(top)}개 공개 전환 대상:")
    for t in top:
        print(f"  [{t['score']:5.1f}점, {t['word_count']:4d}단어] {t['title']}")

    results = []
    for t in top:
        r = requests.post(f"{BASE}/posts/{t['id']}", auth=(USER, PW), timeout=30,
                           json={"status": "publish"})
        ok = r.status_code == 200
        results.append({"id": t["id"], "title": t["title"], "ok": ok,
                         "status_code": r.status_code})
        print(f"  {'OK' if ok else 'FAIL'} ({r.status_code}) - {t['title']}")

    succeeded = sum(1 for x in results if x["ok"])
    print(f"\n완료: {succeeded}/{len(top)}개 공개 전환 성공")

    with open("koreanews_publish_result.json", "w", encoding="utf-8") as f:
        json.dump({"target_count": TOP_N, "candidates_scored": len(scored),
                    "published": results, "all_scored": scored},
                   f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
