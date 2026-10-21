# London Project — Seoul Current-Affairs Social Workflow Review
**Date:** 2026-10-21  
**Status:** Design and integration checklist recorded; implementation, deployment, channel creation, and social publishing are NOT yet performed.

## 1. Goal and scope
Create a Korean-language current-affairs workflow for the planned **서울저널 / SEOUL JOURNAL** brand, separate from and preserving the existing Rosie's Picks channel. Initial social destinations: Threads, Instagram, and Facebook. The user will create the YouTube channel separately.

Coverage: Korean politics and parliamentary audits, economy and public support programs, society, international affairs, war/defense, sports (including same-day KBO playoff results), culture, and other topics whose public search interest is rising.

## 2. Editorial and visual standard
- Create original Korean explainers, not copied article text or recycled broadcaster footage.
- Strong but accurate headline; opening hook in the first sentence; facts, attributed claims, and analysis clearly separated.
- Record original source URLs; prefer government/assembly releases, official sports records, primary documents, and multiple reliable reports for contested events.
- Political content must not be scored or selected to favor/attack a person or party. Rank topics by public interest, recency, practical relevance, and source confidence.
- Never invent quotes, poll numbers, scores, home runs, casualty counts, policy eligibility, or deadlines.
- Visual identity: deep navy, white, restrained red/yellow accents; SEOUL JOURNAL · 서울저널 masthead; one relevant portrait/image per card rather than a collage of unrelated faces; verify identities and image rights.
- Each network gets its own final export and caption: Instagram 4:5 or 9:16 as appropriate, Facebook feed/Reels format as appropriate, Threads native text/image format. Do not assume one asset/caption works identically on all three.

## 3. Trend and story discovery
1. Poll public Google Trends Korea pages and official RSS/news sources on a scheduled interval.
2. Use Naver DataLab web UI/publicly available information as a secondary trend signal. Do not assume a new Naver API key is available or free.
3. For sports, confirm facts against official KBO schedules and game records.
4. For policy/support payments, verify eligibility, deadlines, amounts, and official application URLs against the responsible public authority.
5. Deduplicate topics by normalized event/entity/time window; store source URLs, timestamps, and topic state.
6. Rank candidates with a transparent heuristic: search-interest change (30), recency (20), likely sustained interest (15), practical relevance (15), source confidence (20). This is a prioritization heuristic, not a prediction of views.
7. If a story is unverified or primary-source confidence is below the configured threshold, route it to review rather than publication.

## 4. End-to-end pipeline
1. Trend and source collectors.
2. Deduplication and topic scoring.
3. Source verification and fact ledger.
4. Korean script and headline generation.
5. Visual asset selection and rights check.
6. Voice generation.
7. Per-platform rendering for Threads, Instagram, and Facebook.
8. Audio, subtitle, source, and visual QA.
9. Approval queue.
10. Scheduled/published state via authorized connector/API.
11. Metrics collection and next-day review.

Each stage must be independently retryable and persist state. A failed voice/render/post stage should not restart the whole pipeline. A failed QA, unverified claim, missing source record, or uncertain image right must block automatic publishing. Keep a post idempotency key to prevent duplicates. Log every retry and platform response.

## 5. Voice: ElevenLabs primary, Vrew fallback path
### ElevenLabs primary
- Use the official Text-to-Speech API from the server-side worker.
- Required setup: user creates an API key in the ElevenLabs dashboard, selects only required API scopes/permissions if available, configures usage/credit limits where available, and supplies the key directly to a secure secret store or environment variable named ELEVENLABS_API_KEY.
- Never ask the user to paste the secret into chat, source files, issue comments, or public GitHub. Never commit .env or API credentials. Keep .env.example with placeholder names only.
- Configure at least two Korean voice profiles (one masculine-presenting, one feminine-presenting) and rotate them across videos; optional within-video dialogue only when it improves clarity.
- Keep background music disabled by default. Add no music/sound effects unless separately approved.
- Record voice id, model id, request id, character count, estimated credits, generated file hash, and status; never record the API key.
- Handle quota/rate-limit/network errors with bounded retries and backoff. Prevent duplicate charges by persisting job state before retrying. Route exhausted quota or repeated failures to fallback/manual review.
- Verify pronunciation for names, institutions, numerals, scores, dates, and acronyms using a glossary and sample playback.

### Vrew fallback
- Official public Vrew materials describe Korean male/female AI voices, noise removal, subtitles, and export of audio/video.
- No publicly documented, generally available Vrew API for server-side automated TTS was verified in this review. A paid desktop subscription does not itself prove API access.
- Until Vrew confirms a supported API, treat it as a manual fallback: the job queue creates a ready-to-use script/voice assignment; an operator generates/exports audio in Vrew and uploads it to the job's fallback input; the pipeline then runs the same QA. Do not use brittle UI automation or claim seamless API fallback.
- If a supported Vrew API is later confirmed, add it behind the same provider interface as ElevenLabs.

