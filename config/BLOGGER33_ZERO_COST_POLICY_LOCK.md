# BLOGGER33 ZERO-COST POLICY LOCK

Status: **CANONICAL / LOCKED**
Effective: 2026-09-18
Scope: All 33 Blogger / Blogspot publishing destinations

## Non-negotiable publishing policy

### Text
- Blogger33 article writing must use a **zero-cost / free text engine only**.
- Paid OpenAI API use is forbidden.
- Paid Gemini API use is forbidden.
- Any paid text API/provider is forbidden.
- There must be **no automatic paid fallback**.
- If the approved free text engine is unavailable, quota-limited, misconfigured, or fails the quality gate, that site's publication must be held/failed without spending money.
- One site's text failure must never block the other Blogger sites.

### Images
- Use **copyright-safe free images only** when a relevant image is available.
- Paid image generation is forbidden.
- Paid stock-image acquisition is forbidden.
- There must be **no automatic paid image fallback**.
- If no suitable free image is available, publish the article **without an image**.
- Image absence must never be a publication hard failure.

### Quality / AdSense
- Zero cost does not waive quality requirements.
- One Blogger = one clear specialist topic.
- Labels: 1–3 highly relevant labels only.
- Golden Keyword must fit the site's locked topic and must not materially duplicate existing search intent.
- Exposed prompts, placeholders, fabricated experience, thin/repetitive content, and irrelevant images are forbidden.
- Actual Blogger Post ID + public URL are required for a successful publication receipt.

## Change control
This policy may not be weakened by legacy workflows, environment variables, fallback providers, or old configuration. Any code path that could silently spend money on Blogger33 text or images must fail closed instead.
