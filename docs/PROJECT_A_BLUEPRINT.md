# PROJECT A — Korea365 AI Orchestration Blueprint

Status: CANONICAL
Project name: Project A
Owner / final business decision maker: Chairman
Primary PM: CODEX / OpenAI
Plan B Acting PM: Claude / Anthropic
Plan C continuity assistant: Gemini
Canonical repository: huh0303-cmyk/-WP-QWEN-autobot
Canonical Git path: docs/PROJECT_A_BLUEPRINT.md
Canonical VPS path: /opt/korea365/docs/PROJECT_A_BLUEPRINT.md
Machine-readable policy: config/project_a_blueprint.json

---

## 1. Mission

Project A is the operating architecture for the Korea365 portfolio.
Its purpose is to keep content, publishing, verification, reporting and recovery running even when one AI provider, one workflow or one execution worker is unavailable.

The system must never treat an AI statement, a workflow exit code, or a UI message saying “done” as proof of completion.
Only independently verifiable external evidence may create the state VERIFIED_COMPLETE.

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
  -> Control Korea365 verified report

The Chairman remains the final business decision maker.
The PM may plan, decompose, assign, implement, test and request verification, but the PM may not self-certify publication.

---

## 3. Agent roles

### CODEX — Primary Project Manager

CODEX owns:
- strategy translation into executable tickets
- priority and sequencing
- architecture decisions within approved policy
- task decomposition
- assignment to Claude, Gemini, VPS and GitHub workers
- implementation and code changes
- acceptance criteria
- remediation after failed audits
- consolidated reporting

CODEX does not own the final VERIFIED_COMPLETE flag.

### Claude — Plan B Acting PM + Independent Audit Lead

Claude normally serves as independent reviewer/auditor.
If CODEX/OpenAI is unavailable because of quota, rate limit, timeout, provider failure or an expired PM lease, Claude automatically becomes Acting PM.

As Acting PM Claude inherits:
- open task list
- latest decisions
- acceptance criteria
- recent errors
- audit failures
- unfinished assignments

Claude continues the same plan; it must not silently restart or replace business strategy.
When CODEX returns, ownership may be handed back with the same state packet.

### Gemini — Plan C Continuity + Production Engine

Gemini normally serves as:
- Blogger/Blogspot production model
- low-cost bulk content helper
- secondary verification assistant
- structured extraction and summarization worker

If both CODEX and Claude are unavailable, Gemini may provide continuity for pre-approved operational tasks and audit summarization.
Gemini may not independently approve new paid services, change portfolio scope, or self-certify completion.

### VPS — Persistent execution plane

The VPS owns long-running and always-on work:
- schedulers
- queue workers
- rendering
- YouTube generation/upload workers
- RSS/data collection
- operation receipts
- SQLite orchestration state
- audit probes

The VPS is the continuity layer that must keep running even when a chat/session is closed.

### GitHub — source control + workflow execution

GitHub owns:
- canonical code
- version history
- workflows
- auditable commits
- rollback point
- Project A blueprint source of truth

---

## 4. Failover policy

### Plan A
Primary PM: CODEX/OpenAI

Normal path:
Control Korea365 -> CODEX PM -> Orchestrator -> workers -> Audit Engine -> report

### Plan B
Trigger examples:
- OpenAI quota exhausted
- HTTP 429/rate limit
- provider timeout
- provider outage
- PM lease expires
- repeated provider failure

Action:
Claude becomes Acting PM and receives the current handoff packet.
The handoff packet contains open tasks, decisions, criteria, errors and recent events.

### Plan C
Trigger examples:
- CODEX unavailable
- Claude unavailable or exhausted

Action:
Gemini becomes continuity assistant for pre-approved tasks and structured audit/reporting.
Human approval remains required for business-scope changes, new paid services and irreversible operations.

---

## 5. Completion truth model

The system uses these states:

- REQUESTED
- RUNNING
- READY_FOR_AUDIT
- VERIFIED_COMPLETE
- VERIFIED_PRIVATE
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

## 6. Web publication verification

For WordPress / Blogger / Tistory / News:

