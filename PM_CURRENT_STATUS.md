# PM CURRENT STATUS

Updated: 2026-09-26 KST
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

## Runtime architecture
- GitHub: source/configuration/version history/rollback; do not use it as the default heavy video renderer.
- Hostinger VPS: 24/7 runtime and YouTube generation/render/upload worker.
- n8n Community Edition: target orchestration layer for schedules, retries, queues, isolation and receipts.
- Existing Python/systemd components may remain behind n8n when they are proven and cheaper to reuse.
- Control Korea365: executive status/approval surface.
- Local persistent browser automation is required for browser-only destinations such as Tistory/Naver where no stable write API path is available.

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
