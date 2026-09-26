# 런던프로젝트GPT — Final Architecture

## 1. Design goal
The architecture must remain simple, stable, cheap, restartable, and understandable by the next AI without chat history.

## 2. Layers

### A. GitHub — durable source of truth
Responsibilities:
- code
- configuration
- n8n workflow JSON
- deployment workflow
- architecture documentation
- rollback history
- AI-project handoff records

GitHub is **not** the default 24/7 scheduler and **not** the video renderer.

### B. Hostinger VPS — single always-on runtime
Responsibilities:
- Docker
- n8n Community Edition
- existing Korea365 Python/systemd workers
- YouTube render/upload workers
- publication evidence and queue files
- Control Korea365 backend

VPS root: `/opt/korea365`

### C. n8n Community — central orchestrator
Responsibilities:
- schedule
- dispatch
- retries
- failure isolation
- deduplication
- HOLD/dead-letter
- execution receipts
- local-agent handoff
- bounded polling only where needed

n8n does **not** write long content or render long video itself.
It calls existing workers.

### D. localhost allowlist gateway
Purpose:
- n8n can trigger only approved existing systemd services.
- no arbitrary shell execution.
- token authenticated.
- bound to localhost.

Current service:
- `korea365-n8n-gateway.service`
- health: `127.0.0.1:8766/health`

### E. Control Korea365
Responsibilities:
- dashboard
- status
- operator actions
- publication evidence
- four CEO metrics
- link to actual result

It must not become a second orchestration engine.

### F. LondonLocalAgent
Purpose:
- Naver Blog 3
- Tistory 5

Reason:
These destinations require local authenticated browser sessions.

Rules:
- PC only needs to be available during browser publication windows.
- login/captcha/human verification => HOLD.
- never brute-force authentication.
- do not embed credentials/cookies in EXE or GitHub.
- final success requires public URL.

### G. Aside / Chrome
Used only as browser session surface.
Not the system of record and not the scheduler.

## 3. Final data flow

```
GitHub
  ↓ deploy/version
VPS
  ├─ n8n
  │   ├─ WP25_MASTER → existing WP worker
  │   ├─ BLOGGER33_MASTER → existing Blogger worker
  │   ├─ NEWS2_MASTER → newsroom worker
  │   ├─ YOUTUBE_*_MASTER → VPS video workers
  │   ├─ SNS_MASTER → approved platform publisher
  │   ├─ METRICS_MASTER → metric collectors
  │   └─ NAVER3/TISTORY5_MASTER → local queue
  │                                  ↓
  │                           LondonLocalAgent
  │                                  ↓
  │                           Aside/Chrome session
  └─ Control Korea365 ← receipts/status/metrics
```

## 4. Cost rule
- n8n Community: free software.
- PyInstaller/local Python: free software.
- GitHub: existing account.
- VPS: existing infrastructure; no additional runtime subscription.
- New paid API/SaaS requires explicit owner approval.
- Make.com is not in the production architecture.

## 5. Anti-patterns prohibited
- one workflow per site/channel
- duplicated GitHub cron + systemd timer + n8n schedule for same job
- Control Korea365 acting as full scheduler
- GitHub video rendering
- infinite retries
- blind browser automation after CAPTCHA
- storing passwords or cookies in repository
- counting workflow success as publication success
