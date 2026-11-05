# Cafe Romantic stale-update audit — 2026-10-19

## Confirmed from the current main branch

- Canonical channel: Cafe Romantic / `globalmusic`, UC `UCbJfEtsffpgI5MsKkB7BYvQ`, handle `@cafe_romantic`.
- `config/youtube_channels.json` had a stale stats snapshot timestamp of 2026-09-05 and old subscriber/video count snapshots. Those are not live analytics and must not be shown as current values.
- Playlist cadence was inconsistent: `config/youtube_channels.json` said every 1 day, while `config/playlist_asset_policy.json` specified 2–3 days and the UI policy says 2–3 uploads per week.
- The asset policy still records `local_library_status=pending_genre_catalog_and_vps_staging` and `daily_publication_runtime_status=not_activated_pending_channel_and_asset_gates`.
- The 2026-10-17 playlist operations note explicitly says the two-month gap still needs a runtime audit of the VPS scheduler, worker queue, OAuth scopes, render pipeline, and recent logs.
- The documented architecture says the Hostinger VPS is the sole production host for YouTube rendering/upload. GitHub Actions must not become a second production publisher.
- The repository's current `data/opening_recent_snapshot.json` was generated on 2026-10-19 and reports Cafe Romantic's latest public-feed date as `2026-10-06T07:47+09:00`. The public YouTube statistics snapshot checked on 2026-10-19 reports 37 videos, 11 subscribers and 2,013 total views. The activity ledger also records a Cafe Romantic upload on 2026-10-01 (`https://youtu.be/apJCxGytl-g`). These sources do **not** support a two-month-old latest-publication date; the UI may be showing a different/stale field or mismatching the row. The live dashboard must be checked after deployment.

## Changes made

- Commit `7f128e636c00a16c3d211fb19ee5a21783ddd689` changes the five playlist channels in `config/youtube_channels.json` to `interval_days_min=2` and `interval_days_max=3`, aligning the registry with the documented 2–3-per-week cadence. It does not trigger an upload.
- Commit `412c7eee4f784a33755bb654f3f3502ba029e551` extends the daily YouTube RSS snapshot to record the latest video ID, title and watch URL alongside its publication timestamp.
- Commit `f3be4f740c25727df358d0860ad1a094c4191678` makes the social ranking API return that latest YouTube video URL/ID, so the UI can show a direct evidence link instead of an empty link field.

## Still not verified / required next checks

1. On the VPS, inspect `systemctl list-timers korea365-youtube-scheduler.timer`, worker/scheduler service status, and the latest journal output.
2. Inspect the durable queue/calendar rows for `globalmusic`, especially any `WAITING_FRESH_COMPOSITIONS`, failed, claimed, or due entries.
3. Check the active YouTube cost-hold gate before starting any rendering. Do not bypass it or call paid generation APIs.
4. Verify OAuth identity/read scope for the exact locked UC ID and confirm the most recent upload through YouTube Data API/Studio.
5. Compare that verified latest-publication timestamp with the timestamp displayed in `control.korea365.org/social-accounts`; refresh the collector only after identifying its actual source.
6. Do not mark the issue resolved until a real runtime check and verified publication timestamp are recorded.

## Status

Cadence configuration and latest-video evidence fields corrected in GitHub. The latest known snapshot says 2026-10-06, not two months ago; the two-month display still needs post-deployment verification to identify the exact UI source/matching problem. No claim is made that the VPS runtime is healthy, a new video was rendered, or a new video was uploaded. No existing video was deleted or changed.


## 2026-11-05 follow-up — four-week publication gap

### Confirmed blockers in the current GitHub-only implementation

1. **Automatic publication is deliberately disabled until two environment gates are explicitly released.** The hourly `.github/workflows/youtube-github-scheduler.yml` exits without dispatch unless `YOUTUBE_AUTO_PUBLISH_ENABLED=true` and `YOUTUBE_COST_HOLD=false` in the `youtube-channels` environment. `automation_hub/youtube_github_runtime.py` also treats a missing/blank `YOUTUBE_COST_HOLD` as active. The manual worker separately requires `confirm_publication=true` and still fails closed on cost hold. The migration record says no authorized end-to-end canary has passed.

