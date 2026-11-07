# London Project — YouTube 20 channels recovery ledger
Date: 2026-11-07 KST

## Source of truth
Target 10 language + 5 playlist + 5 knowledge. Seoul Journal is an additional separately managed channel. Do not reclassify the 20 channel core.

## Seoul Journal
- Legacy fixed scheduled private-only queue replaced by separate randomized 3-window flow: `.github/workflows/seoul-journal-randomized-shorts.yml`, `scripts/seoul_journal_slot_gate.py`, `scripts/seoul_journal_news_shorts.py`.
- Each day choose one random 10-minute slot in 08:00–10:00 (politics), 13:00–15:00 (sports), and 19:00–22:00 (politics), KST. Source-attributed title-based original narration/graphic; do not fabricate latest news.
- Dry run succeeded: GitHub Actions run 42369801194 (sports).
- OAuth still BLOCKED: exact-channel refresh preflight run 42369642936 returned `unauthorized_client`. Multi-client diagnosis run 42369894447 failed for all candidate pairs, though other channels passed. Owner consent generated run 42370034910 and opened in ChrisHUH Chrome. Await owner approval/reissue. Do not set `SEOUL_JOURNAL_SHORTS_LIVE=true` until exact channel identity and public upload are verified.
- Important: *verified rights-cleared actual photos of named politicians/athletes are not yet integrated*. No unrelated/wrong-identity images or unauthorised news photo scraping.

## Core 20 / language
- 10 languages: recent public video feed activity Nov 5–6; scheduled upload receipts Nov 7, 10/10 succeeded (run 42267246578). Preserve their existing independent workflow.

## Playlists
- `globalmusic` CAFE_ROMANTIC: recent public Nov 6; preserve verified free-only path.
- `healing` CAFE_HEALING: public activity Nov 6, but dedicated run 41868149984 failed downloading Pexels video HTTP 403. Updated `scripts/healing_motion.py` to fetch official free Pexels video_files MP4 URLs using existing PEXELS_API_KEY; key passed to `cafe-healing-publish.yml`. Needs one targeted smoke test/next scheduled publication.
- `mbb` CAFE_MOZART: re-enabled disabled workflow. Fixed OAuth client fallback to existing repository client, installed missing pytest, passed SHEET_ID. Calendar contained three exact IDs `HEALING-20261113-1400` on sheet rows 2588, 2593, 2598. Backed up and quarantined duplicates 2593/2598, kept 2588. Added read_calendar in-memory identical-unclaimed-duplicate quarantine, preserving original physical sheet row numbering; conflicting duplicates remain fail closed. Actual upload attempt must be verified separately; last live retry run 42371169525.
- `starbucks` CAFE_STARBUCKSVIBES: last public Aug 16; identified Google Drive source folder with 44 audio files and added folder ID as `youtube-channels` Environment variable, consumed via workflow vars fallback. Need verify music creation/commercial rights and fresh asset manifest; global cost hold remains.
- `kpop` CAFE_KPOP: last public Oct 5; identified Google Drive source folder with 24 audio files and added folder ID as `youtube-channels` Environment variable, consumed via workflow vars fallback. Need verify source rights (particularly Suno plan licensing), track duplication and images; global cost hold remains.

## Knowledge channels
- NASA_XFILES (Aug 26), HISTORY_TV_TODAY (Sep 30), INVENTION_STORY1 (Aug 26), SILENT_ERA_FILM (Aug 25), RETRO_USA1 (Sep 2) last public posts.
- Exact OAuth preflight for all 10 playlist+knowledge succeeded Nov 5 (run 41982080749), but that is not a publish confirmation.
- Main `youtube-github-scheduler.yml` runs but its guard sees `YOUTUBE_COST_HOLD=true` and `YOUTUBE_AUTO_PUBLISH_ENABLED` unset; it reports workflow success while skipping any publication. Do not globally disable hold.
- `config/KNOWLEDGE_CHANNEL_POLICY_LOCK.md` requires scene-verified rights-cleared footage, ElevenLabs narrator and private upload before owner release; existing `youtube_github_worker.py` requires FISH_AUDIO_API_KEY instead and image source wrappers require an owner-reviewed daily still. Resolve policy/pipeline and approved free tier before enabling; not safe to claim these five recovered.

## Next safe actions
1. Finish Seoul Journal owner Google OAuth consent, update token as GitHub Secret, exact-channel preflight, then allow live uploads.
2. Finish Mozart upload test and verify video ID + actual privacy/processing status; isolate any further calendar records if they conflict.
3. Independently run Pexels source smoke test for healing.
4. Produce rights manifest for each owner-provided K-pop and Starbucks source; test one per channel before publishing.
5. For knowledge 5, align narration policy with verified cost-free availability and source rights, create one scene-manifest dry-run each, then upload private with exact channel ID verification.
6. Do not equate GitHub job success with YouTube publication; record video URL, channel ID, privacy status and duplicate guard.
