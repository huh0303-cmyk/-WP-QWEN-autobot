# Immediate operating order — Seoul Journal + Seoul Jisoo (2026-10-21 KST)

## Do not use Metricool for this task
Metricool is reserved for the user's Korean/TOPIK vocabulary workflow. Do not create, schedule, or publish Seoul Journal news or Seoul Jisoo shopping/news content through Metricool.

## Priority order
1. Read the one-year Golden Keyword Calendar Google Sheet directly. The existing Seoul Journal queue script references:
   https://docs.google.com/spreadsheets/d/1lGKkvLxKOi9pufCuzvYpylqnK7apLx8f/export?format=csv&gid=796729184
   The daily policy is to select the five keyword candidates from the row dated four days before the current KST date, then validate each candidate against same-day Naver DataLab trend and news coverage. Never claim the keywords were retrieved or validated unless the exact row and sources are recorded.
2. Create 5 Golden Calendar Shorts plus 2 reactive daily news Shorts (morning and afternoon), target 7 packages/day.
3. Render vertical 9:16 MP4, Korean captions, and dark navy / white-yellow-red mobile-first thumbnail. ElevenLabs only; no fallback TTS.
4. Upload the Seoul Journal video to the exact Seoul Journal YouTube channel as PRIVATE. Do not publish publicly until the owner reviews in YouTube Studio.
5. For Seoul Jisoo Instagram, verify the exact @seoul_jisoo account and posting permission, then publish the same approved video as a Reel using the appropriate caption. Do not use the connected SIS/TOPIK Metricool brand as a substitute.
6. Only after account-specific permission is verified, proceed in order: TikTok, Facebook Reels, Instagram Reels, Threads. For the immediate task, Instagram @seoul_jisoo is the first social destination.
7. Keep platform status separate: DRAFT_READY, RENDERED, YOUTUBE_PRIVATE_UPLOADED, INSTAGRAM_PUBLISHED, etc. Workflow success alone is not proof of a published post.

## Current verified blockers (as of this note)
- The existing `.github/workflows/seoul-journal-daily-shorts.yml` only creates an editorial queue JSON; it does not render an MP4 or upload to YouTube.
- The existing voice test script requires `ELEVENLABS_API_KEY` and a script input; it produces an MP3 only and explicitly does not publish.
- The connected Metricool brand observed on 2026-10-21 is `서울국제대학 SIS - TOPIK Center`; it must not be used for this task.
- Repository account audit lists Instagram `@seoul_jisoo` as a known profile but marks publish authorization as missing. Profile existence is not posting permission.
- The Google Sheet CSV endpoint above is the intended calendar source, but this note does not claim its current row or five keywords have been retrieved. Record the exact date, five cells, validation URLs, and status before marking calendar work complete.
