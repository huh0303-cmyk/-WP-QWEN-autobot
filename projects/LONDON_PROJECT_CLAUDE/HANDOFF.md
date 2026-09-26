# CLAUDE HANDOFF

If Claude's session/quota ends, the next Claude session should:

1. Read `STATUS.md` and `DECISIONS.md` in this folder first (short summary),
   then `docs/LONDON_PROJECT_CLAUDE_STATE.md` (full chronological log with
   exact evidence, run IDs, and site-by-site tables).
2. Read `docs/LONDON_PROJECT_CLAUDE_CHARTER.md` for scope/principles and
   `config/LONDON_PROJECT_CLAUDE_OWNER_LOCK_2026-09-26.md` for the file
   ownership boundary vs. the GPT/Gemini tracks.
3. Do not re-run the two AdSense workflows blindly — real results already
   exist (run 36233819256, run 36233910201). Instead:
   - Retry `ensure-required-pages.yml` for the 9 sites that hit a suspected
     WAF/rate-limit block (exact list in STATE.md "2026-09-26 (4차)"),
     ideally after adding a longer per-site delay or a single-site input
     parameter to the script so the retry doesn't repeat the same block.
   - For the 12 sites confirmed to already have all 4 required pages,
     required-pages is a closed line of investigation — look elsewhere
     (content quality, site age, traffic, manual review notes) for the
     actual AdSense blocker.
4. Do not assume LONDON_PROJECT_GPT or LONDON_PROJECT_GEMINI's conclusions
   are correct — this track is independently responsible for its own
   results per the owner's explicit instruction. Re-verify anything
   material before relying on it.
5. Before creating any new script/workflow, check `git log --oneline -5 --
   <path>` — this track already made and corrected that mistake once this
   session (see DECISIONS.md item 2).
6. Record every material step in `docs/LONDON_PROJECT_CLAUDE_STATE.md`
   (append new dated section at the top) and commit + push before ending.
