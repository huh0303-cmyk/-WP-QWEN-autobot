# YouTube registry release guard

## Purpose

The YouTube registry is loaded before any channel publishing work starts. A registry exception must block the release before media generation or an upload attempt.

## Required gate

Every change to `automation_hub/youtube_registry.py` runs the GitHub-only YouTube Worker Tests workflow on `main` and pull requests. The gate must:

1. compile the registry module;
2. load the configured ten playlist and knowledge channels; and
3. validate each channel's required worker workflow mapping.

## Incident rule

If a release fails before dependency installation because of a registry exception, fix the shared module once, add or confirm the matching regression coverage, run the gate, then retry only the affected channels. Record the cause and corrective commit in the Git history. Do not repeatedly rerun all channels before the shared validation succeeds.
