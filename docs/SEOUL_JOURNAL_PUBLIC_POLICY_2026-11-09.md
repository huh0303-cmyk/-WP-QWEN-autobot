# 서울저널 공개 발행 운영원칙 — 2026-11-09 KST
Owner approval: 2026-11-09, current conversation. Supersedes conflicting private-only, daily-seven, ElevenLabs-only and general-sports rules for Seoul Journal.
Channel: 서울저널 @seouljournal1 / UChRUdHZlXSjftAqBtdDNEWA.

## Cadence and topics
- Target three PUBLIC Shorts/day, KST morning 08:00–10:00, midday 13:00–15:00, evening 19:00–22:00.
- Existing deterministic date/slot random gate selects a 10-minute-grid time. Actions can run late; public slot marker prevents repeated publication.
- Morning politics, midday social hot issues, evening current affairs/hot issues. Politics can fill a weak social news queue.
- Sports includes 한국시리즈, 프로야구/KBO, 프로축구/K리그 and 배드민턴. Use verified current reports; never invent games or results. Every other evening prioritizes sports.
- No suitable fresh supported story: fail visibly rather than invent or replay old news. Three is the daily target, not guaranteed output when dependencies fail.

## Presentation and voice
- Approved concept: original Seoul Journal cards with a large relevant person's photo, large phone-readable headline, changing captions and distinct compositions.
- Each Short randomly selects one of five in-house layouts: split red rail, oversized quote, full-width bottom strip, angled label, or face-left panel. Store the style in the render receipt and keep it consistent inside that one Short. Change headline placement, scale, palette and panel shape across uploads. Benchmark abstract composition mechanics from 500k+ view Korean news Shorts; do not copy their images, wording, logos or footage, and do not promise view counts.
- Resolve the main person from the source/video title, not incidental mentions in article body or AI narration. Use only that subject's cleared assets. If no matching portrait is cleared, stop and report it; never fall back to Lee Jae-myung or a Japanese/other unrelated person. Label archival photos and record source, author, date, license and edits. Never present generated politician images as real news photographs.
- Narration speed exactly 1.2x through FFmpeg atempo. Central priority Fish Audio -> local Qwen3-TTS -> Edge-TTS. Select randomly from two male and two female Korean voice profiles per Short, then record selected voice/provider in render receipt. Fish uses voice-specific environment IDs only when configured; no claim that Fish voices were auditioned. Qwen still requires a configured voice/model adapter.
- Qwen requires an installed model and QWEN3_TTS_COMMAND. Without that configured adapter, proceed to Edge and record the reason. No claim that Qwen is installed.
- Minimum three distinct cleared subject photos per Short, target 3–5. Alternate 1.00–1.10 zoom in/out with stationary transparent text overlay. No single-photo still fallback. 이재명 photos are discovered by exact named Commons titles with license records; other subjects require reviewed photo_files. Missing assets stop production visibly.
- Gemini-only automatic drafts. Manual first release is independently written and source-reviewed; no GPT/Claude draft used.
- Vary narration structure among factual hook, open question, exact attributed quote, scene-setting and claim/response contrast. Vary sentence length and pacing; no stock intro/outro. Hook in first sentence; attribute allegations, material rebuttals and uncertainties. Never imply a hypothetical clash, invented quote or proven guilt.
- Subject matching/thumbnail/voice fixes committed to the production scripts on 2026-11-09; output receipt records the chosen style and voice.
- Thumbnail JPEG is generated plus matching vertical cover embedded. YouTube may reject API custom thumbnails for this channel/Shorts; log that separately and do not misreport thumbnail application.

