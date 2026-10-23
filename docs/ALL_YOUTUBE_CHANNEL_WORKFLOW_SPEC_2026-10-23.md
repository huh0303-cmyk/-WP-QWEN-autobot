# London Project — YouTube Channel Workflow Specification
Last updated: 2026-10-23
Status: Operating specification; this document does not itself execute uploads or prove that credentials, media files, or scheduled jobs are available.

## Global safety and publishing rules
- Preserve existing content. Do not delete or overwrite existing videos, source music, or project files as part of routine operation.
- Upload new videos as **private** by default. Never automatically switch them to public without explicit authorization.
- Randomize publication times within configured permitted windows; avoid predictable minute patterns and avoid scheduling collisions where practical.
- Track each item with a stable job ID, channel ID, source asset references, content hash, upload status, YouTube video ID, and timestamps.
- Make retries item-scoped and idempotent: retry only the failed item; do not duplicate successful uploads.
- Do not claim a job is complete until the actual output/upload state has been checked.
- Use only media with verified usage rights. A public-domain composition does not automatically make a particular modern recording public domain.
- Do not start or trigger production/upload workflows merely by updating this specification.

## 1. Language learning channels — 10 channels, every channel daily
### Channels
- German Survival — @SIS_GermanSurvival
- Portuguese Survival — @Portuguese_survival
- Japanese Survival — @SIS_Japanese1
- Vietnamese Survival — @SIS_VietnameseSurvival
- Spanish Survival — @SIS_SpanishSurvival
- French Survival — @SIS_FrenchSurvival
- English Survival — @English_survival
- Italian Survival — @SIS_ItalianSurvival
- Chinese Survival — @SIS_ChineseSurvival
- Seoul International University TOPIK Center — @seoul_topik1

### Cadence
- Each of the 10 channels publishes **one video every day**: 10 videos/day, 70 videos/week across the group.
- Randomize each channel's time independently within its configured local publishing window.
- Keep uploads private unless a separate explicit public-release rule is approved.

### Nine foreign-language channels
- Lesson 1: engaging orientation video covering major language-using countries, approximate global speaker population with a dated reliable source, alphabet/script and pronunciation, and interesting language facts.
- From lesson 2: beginner vocabulary photo-and-audio quiz format.
- Initial target: 100 quiz videos total across the nine channels, with 3 questions per video (300 questions total), subject to the production plan being configured per channel.
- Each quiz: clear real-object photo; natural native-speaker pronunciation; question and three answer choices; 6-second countdown; answer reveal with restrained visual celebration and sound effect; repeat the word pronunciation.
- After the 100 beginner vocabulary videos, move to basic everyday expressions.
- Use natural, clearly articulated native voices. Multiple distinct native voices may be randomized when real voice options are verified and quality-tested. Do not use untested or obviously poor robotic output.
- Use accurate spelling, translations, and pronunciation. Rights-check images, audio, and generated assets.

### Korean TOPIK Center (separate curriculum)
- Do not use the beginner survival-word curriculum.
- Lesson 1: Korean/TOPIK course orientation.
- Subsequent lessons: intermediate TOPIK vocabulary appropriate to the target level, with contextual meaning/examples as useful.
- Learner hears a natural Korean native-speaker pronunciation and repeats it **six times** per target word.
- The six repetitions are a pronunciation-learning exercise, distinct from the 6-second quiz countdown used by the other channels.
- Keep vocabulary level consistent with intermediate TOPIK learners.

## 2. Health channels — separate editorial workflows
- Japanese Health Clinic — @Health_Clinic_Japan
- Health Clinic USA — @health_clinic_usa
- Localize language, units, examples, and trusted references to the intended audience.
- Use evidence-based, non-sensational health education; distinguish general information from diagnosis or individualized treatment.
- Review factual claims, source dates, contraindications and safety-critical wording before rendering.
- Avoid unsupported promises, fear-based claims, and misleading thumbnails.
- Use private uploads by default and item-scoped retries. This specification does not set a new publishing cadence for health channels.

