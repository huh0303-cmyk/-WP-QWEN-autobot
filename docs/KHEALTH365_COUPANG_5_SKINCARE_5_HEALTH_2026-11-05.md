# K-Health365 Coupang Partners workflow: 5 skincare + 5 health

Date: 2026-11-05 KST
Task: khealth365-coupang-5-beauty-5-health

## Locked product composition
- Exactly 10 products per published article footer.
- 5 K-Beauty skincare products: toner, moisturizer, sunscreen, essence/serum.
- 5 health functional food/supplement products.
- Every card uses its own Coupang Partners affiliate URL and account-generated official Coupang image creative.
- No stock images, search thumbnails, guessed image URLs, or substitute products are allowed.
- Existing catalog entries are replaceable. The catalog is the source of truth; product refreshes replace entries only after new account-generated affiliate URL and official image are captured and validated.

## Current catalog
- Beauty 5: Anua Heartleaf toner; Torriden Dive-In toner; Round Lab Birch moisturizer; Beauty of Joseon Relief Sun; COSRX Snail Dual Essence.
- Health 5: Lacto-Fit Gold probiotics; RTG Omega-3 + vitamin D; Nutrione lutein/zeaxanthin; collagen supplement; CJ BioCore probiotics.
- 10 unique affiliate URLs and 10 distinct Coupang CDN image URLs are stored in config/affiliate/k-health365-sitewide-10.json.
- Beauty records are derived from the authenticated Coupang Partners-generated product-tag capture in data/affiliate/oliveyoung-kskin365-verified-product-pool.json. Health records reuse five existing account-confirmed K-Health365 entries.
- These are valid registered account-generated links and creative URLs in the repository; image HTTP status and public page rendering still require a workflow run.

## Workflow
- GitHub Actions manual workflow: .github/workflows/khealth365-coupang-10.yml
- Default mode is preview (read-only).
- Apply mode replaces the managed affiliate footer section and adds the fixed 5+5 composition. Existing article body text is retained; the managed affiliate area is rebuilt, not duplicated.
- Optional limit allows a small pilot. 0 means all published K-Health365 posts.
- GitHub secrets required: KHEALTH365_WP_USER and KHEALTH365_WP_APP_PASSWORD.
- The script validates exactly 5 beauty + 5 health products, 10 distinct affiliate URLs and 10 distinct official image URLs before touching WordPress.
- The script checks authenticated REST read-back and public rendered affiliate links after updates.
- Every run uploads output/khealth365-sitewide-10-report.json as an audit artifact.

## Safety / rollout
1. Run preview with limit 1.
2. Inspect report and verify that it identifies exactly 10 products and the intended post.
3. Apply with limit 1; verify desktop/mobile public page and image display.
4. Only after the pilot succeeds, run preview with limit 0 and inspect the full post count.
5. Apply all only after reviewing the full preview report.
6. Never report completion based only on a successful GitHub Actions status; require post-level REST and public-render evidence.

## Important limitation
The current image resolver scrapes the Open Graph image from the Coupang affiliate destination only when image_url is blank. This workflow starts with populated official image creatives. Actual image HTTP response and rendered browser visibility are verified during the pilot; they are not claimed as completed by catalog registration alone.
