# Calendar-driven private review production

User-confirmed operating policy, 2026-08-31:

- Active YouTube scope: five playlists and five knowledge channels. Language
  education and unrelated legacy workflows remain disabled.
- The 2026-08-28 emergency generation lock is lifted only for these two workers
  and their central calendar scheduler.
- The 14-day calendar supplies the channel, KST production-start time and topic.
  This is not a promise of exact upload-completion time: Actions can queue, and
  rendering/uploading takes additional time. Polling is every 15 minutes.
- Automated uploads MUST remain private with no `publishAt`. Review/approval
  does not publish. The owner must explicitly click Publish in the administrator
  page (YouTube Studio). No automatic public transition is added here.
- WordPress and Blogger share the keyword/source/quality/review/result pipeline;
  Blogger follows its corresponding WordPress source. This change does not
  approve public blog publication or alter the existing blog worker policies.

## Duplicate and recovery rules

The scheduler normalizes old playlist display names to the registered channel ID.
An original `CAL-` series takes precedence over accidentally appended `ROLL-`
rows through the original series end date. Suppressed rows are kept for audit;
no historical data is deleted. One canonical channel/day is selected.

Only `기획확정·자료준비` rows in the current bounded Sheet window are eligible.
Expired untouched rows are changed to `PASS`, written to `자동화_유튜브실행`, and
never caught up. See CALENDAR_NO_CATCHUP_POLICY.md.
Claim the row as `자료수집` before calling GitHub. Workers
must bind the claim once, and consume a separate upload marker before the API
upload. Failed/ambiguous requests and GitHub reruns never automatically upload
again; inspect the run and Studio before explicitly resetting a failed claim.

On completion, validate private status and OAuth channel identity in the receipt,
then write `비공개 업로드` plus a Studio review URL to calendar columns M:O. Missing
or invalid receipts are recorded as `실패`. A claimed row with no callback requires
manual reconciliation; it must not be reset merely because time has elapsed.

The channel tab remains the ON/OFF control plane. Its `next_run_at` is read as an
additional dispatch gate and, after a confirmed dispatch, is synchronized to the
next future central-calendar row. The calendar roller enforces a 2–3 day gap and
irregular, non-colliding KST times.

Before rendering, each worker refreshes both an upload-only token and a read-only
identity token, then requires the authenticated account to expose exactly the
registered channel ID. Run **YouTube Hub — 10 channel readiness** after rotating
credentials; it checks all ten profiles and the Sheet without uploading or changing
any YouTube video. Tokens must be authorized for `youtube.upload` and
`youtube.readonly`; broad mutation scopes are intentionally not used by workers.

Approval/publication is human-only: open the emailed Studio edit URL, review the
private video, and click Publish in Studio. No Sheet decision or GitHub workflow
can change a video to public or set `publishAt`. A read-only status sync later
observes the Studio result and records `공개완료` plus `public_confirmed` in the
execution log; it has no YouTube mutation scope.

## Checks

Run the central workflow with `dry_run=true` first. This performs reads only.
Worker dispatch without a calendar ID and one-use claim is intentionally blocked.
Local regression command:

```
python -m pytest tests/test_youtube_calendar.py tests/test_youtube_control.py tests/test_room_safety_contract.py -q -k "not test_room_counts_are_fixed"
```

The excluded legacy room-count assertion currently expects 69 while the existing
registry contains 72; no room registrations are changed by this implementation.
