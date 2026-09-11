# Tistory publication policy — 2026-09-07

Each of the five existing blogs has two slots every day in Asia/Seoul:
07:00–10:59 and 13:00–16:59. Each site uses a shuffled minute schedule;
adjacent days never repeat the same minute. GitHub checks due slots every
five minutes. Actions queue delays and generation mean these are target
start times, not guaranteed public-post timestamps.

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

GitHub runs scheduling and article preparation with the PC off. Public
Tistory publication still requires the authenticated browser registrar to
be running. A stopped PC, expired login, or CAPTCHA blocks that final step;
do not report queueing or draft creation as public publication.
