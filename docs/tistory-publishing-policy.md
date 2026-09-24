# Tistory publication policy — 2026-09-07

Each of the five existing blogs has exactly one randomized publication slot per KST day. The target is one public post per site per day. The dispatcher avoids exact-hour/repeating machine-like times. Generation and local-browser execution delays may shift the final public timestamp.

The dispatcher records a site/day/slot reservation on main before dispatch.
It never blindly redispatches an ambiguous request. The old daily cron is
removed. A scheduled request generates only its own site's article.

Automatic keywords require Korean Google Trends approximate search traffic
and mentions from at least two media outlets. Search interest and mention
frequency have equal weight. Site relevance remains required. No fixed
evergreen seed fallback is allowed when evidence is unavailable. Recent RSS
titles and queue titles/topics are excluded, and generated titles are checked
again before image generation. Google Trends numbers are approximate search
interest, not a census of all searches across all platforms.

Queue metadata retains tags and the representative image URL. The browser
registrar confirms tag entry and uploads a representative image into the
publication dialog; missing media or a missing decoded preview blocks save.
Signed R2 and Replicate image URLs are rehosted before entering the queue.
The supplied search description is inserted as a leading body summary and
verified after reopening. Tistory's native editor has no separate Blogger-style
search-description field; search engines may choose their own result snippet.

GitHub runs scheduling and article preparation with the PC off. Public Tistory publication is completed by the authenticated local browser registrar. As of 2026-09-25 the owner reported the Tistory login is already completed; do not ask for another login unless runtime verification detects an expired session or CAPTCHA. A stopped PC, expired session, or CAPTCHA blocks only the final browser step; never report queueing as public publication.