Minimum evidence for public publication:
- exact target site identity matches job
- exact public URL exists
- HTTP response is successful
- URL is not admin/preview/manage URL
- page is not a login/error/404 placeholder
- expected title or job marker is present when available
- verification timestamp is stored

GitHub workflow success without these checks must remain READY_FOR_AUDIT or NEEDS_ATTENTION.

---

## 7. YouTube verification

YouTube upload verification must use the YouTube API or validated upload receipt.

For private uploads:
- valid 11-character video ID
- authenticated channel ID equals configured target channel ID
- privacyStatus == private
- validated Studio review URL exists
- upload receipt is attached to the exact job

State: VERIFIED_PRIVATE, not VERIFIED_COMPLETE/public.

For public uploads:
- video ID exists
- target channel identity matches
- privacyStatus is public
- YouTube API can retrieve the video
- public watch URL is generated from the verified video ID

Only then may the system report public YouTube publication as VERIFIED_COMPLETE.

---

## 8. Audit architecture

### Layer 1 — Deterministic Audit Engine

Code, not an LLM, checks:
- URLs
- APIs
- IDs
- HTTP responses
- platform status
- timestamps
- target identity
- receipts

This layer owns VERIFIED_COMPLETE.

### Layer 2 — Claude independent audit

Claude reviews Layer 1 evidence and checks for:
- inconsistencies
- missing evidence
- duplicate publication
- wrong site/channel
- partial completion presented as full completion
- suspicious success claims
- regression risk

Claude produces a short executive audit summary but cannot override missing evidence.

### Layer 3 — Gemini cross-check

Gemini may independently summarize evidence and flag inconsistencies.
It is a secondary check, not the final authority.

---

## 9. Reporting to Control Korea365

Every executive report should show:

- VERIFIED COMPLETE
- VERIFIED PRIVATE / REVIEW REQUIRED
- RUNNING
- FAILED
- NEEDS ATTENTION

For each item include when available:
- platform
- site/channel
- title/task
- public or review URL
- verified timestamp
- evidence source
- active PM/provider
- failure reason or next action

The top summary must never count READY_FOR_AUDIT as completed.

---

## 10. Current platform scope

Web publishing scope:
- general WordPress: 25
- news WordPress: 2
- total WordPress family: 27
- Blogspot/Blogger: managed portfolio
- Tistory: 5

YouTube and social properties are operated through their dedicated registries and workers.
The exact enabled inventory is configuration-driven and may change without changing this architecture.

---

## 11. Canonical runtime locations

GitHub:
- repo: huh0303-cmyk/-WP-QWEN-autobot
- blueprint: docs/PROJECT_A_BLUEPRINT.md
- machine policy: config/project_a_blueprint.json
- PM controller: control_center/pm_orchestrator.py
- provider failover: control_center/orchestrator.py
- deterministic audit: control_center/audit_engine.py
- audit reporter: scripts/project_a_audit_report.py
- publication receipts: control_center/operations.py
- GitHub publication gateway: control_center/operation_gateway.py

VPS target:
- application: /opt/korea365
- blueprint: /opt/korea365/docs/PROJECT_A_BLUEPRINT.md
- machine policy: /opt/korea365/config/project_a_blueprint.json
- operation DB: /opt/korea365/data/control-operations.sqlite3
- audit report: /opt/korea365/data/project_a_audit_report.json
- environment: /etc/korea365/control.env

---

## 12. Blueprint update protocol

This document is a living operating blueprint.

Any material change to Project A must update this document in the same change set when it affects:
- agent roles
- failover order
- platform scope
- completion rules
- audit evidence
- execution locations
- cost/safety policy
- publishing policy

Every update must append a line to the Change Log below.
Claude and Gemini must be given the machine-readable policy and this blueprint before performing PM, audit or production tasks.

The blueprint is not considered deployed to the VPS until the sync script records the exact Git commit SHA and file checksums.

---

## 13. Change log

- 2026-09-16: Project A formally named. CODEX primary PM, Claude Plan B Acting PM + audit lead, Gemini Plan C continuity. Deterministic external-evidence audit made sole authority for VERIFIED_COMPLETE. GitHub/VPS dual-copy policy established.
