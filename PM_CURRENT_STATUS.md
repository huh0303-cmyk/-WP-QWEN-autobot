# PM CURRENT STATUS

Updated: 2026-08-27 KST
Role: handoff/current-state companion to MASTER_MONETIZATION_STRATEGY_2026.md

## North Star
- Primary target: KRW 1,000,000/month sustainable combined revenue by year-end 2026.
- Business model: diversified passive-income portfolio combining AdSense/platform ads, shopping affiliate, travel affiliate, digital products and qualified leads while minimizing inventory, fulfillment and manual CS.
- Publishing volume is not the North Star; net revenue, qualified traffic, indexing, conversion and cost efficiency are.

## Frozen business policy
- WordPress long-form = GPT.
- Blogger/Blogspot long-form = Gemini.
- YouTube generated thumbnail = Replicate black-forest-labs/flux-schnell.
- Approved non-YouTube Replicate image pool only: flux-schnell, bytedance/sdxl-lightning-4step, jyoung105/sdxl-turbo.
- No silent fallback to legacy paid image providers.
- One-source-multi-use is allowed only with platform-native rewrites; duplicate mass posting is not.
- New paid API/SaaS/subscription requires explicit approval.
- Default automated publication mode should favor draft/private/review until verified.

## Current portfolio direction
- WordPress: ~26 active sites, AdSense-focused money/search assets. K-health365.com is the confirmed AdSense-approved site.
- Blogspot: matching/related traffic and keyword discovery layer; not verbatim duplicates of WP.
- Tistory: 5 properties.
- Naver Blog: 3 properties, conservative/account-safe automation.
- TikTok: 30k+ flagship social audience.
- Facebook: 3 pages, several thousand followers on relevant pages.
- Instagram: 3 accounts, several thousand followers on relevant accounts.
- Threads: early-stage discovery channel.
- TOPIK YouTube: ~5.7k subscribers, monetization just started; highest-priority proven education audience.
- Playlist YouTube pillars: K-pop / Romantic / Healing / Starbucks-work / Classical-Mozart.
- Knowledge YouTube pillars: NASA / Invention / Retro USA / Old Hollywood / History Today.
- Additional education/language and senior-health channel families remain growth assets.

## Revenue strategy now
1. Stabilize automation and eliminate API/cost leakage.
2. Complete observability in the Google Sheet '올뉴종합상황실'.
3. Improve indexing, search impressions and AdSense eligibility/performance.
4. Connect proven social/YouTube traffic into money sites and owned audience.
5. Test a small number of measurable affiliate programs: shopping + one travel affiliate family.
6. Build a reusable TOPIK digital-product funnel.
7. Scale only proven winners; reduce low-ROI assets.

## Immediate technical priorities for Work/Codex
Priority 1 — GitHub normalization
- Compare MASTER policy with all active code/config/workflows.
- Remove/disable stale API refs, duplicate workflows/schedulers, dead pipelines, retired channels, stale OAuth fallback, excessive retries, duplicate calls and silent-success bugs.
- Do not delete ambiguous business-critical code without reporting first.

Priority 2 — Measurement system
Use '올뉴종합상황실' as executive control center. Automate only verifiable metrics; mark unavailable sources as '연결 필요'. Target data:
- Per web property: published count, indexed count, non-indexed count, index rate, recent index delta, GSC impressions/clicks/CTR/position, visitor/user data, errors.
- AdSense: today/7d/month revenue and useful efficiency metrics when available.
- YouTube: subscribers, views, watch time, recent uploads, revenue, growth.
- Social: followers, views, engagement, posts, growth where official APIs permit.
- Cost: OpenAI, Gemini, Replicate and other actual API spend where retrievable.
- Executive KPI: revenue - AI/API/tool cost = net revenue/profit.

Priority 3 — Content engine normalization
- WP = GPT only.
- Blogger = Gemini only.
- YouTube thumbnail = FLUX Schnell only.
- SNS = one-source-multi-use with native title/hook/caption/CTA/hashtag/timing and duplicate prevention.
- Randomized/natural schedules; avoid synchronized machine-like publishing.

Priority 4 — End-to-end minimal tests
Test one representative unit only before scale:
1. 1 WordPress item
2. 1 Blogger item
3. 1 TOPIK item
4. 1 SNS set
5. 1 YouTube item
Validate generation -> image -> quality -> duplicate check -> draft/private/review -> logs -> Google Sheet record.

## PM Phase 2 backlog
- TOPIK cumulative vocabulary-test platform (see TOPIK_QUIZ_PLATFORM_PHASE2.md).
- Owned-audience funnel: free TOPIK resource -> opted-in contact/member -> digital product -> study/KStudy365 lead where appropriate.
- Affiliate attribution and revenue tracking by content/program.
- 30-day asset ROI classification: SCALE / WATCH / STOP.
- Intern operations model: human review, Vietnamese learner insight, comment/community analysis, landing-page and lead funnel support.

## Operating roles
- User: final business decision maker.
- ChatGPT PM: strategy, monetization architecture, priorities, quality bar, cost policy, interpretation of metrics, task specification.
- Work/Codex: implementation, code changes, integration, tests, commits, automation execution.
- Claude: independent QA/audit when used; should not reinvent business strategy.
- Gemini: designated production model for Blogger and other explicitly assigned low-cost tasks only.
- GitHub Actions: recurring production worker after validation.
- Google Sheet '올뉴종합상황실': control room and performance record.

## Reporting rule
Never say 'complete' without evidence. Completion reports should include:
- problem found
- change made
- remaining issue
- changed files
- test result
- Google Sheet result when applicable
- API/cost impact
- commit SHA
- next action
