# London Project Affiliate Engine

Shared monetization engine for WordPress, Blogger/Blogspot, YouTube and TikTok.

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
7. Expand to the full WordPress and Blogspot inventories.

## New-content runner

`runner.py` polls the registered WordPress and Blogger destinations for recent
posts, appends a marked block only when all ten verified offers are available,
and skips any post already containing the marker. The scheduled GitHub Actions
workflow is dry-run only. A real write needs an explicit manual `write` run and
the `AFFILIATE_WRITE_ENABLED=true` GitHub secret.

Add approved tracking URLs to `data/catalogs/{site_key}.json`; do not commit API keys,
passwords, tokens, or unverified URLs.
