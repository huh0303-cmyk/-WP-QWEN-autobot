# London Project — GitHub Actions Workflow Audit (2026-09-26)

Auditor: Claude (independent QA role per `CLAUDE.md`)
Scope: `.github/workflows/*` (66 files at audit start), dead-path search, n8n readiness, Tistory/Naver local runner risk.
No new paid API, Make.com, or SaaS introduced. This audit reorganizes the existing London Project toward n8n; it does not design a new system.

## 1. Workflow classification (66 files)

Legend: **KEEP** = stays as-is, reusable manual/CI/execution primitive. **REPLACE_BY_N8N** = this workflow's *schedule trigger* should move to the matching n8n master; the workflow itself is kept as the `workflow_dispatch` execution target n8n calls. **DELETE_NOW** = executed this session. **DELETE_AFTER_MIGRATION** = redundant only once its n8n master has an end-to-end verified receipt (per the migration doc's own gate); do not touch before that.

### DELETE_NOW (executed, see §3)
| File | Reason |
|---|---|
| `check-site-groups.yml` | Backing script's own docstring: "One-off read-only check." Question already answered. |
| `aggregate-gsc-public-final.yml` | Hardcodes historical run ID `33284433841` (`gh run download 33284433841`); that run's artifacts are past GitHub's 90-day retention. Can never succeed again. |

### REPLACE_BY_N8N (the only 4 workflows with a native `schedule:` cron — these are exactly what the 10 named masters are supposed to absorb)
| File | Current cron | Target master | Note |
|---|---|---|---|
| `daily-publication-floor.yml` | `13 * * * *` (hourly) | WP25_MASTER / BLOGGER33_MASTER | See §2 risk — the one existing n8n stub (`wp25_master.json`) dispatches this exact workflow on its **own** hourly schedule, on top of this workflow's own hourly cron. If both are ever active at once this is a live double-trigger, not a hypothetical one. |
| `sns-24-hourly.yml` | `17 * * * *` (hourly) | SNS_MASTER | Currently 0/24 SNS slots have verified write connection (per `LONDON_PROJECT_CURRENT_STATE_2026-09-25.md`), so today this is mostly a no-op poll, but the cron itself still runs 24x/day. |
| `tistory-one-daily-dispatcher.yml` | `*/5 * * * *` (every 5 min) | TISTORY5_MASTER | Directly violates the project's own cost policy ("불필요한 5/10/15/20/30분 polling 금지," `LONDON_PROJECT_BLUEPRINT.md` §5). Highest-priority migration target of the four. Does not call any paid API itself (only GitHub's own API), so it is a policy violation, not a paid-API cost leak. |
| `daily-site-traffic.yml` | `7 22 * * *` (07:07 KST) | METRICS_MASTER | Once-daily, read-only. Lowest-risk of the four; fine to migrate last. |

**Do not delete any of these four now** — no evidence any of their jobs has actually moved to the VPS/n8n yet (see §4: n8n readiness is effectively 0/10). Deleting them today would leave WordPress/Blogger/SNS/Tistory/metrics with no scheduling at all.

### KEEP — with defects flagged (not deletions, but need a fix)
| File | Defect |
|---|---|
| `adsense-infrastructure-audit.yml` (→ `scripts/audit_adsense_sites.py`) | Hardcodes its own 26-domain `DOMAINS` list instead of importing `site_registry.ACTIVE_SITES`. It is missing `kskin365.com` (a real active WP site) and mixes the 2 newsrooms into a "WordPress sites" audit, which is what `LONDON_PROJECT_BLUEPRINT.md` §11 explicitly prohibits ("일반 WP와 News를 같은 publisher/scheduler에 결합하는 구조"). Net effect: this audit silently never checks one real site. Fix: import `ACTIVE_SITES` from `scripts/site_registry.py` (the correct, current 27-entry canonical registry) and filter newsrooms out, the same way `submit_all_sitemaps.py` already does correctly. |
| `automation-room-result-collector.yml`, `site-publication-receipts.yml` | Both have a `workflow_run` trigger that lists `"BlogPublish — Single Site (dispatched by A/B scheduler)"` as a source workflow. That workflow no longer exists anywhere in `.github/workflows/` — it was removed at some earlier cleanup and these two were never updated. The reference is silently dead (GitHub just never fires that branch); the other listed source workflows in the same trigger block still exist and still work, so these two files are not fully broken, just partially stale. Fix: drop the dead entry from the `workflow_run.workflows` list. |
| `wordpress-site-logos.yml`, `wordpress-verify.yml` | Titled "WordPress 27" though the canonical regular-WP count is 25 (+2 separate newsrooms = 27 total properties, not 27 WP sites). Confirmed cosmetic only — `verify_wordpress_connections.py` actually reads live rows from `config/automation_hub_sites.json` filtered to `platform == "wordpress"`, not a hardcoded 27. No functional bug, just a misleading title. |
| `submit-all-sitemaps.yml` | Titled "26개 사이트" but correctly imports `ACTIVE_SITES` from `scripts/site_registry.py` (27 entries minus retired = live count). Functionally correct; title is stale. |

