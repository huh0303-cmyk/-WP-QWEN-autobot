# London Project — Canonical Current State

Updated: 2026-09-25 (Asia/Seoul)

## Owner cadence override — 2026-09-25

- The locked ten YouTube channels only: two or three private productions per channel per week, with the production days randomized each week.
- Every non-YouTube destination/account: one post per day.
- A daily slot is generated from the destination's own topic bank or role brief and carries a date/account duplicate key.
- Browser login alone is not represented as API write authorization. A blocked account remains planned but is not falsely marked published.

This file is the canonical continuity record for the Korea365 London Project. Before asking the owner to repeat channel names, IDs, account roles, or publishing policy, read this file and the referenced machine-readable configuration.

## Final business objective lock — 2026-09-25

- **Center of the entire London Project: `k-health365.com`**, the only currently AdSense-approved site and the operating benchmark.
- The primary business goal is **Google AdSense revenue growth**. The leading operating KPIs are **daily visitors, pageviews, Google indexed URLs, AdSense approval status, and AdSense revenue**.
- **Canonical operating count:** 25 regular WordPress sites **including `k-health365.com`**, plus 2 separate newsrooms. Of the 25 regular WordPress sites, `k-health365.com` is the currently AdSense-approved center and the other 24 are additional AdSense-approval targets. Blogspot has 33 properties.
- **YouTube core 10 only** (5 playlist + 5 knowledge): publish 2–3 times per channel per week on randomized days.
- **All other connected non-newsroom destinations:** target 1 public publication per destination/account/channel per KST day, subject to exact identity/write authorization and quality gates.
- **Newsrooms:** `koreanews365.com` and `theseouljournal.com` target 3–10 verified breaking-news stories per newsroom per KST day. Never fabricate filler when verified leads are insufficient.
- **Google indexing is revenue infrastructure:** indexing gaps, sitemap/GSC failures, accidental noindex, crawl blocks and low-value duplication are priority operational defects, not secondary SEO notes.

## Non-negotiable operating rules

- Never store passwords, OAuth refresh tokens, API keys, cookies, or application passwords in Git.
- Do not claim an account is connected merely because its public profile can be opened. A publishing connection is complete only after identity and write permission are verified.
- Never create a duplicate account before checking the existing account inventory.
- YouTube publishing remains private/review-only unless the owner separately approves a public release.
- Blogspot: 33 blogs, one public post per blog per day, distributed randomly through the day, with a per-blog/per-date duplicate guard.
- TikTok, Instagram, Facebook, and Threads use the same six-role policy. Public automation starts per account only after that account's identity and write credential are verified.
- Visible content must read naturally and must not contain internal generation/process notices. This does not authorize fake experience, fabricated evidence, undisclosed sponsorship, or misleading health claims.

## YouTube: locked ten-channel mapping

The following IDs are authoritative. Do not ask the owner to provide them again.

| No. | Production key | Locked name | Channel ID |
|---:|---|---|---|
| 01 | `globalmusic` | CAFE_ROMANTIC | `UCbJfEtsffpgI5MsKkB7BYvQ` |
| 02 | `healing` | Cafe healing | `UC7yEsLM-HoXudngrD-4FIqg` |
| 03 | `starbucks` | CAFE_STARBUCKSVIBES / Starbucks vibes | `UC_e-sbLkVgwJNYEeobolNog` |
| 04 | `mbb` | CAFE_MOZART | `UC7jOhyMa-FIrzZuea97z1Pw` |
| 05 | `kpop` | CAFE_KPOP | `UCKZsfAWyCmY0jckf4IWZrqw` |
| 06 | `nasa` | NASA_XFILES | `UCtNLZO07Oh3UnXPI2CjOgNg` |
| 07 | `history` | HISTORY_TV_TODAY | `UCVBvZwodUF4s57KeNicxQ3w` |
| 08 | `invention` | INVENTION_STORY1 | `UCgNj-yS93A_fOHXXvG49fww` |
| 09 | `silent_era` | SILENT_ERA_FILM | `UCLvy6kSpC8-7o3hnSrfQ47g` |
| 10 | `retro_reels` | RETRO_USA1 | `UCwh49EokdWFJqYFE_zA6XDQ` |

Production result recorded on 2026-09-24/25:

- The prior HTTP 403 cards were not proof that the channels did not exist; they reflected an incomplete/incorrect lookup-auth path.
- Queue ownership was repaired and `korea365-youtube-worker.service` was restarted successfully.
- Jobs for all ten locked keys were queued for private/review publishing only.
- Control-room state and the ten-channel lock were synchronized. See `data/youtube-ten-channel-lock.json` and `data/youtube-ten-control-receipt.json` on production when auditing runtime state.

## Blogspot 33: daily production policy

- All 33 blogs were checked through the Blogger API, public URL, metadata, and registry rows.
- Production scheduling runs on the VPS, not by relying on the previously failing GitHub Actions text-generation path.
- The daily coordinator starts at 00:05 KST and spreads 33 individual jobs approximately from 06:10 to 23:20 KST.
- Each blog receives exactly one public post per date when successful; the publisher uses a date/account idempotency key.
- Generation/transient failures are retried without duplicating a successful publication.
- The systemd units and scheduler scripts committed with this record are the deployable source of truth.

