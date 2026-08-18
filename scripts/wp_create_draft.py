#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wp_create_draft.py
─────────────────────────────────────────────────────────────
Gemini Gem이 만든 6개 항목(제목/본문/태그/메타디스크립션/포커스키워드)을
받아서 해당 사이트에 "초안(draft)" 상태로 글을 등록한다. 발행은 사람이
WP 관리자 화면에서 직접 누른다 — 이 스크립트는 절대 자동 발행하지 않는다.

사용법:
    python scripts/wp_create_draft.py <site_url> <title_file> <body_file> <tags_file> <meta_file> <focus_kw_file>

환경변수:
    WP_APP_PASSWORD  — 해당 사이트 REST 쓰기 권한 앱 비밀번호
    WP_USER          — 기본값 huh0303@gmail.com
"""
import os
import sys
import requests

WP_USER = os.environ.get("WP_USER", "huh0303@gmail.com")


def log(msg):
    print(msg, flush=True)


def get_or_create_tag(site, name, auth):
    r = requests.get(f"{site}/wp-json/wp/v2/tags", auth=auth,
                      params={"search": name, "per_page": 10}, timeout=20)
    r.raise_for_status()
    for t in r.json():
        if t["name"].strip().lower() == name.strip().lower():
            return t["id"]
    r = requests.post(f"{site}/wp-json/wp/v2/tags", auth=auth,
                       json={"name": name}, timeout=20)
    r.raise_for_status()
    return r.json()["id"]


def markdown_headings_to_html(text):
    """## / ### 마크다운 헤딩만 최소 변환 (Gem 출력이 마크다운이라 WP 블록에 그대로
    넣으면 ##이 텍스트로 보임 — 워드프레스 클래식 에디터 기준 <h2>/<h3>로 치환)."""
    lines = text.split("\n")
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### "):
            out.append(f"<h3>{stripped[4:]}</h3>")
        elif stripped.startswith("## "):
            out.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("- "):
            out.append(f"<li>{stripped[2:]}</li>")
        elif stripped:
            out.append(f"<p>{stripped}</p>")
    return "\n".join(out)


def main():
    site = sys.argv[1].rstrip("/")
    title = open(sys.argv[2], encoding="utf-8").read().strip()
    body_raw = open(sys.argv[3], encoding="utf-8").read().strip()
    tags_raw = open(sys.argv[4], encoding="utf-8").read().strip()
    meta_desc = open(sys.argv[5], encoding="utf-8").read().strip()
    focus_kw = open(sys.argv[6], encoding="utf-8").read().strip()

    pw = os.environ.get("WP_APP_PASSWORD")
    if not pw:
        log("❌ WP_APP_PASSWORD 없음")
        raise SystemExit(1)
    auth = requests.auth.HTTPBasicAuth(WP_USER, pw)

    body_html = markdown_headings_to_html(body_raw)

    tag_names = [t.strip() for t in tags_raw.split(",") if t.strip()]
    tag_ids = [get_or_create_tag(site, name, auth) for name in tag_names]
    log(f"   태그 {len(tag_ids)}개 확보")

    payload = {
        "title": title,
        "content": body_html,
        "status": "draft",
        "tags": tag_ids,
        "meta": {
            "rank_math_description": meta_desc,
            "rank_math_focus_keyword": focus_kw,
        },
    }
    r = requests.post(f"{site}/wp-json/wp/v2/posts", auth=auth, json=payload, timeout=30)
    r.raise_for_status()
    post = r.json()
    log(f"✅ 초안 등록 완료: #{post['id']} — {post['link']}")
    log(f"   편집 화면: {site}/wp-admin/post.php?post={post['id']}&action=edit")


if __name__ == "__main__":
    main()
