# Tistory random three-daily operation — 2026-10-01

## Owner decision

- The five existing Tistory properties remain eligible.
- The network publishes exactly three posts per KST day, not three posts per site.
- Each selected site receives at most one post that day.
- Site choice and publishing minutes are randomized daily.

## Execution contract

1. The dispatcher chooses three distinct enabled sites with operating-system randomness.
2. It assigns non-round minutes between 08:10 and 22:50 KST, at least 90 minutes apart.
3. The complete selection is written to `data/tistory-slots/YYYY-MM-DD/selection.json` before any article workflow is dispatched.
4. Every retry reads that saved selection, so a restart cannot add a fourth site.
5. A site/day receipt is reserved before dispatch. An ambiguous dispatch is not blindly repeated.
6. Topics still pass source, freshness, duplicate, quality, and local logged-in publication verification; randomization does not bypass those gates.

Canonical configuration: `config/tistory_portfolio.json`.

## Verification

- JSON configuration validation: passed.
- Targeted Tistory, Naver, and multi-platform tests: 22 passed.
- Locked Tistory cadence contract test: passed.
- Local Tistory registrar queue at the time of change: empty; no live post was claimed from this configuration change alone.

## Live-operation state

- The GitHub dispatcher runs an hourly lightweight due check at minute 07.
- Manual bootstrap run `36742839334` completed successfully after deployment: `https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions/runs/36742839334`.
- The persisted 2026-10-01 KST selection is:
  - `tistory_ktrip365` at 11:48 KST
  - `tistory_insurance_lab` at 13:43 KST
  - `tistory_life365` at 21:38 KST
- Selection receipt: `data/tistory-slots/2026-10-01/selection.json`, remote commit `21f9e818`.
- At 01:15 KST all three times were still in the future, so the bootstrap run correctly saved the selection without prematurely dispatching article generation.
- The current local Tistory registrar has no queued job. Public URLs will be recorded only after the remote workflow generates, queues, and the logged-in local registrar verifies each post.
- No password, token, or private credential is stored in this document or the repository.
