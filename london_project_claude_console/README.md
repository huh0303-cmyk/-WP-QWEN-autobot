# 런던프로젝트클로드 — Local Browser Console

## Current architecture
This is the local operator console for Naver/Tistory browser workflows. It must run on the owner's Windows PC because those platforms may require an authenticated interactive browser session. It is not a VPS service.

- WordPress, Blogspot and newsroom actions are dispatched to GitHub Actions workflows.
- YouTube publishing uses the dedicated GitHub Actions worker and remains cost-hold gated.
- Naver/Tistory browser automation stays local to the user's PC until a supported non-interactive GitHub-hosted authentication path exists.
- VPS, SSH, systemd, server-local queues, and server-hosted n8n are retired and must not be recreated.

## Local setup (Windows PC)
Requirements: Node.js 18 or newer, Chrome installed, and the user's existing authenticated browser profile.

1. Open PowerShell in this directory.
2. Run `npm install`.
3. Set required environment variables in the current PowerShell session or a local untracked .env file:
   - LPC_USER
   - LPC_PASS
   - LPC_SESSION_SECRET
   - LONDON_PROJECT_GITHUB_TOKEN (GitHub Actions read/write permission for workflow dispatch)
4. Run `npm start`.
5. Open the local URL printed by the server. Do not expose the console publicly without a security review.
6. Confirm the correct Chrome profile is authenticated before any Naver/Tistory task.

Never commit tokens, passwords, cookies, OAuth JSON, or local browser profiles.

## GitHub Actions dispatch
The console uses GitHub's official workflow-dispatch API for the mapped actions:
- wp25_tick -> daily-publication-floor.yml
- blogger33_daily -> blogger-33-daily-github.yml
- news2 -> newsrooms-daily-publisher.yml
- Four-agent pipeline -> london-content-pipeline.yml

GitHub workflow runs are the execution record. A dispatch acknowledgement is not proof that a post was published; verify the resulting post/video ID, public URL, destination account/channel ID, privacy state, and durable receipt.

## Current limitations
- Four-agent pipeline dispatch is implemented, but stage-only retry and rewrite-only workflow dispatch remain explicitly HOLD until a GitHub-native state restore/retry path is available.
- The four-agent workflow is blocked unless LONDON_PIPELINE_COST_HOLD is explicitly false in the london-project environment. Public mode additionally requires explicit confirmation.
- The YouTube worker is manual-only and blocked unless YOUTUBE_COST_HOLD is explicitly false in the youtube-channels environment.
- Naver/Tistory are not claimed as GitHub-hosted. If the local authenticated session is unavailable, stop and mark HOLD.
- Do not change existing post/video privacy or delete existing content during infrastructure migration.

## Troubleshooting
- Missing LONDON_PROJECT_GITHUB_TOKEN: no GitHub workflow was started. Configure a private local token with the minimum required Actions permissions.
- GitHub dispatch failure: inspect the target workflow file, repository/ref, token permissions and workflow run history.
- Browser login/captcha failure: resolve it in the user's local browser session; do not attempt server-side login or copy cookies to GitHub.
