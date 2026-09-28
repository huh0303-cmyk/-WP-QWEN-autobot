# LondonProjectGPT: writing, image and GSC submission

Status: implementation and live verification in progress, 2026-09-28 KST.

## Current providers and limits

- Writer: Gemini 2.5 Flash once, then GPT-5 mini paid API once if configured, then local Ollama Qwen 2.5 3B. A free ChatGPT browser account is not an API fallback. A failing quality gate can retain the prior passing article; otherwise the stage fails.
- The shared monthly `budget_guard` is an estimated spend cap, not a provider quota meter. It does not guarantee absence of 429 errors, concurrent overspend or free-tier exhaustion. Provider attempts are bounded; retries are not unbounded.
- Image: approved Pexels/Pixabay stock and permanent hosting when all keys and `STOCK_IMAGES_ENABLED` are present; then Replicate SDXL Lightning and Flux Schnell, one attempt each, maximum one image. If none works, the article continues without an image. The live VPS had Pexels/Pixabay API keys but no active stock flag, Replicate token or GH asset token when inspected. Therefore image generation is not currently assured.
- Agent 4: manual mode hands off copyable title, HTML and image URL; the user publishes and pastes the public URL, which is checked for selected host, HTTP 200 HTML and article title. Auto mode queues the existing WordPress publisher worker or Blogger publisher and stores a post ID and URL receipt. Re-running a completed publication returns its receipt without a second publish call.

## GSC path

After a verified *public* receipt, the server dispatches `.github/workflows/london-gsc-submit.yml` through its existing `GH_TOKEN`. The action checks that the URL is on the selected site, publicly reachable and not marked `noindex`; checks the site's sitemap; uses the existing GitHub `GSC_SERVICE_ACCOUNT_JSON` secret to find the site's verified property; submits its sitemap with the Search Console Sitemaps API; verifies the API response; and copies a small result receipt to `data/london-gsc-receipts`. The web app displays queued, submitted or failed. Drafts do not dispatch. The GSC credential remains in GitHub Actions, not in the VPS application environment.

The general Indexing API is restricted by Google to JobPosting and BroadcastEvent pages. Standard articles use sitemap submission. `submitted` means Google received a sitemap request; it does not mean the new URL is indexed. The displayed receipt deliberately does not claim indexing.

## Operational verification / remaining work

- Targeted local tests, workflow validation and live dry run should be recorded in the activity ledger.
- An absent site property, a private/invalid post, a missing credential or a GitHub dispatch permission failure must appear as a failed submission. A GSC failure never triggers another WordPress/Blogger publication.
- If a submitted post is not indexed later, inspect its URL in Search Console for canonical/noindex/crawl issues; this workflow cannot promise immediate indexing.
