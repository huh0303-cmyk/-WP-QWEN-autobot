# K-Health365 Affiliate Product Cards Pilot

- Site: https://k-health365.com
- Pilot post: 6148 (골다공증 초기증상과 예방법: 뼈 건강 지키는 올바른 습관)
- Per-post selection: randomized 5–10 products, bounded by the operator-selected min/max.
- Selection: title/body relevance first; related products allowed; manufacturer duplication allowed.
- Card layout: verified product image, product title, affiliate CTA, required disclosure.
- Safety: no unrelated products to fill the count; no unverified affiliate URLs or image URLs; no stale prices; no medical treatment/prevention claims.
- Scope: this pilot is limited to post 6148. Preserve existing content, post status, featured image, SEO metadata, and AdSense configuration.
- Rollout: preview and verify candidate cards before applying. Any broader site rollout requires separate approval.

## Current known candidates

1. 관절엔 콘드로이친 1200 — https://link.coupang.com/a/ihKqEBmP48 (image URL still needs verification)
2. 고려은단 뼈건강 칼마디 K2 — https://link.coupang.com/a/ihPTujzeyy (image URL supplied; verify it resolves to the exact product)
3. 순수식품 rTG 오메가3 + 비타민D — https://link.coupang.com/a/ihaVByREei (image URL still needs verification)
4. 고려은단 멀티비타민 올인원 — https://link.coupang.com/a/ihPGNw5JzU (image URL still needs verification)
5. 유한양행 식물성 MSM — product page confirmed by user screenshot; affiliate URL and image URL still need verification before activation.

## Required GitHub secrets for a future write-enabled deployment

- KHEALTH365_WP_USER
- KHEALTH365_WP_APP_PASSWORD

Never store credentials in the repository. Default execution mode must be preview. Apply must be a deliberate, separately selected action and must update only post 6148.
