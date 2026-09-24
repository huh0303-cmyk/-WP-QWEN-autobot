# YouTube 10-channel permanent lock

These ten channels are permanently identified by YouTube channel ID, never by a Google brand-account display name. Reuse the verified existing read connections. Do not ask the user to authorize them again unless runtime evidence proves that a stored connection has been revoked or removed.

## Playlist channels

| # | Canonical name | Channel ID | Existing connection |
|---|---|---|---|
| 01 | CAFE_ROMANTIC | `UCbJfEtsffpgI5MsKkB7BYvQ` | Direct YouTube Analytics |
| 02 | CAFE_HEALING | `UC7yEsLM-HoXudngrD-4FIqg` | Direct YouTube Analytics |
| 03 | CAFE_STARBUCKSVIBES | `UC_e-sbLkVgwJNYEeobolNog` | Windsor YouTube read-only; old brand label `Chinese Survival` |
| 04 | CAFE_MOZART | `UC7jOhyMa-FIrzZuea97z1Pw` | Windsor YouTube read-only; old brand label `Mozart-Bach-Beethoven` |
| 05 | CAFE_KPOP | `UCKZsfAWyCmY0jckf4IWZrqw` | Windsor YouTube read-only; old brand label `K-pop Studio` |

## Knowledge channels

| # | Canonical name | Channel ID | Existing connection |
|---|---|---|---|
| 06 | NASA_XFILES | `UCtNLZO07Oh3UnXPI2CjOgNg` | Windsor YouTube read-only |
| 07 | HISTORY_TV_TODAY | `UCVBvZwodUF4s57KeNicxQ3w` | Windsor YouTube read-only |
| 08 | INVENTION_STORY1 | `UCgNj-yS93A_fOHXXvG49fww` | Windsor YouTube read-only |
| 09 | SILENT_ERA_FILM | `UCLvy6kSpC8-7o3hnSrfQ47g` | Windsor YouTube read-only; old brand label `SILENT_ERA_TIMES` |
| 10 | RETRO_USA1 | `UCwh49EokdWFJqYFE_zA6XDQ` | Windsor YouTube read-only; old brand label `RETRO_REELS_TIMES` |

## Operating rule

- Channel ID is the only identity key. Brand-account labels are historical aliases only.
- Control-room cards report the stored read connection, not whether an unrelated publishing token has extra scopes.
- No automatic upload or publication is authorized by this lock.
- Runtime proof lives in `/opt/korea365/data/windsor-youtube-connection-proof.json`, `/opt/korea365/data/account-audience-metrics.json`, and `/opt/korea365/data/youtube-ten-channel-lock.json`.
