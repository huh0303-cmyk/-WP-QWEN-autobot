# Coupang Partners Fleet Rollout — 2026-10-31

Status: BLOCKED BEFORE CONTENT WRITES — inventory/spec committed; no posts changed by this task.
Owner: Chairman
Canonical repo: `huh0303-cmyk/-WP-QWEN-autobot`

## Request
1. Rank the 25 general WordPress sites by verified visitors for the previous Korea Standard Time (KST) calendar day, descending.
2. Process each site's latest 100 published posts (up to 2,500 posts total) for relevant Coupang Partners product placement.
3. Keep this automation in London Project/GitHub and make scheduled work independent of the user's PC.
4. Record every site/post outcome and verify actual public URLs.

## Canonical site inventory
Read `scripts/site_registry.py`. It currently has 27 WordPress destinations, including two newsroom destinations (`koreanews365.com`, `theseouljournal.com`). For this request, target the 25 general sites only; exclude those two newsroom sites unless the owner explicitly changes scope.

## Ranking contract
- Source: each site's authoritative visitor counter, documented in `docs/KOREA365_PM_LOCK_2026-09-29.md` as `/wp-json/site-stats/v1/visitors`.
- Rank using the confirmed previous-KST-day visitor count, descending.
- Do not substitute total visitors, GSC clicks/impressions, estimates, stale snapshots, or zero for missing data.
- If a site's yesterday count is missing or stale, leave it unranked and log the connector error; do not guess.
- Persist timestamp, metric value, source URL, freshness, and rank in the run receipt.

## Per-post selection contract
- For each ranked general site, fetch up to the 100 most recently published posts, newest first. Do not change publication dates, statuses, titles, slugs, categories, or existing body text except adding a validated product module.
- Do not publish drafts/private posts or change any post's status.
- Skip a post when a suitable product cannot be established; report it as `SKIPPED_NO_RELEVANT_PRODUCT`.
- Do not inject the same generic product into unrelated posts. Product choice must match the post topic and buying intent.
- Keep the site's existing content intact. Add modules idempotently; re-runs must not duplicate affiliate modules.
- Include the Coupang Partners disclosure in Korean where appropriate, preserve required `nofollow/sponsored` link attributes, and use only product image assets that the affiliate program permits.
- Never invent product IDs, affiliate short links, product images, prices, sales rankings, or conversion data.
- Do not claim a product is a best-seller unless a verifiable source supports that claim.
- Keep medical/health content informational; no disease-cure claims or unsupported health claims.

## Required inputs / preflight blockers
Current WPVibe inventory reports only three connected sites (`k-health365.com`, `kworld365.com`, `kstudy365.com`); this is not proof that all 25 site credentials are currently usable. The canonical registry names 25 general sites, but live authentication and write permission must be verified per site.

Before any write:
1. Verify the expected site registry and per-site credentials/secrets are present in GitHub Actions without printing secret values.
2. Verify each site's visitor endpoint and WordPress REST authentication.
3. Establish an approved product/link/image source. Current legacy banner scripts are not safe to reuse as-is: they insert a generic laptop/carry case banner into unrelated content, and one script can promote a private post and change its publication date. Those behaviors are explicitly prohibited for this task.
4. Build a read-only manifest first: site rank, yesterday visitors, post ID/title/date/permalink, proposed product match, validated partner URL, validated image URL, and planned action.
5. Only posts with a validated product match and valid partner URL/image may be written. No blanket banner injection.

## Execution and PC-off requirement
- Run scheduled work only on GitHub Actions or the existing cloud/VPS worker; never rely on a local browser/PC process.
- Use a manual `workflow_dispatch` for an initial dry-run, then scheduled runs after preflight passes.
- Process one site at a time in visitor-rank order. Isolate failures per site; a failed site must not block the next site.
- Max one retry per transient error. Fail fast on authentication, quota, rate-limit, or missing product-data failures.
- Use batches (suggested 10 posts/site per write batch) with a durable receipt after each batch; stop safely on an error threshold.
- Do not enable a scheduled write workflow until the read-only manifest is reviewed and required inputs pass. Never expose credentials in logs or artifacts.

## Acceptance criteria
A task is complete only when:
- 25/25 target sites have a verified connection or a clearly recorded blocker;
- site rank uses verified prior-KST-day visits, descending;
- each site has an inventory of up to 100 newest published posts;
- each changed post has a matching product, valid affiliate link/image, preserved status/date, and no duplicate module;
- each write is verified by re-fetching the exact post and public permalink;
- all outcomes are recorded in an append-only receipt, including skipped and failed posts;
- scheduled execution is shown to run without a user's PC being online.

## Current observed state (2026-10-31)
- London Project repository exists and is writable: `huh0303-cmyk/-WP-QWEN-autobot`.
- `scripts/site_registry.py` lists 27 destinations total, of which 25 are non-news general sites.
- WPVibe currently lists only 3 connected sites, not 25.
- Desktop Commander lists two computers, both offline.
- No post edits or 2,500-post batch writes have been performed as part of this task.
- This document records the requested work and safety/acceptance contract; it is not evidence that the live rollout is complete.

## Run ledger template
For each run, append a dated record to the activity ledger with:
- run_id, start/end KST, workflow URL, code commit SHA;
- ordered site list and visitor evidence;
- per-site auth/endpoint status;
- per-post status: planned / updated / verified / skipped / failed;
- post ID, permalink, product evidence, partner URL validation, image validation;
- before/after content hash or module marker;
- retry count and concise error;
- final verified counts (not merely workflow success).

