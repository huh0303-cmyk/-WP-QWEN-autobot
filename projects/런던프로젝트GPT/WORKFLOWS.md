# 런던프로젝트GPT — Workflow Map (GitHub-only)

## 1. WordPress
- GitHub Actions owns schedules and execution.
- Each site uses its own credential mapping and a verified public URL receipt.
- A retry first reconciles the last attempt against the destination; never blindly duplicate a post.

## 2. Blogger / Blogspot
- GitHub Actions owns API-based execution and schedule.
- Preserve per-blog identity, publication idempotency, and public URL receipts.
- Do not rely on a server-local timer or file queue.

## 3. YouTube playlist and knowledge channels
- Current execution path: .github/workflows/youtube-github-worker.yml -> scripts/youtube_github_worker.py.
- One selected channel per manual run, GitHub-hosted runner only.
- Cost hold is fail-closed unless YOUTUBE_COST_HOLD is explicitly false in the youtube-channels environment.
- Channel OAuth identity must match the locked channel ID.
- Keep the 10-channel automatic cadence disabled until scheduler migration, CI, read-only preflight and authorized canary are verified.
- Do not use the retired VPS queue or n8n workflow JSON.

## 4. Naver and Tistory
- Browser-dependent flows remain on the user's PC with the authenticated local browser profile.
- Do not claim these are GitHub-migrated without supported non-interactive auth.
- Keep tasks HOLD when the user session or human challenge is required.

## 5. Social APIs
- Use direct GitHub Actions workflows only where supported write credentials and exact destination IDs exist.
- Keep credentials in GitHub Actions secrets; never commit token files or cookies.

## 6. Global invariants
- No VPS, SSH, systemd timers, server-local queue or server-hosted n8n.
- Concurrency groups and durable destination receipts guard retries.
- Existing posts/videos are preserved; infrastructure migration does not change privacy.
- Missing evidence means HOLD, not success.
