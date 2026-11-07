# Meta ten-account execution checkpoint — 2026-11-07 KST

Owner mandate: five Instagram plus five Threads connections; each connection three posts daily at randomized KST times. Latest instruction supersedes prior one-post or language-only cadence.

## Verified
- ChrisHUH DC/PowerShell connected; GitHub CLI authenticated as huh0303-cmyk.
- Repository main fetched at 4ee900a1; isolated worktree used to preserve unrelated local changes.
- GitHub environment META-SOCIAL contains three account tokens. Actual /me verification run 42342979215 confirmed:
  - Instagram english_pick1: 17841441355349874
  - Instagram japanese_pick: 17841411813216531
  - Threads seoul_jisoo: 29598479706425784
- No write scope or public publication verified. Stored the verified Threads user ID as an environment variable.
- Other seven account tokens are absent.
- Instagram token generator lists seoul_topik (17841410825136018), seoul_chris1 (17841449179626171), seoul_jisoo (17841404970616486), japanese_pick and english_pick1.
- Threads token generator currently displays seoul_jisoo only. Accounts Center screenshot shows Threads seoultopik, which must not silently substitute for seoul_topik.
- Instagram seoul_topik token generation opened a force-authentication sign-in page. Owner login is required; no credentials requested in chat or read from password stores.

## Changes
- Updated both cadence configs to three per account per platform.
- Added deterministic per-date randomized 30-slot plan across morning/afternoon/evening KST windows.
- Added plan-only GitHub workflow; it does NOT dispatch public posts.
- Added hidden-input token registration helper: verifies exact /me handle before storing token via gh stdin to META-SOCIAL. Token values never enter repository files.
- Three schedule tests and four existing policy tests passed; Python compilation and diff checks passed.

## Remaining
1. Owner logs in to seoul_topik in prepared Instagram OAuth popup.
2. Complete remaining seven token flows, verifying each exact handle. Resolve seoul_chris1 versus requested seoul_chris and seoultopik versus seoul_topik with actual platform identity.
3. Verify publish scopes and token expiry/refresh handling.
4. Implement topic-specific Gemini content/media queue, editorial validation, persistent idempotent dispatcher, failure recovery and public URL receipts.
5. Run actual per-account production canaries and verify public URLs before declaring KPI achieved.

Status: PARTIAL. Authentication and daily publishing KPI are not complete. No public post was created in this session.

## Account correction — 2026-11-07
- `english_pick_daily` is not owned by the user. It was removed from the pending Threads tester dialog and was never invited, authorized, tokenized, or published through this workflow.
- Do not confuse it with the separately listed exact Instagram handle `english_pick1`, which remains isolated by exact-handle verification. No token from `english_pick_daily` may be accepted.
- The actual Threads handle `seoultopik` was invited as a Threads tester and is currently pending acceptance.

- Threads seoultopik login handoff: the browser's saved password was rejected by Threads. The login page is open with the exact Instagram username; owner must enter the current password. No password was read, logged, or committed.



## Token registration checkpoint — 2026-11-07

Current exact-identity result: 7/10 connections verified by workflow run `42366598475`.

| Platform | Account | Result |
|---|---|---|
| Instagram | seoul_topik | Long-lived token and token-scoped user ID stored; `/me` exact match |
| Instagram | seoul_jisoo | Long-lived token and token-scoped user ID stored; `/me` exact match |
| Instagram | english_pick1 | Existing token exact match verified |
| Instagram | japanese_pick | Existing token exact match verified |
| Instagram | seoul_chris1 | Deferred by owner |
| Threads | seoultopik | Tester accepted; token/user ID stored; exact match verified |
| Threads | seoul_jisoo | Token/user ID stored; exact match verified |
| Threads | english_pick1 | Tester accepted; token/user ID stored; exact match verified |
| Threads | japanese_pick | BLOCKED: Threads profile does not exist; public profile URL returns not found |
| Threads | seoul_chris1 | Deferred by owner |

The current Threads handle for the TOPIK account is `seoultopik` (no underscore), while the Instagram handle is `seoul_topik`. Secret logical keys remain `SEOUL_TOPIK`.

The web Threads signup/SSO route cannot create `japanese_pick` in the current Accounts Center session and repeatedly returns to `seoultopik`. Create the missing `japanese_pick` profile once in the mobile Threads add-profile flow, then accept the tester invitation and generate its API token.

No public publishing was attempted. The readiness workflow remains a non-publishing check; enablement still requires the remaining required profile/token connections, write-scope verification, and a canary public URL receipt.
