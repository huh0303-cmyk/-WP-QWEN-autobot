# K-Health365 Omega-3 duplicate affiliate module diagnosis
Date: 2026-11-05 (KST)

## Finding
WordPress post 7314 (Omega-3 EPA/DHA comparison) contains two independent affiliate modules:
- A standalone `.affiliate-recommendation` block for Pure Food rTG Omega-3 + Vitamin D, using affiliate URL `https://link.coupang.com/a/ihaVByREei` and a locally uploaded product image.
- The legacy `KHEALTH365-COUPANG-START/END` ten-product footer, which also contains an Omega-3 product card for Jongkundang Health Promega Omega-3 Triple.

These are separate product-card modules, not a single image element duplicated by CSS. The previous footer workflow only replaced its own marker block and did not recognize the unmarked standalone affiliate module, so both remained in the same article.

## Workflow changes
- `automation_hub/coupang_partners.py` now removes only a known standalone `.affiliate-recommendation` div when it contains both a Coupang Partners tracking URL and an image. Other article images and unrelated divs are preserved.
- Product selection now excludes affiliate URLs and product image assets already present in the article body, and deduplicates candidate image assets before selecting the ten cards.
- Unknown unmarked affiliate blocks remain protected from automatic rewriting.
- `scripts/khealth365_sitewide_coupang_10.py` accepts `--post-id` for a targeted repair instead of scanning every post.
- Added manual GitHub Actions workflow `.github/workflows/khealth365-repair-duplicate-omega3.yml`, defaulting to post ID 7314 and using the existing `KHEALTH365COM` repository secret.

## Verification
- Regression tests: 8 passed (new duplicate-guard tests and existing Coupang footer tests).
- The targeted GitHub Actions workflow has been committed but was not dispatched in this session.
- The live WordPress post has therefore not yet been edited. The current browser-side chat session is read-only and the connected desktop process did not have a WordPress application password in its environment.

## Run the targeted live repair
In GitHub, open Actions → “K-Health365 repair duplicate Omega-3 affiliate module” → Run workflow. Keep post_id at 7314. Confirm the run succeeds, then verify the public post and the uploaded JSON report before considering the live repair complete.
