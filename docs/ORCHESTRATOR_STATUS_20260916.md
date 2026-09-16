# Orchestrator implementation status — 2026-09-16

## Implemented on branch

- resilient text-provider router
- OpenAI -> Claude -> Gemini fallback for WordPress/general work
- Gemini -> Claude -> OpenAI fallback for Blogger
- provider health/cooldown persisted in SQLite
- explicit failure when all providers are unavailable
- provider health API module
- unit tests for fallback and cooldown
- deployment/runbook documentation
- orchestrated article-generator wrapper retaining provider/model metadata

## Not yet proven live

- VPS environment does not yet have a verified `ANTHROPIC_API_KEY` from this change.
- No live failover test has been executed from this branch.
- Existing production `generator.py` and Flask app still need direct wiring or import replacement before this branch can be called production-complete.
- PR must not be merged until tests and one draft-only end-to-end failover test pass.

This file deliberately distinguishes code completion from production deployment.