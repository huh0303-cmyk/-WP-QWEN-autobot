#!/usr/bin/env python3
"""Select date-correct subjects for the knowledge-channel pipelines."""
from __future__ import annotations

import datetime as dt
import random
import sys

import requests

KST = dt.timezone(dt.timedelta(hours=9))


def history_today(now: dt.datetime) -> str:
    url = (
        "https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/events/"
        f"{now.month:02d}/{now.day:02d}"
    )
    response = requests.get(
        url,
        headers={"User-Agent": "Korea365KnowledgeChannels/1.0 (editorial research)"},
        timeout=30,
    )
    response.raise_for_status()
    events = response.json().get("events", [])
    candidates = []
    for event in events:
        text = " ".join(str(event.get("text", "")).split())
        year = event.get("year")
        pages = event.get("pages") or []
        if text and year and pages:
            candidates.append((len(pages), len(text), f"{year}: {text}"))
    if not candidates:
        return f"What happened on {now.strftime('%B %d')} in history"
    # Prefer events with strong supporting page coverage, then rotate among the
    # best candidates deterministically for that calendar date.
    candidates.sort(reverse=True)
    shortlist = [item[2] for item in candidates[: min(8, len(candidates))]]
    return random.Random(now.strftime("%Y-%m-%d-history-today")).choice(shortlist)


def main() -> None:
    channel = sys.argv[1] if len(sys.argv) > 1 else ""
    now = dt.datetime.now(KST)
    if channel == "history":
        print(history_today(now))
        return
    raise SystemExit(f"unsupported channel: {channel}")


if __name__ == "__main__":
    main()
