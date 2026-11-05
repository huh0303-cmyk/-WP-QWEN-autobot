# CAFE_HEALING — content, sound mix, thumbnails, GitHub cadence

Date: 2026-10-17
Canonical channel ID: `UC7yEsLM-HoXudngrD-4FIqg` (handle `@cafe_healing1`).

## Owner requirements

- Keep the channel focused on natural healing ambience; current rain and stream sounds are working and should remain core formats.
- Publish the five requested themes one at a time in a fixed rotation: fireplace/bulmeong → rain → forest wind → birdsong → quiet temple garden/bells, then repeat. Keep each upload focused on one primary sound theme.
- Keep visuals deliberately simple: one main licensed moving scene (or at most two closely related shots), gently crossfaded and looped; do not build a busy montage. Sound is the main product. Use one primary sound plus at most one quiet supporting layer. Avoid harsh loudness, obvious loop seams, sudden edits, music, and narration. For example: (A) forest stream + birds + breeze; (B) gentle rain + distant wind chime; (C) fireplace crackle + rain outside a cabin; (D) forest breeze + birds + subtle temple chime. Chimes should be occasional and soft, not continuous or piercing.
- Publish 2–3 times weekly on randomized, well-spaced days/times recorded in the Google Sheet calendar. GitHub Actions polls the calendar and publishes only due rows; the workflow must not invent or silently pull forward a future slot. VPS is not the production host.
- Keep existing videos; no deletion. Verify exact OAuth channel ID immediately before upload and verify new video ID/channel ID/privacy/duration afterward.

## Existing pipeline observations

- `docs/HEALING_MOTION_POLICY.md` already specifies rain or creek/birds, 74–175 minutes, no music, no narration, no thumbnail text, and natural moving footage. `scripts/healing_motion.py` creates rain/stream titles and scenes.
- The existing random scheduler `.github/workflows/content-random-scheduler.yml` is plan-only (`DRAFT_ONLY`) and does not publish. Legacy healing generation has been coupled to the VPS worker. These need a GitHub-hosted replacement, not just a changed calendar.
- GitHub Actions runners are ephemeral; inputs and state must be explicitly checked out/downloaded and output receipts committed or uploaded as workflow artifacts.

## Benchmark notes (public results observed 2026-10-17)

Use successful videos as pattern research, not copying:

- `Forest Ambience: Water Sounds, Birds Singing, ASMR` — reported 2,822,824 views; 8 hours. Pattern: specific natural sound combination + simple scene + long, uninterrupted ambience.
- `Rain Sounds + Stream for Sleep, Focus, Studying | 4K Nature Video White Noise 10 Hours` — reported 5,033,593 views. Pattern: clear sound keywords, use case, visual quality, exact duration.
- `Rainforest Sounds - Water Sound Nature Meditation` — reported 12,439,097 views. Pattern: broad searchable sound category, long duration, nature-first promise.
- `The Ambiance Felt From the Window on a Cold Rain Day | Warm, Relaxing Fireplace` — reported 1,000,000 views. Pattern: a single cozy visual story and a strong rain + fire sound pairing.

Counts above are third-party/search observations and can change; recheck counts before using a result in future benchmark reports. Do not copy titles, thumbnails, footage, audio, or branding.

## Updated five-theme production plan — 2026-11-06

### Proven-demand benchmark checks
These are reference patterns, not assets to copy:
- Fireplace 4K, "Relaxing Fire Sounds" — approximately 20.5M YouTube views; one steady fireplace scene, real fire texture, no music.
- Rainy Bedroom, "Soothing Rain Sounds in the Forest" — approximately 4.5M views; long uninterrupted rain ambience, clear sleep/focus use.
- Naturescapes, "Woodland Stream & Birdsong" — approximately 1.1M views; one forest-water setting with birdsong.
- The Guild of Ambience, "Study Sounds | Windy Weather White Noise" — reported above 600K views; a single wind-weather sound concept.
- Temple ambience has not yet produced a sufficiently verified 500K+ sound-only benchmark in this research pass. Treat it as a carefully tested series entry, not a proven high-view format.

