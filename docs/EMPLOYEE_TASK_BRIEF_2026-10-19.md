# London Project — Employee Work Instructions
**Work date:** 19 October 2026  
**Project:** control.korea365.org  
**Purpose:** Reconcile all channel/account inventories and verify account-by-account immediate publishing readiness. This is an audit and controlled verification task; do not make unapproved public posts.

## A. Required deliverables by end of day

1. A master inventory for all YouTube and social accounts, with one row per channel/account.
2. A gap report: missing accounts, duplicate entries, missing handles/IDs, missing workflows, expired/logged-out connections, and publishing blockers.
3. Evidence for each immediate-publish test: timestamp, account/channel identity, workflow/job ID, result, and public URL if a post was explicitly authorized and published.
4. A prioritized list of fixes and who/what is needed for each blocker.
5. A final report to the project owner. Never mark an unverified item as complete.

## B. YouTube inventory to reconcile

Expected target: **23 channels**:
- Knowledge: 5
- Language: 10
- Playlist: 5
- Health: 2
- Shopping: 1

This is the target to verify, not a claim that all 23 are already registered. Read the repository's current channel registries, workflows, secrets references (names only; never reveal secret values), and dashboard data. Compare the target to the actual configuration and list every missing or extra channel.

For every actual channel, record:
- Category
- Display/channel name
- Handle
- Channel ID
- Main content topic
- Language
- Publishing frequency and schedule
- Workflow name/path
- Enabled/disabled state
- Connection/auth status
- Latest verified public video URL and date
- Immediate-publish readiness: PASS / FAIL / NOT TESTED
- Evidence or exact blocker

Do not guess missing channel names, handles, language, schedule, or workflow. Mark unknown values as `UNVERIFIED` and assign a follow-up.

## C. Playlist channel rule — mandatory

- Each playlist channel must publish **2–3 times per week**.
- Before making each thumbnail, find relevant videos in the same category with **at least 1,000,000 views**.
- Record the reference title, URL, observed view count, and date checked.
- Learn from the composition, contrast, color palette, focal point, readability, and visual hierarchy, but make an original thumbnail. Never copy another creator's thumbnail or unlicensed artwork.
- If no suitable 1M+ example is found, record the search terms and closest relevant references, and flag the exception.
- Confirm the selected channel ID, schedule, video language, rights to audio/video assets, and final public URL.
- See `docs/YOUTUBE_PLAYLIST_PUBLISHING_POLICY.md` for the full policy.

## D. Social-account inventory

Inventory **every account found in the current project records** for:
- Instagram
- Threads
- TikTok
- Facebook

One row per account; do not merge several accounts into one row. Record:
- Platform and category/brand
- Display name and @handle
- Profile URL / account ID if available
- Main content topic and language
- Intended publishing frequency
- Workflow/script/config source
- Connection status and last verified date
- Immediate/manual publish capability: PASS / FAIL / NOT TESTED
- Latest verified public post URL and date
- Exact blocker / next action

Use current active-account registries first. Older or inactive inventory must be labeled inactive/unconfirmed rather than presented as active. Do not invent handles or infer that an account is connected merely because its name appears in a file.

## E. Immediate-publish verification on control.korea365.org

For every account, verify whether the dashboard's immediate-publish control:
1. Selects the correct platform and account/channel.
2. Sends the task to the intended workflow with the right account identifier.
3. Shows a job/run ID and an understandable status.
4. Prevents duplicate dispatches and keeps each account's job isolated.
5. Reports the real result; “queued”, “accepted”, or “dispatched” is not the same as “published”.
6. Provides a public URL and timestamp after a successful authorized publication.

Testing rules:
- Start with a non-public/draft or dry-run test where supported.
- Do not publish publicly without explicit approval from the project owner for that test.
- Do not delete existing posts or videos.
- Do not change production schedules, secrets, or live settings without approval and a backup/rollback plan.
- If one account fails, record and fix that account independently; do not stop unrelated accounts unless a shared system-wide incident requires it.
- If authentication, CAPTCHA, permission, or an uncertain publish result occurs, stop that account's run and report the blocker. Do not repeatedly retry an uncertain public publish.

## F. Evidence standard

Use these exact status definitions:
- **PUBLISHED:** public URL opened and verified.
- **SCHEDULED:** future schedule visibly confirmed.
- **DISPATCHED:** workflow accepted request; publication not verified.
- **PASS (TEST):** test completed with evidence, without claiming public publication.
- **BLOCKED:** exact error and evidence captured.
- **NOT TESTED / UNVERIFIED:** insufficient evidence.

For each test, save a screenshot or log excerpt (hide tokens, cookies, emails, and other credentials), the timestamp, account identifier, workflow/run ID, and outcome.

## G. Final acceptance checklist

- [ ] Actual YouTube channel count compared with target 23 and discrepancies listed.
- [ ] Each YouTube channel has name, handle, topic, language, frequency, workflow, status, and evidence fields.
- [ ] Playlist channels show 2–3 publications per week.
- [ ] Playlist thumbnails have 1M+ same-category reference evidence or a documented exception.
- [ ] Instagram, Threads, TikTok, and Facebook accounts are listed individually from source records.
- [ ] Immediate-publish capability is verified account by account; untested accounts remain clearly marked.
- [ ] No public post was made without authorization.
- [ ] No existing content was deleted.
- [ ] Backups and rollback notes exist for any approved configuration change.
- [ ] Final report lists PASS, FAIL, NOT TESTED, missing items, evidence links, and next actions.

## H. End-of-day report format

1. Total accounts found by platform and category
2. Target vs actual YouTube channel count
3. Accounts fully verified for immediate publishing
4. Accounts blocked / not tested and exact reason
5. Playlist thumbnail references checked (with links)
6. Changes made, files changed, commit/run IDs
7. Public URLs for any explicitly approved publications
8. Top three next actions and owner for each

**Important:** Do not report “everything works” unless every listed account has evidence. A configuration entry or workflow file alone is not proof of a working live connection or successful publication.
