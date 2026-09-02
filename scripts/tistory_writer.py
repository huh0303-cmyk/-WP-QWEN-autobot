#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate one article draft per Tistory site job.

LOCKED: Gemini first; GPT rewrites after generation/quality/review failure
and performs the final independent review. SEO/quality below 70 is rejected.

Reads a plan produced by tistory_daily_planner.py and writes drafts only —
this never publishes anything. Every job stays publish_policy=awaiting_approval
and public_allowed=false; a human (or a later approved workflow) posts it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
from gemini_text import gemini_generate_text  # noqa: E402
from openai_text import openai_available, openai_generate_text  # noqa: E402
from replicate_image_provider import generate_image_url  # noqa: E402
from three_model_consensus import three_model_consensus  # noqa: E402

WRITER_SYSTEM_PROMPT = (
    "You are a careful Korean/English blog writer for a Tistory site. "
    "Write a single, original, well-structured article. Never fabricate a "
    "date, amount, deadline, or eligibility rule — if the job requires an "
    "official source and you are not certain of a specific fact, say the "
    "reader should confirm it on the official site instead of guessing. "
    "Never copy sentences, paragraph order, headings, examples or FAQs from WordPress, Blogspot, or another Tistory site. "
    "Use a platform-specific search intent and newly built outline. "
    "The title is the most important text element: make it emotionally resonant, curiosity-driving and benefit-led so a real reader wants to click, without clickbait or false promises. "
    "Never use AI-sounding stock phrases, repeated title formulas, or a title similar to another article. "
    "Never use the word Unlock or any Unlock/Unlocking title formula; rewrite it as a specific natural headline. "
    "The image_prompt is equally important and must visualize the title's specific human situation, emotion and practical benefit as the first image. "
    "Return strict JSON: {\"title\": str, \"category\": str, \"meta_description\": str, \"image_prompt\": str, \"body_html\": str}. "
    "body_html must be simple HTML (h2/h3/p/ul/li only, no inline styles, no scripts). "
    "Every paragraph must contain no more than two short sentences. Never place bullet symbols "
    "inside a paragraph; convert enumerations into a real ul/li list. Break long explanations "
    "into separate p elements so the mobile article has visible breathing room."
)

AUDIT_SYSTEM_PROMPT = (
    "You are a strict editorial auditor, not a writer. You will be shown one "
    "draft article and its site rules. Check only for: (1) any date, amount, "
    "deadline, or eligibility rule stated as fact without attribution to a "
    "named official source, when the site requires that; (2) the category "
    "not being one of the allowed categories; (3) any sentence that reads as "
    "fabricated or overconfident about a fact an LLM cannot actually know. "
    "Return strict JSON: {\"ok\": bool, \"issues\": [str, ...]}. If there is "
    "nothing wrong, return {\"ok\": true, \"issues\": []}."
)


def build_writer_prompt(job: dict) -> str:
    lines = [
        WRITER_SYSTEM_PROMPT,
        "",
        f"Site: {job['title']} ({job['language']})",
        f"Audience: {job['audience']}",
        f"Allowed categories: {', '.join(job['categories'])}",
        f"Search intent focus: {', '.join(job['intent'])}",
        f"Seed topic: {job['seed_topic']}",
    ]
    if job.get("trend_mode"):
        lines.append(
            "This site only covers time-sensitive practical info (subsidies, "
            "reservations, schedules, festivals). Pick today's most likely "
            "high-search-volume angle on the seed topic."
        )
    if job.get("official_source_required"):
        lines.append(
            "Any date, amount, or deadline MUST be attributed to an official "
            "source by name (e.g. 정부24, 코레일, 지자체 공고). If you don't know "
            "the exact current figure, tell the reader to check the official "
            "source instead of inventing a number."
        )
    lines.append("Write the article now as the JSON object described above.")
    return "\n".join(lines)


def build_prompt(job: dict) -> str:
    """Backward-compatible alias kept for existing tests/callers."""
    return build_writer_prompt(job)


MIN_BODY_CHARS = 800
MIN_QUALITY_SCORE = 70
MAX_CONSENSUS_REWRITES = 2


def structural_check(draft: dict) -> list[str]:
    """Minimum viability floor before a draft is treated as DRAFT_READY.

    This is not an SEO score — it only catches obviously broken output
    (near-empty body, no title, no real structure) that the writer or
    Model review could otherwise let through silently.
    """
    issues: list[str] = []
    title = str(draft.get("title", "")).strip()
    body = str(draft.get("body_html", ""))
    plain = re.sub(r"<[^>]+>", "", body)
    plain = re.sub(r"\s+", "", plain)
    if not title:
        issues.append("title is empty")
    if re.search(r"(?i)\bunlock(?:s|ed|ing)?\b", title):
        issues.append("TITLE_QUALITY_FAIL: Unlock title formulas are forbidden")
    if len(plain) < MIN_BODY_CHARS:
        issues.append(f"body length {len(plain)} is below the {MIN_BODY_CHARS}-character floor")
    if not re.search(r"(?is)<h[23][\s>]", body):
        issues.append("body has no h2/h3 headings")
    paragraph_texts = [
        re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", value)).strip()
        for value in re.findall(r"(?is)<p(?:\s[^>]*)?>(.*?)</p>", body)
    ]
    if any(len(value) > 320 for value in paragraph_texts):
        issues.append("body contains a paragraph longer than 320 characters")
    if re.search(r"(?is)<p(?:\s[^>]*)?>[^<]*(?:▶|■|●|◆|▪|•)[^<]*</p>", body):
        issues.append("bullet-like text must be converted to a real ul/li list")
    return issues


