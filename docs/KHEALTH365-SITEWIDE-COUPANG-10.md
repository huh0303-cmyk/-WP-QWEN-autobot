# K-Health365 sitewide Coupang Partners — 10 products

## Goal
Show exactly ten distinct Coupang Partners products at the end of every published K-Health365 post. The workflow is manually runnable for future posts. Preserve article text outside the affiliate block, post status, publication date, featured image, SEO metadata, and AdSense code.

## Ten-product pool
Six existing account links and official banner creatives were captured from the live K-Health365 article inspected on 2026-11-01. Four additional personal affiliate links were already present in the K-Health365 affiliate catalog:
1. 락토핏 정품 골드 80포
2. 순수식품 rTG 오메가3 비타민D
3. 뉴트리원 루테인 지아잔틴 164
4. 모발 콜라겐 3270
5. 종근당건강 프로메가 오메가3 트리플
6. CJ 바이오코어 500억 특허유산균
7. 관절엔 콘드로이친 1200
8. 고려은단 뼈건강 칼마디 K2
9. 고려은단 멀티비타민 올인원
10. 유한양행 식물성 MSM

The four additional product images are resolved from their Coupang affiliate destinations at runtime and must pass an image content-type check. No fabricated image URLs are permitted.

## Safe replacement behavior
- The script replaces the existing marked section between KHEALTH365-COUPANG-START and KHEALTH365-COUPANG-END.
- If a post has an old unmarked Coupang section, it is reported as SKIPPED_UNMARKED_LEGACY_BLOCK. The script will not append a second block and create more than ten cards.
- If a post has no existing affiliate block, the ten-card section is appended to the end.
- Each product link is rendered as a linked image and a CTA, with rel="sponsored nofollow noopener".
- The Coupang Partners disclosure appears once inside the new block.
- Apply mode reads each post back through the authenticated WordPress REST API and verifies the public rendered post contains all ten distinct affiliate destinations.

## Run
GitHub Actions → K-Health365 Sitewide Coupang 10 Products.
1. Run preview first with limit=1 to test the first published post.
2. Review the uploaded JSON report, especially skipped_legacy and errors.
3. Only after preview review, run apply with confirm_apply=APPLY-ALL.
4. Future posts can be handled by rerunning the same workflow.

## Required repository secrets
- KHEALTH365_WP_USER
- KHEALTH365_WP_APP_PASSWORD

Secrets are never stored in source control. Default mode is preview. The workflow does not auto-run on a schedule and does not change WordPress posts unless the operator explicitly chooses apply and supplies the confirmation phrase.

## Important limitation
A post containing a legacy affiliate section without the two recognized markers is intentionally skipped for manual migration. Resolve all such skips before declaring the sitewide rollout complete.
