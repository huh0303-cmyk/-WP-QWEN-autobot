# Playlist owner policy deployment — 2026-09-08

Merged PR 42: existing approved music and Gemini app exports are the defaults; paid API generation is opt-in. Romantic playlists select equal track counts in French, Japanese, Spanish and Italian. Korean acoustic K-pop remains Korean. Upload validation requires English titles up to 100 characters and English descriptions of 800–1200 characters. All automated uploads remain private.

Merged PR 43: runtime secrets are encrypted to the existing VPS public key; only the VPS private key can decrypt them. Plaintext credentials are stored at /etc/korea365/youtube-runtime.json with mode 0600. No plaintext credentials are in Git or artifacts.

On srv1959434, the existing control service uses root and /etc/korea365/control.env. The installed YouTube worker matches this runtime user and environment and invokes scripts/run_youtube_vps.py --daemon. Do not replace its local service with the generic example until those differences are reconciled.

Verified: Cafe Romantic OAuth resolves to the locked owner channel. Worker service installed and enabled. Gemini subscription app generated a new cafe image and a 3-minute French vocal sample at https://gemini.google.com/app/1046918719863b9f.

Still outstanding: import the new Gemini exports to the per-channel Drive banks, verify audio language tags (existing filenames mostly lack explicit language labels), complete a full mixed-language private upload, and verify the other channels. Scheduler activation and five successful uploads are not claimed by this deployment note.
