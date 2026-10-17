# London Project AI Provider Lock — Chairman Directive (2026-10-17)

**Status: LOCKED. Applies to every writing, editing, review, validation, and LLM-assisted audit task.**

1. Gemini text models only. Primary: `gemini-3.8-flash`.
2. On quota, rate-limit, model-unavailable, or request failure, move to the next configured free Gemini text model. Default order:
   - `gemini-3.8-flash`
   - `gemini-2.5-flash`
   - `gemini-2.5-flash-lite`
   - `gemini-2.0-flash-lite`
3. GPT/OpenAI and Claude/Anthropic are prohibited in content generation, rewriting, editorial review, quality verification, model consensus, fallback, orchestration, and LLM-assisted audit. Do not route to them even if legacy environment variables or old chain settings remain.
4. Do not call paid APIs. No paid-provider fallback. If every permitted Gemini model is unavailable or quota-exhausted, record the failure and hold the task/queue; do not retry the exhausted model endlessly and do not publish unverified content.
5. This policy does not replace deterministic external verification. Publication checks must use evidence such as the actual public URL, HTTP response, platform API state, post ID, target account/site identity, and timestamps. An LLM must never certify its own work as complete.
6. Image generation is a separate pipeline. Never use an image-generation model for text writing, summarization, recovery, or validation. Prefer relevant, license-safe free images (Pexels/Pixabay); if unavailable, follow the existing image fallback policy.
7. Do not delete existing published or scheduled posts. This lock changes provider routing and operating instructions only.
8. Before deploying the local/VPS service, sync the committed code, run tests, restart the relevant worker, and verify provider health/logs. A GitHub commit alone does not prove production deployment.

## Enforcement

- Canonical implementation: `control_center/orchestrator.py`
- Runtime fallback override: `ORCHESTRATOR_GEMINI_MODELS` (comma-separated Gemini text model IDs only)
- Primary override: `ORCHESTRATOR_GEMINI_MODEL`
- Legacy `ORCHESTRATOR_CHAIN_*`, OpenAI, and Anthropic settings must not re-enable prohibited providers.
- All changes must be committed to this repository and checked against the canonical implementation before deployment.
