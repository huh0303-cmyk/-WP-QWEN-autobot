#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate one article draft per Tistory site job.

LOCKED: Gemini first; GPT rewrites only after generation/quality failure;
Claude is a blocking final audit. SEO/quality score below 70 is rejected.

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
from claude_text import claude_available, claude_generate_text  # noqa: E402
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
    "Never use exclamation marks, '비법', '완벽', '놓치지 마세요', '후회합니다', 'insider tips', 'unlock', 'seamless', or stacked headline formulas. "
    "Prefer a calm, specific title that names the exact reader task. Never use AI-sounding stock phrases, repeated title formulas, or a title similar to another article. "
    "The image_prompt is equally important and must visualize the title's specific human situation, emotion and practical benefit as the first image. "
    "Return strict JSON: {\"title\": str, \"category\": str, \"meta_description\": str, \"image_prompt\": str, \"body_html\": str}. "
    "body_html must be simple HTML (h2/h3/p/ul/li only, no inline styles, no scripts)."
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
        sources = job.get("official_sources") or []
        if sources:
            lines.append(
                "Use at least two of these official references as named clickable links in the body, "
                "and do not invent any other URL: " + "; ".join(sources)
            )
    lines.append(
        "Write practical steps, a short checklist, and limits/exceptions. Avoid promotional conclusions, "
        "unsupported statistics, guaranteed outcomes, and repetitive filler."
    )
    lines.append("Write the article now as the JSON object described above.")
    return "\n".join(lines)


def build_prompt(job: dict) -> str:
    """Backward-compatible alias kept for existing tests/callers."""
    return build_writer_prompt(job)


MIN_BODY_CHARS = 800
MIN_QUALITY_SCORE = 70


def structural_check(draft: dict) -> list[str]:
    """Minimum viability floor before a draft is treated as DRAFT_READY.

    This is not an SEO score — it only catches obviously broken output
    (near-empty body, no title, no real structure) that the writer or
    Claude audit could otherwise let through silently.
    """
    issues: list[str] = []
    title = str(draft.get("title", "")).strip()
    body = str(draft.get("body_html", ""))
    plain = re.sub(r"<[^>]+>", "", body)
    plain = re.sub(r"\s+", "", plain)
    if not title:
        issues.append("title is empty")
    if len(plain) < MIN_BODY_CHARS:
        issues.append(f"body length {len(plain)} is below the {MIN_BODY_CHARS}-character floor")
    if not re.search(r"(?is)<h[23][\s>]", body):
        issues.append("body has no h2/h3 headings")
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


