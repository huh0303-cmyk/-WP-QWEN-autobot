# TODAY IN HISTORY — 15-minute English documentary pilot

Status: **isolated code pilot / not connected to live publishing**. Updated 2026-11-12.

## Scope
- Keep current Shorts and legacy knowledge-upload workflow unchanged.
- Target 12–18 min, roughly 15 min, 16:9 1080p, 40–60 genuinely distinct stills.
- Use two verified historical events sharing the frozen month/day, most recent event first.
- Narration is English. Each scene has a separate *already-generated* narration audio file.
- All stills must have item-specific usage-right evidence and matching scene descriptions.
- The new isolated renderer does not fetch events, create scripts, call Gemini, generate TTS, or upload to YouTube. Those are separate integration stages.
- Publishing after this pilot requires verified YouTube account, PRIVATE visibility and explicit approval to release publicly.

## Thumbnail standard
- Generate **three** 1280×720 JPEG candidates using separate reviewed event images.
- The MONTH + DAY is the largest text. Headline maximum six words and two lines.
- High contrast, useful mobile-safe margins. No unrelated or fabricated historical scenes.
- Operator chooses a thumbnail after reviewing accuracy and readability.

## Caption standard
- English only; one short caption at a time, 1–6 words per line.
- Captions supplied per scene with offsets **derived from TTS timestamps**, not guessed from text length.
- Export editable SRT and burn subtitles in the review MP4; position near the bottom, with outline.
- Validator checks timing order, overlap and actual audio-duration limits. Visual and phonetic synchronization still need review.

## Example input (production manifest)
```json
{
  "channel_key": "history",
  "language": "en",
  "upload_visibility": "private",
  "episode_date": "2026-11-12",
  "thumbnail_title": "TWO WORLD CHANGING EVENTS",
  "events": [
    {"date":"1954-11-12","fact_sources":["https://source.example/primary-1"]},
    {"date":"1927-11-12","fact_sources":["https://source.example/primary-2"]}
  ],
  "scenes": [
    {
      "event_date": "1954-11-12",
      "image": "local-reviewed-still-001.jpg",
      "audio": "narration-scene-001.wav",
      "source_url": "https://archive.example/item-001",
      "rights_basis": "Verified specific work license and attribution record",
      "visible_content": "Precisely describe what can be seen in the source",
      "narration_excerpt": "Spoken narration describing that visible scene",
      "captions": [
        {"start":0.3,"end":2.1,"text":"A turning point"},
        {"start":2.1,"end":4.7,"text":"Changed the world"}
      ]
    }
  ]
}
```
(Expand to 40–60 scenes, all with unique licensed media; example domains are **placeholders**, never publish.)

## Run locally after separately preparing sources and voice audio
```bash
python -m pip install Pillow
python scripts/history_longform_pilot.py /path/to/manifest.json --check-only
python scripts/history_longform_pilot.py /path/to/manifest.json --output artifacts/history-pilot
```
Expected: `review.mp4`, `captions.srt`, `thumbnail_1.jpg` to `thumbnail_3.jpg`, `review_report.json`.
All outputs are **for manual review**, not a YouTube upload. The script does not read credentials.

## Offline smoke test
The standalone GitHub workflow runs automatically on its PR paths and can be manually dispatched. Tests synthesize two simple still images and two short audio tracks **solely for video QA**. No history claims, API charges, remote images, or uploads.

```bash
PYTHONPATH=. python -m unittest discover -s tests -p 'test_history_longform_pilot.py' -v
```

## Pending production integration
1. Select and verify exactly two real events for the date, with cited primary sources.
2. Collect 40–60 truly different reusable visuals and specific license/rights basis.
3. Generate sufficiently long English narration with existing Gemini fallback and FREE TTS chain (Fish → local Qwen → Edge); save word/phrase timings.
4. Review factual accuracy and the actual alignment between audio/visual/captions.
5. Produce the full duration review video and select thumbnail.
6. Verify the intended HISTORY channel identity and separately upload PRIVATE once, guard against duplicate uploads.
7. Release to PUBLIC only after a separate editorial decision.

**Do not interpret a successful synthetic CI render as a production episode or completed end-to-end automation.**