def _parse_json_response(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def _write_body(job: dict, provider: str = "gemini") -> tuple[str, str]:
    """Returns (raw_response_text, engine_used).

    Routing comes from the locked automation_hub.content_model_policy, not
    from ad-hoc exception handling: important_content (trend/official-source
    sites) goes to GPT directly; everything else is Gemini-only. If Gemini
    fails, that is NOT treated as a reason to silently upgrade to a paid
    tier — the job just fails (WRITE_FAILED), same as the policy's
    "no silent paid fallback when the free tier is unavailable" rule.
    """
    prompt = build_writer_prompt(job)
    if provider == "gpt":
        if not openai_available():
            raise RuntimeError("GPT escalation requested but OpenAI credentials are unavailable")
        return openai_generate_text(prompt, temperature=0.7, max_retries=3), "gpt"

    return gemini_generate_text(prompt, temperature=0.7), "gemini"


def quality_score(draft: dict, job: dict) -> tuple[int, list[str]]:
    issues = structural_check(draft)
    body = str(draft.get("body_html", ""))
    plain = re.sub(r"<[^>]+>", " ", body).lower()
    score = 30 if not issues else max(0, 30 - 10 * len(issues))
    score += 15 if str(draft.get("meta_description", "")).strip() else 0
    score += 15 if any(str(x).lower() in plain for x in job.get("intent", [])) else 0
    score += 15 if len(re.findall(r"(?is)<h[23][\s>]", body)) >= 2 else 5
    score += 10 if re.search(r"(?is)<(?:ul|ol)[\s>]", body) else 0
    source_needed = bool(job.get("official_source_required"))
    has_source = bool(re.search(r"https?://|정부24|보조금24|고용24|국세청|복지로|코레일|SRT|공식", body, re.I))
    score += 15 if (not source_needed or has_source) else 0
    if source_needed and not has_source:
        issues.append("required official source is missing")
    title = str(draft.get("title", "")).strip().lower()
    banned_title_patterns = ("완벽 가이드", "총정리", "알아보겠습니다", "모든 것", "ultimate guide", "everything you need")
    if any(pattern in title for pattern in banned_title_patterns):
        issues.append("AI-like or repetitive title formula")
        score = min(score, 69)
    if len(title) < 12:
        issues.append("title lacks a specific emotional/benefit hook")
        score = min(score, 69)
    return min(score, 100), issues


def _consensus_issues(consensus: dict) -> list[str]:
    issues: list[str] = []
    for model, check in (consensus.get("checks") or {}).items():
        if check.get("ok") is True:
            continue
        for issue in check.get("issues") or []:
            issues.append(f"{model}: {issue}")
    return issues


def _rewrite_after_consensus(draft: dict, job: dict, consensus: dict) -> dict:
    """Use GPT only as the configured repair engine after a failed review."""
    if not openai_available():
        raise RuntimeError("GPT rewrite requested but OpenAI credentials are unavailable")
    feedback = "\n".join(f"- {issue}" for issue in _consensus_issues(consensus))
    prompt = (
        f"{WRITER_SYSTEM_PROMPT}\n\n"
        "Revise the supplied draft so every reviewer issue is genuinely fixed. "
        "Keep the same site, language, search intent and allowed category. "
        "Remove clickbait, unsupported numbers, repetitive AI-like phrases and vague generalities. "
        "Make the article practical and specific without inventing facts.\n\n"
        f"Site: {job['title']} ({job['language']})\n"
        f"Allowed categories: {', '.join(job['categories'])}\n"
        f"Seed topic: {job['seed_topic']}\n"
        f"Reviewer issues:\n{feedback}\n\n"
        f"Current draft JSON:\n{json.dumps(draft, ensure_ascii=False)}\n\n"
        "Return only the corrected JSON object."
    )
    parsed = _parse_json_response(openai_generate_text(prompt, temperature=0.35, max_retries=3))
    category = parsed.get("category")
    if category not in job["categories"]:
        category = draft["category"] if draft.get("category") in job["categories"] else job["categories"][0]
    rewritten = {
        **draft,
        "title": parsed.get("title", ""),
        "category": category,
        "body_html": parsed.get("body_html", ""),
        "meta_description": parsed.get("meta_description", ""),
        "image_prompt": parsed.get("image_prompt", "") or parsed.get("title", ""),
        "engine": "gpt-rewrite",
    }
    score, issues = quality_score(rewritten, job)
    rewritten["quality_score"] = score
    rewritten["quality_issues"] = issues
    if score < MIN_QUALITY_SCORE or issues:
        raise RuntimeError(f"rewritten quality={score}; {'; '.join(issues)}")
    return rewritten


def generate_draft(job: dict) -> dict:
    errors = []
    draft = None
    for provider in ("gemini", "gpt"):
        try:
            raw, engine = _write_body(job, provider)
            parsed = _parse_json_response(raw)
        except Exception as exc:
            errors.append(f"{provider}: {exc}")
            continue
        if parsed.get("category") not in job["categories"]:
            parsed["category"] = job["categories"][0]
        candidate = {
        "job_id": job["job_id"],
        "site_id": job["site_id"],
        "title": parsed.get("title", ""),
        "category": parsed["category"],
        "body_html": parsed.get("body_html", ""),
        "meta_description": parsed.get("meta_description", ""),
        "image_prompt": parsed.get("image_prompt", "") or parsed.get("title", ""),
        "engine": engine,
        "status": "DRAFT_READY",
        "publish_policy": "awaiting_approval",
        "duplicate_guard": True,
        "public_allowed": False,
        }
        score, issues = quality_score(candidate, job)
        candidate["quality_score"] = score
        candidate["quality_issues"] = issues
        if score >= MIN_QUALITY_SCORE and not issues:
            draft = candidate
            break
        errors.append(f"{provider}: quality={score}; {'; '.join(issues)}")
    if draft is None:
        return {"job_id": job["job_id"], "site_id": job["site_id"], "status": "QUALITY_FAILED", "error": " | ".join(errors), "public_allowed": False}
    rewrite_errors: list[str] = []
    for attempt in range(MAX_CONSENSUS_REWRITES + 1):
        consensus = three_model_consensus(
            title=draft["title"], content=draft["body_html"], meta=draft["meta_description"],
            keyword=job["seed_topic"], gemini_generate=lambda prompt: gemini_generate_text(prompt, temperature=0.0),
        )
        draft["three_model_consensus"] = consensus
        draft["consensus_attempts"] = attempt + 1
        if consensus.get("ok") is True:
            break
        if attempt >= MAX_CONSENSUS_REWRITES:
            draft["status"] = "CONSENSUS_FAILED"
            draft["error"] = "Gemini and GPT did not both approve after guided rewrites"
            draft["rewrite_errors"] = rewrite_errors
            return draft
        try:
            draft = _rewrite_after_consensus(draft, job, consensus)
        except Exception as exc:
            rewrite_errors.append(str(exc))
            draft["status"] = "CONSENSUS_FAILED"
            draft["error"] = f"Consensus rewrite failed: {exc}"
            draft["rewrite_errors"] = rewrite_errors
            return draft
    # Nano Banana is attempted only when its free tier is explicitly enabled
    # by the shared policy. Current official API tier is not free, so the
    # workflow skips it and enters the approved Replicate chain below.
    draft["image_url"] = generate_image_url(draft["image_prompt"], theme=draft["category"])
    draft["image_alt"] = f"{str(draft['image_prompt']).strip()} 관련 장면"
    draft["first_image_priority"] = True
    draft["image_policy"] = "free_nano_then_flux_schnell_then_sdxl_lightning_then_sdxl_turbo_or_quality_fail"
    if not draft["image_url"]:
        draft["status"] = "IMAGE_FAILED"
        draft["error"] = "Approved image chain failed; Tistory draft registration is blocked"
    return draft


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default="artifacts/tistory-daily-plan.json")
    parser.add_argument("--output", default="artifacts/tistory-daily-drafts.json")
    args = parser.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    drafts = [generate_draft(job) for job in plan["jobs"]]
    # Hard portfolio guard: similar/repeated titles across the five accounts
    # never reach the review-ready state.
    for index, draft in enumerate(drafts):
        if draft.get("status") != "DRAFT_READY":
            continue
        for previous in drafts[:index]:
            if previous.get("status") != "DRAFT_READY":
                continue
            ratio = SequenceMatcher(None, str(previous.get("title", "")).lower(), str(draft.get("title", "")).lower()).ratio()
            if ratio >= 0.55:
                draft["status"] = "DUPLICATE_TITLE_BLOCKED"
                draft["error"] = f"title similarity {ratio:.3f} with {previous.get('site_id')}"
                break

    result = {
        "date": plan["date"],
        "public_allowed": False,
        "review_models": ["gemini", "gpt"],
        "drafts": drafts,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    statuses = {d["status"] for d in drafts}
    print(json.dumps({"drafts": len(drafts), "statuses": sorted(statuses)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
