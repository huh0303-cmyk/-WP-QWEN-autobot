---
name: london-blog-ops
description: Operate or report on the Korea365 LondonProjectGPT blog network, including four-agent runs, daily publishing checks, site traffic, Google indexing, and AdSense revenue. Use for this project's operational questions; do not use for unrelated WordPress sites.
---

# London blog operations

Use this skill for requests about the Korea365 LondonProjectGPT console and its WordPress or Blogspot network. Find the project's repository and read its `AGENTS.md`, the current GitHub record, and the relevant canonical policy before changing code or production state. The authoritative scope is `docs/LONDON_PROJECT_GPT_BLOG_CONSOLE_LOCKED_SCOPE_2026-09-27.md`; operational results belong in `docs/LONDON_PROJECT_ACTIVITY_LEDGER.md` in the same session.

## Read the right evidence

- Identify the exact site or blog key and Korea date first. Verify the site mapping from the current registry; do not guess an ID from a similar domain.
- For visits, use a verified site visitor counter or connected GA4 property and state which one was used. Search Console clicks and impressions are search performance, not visitor counts.
- For Google indexed pages or a particular URL's indexing, use a connected Search Console property or URL Inspection. Public `site:` queries are only rough clues. If the property is not connected, report the metric as unavailable.
- For revenue, use the relevant AdSense account's dated report. Approval state or an earnings estimate is not actual revenue. Do not infer revenue from traffic.
- Prefer already connected tools. GSC Wizard may provide Search Console and linked GA4 after the user connects it; WordPress access may use a connected WPVibe site. The public OpenAI Docs MCP answers OpenAI documentation questions, not site metrics.

## Four-agent work

- Agent 1 chooses a keyword with source evidence; Agent 2 writes the site-specific article; Agent 3 prepares at most one suitable image; Agent 4 publishes and verifies a receipt.
- On an automatic run, inspect the selected site, category, mode, `run_id`, stage statuses, and receipt. On a manual run, agents 1–3 prepare the package; a person performs public publishing, then the console verifies the pasted URL. Do not represent `manual_required` as published.
- Before any retry or publication, check today's publication key, existing public URL or post ID, and the run's receipt. Do not send the same article twice merely because a previous response timed out or a stage was rerun.
- Name the failed blog key, failed stage, exact observed error, and next action. Preserve successful stages when a single stage can be repaired.

Keep credentials out of chat, commits, and reports. A skill does not authorize a new publication, account connection, or bulk action; follow the current user's request and project policy for those actions.
