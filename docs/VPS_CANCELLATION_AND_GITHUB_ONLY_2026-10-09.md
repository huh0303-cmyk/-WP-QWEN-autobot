# VPS cancellation and GitHub-only transition — 2026-10-09

## Owner decision
The owner retired VPS hosting and requires London Project to use GitHub Actions as its only hosted execution plane. This decision is binding. The former VPS/n8n architecture is not an approved production path.

## Migration work merged to main on 2026-10-26 (PR #230)
- Removed all 21 previously inventoried SSH-based VPS workflows from this branch.
- Removed the VPS deployment engine and its systemd unit/timer files from `deploy/vps`.
- Removed n8n Docker deployment assets, the n8n gateway service, and VPS runtime installer/sealer scripts.
- Retired server-only YouTube/Blogger/WordPress worker entry points.
- Added `automation_hub/youtube_github_runtime.py` and `scripts/youtube_github_worker.py`.
- Added `.github/workflows/youtube-github-worker.yml` for one-channel GitHub-hosted execution, with explicit manual confirmation and a fail-closed cost hold.
- Routed control-center YouTube actions to GitHub Actions dispatch instead of creating a local/server queue.
- Updated architecture, topology, status, and migration documents to stop treating VPS/n8n as active infrastructure.

## Safety rules
1. Do not delete existing posts or videos.
2. Do not change privacy/publication state during infrastructure migration.
3. Never report an upload as successful without a destination-verified receipt.
4. Preserve channel identity checks, duplicate protection, cost hold, and bounded retries.
5. GitHub Actions is not a durable filesystem: only use explicit persisted state (Google Sheet calendar, workflow artifacts, or approved GitHub-native storage).
6. Do not enable public publishing until owner-approved cost review and read-only channel identity checks pass.

## Remaining verification — migration is not yet complete
- The legacy module `automation_hub/youtube_vps_queue.py` was removed after active consumers were moved to GitHub Actions dispatch/runtime.
- Historical documentation and activity ledgers still mention the former VPS for audit context. They are non-executable records, not current runbooks; active workflow/code/config directories pass the static no-VPS runtime scan.
- The GitHub-hosted worker has not yet completed an authorized end-to-end canary. Its cost hold is intentionally active by default.
- The hourly GitHub Actions scheduler is now present, but it remains disabled by default unless YOUTUBE_AUTO_PUBLISH_ENABLED=true and YOUTUBE_COST_HOLD=false in the youtube-channels environment. No automatic public publishing was enabled.
- Naver/Tistory browser-based tasks cannot be called GitHub-migrated unless a supported non-interactive auth path exists; otherwise they remain explicitly HOLD.

## Acceptance criteria
- No active production workflow uses SSH, VPS secrets, systemd, n8n-on-server, `/opt/korea365`, or `/etc/korea365`.
- The old queue/runtime files have no active consumers.
- GitHub-only worker tests pass.
- Read-only OAuth identity checks confirm the exact channel IDs.
- A manually authorized canary produces a verified video ID, destination URL, expected channel ID, privacy state, and durable receipt.
- Other platforms have equivalent destination-verified receipts or are explicitly marked HOLD.

**Status: VPS/n8n execution and deployment assets are retired on main. The static no-VPS runtime scan and focused CI passed. End-to-end publishing verification and the automatic YouTube cadence remain gated pending owner-approved canary and channel identity checks.**
