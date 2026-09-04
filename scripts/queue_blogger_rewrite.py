#!/usr/bin/env python3
"""Create one original Blogger review draft under the locked common policy."""
from __future__ import annotations

import json
import html
import os
import re
import socket
import sys
import uuid
from urllib.parse import urlparse, parse_qs
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from automation_hub.blogger_rewriter import (
    blogger_quality_score,
    extract_http_links,
    normalize_rewrite_format,
    parse_rewrite_json,
    rewrite_prompt,
)
from automation_hub.content_identity import active_duplicate, canonical_source_id, stable_content_id
from automation_hub.blogger_topic_router import (
    NoEligibleTopic,
    NoRelatedWordPressSource,
    resolve_automatic_source,
)
from automation_hub.original_writer import original_prompt, original_quality_score
from automation_hub.time_utils import iso_kst
from gsheets_direct import get_sheets_service
from openai_text import openai_available, openai_generate_text
from replicate_image_provider import generate_image_url
from sync_automation_hub_to_sheets import QUEUE_TAB
from budget_guard import check_and_record

# Worst case for one run: two GPT writing attempts plus one image.
ESTIMATED_COST_PER_RUN_USD = 0.03
KPOP_SITE_ID = "blogger_kworld365_kpop"
KPOP_TERMS = (
    "k-pop", "kpop", "idol", "comeback", "album", "single", "music video",
    "concert", "fan meeting", "fandom", "billboard", "gaon", "circle chart",
    "music bank", "inkigayo", "m countdown", "artist", "group", "soloist",
)


def is_kpop_source(post: dict) -> bool:
    """Allow the dedicated KWorld365 Blogger only K-pop source articles."""
    title = str(post.get("title", {}).get("rendered", ""))
    body = str(post.get("content", {}).get("rendered", ""))
    text = html.unescape(re.sub(r"<[^>]+>", " ", f"{title} {body}")).lower()
    return any(term in text for term in KPOP_TERMS)


def _records(values: list[list[str]]) -> list[dict[str, str]]:
    if not values:
        return []
    header = values[0]
    return [dict(zip(header, [*row, *([""] * (len(header) - len(row)))])) for row in values[1:] if row]


