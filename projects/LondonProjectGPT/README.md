# 런던프로젝트GPT

- Owner/PM: ChatGPT
- Independent track: no delegation to Claude or Gemini.
- Goal: production-grade operating app for Korea365/London Project.
- Production control room: https://control.korea365.org
- App route: /london-gpt
- Existing credentials/secrets/runtime assets are reused; do not ask the owner to resupply them unless verified missing.
- Completion means verified runtime behavior and publication receipts, not code presence.
- Primary architecture: GitHub + VPS 24/7 + n8n orchestration + local browser only for login-bound platforms.
- Browser-bound platforms: Naver/Tistory first; other SNS only when write auth requires human login/OAuth.
- Standard pipeline: Research -> Writer -> Review -> Image -> Publish -> Verify.
- Failure policy: bounded retries, HOLD/dead-letter, no infinite loops.
- Secrets: never commit passwords, cookies, OAuth tokens or API keys.
