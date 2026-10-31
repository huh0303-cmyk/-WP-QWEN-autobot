# OliveYoungKorea + Kskin365 Coupang Partners rollout

Date: 2026-11-01 KST
Task ID: oliveyoung-kskin365-coupang-all-posts-20261101

## Goal
Place eight relevant, account-generated Coupang Partners products at the end of every published post on both WordPress sites. Keep each post's original editorial content and use a varied product mix selected from a shared skincare/K-beauty pool.

## Sites and post scope
- OliveYoungKorea: 64 published posts.
- Kskin365: 104 published posts.
- Total: 168 published posts.
- Planned placement: 8 unique products per post, 1,344 product placements.

## Verified product pool
- 50 Coupang Partners search candidates were prepared.
- 47 candidate products were successfully captured with official account-generated blog tags and affiliate URLs.
- Deduplicated identical product IDs and excluded one generic cleansing brush result that did not match the requested branded device.
- Final verified pool: 45 unique products with official affiliate URLs and official Coupang image creatives.
- Search result selection used the Coupang Partners default Coupang-ranking order and the first matching result for each search query. Do not describe this as a verified sales-volume ranking.
- Product pool file: `data/affiliate/oliveyoung-kskin365-verified-product-pool.json`.
- Raw portal capture log: `reports/oliveyoung-kskin365-coupang-products-2026-11-01.ndjson`.

## Per-post product selection
- 3 products selected for topic relevance.
- 2 daily skincare essentials (cleanser, toner, sunscreen, or moisturizer).
- 2 premium/high-ticket products.
- 1 additional randomized product.
- Frequency balancing is used to avoid overexposing the same products.
- Validation: 168 posts mapped; each has exactly 8 unique products; all 168 product combinations are unique.
- Placement map: `reports/oliveyoung-kskin365-affiliate-placement-map-2026-11-01.json`.

## Affiliate markup
- Uses the exact Coupang Partners account-generated affiliate URL and official image creative.
- Each product has a clickable image, linked English product title, and a current-price CTA.
- The affiliate disclosure is included in English and the required Korean wording.
- Products are appended at the end of each post inside a replaceable marker section. Re-runs replace that section instead of duplicating it.

## Editorial cleanup completed before affiliate insertion
- OliveYoungKorea: 8 repeated inline-image blocks removed from duplicate posts; original posts and media-library assets retained.
- Kskin365: 6 cross-post duplicate inline-image blocks and 1 within-post duplicate image removed; one duplicate title corrected on post 2905.
- Cleanup was applied with authenticated WordPress REST updates and read-back/public rendering verification.
- No posts or media-library assets were deleted.

## Execution controls
- Use Desktop Commander + PowerShell for local/browser/repository tasks.
- WPVibe is disabled and must not be used.
- WordPress updates use the two site-specific GitHub secrets.
- The insertion workflow has dry_run and apply modes. Run dry_run first and inspect the artifact before apply.
- Verify every post's eight unique affiliate URLs in authenticated read-back and the public rendered page.
- Never report completion until all 168 posts are updated or explicitly accounted for in the report.
