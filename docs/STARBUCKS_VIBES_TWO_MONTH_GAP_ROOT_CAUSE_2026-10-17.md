# Starbucks Vibes publishing gap — root-cause audit (2026-10-17)

## Findings confirmed from repository evidence

### 1. The workflow named `Content Random Scheduler` is not a publisher

File: `automation-master/.github/workflows/content-random-scheduler.yml`

It runs three times daily, creates `scheduler-plan.json`, sets `mode` to `DRAFT_ONLY`, and ends with a safety notice that generation/distribution remain draft/private. It does not render audio/video, enqueue a YouTube upload, call the YouTube API, or verify a published video. Its random `run_this_gate` flags are planning hints only. Therefore its cron being active cannot guarantee a Starbucks Vibes upload.

### 2. The actual uploader is a separate system and the repository explicitly separates scheduling from publication

`docs/YOUTUBE_23_DAILY_READINESS_2026-10-01.md` states that the daily plan timer only writes an audit manifest; the core YouTube scheduler reads a separate Google Sheet; the 15-minute dispatcher owns the upload queue. Calendar rows alone do not invoke the worker or create videos. The same audit documented a real production blocker: `globalmusic` waited at `WAITING_FRESH_COMPOSITIONS` because new original music was required and the Drive bank could not be reused. This is evidence of a content-production/queue gate in the broader playlist system, but is not by itself proof that Starbucks had that exact queue state.

### 3. Starbucks channel identity was previously authorized, but authorization is not publication

`docs/YOUTUBE_23_DAILY_READINESS_2026-10-01.md` records an exact `channels.list(mine=true)` match for Starbucks Vibes channel ID `UC_e-sbLkVgwJNYEeobolNog` and storage of its refresh token in protected VPS runtime and GitHub Actions. It explicitly says this is not a public-video receipt. Thus a channel token/identity grant alone does not explain or fix the two-month publishing gap.

### 4. The current evidence does not establish a live VPS scheduler/worker state for 2026-10-17

The latest inspected repository evidence establishes the workflow's draft-only nature and the separation between calendar and uploader, but no fresh VPS service status, queue row, upload log, or YouTube publish receipt was available in this audit. We must not invent a more specific Starbucks failure such as expired OAuth, a stopped systemd service, missing music assets, or a particular failed queue item without that runtime evidence.

## Root-cause conclusion

**Confirmed design/root-cause:** the visible randomized scheduler is only a `DRAFT_ONLY` planning gate and is not connected to an end-to-end generation → queue → upload → post-upload verification flow. Consequently, it can run on schedule while no video is published. The system also has a separately managed Google Sheet/15-minute dispatcher, so missing calendar entries, failed queue rows, production blockers, or a stopped dispatcher can independently halt publication.

**Not yet proven for this exact channel:** whether Starbucks Vibes' two-month gap was caused by a stopped VPS timer/service, missing/failed Starbucks queue entries, no fresh rendered music assets, a dispatch error, or token/scope revocation. To resolve that last-mile cause, collect live evidence from `korea365-youtube-worker.service`, the 15-minute dispatcher/timer, queue rows for `CAFE_STARBUCKSVIBES`, the protected runtime token preflight (never print token values), latest worker logs, and YouTube API recent-upload list for `UC_e-sbLkVgwJNYEeobolNog`.

## Required repair sequence

1. Inspect the live VPS service/timer state and last successful/failed runs.
2. Inspect the Google Sheet queue for `CAFE_STARBUCKSVIBES`, including failed rows and exact error messages; do not reset/retry ambiguous uploads before reconciliation.
3. Confirm fresh original music and final rendered file exist, validate duration, title, thumbnail, and audio uniqueness.
4. Verify authenticated `mine=true` channel ID exactly equals `UC_e-sbLkVgwJNYEeobolNog`.
5. Publish only after all checks pass, then verify returned video ID, exact channel ID, title, duration, privacy state, and public watch URL.
6. Implement a 2–3 uploads/week randomized cadence with actual queue dispatch and failure alerts; do not use random planning flags as a substitute for scheduled uploads.

No videos were deleted or published by this audit. This report records repository-backed findings and clearly marks the remaining runtime evidence requirement.