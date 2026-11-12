# Seoul Journal reference-video style contract
Reference: https://www.youtube.com/shorts/1DE5qibASjc
Status: REFERENCE LINK RECORDED; video frames/audio NOT YET DIRECTLY INSPECTED. Do not assert exact shot timings, colors, fonts, soundtrack or other reference-specific properties until inspected.

## Instruction hierarchy
- Owner wants Seoul Journal political Shorts visually and rhythmically close to the reference, while preserving Seoul Journal branding and original independently produced editing.
- Apply existing docs/seoul-journal-shorts-production-contract.md and docs/SEOUL_JOURNAL_JISOO_POLITICAL_SHORTS_STANDARD_2026-11-09.md, subject to latest owner instructions and rights checks.
- Do not copy original video, audio, broadcaster watermark, copyrighted music, graphics or unlicensed footage. A similar journalistic editing style is the target.

## Baseline render gate
- 1080x1920, 9:16, political confrontation as source-backed news, named actual politicians and authentic rights-cleared imagery.
- Opening hook <= 2s, visual change ~1.5–2.5s, multiple distinct images, subtle motion, high-contrast synced 2–3-word captions without face-blocking rectangles.
- Accurate attribution of quotations, counterstatements, context, date, and source. No invented dialogue or implied live video.
- Six verified randomized voice profiles, using shared TTS chain Fish -> Qwen -> Edge where available; check intelligibility and sync.
- Neutral viewer question outro 3–5s. Never fabricate a live poll or percentages.
- First one episode PRIVATE; attach MP4, thumbnail, caption/transcript, evidence URLs, image licenses and QA result. PUBLIC daily scheduling only after owner approval.

## Reference inspection checklist (pending)
Record: total runtime, shot-by-shot timings, first-2-second hook, font family/size/color, captions position, music/SFX, photo vs original video proportion, transitions, politician naming, end-card, branding.
No unsupported claim of exact matching without inspecting actual video.

## Current implementation gaps observed
- scripts/seoul_journal_shorts_pipeline.py selects first eligible Naver politics card instead of prioritizing Lee/Han confrontation.
- Its TTS chain is Fish -> Edge, missing Qwen; another docs file still prescribes ElevenLabs contrary to newer shared TTS policy.
- Generic branded-background fallback conflicts with politician-photo-first standard.
- Historical private-only and daily-public instructions conflict. Gate first canary PRIVATE, do not enable PUBLIC blindly.
