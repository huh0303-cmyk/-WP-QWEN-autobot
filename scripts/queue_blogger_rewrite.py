#!/usr/bin/env python3
"""Rewrite one verified WordPress post with Gemini and queue it for Blogger.

Text policy: Blogger = Gemini only.
Image policy: Replicate approved 3-model gateway only; one image maximum.
"""
from __future__ import annotations

import html
import json
import os
import socket
import sys
import uuid
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from automation_hub.blogger_rewriter import blogger_quality_score, normalize_rewrite_format, parse_rewrite_json, rewrite_prompt
from automation_hub.content_identity import active_duplicate, canonical_source_id, stable_content_id
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


def _records(values: list[list[str]]) -> list[dict[str, str]]:
    if not values:
        return []
    header = values[0]
    return [dict(zip(header, [*row, *([""] * (len(header) - len(row)))])) for row in values[1:] if row]


def _append_failure(service, sheet_id: str, blogger_site_id: str, *,
                    error_code: str, message: str, source_url: str = "") -> None:
    """Record a blocked rewrite without inventing a draft or public URL."""
    row = [
        iso_kst(), f"blogger-rewrite-{uuid.uuid4().hex[:12]}", blogger_site_id,
        "failed", "FALSE", "", "", "", canonical_source_id(source_url),
        "", "", error_code, message[:1000], iso_kst(),
    ]
    service.spreadsheets().values().append(
        spreadsheetId=sheet_id, range=f"'{QUEUE_TAB}'!A1",
        valueInputOption="RAW", insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()


def force_ipv4_dns_if_requested():
    """Avoid an unroutable AAAA path without changing authoritative DNS."""
    if os.environ.get("FORCE_SOURCE_IPV4", "false").strip().lower() not in {"1", "true", "yes", "on"}:
        return
    original = socket.getaddrinfo

    def ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
        rows = original(host, port, socket.AF_INET, type, proto, flags)
        if not rows:
            raise OSError(f"no IPv4 address for {host}")
        return rows

    socket.getaddrinfo = ipv4_only


def main():
    force_ipv4_dns_if_requested()
    sheet_id = os.environ.get("SHEET_ID", "").strip()
    source_url = os.environ.get("SOURCE_WP_URL", "").rstrip("/")
    blogger_site_id = os.environ.get("BLOGGER_SITE_ID", "").strip()
    if not all((sheet_id, source_url, blogger_site_id)):
        raise SystemExit("SHEET_ID, SOURCE_WP_URL and BLOGGER_SITE_ID are required")
    service = get_sheets_service()
    try:
        posts = requests.get(f"{source_url}/wp-json/wp/v2/posts", params={"status": "publish", "per_page": 10, "orderby": "date", "order": "desc"}, timeout=30)
        posts.raise_for_status()
    except requests.RequestException as exc:
        _append_failure(service, sheet_id, blogger_site_id, error_code="SOURCE_FETCH", message=f"WordPress source fetch failed: {exc}", source_url=source_url)
        raise
    existing = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"'{QUEUE_TAB}'!A1:N").execute().get("values", [])
    queue_records = _records(existing)
    source = next(
        (
            post for post in posts.json()
            if not active_duplicate(queue_records, site_id=blogger_site_id, source_id=post.get("link", ""))
        ),
        None,
    )
    if not source:
        _append_failure(service, sheet_id, blogger_site_id, error_code="NO_NEW_SOURCE", message="새로운 WordPress 원문이 없어 생성과 유료 API 호출을 시작하지 않았습니다.", source_url=source_url)
        raise RuntimeError(
            "새로운 WordPress 원문이 없어 Blogger 검토 대기 행을 만들지 못했습니다."
        )
    language = os.environ.get("BLOGGER_LANGUAGE", "en").strip().lower()
    korean_source_hosts = {"koreanews365.com", "www.koreanews365.com", "k-health365.com", "www.k-health365.com"}
    source_host = requests.utils.urlparse(source_url).netloc.lower()
    if language == "ko" and source_host not in korean_source_hosts:
        _append_failure(service, sheet_id, blogger_site_id, error_code="LANGUAGE_POLICY", message="Korean Blogger output is allowed only for approved Korean source sites.", source_url=source["link"])
        raise RuntimeError("Korean Blogger output is allowed only for koreanews365.com and K-health365.com")
    target_chars = int(os.environ.get("BLOGGER_TARGET_CHARS", "1800"))
    maximum = float(os.environ.get("BLOGGER_MAX_SIMILARITY", "0.68"))
    minimum_quality = int(os.environ.get("BLOGGER_MIN_QUALITY_SCORE", "75"))
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
    try:
        image_url = generate_image_url(rewritten["title"], theme="Blogger")
    except Exception as exc:
        _append_failure(service, sheet_id, blogger_site_id, error_code="IMAGE_GENERATION", message=f"Approved Replicate image generation failed: {exc}", source_url=source["link"])
        raise
    if not image_url:
        _append_failure(service, sheet_id, blogger_site_id, error_code="IMAGE_GENERATION", message="Approved Replicate provider returned no image; draft queueing blocked.", source_url=source["link"])
        raise RuntimeError("Approved Replicate provider returned no image")
    if image_url not in content:
        content = _attach_replicate_image(content, image_url, rewritten["title"])
    image_model = "replicate-approved"

    content_id = stable_content_id(
        "blogger", blogger_site_id, source["link"],
        version=os.environ.get("BLOGGER_CONTENT_VERSION", "v1"),
    )
    job_id = f"blogger-{content_id}"
    labels = rewritten.get("labels", [])
    if isinstance(labels, str):
        labels = [x.strip() for x in labels.split(",") if x.strip()]
    # MASTER policy: generation only creates a review queue item. Publishing
    # requires a separate, explicitly approved platform-publish action.
    publish_now = False
    # Re-read immediately before append. Workflow concurrency serializes the
    # normal scheduler path; this second check also blocks a queue/operator race.
    latest = service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=f"'{QUEUE_TAB}'!A1:N"
    ).execute().get("values", [])
    duplicate = active_duplicate(_records(latest), site_id=blogger_site_id, source_id=source["link"])
    if duplicate:
        print(json.dumps({"queued": False, "duplicate_blocked": True, "existing_job_id": duplicate.get("job_id"), "content_id": content_id}, ensure_ascii=False))
        return 0
    row = [iso_kst(), job_id, blogger_site_id, "ready", "TRUE" if publish_now else "FALSE", rewritten["title"], content, ",".join(labels[:5]), canonical_source_id(source["link"]), "", "", "", f"content_id={content_id}; quality_score={quality_score}; rewritten_similarity={similarity_score:.3f}; images={image_model}; meta_description={rewritten['meta_description']}", ""]
    service.spreadsheets().values().append(spreadsheetId=sheet_id, range=f"'{QUEUE_TAB}'!A1", valueInputOption="RAW", insertDataOption="INSERT_ROWS", body={"values": [row]}).execute()
    print(json.dumps({"queued": True, "job_id": job_id, "content_id": content_id, "source": canonical_source_id(source["link"]), "quality_score": quality_score, "similarity": round(similarity_score, 3), "image_count": 1 if image_model != "0" else 0, "meta_description": rewritten["meta_description"], "publish_now": publish_now, "text_provider": "gemini", "image_provider": image_model}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
