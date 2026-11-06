# Meta five-account operating policy

Effective: 2026-11-06 KST. Owner-confirmed mapping for both Instagram and Threads.

| Account | Instagram handle | Threads handle | Daily editorial scope |
|---|---|---|---|
| TOPIK | @seoul_topik | @seoul_topik | TOPIK education |
| Jisoo | @seoul_jisoo | @seoul_jisoo | Current issues, politics, sports, health supplements, skincare |
| Chris | @seoul_chris | @seoul_chris | Current issues, politics, sports, health supplements, skincare |
| English | @english_pick1 | @english_pick1 | Beginner-to-practical English conversation |
| Japanese | @japanese_pick | @japanese_pick | Beginner-to-practical Japanese conversation |

## Operating rules
- Target cadence: one native-format post per account per platform per day.
- KST randomized publication window: 08:10–22:50; minimum spacing 15 minutes.
- No verbatim cross-posting between Instagram and Threads.
- Current-affairs and political posts require dated, reliable sources and neutral framing.
- Sports results/schedules, product prices, and availability require current verification.
- Health and skincare claims require reliable evidence; no diagnosis or guaranteed efficacy.
- Account-specific authentication must never be substituted across handles or platforms.
- A post is successful only after its public URL is retrieved and recorded.
- Never commit access tokens, passwords, or private credentials.

## Meta application
- App: SIS Center Publisher
- App ID: 1383946033947009
- Existing dashboard use cases show Threads API, Instagram content management, and Pages API selected. These checkmarks do not prove account-specific OAuth, write scopes, or publish permission.
- Ten independent connections are required: five Instagram and five Threads.

## Authentication variable names
For each account and platform, register GitHub Actions environment secrets:
- META_{PLATFORM}_{ACCOUNT_KEY}_ACCESS_TOKEN
- META_{PLATFORM}_{ACCOUNT_KEY}_USER_ID

PLATFORM is INSTAGRAM or THREADS. ACCOUNT_KEY is SEOUL_TOPIK, SEOUL_JISOO, SEOUL_CHRIS, ENGLISH_PICK1, or JAPANESE_PICK. No token values or IDs are stored in this repository. OAuth consent and platform-specific write scopes must be approved per account.

## Scheduler state
.github/workflows/meta-five-account-daily-preflight.yml runs at 09:10 KST daily. It checks whether all ten account-specific token/user-ID pairs are present without printing values. This is a readiness check only, not a content publisher.

Publication remains safely blocked until all ten identities and write scopes are verified and a daily approved content queue plus publisher integration is connected. Do not report automatic daily publishing as active before a real public post URL has been verified for each target account.

## Current state at policy creation
- Owner confirmed the exact five handles are intended on both platforms.
- Account registration, OAuth consent, token validity, user IDs, write permissions, content queue, and public post receipts are not yet verified for these ten connections.
- publish_enabled=false.
