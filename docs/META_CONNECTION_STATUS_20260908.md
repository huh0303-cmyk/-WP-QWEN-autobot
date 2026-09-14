# Meta connection verification — 2026-09-08

App: SIS Center Publisher, 1383946033947009. Portfolio: SeoulTopik.

## Verified configuration changes
- Added pages_manage_posts in the Pages API use case. Status: ready for testing.
- Added instagram_content_publish in the Instagram API use case. Status: ready for testing. instagram_basic was already ready for testing.
- Added threads_content_publish in the Threads API use case. Status: ready for testing. threads_basic was already configured.
- A fresh Facebook OAuth request now includes pages_manage_posts, instagram_basic, and instagram_content_publish. The previous Invalid Scopes response preceded these additions. Token issuance has NOT completed.

## Remaining blockers and verification
- Browser OAuth is still on the Jungyoon Huh / SIS Center Publisher Continue screen. No new page token, Instagram ID, or Threads token has been verified.
- Repository secret writes returned HTTP 400 using both gh secret set and REST sealed-box encryption. No new credentials or page-ID secrets were saved.
- ENGLISH expected Facebook Page ID: 61592457107609.
- LANGUAGE expected Facebook Page ID: 61593057083167.
- Do not infer that me/accounts error 100/33 proves a business-verification requirement. Check token permissions, authorized assets, and the exact Page endpoint response first.
- scripts/social_publish.py currently finishes Facebook Reels with video_state=DRAFT. An upload success is not a published Facebook post.
- Instagram and Threads use distinct account credentials. A Facebook page token does not replace a Threads user token.
- social-publish-one.yml needs source media metadata and a publicly reachable HTTPS video URL for Instagram/Threads. Registering tokens alone is insufficient.
- Do not dispatch a publishing test or claim successful publication until credentials, target identity, input media, and publication result have been checked.

## Concurrent playlist delivery
Cafe Mozart rendered successfully in Actions run 34188476253, commit 5fc90ba9ce68f24802ca0088845e3fbbc037f38a. 25 complete piano movements, measured 3570.64 seconds. Full video artifact retained for 7 days. It is rendered_not_uploaded; private YouTube upload still needs valid channel-scoped authorization.
