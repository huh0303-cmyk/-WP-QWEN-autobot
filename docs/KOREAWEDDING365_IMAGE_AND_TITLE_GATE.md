# Korea Wedding 365 — Image and Headline Quality Gate

## Required publishing behavior
- Never reuse an image just because a search/generation attempt failed.
- Prefer a topic-relevant, rights-safe image that is not already used by a recent post on KoreaWedding365.
- Compare normalized source URLs and image fingerprints (perceptual hash) against recent posts before assigning a featured image.
- If image uniqueness or relevance cannot be verified, publish with no featured image and no inline image. Do not use generic wedding stock art as a filler.
- Avoid title openings such as "How to", "How do", "Understanding", "Navigating", "Managing", "Preparing", "Exploring", "Discovering", "Essential Steps", and "A Guide to" when they create repetitive patterns.
- Generate titles from the concrete subject, a reader decision, a meaningful distinction, or a verified change. Check the last 50 published titles for exact, near-duplicate, and repeated opening frames.
- If the title still fails after one rewrite, stop and leave the item in the review/error queue; never bypass the gate.
- Do not mass-edit or delete old posts. Existing-post image cleanup must first run in audit-only mode and preserve a backup before each approved edit.

## Existing-post repair mode
The script `scripts/repair_wp_duplicate_images.py` keeps the oldest use of a photo and removes later duplicates. For Korea Wedding 365, run with `APPLY_CHANGES=false` first. Only use `APPLY_CHANGES=true` after reviewing the artifact. A removal is intentional: the post remains published and its text remains, but the repeated featured/inline photo is removed rather than replaced with another unverified image.

## Known limitation
The current repair script compares image fingerprints for posts returned by `editorial_image_guard.recent_posts`. Confirm the number of posts covered in the generated report before treating the scan as a complete site-wide audit.
