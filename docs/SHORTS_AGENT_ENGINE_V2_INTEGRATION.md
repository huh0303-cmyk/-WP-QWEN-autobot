# London Project Shorts Engine — integration contract (draft, not deployed)
Date: 2026-11-10
Scope: all Shorts channels; pilot Seoul Journal first.
This branch is isolated from scheduled production. Do not enable automatic public posting until verified.

## Text generation
Use ONLY Gemini for automated narration, metadata and script generation.
Primary model: gemini-3.8-flash.
Fallback on availability/quota failures: gemini-3.5-flash, then gemini-3.1-flash-lite.
Fail closed if no free-tier call succeeds. Never silently switch to OpenAI or Claude.
Use an explicit provider adapter and JSON schema; log model ID and request outcome, never API keys.
Fact verification requires grounded source claims and editorial review; Gemini alone is not proof.

## Portraits: three permitted paths
1. Previously cleared portrait library, matching the exact person and issue.
2. Wikimedia Commons assets with machine-readable license, attribution and source.
3. Official press/agency photos with verified permission for reuse.
Require >=3 distinct cleared photos for political Shorts. No unrelated substitute,
unlicensed scraping, generated politician portraits presented as authentic, or generic background fallback.
Persist SHA256 and perceptual hash; flag repeated composition and subject mismatch.
All three failures => HOLD_ASSETS, not publish.

## Audio
Fish Audio (configured permitted plan/voice IDs) -> locally configured Qwen3-TTS -> Edge TTS.
Record actual provider and selected Korean voice profile (2 male, 2 female).
Validate ffprobe duration, FFmpeg silence detection, onset timing, and decoded output.
Human-reviewed naturalness or an independently calibrated speech quality model is required
to assert non-robotic voice; silence detection alone cannot measure naturalness.
No configured Qwen adapter => skip with reason; never pretend installed.

## Pipeline
Discover -> Source fact check -> Gemini draft -> Title/content dedupe -> Photo clearance
-> TTS -> Audio QA -> Caption sync -> Render -> Frame/audio QA -> PRIVATE upload
-> YouTube processing/readback -> review approval -> optional scheduled/public posting.
Use per-job idempotency keys and persistent stage receipts; retries only for transient errors.
Authentication/rights/factual failures must stop that job, not other channels.
Keep history in durable storage, not only short-lived Actions artifacts.

## Pilot gate
scripts/shorts_quality_gate.py expects a job manifest and checks title similarity,
SHA256 photo reuse, minimum assets, ffprobe audio, silence, and explicit review flags.
This is a first-stage gate, NOT integrated with the current upload script.
Next integration must invoke it before any YouTube insert; also implement perceptual
image matching, actual caption timing validation, and rollback tests.
