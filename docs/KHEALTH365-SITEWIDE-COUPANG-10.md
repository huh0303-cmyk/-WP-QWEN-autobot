# K-Health365 sitewide Coupang Partners — shared London standard

K-Health365 uses the same shared Coupang Partners policy as the WordPress and Blogspot network.

- Target: up to 10 verified product cards at the end of each post.
- Selection: first two are chosen for broad article relevance; remaining products follow the flexible Korea lifestyle / K-beauty / K-health / digital mix where verified catalog entries exist.
- Category counts are soft guidance, not hard quotas. Missing categories are filled with the strongest available verified products.
- Product images must come from official Coupang CDN creatives. Unverified links or fabricated images are never used.
- Existing K-Health365 marker blocks are migrated to the shared London marker block by the bulk updater.
- Unknown unmarked legacy affiliate sections are preserved and reported for manual review rather than duplicated.
- The daily 12:00 KST GitHub Actions job continues to use preview/apply controls and read-back verification.
- The bulk updater changes only post content. It must preserve publication status/date, featured image, SEO metadata and all content outside the affiliate section.

The shared implementation is `automation_hub/coupang_partners.py`; see `docs/LONDON_SHARED_COUPANG_PARTNERS_STANDARD.md` for network-wide policy and limitations.
