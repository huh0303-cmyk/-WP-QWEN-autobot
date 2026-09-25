# Today Publication Status — 2026-09-25 KST

Checked at approximately 11:50 KST.

## Confirmed public publications: 4

1. WordPress — k-health365.com — published 09:01 KST.
2. Blogger — ki-korea.blogspot.com — published about 06:33 KST.
3. Blogger — seoulintlschoolguide.blogspot.com — published 08:39 KST.
4. Blogger — koreainvest365.blogspot.com — published 10:51 KST.

Only receipt/public-URL verified publications are counted.

## Current same-day state

- WP25: 1 confirmed public. Several missing-site recovery claims were created, but the GitHub WordPress child runs are failing and VPS authenticated REST probes returned HTTP 403. Do not count claims as publications.
- Blogger33: 3 confirmed public. Additional Blogger recovery jobs are dispatched/claimed/failed and will only count after public URL verification.
- Newsrooms2: 0 confirmed today in the checked GitHub RSS publisher runs.
- Tistory5: 0 confirmed; today's dispatcher run failed.
- Naver N1=huh0303: 0 confirmed; identity is mapped but no public receipt yet.
- Instagram/TikTok/Threads/Facebook: 0 confirmed; browser sessions exist but today's SNS scheduler did not produce public receipts.
- Core YouTube: today's generated schedule has 5 ready private-review production slots: INVENTION_STORY1, CAFE_MOZART, RETRO_USA1, CAFE_HEALING, SILENT_ERA_FILM. These are not counted as public publications.

## Today's operating schedule

- WP25: target 1 public post/site/day. Safety floor cron checks hourly at minute 13 KST and fills missing sites only, bounded per run.
- Blogger33: target 1 public post/site/day. Same hourly minute-13 public-floor reconciliation.
- Newsrooms2: 3–10 verified breaking stories per newsroom/day, event-driven from RSS, no fixed filler slots.
- Tistory5: one randomized public slot/site/day in the 08:10–22:50 KST window; local browser publication verification required.
- Naver: only N1=huh0303 active first; target one public post/day after local receipt verification. N2/N3 are not active targets.
- SNS: 24 account slots (Instagram6, TikTok6, Threads6, Facebook6), one public post/account/day after write authorization.
- Core YouTube10: 2–3 productions/channel/week; today's 5 scheduled items remain private-review-only until approval.

## Counting rule

Queued, claimed, dispatched, workflow-success, login-present, and private-review states are not public publication counts. Only a verified public URL counts.
