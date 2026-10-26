# 런던프로젝트GPT — Control App Specification

## Role
The control app is an operator dashboard and dispatch client. GitHub Actions is the hosted execution plane and repository main is the code/config source of truth. The control app must not own a server-local publication queue.

## Core functions
- Show GitHub Actions run status and links.
- Show site/channel registry, expected destination IDs, and last verified publication receipts.
- Dispatch an explicit one-channel YouTube workflow only after the operator confirms.
- Display cost-hold state and block execution when the hold is active.
- Show per-platform HOLD reasons when credentials or interactive authentication are missing.
- Keep publication evidence separate from run status; never display success without a destination receipt.

## Safety
- Do not expose secrets in the UI or logs.
- Do not change existing video/post privacy as part of migration.
- Do not automatically retry an ambiguous upload.
- Do not route actions to VPS, SSH, systemd, or server-hosted n8n.
- Local Naver/Tistory browser tasks must be clearly labeled as PC-only and require an authenticated user session.

## Health indicators
- GitHub Actions workflow status and last successful run.
- Last destination-verified receipt and age.
- Cost hold active/released.
- OAuth identity preflight status.
- Duplicate guard and queue reconciliation status.
- Platform-specific HOLD/credential status.

## Completion definition
A workflow is complete only when the intended destination's exact content ID, public URL/privacy state, expected account/channel ID, and timestamp are verified and recorded.
