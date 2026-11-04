# Seoulmall Affiliate Rollout — 2026-11-04

## User-approved execution order
1. WordPress (WP)
2. Blogger / Blogspot
3. YouTube
4. TikTok
5. Facebook
6. Instagram
7. Threads

Process each platform in order. Complete eligible destinations, verify placements, record counts/errors, then proceed. Do not reorder unless the user changes this instruction.

## Required Seoulmall destination
- Requested storefront slug: `seoulmall`
- Requested URL: `https://influencers.coupang.com/s/seoulmall`
- Previous URL: `https://influencers.coupang.com/s/seoulshop`
- IMPORTANT: changing a Coupang Influencer storefront slug is an account-side portal action. A code/config edit does not change the public route. Change the slug in the authenticated Coupang Influencer portal, then open the requested URL and verify it resolves to the user's Seoulmall storefront. Until verified, do not publish the new URL as a live destination; retain the previous URL only as a recorded legacy value.

## Placement requirements
- Existing eligible blog posts: add both (a) the verified Seoulmall storefront link and (b) ten verified Coupang product image cards.
- Product mix per post: 2 topic-relevant, 2 Korean daily-life/popular, 2 K-Beauty, 2 K-Health dietary supplements, 2 eSIM/USIM/mobile data/roaming.
- Use each site's own verified product catalog and account-attributed affiliate URLs. Never borrow another site's products or fabricate tracking/image URLs.
- Include a clear affiliate disclosure near the placement and respect platform-specific rules.
- Do not overwrite article body text, title, slug, status, publish date, featured image, SEO metadata, or unrelated links. Make only idempotent, marked insertions in approved fields.
- Do not force irrelevant product cards into unrelated content. Record exclusions.

## Platform-specific handling
- WordPress: add storefront link + ten image cards to eligible existing published posts; read each updated post back to verify.
- Blogger/Blogspot: same policy; use Blogger API and verify each updated post.
- YouTube: add verified storefront link and relevant product links in descriptions/pinned comments where supported; preserve existing descriptions.
- TikTok: use profile/link-in-bio and relevant video descriptions/comments only where clickable links are supported.
- Facebook: use Page profile/CTA and relevant post copy; preserve existing content.
- Instagram: use profile link and supported link stickers/eligible features; do not assume ordinary captions make URLs clickable.
- Threads: use profile link and relevant post text where supported; preserve existing content.

## Run safety and progress
- Run in the approved platform order.
- Preview first, then apply in small batches with checkpoints.
- Resume from last verified checkpoint after interruption; do not repeat successful insertions.
- Maintain a run log: platform, account/site, scanned, eligible, updated, verified, skipped, errors, timestamp.
- Never report completion based only on a queued workflow or preview. Report verified counts only.
- No VPS. Run locally / GitHub Actions only when credentials and secrets are available and validated.
- WPVibe is permanently excluded.
