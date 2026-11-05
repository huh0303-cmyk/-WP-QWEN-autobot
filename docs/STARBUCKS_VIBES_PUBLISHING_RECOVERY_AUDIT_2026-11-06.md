# CAFE_STARBUCKSVIBES publishing recovery audit — 2026-11-06

## Target identity

- Channel key: `starbucks`
- Canonical channel: `CAFE_STARBUCKSVIBES` / `@Starbucksvibes`
- Locked YouTube channel ID: `UC_e-sbLkVgwJNYEeobolNog`
- Registry: `config/youtube_channels.json`
- Registry status: `enabled=true`, playlist workflow `generate-youtube-playlist.yml`, configured cadence 2–3 days.
- YouTube Studio dashboard observed 2026-11-06: channel page loads; latest-video card reports approximately 81 days; subscriber count 4. This is UI evidence, not a complete API upload-history audit.

## Confirmed publishing blockers

1. **Automatic publishing is globally disabled by design.** The active GitHub-only scheduler `.github/workflows/youtube-github-scheduler.yml` exits without processing unless both `YOUTUBE_AUTO_PUBLISH_ENABLED=true` and `YOUTUBE_COST_HOLD=false` are explicitly set in the `youtube-channels` environment.
2. **Manual publishing is also cost-hold gated.** `.github/workflows/youtube-github-worker.yml` requires manual `confirm_publication=true`; `automation_hub/youtube_github_runtime.py::check_cost_hold` fails closed unless the hold is explicitly released or a narrowly scoped free-only exception passes.
3. **The only current free-only exception is Globalmusic.** `free_only_channel_allowed()` hard-codes `channel_key == "globalmusic"` and requires its owner-Drive music, Pexels thumbnail, and disabled paid API configuration. Starbucks is not covered. Do not broaden this exception or release the global hold as a side effect of this repair.
4. **Starbucks has no verified free-only production path in the current worker.** The playlist maker defaults to `approved_bank`; its generic image path defaults to `gemini_app_export` and requires an unused, reviewed `gemini_*` image in the Starbucks thumbnail Drive folder. The owner-local audio path exists in the maker but requires a private local manifest and staged audio; the previous 2026-10-19/11-05 audit found that owner-local manifest/audio staging was not available to the GitHub runner. The current repository contains no Starbucks-specific, recent asset-preflight receipt proving a fresh approved 50–70 minute audio mix and a unique reviewed 1280×720 thumbnail.
5. **Recent worker runs are not evidence of a Starbucks attempt.** The latest inspected worker canary runs `42052803008` and `42054528245` were configured for `globalmusic` / CAFE_ROMANTIC. They do not test or publish to Starbucks. The earlier canary failed before production because no eligible future Globalmusic calendar row existed; a later Globalmusic canary also failed during execution. Neither is a Starbucks publication receipt.
6. **OAuth identity and publishing are separate gates.** Historical records say the Starbucks OAuth identity was matched to the locked UC ID and a refresh token was stored in protected locations. That historical identity check is not a current live token-scope check and is not proof of upload permission or a public video.

## Root-cause conclusion

The confirmed current blocker is the GitHub-only publishing safety configuration: automatic scheduling is disabled and the manual worker is fail-closed under the global cost hold. Starbucks has no channel-specific free-only exception, so a manual run cannot proceed while the hold remains active. Independently, the current repository evidence does not prove that Starbucks has a fresh, approved audio pool and unused reviewed thumbnail available to the GitHub runner. The historical OAuth match does not remove either blocker.

## Safe recovery sequence

1. Keep the global cost hold in place. Do not change environment variables or add a Starbucks exception until the owner explicitly approves a fully free-only Starbucks path or separately approves the cost review.
2. Add a read-only Starbucks preflight that verifies: Google Sheets channel enabled state and next eligible calendar row; presence (not values) of the exact Starbucks OAuth secret trio; authenticated `channels.list(mine=true)` exact match to `UC_e-sbLkVgwJNYEeobolNog`; approved audio count, SHA-256 uniqueness, rights, durations, and 50–70 minute mix; and a fresh unused, reviewed 1280×720 thumbnail. Never print tokens or secret values.
3. If the owner-approved assets and no-cost image source pass, implement a narrowly scoped Starbucks free-only path with paid APIs disabled, explicit source selection, and tests. Do not reuse the Globalmusic exception by changing its channel identity or weaken its guard.
4. Run one manually authorized Starbucks canary only after all preflight checks pass. Verify the returned video ID, exact channel ID, title, 50–70 minute duration, thumbnail read-back, privacy status, and public URL.
5. Only after a successful verified canary, enable a randomized 2–3 uploads/week Starbucks schedule and alert on missing calendar rows, failed renders, upload errors, and absent public receipts.

## Actions taken in this audit

- Inspected the target channel in the connected YouTube Studio tab.
- Inspected the repository channel registry, playlist policy, YouTube worker, scheduler, cost-hold runtime, GitHub Actions runs, and the earlier Starbucks gap audit.
- No videos were deleted, edited, made private, or uploaded.
- No secrets, cost-hold settings, or automatic-publication settings were changed.
- This audit is a root-cause record; it does not claim the channel is repaired or publishing has resumed.
