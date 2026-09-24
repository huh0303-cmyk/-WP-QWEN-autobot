# GitHub Operation Record Policy

Status: CANONICAL — 2026-09-25 KST  
Owner: Chairman / user  
Scope: London Project and all connected Korea365 operations

## Non-negotiable rule

Every material result must be written to GitHub during the same work session.
Do not leave decisions, findings, fixes, IDs, role changes, failures, test results,
or unresolved states only in chat.

## What must be recorded immediately

- user decisions and scope changes
- discovered account/channel/site IDs and ownership mappings
- configuration changes
- code changes
- role/architecture changes
- test and verification results
- failures, blocks, missing credentials and missing IDs
- external publication/upload receipts
- rollback or recovery information
- unresolved items and exact next action

## Recording standard

1. Update the canonical config or documentation file that owns the fact.
2. Add or update an activity-ledger entry for operational execution.
3. Commit each coherent change with a descriptive message.
4. Fetch back or otherwise verify the saved GitHub state before reporting completion.
5. Never replace a verified ID with a guessed value.
6. Never rely on chat memory as the source of truth.
7. On the next session, resume from GitHub records before asking the Chairman to repeat prior decisions.
8. Secrets, passwords, tokens and private credentials must never be committed.

## Continuity rule

If work is interrupted, the next agent must read the latest GitHub commits,
canonical config files, this policy, and the London Project activity ledger,
then continue from that state. Re-asking the Chairman for facts already recorded
in GitHub is a process failure.

## Current enforcement note

This policy was added after the Chairman explicitly instructed that every result,
including intermediate confirmations and corrections, be updated and permanently
recorded in GitHub so the same instruction does not need to be repeated.