### KEEP — reusable manual tools / CI / execution primitives (no defect found)
`a-group-sequential-publish.yml`, `audit-blogger-draft-search-descriptions.yml`, `audit-blogger-image-alt.yml`, `audit-site-kit.yml`, `automation-canary-dispatch.yml`, `automation-hub-bootstrap.yml`, `automation-hub-tests.yml` (CI), `blogger-emergency-title-repair.yml`, `blogger-rewrite.yml`, `blogger-verify.yml`, `ceo-sns-probe.yml`, `check-blogger-accounts.yml`, `coupang-banner-inject.yml`, `daily-network-publish.yml`, `deploy-control-cards.yml`, `deploy-regular-site-menus.yml`, `deploy-to-vps.yml` (CI/CD), `diag-youtube-scope.yml`, `emergency-privacy-lockdown.yml`, `fetch-blogger-blog-ids.yml`, `generate-editorial-image.yml`, `golden-keyword-queue.yml`, `google-metrics-verify.yml`, `gsc-sitemap-diagnosis.yml`, `install-vps-playlist-runtime.yml`, `keyword-evidence-audit.yml`, `khealth-recovery-audit.yml`, `khealth-restore.yml`, `khealth-submit-sitemap.yml`, `n8n-vps-preflight.yml`, `newsrooms-daily-publisher.yml`, `notify-existing-draft.yml`, `platform-publish-v2.yml`, `provision-vps-wp-credentials.yml`, `prune-unindexed-posts.yml`, `publication-health.yml`, `publish-blogger-33-now.yml`, `publish-now.yml`, `reconcile-tistory.yml`, `repair-regular-site-menu.yml`, `restore-youtube-ten-control.yml`, `seouljournal-dashboard-deploy.yml`, `stock-image-preflight.yml`, `tistory-daily-plan.yml`, `topik-longform-weekly.yml`, `topik-quiz-daily.yml`, `verify-blogger-oauth.yml`, `wp-auth-bootstrap.yml`, `wp-category-consolidation-dry-run.yml`, `wp-category-consolidation.yml`, `wp-create-draft.yml`, `wp-emergency-title-repair.yml`, `wp-vps-floor-status.yml`, `youtube-ten-auth-preflight.yml`.

Note on `wp-category-consolidation.yml` / `-dry-run.yml`: these look like a one-off pair at first glance but are fully parameterized by `site_url`/`site_key` and gated behind a typed confirm string — they are the general-purpose per-site tool, still actively relevant to the jobkorea365.com-style category cleanup work. Not one-off; kept.

Note on Blogger publish paths: `blogger-rewrite.yml`, `platform-publish-v2.yml`, `publish-blogger-33-now.yml`, and `daily-publication-floor.yml` are **four separate entry points** that can each cause a Blogger publish today. This is the clearest concrete instance of "중복 scheduler" in the repo. None is provably dead (each takes different inputs — new-article generation, queue-drain, direct-publish-by-trigger-file, and the hourly floor — so they are not simple duplicates of each other), so none is deleted here. Recommendation: once `BLOGGER33_MASTER` exists in n8n, it should own the trigger, calling exactly one of these as its execution step; the other three should be reduced to break-glass manual tools or removed.

