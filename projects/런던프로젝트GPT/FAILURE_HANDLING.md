# 런던프로젝트GPT — Failure Handling

## Principle
Failure belongs to one destination/job, not the entire fleet.

## Retry
- max automatic retry: normally 1 for same deterministic failure.
- provider-wide 403/429/quota/billing => circuit-break that provider.
- repeated same failure => HOLD/dead-letter, not loop.

## HOLD classes
- HOLD_LOGIN
- HOLD_CAPTCHA
- HOLD_PERMISSION
- HOLD_QUOTA
- HOLD_BILLING
- HOLD_SOURCE
- HOLD_DUPLICATE
- HOLD_CREDENTIAL
- HOLD_MANUAL_REVIEW

## Evidence rule
Do not mark success because:
- process exited 0
- workflow ended
- queue file exists
- AI said done

Accept success only with destination-specific receipt.

## Browser-only rule
Never automate around CAPTCHA or human verification.
The job waits in HOLD and resumes after valid login.
