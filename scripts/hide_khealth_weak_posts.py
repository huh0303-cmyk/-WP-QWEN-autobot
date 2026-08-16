#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hide_khealth_weak_posts.py
─────────────────────────────────────────────────────────────
k-health365.com 전체 246개 글을 SEO 점수(estimate_seo_score)+AI티 문구+
제목 반복패턴 기준으로 스캔해서, 약한 글(73개, 2026-08-17 스캔 기준)을
비공개(private) 전환한다 — 삭제 아님, 언제든 복구 가능.

기본값은 DRY RUN(리포트만). --execute를 줘야 실제로 비공개 전환.

사용법:
    python scripts/hide_khealth_weak_posts.py           # 리포트만
    python scripts/hide_khealth_weak_posts.py --execute # 실제 전환
"""
import os
import re
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests  # noqa: E402
from autopost_mega import estimate_seo_score, WP_USER  # noqa: E402

SITE = "https://k-health365.com"
CLICHE_RE = re.compile(
    r'complete guide to|ultimate guide|everything you need to know|'
    r'top \d+ (?:reasons|tips|ways|things)|총정리|완벽\s*가이드|완벽\s*정리|'
    r'모든\s*것을\s*알아|현대\s*사회에서|충격적인 사실|알고 계셨나요|궁금증을 모두 해소',
    re.IGNORECASE,
)
SEO_THRESHOLD = 60


def log(msg):
    print(msg, flush=True)


def fetch_all_posts():
    all_posts = []
    page = 1
    while True:
        r = requests.get(f"{SITE}/wp-json/wp/v2/posts",
                          params={"per_page": 100, "page": page,
                                  "_fields": "id,date,slug,link,content,title,meta"},
                          timeout=30)
        if r.status_code != 200:
            break
        posts = r.json()
        if not posts:
            break
        all_posts.extend(posts)
        page += 1
        if page > 5:
            break
    return all_posts


def scan(posts):
    title_words_counter = {}
    results = []
    for p in posts:
        title = p["title"]["rendered"]
        body = p["content"]["rendered"]
        meta = p.get("meta", {}) or {}
        desc = meta.get("rank_math_description", "") or ""
        kw = meta.get("rank_math_focus_keyword", "") or ""
        kw0 = kw.split(",")[0] if kw else ""
        plain = re.sub(r"<[^>]+>", "", body)
        n_img = len(re.findall(r"<img[\s>]", body, re.IGNORECASE))
        faq = [(q, "a") for q in re.findall(r"<h3[^>]*>\s*Q[:.]?\s*(.*?)</h3>", body, re.IGNORECASE)]
        score = estimate_seo_score(title, body, desc, ["x"] * 3, faq, ["x"] * n_img, kw0)
        ai_tell = bool(CLICHE_RE.search(title)) or bool(CLICHE_RE.search(plain[:2000]))
        key = " ".join(re.sub(r"<[^>]+>", "", title).split()[:2]).lower()
        title_words_counter[key] = title_words_counter.get(key, 0) + 1
        results.append({"id": p["id"], "title": re.sub(r"<[^>]+>", "", title), "slug": p["slug"],
                         "score": score, "ai_tell": ai_tell, "title_key": key, "link": p["link"]})
    for r in results:
        r["dup_title_pattern"] = title_words_counter[r["title_key"]] >= 3
    return results


def main():
    execute = "--execute" in sys.argv
    pw = os.environ.get("KHEALTH365COM", "")
    if not pw:
        log("❌ KHEALTH365COM 비밀번호 없음")
        raise SystemExit(1)

    log("1/2 246개 글 스캔 중...")
    posts = fetch_all_posts()
    results = scan(posts)
    targets = [r for r in results if r["score"] < SEO_THRESHOLD or r["ai_tell"] or r["dup_title_pattern"]]
    log(f"   전체 {len(results)}개 중 대상 {len(targets)}개")

    if not execute:
        log("\n🔍 DRY RUN — 아무것도 안 바뀜. --execute로 실제 전환.")
        for r in targets:
            log(f"   {r['score']:3}점 | id={r['id']} | {r['title'][:40]}")
        return

    log(f"2/2 {len(targets)}개 글 비공개 전환 중...")
    ok = fail = 0
    for r in targets:
        try:
            resp = requests.post(f"{SITE}/wp-json/wp/v2/posts/{r['id']}",
                                  auth=(WP_USER, pw), json={"status": "private"}, timeout=20)
            if resp.status_code in (200, 201):
                ok += 1
                log(f"   ✅ {r['id']} {r['title'][:30]}")
            else:
                fail += 1
                log(f"   ❌ {r['id']}: {resp.status_code}")
        except Exception as e:
            fail += 1
            log(f"   ❌ {r['id']}: {e}")

    log(f"\n✅ 완료 — 성공:{ok} / 실패:{fail}")


if __name__ == "__main__":
    main()
