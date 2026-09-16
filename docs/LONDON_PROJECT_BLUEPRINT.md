# 런던프로젝트 (London Project) — Korea365 AI Orchestration Blueprint

Status: CANONICAL
Project name: 런던프로젝트 (London Project)
Owner / final business decision maker: Chairman
Primary PM: CODEX / OpenAI
Plan B Acting PM: Claude / Anthropic
Plan C continuity assistant: Gemini
Canonical repository: huh0303-cmyk/-WP-QWEN-autobot
Canonical Git path: docs/LONDON_PROJECT_BLUEPRINT.md
Canonical VPS path: /opt/korea365/docs/LONDON_PROJECT_BLUEPRINT.md
Machine-readable policy: config/london_project_blueprint.json
Content cadence policy: config/london_content_schedule.json
Activity policy: config/london_activity_policy.json
Content runbook: docs/LONDON_PROJECT_CONTENT_PIPELINES.md
Activity runbook: docs/LONDON_PROJECT_ACTIVITY_LEDGER.md

---

## 1. Mission

런던프로젝트 is the operating architecture for the Korea365 portfolio. It keeps content, publishing, verification, reporting, failover and historical traceability running even when one AI provider, workflow or execution worker is unavailable.

No AI statement, workflow exit code, generated file or UI “done” message is proof of completion. Only deterministic external evidence may create VERIFIED_COMPLETE.

Every task, including failed, blocked, retried, cancelled and handed-off work, must remain traceable in the London Project activity ledger.

---

## 2. Control hierarchy

Chairman
  -> Control Korea365
  -> CODEX PM
  -> Orchestrator
     -> OpenAI workers
     -> Claude workers
     -> Gemini workers
     -> VPS workers
     -> GitHub Actions
  -> Publishing platforms
  -> Deterministic Audit Engine
  -> Claude independent audit summary
  -> Gemini secondary cross-check
  -> Control Korea365 verified report

The Chairman remains the final business decision maker. The PM may plan, decompose, assign, implement, test and request verification, but may not self-certify publication.

---

## 3. Agent roles

### CODEX — Primary Project Manager
- translates Chairman instructions into executable tasks
- creates/maintains task_id lineage
- controls priority, cadence, randomized KST scheduling and collision avoidance
- assigns Claude/Gemini/VPS/GitHub workers through Orchestrator
- preserves durable handoff state
- orders rework after failed audits
- reports verified state to Control Korea365
- cannot create VERIFIED_COMPLETE

### Claude — Independent Audit Lead + Plan B Acting PM
- normally performs independent QA and systems audit
- checks content quality, target correctness, source/evidence, schedule compliance, duplicate risk and activity-ledger continuity
- for 10-Language Survival, checks lesson numbering, localization quality, structure, duplicate risk and private-upload evidence
- if CODEX/OpenAI is unavailable due to quota, rate limit, timeout, outage, authentication failure or expired PM lease, becomes Acting PM and continues the same plan from the durable handoff packet
- cannot create VERIFIED_COMPLETE

### Gemini — Production Engine + Plan C Continuity
- Blogger/Blogspot independent content production
- low-cost bulk/structured production
- 10-Language Survival script/localization production
- multimodal/image prompt assistance and secondary cross-check
- if both CODEX and Claude are unavailable, continues only pre-approved operational work from durable state
- may not redesign business strategy, activate new paid services or create VERIFIED_COMPLETE

### VPS — Persistent execution plane
- 24/7 queue and scheduler
- randomized KST execution
- rendering, TTS, subtitles and thumbnails
- YouTube private upload workers
- RSS/data collection
- durable SQLite state and append-only JSONL activity mirror
- audit probes and long-running work

### GitHub — source control + deployment authority
- canonical code and policy
- version history and rollback
- CI/tests and deployment workflows
- reviewed `main` is release authority

### Deterministic Audit Engine
- sole authority for VERIFIED_COMPLETE
- web: exact target URL, host, HTTP, publication identity
- YouTube: video_id, exact channel_id, privacyStatus and API evidence
- all audit evidence must be tied to task_id and timestamp

