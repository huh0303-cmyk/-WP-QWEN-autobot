# Task routing policy

- `wordpress`: OpenAI primary, Claude backup, Gemini continuity backup.
- `blogger`: Gemini primary, Claude backup, OpenAI continuity backup.
- publication execution remains in existing GitHub/VPS workers.
- newsroom RSS execution remains event-driven and must not be converted to a fixed daily quota.
- Tistory remains local-login/review constrained where the existing platform rules require it.
