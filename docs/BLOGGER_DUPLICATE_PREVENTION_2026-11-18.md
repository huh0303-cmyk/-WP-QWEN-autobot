# Blogger duplicate prevention — mandatory publishing acceptance criteria

Date: 2026-11-18. Scope: existing 33 Blogger properties. Four additional owned properties remain separate, outside the daily 33 publishing scope until approved.

## Publication must fail closed
- Before each post, check global 14-day history across Blogger sites and, where accessible, WordPress for title, topic, introduction, body, featured and inline images.
- Normalize title/body for exact duplicates, compare near-duplicate titles, intros and full-body content; semantic topic similarity >= 0.85 requires topic reselection or genuine rewrite and recheck, not a cosmetic title suffix.
- Image check: canonical URL, provider asset ID, SHA-256 of downloaded bytes, perceptual image hash (resizes, recompression and alternate URLs). A failed download/hash is UNKNOWN, not unique. Do not publish that image until inspected or replaced.
- Prohibit same featured and body image, repeated image within a post, and global 14-day image reuse. Require topic-relevant ALT, source/license and image identity ledger.
- Preserve global persistent dedup ledger across scheduled workflow runs; concurrent jobs must acquire a lock or use atomic reservation before publishing to prevent races.
- Source fallback: randomize Pexels/Pixabay first, then SDXL Turbo, FLUX Schnell; if none qualifies, follow each site's image-less publication policy or hold for review. Never reuse an image simply to meet a quota.
- Preserve each site's distinct topic, persona, tone and content structure. Target 2,500–4,000 Korean characters or site-specific language-equivalent target, H2/H3, useful FAQ, no generic padded prose, no year in title.
- Run backups before edits; preserve canonical URLs and metadata. Existing posts: inventory, report exact duplicate groups, dry-run, single draft canary, verify rollback, then only approved repairs. Never mass-delete images or posts.
- Verify actual Blogger live post URL and publish timestamp after successful publish. Report per-site accepted, rejected_duplicate_image, rejected_duplicate_content, auth_failed, publish_failed, published_verified.

## Implementation status
This document records the required policy, not proof that all live publisher scripts implement it. The existing `scripts/cleanup_blogger_duplicate_images_since.py` primarily uses URL identity and can remove repeated inline images when DRY_RUN=false; do not run it in write mode until backup, stronger fingerprints, and rollback checks are present. Integrate these gates into every actual Blogger publishing entrypoint and add regression tests before enabling 33/day live publication.
