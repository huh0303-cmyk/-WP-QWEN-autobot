# SIS vocabulary cards — owner instructions, 2026-09-08

Three cards per session: TOPIK Korean, ENGLISH beginner English, LANGUAGE rotation.
Two sessions daily in Asia/Seoul. Choose a stable random minute in 03:00–07:00 and
14:00–18:00 for each date. This is six original cards and, when all five platforms
are connected, up to thirty public deliveries per day.

Each vocabulary video includes a meaning-matched picture, target word repeated
five times, target-language example sentence repeated five times, synchronized
word/sentence bounce, and matching target-word emphasis in the example. LANGUAGE
explanations are English. Rotation is German, French, Vietnamese, Spanish.

After ten distinct successfully published words in each learning language, queue
a ten-question review. The owner selected replacement, not additional cards:
the next eligible slot for that language contains its quiz instead of a new word.
Do not count cross-platform copies, drafts, private uploads or failed publications.
Retries retain the same content identity. Resolve ambiguous remote outcomes before
attempting a second upload. A quiz must be publicly verified before its review
batch is marked complete. Quiz cards do not increment vocabulary counts.

## Destinations verified or registered

| Platform | TOPIK | ENGLISH | LANGUAGE |
|---|---|---|---|
| YouTube | UCdA24IuR-JE7qButWv5jLqA (registry) | UCrjkKWMHzAAvpLIFgHnwcWg, English Survival, @English_Survival (live channel verified) | UCOWoNH_d6p45ywQ6W0Z1Jng, SIS-Language Center, @sis_languagecenter (live channel verified) |
| Facebook API page | 1128119143729384 | 1247951015067104 | 1236641259534475 |
| Instagram | Graph returned sis_topik1 / 17841410825136018; dashboard says sis__topik: reconcile before publishing | sis_english1 (registered, OAuth unverified) | sis_language (registered, OAuth unverified) |
| Threads | sis__topik (registered) | sis_english1 (registered) | sis_language (registered) |
| TikTok | sis_topik (registered) | unidentified | unidentified |

The old LANGUAGE YouTube label Studio_starbucks refers to the same channel ID;
its current live name is SIS-Language Center. A public channel page does not prove
the current OAuth credential has upload permission. Verify channels.list(mine=true)
against the configured channel ID before API upload. Never use an unrelated music
or documentary channel credential for these educational brands.

## Implementation boundary and live blockers

The new config and control-center section record this approved operating plan.
The SQLite ledger implements deterministic schedule planning, per-platform public
receipts, rotation after first verified publication, unique-word counting, and
ten-question quiz manifests. It is not yet connected to a renderer, persistent VPS
worker, quiz replacement dispatcher, or all-platform public publisher. enabled
remains false. No scheduled task or live social post is claimed by this change.
The obsolete 11:41 KST legacy TOPIK review schedule is removed to avoid duplicate
content outside the new owner's six-card cadence. Its manual review entry remains.

Existing social_publish.py uses private YouTube uploads and Facebook drafts.
TikTok has no TIKTOK_ACCESS_TOKEN in repository/environment secret inventory;
Threads has no configured credentials. Instagram per-brand IDs/tokens/permissions
remain incomplete. Facebook ENGLISH and LANGUAGE page credentials are saved in
the social-publish environment; TOPIK FB_PAGE_ID needs explicit configuration.

Use existing licensed imagery and cached audio. No paid image/audio generation
is enabled by this plan. Codex subscription/usage and actual provider charges have
not been measured; never display an invented zero-cost receipt.

Validation: python -m unittest discover -s tests -p test_vocabulary_card_ledger.py -v
