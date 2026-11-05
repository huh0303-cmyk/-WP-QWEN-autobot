# Global Weekly Coupang Set v7.0 — LOCKED DESIGN

Effective: 2026-11-05 (Asia/Seoul)
Canonical catalog: `config/affiliate/global-weekly-10.json`
Active set: `global-week-2026-11-05`
Lock window: 2026-11-05 00:00 KST through 2026-11-12 00:00 KST (168 hours)

## One set shared across the network

The same ten product records are the single source of truth for all registered WordPress, Blogger/Blogspot, YouTube, Instagram, Threads and TikTok destinations. Do not create a different product mix or tracking URL set per site, account, channel, post or article during the lock window.

Composition and display order:
1. Featured first: Lacto-Fit Gold probiotic (health functional food)
2. Remaining four health functional food / wellness products
3. Five K-Beauty skincare products

The category balance remains exactly five health + five K-Beauty; the featured first item is a merchandising priority, not an extra slot.

The ten items are Coupang Partners only. Product title, product ID, tracking URL and image URL must stay paired. No random selection or per-channel substitution.

## Channel-aware rendering

- WordPress: ten responsive product cards at the bottom of eligible articles; use the same global records.
- Blogger/Blogspot: place official partner logos immediately above the ten product cards at the article footer where template support allows; do not place them at the article top.
- YouTube: list the ten tracked links in the description, grouped into K-Beauty (5) and health (5); use a pinned comment/index where permitted. Do not describe text links as embedded shopping cards.
- Instagram: use one canonical weekly landing page as the profile/bio destination; use Story links or other clickable surfaces only where the account supports them.
- Threads: use the same weekly landing page in profile or post links where supported; do not assume all post URLs are clickable.
- TikTok: use the same weekly landing page in bio; native product links only when enabled for that account. Do not rely on unsupported caption URLs.
- All social profiles should point to the same current weekly landing page. That page must show the same ten items and tracking URLs.

## 7-day lock and review

During the 168-hour window, keep the set unchanged across all channels. Do not rotate products just to make the weekly list look new.

A midweek replacement is permitted only when a tracked link is broken, the product is unavailable, its image fails or loses permission, or a documented platform/policy restriction requires it. Replacement must come from the authenticated Coupang Partners account, pass link/image checks, and be updated consistently across all channels. Record the change and retain the previous snapshot for rollback.

At the weekly review, evaluate clicks, orders, confirmed commissions, availability, tracking-link health and image health. Retain products with evidence of performance; replace only selected weak or invalid products. Do not invent sales rank, popularity, conversion, price or commission data.

## Disclosure and safety

Show the required Coupang Partners disclosure at product placements and on the weekly landing page. Do not make medical treatment or disease-prevention claims. Do not state that every purchase is guaranteed to earn commission.

Top partner banners are separate from the ten Coupang product cards. Their links must be verified independently. OLIVE YOUNG's current stored URL is not yet verified for commission attribution; do not describe it as confirmed tracking until validated.

## Deployment gate

This document and the canonical catalog define the global design. They do not by themselves publish or edit every destination. Keep fleet live writes disabled until the K-Health365 pilot is verified and the owner explicitly approves expansion. Platform adapters must check account permissions and platform rules; report unsupported edits as pending rather than claiming success.


## Official partner logo placement

For the K-Health365 pilot, use the official logo artwork from each company's own asset domain: Coupang Partners asset, OLIVE YOUNG official CDN, and Trip.com logo URL declared by Trip.com itself. The logo module belongs immediately above the ten product cards in the article footer, not at the top of the article. Coupang's official media guidelines prohibit hyperlinking its logo and prohibit placing it together with third-party marks; therefore show the Coupang logo in its own standalone row with a separate tracked text link, then show OLIVE YOUNG and Trip.com logos in a separate row. Preserve original artwork and proportions.