### Audio QA gates
- Check duration, silence/clipping, peak level, unexpected hum/continuous mechanical noise, and abrupt loudness differences between speakers.
- Use FFmpeg filters/analysis as diagnostics, not as a guarantee that all noise is removed.
- Optionally run speech-to-text on rendered audio and compare against the script for missing/incorrect phrases.
- On failure: one controlled regeneration with revised voice settings; then Vrew/manual fallback; if still failing, mark REVIEW_REQUIRED and do not publish.

## 6. Per-platform publishing and Metricool
- The current Metricool brand observed during this review is 서울국제대학 SIS - TOPIK Center; its connected YouTube is Japanese Survival, with Facebook page 서울국제대학 SIS - TOPIK Center, Instagram sis_topik1, Threads englishsurvival1, and TikTok sis_topik. This is not a confirmed 서울저널 account set.
- Create/use a separate Metricool brand for 서울저널 after the user creates or identifies the intended Facebook Page, Instagram professional account, and Threads profile. Verify each connected identity before scheduling.
- Metricool can be evaluated for calendar/scheduling/analytics; do not assume every format or feature is available on every plan/account.
- Direct Meta APIs may be considered only after confirming app permissions, professional-account requirements, Page roles, review/access requirements, and supported Threads/Instagram/Facebook publishing endpoints. Do not claim these are configured.
- Never publish or schedule content until the user approves the account identity, test asset, caption, and schedule.

## 7. Proposed operating cadence
- Poll trends and sources every 30–60 minutes, subject to source rate limits and terms.
- Candidate stories remain in a queue; daily publishing target is 1–2 high-quality posts per network, not an obligation to post when no story qualifies.
- Publish a platform-adapted image/card or short clip; keep headline and factual context readable on mobile.
- Use an approval queue initially. Automatic posting can be enabled only after test posts, credentials, account mappings, rights checks, and audio QA are verified.
- Collect post IDs, timestamps (Asia/Seoul), source URLs, topic category, asset hash, voice provider, QA outcome, impressions/reach/views/engagement when available, and errors.
- Review after 1, 7, and 21 days; compare retention and useful engagement rather than views alone.

## 8. Free-first / paid-by-choice constraints
- Prefer existing VPS, Python, FFmpeg, SQLite/JSON, public RSS/official sources, and the user's existing subscriptions.
- ElevenLabs API consumption is potentially metered separately from subscription entitlements; verify current dashboard quotas and costs before running batches. Start with one short test and usage limits.
- Vrew is already subscribed to by the user, but API availability is unconfirmed. Manual export remains the fallback until confirmed.
- Do not add paid APIs, paid SaaS, or paid stock imagery without explicit approval.
- Publicly accessible imagery is not automatically free for commercial reuse; record source and license or use original/appropriately licensed assets.

## 9. Required secrets and user inputs
- ELEVENLABS_API_KEY: add only via secure environment/secret manager, never chat or GitHub source.
- Confirm the actual Vrew product (assumed to mean Vrew/브루) and ask Vrew support whether an official server-side API is available for the user's plan.
- Confirm the new 서울저널 Facebook Page, Instagram professional account, and Threads profile handles/URLs.
- Confirm which Metricool brand should be used or create a separate brand for the new project.
- User will create the new YouTube channel. Do not repurpose Rosie's Picks.

## 10. Today's status checklist — 2026-10-21
- [x] Workflow requirements and safety gates documented.
- [x] Official ElevenLabs API authentication documentation reviewed.
- [x] Official Vrew public product/voice/export materials reviewed.
- [ ] Existing local production code paths fully inspected and modified.
- [ ] ElevenLabs key securely configured and test request run.
- [ ] Vrew API support confirmed; until then fallback is manual.
- [ ] New social accounts/Metricool brand verified.
- [ ] First sample card/video reviewed and approved.
- [ ] Publishing test performed with explicit user approval.
- [ ] Production deployment completed and verified.

## References
- ElevenLabs API authentication: https://elevenlabs.io/docs/ko/api-reference/authentication
- ElevenLabs quickstart: https://elevenlabs.io/docs/eleven-api/quickstart/
- ElevenLabs API keys: https://elevenlabs.io/docs/overview/administration/workspaces/api-keys
- Vrew Korean TTS: https://vrew.ai/ko/feature/text-to-speech/
- Vrew pricing/credits: https://vrew.ai/ko/payment/pricepolicy
- Vrew terms: https://vrew.ai/ko/terms-of-service/
- Google Trends Korea: https://trends.google.co.kr/trending?geo=KR
- Naver DataLab: https://datalab.naver.com/
- KBO official: https://www.koreabaseball.com/