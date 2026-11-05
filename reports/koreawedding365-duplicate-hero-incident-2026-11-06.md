# KoreaWedding365 duplicate hero image incident

Date: 2026-11-06
Post: https://koreawedding365.com/2026/10/31/korean-immigration-policy-updates-2026-what-international-couples-need-to-know-for-marriage-registration-and-visa-planning/

## Finding
The public page renders a featured image (`news-c96959f30e61.jpg`) and also begins the article body with an inline image (`pexels-photo-12004745.jpeg`). Both use the full post title as ALT text. The duplicate is therefore a two-placement hero problem: the WordPress theme renders `featured_media`, while the article body separately contains a title-labelled lead image. The filenames differ, so URL/name-only checks cannot catch it.

## Root cause
- `scripts/editorial_image_guard.py::filter_wp_images` checks candidate featured images against recent posts' featured-media URLs only. It does not inspect the candidate article's own body HTML.
- `scripts/autopost_mega.py::wp_post` intentionally avoids prepending its own hero image, but did not sanitize a lead image already embedded in generated `body_html`.
- The previous hero cleanup utility only handles a narrow leading block / URL or basename match; it does not safely identify the observed title-labelled paragraph image.

## Changes committed
- Added `strip_title_duplicate_lead_image()`: examines only the first HTML block and removes it only when its image ALT exactly matches the post title. Later editorial images, affiliate product images, and unrelated content are preserved.
- Wired the guard into `scripts/autopost_mega.py::wp_post` before publication.
- Added regression tests for paragraph and figure wrappers, unrelated images, and later product/editorial images.
- Added `scripts/fix_koreawedding_duplicate_hero.py` for the existing post. It requires the repository secret `KOREAWEDDING365COM`, creates a JSON backup, patches only the post body, reads it back, and verifies that `featured_media` is unchanged.

## Safety / execution status
Code changes are committed to `main`. The targeted live-post repair script is ready, but it has not been executed in this session because the connected GitHub tools available here do not expose workflow dispatch or WordPress credentials. Therefore the live page has not yet been changed; do not report the existing post as fixed until the script reports `fixed_verified` and a public-page read-back confirms one hero image.
