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
Content pipeline runbook: docs/LONDON_PROJECT_CONTENT_PIPELINES.md

---

## 1. Mission

런던프로젝트 is the operating architecture for the Korea365 portfolio. It keeps content, publishing, verification, reporting and recovery running even when one AI provider, workflow or execution worker is unavailable.

The system must never treat an AI statement, a workflow exit code, or a UI message saying “done” as proof of completion. Only independently verifiable external evidence may create the state VERIFIED_COMPLETE.

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

The Chairman remains the final business decision maker. The PM may plan, decompose, assign, implement, test and request verification, but the PM may not self-certify publication.

---

## 3. Agent roles

### CODEX — Primary Project Manager

CODEX owns strategy translation into executable tickets, priority and sequencing, daily/weekly cadence control, randomized schedule planning, architecture within approved policy, task decomposition, assignment to Claude/Gemini/VPS/GitHub workers, implementation, acceptance criteria, remediation after failed audits and consolidated reporting.

CODEX must read `config/london_content_schedule.json` and may not self-certify VERIFIED_COMPLETE.

### Claude — Plan B Acting PM + Independent Audit Lead

Claude normally serves as independent reviewer/auditor. It checks content quality, schedule compliance, evidence, wrong targets, duplicates and false completion. For 10-Language Survival it independently QA-checks lesson numbering, meaning/localization, metadata and private-upload evidence.

If CODEX/OpenAI is unavailable because of quota, rate limit, timeout, provider failure, authentication failure or expired PM lease, Claude becomes Acting PM and inherits open task list, publishing schedule, latest decisions, acceptance criteria, recent errors, audit failures and unfinished assignments. Claude continues the same plan and must not silently restart or replace business strategy.

### Gemini — Plan C Continuity + Production Engine

Gemini normally serves as Blogger/Blogspot production model, low-cost bulk content helper, structured extraction worker, 10-Language Survival script/localization producer and secondary audit cross-check.

If both CODEX and Claude are unavailable, Gemini may provide continuity for pre-approved operational tasks and audit summarization. Gemini may not independently approve new paid services, change portfolio scope, override cadence, or self-certify completion.

### VPS — Persistent execution plane

The VPS owns schedulers, queues, randomized KST execution times, rendering, YouTube generation/private upload workers, RSS/data collection, durable orchestration state and audit probes. It is the continuity layer that remains active even when a chat/session is closed.

### GitHub — source control + workflow execution

GitHub owns canonical code, version history, workflows, auditable commits, rollback points and the London Project blueprint source of truth.

---

## 4. Publishing cadence and randomized timing

Canonical machine policy: `config/london_content_schedule.json`.
Canonical human-readable runbook: `docs/LONDON_PROJECT_CONTENT_PIPELINES.md`.

All planned schedules use KST (Asia/Seoul).

Rules:
- Planned publication at exact clock hours is forbidden.
- Default actual execution time is the calendar/base time plus a random offset within ±60 minutes.
- Regular minute patterns such as 00/05/10/15/20/25/30/35/40/45/50/55 should be avoided; irregular minutes such as 14, 16 or 27 are preferred.
- Same-platform items should normally be separated by at least 30 minutes.
- Multiple sites/channels must be spread across distinct minutes and repeated day/time patterns should be avoided.
- Event-driven news remains separate from normal WordPress cadence.

Current cadence:
- General WordPress: one post per enabled general site per day.
- News WordPress: RSS/event driven, separately managed.
- Blogspot: Special-A/A 3–4 per week; B 2–3 per week; no WordPress copy/paste.
- Tistory: 2–3 per week per active site.
- YouTube Playlist 5: 2–3 per week per channel, private-first review.
- YouTube Knowledge 5: 2–3 per week per channel, private-first review.
- 10-Language Survival: three private uploads per language per week.
- Social: cadence is defined in `config/london_content_schedule.json`; Threads mirrors Instagram topic/direction.

---

## 5. 10-Language Survival 50-lesson program

Languages: Korean/TOPIK, English, Japanese, Chinese, Vietnamese, Spanish, French, German, Italian, Portuguese.

Target:
- 50 lessons per language
- 500 lessons total
- current canonical progress through Lesson 2
- next production starts at Lesson 3
- three items per language per week

Workflow:
CODEX weekly lesson bundle -> Orchestrator assignment -> Gemini production/localization -> Claude independent QA -> VPS render/upload -> YouTube private -> deterministic VERIFIED_PRIVATE -> Chairman review -> explicit approval -> public transition -> deterministic public verification -> VERIFIED_COMPLETE.

All new Survival uploads must be private first. No Agent may make them public before Chairman approval.

---

## 6. Failover policy

### Plan A
Primary PM: CODEX/OpenAI.
Normal path: Control Korea365 -> CODEX PM -> Orchestrator -> workers -> Audit Engine -> report.

### Plan B
Triggers include OpenAI/API quota exhaustion, HTTP 429/rate limit, provider timeout/outage, authentication failure, expired PM lease or repeated provider failure.
Action: Claude becomes Acting PM and receives the current handoff packet with open tasks, schedules, decisions, criteria, errors and recent events.

### Plan C
If both CODEX and Claude are unavailable, Gemini becomes continuity assistant for pre-approved tasks and structured audit/reporting. Human approval remains required for business-scope changes, new paid services and irreversible operations.

### SAFE HOLD
If CODEX/OpenAI, Claude/Anthropic and Gemini are all unavailable, VPS preserves durable state and queues. New content generation and unapproved public publication stop. Only already-generated, already-verified and already-approved scheduled actions may proceed when policy explicitly allows them. YouTube may never be made public without the required Chairman approval. Recovery resumes from the last durable handoff packet.

