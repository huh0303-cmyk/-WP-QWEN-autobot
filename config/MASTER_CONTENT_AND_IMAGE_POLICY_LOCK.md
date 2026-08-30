# MASTER CONTENT + IMAGE POLICY — LOCKED

Status: LOCKED / GitHub source of truth

This file freezes the approved network-wide content writing and image generation architecture. Do not change these rules silently. Any future change requires an explicit user instruction and a new GitHub commit.

## 1. Content writing pipeline

Scope: WordPress, Blogger, Tistory, newsroom content where applicable, YouTube scripts, SNS copy.

1. Keyword and search-intent selection.
2. Verify current official sources first when freshness or YMYL accuracy requires it.
3. Gemini 2.5 Flash writes the first draft by default.
4. Run structural and quality gates.
5. If Gemini generation fails or the draft fails quality/policy/format gates, route to ChatGPT/GPT for recovery and rewrite.
6. Claude performs final editorial, grammar and quality audit. Claude is an auditor, not the routine bulk first-draft writer.
7. Validate SEO structure and metadata.
8. Save only as DRAFT / PRIVATE / AWAITING_APPROVAL. No automatic public publishing under this master policy.

### Claude audit responsibilities

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

Claude must not invent facts while editing. Material factual uncertainty goes back to source verification. Failed audit => REWRITE_REQUIRED or QUALITY_FAIL.

## 2. Image generation pipeline

Scope: WordPress 27, Blogger 27, YouTube and SNS.
Provider: Replicate.
Credential: REPLICATE_API_TOKEN.

Strict generation order:

1. FLUX.1 Schnell — black-forest-labs/flux-schnell
2. SDXL-Lightning 4-step — bytedance/sdxl-lightning-4step
3. SDXL Turbo — jyoung105/sdxl-turbo

If a model fails or is unavailable, try the next model in the strict order above. If all three fail, use zero images or QUALITY_FAIL and send for review.

Hard rules:

- image must be relevant to the article/video topic
- free-stock fallback is forbidden
- generic filler images are forbidden
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
