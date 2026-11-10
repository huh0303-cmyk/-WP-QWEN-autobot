# Content Engine Normalization — 2026-08-27

Authority: `MASTER_MONETIZATION_STRATEGY_2026.md`.

## Verified routing

- Ordinary WordPress production is hard-routed to OpenAI/GPT and review draft.
  It has no Gemini prose fallback.
- Blogger rewriting is hard-routed to Gemini and human-review draft.
- Generated images across WordPress, Blogger, Tistory, YouTube videos and Shorts use one shared ordered gateway: Pexels → Pixabay → SDXL Turbo → FLUX.1 Schnell.
- The only approved Replicate model IDs are `bytonylee/sdxl-turbo` and `black-forest-labs/flux-schnell`; each is attempted once with one output maximum. SDXL Lightning and FLUX.1 [dev] are excluded.

## Repairs in this pass

- Corrected the third configured Replicate model ID to the MASTER-approved model.
- Routed TOPIK quiz illustrations through the shared Replicate gateway and removed
  dormant Gemini/OpenAI image fallback code from that review generator.
- Changed TOPIK social metadata from one common caption to native TikTok,
  Instagram, Facebook, and Threads title/hook/caption/CTA/hashtag objects.
- Added per-platform content fingerprints, duplicate skip state, and deterministic
  staggered recommended posting times.
- Bounded the social YouTube uploader to one retry owner and three attempts.

## Remaining verification

- The SNS duplicate state is durable for repeated runs in the same working
  directory. Step 4 must verify a persisted Sheet/log identity before any future
  cross-run automated public posting is enabled.
- Platform-native copy is prepared for review. No social public publishing was
  performed in this normalization pass.
- Retired/manual legacy image scripts remain in the repository but are not wired
  into active generated-thumbnail workflows. They were not deleted without an
  explicit retention decision.
