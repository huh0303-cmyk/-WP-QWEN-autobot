# Seoul Journal Daily Shorts workflow

This workflow prepares a seven-item editorial queue; it does not publish automatically unless a verified Seoul Journal upload credential is configured in a future upload stage.

## Editorial contract
- 5 golden-keyword Shorts: read the calendar CSV, target the row from four calendar days earlier, then validate each candidate against current Naver DataLab trend evidence and current media coverage.
- 2 reactive Shorts: one morning and one afternoon. Political coverage must include Lee Jae-myung and Han Dong-hoon daily when there is a current, sourced angle; never fabricate an angle when the day's evidence does not support it.
- Analyze at least five competitor Shorts with >=200,000 views before script drafting. Record URLs, views, title structure, hook, pacing, caption density, thumbnail composition, and comment CTA. Learn patterns only; do not copy scripts or thumbnails.
- All-channel thumbnail rule: bold high-contrast newsroom headline; deep dark background; 2–4 subject images only when genuine and licensed/appropriate; large yellow/white/red headline text; one clear claim/question; mobile legibility. Do not use fabricated politician likenesses or state allegations as fact.
- Voice: ElevenLabs only; energetic newsroom delivery, high pitch/tension, target 1.2x post-production tempo. Never fall back to system/Edge TTS.
- Metadata: search-led title, concise sourced description, 8–15 relevant tags; no keyword stuffing.
- Upload stage must use the exact Seoul Journal channel OAuth and PRIVATE visibility. If channel identity/authorization cannot be verified, stop before upload and leave an editorial queue.

## Calendar caveat
The linked sheet export currently identifies itself as a 2027 season-candidate calendar, and explicitly says keywords are season candidates before actual search-volume measurement. On 2026-10-21, a row from four days earlier may not exist. In that case the workflow must mark the golden-keyword batch blocked (not pretend the calendar proves current demand) and still prepare the two reactive slots from independently verified current coverage.
