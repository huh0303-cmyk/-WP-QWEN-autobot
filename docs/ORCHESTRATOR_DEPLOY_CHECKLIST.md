# Orchestrator deployment checklist

Do not mark the CODEX/Orchestrator failover system complete until every item below is verified on the VPS.

## Code
- [x] `control_center/orchestrator.py` exists
- [x] OpenAI -> Claude -> Gemini failover for WordPress/general tasks
- [x] Gemini -> Claude -> OpenAI failover for Blogger tasks
- [x] SQLite provider cooldown/circuit breaker
- [x] unit tests for failover behavior
- [ ] existing `control_center/generator.py` wired through orchestrator
- [ ] Flask app installs `/api/orchestrator/health`

## VPS secrets
- [ ] `OPENAI_API_KEY` present
- [ ] `ANTHROPIC_API_KEY` present
- [ ] `GEMINI_API_KEY` present
- [ ] keys are only in secret/environment storage, never repo or Sheet

## Runtime
- [ ] `CONTROL_OPERATIONS_DB=/opt/korea365/data/control-operations.sqlite3`
- [ ] `korea365-control.service` restarted successfully
- [ ] `korea365-operations.service` running
- [ ] `/api/orchestrator/health` returns provider state

## Failover acceptance test
1. Keep one WordPress draft-only test job.
2. Temporarily disable the primary OpenAI key in the test environment only.
3. Run the exact same draft request.
4. Verify Claude handles generation.
5. Verify the job remains draft/non-public.
6. Verify provider health shows OpenAI cooldown and Anthropic success.
7. Restore OpenAI key.
8. Never simulate failover by publishing a duplicate public article.

## Completion evidence
- commit SHA
- unit test output
- VPS service status
- one draft test request ID
- provider used/model used
- no duplicate public URL
