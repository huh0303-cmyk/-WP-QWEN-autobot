# Merge gate

Merge only when:

1. production generator uses `control_center.orchestrator.generate_text` directly or through the approved wrapper;
2. Flask app exposes `/api/orchestrator/health`;
3. unit tests pass;
4. one draft-only failover test proves OpenAI unavailable -> Claude success;
5. no duplicate public post is created;
6. VPS secret storage contains valid Anthropic credentials;
7. provider/model metadata is visible in logs or execution records.
