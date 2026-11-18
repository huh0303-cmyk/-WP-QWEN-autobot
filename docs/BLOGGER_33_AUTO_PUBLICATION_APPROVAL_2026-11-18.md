# Blogger 33 — Owner approved automatic public publication
Approval: 2026-11-18. Scope: exactly 33 approved Blogger properties, once per site per Korea Standard Time calendar day, after quality verification. This supersedes the **draft-only/manual-final-publication** restrictions in `docs/BLOGGER_CONTENT_POLICY.md` paragraphs 25–26 for these 33 approved destinations only. Other editorial, copyright, source, quality, and privacy requirements remain effective.

## Publication contract
1. Each verified site may publish **at most one LIVE post per KST date**. Check Blogger's authenticated LIVE posts and KST published timestamps before writing; an Actions run marker alone is not sufficient. On retries, recover existing post IDs and never create a duplicate.
2. Source article must be original and meet site-specific persona/tone/length, structure, sources, 4-category label taxonomy, language, duplication, image/ALT and safety checks; quality gate at least 75/100 where available.
3. For each post, record blog ID, post ID, title, URL, API status LIVE, and ideally public HTTP 200 and matching content. If HTTP check fails, distinguish API-confirmed LIVE from publicly verified; never claim HTTP verification without it.
4. Random non-round morning dispatch per day, no AM+PM duplicate. GitHub scheduler delay/skip possible; monitor missed dates.
5. **Release gate**: actual owned inventory of 33, OAuth permission, backups of posts/theme/settings and restore check, one English and one Korean test, approved editorial/image pipelines, and successful result verification. Keep `BLOGGER_33_BACKUP_AND_TEST_VERIFIED` unset/false until all are confirmed. The release gate is not itself evidence of backup.
6. No changes to WP K-health365.com AdSense/DNS/old posts. Existing Blogger posts/URLs preserved unless separately verified and backed up.
7. Current code may still contain legacy 31-site assumptions, 1–3 labels, affiliate catalog fail-closed and multiple writers; every executable route must be audited before enabling production. GitHub commit does not mean release complete.

## Immediate status
- Owner authorization: **YES**.
- Runtime activation: **NO** until full preflight and backups.
- Publishing schedule target: 33 posts/day maximum, 1 per verified site, with no guarantee of success until real-world evidence.
