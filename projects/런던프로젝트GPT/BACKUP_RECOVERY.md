# 런던프로젝트GPT — GitHub-only Backup / Recovery Plan

## 1. Source of truth
- GitHub repository huh0303-cmyk/-WP-QWEN-autobot, protected main branch, reviewed migration branches, and immutable commit history.
- Workflow definitions, registries, scripts, tests, runbooks, and migration records live in GitHub.
- Google Sheets remains the durable YouTube calendar and platform control data store where the code expects it.
- GitHub Actions workspaces are ephemeral. Do not use workspace files or caches as a durable queue.

## 2. What to back up
- Versioned source, workflow, config and policy files.
- Sanitized workflow artifacts and publication receipts.
- Required non-secret runtime manifests and run history.
- Google Sheets data using an owner-approved export or API-based backup process.
- Local authenticated Naver/Tistory browser profiles remain on the user's PC and must not be copied to GitHub.

## 3. Secrets
- Store tokens only in GitHub Actions repository/environment secrets or the platform's approved credential store.
- Never commit OAuth JSON, refresh tokens, browser cookies, passwords, private keys, or unredacted logs.
- Keep secret names and setup instructions in docs, never secret values.

## 4. Recovery
1. Identify the last known-good Git commit and the failed workflow run.
2. Revert the code/config change through a reviewed GitHub commit; do not reset or force-push main.
3. Re-run read-only preflight checks.
4. Verify exact destination/account/channel identity before any write action.
5. Use a private/dry-run canary where supported; do not automatically retry an upload if the previous attempt may have succeeded.
6. Confirm a durable receipt with content ID, destination URL, privacy state, timestamp and sanitized error reason.
7. Restore schedule only after duplicate prevention, cost hold, and receipts pass tests.

## 5. Failure handling
- Keep YouTube cost hold active unless the owner explicitly releases it after cost review.
- Do not delete existing content or mass-change privacy during infrastructure recovery.
- If a platform requires an unavailable interactive session, mark the task HOLD and ask for a supported authorization path.
- A GitHub Actions success status alone is not proof of publication.
- The retired VPS/n8n architecture is not a recovery target and must not be recreated.

## 6. Completion evidence
Each recovered platform must have current workflow evidence and a destination-verified canary or be explicitly listed as HOLD. Never claim 100% migration from source code presence alone.