## WordPress correction recorded

- `kworld365.com` post 895 had an operational stock-photo/license sentence visible as the first body line.
- The visible sentence was removed while license provenance remains internal.
- `scripts/free_article_supplier.py` was corrected so future posts do not expose that operational caption.

## Social network six-role matrix

Applies identically to TikTok, Instagram, Facebook, and Threads:

1. Korean / TOPIK
2. Japanese
3. English
4. Health supplements and health shopping
5. Travel, hotels, and K-pop ticket shopping
6. Lifestyle hot-item shopping

Roles 4–6 are shopping channels. Target cadence is one public post per verified account per day, randomly distributed from 08:10 to 22:50 KST, with at least a 15-minute spacing and a per-platform/account/date duplicate guard.

The machine-readable authority is `config/sns_six_channel_policy.json`.

Status at this checkpoint:

- Required slots: 24 (6 roles × 4 platforms)
- Existing/observed identities: 13
- Missing identities: 11
- Verified write connections: 0 of 24

Therefore the desired policy is recorded, but public SNS automation must remain disabled per account until OAuth/write permission is actually verified. Existing handles and the missing-slot list are fully captured in the JSON; do not ask the owner to re-list them.

## Control room state

- `/social-accounts` is now the unified 52-card account room: YouTube 20, SNS 24, Tistory 5, and Naver 3.
- SNS is shown as six independent role cards on each of TikTok, Instagram, Facebook, and Threads, including missing-account slots.
- Each card has its own identity, public-profile link when known, official-login link, connection level, operating role, and action explanation.
- Existing unconnected SNS cards open the official login path and never pretend to publish.
- The ten core YouTube cards queue private jobs only.
- Each Tistory card targets one public post per day through the local registrar. The owner reported Tistory is already logged in on 2026-09-25; do not request login again unless an actual session check fails or CAPTCHA appears.
- Naver N1, N2, and N3 are separate cards and must remain separate login/profile bindings. The owner reported Naver is already logged in on 2026-09-25. Do not ask for login again; the remaining task is to bind the existing logged-in sessions to the exact N1/N2/N3 blog IDs and verify one public test per account.

## Social login verification checkpoint — 2026-09-25

Owner explicitly requested live login verification for **Instagram, TikTok, Threads, and Facebook**. Do not omit Facebook. Use the owner's existing browser sessions first; do not ask for credentials in chat and do not force a re-login if the session is already valid.

Current blocker at this checkpoint: the authorized PC device `ChrisHUH` is reported offline by the remote desktop connector, so the browser sessions cannot be inspected or opened remotely from this chat. This is a device-connection blocker, not evidence that the social accounts are logged out.

When the device connection is available, verify in this order and record each account separately: Instagram -> TikTok -> Threads -> Facebook. For each account, capture: exact handle/page ID, current login state, publish/write permission state, and one reversible test receipt before enabling daily public posting.

## Live social browser-session result — 2026-09-25

Remote device `ChrisHUH` is online again. Chrome `Profile 5` contains active session evidence for **Instagram, TikTok, Threads/Instagram, and Facebook**; the four sites were opened explicitly in that profile. No cookie values or passwords were read or stored.

This checkpoint means **do not ask the owner to log in again** unless the browser itself shows an expired-session/MFA/CAPTCHA challenge. It does **not** mean platform write/API authorization is complete. Keep `publish_connected=false` until the exact account/page identity and write scope are verified and one account-specific publication test produces a receipt.

## Naver N1 connection checkpoint — 2026-09-25

- Owner selected **N1 = `huh0303`** as the first Naver blog to activate.
- Google Sheet `CEO종합상황실` -> `자동화_플랫폼계정` now contains an enabled Naver row for `naver_n1`, destination `huh0303`, editor URL `https://blog.naver.com/GoBlogWrite.naver?blogId=huh0303`, cadence one public post per KST day.
- GitHub `config/automation_rooms.json` is synchronized: N1 enabled, destination `huh0303`, public policy, daily 1 / weekly 7.
- The public blog and Naver write-editor URLs were opened on the owner's PC. Do not ask the owner to re-enter the N1 identity.
- Remaining verification is one real public test receipt from the local browser publisher; until that receipt exists, do not claim daily_active.

## Remaining work, in order

1. Verify or create only the 11 missing SNS identities, checking for duplicates first.
2. Record Facebook page IDs and confirm the Japanese page-role mapping.
3. Complete Meta/Instagram/Threads and TikTok OAuth with write scope; authentication and final consent require the owner in the browser.
4. Run one private/draft or platform-supported test per account; record receipt IDs.
5. Enable one-public-post-per-day scheduling only for accounts that pass identity + write + test verification.
6. Expand the control-room UI to show the canonical 24 SNS slots and live connection/publication receipts.

## Verification language

Use these states consistently:

- `observed`: a profile/page was seen publicly or in the owner UI.
- `identity_verified`: the exact account/page ID or handle was confirmed.
- `publish_connected`: a write credential was verified.
- `test_published`: a real draft/private/test receipt exists.
- `daily_active`: recurring publication is enabled and the latest run is healthy.

Never collapse those five states into a single vague “connected” label.