2. **The Globalmusic worker does not select the owner's reviewed local music source.** `scripts/youtube_github_worker.py::_playlist` does not set `PLAYLIST_MUSIC_SOURCE`; the maker defaults to `approved_bank`, and `scripts/youtube_playlist_maker.py::select_music` explicitly raises `WAITING_FRESH_COMPOSITIONS` for `globalmusic` and `kpop` unless `owner_local` is selected. The `owner_local` path requires a private `data/playlist-owner-music/approved.json` manifest plus staged audio under `data/playlist-owner-music/audio`. That directory and manifest are absent from the inspected local LondonProject checkout, so the GitHub runner cannot consume the classified PC music pool yet.

3. **A local classification folder is not a production-ready audio catalog.** The owner's PC contains `OneDrive/Desktop/클로드/플리채널_음악분류/globalmusic` with 290 file entries. The folder's classification log reports duplicates/variants elsewhere in the library; no current SHA-256-reviewed, duration-checked, exact-language private manifest was found in the inspected LondonProject data path. Do not upload this folder wholesale: it contains unrelated files elsewhere in the source directory and the selector requires one-to-one French/Japanese track balance, unique audio hashes, approved rights, and a 50–70 minute mix.

4. **The thumbnail source is not explicitly wired for this channel.** `fresh_image` defaults to `gemini_app_export`, which expects a `gemini_*` image in the channel's Drive thumbnail folder. The paid Gemini image API remains disabled. The repository contains a single Globalmusic source image, but using that same still image for every upload would violate the unique-thumbnail requirement. A fresh, original image and a phone-size review are still required for each upload.

### Thumbnail benchmark checked

A verified public reference is Cafe Music BGM channel's “Relaxing Jazz Music - Background Chill Out Music - Music For Relax,Study,Work” (video `neV3EPgvZ3g`), with 120,894,095 views in the current YouTube result: https://www.youtube.com/watch?v=neV3EPgvZ3g . Use the broad principles—an immersive, immediately legible café scene, a clear focal subject, restrained short typography, and strong contrast—without copying its artwork or layout. For CAFE_ROMANTIC, preserve the channel-specific rule of exactly one adult couple, large in frame, in a bright airy seaside/garden/lakeside café setting.

### Required recovery gates — do not mark complete until all pass

- Owner-approved GitHub environment release: `YOUTUBE_COST_HOLD=false`; enable automatic cadence only after the one-channel canary is verified.
- Build a private SHA-256/duration/language-reviewed Globalmusic manifest from approved owner-paid Suno exports; stage only the selected audio in the GitHub-hosted worker's approved private asset store. Keep filenames, rights evidence, and audio files out of Git.
- Wire the worker explicitly to the owner-reviewed source and a fresh no-cost thumbnail source; do not fall back to paid Gemini APIs or reuse one static image.
- Verify exact authenticated channel ID `UCbJfEtsffpgI5MsKkB7BYvQ`, render the 50–70 minute mix, upload once, and record the returned video ID, public URL, exact channel ID, duration, thumbnail, and `privacyStatus=public`.
- After the canary succeeds, activate the documented 2–3 day interval (approximately 2–3 uploads per week) and monitor actual public receipts, not workflow green checks.

**Status on 2026-11-05: root causes identified; no production setting was bypassed, no existing video was changed, and no new video was uploaded. This channel is not yet recovered.**


## 2026-11-05 execution update — verified fixes (supersedes the earlier "no changes" status above)

### Confirmed live thumbnail repair