## Benchmark evidence (public vidIQ retrieval 2026-11-09 KST)
Individual short-duration videos, not channel aggregate views:
- 조선일보 https://www.youtube.com/watch?v=9HUYi7z_R40 — 1,575,251 views, 44 sec.
- 조선일보 https://www.youtube.com/watch?v=wYWdFa1eX3U — 1,198,882 views, 32 sec.
- 조선일보 https://www.youtube.com/watch?v=iTFLp8jieKU — 1,058,984 views, 59 sec.
- 매일신문 https://www.youtube.com/watch?v=imD1Kcv2HZc — 722,432 views, 1m41s; Shorts classification not independently verified.
- 매일신문 https://www.youtube.com/watch?v=wacaEguWetc — 1,600,861 views, 13m02s; landscape thumbnail reference only, NOT a qualifying Short.
These are research observations, not a promise of future views. Current implementation borrows only abstract clear-subject / specific-question mechanics. Full clip/audio/visual audits remain incomplete; do not claim 500k benchmark production fully audited. No copied footage, branding or voice.
Public vidIQ research during this session used 20 credits across four searches.

## Workflow and verification
1. Check exact OAuth channel and previous 100 uploads.
2. Check public day-slot marker and source URL before generation.
3. Select a Naver report with article timestamp <=36h and sufficient body; reject stale, opinion, ad and out-of-scope sports.
4. Generate original Gemini summary with claims/rebuttals, title and 6–10 caption beats.
5. Clear portrait -> central TTS -> 1.2x audio -> 9:16 MP4 + JPEG.
6. Recheck public source/slot duplicates before insert; serialize public workflows.
7. Insert public, save receipt immediately, read back exact channel and privacy. Record thumbnail result independently.
8. Preserve source package, photo rights, audio provider, preview/video and receipt as Actions artifacts.

## First public release
- https://www.youtube.com/shorts/oEZaFVnqKR0
- Title: 이재명이 지명한 이용철…왜 대장동 공방에 섰나? #Shorts
- Source: https://n.news.naver.com/mnews/article/028/0002831263 (2026-11-08 21:16 KST).
- 51.223 seconds rendered, 1080x1920, 8 caption cards, Edge-TTS fallback, 1.2x.
- Public privacy confirmed by YouTube API after insert. Custom thumbnail API did not apply (HttpError); embedded first-frame art exists. This is not proof that YouTube selected that frame as the Shorts cover.
- Replaced none; earlier private prototype LAwSW_CIjlg remains private.
- Auth fix used valid client 886253028121… and matching token in FISH_AUDIO_API_KEY environment, dedicated SEOUL_JOURNAL_* names. The open shorts-client 21786518147… was not changed; no raw credential in git.

## Runtime verification
PR #273 merged (1a39cba65feebe5f682518afbea3130eee67970f). Full no-extra-publication Actions run https://github.com/huh0303-cmyk/-WP-QWEN-autobot/actions/runs/42498013145 succeeded: fresh article -> Gemini draft -> Fish Audio -> 1.2x render -> 9 captions -> artifact, 36.643 seconds. Scheduled end-to-end public insert has not occurred yet; direct public insert/readback succeeded for the first release.

## 2026-11-09 presentation revision
- Shorts-first channel: full-frame real photos, colored yellow/white outlined text on transparent background, face clear, category below portrait focal area. 16:9 is a separate thumbnail composition.
- Public revision of oEZaFVnqKR0 authorized; allow exactly its motion-v2 marker, preserve all other source/slot duplicate guards. Old public video is not automatically deleted.
- Native YouTube scheduling accepts explicit future ISO8601 timestamp, uploads private with publishAt, then requires schedule readback. Saving workflow settings alone does not prove a scheduled video exists.


## Current asset gate
- Oh Se-hoon: use only a verified Commons portrait with the corresponding license metadata.
- Lee Yong-cheol: official DAPA portrait requires a confirmed KOGL Type 1 reuse mark or separate reuse authorization. Until confirmed, production stops with LICENSE_REVIEW_REQUIRED; never substitute Lee Jae-myung.
- Retrofitting an already-public Short requires a newly rendered, reviewed package and a YouTube thumbnail update or replacement publication; a code commit alone does not change existing uploads.
