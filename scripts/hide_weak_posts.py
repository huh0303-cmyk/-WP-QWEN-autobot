#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hide_weak_posts.py
─────────────────────────────────────────────────────────────
2026-08-17 "대수술" 지시: 27개 사이트 전체를 SEO 점수(estimate_seo_score)
+ AI 흔적 문구(cleanup_ai_toned_posts.py의 AI_TELL_RE) + 제목 반복패턴
기준으로 스캔해서, 다음 중 하나라도 해당하면 무조건 비공개(private) 전환:
  - SEO 점수 < SEO_THRESHOLD(80)
  - AI 티 문구 1개 이상 검출
  - 같은 제목 앞 2단어가 3회 이상 반복(대량생산 패턴)

2026-08-17 추가 정정: 사용자 확인 — "저품질 기준에 걸려도 이미 구글에 색인된
글은 남겨둬야지". scripts/data/protected_indexed_posts.json에 있는 글 ID는
cleanup_ai_toned_posts.py가 실제 GSC urlInspection API로 확인해 "색인됨"이라고
검증한 것들 — 점수/AI티가 뭐가 나오든 이 목록에 있으면 절대 비공개 전환 안 함.
이 파일이 아직 없는 사이트는 보호 목록이 비어 있으므로(=색인 확인을 아직
못한 사이트) 기존처럼 점수/AI티 기준만으로 판단한다.

사용법:
    python scripts/hide_weak_posts.py [--site=<url>] [--offset=N] [--limit=N] [--execute]
    (사이트 미지정이면 27개 전체)
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests  # noqa: E402
from autopost_mega import estimate_seo_score, WP_USER  # noqa: E402
from cleanup_ai_toned_posts import (  # noqa: E402
    SITE_SECRET_MAP, AI_TELL_RE, HEADING_QUESTION_RE, score_ai_tell,
)

SEO_THRESHOLD = 80
PROTECTED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "data", "protected_indexed_posts.json")


def load_protected():
    try:
        with open(PROTECTED_PATH, encoding="utf-8") as f:
            return {site: set(ids) for site, ids in json.load(f).items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def log(msg):
    print(msg, flush=True)


def fetch_all_posts(site):
    all_posts = []
    page = 1
    while True:
        r = requests.get(f"{site}/wp-json/wp/v2/posts",
                          params={"per_page": 100, "page": page, "status": "publish",
                                  "_fields": "id,date,slug,link,content,title,meta"},
                          timeout=30)
        if r.status_code != 200:
            break
        posts = r.json()
        if not posts:
            break
        all_posts.extend(posts)
        page += 1
        if page > 20:
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
        signals, hits, heading_hits = score_ai_tell(re.sub(r"<[^>]+>", "", title), body)
        ai_tell = signals >= 1
        key = " ".join(re.sub(r"<[^>]+>", "", title).split()[:2]).lower()
        title_words_counter[key] = title_words_counter.get(key, 0) + 1
        results.append({"id": p["id"], "title": re.sub(r"<[^>]+>", "", title), "slug": p["slug"],
                         "score": score, "ai_tell": ai_tell, "ai_hits": hits,
                         "title_key": key, "link": p["link"]})
    for r in results:
        r["dup_title_pattern"] = title_words_counter[r["title_key"]] >= 3
    return results


def process_site(site_url, pw_env, execute, protected):
    pw = os.environ.get(pw_env, "")
    if not pw:
        log(f"⏭  {site_url} — 비밀번호 없음(secret {pw_env}), 스킵")
        return 0, 0

    log(f"🌐 {site_url}")
    posts = fetch_all_posts(site_url)
    results = scan(posts)
    site_protected = protected.get(site_url, set())
    candidates = [r for r in results if r["score"] < SEO_THRESHOLD or r["ai_tell"] or r["dup_title_pattern"]]
    targets = [r for r in candidates if r["id"] not in site_protected]
    n_protected_skipped = len(candidates) - len(targets)
    log(f"   전체 {len(results)}개 중 대상 {len(targets)}개 "
        f"(SEO<{SEO_THRESHOLD} 또는 AI티 또는 제목반복"
        + (f", 색인확인돼서 보호한 {n_protected_skipped}개 제외" if site_protected else "") + ")")
    for r in targets[:8]:
        reason = []
        if r["score"] < SEO_THRESHOLD:
            reason.append(f"SEO{r['score']}")
        if r["ai_tell"]:
            reason.append(f"AI티{r['ai_hits'][:2]}")
        if r["dup_title_pattern"]:
            reason.append("반복제목")
        log(f"      [{'/'.join(reason)}] {r['title'][:45]}")
    if len(targets) > 8:
        log(f"      ... 외 {len(targets) - 8}건")

    if not execute:
        log("")
        return len(results), len(targets)

    ok = fail = 0
    for r in targets:
        try:
            resp = requests.post(f"{site_url}/wp-json/wp/v2/posts/{r['id']}",
                                  auth=(WP_USER, pw), json={"status": "private"}, timeout=20)
            if resp.status_code in (200, 201):
                ok += 1
            else:
                fail += 1
                log(f"      ❌ {r['id']}: HTTP {resp.status_code}")
        except Exception as e:
            fail += 1
            log(f"      ❌ {r['id']}: {e}")
    log(f"   → 비공개 전환 성공:{ok} / 실패:{fail}\n")
    return len(results), len(targets)


def main():
    execute = "--execute" in sys.argv
    only_site = None
    offset = None
    limit = None
    for a in sys.argv[1:]:
        if a.startswith("--site="):
            only_site = a.split("=", 1)[1]
        elif a.startswith("--offset="):
            offset = int(a.split("=", 1)[1])
        elif a.startswith("--limit="):
            limit = int(a.split("=", 1)[1])

    site_items = list(SITE_SECRET_MAP.items())
    if only_site:
        needles = [s.strip() for s in only_site.split(",") if s.strip()]
        site_items = [(u, s) for u, s in site_items if any(n in u for n in needles)]
        if not site_items:
            log(f"❌ 알 수 없는 site: {only_site}")
            raise SystemExit(1)
    elif offset is not None or limit is not None:
        start = offset or 0
        end = start + limit if limit is not None else len(site_items)
        site_items = site_items[start:end]
        log(f"📦 배치 모드: 사이트 {start}~{end - 1}번째만 처리 ({len(site_items)}개)")

    protected = load_protected()

    mode = "실행(비공개 전환)" if execute else "리포트만(DRY RUN)"
    log(f"{'=' * 60}")
    log(f"🔍 저품질 글 정리 — SEO<{SEO_THRESHOLD} 또는 AI흔적 또는 제목반복 → 무조건 비공개 "
        f"(단, 색인 확인된 글은 보호) — {mode}")
    log(f"{'=' * 60}\n")

    total_posts = total_targets = 0
    for site_url, pw_env in site_items:
        try:
            n_posts, n_targets = process_site(site_url, pw_env, execute, protected)
        except Exception as e:
            log(f"   ⚠️ {site_url} 처리 중 오류(스킵하고 계속): {e}\n")
            continue
        total_posts += n_posts
        total_targets += n_targets

    log(f"{'=' * 60}")
    log(f"✅ 완료 — 조사 {total_posts}건 / 대상(비공개 전환 {'완료' if execute else '예정'}) {total_targets}건")
    if not execute:
        log("   DRY RUN — 아무것도 안 바뀜. --execute로 실제 전환.")
    log(f"{'=' * 60}")


if __name__ == "__main__":
    main()
