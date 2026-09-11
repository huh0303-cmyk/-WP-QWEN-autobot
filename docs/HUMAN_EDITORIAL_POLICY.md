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

## Network image-generation order

This order applies to every generated image for all 27 WordPress sites, all 27 Blogger sites, YouTube, and every SNS channel. Replicate is the single approved image-generation provider and must be accessed through the GitHub Actions secret `REPLICATE_API_TOKEN`:

1. `FLUX.1 Schnell` — primary and preferred model.
2. `SDXL-Lightning 4-step` — low-cost fallback. Do not substitute the less stable 1-step checkpoint.
3. `SDXL Turbo` — final generation fallback.

The order is mandatory. Skip an unavailable model and move to the next approved Replicate model instead of silently substituting Gemini, OpenAI, stock imagery, or another generator. Every output must pass topic-relevance and usage-rights checks. If all three models fail or produce misleading/weakly related output, use zero images for text content and stop the image job for visual-first content pending human review.

Do not hard-code a universal per-image price. Record the provider, endpoint, resolution, actual billed amount when available, model ID, prompt, license basis, and output receipt because hosting prices and commercial terms can change.
