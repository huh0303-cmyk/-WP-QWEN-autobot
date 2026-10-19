# Cafe Romantic stale-update audit — 2026-10-19

## Confirmed from the current main branch

- Canonical channel: Cafe Romantic / `globalmusic`, UC `UCbJfEtsffpgI5MsKkB7BYvQ`, handle `@cafe_romantic`.
- `config/youtube_channels.json` had a stale stats snapshot timestamp of 2026-09-05 and old subscriber/video count snapshots. Those are not live analytics and must not be shown as current values.
- Playlist cadence was inconsistent: `config/youtube_channels.json` said every 1 day, while `config/playlist_asset_policy.json` specified 2–3 days and the UI policy says 2–3 uploads per week.
- The asset policy still records `local_library_status=pending_genre_catalog_and_vps_staging` and `daily_publication_runtime_status=not_activated_pending_channel_and_asset_gates`.
- The 2026-10-17 playlist operations note explicitly says the two-month gap still needs a runtime audit of the VPS scheduler, worker queue, OAuth scopes, render pipeline, and recent logs.
- The documented architecture says the Hostinger VPS is the sole production host for YouTube rendering/upload. GitHub Actions must not become a second production publisher.
- The activity ledger records a Cafe Romantic upload on 2026-10-01 (`https://youtu.be/apJCxGytl-g`). Therefore a dashboard saying “last update two months ago” may also indicate that the account-ranking collector is stale or not using the verified YouTube upload receipt; this needs reconciliation against the live YouTube API/Studio and the dashboard's source field.

## Change made

Commit `7f128e636c00a16c3d211fb19ee5a21783ddd689` changes the five playlist channels in `config/youtube_channels.json` to `interval_days_min=2` and `interval_days_max=3`, aligning the registry with the documented 2–3-per-week cadence. It does not trigger an upload.

## Still not verified / required next checks

1. On the VPS, inspect `systemctl list-timers korea365-youtube-scheduler.timer`, worker/scheduler service status, and the latest journal output.
2. Inspect the durable queue/calendar rows for `globalmusic`, especially any `WAITING_FRESH_COMPOSITIONS`, failed, claimed, or due entries.
3. Check the active YouTube cost-hold gate before starting any rendering. Do not bypass it or call paid generation APIs.
4. Verify OAuth identity/read scope for the exact locked UC ID and confirm the most recent upload through YouTube Data API/Studio.
5. Compare that verified latest-publication timestamp with the timestamp displayed in `control.korea365.org/social-accounts`; refresh the collector only after identifying its actual source.
6. Do not mark the issue resolved until a real runtime check and verified publication timestamp are recorded.

## Status

Cadence configuration corrected in GitHub. No claim is made that the VPS runtime is healthy, a new video was rendered, or a new video was uploaded. No existing video was deleted or changed.
