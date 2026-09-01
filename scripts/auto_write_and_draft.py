#!/usr/bin/env python3
"""Sheet-triggered original-content pipeline: pick a due keyword from
자동화_황금키워드, write it (Gemini -> GPT fallback), pass Gemini+GPT+Claude
consensus, generate one image, create a WordPress or Blogger DRAFT (never
publish), update the sheet row, and leave a record for the existing
email+Kakao review notifier.

SITE_ID must be one of content_engine_profiles.json's site_key values
prefixed "wp_" or "blogger_" (e.g. wp_ktrip365, blogger_ktrip365) - the
prefix picks the platform and, deliberately, its own separate keyword
queue, so WordPress and Blogspot for the same site are never writing the
same keyword.
"""
from __future__ import annotations

import html
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from automation_hub.blogger_adapter import BloggerPublisher
from automation_hub.blogger_rewriter import normalize_rewrite_format, parse_rewrite_json
from automation_hub.original_writer import original_prompt, original_quality_score
from automation_hub.publishing import PublishJob
from automation_hub.sheet_schema import KEYWORD_HEADER
from automation_hub.time_utils import iso_kst
from budget_guard import check_and_record
from create_manual_wp_draft import WP_USER, ensure_featured_media, resolve_category_id, resolve_tag_ids
from gemini_text import gemini_generate_text
from gsheets_direct import ensure_tab, get_sheets_service
from openai_text import openai_available, openai_generate_text
from claude_text import claude_available, claude_generate_text
from process_platform_queue import _access_token
from replicate_image_provider import generate_image_url
from three_model_consensus import three_model_consensus

KEYWORDS_TAB = "자동화_황금키워드"
RESULT_FILE = "newsroom_publish_result.json"
# Worst case: 2 write attempts (gemini+gpt) + 3-way consensus (gemini+gpt+claude) + 1 image.
ESTIMATED_COST_PER_RUN_USD = 0.03


def _consensus_passes(consensus: dict) -> bool:
    """Require a 2-of-3 editorial majority, not subjective unanimity."""
    checks = consensus.get("checks") or {}
    return sum(1 for check in checks.values() if check.get("ok") is True) >= 2


def _records(values: list[list[str]]) -> list[dict[str, str]]:
    if not values:
        return []
    header = values[0]
    return [dict(zip(header, [*row, *([""] * (len(header) - len(row)))])) for row in values[1:] if row]


def _col(index_1based: int) -> str:
    letters = ""
    n = index_1based
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _set_status(service, sheet_id: str, sheet_row: int, status: str) -> None:
    status_col = KEYWORD_HEADER.index("status") + 1
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id, range=f"'{KEYWORDS_TAB}'!{_col(status_col)}{sheet_row}",
        valueInputOption="RAW", body={"values": [[status]]},
    ).execute()
    if status in {"초안완료", "발행완료"}:
        used_at_col = KEYWORD_HEADER.index("used_at") + 1
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id, range=f"'{KEYWORDS_TAB}'!{_col(used_at_col)}{sheet_row}",
            valueInputOption="RAW", body={"values": [[iso_kst()]]},
        ).execute()


