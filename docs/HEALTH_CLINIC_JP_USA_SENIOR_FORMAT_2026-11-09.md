# Health Clinic Japan and USA — senior format (2026-11-09)

## Current channel and workflow audit
- Japan channel: `Health_Clinic_Japan`, locked UC ID `UCC_PcHMv-Uxpr00Pjw_J2Wg`; 24 videos are visible on the channel page, 3 subscribers at inspection.
- The channel page still says “Welcome to Studio Quiz JP channel,” an outdated identity line.
- The active daily worker is `scripts/channel_long_video.py` via `.github/workflows/youtube-health-shopping-daily.yml`; prior generated-video implementation had one repeated image in the separate active builder path and western-default English stock searches.
- Existing visual sourcing uses Pexels/Pixabay queries and deduplicates stock IDs within one video. Use Japan-local Japanese older adults for Japan; for USA, intentionally include a varied U.S. senior pool, including Asian American seniors. Do not infer any person's ethnicity from imagery or claim that a stock person is Japanese/American unless source metadata supports it.
- Keep distinct scripts/local examples for the Japanese and U.S. audiences; use original compositions and licensed stock media, not copied competitor assets.

## Shared TTS requirement
- Provider order for both health channels: 1) Fish Audio, 2) Qwen3-TTS, 3) Edge TTS.
- Select one of four profiles randomly per video: two male and two female documentary/news-anchor-style narrators, with locale-specific Japanese and U.S. English profiles. Pass the selected profile through Fish Audio (optional profile reference ID), Qwen3-TTS (profile speaker), and Edge TTS so provider fallback does not lose narrator selection.
- Qwen endpoint and optional credentials are environment inputs; never print or commit secret values.
- Confirmed current code implements the ordered attempts, random narrator routing to all three providers, and locale-specific image query variants in the active channel worker.
- Runtime dependency/credential state remains an operational gate: `QWEN3_TTS_URL` is configured as a repository Actions variable and optional `QWEN3_TTS_API_KEY` is read as a secret. Fish profile reference IDs and Qwen speaker mappings are optional per-profile settings; without them those providers use their defaults. Fish API credential presence and provider success were not probed. Edge TTS remains the final configured fallback. Do not claim Fish/Qwen provider audio was successfully generated until a verification run records the engine and artifact.

## Verification and rollout
- Voice-routing follow-up is proposed on a feature branch and must pass focused checks before merge.
- No video was generated or uploaded during this change.
- YouTube OAuth exact-channel preflight and live private upload remain separate gates. Existing scheduled privacy is private.