def _profile_for_blogger(blogger_site_id: str) -> dict:
    site_key = blogger_site_id.removeprefix("blogger_")
    profiles = json.loads(
        (ROOT / "config" / "content_engine_profiles.json").read_text(encoding="utf-8")
    )["profiles"]
    profile = next((item for item in profiles if item.get("site_key") == site_key), None)
    if profile is None:
        raise RuntimeError(f"등록되지 않은 Blogger 사이트 ID입니다: {blogger_site_id}")
    return profile


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
    force_keyword = os.environ.get("BLOGGER_FORCE_KEYWORD", "").strip()
    blogger_site_id = os.environ.get("BLOGGER_SITE_ID", "").strip()
    if not all((sheet_id, blogger_site_id)):
        raise SystemExit("SHEET_ID and BLOGGER_SITE_ID are required")
    service = get_sheets_service()
    existing = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"'{QUEUE_TAB}'!A1:N").execute().get("values", [])
    queue_records = _records(existing)
    profile = _profile_for_blogger(blogger_site_id)
    selected_topic = ""
    source_match_score = None
    route_code = "WP_RELATED_SOURCE"
    evidence_sources: list[dict[str, str]] = []
    if source_url:
        try:
            parsed = urlparse(source_url)
            site_root = f"{parsed.scheme}://{parsed.netloc}"
            exact_ids = parse_qs(parsed.query).get("p", [])
            slug = parsed.path.strip("/").rsplit("/", 1)[-1] if parsed.path.strip("/") else ""
            if exact_ids:
                if not exact_ids[0].isdigit():
                    raise ValueError("Invalid exact WordPress source ID")
                posts = requests.get(f"{site_root}/wp-json/wp/v2/posts/{exact_ids[0]}", timeout=30)
            elif slug:
                posts = requests.get(
                    f"{site_root}/wp-json/wp/v2/posts",
                    params={"slug": slug, "status": "publish"},
                    timeout=30,
                )
            else:
                posts = requests.get(f"{site_root}/wp-json/wp/v2/posts", params={"status": "publish", "per_page": 10, "orderby": "date", "order": "desc"}, timeout=30)
            posts.raise_for_status()
            source_posts = [posts.json()] if exact_ids else posts.json()
            if slug and not source_posts:
                raise RuntimeError(f"No published post found at slug '{slug}' on {site_root}")
            if (exact_ids or slug) and source_posts[0].get("status") != "publish":
                raise RuntimeError("Calendar WordPress source is not public; awaiting human approval")
        except requests.RequestException as exc:
            _append_failure(service, sheet_id, blogger_site_id, error_code="SOURCE_FETCH", message=f"WordPress source fetch failed: {exc}", source_url=source_url)
            raise
    elif force_keyword:
        # 키워드보고발행: CEO already picked this exact topic (a chip from
        # the paired WP site's own category pool) — skip the live
        # cross-media research entirely and just find the closest matching
        # public post for it, same matching logic resolve_automatic_source
        # itself uses.
        from automation_hub.blogger_topic_router import fetch_public_wp_posts, select_wp_source

        wp_url = str(profile["wordpress"]["url"]).rstrip("/")
        already_used = [
            record.get("source_keyword", "")
            for record in queue_records
            if record.get("site_id") == blogger_site_id
        ]
        try:
            candidate_posts = fetch_public_wp_posts(wp_url)
        except requests.RequestException as exc:
            _append_failure(service, sheet_id, blogger_site_id, error_code="SOURCE_FETCH", message=f"WordPress source fetch failed: {exc}", source_url=wp_url)
            raise
        selected = select_wp_source(force_keyword, candidate_posts, profile=profile, excluded_urls=already_used)
        selected_topic = force_keyword
        route_code = "WP_RELATED_SOURCE" if selected else "INDEPENDENT_TREND_ARTICLE"
        if selected:
            post, source_match_score = selected
            source_posts = [post]
            source_url = str(post["link"])
        else:
            source_posts = []
            source_url = ""
    else:
        already_used = [
            record.get("source_keyword", "")
            for record in queue_records
            if record.get("site_id") == blogger_site_id
        ]
        try:
            routed = resolve_automatic_source(profile, excluded_urls=already_used)
        except NoEligibleTopic as exc:
            _append_failure(
                service, sheet_id, blogger_site_id, error_code="NO_TREND_TOPIC",
                message=str(exc), source_url=profile["wordpress"]["url"],
            )
            raise
        except NoRelatedWordPressSource as exc:
            _append_failure(
                service, sheet_id, blogger_site_id, error_code="NO_RELATED_WP_SOURCE",
                message=str(exc), source_url=profile["wordpress"]["url"],
            )
            raise
        selected_topic = routed.topic.keyword
        source_match_score = routed.source_score
        route_code = routed.result_code
        evidence_sources = [
            {"outlet": outlet, "title": title, "url": url}
            for outlet, title, url in routed.topic.evidence_items
        ]
        if routed.post is not None:
            source_posts = [routed.post]
            source_url = str(routed.post["link"])
        else:
            source_posts = []
            source_url = ""
        print(json.dumps({
            "route_code": route_code,
            "automatic_topic": selected_topic,
            "topic_score": routed.topic.score,
            "media_mentions": routed.topic.mention_count,
            "media_outlets": routed.topic.outlet_count,
            "viral_score": routed.topic.viral_score,
            "source_wp_url": source_url or None,
            "source_match_score": source_match_score,
        }, ensure_ascii=False))

    def golden_source_score(post):
        title = post.get("title", {}).get("rendered", "").lower()
        intent = os.environ.get("BLOGGER_SEARCH_INTENT", "").lower().split(",")
        persona = os.environ.get("BLOGGER_PERSONA", "").lower().split()
        return 40 + min(30, 10 * sum(x.strip() in title for x in intent if x.strip())) + min(20, 4 * sum(x in title for x in persona if len(x) > 3)) + min(10, len(title) // 12)
    eligible = [post for post in source_posts if not active_duplicate(queue_records, site_id=blogger_site_id, source_id=post.get("link", ""))]
    source = max(eligible, key=golden_source_score, default=None)
    evidence_urls = [item["url"] for item in evidence_sources if item.get("url")]
    source_identity = source.get("link", "") if source else (evidence_urls[0] if evidence_urls else "")
    if source_posts and not source:
        _append_failure(service, sheet_id, blogger_site_id, error_code="NO_NEW_SOURCE", message="새로운 WordPress 원문이 없어 생성과 유료 API 호출을 시작하지 않았습니다.", source_url=source_url)
        raise RuntimeError(
            "새로운 WordPress 원문이 없어 Blogger 검토 대기 행을 만들지 못했습니다."
        )
    if source is None and not evidence_urls:
        _append_failure(
            service, sheet_id, blogger_site_id, error_code="NO_TREND_EVIDENCE",
            message="독립 신규 글에 사용할 복수 매체 근거 URL이 없습니다.",
        )
        raise RuntimeError("Independent trend article requires verified media evidence")
    if active_duplicate(queue_records, site_id=blogger_site_id, source_id=source_identity):
        _append_failure(
            service, sheet_id, blogger_site_id, error_code="DUPLICATE_SOURCE",
            message="같은 원문 또는 당일 매체 근거로 이미 진행 중인 글이 있습니다.", source_url=source_identity,
        )
        raise RuntimeError("Duplicate Blogger source is already active")
    if source is not None and blogger_site_id == KPOP_SITE_ID and not is_kpop_source(source):
        _append_failure(
            service, sheet_id, blogger_site_id,
            error_code="KPOP_TOPIC_LOCK",
            message="KWorld365는 K-pop 전문 채널이므로 K-pop과 무관한 원문을 차단했습니다.",
            source_url=source.get("link", source_url),
        )
        raise RuntimeError("KWorld365 K-pop topic lock rejected a non-K-pop source")
    language = os.environ.get("BLOGGER_LANGUAGE", "en").strip().lower()
    korean_source_hosts = {"koreanews365.com", "www.koreanews365.com", "k-health365.com", "www.k-health365.com"}
    source_host = requests.utils.urlparse(source_url).netloc.lower() if source_url else ""
    if source is not None and language == "ko" and source_host not in korean_source_hosts:
        _append_failure(service, sheet_id, blogger_site_id, error_code="LANGUAGE_POLICY", message="Korean Blogger output is allowed only for approved Korean source sites.", source_url=source["link"])
        raise RuntimeError("Korean Blogger output is allowed only for koreanews365.com and K-health365.com")
    target_chars = int(os.environ.get("BLOGGER_TARGET_CHARS", "1800"))
    maximum = float(os.environ.get("BLOGGER_MAX_SIMILARITY", "0.68"))
    minimum_quality = int(os.environ.get("BLOGGER_MIN_QUALITY_SCORE", "70"))
    topic_for_safety = (
        source["title"]["rendered"] + " " + source_url
        if source is not None else selected_topic + " " + profile["wordpress"].get("theme", "")
    )
    ymyl = any(word in topic_for_safety.lower() for word in ("visa", "immigration", "insurance", "medical", "hospital", "treatment", "비자", "보험", "의료"))
    rewritten = None
    quality_score = 0
    failures = []
    similarity_score = 1.0
    text_provider = ""
    # Paid generation starts only after the deterministic topic, duplicate and
    # source/fallback checks have selected a valid route.
    check_and_record(ESTIMATED_COST_PER_RUN_USD, label=f"blogger-rewrite:{blogger_site_id}")
    # Blogger's locked authoring policy is GPT-5 mini first.  A second GPT
    # The second GPT attempt uses deterministic quality-gate feedback.
    for attempt in range(1, 3):
        provider = "gpt"
        if source is not None:
            prompt = rewrite_prompt(source["title"]["rendered"], source["content"]["rendered"], source["link"], language=language, persona=os.environ.get("BLOGGER_PERSONA", profile["blogspot"].get("persona", "helpful specialist editor")), tone=os.environ.get("BLOGGER_TONE", profile["blogspot"].get("tone", "practical and clear")), target_chars=target_chars, prior_feedback="; ".join(failures))
        else:
            prompt = original_prompt(
                keyword=selected_topic,
                site_theme=profile["wordpress"].get("theme", ""),
                language=language,
                persona=os.environ.get("BLOGGER_PERSONA", profile["blogspot"].get("persona", "helpful specialist editor")),
                tone=os.environ.get("BLOGGER_TONE", profile["blogspot"].get("tone", "practical and clear")),
                target_chars=target_chars,
                prior_feedback="; ".join(failures),
                verified_sources=evidence_sources,
            )
        try:
            if not openai_available():
                raise RuntimeError("GPT-5 mini writer unavailable")
            raw = openai_generate_text(prompt, temperature=0.7, max_retries=1)
            candidate = parse_rewrite_json(raw)
            if source is not None:
                candidate = normalize_rewrite_format(candidate, target_chars=target_chars, source_url=source["link"], ymyl=ymyl)
                quality_score, failures, similarity_score = blogger_quality_score(candidate, source_title=source["title"]["rendered"], source_url=source["link"], source_html=source["content"]["rendered"], target_chars=target_chars, maximum_similarity=maximum, language=language)
                critical_prefixes = ("body length", "verified WordPress source link", "YMYL", "meta description is incomplete", "language mismatch")
            else:
                candidate = normalize_rewrite_format(candidate, target_chars=target_chars, source_url="", ymyl=ymyl)
                quality_score, failures = original_quality_score(candidate, keyword=selected_topic, target_chars=target_chars, language=language)
                used_evidence = set(extract_http_links(candidate.get("content_html", ""))) & set(evidence_urls)
                if len(used_evidence) < min(2, len(evidence_urls)):
                    failures.append("verified trend evidence links are incomplete")
                    quality_score = max(0, quality_score - 15)
                similarity_score = 0.0
                critical_prefixes = ("body length", "verified trend evidence", "YMYL", "meta description is incomplete", "language mismatch")
            print(json.dumps({"attempt": attempt, "quality_score": quality_score, "failures": failures}, ensure_ascii=False))
            critical_failures = [failure for failure in failures if failure.startswith(critical_prefixes)]
            if quality_score >= minimum_quality and not critical_failures:
                rewritten = candidate
                text_provider = provider
                break
        except Exception as exc:
            failures = [f"invalid output: {exc}"]
            print(json.dumps({"attempt": attempt, "quality_score": 0, "failures": failures}, ensure_ascii=False))
    if rewritten is None:
        failure_row = [iso_kst(), f"blogger-rewrite-{uuid.uuid4().hex[:12]}", blogger_site_id, "failed_quality", "FALSE", "", "", "", source_identity, "", "", "QUALITY_GATE", f"route_code={route_code}; quality_score={quality_score}; failures={'; '.join(failures)}", iso_kst()]
        service.spreadsheets().values().append(spreadsheetId=sheet_id, range=f"'{QUEUE_TAB}'!A1", valueInputOption="RAW", insertDataOption="INSERT_ROWS", body={"values": [failure_row]}).execute()
        raise RuntimeError(f"Blogger 품질점수 {quality_score}/100: GPT-5 mini 초안·재작성이 모두 {minimum_quality}점 미만이므로 초안 생성을 차단했습니다. {failures}")

    content = rewritten["content_html"]
    image_model = "0"
    image_subject = (rewritten.get("image_queries") or [rewritten["title"]])[0]
    image_alt = (
        f"{str(image_subject).strip()} 관련 장면"
        if language.startswith("ko") else
        f"Scene related to {str(image_subject).strip()}"
    )
    image_url = generate_image_url(image_subject, theme=rewritten["title"])
    if not image_url:
        print(json.dumps({
            "image_pass": True,
            "reason": "SDXL Lightning and FLUX Schnell both failed; queueing text-only draft",
        }, ensure_ascii=False))
    if image_url:
        content = f'<p><img src="{html.escape(image_url, quote=True)}" alt="{html.escape(image_alt, quote=True)}" /></p>' + content
        image_model = "approved_image_chain"

    content_id = stable_content_id(
        "blogger", blogger_site_id, source_identity,
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
    duplicate = active_duplicate(_records(latest), site_id=blogger_site_id, source_id=source_identity)
    if duplicate:
        print(json.dumps({"queued": False, "duplicate_blocked": True, "existing_job_id": duplicate.get("job_id"), "content_id": content_id}, ensure_ascii=False))
        return 0
    label_count = 8 + int(content_id[:2], 16) % 7
    row = [iso_kst(), job_id, blogger_site_id, "ready", "TRUE" if publish_now else "FALSE", rewritten["title"], content, ",".join(labels[:label_count]), canonical_source_id(source_identity), "", "", "", f"route_code={route_code}; content_id={content_id}; selected_topic={selected_topic or 'manual_source'}; source_match_score={source_match_score if source_match_score is not None else 'none'}; quality_score={quality_score}; rewritten_similarity={similarity_score:.3f}; images={image_model}; image_status={'generated' if image_url else 'pass_no_image'}; meta_description={rewritten['meta_description']}", ""]
    service.spreadsheets().values().append(spreadsheetId=sheet_id, range=f"'{QUEUE_TAB}'!A1", valueInputOption="RAW", insertDataOption="INSERT_ROWS", body={"values": [row]}).execute()
    github_output = os.environ.get("GITHUB_OUTPUT", "").strip()
    if github_output:
        with open(github_output, "a", encoding="utf-8") as output_file:
            output_file.write(f"job_id={job_id}\n")
    print(json.dumps({"queued": True, "result_code": route_code, "job_id": job_id, "content_id": content_id, "selected_topic": selected_topic or None, "source": canonical_source_id(source_identity), "source_wp_url": source.get("link") if source else None, "source_match_score": source_match_score, "golden_keyword_score": golden_source_score(source) if source else None, "quality_score": quality_score, "similarity": round(similarity_score, 3), "image_count": 1 if image_model != "0" else 0, "meta_description": rewritten["meta_description"], "publish_now": publish_now, "text_provider": text_provider, "image_provider": image_model}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
