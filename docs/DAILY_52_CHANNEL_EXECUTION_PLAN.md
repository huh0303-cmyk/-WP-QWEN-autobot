# Daily Channel Execution Plan

## Goal

Prepare one daily slot for every non-YouTube destination: TikTok 6, Instagram 6, Facebook 6, Threads 6, Tistory 5, and Naver 3. Only the locked ten YouTube channels are scheduled, each on two or three randomly selected days per week and always as private/review-only production.

## Implemented foundation

- `scripts/plan_52_channel_daily.py` loads the canonical account registries and refuses to run unless exactly 32 daily non-YouTube targets and 10 locked YouTube identities are present.
- Every account gets one deterministic date/account duplicate key.
- Due targets are reshuffled and distributed between 08:10 and 22:50 KST, with non-round minute jitter.
- The result is saved as `data/daily-channel-schedule/YYYY-MM-DD.json`.
- `korea365-daily-52-plan.timer` creates the plan at 00:01 KST each day with a small service-start jitter.
- Planning is separated from publishing. A slot is `ready` only after exact identity and write authority are verified; otherwise it is `blocked_auth`.

## Release gates

1. YouTube: only the locked ten channels are eligible, two or three times weekly, and remain `private_review_only`; public release requires a separate owner decision.
2. TikTok, Instagram, Facebook, Threads: public posting requires account identity, platform write authorization, and one receipt-backed test.
3. Tistory: public posting requires the local persistent browser login and one successful account-specific test.
4. Naver: each of N1, N2, and N3 requires a separate persistent login profile, exact blog ID, and one successful test.
5. No executor may convert `blocked_auth` into a publish attempt.

## GPT continuation sequence

1. Read `docs/LONDON_PROJECT_CURRENT_STATE_2026-09-25.md`, `docs/GPT_CONTINUITY_HANDOFF_2026-09-25.md`, this file, and `config/sns_six_channel_policy.json`.
2. Inspect the latest `data/daily-52-schedule/YYYY-MM-DD.json` on the VPS.
3. Work through blocked accounts one at a time. Ask the owner only to complete login, MFA, captcha, or final consent.
4. Record exact account/page ID and write scope. Never store credentials in Git.
5. Perform one reversible test and save the receipt.
6. Set that account's canonical `publish_connected` flag only after the test succeeds.
7. Connect the due-slot executor for that platform with a per-account/date idempotency check.
8. Report five states separately: observed, identity verified, publish connected, test published, daily active.

## Completion definition

The project is complete only when all 52 cards have a verified identity, verified write permission, a successful test receipt, and a healthy latest daily run. A generated slot alone is not publication proof.
