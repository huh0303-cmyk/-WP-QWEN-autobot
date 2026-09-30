# Blogger 33 free writer and schedule — 2026-10-01

The 2026-09-28 fallback work remained in open PR #130 and was not in `main`.
The production runner still selected only `gemini-2.5-flash-lite` with the
article-runtime key and retried the same 429 three times. The scheduler spread
33 sites only from 06:10 to 23:20 KST. These caused repeated quota failures
on 2026-09-28, 29 and 30.

The daily publisher now uses the separate server-held free-tier project
(`/etc/korea365/free-writer.json`) and tries three free-tier model endpoints:
`gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, and
`gemini-2.5-flash-lite`. A 429 switches to the next model and places the
failed model on a shared one-hour cooldown. A 5xx also switches models.
The publisher never invokes the paid OpenAI API. The server policy must say
`billing_verified: free_tier`; otherwise it stops. A historical date check
that disabled the fallback after seven days was removed. The project tier
must still be checked operationally when billing settings change.

The scheduler starts at 00:20 and finishes at 23:30 KST, leaving time before
the 23:50 audit. It continues to randomize order and jitter slots within
the full day. The publication marker and existing-post lookup remain the
duplicate guard. Free quotas and editorial gates may still prevent all 33
sites from publishing; three endpoints are not three independent providers.

Verification on 2026-10-01: the server-held free project returned HTTP 200
and `STOP` for short, non-publishing probes on all three model IDs. Local
fallback and schedule tests passed. No old failed publication was replayed.

Official references: https://ai.google.dev/gemini-api/docs/pricing and
https://ai.google.dev/gemini-api/docs/rate-limits.
