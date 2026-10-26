# VPS cancellation and GitHub-only transition — 2026-10-09

## Owner decision
- Hostinger VPS cancellation was confirmed by the owner on 2026-10-09.
- The n8n-on-VPS migration plan is retired.
- All production scheduling and execution must move to GitHub Actions. VPS must not remain a production dependency.
- This is a migration directive, not evidence that every repository component has already been migrated.

## Audit update — 2026-10-26

A repository search found that the directive has not yet been fully implemented in code:
- 21 workflow files still matched `appleboy/ssh-action`.
- `.github/workflows/youtube-vps-enqueue-today.yml` still reads `VPS_HOST`, `VPS_USER`, and `VPS_SSH_PRIVATE_KEY`, then runs a queue command on the remote host.
- `scripts/run_youtube_vps.py` reads `/etc/korea365/youtube-runtime.json`.
- `scripts/youtube_vps_worker.py` and `automation_hub/youtube_vps_queue.py` depend on a server-local queue and other persistent runtime state.
- `projects/런던프로젝트GPT/ARCHITECTURE.md` previously described VPS/systemd/n8n as the production runtime; it has now been updated to the GitHub-only target architecture.

## Migration safety rules
1. Do not delete existing posts or videos.
2. Do not change privacy/publication state as part of infrastructure migration.
3. Do not remove a production worker before a GitHub-native replacement is tested.
4. Preserve cost-hold, duplicate prevention, exact account/channel identity checks, and publication receipts.
5. A workflow run is not proof of publication; verify the destination ID and resulting content URL/privacy state.
6. Do not claim the migration is complete until each platform's actual execution path is either migrated and verified or explicitly held because it requires unavailable authentication.

## Historical checks from 2026-10-09 (not a current health guarantee)
- Blogger 33 had a GitHub Actions schedule.
- WordPress daily publication floor and Tistory error isolation were being repaired.
- Control center, Naver/Tistory browser runners, YouTube worker, queue, and metrics still needed individual migration review.

## Required next steps
1. Inventory every SSH-based workflow and classify it as replace, retire, or read-only historical evidence.
2. Replace the YouTube server queue/worker with GitHub-hosted execution and durable GitHub-native state before retiring it.
3. Verify channel OAuth identity and use private canaries before enabling any new recurring public upload.
4. Migrate WordPress, Blogger, news, social, Naver, and Tistory separately with exact publication receipts.
5. After replacements pass, retire VPS workflows, server-only scripts, deployment paths, and obsolete secret references.

**Status: migration in progress; repository is not yet fully VPS-free.**
