# Coupang Partners — Per-Site Catalog & Random Rotation
Date: 2026-10-31 (KST)
Status: IMPLEMENTATION REQUIREMENT — catalog-first; no article writes authorized by this file
Repository: huh0303-cmyk/-WP-QWEN-autobot

## The intended behavior
Every blog has its own topic and therefore its own Coupang product pool. Do **not** use one portfolio-wide list of generic products. Prepare an approximately 40-offer catalog for each site's subject, then randomly rotate only relevant offers into that site's existing published articles.

The random choice happens **after relevance filtering**, never before it. Randomness must not cause an unrelated product to appear in an article.

## Per-site catalog rule
Each site gets a separate catalog keyed by canonical site URL / site key:
- target size: about 40 distinct offers per site (not 40 shared offers for every site)
- each offer must have: product title, topic tags, allowed article tags/categories, Coupang product/item identifiers where available, the user's verified affiliate deep link, approved image URL/source and image-use basis, last verified timestamp, active flag
- no placeholder, guessed, generic homepage, or unverified tracking URL may enter the active pool
- if fewer than 40 verified relevant offers exist, use the verified subset; never pad the pool with unrelated products

## Catalog composition
Build the 40-item pool around the site's editorial subject and reader intent. Suggested allocation (adapt per site):
- 24 core-topic products: directly related to the site's main subject
- 8 adjacent-use products: genuinely useful in the same reader journey
- 4 seasonal / trend products: only while relevant and in season
- 4 premium / higher-priced products: only where the article context supports them

Examples of subject mapping (illustrative categories, not approved product records):
- K-Health365: nutrition and health-management products, home monitoring / exercise / sleep-support items; no disease-treatment claims.
- K-Trip365: travel essentials, luggage, adapters, eSIM-compatible accessories, organizers and destination-relevant travel gear.
- K-RealEstate365: home maintenance, cleaning, safety, lighting, storage and moving-in essentials.
- K-Finance365: office / document organization and practical work tools only where the article supports them; do not force unrelated goods.
- OliveYoungKorea / K-Skin365: skincare, sun care, cleansing, hair/body care and beauty tools, matched to the actual article.
- K-Tech365: computing, mobile, peripherals, storage, networking and accessories.
- JobKoreaGlobal: interview, office, language-learning and work-preparation tools.
- K-World365 / general lifestyle properties: map each site's actual categories before building its pool; do not assume one universal lifestyle catalog.

## Article matching and random selection
For each existing published article:
1. Read site identity, post title, categories, tags, excerpt and body topic.
2. Filter that site's own active catalog by exact topic/category/tag compatibility and minimum relevance score.
3. Exclude offers already placed in that article and offers repeated too frequently on that site.
4. Randomly sample from the remaining eligible offers, weighted by relevance score and rotation balance.
5. Default target: 6–7 cards per article; use fewer when fewer relevant verified offers exist. Never force a fixed count.
6. Ensure variety: avoid showing the same brand or product family repeatedly in one block.
7. Store the selected offer IDs and random seed/selection receipt so the result is auditable and reruns are deterministic for the same run ID.

## Rotation and fairness
- Track per-site and per-offer placement counts, last-used date, and last-used post.
- Prefer eligible offers with lower recent exposure.
- Do not repeat an offer in the same post.
- Set configurable cooldowns to avoid the same product appearing across consecutive posts.
- A rerun must not reshuffle or duplicate an already verified block unless an explicit refresh operation is requested.

## Affiliate link and image validation
An offer is eligible only when:
- its deep link is generated from or confirmed for the user's Coupang Partners account;
- the link resolves to the intended product page and retains required tracking;
- the product image is supplied through a permitted Coupang source/widget or otherwise has documented usage permission;
- the product is available/active at verification time, where status can be checked.
Do not scrape or hotlink product images contrary to program terms. If image rights or a valid image URL are not confirmed, use a compliant text-only CTA or skip the offer.

## Placement rules
- Append the product module to existing published posts only.
- Preserve all original body text, post title, slug, date, status, categories, tags, featured image, media, and ad blocks.
- Never publish drafts/private posts or alter publication status/date.
- Include the required affiliate disclosure and appropriate sponsored/nofollow link attributes.
- Use a stable managed-block marker; reruns must be idempotent.
- Default to dry-run; pilot 3–5 posts per site before scaling.
- Verify the rendered permalink, all product destinations, images, disclosure and rel attributes after each write.
- Isolate failures per post and continue safely; write append-only receipts.

## Portfolio execution
- Keep site catalogs independent, even when two sites cover adjacent topics.
- Process sites sequentially with bounded batches.
- Prioritize sites using reliable previous-day KST traffic only when source/date/coverage are known. Missing analytics is "not collected", never zero.
- Do not assume all WordPress sites are connected merely because one site is connected.
- Run on GitHub Actions/cloud runner so the user's PC does not need to remain on.
- Keep all credentials in GitHub Secrets; never commit partner credentials, WordPress passwords, cookies or private account exports.

## Required files / data model
Recommended configuration:
- `config/affiliate/coupang_sites.json`: site-to-topic map and per-site catalog reference
- `config/affiliate/catalogs/<site_key>.json`: independent offer catalog for each site
- `data/affiliate/rotation_state.json`: per-site rotation state (generated artifact, not committed if it contains private tracking data)
- `reports/affiliate_runs/<run_id>.json`: per-post append-only result receipts (sanitize private values)

Offer schema:
```json
{
  "offer_id": "stable-id",
  "provider": "coupang",
  "product_title": "verified product title",
  "product_id": "verified product id",
  "item_id": "verified item id",
  "topic_tags": ["site-topic", "article-intent"],
  "allowed_categories": ["verified category"],
  "affiliate_url": "user-account-verified deep link",
  "image_url": "provider-approved image URL",
  "image_rights_basis": "official widget/feed/permission reference",
  "last_verified_at": "ISO-8601 timestamp",
  "active": true
}
```

## Important boundary
This commit records the correct catalog and rotation behavior. It does **not** claim that 40 verified products have already been sourced for every site, that affiliate URLs/images have been validated, or that any WordPress post has been modified. Product records must be populated from the user's actual Coupang Partners account and approved product/image sources before write mode is enabled.
