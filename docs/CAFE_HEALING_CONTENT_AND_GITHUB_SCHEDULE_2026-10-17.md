# CAFE_HEALING — content, sound mix, thumbnails, GitHub cadence

Date: 2026-10-17
Canonical channel ID: `UC7yEsLM-HoXudngrD-4FIqg` (handle `@cafe_healing1`).

## Owner requirements

- Keep the channel focused on natural healing ambience; current rain and stream sounds are working and should remain core formats.
- Expand the sound palette across releases: rain on leaves/window/roof; flowing creek/waterfall; soft wind through trees; birds; delicate temple/wind chimes; and a warm fireplace with clearly audible natural crackles.
- Use one or two primary sound elements and a few restrained secondary elements per video, not every sound at equal volume. Avoid harsh loudness, artificial repetitive loops, sudden edits, music, and narration. For example: (A) forest stream + birds + breeze; (B) gentle rain + distant wind chime; (C) fireplace crackle + rain outside a cabin; (D) forest breeze + birds + subtle temple chime. Chimes should be occasional and soft, not continuous or piercing.
- Publish 2–3 times weekly on randomized, well-spaced days/times using GitHub Actions as the scheduler/runner. VPS is not the production host.
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

This file locks the requested channel policy and provides benchmark references. It does not claim that GitHub Actions has been deployed end-to-end or that a new video was uploaded. The current repository still needs the actual GitHub-native render/upload workflow, source asset availability check, and verified YouTube API receipt.