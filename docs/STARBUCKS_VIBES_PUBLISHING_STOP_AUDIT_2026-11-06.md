# Starbucks Vibes publishing stop audit — 2026-11-06

Target: CAFE_STARBUCKSVIBES / @Starbucksvibes

Channel ID: `UC_e-sbLkVgwJNYEeobolNog`; registry key: `starbucks`.

## Confirmed blockers

- The 2026-11-05 read-only OAuth preflight records the exact Starbucks channel ID. This is identity verification, not a public upload receipt.
- The current `.github/workflows/youtube-github-worker.yml` is `workflow_dispatch` only and requires `confirm_publication=true`. The runbook explicitly keeps automatic 10-channel cadence disabled until migration, CI, read-only preflight and an authorized canary pass.
- `automation_hub/youtube_github_runtime.py` fails closed unless `YOUTUBE_COST_HOLD=false`; the only free-only exception is `globalmusic`. Starbucks is blocked before a calendar row is claimed. Do not bypass the global hold or enable paid APIs.
- `scripts/youtube_github_worker.py::_playlist` explicitly configures owner-Drive/Pexels only for Globalmusic. Starbucks falls through to `approved_bank` music and `gemini_app_export` thumbnails. The latter requires a reviewed `gemini_*` image in the Drive thumbnail folder; the 2026-10-01 batch receipt recorded Starbucks as `WAITING_ASSETS` because an approved Gemini thumbnail was missing.
- `scripts/playlist_owner_library.py` has a Starbucks `instrumental_cafe` selector with SHA-256/rights/duration checks and a 50–70 minute target, but the GitHub worker does not activate `owner_local` for Starbucks. No current runner preflight proves a complete reviewed pool and fresh unique 1280x720 thumbnail are available.
- `config/youtube_channels.json` retains the legacy workflow label `generate-youtube-playlist.yml`; the current executable is `.github/workflows/youtube-github-worker.yml`. Changing that label alone would not restore publication.

## Root cause

The channel's OAuth identity is recorded as verified. Publication is stopped because the GitHub-only worker has no enabled automatic cadence, the global cost hold blocks Starbucks, and no verified free-only Starbucks music/thumbnail path is wired into the worker.

## Safe recovery

1. Keep the global cost hold and paid API paths disabled.
2. Prepare a private Starbucks `approved.json` and reviewed instrumental-cafe audio pool with owner-confirmed rights, unique hashes, validated durations, and enough tracks for 50–70 minutes. Keep audio and private filenames out of Git.
3. Add a read-only Drive preflight for the Starbucks music and thumbnail folders; require fresh unused original 1280x720 art.
4. Add a narrowly scoped free-only Starbucks worker path, with Gemini/Lyria/paid APIs disabled and fail-closed asset checks.
5. Run CI and one owner-authorized canary; verify video ID, exact channel ID, title, duration, thumbnail CDN read-back, and `privacyStatus=public`.
6. Only after a verified public receipt, enable a randomized 2–3 uploads/week schedule with idempotent claims and failure alerts.

## Audit actions

Diagnosis recorded. No secrets, environment variables, OAuth tokens, Sheet rows, or existing videos were changed. No publish run was dispatched, no paid API was called, and no upload is claimed.
