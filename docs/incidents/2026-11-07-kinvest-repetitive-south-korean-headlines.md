# Korea Invest 365 — Repetitive “South Korean” Headline Incident

- Date detected: 2026-11-07 (KST)
- Affected destination: https://koreainvest365.blogspot.com/
- Site key: `kinvest365`
- Symptom: multiple recent Blogger headlines begin with the same generic phrase, “South Korean”. The phrase also appears repeatedly in opening paragraphs.

## Root cause

Code review of `scripts/publish_blogger_33_now.py` found that the English Blogger prompt required varied headline structures and prohibited generic gerund openers, but did not prohibit generic country-adjective openers such as “South Korean” or “Korean”. The post-generation quality gate called `title_cliches()` but had no site-specific check for this pattern. The model could therefore repeatedly choose the same country-first construction and the pipeline would accept it.

The inspected prompt did not establish that the keyword file itself mechanically prepended “South Korean”; this incident is attributed to an underspecified generation prompt plus a missing deterministic title gate, not to an unproven keyword-file mutation.

## Fix committed

1. Add `automation_hub/kinvest_title_guard.py`, rejecting English titles beginning with “South Korean” or “Korean” for `kinvest365` only.
2. Add a site-specific prompt instruction: lead with the actual market instrument, company, event, data point, or investor decision; mention Korea later only when context requires it.
3. Run the guard before normal title checks. A rejection raises a retriable quality-gate error, so the title is regenerated rather than published unchanged.
4. Add unit tests for both rejected prefixes, a valid subject-first title, and case/whitespace variants.

## Prevention / operating controls

- Keep this rule scoped to `kinvest365`; do not globally ban “Korean” where it is necessary for other sites.
- Preserve recent-title context and existing repetition checks.
- Regenerate rejected titles; do not mechanically strip the prefix, which can break grammar.
- Run the unit tests before any workflow execution.
- Do not run a publish workflow as part of this fix. Existing public posts are not edited automatically; retrospective corrections require a separate reviewed batch.

## Verification status

- Code and policy changes: committed.
- Unit tests: added; execution remains pending.
- Live publishing: not run.
- Existing public titles: not modified.
