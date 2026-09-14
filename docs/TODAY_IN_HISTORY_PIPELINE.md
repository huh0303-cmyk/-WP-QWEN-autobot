# Today in History — approved production contract

Updated: 2026-09-06. Channel routing key: `history` (existing HISTORY_TODAY_TIMES OAuth mapping).

## Implementation status — do not confuse specification with a working service

This document fixes the requested target pipeline. `scripts/history_episode_contract.py`
provides an offline manifest validator and no-immediate-repeat narrator selector.
It is NOT yet wired into the legacy production renderer or scheduler.
No new production run, upload, paid generation, or unlocking is authorized by this commit.
The existing emergency locks and private-upload policy remain unchanged.
The September 6 Brian sample was generated in the ElevenLabs website; its audio file
has not been ingested into this repository. The revised sample is not finished.

## Editorial and visual rules

- Freeze the episode date at job creation in the channel's configured timezone; never
  recompute 'today' halfway through a job. Explicit dates also permit reruns/backfills.
- English narration and English burned-in subtitles plus editable SRT.
- MONTH + DAY (e.g. SEPTEMBER 6) is the largest identifying text on thumbnail,
  opening and event transitions. The event year is secondary. Use the same date in title.
- Order verified events newest to oldest. September 6 example: 1901, 1757, 1522.
  Event dates are not filming dates. McKinley's attack and later death must stay distinct.
- Sample: approximately 2–3 minutes. Regular episodes: 10–15 minutes when supported
  by sufficient relevant material. Never pad with unrelated or repeated footage.
- Prioritize relevant archival moving footage. Where it does not exist, use sourced
  portraits with gentle motion, maps, timelines or clearly labelled explanatory animation.
  Never imply an illustration records the event, or fabricate historical footage.
- Opening preference: if even one relevant, rights-cleared actual moving clip exists,
  lead with a short excerpt and narration describing that visible scene. Then transition
  to labelled explanatory AI imagery/animation as needed. Never use an unrelated real
  clip just to satisfy this preference. Preserve newest-to-oldest event order; an opening
  teaser from another event must be clearly labelled as a teaser, not a false chronology.
- Legible subtitles, normally two lines; protect source captions and safe margins.
  Scene changes and subtle movement support comprehension, not constant effects.

## Fixed production sequence

1. Create persistent episode ID, date, intended channel and status; check duplicates.
2. Research events for that month/day. Save primary-source URLs and checked factual claims.
3. Sort events descending by event date, BEFORE writing or generating audio.
4. Search/download candidate visuals; retain item URLs and per-item commercial-use basis.
   An institution/collection name alone is not proof that every item is reusable.
5. Inspect actual video frames. Record usable in/out points and visible actions per scene.
6. Write narration against those exact scenes. Keep context that cannot be shown on labelled
   maps/timelines. Verify facts and visual alignment before paid speech generation.
7. Select one approved stock ElevenLabs voice for the whole episode: Brian, George,
   Daniel or Bill. Randomly exclude the preceding completed episode's voice.
   Save choice before TTS; retries and segments reuse it. No cloned celebrity narrator.
8. Resolve selected voice from the authenticated account; preflight access and credits.
   On authentication failure stop with a precise failure state, rather than repeat charges
   or silently switch vendor. API output must be decoded and saved server-side, not depend
   on a user's browser download. Verify nonempty audio and duration with a media probe.
9. Generate speech per scene/paragraph with alignment timestamps. Cache by text + voice +
   model + settings. Build the scene timeline from actual audio duration, then assemble
   only matched visual intervals. Do not independently loop a generic footage playlist.
10. Generate SRT from alignment; burn captions; overlay month/day; create matching thumbnail.
11. Review final frames AND audio: date prominence, descending chronology, factual accuracy,
    rights notes, scene correspondence, subtitle timing, intelligibility, no black/silent gaps.
    Run the offline manifest validator; schema checks cannot replace actual review.
12. Verify authenticated YouTube channel identity against history routing, then upload
    PRIVATE and retain video ID/URL. Do not blindly retry an uncertain upload (duplicates).
    Public release requires a separate explicit decision. No cross-channel fallback.
13. Archive manifest, script, sources/rights, voice metadata, audio, SRT, MP4, thumbnail,
    review report, cost/credit usage and upload receipt. Resume from last valid stage.

## Remaining integration work

- Replace the legacy one-topic/generic clip-loop assembly with event/scene timeline assembly.
- Add persistent episode/previous-voice storage to the central scheduler, with atomic
  reservation and stable retry selection. The helper alone is not cross-run persistence.
- Resolve the production ElevenLabs secret/access problem and verify server-side saving.
- Call the manifest validator before upload; persist actual review evidence rather than
  marking checklist flags true automatically.
- Wire frozen episode date into main video, thumbnail and metadata (legacy thumbnail
  currently reads machine-local current time).
- Apply approved voice routing to other narrated channels after language/channel mapping;
  do not introduce narration into channels intentionally configured as silent films.

## Acceptance test

A paid end-to-end trial must produce a playable English episode with matched visuals,
correct SRT and date display, then return a verified private history-channel URL.
Until that happens, report 'contract saved / integration pending', not 'automation complete'.
