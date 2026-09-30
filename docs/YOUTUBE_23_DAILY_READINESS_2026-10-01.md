# YouTube 23 daily public readiness — 2026-10-01 KST

Owner request: use ChatGPT for routine planning and operation, Codex when code
changes are necessary; publish one verified public video per channel each day.
The locked inventory has 23 channels: playlist 5, knowledge 5, language 10,
health 2, shopping 1 (`Seoul_Jisoo1`, @rosiespicks). Exact UC IDs remain in
`config/YOUTUBE_23_CHANNEL_MASTER_LOCK_2026-09-27.json`.

## October 1 daily cadence repair, 05:40 KST

The owner reaffirmed one public item per channel per day and asked to connect actual execution, rather than showing an aspirational plan. The daily plan timer's root-owned output directory caused three consecutive failed runs; it was repaired on the VPS and the October 1 manifest now succeeds with 47 total slots and 23 YouTube targets. The deploy workflow now installs the timer units and enforces `korea365` ownership of that output directory. The core ten's registry and 14-day rolling calendar have been changed to daily future slots, filling empty dates left by the previous 2–3 day calendar while preserving already claimed/failed dates. `CAL` rows block a `ROLL` row on the same channel and date only. These code changes do not make an upload by themselves.

The interactive exact-ID OAuth renewal tool now accepts every key in the locked 23, using unique per-channel secret names, and saves a new token only after `mine=true` returns exactly the expected UC ID. The K-POP flow was restarted and reached Google's unverified-app warning after selecting the first `Studio_K3` brand alias. The owner must personally review/continue that security warning and consent; no new K-POP token or publication is claimed until the callback and exact-ID check succeed. Remaining language, health and shopping channels still need their account-specific authorization plus video production and public receipt paths. Instagram, Threads, TikTok and Facebook also lack a verified per-role daily API publisher; the current 16 role slots must stay blocked until exact external account IDs, write credentials and content assets are verified.

The daily plan timer only writes an audit manifest; the core YouTube scheduler reads a separate Google Sheet. A new YouTube-only calendar roll service and daily timer now fill missing dates for the core ten from tomorrow through day 13. The roll uses the protected VPS Google runtime, a single-process lock, and the existing Sheet header/date guards. It never rewrites an existing date, creates same-day catch-up rows, or invokes the upload worker. Public execution still depends on a verified token, fresh content and the separate 15-minute dispatcher. Its live timer/service result must be recorded after deployment.

Live receipt: PR #176 merged as `2d15e2e9ccb3cb77f744e87dfd48d701cba8ffaf`, Deploy to VPS run `36774910541` succeeded, VPS HEAD matched, and `korea365-youtube-calendar-roll.timer` was enabled/active. An operator-started service run succeeded and logged `Added 128 calendar rows; rolling horizon=2026-10-14`. A second immediate service run succeeded and logged `Calendar already covers 2026-10-01 through 2026-10-14; no rows added`, establishing calendar idempotency. The new rows are future core-channel schedule entries, not video publication receipts. The old 15-minute scheduler remains the upload queue owner. K-POP OAuth remained at the owner-only Google warning at the time of this receipt.

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

## Direct live-page recheck, 04:16–04:20 KST

The owner supplied a 48-row CONTROL/SNS export and asked us to open the
destinations directly. The live `https://sns.korea365.org/social-accounts?platform=SNS`
page still showed YouTube 24, Instagram 6, Threads 6 and the old Jisoo/Japanese
handles. This is the pre-deployment page: the 23/4/4 policy in merged PR #167
has not reached VPS because the deploy owner returned `waiting_for_video`.
Treat the page as a navigation inventory, not evidence of upload OAuth rights.

Opening the explicit `/channel/<UC ID>` destinations in a browser confirmed:

| Destination | Live title and handle | Important observed content |
| --- | --- | --- |
| `UCmt8f9yUT6iTxBys8eH4-Cg` | French Survival, `@SIS_FrenchSurvival` | 1 French lesson; 2 older unrelated US archive videos remain. |
| `UCKvKhETLGPaRV3qfWv2bM2g` | Portuguese Survival, `@Portuguese_survival` | 2 Portuguese lessons; 3 older unrelated science/archive/health videos remain. |
| `UCRZ0uc_bxKDMwz3noBBi9KQ` | Vietnamese Survival, `@SIS_VietnameseSurvival` | 2 Vietnamese lessons; 1 older Bach video remains. |
| `UCAizx0tPkRSol8sIhanN_QQ` | Seoul_Jisoo1, `@rosiespicks` | Public channel has 6 existing health-themed videos/Shorts; shopping transition is an editorial plan, not evidence of existing shopping output. |