def _profile_for(site_id: str) -> tuple[str, dict]:
    platform = "wordpress" if site_id.startswith("wp_") else "blogger" if site_id.startswith("blogger_") else ""
    if not platform:
        raise SystemExit(f"SITE_ID must start with wp_ or blogger_, got {site_id!r}")
    site_key = site_id.removeprefix("wp_").removeprefix("blogger_")
    profiles = json.loads((ROOT / "config" / "content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    for profile in profiles:
        if profile["site_key"] == site_key:
            return platform, profile
    raise SystemExit(f"No content_engine_profiles.json entry for site_key={site_key!r}")


def _next_due_row(service, sheet_id: str, site_id: str) -> tuple[int, dict] | None:
    values = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"'{KEYWORDS_TAB}'!A1:K").execute().get("values", [])
    records = _records(values)
    candidates = [(i, r) for i, r in enumerate(records) if r.get("site_id") == site_id and r.get("status") in {"대기", "보류"}]
    if not candidates:
        return None
    candidates.sort(key=lambda pair: float(pair[1].get("total_score") or 0), reverse=True)
    index, record = candidates[0]
    return index + 2, record  # header row + 1-indexed


def _write_article(*, keyword: str, site_theme: str, language: str, persona: str, tone: str,
                   min_chars: int, target_chars: int, max_chars: int,
                   review_feedback: str = "") -> tuple[dict | None, int, list[str], str]:
    failures: list[str] = [review_feedback] if review_feedback else []
    for attempt, provider in enumerate(("gemini", "gpt"), start=1):
        prompt = original_prompt(keyword=keyword, site_theme=site_theme, language=language,
                                  persona=persona, tone=tone, target_chars=target_chars,
                                  prior_feedback="; ".join(failures))
        try:
            if provider == "gemini":
                raw = gemini_generate_text(prompt, temperature=0.7)
            else:
                if not openai_available():
                    raise RuntimeError("GPT fallback unavailable")
                raw = openai_generate_text(prompt, temperature=0.7, max_retries=1)
            candidate = parse_rewrite_json(raw)
            ymyl = any(w in keyword.lower() for w in ("visa", "immigration", "insurance", "medical", "hospital", "treatment", "비자", "보험", "의료"))
            candidate = normalize_rewrite_format(candidate, target_chars=target_chars, source_url="", ymyl=ymyl)
            score, failures = original_quality_score(candidate, keyword=keyword, target_chars=target_chars)
            print(json.dumps({"attempt": attempt, "provider": provider, "score": score, "failures": failures}, ensure_ascii=False))
            critical = [f for f in failures if f.startswith(("body length", "meta description is incomplete"))]
            if score >= 75 and not critical:
                return candidate, score, failures, provider
        except Exception as exc:
            failures = [f"invalid output: {exc}"]
            print(json.dumps({"attempt": attempt, "provider": provider, "score": 0, "failures": failures}, ensure_ascii=False))
    return None, 0, failures, ""


def _publish_wordpress(*, site_url: str, secret_name: str, article: dict, image_url: str) -> dict:
    wp_pass = os.environ.get(secret_name, "")
    if not wp_pass:
        raise SystemExit(f"No WordPress application password found in env var {secret_name}")
    data = {
        "title": article["title"], "content": article["content_html"], "status": "draft",
        "comment_status": "closed", "ping_status": "closed",
    }
    category_id = resolve_category_id(site_url, wp_pass, "")
    if category_id:
        data["categories"] = [category_id]
    tag_ids = resolve_tag_ids(site_url, wp_pass, article.get("labels", []))
    if tag_ids:
        data["tags"] = tag_ids
    if article.get("meta_description"):
        data["meta"] = {"rank_math_description": article["meta_description"]}
    featured_media_id = ensure_featured_media(site_url, wp_pass, image_url, article["title"])
    if featured_media_id:
        data["featured_media"] = featured_media_id
    response = requests.post(f"{site_url}/wp-json/wp/v2/posts", auth=(WP_USER, wp_pass), json=data, timeout=30)
    if response.status_code not in (200, 201):
        raise SystemExit(f"WordPress draft creation failed: HTTP {response.status_code}: {response.text[:400]}")
    payload = response.json()
    if payload.get("status") != "draft":
        raise SystemExit(f"WordPress returned unexpected status {payload.get('status')!r}")
    post_id = payload.get("id")
    return {
        "status": "draft", "platform": "wordpress", "site": site_url,
        "url": payload.get("link", ""),
        "edit_url": f"{site_url.rstrip('/')}/wp-admin/post.php?post={post_id}&action=edit",
        "title": article["title"], "post_id": post_id,
    }


def _publish_blogger(*, blog_id: str, article: dict, image_url: str, site_id: str,
                     site_url: str, keyword: str) -> dict:
    token = _access_token("")
    content = article["content_html"]
    if image_url:
        content = f'<p><img src="{html.escape(image_url, quote=True)}" alt="{html.escape(article["title"], quote=True)}" /></p>' + content
    job = PublishJob(
        job_id=f"auto-{site_id}-{abs(hash(keyword))}", site_id=site_id, title=article["title"], content_html=content,
        labels=article.get("labels", []), publish_now=False, source_keyword=keyword,
        search_description=article.get("meta_description", ""),
    )
    result = BloggerPublisher(site_id, blog_id, token).publish(job)
    if not result.ok:
        raise SystemExit(f"Blogger draft creation failed: {result.error_code} {result.message}")
    return {
        "status": "draft", "platform": "blogger", "site": site_url or site_id,
        "url": result.public_url, "edit_url": result.public_url,
        "title": article["title"], "post_id": result.remote_id,
    }


def main() -> int:
    sheet_id = os.environ.get("SHEET_ID", "").strip()
    site_id = os.environ.get("SITE_ID", "").strip()
    direct_keyword = os.environ.get("DIRECT_KEYWORD", "").strip()
    source_wp_url = os.environ.get("SOURCE_WP_URL", "").strip()
    if not site_id or (not sheet_id and not direct_keyword):
        raise SystemExit("SITE_ID and either SHEET_ID or DIRECT_KEYWORD are required")

    platform, profile = _profile_for(site_id)
    check_and_record(ESTIMATED_COST_PER_RUN_USD, label=f"auto-write:{site_id}")

    service = None
    sheet_row = None
    if direct_keyword:
        keyword = direct_keyword
    else:
        service = get_sheets_service()
        ensure_tab(service, sheet_id, KEYWORDS_TAB, KEYWORD_HEADER)
        due = _next_due_row(service, sheet_id, site_id)
        if not due:
            print(json.dumps({"ok": True, "skipped": True, "reason": "no 대기 keyword queued for this site"}, ensure_ascii=False))
            return 0
        sheet_row, record = due
        keyword = record["keyword"]
        _set_status(service, sheet_id, sheet_row, "작성중")

    if platform == "wordpress":
        settings = profile["wordpress"]
        language, site_url = profile["language"], settings["url"]
    else:
        settings = profile["blogspot"]
        language, site_url = profile["language"], settings["url"]
        if not settings.get("ready_for_automation"):
            _set_status(service, sheet_id, sheet_row, "보류")
            raise SystemExit(f"{site_id}: Blogspot blog not yet created/wired (destination_id missing)")
        if direct_keyword:
            wp_base = profile["wordpress"]["url"].rstrip("/") + "/"
            if not source_wp_url.startswith(wp_base):
                raise SystemExit(f"{site_id}: SOURCE_WP_URL must be a public article under {wp_base}")
            check = requests.get(source_wp_url, timeout=30, allow_redirects=True)
            if check.status_code != 200:
                raise SystemExit(f"{site_id}: SOURCE_WP_URL is not publicly reachable (HTTP {check.status_code})")

    editorial_funnel = settings.get("editorial_funnel") or profile["wordpress"].get("editorial_funnel") or {}
    funnel_context = json.dumps(editorial_funnel, ensure_ascii=False) if editorial_funnel else ""
    writer_args = dict(
        keyword=keyword, site_theme=profile["wordpress"]["theme"] + (f". Editorial funnel and safety rules: {funnel_context}" if funnel_context else ""), language=language,
        persona=settings["persona"], tone=settings["tone"],
        min_chars=settings["min_chars"], target_chars=settings["target_chars"], max_chars=settings["max_chars"],
    )
    article, score, failures, provider = _write_article(**writer_args)
    if article is None:
        if service is not None and sheet_row is not None:
            _set_status(service, sheet_id, sheet_row, "보류")
        raise SystemExit(f"Quality gate failed for {site_id}/{keyword}: score={score} failures={failures}")

    consensus = {}
    for consensus_attempt in range(1, 4):
        consensus = three_model_consensus(
            title=article["title"], content=article["content_html"], meta=article["meta_description"],
            keyword=keyword, gemini_generate=lambda check: gemini_generate_text(check, temperature=0.0),
        )
        if _consensus_passes(consensus):
            break
        if consensus_attempt >= 3:
            continue
        issues = []
        for model, check in (consensus.get("checks") or {}).items():
            for issue in check.get("issues") or []:
                issues.append(f"{model}: {issue}")
        feedback = "Revise the article to resolve every reviewer issue: " + "; ".join(issues)
        print(json.dumps({"consensus_attempt": consensus_attempt, "action": "revise", "issues": issues}, ensure_ascii=False))
        article, score, failures, provider = _write_article(**writer_args, review_feedback=feedback)
        if article is None:
            break
    if article is None or not _consensus_passes(consensus):
        if service is not None and sheet_row is not None:
            _set_status(service, sheet_id, sheet_row, "보류")
        raise SystemExit(f"Gemini/GPT/Claude consensus failed for {site_id}/{keyword}: {json.dumps(consensus, ensure_ascii=False)}")

    image_subject = (article.get("image_queries") or [article["title"]])[0]
    image_url = "" if os.environ.get("IMAGE_MODEL", "").strip() == "none" else (generate_image_url(image_subject, theme=article["title"]) or "")

    if platform == "wordpress":
        record_out = _publish_wordpress(site_url=site_url, secret_name=settings["secret_name"], article=article, image_url=image_url)
    else:
        record_out = _publish_blogger(
            blog_id=settings["destination_id"], article=article, image_url=image_url,
            site_id=site_id, site_url=site_url, keyword=keyword,
        )
    record_out["quality_score"] = score
    record_out["site_id"] = site_id

    existing = {"records": []}
    if Path(RESULT_FILE).exists():
        try:
            existing = json.loads(Path(RESULT_FILE).read_text(encoding="utf-8"))
        except Exception:
            existing = {"records": []}
    existing.setdefault("records", []).append(record_out)
    Path(RESULT_FILE).write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    if service is not None and sheet_row is not None:
        _set_status(service, sheet_id, sheet_row, "초안완료")
    print(json.dumps({"ok": True, "site_id": site_id, "keyword": keyword, "score": score, "provider": provider, "url": record_out.get("url")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
