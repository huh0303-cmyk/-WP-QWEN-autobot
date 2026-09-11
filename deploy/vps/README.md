# Korea365 VPS runtime

Hostinger VPS is the sole production host.
The production topology is `nginx -> gunicorn control center -> durable VPS queue -> single YouTube worker`.
GitHub Actions is CI-only and does not generate or upload YouTube videos.

## Automatic production code deployment (September 9, 2026)

The production VPS pulls `origin/main` every 60–70 seconds using its existing repository
read access. No inbound SSH deployment key is stored in GitHub. `main` remains the release
authority; merge reviewed changes there. This timer updates application code automatically,
not just the checkout metadata. GitHub runs `VPS deployment safety tests` for deployment changes.

Install the tested deployment engine once (as root):

```bash
install -d -m 755 /usr/local/lib/korea365
install -m 755 deploy/vps/sync_main.py /usr/local/lib/korea365/sync_main.py
install -m 644 deploy/vps/korea365-deploy.service deploy/vps/korea365-deploy.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now korea365-deploy.timer
systemctl start korea365-deploy.service
```

The engine is installed outside the application checkout so a bad application release cannot
replace its recovery program. Upgrade that engine explicitly after its tests pass; do not
blindly replace systemd unit files during an application release.

Code in `automation_hub`, `control_center`, `scripts`, `config`, `deploy`, `tests`, `tools`,
`multilang_quiz`, `.github`, and root Python files is synchronized. Existing runtime data,
generated assets, root state JSON files, credentials and `.venv` are preserved. Dependency
manifest changes pause deployment for a tested environment update. Conflicting server-only
code also pauses deployment, rather than silently destroying a hotfix. Previously applied
hotfixes identical to main are accepted. Do not run `git clean` or `git reset --hard` on production.

The deployer holds the video worker's own lock before stopping services. An active video
job defers deployment. It backs up every changed code file, applies code, updates HEAD, starts
all three production services and checks `/healthz` plus systemd state. Failure restores
the previous files and HEAD. An interrupted deployment is recovered on the next timer run.
A failed release is not retried until a new main commit is available.

Inspect actual deployed revision and status:

```bash
cat /opt/korea365/data/deploy-status.json
systemctl list-timers korea365-deploy.timer
journalctl -u korea365-deploy.service -n 30 --no-pager
```

Backups are private under `data/deployment-backups/`. A successful code deployment does not
claim that paid provider credits, external account permissions, or individual publications
are healthy; those require their own end-to-end checks.

## Initial installation reference

Install `ffmpeg`, `fonts-nanum`, Python 3.11+, create user `korea365`, clone this repository at
`/opt/korea365`, create `/opt/korea365/.venv`, and install `requirements-control-center.txt` plus
`pillow google-api-python-client google-auth google-auth-httplib2 google-genai`.

Put credentials in `/etc/korea365/control-center.env` (mode `600`). It must include Google/YouTube
OAuth variables, `SHEET_ID`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, voice IDs,
and output-folder IDs. Playlist input-folder IDs are intentionally unused. Recommended generation
settings are `LYRIA_MODEL=lyria-3.5`, `GEMINI_IMAGE_MODEL=gemini-3.1-flash-image`,
`LYRIA_TRACK_COUNT=20`, and `LYRIA_MAX_TRACKS=30`.

Copy the four unit files to `/etc/systemd/system/`, then run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now korea365-control.service korea365-youtube-worker.service korea365-youtube-scheduler.timer
```

The nginx virtual host for `control.korea365.org` should proxy to `127.0.0.1:8000`.

After deployment, queue exactly one Cafe Romantic validation playlist with all three locks
(VPS render, fresh Lyria music, fresh benchmark-informed Gemini thumbnail):

```bash
sudo -u korea365 /opt/korea365/.venv/bin/python /opt/korea365/scripts/youtube_vps_worker.py --enqueue-channel globalmusic
```

Watch it with `journalctl -u korea365-youtube-worker.service -f`. The upload remains PRIVATE.
