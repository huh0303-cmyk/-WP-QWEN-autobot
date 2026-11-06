# PM CURRENT STATUS

Updated: 2026-11-06 KST
Role: London Project current source-of-truth summary

## North Star
- Primary web KPI: AdSense approval/readiness, useful search traffic, indexing, reliability and net revenue.
- Raw publishing volume is not a success metric.
- k-health365.com is the confirmed AdSense-approved reference property.

## Current portfolio — authoritative counts
- WordPress ordinary sites: 25 total.
- Newsrooms: 2, operated under separate newsroom rules.
- Blogspot: 33.
- Tistory: 5.
- Naver Blog: 3 registered targets; activation is account/login verification dependent.
- YouTube and SNS are managed separately from the AdSense web-fleet count.

Any older references to WP 24, WP 26/27, Blogger 27, or combined counts are historical and must not be used as the current operating baseline.

## Runtime architecture — current owner directive (2026-11-06)
- VPS, SSH, Linux server runtime, systemd, server-local queues and server-hosted n8n are not approved execution paths. Do not use or restore them.
- Instagram/Threads account authentication and publishing work is performed on the owner's authorized Windows PC through Desktop Commander and PowerShell.
- GitHub is the source/configuration/version-history/rollback repository.
- https://control.korea365.org/ is the GitHub Pages executive dashboard (source: main:/docs/index.html).
- Local-PC jobs require the PC to be powered on, connected and authenticated; do not describe them as 24/7 server execution.
- Other platform-specific automation may use only separately approved, currently verified execution paths; do not infer a VPS dependency.

## Platform rules
### WordPress 25
- AdSense approval/readiness first.
- Protect approved/indexed/high-quality content.
- No mass deletion. Non-protected content may be private/noindex only under the locked cleanup policy.
- Empty categories should be removed; taxonomy kept focused.
- Publication success requires a verified public URL/receipt.

### Newsrooms 2
- Separate newsroom cadence and short breaking-story rules.
- Do not mix newsroom rules into the ordinary WP25 logic.

### Blogspot 33
- Independent articles; no verbatim WP duplication.
- Publication success requires a verified public URL/receipt.

### Tistory 5
- Cloud may prepare/queue content.
- Final browser execution depends on a persistent local login/session.
- Human verification/CAPTCHA/login interruptions must stop automation rather than loop aggressively.

### Naver Blog 3
- Each blog/account requires its own verified identity/login profile.
- Login presence alone is not a publication receipt.
- Human verification or platform restriction must halt automation safely.
- Start with verified account-specific canary tests before scaling.

## n8n migration rule
- Migrate one proven path at a time.
- Per-site/account isolation: one failure must not block other destinations.
- Bounded retries, duplicate prevention, HOLD/dead-letter state and execution receipts are mandatory.
- Do not disable a production path until the n8n replacement has end-to-end evidence and rollback.

## GitHub cleanup rule
- Delete clearly obsolete one-off workflows and obsolete count-based workflows.
- Historical reports may remain as evidence, but must be marked historical and must not drive current automation.
- Ambiguous production-critical workflows are reviewed before deletion.
- Any new workflow must have an owner, scope, cadence/trigger and retirement condition.

## Reporting rule
Never report completion from queue/dispatch/login presence alone.
Completion evidence should include:
- problem found
- change made
- remaining issue
- changed files
- test/publication receipt
- API/cost impact when relevant
- commit SHA
- next action


## Instagram and Threads — Seoul Jisoo / Seoul Chris (2026-11-06)
- Instagram and Threads use the same five designated handles: seoul_topik, english_pick, japanese_pick, seoul_jisoo, seoul_chris.
- Seoul Jisoo and Seoul Chris each target 3 distinct posts per day, randomized within 08:00–23:00 KST, with at least 120 minutes between posts per account.
- Jisoo covers health and broad political/social/economic/sports/entertainment/lifestyle hot issues; health functional foods only when relevant.
- Chris covers K-beauty, skincare, cosmetics and broader popular trends; cosmetics only when relevant.
- Editorial-first: entertaining/useful content is primary; contextual Coupang Partners link only at the end, with disclosure and verified tracking URL. No forced product placement.
- Check Naver search-interest terms and news sources daily. Do not invent search-volume rankings. Separate facts, allegations and opinion in political coverage; verify current sports data.
- Instagram and Threads copy must be platform-native, not verbatim duplicates.
- Publish authorization remains pending until account identity, write scope and a real publication receipt are verified. Schedule policy does not mean live publishing is active.
- Binding policy: config/sns_six_channel_policy.json; detailed guide: docs/SEOUL_JISOO_CHRIS_EDITORIAL_POLICY_2026-11-06.md; dashboard: https://control.korea365.org/.
