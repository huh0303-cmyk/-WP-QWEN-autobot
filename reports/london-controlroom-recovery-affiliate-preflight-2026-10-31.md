# London Project recovery and Coupang preflight — 2026-10-31

## Control room recovery
- URL: https://control.korea365.org/
- GitHub Pages response: HTTP 200
- JSON endpoints checked: dashboard.json, visitor_metrics.json, social_inventory.json, social_metrics.json — all HTTP 200 and valid JSON.
- Dashboard data refresh workflow: run 41186845916 — success.
- Latest dashboard snapshot: 2026-10-31 18:00:28 KST; GSC reference date 2026-10-28.
- Inventory rows: 66 total = 25 WordPress/newsroom, 33 Blogspot, 5 Tistory, 3 Naver.
- Fixed malformed dashboard JSON newline, Blogger JSON writer, Social platform count lookup (undefined), and restored all 33 registered Blogspot entries.
- Commits: 09173a6589bc44732aeb448b462e08baf592d4e7 (dashboard JSON repair), c8a27ce694b5d6598613054fad600ccb4ce13a25 (Blogger JSON writer), f2f5ae099a843425c39ca3080437d111f6a00788 (social count rendering), 6412ff9427acd9c42d4ed383a12adb59b0a370c6 (Blogspot inventory).

## WordPress affiliate preflight
- Workflow: affiliate-cloud-preflight.yml
- Run: 41186746241
- Mode: read-only; writes_performed = 0
- Target sites: 24 general WordPress sites
- Authenticated and post inventory read: 20
- Blocked for further diagnosis: 4
- Published posts scanned: 1,622
- Missing tags: 74
- Missing featured images: 517
- Artifact: affiliate-cloud-preflight-41186746241

### Blocked sites (do not treat all as site-down)
- k-visa365.com — authenticated REST endpoint returned HTTP 403; site reachability and admin-side connection are separate. User reports the site connection is working; preserve it in the target list and investigate REST/WAF/auth identity without replacing credentials.
- ksa-korea.org — ConnectionError
- sis-korea.com — SSLError
- ki-korea.com — SSLError

## Affiliate insertion status
- No bulk affiliate content writes were made in this preflight.
- Do not reuse the legacy generic laptop banner workflow for the fleet: it targets only koreamedicaltour.com and k-trip365.com, can promote a private post and alter publication dates, and is not a content-relevance-based 100-post deployment.
- Verified account-generated product links available in current records are limited (Omega-3, multivitamin, chondroitin); the wider 40-product/site mapping and each product's approved image/link evidence must be present before inserting 5–10 products per post.
- Existing safe operating rules: latest 100 published posts per site, match products to post topics, preserve body/date/status/featured image, disclosure + sponsored/nofollow, idempotent markers, dry-run and pilot first, per-post verification and append-only receipts.
- The affiliate cloud preflight is scheduled on GitHub Actions and is independent of the user's PC. This does not mean the affiliate write engine is deployed or scheduled.
