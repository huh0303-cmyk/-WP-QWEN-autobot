#!/usr/bin/env python3
"""Repair K-Health365 draft 5927 without changing its publication status."""
from __future__ import annotations

import json
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(__file__))
from create_manual_wp_draft import WP_USER, ensure_featured_media  # noqa: E402
from replicate_image_provider import generate_image_url  # noqa: E402

SITE = "https://k-health365.com"
POST_ID = 5927
FOCUS_KEYWORD = "정기 건강검진"


def main() -> int:
    password = os.environ.get("KHEALTH365COM", "").strip()
    if not password:
        raise SystemExit("KHEALTH365COM is missing")
    endpoint = f"{SITE}/wp-json/wp/v2/posts/{POST_ID}"
    before = requests.get(endpoint, auth=(WP_USER, password), params={
        "context": "edit", "_fields": "id,status,title,featured_media,meta"
    }, timeout=30)
    before.raise_for_status()
    post = before.json()
    original_status = post["status"]
    title = post["title"]["rendered"]
    media_id = int(post.get("featured_media") or 0)
    image_url = ""
    if not media_id:
        image_url = generate_image_url(
            "Korean adult preparing a concise health screening question checklist at home, calm natural light, stethoscope nearby, no text, no logos",
            theme="정기 건강검진 질문 준비 건강정보",
        ) or ""
        if not image_url:
            raise SystemExit("approved image chain failed; draft left unchanged")
        media_id = ensure_featured_media(SITE, password, image_url, title)
        if not media_id:
            raise SystemExit("WordPress media upload failed; draft left unchanged")
    patch = {
        "featured_media": media_id,
        "meta": {
            "rank_math_focus_keyword": FOCUS_KEYWORD,
            "rank_math_description": "정기 건강검진 전 꼭 준비할 질문과 검진 결과 확인법, 의료진 상담 시 놓치지 말아야 할 핵심 사항을 단계별로 정리합니다.",
        },
    }
    saved = requests.post(endpoint, auth=(WP_USER, password), json=patch, timeout=30)
    saved.raise_for_status()
    verify = requests.get(endpoint, auth=(WP_USER, password), params={
        "context": "edit", "_fields": "id,status,featured_media,meta"
    }, timeout=30)
    verify.raise_for_status()
    actual = verify.json()
    ok = (
        actual["status"] == original_status
        and int(actual.get("featured_media") or 0) == media_id
        and str((actual.get("meta") or {}).get("rank_math_focus_keyword") or "") == FOCUS_KEYWORD
    )
    result = {
        "ok": ok, "post_id": POST_ID, "status_preserved": actual["status"],
        "featured_media": media_id, "focus_keyword": (actual.get("meta") or {}).get("rank_math_focus_keyword", ""),
        "image_generated": bool(image_url), "edit_url": f"{SITE}/wp-admin/post.php?post={POST_ID}&action=edit",
    }
    with open("wp_post_5927_repair_result.json", "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
