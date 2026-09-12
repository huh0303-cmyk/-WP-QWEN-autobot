# FINAL Content + Image Pipeline

Status: LOCKED / OWNER APPROVED
Date: 2026-09-12

This document is the authoritative pipeline policy. Older conflicting writing/image fallback documentation must not override it.

## Writing

Primary writers:
1. GPT-5 mini
2. Gemini Flash

Routing:
- Select GPT-5 mini or Gemini Flash randomly / alternately for each article.
- Do not copy one platform article verbatim to another platform.
- Each platform/site output must preserve its own persona, language, search intent and formatting.

Fallback:
- If GPT-5 mini fails or fails quality validation -> retry with Gemini Flash.
- If Gemini Flash fails or fails quality validation -> retry with GPT-5 mini.
- Failure includes API failure, empty/truncated output, wrong language, malformed structure, severe repetition, or quality-gate failure.
- If both fail after controlled retry, mark only that job FAILED/RETRY. Never block the rest of the network.

## Image

Order is fixed:

1. Pexels / Pixabay stock search
   - Search both/free sources as available.
   - Use stock image only when it matches the article/title/intent sufficiently.
   - Reject irrelevant or misleading images.

2. SDXL Lightning
   - First AI image generation fallback when no acceptable Pexels/Pixabay image is found.

3. FLUX Schnell
   - Second AI image generation fallback when SDXL Lightning fails or its result is unsuitable.

4. No image
   - If stock + SDXL Lightning + FLUX Schnell all fail or are unsuitable, publish without an image.
   - Image failure must never block an otherwise valid article.

## Quality Gate

Before publication check at minimum:
- correct site/topic/persona
- correct language
- non-duplicate title
- no verbatim cross-platform duplication
- no empty/truncated/malformed content
- no obvious repetitive AI-template phrasing
- image relevance when an image is used
- valid ALT text when an image is used

## Publication Flow

MASTER / scheduler
-> topic + keyword + target site/platform
-> random/alternate writer (GPT-5 mini or Gemini Flash)
-> opposite writer fallback on failure
-> quality gate
-> Pexels/Pixabay relevance search
-> SDXL Lightning fallback
-> FLUX Schnell fallback
-> no-image fallback
-> platform-specific formatting
-> queue / publisher
-> real publication URL or provider receipt
-> result/status/error returned to Control Room / MASTER

## Reliability Rule

One failed site/platform/job must never stop other sites/platforms/jobs. Failures are isolated, logged and retryable.

## Success Definition

A job is SUCCESS only after a real provider publication result is confirmed (URL/post ID/receipt as applicable). Code existence, dispatch, or queue acceptance alone is not publication success.
