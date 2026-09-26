# LondonProjectGPT Local App

This folder contains the actual no-new-cost Windows operator/local-browser app source.

## Purpose
The app is intentionally thin.
It does not replace VPS or n8n.

Functions:
- open Control Korea365
- check local repo / Python / Aside
- start Aside
- launch Naver login
- run one Naver ready job
- launch Tistory login
- inspect Tistory local queue
- run one Tistory ready job

## Safety
- no passwords, OAuth tokens or cookies are compiled into the EXE
- local .env is read only at runtime and values are never shown
- one-job execution is the default
- CAPTCHA/login challenge must be handled by the user; no bypass logic
- cloud scheduling remains on VPS/n8n

## Build
Run PowerShell:

```powershell
cd projects\런던프로젝트GPT\app
.\build_exe.ps1
```

Output:
`dist\LondonProjectGPT.exe`

PyInstaller is free/open-source. No new SaaS is required.

## Repository discovery
The app checks:
1. `LONDON_PROJECT_ROOT`
2. `~/Documents/LondonProject`
3. `~/Documents/-WP-QWEN-autobot`
4. a small OneDrive search for `-WP-QWEN-autobot`

Recommended:
set `LONDON_PROJECT_ROOT` explicitly after the final local repo location is fixed.

## Important
The EXE is a local browser agent, not the full London Project.
The brain remains:
GitHub + VPS + n8n + existing workers.
