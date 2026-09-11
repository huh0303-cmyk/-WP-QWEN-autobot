# Cafe Romantic private review completed

- Video: https://www.youtube.com/watch?v=htai4c5jPH4
- Studio: https://studio.youtube.com/video/htai4c5jPH4/edit
- YouTube API verified: `privacyStatus=private`, `processingStatus=succeeded`.
- Exact channel: `UCbJfEtsffpgI5MsKkB7BYvQ`.
- Duration: `PT1H22S` (60 minutes 22 seconds).
- English description: 1,037 characters.
- Custom thumbnail set successfully; YouTube returns thumbnail resolutions through maxres.
- 20 different existing songs: French 5, Japanese 5, Spanish 5, Italian 5.
- Locally checked audible language with Whisper base; selected confidence >= 0.8.
- Visuals: diverse adult romantic male-female couples, huge PLAYLIST title,
  six-second subtle introductory movement, actual soundtrack-driven waveform.
- Benchmark and image provenance: `docs/PLAYLIST_THUMBNAIL_BENCHMARK.md`.

Server evidence is retained in `/opt/korea365/data/romantic-review-20260908/`:
`tracks.json`, audio-language analysis files, `upload.json`, `completed.json`,
`verified-upload-status.json`, rendered video and thumbnail. `upload.json` is
saved before thumbnail operations so a thumbnail retry cannot create another video.

The review runner additionally requires `faster-whisper==1.2.1` in the existing
VPS venv and downloads the open-source `base` model on first use. It ran as
`korea365-romantic-review-20260908.service` independently of the owner's PC.

This confirms this single Cafe Romantic review. It does not claim all five
playlist channels have finished, or that recurring Gemini assets are ready.
Language detection does not establish singer gender or artistic quality.
