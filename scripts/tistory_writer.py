#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate one article draft per Tistory site job.

2026-08-28 정책(config/content_writing_policy.json, LOCKED): Gemini Flash
(무료)가 기본 작가, GPT는 important_content(trend_mode/공식출처 필요 사이트)
같은 명시적 신호가 있을 때만 쓴다 — Gemini가 그냥 실패했다고 조용히 GPT로
넘어가지 않는다("무료 tier 소진만으로는 유료로 안 간다"). Claude는 글을 쓰지
않고, 완성된 초안을 훑어 정책 위반(출처 없는 날짜/금액 등)이 있는지
감사(system audit)만 한다.

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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
from automation_hub.content_model_policy import choose_writer  # noqa: E402
from claude_text import claude_available, claude_generate_text  # noqa: E402
from gemini_text import gemini_generate_text  # noqa: E402
from openai_text import openai_available, openai_generate_text  # noqa: E402

WRITER_SYSTEM_PROMPT = (
    "You are a careful Korean/English blog writer for a Tistory site. "
    "Write a single, original, well-structured article. Never fabricate a "
    "date, amount, deadline, or eligibility rule — if the job requires an "
    "official source and you are not certain of a specific fact, say the "
    "reader should confirm it on the official site instead of guessing. "
    "Return strict JSON: {\"title\": str, \"category\": str, \"body_html\": str}. "
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
    lines.append("Write the article now as the JSON object described above.")
    return "\n".join(lines)


def build_prompt(job: dict) -> str:
    """Backward-compatible alias kept for existing tests/callers."""
    return build_writer_prompt(job)


MIN_BODY_CHARS = 800


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


def _write_body(job: dict) -> tuple[str, str]:
    """Returns (raw_response_text, engine_used).

    Routing comes from the locked automation_hub.content_model_policy, not
    from ad-hoc exception handling: important_content (trend/official-source
    sites) goes to GPT directly; everything else is Gemini-only. If Gemini
    fails, that is NOT treated as a reason to silently upgrade to a paid
    tier — the job just fails (WRITE_FAILED), same as the policy's
    "no silent paid fallback when the free tier is unavailable" rule.
    """
    prompt = build_writer_prompt(job)
    important = bool(job.get("trend_mode") or job.get("official_source_required"))
    paid_writer_allowed = os.environ.get("TISTORY_ALLOW_PAID_WRITER", "false").strip().lower() in {
        "1", "true", "yes", "on"
    }
    decision = choose_writer(important_content=important and paid_writer_allowed)

    if decision.provider == "openai":
        if not openai_available():
            raise RuntimeError("GPT escalation requested but OpenAI credentials are unavailable")
        return openai_generate_text(prompt, temperature=0.7, max_retries=3), "gpt"

    return gemini_generate_text(prompt, temperature=0.7), "gemini"


def audit_draft(draft: dict, job: dict) -> dict | None:
    """Claude reviews the finished draft for policy violations. This never
    blocks publication by itself — it only annotates the draft so a human
    reviewer (or a future stricter gate) can see what Claude flagged."""
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
    try:
        raw, engine = _write_body(job)
    except Exception as exc:
        return {
            "job_id": job["job_id"],
            "site_id": job["site_id"],
            "status": "WRITE_FAILED",
            "error": str(exc),
            "public_allowed": False,
        }

    try:
        parsed = _parse_json_response(raw)
    except json.JSONDecodeError as exc:
        return {
            "job_id": job["job_id"],
            "site_id": job["site_id"],
            "status": "PARSE_FAILED",
            "error": str(exc),
            "raw_preview": raw[:500],
            "public_allowed": False,
        }
    if parsed.get("category") not in job["categories"]:
        parsed["category"] = job["categories"][0]

    draft = {
        "job_id": job["job_id"],
        "site_id": job["site_id"],
        "title": parsed.get("title", ""),
        "category": parsed["category"],
        "body_html": parsed.get("body_html", ""),
        "engine": engine,
        "status": "DRAFT_READY",
        "publish_policy": "awaiting_approval",
        "duplicate_guard": True,
        "public_allowed": False,
    }
    structural_issues = structural_check(draft)
    if structural_issues:
        draft["status"] = "QUALITY_FAILED"
        draft["error"] = "; ".join(structural_issues)
        return draft
    draft["audit"] = audit_draft(draft, job)
    return draft


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default="artifacts/tistory-daily-plan.json")
    parser.add_argument("--output", default="artifacts/tistory-daily-drafts.json")
    args = parser.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    drafts = [generate_draft(job) for job in plan["jobs"]]

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
