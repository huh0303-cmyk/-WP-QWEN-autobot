# Meta 12-Account (Instagram 6 + Threads 6) Token Setup Runbook

Owner-facing step-by-step for completing the remaining account connections. Hand this directly
to whichever human or AI session (Claude or GPT) is doing the clicking — every step after
"log in" requires the account owner's own password/consent and cannot be automated by any AI.

Source of truth for handles/IDs: `config/SNS_SIX_BRAND_IDENTITY_LOCK_2026-11-21.json`.

## Status as of 2026-11-23 (this session)

| Platform  | Account         | Status |
|-----------|-----------------|--------|
| Instagram | english_sos1 | TEST PUBLISHED; public URL verified: https://www.instagram.com/p/DgFGOG7lSYt/ (run 45150520283) |
| Instagram | korean_sos1 | TOKEN SAVED BUT EXPOSED IN SCREENSHOT; replace before any use; preflight not run |
| Instagram | japanese_sos1   | NOT DONE |
| Instagram | seoul_jisoo1    | NOT DONE |
| Instagram | seoul_journal1  | NOT DONE |
| Instagram | chinese.sos1    | NOT DONE — **not yet connected to the publisher app at all**, needs "계정 추가" first |
| Threads   | all 6           | NOT DONE |

**Known findings to account for, not to fix in this runbook:**
- Two different Meta apps are currently in use for token issuance: app `2064957407740645`
  ("클로드", used for english_sos1) and app `1383946033947009` ("SEOUL TOPIK" / SIS Center
  Publisher-IG, used for korean_sos1 just now). Both work functionally, but pick one going
  forward to avoid confusion — SEOUL TOPIK already has `instagram_content_publish` scope
  confirmed, so prefer it.
- Legacy secret/variable names from the old 5-account scheme (`*_SEOUL_TOPIK_*`,
  `*_SEOUL_CHRIS_*`, `*_SEOUL_JISOO_*` without the `1` suffix, `*_ENGLISH_PICK1_*`,
  `*_JAPANESE_PICK_*`) are still present in `META-SOCIAL` alongside the new `*_SOS1_*` keys.
  `ENGLISH_PICK1_USER_ID` (17841441355349874) matches `ENGLISH_SOS1` exactly — same account,
  old name. `JAPANESE_PICK_USER_ID` (17841411813216531) does **not** exactly match the
  `japanese_sos1` ID confirmed in this runbook (17841441813216531) — verify which is current
  before reusing either; do not assume they are the same account. This needs a separate cleanup
  task once all 12 connections are verified; it does not block today's work.
- The korean_sos1 token value was briefly visible in a screenshot sent during this session.
  Recommended: regenerate it once (Meta token screen → "토큰 생성" again invalidates the old
  one) and re-save, next time it's convenient. Not urgent enough to block other accounts.

## Step-by-step: generating one Instagram token (repeat per account)

1. Open a Chrome window and log into **instagram.com as the target account** (e.g.
   `japanese_sos1`). Use the account switcher if already logged into Instagram as a different
   brand — do not skip this, using the wrong logged-in account produces a token for the wrong
   account.
2. Go to **developers.facebook.com** → top-right **"내 앱"** → **SEOUL TOPIK** (app ID
   `1383946033947009`).
3. Left sidebar → **이용 사례** → find **"Instagram에서 메시지 및 콘텐츠 관리"** (green check) →
   click its **"맞춤 설정"** button.
