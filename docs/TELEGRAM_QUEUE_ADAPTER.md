# Telegram queue adapter

The adapter in `scripts/telegram_queue_bot.py` receives Telegram commands and appends them to the existing Google Sheets tab `자동화_발행대기`. It does **not** publish posts and does not use Naver passwords.

## Required environment

- `TELEGRAM_BOT_TOKEN`: token from BotFather; keep it in the host's secret environment, never in Git.
- `TELEGRAM_ALLOWED_CHAT_IDS`: comma-separated numeric Telegram chat ID(s) or user ID(s) allowed to enqueue.
- `SHEET_ID`: the existing London Project Google Sheet ID.
- Google Sheets credentials expected by `gsheets_direct.py` must be configured on the host, using the existing local OAuth/service-account setup.

Install the runtime dependency in the bot's dedicated virtual environment:

```bash
python -m pip install "python-telegram-bot>=20,<23"
```

Start the process on a persistent trusted PC/VPS (not a 30-minute GitHub Actions schedule):

```bash
python scripts/telegram_queue_bot.py
```

## Commands

```text
/naver1_365 Title | Body
/naver2_365 Title | Body
/naver3_365 Title | Body
```

The adapter resolves the destination against an enabled Naver account row in `자동화_플랫폼계정` and writes a canonical row to `자동화_발행대기` with `status=ready`, `publish_now=FALSE`, and `visibility=draft`. This is queue registration only. The existing local Naver runner remains responsible for editing/publishing and result verification. An account mismatch or Sheets error does not create a queue item.

## Important

- Configure the allowed Telegram IDs before starting; the bot refuses to start without this allowlist.
- Do not place Telegram tokens, Naver passwords, or Google OAuth secrets in repository files or commit messages.
- This adapter is not yet running or hosted by this commit. Deployment and a test message must be performed on the trusted host before the bot can receive commands.
