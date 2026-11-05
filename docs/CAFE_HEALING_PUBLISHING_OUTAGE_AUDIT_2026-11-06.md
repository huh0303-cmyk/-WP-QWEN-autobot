# CAFE HEALING publishing outage audit — 2026-11-06

## Channel identity
- User-requested handle: @cafe_healing1
- Locked channel key: healing
- Locked UC ID: UC7yEsLM-HoXudngrD-4FIqg
- Source of truth: config/YOUTUBE_23_CHANNEL_MASTER_LOCK_2026-09-27.json and config/youtube_channels.json

## Confirmed blocking conditions
1. .github/workflows/youtube-github-scheduler.yml exits successfully without dispatch when YOUTUBE_AUTO_PUBLISH_ENABLED is not exactly true OR YOUTUBE_COST_HOLD is not exactly false.
2. automation_hub/youtube_github_runtime.py treats an unset/true YOUTUBE_COST_HOLD as active and rejects all playlist publishing except its existing narrowly scoped Globalmusic free-only exception.
3. The manual youtube-github-worker.yml requires confirm_publication=true and still rejects healing while the global cost hold is active.
4. The existing worker does contain a healing renderer route (scripts/healing_motion.py), so the outage is not accurately described as a missing renderer. The missing piece is an enabled, safe, channel-scoped scheduled dispatch path and a verified production run.
5. docs/CAFE_HEALING_CONTENT_AND_GITHUB_SCHEDULE_2026-10-17.md explicitly requires 2–3 randomized releases/week and post-upload verification, but says its GitHub-native end-to-end deployment and receipt were not yet verified.

## Important safety constraints
- Do not switch off the global YOUTUBE_COST_HOLD or globally enable all YouTube channels as a channel-specific repair.
- The healing renderer can operate without Gemini/OpenAI/Lyria/Fish Audio generation: rain audio is synthesized locally with FFmpeg; creek ambience uses Pexels footage and bundled CC0 bird audio.
- Any healing-only cost-hold exception must require explicit PLAYLIST_FREE_ONLY_CHANNEL=healing, PLAYLIST_PAID_API_ENABLED=false, blank paid-provider keys, the healing-only OAuth secret trio, Google Sheets credentials, and the exact locked UC ID check immediately before upload.
- The scheduler must select only a due healing calendar row; it must not use the manual run-now selector or upload a future calendar row early.
- Keep existing videos. Never retry an ambiguous upload without reconciling the YouTube upload history and stable marker.

## Verification still required
A code review does not prove the GitHub Actions environment secrets exist or are valid. The first scheduled run must verify:
1. The healing calendar row is due and channel is ON in the control sheet.
2. OAuth mine=true equals UC7yEsLM-HoXudngrD-4FIqg.
3. Render duration is 74–175 minutes, with no music or narration and a valid thumbnail.
4. The upload receipt reports the exact channel ID, video ID, PUBLIC privacy, duration, and watch URL.
5. The GitHub Actions run completes successfully and the new video appears on @cafe_healing1.

## Status
Root-cause review completed from repository code and policy. No global cost gate was bypassed, no secrets were read, no video was uploaded, and no existing video was changed in this audit.
