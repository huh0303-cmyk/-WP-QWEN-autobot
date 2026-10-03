# Automation Topology — 2026-08-27

Authority: `MASTER_MONETIZATION_STRATEGY_2026.md`.

## Scheduled production/control paths

| Owner | Scheduler | Downstream | Provider | Destination | Safety |
|---|---|---|---|---|---|
| Ordinary WordPress | `publish-scheduler.yml` (:37 hourly) | `daily-network-publish.yml` -> `autopost_current.py` | GPT text; legacy paid image flags off | one WP site | scheduler dispatch cap 1 |
| Newsrooms | `newsrooms-daily-publisher.yml` | `autopost_current.py` | current newsroom writer path | one of two newsroom sites | source, length and quality gates |
| Blogger daily | `blogger-daily-scheduler-v2.yml` (:08/:28/:48) | `blogger-rewrite.yml` | GPT-5 mini text | Blogger draft | one connected site/day |
| Sheet platform queue | `platform-publish-v2.yml` (:17 hourly) | `process_platform_queue.py` | pre-generated queue content | Blogger draft; other review paths | duplicate-suspect with Blogger daily |
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

## 2026-10-03 implementation status — do not mistake target architecture for live cutover

- The locked architecture names n8n as the intended central orchestrator, but the
  checked-in `wp25_master.json` and `blogger33_master.json` both have `active: false`.
  The deploy workflow imports both and explicitly publishes only the four-agent
  content workflow. This repository state does not establish that the two scheduled
  master workflows are active on the VPS.
- The VPS preflight on 2026-10-03 found the Blogger daily timer, WP publisher service,
  operations service, and n8n gateway installed/enabled. A unit-file listing is not
  proof that a timer fired successfully or that a public post was created.
- Therefore the 60-site schedule is **not yet proven to be a single n8n-owned path**.
  Do not activate the n8n master schedules or disable the existing publishers until
  a shared per-site/date/content idempotency key, duplicate reconciliation, and
  receipt-backed end-to-end canaries pass for WP and Blogger.
- The four-agent console had a separate 12-second webhook-start timeout that could
  label an ambiguous n8n acknowledgement as a terminal start failure. The UI now
  keeps that run in acknowledgement-pending status and polls the same `run_id`;
  it must not automatically submit a second run. This code change was tested and
  included in PR #203; follow-up deployment receipt is recorded in the activity ledger.
- The YouTube knowledge job runner remains a separate VPS worker; its Oct 3 queue
  audit showed no pending/running jobs. Do not treat that worker as a blog publisher
  or as proof that n8n owns the complete blog schedule.
- CONTROL, BLOG, and SNS are three host-routed views of the same authenticated
  control-center app, not three independent deployments. Their shared navigation and
  operating copy distinguishes dispatch, acknowledgement-pending, queued work,
  verified account permission, and a public receipt. BLOG must not imply that every
  daily platform scheduler has cut over to n8n. These console changes were deployed
  after the guarded VPS deploy gate cleared; details are in the activity ledger.
