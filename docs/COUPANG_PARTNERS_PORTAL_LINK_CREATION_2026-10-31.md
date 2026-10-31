# Coupang Partners — Actual Portal Link Creation Procedure
Date: 2026-10-31 (KST)
Source: authenticated Coupang Partners portal screen inspected during the current session
Repository: huh0303-cmyk/-WP-QWEN-autobot

## Confirmed workflow in the user's logged-in account
The operator is already authenticated to the user's Coupang Partners account. Product links are created from that account's portal UI; there is no need to ask the user to type or disclose a separate partner ID for each product.

1. Open **상품 링크** in Coupang Partners.
2. Search the relevant product or choose a product from the search results.
3. Click that product's **링크 생성** button.
4. The portal opens **링크 생성** for the selected product.
5. The portal displays:
   - a **단축 URL** (example observed in the current session: `https://link.coupang.com/a/iiqJxkUOY0`);
   - an **이미지 + 텍스트** preview;
   - an **HTML** option with **일반태그 / 블로그용 태그** choices and an **HTML 복사** action. The observed HTML included an official Coupang iframe, e.g. `<iframe src="https://coupa.ng/cqy7Lo" ...></iframe>`.
6. Use the portal-generated short URL as the affiliate destination. When the product-card image/creative is required, prefer the portal-generated **블로그용 태그** or other official HTML output as supplied, subject to the destination site's support and Coupang's terms. Do not reconstruct or guess the iframe URL.
7. Store the product title, product identifier, portal-generated short URL, official HTML/tag (if applicable), source image/creative reference, and capture timestamp in that site's own catalog.
8. Repeat for each chosen product. The account's logged-in portal applies the account's affiliate attribution automatically.

## Mandatory disclosure
Coupang portal displayed this required disclosure:
`이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.`
Include it with affiliate placements.

## Important implementation correction
- Do not ask the operator for a partner ID to append manually to every item.
- Do not substitute a generic Coupang home link for product-specific affiliate links.
- Do not treat the example short URL or iframe URL above as a reusable link for other products; each product must have its own portal-generated output.
- Do not scrape a product image from the affiliate short URL as the default method when the portal provides an official image+text / HTML tag. Use the official tag where supported; otherwise record the portal-provided product image URL only if it is actually exposed and permitted for use.
- The browser automation / server worker must not claim to have generated a portal link unless the actual portal-generated output was captured and stored. The current Browser connection is read-only; this document records the verified manual portal flow, not an automated click implementation.
- API automation is a separate optional route requiring Coupang Partners Open API Access Key and Secret Key. Those are not the same thing as the partner ID, and are not required for this manual portal flow.

## Relation to London Project's product rotation
Each website retains its own topic-specific pool (target about 40 offers). For each product, save its own portal-generated link/tag. Article matching filters the site's pool by article topic first, then randomly rotates only relevant, verified products into a 6–7-card block (or fewer if the eligible pool is smaller). Never randomize across unrelated sites or products.
