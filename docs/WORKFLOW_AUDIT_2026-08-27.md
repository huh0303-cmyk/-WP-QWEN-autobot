# Workflow Audit — 2026-08-27

## Confirmed defects repaired

1. Newsroom HTML cap reserved 450 characters and could trim a corrected article to 1,550, below its 1,750 target/minimum gate. The trim target is now bounded by `min_chars`; regression coverage reproduces the minimum-crossing condition.
2. Enabled `kskin365.com` still had a `Retired Site` author identity. It now has an active skincare editorial identity.
3. Situation-room reporting hard-coded 21 historical YouTube channels, including retired families. It now combines the canonical 10-channel scheduler registry with a separate six-channel strategic reporting registry and rejects duplicate labels/IDs.
4. Search Console sitemap aggregates were displayed as generic `색인수`. New writes identify them as `사이트맵 보고 색인수`; result records expose `sitemap_indexed` and `sitemap_submitted`. Compatibility alias remains temporarily for old readers.
5. A dead schedule-only random-delay step was removed from the manual-only multilingual review workflow.
6. The weekly Rank Math health check could fail while the workflow continued as successful. The core check now fails closed; report commit remains available through `if: always()`.
7. The approved YouTube uploader and TOPIK review uploader nested five client retries inside an eight-attempt outer loop. Each now has one retry owner, a three-attempt ceiling, and an eight-second maximum backoff.

## Provider/model policy findings

- Active WP workflow supplies OpenAI text and disables OpenAI/Gemini image generation.
- The paid-image policy tests block legacy paid image opt-ins.
- Approved Replicate provider code uses `REPLICATE_API_TOKEN` and only the three MASTER-approved models.
- Blogger prose is Gemini-generated. Its optional Pexels/Pixabay stock-photo lookup is not a generated-thumbnail fallback and does not use a paid AI image provider; it remains a policy-review item rather than being deleted blindly.
- YouTube generated-thumbnail policy remains FLUX Schnell. No legacy generated-image provider was enabled.

## High-risk unresolved items (not deleted)

- Blogger daily generation and Sheet queue now share a destination/source identity lock. Existing historical rows remain compatible through `site_id + source_keyword` matching.
- Ordinary WP direct publishing remains enabled in `daily-network-publish.yml`; whether this is an approved production path versus review-first requires owner confirmation. `wp-create-draft.yml` exists for explicit draft tests.
- The newsroom workflow has 20 daily cron entries across two newsrooms. This matches the configured maximum of 10/site/day but is cost/volume sensitive; no schedule was removed without business confirmation.
- Registry count is 25 ordinary WP + 2 newsrooms while owner planning language says 26 + 2. No site was invented or deleted.
- AdSense, YouTube revenue/watch time, platform engagement, and provider billing credentials are not connected in the repository; control Sheet marks these `연결 필요`.
- `continue-on-error` remains on non-core notification/Drive-review upload steps. Core publishers themselves must continue to fail closed; each remaining case needs path-specific review.
- Retired/manual upload scripts still contain older retry implementations. They were not deleted or rewritten because they are outside the active scheduler graph and their business retention status is not established.
- A thumbnail-set failure can occur after a YouTube video has already uploaded. The uploader records the error, but automatic rollback/re-upload was not added because that could create duplicate publications; this needs an explicit recovery policy.

## Workflow classification

- ACTIVE: Blogger scheduler, platform queue, WP scheduler, WP downstream publisher, newsroom publisher, YouTube controller, site metrics, situation room, weekly keywords, weekly RankMath.
- MANUAL/DOWNSTREAM: all items listed in `AUTOMATION_TOPOLOGY.md` manual section.
- DUPLICATE-SUSPECT: Blogger daily scheduler vs Sheet queue.
- DESTRUCTIVE MANUAL: prune-unindexed posts.

## Validation performed

- Full local unit suite: 46 tests.
- Python compilation: active approved YouTube uploader, TOPIK review uploader, and active-policy auditor.
- Active-policy audit: PASS. Automation Hub configuration validation: PASS.
- No production content generation, image generation, public posting, or paid API call was made.
