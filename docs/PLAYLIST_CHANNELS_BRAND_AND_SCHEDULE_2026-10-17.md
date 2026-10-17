# Playlist channel production lock — 2026-10-17

## Starbucks Vibes (`@Starbucksvibes`)

**Positioning:** quiet background music for focused work, reading, studying, and long sessions. The sound is calm jazz, mellow blues, soft café jazz, brushed drums, warm piano/Rhodes, upright bass, restrained guitar, and low-key instrumental grooves. Avoid energetic K-pop, loud drops, busy vocals, harsh transitions, or music that competes with work.

**Thumbnail direction:** preserve the rainy-window / warm lamp / cozy café / night city visual identity. Use a premium editorial composition, strong contrast, restrained warm amber and deep teal, and refined high-contrast serif typography for `PLAYLIST`. Small secondary labels only (e.g. `FOCUS JAZZ`, `MELLOW BLUES`, `WORK • STUDY • READ`). Keep the title readable at mobile size. Add a subtle, elegant waveform/equalizer near the bottom; no clutter, no oversized crude text.

**Titles and filenames:** never expose raw filenames such as `2026_8_13_3553.mp4`. Use human-readable search-friendly titles, for example:
- `Rainy Night Café ☕ Mellow Jazz & Soft Blues for Deep Focus | 2 Hours`
- `Quiet Coffee Shop Jazz 🎷 Smooth Blues Instrumentals for Work, Study & Reading | 90 Minutes`
- `Warm Lamp, Rainy Window 🌧️ Relaxing Café Jazz for a Calm Workday | 2 Hours`

Only include duration when it matches the final rendered video duration. Date belongs in internal asset filenames/metadata, not as a substitute for a useful public title. Suggested internal filename: `starbucks_vibes_YYYY-MM-DD_focus-jazz_120min.mp4`.

**Cadence:** target 2–3 uploads per week, distributed across different days with randomized publish times. Do not schedule daily. Check recent uploads and pending queue first; never create a duplicate for a date/asset. If generation, render, or OAuth verification fails, report the channel as blocked instead of silently skipping or claiming success.

## K-pop Studio 7 (`@kpop_studio7`)

**Positioning:** sweet, fresh, cozy acoustic K-pop / Korean acoustic pop for quiet moments. Preserve the sunset city, warm room, guitar, soft window-light mood. Use refined premium typography for `PLAYLIST`, avoid generic oversized sans-serif treatment, and use a clean subtle waveform along the lower edge.

**Music uniqueness:** the first two tracks in every playlist must never be the same recording or the same composition/version. Before rendering, compare stable track IDs and normalized title/artist metadata; where audio files are available, also compare audio fingerprints/hashes. Fail the build if tracks 1 and 2 match. Also compare the new playlist against recent outputs to avoid accidental repeats. A hash alone is not sufficient to detect the same song re-encoded; combine metadata and audio fingerprinting where available.

## High-view benchmarking guardrails

Benchmark public 1M+ view work-music and café-jazz videos for title structure, visual hierarchy, and mobile legibility. Record the source URL, observed view count, and observation date in the benchmark log. Treat patterns as inspiration, not copying: do not reuse competitors' thumbnails, exact titles, logos, or artwork. View counts change; do not label an example “1M+” unless verified at research time.

## Release safety / verification

- Do not delete existing videos.
- Do not claim deployment, scheduling, or upload completion without evidence from the runtime and YouTube Studio/API.
- Verify the authenticated channel ID before upload; verify the returned video ID, channel ID, title, duration, and privacy state after upload.
- User's free-only constraint remains in force: no paid APIs, paid stock imagery, or paid SaaS. Follow the separate Gemini-free-only rule for text generation.

## Current status (2026-10-17)

This file locks the requested content and design policy in GitHub. It does **not** prove the scheduler has been fixed, deployed, or that a new video has been published. The reported two-month gap still requires a runtime audit of GitHub Actions/VPS scheduler, worker queue, OAuth scopes, render pipeline, and recent run logs. The next implementation step is to map these requirements to the actual channel-specific workflow and add a randomized 2–3/week schedule with failure alerts and post-run receipts.