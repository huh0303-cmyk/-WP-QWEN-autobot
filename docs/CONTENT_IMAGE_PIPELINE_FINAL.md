# London Project — Content Engine Policy (2026-11-10)
Status: OWNER DIRECTIVE / supersedes prior conflicting text and image routing policies.
Scope: WordPress, Blogger/Blogspot, Tistory, YouTube scripts/shorts/descriptions, news and all other generated editorial content.

## English text fallback — exact priority
1. gemini-3.6-flash
2. gemini-3.5-flash
3. gemini-3.5-flash-lite
4. gemini-3.1-flash-lite
5. gemini-2.5-flash
6. gemini-3.8-flash

## Korean text fallback — exact priority
1. gemini-3.5-flash-lite
2. gemini-3.1-flash-lite
3. gemini-3.5-flash
4. gemini-2.5-flash
5. gemini-3.6-flash
6. gemini-3.8-flash

Route by OUTPUT language, not domain or UI language. Attempt each model in order; advance on unavailable model, API failure, empty/truncated/malformed output or quality rejection. After six failures, fail only that content job, never publish empty text. No GPT, Claude, Qwen, random writer selection or hidden extra fallback. Model IDs must be checked against the actual Gemini API model catalog before enabling production; an unavailable model is a failed step, not a reason to silently substitute an unapproved model.

## Images — exactly four attempts
1. Free stock source Pexels or Pixabay, randomized first choice per article
2. The other free stock source
3. Paid SDXL Lightning via configured provider
4. Paid FLUX.1 Schnell via configured provider

Accept only relevant, licensed, nonduplicate, nonwatermarked images, with descriptive ALT. If all four fail, publish valid text without image. No fifth image source, reverse fallback, or stock search after paid models. Paid usage requires configured credentials and billing authorization.

## Implementation obligations
- Replace legacy conflicting code paths, not merely documentation.
- Use one shared language-aware text router and one shared image router; migrate every platform entrypoint.
- Preserve platform-specific formatting, quality gates, deduplication and isolated job failures.
- Do not trigger mass publication while migrating.
- Test one English and one Korean item in draft/private mode, including image and fallback traces.
- Record exact model/provider attempted, result and error in logs; never log credentials.
- Verify GitHub Actions and provider receipts before claiming production migration complete.

This document replaces the 2026-09-12 GPT-5-mini/random Gemini policy. Existing code is not automatically migrated by this document commit.
