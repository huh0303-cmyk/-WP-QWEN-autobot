# WordPress Publication Policy

Authority: `MASTER_MONETIZATION_STRATEGY_2026.md`.

## Enforced behavior

- Ordinary WordPress blogs always create `draft` posts for review.
- A public WordPress post is allowed only when the destination is a newsroom and both
  `WP_POST_STATUS=publish` and `WP_PUBLICATION_APPROVED=true` are present.
- A malformed, missing or contradictory setting fails closed to `draft`.
- Draft creation does not perform public-page verification or IndexNow submission.
- Public newsroom creation still requires the existing source, length, quality, REST
  response-status and public-page verification gates before IndexNow.

## Active workflows

- `daily-network-publish.yml`: ordinary WP, `draft`, no public approval.
- `newsrooms-daily-publisher.yml`: newsroom-only target resolution, explicit public approval.
- `wp-create-draft.yml`: manual draft path remains available.

`WP_AUTOPUBLISH_ENABLED` is retained as the legacy engine execution switch; it no longer
determines whether a post is public. Public visibility is controlled by the fail-closed
policy above.
