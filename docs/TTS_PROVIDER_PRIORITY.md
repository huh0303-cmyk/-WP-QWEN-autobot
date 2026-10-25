# London Project global TTS policy (FREE-ONLY)

**Status:** Policy committed; rollout across every channel is not complete until each pipeline is migrated and tested.

## Required provider order

1. **Fish Audio S2.1 Pro Free** — model `s2.1-pro-free`, primary provider while the provider's free offer remains available and its terms permit the workload. The currently announced free period is understood to run through **2026-11-30**; re-check official terms before and after that date.
2. **Alibaba Qwen3-TTS (local)** — use only when installed, the target language is supported, and a language-specific quality test has passed. Local inference avoids per-character API charges but still uses local compute/electricity.
3. **Microsoft Edge TTS** — free fallback when the requested language/voice is available and generation succeeds.
4. **Another verified free provider** — only after confirming its pricing, terms, target-language support, and output quality.

## Hard cost guard

- **Paid TTS is prohibited as an automatic fallback.** Do not call ElevenLabs, paid Fish Audio models, or any other paid TTS endpoint automatically.
- If all enabled free providers fail, mark the task failed, log the provider/error category without secrets, and retry according to the queue policy. Do not silently publish silence or placeholder audio.
- Do not log API keys, tokens, or other credentials.
- Record the successful engine, model, language/voice, and retry count in the build manifest when available.
- Do not claim a channel is migrated merely because this policy or helper exists.

## Scope

This policy is intended to be shared by all London Project video pipelines: YouTube language channels, health, knowledge, shopping, Seoul Journal, and any other video channel. Existing channel-specific scripts must call the shared helper or implement the same verified free-only order. Migration is complete only after code review and test renders for each pipeline/language family.

## Shared helper

`scripts/tts_provider_priority.py`

The helper accepts provider adapters so each provider integration can be tested independently. Fish Audio must use model `s2.1-pro-free`; Qwen is a local adapter; Edge TTS is the next fallback. If no free adapter succeeds, the helper must fail closed rather than call a paid service.
