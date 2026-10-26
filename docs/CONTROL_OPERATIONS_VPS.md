# Control Center Operations — GitHub-only replacement

RETIRED: this document previously described VPS/systemd operations and must not be used to configure or repair production.

## Current rule
- Production workflows run on GitHub Actions.
- Do not use SSH, /opt/korea365, /etc/korea365, systemd, or server-hosted n8n.
- Control-center YouTube actions dispatch .github/workflows/youtube-github-worker.yml.
- The YouTube workflow is manual-only and cost-hold gated until an owner-approved end-to-end canary passes.
- A GitHub workflow run is not proof of publication. Verify the destination URL, content ID, expected account/channel ID, and privacy state.

## Operational status
The 2026-10-26 migration branch retires the known SSH-based workflows and server deployment assets. Remaining legacy scripts or documents mentioning VPS are historical or migration blockers and must not be executed as current runbooks. See docs/VPS_CANCELLATION_AND_GITHUB_ONLY_2026-10-09.md, docs/GITHUB_ONLY_NO_VPS_MIGRATION_INVENTORY_2026-10-26.md, and projects/런던프로젝트GPT/ARCHITECTURE.md.

## Safety
Do not delete posts/videos or change publication privacy during infrastructure cleanup. If a platform lacks a supported GitHub-hosted auth route, mark it HOLD instead of silently using a local or server browser session.
