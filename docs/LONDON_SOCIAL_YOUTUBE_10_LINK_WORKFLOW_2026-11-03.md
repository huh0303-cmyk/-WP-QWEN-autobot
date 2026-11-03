# Social & YouTube affiliate distribution — locked workflow

Effective: 2026-11-03. This is the canonical workflow for YouTube, TikTok, Facebook, Instagram and Threads.

## Per-content link allocation

Every source content item is assigned exactly ten verified affiliate offers:
- Coupang Partners: 4
- Olive Young Global: 2
- Trip.com: 2
- Agoda: 2

The exact same 10-offer allocation is used for new content and existing-content backfill. Catalogs are destination-specific; no URL is fabricated, guessed, or copied from another account's catalog. A content item is blocked if the destination catalog does not contain exactly ten valid offers with the required provider mix, verified tracking links and permitted image rights.

## Destination scope

- YouTube: all 23 entries in `config/YOUTUBE_23_CHANNEL_MASTER_LOCK_2026-09-27.json`. Planned channels with no channel ID remain visible as blocked; they are never silently treated as publishable.
- TikTok, Facebook, Instagram and Threads: every account row in `config/sns_six_channel_policy.json`. Accounts that do not exist or are not identity-verified remain blocked and are not treated as connected.
- New and existing content use the same per-destination job model. Each job has a stable ID, independent blockers, and destination-scoped retry.

## Platform placement rules

- YouTube: all ten URLs in the video description; a concise grouped link section may also be copied to a pinned comment when channel permissions and comment policy allow it.
- TikTok: use supported product-link surfaces and the profile bio link. Put direct caption URLs only where the account, region and current TikTok feature make them clickable. If ten separate clickable links cannot be represented, preserve all ten in the destination link hub/landing page and record the actual placement; do not claim ten caption links were clickable.
- Instagram: use profile link and Story link stickers where available. Captions may contain URLs for context, but are not counted as clickable unless the platform/account actually makes them clickable. A link hub can carry all ten URLs.
- Threads: include direct URLs in the post body where allowed; use profile link as supplementary placement.
- Facebook: include all ten URLs in the Page post where appropriate and allowed; retain them in the Page link surface as a supplementary destination.

All copy is adapted to the destination's language, topic and format; no verbatim cross-platform duplication. Preserve existing content. Never delete posts or overwrite existing affiliate links. Health and travel claims must follow the portfolio's evidence and safety rules.

## Automation sequence

1. A new-content publisher sends a `repository_dispatch` event of type `london_content_published` with `content_id`, `title`, `url` and `summary`; alternatively an operator starts the workflow manually.
2. `.github/workflows/london-social-affiliate-10-links.yml` runs the queue builder.
3. The builder loads the 23-channel YouTube master and all social-account rows, validates each destination-specific 10-offer catalog, and creates one independent job per destination.
4. Each job reports exactly ten links or explicit blockers. Missing catalog, missing identity, missing OAuth permission or unsupported placement is never reported as success.
5. The queue is uploaded as a GitHub Actions artifact for review and downstream platform adapters.
6. A platform adapter may publish only after account-specific OAuth scopes, platform policy checks, manual live-write approval and receipt/readback verification are implemented and enabled.

## Current execution boundary

This commit implements the canonical policy, event/manual trigger, per-destination queue generation, validation and artifact reporting. It deliberately does not claim that posts have already been edited or published. The current account inventory records `publish_connected=false` for the social accounts, and the workflow does not contain verified write adapters/tokens. Therefore this workflow is safe by default and produces blocked/ready queue records only. Live publishing remains disabled until each adapter and account authorization is verified.
