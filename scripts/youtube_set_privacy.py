#!/usr/bin/env python3
"""Retired legacy privacy mutator.

Infrastructure migration must never mass-change existing video privacy. This
script intentionally performs no API calls. Use an owner-reviewed, exact-video
GitHub workflow only if a future privacy change is explicitly authorized.
"""
raise SystemExit(
    "Legacy privacy mutation is disabled. No video was changed. "
    "Do not use this server-era entry point."
)
