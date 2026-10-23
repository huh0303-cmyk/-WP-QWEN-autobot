# Seoul Journal Shorts Studio deployment notes

This is a separate service intended to reuse the London Project Hostinger VPS without replacing existing services.

Before enabling:
1. Check VPS RAM/disk and existing services; do not change existing services.
2. Create a dedicated Linux user `seoulstudio` and writable app artifact directory.
3. Create root-owned `/etc/seoul-journal-studio.env` with OPENAI_API_KEY, ELEVENLABS_API_KEY, SEOUL_JOURNAL_VOICE_ID, YOUTUBE_OAUTH_CLIENT_ID, YOUTUBE_OAUTH_CLIENT_SECRET, SEOUL_JOURNAL_YOUTUBE_OAUTH_REFRESH_TOKEN, SEOUL_JOURNAL_YOUTUBE_CHANNEL_ID. Restrict permissions.
4. Install ffmpeg with the subtitles/libass filter and Noto CJK fonts.
5. Configure a TLS-protected reverse proxy with authentication to 127.0.0.1:8501. Never expose port 8501 directly to the public internet.
6. Review control.korea365.org routes before adding a link. This app does not modify the existing control center.

The app's upload action requires explicit checkbox confirmation, validates the expected YouTube channel ID and uploads PRIVATE only. It does not automatically publish publicly. AI generation costs may occur when generation buttons are used. Session logs are not a durable central audit log.
