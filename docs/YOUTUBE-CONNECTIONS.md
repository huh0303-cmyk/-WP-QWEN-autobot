# YouTube persistent connections

Verified 2026-09-24 KST. Reuse stored connections; do not ask the user to authorize again unless an actual revocation or new scope requires it.

## Verified coverage
Playlist 5 and knowledge 5: all ten channel identities verified with actual API responses. Windsor provides 15 selected channels, plus two direct Analytics connections (romantic UCbJfEtsffpgI5MsKkB7BYvQ and healing UC7yEsLM-HoXudngrD-4FIqg): 17 active collection connections.

- CAFE_MOZART: `UC7jOhyMa-FIrzZuea97z1Pw`
- Spanish Survival: `UC9mvVEdL9Tllkit5v2Qv8UQ`
- Seoul_Jisoo1: `UCAizx0tPkRSol8sIhanN_QQ`
- Italian Survival: `UCK8B-BM09Cz-ockaQYLL5LA`
- German Survival: `UCKF98zgzm7YRWlyMaoJJKIQ`
- CAFE_KPOP: `UCKZsfAWyCmY0jckf4IWZrqw`
- SILENT_ERA_FILM: `UCLvy6kSpC8-7o3hnSrfQ47g`
- HISTORY_TV_TODAY: `UCVBvZwodUF4s57KeNicxQ3w`
- CAFE_STARBUCKSVIBES: `UC_e-sbLkVgwJNYEeobolNog`
- 서울국제대학-TOPIK센터: `UCdA24IuR-JE7qButWv5jLqA`
- INVENTION_STORY1: `UCgNj-yS93A_fOHXXvG49fww`
- French Survival: `UCmt8f9yUT6iTxBys8eH4-Cg`
- English Survival: `UCrjkKWMHzAAvpLIFgHnwcWg`
- NASA_XFILES: `UCtNLZO07Oh3UnXPI2CjOgNg`
- RETRO_USA1: `UCwh49EokdWFJqYFE_zA6XDQ`

## Runtime
- VPS systemd `korea365-channel-metrics.timer` invokes `korea365-channel-metrics.service` daily.
- Collectors execute direct Analytics, public metrics, then Windsor metrics in that order.
- Output `/opt/korea365/data/account-audience-metrics.json` is read by the control center account cards.
- Evidence `/opt/korea365/data/windsor-youtube-connection-proof.json`.
- Credentials remain ONLY in restricted VPS `/etc/korea365/youtube-runtime.json` and `/etc/korea365/windsor-analytics.json`; never commit their contents.
- Windsor API returned HTTP 200, 75 daily channel rows, latest available date 2026-09-20. Missing yesterday is pending, never a fabricated zero.
- Windsor trial supports 15 selected accounts, expires 2026-10-23. No payment authorized. Health Clinic Japan and USA are authorized but not selected for daily Windsor collection. Other unverified channels are not marked complete.
- The old Google brand `Chinese Survival` resolved to CAFE_STARBUCKSVIBES. Brand labels MUST NOT be used as channel identity.
- Reauthorization can change Windsor numeric account IDs; use the selected-account IDs shown in its preview and verify the real YouTube IDs.
- This is analytics collection, not a new publishing authorization. YouTube/SNS remain subject to content-specific final approval. No publication queues were changed.

## Recovery
Read this record first, then check the timer and latest evidence. Retry stored credentials before asking for login. Never put tokens, API keys or full OAuth URLs in this repository. Do not claim that a third-party trial is permanent free operation.
