# Human editorial quality policy

This policy applies to Blogger, WordPress, and YouTube scripts, descriptions, titles, thumbnails, and supporting copy.

1. Optimize for a real reader or viewer, not for evading an AI detector. No detector result can prove human authorship.
2. Block observable automation artifacts: model self-reference, prompt fragments, code fences, placeholder text, repeated boilerplate, fabricated first-hand experience, unsupported statistics, fake quotations, and mechanically repeated structures.
3. Preserve each destination's own audience, persona, tone, vocabulary, length range, editorial scope, and language. Do not reuse a network-wide generic voice.
4. Use concrete verified facts and primary sources where the topic requires them. Never invent expertise, credentials, sources, links, experiences, or freshness claims.
5. Vary structure only when the subject calls for it. Do not force tables, FAQs, numbered titles, images, or calls to action into every item.
6. Images and thumbnails must be genuinely related to the specific item. When no suitable licensed image exists, text articles may use zero images; never insert a generic decorative substitute merely to fill a slot.
7. Automated quality scores are internal pre-publication signals, not Google, AdSense, Rank Math, or human-review scores and never guarantee approval or reach.
8. Blogger remains human-review-first: create a private draft and require the owner to make the final publication decision.

## Network image fallback order

Use this exact order for WordPress, Blogger/Blogspot, Tistory, YouTube long-form videos, and Shorts:

1. Relevant, licensed Pexels image
2. Relevant, licensed Pixabay image
3. Replicate `bytonylee/sdxl-turbo`
4. Replicate `black-forest-labs/flux-schnell`

The two Replicate models are the only approved paid image generators. Make at most one attempt per model and request one output per attempt. Do not use SDXL Lightning, FLUX.1 [dev], Nano Banana, OpenAI image generation, or other image providers. If the four stages fail relevance, licensing, factual-integrity, or quality checks, continue without an image where the platform permits it; never substitute a generic filler. Store the token only as GitHub Actions secret `REPLICATE_API_TOKEN`.

Replicate lists FLUX Schnell at $3 per 1,000 output images ($0.003 each). The SDXL Turbo community model page estimates about $0.0015 per run; amounts can vary with inputs. A content item that needs both paid stages can therefore use about $0.0045 in model charges. Log actual billed amounts when available.
