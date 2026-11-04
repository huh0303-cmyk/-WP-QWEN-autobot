# SeoulMall Omnichannel Rollout

Updated: 2026-11-04 (KST)
Status: IN PROGRESS — execution order locked; no site-wide deployment claimed.

## Brand standard
- Umbrella: SEOUL MALL
- Slogan: Beyond BTS, Discover Korea.
- Store URL currently verified: https://influencers.coupang.com/s/seoulshop
- Store display name: SeoulMall
- Store slug remains seoulshop; do not claim it has changed to seoulmall.
- Maintain identical K-series naming across web and social channels.

## Storefront taxonomy
1. K-Beauty — Korean skincare, hydration, anti-aging.
2. K-Health — supplements and wellness products.
3. K-Tour — actual Korea tour packages and experiences, not travel accessories.
4. K-Hotels — actual Korea hotel booking/accommodation products, not travel accessories.
5. K-Digitals — laptops, tablets and mobile phones; prioritize Samsung where appropriate.
6. K-Life — travel essentials, everyday essentials and trending products.

Initial storefront target: 20 products total, distributed by relevance across all six collections. Every item must have an attractive representative image, clear title and an account-generated Coupang affiliate tracking URL. Do not invent popularity/sales rankings. Record evidence and date captured. Remove or reclassify irrelevant legacy travel accessories from K-Tour/K-Hotels.

## Rollout order
1. Complete SeoulMall storefront: six collections and 20 relevant products; verify image, tracking URL, collection placement and public storefront rendering.
2. K-trip365.com
3. JobKorea365.com
4. JobKoreaGlobal.com
5. KoreaWedding365.com
6. KStudy365.com
7. StudyInKorea365.com
8. K-Health365.com
9. Expand to every eligible website and every registered YouTube, TikTok, Facebook, Instagram and Threads channel in control.korea365.org.

## Shared creative implementation
- Reuse a single responsive SeoulMall banner/card design, optimized for desktop and mobile.
- Use the live verified store URL as the destination; use account-generated tracking URLs for individual products.
- Include a clear affiliate disclosure adjacent to affiliate links.
- Adapt placement to platform capabilities: blog post/page, YouTube channel/video descriptions, social bios/posts/stories. Do not claim unsupported clickable placements.
- Keep the original site's topic and user experience primary; no blanket insertion into locked/excluded sites or channels without eligibility checks.

## Quality gates
- Preserve site-specific affiliate catalogs and the existing five locked WordPress sites.
- Back up before edits; use dry-run/preview; test one representative page per site before bulk rollout.
- Verify desktop and mobile rendering, image loads, destination URL and affiliate attribution format.
- Distinguish verified identity from registered-only social accounts; current preflight says social publishing connections are not established (TikTok 0, Instagram 0, Threads 0, Facebook 0). Do not report posting as completed without a publication receipt.
- Never publish automatically or enable paid APIs, paid image services or paid SaaS without explicit approval.
- Record every change, test, failure, and next action in this repository during the same session.

## Current baseline / blockers (2026-11-04)
- Local PC: ChrisHUH online; repo C:\Users\huh03\LondonProject; branch main was one commit ahead of origin/main at initial inspection.
- Working tree already contained substantial unrelated/uncommitted affiliate-engine, product-master, report, screenshot and script changes. Do not reset, clean, overwrite or bulk-stage these files.
- Coupang storefront verified at https://influencers.coupang.com/storefront: display name SeoulMall; slogan Beyond BTS, Discover Korea.; public slug seoulshop; five old collections with two products each (10 total). New six-collection taxonomy not yet applied.
- Existing local master data file data/affiliate/coupang-master-products.json contains account-generated tracked products captured from Coupang Partners portal; it must be audited and deduplicated before selection. Its existence does not prove products have been added to the public SeoulMall storefront.
- Existing preflight report reports live_writes_enabled=false, WordPress 25 (5 locked), Blogger 33, YouTube 23, and zero connected publishing integrations for the listed social platforms. Re-run preflight before deployment; this report was generated 2026-11-03 and is not a current live verification.
- Current local product backfill preview for K-trip365 is blocked because the site-specific catalog ktrip365-affiliate-matrix.json is missing. Do not bulk insert until that catalog is built and validated.
- Windows AC standby and hibernate timeouts have been set to Never (0) for this work session. Monitor timeout may remain enabled. Verify settings after restart/power-plan changes.


## Explicit user directive — global SeoulMall link rollout (2026-11-04 KST)
- User clarified the goal: insert the SeoulMall destination/link across **all existing and future content** in every owned/registered WordPress site, Blogspot blog, YouTube channel/video description, Facebook page/post, TikTok account/content, Instagram account/content, and Threads account/content.
- User's required execution order for today's work (supersedes any earlier channel order): **1) WordPress → 2) Blogspot → 3) YouTube → 4) TikTok → 5) Facebook → 6) Instagram → 7) Threads.**
- User explicitly requests changing the public SeoulMall store slug from `seoulshop` to `seoulmall`. Current verified public URL is still `https://influencers.coupang.com/s/seoulshop`; the requested new URL `https://influencers.coupang.com/s/seoulmall` is NOT verified and must not be inserted as a live destination until Coupang confirms/permits the slug change and the new URL resolves to the user's storefront.
- First investigate and attempt the slug change in the authenticated Coupang Influencer storefront settings. If the UI does not expose it, use official Coupang support route to request the change. Do not rename the store display name as a substitute; display name is already SeoulMall.
- Link insertion policy: use one canonical SeoulMall destination once confirmed; adapt format by platform (responsive banner/card + CTA in WordPress/Blogspot; video descriptions/channel links for YouTube; supported bio/profile/post placements for social platforms). Keep existing content intact, preserve post metadata/media, avoid duplicate insertions, and include legally/policy-required affiliate disclosure.
- Existing content modification is platform-specific. Use official APIs or authenticated UI only where permitted. For platforms that do not permit editing old captions/posts, add the link to supported profile/bio surfaces and apply to all new content going forward; report the exact coverage and limitations.
- Execution is ordered and staged. For each platform: inventory all registered destinations; backup/export where supported; dry-run; test one representative item; obtain/confirm user authorization where platform permissions require it; bulk apply; read back/verify each target; record counts (eligible, changed, skipped, failed) and evidence. Never report an item as completed without a publication/update receipt or authenticated read-back.
- This directive is the active top-level rollout scope and order. It does not authorize unrelated edits, post deletion, or modification of the five previously locked WordPress sites unless the user's explicit global instruction is treated as authorization for this SeoulMall-only insertion; preserve their other content/settings.
- Current actual state at directive time: no cross-platform SeoulMall link rollout has been performed; the storefront slug change is also not yet verified.
