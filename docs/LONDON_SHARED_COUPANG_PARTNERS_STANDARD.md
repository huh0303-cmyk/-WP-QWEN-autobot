# London Project — Shared Coupang Partners Standard

This is the single shared editorial and rendering policy for all WordPress and Blogspot/Blogger destinations in the London Project. It extends the existing publisher paths; it does not create a competing scheduler or publishing pipeline.

## Selection rule (exactly 10 cards; flexible category mix)
- 2 article-relevant products: highest priority; interpret relevance broadly and sensibly, not as an exact-match constraint.
- About 2 Korea lifestyle / popular everyday items.
- About 2 K-beauty / Olive Young bestsellers.
- About 2 K-health supplements.
- About 2 Korea digital products: eSIM, USIM, mobile data.
The category counts are flexible guidelines, not hard quotas; the total of exactly ten unique cards is mandatory. When a category is unavailable, use the strongest available verified candidates. Do not invent affiliate links, images, product availability, prices, or sales rankings. A portal's search ordering is not proof of sales volume.

## Conversion-aware selection
Prefer recognizable, widely useful, easy-to-understand products with accessible price points and low purchase friction. Article relevance leads the first two slots. Favor actual verified sales/popularity evidence when available; otherwise say nothing about sales rank. Affiliate attribution may occur after the visitor follows the link and purchases a different eligible item within the program's attribution window; do not make guarantees about commission eligibility or timing in article copy.

If a site's own verified catalog has fewer than ten eligible products, the publisher blocks that post rather than inserting fewer cards or borrowing another site's catalog.

## Presentation
- Footer after the article, responsive grid (4 desktop / 2 mobile; matching the supplied reference screenshot).
- Each card includes the official product image, product title, and affiliate CTA.
- Required Coupang Partners disclosure appears visibly.
- Affiliate links use `rel="sponsored nofollow noopener"`.
- Replace the existing shared marker block; never stack duplicates.
- If legacy Coupang markup is unmarked, preserve it for review rather than appending another block.

## Shared integration
- WordPress legacy publisher: `scripts/autopost_mega.py::wp_post`.
- WordPress locked four-agent publisher: `scripts/london_four_agent_pipeline.py::_publish_wordpress_native`.
- Blogger/Blogspot queue + four-agent publisher: `automation_hub/blogger_adapter.py::BloggerPublisher.publish`.
- Blogger/Blogspot direct 33-site publisher: `scripts/publish_blogger_33_now.py`.
- Product pools are read from verified repository catalogs. Product records without official affiliate URLs and usable Coupang CDN images are excluded.
- Current verified pools include the Olive Young / K-Skin 45-product capture and K-Health365's affiliate catalog. Broader lifestyle and digital pools must be populated from the user's authenticated Coupang Partners portal before those categories can be guaranteed across every destination.

The footer displays ten cards on every device. The grid is responsive: four columns on desktop and two on narrow/mobile screens, with natural card heights and row wrapping.

## Existing content rollout
This integration affects newly created posts only. It does not mass-edit published articles. Historical backfill must be a separate preview/report/apply operation per platform, with explicit approval and preservation checks.

## Operational guardrails
- Do not alter article text, publication status/date, featured images, SEO metadata, or newsroom editorial content.
- No new scheduler. Use the locked London 4-Agent / existing WP and Blogger publishers.
- Require ten verified records before a post is sent to WordPress or Blogger. If the site's catalog is short, fail that site's publish job and report which catalog needs additional portal-captured products.
