# Blogger content policy

This policy applies to every current and future Blogger destination.

Default publishing language is English. Korean is allowed only for Blogger destinations mapped to `koreanews365.com` or `K-health365.com`.

Default address rule: use the WordPress domain stem as the Blogspot subdomain (`example.com` -> `example.blogspot.com`). The official Blogger host is `blogspot.com`, not `blogpost.com`. Preserve meaningful hyphens, remove only the top-level domain, and do not add `guide`, `blog`, numbers, or other suffixes unless the exact domain-stem address is unavailable and the user explicitly approves an alternative. Availability checks do not reserve an address; only successful blog creation does.

1. Publish and verify the matching WordPress article first.
2. Reuse the primary keyword, but rebuild the Blogger article instead of copying or sentence-level paraphrasing.
3. WordPress text is generated with GPT. Blogger text is generated only with Gemini.
4. Each Blogger destination inherits the persona and tone of its matching WordPress site.
5. Optimize the title, primary keyword, per-post search description (about 120 characters, 110-130 range), a short descriptive English permalink, and 10-14 relevant single-topic Blogger labels.
6. Use 0-2 genuinely relevant images generated through the approved Replicate routing policy. Use zero when no generated candidate is sufficiently relevant or safe. Never insert a generic filler image merely to occupy a slot.
7. Visa, insurance, and medical-tourism posts require official sources, an as-of date, a change-warning, and an appropriate informational disclaimer.
8. Change structure, examples, headings, and framing to prevent duplicate content.
9. Do not upload the generated profile logo. The profile photo remains user-managed.
10. Do not schedule creation or publishing at repetitive round-clock times. Distribute runs across different, non-round times within approved operating windows.
11. Write for a real reader's task, not for search-engine manipulation. Every post must add original synthesis, a complete answer, and practical next steps beyond the WordPress source.
12. Use a descriptive, non-clickbait title; a direct-answer introduction; logically ordered H2/H3 sections; and checklists, comparisons, tables, or FAQs only when they materially help.
13. Make authorship and scope clear. Never invent credentials, first-hand experience, statistics, quotations, case studies, or sources.
14. Link naturally to the verified source WordPress article and, when available in the source, one or more genuinely related WordPress guides. Do not create keyword-stuffed or repetitive anchor text.
15. For factual and time-sensitive claims, link to relevant official government, regulator, university, hospital, insurer, or other primary sources already verified in the WordPress source. Never invent or guess a URL.
16. Reject thin, generic, mass-produced-looking output, repeated templates, filler introductions, keyword stuffing, fake freshness, excessive FAQs, and unsupported claims before publication.
17. Before applying for AdSense, every Blogger site must have useful published content plus clear About, Contact, Privacy Policy, and editorial/disclaimer pages appropriate to its topic.
18. AdSense approval is never guaranteed. Optimize for Google Publisher Policies, people-first usefulness, originality, trust, and a good reader experience rather than writing "for approval" or manipulating rankings.
19. Each connected Blogger destination publishes at most one post per KST calendar day. Its daily target time is a site-specific baseline plus deterministic random jitter of up to four hours in either direction, with round-clock times avoided.
20. A scheduled Blogger run is skipped when no new, publicly published WordPress source article is available. It must never fabricate a source or republish an already-used WordPress URL.
21. The scheduler runs every 20 minutes, dispatches at most one site per run, and keeps at least 20 minutes between network dispatches. New Blogger sites enter the schedule only after their registry record is connected and explicitly set to review-mode daily drafting.
22. Before publication, Blogger uses its own 100-point pre-publication quality/SEO rubric. This internal score is not a score issued by Google and does not guarantee AdSense approval. A post must score at least 75/100.
23. Gemini receives at most two full writing attempts. The second attempt receives the first attempt's failed checks. If both attempts score below 75, the job fails closed and nothing is queued or published.
24. Blogger quality scoring never awards or deducts points merely for having an image. A generated image is attached only when it has clear topic overlap and passes the rights and safety checks; otherwise keep the article at zero images.
25. All Blogger articles are uploaded as private drafts. Automation must never press the final publish action. After draft creation, record the authenticated Blogger edit URL and email it to the owner for human reading, editing, and manual publication.
26. The platform worker forcibly converts every Blogger queue item to draft mode, including an older row that accidentally contains a publish flag. Final Blogger publication is manual-only.
27. All 27 Blogger image pipelines follow `config/network_image_generation_policy.json` through Replicate: FLUX.1 Schnell first, SDXL-Lightning 4-step second, and SDXL Turbo third. Blogger still permits zero images and remains human-review-only.
28. `k-health365.com` WordPress and `k-health365.blogspot.com` Blogger are separate editorial properties. WordPress is the source-side site, but Blogger must receive a newly written article with a distinct search intent, outline, examples, wording, and generated image rather than copied or lightly paraphrased WordPress text.
29. `k-health365.blogspot.com` remains a Korean-language Blogger property. Its custom-domain field must not claim `www.k-health365.com`, which belongs to the WordPress property. DNS and the approved AdSense account/site records are outside Blogger automation scope and must never be changed by the publishing worker.
    - 2026-08-28 incident: this rule was violated in practice — the Blogger settings for `K- health 365 연구소` (blog ID `8294304371132383961`) had `www.k-health365.com` set as its custom domain, which broke `k-health365.blogspot.com` (returned HTTP 404) while leaving `k-health365.com`/`www.k-health365.com` unaffected since DNS never actually pointed there. Fixed by removing the stale custom domain in Blogger settings (not DNS, not WordPress). `k-health365.blogspot.com` now returns HTTP 200, HTTPS redirect enabled, robots.txt/sitemap.xml verified live, sitemap submitted to Search Console. AdSense showed "블로그 승인되지 않음" at fix time — likely a side effect of the domain being down; needs a fresh check after Google re-crawls. This blog is still not registered in `config/automation_hub_sites.json` (7th Blogger site, not yet wired into `blogger_daily_scheduler.py`) — a separate decision, not resolved here.
30. Every Blogger image that is used must include a useful topic-specific ALT description. Image generation follows the approved Replicate-to-FLUX route; irrelevant or unsafe images are rejected.
    - 2026-08-28 incident: during the 27-channel shell rollout, an interrupted/frozen "새 블로그" creation dialog silently produced a duplicate `한국생활지원정보` shell (id `777260289366042949`, address `life-support-korea365.blogspot.com`) alongside the original (id `2531035487222435079`, address `korea-life-support365.blogspot.com`). The duplicate had zero posts. Per user instruction, it was soft-deleted via Blogger's own "내 블로그 삭제" (90-day recoverable trash), not permanently destroyed, and never recorded in the registry. Lesson: after any "새 블로그" dialog that showed unresponsive/frozen input, re-verify the blog switcher's full list (including "삭제된 블로그") before creating the next shell, rather than assuming the stuck attempt produced nothing.

## Publishing order for the first six Blogger sites

1. k-trip365
2. jobkorea365
3. kstudy365
4. K-visa365
5. koreainsurance365
6. koreamedicaltour365

## Shared public author identity

- Display name: `Korea 365 Editorial Desk`
- Bio: `Korea 365 Editorial Desk publishes practical, source-led guides to jobs, travel, visas, insurance, medical tourism, and study in Korea. We prioritize current official sources, clear procedures, and plain-language explanations. Time-sensitive requirements should always be confirmed with the relevant authority.`
