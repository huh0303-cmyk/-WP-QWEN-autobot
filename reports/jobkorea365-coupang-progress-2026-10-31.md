# JobKorea365 Coupang Placement — Execution Checkpoint

Date: 2026-10-31 KST  
Repository: huh0303-cmyk/-WP-QWEN-autobot  
Working branch: fix/jobkorea365-coupang-placements-20261031

## User-approved operating decisions

- Use Desktop Commander (DC) and PowerShell together for local PC, browser, filesystem and command execution.
- Continue in this ChatGPT session when Work/Codex is unavailable; do not redirect the user to Work/Codex.
- WPVibe is disabled by the user and must not be used.
- Record all material decisions and results in GitHub in the same session.
- The requested placement unit is each individual post/article. Each eligible JobKorea365 post should receive 5–10 article-matched products, not 5–10 products per site.
- Build a separate JobKorea365 pool of approximately 40–50 commercial product candidates, then select 5–10 per article by relevance, purchase intent, practical Korea-living needs and appropriate higher-ticket value.

## PC / repository findings

- Connected Windows PC: ChrisHUH.
- Existing project repository: C:\Users\huh03\Documents\LondonProject.
- Existing working tree was dirty and significantly behind GitHub, so it was not reset or overwritten.
- Fetched current origin/main and created a clean worktree from commit 364180cf at C:\Users\huh03\Documents\LondonProject-JobKorea365-Coupang.
- New working branch: fix/jobkorea365-coupang-placements-20261031.
- GitHub CLI authentication is available on the PC.
- JOBKOREA365COM is present in GitHub Actions workflow environment mappings; secret values are not read or written to the repository.
- WPVibe was not used.

## JobKorea365 live-site read-only inventory

Source: GitHub Actions run 41186746241, workflow affiliate-cloud-preflight.yml, dated 2026-10-31.

- Site: https://jobkorea365.com
- WordPress authentication: HTTP 200 (auth=ok)
- Published posts: 77
- Posts without tags: 5
- Posts without featured image: 31
- Affiliate placements confirmed by inventory: 0 / not inserted
- Writes performed by this preflight: 0

The run also reported 20 authenticated sites and 4 blocked sites across its broader 24-site fleet; this does not change the successful JobKorea365 HTTP 200 result.

## Product pool and inventory tooling prepared

- Expanded the earlier 30-candidate list to 50 JobKorea365 product candidates in config/affiliate/jobkorea365-coupang-50-candidate-pool.md.
- Added scripts/jobkorea365_coupang_inventory.py and .github/workflows/jobkorea365-coupang-inventory.yml for a targeted read-only export of all published posts, including text previews for article-specific matching.
- Python syntax validation passed for the inventory script.
- git diff --check passed at the time of initial validation.

## Coupang Partners portal status

- The Chrome session is signed in to partners.coupang.com.
- The product search screen is visible behind the current portal dialog.
- A click on the 내 정보 area opened an identity-verification dialog. The portal then displayed: 인증이 완료되지 않았습니다. 인증이 완료되지 않아 페이지에 접근할 수 없습니다. 홈으로 이동합니다.
- This is an account-side verification gate. Do not bypass it or fabricate portal links. The next required action is to complete Coupang's own verification flow in the logged-in browser if product-link creation remains blocked.
- Existing generic Coupang Home links in data/affiliate/coupang-links.json are not product-specific and must not be used as substitutes for the 40–50 selected products.
- No product-specific JobKorea365 affiliate short links or official image/tag creatives have yet been captured in this checkpoint.

## Next actions

1. Run the new targeted inventory workflow and save the 77-post article preview manifest.
2. Match each post to 5–10 of the 50 candidate products, avoiding irrelevant product placement in legal/visa explainers.
3. Resolve Coupang portal verification and capture exact product-specific short URLs and official image+text / blog tags from the authenticated account.
4. Dry-run and pilot 3–5 posts; verify public HTML, disclosure, rel attributes, exact product links and image rendering.
5. Only after pilot verification, process the remaining eligible posts in resumable batches. Preserve all original post content and metadata.
6. During insertion, audit missing featured images (31), missing tags (5), and other SEO/content/link/layout issues. Fix only safe, verified issues; do not delete posts.

## Truthful completion status

NOT PUBLISHED YET. The product pool and read-only workflow are prepared; 77 published posts are verified; product-specific portal links/creatives and the live-site pilot are still outstanding.
