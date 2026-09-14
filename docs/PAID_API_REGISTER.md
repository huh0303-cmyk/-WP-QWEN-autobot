# Paid API register

This register records paid or credit-bearing APIs confirmed by the owner. Never store secret values, complete token prefixes, card details, or billing identifiers in Git.

Last verified: 2026-08-27 (KST)

| Service | Purpose and scope | Credential name | Confirmed billing state | Operating rule |
| --- | --- | --- | --- | --- |
| Replicate | All generated images for 27 WordPress sites, 27 Blogger sites, YouTube and SNS | `REPLICATE_API_TOKEN` | USD 10.00 credit purchased successfully; USD 10.00 remaining at verification | Use only the three-model priority in `config/network_image_generation_policy.json`; log actual usage and remaining credit |
| Google Gemini API | Blogger article generation and workflows explicitly assigned to Gemini | `GEMINI_API_KEY` | Tier 1 project billing observed; monthly spend limit shown as KRW 80,000. The limit is a cap, not a prepaid balance | Monitor spend separately; Blogger text remains Gemini-only under `docs/BLOGGER_CONTENT_POLICY.md` |

## Image API policy

Replicate is the only approved provider for newly generated images across the full network. The required order is:

1. `black-forest-labs/flux-schnell`
2. `bytedance/sdxl-lightning-4step`
3. `bytonylee/sdxl-turbo`

The same Replicate account token covers all three models. Do not create or store one token per model. Do not expose the token in source code, logs, screenshots, spreadsheets, prompts, or documentation.

Generated imagery is never mandatory for a text article. Use 0 images if every candidate fails relevance, licensing, factual-integrity, medical/legal/financial safety, or quality checks. YouTube and other visual-first jobs must stop for human review when no acceptable image is available.

## Cost-control records

For every paid image job, retain provider, model ID, destination, content URL or job ID, resolution, number of outputs, actual billed amount when available, timestamp, prompt reference, and approval result. Alert before credit exhaustion; never enable auto-reload or purchase additional credit without the owner's explicit approval.

Other credentials found in workflows are not classified as paid merely because an API key exists. Add a service to this table only after its current billing status has been verified by the owner or provider billing page.
