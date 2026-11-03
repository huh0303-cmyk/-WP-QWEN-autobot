# London Project — 10-item affiliate and omnichannel publishing standard

Effective 2026-11-03. This is the canonical portfolio policy.

## Fixed provider allocation per eligible article
- Coupang Partners: exactly 4 offers.
- Olive Young Global: exactly 2 offers.
- Trip.com: exactly 2 offers.
- Agoda: exactly 2 offers.
- Total: exactly 10 offers.

The four Coupang positions are two article-topic offers, one site-audience-relevant health/lifestyle offer, and one Korea daily-life essential. Olive Young positions are beauty/personal-care offers relevant to the audience. Trip.com positions are travel, accommodation, transport, activity or eSIM offers. Agoda positions are accommodation/hotel offers. A provider slot must not be filled with an unrelated item merely to hit the count; if no suitable verified offer exists, hold that content item and report the missing slot.

## Per-destination catalog isolation
Every WordPress domain and every Blogger blog has its own catalog. A WordPress catalog must never be reused for its Blogger counterpart. Each catalog must contain four Coupang, two Olive Young, two Trip.com and two Agoda offers with real account-generated tracking URLs, permitted image URLs, and verification flags. Commission percentages are read from current provider dashboards/terms; no fixed commission is promised or fabricated.

## Blog rendering
New articles receive a responsive 10-card affiliate section: four columns on desktop and two on mobile. Every card contains the permitted product image, title, tracking URL and “쇼핑하기” CTA. Add an affiliate disclosure and sponsored/nofollow attributes. Existing content is backfilled in small, reportable batches, append-only and idempotent. Preserve existing copy and links.

## Omnichannel distribution
- WordPress: 25 requested destinations; new-content insertion and existing-post backfill.
- Blogger: 33 requested destinations; new-content insertion and existing-post backfill.
- YouTube: 23 channels; place relevant tracking links in descriptions and pinned comments only where allowed. Existing video-description edits require verified channel OAuth permissions.
- TikTok: registered accounts; use bio/product-link surfaces supported by that account and region. Do not assume arbitrary clickable caption links.
- Instagram: registered accounts; use profile/story/product-link surfaces available to the account. Do not assume caption URLs are clickable.
- Threads: registered accounts; use post/profile links subject to current platform rules.
- Facebook: registered Pages; use post/page links where authorized.

Each social platform receives a native adaptation of the source content rather than verbatim cross-posting. Maintain one job ID per destination, deduplicate by platform/content ID, record a publication receipt, and retry only failed destinations.

## Rollout and safety
1. Finish and validate K-trip365's own 10-offer catalog.
2. Build KStudy365's separate catalog.
3. Expand to the remaining eligible WordPress sites, then 33 Blogger blogs.
4. Connect and verify the 23 YouTube channels.
5. Verify each TikTok, Instagram, Threads and Facebook account and its publish/edit permissions.
6. Run preview first. Live writes require an explicit manual approval gate and verified credentials.
7. Never delete content, replace existing affiliate links, or claim an edit/publish succeeded without reading back a platform receipt.

## Current implementation status
This policy is the approved target architecture, not a claim that every account is connected or every post has already been edited. The existing affiliate runner and four-network matrix still need to be aligned to this 10-total allocation before enabling live writes. Social connectors and existing-post edit scopes must be verified per account. Missing credentials, partner links, media, or API permissions are reported as blocked/awaiting setup, not silently skipped.
