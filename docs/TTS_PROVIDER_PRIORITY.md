# London Project global TTS policy (FREE-ONLY)

**Status:** Policy committed; rollout across every channel is not complete until each pipeline is migrated and tested.

## Required provider order

1. **Fish Audio S2.1 Pro Free** — model `s2.1-pro-free`, primary provider while the provider's free offer remains available and its terms permit the workload. The currently announced free period is understood to run through **2026-11-30**; re-check official terms before and after that date.
2. **Alibaba Qwen3-TTS (local)** — use only when installed, the target language is supported, and a language-specific quality test has passed. Local inference avoids per-character API charges but still uses local compute/electricity.
3. **Microsoft Edge TTS** — free fallback when the requested language/voice is available and generation succeeds.

**Qwen3 local setup:** Set `QWEN3_TTS_COMMAND` to an installed local inference command with `{text_file}`, `{output_file}`, and `{language}` placeholders. Without this command Qwen3 is unavailable and the helper proceeds to Edge TTS. Never point this command at a paid cloud API. On GitHub-hosted runners, a local model and its dependencies must be installed in the job before Qwen3 can run; configuring the order alone does not install the model.

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

## Final owner instruction — 2026-11-08

This supersedes ALL older London Project TTS order instructions, including old ElevenLabs-first, Fish-to-Edge-only, or fourth-provider fallback instructions. Exactly three engines are permitted in this order for every TTS-dependent workflow (language, knowledge, Seoul Journal, news, health, long-form and Shorts):

1. Fish Audio `s2.1-pro-free` (only when the free tier is available and allowed)
2. Qwen3-TTS locally installed and verified for the target language
3. Microsoft Edge-TTS free voice

On each failed or unavailable provider, record a non-secret failure reason and try the next. If all three fail, abort publishing; never upload silent or placeholder audio and never use a paid or fourth provider. Legacy documents mentioning ElevenLabs or other ordering are historical, not policy. Each actual video producer must be migrated and test-rendered; this document alone does not prove complete migration. Before publishing, verify channel OAuth identity, private/public setting, non-duplicate content, and successful audio generation. A private test upload is the default safe validation mode.

## Owner voice direction — 2026-11-10

- For every spoken-video pipeline, select from a rotating pool of **three male and three female** voices per supported output language, randomized per video.
- Voices must be auditioned and approved for **deep, substantial documentary narration or authoritative broadcast-news delivery**. Female voices must likewise sound polished, mature, confident and professional; do not use childish, cartoonish or excessively bright voices.
- The six-voice requirement is independent of provider: Fish Audio `s2.1-pro-free` -> locally installed Qwen3-TTS -> Microsoft Edge TTS, in that exact order. Never add a paid or fourth TTS provider.
- If the selected provider lacks an approved voice or returns invalid audio, try the next approved provider. If all three fail, **block video rendering/upload/publication**; never publish a silent video.
- Audit and migrate all YouTube, TikTok, Instagram Reels, Facebook Reels and other voice-dependent pipelines. Do not claim migration complete before each producer is wired and tested. An API voice name alone does not prove its vocal quality; audition and approve six voices for each target language.

## Network-wide six-voice rotation lock — 2026-11-10

**Mandatory across every voice-dependent publishing workflow** (YouTube, TikTok, Instagram/Facebook Reels, Threads video, WordPress/Blogspot/Tistory video): exactly **3 approved male + 3 approved female** narrator voices per output language. Male timbre: deep, resonant, measured documentary or authoritative news anchor. Female timbre: composed, mature, professional, confident and trustworthy. Audition each voice before approval; names/metadata alone are insufficient.

Select one of the six approved voices randomly **for each new video**, with recent-use suppression: do not reuse the immediately previous voice for the same channel when at least two approved choices are available. Persist a per-channel voice-use history across scheduled runs so successive executions do not repeatedly select the same voice. Rotate across both genders without hardcoding a single default narrator. Record chosen voice ID, gender, provider and selection timestamp without credentials.

The engine order remains strictly **Fish Audio S2.1 Pro Free -> Qwen3-TTS local -> Microsoft Edge TTS**. Each provider must use an approved voice compatible with the output language; on unavailable provider/voice or invalid audio move forward, never silently change to an unapproved narrator. **If all three providers fail to produce verified non-silent speech, fail the video job and do not render/upload/publish it.** Do not publish muted placeholders or use paid/fourth TTS. Text-only posts do not require TTS.

Implementation status: this policy is a network-wide requirement, not evidence that every publisher has migrated. Audit every platform entrypoint and verify successful voice rotation and three-stage fail-closed behavior before declaring deployment complete.
