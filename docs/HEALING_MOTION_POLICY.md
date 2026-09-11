# Healing channel nature video policy

Owner instruction, 2026-09-08: choose rain or creek/birds randomly; choose duration uniformly from 74 through 175 minutes. No thumbnail text, no music, no narration. All automated uploads are PRIVATE to UC7yEsLM-HoXudngrD-4FIqg (OAuth brand K-ISSUE).

Use real moving footage of falling rain and wet leaves, or flowing forest water. Crossfade the scene loop boundary. Rain audio is continuously synthesized; creek audio blends flowing-water audio with forest birds. Do not describe edited loops as uninterrupted field recordings.

VPS playlist worker routes healing jobs to scripts/healing_motion.py. A stable schedule/job identifier determines the random selection, preserving it on retries. Manual GitHub samples use the run ID. Before upload, scan the authenticated channel's upload history for that job marker. Verify PRIVATE status and video processing before reporting success.

Sources reviewed 2026-09-08:

- Rain footage: https://www.pexels.com/video/waving-leaves-during-heavy-rain-13166787/
- Clear shallow creek footage: https://www.pexels.com/video/a-stream-in-the-jungle-with-rocks-and-trees-18132437/
- Separate flowing-water audio, mixed at a gentle level: https://www.pexels.com/video/flowing-river-on-the-rain-forest-5021254/
- Pexels license: https://www.pexels.com/license/
- Bird audio: Magnesus, Forest birds - ambient seamless loop, https://freesound.org/people/Magnesus/sounds/723913/ . The source page explicitly specifies Creative Commons 0, https://creativecommons.org/publicdomain/zero/1.0/ . The bundled MP3 is the official high-quality preview, https://cdn.freesound.org/previews/723/723913_2008500-hq.mp3 . Retained locally to avoid intermittent CDN failures.

The earlier static 75-minute sample 0QjuP8V4MV8 remains private and is not the motion version. Existing uploaded videos cannot have their video stream replaced; motion revisions receive a new private video ID.
