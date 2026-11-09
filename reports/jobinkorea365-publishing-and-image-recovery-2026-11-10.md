# JobInKorea365 publishing incident and recovery

Date: 2026-11-10 (KST)
Site: https://jobinkorea365.com

## Verified findings
- The homepage's newest visible article, “Strategic Job Search Paths for International Tech Talent in Korea,” has original publish date 2026-11-01 and modified date 2026-11-09. It is an update, not a new Nov 9 publication.
- This article has no visible featured/editorial image.
- The site's 46-item SEO metadata batch log reports 45/46 success. Item 869 timed out after 60 seconds while navigating to wp-admin. This was an SEO metadata batch, not an article-publishing run.
- A workflow run started 2026-11-09 17:10 UTC (run 42661956114) with run name identifying a JobInKorea365-only recovery, but its workflow_dispatch inputs were blank. The workflow therefore fanned out across the site matrix. As of 2026-11-10 it was still in progress and the JobInKorea365 matrix job (129315562670) was queued; no publication result was recorded for this site.
- In .github/workflows/daily-network-publish.yml the user-controlled target_site_url defaults blank, which means all sites. Always provide the exact target URL on a recovery dispatch.
- scripts/autopost_current.py reads WP_IMAGE_COUNT, but its initializer sets base.WP_IMAGE_COUNT to 0 unconditionally unless the environment happens to be "0"; this reverses the requested count. Thus the current publishing entrypoint suppresses article images despite the workflow asking for one.
- Image generation and WordPress authorization are not established by the public page or the SEO batch log. Do not claim either was validated.

## Corrective actions required
1. Correct the WP_IMAGE_COUNT initializer to preserve a validated value (0/1), default to 1, and fail closed if mandatory image upload/featured_media setup fails for this site.
2. Add a JobInKorea365-only workflow dispatch path and an assertion that TARGET_SITE_URL is exactly https://jobinkorea365.com before invoking publishing. Do not run the 25-site matrix for this recovery.
3. Add timeout/retry with exponential backoff to the SEO metadata browser batch, and persist item-level checkpoints so a retry resumes only missing work.
4. Ensure the generated or licensed matching image is uploaded to WordPress, attached as featured_media, and has descriptive ALT text. Avoid text-only public publication.
5. Confirm WordPress REST credentials and publish capability through a non-mutating authentication check before publishing.
6. Publish one article only after those gates pass; verify its public URL, actual publication date, featured-media attachment, image URL, and ALT text.
7. Only after verifying the one-post recovery, restore the normal site cadence. Keep the network-wide freeze in place; never enable unattended publishing for all sites as a side effect.

## Current execution status
No JobInKorea365 recovery post has been verified as published in this session. The queued run was not a site-specific execution. Do not report the site fixed or resumed until the above gates and live verification are complete.
