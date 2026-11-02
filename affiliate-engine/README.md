# London Project Affiliate Engine

Shared monetization engine for WordPress, Blogger/Blogspot, YouTube and TikTok.

## Business rule
Every article gets exactly 10 placements:
- 2 directly related to the article topic
- 2 K-beauty
- 2 K-health / health-food
- 1 Korea daily-life essential
- 1 travel package / tour / activity
- 1 K-pop album / official merchandise
- 1 data eSIM / SIM

Coupang Partners is mandatory in the affiliate mix. Trip.com, Agoda, Olive Young Global and Naver Travel Connect are selected when the product type is eligible and a real tracking URL is available.

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
