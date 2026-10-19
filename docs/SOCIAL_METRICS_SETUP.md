# Daily social profile metrics

The London Project account table reads `docs/social_metrics.json`. The scheduled workflow `Daily social account metrics` refreshes it every day at 07:23 KST and keeps a dated copy under `data/social_metrics_history/`.

## Collected fields

- Subscribers/followers and following count when provided by the platform API
- Content/video/post count
- Total channel views or account likes when exposed by the API
- Account creation date where officially exposed (currently YouTube's `snippet.publishedAt`)
- Latest published item date and, when available, latest item's views, likes, and comments
- Last successful metric fetch time, data source, status, and an error reason if the API call cannot run

Missing data stays null; it is never replaced with zero. If a collection fails after a prior successful snapshot, the previous values are retained and labelled stale. An API that does not expose a creation date is marked as such rather than assigning a guessed date.

## Credentials

YouTube public channel statistics use the existing GitHub Actions environment secret `YOUTUBE_API_KEY` and the channel IDs in `docs/social_inventory.json`. The key must have YouTube Data API v3 enabled.

For Facebook Pages, Instagram Business/Creator accounts, Threads, and TikTok, put per-account credentials into the **GitHub Environment** `google-metrics` secret named `SOCIAL_METRICS_AUTH_JSON`. The key names are the platform handles shown in the inventory; a full profile URL can be used instead when the handle is missing. Use the structure in `config/social_metrics_auth.example.json`.

- Facebook: `page_id` and a Page access token with permission to read the Page's public metrics/posts.
- Instagram: Instagram Business/Creator `user_id` and Graph API token with the required insights/content permissions.
- Threads: Threads user ID and token with the needed profile, content-read and insights permissions.
- TikTok: an OAuth access token for each account authorized through a TikTok developer app with user statistics and video-list scopes.

Never commit real access tokens to the repository and do not paste them into a chat message. Add them only in the GitHub Environment secrets settings. A personal Facebook profile is not interchangeable with a Facebook Page and its Page token.

## Platform limitations

The official APIs do not provide account creation dates for every platform. In particular, TikTok's standard user-info API, Instagram Graph API, and Threads API do not expose an account's original creation timestamp. For those platforms, the dashboard will show that the creation date is not available from the API. A latest/oldest public post date is not the same thing as the account creation date.

The collector uses official APIs only. It does not parse public page HTML, bypass login, or circumvent platform rate limits/permissions. When per-account credentials are absent, the workflow still records the account row and marks the specific authentication blocker.
