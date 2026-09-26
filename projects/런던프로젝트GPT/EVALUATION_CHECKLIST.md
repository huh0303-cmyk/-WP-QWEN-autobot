# 런던프로젝트GPT — Evaluation Checklist

This file is the acceptance rubric for the GPT project.

## Architecture
- [ ] GitHub is durable source of truth.
- [ ] VPS is the 24/7 runtime.
- [ ] n8n Community is central orchestration.
- [ ] Control Korea365 is not a duplicate scheduler.
- [ ] browser-only work is isolated to local agent.
- [ ] no Make.com dependency.
- [ ] no new paid SaaS required.

## n8n
- [x] n8n container running on VPS verified.
- [x] n8n health endpoint verified.
- [x] localhost gateway health verified.
- [x] WP25 master imported.
- [x] Blogger33 master imported.
- [ ] remaining masters implemented and verified.
- [ ] restart persistence verified.

## Web publishing
- [ ] WP25 end-to-end receipts verified.
- [ ] Blogger33 end-to-end receipts verified.
- [ ] News2 verified independently.
- [ ] no stale duplicate scheduler remains after migration.

## Local browser
- [ ] LondonLocalAgent packaged.
- [ ] Naver 3 login/profile mapping verified.
- [ ] Tistory 5 login/profile mapping verified.
- [ ] one Naver public URL receipt verified.
- [ ] one Tistory public URL receipt verified.
- [ ] CAPTCHA/login correctly moves job to HOLD.

## YouTube
- [ ] Playlist5 master verified.
- [ ] Knowledge5 master verified.
- [ ] Language registry master verified.
- [ ] video_id/channel_id/privacyStatus evidence stored.

## SNS
- [ ] SNS master implemented.
- [ ] connected-account registry verified.
- [ ] result IDs/URLs recorded.

## Dashboard
- [x] explicit 1위, 2위, 3위 sequential ranking rule implemented.
- [x] four CEO metrics prioritized.
- [x] Google index metric visually emphasized.
- [ ] all displayed values use one consistent definition/source.

## Cleanup
- [ ] obsolete one-off workflows removed.
- [ ] Render-era paths removed.
- [ ] superseded duplicate schedulers removed.
- [ ] no Windows-invalid generated filenames remain in active paths.

## Recovery
- [ ] n8n recovery tested.
- [ ] VPS reboot recovery tested.
- [ ] local-agent restart tested.
- [ ] rollback to known-good commit tested.

## 100% completion gate
All unchecked production-critical items above must have runtime evidence.
