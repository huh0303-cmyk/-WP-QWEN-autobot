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
The follow-up preflight run `36757425951` identified Google's error reason as
`insufficientPermissions` for both, matching the eight core channels. The
existing refresh tokens are upload-only; reauthorization must add identity
read access and verify the locked UC ID before any secret is replaced.
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

## Interactive authorization repair

`scripts/reauthorize_youtube_channel.py` authorizes one locked core or health
channel at a time with full YouTube scope. The owner selects the Google/brand
account and approves in the browser. The script compares `mine=true` with the
locked UC ID before it stores a refresh token; an account mismatch stores
nothing. Core tokens go to the protected VPS runtime and GitHub repository
secret; health tokens go to their existing GitHub repository secrets. It does
not print token values or publish a video. Authorization is a prerequisite,
not proof that fresh approved content and a daily executor are ready.

At 03:23 KST the first KPOP authorization window was open at Google's account
selection screen, waiting for the owner's account choice and consent. No new
token or video publication has been verified yet.

## Owner inventory correction, 03:27 KST

The owner supplied the full displayed-name/handle list with 23 current channel
targets and two future shopping slots. The locked master already contains
exact UC IDs for all 23 current targets, including Japanese Survival
`@seoul_japanese1`, TOPIK `UCdA24IuR-JE7qButWv5jLqA`, both Health Clinic
channels, and Seoul_Jisoo1 `UCAizx0tPkRSol8sIhanN_QQ`. The two additional
shopping slots have neither handle nor UC ID and must not be counted as
active targets or sent uploads. `SIS-Language Center` appears in the owner's
supplemental list but is outside this 23-channel daily target.

Use the locked UC IDs over the pasted list's corrupted/missing characters:
`CAFE_ROMANTIC` starts `UCbJ...`, `CAFE_HEALING` is
`UC7yEsLM-HoXudngrD-4FIqg`, and `INVENTION_STORY1` includes the final `1`.
The locked title/handle is authoritative when an older displayed-name row
differs. No alias shown in Google's brand-account selector establishes a
channel identity until `mine=true` returns the exact locked UC ID.

The five retired keys (`science`, `classical`, `myth`, `american_archive`,
`classic_reads`) remain excluded from the executor. **Correction to the
repository-only check:** the `youtube-channels` GitHub Actions environment
still contains three retired refresh-token secrets:
`YOUTUBE_OAUTH_REFRESH_TOKEN_SCIENCE_FACTS_TIMES`,
`YOUTUBE_OAUTH_REFRESH_TOKEN_MYTH_LEGEND_TIMES`, and
`YOUTUBE_OAUTH_REFRESH_TOKEN_CLASSIC_READS_TIMES`. The other two retired
names (`CLASSICAL_JOURNAL`, `AMERICAN_ARCHIVE_TIMES`) were absent from the
repository and every listed environment. No secret values were read and no
secret was deleted. Keep all five keys prohibited; the owner must remove the
remaining three environment secrets from the GitHub Settings UI before the
old warning can be closed.

The KPOP selector's first `Studio_K3` was chosen according to the locked
legacy alias. Google then displayed an unverified-app warning for the owner's
OAuth app. The browser was handed to the owner to decide whether to proceed;
no warning was bypassed by automation. The exact-ID guard still applies.

The owner confirmed French Survival `UCmt8f9yUT6iTxBys8eH4-Cg`, Portuguese
Survival `UCKvKhETLGPaRV3qfWv2bM2g`, and Vietnamese Survival
`UCRZ0uc_bxKDMwz3noBBi9KQ` are **language** targets. Direct YouTube
`/channel/<UC ID>` pages on 2026-10-01 displayed those respective titles.
They must never be repurposed as shopping channels. The two additional
shopping slots are separate from the 23 verified channels: the historical
`Jisoo2/@sis_languagecenter` candidate still returns YouTube 404 and has no
verified UC ID; the second new slot has no known handle or ID. Neither is
eligible for upload until a distinct UC ID is verified in YouTube Studio and
the public page. The supplied social table has 23 locked YouTube channels
plus this one provisional `Jisoo2` row; its Facebook/Threads/Instagram/TikTok
rows are other platforms, not extra verified YouTube channels.
