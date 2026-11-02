# New-content affiliate automation

## Scope

This GitHub Actions workflow handles newly published content only. It polls the
registered WordPress and Blogger destinations every six hours, then appends one
marked affiliate block only when every one of the ten required slots has a
verified tracking URL in `affiliate-engine/data/offers.json`.

It never uses Hostinger or any VPS.

## Safety controls

- The scheduled workflow is dry-run only.
- A live write requires the manual workflow mode `write` and the GitHub Actions
  secret `AFFILIATE_WRITE_ENABLED=true`.
- WordPress and Blogger credentials remain GitHub Actions secrets.
- The marker `london-affiliate-engine:v2` prevents duplicate insertion.
- Existing body content and existing links are only appended to, never replaced.
- Missing, invalid, or incomplete ten-slot inventory produces a report and no
  content write.

## Registered inventory

At implementation time, the existing repository registry contains 27 distinct
WordPress destinations and 33 Blogger destinations. The workflow reads that
registry dynamically. The requested 35 Blogger inventory and all social-account
IDs are not yet present, so they are not guessed or written to.

## Social platforms

YouTube, TikTok, Facebook, Instagram and Threads require their own account IDs,
OAuth scopes and API review/permissions. They are intentionally excluded from
the live-write path until their credentials and allowed placement surfaces are
registered. This prevents an unapproved platform API call or unsupported edit.

## Existing-post backfill

Use the manual workflow with `scope=backfill`. It processes at most five
previously unmarked published posts per site per run, newest to oldest. A post
is changed only after all ten slots resolve to verified URLs; otherwise the
report records the missing slot and the post remains untouched. Re-run the
manual workflow until every eligible post has the marker. This bounded approach
provides a report and rollback boundary for each group instead of changing the
entire network in one operation.

## Required offer format

Each offer must contain `slot`, `title`, `url`, `providers` and `keywords`.
Only account-generated tracking URLs may be stored. API keys, passwords and
tokens must never be committed.
