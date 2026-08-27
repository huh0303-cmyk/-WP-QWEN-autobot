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

from automation_hub.blogger_rewriter import attach_single_image, blogger_quality_score, find_one_free_image, image_is_relevant, parse_rewrite_json, rewrite_prompt
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
    target_chars = int(os.environ.get("BLOGGER_TARGET_CHARS", "1800"))
    maximum = float(os.environ.get("BLOGGER_MAX_SIMILARITY", "0.68"))
    minimum_quality = int(os.environ.get("BLOGGER_MIN_QUALITY_SCORE", "80"))
    rewritten = None
    quality_score = 0
    failures = []
    similarity_score = 1.0
    for attempt in range(1, 3):
        prompt = rewrite_prompt(source["title"]["rendered"], source["content"]["rendered"], source["link"], language=language, persona=os.environ.get("BLOGGER_PERSONA", "helpful specialist editor"), tone=os.environ.get("BLOGGER_TONE", "practical and clear"), target_chars=target_chars, prior_feedback="; ".join(failures))
        try:
            candidate = parse_rewrite_json(gemini_generate_text(prompt, temperature=0.7))
            quality_score, failures, similarity_score = blogger_quality_score(candidate, source_title=source["title"]["rendered"], source_url=source["link"], source_html=source["content"]["rendered"], target_chars=target_chars, maximum_similarity=maximum)
            print(json.dumps({"attempt": attempt, "quality_score": quality_score, "failures": failures}, ensure_ascii=False))
            if quality_score >= minimum_quality:
                rewritten = candidate
                break
        except Exception as exc:
            failures = [f"invalid output: {exc}"]
            print(json.dumps({"attempt": attempt, "quality_score": 0, "failures": failures}, ensure_ascii=False))
    if rewritten is None:
        raise RuntimeError(f"Blogger 품질점수 {quality_score}/100: 2회 모두 {minimum_quality}점 미만이므로 발행을 차단했습니다. {failures}")
    content = rewritten["content_html"]
    image_providers = []
    for query in rewritten["image_queries"]:
        image = find_one_free_image(query, pexels_key=os.environ.get("PEXELS_API_KEY", ""), pixabay_key=os.environ.get("PIXABAY_API_KEY", ""))
        if image is not None and image_is_relevant(image, query=query, title=rewritten["title"]) and image.url not in content:
            content = attach_single_image(content, image, rewritten["title"])
            image_providers.append(image.provider)
    job_id = f"blogger-rewrite-{uuid.uuid4().hex[:12]}"
    labels = rewritten.get("labels", [])
    if isinstance(labels, str):
        labels = [x.strip() for x in labels.split(",") if x.strip()]
    publish_now = os.environ.get("BLOGGER_PUBLISH_NOW", "false").strip().lower() in {"1", "true", "yes", "y", "on"}
    row = [iso_kst(), job_id, blogger_site_id, "ready", "TRUE" if publish_now else "FALSE", rewritten["title"], content, ",".join(labels[:5]), source["link"], "", "", "", f"quality_score={quality_score}; rewritten_similarity={similarity_score:.3f}; images={','.join(image_providers) or '0'}; meta_description={rewritten['meta_description']}", ""]
    service.spreadsheets().values().append(spreadsheetId=sheet_id, range=f"'{QUEUE_TAB}'!A1", valueInputOption="RAW", insertDataOption="INSERT_ROWS", body={"values": [row]}).execute()
    print(json.dumps({"queued": True, "job_id": job_id, "source": source["link"], "quality_score": quality_score, "similarity": round(similarity_score, 3), "image_count": len(image_providers), "meta_description": rewritten["meta_description"], "publish_now": publish_now, "text_provider": "gemini"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
