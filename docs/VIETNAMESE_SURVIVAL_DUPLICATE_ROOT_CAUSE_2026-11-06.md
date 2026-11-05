# Vietnamese Survival Shorts duplicate incident — 2026-11-06

## Verified channel and live examples
- Channel: Vietnamese Survival / @SIS_VietnameseSurvival
- Exact channel ID: `UCRZ0uc_bxKDMwz3noBBi9KQ`
- YouTube Studio inspection on 2026-11-06 showed the same beginner noun lesson twice:
  - 2026-10-12: `sách (sách) • điện thoại (điện thoại) | book • phone #Shorts`
  - 2026-10-26: the same `book • phone` lesson under a different video ID.
- Other visible older noun-pair lessons included sun/moon and water/coffee. The user has already removed some videos; this incident work does not delete or change any existing video.

## Root cause
The old builder had a date-driven fallback selector. It assembled a fixed cycle from the catalog and returned `ordered[release_index % len(ordered)]`. That design necessarily repeated content when the cycle wrapped. Earlier, the noun subset was also selected disproportionately, producing repeated beginner noun lessons such as book/phone, sun/moon, and water/coffee. A newer live-history selector and adjective-only daily workflow had been added, but the builder still retained the unsafe date-cycle fallback for direct/manual invocations. That left two different selection paths with different guarantees.

## Permanent safeguards committed
1. `scripts/survival_adjective_short.py`: generation now fails closed unless an explicit `--pair-id` is supplied by the live-history selector. Date-based modulo cycling is removed. Retired noun lessons are rejected even if explicitly requested.
2. `scripts/select_unique_survival_pair.py`: extracted per-video history matching into `pair_is_used`. Each uploaded video's title, description, and tags stay grouped together; a pair is marked used when its stable pair ID or both localized words occur in the same video metadata. Full uploads-playlist pagination remains required across all ten language channels.
3. `scripts/publish_survival_adjective_shorts.py`: the existing final pre-upload guard remains in place and scans the complete channel uploads playlist, rejecting repeated title, semantic content key, pair ID, or localized word pair. It fails closed before `videos.insert`.
4. `tests/test_survival_adjective_short.py`: regression tests cover missing pair ID, retired noun rejection, Vietnamese legacy book/phone metadata, stable pair-ID matching, and preventing false matches assembled from two different videos.
5. `.github/workflows/github-only-youtube-worker-tests.yml`: selector and regression test paths are included in the test workflow.

## Operating rules
- The ten-language Shorts workflow must select from the live full upload histories before rendering.
- The same lesson must pass the duplicate check again immediately before upload.
- Do not recycle a lesson merely because a calendar cycle wrapped.
- If the history scan or channel identity check fails, stop the batch; do not bypass the check or silently use a date-based fallback.
- Keep the existing CEFR B1-B2 curriculum; noun drills are retired from this series.
- Do not delete, privatize, or replace old videos as part of this prevention patch. Cleanup requires a separate evidence-based review and the owner's direction.

## Validation status
- GitHub source changes are committed to the repository's default branch.
- Automated regression execution still needs a successful GitHub Actions run after these commits. A commit alone is not a test-pass receipt.
- The YouTube Studio page is evidence of the duplicate examples; it is not evidence that the newly committed workflow has already run.
