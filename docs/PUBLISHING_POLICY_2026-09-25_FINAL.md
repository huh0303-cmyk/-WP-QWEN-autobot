# Publishing Policy — 2026-09-25 Final

- The locked ten YouTube channels are the only YouTube production set. Starting 2026-09-26, each receives two or three VPS-generated private review jobs per seven-day cycle. YouTube is not dispatched by GitHub Actions and is never automatically made public.
- The other ten reference YouTube cards are inventory only and are excluded from production scheduling.
- TikTok 6, Instagram 6, Facebook 6, and Threads 6 each receive one GitHub-managed hourly slot per KST day. The account order is reshuffled daily, so exactly one of the 24 SNS accounts is selected each hour.
- Tistory 5 and Naver 3 remain one post per account per day after their persistent local login tests are complete.
- A schedule request is not publication proof. Each platform must retain account/date idempotency and a remote publication receipt.
- GitHub stores code, policy, schedules, and secret names only. Tokens remain in GitHub Secrets or the authorized runtime.

## Required GitHub secret bundle

`SNS_ACCOUNT_CREDENTIALS_JSON` must contain a separate record for every one of the 24 SNS cards: exact platform, role key, immutable account/page ID, access token or refresh material, granted scopes, and expiry. The workflow must reject a credential whose returned identity differs from the selected card.

The hourly SNS workflow is installed now, but missing credentials are a hard failure, not a successful publication. After the owner completes platform login/consent, the next GPT must populate or rotate the secret bundle, perform one account-specific test, and connect the selected payload to the platform publisher.