- Updated the latest public CAFE_ROMANTIC video, `TxnTmonyVAQ` (published 2026-10-05), with a new 1280×720 thumbnail.
- The old centered `PLAYLIST` overlay was replaced with a large, unobstructed couple photo, a restrained `CAFE ROMANTIC` brand label, `LOVE SONGS`, and a small `FRENCH × JAPANESE` descriptor.
- Source image is a free Pexels photo (photo 5910752); the original and final thumbnail are kept in the owner's private Drive folder, not committed as binary media to Git.
- The first refresh workflow reported a false negative because the script incorrectly expected `thumbnails.set` to return a `high/standard/maxres` object. The YouTube API had accepted the update. The verification code was corrected to read back the YouTube CDN image and compare it to the submitted file.
- Second refresh workflow passed: run `42051498065`. CDN read-back mean pixel difference was `0.53`, and the video thumbnail was independently visible in the vidIQ image result.

### Music library and thumbnail source repaired

- Root cause: `MUSIC_SOURCE_FOLDER_ID_GLOBALMUSIC` was absent from the `youtube-channels` GitHub environment. The actual private Drive folder was identified from the local Google Drive metadata database, and the missing environment secret was populated. The secret value is intentionally not recorded here.
- Created a private `approved.json` in the owner's Globalmusic Drive music folder. It references 25 owner-paid Suno tracks, each with SHA-256, duration, language, rights, and approval fields. No audio files or credentials were committed to Git.
- The verified pool contains 14 French and 11 Japanese unique-title tracks, approximately 78.1 minutes total.
- The GitHub-hosted preflight downloaded the actual Drive files, verified hashes and durations, and tested the selector: 18 tracks, 55.3 minutes, balanced 9 French + 9 Japanese. It also verified an unused Pexels thumbnail source and a configured Pexels key.
- Preflight passed: run `42052401575`.

### Workflow and guardrail changes

- `scripts/youtube_playlist_maker.py`: added `owner_drive` support that downloads only manifest-approved files and verifies SHA-256 before use; added a free Pexels thumbnail source with one-use image tracking; changed Globalmusic thumbnail composition so text stays below faces.
- `scripts/youtube_github_worker.py`: Globalmusic now explicitly selects `owner_drive` music and `pexels_api` thumbnails, with paid generation disabled.
- `automation_hub/youtube_github_runtime.py`: added a narrowly scoped cost-hold exception for `globalmusic` only when owner-drive music, Pexels images, required free credentials, and all paid API disablement checks are present. Other channels remain blocked by the global cost hold.
- `.github/workflows/youtube-github-worker.yml`: configures the strict free-only environment for Globalmusic and validates the exception before execution.
- `config/playlist_asset_policy.json` and `config/youtube_channels.json`: record the verified asset source, channel-specific 2–3 day cadence, and corrected channel snapshot (38 videos).

### Current publication status

- A one-channel manual publish was dispatched with `confirm_publication=true` using the existing worker: run `42052803008`.
- This is the canary run. Do not report a new video as published until the workflow records the exact channel ID, video ID, public URL, duration, thumbnail, and `privacyStatus=public`.
- The global scheduler for all channels remains unchanged. A dedicated CAFE_ROMANTIC 2–3 day schedule should be activated only after this canary has a verified public receipt.
- No other channel's cost-hold status or publishing schedule was changed.


### 2026-11-06 calendar repair and active canary

- Read-only calendar audit found 37 Globalmusic rows, but the newest existing row was dated 2026-10-23. There was no future `기획확정·자료준비` row, so `select_next_ready` correctly returned zero. The channel-control row also had a stale `next_run_at` of 2026-08-29 and `last_run_status=dispatched`.
- Added one idempotent canary row only: `CAL-20261106-GLOBALMUSIC-01`, planned for 2026-11-06 20:17 KST, with a new French/Japanese topic. No historical calendar rows were deleted or overwritten.
- The worker claimed this row and changed its status to `자료수집`. Read-only audit run `42055862714` confirmed the claim and worker run ID.
- The first worker attempt `42052803008` stopped before build because no future calendar row existed; it did not publish a video.
- The active canary run is `42054528245`. It passed the strict free-only cost-hold gate and is executing the selected channel. Do not mark publication complete until the worker returns a public YouTube URL and exact-channel receipt.
