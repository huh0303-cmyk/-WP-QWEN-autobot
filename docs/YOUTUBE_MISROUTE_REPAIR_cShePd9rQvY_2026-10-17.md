# YouTube Misroute Repair — cShePd9rQvY

- Date: 2026-10-17
- User instruction: move `https://youtu.be/cShePd9rQvY` out of French Survival and place it under Today History.
- Video ID: `cShePd9rQvY`
- Existing evidence: `docs/LONDON_PROJECT_CLAUDE_STATE.md` records that this is the private upload of the 1946 U.S. railway strike archive video, and that it landed on the channel currently branded **French Survival** because the legacy OAuth refresh token named `AMERICAN_ARCHIVE_TIMES` actually authenticated channel ID `UCmt8f9yUT6iTxBys8eH4-Cg`.
- Correct destination from canonical channel lock: **HISTORY_TV_TODAY** / channel ID `UCVBvZwodUF4s57KeNicxQ3w` (the project's Today History knowledge channel).
- Root cause: legacy selector/secret name was treated as identity; upload script did not verify the actual authenticated channel before uploading.
- Required repair: re-upload the original source asset to the exact destination channel ID `UCVBvZwodUF4s57KeNicxQ3w`, verify the new video ID, exact channel ID and privacy state via YouTube API, and only then consider cleanup of the incorrect private copy.
- Safety: YouTube does not provide a way to transfer an existing video's ownership/channel by changing its channel field. A replacement upload on the correct channel is required. Keep the wrong copy private until the replacement is verified; do not delete any video automatically.
- Current execution status: **GitHub incident and routing policy recorded; actual replacement upload is NOT YET VERIFIED**. Do not mark this repair complete until API evidence proves the replacement is on the destination channel.
- Permanent prevention: resolve all uploads by canonical channel ID, never by legacy selector labels alone; fail closed if the OAuth-authenticated channel ID does not equal the configured expected ID.
