# PM PREWORK AUDIT — 2026-08-27

Status: VERIFIED FINDINGS BEFORE WORK/CODEX
Authority: MASTER_MONETIZATION_STRATEGY_2026.md
Purpose: give Codex concrete defects to fix first, not just a generic audit request.

## Priority 0 — Newsroom publishing bug (HIGH)
Latest scheduled run of `newsrooms-daily-publisher.yml` failed in the publish step for `koreanews365.com`.

Observed sequence from GitHub Actions log:
- source draft length: 1661 chars
- regeneration attempt 2 SEO: 26
- length correction: 1661 -> 2289
- HTML-preserving cap correction: 1542
- final hard gate requires >=1750, therefore publish skipped and workflow failed

Interpretation:
The generator did produce enough text after correction, but the later HTML-preserving length cap reduced the article below the newsroom minimum. This is a deterministic post-processing conflict, not primarily an RSS-source failure.

Codex action:
1. locate newsroom length-normalization/post-processing functions in `scripts/autopost_mega.py` or called helpers;
2. make min/max constraints internally consistent;
3. preserve valid HTML while guaranteeing final visible-text length remains inside the newsroom target range;
4. add a regression test reproducing 1661 -> correction -> final >= minimum;
5. test ONE private/draft newsroom item only before production scheduling resumes.

Do not lower quality gates simply to make the workflow green without checking policy.

## Priority 1 — Situation room YouTube registry is stale (HIGH)
`config/youtube_channels.json` is the current 10-channel automated registry (5 playlist + 5 knowledge), but `scripts/situation_room_daily.py` still hard-codes a much larger historical channel list.

Stale entries still visible in the situation-room code include historical/retired channel families such as:
- SCIENCE_FACTS_TIMES
- CLASSICAL_TIMES
- MYTH_LEGEND_TIMES
- AMERICAN_ARCHIVE_TIMES
- CLASSIC_READS_TIMES
and other legacy mappings.

Risk:
- wrong executive dashboard numbers;
- confusion between active and retired channels;
- unnecessary YouTube API calls;
- channel-ID/name drift after historical brand-account reassignments.

Codex action:
- remove hard-coded duplicate registry from the situation room;
- load active YouTube channels from the canonical registry (`config/youtube_channels.json` via `automation_hub/youtube_registry.py`) wherever possible;
- keep TOPIK/language/health channels in a clearly separate canonical registry if they are intentionally outside the 10-channel scheduler;
- add validation that duplicate channel IDs and retired channel keys cannot enter the executive report silently.

## Priority 2 — Site-count / source-of-truth mismatch (HIGH)
Verified current code state:
- `config/automation_hub_sites.json` contains 17 A-group WordPress blogs + 8 B-group WordPress blogs = 25 ordinary WP blogs.
- It then contains the 2 newsroom WordPress properties separately, for 27 WordPress destinations in the active registry.
- `scripts/daily_site_traffic.py` also hard-codes 27 URLs and the Sheet tab is named `27개사이트_트래픽`.

Business/PM state reported by the owner uses the portfolio concept `WP 26 + newsrooms 2`.

Therefore one ordinary WordPress property is either:
1. missing from the active registry; or
2. counted in the owner's portfolio but intentionally not active; or
3. a historical count that has not yet been reconciled.

Codex action:
- do NOT add/delete a site by guess;
- compare MASTER/PM documents, automation registry, scheduler config, WordPress secret references and live portfolio records;
- identify the exact missing/extra property and report it before changing counts;
- after confirmation, make one canonical site registry feed traffic, publishing and dashboard code instead of maintaining separate hard-coded URL lists.

## Priority 3 — KSkin restored status conflicts with stale code metadata (MEDIUM/HIGH)
`config/automation_hub_sites.json` currently treats `kskin365.com` as an enabled A-group WordPress site with a live skincare persona and affiliate profile.

But `scripts/autopost_mega.py` still contains stale author metadata for `kskin365.com` using:
- name: `Retired Site`
- bio beginning `Retired Site...`

This conflicts with the restored/active registry state and can leak an obviously wrong byline or site identity into published content.

Codex action:
- remove the stale retired-site author metadata for KSkin;
- source author/site identity from the canonical registry/profile instead of maintaining a divergent hard-coded identity table where feasible;
- add a validation test that enabled sites cannot carry a `Retired Site` author/persona marker.

## Priority 4 — Blogger has two active processing paths (DUPLICATE-SUSPECT)
Path A:
- `.github/workflows/blogger-daily-scheduler-v2.yml`
- every 20 minutes (`8,28,48 * * * *`)
- `scripts/blogger_daily_scheduler.py`
- dispatches `blogger-rewrite.yml`
- one Gemini Blogger draft per connected site/day; `publish_now=false`.

Path B:
- `.github/workflows/platform-publish-v2.yml`
- every hour at :17
- `scripts/process_platform_queue.py`
- processes `자동화_발행대기` Blogger rows from Google Sheet;
- Blogger is forced to draft mode.

These are not identical implementations, but they can target the same Blogger property if the same content/job enters both systems.

Codex action:
- define one canonical ownership rule for Blogger job creation;
- use stable `content_id/source_id` so the scheduler path and queue path cannot create two drafts for the same content intent;
- do not simply delete either workflow until queue ownership is mapped.

## Priority 5 — WordPress publish/draft semantics require verification (HIGH until proven)
`daily-network-publish.yml` sets:
- `AI_TEXT_PROVIDER=openai`
- `OPENAI_IMAGE_ENABLED=false`
- `GEMINI_IMAGE_GENERATION_ENABLED=false`
- `REPLICATE_API_TOKEN` present
but also sets `WP_AUTOPUBLISH_ENABLED=true`.

