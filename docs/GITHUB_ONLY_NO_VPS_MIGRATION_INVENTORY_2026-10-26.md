# GitHub-only migration inventory — 2026-10-26

This inventory was produced from searches against the default branch of `huh0303-cmyk/-WP-QWEN-autobot`. It is a migration worklist, not proof that any listed workflow is currently running.

## Rule
No production path may use a VPS, SSH, systemd timers, a server-local queue, `/opt/korea365`, or `/etc/korea365`. Do not simply delete a worker that still owns production behavior: first replace and test it on GitHub Actions. Do not delete posts/videos or alter privacy during this infrastructure work.

## SSH-based workflows found (21)
Each file must be replaced by a GitHub-native workflow or retired once confirmed unnecessary:

- `.github/workflows/vps-inventory.yml` — retire (server inventory is obsolete).
- `.github/workflows/london-n8n-stale-batch.yml` — migrate reviewed publication batch to Actions-native execution; verify exact destinations and receipts.
- `.github/workflows/london-ollama-bootstrap.yml` — retire server-local Ollama bootstrap; choose only an available GitHub-hosted free fallback.
- `.github/workflows/emergency-vps-inventory.yml` — retire (server inventory is obsolete).
- `.github/workflows/london-gpt-proof-wp-vps.yml` — replace with Actions-native WordPress read-only proof or retire.
- `.github/workflows/n8n-vps-preflight.yml` — retire server preflight; replace checks with repository/workflow preflight.
- `.github/workflows/youtube-publish-existing-now.yml` — migrate to direct GitHub-hosted YouTube API execution with channel-ID preflight and verified receipt.
- `.github/workflows/diagnose-control-center-routing.yml` — replace with GitHub-native diagnostics or retire.
- `.github/workflows/youtube-vps-full-audit.yml` — replace with read-only GitHub-hosted audit and artifact output.
- `.github/workflows/youtube-vps-service-repair.yml` — retire systemd repair; replace with GitHub workflow/code health checks.
- `.github/workflows/deploy-london-n8n.yml` — retire VPS/n8n deployment; no production dependency on server-hosted n8n.
- `.github/workflows/youtube-vps-resume-stalled-job.yml` — migrate to durable GitHub-native job state and bounded retry.
- `.github/workflows/london-provider-presence-probe.yml` — replace with GitHub-hosted provider availability preflight or retire.
- `.github/workflows/youtube-vps-runtime-repair.yml` — retire server runtime repair; replace with CI checks.
- `.github/workflows/wp-vps-floor-status.yml` — replace with GitHub Actions run/receipt status.
- `.github/workflows/london-n8n-four-agent-canary.yml` — migrate the four-agent canary to GitHub-hosted execution and artifacts.
- `.github/workflows/youtube-vps-enqueue-today.yml` — replace the remote queue enqueue with GitHub-native dispatch and durable state.
- `.github/workflows/one-off-korea365-subdomain-tls.yml` — retire or replace with supported DNS/hosting provider API; do not SSH to a server.
- `.github/workflows/provision-vps-wp-credentials.yml` — retire; credentials must be stored in GitHub Actions secrets, not provisioned to a server.
- `.github/workflows/youtube-vps-job-status.yml` — replace with GitHub workflow/job status and publication receipts.
- `.github/workflows/restore-youtube-ten-control.yml` — migrate to repository-backed config and Actions artifacts; no remote restore.

## Server-only YouTube dependencies found
- `scripts/run_youtube_vps.py` loads `/etc/korea365/youtube-runtime.json`.
- `scripts/youtube_vps_worker.py` claims jobs from a local queue, reads Google Sheets state, renders/uploads content, and updates local dashboard files.
- `automation_hub/youtube_vps_queue.py` stores queue state in local folders and uses `/etc/korea365/youtube-cost-hold` as a server-owned cost hold.
- Other scripts refer to `/opt/korea365` and server-only credentials/paths. Each reference needs classification: runtime dependency, data path to replace, or historical evidence.

## Platform migration order
1. YouTube queue/worker: preserve cost hold, duplicate protection, channel identity checks, exact receipts, bounded retries, and durable state.
2. WordPress and Blogger: verify all schedules are Actions-native and remove misleading VPS fallback comments/keys.
3. Newsroom and other social platforms: replace SSH dispatch with direct Actions/API execution.
4. Naver/Tistory: only migrate if supported non-interactive authentication exists; otherwise explicitly HOLD instead of claiming success.
5. Control dashboard and metrics: consume GitHub workflow statuses and verified receipts.
6. Remove obsolete VPS scripts/docs/workflows/secrets references only after the replacement path passes tests and authorized canary runs.

## Completion criteria
- No active workflow calls SSH or expects VPS host/key secrets.
- No production code reads `/opt/korea365` or `/etc/korea365`.
- Schedules have one owner and concurrency/deduplication guards.
- Credentials remain in GitHub Actions secrets/environments.
- A destination-verified canary and receipt exist for each migrated platform.
- Historical evidence may mention the former VPS, but it must be clearly labeled as historical and must not be executable.
