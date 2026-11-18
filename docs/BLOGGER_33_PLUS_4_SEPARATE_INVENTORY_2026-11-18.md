# Blogger portfolio: existing 33 + separately discovered 4

Date: 2026-11-18

## Owner decision (explicit)
The four unregistered-but-owned Blogger sites are DISTINCT ADDITIONAL blogs. They are not replacements, corrections, or aliases for the four configured sites not matched by the current OAuth identity.

## Verified preflight #7 counts
- Configured master inventory: 33 — preserve unchanged.
- Verified within configured inventory: 29.
- Configured but not matched by current OAuth identity: 4 — preserve their entries and investigate account permissions separately.
- Owned but absent from configured master inventory: 4 — maintain as a separate additional inventory, not replacements.
- Combined inventory target: 37 distinct entries, pending URL-by-URL reconciliation.

## Safety and publishing policy
1. Never replace, remove, or rename any of the existing 33 solely because the OAuth preflight reports missing.
2. Do not automatically insert the four additional sites into the 33-site publishing schedule.
3. Preserve all four additional owned sites as separate records; extract their exact URLs and Blogger IDs from the preflight artifact before enabling publishing.
4. Publishing for the 29 verified existing sites may proceed only through the existing backup, editorial QA, idempotency, and publication receipt gates. Do not falsely claim that preflight equals publication.
5. Keep the four configured-but-unverified sites blocked from publishing until ownership is independently confirmed.
6. Do not expand the 33-site daily quota to 37 without a separate explicit decision.

Source: Blogger 33 read-only ownership preflight #7: `configured channels: 33; Verified: 29 Missing: 4 Unregistered owned: 4`.
