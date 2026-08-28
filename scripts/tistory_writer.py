#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate one article draft per Tistory site job.

2026-08-28 정책(사용자 지시): Gemini Flash(무료)가 주력 작가, GPT는 Gemini가
실패했을 때만 쓰는 escalation. Claude는 글을 쓰지 않고, 완성된 초안을 훑어
정책 위반(출처 없는 날짜/금액 등)이 있는지 감사(system audit)만 한다.

Reads a plan produced by tistory_daily_planner.py and writes drafts only —
this never publishes anything. Every job stays publish_policy=awaiting_approval
and public_allowed=false; a human (or a later approved workflow) posts it.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
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


def _parse_json_response(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def _write_body(job: dict) -> tuple[str, str]:
    """Returns (raw_response_text, engine_used). Gemini first; GPT only if
    Gemini fails outright (never silently — every fallback is logged)."""
    prompt = build_writer_prompt(job)
    try:
        return gemini_generate_text(prompt, temperature=0.7), "gemini"
    except Exception as gemini_err:
        if not openai_available():
            raise RuntimeError(f"Gemini failed and GPT escalation is unavailable: {gemini_err}") from gemini_err
        print(f"   ⚠️ Gemini 실패({gemini_err}) → GPT로 재작성")
        return openai_generate_text(prompt, temperature=0.7, max_retries=3), "gpt-rewrite"


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
