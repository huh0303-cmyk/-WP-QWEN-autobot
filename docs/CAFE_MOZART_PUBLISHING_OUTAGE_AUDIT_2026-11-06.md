# CAFE_MOZART publishing outage audit — 2026-11-06

## Channel identity
- Handle: `@cafe_mozart`
- Canonical channel ID: `UC7jOhyMa-FIrzZuea97z1Pw`
- Registry key: `mbb`
- Type: playlist
- OAuth secret profile: `MBB`
- Registry state: `enabled=true`
- Cadence: every 2–3 days (randomized); release delay: 9 hours
- Content policy: instrumental classical recordings; Mozart and Beethoven

## Confirmed repository findings
1. The channel is correctly present and enabled in `config/youtube_channels.json`; its canonical channel ID and MBB credential profile are registered.
2. The GitHub-hosted worker workflow includes `mbb` as a selectable channel and maps the MBB client ID, client secret, refresh token, music source folder, output folder and thumbnail folder into the job environment.
3. The worker's playlist path selects per-channel OAuth credentials, invokes `scripts/youtube_playlist_maker.py`, then `scripts/youtube_calendar_result.py upload-start` and `scripts/youtube_publish_approved.py`.
4. Both the workflow guard and runtime worker fail closed when `YOUTUBE_COST_HOLD` is not explicitly false. The only code-level exception is a tightly constrained `globalmusic` free-only path. There is no equivalent MBB exception. Thus if the repository environment variable `YOUTUBE_COST_HOLD` remains true/empty, an MBB upload is blocked before calendar claim/render/upload. Do not bypass this control or release the cost hold without the owner's explicit cost approval.
5. The latest inspected YouTube GitHub Worker run (run ID `42061434442`) is executing the `globalmusic` special-case path, not MBB. It is not evidence of a Mozart upload or repair. The other two worker runs in the inspected recent history failed, but the retrieved metadata does not establish that they targeted MBB.
6. The prior Mozart audit dated 2026-10-17 already documented the last known upload gap (Studio screenshot showed 2026-10-01) and explicitly said VPS/queue/token evidence and a verified upload receipt were still missing.

## Root-cause assessment
- Confirmed configuration-level blocker: MBB has no approved cost-hold exception. If `YOUTUBE_COST_HOLD` is still active, MBB is intentionally blocked.
- Not yet proven: current MBB OAuth validity, MBB source-folder contents/rights metadata, calendar row readiness, current action-run error for an MBB-targeted attempt, and successful post-upload identity/privacy verification.
- The old VPS dispatcher/worker architecture is not a reliable recovery route by itself; the repository's current GitHub worker is the intended runner, but it still needs an owner-approved cost path and complete MBB input assets.

## Required next steps (safe order)
1. Owner confirms whether the cost hold may be lifted for this one channel, or supplies/approves a genuinely free-only MBB path (owner-owned rights-cleared audio, authorized artwork, no paid generation APIs).
2. Read-only preflight: verify MBB OAuth `channels.list(mine=true)` returns exactly `UC7jOhyMa-FIrzZuea97z1Pw`; verify MBΒ source audio, documented rights, thumbnail source and a ready calendar row.
3. Run a private/dry-run render and validate duration, audio, thumbnail, title, metadata and rights manifest.
4. Only after explicit upload authorization, upload one video; verify returned video ID, channel ID, title, duration and privacy status; write a receipt.
5. Confirm recurring 2–3 weekly randomized MBB slots execute and alert on failure. Never duplicate an ambiguous upload; never delete existing videos.

## Actions taken in this audit
- Read the channel registry, release policy, worker workflow, worker/runtime implementation, scheduler implementation and the earlier Mozart recovery record.
- Inspected recent GitHub Actions run metadata and one worker's job-step status.
- No cost-hold setting was changed, no secrets were accessed or exposed, no upload was attempted, and no successful publication is claimed.
