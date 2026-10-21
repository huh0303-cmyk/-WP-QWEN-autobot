# SEOUL JOURNAL — Political & Current-Affairs Shorts Workflow
**Date:** 2026-10-21  
**Status:** Workflow specification only. No production code, API connection, audio generation, video export, account linking, or publishing is claimed complete.

## 1. Reference-channel study (public analytics snapshots)

Study public examples for format and packaging, not for copying scripts, footage, thumbnails, or editorial positions.

1. **K-위인전** — https://dhesy.com/creators/UCRbI8_BjL8VrPij_Ql9l8_g  
   Snapshot shown 2026-10-08: approx. 270K subscribers, 450M lifetime views, reported lifetime average around 1.021M views/video; recent 90-day median around 570K. Format: recognizable public figure + a specific quote/reaction + one clear political tension. Treat third-party metrics as estimates and recheck YouTube directly.
2. **핫한이슈만!** — https://allsnsrank.com/youtube/channel/UCpw4o6HRpDyLGa8XNKrMAkA  
   Snapshot shown 2026-10-13: approx. 207K subscribers, 294.8M lifetime views, 790 uploads; third-party page reports an average around 373K views/video and several 1M+ clips. Format: rapid, frequent Shorts; strong “why / difference / reason” framing; often adapts sports and public-figure disputes. Do not assume its political clips alone drive all channel views.
3. **빛그린대한민국** — https://allsnsrank.com/youtube/channel/UCw3F3aOzIiALLPpHdIGzr1A  
   Snapshot shown 2026-10-13: approx. 100K subscribers, 82.7M lifetime views, 273 uploads; third-party page reports average around 303K views/video and multiple 1M+ clips. Format: one recognizable person, a concrete event or quote, high-contrast emotional stakes, frequent uploads. It appears politically opinionated; Seoul Journal should learn packaging mechanics but retain factual, clearly attributed, non-partisan reporting.
4. **Additional format comparator: 정치본색** — https://dhesy.com/en/creators/UC53BN2jwlduA5rHwq6FNvUw  
   Snapshot shown 2026-10-08: approx. 128K subscribers and 85.3M views; recent Shorts averages are lower than the channel’s lifetime average, illustrating why each recent video must be reviewed rather than relying on channel totals.

**Research limitation:** this first pass reviewed public channel analytics and listed top/recent video titles, not every video frame or actual audio track. Do not claim that the creators use ElevenLabs or infer voice IDs from the sound alone. A follow-up manual review should sample 10–15 top-performing recent Shorts per reference channel and record first-frame design, title/thumbnail hook, runtime, cuts, caption density, source attribution, narration style, and public view count.

## 2. Seoul Journal positioning

- Brand: **서울저널 | SEOUL JOURNAL**, handle **@seouljournal1**.
- Visual system: deep navy base, white headline, restrained red/yellow accent; high-contrast, mobile-first.
- Core promise: fast, understandable, source-grounded current affairs.
- Avoid copying a competitor’s exact title, thumbnail composition, narration, footage, or script.
- Political balance: cover stories based on news value and evidence, not whether a figure is liked or disliked. Include relevant responses and context. Distinguish confirmed facts, allegations, quotes, and analysis.

## 3. Thumbnail / first-frame system (highest priority)

For vertical Shorts, the first frame is the thumbnail-like hook; also prepare a custom 9:16 cover where the platform allows it.

1. One main, verified person or one clear scene only; no collage of unrelated politicians.
2. Keep the face large and unobstructed; place a short headline in a separate high-contrast area.
3. Use 3–7 Korean words where possible; one question or tension only.
4. Show the news angle, not a verdict: e.g. “국감서 나온 이 발언”, “발표와 실제 조치는?”, “쟁점은 무엇인가”.
5. Add a small source/date label only when helpful; do not clutter the cover.
6. Generate two cover variants for internal review. Do not publish both simultaneously just to test.
7. Never fabricate a quote, expression, scene, headline, or photo context. If an image is illustrative or AI-generated, label it where a reasonable viewer might mistake it for documentary footage.
8. Maintain a rights log for each photo/video: original URL, publisher/photographer, license/permission, download date, and intended use. A politician being famous or a photo being publicly viewable does **not** automatically mean it is free to reuse. Prefer official government/assembly press media with explicit reuse terms, licensed stock, or permission; check each asset’s terms and attribution requirements.

## 4. Voice library — shortlist, then verify IDs

Official ElevenLabs Korean TTS page lists these Korean-capable voice names: **Anna Kim** (tender/calm/clear), **Hyunbin** (diplomatic/clear/measured), **Bin** (measured/serious), **Chris** (warm/clear), and **Hyuk** (cold/clear). These are a listening shortlist, not a confirmed male/female roster; confirm the current voice profile, Korean pronunciation, gender presentation, commercial-use terms, and exact voice ID inside the account before using them. Voice-library listings and IDs can change.

