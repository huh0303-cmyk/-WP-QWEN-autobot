# 런던프로젝트GPT — App Specification

## App name
**LondonProjectGPT**

## App model
Do **not** package the entire cloud system into one Windows EXE.
That would make the project PC-dependent and less stable.

Use two app surfaces:

### 1. Control Korea365 — web operator app
Runs on VPS.
Functions:
- fleet status
- ranking
- four CEO metrics
- publication result links
- safe per-destination actions
- HOLD/failure visibility
- n8n/VPS health

### 2. LondonLocalAgent — small Windows app/EXE
Runs only on owner PC.
Purpose:
- Naver 3
- Tistory 5
- authenticated browser-only execution

Recommended implementation:
- Python
- Playwright/approved local browser bridge
- PyInstaller packaging
- Windows Task Scheduler or startup registration
- local SQLite queue cache
- no embedded secrets

## LondonLocalAgent states
- IDLE
- READY
- RUNNING
- PUBLISHED
- HOLD_LOGIN
- HOLD_CAPTCHA
- FAILED
- RECEIPT_SENT

## LocalAgent job contract
Required:
- task_id
- platform
- destination_id
- title
- body
- publish_mode
- created_at
- idempotency_key

Return:
- task_id
- state
- public_url or editor_url
- post_id if available
- error_class
- finished_at

## EXE policy
The EXE is only a thin local browser worker.
n8n/VPS remains the system brain.
This preserves:
- 24/7 operation without PC
- cheap recovery
- small Windows footprint
- low support burden
- no duplicated business logic
