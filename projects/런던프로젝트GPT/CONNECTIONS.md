# 런던프로젝트GPT — Platform Connections (GitHub-only target)

## WordPress
- Canonical path: GitHub Actions -> WordPress REST API -> verify the exact public URL and post ID.
- Per-site credentials remain in GitHub Actions secrets; never store a server credential JSON file.

## Blogger / Blogspot
- Canonical path: GitHub Actions -> Google Blogger API/OAuth -> verify the returned blog/post ID and public URL.
- Durable scheduling state is in the approved Google Sheets/repository state, not a runner's local filesystem.

## YouTube
- Canonical path: GitHub Actions -> youtube-github-worker.yml -> YouTube API.
- The channel registry's exact YouTube channel ID is the identity key; display names are not identity.
- Cost hold remains enabled unless explicitly released by the owner after cost review.
- Current worker is manual-only and not yet considered production-verified until an authorized canary produces a verified receipt.

## Naver / Tistory
- Canonical path remains the user's PC and authenticated browser profile while the platforms require interactive login.
- These platforms are HOLD if the local session is unavailable; do not invent an API connection or reuse another account's token.

## Instagram / Threads / Facebook / TikTok
- Use a GitHub-hosted API workflow only when the official account/destination ID and write permission are verified.
- Read-only access or a profile URL does not prove write permission.

## Retired
VPS, SSH, systemd, server-local queues, n8n-on-server, /opt/korea365 and /etc/korea365 are not approved production dependencies.
