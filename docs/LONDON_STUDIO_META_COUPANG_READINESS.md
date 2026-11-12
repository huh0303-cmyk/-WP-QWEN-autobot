# London Studio — Meta / Coupang readiness contract

Status: PREPARATION ONLY. Do not infer secret presence or valid publish permissions from configuration or old reports. Never enable live publishing from this document.

## Deployment
- Control console: ControlKorea365.org; planned studio subdomain pending DNS, deployment, authentication.
- GitHub Actions scheduled dispatch works independently of user's PC.
- Store account tokens in GitHub **Environment Secrets**, not repository secrets (repository limit already reached).
- Existing Meta dispatcher uses environment `META-SOCIAL`; legacy `social-publish-one.yml` uses `social-publish`. Do not silently merge or move keys without auditing workflow `environment:` and secret names.
- Never store raw tokens in Git, browser storage, logs, chat, or artifacts.

## Identity and authentication gate
1. Enumerate each exact Instagram, Threads, Facebook Page and TikTok account from live control-center inventory; compare exact immutable platform user/page IDs with current platform API.
2. Instagram and Threads handles are not interchangeable. Historic verified Threads TOPIK handle: `seoultopik`; Instagram: `seoul_topik`. `seoul_chris1` vs `seoul_chris` requires confirmation.
3. Verify token-scoped `/me` ID, required publish scopes, token expiry and refresh path, and one account-specific canary receipt. Never substitute another account's token.
4. Existing META-SOCIAL documented account-token checkpoint (2026-11-07) is historical, not current verification.
5. Keep all public publishing OFF until explicit per-account permission and canary verification; account failures do not block other platforms.

## Environment secrets and variables
- Existing `meta-randomized-dispatch.yml` reads `META_THREADS_<ACCOUNT>_ACCESS_TOKEN`, `META_THREADS_<ACCOUNT>_USER_ID`, `GEMINI_API_KEY` from environment `META-SOCIAL`; `META_LIVE_PUBLISH` is an environment variable.
- Instagram, Facebook and TikTok dispatchers must be audited for their **actual** secret names and `environment:` before adding credentials. Do not invent or overwrite keys.
- Non-secret account IDs may be environment variables; access tokens must be environment secrets.
- Do not create placeholder secrets: empty values are not valid authentication.

## Coupang Partners affiliate gate
- Only use verified product-specific tracking URLs issued in owner's Coupang Partners account. Never fabricate/modify URLs.
- Product record: product ID, title, category, exact tracking URL, approved asset, last validation, target channel, and campaign ID.
- Include the exact disclosure: 이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.
- Instagram caption URLs may not be clickable: use approved profile link hub or Stories link sticker; track link-hub visits and outbound clicks.
- Threads: use a verified permitted link placement and test actual click-through before scaling.
- No misleading earnings claims, fake testimonials, irrelevant products or duplicate spam. Observe platform affiliate/ad policies and Coupang terms.
- Metrics: published permalink, product ID, tracking URL, impressions, profile visits, outbound clicks, conversions and attributable commission where available. Do not infer sales from post count.

## Fail-safe stages
KEYWORD_DISCOVER -> RANK -> PRODUCT_MATCH -> COPY_AND_MEDIA -> QA_AND_DISCLOSURE -> ACCOUNT_AUTH -> DRAFT_OR_CANARY -> PUBLISH -> VERIFY_PERMALINK -> RECEIPT.
Missing affiliate URL, scope, identity or verified media => BLOCKED, not PUBLISHED.
Use durable idempotency key (platform, immutable account ID, content fingerprint, schedule slot). Retry transient errors; do not retry ambiguous publish outcomes without remote verification.

## Next checks
- Read live ControlKorea365 ordering, not obsolete expected counts in `automation_rooms.json`.
- Inspect GitHub environment metadata via authorized CLI/API; this connector cannot list/write environment secrets. Ask owner for OAuth approval only when actually required.
- Validate current Meta token scope and real canary receipts before setting `META_LIVE_PUBLISH=true`.
- Start with one approved product and one verified account per platform, then expand.
