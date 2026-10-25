# Daily Shorts Run Status — 2026-10-25 (KST)

## Result summary

- Prepared one fact-checked editorial script for each requested channel: 9 scripts total (two Seoul Journal pieces plus seven channel pieces).
- Committed the script pack to this branch.
- Dispatched the existing Seoul Journal private-short workflow twice: once for a Naver Politics auto-selection and once for a current Naver Sports article.
- Both workflow runs stopped at the exact-channel YouTube OAuth preflight with `unauthorized_client`.
- No ElevenLabs narration was generated in either run, no MP4 was rendered, and no video was uploaded.
- No public or scheduled post was created by this run.

## GitHub record

- Branch: `content/daily-shorts-2026-10-25`
- Script-pack commit: `85f307a3fc2297bdc8ea744b1fd8e7ac8ebed70d`
- Script pack: `drafts/shorts-2026-10-25/daily-channel-short-pack.md`

## Workflow attempts

### Seoul Journal politics

- Run: https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions/runs/40152723937
- Status: failed before generation.
- Exact error: `SEOUL_JOURNAL: refresh rejected: unauthorized_client`
- The required secret names were present, but Google's OAuth refresh endpoint rejected the configured client/token combination.
- ElevenLabs validation, FFmpeg installation, narration, rendering, and upload steps were skipped.
- Artifact directory was not created; no MP4 or upload receipt exists.

### Seoul Journal sports / weather risk

- Source article supplied: https://m.sports.naver.com/kbaseball/article/445/0000481806
- Article timestamp shown on Naver Sports: 2026-10-25 10:56 KST.
- Run: https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions/runs/40152817075
- Status: failed before generation.
- Exact error: `SEOUL_JOURNAL: refresh rejected: unauthorized_client`
- The workflow did not reach article extraction, ElevenLabs narration, rendering, or upload.
- No MP4 or upload receipt exists.

## Existing pipeline and local environment audit

- Windows device `ChrisHUH` is online.
- Local Python: 3.11.9.
- Local FFmpeg: 8.1.2.
- No relevant ElevenLabs or YouTube OAuth variables were present in the local process environment.
- No `.env*` file was found in the LondonProject working tree; credential values were not read or exposed.
- `.github/workflows/seoul-journal-daily-shorts.yml` only creates an editorial queue JSON; it does not render or upload a video.
- `.github/workflows/seoul-journal-political-shorts.yml` can create a one-minute political Short and upload it as PRIVATE, but it is gated by exact-channel OAuth preflight. Both attempts failed at that gate.
- `.github/workflows/youtube-health-shopping-daily.yml` produces 3–5 minute videos for Health Clinic USA, Japan, and Seoul Jisoo1, not the requested Shorts. It was not dispatched to avoid substituting a long-form format.
- The repository channel registry points NASA, History Today, Retro Reels, and Old Hollywood to `curio-longform-daily.yml`, but that workflow was not present in the root `.github/workflows` listing on `main` during this audit. The existing `scripts/curio_longform.py` is a long-form generator, not a verified Shorts pipeline.
- Local working tree contains many unrelated modifications and is far behind `origin/main`; it was not used for commits or production builds.

## Exact blockers / next actions

1. Repair the Seoul Journal Google OAuth client/refresh-token pairing. Do not rotate or overwrite secrets blindly; verify the OAuth client that issued the refresh token, then re-authorize the exact `@seouljournal1` channel.
2. Re-run the read-only `scripts/youtube_auth_preflight.py` until it confirms the expected channel ID.
3. Verify the approved Seoul Journal ElevenLabs voice ID; generate narration only with ElevenLabs.
4. Build/render and inspect the actual MP4. If upload is attempted, require a YouTube video ID and verify `privacyStatus=private`.
5. For other channels, add or restore a tested Shorts-specific workflow that consumes the channel-specific narration and approved ElevenLabs voice IDs. Do not substitute the long-form pipeline or an English voice for Japanese.
6. Do not mark any item as rendered/uploaded until the file or platform receipt is present.

## Sources recorded in the script pack

The pack includes source links for all editorial scripts, including Yonhap/AP/Seoul Newspaper for the North Korea–China visit; NOL Ticket, TVING, and a Naver Sports report for the KIA–Samsung playoff weather risk; MHLW and CDC health guidance; NASA's October 23 Artemis III announcement; BFI/San Francisco Silent Film Festival material for The General; and the UN Digital Library/Ask DAG for Resolution 2758.
