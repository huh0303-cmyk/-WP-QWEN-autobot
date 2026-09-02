# Content cadence policy lock

This file is an executable operating contract, not a planning note. Any change to these rules must update the registry, worker logic, and `tests/test_locked_content_contract.py` in the same reviewed commit.

## Locked rules

- Quality threshold: **70/100** across every writing and draft gate.
- Writing engine: **OpenAI `gpt-5-mini` only** for WordPress, both newsrooms, Blogger, and Tistory first drafts and rewrites. Gemini is an independent reviewer only; it is never an automatic writer fallback.
- Blog image engine: Replicate **`bytedance/sdxl-lightning-4step` first**, then one **`black-forest-labs/flux-schnell`** fallback attempt, then text-only. Gemini/OpenAI/stock image fallbacks are disabled.
- WordPress blogs: **25 destinations, exactly one item per destination per KST day** (`daily=1`, `weekly=7`).
- Newsrooms: **2 destinations** (`koreanews365.com`, `theseouljournal.com`), **3–10 public briefs per KST day per newsroom**, driven by timely RSS/primary-source leads. Each brief must contain **700–1,500 visible characters**, retain source attribution, reject duplicate source URLs, and run through the single newsroom owner lock.
- Blogger: **27 destinations, exactly one private draft per destination per KST day**. A matching WordPress source must exist first. Publication remains review-gated.
- Tistory: **5 destinations, exactly one private draft per destination per KST day**. Deterministic `site_id:date` job IDs and a single-owner workflow prevent duplicate enqueue.
- YouTube: **10 channels**, one private production per channel every **2–3 days**. The interval sequence is deterministically randomized and may not collapse into a fixed repeating template; consecutive publication times for a channel must differ. Playlist and knowledge workers share one repository-wide production lock. Public release always requires human action.
- Calendar schedulers use a bounded late polling window so ordinary GitHub Actions delay cannot make a row permanently invisible. Future rows and rows older than the window are never dispatched automatically.

## Ownership and failure behavior

- Claim before external dispatch; keep a durable identity marker on ambiguous network outcomes.
- `cancel-in-progress` is false for production owners: a newer schedule must not kill an active publication.
- A remote side effect is never retried blindly. Reconciliation must search the destination identity marker first.
- Google Sheets is the operating ledger; deterministic schedule/job IDs are the idempotency keys.
