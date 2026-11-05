# Ten-language YouTube Shorts incident — 2026-11-05

## Root cause: publishing
The 2026-11-05 run 42048171082 completed selection, build, Fish Audio key validation, video generation, and artifact upload. The publish step then failed for all nine selected languages because the publisher required language-scoped OAuth client ID and secret variables while the workflow supplied the shared OAuth client ID and secret. The log explicitly reported Missing YOUTUBE_OAUTH_CLIENT_ID_LANGUAGE_<CODE> for ko, ja, zh, vi, es, fr, de, it, and pt. That manual run's selected list omitted en even though the channel registry contains ten enabled channels.

## Permanent code correction now present on main
Commit 4b462a66369c4e537340c0f12664643555820d88 updates scripts/publish_survival_adjective_shorts.py so CLIENT_ID and CLIENT_SECRET may safely fall back to the shared OAuth application credentials. REFRESH_TOKEN remains strictly language-specific. Exact channel ID verification remains the safety boundary against cross-channel uploads. This matches the current GitHub Actions environment, which supplies one shared OAuth client ID/secret and ten independent language refresh tokens.

## Ten-channel duplicate audit
Run 42048011059 completed a full-history audit of all ten configured language channels (ko, en, ja, zh, vi, es, fr, de, it, pt). It reported 52 duplicate Shorts and the report marked all 52 duplicate video IDs VERIFIED_PRIVATE: en 7, ja 2, zh 12, vi 7, es 7, fr 5, de 7, it 1, pt 4, ko 0. The Italian duplicate was the repeated libro/telefono lesson: retained video TRo2hNm2Dm4; duplicate video 4OZfOu78d68 set private. The Studio page also showed the duplicate upload as private.

## Content controls
- Retain full uploads-playlist history scanning; do not limit duplicate detection to the latest 30/50/500 items.
- Reject repeated semantic pair IDs, content keys, normalized title pairs, and target-language word pairs before media generation and again before upload.
- Keep the B1-B2 adjective curriculum; noun pairs such as book/phone, sun/moon, water/coffee are retired from this series.
- Keep language-specific Fish Audio voice/locale validation and fail closed; do not silently substitute a different voice provider.
- Confirm exact channel ID before upload and confirm public privacy status after upload.
- Do not mark a replacement or old video private until the corrected replacement is verified public.

## Release verification still required
The OAuth fallback code correction is committed, but a new workflow run on the corrected main commit must still be executed and verified. The in-progress runs 42048830045 and 42049150476 were created against the earlier commit and therefore do not validate the correction. The run must use all ten language codes and finish with ten successful public uploads, ten verified channel IDs, ten valid MP4/manifests, and zero duplicate pairs.

## Evidence
- Failed publish run: https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions/runs/42048171082
- Ten-language duplicate audit: https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions/runs/42048011059
- OAuth fallback fix commit: https://github.com/huh0303-cmyk/-WP-QWEN-autobot/commit/4b462a66369c4e537340c0f12664643555820d88
- Duplicate audit artifact: https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions/runs/42048011059/artifacts/13424603491