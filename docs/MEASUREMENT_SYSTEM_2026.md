# Measurement System — 2026

`올뉴종합상황실` is the canonical measurement control plane. A blank monetary
cell is not zero. Revenue, cost, and net profit remain `연결 필요` until every
required official source for that period supplies an actual value.

## Automated now

- Per WordPress site: published post count, footer visitor counts, sitemap
  indexed/submitted counts, derived unindexed count and index rate, recent
  indexed-count change, GSC clicks/impressions/CTR/average position, and errors.
- YouTube public channel totals: subscribers and views with daily change.
- Officially connected SNS follower counts. Missing credentials or unsupported
  official endpoints are written as connection errors, never fabricated numbers.

## Connection required

- AdSense today/7-day/month revenue, RPM, and CPC: AdSense Management API OAuth.
- YouTube watch time and revenue: owner OAuth with YouTube Analytics monetary scopes.
- TikTok/Meta/Threads views, engagement, post counts, and growth: official account
  insights permissions for every reporting account.
- OpenAI, Gemini/Google Cloud, Replicate, and other provider costs: official billing
  API or billing export. API-call counts are not converted into estimated currency.

## Definitions

- `사이트맵 보고 색인수` is the Search Console Sitemaps API aggregate, not a full
  URL Inspection census.
- `미색인수 = max(사이트맵 제출URL수 - 사이트맵 보고 색인수, 0)`.
- `색인율 = 사이트맵 보고 색인수 / 사이트맵 제출URL수 * 100`; unavailable when
  the submitted count is zero or missing.
- `최근 색인 증가` compares the current official sitemap count with the previous
  committed collector snapshot. No previous snapshot means blank, not zero.
