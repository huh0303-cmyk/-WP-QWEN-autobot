# JobInKorea365 publishing and image incident

Date: 2026-11-10 (KST)
Site: https://jobinkorea365.com

## Verified live state
- The selected public article is titled “Strategic Job Search Paths for International Tech Talent in Korea.”
- Its visible published date is 2026-11-01 (the page also shows an updated date of 2026-11-09). Thus the live article is not evidence of a new publication on Nov 9.
- The article has no visible featured/inline editorial image in its rendered content.
- The article includes a cross-domain link to jobkorea365.com and generic, repeated instructional copy. Review content quality before treating it as a recovery publication.

## Repository findings
- wp_jobinkorea is configured in docs/SITE_PUBLISHING_TIERS.md.
- Historical data/site-publication-history.json contains a Sep 12 wp_jobinkorea workflow success with no public URL, and older REST API 403 failures. These records do not establish the cause of the current Nov 2026 gap.
- scripts/autopost_mega.py contains a global publishing freeze: WP_AUTOPUBLISH_ENABLED defaults to false, with a comment that publishing stays disabled unless a future reviewed workflow explicitly opts in.
- Existing London pipeline documentation says image creation/selection is conditional on provider credentials and enable flags; its documented fallback can continue without an image. That behavior explains how an image-less post can pass through, but does not prove which exact provider failed for this post.
- KoreaWedding365 is configured separately as wp_koreawedding; its records show publications, and the repository has a duplicate-hero incident report. The reusable lesson is to set WordPress featured_media and avoid inserting the same hero again into the body. It does not establish that its writer/image engine is interchangeable without inspecting current workflow code and secret availability.

## Required recovery work
1. Inspect the actual scheduled/manual workflow run history and logs for wp_jobinkorea around Nov 2–10; the repository's tracked history is stale and cannot identify a current failing step.
2. Check the exact site secret, WordPress REST authentication, and publish capability without exposing secret values.
3. Compare the full wp_jobinkorea and wp_koreawedding workflow/config/provider paths. Reuse only the shared writer and image implementation that can be verified as site-compatible.
4. Make an image mandatory for this site: require one relevant licensed stock or generated asset, upload it to WordPress, set it as featured_media, provide descriptive ALT text, and fail/queue the article when no image is attached. Do not silently publish text-only articles.
5. Keep the global freeze intact until a narrowly scoped, reviewed JobInKorea365 recovery workflow is added. The user's explicit request on 2026-11-10 authorizes that scoped recovery; do not enable unattended publishing across the whole network.
6. Resume with one reviewed JobInKorea365 post, verify its public URL, publish date, image URL, and featured-media attachment, then restore the site's normal cadence and monitor the next run.

## Current status
Root cause is not yet established from available evidence. No recovery post has been published, and no provider credentials or workflow logs were available in the evidence reviewed for this report. Avoid claiming the site is fixed until the recovery run is verified live.
