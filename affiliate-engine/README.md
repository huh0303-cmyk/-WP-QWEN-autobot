# London Project Affiliate Engine

Shared monetization engine for every enabled destination in the control.korea365.org registry, excluding only Naver Blog and Tistory; includes WordPress, Blogger/Blogspot and supported social/video destinations.

## Business rule
Every eligible article gets exactly 10 affiliate placements:
- 4 Coupang Partners
- 2 Olive Young Global
- 2 Trip.com
- 2 Agoda

Every WordPress domain and every Blogger blog has its own separate catalog. Each
catalog must have verified, topic-appropriate offers, real account-generated
tracking URLs, and permitted product images. The engine blocks a post if any
provider slot is missing or irrelevant; it never invents links or commission
rates. Commission rates are read from the current provider dashboard/terms.

## Revenue objective
Optimize confirmed commission per qualified visitor, not commission percentage alone. Evaluate topic relevance, intent, effective commission, order value, conversion evidence, cookie/attribution rules, availability and cancellations/refunds.

## Publishing rules
- Preserve all existing article content and affiliate links.
- Append new affiliate cards only; never delete or overwrite existing material.
- Idempotency key prevents duplicate insertion.
- Use only verified partner tracking URLs and permitted image sources.
- Clearly disclose affiliate relationships.
- If a required slot has no eligible product or verified tracking URL, hold the post in review; never invent a URL.
- Blogger content must be independently written, not copied verbatim from WordPress.
- YouTube links go in descriptions/pinned comments where allowed.
- TikTok links use only features available to that account and region.

## Current deployment status
This commit establishes the shared policy/configuration and a manual validation workflow. It does NOT claim affiliate links have been generated or posts modified.

## Rollout
1. Validate partner tracking-link inventory and image rights.
2. Connect each WordPress site's authorized REST credentials.
3. Connect Blogger via OAuth and enumerate Blog IDs.
4. Dry-run K-Trip365's published posts in batches of five.
5. Review generated cards and link checks.
6. Enable writes only after pilot verification.
7. Expand to every enabled WordPress and Blogger destination in the control-center registry.

## New-content runner

`runner.py` polls the registered WordPress and Blogger destinations for recent
posts, appends a marked block only when all ten verified offers are available,
and skips any post already containing the marker. The scheduled GitHub Actions
workflow is dry-run only. A real write needs an explicit manual `write` run and
the `AFFILIATE_WRITE_ENABLED=true` GitHub secret.

Add approved tracking URLs to `data/catalogs/{site_key}.json`; do not commit API keys,
passwords, tokens, or unverified URLs.


## YouTube and social 10-link workflow

The canonical workflow is `.github/workflows/london-social-affiliate-10-links.yml`.
It covers all 23 current YouTube master channels and every TikTok, Facebook,
Instagram and Threads account row in `config/sns_six_channel_policy.json`.
It creates one independently retryable job per destination and validates the
exact 4+2+2+2 allocation (10 total) against a destination-specific catalog.
See `docs/LONDON_SOCIAL_YOUTUBE_10_LINK_WORKFLOW_2026-11-03.md`.

The queue builder is intentionally non-publishing. New-content publishers can
send the `london_content_published` repository_dispatch event; existing-content
backfills can be started manually. The workflow stores a queue artifact and
explicit blockers. Platform OAuth write adapters and receipt-backed live
publishing remain disabled until each account is authorized and the adapter
is implemented.
