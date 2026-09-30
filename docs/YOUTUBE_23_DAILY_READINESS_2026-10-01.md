# YouTube 23 daily public readiness — 2026-10-01 KST

Owner request: use ChatGPT for routine planning and operation, Codex when code
changes are necessary; publish one verified public video per channel each day.
The locked inventory has 23 channels: playlist 5, knowledge 5, language 10,
health 2, shopping 1 (`Seoul_Jisoo1`, @rosiespicks). Exact UC IDs remain in
`config/YOUTUBE_23_CHANNEL_MASTER_LOCK_2026-09-27.json`.

## Today's evidence

Read-only YouTube Data API checked all 23 exact UC IDs at 03:04 KST. Healing
already had three public uploads dated today in KST (`hebod9gD6Tw`,
`XRw2wVQYLeY`, `S8gOupjlv_w`), so no more should be queued. The other 22
showed no public upload today among their latest five public uploads.

The canonical VPS worker and 15-minute scheduler were active. Its registry
contains only playlist 5 and knowledge 5, with a 2–3 day cadence except
History daily. The latest exact-channel OAuth preflight (run `36689192200`)
passed only `globalmusic` and `healing`. `starbucks`, `mbb`, `kpop`, `nasa`,
`history`, `invention`, `silent_era`, and `retro_reels` failed HTTP 403 at
`channels.list(mine=true)`. A further read-only VPS check found all eight
refresh tokens valid but limited to `youtube.upload`; Google's response reason
was `insufficientPermissions`. The upload scope alone cannot prove the exact
authenticated channel before posting, so each channel requires an OAuth token
with both upload and read/identity scope. This does not prove the tokens could
not upload; it proves the safety preflight cannot identify their destination.

`globalmusic` has a failed calendar row for today. Its original worker log
shows `WAITING_FRESH_COMPOSITIONS` before upload: the owner requires new
original music and prohibits reuse of the Drive bank. Resetting or duplicating
that row would not supply the missing composition. No public URL exists.

Language 10, Health Clinic 2, and shopping 1 are outside the current canonical
worker registry. The language series config has old upload flags and a private
upload policy; these are not proof of current exact-channel write credentials.
The Health Clinic EN/JP refresh-token secret names exist in GitHub. Read-only
preflight run `36757036544` refreshed both tokens but `mine=true` returned
HTTP 403 for Japan and USA. Their exact channel identity remains unverified.
The legacy health pipeline also needs content sourcing,
medical quality review, and the new public receipt guard before activation.
Shopping lacks a current executor and verified write token.

## Activation gates

For every channel: verify exact UC ID against the authenticated upload token;
verify no public post for its KST date; prepare original channel-specific
content and rights/source evidence; then upload once and verify returned
video ID, exact channel ID, `privacyStatus=public`, and public watch URL.
Failed or ambiguous upload calls require reconciliation before retry. Add
daily calendar rows only after the channel passes these gates; merely changing
cadence in the registry would create daily failed jobs.

ChatGPT scheduled work can plan and monitor with connected tools, but the
ChatGPT subscription is not a free server-side OpenAI API credential. The VPS
worker remains the durable uploader; Codex is reserved for code and connector
repairs. API pricing: https://developers.openai.com/api/docs/pricing. ChatGPT
scheduled tasks: https://learn.chatgpt.com/docs/automations.