---

## 7. Completion truth model

States:
- REQUESTED
- RUNNING
- READY_FOR_AUDIT
- VERIFIED_PRIVATE
- REVIEW_REQUIRED
- VERIFIED_COMPLETE
- REWORK_REQUIRED
- FAILED
- BLOCKED
- NEEDS_ATTENTION

Rules:
1. No AI provider may directly create VERIFIED_COMPLETE.
2. GitHub Actions success alone is not publication evidence.
3. A generated file alone is not upload evidence.
4. A queue status alone is not publication evidence.
5. VERIFIED_COMPLETE requires external evidence tied to the exact job/site/channel.
6. Evidence must be stored with timestamp and target identity.

---

## 8. Web publication verification

For WordPress, Blogger, Tistory and News, minimum evidence for public publication is exact target site identity, exact public URL, successful HTTP response, non-admin/non-preview URL, non-login/non-404 page, expected title or job marker when available, and verification timestamp.

GitHub workflow success without these checks remains READY_FOR_AUDIT or NEEDS_ATTENTION.

---

## 9. YouTube verification and review

For private uploads, verify valid 11-character video ID, authenticated channel ID equals target channel ID, privacyStatus=private, validated Studio review URL and a job-bound upload receipt. State is VERIFIED_PRIVATE, never public complete.

For review-gated channels, VERIFIED_PRIVATE becomes REVIEW_REQUIRED until Chairman approval.

For public uploads, verify video ID, exact target channel, privacyStatus=public, successful YouTube API retrieval and a verified public watch URL. Only then may the system report VERIFIED_COMPLETE.

---

## 10. Audit architecture

Layer 1 — Deterministic Audit Engine: code checks URLs, APIs, IDs, HTTP responses, platform status, timestamps, target identity and receipts. This layer alone owns VERIFIED_COMPLETE.

Layer 2 — Claude independent audit: reviews Layer 1 evidence for inconsistencies, missing evidence, duplicates, wrong target, partial completion, schedule violations and regression risk. Claude may summarize but cannot override missing evidence.

Layer 3 — Gemini cross-check: independently summarizes evidence and flags inconsistencies. It is a secondary check, not final authority.

---

## 11. Reporting to Control Korea365

Executive reports show VERIFIED COMPLETE, VERIFIED PRIVATE / REVIEW REQUIRED, RUNNING, FAILED, REWORK and NEEDS ATTENTION. Each item includes platform, site/channel, title/task, public/review URL, verified timestamp, evidence source, active PM/provider, schedule slot and failure reason or next action when available.

READY_FOR_AUDIT is never counted as complete.

---

## 12. Current platform scope

- General WordPress: 25
- News WordPress: 2
- Total WordPress family: 27
- Blogspot/Blogger: managed portfolio
- Tistory: 5
- YouTube Playlist: 5
- YouTube Knowledge: 5
- 10-Language Survival: 10 languages × 50 lessons
- Social: Instagram, Threads, TikTok, Facebook active registries

Exact enabled inventory is configuration-driven.

---

## 13. Canonical runtime locations

GitHub:
- repo: huh0303-cmyk/-WP-QWEN-autobot
- blueprint: docs/LONDON_PROJECT_BLUEPRINT.md
- machine policy: config/london_project_blueprint.json
- content pipeline: docs/LONDON_PROJECT_CONTENT_PIPELINES.md
- content schedule: config/london_content_schedule.json
- CODEX instructions: CODEX.md
- Claude instructions: CLAUDE.md
- Gemini instructions: GEMINI.md
- PM controller: control_center/london_orchestrator.py
- provider failover: control_center/orchestrator.py
- deterministic audit: control_center/audit_engine.py
- audit reporter: scripts/london_project_audit_report.py

VPS:
- application root: /opt/korea365
- blueprint: /opt/korea365/docs/LONDON_PROJECT_BLUEPRINT.md
- machine policy: /opt/korea365/config/london_project_blueprint.json
- content schedule: /opt/korea365/config/london_content_schedule.json
- operation DB: /opt/korea365/data/control-operations.sqlite3
- blueprint version receipt: /opt/korea365/data/london_project_blueprint_version.json
- audit report JSON: /opt/korea365/data/london_project_audit_report.json
- audit report Markdown: /opt/korea365/data/london_project_audit_report.md
- environment: /etc/korea365/control-center.env

---

## 14. Blueprint update protocol

This is a living operating blueprint. Any material change affecting agent roles, failover order, platform scope, completion rules, audit evidence, runtime locations, cost/safety policy, publishing policy or cadence must update this document and the applicable machine-readable config in the same change set.

Claude and Gemini must read the machine policy, content cadence policy and this blueprint before PM, audit or production work. VPS deployment is not considered verified until the deployed revision/checksum receipt is available.

---

## 15. Change log

- 2026-09-16: Project renamed and formalized as 런던프로젝트 (London Project). CODEX primary PM, Claude Plan B Acting PM + audit lead, Gemini Plan C continuity. Deterministic audit is sole authority for VERIFIED_COMPLETE. GitHub/VPS dual-storage policy established.
- 2026-09-16: Added canonical content cadence, KST ±60-minute randomized schedule, exact-hour avoidance, 10-Language Survival 50-lesson private-first workflow, Chairman review gate, CODEX/Claude/Gemini role split and SAFE HOLD when all AI providers are unavailable.
