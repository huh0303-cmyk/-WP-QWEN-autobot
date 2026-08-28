#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate one article draft per Tistory site job using Claude.

Reads a plan produced by tistory_daily_planner.py and writes drafts only —
this never publishes anything. Every job stays publish_policy=awaiting_approval
and public_allowed=false; a human (or a later approved workflow) posts it.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
from claude_text import claude_available, claude_generate_text  # noqa: E402

SYSTEM_PROMPT = (
    "You are a careful Korean/English blog writer for a Tistory site. "
    "Write a single, original, well-structured article. Never fabricate a "
    "date, amount, deadline, or eligibility rule — if the job requires an "
    "official source and you are not certain of a specific fact, say the "
    "reader should confirm it on the official site instead of guessing. "
    "Return strict JSON: {\"title\": str, \"category\": str, \"body_html\": str}. "
    "body_html must be simple HTML (h2/h3/p/ul/li only, no inline styles, no scripts)."
)


def build_prompt(job: dict) -> str:
    lines = [
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
    lines.append("Write the article now as the JSON object described in the system prompt.")
    return "\n".join(lines)


def generate_draft(job: dict) -> dict:
    if not claude_available():
        return {
            "job_id": job["job_id"],
            "site_id": job["site_id"],
            "status": "SKIPPED_CLAUDE_DISABLED",
            "public_allowed": False,
        }
    raw = claude_generate_text(build_prompt(job), system=SYSTEM_PROMPT, temperature=0.7)
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        parsed = json.loads(text)
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
    return {
        "job_id": job["job_id"],
        "site_id": job["site_id"],
        "title": parsed.get("title", ""),
        "category": parsed["category"],
        "body_html": parsed.get("body_html", ""),
        "status": "DRAFT_READY",
        "publish_policy": "awaiting_approval",
        "duplicate_guard": True,
        "public_allowed": False,
    }


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
        "claude_enabled": claude_available(),
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
