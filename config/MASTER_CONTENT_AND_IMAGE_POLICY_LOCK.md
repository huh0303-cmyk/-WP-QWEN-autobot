# MASTER CONTENT + IMAGE POLICY — LOCKED

Status: LOCKED / GitHub source of truth

The mandatory site-by-site persona, tone, do/don't and platform overlays are defined in `config/SITE_EDITORIAL_PLAYBOOKS.md`. They are part of this lock, not optional suggestions.

This file freezes the approved network-wide content writing and image generation architecture. Do not change these rules silently. Any future change requires an explicit user instruction and a new GitHub commit.

## 1. Content writing pipeline

Scope: WordPress, Blogger, Tistory, newsroom content where applicable, YouTube scripts, SNS copy.

1. Keyword and search-intent selection.
2. Verify current official sources first when freshness or YMYL accuracy requires it.
3. GPT-5 mini writes the first draft by default.
4. Run structural and quality gates.
5. If the draft fails quality/policy/format gates, GPT-5 mini rewrites it.
6. Gemini 2.5 Flash performs the independent editorial, factual and quality review after the GPT draft and any required rewrite.
7. Validate SEO structure and metadata.
8. Save only as DRAFT / PRIVATE / AWAITING_APPROVAL. No automatic public publishing under this master policy.

### Network-wide engine default lock (2026-09-02)

- WordPress 27, Blogger 27, Tistory 5 and newsroom content use GPT-5 mini as the default first-draft writer.
- The control center, Google Sheet job defaults and execution workflows must display and use GPT-5 mini as their routine writing default.
- Claude is not part of the WordPress, Blogger or Tistory writing/review pipeline.
- Control-center cards, stored job defaults, workflows and execution code must agree with this order: GPT-5 mini draft/rewrite -> Gemini 2.5 Flash independent review.

### Gemini independent review responsibilities

- grammar and spelling
- awkward, translated or AI-sounding phrasing
- readability and sentence flow
- title naturalness
- H2/H3 structure
- repetition and mass-template patterns
- site persona, language and tone consistency
- search-intent alignment
- labels/categories/metadata consistency
- unsupported or suspicious claims
- internal contradictions
- final editorial quality gate

Gemini must not invent facts while reviewing. Material factual uncertainty goes back to source verification. Failed review => REWRITE_REQUIRED or QUALITY_FAIL.

### Network-wide title ban — `Unlock` (LOCKED 2026-09-02)

- WordPress 27, Blogger 27 and Tistory 5 must never generate, save, schedule or publish a title containing `Unlock`, regardless of capitalization.
- `Unlock the Secrets`, `Unlock Your...`, `Unlocking...` and similar mass-produced formulas must be rewritten as specific, natural headlines.
- The ban is enforced in every writer prompt and again in the deterministic pre-save gate. Model approval cannot override it.
- Violation result: `TITLE_QUALITY_FAIL`; the draft remains unsaved and unpublished until its title passes recheck.

### Network-wide mass-produced AI phrase ban

- Title formulas including `Ultimate/Complete/Comprehensive Guide`, `Discover/Unleash the Power`, `Navigate the Complexities/Landscape`, `Your Path to`, `Mastering the Art of`, `Revolutionize`, `Game Changer`, `Everything You Need to Know`, `Secrets Revealed/Unveiled`, `The Future of`, `완벽 가이드`, `궁극의 가이드` and `총정리` are forbidden alongside every `Unlock` variation.
- Body filler including `In today's fast-paced/dynamic world`, `In the ever-evolving landscape`, `Delve into`, `Embark on a journey`, `A tapestry of`, `In the realm of`, `Look no further`, `Whether you're a seasoned`, `Elevate your experience`, `Seamlessly navigate`, `It's important to note`, `As we all know`, `In conclusion` and `Without further ado` is forbidden.
- Title violations are `TITLE_QUALITY_FAIL`. Body violations are `REWRITE_REQUIRED`. Neither may be saved, scheduled, emailed for approval or published before correction.
- These deterministic gates apply equally to Gemini and GPT output across WordPress 27, Blogger 27 and Tistory 5.

## 2. Image generation pipeline

Scope: WordPress 27, Blogger 27 and Tistory 5. YouTube retains its separate FLUX-only thumbnail lock.
Provider: Replicate.
Credential: REPLICATE_API_TOKEN.

Strict generation order:

1. SDXL-Lightning 4-step — bytedance/sdxl-lightning-4step
2. FLUX.1 Schnell — black-forest-labs/flux-schnell
3. Both unavailable or rejected — PASS and continue without an image

If SDXL Lightning fails or is unavailable, try FLUX Schnell once. If both fail, remove the rejected image and continue with a text-only draft; image failure must not block draft creation, review email or later publication.

Hard rules:

- image must be relevant to the article/video topic
- free-stock fallback is forbidden
- generic filler images are forbidden
- generated blog images must contain no visible letters, words, numbers, captions, labels, logos, watermarks or UI anywhere in the scene
- illegible pseudo-text, random glyphs, fake Hangul and Chinese/Japanese-looking dummy characters are blocking `QUALITY_FAIL` defects
- avoid documents, forms, checklists, certificates, screens, signs, books and packaging whenever they could invite the image model to fabricate writing
- if any text or pseudo-text is visible, reject that image and try the next approved model; if both fail, continue text-only
- do not fabricate official documents
- do not create misleading medical/legal/financial evidence
- image/provider/license/cost logging is required
- Blogger requires human review before publication
- playlist thumbnails retain the existing-frame-only exception; do not generate thumbnail video

### YouTube playlist thumbnail lock (2026-08-30)

- every new playlist source image and thumbnail must be generated with FLUX.1 Schnell
- Drive thumbnail-bank, free-stock, SDXL, Gemini image and OpenAI image fallback are forbidden
- the result must look like authentic professional photography; obvious AI anatomy, plastic skin,
  malformed hands, duplicated objects, fake reflections, CGI or illustration styling is QUALITY_FAIL
- generate exactly one 16:9 source image and reuse it as the full-video still and thumbnail source
- `Cafe_Romantic` uses a sweet affectionate couple photo series, including tasteful black-and-white
  photography; the final overlay is the large `Cafe_Romantic` brand with a waveform below
- Healing uses rain-heavy jungle, forest, stream, river, open nature or temple-in-nature photography;
  no thumbnail text
- Cafe Music uses a close-up seasonal drink with an open sea, coast, Eiffel Tower or other landmark
  visible through a large window; no commercial cafe brand marks
- MBB uses elegant instruments and theme-led classical photography; thumbnail text is omitted or kept
  extremely short and must never overlap
- K-pop uses high-end realistic Korean pop editorial photography
- every playlist channel runs once after a random 2-3 day interval, never a fixed two-day cadence
- the next KST execution time uses an irregular random minute inside the allowed window; round
  five-minute marks and the channel's previous HH:MM are excluded so repeated machine-like timestamps
  are forbidden

## 3. Change control

These two configuration files are the executable master references:

- config/content_writing_policy.json
- config/network_image_generation_policy.json

This lock document summarizes the approved rules and exists to prevent accidental policy drift. If code, workflows or legacy scripts conflict with these files, the conflicting implementation must be corrected rather than silently changing this policy.
