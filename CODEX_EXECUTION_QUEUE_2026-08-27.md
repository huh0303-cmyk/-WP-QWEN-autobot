# CODEX EXECUTION QUEUE — 2026-08-27

Status: READY FOR WORK/CODEX
Authority: MASTER_MONETIZATION_STRATEGY_2026.md + PM_CURRENT_STATUS.md
Execution rule: complete and verify in order. Do not skip ahead because a later feature is more interesting.

## PRE-FLIGHT — Read verified PM findings first
Before Ticket 1, read:
- `docs/PM_PREWORK_AUDIT_2026-08-27.md`

Fix the verified blockers in this exact order before doing a broad refactor:
1. newsroom length-normalization conflict causing scheduled Koreanews365 failure;
2. stale hard-coded YouTube channel list in `situation_room_daily.py` vs canonical registry;
3. Blogger duplicate-suspect ownership between daily scheduler and Sheet queue;
4. verify ordinary WP direct-publish vs draft/private semantics;
5. clean dead/manual workflow conditionals only after behavior is understood.

Do not run the full production portfolio while fixing these.

## Ticket 1 — Repository normalization audit
Goal: make active automation topology understandable and safe before adding features.

Tasks:
- inventory every active .github/workflows/*.yml
- classify each workflow: ACTIVE / MANUAL-ONLY / LEGACY / DUPLICATE-SUSPECT / DISABLED
- map workflow -> entry script -> external API/provider -> output destination
- detect overlapping schedulers dispatching the same downstream workflow or content family
- detect retired-channel references
- detect stale OAuth fallback and unused environment-variable/secret references
- detect excessive retry/fallback chains
- detect silent-success / false-complete behavior
- do not delete ambiguous business-critical code; flag first

Required output:
- docs/AUTOMATION_TOPOLOGY.md
- docs/WORKFLOW_AUDIT_2026-08-27.md
- exact list of files changed
- tests + commit SHA

## Ticket 2 — Measurement / observability first
Goal: turn Google Sheet '올뉴종합상황실' into the executive control room.

Implement verifiable data only.

Web/SEO target metrics:
- site
- published count
- indexed count if technically obtainable with documented method
- non-indexed count / index rate where valid
- GSC impressions
- GSC clicks
- CTR
- average position
- visitor/user metric from the correct analytics source when connected
- collection error/status

Revenue target metrics:
- AdSense today / 7d / month when API connection exists
- YouTube revenue when connection exists
- affiliate/shopping fields designed for future attribution

YouTube target metrics:
- channel
- subscribers
- views
- watch time
- recent upload
- revenue if available
- growth delta

Social target metrics:
- official-API obtainable followers/views/engagement/posts/growth
- unsupported data must be marked CONNECTION_REQUIRED, never fabricated

Cost target metrics:
- OpenAI
- Gemini
- Replicate
- other actual API costs where retrievable

Executive layer:
- revenue
- AI/API/tool cost
- net revenue

Required output:
- data-source map documenting exactly which API supplies each metric
- Sheet tabs/ranges updated without destroying existing data
- one-site / one-channel sample verification before scaling
- commit SHA

Important: reuse and normalize the existing `daily-site-traffic.yml`, `situation-room-daily.yml`, and GSC audit paths instead of creating a competing second measurement stack.

## Ticket 3 — Content routing conformance
Goal: enforce frozen model/provider policy.

Must hold:
- WordPress long-form = GPT
- no silent Gemini fallback for WP long-form
- Blogger/Blogspot long-form = Gemini
- YouTube generated thumbnail = black-forest-labs/flux-schnell only
- approved non-YouTube Replicate pool only: flux-schnell / bytedance sdxl-lightning-4step / jyoung105 sdxl-turbo
- legacy image providers must not be reachable from active paths
- REPLICATE_API_TOKEN is the shared credential for approved Replicate images
- retries bounded
- duplicate-generation guard present

Required output:
- automated policy tests
- one representative dry/private test per engine
- commit SHA

## Ticket 4 — Publishing safety and deduplication
Goal: prevent spam-like cross-platform behavior and accidental duplicates.

Implement/verify:
- stable content_id/source_id across derivatives
- per-platform duplicate lock
- no identical copy/paste across WP/Blogger/Tistory/Naver/SNS
- platform-native title/hook/caption/CTA/hashtags
- natural randomized schedules
- no synchronized multi-account burst
- default draft/private/review where applicable
- Naver conservative/manual-review path

Required output:
- dedup design note
- tests proving duplicate block
- commit SHA

## Ticket 5 — Minimal E2E proof
Do NOT run the whole portfolio.

Test exactly one representative unit for each:
1. WordPress
2. Blogger
3. TOPIK content
4. SNS derivative set
5. YouTube

Validate:
source -> generation -> image/media -> quality -> duplicate gate -> draft/private/review -> log -> Google Sheet record

Stop and report on any unexpected paid-call multiplication.

## Ticket 6 — Only after Tickets 1–5 are stable
Promote Phase-2 opportunities selectively:
- TOPIK_QUIZ_PLATFORM_PHASE2.md MVP
- owned-audience/lead-magnet funnel
- affiliate attribution
- SCALE/WATCH/STOP ROI engine

Do not implement all Phase-2 items simultaneously.

## Cost guardrails
- no new paid SaaS/API without explicit approval
- no broad production test
- no unbounded retries
- no chained paid-provider fallbacks
- no image batch generation for testing
- every completion report includes cost impact

## Completion format
For every ticket report:
1. problem found
2. changes made
3. remaining risks
4. files changed
5. tests and result
6. data/Sheet verification when relevant
7. API/cost impact
8. commit SHA
9. next ticket readiness
