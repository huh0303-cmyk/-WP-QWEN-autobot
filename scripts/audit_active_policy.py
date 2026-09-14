#!/usr/bin/env python3
"""Fail CI when active automation paths drift from the operating policy.

2026-09-03: CEO decision — Gemini is removed as an editorial reviewer
network-wide (WP, Blogger, Tistory, newsrooms). It kept blocking every
draft on real billing outages, and even when reachable its own factual
judgment on a newsroom rewrite had no route to try a different article,
stalling koreanews365/theseouljournal at 0 published for a full day.
Two independent cold-context GPT passes replace it everywhere. This
audit now asserts Gemini's ABSENCE from every reviewer role instead of
its presence — the reverse of the pre-2026-09-03 policy.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"

GEMINI_REVIEWER_TOKENS = (
    "GEMINI_REVIEW_MODEL",
    "BLOGGER_GEMINI_MODEL",
    "gemini_generate",
)
REVIEWER_WORKFLOWS = (
    "daily-network-publish.yml",
    "newsrooms-daily-publisher.yml",
    "blogger-rewrite.yml",
    "tistory-daily-plan.yml",
    "sheet-triggered-auto-write.yml",
)

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
    keyword_policy = json.loads((ROOT / "config" / "golden_keyword_policy.json").read_text(encoding="utf-8"))
    viral_sites = keyword_policy.get("viral_general_sites", {})
    expected_viral_sites = {
        "wordpress": {"https://koreanews365.com", "https://korea365.org"},
        "blogger": {"https://korea365guide.blogspot.com"},
        "tistory": {"https://huh0303.tistory.com"},
    }
    for platform, expected_urls in expected_viral_sites.items():
        if set(viral_sites.get(platform, [])) != expected_urls:
            fail(f"viral general-site registry drift for {platform}: {viral_sites.get(platform, [])}")
    if viral_sites.get("topic_mode") != "today_cross_media_repeated_nouns_first" or viral_sites.get("cross_category") is not True:
        fail("viral general sites lost today's cross-media noun-first, cross-category routing")
    required_examples = {"용혜인", "김승원", "민주당", "추석 예매", "대통령 지지율", "KBO", "손흥민"}
    if not required_examples.issubset(set(viral_sites.get("entity_examples", []))):
        fail("viral general-site entity examples drifted from the CEO lock")

    consensus_src = (ROOT / "scripts" / "three_model_consensus.py").read_text(encoding="utf-8")
    if "gemini_generate(" in consensus_src:
        fail("three_model_consensus.py still invokes gemini_generate — Gemini reviewer must stay uncalled")
    if "gpt_1" not in consensus_src or "gpt_2" not in consensus_src:
        fail("three_model_consensus.py is not running two independent GPT passes")

    for name in ("queue_blogger_rewrite.py", "tistory_writer.py"):
        src = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        if "gemini_generate" in src or "three_model_consensus" in src:
            fail(f"{name} re-wired Gemini/consensus review — Blogger/Tistory use a GPT-only quality gate")

    workflow_text = {}
    for path in WF.glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        workflow_text[path.name] = text
        for token in BANNED_IMAGE_SECRET_REFS:
            if token in text:
                stock_authorized = (path.name in (*REVIEWER_WORKFLOWS, "stock-image-preflight.yml")
                                    and token in ("secrets.PEXELS_API_KEY", "secrets.PIXABAY_KEY"))
                if not stock_authorized:
                    fail(f"{path.name} still references banned image secret {token}")
        for token in BANNED_DEPRECATED_CHANNEL_REFS:
            if token in text:
                fail(f"{path.name} still references deprecated channel {token}")
        if path.name in REVIEWER_WORKFLOWS:
            for token in GEMINI_REVIEWER_TOKENS:
                if token in text:
                    fail(f"{path.name} still wires Gemini into a reviewer role via {token}")

    for name in YOUTUBE_IMAGE_WORKFLOWS:
        text = workflow_text.get(name, "")
        if not text:
            fail(f"missing expected workflow {name}")
        if name == "generate-youtube-playlist.yml":
            if any(token in text for token in ("secrets.REPLICATE_API_TOKEN", "secrets.OPENAI_API_KEY", "secrets.GEMINI_API_KEY")):
                fail("playlist must not receive paid generation credentials")
        elif "REPLICATE_API_TOKEN" not in text:
            fail(f"{name} does not receive REPLICATE_API_TOKEN")

    # YouTube rendering is VPS-owned. The retained Actions definitions are
    # emergency documentation only and must stay un-runnable.
    for name in ("youtube-control-scheduler.yml", "generate-youtube-playlist.yml", "curio-longform-daily.yml"):
        if "if: ${{ false }}" not in workflow_text.get(name, ""):
            fail(f"{name} can still run; YouTube production must be VPS-only")
    vps_readme = (ROOT / "deploy" / "vps" / "README.md").read_text(encoding="utf-8")
    if "Hostinger VPS is the sole production host" not in vps_readme:
        fail("Hostinger VPS single-host contract is missing")
    control_source = (ROOT / "control_center" / "app.py").read_text(encoding="utf-8")
    vps_worker = (ROOT / "scripts" / "youtube_vps_worker.py").read_text(encoding="utf-8")
    playlist = (ROOT / "scripts" / "youtube_playlist_maker.py").read_text(encoding="utf-8")
    if "enqueue_youtube_vps" not in control_source or "youtube-control-scheduler.yml" in control_source:
        fail("control center YouTube buttons are not exclusively routed to the VPS queue")
    if 'os.environ.get("PLAYLIST_MUSIC_SOURCE", "approved_bank")' not in playlist:
        fail("playlist must default to prepared music rather than paid generation")
    queue = (ROOT / "automation_hub" / "youtube_vps_queue.py").read_text(encoding="utf-8")
    if "cost_hold_active" not in queue or "/etc/korea365/youtube-cost-hold" not in queue:
        fail("VPS YouTube queue lost the active cost-hold check")
    if "youtube_calendar_result.py" not in vps_worker or "youtube_publish_approved.py" not in vps_worker:
        fail("VPS worker lost calendar reporting or private playlist upload")
    for name in ("archive_footage_longform.py", "nasa_archive_longform.py"):
        source = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        if "generate_thumbnail" not in source or "flux_thumbnail_provider" in source:
            fail(f"{name} is not using fresh Gemini thumbnail generation")

    wp = workflow_text.get("daily-network-publish.yml", "")
    if 'AI_TEXT_PROVIDER: "openai"' not in wp or 'OPENAI_MODEL: "gpt-5-mini"' not in wp:
        fail("WordPress publisher is not routed to GPT-5 mini as the primary writer")
    if "secrets.OPENAI_API_KEY" not in wp or 'OPENAI_ENABLED: "true"' not in wp:
        fail("WordPress publisher lost its GPT-5 mini credentials")
    wp_publisher = (ROOT / "scripts" / "autopost_mega.py").read_text(encoding="utf-8")
    if "def generate_content_gemini(prompt, use_gpt=False)" not in wp_publisher:
        fail("WordPress text generator lost its compatibility entrypoint")
    if "SEO_TARGET  = 70" not in wp_publisher:
        fail("WordPress publication threshold is not 70")
    # 2026-09-03 CEO decision: manual per-item review doesn't scale past
    # ~30 drafts/day, so ordinary WP publishing now defaults to public once
    # the two-pass GPT editorial gate approves — that gate is unconditional
    # either way (require_editorial_approval always runs before wp_post()
    # can save anything). Assert the switch defaults to auto-publish and
    # still wires to the same status mapping, not that it's fail-closed.
    wp_public_gate = (
        'publication_approved:' in wp
        and 'default: true' in wp
        and "inputs.publication_approved && 'publish' || 'draft'" in wp
        and "inputs.publication_approved && 'true' || 'false'" in wp
    )
    if not wp_public_gate:
        fail("ordinary WordPress workflow lost its auto-publish-on-gate-pass default")

    newsroom = workflow_text.get("newsrooms-daily-publisher.yml", "")
    if 'WP_POST_STATUS: "publish"' not in newsroom or 'WP_PUBLICATION_APPROVED: "true"' not in newsroom:
        fail("newsroom workflow lacks explicit public-publication approval")
    if "newsroom-publisher-single-owner" not in newsroom or newsroom.count("python scripts/autopost_current.py") != 1 or "for attempt in" in newsroom:
        fail("newsroom must retain a single owner and one generation attempt per RSS event")
    if 'AI_TEXT_PROVIDER: "openai"' not in newsroom or 'OPENAI_MODEL: "gpt-5-mini"' not in newsroom:
        fail("newsroom workflow is not routed to GPT-5 mini")
    if "- cron:" in newsroom or "source_item:" not in newsroom or "source_url:" not in newsroom:
        fail("newsrooms must consume newly detected RSS stories without a daily publication quota")
    newsroom_source = (ROOT / "scripts" / "autopost_mega.py").read_text(encoding="utf-8")
    if "pool = candidates if exact_source_url else preferred_candidates or candidates" not in newsroom_source:
        fail("RSS publisher must honor the exact detected source before optional category preferences")

    rankmath = workflow_text.get("daily-rankmath-check.yml", "")
    if "continue-on-error: true" in rankmath:
        fail("Rank Math health check can report workflow success after check failure")

    approved_upload = (ROOT / "scripts" / "youtube_publish_approved.py").read_text(encoding="utf-8")
    if "next_chunk(num_retries=0)" not in approved_upload or "max_retries = 3" not in approved_upload:
        fail("approved YouTube uploader lost its bounded single-owner retry policy")

    blogger = workflow_text.get("blogger-rewrite.yml", "")
    if "REPLICATE_API_TOKEN" not in blogger:
        fail("Blogger workflow is not wired to Replicate images")
    if 'BLOGGER_MIN_QUALITY_SCORE: "70"' not in blogger:
        fail("Blogger publication threshold is not 70")

    if "load_live_general_keyword(site)" not in wp_publisher or 'GENERAL_VIRAL_WP_SITES = {"https://korea365.org"}' not in wp_publisher:
        fail("korea365.org lost live cross-media general-topic routing")
    tistory_plan = workflow_text.get("tistory-daily-plan.yml", "")
    tistory_planner = (ROOT / "scripts" / "tistory_daily_planner.py").read_text(encoding="utf-8")
    if 'TISTORY_LIVE_TRENDS_ENABLED: "true"' not in tistory_plan or "live_cross_media_noun_frequency" not in tistory_planner:
        fail("huh0303.tistory.com lost live cross-media general-topic routing")

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
