# London Project — owner decisions and next actions
Updated: 2026-10-22 (Vietnam time; KST noted where applicable)

## Verified current state
- Control dashboard grouping/date changes are committed on branch `fix/control-platform-group-ranking-20261021`, commit `8dc848aa3fcf8cc9efff888db56d6c0024ee103e`; PR #217 is open. Production deployment and runtime behavior are not verified.
- Seoul Journal audit recorded that the scheduled Shorts workflow was blocked before upload: the configured annual keyword calendar had 2027 rows but no required `2026-10-17` row; the only authorized YouTube channel found was Seoul International University–TOPIK Center (`@seoul_topik1`), not Seoul Journal; `@seoul_jisoo` publishing authorization was missing; approved ElevenLabs credentials/voice ID must be verified.
- Never upload Seoul Journal content to the TOPIK channel as a substitute.
- Do not report a post as published without a real public URL/post ID or verified platform receipt.

## Owner decisions required
1. **Seoul Journal keyword calendar:** provide/fix the missing 2026-10-17 row, OR explicitly approve a different calendar date/source/rule. Do not silently change dates.
2. **Correct Seoul Journal YouTube channel:** owner must connect/authorize the exact channel in the publishing integration. Do not send credentials or API keys in chat or commit them to the repository.
3. **Instagram @seoul_jisoo:** owner must authorize the exact account for publishing through the chosen integration; handle existence alone is not authorization.
4. **ElevenLabs:** owner must ensure `ELEVENLABS_API_KEY` and the approved per-channel voice IDs are stored as GitHub Actions secrets and/or VPS environment secrets. For the Japanese health channel, the approved Japanese voice ID must be supplied in secret storage; do not replace it with an English voice.
5. **Publishing scope:** do not publish a real video/Reel without the correct channel/account authorization. A draft/render test is acceptable only where it does not upload publicly.

## Execution order after decisions
1. Validate and repair PR #217: inspect checks, test ranking data fields, verify date banner, then confirm deployment separately.
2. Confirm GitHub Actions workflow triggers and secret references; run safe non-publishing validation first.
3. Run channel-specific ElevenLabs voice audit using credentials from secret storage; keep audit audio private.
4. Fix Seoul Journal calendar/channel/voice blockers, render one preview, ask owner to approve before public upload.
5. Fix Instagram authorization and run a non-public/lowest-risk validation before posting.
6. Verify unattended execution via workflow run history or VPS service logs; PC-off operation is only claimed for jobs that are demonstrably running on GitHub Actions/VPS.

## Status labels
- DONE = evidence exists and verification passed.
- COMMITTED = code/doc exists in GitHub; not necessarily deployed.
- BLOCKED_OWNER = explicit owner action/decision required.
- BLOCKED_TECH = code, workflow, deployment, or credential validation incomplete.
- NEVER mark COMMITTED as DONE or queued as published.


## Owner decisions confirmed — 2026-10-22 (Vietnam time)

1. **Seoul Journal calendar:** change the rule to use valid keywords from another dated calendar row when the target row is missing. The queue must record both the target date and actual selected row; every keyword remains pending same-day trend/news validation. Never imply an old/future calendar row is currently trending without that validation.
2. **YouTube:** owner will directly connect and authorize the dedicated Seoul Journal account. Until the integration returns evidence of the exact channel ID, do not upload or substitute another channel.
3. **Instagram:** owner will connect publishing authorization for the exact `@seoul_jisoo` account. Handle existence alone is not sufficient.
4. **ElevenLabs:** retain existing per-channel voice assignments and verify credential/voice-ID availability. Do not rotate voices or substitute the Japanese voice.
5. **Public publishing:** after technical validation, public publishing is allowed only to pre-designated channels with account-specific authorization. Do not publish to any unapproved account. Record platform post URL/ID as proof.

## Execution evidence — 2026-10-22

- Implemented the calendar fallback in `scripts/seoul_journal_daily_queue.py`: if the target date is absent, select the closest dated row containing at least one of the five keyword cells, record target date, selected row, distance, and explicit override; each item remains `awaiting_datalab_and_media_validation`.
- The existing Seoul Journal workflow remains an editorial queue only; it does not render an MP4 or publish. This change does not authorize a public post by itself.
- GitHub Actions secret values cannot be read back through repository file APIs. ElevenLabs connectivity is not yet verified because the audition workflow has not been run with its required confirmation input; credentials must remain in GitHub environment secrets, never in Git.
- YouTube and Instagram connection/authorization remain owner actions in their respective platform/integration UI. No public post has been attempted.
- Status: calendar rule **COMMITTED, execution test pending**; YouTube **BLOCKED_OWNER**; Instagram **BLOCKED_OWNER**; ElevenLabs **BLOCKED_TECH until workflow audit evidence**; public publishing **AUTHORIZED BY POLICY AFTER VALIDATION, NOT YET EXECUTED**.
