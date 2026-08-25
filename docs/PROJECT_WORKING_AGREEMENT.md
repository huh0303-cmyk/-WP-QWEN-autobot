# WP Network Project Working Agreement

This file records the operating agreement for the 27-site WordPress rebuild.
Decisions must not exist only in chat.

## GitHub is the durable record

1. Every approved technical, editorial, SEO, source-rights, cadence, lifecycle,
   or site-scope decision is committed to the active feature branch during the
   same work session.
2. Each coherent change receives a descriptive commit message.
3. The active pull request body or conversation records the reason, safety
   constraints, verification result, and remaining work.
4. No claim of completion is made until the GitHub file/commit is fetched back
   and verified.
5. WordPress production mutations are recorded separately with a timestamped
   manifest or receipt artifact. A code commit does not imply that a live-site
   operation ran.
6. Secrets, credentials, personal tokens, and private source agreements are
   never committed. Only secret names and policy state are stored.

## Continuity and work sizing

The assistant cannot inspect or guarantee the product's exact remaining message,
token, or daily usage quota. Therefore continuity is handled by checkpoints:

1. Before a large operation, split work into reviewable phases that can each be
   completed and committed independently.
2. State the phase boundary before beginning if the requested scope is unlikely
   to fit safely in one work session.
3. Commit and push after every material phase; do not accumulate a large set of
   unpushed changes.
4. Keep the legacy auto-publisher locked while rebuild work is incomplete.
5. If interruption occurs, resume from the latest GitHub commit and PR record,
   not from chat memory.
6. Never start a destructive live-site batch unless its audit, manifest,
   rollback method, and expected runtime have already been recorded.
7. For operations across all sites, prove the workflow on k-health365.com first,
   inspect results, then expand in bounded batches.

## Current durable decisions

- k-health365.com is the first recovery and validation site.
- kskin365.com is active again and is included in the 27-site registry, visitor counter rollout, audits, and daily blog scheduler.
- Legacy automatic WordPress publishing remains disabled.
- The rebuilt flow is audit -> draft -> quality gate -> human approval -> publish.
- All site personas are neutral editorial desks with one explicit topic scope.
- Images must be relevant; relevance-check failure is a rejection, not a pass.
- Sources requiring written commercial permission or a separate syndication
  agreement are excluded entirely. News automation uses only recorded CC BY,
  eligible public-domain, and primary-government feeds with item-level checks.
- Chosun, Yonhap News TV, CNN, The New York Times, BBC, Reuters, and AP are
  blocked from automatic ingestion unless this policy is changed by a reviewed PR.
- Koreanews365 and The Seoul Journal start at 3-5 total articles per site per
  day, not 3-5 per category, with at least two original articles per day and at
  least 30 percent original articles per week.
