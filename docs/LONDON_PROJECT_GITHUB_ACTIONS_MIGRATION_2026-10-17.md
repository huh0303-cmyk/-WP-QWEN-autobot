# London Project execution migration: GitHub Actions only

Date: 2026-10-17
Owner directive: VPS is no longer used. GitHub is the execution and source-of-truth platform.

## Binding decision

- GitHub repository `huh0303-cmyk/-WP-QWEN-autobot` is the canonical source of code, schedules, queue manifests, logs/receipts, and migration status.
- GitHub Actions is the intended scheduler/runner. Do not depend on Hostinger VPS, SSH dispatch, systemd timers, `/opt/korea365`, or a VPS-hosted queue for new production execution.
- Store credentials only in GitHub Actions repository/environment secrets. Never commit tokens, OAuth JSON, cookies, or API keys.
- Scheduled workflows must do real work or explicitly fail; a `DRAFT_ONLY` planning artifact must not be reported as a publication.
- Do not delete existing videos/posts. No publication may be claimed without an API receipt proving the returned ID, expected channel/account ID, and resulting privacy/public URL.
- Preserve the owner's no-paid API/SaaS constraint and Gemini-free-only content-generation rule.

## Confirmed migration blockers from repository audit

1. `.github/workflows/content-random-scheduler.yml` runs three times daily but only creates `scheduler-plan.json` with `mode=DRAFT_ONLY`; it does not render, enqueue, upload, or verify content.
2. Existing workflow and documentation paths still invoke VPS services, SSH commands, `/opt/korea365`, or the VPS queue. These are not valid execution dependencies under the owner's new directive.
3. Playlist video generation depends on source media, FFmpeg/audio tools, and per-channel OAuth credentials. The runner must install/use free tools and fetch only assets available from repository-controlled sources or explicit authorized storage; it must not assume a VPS filesystem or silently reuse restricted source media.
4. YouTube OAuth secrets already have a documented GitHub Actions environment scope (`youtube-channels`) for many channels. Every job that needs them must declare that environment and validate the exact locked UC ID before upload.
5. GitHub Actions hosted runners are ephemeral. Any state needed between runs (dedupe ledger, schedule, queue, receipts) must be committed back safely or stored in an authorized GitHub artifact/cache/data store; workspace files alone do not persist.

## Migration phases

### Phase 1 — Inventory and stop misleading schedules

- Inventory all workflows that call VPS/SSH/systemd and all workflows that only create plans.
- Keep production publishing disabled for any workflow that cannot produce and verify a complete receipt.
- Mark legacy VPS workflows as migration-only; do not silently route new jobs to VPS.

### Phase 2 — GitHub-native queue and cadence

- Implement an idempotent GitHub-owned schedule manifest for the five playlist channels and five knowledge channels.
- Playlist cadence: 2–3 randomly distributed runs per channel per week, including CAFE_MOZART and Starbucks Vibes.
- Generate due work only after checking channel/date duplicates; concurrency groups prevent overlapping jobs.
- Persist per-run manifests/receipts in the repository under an appropriate data path or workflow artifacts.

### Phase 3 — GitHub-hosted production and upload

- Add channel-specific render steps using free/open-source tools (e.g. FFmpeg) on `ubuntu-latest` where compatible.
- Pull source media only from known, authorized repository/Drive sources; do not assume local PC files exist in the runner.
- Validate music rights/source metadata, actual rendered duration, title, thumbnail, and duplicate tracks before upload.
- Verify the OAuth identity with `channels.list(mine=true)` against the locked channel ID immediately before upload.
- Upload via YouTube API, then verify returned video ID, channel ID, title, duration, privacy state, and watch URL. Record evidence.
- Use environment-scoped secrets and never print secret values.

### Phase 4 — Migrate other publishers

- Audit WordPress, Blogspot, Naver, Tistory, and social publishing workflows individually. GitHub Actions cannot reuse a logged-in local browser session; each connector/API requires its own supported credentials and exact account verification.
- Do not mark any platform migrated until its real publication receipt has been verified.

### Phase 5 — Decommission old execution references

- Once GitHub-native jobs pass end-to-end tests, update runbooks/tests to remove VPS as production host and retire VPS dispatch workflows. Do not delete user content or secrets without explicit authorization.

## Current status

This commit records the owner's binding migration decision and the concrete blockers found in the current repository. It is not evidence that the full publisher has already been ported or that uploads are running from GitHub Actions. The next code change must replace the current plan-only playlist scheduler with a GitHub-native queue/runner and test it against CAFE_MOZART's exact channel ID `UC7jOhyMa-FIrzZuea97z1Pw` before enabling publication.