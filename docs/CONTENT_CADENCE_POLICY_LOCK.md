# Content cadence policy lock

This file is an executable operating contract, not a planning note. Any change to these rules must update the registry, worker logic, London Project policy, and tests in the same reviewed commit.

## Locked rules

- Quality threshold: **70/100** across every writing and draft gate.
- Writing engine: use the active approved writing-engine policy in `config/content_writing_policy.json`; do not invent an unapproved provider fallback.
- Blog/news image order: relevant copyright-safe **Pexels first, Pixabay second**, then approved Replicate **`bytedance/sdxl-lightning-4step`**, then **`black-forest-labs/flux-schnell`**, then text-only/no-image. Newsroom photos from other publishers may not be copied without a compatible license or permission.
- WordPress blogs: **25 destinations, exactly one item per destination per KST day** (`daily=1`, `weekly=7`). Planned timing is randomized and must avoid exact-hour/repeating machine-like slots.
- Newsrooms: **2 destinations** (`koreanews365.com`, `theseouljournal.com`), driven by verified RSS/breaking-news leads. Operating target is **3–10 verified stories per newsroom per KST day, hard maximum 10**. If fewer than three suitable verified leads exist, publish fewer rather than invent filler. No fixed publication slots. Each brief must retain source attribution, reject duplicate source URLs and pass the single newsroom owner lock.
- Blogger: the enabled Blogger portfolio prepares **one private review-gated draft per destination per KST day**. A paired WordPress source must exist first where the site is paired. Publication remains review-gated; cross-platform copy/paste is prohibited.
- Tistory: the five enabled properties follow the current `config/tistory_portfolio.json` runtime contract and remain review-gated. Any cadence change must update that registry and its tests together.
- YouTube Playlist + Knowledge: **10 channels total**, one private production per channel every **2–3 days**. The interval sequence is randomized, consecutive publication times for a channel must differ, and channel slots must not collide. Playlist and knowledge workers share one repository-wide production lock. Public release always requires human action.
- 10-Language Survival: **10 languages × 50 lessons**. Canonical progress is through Lesson 2; next is Lesson 3. Each language gets one new private lesson every **2–3 days**, with staggered slots across languages. Public release requires Chairman review and approval.
- Calendar schedulers use bounded polling windows so ordinary workflow delay cannot make a valid row permanently invisible. Future rows and stale rows outside the window are never dispatched automatically.
- London Project activity ledger: every task must have a task_id and preserve request, assignment, attempts, failure/success, retries, failover, evidence, human approval and audit result. Failed work is never silently discarded.

## Ownership and failure behavior

- Claim before external dispatch; keep a durable identity marker on ambiguous network outcomes.
- `cancel-in-progress` is false for production owners: a newer schedule must not kill an active publication.
- A remote side effect is never retried blindly. Reconciliation must search the destination identity marker first.
- Durable schedule/job IDs are idempotency keys.
- The Deterministic Audit Engine alone may create `VERIFIED_COMPLETE`.
