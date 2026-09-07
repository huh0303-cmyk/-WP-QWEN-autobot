# Korea365 VPS runtime

Production topology is `nginx -> gunicorn control center -> durable VPS queue -> single YouTube worker`.
Render and GitHub Actions are not YouTube render hosts.

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
