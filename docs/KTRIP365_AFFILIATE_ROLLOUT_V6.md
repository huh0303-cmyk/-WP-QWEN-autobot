# K-Trip365 Coupang affiliate rollout (v6)

## Required layout

### Header buttons (one row)
1. Coupang Partners — branded image/tile linked to the verified Coupang Partners destination URL.
2. OLIVE YOUNG — branded image/tile linked to the verified Olive Young affiliate destination URL.
3. Trip.com — branded image/tile linked to the verified Trip.com affiliate destination URL.

These three are header buttons only. They are not counted among the ten product cards.

### Bottom product cards (exactly ten; Coupang Partners only)
- 2 K-Beauty / cosmetics
- 1 laptop
- 1 desktop PC
- 2 K-Health dietary supplements (examples for search: omega-3, Lactofit probiotics, CheongKwanJang red ginseng; only use genuine available listings)
- 2 Korea travel packages
- 2 Korea hotel products

All ten products must have account-generated Coupang Partners tracking URLs and official product images captured from the Coupang Partners portal. Do not substitute ordinary shopping URLs or guessed tracking URLs.

## Rotation and site isolation
- Maintain a separate product pool for each site; K-Trip365 must never borrow another site's catalog.
- Target a site-specific pool of about 100 verified offers: 20 beauty, 10 laptops, 10 desktop PCs, 20 supplements, 20 Korea travel packages, 20 Korea hotel products.
- Use different ten-item combinations across batches; normally rotate the combination every 10–20 posts. Do not force a unique set on every single post.
- Select the two items within each category for relevance to the article and K-Trip365 audience.
- Store the selection/rotation key and exact product IDs per post so future runs are deterministic and auditable.

## Existing published posts
- Inventory all published K-Trip365 posts using WordPress REST API with edit context.
- Back up each original raw content plus status, date, featured image and SEO metadata before the first write.
- Replace only the designated London Project affiliate block. Preserve all editorial content and all unrelated markup.
- Pilot one published post first; read back the raw content and fetch the public URL.
- Require exactly 3 header buttons, exactly 10 Coupang cards, 10 unique tracking URLs, 10 official images, one disclosure, correct 2/1/1/2/2/2 category counts, and HTTP 200 public read-back.
- Batch the remaining posts only after the pilot passes. Record per-post results and failures; never mark unverified posts as successful.

## New posts (mandatory)
- Integrate the same renderer into the canonical WordPress publishing path after article content is generated and before the post is published.
- Fail closed if the site-specific catalog lacks any required category, an affiliate URL is not portal-captured, an official image is missing, or the final count/category mix is wrong.
- Do not publish a new K-Trip365 post without the three header buttons and ten bottom Coupang cards.
- Keep the disclosure and product block idempotent: retries must replace the existing managed block, not append duplicates.

## Current implementation warning
The policy is now version 6. Existing K-Trip365 data includes older fixed ten-product catalogs and previous backfill scripts. Those files are not proof that the v6 mix is ready or that live posts have been updated. Do not run a legacy mass-update script until the site-specific pool has been rebuilt and the v6 category validation is implemented. No live WordPress posts are changed by this policy/documentation commit.
