# Seoul Shorts voice and photo change

Task and correlation ID: seoul-shorts-voice-photo-20261109. Requested by the project owner on 2026-11-09 KST. State: code verification; live production pending.

- Seoul Jisoo previously rendered a static graphic with one hard-coded Edge voice. Its scheduled workflow now uses the licensed multi-photo renderer with Seoul Jisoo branding and includes photo attribution in the upload description. Stories with fewer than three eligible images fail before upload.
- Seoul Journal's randomized workflow and Seoul Jisoo expose two anchor and two documentary slots. Fish Audio voice references come from secrets. The local Qwen command remains optional, then Edge is the final fallback. Voice selection is deterministic per story, with no cross-story repeat guarantee.
- Python compilation passed. FFmpeg 6.1.1 removed 0.5 seconds of synthetic leading silence and rendered the remaining 1.5 seconds at 1.2x (1.250146 seconds).
- Pending: verify four distinct Fish references and a configured Qwen runner, render and listen to a real sample, verify licensed photos for the actual subjects, and identify the latest originals for remake. No originals were changed and no upload was attempted.