---

## 4. Mandatory activity ledger

Every request and scheduled action receives a task_id before execution.

Required history includes:
- request and acceptance criteria
- platform/target
- assigned Agent and assignment changes
- every provider/worker attempt
- success/failure/error/retry
- Plan A/B/C/SAFE HOLD transitions
- external evidence
- human review/approval
- deterministic audit result
- final state

Canonical policy: `config/london_activity_policy.json`.
Canonical implementation: `control_center/london_activity.py`.

VPS storage:
- SQLite: `/opt/korea365/data/control-operations.sqlite3`
- JSONL: `/opt/korea365/data/london_project_activity.jsonl`

Failed work is never deleted or silently replaced by a new unlinked task.

---

## 5. Publishing cadence and randomized timing

Canonical machine policy: `config/london_content_schedule.json`.

All planned schedules use KST (Asia/Seoul).

Timing rules:
- exact clock-hour publication is forbidden for planned content
- actual time uses a default ±60-minute random window around the base schedule
- regular minute patterns such as 00/05/10/15/20/25/30/35/40/45/50/55 are avoided
- same-platform items normally keep at least 30 minutes separation
- channels/sites are distributed across distinct minutes
- repeated day/time patterns are avoided
- RSS breaking news is event-driven and exempt from artificial waiting when urgency requires publication, while still respecting duplicate and source checks

Cadence:
- General WordPress: one post per enabled general site per KST day
- Newsrooms: each newsroom targets 3–10 verified RSS/breaking-news stories per KST day, maximum 10; never invent filler when verified source leads are insufficient
- Blogger: current review-gated daily private-draft contract remains in force unless explicitly changed
- Tistory: current runtime contract remains in force unless explicitly changed
- YouTube Playlist 5: one private production per channel every 2–3 days
- YouTube Knowledge 5: one private production per channel every 2–3 days
- 10-Language Survival: one private lesson per language every 2–3 days
- Social cadence follows `config/london_content_schedule.json`; Threads mirrors Instagram topic/direction

---

## 6. Image policy

Copyright-safe imagery is the default first choice.

Order:
1. Pexels relevant free image
2. Pixabay relevant free image
3. approved SDXL Lightning fallback
4. approved FLUX Schnell fallback
5. text-only/no-image when suitable imagery is unavailable

Newsrooms must not copy unlicensed news-agency or publisher photos. Source/rights suitability and relevance are required before publication.

---

## 7. 10-Language Survival 50-lesson program

Languages:
Korean/TOPIK, English, Japanese, Chinese, Vietnamese, Spanish, French, German, Italian, Portuguese.

Target:
- 50 lessons per language
- 500 lessons total
- canonical progress through Lesson 2
- next production begins at Lesson 3
- one new private lesson per language every 2–3 days
- language slots are staggered to avoid simultaneous repetitive publishing

Workflow:
CODEX task bundle -> Orchestrator -> Gemini production/localization -> Claude independent QA -> VPS render/upload -> YouTube private -> deterministic VERIFIED_PRIVATE -> REVIEW_REQUIRED -> Chairman approval -> public transition -> deterministic public verification -> VERIFIED_COMPLETE.

No Agent may make a review-gated video public before Chairman approval.

---

## 8. YouTube Playlist and Knowledge programs

Playlist 5 channels and Knowledge 5 channels each use the existing 2–3 day interval model.

Rules:
- one private production per channel every 2–3 days
- channel times should not collide
- consecutive run times for a channel should differ
- private first
- deterministic video/channel/privacy verification
- Chairman review before public release
- public API re-verification after release

---

## 9. Failover policy

### Plan A — CODEX
Normal path:
Control Korea365 -> CODEX PM -> Orchestrator -> workers -> Audit Engine -> report.

### Plan B — Claude Acting PM
Triggers include OpenAI/API quota exhaustion, HTTP 429/rate limit, timeout/outage, authentication failure, expired PM lease or repeated provider failure.
Orchestrator records FAILOVER and passes open tasks, schedules, decisions, criteria, errors, audit failures and ledger cursor to Claude.
Claude continues the same plan instead of restarting strategy.

