# WordPress + Blogspot quality repair — 2026-11-13

Owner's latest policy: rewrite existing posts to **2,500–3,500 non-whitespace characters**, readable attractive site-specific layout, no mass-generated titles, no four-digit years in titles, no repeated images. Preserve original URLs/SEO metadata where possible, back up and run limited draft tests before bulk changes.

## Writing and layout
- 1 concise opening; 4–6 useful H2 sections with descriptive H3 as appropriate; brief paragraphs, concrete information, practical takeaways, short FAQ when relevant. No padded repetition or unsupported facts.
- No title formulas: Official Guide, Ultimate Guide, Comprehensive Guide, Guidelines, Strategic Scheduling, Editorial Analysis, Practical Guide, 完벽 가이드, 총정리, etc. Ban four-digit years in titles unless explicitly approved for a specific historical article.
- Detect near-duplicate titles and introductions across each site AND fleet, not only exact normalized matches; avoid adding generic suffixes to make a duplicate look unique.
- Distinct site palettes; mobile-readable H2/H3 spacing, line-height, bullets, internal links and correct ALT. Do not change existing slugs automatically.
- Exclude K-health365 from the mass rewrite queue per prior owner instruction; keep routine operations separate.

## Image
- Preserve unique existing images. Replace only confirmed duplicates or mismatched assets.
- Check URL, media ID, byte SHA256 and perceptual similarity of downloaded actual image; store persistent 7-day global reuse ledger across WordPress and Blogger.
- Randomize which of Pexels/Pixabay is attempted first per post, then SDXL Turbo then FLUX Schnell. No fifth provider; if all fail, image-less publish only when policy permits. Track licensing, source, ALT and featured/body nonduplication.
- Failure to inspect an image is NOT evidence that it is unique. Mark NEEDS_REVIEW.

## Deployment gates
- Inventory actual WP and Blogspot URLs, post IDs, titles, content lengths, featured/body image fingerprints and duplicates; report exact counts and links.
- Canary one WP and one Blogger in DRAFT first; compare old/new content and preserve backup, source metadata and image attribution.
- Do not mass-update public posts until QA and rollback checks pass. Rate-limit and isolate each site.
- Count rewritten vs failed vs unchanged, before/after duplicate image/title rates and source URLs.
- Existing kworld/kfinance scripts tightened to 2,500–3,500 character acceptance and removed generic title suffix list in commits bd55686 and eb044875. They are NOT proof of live rewrite.
- Blogger and other WordPress active production paths still require wiring and tests. Kfinance image detection currently relies on media ID and needs perceptual cross-media checks. Do not claim network-wide fix.