- **Signature anchor:** choose one voice after a blind listening test and use it on about 50–60% of clips for recognizable brand continuity.
- **Alternates:** choose two additional voices of each presentation (male-presenting and female-presenting) only after auditioning actual Korean samples. Rotate by story format, not randomly on every sentence.
- **Provisional audition list:** Hyunbin, Bin, Chris, Hyuk, Anna Kim, plus two additional Korean voices selected from the live account library. Do not hard-code voice IDs until the owner supplies/securely configures them and the IDs are checked.
- Suggested role mix: signature female lead for explainers; signature male lead for urgent headlines; alternates for interview/quote explainers and second voice. A two-voice dialogue is optional, not mandatory.
- Store only non-secret metadata in the repo: voice_label, voice_id, presentation, role, approved, sample_date. Store the API key only in a VPS secret/environment variable such as ELEVENLABS_API_KEY. Never put the key in GitHub, issue comments, chat, logs, or screenshots.

Official Korean TTS page: https://elevenlabs.io/text-to-speech/korean  
API authentication: https://elevenlabs.io/docs/ko/api-reference/authentication  
API keys: https://elevenlabs.io/docs/overview/administration/workspaces/api-keys

## 5. Production pipeline

1. **Trend discovery:** collect candidate topics from current reporting and trend signals; record timestamp, source, claim, evidence strength, affected people, and whether the issue is still current.
2. **Source verification:** use at least two credible sources for consequential disputed claims where available; primary document/official statement first. Keep URLs and exact publication dates in the job record.
3. **Editorial brief:** define the one-sentence news angle, what is confirmed, what is alleged, response/context, and what remains unknown.
4. **Script:** 25–45 seconds by default; hook in first 1–2 seconds; one issue per Short; clear attribution; no invented quotes, certainty, or dramatic claims unsupported by sources.
5. **Thumbnail:** generate two draft covers using only verified, rights-cleared imagery; editor checks face identity, wording, readability, and source framing.
6. **Voice:** call ElevenLabs TTS with approved voice ID; test a short sample first. No voice cloning or imitation of politicians/journalists/other real people without documented permission.
7. **Edit:** 9:16 vertical, readable Korean captions, purposeful cuts, restrained effects, no background music by default unless specifically approved; ensure captions match speech.
8. **QA gate:** script/source match, names/titles, pronunciation, audio clipping/silence, captions, image rights, misleading edits, current date, and platform rules.
9. **Preview approval:** show the owner the cover, script, voice assignment, sources, and rendered video. Default status is REVIEW_REQUIRED.
10. **Publish:** only after explicit approval and confirmed connection to the correct Seoul Journal YouTube account. Record final URL, publish time (KST), title, views at 24h/72h/7d, and any correction.
11. **Learning loop:** compare performance by hook type, face size, word count, voice, runtime, retention, viewed-vs-swiped-away, likes/comments, and source category. Change one or two variables at a time.

## 6. Job record fields

job_id, topic, trend_timestamp, sources[], claims[], script_version, voice_label, voice_id, thumbnail_a, thumbnail_b, asset_rights[], caption_file, render_path, qa_status, owner_approval, publish_status, youtube_url, views_24h, views_72h, views_7d, correction_note.

Allowed states: IDEA → SOURCES_CHECKED → SCRIPT_READY → ASSET_CHECK → VOICE_READY → RENDERED → QA_PASSED → REVIEW_REQUIRED → APPROVED_TO_PUBLISH → PUBLISHED. Failure states return only to the failed stage; never auto-publish after a failed QA check.

## 7. API / access items required from owner

1. ElevenLabs API key: create in ElevenLabs account and place directly into the authorized VPS secret manager/environment; do not paste into ChatGPT or commit to GitHub.
2. Voice IDs: choose the shortlisted voices in the account and add IDs to the private runtime configuration; IDs are not API secrets but should be verified.
3. YouTube channel: confirm the channel is **서울저널 / @seouljournal1** and connect the correct Google account through OAuth in the publishing environment. Do not share Google passwords or OAuth refresh tokens in chat.
4. Video renderer/storage: confirm which existing London Project renderer and output directory should be used; do not assume a working renderer until tested.
5. Vrew: use as manual fallback unless official supported server-side API access is verified. Do not rely on brittle desktop automation as if it were a supported API.

## 8. Initial experiment

Create 3 pilot Shorts from 3 different topic formats (a current political statement, a parliamentary/public accountability issue, and a high-interest public-policy issue). For each, prepare two cover variants and one approved narration voice; vary the voice across pilots. Review with the owner before publishing. After 24/72 hours, compare retention and viewed-vs-swiped-away before changing the default voice or thumbnail template.

## 9. Done / not done boundary

This file is a committed workflow specification. It does not mean the channel videos were downloaded, voice samples were listened to, ElevenLabs was connected, IDs were saved, an MP4 was rendered, or posts were published.
