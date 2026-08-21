# Korean/English Newsroom Launch Receipt

Date: 2026-08-21 KST

## Production sites

- https://koreanews365.com — Korean-language independent general newspaper
- https://theseouljournal.com — English-language Korea/Asia newspaper

## Applied

1. Automatic publishing remains disabled.
2. Site names, taglines and Asia/Seoul timezone applied.
3. Dedicated newsroom categories created without deleting legacy categories.
4. About, editorial standards, corrections/right of reply, tips and source/copyright pages created or updated.
5. Official free Twenty Twenty-Five installed and activated on both sites.
6. Temporary migration snippets were deleted after theme verification.
7. Distinct front-page templates deployed:
   - Korean: navy/white, red breaking accent, Korean desks.
   - English: black/white/deep-blue, serif-led international newsroom.
8. Responsive CSS includes a one-column mobile layout.
9. No existing post or category was deleted during this launch phase.

## Production receipts

- Foundation run: https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions/runs/32434017429
  - Result: Success
  - Artifact: newsroom-foundation-receipt-32434017429
- Theme activation run: https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions/runs/32434224832
  - Result: Success
  - Artifact: newsroom-theme-receipt-32434224832
- Front-page deployment run: https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions/runs/32434439889
  - Result: Success
  - Artifact: newsroom-front-page-receipt-32434439889

## Verification

- Active body theme class: `wp-theme-twentytwentyfive` on both sites.
- Korean H1: `한국신문`
- English H1: `THE SEOUL JOURNAL`
- Expected category navigation and editorial footer links are present.
- Desktop audit at 1280px showed no horizontal overflow.

## Follow-up gate

Legacy posts are not approved merely because the front page is live. They remain subject to the separate full content/index audit. Failed or non-indexed legacy posts should be changed to private, not deleted. New automatic publication remains blocked until the editorial quality and image gates pass.
