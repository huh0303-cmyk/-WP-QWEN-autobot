#!/usr/bin/env python3
"""Select date-correct subjects for the knowledge-channel pipelines."""
from __future__ import annotations

import datetime as dt
import random
import sys

import requests

KST = dt.timezone(dt.timedelta(hours=9))


def history_events(now: dt.datetime) -> list[dict]:
    url = f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/events/{now.month:02d}/{now.day:02d}"
    response = requests.get(url, headers={"User-Agent": "Korea365KnowledgeChannels/1.0"}, timeout=30)
    response.raise_for_status()
    candidates = []
    for event in response.json().get("events", []):
        if not event.get("text") or not isinstance(event.get("year"), int) or not event.get("pages"):
            continue
        sources = [p.get("content_urls", {}).get("desktop", {}).get("page", "") for p in event["pages"]]
        candidates.append({"year": event["year"], "text": event["text"], "sources": [s for s in sources if s], "coverage": len(event["pages"])})
    if not candidates:
        raise RuntimeError("No sourced events for today's date")
    # Coverage selects research leads; presentation is always reverse chronology.
    selected = sorted(candidates, key=lambda e: e['coverage'], reverse=True)[:8]
    return sorted(selected, key=lambda e: e['year'], reverse=True)


def history_today(now: dt.datetime) -> str:
    return f"{now.strftime('%B %d')} — Today in World History: " + " | ".join(f"{e['year']}: {e['text']}" for e in history_events(now))


def main() -> None:
    channel = sys.argv[1] if len(sys.argv) > 1 else ""
    now = dt.datetime.now(KST)
    if channel == "history":
        print(history_today(now))
        return
    raise SystemExit(f"unsupported channel: {channel}")


if __name__ == "__main__":
    main()
