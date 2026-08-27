# Automation Topology — 2026-08-27

Authority: `MASTER_MONETIZATION_STRATEGY_2026.md`.

## Scheduled production/control paths

| Owner | Scheduler | Downstream | Provider | Destination | Safety |
|---|---|---|---|---|---|
| Ordinary WordPress | `publish-scheduler.yml` (:37 hourly) | `daily-network-publish.yml` -> `autopost_current.py` | GPT text; legacy paid image flags off | one WP site | scheduler dispatch cap 1 |
| Newsrooms | `newsrooms-daily-publisher.yml` | `autopost_current.py` | current newsroom writer path | one of two newsroom sites | source, length and quality gates |
| Blogger daily | `blogger-daily-scheduler.yml` (:08/:28/:48) | `blogger-rewrite.yml` | Gemini text | Blogger draft | one connected site/day |
| Sheet platform queue | `platform-publish.yml` (:17 hourly) | `process_platform_queue.py` | pre-generated queue content | Blogger draft; other review paths | duplicate-suspect with Blogger daily |
| YouTube | `youtube-control-scheduler.yml` (:27 hourly) | playlist/knowledge workflows | FLUX Schnell thumbnail policy | one channel dispatch | canonical 10-channel registry, cap 1 |
| Site metrics | `daily-site-traffic.yml` (05:20 KST) | `daily_site_traffic.py` | WP REST + GSC | control Sheet | read-only collection |
| Executive report | `situation-room-daily.yml` (08:10 KST) | `situation_room_daily.py` | GSC/YouTube/official SNS connections | control Sheet + configured notifications | canonical reporting registry |
| Keyword refresh | `weekly-keyword-refresh.yml` | `refresh_keyword_pool_current.py` | Gemini search grounding | keyword pool | weekly |

## Manual/review/maintenance

`automation-hub-bootstrap`, `blogger-rewrite`, `blogger-verify`, `curio-scheduler`,
`curio-longform-daily`, `daily_multilang_quiz`, `deploy-visitor-api`,
`emergency-privacy-lockdown`, `generate-youtube-playlist`, `generate-youtube-video`,
`gsc-post-index-audit`, `health-clinic-daily`, `prune-unindexed-posts`,
`refresh-playlist-thumbnails`, `seouljournal-dashboard-deploy`, `submit-all-sitemaps`,
`topik-longform-weekly`, `topik-quiz-daily`, and `wp-create-draft` are manual or
downstream-dispatched. `prune-unindexed-posts` is destructive and must remain explicit.

## Canonical registries

- Sites/publishing: `config/automation_hub_sites.json` (currently 25 ordinary WP + 2 newsrooms; owner-reported 26 + 2 remains unreconciled).
- YouTube automated publishing: `config/youtube_channels.json` (5 playlist + 5 knowledge).
- YouTube executive-only strategic channels: `config/youtube_reporting_channels.json`.
- Sheet: `SHEET_ID`, currently documented as `12l1w6g-DF4YvVpkEx8YCEsIMTf7TXkUzANm3ldauYiI`.

## Known overlap requiring business confirmation

Blogger daily generation and `자동화_발행대기` can address the same Blogger property.
Neither path was deleted. A shared stable `content_id/source_id` lock is still required
before both schedules can be declared duplicate-safe.
