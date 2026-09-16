# Orchestrator secret handling

Never commit API tokens. `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `GEMINI_API_KEY` must be injected from VPS secret/environment storage. Provider health output must never include secret values. Error bodies are truncated before persistence; operators should still avoid upstream prompts or services that echo credentials.
