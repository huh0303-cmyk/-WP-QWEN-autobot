# London Project — TTS standard, owner decision 2026-11-10

## Mandatory provider order, free-only
1. Fish Audio S2.1 Pro Free (only when provider and account genuinely allow free use)
2. Qwen3-TTS local, with installed model, language-tested voices and configured QWEN3_TTS_COMMAND
3. Microsoft Edge TTS, verified voice in target language

No silent skipping of configured providers. An unavailable provider must be logged as unavailable; next provider is then tried. No fourth or paid fallback. All providers failing blocks only the affected publication. Local Qwen installation and GPU/CPU execution cost must be checked; open weights do not imply free hosted compute.

## Narrators: six roles per channel
M1 male news anchor; M2 male documentary; M3 male news anchor;
F1 female news anchor; F2 female documentary; F3 female news anchor.
Randomize by video and avoid the last two narrator roles where a persistent history is available. Map each role to an actual verified voice per provider and language. Never label six slots as six distinct voices without validating six actual voice IDs. Fish/Qwen provider voice mappings are deployment prerequisites for genuine 6-voice rotation. Use the same selected role throughout a video, unless a dialogue deliberately uses separate speakers. News and documentary tone are editorial targets, not guaranteed by voice names.

## Quality gates
Decode audio with ffprobe, check duration, silence, clipping, truncation, pronunciation/ASR script match, speaker/voice mismatch, caption timing, volume and speed. Save engine, language, voice, role, retries and failure reasons to manifest without secrets. The existing shared helper currently checks file decode/duration; the remaining QA gates are rollout work.

## Deployment truth
Shared helper and Seoul Journal draft integration exist on branch feature/shorts-quality-gates-20261110. Existing channel-specific TTS paths remain unconverted until each is migrated, tested and deployed. GitHub-hosted runners do not retain local JSON narrator history across jobs: store rotation history in a durable repository artifact/database or shared storage. Current history is only effective within a persistent runner workspace. Verify voice IDs via provider before enabling production.

## Priority migrations
Seoul Jisoo; Health Clinic Japan/USA; 10 language Shorts; knowledge/history; shopping and all other narrated channels. Run targeted tests with mock adapters then real free-provider smoke renders. Do not assert global rollout complete until tests and publish receipts are collected.
