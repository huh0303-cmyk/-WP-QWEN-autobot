#!/usr/bin/env python3
"""Create one original Blogger review draft under the locked common policy."""
from __future__ import annotations

import json
import html
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

from automation_hub.blogger_rewriter import (
    blogger_quality_score,
    normalize_rewrite_format,
    parse_rewrite_json,
    rewrite_prompt,
)
from automation_hub.content_identity import active_duplicate, canonical_source_id, stable_content_id
from automation_hub.time_utils import iso_kst
from gsheets_direct import get_sheets_service
from gemini_text import gemini_generate_text
from openai_text import openai_available, openai_generate_text
from claude_text import claude_available, claude_generate_text
from replicate_image_provider import generate_image_url
from sync_automation_hub_to_sheets import QUEUE_TAB


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
    def golden_source_score(post):
        title = post.get("title", {}).get("rendered", "").lower()
        intent = os.environ.get("BLOGGER_SEARCH_INTENT", "").lower().split(",")
        persona = os.environ.get("BLOGGER_PERSONA", "").lower().split()
        return 40 + min(30, 10 * sum(x.strip() in title for x in intent if x.strip())) + min(20, 4 * sum(x in title for x in persona if len(x) > 3)) + min(10, len(title) // 12)
    eligible = [post for post in posts.json() if not active_duplicate(queue_records, site_id=blogger_site_id, source_id=post.get("link", ""))]
    source = max(eligible, key=golden_source_score, default=None)
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
    minimum_quality = int(os.environ.get("BLOGGER_MIN_QUALITY_SCORE", "70"))
    ymyl = any(word in (source["title"]["rendered"] + " " + source_url).lower() for word in ("visa", "immigration", "insurance", "medical", "hospital", "treatment"))
    rewritten = None
    quality_score = 0
    failures = []
    similarity_score = 1.0
    text_provider = ""
    for attempt, provider in enumerate(("gemini", "gpt"), start=1):
        prompt = rewrite_prompt(source["title"]["rendered"], source["content"]["rendered"], source["link"], language=language, persona=os.environ.get("BLOGGER_PERSONA", "helpful specialist editor"), tone=os.environ.get("BLOGGER_TONE", "practical and clear"), target_chars=target_chars, prior_feedback="; ".join(failures))
        try:
            if provider == "gemini":
                raw = gemini_generate_text(prompt, temperature=0.7)
            else:
                if not openai_available():
                    raise RuntimeError("GPT fallback unavailable")
                raw = openai_generate_text(prompt, temperature=0.7, max_retries=1)
            candidate = parse_rewrite_json(raw)
            candidate = normalize_rewrite_format(candidate, target_chars=target_chars, source_url=source["link"], ymyl=ymyl)
            quality_score, failures, similarity_score = blogger_quality_score(candidate, source_title=source["title"]["rendered"], source_url=source["link"], source_html=source["content"]["rendered"], target_chars=target_chars, maximum_similarity=maximum)
            print(json.dumps({"attempt": attempt, "quality_score": quality_score, "failures": failures}, ensure_ascii=False))
            critical_failures = [failure for failure in failures if failure.startswith(("body length", "verified WordPress source link", "YMYL"))]
            if quality_score >= minimum_quality and not critical_failures:
                rewritten = candidate
                text_provider = provider
                break
        except Exception as exc:
            failures = [f"invalid output: {exc}"]
            print(json.dumps({"attempt": attempt, "quality_score": 0, "failures": failures}, ensure_ascii=False))
    if rewritten is None:
        failure_row = [iso_kst(), f"blogger-rewrite-{uuid.uuid4().hex[:12]}", blogger_site_id, "failed_quality", "FALSE", "", "", "", source["link"], "", "", "QUALITY_GATE", f"quality_score={quality_score}; failures={'; '.join(failures)}", iso_kst()]
        service.spreadsheets().values().append(spreadsheetId=sheet_id, range=f"'{QUEUE_TAB}'!A1", valueInputOption="RAW", insertDataOption="INSERT_ROWS", body={"values": [failure_row]}).execute()
        raise RuntimeError(f"Blogger 품질점수 {quality_score}/100: Gemini와 GPT 모두 {minimum_quality}점 미만이므로 발행을 차단했습니다. {failures}")

    if not claude_available():
        _append_failure(service, sheet_id, blogger_site_id, error_code="AUDIT_UNAVAILABLE", message="Claude final audit is mandatory.", source_url=source["link"])
        raise RuntimeError("Claude final audit is mandatory")
    audit_prompt = json.dumps({"rules": "Check factual support, grammar, natural human tone, search intent, AI-like phrasing, repeated/similar title and cross-platform copying. Return strict JSON with ok and issues.", "source_title": source["title"]["rendered"], "draft": rewritten}, ensure_ascii=False)
    try:
        audit_raw = claude_generate_text(audit_prompt, system="You are a blocking editorial auditor. Return only JSON: {\"ok\": bool, \"issues\": [str]}", temperature=0.0)
        audit_text = audit_raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        audit_result = json.loads(audit_text)
    except Exception as exc:
        audit_result = {"ok": False, "issues": [str(exc)]}
    if audit_result.get("ok") is not True:
        _append_failure(service, sheet_id, blogger_site_id, error_code="AUDIT_FAILED", message=json.dumps(audit_result, ensure_ascii=False), source_url=source["link"])
        raise RuntimeError("Claude final audit failed")

    content = rewritten["content_html"]
    image_model = "0"
    image_subject = (rewritten.get("image_queries") or [rewritten["title"]])[0]
    image_url = generate_image_url(image_subject, theme=rewritten["title"])
    if image_url:
        content = f'<p><img src="{html.escape(image_url, quote=True)}" alt="{html.escape(rewritten["title"], quote=True)}" /></p>' + content
        image_model = "approved_image_chain"

    content_id = stable_content_id(
        "blogger", blogger_site_id, source["link"],
        version=os.environ.get("BLOGGER_CONTENT_VERSION", "v1"),
    )
    job_id = f"blogger-{content_id}"
    labels = rewritten.get("labels", [])
    if isinstance(labels, str):
        labels = [x.strip() for x in labels.split(",") if x.strip()]
    publish_now = os.environ.get("BLOGGER_PUBLISH_NOW", "false").strip().lower() in {"1", "true", "yes", "on"}
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
    print(json.dumps({"queued": True, "job_id": job_id, "content_id": content_id, "source": canonical_source_id(source["link"]), "golden_keyword_score": golden_source_score(source), "quality_score": quality_score, "similarity": round(similarity_score, 3), "image_count": 1 if image_model != "0" else 0, "meta_description": rewritten["meta_description"], "publish_now": publish_now, "text_provider": text_provider, "image_provider": image_model}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