`https://www.youtube.com/@sis_languagecenter` still returned a visible 404,
so the provisional Jisoo2 row cannot be used to infer a second shopping UC ID.
The direct `https://www.instagram.com/seoul_jisoo/` profile opened and its
page title showed `Chris Huh(@seoul_jisoo)`: the username is live, while the
display-name change is still pending Meta reauthentication. The new Threads
URL opened a login screen, which does not confirm a Threads handle change.
Do not delete old videos, infer token ownership or upload to these targets
from this public-page inspection.

## Owner's final channel-role confirmation, 04:23 KST

The owner reconfirmed the exact UC IDs above for French, Portuguese and
Vietnamese **language** channels. Existing off-topic videos do not change
their destination identities. The owner also clarified that the six older
Korean-language health items on `Seoul_Jisoo1` are legacy *Health Clinic
Korea* content. Its definitive forward role is **Seoul Jisoo multi-category
shopping/booking**, paired with the active Seoul Jisoo Instagram brand
`@seoul_jisoo`. Do not classify this UC ID as an active Health Clinic Korea
destination. The only active Health Clinic destinations remain Japan and USA.
The owner intends to remove the old Korean health videos, but no deletion was
performed or verified in this session. Record removal receipts only after an
explicit deletion run and public-page check. The Instagram username is live;
its display name remains `Chris Huh` until Meta reauthentication and save.
Other Seoul Jisoo platform accounts are a shopping-brand direction, not
verified account IDs or publish permissions.

## Owner's final editorial correction, 03:55 KST

The five knowledge destinations are `NASA_XFILES`, `HISTORY_TV_TODAY`,
`INVENTION_STORY1`, `SILENT_ERA_FILM`, and `RETRO_USA1`. History selects
exactly two sourced events on the episode month/day, newest historical year
first. The topic selector and offline manifest validator now enforce two;
the full event/scene renderer remains an integration gate.

The two health destinations are **Health_Clinic_Japan (Japanese)** and
**Health Clinic USA (English)**. The owner's intervening Korea reference was
explicitly corrected to USA. The benchmark and format evidence is in
`docs/HEALTH_CLINIC_JP_USA_SENIOR_FORMAT_2026-10-01.md`.

## OAuth continuation after owner approval

The owner completed K-POP consent. The renewal script accepted only the exact
single `mine=true` ID `UCKZsfAWyCmY0jckf4IWZrqw` and stored the KPOP
refresh-token secret in the VPS runtime and GitHub Actions; neither value was
logged or committed. The live CONTROL sheet will read a separate non-secret
OAuth receipt file, written only after this exact-ID check. Its label means
channel identity was checked at the receipt time; it does not certify current
token health or a public video.

The next Starbucks consent attempt revealed that Google's brand selector does
not display `CAFE_STARBUCKSVIBES`. It displays **two** entries named `Chinese
Survival`. The owner approved the first observed entry; the script accepted
only the exact single `mine=true` ID `UC_e-sbLkVgwJNYEeobolNog` and stored
`YOUTUBE_OAUTH_REFRESH_TOKEN_STARBUCKS` in the VPS runtime and GitHub Actions.
The successful Google brand ID is recorded in
`config/youtube_oauth_brand_mapping.json`; selector order is not an identity
rule. The other Chinese Survival entry has not been mapped.

The owner then approved the `Mozart-Bach-Beethoven` Google brand. Its
`mine=true` result matched only CAFE_MOZART `UC7jOhyMa-FIrzZuea97z1Pw`.
The MBB refresh token was stored in the protected VPS runtime and GitHub
Actions secret store, and a non-secret CONTROL receipt was written. This is
not an upload or public video receipt. The Google brand ID is now locked in
`config/youtube_oauth_brand_mapping.json` as a navigation hint; exact UC ID
remains the authority.

