# London Project Architecture Lock — 2026-09-26

## Production architecture
- n8n Community Edition: central orchestrator.
- Make.com: not used in production.
- Hostinger VPS: keep; runs n8n, YouTube workers, render/upload tasks, reusable Python/systemd services.
- GitHub: source code, workflow JSON, configuration, version history, rollback and audit trail.
- Control Korea365: executive status and approval dashboard.

## Web fleet
- WordPress: 25 ordinary sites.
- Newsrooms: 2, separate rules.
- Blogspot: 33.
- Tistory: 5.
- Naver Blog: 3.

## n8n master workflows
Do not create one workflow per site or channel.
Use a small master set:
1. WP25_MASTER
2. BLOGGER33_MASTER
3. NEWS2_MASTER
4. TISTORY5_MASTER
5. NAVER3_MASTER
6. YOUTUBE_PLAYLIST5_MASTER
7. YOUTUBE_KNOWLEDGE5_MASTER
8. YOUTUBE_LANGUAGE_MASTER
9. SNS_MASTER
10. METRICS_MASTER

n8n schedules, dispatches, retries, isolates failures, manages HOLD/dead-letter states, prevents duplicates and records receipts.
Existing proven Python/systemd publishers remain reusable execution engines behind n8n.

## Aside / local browser
- Aside version 1.0.922.1 installed and launch-verified on the owner PC.
- Primary use: Naver Blog and Tistory browser-only publication.
- Owner reported Naver and Tistory logins completed on 2026-09-26.
- n8n prepares and queues jobs; local browser execution performs publication and must return a verified public URL/receipt.
- CAPTCHA, re-authentication or human verification => HOLD. No brute-force or infinite retry.
- PC does not need to stay on 24/7; it only needs to be available during browser-publication windows.

## YouTube
- VPS owns video generation/render/upload execution.
- n8n owns orchestration and status/retry only.
- Playlist, Knowledge and Language channel families are registry-driven masters, not per-channel workflows.

## Cleanup rule
- Delete obsolete one-off workflows, old count-based workflows and superseded schedulers once replacement evidence exists.
- Do not retain completed one-off jobs as active workflows.
- Never disable a working production path before its n8n replacement has an end-to-end receipt.
