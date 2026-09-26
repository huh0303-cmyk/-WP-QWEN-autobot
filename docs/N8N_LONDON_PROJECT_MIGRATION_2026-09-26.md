# London Project — n8n-first migration plan (2026-09-26)

## North Star
- k-health365.com is the confirmed AdSense-approved reference property.
- Primary web objective: improve AdSense approval readiness for the remaining WordPress 24 + Blogspot 33 properties.
- Publishing volume is a means, not the KPI. Quality, indexability, policy readiness, reliability and measurable traffic are the KPI.

## Cost policy
- Use the existing Hostinger VPS.
- n8n Community Edition is self-hosted on the existing VPS; do not purchase n8n Cloud or Make.
- No new paid SaaS/subscription without explicit user approval.
- Existing AI/API charges remain separate and must obey existing budget/kill-switch rules.

## Roles
- GitHub: source of truth, version history, configuration and rollback.
- Hostinger VPS: 24/7 runtime.
- n8n: orchestration, scheduling, retries, isolation, observability.
- Existing Python/systemd workers: keep working components; n8n calls them rather than rewriting everything.
- Control Korea365: executive status/approval dashboard.

## Reliability rule
A failure in one site/channel must not stop other sites/channels.
- per-site queue
- bounded retry with backoff
- dead-letter/hold state after repeated failure
- idempotency key / duplicate prevention
- execution receipt and error reason
- image failure may continue without image when the site policy allows it
- never report success without publication/upload receipt

## Phase 0 — no destructive changes
1. Snapshot current VPS/repository state.
2. Inventory active GitHub Actions, systemd services/timers and workers.
3. Do not delete/disable existing production paths until replacement passes end-to-end tests.

## Phase 1 — n8n foundation
- Deploy n8n Community in an isolated Docker stack on the existing VPS.
- Persistent volume + database backup.
- Bind locally first; expose only through authenticated HTTPS reverse proxy.
- Health check and restart policy.
- Resource limits so YouTube rendering cannot starve orchestration.

## Phase 2 — web publishing pilot
Run representative end-to-end tests:
1. WordPress: k-health365.com as reference/validation property; use draft/private test unless explicitly approved otherwise.
2. Blogger: one connected Blogspot property, draft test.
Validate: topic -> generation -> quality checks -> optional image -> duplicate check -> draft -> receipt -> control-center log.

Scale only after pilot passes.

## Phase 3 — AdSense web fleet
- WordPress fleet: 24 remaining properties.
- Blogspot fleet: 33 properties.
- Site-level state: APPROVED / READY / FIX / HOLD.
- Site-level readiness checks: focused topic, required pages, navigation, empty/duplicate taxonomy, content quality, indexability, broken URLs, internal links, mobile access and policy-risk flags.
- WP and Blogger must use independently written content; no verbatim cross-posting.

## Phase 4 — Tistory 5 + Naver Blog 3
- n8n prepares/queues content and records receipts; it does not assume browser login is permanently valid.
- Tistory: use the persistent local browser runner only after one account-specific canary verifies the current login/session and editor path.
- Naver: use separate persistent profiles per account/blog. Start with one canary account and scale only after a verified public receipt.
- CAPTCHA, human verification, login challenge, or platform restriction => HOLD and human handoff. Never loop or brute-force.
- Login-present is not success; only a verified destination URL/receipt counts.

## Phase 5 — YouTube
- Keep the VPS video worker as the render/upload owner.
- n8n orchestrates queueing/status/retry only.
- Video/thumbnail generation remains behind the existing cost safety gates; no unapproved paid generation.
- Private upload test before any public automation.

## Migration gate
Only after n8n pilot evidence exists:
- disable duplicate schedulers one at a time,
- retain rollback,
- record changed files/services, test receipt, API/cost impact and commit SHA.

## Make.com decision
Do not use Make.com in the production London Project. Its free tier is useful for small experiments, but a multi-site, multi-step 24/7 fleet is better kept on the already-paid VPS with self-hosted n8n to avoid credit limits and an additional SaaS dependency.


## Reference workflow adopted from YouTube QRJNEW08l5s
Reviewed on 2026-09-26 from the video's Korean subtitles.

Useful pattern to adopt:
- Cron/scheduled trigger.
- RSS/news-source ingestion.
- Select a small number of recent relevant items.
- LLM transforms source material into an original platform-specific article.
- Publish to Blogger/WordPress.
- Reuse the approved article/topic as the input for a short-form script.
- Generate/render short-form video asynchronously.
- Poll job status with bounded waits/retries.
- Upload completed video to YouTube and record the receipt.

London Project modifications:
- Apply to WordPress 25 total (k-health365.com is the AdSense-approved reference + 24 approval targets) and Blogspot 33.
- No verbatim WP/Blogger duplication.
- AdSense readiness and useful original content outrank raw publishing volume.
- Do NOT use the video's paid avatar/video API path.
- Paid image generation is OFF. Prefer no image, existing rights-cleared assets, or free/local generation only.
- Short-form rendering should use the existing VPS worker + FFmpeg/template/captions and rights-cleared/free assets; n8n orchestrates rather than renders.
- YouTube upload defaults to private/test until the channel mapping and quality checks pass.
- Per-site/per-channel isolation: one failed property cannot block the rest.
- No unbounded polling loops; retries have caps and dead-letter/HOLD states.
- No new paid API/SaaS without explicit user approval.


## 2026-09-26 cleanup checkpoint
Removed obsolete active workflows that could conflict with the current baseline:
- `.github/workflows/_one-off-mbb-set-public-19.yml`
- `.github/workflows/one-off-bump-youtube-calendar-slots.yml`
- `.github/workflows/sync-24-sites-gsc-index-visibility.yml`

Current authoritative web-fleet baseline:
- WordPress 25 ordinary sites
- Newsrooms 2 separate
- Blogspot 33
- Tistory 5
- Naver Blog 3
