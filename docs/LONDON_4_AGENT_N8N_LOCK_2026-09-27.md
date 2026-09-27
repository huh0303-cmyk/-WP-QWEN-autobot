# LONDON 4-AGENT n8n LOCK — 2026-09-27

## Status
This document is the authoritative content-publishing architecture for London Project WordPress 25 + Blogspot 33.
Do not create a second competing article pipeline or duplicate scheduler. Extend or repair this pipeline in place.

## Runtime
- Source of truth: GitHub repository `huh0303-cmyk/-WP-QWEN-autobot`
- 24/7 runtime: existing Hostinger VPS
- Orchestrator: self-hosted n8n Community Edition
- Primary n8n workflow:
  - name: `London Content - 4 Agent Pipeline`
  - id: `london-content-four-agent-v1`
  - webhook: `/webhook/london-content-four-agent`
- Persistent run state: `/opt/korea365/data/london-pipeline/<run_id>.json`
- PC is NOT required for normal publishing operation.

## Visible n8n flow
```
START - Site Request
        |
        v
RUN CONTEXT
        |
        v
AGENT 1 - Topic Research
        |
        v
AGENT 2 - Writer
        |
        v
AGENT 3 - Image
        |
        v
AGENT 4 - Publisher + Verify
        |
        v
RECEIPT - Verified Result
```

A failed agent must stop that execution at its own n8n node. Do not silently continue across a failed research, writing or publishing gate. Image is the only optional stage: image generation failure may continue as no-image when site policy allows.

## AGENT 1 — Topic Research
Goal: select one current, useful, non-duplicate search-intent topic.

Required evidence surfaces:
1. Google: direct Google Trends KR RSS + Google News RSS.
2. Naver: direct Naver News/Search observation.
3. Media: independent current media coverage.
4. GSC: site-specific query impressions when available.

Metric integrity:
- Never invent Google or Naver absolute search volume.
- GSC impressions are not market search volume.
- Google Trends approximate/relative traffic is not monthly search volume.
- Media mention counts and search-result samples are not search volume.
- If a verified absolute-volume source is unavailable, record `VOLUME: unavailable`.

Normal route:
`direct Google/Naver/media collection -> local Ollama Qwen -> duplicate check`

Cloud search is a bounded fallback only when the zero-cost direct route is unavailable.

## AGENT 2 — Writer
Goal: produce an original article matching the selected site's persona, language, tone and target length.

Rules:
- WordPress and paired Blogspot content must be independently written; no verbatim cross-posting.
- Mechanical quality gate: minimum score 70 plus critical length/meta/language gates.
- Site-specific persona and editorial funnel come from `config/content_engine_profiles.json`.
- Medical/visa/finance/legal safety rules remain fail-closed where applicable.

Provider resilience:
- Existing cloud writer may use Gemini first.
- Bounded GPT-5-mini fallback is allowed only behind the existing budget guard and only when API credits exist.
- If cloud providers are exhausted, local Ollama `qwen2.5:3b` is the zero-cost fallback.
- One provider's quota exhaustion must not stop the fleet permanently.

## AGENT 3 — Image
Goal: attach at most one relevant image.

Rules:
- 0–1 image per article.
- Never publish a temporary Blogger image URL; stabilize it or discard it.
- ALT text must describe the actual scene; never keyword-stuff.
- Image failure can continue without an image when the site policy allows.
- Canary runs beginning with `canary-` intentionally skip paid image generation while still exercising the Agent 3 node.
- Normal production keeps the image stage enabled.

## AGENT 4 — Publisher + Verify
WordPress:
- use WordPress REST API
- focus keyword/meta preserved
- return remote post ID + URL
- draft is the safe canary default
- public mode must pass public URL verification

Blogger:
- use Blogger v3 API
- stable idempotency marker prevents duplicate drafts/posts
- return remote post ID + editor/public URL
- public mode must verify live URL

No execution may be called successful without a receipt containing at least:
- `site_id`
- `run_id`
- `post_id`
- `url`
- status
- verified timestamp

## Failure diagnosis
The first red n8n node is the owning failure domain:
- Agent 1 red: research source / research synthesizer / duplicate gate
- Agent 2 red: writer provider / quality gate / language or length
- Agent 3 red: image generator/hosting; normally converts to no-image rather than fleet failure
- Agent 4 red: platform auth/API/WAF/REST/verification

Every run uses a stable `run_id`. Inspect the corresponding state JSON plus the n8n execution details before changing code.

## Cost / resilience rules
- n8n Community Edition: self-hosted on existing VPS; no n8n Cloud subscription required for production.
- Local Ollama/Qwen is the zero-cost fallback and runs on the VPS.
- Cloud AI subscription plans do not automatically cover API usage; API costs/quotas are independent.
- Existing budget guard remains mandatory before paid API calls.
- Never buy a new SaaS or increase paid API spend without explicit owner approval.

## Migration rule
Legacy WP/Blogger schedulers are not destructively removed until this 4-Agent pipeline passes end-to-end WordPress and Blogger canaries. After verified canaries, migrate one scheduler at a time and retain rollback.

## Verified evidence recorded during build
- n8n workflow import + publish + container restart succeeded on VPS.
- gateway health reported `pipeline:true`.
- Agent 1 previously produced a real researched topic with Google/Naver/media evidence:
  `Korea Autumn Foliage Itinerary 2026`.
- Direct VPS probes returned HTTP 200 for Google Trends RSS, Google News RSS and Naver News Search.
- VPS: 2 CPU, 7.7 GiB RAM, about 66 GiB free disk at build time.
- Ollama `qwen2.5:3b` was pulled to the VPS and returned `LOCAL_OK` in a real generation test.
- OpenAI API was observed with zero remaining credits and Gemini API with the free-tier daily request limit exhausted; this is why the local fallback is mandatory rather than optional.

## Ownership
GPT/PM coordinates architecture, deployment and final validation.
Claude/Codex/Gemini may assist with bounded QA/research/code tasks, but they must not create parallel replacement pipelines.