The owner approved the `K-RELAX` Google brand for NASA_XFILES. The tool
accepted only exact `UCtNLZO07Oh3UnXPI2CjOgNg`, stored the NASA refresh
token in both protected stores and wrote the non-secret CONTROL receipt.
The owner next approved the `Spanish Survival` Google brand selector entry;
the History tool accepted only exact `UCVBvZwodUF4s57KeNicxQ3w`, stored
the History refresh token in both protected stores and wrote its CONTROL
receipt. This historical selector name must not be confused with the
separate Spanish Survival language channel `UC9mvVEdL9Tllkit5v2Qv8UQ`.

The owner approved the `K-pop Studio` Google brand for INVENTION_STORY1.
The tool accepted only exact `UCgNj-yS93A_fOHXXvG49fww`, stored the
Invention refresh token in the protected VPS and GitHub stores and wrote
the non-secret CONTROL receipt. This historical selector name is distinct
from CAFE_KPOP `UCKZsfAWyCmY0jckf4IWZrqw`.

The owner's screenshot showed an Aside browser `ERR_BLOCKED_BY_CLIENT` page
at `localhost` after a consent link was opened from chat. The completed
OAuth runs had already returned exact-ID success via Chrome. Therefore the
Aside error is a blocked duplicate callback view, not evidence that those
successful token stores failed. For the next approvals the owner was told to
copy each link address into Chrome, which supports the local callback; no
Aside protection was disabled.

The owner approved `SILENT_ERA_TIMES` for SILENT_ERA_FILM. The tool accepted
only exact `UCLvy6kSpC8-7o3hnSrfQ47g`, stored the Silent Era refresh token
in both protected stores and wrote its non-secret CONTROL receipt. Its
Google brand ID is stored as a navigation hint, with the UC ID authoritative.

The owner approved `RETRO_REELS_TIMES` for RETRO_USA1. The tool accepted
only exact `UCwh49EokdWFJqYFE_zA6XDQ`, stored the Retro refresh token in
the protected VPS and GitHub stores and wrote the non-secret CONTROL receipt.
Together with the earlier KPOP, Starbucks, Mozart, NASA, History, Invention
and Silent Era renewals, all eight core channels that had failed the earlier
identity-read scope preflight now have exact-ID OAuth receipts. Romantic and
Healing had passed the earlier read-only preflight and were not asked to
repeat consent. None of these receipts is a public-video receipt.

Google's OAuth documentation says external Testing-mode refresh tokens with
YouTube scope expire after seven days. Production-mode tokens can also stop
working if access is revoked, unused for six months, or invalidated for other
documented reasons. The project's OAuth publishing status has not yet been
verified, so a one-time consent cannot be promised to last forever. Source:
https://developers.google.com/identity/protocols/oauth2#expiration

## Owner account selector and Japanese Survival renewal

On 2026-10-01 KST the signed-in YouTube account switcher displayed all 23
locked target channel names and handles under the same Google login. Japanese
Survival showed `@seoul_japanese1`, matching the existing locked master (the
older `@seoul_japanese` spelling in chat was stale). The Google OAuth selector
listed one primary account and 22 brand accounts, but many brand names were
historical aliases. The order of those two lists aligned with the eight
already verified exact-ID grants; this is a navigation hint only, not an
identity guarantee. Every new grant still requires a single exact
`channels.list(mine=true)` UC ID match before any credential is stored.

The owner approved the primary `CHRIS JUNGYOON HUH` Google account for
Japanese Survival. The renewal tool returned the single locked ID
`UCOWoNH_d6p45ywQ6W0Z1Jng` and stored only the `LANGUAGE_JA` refresh secret
in the protected VPS and GitHub stores. The GitHub secret name and the
non-secret server CONTROL receipt were independently confirmed; no token
value was logged. This is account authorization, not a video upload or
public-release receipt. Health_Clinic_Japan is the next owner approval in
progress, with old Google selector name `K-KIDS`; its channel ID had not yet
been accepted at the time of this entry.

The owner then approved `K-KIDS` and `K-HEALING` in separate Google flows.
Exact `mine=true` checks matched Health_Clinic_Japan
`UCC_PcHMv-Uxpr00Pjw_J2Wg` and Health Clinic USA
`UC91BpNSb4nUwD6jrpthK7FQ`, respectively. The `HEALTH_CLINIC_YOUTUBE_REFRESH_TOKEN_JP`
and `HEALTH_CLINIC_YOUTUBE_REFRESH_TOKEN_EN` secrets were stored in the
protected VPS and GitHub stores and non-secret CONTROL receipts were written.
The historical brand names and Google brand IDs are locked in
`config/youtube_oauth_brand_mapping.json` only as navigation hints. These
authorizations do not certify that either health video has been produced or
published.

