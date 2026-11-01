# Coupang Partners sequential rollout

Updated: 2026-11-02

## Owner-approved processing order
1. K-Trip365 WordPress (`wp_ktrip365`) — process every existing eligible post.
2. Remaining registered WordPress sites, one site at a time.
3. Registered Blogger sites, one blog at a time.

Do not start the next site until the current site's report has been written and post updates have been read back and verified.

## Per-site completion criteria
- The site's own catalog contains at least 10 distinct, account-generated Coupang Partners links.
- Each product has a valid `https://link.coupang.com/` destination, a title, and an official Coupang CDN image.
- Existing post content and legacy affiliate placements are preserved; append the managed block only where safe.
- Never delete posts. Never overwrite unrelated content.
- Verify every updated post by reading it back and confirming all 10 distinct destinations.
- Record counts for posts scanned, updated, already complete, skipped for legacy review, catalog missing, and errors.
- Commit a site-level JSON/Markdown report to the repository before advancing.

## Stop conditions
Stop the current site and report the exact blocker if its catalog has fewer than 10 verified products, the platform credentials/OAuth are unavailable, API access fails, or read-back verification fails. Do not borrow products or affiliate links from another site's catalog.

## Protected destinations
Respect the existing locked-site policy for `k-health365.com`, `krealestate365.com`, `kworld365.com`, `oliveyoungkorea.com`, and `ksa-korea.org`; do not modify these without a specific later authorization.

## Current verified readiness (2026-11-02)
- K-Trip365 registry entry exists.
- The K-Trip365 per-site verified product catalog was not found at the standard catalog paths.
- The existing backfill workflow requires 10 verified site-scoped products and the relevant WordPress/Blogger credentials.
- The existing workflow is manual-dispatch only; it is not a persistent sequential scheduler.
- No production post update is authorized by this readiness note. Do not report a site as complete until actual post read-back verification succeeds.

## Reporting
After each site, publish a concise result containing site ID, posts scanned, posts updated, affiliate cards inserted, already-complete posts, skipped posts, errors, and the report path. Only then advance to the next site.
