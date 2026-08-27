#!/usr/bin/env python3
"""Rewrite one verified WordPress post with Gemini and queue it for Blogger."""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from automation_hub.blogger_rewriter import attach_single_image, find_one_free_image, parse_rewrite_json, rewrite_prompt, similarity
from automation_hub.time_utils import iso_kst
from gsheets_direct import get_sheets_service
from gemini_text import gemini_generate_text
from sync_automation_hub_to_sheets import QUEUE_TAB


def main():
    sheet_id = os.environ.get("SHEET_ID", "").strip()
    source_url = os.environ.get("SOURCE_WP_URL", "").rstrip("/")
    blogger_site_id = os.environ.get("BLOGGER_SITE_ID", "").strip()
    if not all((sheet_id, source_url, blogger_site_id)):
        raise SystemExit("SHEET_ID, SOURCE_WP_URL and BLOGGER_SITE_ID are required")
    posts = requests.get(f"{source_url}/wp-json/wp/v2/posts", params={"status": "publish", "per_page": 10, "orderby": "date", "order": "desc"}, timeout=30)
    posts.raise_for_status()
    service = get_sheets_service()
    existing = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"'{QUEUE_TAB}'!A1:N").execute().get("values", [])
    used_sources = {row[8] for row in existing[1:] if len(row) > 8}
    source = next((post for post in posts.json() if post.get("link") not in used_sources), None)
    if not source:
        print("새로운 WordPress 원문이 없습니다.")
        return 0
    language = os.environ.get("BLOGGER_LANGUAGE", "en").strip().lower()
    korean_source_hosts = {"koreanews365.com", "www.koreanews365.com", "k-health365.com", "www.k-health365.com"}
    source_host = requests.utils.urlparse(source_url).netloc.lower()
    if language == "ko" and source_host not in korean_source_hosts:
        raise RuntimeError("Korean Blogger output is allowed only for koreanews365.com and K-health365.com")
    prompt = rewrite_prompt(source["title"]["rendered"], source["content"]["rendered"], source["link"], language=language, persona=os.environ.get("BLOGGER_PERSONA", "helpful specialist editor"), tone=os.environ.get("BLOGGER_TONE", "practical and clear"), target_chars=int(os.environ.get("BLOGGER_TARGET_CHARS", "1800")))
    rewritten = parse_rewrite_json(gemini_generate_text(prompt, temperature=0.7))
    score = similarity(source["content"]["rendered"], rewritten["content_html"])
    maximum = float(os.environ.get("BLOGGER_MAX_SIMILARITY", "0.68"))
    if score > maximum:
        raise RuntimeError(f"재작성 유사도 {score:.3f}가 제한 {maximum:.3f}보다 높아 발행을 차단했습니다.")
    content = rewritten["content_html"]
    image_providers = []
    for query in rewritten["image_queries"]:
        image = find_one_free_image(query, pexels_key=os.environ.get("PEXELS_API_KEY", ""), pixabay_key=os.environ.get("PIXABAY_API_KEY", ""))
        if image is not None and image.url not in content:
            content = attach_single_image(content, image, rewritten["title"])
            image_providers.append(image.provider)
    job_id = f"blogger-rewrite-{uuid.uuid4().hex[:12]}"
    labels = rewritten.get("labels", [])
    if isinstance(labels, str):
        labels = [x.strip() for x in labels.split(",") if x.strip()]
    publish_now = os.environ.get("BLOGGER_PUBLISH_NOW", "false").strip().lower() in {"1", "true", "yes", "y", "on"}
    row = [iso_kst(), job_id, blogger_site_id, "ready", "TRUE" if publish_now else "FALSE", rewritten["title"], content, ",".join(labels[:5]), source["link"], "", "", "", f"rewritten_similarity={score:.3f}; images={','.join(image_providers) or '0'}; meta_description={rewritten['meta_description']}", ""]
    service.spreadsheets().values().append(spreadsheetId=sheet_id, range=f"'{QUEUE_TAB}'!A1", valueInputOption="RAW", insertDataOption="INSERT_ROWS", body={"values": [row]}).execute()
    print(json.dumps({"queued": True, "job_id": job_id, "source": source["link"], "similarity": round(score, 3), "image_count": len(image_providers), "meta_description": rewritten["meta_description"], "publish_now": publish_now, "text_provider": "gemini"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