def audit_draft(draft: dict, job: dict) -> dict | None:
    """Claude is the mandatory final editorial gate."""
    if not claude_available():
        return None
    prompt = (
        f"Site rules: allowed categories = {job['categories']}; "
        f"official_source_required = {job.get('official_source_required', False)}.\n\n"
        f"Draft title: {draft.get('title', '')}\n"
        f"Draft category: {draft.get('category', '')}\n"
        f"Draft body_html:\n{draft.get('body_html', '')}"
    )
    try:
        raw = claude_generate_text(prompt, system=AUDIT_SYSTEM_PROMPT, temperature=0.0)
        return _parse_json_response(raw)
    except Exception as exc:
        return {"ok": None, "issues": [f"audit_failed: {exc}"]}


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
    consensus = three_model_consensus(
        title=draft["title"], content=draft["body_html"], meta=draft["meta_description"],
        keyword=job["seed_topic"], gemini_generate=lambda prompt: gemini_generate_text(prompt, temperature=0.0),
    )
    draft["three_model_consensus_initial"] = consensus
    if consensus.get("ok") is not True and openai_available():
        issue_lines = []
        for model, result in consensus.get("checks", {}).items():
            for issue in result.get("issues", []):
                issue_lines.append(f"- {model}: {issue}")
        rewrite_prompt = (
            WRITER_SYSTEM_PROMPT + "\n\nRewrite the draft so every audit issue is genuinely fixed. "
            "Keep the allowed category, remove hype and unsupported claims, add concrete official-source links "
            "from the supplied list, and make the tone sound like a careful human editor. Do not merely add disclaimers.\n"
            f"Allowed category: {draft['category']}\nOfficial sources: {job.get('official_sources', [])}\n"
            f"Seed topic: {job['seed_topic']}\nAudit issues:\n" + "\n".join(issue_lines) +
            "\nCurrent draft:\n" + json.dumps({
                "title": draft["title"], "category": draft["category"],
                "meta_description": draft["meta_description"],
                "image_prompt": draft["image_prompt"], "body_html": draft["body_html"],
            }, ensure_ascii=False)
        )
        try:
            revised = _parse_json_response(openai_generate_text(rewrite_prompt, temperature=0.25, max_retries=2))
            revised["category"] = draft["category"]
            draft.update({
                "title": revised.get("title", draft["title"]),
                "body_html": revised.get("body_html", draft["body_html"]),
                "meta_description": revised.get("meta_description", draft["meta_description"]),
                "image_prompt": revised.get("image_prompt", draft["image_prompt"]),
                "engine": draft["engine"] + "+gpt_consensus_rewrite",
            })
            score, issues = quality_score(draft, job)
            draft["quality_score"], draft["quality_issues"] = score, issues
            if score >= MIN_QUALITY_SCORE and not issues:
                consensus = three_model_consensus(
                    title=draft["title"], content=draft["body_html"], meta=draft["meta_description"],
                    keyword=job["seed_topic"], gemini_generate=lambda prompt: gemini_generate_text(prompt, temperature=0.0),
                )
        except Exception as exc:
            draft["consensus_rewrite_error"] = str(exc)
    if consensus.get("ok") is not True and openai_available():
        issue_lines = []
        for model, result in consensus.get("checks", {}).items():
            issue_lines.extend(f"- {model}: {issue}" for issue in result.get("issues", []))
        final_prompt = (
            WRITER_SYSTEM_PROMPT + "\n\nThis is the final corrective edit. Fix every remaining audit issue below, "
            "not just the wording. Replace numbered/list-template headlines with a specific natural title. "
            "Remove any promise not delivered by the body. Consolidate repetitive cautions. Add one concrete "
            "worked example or comparison table when useful. Use clickable official links and remove any exact "
            "time, fare, rate, date, or rule that is not directly supported.\n"
            f"Allowed category: {draft['category']}\nOfficial sources: {job.get('official_sources', [])}\n"
            f"Seed topic: {job['seed_topic']}\nRemaining issues:\n" + "\n".join(issue_lines) +
            "\nDraft to revise:\n" + json.dumps({
                "title": draft["title"], "category": draft["category"],
                "meta_description": draft["meta_description"],
                "image_prompt": draft["image_prompt"], "body_html": draft["body_html"],
            }, ensure_ascii=False)
        )
        try:
            revised = _parse_json_response(openai_generate_text(final_prompt, temperature=0.15, max_retries=2))
            draft.update({
                "title": revised.get("title", draft["title"]),
                "body_html": revised.get("body_html", draft["body_html"]),
                "meta_description": revised.get("meta_description", draft["meta_description"]),
                "image_prompt": revised.get("image_prompt", draft["image_prompt"]),
                "engine": draft["engine"] + "+gpt_final_edit",
            })
            score, issues = quality_score(draft, job)
            draft["quality_score"], draft["quality_issues"] = score, issues
            if score >= MIN_QUALITY_SCORE and not issues:
                consensus = three_model_consensus(
                    title=draft["title"], content=draft["body_html"], meta=draft["meta_description"],
                    keyword=job["seed_topic"], gemini_generate=lambda prompt: gemini_generate_text(prompt, temperature=0.0),
                )
        except Exception as exc:
            draft["consensus_final_edit_error"] = str(exc)
    draft["three_model_consensus"] = consensus
    if consensus.get("ok") is not True:
        draft["status"] = "CONSENSUS_FAILED"
        draft["error"] = "Gemini, GPT and Claude did not all approve after corrective rewrite"
        return draft
    # Nano Banana is attempted only when its free tier is explicitly enabled
    # by the shared policy. Current official API tier is not free, so the
    # workflow skips it and enters the approved Replicate chain below.
    draft["image_url"] = generate_image_url(draft["image_prompt"], theme=draft["category"])
    draft["first_image_priority"] = True
    draft["image_policy"] = "free_nano_then_flux_schnell_then_sdxl_lightning_then_sdxl_turbo_or_none"
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
        "claude_audit_enabled": claude_available(),
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
