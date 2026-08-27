# MASTER MONETIZATION STRATEGY 2026

Status: FROZEN / MASTER POLICY
Frozen: 2026-08-27 KST
Primary business target: reach KRW 1,000,000/month meaningful revenue by year-end 2026, with 2–3 months of consistent execution and optimization.

## 1. North Star
This repository is not primarily a content-volume project. It is a monetization system. Optimize for revenue, profit, qualified traffic, leads, and sustainable account/site growth — not raw publishing count.

Priority revenue layers:
1. AdSense / platform ad revenue.
2. Affiliate and commerce revenue (products, supplements where appropriate, shopping, hotels/travel, etc.).
3. Higher-value leads/services/subscriptions and other second/third-stage monetization.
4. Control AI/API/tool costs so net profit matters.

## 2. Web portfolio
### WordPress
- Approximately 26 operating WordPress sites; portfolio has been operated for about 10 months.
- AdSense is a primary near-term goal.
- Current confirmed AdSense approval success: K-health365.com.
- WordPress article generation policy: GPT.
- Do not silently fall back to Gemini for WordPress article writing.
- K-health365.com is also a candidate funnel for supplement-related monetization, but commerce must not undermine information quality or AdSense/site trust.

### Blogspot / Blogger
- Blogspot network starts as a traffic/search expansion layer alongside the WordPress portfolio.
- The intended architecture is corresponding/related Blogspot properties around the same business/topic portfolio, while content must NOT be copied verbatim from WordPress.
- Keyword/topic opportunities may overlap with WordPress, but Blogger must produce independently written content.
- Blogger article generation policy: Gemini.
- Blogger should support traffic discovery, keyword testing and CTA/funnel movement toward appropriate money assets.

### Tistory and Naver Blog
- Tistory: 5 accounts/properties in the portfolio.
- Naver Blog: 3 accounts/properties in the portfolio.
- Use one-source-multi-use planning, but adapt each output to the platform; do not mass-copy identical text.
- Cross-channel CTA/funnel design is required.
- Naver automation must be conservative and account-safe; avoid reckless bot-style mass publishing.

## 3. One-source multi-use funnel
One core topic/content idea may generate platform-specific derivatives for WP, Blogger, Tistory, Naver, YouTube, TikTok, Instagram, Facebook and Threads.

Rules:
- Same topic/keyword does not mean duplicate copy.
- Each platform gets native title, body/caption, length, hook, CTA and timing.
- Avoid obvious AI repetition, duplicate titles, duplicate media and simultaneous spam-like posting.
- CTA should move users toward the most appropriate monetizable destination rather than create circular low-value linking.

## 4. YouTube portfolio
### TOPIK
- Seoul TOPIK channel: approximately 5,700 subscribers at freeze date.
- Monetization has just begun; cumulative revenue mentioned at freeze date: about USD 8.
- Treat this as a priority proven audience asset.

### Language channels
- English/language learning and other-language channel family.
- Use education content to build audience and connect appropriate education/study funnels.

### Senior health channels
- Senior/health content planned across Korean, Japanese and English.
- Health content requires higher factual-quality and safety standards; monetization must not drive unsupported medical claims.

### Playlist channels — 5 pillars
1. K-pop
2. Romantic
3. Healing
4. Starbucks/work-focus style music
5. Classical/Mozart

### Knowledge channels — 5 pillars
1. NASA
2. Invention
3. Retro USA
4. Old Hollywood
5. History Today

YouTube thumbnail policy: FLUX Schnell via Replicate for generated thumbnails, with cost controls. Do not re-enable legacy paid image providers without explicit approval.

## 5. Social portfolio
- TikTok: 30,000+ follower flagship asset at freeze date.
- Facebook: 3 pages, roughly 2,000–3,000 followers range on relevant pages as reported.
- Instagram: 3 accounts, roughly 2,000–3,000+ range as reported.
- Threads: newly started; current scale not yet established.

Social strategy:
- Grow audience first without turning feeds into constant ads.
- Use high-performing organic/educational/quiz content for reach.
- Introduce monetization content selectively.
- Route qualified users into relevant web, education, shopping, travel or other monetization funnels.

## 6. AI/model routing — frozen policy
- WordPress long-form writing: GPT.
- Blogger/Blogspot writing: Gemini.
- YouTube generated thumbnails: Replicate black-forest-labs/flux-schnell.
- Approved Replicate image model pool for non-YouTube image needs:
  1. black-forest-labs/flux-schnell
  2. bytedance/sdxl-lightning-4step
  3. jyoung105/sdxl-turbo
- Shared Replicate credential: REPLICATE_API_TOKEN.
- Do not silently introduce or fall back to legacy paid image APIs/providers.
- Codex is an implementation/development agent; it must implement this master specification rather than invent business policy.

## 7. Cost policy
The business must not solve problems by continuously adding subscriptions and API spend.
- Reuse existing paid assets before buying new tools.
- Avoid duplicate AI calls.
- Limit retries.
- Limit image generation count.
- Prefer one master content object transformed into platform-specific derivatives.
- New paid APIs/SaaS/subscriptions require explicit cost/benefit review and user approval.
- Measure net revenue after AI/API/tool costs.

## 8. AdSense strategy
AdSense is a primary first-stage monetization target, but do not optimize for sheer AI article volume.
- Prioritize useful search-intent content, indexing, internal structure, trust, originality and user value.
- Use Search Console performance to identify topics that deserve expansion.
- Scale sites/topics that gain impressions/clicks; reduce waste on persistently non-performing areas.
- Avoid duplicate/near-duplicate multi-site publishing.

## 9. Revenue roadmap
### Stage 1 — now
- Stabilize existing automation.
- Stop API/cost leakage.
- Improve AdSense eligibility and search traffic.
- Grow proven social/YouTube assets consistently.

### Stage 2 — next 2–3 months
- Connect social traffic to appropriate money sites.
- Increase qualified search traffic.
- Build repeatable affiliate/shopping experiments.
- Track platform/site ROI.

### Stage 3 — year-end 2026 target
- Achieve meaningful combined monthly revenue with a target of KRW 1,000,000/month.
- Revenue may combine AdSense, YouTube/platform ads, affiliate/shopping, travel/hotel/product opportunities and higher-value leads/services.
- Concentrate resources on the best-performing 20% of assets instead of treating every property equally.

## 10. Implementation governance
This file is the master business-policy source for automation implementation.

Before changing automation, an agent/developer should check this file first.

Do NOT independently change:
- business goal,
- channel roles,
- GPT vs Gemini routing,
- approved image-provider policy,
- monetization priorities,
- account-safety rules,
- paid-service policy.

If code/config conflicts with this master policy, flag the conflict and repair it only when the intended implementation is clear. Material strategy changes require explicit user approval.

## 11. Management KPI
The executive dashboard should ultimately emphasize:
- Search impressions/clicks/CTR/position
- Indexed content and site health
- Social/video views and follower/subscriber growth
- AdSense/platform revenue
- Affiliate clicks/orders/revenue
- Leads/inquiries
- AI/API/tool cost
- Net revenue/profit

Publishing count is an operational metric, not the North Star.
