# KoreaWedding365 duplicate hero image incident

Date: 2026-11-06
Post: https://koreawedding365.com/2026/10/31/korean-immigration-policy-updates-2026-what-international-couples-need-to-know-for-marriage-registration-and-visa-planning/

## Finding
The public page renders a featured image (`news-c96959f30e61.jpg`) and also begins the article body with an inline image (`pexels-photo-12004745.jpeg`). Both use the full post title as ALT text. The duplicate is therefore a two-placement hero problem: the WordPress theme renders `featured_media`, while the article body separately contains a title-labelled lead image. The filenames differ, so URL/name-only checks cannot catch it.

## Root cause
- `scripts/editorial_image_guard.py::filter_wp_images` checks candidate featured images against recent posts' featured-media URLs only. It does not inspect the candidate article's own body HTML.
- `scripts/autopost_mega.py::wp_post` intentionally avoids prepending its own hero image, but did not sanitize a lead image already embedded in generated `body_html`.
- The existing `fix_duplicate_hero_images_v2.py` already fetched the featured image SHA-256, but its matcher never used the `hero_sha256` argument. It also rejected paragraph-wrapped `<p><img></p>` lead blocks. Thus a Pexels source re-hosted as a differently named WordPress featured image bypassed cleanup.

## Changes committed
- Added `strip_title_duplicate_lead_image()`: examines only the first HTML block and removes it only when its image ALT exactly matches the post title. Later editorial images, affiliate product images, and unrelated content are preserved.
- Wired the guard into `scripts/autopost_mega.py::wp_post` before publication.
- Added regression tests for paragraph and figure wrappers, unrelated images, and later product/editorial images.
- Fixed `scripts/fix_duplicate_hero_images_v2.py`: it now supports `<figure>`, `<p><img></p>`, and bare `<img>` lead blocks, and actually compares SHA-256 bytes when URL/basename differ. The existing manual workflow `.github/workflows/fix-duplicate-hero-images-v2.yml` already supplies `KOREAWEDDING365COM` and supports a site filter.
- Added `scripts/fix_koreawedding_duplicate_hero.py` as a narrowly scoped, backup-first/read-back-verified repair option for the exact post.

## Safety / execution status
Code changes are committed to `main`. The targeted live-post repair script is ready, but it has not been executed in this session because the connected GitHub tools available here do not expose workflow dispatch or WordPress credentials. Therefore the live page has not yet been changed; do not report the existing post as fixed until the script reports `fixed_verified` and a public-page read-back confirms one hero image.
