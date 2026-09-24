# Control Room Connection Audit — 2026-09-25

## Executive verdict

The control room is **not yet 100% end-to-end connected**. Several inventories are registered, but public write authorization or receipt-backed publication is still missing on some platforms.

## Verified now

- WordPress registry: 27 enabled entries = 25 regular WordPress including k-health365.com + 2 newsrooms.
- Blogspot: 33/33 destination IDs present and enabled.
- Core YouTube: 10/10 channel IDs present and enabled (5 playlist + 5 knowledge).
- Tistory: 5/5 destination URLs enabled. One-post-per-day policy and missing GitHub workflows were repaired on 2026-09-25.
- Naver N1: activated as huh0303 in GitHub and the operating Google Sheet; editor URL is registered and the owner reported the browser login already exists.
- Social browser sessions: Instagram, TikTok, Threads/Instagram, and Facebook session evidence exists in Chrome Profile 5 on device ChrisHUH.

## Not yet end-to-end verified

- Blogspot 33 are currently configured with publish_policy=draft in automation_hub_sites.json. They are registered, but this is not the final target of one public post per day.
- Tistory 5 still need receipt-backed public publication verification after the repaired queue/workflow reaches the already logged-in local registrar. Older 2026-09-25 schedule rows still show blocked_auth and must be regenerated/reconciled.
- Naver N1=huh0303 is configured, but one real public test receipt has not yet been recorded. N2/N3 remain intentionally disabled.
- Instagram/TikTok/Threads/Facebook are browser-login verified, but account-specific write/API authorization and publication receipts are not yet verified; current daily schedule marks them blocked_auth.
- Survival language YouTube channels Chinese, Vietnamese, Portuguese still lack exact channel IDs. Japanese ID is known but upload_enabled remains false in the current file.

## Canonical business target

- Regular WordPress: 25 total, including k-health365.com, one public post per day.
- Newsrooms: 2, each 3–10 verified breaking-news posts per day.
- Blogspot: 33, one public post per day.
- Tistory: 5, one public post per day.
- Naver: start with N1=huh0303, one public post per day after receipt-backed verification.
- Instagram/TikTok/Threads/Facebook: one public post per connected account per day after write authorization.
- Core YouTube 10 only: 2–3 productions per channel per week.
- Revenue KPI priority: daily visitors, pageviews, Google indexing, AdSense approval, AdSense revenue.
- k-health365.com remains the currently AdSense-approved center and operating benchmark.

## Rule

Do not display login presence, destination registration, queued work, or draft creation as “connected/publication complete.” A platform is publish_connected only after identity + write permission + successful receipt-backed publication are verified.
