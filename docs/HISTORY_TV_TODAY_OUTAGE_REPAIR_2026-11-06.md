# HISTORY_TV_TODAY publishing outage — 2026-11-06

Channel: HISTORY_TV_TODAY / @HISTORY_TV_TODAY  
Locked channel ID: `UCVBvZwodUF4s57KeNicxQ3w`  
Scheduler key: `history`

## Confirmed code-level causes

1. **Automatic publishing is intentionally gated off by default.** `.github/workflows/youtube-github-scheduler.yml` exits before checkout or execution unless the `youtube-channels` environment has `YOUTUBE_AUTO_PUBLISH_ENABLED=true` and `YOUTUBE_COST_HOLD=false`. The worker independently fails closed while cost hold is active. This is a deliberate safety control, not a scheduler crash.
2. **Scheduled knowledge jobs were missing the Fish Audio secret in the workflow environment.** `scripts/youtube_github_worker.py::_knowledge` explicitly raises when `FISH_AUDIO_API_KEY` is empty. The manual worker workflow passed this secret, but the hourly scheduler workflow did not. Fixed on 2026-11-06 by adding `FISH_AUDIO_API_KEY: ${{ secrets.FISH_AUDIO_API_KEY }}` to the scheduler job environment (commit `71ddd8a85b8a9e1b20bd02c07471ab32c6204f97`).
3. **History's approved editorial contract is not fully integrated.** `docs/TODAY_IN_HISTORY_PIPELINE.md` states that `history_episode_contract.py` is only an offline validator and is not wired into the legacy renderer/scheduler. The active worker still routes the history key through `archive_footage_longform.py`, not a complete date-frozen two-event production path. This remains an implementation gap; do not claim full restoration.
4. **Channel write authorization has not been proven by this inspection.** Historical records report HTTP 403 on read-only OAuth identity checks for the History upload connection. The worker must verify the exact authenticated UC ID before upload; no alias/brand label is acceptable.

## Changes made

- Added the missing Fish Audio secret mapping to the hourly GitHub scheduler workflow.
- Preserved the existing fail-closed cost hold and auto-publish gates.
- No secret values were read or changed.
- No workflow was dispatched, no video was generated/uploaded, and no publication state was changed.

## Required release checks

1. In GitHub Actions → `youtube-channels` environment, verify `FISH_AUDIO_API_KEY` exists and is valid; do not print its value.
2. Owner must explicitly complete the cost review before setting `YOUTUBE_COST_HOLD=false`; then decide whether automatic publishing should be enabled with `YOUTUBE_AUTO_PUBLISH_ENABLED=true`.
3. Run a controlled History-only canary after the owner authorizes it. Verify OAuth `channels.list(mine=true)` returns exactly `UCVBvZwodUF4s57KeNicxQ3w`.
4. Validate the full episode contract (two sourced same-month/day events, newest-first, scene-matched footage, rights, audio, captions, thumbnail) and retain a durable receipt with video ID, channel ID and privacy state.
5. Do not delete, overwrite, or change visibility of existing videos. Do not automatically backfill the missed dates.

## Current status

**Partially repaired; production remains HOLD.** The scheduled-worker secret omission is fixed in GitHub main. Automatic publishing remains gated by the existing safety variables, History's full editorial integration and channel write authorization remain unverified, and no successful canary/public upload is claimed.
