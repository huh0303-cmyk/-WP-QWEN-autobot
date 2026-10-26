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

## Runtime — GitHub-only target

- VPS systemd collection and server-local runtime files are retired. Do not use /opt/korea365 or /etc/korea365.
- GitHub-hosted workflows must use the youtube-channels environment and scoped GitHub Actions secrets.
- The current youtube-github-worker.yml is manual-only, one channel per run, and blocked unless YOUTUBE_COST_HOLD is explicitly false and the operator confirms publication.
- The worker is not considered production-verified until a read-only OAuth check confirms the exact locked channel ID and a permitted canary returns a verified receipt.
- Analytics collection must be implemented as a GitHub Actions workflow with explicit artifacts/receipts; no old VPS timer should be treated as active.
- Never commit tokens, API keys, full OAuth URLs, or secret JSON. This record lists only public channel IDs and connection metadata.
- This is analytics connection documentation, not publishing authorization. Channel IDs are the identity source; display names are not.

## Recovery
Read this record first, then check the timer and latest evidence. Retry stored credentials before asking for login. Never put tokens, API keys or full OAuth URLs in this repository. Do not claim that a third-party trial is permanent free operation.
