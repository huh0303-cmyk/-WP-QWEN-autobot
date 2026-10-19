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
