# 런던프로젝트GPT — GitHub-only Operations Manual

## Daily check
1. Open the GitHub Actions page for huh0303-cmyk/-WP-QWEN-autobot.
2. Review failed or cancelled runs and inspect their logs/artifacts without exposing secrets.
3. For every reported publication, verify the destination URL/content ID, account or channel ID, privacy state, and timestamp.
4. Check the Google Sheets calendar and publication ledger for duplicate keys and unresolved attempts before retrying.
5. Keep YouTube cost hold active unless the owner explicitly approves a cost review and releases it.
6. Treat Naver/Tistory tasks as local-browser HOLD unless the user's authenticated PC session is available; never claim they are GitHub-hosted.

## YouTube
- Current workflow: .github/workflows/youtube-github-worker.yml.
- Manual dispatch only; choose one channel and explicitly confirm publication.
- The youtube-channels environment variable YOUTUBE_COST_HOLD must be explicitly false or the workflow stops before work.
- Confirm OAuth identity against the exact channel ID before upload.
- Do not retry an upload after an ambiguous network failure until the calendar/receipt is reconciled.
- Do not change privacy on existing videos as part of infrastructure migration.

## Platform routing
- WordPress: GitHub Actions to the destination WordPress REST API, using per-site secrets.
- Blogger/Blogspot: GitHub Actions using Google Blogger API/OAuth.
- Naver/Tistory: user-PC authenticated browser execution only until a supported non-interactive path is approved.
- YouTube: GitHub Actions workflow with exact channel identity and publication receipts.
- Other social platforms: direct API workflows only when write permissions and destination IDs are verified.

## Failure rules
- A green workflow status is not proof of publication.
- Missing credentials, identity mismatch, duplicate suspicion, cost hold, or missing receipt means HOLD.
- Do not delete content or mass-change privacy during cleanup.
- Never use VPS, SSH, systemd, server-local queues, or server-hosted n8n as a fallback.
- See docs/GITHUB_ONLY_NO_VPS_MIGRATION_INVENTORY_2026-10-26.md for outstanding migration gates.
