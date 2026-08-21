# 27-site WordPress clean rebuild

## Non-negotiable rules

1. Legacy automatic publishing stays locked.
2. New content is created as `draft`; publication requires editorial approval.
3. No fabricated first-person experience, credentials, testing, patient/client story, or source.
4. Every factual/YMYL claim must be traceable to a current primary or authoritative source.
5. Each article must pass `content_quality_gate.py`: at least 900 meaningful words/eojeol, four H2/H3 sections, two relevant images, complete descriptive ALT text, and two external sources.
6. ALT describes what is visible and why it matters in the surrounding section. It is not a keyword list and must not duplicate the title.
7. Existing posts are never deleted. Failed posts become recoverable `private` posts only after a manifest review and exact confirmation token.
8. `kskin365.com` remains retired. `k-health365.com` is rebuilt first. `jobkoreaglobal.com` remains review-only until ownership/status is resolved.

## Safe operating order

1. Run **WP Network Rebuild** with `mode=audit`, `site=k-health365.com`.
2. Download and review `rebuild_content_manifest.json`.
3. Run `mode=apply` only after review, with `confirm=PRIVATE_REBUILD_FAILED_POSTS`.
4. Rebuild a small set of cornerstone drafts for K-Health.
5. Validate factual claims, image licenses, image relevance, ALT, canonical URL, schema, and mobile rendering.
6. Publish one reviewed article; observe crawl/index behavior before continuing.