The owner next approved Google brand `서울국제대학SIS` for the TOPIK center.
The tool accepted only its locked `UCdA24IuR-JE7qButWv5jLqA` and stored
`YOUTUBE_OAUTH_REFRESH_TOKEN_LANGUAGE_KO` in both protected stores, with a
non-secret CONTROL receipt.

The owner approved `English Survival`. Its exact `mine=true` result was
`UCrjkKWMHzAAvpLIFgHnwcWg`, and the VPS token was stored. The next GitHub
repository-secret write failed with HTTP 400 because the repository had
reached GitHub's 100-secret limit. The original script had not yet written
the CONTROL receipt, so the English grant was partially recorded. The
repair path reads the stored token into process memory without printing it,
refreshes it, repeats the exact UC ID check, and stores it in the existing
`youtube-channels` GitHub environment (which has its own 100-secret quota).
The script then wrote a non-secret CONTROL receipt including
`github_scope=environment:youtube-channels`. This repair succeeded without
another owner approval. Existing repository secret names continue to update
in place; new channel names use the environment. GitHub Actions jobs need
`environment: youtube-channels` to read environment secrets, while the VPS
has its own protected runtime copy. Neither a token value nor a public video
is in GitHub.

## Owner's missing personal YouTube channel investigation

On 2026-10-01 KST the owner reported that a personal YouTube channel named
`CHRIS JUNGYOON HUH` was no longer visible. The signed-in
`huh0303@gmail.com` YouTube **All channels** switcher showed exactly the 23
project channels and no channel with that personal display name. Google's
OAuth chooser showed `CHRIS JUNGYOON HUH` as the **primary Google account**;
its earlier user-approved `channels.list(mine=true)` returned the single
Japanese Survival channel `UCOWoNH_d6p45ywQ6W0Z1Jng`. The public channel
currently displays `Japanese Survival` / `@seoul_japanese1`; its description
says it was previously `SIS-Language Center`, and its About panel says it
joined on 2021-02-20. Google's signed-in Brand Accounts management page
listed 22 current brand accounts and said there were no deleted brand
accounts. An exact-name YouTube channel search returned no result.

These observations establish that the named personal channel is **not
currently selectable under this signed-in Google account**. They do not
establish that a channel was deleted or identify a prior personal-channel
UC ID. A different Google login or an earlier renamed channel remains
possible. Do not create, rename, move, or overwrite a channel based on the
Google account display name. Next: inspect any old personal video/channel
URL or a second Google account if the owner can supply one; compare the
stable UC ID with current channel identities.

Further direct inspection found a **second remembered Google login** in the
account menu: `seoultopik@gmail.com`, also displaying `CHRIS JUNGYOON HUH`.
It is signed out. Its Google reauthentication page was opened for the owner;
its YouTube channel list has not been inspected. This is a concrete next
account to check before drawing any conclusion about the personal channel.

## Italian Survival identity grant

The owner completed the Italian Survival Google consent. The tool accepted
only the exact locked `channels.list(mine=true)` ID
`UCK8B-BM09Cz-ockaQYLL5LA` and stored
`YOUTUBE_OAUTH_REFRESH_TOKEN_LANGUAGE_IT` in the protected VPS and the
GitHub `youtube-channels` environment. The non-secret VPS receipt and GitHub
environment secret name were checked independently. The Google brand selector
ID `101469748905879577842` is recorded as a navigation hint only. No video
upload or public-release receipt is implied.

The owner then approved Portuguese Survival and Vietnamese Survival in
separate Google flows. Exact `mine=true` checks matched their locked IDs
`UCKvKhETLGPaRV3qfWv2bM2g` and `UCRZ0uc_bxKDMwz3noBBi9KQ`. Their
protected VPS grants, non-secret receipts, and GitHub `youtube-channels`
environment secret names `YOUTUBE_OAUTH_REFRESH_TOKEN_LANGUAGE_PT` and
`YOUTUBE_OAUTH_REFRESH_TOKEN_LANGUAGE_VI` were checked. Historical Google
brand aliases `K-health 365` and `비영리한국유학협회KSA` are navigation hints
confirmed only by those exact-ID results. No public videos were established.
