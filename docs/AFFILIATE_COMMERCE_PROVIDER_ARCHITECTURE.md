# Multi-Provider Affiliate Commerce Architecture

## Goal
Start with Coupang Partners, while keeping the system ready for additional approved shopping, travel, accommodation and connectivity affiliate providers.

## Shared architecture
- Content planner: selects exactly ten offers per post. The first two are the strongest matches to the article. The remaining eight come from useful Korea lifestyle, health, K-beauty, eSIM/data, travel and accommodation categories. These are flexible editorial categories, not fixed merchant quotas.
- Provider adapters: isolate each partner's product search/feed, official tracking-link creation, image/creative retrieval and reporting API.
- Normalized offer record: provider, offer ID, site ID, title, destination URL, verified affiliate URL, image URL, category, keywords, price/currency, availability and popularity evidence.
- Site-specific catalogs: products are scoped to each blog/site and are not silently shared across unrelated sites.
- Common renderer: mixed-provider cards use one responsive layout; image, title and CTA share the same verified affiliate URL.
- Existing WordPress and Blogger publishers call the common engine, not individual partner APIs.
- Reporting: record provider, site, post and placement identifiers; import click/conversion metrics only from official partner reports or APIs.

## Initial providers
- Coupang Partners: first active provider. Use the authenticated partner portal's generated affiliate URL and official image/HTML creative. Do not infer tracking links from ordinary product URLs.
- Alibaba: planned; activate only after account approval and official feed/API/link-generation access are confirmed.
- Airbnb: review required; do not assume current program availability or eligibility. Activate only after an official partner program is verified.
- Agoda and other travel providers: planned; hotel/trip offers can occupy travel slots once approved links and creatives exist.
- Awin or another affiliate network: planned; use official publisher APIs for deep links, feeds and reports when account access allows.

## Security and compliance
- Credentials stay in GitHub Actions Secrets or server environment variables.
- Never scrape behind login, bypass access controls, or invent tracking URLs, images, prices, commission rates or attribution windows.
- Only verified account-owned tracking links and official/licensed creatives may be published.
- Apply each provider's disclosure, destination, attribution and creative rules separately.
- No cross-site catalog sharing unless explicitly authorized.

## Rollout
1. Keep current Coupang publishing stable.
2. Add a provider-neutral offer schema and registry.
3. Normalize Coupang portal captures.
4. Build mixed-provider selection and rendering.
5. Add each new provider only after account authorization and link validation.
6. Preview on JobKorea365, then expand.
7. Backfill old posts only after each site's catalog has ten eligible offers.

A provider marked planned is not connected or generating commissions.