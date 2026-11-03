# Four-network affiliate matrix workflow

## What it does
- Supports Coupang Partners, Agoda, Trip.com, and Olive Young Global.
- Maintains a separate catalog for every individual WordPress or Blogger destination.
- Requires exactly 10 unique offers per provider (40 cards per article).
- Every offer must have a real HTTPS tracking URL, HTTPS product image, verified affiliate-link flag, and verified image-rights flag.
- Appends/replaces only the block bounded by the london-affiliate-matrix:v1 markers. Existing article text and other affiliate blocks are preserved.
- Uses responsive 4-column desktop / 2-column mobile cards, product images, affiliate disclosure, and sponsored/nofollow link attributes.
- Reads back every updated post and checks for exactly 40 card elements.

## Catalogs
Create one file per site at:
data/affiliate/{site_id}-affiliate-matrix.json

Start from data/affiliate/affiliate-matrix-template.json. Each product record must include:
- provider: coupang_partners, agoda, trip_com, or olive_young_global
- id: unique within the site catalog
- title
- tracking_url: actual partner-generated tracking URL
- image_url: permitted product image URL
- affiliate_link_verified: true only after link verification
- image_rights_verified: true only after image-use permission is verified

A site catalog status must be verified or ready. Do not set it until all 40 records are checked. Never copy another site's catalog. WordPress and Blogger versions of the same brand are separate destinations and require separate catalog files. Placeholder URLs are not affiliate links.

The following protected WordPress sites are excluded from this workflow: wp_khealth365, wp_krealestate, wp_kworld365, wp_oliveyoung, and wp_ksa.

## Run
GitHub Actions → Four-network affiliate matrix:
1. Start with preview, new, and one site_id (for example wp_ktrip365).
2. Inspect the artifact report and catalog coverage.
3. Pilot apply with a small limit_per_site only after catalog and credentials are ready.
4. For all existing posts, choose backfill and apply only after reviewing preview.

## Required GitHub Actions secrets
- WP_SITE_CREDENTIALS_JSON: JSON map keyed by site_id or secret_name; each value contains username and app_password.
- BLOGGER_GOOGLE_CLIENT_ID
- BLOGGER_GOOGLE_CLIENT_SECRET
- BLOGGER_GOOGLE_REFRESH_TOKEN
- AFFILIATE_MATRIX_WRITE_ENABLED: set to literal true only when scheduled automatic insertion is authorized.

Scheduled runs inspect recent posts every six hours. They remain read-only unless the write secret is explicitly enabled. Manual apply additionally requires the exact confirmation APPLY-AFFILIATE-MATRIX.

## Current limitations
This workflow does not manufacture affiliate links or scrape unauthorized product images. It blocks a site until that site's own 10 verified offers from each provider are supplied. Agoda/Trip.com offers must be generated from the partner accounts and actual product inventory. The Agoda account still has pending verification; its catalog must not be marked verified until real tracking links are available.
