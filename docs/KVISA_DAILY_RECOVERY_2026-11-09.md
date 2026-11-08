# K-Visa365 daily publication recovery

Owner instruction: repair K-Visa365 publication and automatically publish one article per day. This instruction authorizes the dedicated site publisher; it does not reactivate publishing on other sites.

## Verified findings

- Public REST probe on 2026-11-09 KST returned HTTP 403, `x-hcdn-request-id`, and the HTML title `Checking your browser before accessing. Just a moment...`. Hostinger's browser challenge currently intercepts REST traffic before WordPress JSON can be read.
- GitHub workflow state inspection through the authorized ChrisHUH PC confirmed `daily-network-publish.yml`, `wordpress-25-twice-daily.yml`, and `daily-publication-floor.yml` are `disabled_manually`.
- Existing registry already specifies `wp_kvisa365`, `https://k-visa365.com`, secret `KVISA365COM`, and daily_min=daily_max=1.
- This cloud environment has no secrets or outbound identities. The authorized PC's existing GitHub CLI session is used for deployment without revealing credentials.
- No callable Browser JavaScript or cloud desktop control tool is exposed in this session. Hostinger authenticated settings cannot be inspected or changed through the available tools. No Hostinger API credential was found among GitHub secret names. CDN settings and WordPress authentication were not changed.

## Implemented recovery

- Dedicated `kvisa-one-daily.yml` runs daily at 09:17 Asia/Seoul and supports manual dispatch. It does not depend on enabling the disabled fleet workflows.
- Authentication and publish capability are checked before generation. Existing published or scheduled articles on the current KST day suppress additional generation. All access or malformed-inventory errors block publication.
- The existing production article engine is called once for K-Visa365 only. No automatic retry of an uncertain write is made.
- A separate authenticated inventory and public permalink/title verification produces publication receipts. A successful dispatch or script return alone never establishes a published article.
- Preflight and publication receipt artifacts are retained for 30 days.
- Eight unit tests pass: KST boundary, old post, current public post, current future post, empty day, CDN challenge, authentication failure, missing publish capability, and absence of a public verification receipt (some cases share fixtures). Workflow YAML parsing and whitespace checks pass.

## Outstanding live repair

Authenticated GitHub execution must verify secret availability and live access. If the same Hostinger challenge remains, the hosting owner must provide a callable authenticated Hostinger control surface or configure the path-specific CDN challenge exception. Preserve WordPress authentication and TLS verification. Do not disable CDN or security site-wide, bypass through origin IPs, or claim a public URL until a receipt is verified.
