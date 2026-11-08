# 서울저널 공개 발행 운영원칙 — 2026-11-09 KST
Owner approval: 2026-11-09, current conversation. Supersedes conflicting private-only, daily-seven, ElevenLabs-only and general-sports rules for Seoul Journal.
Channel: 서울저널 @seouljournal1 / UChRUdHZlXSjftAqBtdDNEWA.

## Cadence and topics
- Target three PUBLIC Shorts/day, KST morning 08:00–10:00, midday 13:00–15:00, evening 19:00–22:00.
- Existing deterministic date/slot random gate selects a 10-minute-grid time. Actions can run late; public slot marker prevents repeated publication.
- Morning politics, midday social hot issues, evening current affairs/hot issues. Politics can fill a weak social news queue.
- Sports is strictly 한국시리즈 only. Do not force unrelated regular-season baseball, international sports or fabricated current games into the feed.
- No suitable fresh supported story: fail visibly rather than invent or replay old news. Three is the daily target, not guaranteed output when dependencies fail.

## Presentation and voice
- Approved concept: original Seoul Journal navy/yellow/white/red, large real subject photograph, short specific headline and changing captions.
- Use only relevant licensed/PD photographs. Label archival photos and record source, author, date, license and edits. Never publish concept-generated politician images as real news photographs.
- Narration speed exactly 1.2x through FFmpeg atempo. Central priority Fish Audio -> local Qwen3-TTS -> Edge-TTS.
- Qwen requires an installed model and QWEN3_TTS_COMMAND. Without that configured adapter, proceed to Edge and record the reason. No claim that Qwen is installed.
- Current portrait registry covers 이재명 only; other subjects use original graphics until their assets are individually cleared.
- Gemini-only automatic drafts. Manual first release is independently written and source-reviewed; no GPT/Claude draft used.
- Hook in first sentence; concrete factual title/question. Attribute allegations, material rebuttals and uncertainties. Never imply a hypothetical clash, invented quote or proven guilt.
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
3. Select a Naver report with article timestamp <=36h and sufficient body; reject stale, opinion, ad and non-Korean-Series sports.
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
