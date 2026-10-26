#!/usr/bin/env python3
"""Retired server scheduler entry point.

YouTube execution has moved to the GitHub Actions workflow
`.github/workflows/youtube-github-worker.yml`. This old timer script is
intentionally non-operational so a stale server timer cannot publish content.
"""
raise SystemExit(
    "This legacy scheduler is retired. Use the GitHub Actions workflow "
    "youtube-github-worker.yml; publication remains blocked while YOUTUBE_COST_HOLD is enabled."
)