### Plan C — Gemini continuity
If CODEX and Claude are unavailable, Gemini continues only pre-approved operational tasks, preserves cadence and durable state, and routes results to audit.

### SAFE HOLD
If all three AI providers are unavailable:
- VPS preserves queues, state and activity history
- new content generation stops
- unapproved public publication stops
- only already-generated, already-verified and already-approved scheduled actions may proceed when policy explicitly allows them
- YouTube is never made public without the required Chairman approval
- recovery resumes from the latest durable handoff packet

---

## 10. Completion truth model

States:
REQUESTED, PLANNED, ASSIGNED, RUNNING, READY_FOR_AUDIT, AUDITING, VERIFIED_PRIVATE, REVIEW_REQUIRED, VERIFIED_COMPLETE, REWORK_REQUIRED, FAILED, BLOCKED, NEEDS_ATTENTION, CANCELLED.

Rules:
1. No AI provider may directly create VERIFIED_COMPLETE.
2. GitHub Actions success alone is not publication evidence.
3. Generated files or queue state alone are not publication evidence.
4. VERIFIED_COMPLETE requires external evidence tied to the exact task and target.
5. Evidence is stored with timestamp and target identity.
6. No task may be silently dropped.

---

## 11. Reporting to Control Korea365

Executive reporting must show:
- VERIFIED_COMPLETE
- VERIFIED_PRIVATE / REVIEW_REQUIRED
- RUNNING
- REWORK_REQUIRED
- BLOCKED
- FAILED
- NEEDS_ATTENTION

Each item should include task_id, platform, site/channel, title/task, URL/review URL where available, timestamp, evidence source, active PM/provider, schedule slot, retry count and failure/next-action information.

READY_FOR_AUDIT is never counted as complete.

---

## 12. Canonical runtime locations

GitHub:
- blueprint: `docs/LONDON_PROJECT_BLUEPRINT.md`
- machine policy: `config/london_project_blueprint.json`
- content pipeline: `docs/LONDON_PROJECT_CONTENT_PIPELINES.md`
- content schedule: `config/london_content_schedule.json`
- activity policy: `config/london_activity_policy.json`
- activity runbook: `docs/LONDON_PROJECT_ACTIVITY_LEDGER.md`
- CODEX instructions: `CODEX.md`
- Claude instructions: `CLAUDE.md`
- Gemini instructions: `GEMINI.md`
- activity implementation: `control_center/london_activity.py`

VPS:
- root: `/opt/korea365`
- blueprint: `/opt/korea365/docs/LONDON_PROJECT_BLUEPRINT.md`
- project policy: `/opt/korea365/config/london_project_blueprint.json`
- content schedule: `/opt/korea365/config/london_content_schedule.json`
- activity DB: `/opt/korea365/data/control-operations.sqlite3`
- activity JSONL: `/opt/korea365/data/london_project_activity.jsonl`
- blueprint receipt: `/opt/korea365/data/london_project_blueprint_version.json`
- audit report: `/opt/korea365/data/london_project_audit_report.json`

---

## 13. Blueprint update protocol

Any material change affecting Agent roles, failover order, platform scope, completion rules, audit evidence, runtime locations, cost/safety policy, publishing cadence, approval flow or logging must update this blueprint and the applicable machine-readable config in the same change set.

VPS deployment is not verified until deployed revision/checksum and service health evidence are available.

---

## 14. Change log

- 2026-09-16: 런던프로젝트 formalized with CODEX primary PM, Claude Plan B, Gemini Plan C and deterministic audit as sole VERIFIED_COMPLETE authority.
- 2026-09-16: Added KST randomized timing and private-first human review workflow.
- 2026-09-16: Set General WordPress to one per site/day; Playlist, Knowledge and 10-Language Survival to one private production every 2–3 days per channel/language; newsrooms to verified RSS/breaking-news target 3–10/day with max 10.
- 2026-09-16: Added mandatory London Project activity ledger so success, failure, retries, evidence and failover history remain permanently traceable.
