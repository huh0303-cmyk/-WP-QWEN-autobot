# Naver Home-feed operating setup — 2026-10-01

## Active accounts

- `naver_n1`: 부의정석, blog ID `k-insight-vietnam`, one reviewed public post per day.
- `naver_n2`: 헬스의정석, blog ID `health-standard`, one reviewed public post per day.
- `naver_n3`: 생활의정석, blog ID `sky-only`, one to five reviewed public posts per day; primary account.
- The browser session must be verified against the exact destination blog ID before editing or publishing.

## Operating contract

- Network total: three to seven reviewed posts per KST day: N1 one, N2 one, and N3 one to five.
- At least ten minutes between saves or publications; no bulk publishing.
- Current keyword research, official-source verification, original writing, one copyright-safe image, editorial review, Naver save/publish, and result verification.
- Policy/support posts require a current government or public-agency source and clear attribution.
- Block unverified celebrity gossip, expired or invented benefits, medical/investment guarantees, copied articles, unlicensed photos, and undisclosed affiliate links.
- Revenue is an objective measured from real connected data, never a guarantee.

Canonical machine-readable policy: `config/naver_homefeed_automation.json`.

## First prepared post receipt

- Prepared: 2026-10-01 KST
- Title: `2026년 10월 양육비 선지급, 소득기준 폐지 전에 꼭 확인할 것`
- Primary source: 성평등가족부 보도자료, 2026-09-21
- Verification: 2026-10-29 income-test removal; other eligibility review remains; child payment amount described from official material.
- Image: original generated editorial illustration at `assets/naver/2026-10-01-child-support-advance.png`; no third-party news photo copied.
- Naver editor evidence: logged-in `생활의정석` editor accepted title, body, and image; explicit `저장` returned `임시저장이 완료되었습니다.` and the saved-draft count changed from 114 to 115.
- Draft state at 00:32 KST: `draft_saved`; the draft was not reported as published at that point.
- Public state: `published` after the owner confirmed the logged-in `생활의정석` session.
- Naver log number: `224427681159`
- Public URL: `https://blog.naver.com/sky-only/224427681159`
- Browser verification: Naver PostView showed the exact title, category `[정부지원금]`, author `생활의정석`, timestamp `방금 전`, body, source links, and tags.
- External verification: desktop and mobile public URLs returned HTTP 200; the mobile response contained the exact title.

## Recurring operation

- Codex heartbeat automation ID: `5-2`
- Name: `네이버 3개 블로그 일일 운영`
- Status: active
- Planned daily checks: five non-hourly KST slots, with the ten-minute minimum gap enforced by policy.
- Each run must stop at an honest failure or required confirmation instead of inventing a public result.

## 2026-10-01 account handoff state

- A separate browser session was opened at the exact `naver_n1` editor destination.
- Naver redirected it to the sign-in screen, proving that no usable `naver_n1` authenticated session was available in that browser.
- No credentials were stored in files, logs, commits, or automation prompts.
- Exact next action: the owner completes the visible Naver sign-in; the operator then rechecks the destination blog ID before preparing or publishing the first N1 post. N2 follows in its own verified session.
