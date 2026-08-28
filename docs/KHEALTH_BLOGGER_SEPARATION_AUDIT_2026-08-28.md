# k-health365 Blogger separation audit — 2026-08-28

## Intended ownership

- `https://k-health365.com/` is the WordPress property and canonical production site.
- `https://k-health365.blogspot.com/` is a separate Korean Blogger publication.
- The two properties may cover related subjects, but must not publish copied or lightly paraphrased articles.
- Blogger automation is draft-only. A human performs the final review and publication.

## Live observations before separation

- WordPress root returned HTTP 200 over HTTPS with a self-referencing canonical and index/follow robots metadata.
- `www.k-health365.com` redirected to the apex WordPress URL.
- WordPress robots.txt returned HTTP 200 and declared `https://k-health365.com/sitemap_index.xml`.
- The Rank Math sitemap index returned HTTP 200.
- The Blogger address returned a redirect/error page because Blogger still claimed the historical custom domain `www.k-health365.com`.
- Blogger settings still contained the historical custom domain while domain redirect and Blogger HTTPS were disabled.
- Search-engine visibility and per-site search description were disabled before this audit.
- Custom robots.txt contained literal HTML break strings and incorrectly referenced the WordPress sitemap.
- The Blogger earnings page reported an active AdSense account connected to the blog.
- The AdSense Sites page reported `k-health365.com` as ready and approved.
- The WordPress property served the expected AdSense script and a valid root ads.txt entry.
- GSC contained properties for both `k-health365.com` and `k-health365.blogspot.com`.

## Changes completed in Blogger

- Enabled search-engine visibility.
- Enabled the Blogger search description and preserved its existing Korean description.
- Enabled custom robots.txt and replaced it with:

```text
User-agent: *
Disallow: /search
Allow: /
Sitemap: https://k-health365.blogspot.com/sitemap.xml
```

- Enabled custom ads.txt while preserving the already configured approved publisher entry.
- Preserved the Korean language, analytics measurement setting, AdSense connection, administrator, content, and feeds.

## Explicitly untouched

- DNS records
- WordPress content and settings
- AdSense account, publisher identity, and approved site record
- Existing Blogger posts and media
- Google Analytics measurement identity

## Pending guarded action

Removing `www.k-health365.com` from Blogger is intentionally recorded as pending until the final destructive confirmation is received in the interactive browser session. Immediately after removal, verify:

1. Blogger root HTTP/HTTPS response and self-canonical.
2. Blogger robots.txt and sitemap.xml.
3. Blogger ads.txt.
4. Blogger earnings connection.
5. AdSense site status for the approved WordPress domain.
6. GSC sitemap submission and a representative Blogger URL inspection.

## k-health365 Blogger authoring contract

- Gemini is the default Blogger writer.
- Produce an original Blogger treatment; never copy-paste the WordPress article.
- Use 8-10 relevant noun-form labels.
- Write a unique per-post search description.
- Use a short descriptive English permalink.
- Generate images only through the approved Replicate-to-FLUX route and attach useful ALT text.
- Upload as DRAFT only; automation must never publish.
