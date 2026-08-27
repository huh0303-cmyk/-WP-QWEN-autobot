# Publishing Deduplication Design

## Blogger ownership key

The canonical identity is:

`platform + destination site_id + canonical WordPress source URL + content version`

`automation_hub/content_identity.py` normalizes URL scheme/host, removes fragments and
normalizes trailing slashes. It produces a stable 20-character SHA-256-derived
`content_id`. Blogger queue job IDs are now `blogger-<content_id>`.

The destination is part of the identity intentionally: two distinct Blogger properties
may adapt the same source topic, but one Blogger property may not receive it twice.

## Two gates

1. Before Gemini or Replicate calls, `queue_blogger_rewrite.py` selects only a WordPress
   source without an active row for that Blogger destination.
2. Immediately before queue append, the script re-reads the Sheet and blocks a race.

The queue publisher independently checks for an earlier ready row or a
processing/drafted/published row with the same target/source. A duplicate row is marked
`duplicate_blocked` and no Blogger API call is made.

## Crash safety

Before calling Blogger, the selected row becomes `processing`. If the worker crashes
after creating a remote draft, the row remains reviewable instead of being automatically
retried into a second draft. Recovery of `processing` rows must be manual until the
remote draft ID can be reconciled safely.

## Retry policy

`failed_quality` does not permanently own a source, so a later corrected generation may
retry. Active ownership statuses are `ready`, `processing`, `drafted`, `published`, and
`review_ready`.
