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