### Confirmed clean (no evidence found)
- No Render.com/`onrender.com` residue anywhere in the repo.
- No GitHub-hosted YouTube rendering workflow (matches blueprint §11's explicit prohibition — this rule is currently being followed).
- The "24" naming (`WP24_CATEGORY_MASTER.json`, `WP24_ADSENSE_APPROVAL_POLICY_LOCK.md`) is **not** drift — it correctly means "the 24 WP sites other than the already-approved k-health365.com," matching `LONDON_PROJECT_CURRENT_STATE_2026-09-25.md`.

## 2. Duplicate scheduler — concrete finding

`deploy/n8n/workflows/wp25_master.json` (the one n8n master that actually has a file — see §4) is a schedule-trigger node firing hourly at minute 13, whose only action is to POST to GitHub's API to dispatch `daily-publication-floor.yml` — **the same workflow that already has its own native `13 * * * *` cron.** If this n8n workflow is ever set `"active": true` while `daily-publication-floor.yml`'s own `schedule:` block is still present, WordPress publishing gets double-dispatched every hour. The fix is not "delete one" but sequencing: remove `daily-publication-floor.yml`'s own `schedule:` trigger (keep `workflow_dispatch`) in the same change that activates the n8n workflow. Doing only one side of this is the exact failure mode the migration doc's own "Migration gate" section is meant to prevent.

## 3. DELETE_NOW — executed this session

Deleted and committed (commit `90ad534`):
- `.github/workflows/check-site-groups.yml`
- `.github/workflows/aggregate-gsc-public-final.yml`
- `scripts/check_site_groups.py` (sole backing script, same one-off scope)
- `scripts/aggregate_gsc_public_results.py` (sole backing script, hardcodes the same dead run ID)

Verified before deleting: no other script, workflow, or doc references any of the four paths.

## 4. n8n readiness — actual file/execution evidence

| Master | File exists? | Deployed/active? | Execution evidence |
|---|---|---|---|
| WP25_MASTER | **Yes** — `deploy/n8n/workflows/wp25_master.json` | `"active": false` in the file itself | None. Two-node skeleton only (hourly trigger → one HTTP dispatch call). |
| BLOGGER33_MASTER | No | — | None |
| NEWS2_MASTER | No | — | None |
| TISTORY5_MASTER | No | — | None |
| NAVER3_MASTER | No | — | None |
| YOUTUBE_PLAYLIST5_MASTER | No | — | None |
| YOUTUBE_KNOWLEDGE5_MASTER | No | — | None |
| YOUTUBE_LANGUAGE_MASTER | No | — | None |
| SNS_MASTER | No | — | None |
| METRICS_MASTER | No | — | None |

Supporting infra that does exist: `deploy/n8n/docker-compose.yml` (self-hosted n8n Community, bound to `127.0.0.1:5678`, matches the "no n8n Cloud/Make" cost policy) and `deploy/n8n/n8n.env.example`. `.github/workflows/n8n-vps-preflight.yml` is a `workflow_dispatch`-only SSH diagnostic that would report whether Docker/n8n/node are actually installed on the VPS — its own execution history was not checked in this pass (would require live VPS SSH secrets to run, which this audit did not trigger).

**Bottom line: n8n readiness is 1/10 files, 0/10 deployed, 0/10 executed.** The architecture-lock and migration docs describe the target state accurately; almost none of it is built yet. Any statement elsewhere that n8n masters are "in place" would be a false-completion claim per `CLAUDE.md`'s own audit standard.

## 5. Tistory / Naver local-runner audit

### `scripts/tistory_local_runner.py`
- **Old-before-new risk: confirmed real.** `process_jobs()` selects from `jobs WHERE state IN ('pending','retry') ORDER BY rowid LIMIT ?` — ascending by insertion order. A job that keeps failing is set back to `state='retry'` (same low `rowid`) and therefore keeps winning the `LIMIT` slot ahead of every newer job on every subsequent run. There is no max-attempt cap and no dead-letter/HOLD state in this file — `attempts` is incremented but never gated. This is exactly the "오래된 큐가 새 글보다 먼저 발행" failure mode: one stuck old job can indefinitely starve newer queued posts for that site, silently, with only an `error` string in the local SQLite row as evidence.
- **Login-session separation: not a bug.** All five Tistory properties (`config/tistory_portfolio.json`) are subdomains under what the current-state doc confirms is a single Tistory account (`huh0303`). `--profile-root` defaults to one shared Playwright profile for all five, which is correct for a single-account/multi-blog setup — Naver's requirement for separate per-account profiles (below) does not apply here because Tistory is one account, not five.
- **Repeated-failure handling:** on exception, the job goes to `retry` with the error message stored, and `send_review_email` only fires for `review_ready` results, not failures — so a stuck job fails silently unless someone runs `... status` by hand. No alerting on repeated failure.

### `scripts/naver_blog_local_runner.py`
- **Login-session separation: correct.** `profile_dir = Path(args.profile_root).resolve() / args.site_id` — one persistent profile per account, matching `LONDON_PROJECT_ARCHITECTURE_LOCK_2026-09-26.md`'s explicit requirement ("Naver: use separate persistent profiles per account/blog"). N1/N2/N3 cannot cross-contaminate sessions.
- **Old-before-new risk: low.** Selection is oldest-`ready`-row-first per site, same as Tistory, but there is no in-process retry loop — `if not result.ok: break` stops the whole run on first failure rather than looping on the same row. A failing row can still block that day's later rows in the *same run*, but it cannot accumulate indefinitely across runs the way the Tistory queue can, since there is no persistent local job-state table carrying a `retry` status forward.
- **Windows Scheduled Task / Aside:** no `.xml`/`.ps1` task definition is committed to the repo (expected — that lives on the owner's PC, outside Git). `docs/TISTORY_LOCAL_REGISTRAR.md` documents manual PowerShell invocation only. "Aside" (the local browser tool) appears **only** in `config/LONDON_PROJECT_ARCHITECTURE_LOCK_2026-09-26.md` as a policy statement — there is no code in this repo that invokes or depends on Aside; the actual committed local runners use Playwright, not Aside. If Aside is meant to replace the Playwright runners, that migration hasn't started in code yet either.

## 6. Next actions
See chat summary for the prioritized 5.
