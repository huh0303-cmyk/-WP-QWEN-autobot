# CLAUDE DECISIONS

## 1. Scope: narrow, not a rewrite of the whole London Project

Primary goal is AdSense approval on the 24 not-yet-approved WordPress sites,
under a stability-first constraint. This track does not redesign posting
cadence (already correct) or introduce new infrastructure. Full rationale:
`docs/LONDON_PROJECT_CLAUDE_CHARTER.md`.

## 2. Read existing code before writing new code

Mid-session correction: an early draft overwrote
`scripts/ensure_required_pages.py` without checking whether it already
existed. It did, and was more mature (27-site coverage, 4 page types,
language-aware content, slug+title-length double-matching to avoid false
positives from a documented past incident, per-site exception isolation
from another documented past incident). Reverted via `git checkout HEAD --`
before committing. New standing rule: check `git log --oneline -5 -- <path>`
before creating a file whose purpose might already be covered.

## 3. Write actions to live sites stay manual-trigger until reviewed

`.github/workflows/ensure-required-pages.yml` is `workflow_dispatch` only,
not scheduled — even though the underlying script is idempotent and
per-site-isolated. Automatic scheduling is a decision for after real run
results are reviewed (now available — see STATUS.md).

## 4. Fixed a factual bug rather than guessing

`scripts/audit_adsense_sites.py`'s `APPROVED_GROUP` incorrectly listed 7
sites as approved. Owner directly confirmed only k-health365.com is
approved (2026-09-26). Corrected in code, not left as an assumption.

## 5. Cross-track isolation

Per owner directive ("다 별도야.. 런던프로젝트클로드는 온전히 너꺼"): this
track does not merge, defer to, or overwrite LONDON_PROJECT_GPT or
LONDON_PROJECT_GEMINI's files or conclusions. Discovered via `git log` that
GPT's track pushed concurrently to the same repo during this session — no
conflict occurred (clean rebases both times), but the file-ownership split
in `config/LONDON_PROJECT_CLAUDE_OWNER_LOCK_2026-09-26.md` exists
specifically to keep it that way.

## 6. Real execution over talk

This session obtained a working `GH_TOKEN` in its shell environment and
used the GitHub REST API directly (`workflow dispatch` → poll `runs` →
download `artifacts`) to actually execute both AdSense workflows rather
than only writing code and describing what *should* happen. Evidence is the
run IDs and downloaded artifacts recorded in
`docs/LONDON_PROJECT_CLAUDE_STATE.md`.
