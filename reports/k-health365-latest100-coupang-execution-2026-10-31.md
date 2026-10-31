# K-Health365 Coupang product-card pilot — 2026-10-31

## Request and scope
- Task ID: `khealth-coupang-latest100-20261031-1104-kst`
- User narrowed the immediate scope to one matching post first: choose a Coupang product based on the post topic, insert the affiliate link and product image, and confirm one post succeeds.
- Target site: https://k-health365.com
- No GitHub Actions workflow was dispatched. The existing one-post workflow is hard-coded to a different post and product and was not used.

## Pilot result
- Post ID: 7368, “비타민 미네랄 복합제 선택 시 고려해야 할 성분 구성과 올바른 섭취 기준”
- Product search: Coupang Partners query “멀티비타민”; selected “고려은단 멀티비타민 올인원 우먼 60 플러스, 3개, 60정” (Coupang result displayed 61,950 KRW; 11% discount).
- Account-generated affiliate URL: https://link.coupang.com/a/ihPGNw5JzU
- Official Coupang iframe widget URL: https://coupa.ng/cqyBrW
- Added one product card with a text affiliate link, Coupang-hosted product image/widget, and affiliate disclosure.
- WordPress read-back confirmed the card and link were saved. Post remained published with its original date; featured_media stayed 0 before and after. The idempotency marker `khealth-coupang-product-7368` was present once.
- Public page was opened and visually checked: the text link, product image, shopping button, and disclosure rendered.
- Public post: https://k-health365.com/%eb%b9%84%ed%83%80%eb%af%bc-%eb%af%b8%eb%84%a4%eb%9e%84-%eb%b3%b5%ed%95%a9%ec%a0%9c-%ec%84%a0%ed%83%9d-%ec%8b%9c-%ea%b3%a0%eb%a0%a4%ed%95%b4%ec%95%bc-%ed%95%a0-%ec%84%b1%eb%b6%84-%ea%b5%ac%ec%84%b1/

## Scope correction and verification
During the earlier broader request, three additional cards were temporarily inserted into posts 7372, 6148, and 7275. After the user clarified “one first,” those three cards were removed. Fresh WordPress REST read-backs on 2026-10-31 confirmed all three posts contain neither their task marker nor a Coupang affiliate URL. Their published status, dates, and featured_media remained unchanged (7372: 0; 6148: 6824; 7275: 0).

## Limits and remaining work
- This completes one live pilot only; the latest 100 have not been updated.
- Coupang’s ranked search result was used for product selection, but a verified unit-sales count was not available in this session; do not describe the product as proven highest-selling.
- No media was uploaded and no existing featured image was changed.
- No tests were run.
- A GitHub Actions batch run and full 100-post saved-state verification have not occurred.
