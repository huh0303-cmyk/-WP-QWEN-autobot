# GPT / Codex Continuity Handoff — London Project

Use this document when Codex usage is limited or the work is continued in ChatGPT. It is a continuity guide, not a credential store.

## First instruction to the next assistant

Read these repository files before asking the owner any account questions:

1. `docs/LONDON_PROJECT_CURRENT_STATE_2026-09-25.md`
2. `config/sns_six_channel_policy.json`
3. `docs/LONDON_PROJECT_BLUEPRINT.md` if present
4. Existing YouTube lock/receipt and Blogspot 33 registry files

Treat the ten YouTube mappings and the six-role SNS matrix as already supplied and approved. Do not ask the owner to enumerate them again.

## What is complete

- Ten authoritative YouTube channel IDs are locked and production jobs were queued privately.
- The YouTube worker and queue permissions were repaired.
- Blogspot 33 identity/API checks were completed and the VPS daily randomized scheduler was installed.
- The KWorld visible stock-license first line was removed and the future supplier path was corrected.
- A consolidated social inventory and control-room page were created.
- The full 24-slot TikTok/Instagram/Facebook/Threads role policy is now machine-readable.

## What is intentionally not claimed complete

- TikTok, Instagram, Facebook, and Threads do not yet have verified production write credentials in the VPS runtime.
- Eleven of the 24 required SNS role slots still lack confirmed accounts.
- Public daily SNS publishing is therefore not enabled yet. Do not report it as active merely because a profile URL opens.

## Safe continuation procedure

1. Pull the latest `main` branch of this repository.
2. Compare production runtime files with the committed source; do not reset or overwrite the dirty production tree broadly.
3. Check account existence before creating anything.
4. Ask the owner only for actions that cannot be done without them: login, MFA, captcha, or final OAuth consent.
5. Never request passwords or tokens in chat and never commit secrets.
6. After each account authorization, verify identity and write scope, then perform one reversible test and save its receipt.
7. Enable recurring public posting for that account only after the test passes.
8. Update the canonical current-state document and machine JSON whenever status changes.

## Copy-ready continuation prompt

> Continue the Korea365 London Project from the latest GitHub `main` branch. First read `docs/LONDON_PROJECT_CURRENT_STATE_2026-09-25.md`, `docs/GPT_CONTINUITY_HANDOFF_2026-09-25.md`, and `config/sns_six_channel_policy.json`. Do not ask me to repeat the ten YouTube channel IDs or the six SNS roles. Verify existing accounts before creating duplicates. YouTube remains private/review-only. Blogspot 33 remains one public post per blog per day with randomized scheduling. For TikTok, Instagram, Facebook, and Threads, connect and test accounts one by one; enable daily public posting only after exact identity and write authorization are verified. Never place credentials in Git or chat. Report each account as observed, identity verified, publish connected, test published, and daily active separately.

## Production references

- Control room: `https://control.korea365.org`
- Production application root: `/opt/korea365`
- Control service: `korea365-control.service`
- YouTube worker: `korea365-youtube-worker.service`
- Blogspot scheduler: `korea365-blogger33-daily.timer`

Do not include server passwords, OAuth tokens, cookies, or API keys in future handoffs.
