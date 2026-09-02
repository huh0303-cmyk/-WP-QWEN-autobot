#!/usr/bin/env python3
"""Fail CI when active automation paths drift from the 2026-08-27 operating policy."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"

BANNED_IMAGE_SECRET_REFS = (
    "secrets.PEXELS_API_KEY",
    "secrets.PEXELS_KEY",
    "secrets.PIXABAY_KEY",
    "secrets.STABILITY_API_KEY",
)
BANNED_DEPRECATED_CHANNEL_REFS = (
    "SCIENCE_FACTS_TIMES",
    "MYTH_LEGEND_TIMES",
    "CLASSIC_READS_TIMES",
    "CLASSICAL_JOURNAL",
    "AMERICAN_ARCHIVE_TIMES",
)
YOUTUBE_IMAGE_WORKFLOWS = (
    "generate-youtube-playlist.yml",
    "generate-youtube-video.yml",
    "refresh-playlist-thumbnails.yml",
    "health-clinic-daily.yml",
    "curio-longform-daily.yml",
)


def fail(msg: str) -> None:
    raise SystemExit(f"POLICY ERROR: {msg}")


def main() -> None:
    workflow_text = {}
    for path in WF.glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        workflow_text[path.name] = text
        for token in BANNED_IMAGE_SECRET_REFS:
            if token in text:
                fail(f"{path.name} still references banned image secret {token}")
        for token in BANNED_DEPRECATED_CHANNEL_REFS:
            if token in text:
                fail(f"{path.name} still references deprecated channel {token}")

    for name in YOUTUBE_IMAGE_WORKFLOWS:
        text = workflow_text.get(name, "")
        if not text:
            fail(f"missing expected workflow {name}")
        if "REPLICATE_API_TOKEN" not in text:
            fail(f"{name} does not receive REPLICATE_API_TOKEN")

    wp = workflow_text.get("daily-network-publish.yml", "")
    if 'AI_TEXT_PROVIDER: "openai"' not in wp or 'OPENAI_MODEL: "gpt-5-mini"' not in wp:
        fail("WordPress publisher is not routed to GPT-5 mini as the primary writer")
    if "secrets.OPENAI_API_KEY" not in wp or 'OPENAI_ENABLED: "true"' not in wp:
        fail("WordPress publisher lost its GPT-5 mini credentials")
    if "secrets.GEMINI_API_KEY" not in wp or 'GEMINI_REVIEW_MODEL: "gemini-2.5-flash"' not in wp:
        fail("WordPress publisher lost its Gemini independent-review route")
    wp_publisher = (ROOT / "scripts" / "autopost_mega.py").read_text(encoding="utf-8")
    if "def generate_content_gemini(prompt, use_gpt=False)" not in wp_publisher:
        fail("WordPress text generator lost its compatibility entrypoint")
    if "SEO_TARGET  = 70" not in wp_publisher:
        fail("WordPress publication threshold is not 70")
    wp_public_gate = (
        'publication_approved:' in wp
        and 'default: false' in wp
        and "inputs.publication_approved && 'publish' || 'draft'" in wp
        and "inputs.publication_approved && 'true' || 'false'" in wp
    )
    if not wp_public_gate:
        fail("ordinary WordPress workflow is not fail-closed behind explicit approval")

    newsroom = workflow_text.get("newsrooms-daily-publisher.yml", "")
    if 'WP_POST_STATUS: "publish"' not in newsroom or 'WP_PUBLICATION_APPROVED: "true"' not in newsroom:
        fail("newsroom workflow lacks explicit public-publication approval")
    if "newsroom-publisher-single-owner" not in newsroom or "for attempt in 1 2 3" not in newsroom:
        fail("newsroom workflow lost single-owner execution or bounded retries")
    if 'AI_TEXT_PROVIDER: "openai"' not in newsroom or 'OPENAI_MODEL: "gpt-5-mini"' not in newsroom:
        fail("newsroom workflow is not routed to GPT-5 mini")
    if 'GEMINI_REVIEW_MODEL: "gemini-2.5-flash"' not in newsroom:
        fail("newsroom workflow lost Gemini independent review")

    rankmath = workflow_text.get("daily-rankmath-check.yml", "")
    if "continue-on-error: true" in rankmath:
        fail("Rank Math health check can report workflow success after check failure")

    approved_upload = (ROOT / "scripts" / "youtube_publish_approved.py").read_text(encoding="utf-8")
    if "next_chunk(num_retries=0)" not in approved_upload or "max_retries = 3" not in approved_upload:
        fail("approved YouTube uploader lost its bounded single-owner retry policy")

    blogger = workflow_text.get("blogger-rewrite.yml", "")
    if "REPLICATE_API_TOKEN" not in blogger:
        fail("Blogger workflow is not wired to Replicate images")
    if "BLOGGER_GEMINI_MODEL" not in blogger:
        fail("Blogger workflow lost its Gemini text route")
    if 'BLOGGER_MIN_QUALITY_SCORE: "70"' not in blogger:
        fail("Blogger publication threshold is not 70")

    provider = (ROOT / "scripts" / "replicate_image_provider.py").read_text(encoding="utf-8")
    approved_models = (
        "bytedance/sdxl-lightning-4step",
        "black-forest-labs/flux-schnell",
    )
    for model in approved_models:
        if model not in provider:
            fail(f"approved image model missing: {model}")

    image_policy = json.loads((ROOT / "config" / "network_image_generation_policy.json").read_text(encoding="utf-8"))
    configured_models = tuple(item["model_id"] for item in image_policy["model_priority"])
    if configured_models != approved_models:
        fail(f"Replicate model policy drift: {configured_models}")

    topik = (ROOT / "scripts" / "topik_quiz_shorts.py").read_text(encoding="utf-8")
    if "generate_approved_image" not in topik or "openai_generate_image" in topik or "GEMINI_IMAGE_MODELS" in topik:
        fail("TOPIK review generator can escape the approved Replicate image gateway")
    topik_workflow = workflow_text.get("topik-quiz-daily.yml", "")
    if "REPLICATE_API_TOKEN" not in topik_workflow:
        fail("TOPIK review workflow lacks the shared Replicate token")

    registry = json.loads((ROOT / "config" / "youtube_channels.json").read_text(encoding="utf-8"))
    keys = {c["channel_key"] for c in registry["channels"] if c.get("enabled", True)}
    expected = {"globalmusic", "healing", "starbucks", "mbb", "kpop", "nasa", "history", "invention", "silent_era", "retro_reels"}
    if keys != expected:
        fail(f"enabled YouTube registry drift: {sorted(keys)}")

    print("Active automation policy audit: PASS")


if __name__ == "__main__":
    main()
