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
- Prepared catalog: `config/naver_monthly_keyword_100.json`; it contains exactly 100 research-gated candidate queries for every month. These are candidates, not claims of measured volume.
- The catalog is reproducible with `scripts/build_naver_monthly_keyword_catalog.py`; every selected candidate is rechecked on the day it is used.
- Daily planner: `scripts/naver_monthly_keyword_planner.py`; it persists a daily plan before the first post and keeps every same-account base query distinct that day.
- Same-day override applier: `scripts/apply_naver_trend_overrides.py`; after the 30-candidate brief is complete, it replaces only untouched `RESEARCH_REQUIRED` jobs, preserves their IDs and times, and rejects blocked or wrong-site candidates.
- Research order: Naver DataLab relative trend, Naver News freshness, existing search-entry queries, primary official source, recent-title/body duplicate check.
- Naver DataLab is a relative trend signal. The operation never fabricates absolute volume, visitor counts, or rank probability.
- October priorities include government/local support deadlines, heating and energy support, influenza and year-end health checks, station-specific KTX queries, and area-specific airport-bus queries.
- Article links point first to the current government, public-agency, railway, bus, or airport source. A general search-result link never replaces the primary source.

## Morning trend brief and wake behavior

- A Windows wake-only task named `Korea365_오전운영_깨우기` is scheduled for 06:55 KST with `WakeToRun=true` and `StartWhenAvailable=true`.
- This wakes a sleeping PC; it cannot power on a fully shut-down PC unless the machine firmware separately supports and enables scheduled RTC power-on.
- Codex automation `5-2` starts at 07:07 KST and must finish the daily 30-candidate evidence brief by 07:50. Publishing slots start at 08:17.
- Daily candidates may include current sports, politics/policy, film/culture, military/public-safety, support-program changes, and transport topics when same-day evidence and a primary source exist.
- Political posts stay factual and source-led; film posts use KOBIS/distributor sources without copying; military and mine-safety posts use only public safety information and never operational or location-sensitive information.

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
- Planned checks: hourly at minute 07 from 07:07 through 23:07 KST; the 07:07 run prepares the morning trend brief and later runs process due work. Daily persisted plan and per-site gaps remain authoritative.
- Each run must stop at an honest failure or required confirmation instead of inventing a public result.

## 2026-10-01 account handoff state

- A separate browser session was opened at the exact `naver_n1` editor destination.
- Naver redirected it to the sign-in screen, proving that no usable `naver_n1` authenticated session was available in that browser.
- No credentials were stored in files, logs, commits, or automation prompts.
- Exact next action: the owner completes the visible Naver sign-in; the operator then rechecks the destination blog ID before preparing or publishing the first N1 post. N2 follows in its own verified session.
- Latest verification at approximately 01:45 KST: Naver advanced the N1 account to `아이디 보호조치 해제하기` and requires the owner to set and confirm a new password. This is a mandatory security handoff; the operator did not type, read, store, or submit a password. No N1 public post is claimed until the owner completes the visible form and the exact `k-insight-vietnam` editor is rechecked.

## 2026-10-02 prepared plan

- The next-day plan is persisted at `data/naver-daily-plans/2026-10-02.json` with 17 research-required jobs.
- All slots are between 08:17 and 23:17 and retain the N1/N2 180-minute and N3 75-minute same-account minimum gaps.
- The 07:07 run may replace a planned topic only when the same-day trend brief records stronger evidence; a replaced topic still needs the same source, originality, login, and public-URL gates.

## 2026-10-01 08:07 trend-plan application

- Before the first 09:19 slot, the completed 30-candidate trend brief was applied to all 14 untouched jobs in the persisted plan.
- The planned times, per-site counts, minimum gaps, destination blog IDs, and `RESEARCH_REQUIRED` state were preserved.
- No public post was advanced to 08:07. The already verified 생활의정석 URL remains the only Naver public receipt recorded for the day at this checkpoint.
