# CAFE_MOZART free-only recovery implementation — 2026-11-06

Channel: `@cafe_mozart`
Expected YouTube channel ID: `UC7jOhyMa-FIrzZuea97z1Pw`
Registry key / credential profile: `mbb` / `MBB`

## Owner approval
Owner approved a CAFE_MOZART-only recovery using no paid APIs, existing approved music, and free image sourcing. The global YouTube cost hold remains unchanged.

## Implemented in GitHub
- Added `.github/workflows/cafe-mozart-publish.yml`: GitHub-hosted Ubuntu runner, daily candidate check, deterministic 2–3 releases per ISO week, and manual dispatch input.
- The workflow sets a narrow MBB-only free mode: `PLAYLIST_MUSIC_SOURCE=approved_bank`, `PLAYLIST_IMAGE_SOURCE=pexels_api`, `PLAYLIST_PAID_API_ENABLED=false`, `AUTO_TOPIC=false`, and blanks Gemini/OpenAI/Lyria keys.
- Extended `automation_hub/youtube_github_runtime.py` with a strict MBB exception under the global cost hold. It requires Google Drive credentials, the MBB music/output/thumbnail folders, Pexels API key, and MBB-specific YouTube OAuth credentials. All paid-generation keys must be empty.
- Updated `scripts/youtube_playlist_maker.py`: MBB uses existing Drive approved-bank audio; Pexels queries focus on grand pianos, classical concert halls, orchestras, sheet music and strings; previously used Pexels photo IDs are excluded from future MBB thumbnails.
- Added a dedicated CAFE MOZART thumbnail treatment: 16:9 1280×720, refined serif typography, charcoal/ivory/champagne-gold palette, a clean left-side text field, and the classical instrument/concert photograph as the visual hero. Text stays away from the image's focal area.
- Updated `scripts/youtube_publish_approved.py`: Mozart upload is private until the real thumbnail is successfully applied; only then is it switched to the release-policy public state. Missing/failed thumbnail blocks public release.
- Added `artifacts/cafe_mozart_upload_guard.json` idempotency guard. A Mozart upload that has not reached verified state blocks another upload attempt until reconciled; this prevents duplicate uploads after ambiguous failures.
- Added tests in `tests/test_cafe_mozart_free_publish.py` covering the MBB-only exception, required free sources, and rejection of paid-generation keys.

## Validation
- Python compile checks passed in GitHub Actions run `42062316775` for the publisher/runtime files.
- The dedicated MBB free-mode tests and the full playlist owner-policy tests passed in runs `42062301592`, `42062530199`, and `42062547010`.
- The compile check, cost-hold guard tests, and playlist owner-policy tests all completed successfully after the thumbnail-publication fail-safe and upload-idempotency guard were added.
- The separate daily publisher is committed on the default branch. It is scheduled for a daily 02:31 UTC candidate check; the in-workflow weekly gate permits only the selected two or three weekdays.

## Explicit limitations / remaining verification
- No upload is claimed by this implementation commit.
- The live GitHub Actions dispatch could not be initiated from the available GitHub connection in this session. The owner can start the first canary from Actions → CAFE MOZART - Free-Only GitHub Publisher → Run workflow → set `publish_now=true`.
- The first run must confirm that the Google Sheet has a ready `mbb` calendar row and that the MBB Drive music and thumbnail folders contain usable approved assets. If not, it will fail visibly without using paid APIs or publishing a placeholder.
- Verify the run artifact, final thumbnail preview, exact `mine=true` channel ID, returned video ID, duration, and public status before calling the channel fully recovered.
- Existing videos are not deleted or modified.
