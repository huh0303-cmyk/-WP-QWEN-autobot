#!/usr/bin/env python3
"""Rewrite one verified WordPress post with Gemini and queue it for Blogger.

Text policy: Blogger = Gemini only.
Image policy: Replicate approved 3-model gateway only; one image maximum.
"""
from __future__ import annotations

import html
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

from automation_hub.blogger_rewriter import blogger_quality_score, normalize_rewrite_format, parse_rewrite_json, rewrite_prompt
from automation_hub.time_utils import iso_kst
from gsheets_direct import get_sheets_service
from gemini_text import gemini_generate_text
from replicate_image_provider import generate_image_url
from sync_automation_hub_to_sheets import QUEUE_TAB


def _attach_replicate_image(content: str, image_url: str, title: str) -> str:
    safe_url = html.escape(image_url, quote=True)
    safe_alt = html.escape(title, quote=True)
    figure = (
        f'<figure class="blogger-replicate-image">'
        f'<img src="{safe_url}" alt="{safe_alt}" loading="lazy" />'
        f'</figure>'
    )
    return figure + content


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
    used_sources = {row[8] for row in existing[1:] if len(row) > 8 and len(row) > 3 and row[3] in {"ready", "drafted", "published"}}
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
    ymyl = any(word in (source["title"]["rendered"] + " " + source_url).lower() for word in ("visa", "immigration", "insurance", "medical", "hospital", "treatment"))
    rewritten = None
    quality_score = 0
    failures = []
    similarity_score = 1.0
    for attempt in range(1, 3):
        prompt = rewrite_prompt(source["title"]["rendered"], source["content"]["rendered"], source["link"], language=language, persona=os.environ.get("BLOGGER_PERSONA", "helpful specialist editor"), tone=os.environ.get("BLOGGER_TONE", "practical and clear"), target_chars=target_chars, prior_feedback="; ".join(failures))
        try:
            candidate = parse_rewrite_json(gemini_generate_text(prompt, temperature=0.7))
            candidate = normalize_rewrite_format(candidate, target_chars=target_chars, source_url=source["link"], ymyl=ymyl)
            quality_score, failures, similarity_score = blogger_quality_score(candidate, source_title=source["title"]["rendered"], source_url=source["link"], source_html=source["content"]["rendered"], target_chars=target_chars, maximum_similarity=maximum)
            print(json.dumps({"attempt": attempt, "quality_score": quality_score, "failures": failures}, ensure_ascii=False))
            critical_failures = [failure for failure in failures if failure.startswith(("body length", "verified WordPress source link", "YMYL"))]
            if quality_score >= minimum_quality and not critical_failures:
                rewritten = candidate
                break
        except Exception as exc:
            failures = [f"invalid output: {exc}"]
            print(json.dumps({"attempt": attempt, "quality_score": 0, "failures": failures}, ensure_ascii=False))
    if rewritten is None:
        failure_row = [iso_kst(), f"blogger-rewrite-{uuid.uuid4().hex[:12]}", blogger_site_id, "failed_quality", "FALSE", "", "", "", source["link"], "", "", "QUALITY_GATE", f"quality_score={quality_score}; failures={'; '.join(failures)}", iso_kst()]
        service.spreadsheets().values().append(spreadsheetId=sheet_id, range=f"'{QUEUE_TAB}'!A1", valueInputOption="RAW", insertDataOption="INSERT_ROWS", body={"values": [failure_row]}).execute()
        raise RuntimeError(f"Blogger 품질점수 {quality_score}/100: 2회 모두 {minimum_quality}점 미만이므로 발행을 차단했습니다. {failures}")

    content = rewritten["content_html"]
    image_model = "0"
    # One image maximum. No Pexels/Pixabay/OpenAI/Gemini-image fallback.
    image_url = generate_image_url(rewritten["title"], theme="Blogger")
    if image_url and image_url not in content:
        content = _attach_replicate_image(content, image_url, rewritten["title"])
        image_model = "replicate-approved"

    job_id = f"blogger-rewrite-{uuid.uuid4().hex[:12]}"
    labels = rewritten.get("labels", [])
    if isinstance(labels, str):
        labels = [x.strip() for x in labels.split(",") if x.strip()]
    publish_now = os.environ.get("BLOGGER_PUBLISH_NOW", "false").strip().lower() in {"1", "true", "yes", "y", "on"}
    row = [iso_kst(), job_id, blogger_site_id, "ready", "TRUE" if publish_now else "FALSE", rewritten["title"], content, ",".join(labels[:5]), source["link"], "", "", "", f"quality_score={quality_score}; rewritten_similarity={similarity_score:.3f}; images={image_model}; meta_description={rewritten['meta_description']}", ""]
    service.spreadsheets().values().append(spreadsheetId=sheet_id, range=f"'{QUEUE_TAB}'!A1", valueInputOption="RAW", insertDataOption="INSERT_ROWS", body={"values": [row]}).execute()
    print(json.dumps({"queued": True, "job_id": job_id, "source": source["link"], "quality_score": quality_score, "similarity": round(similarity_score, 3), "image_count": 1 if image_model != "0" else 0, "meta_description": rewritten["meta_description"], "publish_now": publish_now, "text_provider": "gemini", "image_provider": image_model}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
