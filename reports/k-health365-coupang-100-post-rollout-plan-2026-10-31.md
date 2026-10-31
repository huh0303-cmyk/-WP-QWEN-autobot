# K-Health365 Coupang Partners 100-post rollout — 2026-10-31

## Owner requirements
- Target: K-Health365.
- Select the 100 eligible posts by actual GA4 page views, descending (not newest 100).
- Select products primarily by high sales volume / purchase popularity; exclude very low-priced, low-value offers. Prefer established products with substantial review/purchase evidence and a meaningful basket price.
- Match products to article topic; never force a supplement into unrelated policy, vaccination, diagnosis, public-health, or news articles.
- Add product image + product title + the owner's Coupang Partners affiliate URL. Upload image to WordPress media where permitted; preserve existing featured images and content.
- Add Coupang Partners disclosure: "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
- Use rel="sponsored nofollow noopener" on affiliate anchors.
- Log every changed post URL, product, affiliate URL, image/media URL, timestamp, and verification result.

## Current verified evidence
- Coupang Partners portal is open in the user's connected browser. The selected product is "관절엔 콘드로이친 1200 900mg x 60정/5박스"; the portal page displayed the generated short link: https://link.coupang.com/a/ihKqEBmP48.
- This is the only currently observed account-generated affiliate URL in the active portal context. Do not invent or derive affiliate URLs for other products.
- A recent public ranking snapshot dated 2026-10-31 lists popular health products including GNM 100억 유산균, 99바이탈 올인원 종합비타민, 종근당건강 프로메가 오메가3 트리플, 뉴트리원 루테인 지아잔틴, GNM 밀크씨슬, 익스트림 마그네슘, 비비랩 콜라겐, 씨스팡 관절팔팔 and 익스트림 멀티비타민. The ranking page itself warns prices/rankings can change and is not an official Coupang sales ledger.
- A Coupang Omega-3 product page showed "한 달간 1만명 이상 구매", 156k+ reviews and a 2026 Best Awards sales-volume award for 종근당건강 프로메가 오메가3 트리플. Use this only as a candidate signal; recheck current listing before final selection.
- GA4 matching work to date has not established a trustworthy full-site top-100 article list. The previously matched subset is insufficient to label the newest 100 posts as the top 100 by views.

## Hard blockers before automatic publication
1. Affiliate URL set: only the chondroitin link above is verified from the active user's portal. Generate a separate account-owned URL for each selected product family (omega-3, multivitamin, probiotic, lutein, milk thistle, magnesium, collagen, vitamin D/calcium, etc.). Do not reuse one product's link for unrelated products.
2. GitHub Actions runtime: the repository has WordPress workflows using a `KHEALTH365COM` secret and `WP_USER`, but the secret's presence/validity cannot be confirmed by reading workflow YAML. A dedicated workflow must test authenticated GET and media/post write access before any batch edit.
3. GA4: retrieve enough pagePath + screenPageViews rows for the full reporting period and join exact URLs to published WordPress posts. Exclude home, category, tag, admin, search, feed, and 404 paths.

## Safe rollout sequence
1. Build the actual top-100 list from GA4 and WordPress post records.
2. Select one or more best-selling, mid/high-value products per eligible article based on current evidence.
3. Validate each product's account-generated affiliate URL and product image source.
4. Run a dry-run report; deduplicate existing cards/disclosures.
5. Apply in small batches with GitHub Actions, using direct WordPress REST API from the runner (not WPVibe). Upload product images to WP media, then patch post content with the hosted image and affiliate URL.
6. Verify each post by fetching it back; record success/failure. Retry only failed items. Stop automatically at 100 verified eligible posts or when no eligible posts remain.

## Current completion
- Verified account-owned affiliate URLs: 1 (chondroitin).
- Posts modified in this rollout: 0.
- Product cards/media inserted in this rollout: 0.
- GitHub background worker: not yet installed or running. Do not tell the owner the PC-off process is active until a GitHub Actions workflow has been committed, required secrets verified by a run, and the first run succeeds.
