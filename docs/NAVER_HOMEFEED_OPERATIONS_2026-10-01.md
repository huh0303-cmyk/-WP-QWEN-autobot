# Naver Home-feed operating setup — 2026-10-01

## Selected account

- Site ID: `naver_n3`
- Display name: `생활의정석`
- Naver blog ID: `sky-only`
- Editor: `https://blog.naver.com/PostWriteForm.naver?blogId=sky-only`
- Verified Chrome login: account `huh4`
- Standby accounts: `naver_n1` 부의정석, `naver_n2` 헬스의정석

## Operating contract

- One to five reviewed posts per KST day.
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
- Publication state at record time: `draft_saved`; no public URL yet. Do not report as published until Naver returns and the public post URL is verified.

## Recurring operation

- Codex heartbeat automation ID: `5-2`
- Name: `생활의정석 하루 5회 운영`
- Status: active
- Planned daily checks: five non-hourly KST slots, with the ten-minute minimum gap enforced by policy.
- Each run must stop at an honest failure or required confirmation instead of inventing a public result.
