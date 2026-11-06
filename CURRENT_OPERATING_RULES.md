# London Project — Current Operating Rules

**Effective:** 2026-11-06 (Asia/Seoul)  
**Supersedes:** older VPS / SSH / systemd / n8n-hosted-runtime plans and conflicting legacy social cadence notes.

## 1. Approved execution environment
- **Do not use a VPS** for London Project execution. No VPS deployment, SSH, Linux server, systemd timers/services, server-local queues, or server-hosted n8n.
- Interactive social account authentication and Instagram/Threads publishing work must run on the owner's authorized Windows PC, using Desktop Commander, PowerShell, and the existing local project files.
- GitHub is the source repository for code, machine-readable policy, operating instructions, change history, and rollback.
- `https://control.korea365.org/` is the public GitHub Pages control dashboard served from `main:/docs`. Updating `docs/index.html` updates the public dashboard after GitHub Pages deployment.
- The local PC must be powered on, connected, and authenticated for PC-bound tasks. Never describe this as 24/7 unattended server publishing.

## 2. Seoul Jisoo and Seoul Chris — current social policy
- Instagram and Threads use the same five designated accounts: `seoul_topik`, `english_pick`, `japanese_pick`, `seoul_jisoo`, `seoul_chris`.
- Seoul Jisoo: `@seoul_jisoo`, health and everyday-life stories plus broad political, social, economic, sports, entertainment, consumer, and trending topics. Health functional foods only when contextually relevant.
- Seoul Chris: `@seoul_chris`, K-beauty, skincare, cosmetics, beauty trends, and selected broader popular issues. Relevant cosmetics only when contextually appropriate.
- Seoul Jisoo: 3 distinct posts per day. Seoul Chris: 3 distinct posts per day.
- Randomize each account's publication times daily within 08:00–23:00 KST, with at least 120 minutes between that account's posts.
- Publish platform-native versions to Instagram and Threads; do not copy the same text verbatim.
- These are editorial targets. Keep `publish_connected=false` until exact identity, write permission, and a real post receipt are verified.

## 3. Editorial-first and affiliate rules
- Fun, useful, shareable content comes first. The post must be worth reading even if every product link is removed.
- Target 80–90% editorial value and no more than 10–20% contextual commerce.
- No product link is required on every post. Do not force unrelated products into a story.
- When directly relevant, put the product recommendation after the editorial content, at the end.
- Use only the owner's verified Coupang Partners tracking URLs and include clear affiliate disclosure. Never invent tracking URLs or claim a generic URL is an affiliate link.
- No fake personal experience, unsupported product performance, or undisclosed commercial relationship.

## 4. Daily topic research and factual standards
- Research current Korean search-interest phrases using Naver DataLab/search trend sources where available, plus Naver News and reliable primary/major news sources.
- Cover a balanced range of politics, society, economy, sports, entertainment, health, beauty, consumer topics, and practical lifestyle.
- Use high-interest keywords naturally; do not keyword-stuff.
- Do not claim a keyword has the highest search volume unless current, comparable measurement data supports that claim.
- Recheck dates, numbers, names, scores, schedules, and claims. For politics and public affairs, clearly separate confirmed facts, allegations/claims, and commentary.
- Write original summaries and commentary; do not copy article text.
- Check recent posts for duplicate topic, caption, or image.

## 5. Publishing and reporting gates
- Separate preparation, account identity verification, write authorization, scheduler activation, and actual publication.
- A configured schedule is not proof that a scheduler is running.
- A successful publication requires the platform's returned post/media ID or URL and a saved receipt.
- Do not enable public publishing or run a public test without the owner's authorization.
- Never place passwords, tokens, cookies, API secrets, or private affiliate credentials in GitHub, documentation, or chat.

## 6. Machine-readable source and detailed policy
- Primary policy: `config/sns_six_channel_policy.json`.
- Detailed editorial guide: `docs/SEOUL_JISOO_CHRIS_EDITORIAL_POLICY_2026-11-06.md`.
- Public dashboard: `docs/index.html`.
- Historical documents may be retained for audit and recovery, but any conflicting VPS-era or older cadence instruction is superseded by this file for current operations.


## 7. Five-brand Facebook / Instagram / Threads update (2026-11-07)
- Target brands: `seoul_topik`, `seoul_chris`, `seoul_jisoo`, `english_pick`, `japanese_pick`.
- The shared content strategy and proposed Facebook Page rename mapping are documented in `config/meta_five_brand_social_strategy.json` and `docs/META_FIVE_BRAND_CONTENT_WORKFLOW_2026-11-07.md`.
- All five brands may feature K-beauty, skincare, cosmetics, and health functional foods when relevant. Use politics, sports, society, economy, international news, entertainment, and timely topics for reach, with factual verification and clear separation of fact, allegation, and opinion.
- Keep editorial value primary (80–90%); contextual commerce should not exceed 20%. Never force unrelated products into news posts. Use only verified affiliate links with disclosure.
- Proposed Facebook Page renames follow the order in the owner's screenshot and are not applied. Confirm the row-by-row mapping before renaming.
- Instagram currently shows `english_pick1`, while the requested brand is `english_pick`. Do not alter the API identity, user ID, token, or secret key until the owner confirms the actual username change.
- The existing Meta preflight checks Instagram and Threads credential presence only. Facebook Page IDs, Page tokens, and write scopes must be verified separately. No actual publishing is enabled by this policy update.
