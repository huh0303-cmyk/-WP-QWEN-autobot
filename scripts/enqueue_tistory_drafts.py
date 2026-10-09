#!/usr/bin/env python3
"""Append Tistory artifacts to the queue. Emergency publishing pause is active."""
from __future__ import annotations

import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--drafts", default="artifacts/tistory-daily-drafts.json")
    parser.parse_args()
    raise SystemExit(
        "TISTORY_EMERGENCY_PAUSE: queueing is disabled after a low-quality/duplicate-content incident. "
        "Do not enqueue or publish until the five-account audit and duplicate review are complete."
    )


if __name__ == "__main__":
    raise SystemExit(main())
