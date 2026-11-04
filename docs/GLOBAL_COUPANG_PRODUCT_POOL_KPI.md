# Global Coupang Product Pool — KPI and operating standard

## Objective
Maintain one shared, verified Coupang Partners product pool for all current and future blog domains. Every published post receives exactly 10 small product cards. Product combinations are stable for a given post but rotated across posts and domains, so the fleet does not repeat the same 10 items everywhere.

## Initial sourcing target: 200 verified offers
| Category | Target | Sourcing priorities |
|---|---:|---|
| K-Beauty | 40 | Korean skincare, sunscreen, serums, toner, masks, cleansers |
| K-Electronics | 40 | laptops, tablets, PCs, monitors, accessories |
| K-Health | 40 | CheongKwanJang / 정관장, Lactofit / 락토핏, omega-3, multivitamins |
| Korea Travel | 30 | Korea tours, Seoul/Busan/Jeju activities and package products actually sold on Coupang |
| Korea Hotels | 30 | Korea accommodation offers only where Coupang provides a real purchasable affiliate offer |
| K-Lifestyle | 20 | higher-interest household, kitchen and Korean lifestyle products |
| **Total** | **200** | |

## Sourcing and verification
- Product offers must be found in the user's logged-in Coupang Partners portal or another authorized account workflow.
- Generate the tracking URL through the user's own Coupang Partners account. Never construct, guess, or convert ordinary product URLs into affiliate URLs.
- Use the official product image supplied by Coupang, preferably its Coupang CDN image.
- Capture product title, current price, category, rating/review count and any available popularity/sales signal with capture timestamp.
- Reject broken/ambiguous links, missing images, unverified tracking attribution, counterfeit/unsafe items, and low-value filler items.
- Price floor is a soft filter (default KRW 10,000); premium useful products remain eligible. Popularity and relevance outrank cheap price.
- Korea hotel/travel package quotas are targets, not permission to invent Coupang inventory. If Coupang has no eligible hotel booking offer, report the shortfall and do not substitute an unrelated item.

## Rotation
- Shared catalog across all domains; no site-specific cloned pool.
- Every post gets 10 unique product URLs, using article relevance first and soft category distribution second.
- Default mix: 2 beauty, 2 electronics, 2 health, 1 Korea travel, 1 Korea hotel, 2 lifestyle. Underfilled categories are backfilled from the strongest remaining verified offers.
- Stable deterministic assignment per post ID + domain prevents cards changing on every page load; a rotation salt allows a later refresh campaign.
- Avoid giving every post the same 10-item set. Track exposure counts and penalize overused products.
- Reuse across different posts is allowed. Repeating one identical set across the whole fleet is not.
- Keep the 10-card layout compact: 5 columns desktop, 2 columns mobile, image, short title, tracked CTA, and disclosure.

## Fleet rollout
- First import and validate 200 offers.
- Run a read-only preview on K-Health365 and K-Trip365, then one pilot post per site.
- Verify rendered public pages, 10 unique tracked links, 10 valid images, disclosure, and preservation of body/featured image/SEO fields.
- Roll out in batches to all enabled WordPress and Blogger domains. Back up original content and maintain an idempotent marker.
- Future domains register to the shared pool; do not create a separate duplicate catalog unless a legal/provider constraint requires it.

## Current truthful status
The code and import schema are being prepared. The repository's current verified per-site lists do not yet constitute 200 distinct cross-domain offers. The pool remains empty until real account-generated URLs and official images are imported. This prevents fabricated links or placeholder products from being published.
