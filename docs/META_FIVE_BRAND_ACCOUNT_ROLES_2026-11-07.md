# Meta / Instagram / Threads — Owner-confirmed five-brand account map

Effective: 2026-11-07 (Asia/Seoul)

This document records the owner's latest confirmed five-brand operating specification. The machine-readable source of truth is `config/meta_five_brand_account_roles_2026-11-07.json`.

| Brand handle | Instagram | Threads | Editorial role | Cadence |
|---|---|---|---|---:|
| japanese_pick | japanese_pick | japanese_pick | 일본어 필수 기초회화 | 하루 3회 |
| english_pick1 | english_pick1 | english_pick1 | 영어 필수 기초회화 | 하루 3회 |
| seoul_jisoo | seoul_jisoo | seoul_jisoo | 핫이슈·K-뷰티·건강기능식품 | 하루 3회 |
| seoul_chris | seoul_chris (rename verification pending) | seoul_chris (rename verification pending) | 핫이슈·K-뷰티·건강기능식품 | 하루 3회 |
| seoul_topik | seoul_topik | seoul_topik | TOPIK 시험 준비; connect to the primary TOPIK YouTube channel | 하루 3회 |

## Important identity distinctions

- `seoul_chris1` is the previously observed Instagram username. The owner’s requested target is `seoul_chris`. Do not change account IDs, OAuth credentials, or secret names until live Instagram and Threads identity endpoints verify the exact new handle.
- `seoultopik` and `seoul_topik` are different strings. Never substitute one for the other.
- A Facebook personal profile display name is not an Instagram/Threads handle or a Facebook Page name. Do not rename the personal profile until the owner explicitly confirms the exact display name to use. Page-name changes must be handled separately per Page.
- The account-center email notice confirms linked accounts, but does not prove that all five Threads tester invitations have been accepted or that API write scopes are granted.

## Content and scheduling

- Language accounts: three distinct beginner-friendly micro-lessons per day, per platform.
- Seoul Jisoo and Seoul Chris: three distinct daily posts per platform, with hot issues, politics/society/economy, sports, entertainment/viral topics, K-beauty, and health functional foods. Keep the two accounts' angles and copy distinct.
- Seoul TOPIK: TOPIK I/II preparation, vocabulary, grammar, reading, listening, writing, and study-in-Korea information. Link to the primary TOPIK YouTube channel only through verified public channel/video URLs.
- Use Asia/Seoul time. Stagger posts and avoid duplicate topics on the same day.
- Create native, non-verbatim copy for Instagram and Threads.
- Fact-check current affairs, sports, health, and commercial claims. Do not overstate supplement benefits.

## Safety gates

- Public publishing remains disabled.
- Do not publish test posts.
- Do not enable public auto-publishing, alter YouTube cost locks, or change any production secrets as part of this configuration update.
- Require exact per-platform identity verification, platform-specific write permission, and separate owner authorization before publication.
- Never commit access tokens, cookies, passwords, or other secrets.
