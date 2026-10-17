# CAFE_MOZART classical playlist publishing recovery — 2026-10-17

## Evidence from owner-provided YouTube Studio screenshot

Channel: `CAFE_MOZART`, locked YouTube channel ID `UC7jOhyMa-FIrzZuea97z1Pw`.

The latest visible upload in the screenshot is dated 2026-10-01 (`licensed or public-domain classical recordings; Mozart and ...`, 1:07:03, 5 views). Other visible videos are dated 2026-08-26, 2026-08-25, 2026-08-24, 2026-08-22, 2026-08-17, 2026-08-14, 2026-08-13 and 2026-08-12. This is direct evidence of a publishing gap after October 1 in the supplied screenshot, not proof of the exact VPS failure.

## Existing system facts from repository audit

- The core playlist/knowledge channels are intended to publish 2–3 times per week on randomized days.
- The `Content Random Scheduler` workflow only emits a `DRAFT_ONLY` planning file; it does not render, enqueue, upload, or verify a YouTube video.
- The actual uploader is separate: it consumes a Google Sheet/queue via the VPS worker and 15-minute dispatcher. A calendar plan alone cannot publish a video.
- The CAFE_MOZART OAuth identity was previously checked against exact channel ID `UC7jOhyMa-FIrzZuea97z1Pw`. This old receipt does not prove current token validity, current worker health, or a public upload.
- The current live VPS timer/service status, queue rows, and last CAFE_MOZART worker error have not been collected in this audit. Do not guess whether the last-mile failure is a stopped dispatcher, empty queue, missing render, or auth error.

## Content/thumbnail direction

Use Mozart/Bach/Beethoven portrait imagery as a strong, tasteful focal point, integrated with a classical listening scene (piano, sheet music, warm lamp, wood tones). Keep the portrait recognizable but avoid clutter and text over the face. Use refined editorial serif typography, restrained gold/ivory/charcoal palette, clear `CLASSICAL PLAYLIST` or composer/occasion label, and a genuine final runtime. Public title must not expose raw source filenames. Only use recordings with documented rights/public-domain status and retain source/rights metadata.

Example title pattern (only if the actual audio matches): `Mozart & Beethoven for a Quiet Morning | Gentle Classical Piano & Strings • 1 Hour`. Duration must be calculated from the final render; never hardcode a guessed duration.

## Required recovery gates

1. Inspect current VPS worker and 15-minute dispatcher/timer state and logs.
2. Inspect queue/Google Sheet rows for `CAFE_MOZART`; reconcile failed or ambiguous rows before retrying.
3. Confirm an original, rights-cleared classical audio set and final render/thumbnail exist.
4. Verify authenticated `mine=true` channel ID equals `UC7jOhyMa-FIrzZuea97z1Pw` immediately before upload.
5. Upload one video, then verify returned video ID, exact channel ID, title, duration and privacy status via YouTube API; record receipt.
6. Configure 2–3 weekly randomized slots, with failure alert and no duplicate same-day upload.

## Status

GitHub now records the observed gap and the known scheduling architecture. No video was uploaded by this audit, and no runtime fix is claimed. Completion requires live VPS/queue evidence plus a verified YouTube upload receipt. Do not delete existing videos.