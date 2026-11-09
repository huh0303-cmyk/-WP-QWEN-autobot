# WordPress red-site publication recovery (2026-11-10)

Task ID: `wp-red-sites-recovery-20261110`

## Scope and cause

The red rows reviewed on the operations dashboard were koreainsurance365.com (3 days stale), studyinkorea365.com (3 days), and jobinkorea365.com (9 days). The scheduled `wordpress-25-twice-daily` legacy publisher is `disabled_manually`, consistent with the canonical working agreement that keeps fleet publishing disabled. Therefore there were no new scheduled runs after Nov 6. The fleet schedule was not re-enabled.

Two distinct publisher failures were also present in prior run evidence:

- Nov 6 run `42150549964`: koreainsurance365.com REST `/wp-json/wp/v2/types/post` timed out on retries and was marked unreachable.
- Nov 6 run `42262070102`: `NameError: strip_title_duplicate_lead_image is not defined` in the common publisher path. Main already contains the import repair in commit `b26d4f258c2cf96624af6aa4992cad182c7cb7d0`.

## Immediate publication receipts

- koreainsurance365.com: isolated run `42660045117` succeeded. WordPress REST returned post `4620`, dated `2026-11-10T02:05:33`, title “Mandatory NHIS Foreign Resident Registration Steps and Compliance Requirements”, URL https://koreainsurance365.com/mandatory-nhis-foreign-resident-registration-steps-and-compliance-requirements/ . Public page HTTP 200.
- studyinkorea365.com: isolated run `42660053204` succeeded. Post `4366`, dated `2026-11-10T02:04:34`, title “Global Talent Fair Korea 2026 Connects Foreign Graduates to Local Employment Opportunities and Visa Pathways”, URL https://studyinkorea365.com/global-talent-fair-korea-2026-connects-foreign-graduates-to-local-employment-opportunities-and-visa-pathways/ . Public page HTTP 200.
- jobinkorea365.com: run `42660058560` failed in all three retries because live topic selection returned no in-scope keyword (`fallback=true`) and the editorial safety gate raised `ValueError: No in-scope keyword available; preserve job instead of writing an unrelated article`. No new article was published; latest REST post remained ID `1214`, dated `2026-11-01T11:07:40`.

## Isolated-workflow input defect found during recovery

The active manual workflow is named `WordPress 25 — immediate isolated publish`. Its `workflow_dispatch` contract does not declare `force_keyword`, although its reusable `workflow_call` contract does. GitHub CLI accepted the unknown dispatch field without error; run `42661770122` therefore did not receive the requested override. A second run `42661956114` used only declared inputs, but the matrix still queued jobs for every configured site and `target_site_url` is applied only as a step condition, not a matrix filter. That run was canceled before its target reached the publication step. PowerShell/GitHub Actions verification: the failed attempt had 0 successful publication steps on non-target sites; the canceled run's jobinkorea target publication step was skipped and 0 successful non-target publication steps were present. Both runs are canceled. Do not use this manual workflow for isolated one-site publication until the contract is corrected and the matrix is proven to contain only the requested site.

## Recurrence prevention and remaining action

1. Keep the legacy fleet scheduler disabled, per `docs/PROJECT_WORKING_AGREEMENT.md`; never solve a red counter by enabling all 25 sites.
2. Add a regression assertion (this branch) that `wp_post` imports the duplicate-lead-image guard before calling it; this protects the already merged `NameError` correction.
3. Before dispatching a one-site job, require the workflow to reject unknown inputs and build its matrix from the exact canonical site URL. Add an explicit dispatch keyword input if an override is needed. Prove a no-op simulation that lists only the requested matrix job before enabling public publish.
4. For jobinkorea365.com, obtain/select an in-scope keyword and run through the corrected isolated workflow; do not bypass the relevance gate.

## Verification in this session

- `python -m unittest tests.test_duplicate_lead_image_guard -v`: 10 tests passed.
- `git diff --check`: passed.
- Public WordPress REST readback and HTTP 200 page readback verified for the two published posts.
- No credentials, tokens, or secret values are included in this report.
