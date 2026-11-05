# INVENTION_STORY1 publishing stop audit — 2026-11-06

## Target identity
- Channel ID: `UCgNj-yS93A_fOHXXvG49fww`
- Canonical registry key: `invention`
- Canonical name: `INVENTION_STORY1`
- User-reported last public upload: 2026-08-25
- The locked channel inventory maps this exact UC ID to INVENTION_STORY1.
- The 2026-11-05 read-only OAuth preflight snapshot lists this exact UC ID under verified_channels for `invention`; do not repeat OAuth authorization unless a fresh runtime check fails.

## Confirmed repository blockers
1. **Global YouTube scheduler is intentionally fail-closed.** `.github/workflows/youtube-github-scheduler.yml` exits before checkout or job processing unless the `youtube-channels` environment has `YOUTUBE_AUTO_PUBLISH_ENABLED=true` and `YOUTUBE_COST_HOLD=false`. The runtime helper `automation_hub/youtube_github_runtime.py` independently blocks every channel while the cost hold is active, except the narrowly validated Globalmusic free-only exception. Invention is not covered by that exception. This is the immediate system-wide publication gate.
2. **The Invention registry still points to a retired workflow.** `config/youtube_channels.json` sets `invention.workflow=curio-longform-daily.yml`; `automation_hub/youtube_registry.py` still validates knowledge channels against that retired workflow. Repository tests explicitly require legacy `curio-longform-daily.yml` and `curio_scheduler.py` routes to remain retired. The current production worker is `.github/workflows/youtube-github-worker.yml` plus `scripts/youtube_github_worker.py`. Any dispatcher relying on the registry workflow field can therefore target a non-existent/retired workflow.
3. **Current knowledge production has hard prerequisites.** `scripts/youtube_github_worker.py::_knowledge` stops if `FISH_AUDIO_API_KEY` is missing. It invokes `scripts/archive_footage_longform.py`, whose reviewed-image gate requires `EPISODE_DATE` and `assets/youtube/knowledge/<EPISODE_DATE>/invention-source.png` (or the configured `KNOWLEDGE_OWNER_IMAGE_ROOT`). This must be checked for the selected episode date before dispatch. Do not substitute an unrelated image or silently fall back to paid generation.
4. **OAuth identity has a positive recent read-only receipt, not a publication receipt.** `config/youtube-auth-preflight-snapshot-2026-11-05.json` records the exact Invention UC ID as verified. That confirms the recorded identity preflight only; it does not prove current upload permissions, a successful upload, or public visibility.
5. **No publication success is claimed.** A workflow dispatch or successful render is not sufficient. Completion requires a returned video ID, exact `snippet.channelId`, `privacyStatus=public`, and a working public watch URL.

## Safe recovery sequence
- Keep the global cost hold in place until the owner explicitly approves a cost-policy change. Do not turn on paid Gemini or other paid APIs as a shortcut.
- Repair the stale registry/dispatcher contract so the Invention key uses the current GitHub-native worker, while preserving the existing channel ID and per-channel OAuth secret mapping. Update the Sheet workflow field and tests together; do not make a partial registry-only change.
- Verify the Fish Audio dependency and prepare a unique reviewed invention image for the intended episode date. If the owner requires a zero-paid-API route, replace the paid-dependent production steps with a tested free-only path before activation.
- Run a single owner-authorized canary only after the cost gate and required assets/dependencies are satisfied; verify exact channel identity and privacy state before enabling recurrence.
- Restore daily calendar dispatch only through the GitHub-native scheduler/worker. Do not revive the retired Curio workflow.

## Actions taken in this audit
- Read-only inspection of the connected GitHub repository, locked channel inventory, registry, scheduler, worker, upload code, and 2026-11-05 OAuth preflight snapshot.
- No environment gate, GitHub secret, Google Sheet row, or YouTube video was changed. No upload was attempted. The global cost hold remains untouched.