This may be intentional for normal WP/news publishing, but the MASTER also requires draft/private/review-first for automated new content unless a specifically approved production path exists.

Codex action:
- trace exactly what `WP_AUTOPUBLISH_ENABLED=true` does in `autopost_current.py/autopost_mega.py`;
- separate newsroom production policy from ordinary WP review policy;
- document which workflows are authorized to publish directly and which must draft/private.

Do not flip this variable globally without tracing downstream behavior.

## Priority 6 — Current `indexed` dashboard value is sitemap aggregate, not exact URL Inspection count (HIGH for KPI accuracy)
`scripts/daily_site_traffic.py` labels a field `indexed`, but its `get_index_coverage()` implementation reads Search Console sitemap data and sums the sitemap `contents[].indexed/submitted` fields.

This is useful as a sitemap-reported index metric, but it is not the same as an exact per-URL URL Inspection census of all published posts.

Risk:
- executive dashboard may present a sitemap aggregate as if it were an exact total indexed-post count;
- duplicates/multiple sitemap types or sitemap coverage differences can distort comparisons;
- owner may make publishing/AdSense decisions from a metric whose meaning is unclear.

Codex action:
- rename/document the existing metric accurately (for example `sitemap_indexed` / `sitemap_submitted`);
- retain it if useful;
- design a separate sampled or batched URL Inspection audit for exact/verified post-level status within Google API quotas;
- never fabricate a single `total indexed` number if the API method cannot support that meaning;
- expose metric source/method in the Sheet.

## Priority 7 — Workflow cleanup candidates (LOW/MEDIUM)
### `curio-scheduler.yml`
Already comments that automatic scheduling was consolidated into `youtube-control-scheduler.yml`; it is currently manual-only. Classify MANUAL-ONLY, not active scheduler.

### `daily_multilang_quiz.yml`
Workflow is manual-only (`workflow_dispatch`) but still contains a `if: github.event_name == 'schedule'` random-delay step. This is dead conditional code and should be removed or documented.

### `topik-quiz-daily.yml`
Despite the filename, it is review-generation only and does not auto-publish. This is currently account-safe; classify MANUAL-ONLY/REVIEW-GENERATOR.

### `health-clinic-daily.yml`
Automatic schedule is already intentionally stopped pending cost/Drive stability. Classify MANUAL-ONLY and keep that safeguard.

## Priority 8 — Measurement architecture already exists but needs canonicalization
Verified workflows:
- `daily-site-traffic.yml` runs daily before situation room and writes site/traffic/index-related result data;
- `situation-room-daily.yml` runs later and combines site + YouTube + SNS into Sheet/email/Kakao;
- `gsc-post-index-audit.yml` is manual read-only inspection;
- `submit-all-sitemaps.yml` is manual-only.

Codex should improve and consolidate these rather than create a second measurement stack from scratch.

Important PM requirement:
Dashboard must clearly distinguish:
- GSC clicks (Google search visits),
- total visitors/users (GA4 or other valid analytics source if connected),
- footer counters (site-local counter, if retained),
- sitemap-reported indexed/submitted metrics,
- URL Inspection verified index status/count where actually audited.
Never label one metric as another.

## Workflow classification snapshot

### ACTIVE / scheduled
- `publish-scheduler.yml` — WP A/B dispatch controller, hourly :37, max one dispatch
- `daily-network-publish.yml` — dispatched single WP site publisher
- `blogger-daily-scheduler-v2.yml` — Blogger draft scheduler
- `platform-publish-v2.yml` — queued Blogger processor (duplicate-suspect with above)
- `youtube-control-scheduler.yml` — canonical 10-channel YouTube scheduler
- `daily-site-traffic.yml` — daily measurement collector
- `situation-room-daily.yml` — daily executive report
- `newsrooms-daily-publisher.yml` — active, but currently failing due to verified length-processing bug

### MANUAL-ONLY / review / maintenance
- `curio-scheduler.yml`
- `curio-longform-daily.yml` (downstream dispatched/manual generation)
- `generate-youtube-video.yml`
- `refresh-playlist-thumbnails.yml`
- `health-clinic-daily.yml`
- `topik-quiz-daily.yml`
- `daily_multilang_quiz.yml`
- `gsc-post-index-audit.yml`
- `submit-all-sitemaps.yml`
- `prune-unindexed-posts.yml` (destructive; explicit confirmation required)
- `wp-create-draft.yml`

### DUPLICATE-SUSPECT
- Blogger scheduler path vs Sheet platform queue path.

## Cost observations
- WP active workflow disables OpenAI/Gemini image generation and carries Replicate token, consistent with current image policy at workflow level.
- YouTube scheduler disables legacy paid image generation flags.
- Health Clinic auto-schedule is stopped, reducing cost risk.
- Remaining cost risk is mainly duplicate content-generation paths and retries, not an obvious active legacy image workflow in the inspected files.

## Codex first-fix order
1. Fix newsroom post-processing length conflict + regression test.
2. Reconcile canonical site count: active registry currently 25 ordinary WP + 2 news vs owner portfolio concept 26 WP + 2 news; identify exact missing/extra property before changing anything.
3. Fix stale KSkin `Retired Site` identity metadata.
4. Canonicalize situation-room YouTube registry and retire stale dashboard entries.
5. Correct index KPI naming/method and separate sitemap aggregate from URL Inspection evidence.
6. Resolve Blogger duplicate ownership with content/job dedup key.
7. Trace and document WP direct-publish vs draft/private semantics.
8. Clean dead workflow conditionals/names/comments without changing business behavior.
9. Continue full repository normalization audit and measurement work from `CODEX_EXECUTION_QUEUE_2026-08-27.md`.

Do not perform broad production runs while fixing these items.
