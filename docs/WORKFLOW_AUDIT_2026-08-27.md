# Workflow Audit — 2026-08-27

## Confirmed defects repaired

1. Newsroom HTML cap reserved 450 characters and could trim a corrected article to 1,550, below its 1,750 target/minimum gate. The trim target is now bounded by `min_chars`; regression coverage reproduces the minimum-crossing condition.
2. Enabled `kskin365.com` still had a `Retired Site` author identity. It now has an active skincare editorial identity.
3. Situation-room reporting hard-coded 21 historical YouTube channels, including retired families. It now combines the canonical 10-channel scheduler registry with a separate six-channel strategic reporting registry and rejects duplicate labels/IDs.
4. Search Console sitemap aggregates were displayed as generic `색인수`. New writes identify them as `사이트맵 보고 색인수`; result records expose `sitemap_indexed` and `sitemap_submitted`. Compatibility alias remains temporarily for old readers.
5. A dead schedule-only random-delay step was removed from the manual-only multilingual review workflow.

## Provider/model policy findings

- Active WP workflow supplies OpenAI text and disables OpenAI/Gemini image generation.
- The paid-image policy tests block legacy paid image opt-ins.
- Approved Replicate provider code uses `REPLICATE_API_TOKEN` and only the three MASTER-approved models.
- Blogger prose is Gemini-generated. Its optional Pexels/Pixabay stock-photo lookup is not a generated-thumbnail fallback and does not use a paid AI image provider; it remains a policy-review item rather than being deleted blindly.
- YouTube generated-thumbnail policy remains FLUX Schnell. No legacy generated-image provider was enabled.

## High-risk unresolved items (not deleted)

- Blogger duplicate ownership between daily scheduler and Sheet queue lacks a cross-path stable content lock.
- Ordinary WP direct publishing remains enabled in `daily-network-publish.yml`; whether this is an approved production path versus review-first requires owner confirmation. `wp-create-draft.yml` exists for explicit draft tests.
- The newsroom workflow has 20 daily cron entries across two newsrooms. This matches the configured maximum of 10/site/day but is cost/volume sensitive; no schedule was removed without business confirmation.
- Registry count is 25 ordinary WP + 2 newsrooms while owner planning language says 26 + 2. No site was invented or deleted.
- AdSense, YouTube revenue/watch time, platform engagement, and provider billing credentials are not connected in the repository; control Sheet marks these `연결 필요`.
- `continue-on-error` remains on non-core notification/Drive-review upload steps. Core publishers themselves must continue to fail closed; each remaining case needs path-specific review.

## Workflow classification

- ACTIVE: Blogger scheduler, platform queue, WP scheduler, WP downstream publisher, newsroom publisher, YouTube controller, site metrics, situation room, weekly keywords, weekly RankMath.
- MANUAL/DOWNSTREAM: all items listed in `AUTOMATION_TOPOLOGY.md` manual section.
- DUPLICATE-SUSPECT: Blogger daily scheduler vs Sheet queue.
- DESTRUCTIVE MANUAL: prune-unindexed posts.

## Validation performed

- Full local unit suite: 36 tests.
- Python compilation: `autopost_mega.py`, `situation_room_daily.py`, `daily_site_traffic.py`.
- No production content generation, image generation, public posting, or paid API call was made.