### Theme order and visual source plan
1. **Fireplace / 불멍** — Pexels clip 6755352 (one warm firewood close-up); soft crackle bed. Backup clip 946600.
2. **Rain / 빗소리** — existing approved rain pool; rain on leaves/forest canopy; no rapid cuts.
3. **Wind / 바람** — Pexels clip 3027193 (trees/leaves moving in wind); low, slowly changing wind bed.
4. **Birds / 새소리** — Pexels clip 30535102 or 35475944; bundled CC0 forest-bird recording.
5. **Temple / 절 풍경** — Pexels clip 36787646 (Buddhist temple in greenery); very soft, widely spaced original bell-like tones and low-level birds/breeze.

All visual source pages are individually listed in the source code and must remain under the Pexels license. Do not download, sample, or reuse competitor YouTube media. The sound design must state clearly when a sound is synthesized; do not label synthesized audio as a field recording.

### Rotation, runtime and timing
- Rotate the five themes in the order above. Record a category only after the YouTube upload has passed verification; failed attempts do not consume a theme slot.
- Randomize each long-form runtime between 74 and 175 minutes using the schedule ID as the reproducible seed.
- Actual release times come from the pre-existing calendar's randomized 2–3 weekly rows. GitHub Actions checks four times per hour (UTC minutes 3, 19, 37, 53) and publishes only a due row. A push-triggered owner-requested first run may publish the next READY healing row immediately.
- Cache the category and thumbnail history between GitHub runs so themes rotate and thumbnail frames are not immediately repeated.
- Paid generation providers remain blank/disabled. The only bundled field recording used in the new theme plan is the existing CC0 bird ambience; the other generated sound beds are disclosed as original local sound design.

## Thumbnail design direction

- Make the nature scene itself the hero: crisp creek/green forest close-up, rain on leaves/window, glowing firewood and orange embers, or a misty temple garden with a subtle bell.
- Use rich natural contrast and a calm focal point; avoid collage clutter and tiny decorative elements. A thumbnail can use no text or one short label only if it improves mobile readability. Do not cover the scene with oversized text.
- Make each release visually distinct while preserving a recognizable CAFE HEALING palette: forest greens, cool rain blues, misty silver, and warm fire amber.
- Use only owned, licensed, public-domain, or otherwise authorized visual/audio assets. Never download or reuse competitor media.

## Title and duration rules

Use clear, accurate search terms and actual final duration. Examples (select only if the mix matches):
- `Forest Stream, Birds & Soft Breeze | 90 Minutes of Peaceful Nature Sounds`
- `Gentle Rain on Leaves with Distant Wind Chimes | 2 Hours for Rest & Relaxation`
- `Rainy Forest Cabin & Crackling Fireplace | 2 Hours of Cozy Natural Ambience`
- `Temple Garden Breeze and Soft Birds | Peaceful Nature Sounds for Meditation`

Do not promise "no ads" unless the channel owner can guarantee that claim; do not claim field-recorded audio if synthesized or edited. Describe layered/looped audio honestly.

## GitHub Actions migration contract

1. Generate a due manifest for `healing` 2–3 times per ISO week using deterministic randomness keyed to week + channel ID, avoiding duplicate same-day releases.
2. Use `ubuntu-latest`; install FFmpeg and required Python packages. Do not call VPS/SSH/systemd or `/opt/korea365`.
3. Acquire source media from authorized GitHub artifacts/checked-in licensed assets or an explicitly configured permitted storage connector. If source media is unavailable, fail visibly; do not make an empty/placeholder upload.
4. Render and validate: video duration 74–175 minutes unless a specifically approved different duration; audio peak/loudness safety; no music/narration; expected mix components; thumbnail validity; metadata/title duration match.
5. Verify `channels.list(mine=true)` exactly equals `UC7yEsLM-HoXudngrD-4FIqg` immediately before upload.
6. Upload through YouTube API with channel-scoped GitHub Actions environment secrets. After upload, verify the returned video ID, exact channel ID, actual title, duration, privacy state and watch URL. Record JSON receipt and logs as artifact/committed result.
7. Retry safely: use stable job marker and inspect channel upload history before retry. Never create a duplicate if prior request outcome is ambiguous.
8. Cadence and upload success must be observable in a GitHub Actions run; a plan-only output is not success.

## Current status

The five-theme renderer, isolated free-only runtime gate, category-history cache and channel-specific GitHub Actions workflow have been committed. A workflow run and public YouTube upload receipt are still required before publication can be called successful. Existing videos are preserved.