# OLD_HOLLYWOOD / SILENT_ERA publishing stop audit — 2026-11-06

## Confirmed destination
- YouTube channel label shown in Studio: OLD_HOLLYWOOD
- Canonical registry key: `silent_era`
- Canonical channel ID: `UCLvy6kSpC8-7o3hnSrfQ47g`
- Internal legacy alias: `OLD_HOLLYWOOD1` / `SILENT_ERA_TIMES`
- Studio evidence inspected on 2026-11-06: latest visible public upload is dated 2026-08-25; six uploads are visible in the channel's upload list.

## Root causes and blockers found in the repository
1. **Automatic YouTube publishing is deliberately disabled by environment gates.** `.github/workflows/youtube-github-scheduler.yml` exits before checkout/dispatch unless environment `youtube-channels` has `YOUTUBE_AUTO_PUBLISH_ENABLED=true` and `YOUTUBE_COST_HOLD=false`. The repository's current policy keeps the cost hold active by default. This is the immediate reason the GitHub-native scheduler does not publish.
2. **The previous knowledge-channel workflow is retired.** The older `curio-longform-daily.yml` / `curio_scheduler.py` route is historical and is not the current production route. The current GitHub worker is `.github/workflows/youtube-github-worker.yml` plus `scripts/youtube_github_worker.py`.
3. **The current knowledge worker has required production dependencies that must be checked before a run.** `scripts/youtube_github_worker.py::_knowledge` fails closed if `FISH_AUDIO_API_KEY` is absent. For `silent_era`, `scripts/archive_footage_longform.py` requires `EPISODE_DATE` and a reviewed image at `assets/youtube/knowledge/<EPISODE_DATE>/silent-era-source.png` (or the configured `KNOWLEDGE_OWNER_IMAGE_ROOT`). Missing image raises `WAITING_ASSETS`; it is not an optional thumbnail.
4. **No production publication canary is established by the checked-in migration record.** A successful workflow dispatch alone is not evidence of publication; a video ID, exact destination channel ID, public URL and privacy state must be verified.

## Safe recovery plan
- Keep the existing cost hold in place; do not bypass it or enable paid Gemini/ElevenLabs/image APIs as a shortcut.
- Prepare a genuinely free-only `silent_era` production path: verified/public-domain source footage, a unique reviewed thumbnail source, a zero-cost narration/render route (or a deliberately silent-film format that does not require paid TTS), and exact-channel OAuth verification.
- Run one owner-authorized private canary first; verify its video ID and channel ID. Only after that can public publishing cadence be enabled under the owner's cost policy.
- Restore scheduled dispatch only through the GitHub-native worker and calendar, not the retired VPS/systemd or `curio-longform-daily.yml` path.

## Actions taken
- Read-only inspection of the connected YouTube Studio tab and current default-branch source files.
- No workflow was dispatched, no environment gate was changed, no secret was read or changed, and no video was uploaded. This avoids falsely claiming a publication or silently lifting the cost hold.
