# London Project YouTube Publishing Runbook
**Updated:** 2026-10-25  
**Scope:** 23-channel YouTube portfolio, including Seoul Journal political Shorts.

## Required end-to-end pipeline
1. **Select channel and format** — resolve a registered channel profile and content type (Shorts or long-form); never infer a channel from whichever Google account happens to be signed in.
2. **Research and source record** — save source URLs, retrieval time, factual claims, and rights/attribution notes. For Seoul Journal, use Naver Politics articles and preserve the source URL in the description. The first eligible card is only a prominence heuristic, not verified view-count ranking.
3. **Script and editorial checks** — produce the script, title, description, hashtags, and source note. Check factual grounding, allegations language, duplicate topics, and title length before rendering.
4. **Narration** — free-only policy: Fish Audio model `s2.1-pro-free` first when `FISH_AUDIO_API_KEY` is configured; local Qwen3-TTS only when installed and language-verified; Edge TTS as the next free fallback. If all free engines fail, fail the job. Never call paid TTS automatically.
5. **Render** — create a real MP4 with FFmpeg, validate file size, dimensions, duration, audio track, and aspect ratio. Shorts target 9:16 (1080×1920) and no more than 180 seconds; Seoul Journal's current template targets roughly one minute.
6. **Channel identity preflight** — refresh OAuth, query `channels.list(mine=true)`, and require exact equality with the expected channel ID before upload.
7. **Upload and verify** — resumable upload; write a receipt containing video ID, channel ID, privacy state, and source URL. On transient failures retry only the failed stage with bounded attempts; do not create duplicate uploads.
8. **Review gate** — new Seoul Journal Shorts upload as **private**. A human reviews factual accuracy, captions, image rights, audio, title, and description before making public or scheduling. Do not silently switch privacy to public.
9. **Observability** — save a per-job run ID, stage status, sanitized error category, retry count, artifact link, and upload receipt. Never log API keys or OAuth tokens.

## Current implementation state (verified from repository)
- `.github/workflows/seoul-journal-political-shorts.yml` manually builds and uploads a Seoul Journal political Short as private, after an explicit confirmation and exact-channel OAuth preflight.
- `scripts/seoul_journal_shorts_pipeline.py` extracts a Naver News article, drafts a fact-grounded Korean narration package, renders a vertical video, and performs resumable YouTube upload.
- Seoul Journal Shorts narration was migrated away from ElevenLabs to Fish Audio Free with Edge TTS fallback. The Fish Audio key is optional for execution because Edge TTS is the free fallback; configure GitHub Actions secret `FISH_AUDIO_API_KEY` to use Fish Audio as primary.
- `.github/workflows/tts-free-policy.yml` now includes compile and regression checks for the Seoul Journal Shorts TTS path.
- `.github/workflows/seoul-journal-daily-shorts.yml` only creates an editorial queue artifact. It does **not** itself render or upload a Short.
- `.github/workflows/youtube-vps-enqueue-today.yml` queues a single run-now job for its listed ten channel keys; it is not a universal 23-channel dispatcher.

## Remaining work before claiming the entire 23-channel workflow is production-ready
- Inventory every registered channel/profile and map each to its own expected YouTube channel ID and OAuth refresh token.
- Migrate every active Shorts/long-form generator to the shared free-only TTS policy and remove any paid automatic fallback.
- Verify each channel's language, voice, category, title/description policy, privacy default, and retry/idempotency behavior.
- Add a unified dispatch/queue that supports all 23 registered channels without conflating credentials.
- Run read-only OAuth preflight for every channel; then test-render one private canary per channel family and inspect its artifact.
- Enable recurring schedules only after the channel-specific canary passes. Public release remains an explicit approval step.

## Safety invariants
- No API keys, client secrets, refresh tokens, or private credential files in repository code or logs.
- No public upload during setup or validation.
- No automatic paid TTS fallback.
- No retry that creates a second upload without first checking the existing job receipt.
- If source extraction, channel identity, render validation, or upload verification fails, mark the job failed and preserve diagnostics.
