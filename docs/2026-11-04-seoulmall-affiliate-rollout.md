# Seoulmall Store Setup & Product Rotation — 2026-11-04

## Store profile
- Store name: Seoulmall
- Public storefront URL to use: https://influencers.coupang.com/s/seoulmall
- Previous URL (legacy only): https://influencers.coupang.com/s/seoulshop
- Description: Beyond BTS, discover Korea
- Connected YouTube: @seoul_topik1

## Storefront URL
The requested public slug is `seoulmall`, replacing the old `seoulshop` slug. The authenticated Coupang Influencer portal must be used for the account-side slug change. A repository/configuration edit does not change the public route. Verify that https://influencers.coupang.com/s/seoulmall resolves to this Seoulmall storefront before publishing it as a live destination. Keep the old URL only as a legacy reference.

## Six existing collections (categories)
The user has already renamed/configured the six collections in Coupang Influencer. Do not recreate them or rename them again. Populate each collection with approximately 20 relevant products (target 20–25 products per collection):

1. **K-Beauty** — Korean cosmetics and popular beauty products.
2. **K-Health** — health functional foods and health-management products.
3. **K-Life** — Korean daily-life essentials and popular lifestyle products.
4. **K-Tour package** — popular Korea travel products and packages.
5. **K-Hotels** — popular hotels.
6. **K-Digitals** — laptops and tablet PCs.

Target inventory: approximately 120–150 products total across the six collections. Each product must be a real, currently available Coupang product with its genuine product image and the user's valid Coupang Partners tracking link where applicable. Avoid duplicates within a collection; prefer distinct, relevant, popular products and a sensible range of prices. Do not invent product URLs, images, tracking codes, or collection contents.

## Random rotation requirement
Do not permanently show the same fixed products in the same order everywhere. Randomly rotate product selection and display order from the relevant collection pool:
- Shuffle the eligible products within each collection for each new placement or refresh cycle.
- Select products randomly from the matching collection, without duplicates within a single placement.
- Keep category relevance: choose from K-Beauty for beauty content, K-Health for health content, etc.; use mixed categories only when the content or placement is general-purpose.
- Track previously used product IDs per post/channel so rotation can reduce immediate repeats and spread exposure across the full 20–25-product pool.
- Use a reproducible random seed or saved selection history per run so interrupted jobs can resume without changing already completed placements.
- Never randomize away product names, images, affiliate URLs, or collection/category identity; each card must remain correctly matched.
- Random rotation means varied selection/order, not changing the products on every page load in a way that prevents stable verification.

## Placement and verification
- Add the verified Seoulmall storefront link to eligible owned channels and content placements.
- Where product cards are appropriate, use genuine product images and verified account-attributed affiliate URLs.
- Do not impose the old rule requiring every article to contain ten products split into five fixed categories. Select a small, relevant rotating set only where appropriate.
- Preserve existing article text, titles, slugs, publication status, dates, featured images, SEO metadata, and unrelated links.
- Include the required affiliate disclosure.
- Record scanned, eligible, updated, verified, skipped, and error counts. A preview or queued workflow is not a completed placement.

## Platform execution order
1. WordPress
2. Blogger / Blogspot
3. YouTube
4. TikTok
5. Facebook
6. Instagram
7. Threads

Adapt the placement method to each platform's actual link capabilities. For example, do not assume ordinary Instagram captions make URLs clickable. Preserve existing content and verify each placement.

## Run safety
- Preview first; then apply in small batches with checkpoints.
- Resume from the last verified checkpoint and prevent duplicate insertions.
- Do not report completion without read-back or equivalent verification.
- No VPS. Use local execution / GitHub Actions only when credentials and secrets are available and validated.
- WPVibe is excluded.
