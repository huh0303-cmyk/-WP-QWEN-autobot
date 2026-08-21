#!/usr/bin/env python3
"""koreanews365.com의 현재 비공개(private) 글 중, (1) 과거 GSC 색인이 확인돼
protected_indexed_posts.json에 등록된 글, (2) estimate_seo_score >= 80인 글이
몇 개인지 집계한다. 읽기 전용, 아무것도 바꾸지 않음."""
import json
import os
import re
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autopost_mega import estimate_seo_score  # noqa: E402

SITE = "https://koreanews365.com"
USER = os.getenv("WP_USER", "").strip() or "huh0303@gmail.com"
PW = os.getenv("KOREANEWS365COM", "").strip()
PROTECTED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "data", "protected_indexed_posts.json")
SEO_THRESHOLD = 80


def fetch_private_posts():
    rows = []
    page = 1
    while True:
        r = requests.get(f"{SITE}/wp-json/wp/v2/posts", auth=(USER, PW), timeout=40,
                          params={"context": "edit", "status": "private", "per_page": 100, "page": page,
                                  "_fields": "id,date,slug,link,title,excerpt,content,categories,meta"})
        if r.status_code == 400 and "rest_post_invalid_page_number" in r.text:
            break
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if page >= int(r.headers.get("X-WP-TotalPages", "1")):
            break
        page += 1
    return rows


def main():
    if not PW:
        raise SystemExit("Missing KOREANEWS365COM secret")

    protected = set()
    try:
        with open(PROTECTED_PATH, encoding="utf-8") as f:
            protected = set(json.load(f).get("https://koreanews365.com", []))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    print(f"protected_indexed_posts.json 상 koreanews365 색인확인 ID {len(protected)}개")

    posts = fetch_private_posts()
    print(f"비공개 글 총 {len(posts)}개")

    indexed_and_private = []
    high_score = []
    for p in posts:
        pid = p["id"]
        title = p["title"]["raw"]
        body = p["content"]["raw"]
        meta = p.get("meta", {}) or {}
        desc = meta.get("rank_math_description", "") or ""
        kw = (meta.get("rank_math_focus_keyword", "") or "").split(",")[0]
        n_img = len(re.findall(r"<img[\s>]", body, re.IGNORECASE))
        faq = re.findall(r"<h3[^>]*>\s*Q[:.]?\s*(.*?)</h3>", body, re.IGNORECASE)
        score = estimate_seo_score(title, body, desc, ["x"] * 3, [(q, "a") for q in faq],
                                    ["x"] * n_img, kw)
        if pid in protected:
            indexed_and_private.append((pid, title, score))
        if score >= SEO_THRESHOLD:
            high_score.append((pid, title, score))

    print(f"\n=== 과거 구글색인 확인됐는데 지금 비공개인 글: {len(indexed_and_private)}개 ===")
    for pid, title, score in indexed_and_private:
        print(f"  [id={pid}, SEO{score}] {title}")

    print(f"\n=== SEO점수 {SEO_THRESHOLD}점 이상인 비공개 글: {len(high_score)}개 ===")
    for pid, title, score in sorted(high_score, key=lambda x: -x[2])[:40]:
        print(f"  [id={pid}, SEO{score}] {title}")
    if len(high_score) > 40:
        print(f"  ... 외 {len(high_score) - 40}건")

    overlap = set(x[0] for x in indexed_and_private) & set(x[0] for x in high_score)
    print(f"\n둘 다 해당(과거색인 + SEO80+): {len(overlap)}개")


if __name__ == "__main__":
    main()
