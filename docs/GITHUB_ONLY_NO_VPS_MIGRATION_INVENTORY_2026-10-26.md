# GitHub-only migration inventory — 2026-10-26

Repository: `huh0303-cmyk/-WP-QWEN-autobot`  
Merged to main on 2026-10-26 by PR #230 (squash commit df7b8faa7332c98c2c20bab956fca73a4df5129b).

## Binding rule
No production path may depend on VPS, SSH, systemd timers, server-local queues, `/opt/korea365`, `/etc/korea365`, or server-hosted n8n. Do not delete existing videos/posts or change their privacy as part of this migration.

## Retired and merged to main
- 21 SSH-based workflows were removed from the migration branch, including VPS inventory/repair, SSH queue enqueue/status, n8n deployment/canary, runtime credential provisioning, and VPS WordPress status workflows.
- Removed VPS systemd service/timer assets and the VPS code deploy engine.
- Removed n8n Docker deployment configuration and the n8n systemd gateway.
- Removed server-only YouTube/Blogger/WordPress worker entry points and the VPS runtime installer/sealer.
- Replaced the control-center YouTube queue action with GitHub Actions dispatch.
- Added `automation_hub/youtube_github_runtime.py`, `scripts/youtube_github_worker.py`, and `.github/workflows/youtube-github-worker.yml`.
- Added focused regression tests and a workflow to check fail-closed cost hold, queue idempotence, and Python compilation.

## Current GitHub-only YouTube path
1. Operator dispatches `youtube-github-worker.yml` with one channel and explicit `confirm_publication=true`.
2. The workflow runs on `ubuntu-latest`; no SSH or server path is used.
3. The worker checks cost hold before queue creation or execution.
4. The durable calendar remains in Google Sheets; local queue/logs are per-run only.
5. The upload scripts must verify authenticated channel identity and write a receipt before the run is considered successful.
6. Cost hold remains blocked unless the `youtube-channels` environment variable `YOUTUBE_COST_HOLD` is explicitly set to `false`. No public upload was triggered by this migration work.

## Remaining blockers
- `automation_hub/youtube_vps_queue.py` was removed after the control-center and worker callers were migrated.
- Some legacy scripts/docs still contain VPS paths or old n8n instructions; they need targeted migration or a clear historical-only label.
- The new GitHub worker has not completed an authorized end-to-end canary, so it must not be described as production-verified.
- The hourly GitHub scheduler is installed in .github/workflows/youtube-github-scheduler.yml and processes at most one due calendar row per run. It is intentionally disabled unless YOUTUBE_AUTO_PUBLISH_ENABLED=true and YOUTUBE_COST_HOLD=false in the youtube-channels environment; no automatic public publishing was enabled by this migration.
- Naver/Tistory browser tasks must remain HOLD unless a supported GitHub-hosted non-interactive authentication path is available.

## Completion checklist
- [x] No active workflow uses SSH or VPS host/key secrets (static runtime scan passed).
- [x] No active production code reads `/opt/korea365` or `/etc/korea365` (static runtime scan passed).
- [x] Legacy queue module removed after active callers were migrated.
- [x] Focused pytest suite, Python compilation, Node syntax checks, and the static runtime scan pass. The broader operating-policy audit remains a separate check.
- [ ] Read-only OAuth checks match every selected channel's expected channel ID.
- [ ] Authorized canary returns a verified video ID, URL, channel ID, privacy state, and durable receipt.
- [ ] Other platform publishers have verified GitHub-native receipts or are explicitly HOLD.

**Status: VPS/n8n execution and deployment assets are retired on main. Production verification remains in progress: automatic YouTube cadence is disabled, no authorized end-to-end canary has passed, and Naver/Tistory remain PC-authenticated HOLD tasks.**
