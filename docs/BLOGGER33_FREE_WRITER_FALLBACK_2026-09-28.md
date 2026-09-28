# Blogger 33 free writer fallback — 2026-09-28

## Decision

The daily Blogger publisher uses only the Gemini project recorded as
`billing_verified: free_tier` in `/etc/korea365/free-writer.json`. It tries
`gemini-2.5-flash-lite`, then `gemini-2.5-flash` when the first model returns
HTTP 429 or a transient 5xx. A 429 puts that model on a one-hour cooldown
shared by the 33 per-site processes. When both quotas are unavailable, the
site fails clearly with `free_quota_wait_no_paid_fallback`; the runner does
not repeat that same quota-held attempt.

The verification date must be no more than seven days old. Renew the
verification before its expiry; otherwise publication stops with
`free_tier_recheck_due`. The existing `OPENAI_API_KEY` is not used: OpenAI's
GPT text-generation API models do not support the API Free tier, and a
ChatGPT Free account does not supply a free automation API. This retains the
user's free-only cost constraint. Free Gemini quotas also cannot guarantee
33 articles each day.

The publication marker `blogger33-public:<run_key>:<site>` remains in each
article and is checked before creating another post. No backfill or manual
publication is part of this change.

## Verification and follow-up

- Six local unit tests passed for model fallback, cooldown, free-tier guard,
  and existing publisher scope.
- Confirm the production timer remains enabled/active after deployment.
- Audit the next day's 33 transient services and published markers. If both
  free model quotas run out, hold the remaining sites and report their keys.
- Reverify `/etc/korea365/free-writer.json` billing status by 2026-09-30 KST.

Official API model availability: https://developers.openai.com/api/docs/models/gpt-6-luna