4. In the left sub-menu of that page, click **"Instagram 로그인이 포함된 API 설정"** (NOT "API
   setup with Unified login" — that one issues System User tokens, which is the wrong type).
5. Expand section **"2. 액세스 토큰 생성"**. The target account should already be listed with its
   profile ID (these are already discovered — see "Known account IDs" below). If it is **not**
   listed (this is the case for `chinese.sos1`), click **"계정 추가"** first and approve the
   connection while logged in as that account, then it will appear in the list.
6. Click **"토큰 생성"** on the target account's row.
7. A login popup appears, usually pre-filled with whatever account Chrome logged in last — this
   is just browser autofill, not a binding. Clear the field if it shows the wrong handle, and
   log in with the **target account's own password**.
8. A consent screen appears ("~님에 대한 정보를 SIS Center Publisher-IG에 계속 공유하시겠어요?").
   Click **"허용"**.
9. The "토큰 생성됨" popup shows the token once. Check **"이해합니다"**, click **"복사"**.
10. **Do not screenshot this popup** (token value visible = exposed). Just copy and close it.
11. In PowerShell:
    ```
    cd "C:\Users\huh03\Documents\-WP-QWEN-autobot"
    gh secret set META_INSTAGRAM_{ACCOUNT}_ACCESS_TOKEN --env META-SOCIAL -R huh0303-cmyk/-WP-QWEN-autobot --body "$(Get-Clipboard)"
    gh variable set META_INSTAGRAM_{ACCOUNT}_USER_ID --env META-SOCIAL -R huh0303-cmyk/-WP-QWEN-autobot -b "{the account's profile ID}"
    ```
    Replace `{ACCOUNT}` with the uppercase key (`JAPANESE_SOS1`, `SEOUL_JISOO1`,
    `SEOUL_JOURNAL1`, `CHINESE_SOS1`). Reply **"저장함"** only — no screenshots of the token
    screen.
12. Report back which account just finished; the next step is to add a
    `meta-{account}-sos-auth-preflight.yml` workflow (copy
    `.github/workflows/meta-korean-sos-auth-preflight.yml` and swap the account name/env var)
    and run it once via `workflow_dispatch` to confirm identity before moving to the next
    account.

### Known Instagram account IDs (already discovered, step 5 should show these)
- `korean_sos1` → `17841410825136018`
- `seoul_journal1` → `17841449179626171`
- `seoul_jisoo1` → `17841404970616486`
- `japanese_sos1` → **ID mismatch unresolved**: Meta Developers API setup currently displays `17841411813216531`, while an earlier record listed `17841441813216531`. Do not save either ID as verified; generate/verify token and trust the `/me` response only.

- `english_sos1` → `17841441355349874`
- `chinese.sos1` → not yet connected; will be assigned when added in step 5

## Step-by-step: Threads tokens (repeat per account, all 6 remain)

Same app, same account-login caution. In step 3, instead of the Instagram use case, use the
**"Threads API 액세스"** use case (already shows a green check on the app dashboard, meaning it's
configured) → **"맞춤 설정"**. Its token-generation section follows the same per-account list +
"토큰 생성" + login + consent pattern as Instagram. Secret/variable names:
`META_THREADS_{ACCOUNT}_ACCESS_TOKEN` / `META_THREADS_{ACCOUNT}_USER_ID`.

Two Threads accounts (`english_sos1`, `seoul_journal1`) were previously blocked on a missing 2FA
SMS during a prior session's attempt — if that recurs, it is a phone/carrier issue on those
specific Meta accounts, not something fixable from this side; just note it and move to the next
account.

## After all 12 are verified

Per the owner's explicit requirement, do not enable randomized auto-publish scheduling until:
1. All 12 secrets exist and each resolves via its preflight workflow to the exact expected
   account (no mismatches).
2. Each account has one actual test publish with a confirmed public URL.

Only after those prerequisites are complete, enable a GitHub Actions randomized dispatch schedule for 3 posts per day per account on each platform (36 destination posts/day), within 08:10-22:50 KST, with at least a 15-minute gap. Adapt the existing `config/meta_five_account_daily_policy.json` cadence pattern to all six accounts, and update `meta-randomized-dispatch.yml` account/secret references first.

## Operational update - 2026-11-23 18:50 KST

- Published and verified one public Instagram image post for `@english_sos1`: https://www.instagram.com/p/DgFGOG7lSYt/ (media ID `18135124276695322`; GitHub Actions run `45150520283`).
- This is one of 12 required account/platform tests. No other account or Threads post was published, and no automatic schedule was enabled.
- `korean_sos1` token is recorded as visible in a screenshot. Treat it as exposed; replace the token before running its preflight or publishing. The owner's password/2FA/consent may be required during the replacement flow.

## 2026-11-23 implementation status — 12-destination GitHub Actions

The new implementation is on branch `codex/meta-12-destination-publisher-20261123`; the legacy five-account dispatcher is not the 12-account publisher and has been manually disabled. Repository variables `META_LIVE_PUBLISH` and `META_12_TARGETS_READY` are both false. The new scheduled workflow checks both values and also requires all 12 destinations to have verified identity, write scope, and one confirmed public test URL. It creates 36 randomized daily destination slots, grouped in three KST windows between 08:10 and 22:50 with 15-minute minimum spacing.

Current readiness: English SOS Instagram has a public test URL; Korean SOS Instagram identity was verified by read-only preflight, but write permission and its public test remain unverified. Other ten destinations remain pending. Do not enable the schedule until every row passes. The Korean token is stored in the GitHub environment secret; its exposed screenshot history means rotation is recommended. Japanese SOS ID remains unresolved; use only the authenticated `/me` response, never the disputed prior ID. Chinese SOS Instagram app connection and Threads per-account authorization remain to be completed.

The branch includes three manual workflows: all-account read-only identity preflight, one selected destination test publish with deduplication/reservation, and a scheduled publisher gated by readiness. Seoul Journal publication requires a reviewed, source-backed queue item. Merge of the branch makes the workflows available in Actions but does not activate scheduled publication while the two repository variables remain false.
