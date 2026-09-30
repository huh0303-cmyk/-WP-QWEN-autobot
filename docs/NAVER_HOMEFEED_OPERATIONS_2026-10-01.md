# Naver Home-feed operating setup — 2026-10-01

## Active accounts

- `naver_n1`: 부의정석, blog ID `k-insight-vietnam`, three to four randomly spaced reviewed posts per day.
- `naver_n2`: 헬스의정석, blog ID `health-standard`, three to four randomly spaced reviewed posts per day.
- `naver_n3`: 생활의정석, blog ID `sky-only`, eight to ten randomly spaced reviewed posts per day; primary account.
- The browser session must be verified against the exact destination blog ID before editing or publishing.

## Operating contract

- Network total: fourteen to eighteen reviewed posts per KST day.
- Minimum same-account gap: N1/N2 180 minutes, N3 75 minutes; no bulk publishing or catch-up burst.
- Current keyword research, official-source verification, original writing, one copyright-safe image, editorial review, Naver save/publish, and result verification.
- Policy/support posts require a current government or public-agency source and clear attribution.
- Block unverified celebrity gossip, expired or invented benefits, medical/investment guarantees, copied articles, unlicensed photos, and undisclosed affiliate links.
- Revenue is an objective measured from real connected data, never a guarantee.

## Monthly search-demand operation

- Canonical calendar: `config/naver_monthly_keyword_calendar.json`; it covers January through December.
- Daily planner: `scripts/naver_monthly_keyword_planner.py`; it persists a daily plan before the first post and keeps every same-account base query distinct that day.
- Research order: Naver DataLab relative trend, Naver News freshness, existing search-entry queries, primary official source, recent-title/body duplicate check.
- Naver DataLab is a relative trend signal. The operation never fabricates absolute volume, visitor counts, or rank probability.
- October priorities include government/local support deadlines, heating and energy support, influenza and year-end health checks, station-specific KTX queries, and area-specific airport-bus queries.
- Article links point first to the current government, public-agency, railway, bus, or airport source. A general search-result link never replaces the primary source.

## Search registration boundary

- Naver public URL and Naver search visibility are checked after publication.
- Google Search Console is used only for a property whose ownership is verified. A `blog.naver.com` post is not claimed as submitted through an unrelated Korea365 property.
- Google Indexing API is disabled for general Naver blog articles because Google restricts it to `JobPosting` and `BroadcastEvent` pages.
- Sitemap/RSS submission is a crawl hint for owned sites, not an indexing or traffic guarantee.

## Public benchmark research

- Detailed evidence record: `docs/NAVER_SEARCH_GROWTH_RESEARCH_2026-10-01.md`.
- Public high-traffic blog reports and visible Naver results were studied for structure, not copied.
- Reusable patterns: exact search intent in the title, answer-first opening, short scannable sections, current official link, concrete checklist, related internal links, and genuinely useful route/location detail.
- Rejected patterns: repeated keyword blocks, unsupported discount/price claims, stale timetable numbers, fake urgency, and claims of a verified 100,000 daily visitors without connected analytics evidence.

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
- Name: `네이버 3개 월별 키워드 운영`
- Status: active
- Planned checks: hourly at minute 37 from 07:37 through 23:37 KST; daily persisted plan and per-site gaps remain authoritative.
- Each run must stop at an honest failure or required confirmation instead of inventing a public result.

## 2026-10-01 account handoff state

- A separate browser session was opened at the exact `naver_n1` editor destination.
- Naver redirected it to the sign-in screen, proving that no usable `naver_n1` authenticated session was available in that browser.
- No credentials were stored in files, logs, commits, or automation prompts.
- Exact next action: the owner completes the visible Naver sign-in; the operator then rechecks the destination blog ID before preparing or publishing the first N1 post. N2 follows in its own verified session.
