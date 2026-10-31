# AGENTS.md

## Canonical project continuity rule

Before performing project work, read:
- `docs/GITHUB_OPERATION_RECORD_POLICY_2026-09-25.md`
- `docs/LONDON_PROJECT_ACTIVITY_LEDGER.md`
- `docs/PROJECT_WORKING_AGREEMENT.md`

Every material finding, decision, correction, ID mapping, code/config change,
test result, failure, unresolved item and next action must be recorded in GitHub
during the same work session.

Chat-only state is not authoritative. Resume from the latest GitHub commit and
canonical records. Before asking the user to repeat a prior decision, read
the repository records first.

Never commit passwords, API keys, tokens or private credentials.

## Mandatory PC execution and continuity rule — 2026-10-31

- Use Desktop Commander (DC) and PowerShell together for local PC, browser, filesystem, terminal, and verification work.
- When Work/Codex is unavailable or has no token, continue in the current ChatGPT conversation through the connected DC device and PowerShell; do not block or redirect the user to Work/Codex.
- Use direct WordPress REST API or the approved local deployment workflow for WordPress operations. Do not route WordPress work through third-party WordPress MCP plugins.
- Keep project execution and verification independent of any optional WordPress connector.
- Never ask the user to repeat these established operating rules.
