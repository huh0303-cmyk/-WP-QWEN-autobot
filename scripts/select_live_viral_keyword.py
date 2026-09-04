#!/usr/bin/env python3
"""Select one same-day, cross-media viral keyword for a WordPress site."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation_hub.blogger_topic_router import (
    fetch_profile_headlines,
    fetch_today_headlines,
    fetch_trending_terms,
    rank_topics,
)

PROFILES = ROOT / "config" / "content_engine_profiles.json"


def profile_for(url: str) -> dict:
    target = url.rstrip("/")
    payload = json.loads(PROFILES.read_text(encoding="utf-8"))
    for profile in payload.get("profiles", []):
        if str((profile.get("wordpress") or {}).get("url", "")).rstrip("/") == target:
            return profile
    raise SystemExit(f"No content profile for {target}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", required=True)
    parser.add_argument("--output", default="artifacts/live-viral-topic.json")
    args = parser.parse_args()

    profile = profile_for(args.site)
    headlines = fetch_today_headlines()
    headlines.extend(fetch_profile_headlines(profile))
    headlines = list({row["url"]: row for row in headlines}.values())
    topics = rank_topics(headlines, profile=profile, trend_terms=fetch_trending_terms())
    winner = topics[0] if topics else None
    result = {
        "site": args.site.rstrip("/"),
        "keyword": winner.keyword if winner else "",
        "score": winner.score if winner else 0,
        "mention_count": winner.mention_count if winner else 0,
        "outlet_count": winner.outlet_count if winner else 0,
        "surface_count": winner.surface_count if winner else 0,
        "viral_score": winner.viral_score if winner else 0,
        "evidence_urls": list(winner.evidence_urls) if winner else [],
        "fallback": winner is None,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as handle:
            handle.write(f"keyword={result['keyword']}\n")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
