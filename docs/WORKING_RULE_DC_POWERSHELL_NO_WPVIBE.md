# London Project — PC Execution Rule (Permanent)

Date: 2026-10-31 KST

## Mandatory execution environment

- Use Desktop Commander (DC) and PowerShell together for local PC, browser-session, filesystem, command-line, and verification work.
- DC is the authorized bridge to the user's Windows PC; PowerShell is the shell used through that bridge for inspection, scripts, browser/UI automation where appropriate, and validation.
- Do not route routine project work to Work/Codex when the user says those tools are unavailable or have no token. Continue in the current ChatGPT conversation using the connected DC device and PowerShell.
- Do not use WPVibe. The user has explicitly disabled the WPVibe plugin. Do not attempt to reconnect, consume its quota, or use it as a fallback.
- Do not ask the user to repeat these rules. Read this file and `AGENTS.md` before project work.

## GitHub continuity

- Record material decisions, corrections, operating constraints, changes, test results, failures, and next actions in this repository during the same work session.
- Keep credentials, cookies, partner identifiers, tokens, and passwords out of Git history. Use GitHub Secrets or the authenticated account session.
- Preserve existing local changes and use a fresh worktree/branch from the current `origin/main` when the existing working tree is dirty or behind.
- Verify remote GitHub state after pushing; do not report a local-only change as saved to GitHub.

## Current Coupang Partners task — JobKorea365

- Target: `https://jobkorea365.com` (WordPress site ID `wp_jobkorea365`, secret name `JOBKOREA365COM`).
- The requested unit is each individual published article/post, not each site or category.
- Each eligible post should receive 5–10 product recommendations selected for that article's actual topic and reader intent. Use a flexible mix of directly related products, practical Korea-living essentials, and higher-priced products only where relevant.
- Build a site-specific pool of approximately 40–50 products for JobKorea365; do not share the pool blindly with other blogs.
- Every product link must be generated from the user's authenticated Coupang Partners account. Use the portal-generated product-specific short URL and official image+text / blog HTML creative when available. Never guess or append tracking parameters, reuse a different product's URL, or substitute a generic Coupang home link for a product recommendation.
- Do not use generic stock or generated images as the product's actual representative image. Use only the official Coupang creative permitted by the portal/program terms.
- Include the Coupang Partners disclosure and `rel="sponsored nofollow noopener"` on outbound affiliate links.
- First inventory all published posts, map products to each post by relevance, and produce a dry-run manifest. Pilot 3–5 posts, read back the rendered HTML and verify link/image/disclosure, then process the remaining eligible posts in bounded, resumable batches.
- Preserve post content, title, slug, category, tags, status, publication date, featured image, SEO metadata, existing media, and AdSense blocks. Never delete posts.
- During product insertion, also audit and report content/SEO/image/link/layout issues; make only safe, verified corrections that do not alter editorial meaning.
- Track per-product placements and avoid repetitive identical combinations. Do not force products into unrelated legal/visa explainers.

## Current blocker and truthful reporting

- Product-specific links and official creatives must be captured from the authenticated Coupang Partners portal before bulk insertion. A candidate product list is not proof that links have been generated.
- Do not claim posts were modified or published until the WordPress REST read-back and public page verification pass.
