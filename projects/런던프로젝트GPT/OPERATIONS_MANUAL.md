# 런던프로젝트GPT — Operations Manual

## Daily operator view
Control Korea365 should make these four numbers dominant:

1. previous-day daily visitors (delta)
2. cumulative visitors (delta)
3. total public posts (delta)
4. Google indexed public posts (delta)

Ranking:
- previous-day daily visitors descending
- explicit 1위, 2위, 3위...
- unknown values at bottom
- metric is for trend management; perfect absolute visitor accuracy is not required.

## Normal daily operation
1. n8n schedules due jobs.
2. due registry is checked.
3. worker executes one isolated destination.
4. receipt is verified.
5. Control Korea365 updates state.
6. failed destinations move to retry/HOLD without stopping fleet.

## Naver/Tistory
- n8n queues work.
- LondonLocalAgent executes only while PC/browser session is available.
- if login challenge appears, HOLD.
- user login is preserved locally, not in GitHub.

## Maintenance
Weekly:
- dead-letter review
- stale queue review
- disk usage
- n8n execution failures
- YouTube render queue
- obsolete GitHub workflow candidates

Monthly:
- VPS cost/capacity review
- backup restore sanity check
- remove superseded schedulers
- validate registry counts and channel IDs

## No-cost operating rule
Prefer:
- existing VPS
- n8n Community
- Python
- systemd
- GitHub
- free/open-source tooling
No new paid service without explicit owner approval.
