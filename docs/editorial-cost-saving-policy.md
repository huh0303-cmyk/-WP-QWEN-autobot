# Article cost and image selection policy — 2026-09-11

User priority: keep article publishing running; video generation remains disabled.

Writing stays GPT-5-mini. Standard USD per million tokens: input 0.25, output 2.00 (cached input 0.025). Gemini 2.5 Flash is 0.30/2.50, so it is not a price reduction. Compare identical prompts and total billable output (including reasoning) before any model migration. Gemini free tier is an account/project condition, not something guaranteed by a model name or a prepaid balance. Do not introduce search grounding or multiple-model rewrites automatically.

Images: eligible article workflows explicitly set STOCK_IMAGES_ENABLED=true and supply existing PEXELS_API_KEY, PIXABAY_KEY and GH_ASSET_TOKEN. Try one Pexels query, then one Pixabay query. Accept only landscape photos >=1000px with all meaningful subject tokens in source metadata. No generic keyword broadening or paid vision scoring. Metadata is a conservative filter, not a guarantee of exact visual matching. Named events and patient/crime contexts bypass generic stock; newsroom documentary-source checking remains independent.

Search responses are cached 24h. Selected stock photos are saved to owned assets before embedding; Pixabay permanent hotlinks are forbidden. Article body credits source photographer/provider and license. Source records go to artifacts/stock-image-receipts.jsonl. Failures expose exception types only, never API-key-bearing request URLs.

No suitable stock / provider inaccessible / hosting failure -> SDXL Lightning once -> FLUX Schnell once -> existing no-image review/publication behavior. Max one selected output. Other expensive image providers and video flows are not enabled. SDXL public estimate $0.0014 per run (runtime-dependent); FLUX Schnell $0.003 per output. Both attempted: indicative $0.0044, not a guaranteed invoice. Images create separate informational receipts; do not add these to the old $0.03 bundle reservations or that would double count.

Example only: 3,000 input + 2,000 billed output tokens, one writing call per article: GPT $0.00475; Gemini 2.5 Flash $0.00590. At 3,600 articles/month, GPT writing $17.10; SDXL every article ~$5.04. If 70% have suitable free photos, remaining SDXL ~$1.512, total ~$18.612 instead of ~$22.14. Retry, reasoning, failed calls, other pipelines, taxes and FX are excluded. Real savings require observed stock match rate; no 70% guarantee.

Sources:
- https://developers.openai.com/api/docs/models/gpt-5-mini
- https://ai.google.dev/gemini-api/docs/pricing
- https://replicate.com/bytedance/sdxl-lightning-4step
- https://replicate.com/black-forest-labs/flux-schnell/api
- https://www.pexels.com/api/documentation/
- https://pixabay.com/api/docs/
