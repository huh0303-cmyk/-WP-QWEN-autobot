# 런던프로젝트GPT — GitHub-only Architecture

## 1. Binding operating rule
The owner has explicitly retired VPS hosting. GitHub is the sole orchestration and code source of truth. No production workflow may require SSH, a VPS host, systemd timers, a server-local queue, or files under `/opt/korea365` or `/etc/korea365`.

This document describes the target architecture. A component is not considered migrated merely because its code is stored in GitHub; its actual scheduled execution and verified output must run through GitHub Actions.

## 2. Target layers

### A. GitHub repository
Owns source code, workflow definitions, channel/site configuration, migration records, run manifests, and versioned publication receipts where safe.

### B. GitHub Actions
Owns schedules, manual dispatch, bounded retries, concurrency locks, and Linux-hosted execution. Every workflow must declare its required environment and time limits, avoid duplicate schedules, and fail closed when credentials or channel identity cannot be verified.

Hosted runners are ephemeral. State that must survive a run must be persisted explicitly using a carefully scoped repository commit, workflow artifact, or another owner-approved GitHub-native store. Never treat workspace files or caches as durable job queues.

### C. Credentials
Use repository or environment-scoped GitHub Actions secrets. Never commit secrets, OAuth JSON, browser cookies, passwords, or private key material. Verify the exact YouTube channel/account identity immediately before any write or publication.

### D. Publication evidence
A successful workflow run is not proof of publication. Record a receipt containing the destination ID, returned content ID, verified public URL or privacy state, timestamp, and sanitized failure reason. Never log secret values.

### E. Local-browser platforms
Naver/Tistory workflows that require an interactive logged-in browser cannot be declared GitHub-migrated without a supported GitHub-hosted authentication path. If a platform requires an unavailable local session or human challenge, mark it HOLD; do not silently rely on a PC agent or server.

## 3. Non-negotiable safety rules
- No VPS, SSH, systemd, n8n-on-server, or server-local queue as a production dependency.
- No deletion of existing posts or videos during infrastructure migration.
- No mass privacy changes during migration.
- No automatic public upload during migration testing; use dry-run or private canaries with exact-channel checks.
- No duplicate retry unless the previous attempt is reconciled against a durable receipt.
- Preserve the owner's free-only API/tool policy; never introduce paid APIs or services without approval.
- A migration is complete only after workflow tests and a real, authorized, destination-verified canary pass.

## 4. Migration order
1. Inventory every workflow, script, schedule, queue, secret name, and persistent-state dependency that references VPS/SSH/systemd or server-only paths.
2. Replace or retire SSH-only diagnostics and repair workflows that cannot be used after VPS retirement.
3. Port the YouTube queue/worker to GitHub-hosted execution, including cost-hold, channel registry, schedule selection, deduplication, durable state, upload receipts, and bounded retries.
4. Validate each channel family with read-only OAuth identity checks and private canaries before enabling public schedules.
5. Migrate WordPress, Blogger, news, social, Naver, and Tistory individually; preserve account isolation and verify destination receipts.
6. Update dashboard/metrics to consume GitHub workflow status and verified receipts.
7. Only after replacements pass, remove obsolete VPS scripts, deployment files, docs, and secrets references.

## 5. Current status
The repository audit on 2026-10-26 found legacy SSH-based workflows and server-only YouTube worker dependencies still present. Therefore, the repository is **not yet fully GitHub-only**. Do not report migration complete or delete the remaining worker code until replacements pass their checks.

The first known blockers include:
- 21 workflow files matched `appleboy/ssh-action` in repository search.
- YouTube enqueue still calls `VPS_HOST` and imports `automation_hub.youtube_vps_queue` on the remote host.
- `scripts/run_youtube_vps.py` reads `/etc/korea365/youtube-runtime.json`.
- `scripts/youtube_vps_worker.py` uses a server-local queue and Google Sheets configuration.
- The legacy architecture and deployment docs still describe VPS/systemd/n8n as production infrastructure.

Next: map each SSH workflow to a GitHub-native replacement or retire it, and port YouTube execution without losing duplicate protection, cost-hold, channel identity checks, or publication receipts.