## 3. Playlist channels — 5 channels, 3 videos per channel weekly
### Cadence
- Each playlist channel publishes **3 videos per week**: 15 videos/week across the group.
- Randomize publication times; avoid collisions where practical.
- Initial trial: several weeks, then compare click-through rate, views, watch time/retention, and production reliability before changing cadence.
- Upload privately by default; do not switch to public automatically.

### Channel concepts
1. **Starbucks Vibes** — cafe jazz, soft blues, relaxing background music, coffee-shop ambience, work/study/chill.
2. **K-pop Studio 7** — emotional K-pop-inspired, acoustic pop and ballad moods. Use original/licensed tracks; do not imply a track is an official K-pop hit unless authorized and accurate.
3. **Healing** — rain, flowing streams, birdsong, temple bells, and wind chimes. Keep nature sound prominent, avoid abrupt loudness changes, and use visuals suited to calm nature/temple settings.
4. **Cafe Mozart** — classical repertoire and instrumental forms including works by Bach, Mozart, Sarasate, Brahms, Beethoven and others; sonatas, solo works, concertos, chamber music, piano, cello, violin and flute. Verify the recording's rights independently from the composition's rights.
5. **Cafe Romantic** — romantic piano, soft instrumental music, sunset/seaside/candlelit ambience.

### Distinct thumbnail art direction
Use a shared quality standard (high contrast, readable on mobile, restrained text, consistent export quality), but **each channel must have its own visual mood**:
- Starbucks Vibes: warm coffee brown/gold, cafe interior, coffee and city lights.
- K-pop Studio 7: pink/violet, blossoms/window light, dreamy contemporary feeling.
- Healing: deep green, mist, rain, streams, birds, temple/wind-chime details.
- Cafe Mozart: dark wood, amber/gold, piano and classical instruments, elegant concert-room feeling.
- Cafe Romantic: coral/rose/sunset colors, sea view, candles and romantic terrace.
Do not copy another creator's thumbnail or brand assets. Do not show a LIVE badge unless the content is actually live. Use original or appropriately licensed images.

## 4. Music and media sourcing
- The user has authorized considering files in the desktop folder named `음악원본`. Access to that local folder must be verified at execution time; do not assume it is currently mounted or accessible.
- The user has indicated a Suno subscription through next year and has offered access. Use Suno only when the authenticated session/access is actually available, and confirm applicable rights/terms for the track and generation date before monetized use.
- Prefer reviewing existing original music assets before generating new tracks.
- Maintain an asset ledger with filename, duration, format, hash, intended channel, rights/source notes, and use history.
- Do not reuse an asset across channels unless the rights allow it and the reuse is intentional. Detect exact duplicates and flag near-duplicates for review.
- Do not download from third-party sources unless licensing/permission is clear.

## 5. Shared production pipeline
1. Select channel-appropriate topic/music and create a job record.
2. Verify source file availability, rights, language/content accuracy, and duplication.
3. Generate or assemble audio, visuals, captions/metadata, and thumbnail.
4. Render video with validated dimensions, duration, audio level, and playable output.
5. Run content-specific QA (language pronunciation/answer correctness, health safety review, or playlist track/rights review).
6. Upload as private to the verified target channel.
7. Confirm upload success, video ID, privacy status, title, and thumbnail.
8. Record result and logs; retry only failed items without duplicating successful uploads.

## 6. Reporting and verification
- Report separately: planned, produced, rendered, uploaded-private, scheduled, and publicly published.
- Never treat a plan file or successful workflow start as proof that a video was uploaded.
- Do not report a GitHub workflow as active/working until a real run has been checked.
- Credentials and tokens must remain in GitHub Secrets or approved secure storage, never in this document.
- This document defines operating rules only; executable workflows, credentials, schedules, local folder access, and channel permissions must be independently checked and configured.
