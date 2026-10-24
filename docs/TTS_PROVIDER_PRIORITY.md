# TTS provider priority

London Project default TTS order:

1. **Fish Audio** — first choice when its provider adapter and credentials are configured.
2. **Edge TTS** — free fallback; use it before any paid service.
3. **ElevenLabs** — last resort only, and only after both free options fail.

Do not call ElevenLabs directly from a production pipeline before attempting the free providers. Keep provider credentials in GitHub Actions Secrets/environment variables; never print secrets. Record the successful engine in each build manifest. If Fish Audio is not configured, skip it and try Edge TTS. If Edge TTS succeeds, ElevenLabs must not be called.

Shared helper: `scripts/tts_provider_priority.py`. Existing channel-specific scripts must be migrated to this helper or implement the same ordered fallback before this policy is considered fully deployed across all channels.
