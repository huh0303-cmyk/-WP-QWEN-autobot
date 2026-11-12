# n8n Seven-Platform Canary Plan

Status: PLAN ONLY — no production schedulers changed; no content published.

## Discovery
Existing repository docs describe a four-agent n8n pipeline and prior VPS installation. Current live n8n status is not verified. Do not install a competing instance or activate duplicate schedules before auditing.

## Pilot destinations
1. WordPress: Kworld365 (tentative; confirm site registry and REST credentials), draft only.
2. Blogger: select one authorized connected blog after OAuth validation, draft only.
3. YouTube: TODAY IN HISTORY, 14-minute English documentary, private upload only after verified channel mapping and OAuth.
4. TikTok: one authorized account; dry-run/private only where permitted; direct-post app approval required.
5. Instagram: @seoul_topik, one test reel, professional account/API permissions required.
6. Threads: @seoul_topik, one test post, separate authorization required.
7. Facebook: SIS-TOPIK Center page, one test post, page access token required.

## Common quality gates
- Topic/source validation, uniqueness and editorial review
- Text: site-specific language, length, structure, factual checks
- Images: URL/hash/perceptual deduplication, license check, descriptive ALT
- Video: original/right-cleared assets, voice/caption sync, audio loudness, aspect ratio, thumbnail
- Preflight credentials and platform scopes; no cross-account uploads
- Stable idempotency key; bounded retry; failure HOLD state
- Publish receipt: platform, account ID, remote content ID, URL, verification time
- All paid API calls behind budget guard; never silently spend

## Architecture
GitHub remains source of truth. Existing Python engines remain content producers. n8n orchestrates per-platform jobs, quality gates, and receipts. Windows PC self-hosted runner is optional for FFmpeg rendering; no VPS purchase is authorized.

## Implementation order
0. Audit live n8n/VPS/GitHub topology and current active schedules; snapshot before edits.
1. WordPress draft canary.
2. Blogger draft canary.
3. TODAY IN HISTORY private documentary canary.
4. Meta family (Instagram, Threads, Facebook) account-level canaries.
5. TikTok authorized publishing canary.
6. Control center receipts and failure-state integration.

## Promotion gate
Do not enable public publishing or disable legacy schedules until an authorized test produces a verified receipt and rollback is available. Report each platform as NOT STARTED, BLOCKED, TESTED, or VERIFIED; never imply success from workflow import alone.

## Additional platforms to inventory
Tistory, Naver Blog, and any other properties shown in the live control center; not included in this seven-platform pilot until inventory is reconciled.
