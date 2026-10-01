#!/usr/bin/env python3
"""Set existing language-channel videos private after exact ownership checks."""
from __future__ import annotations

import argparse
import json

from publish_survival_adjective_shorts import authenticated_channel_id, make_old_video_private, youtube_service
from survival_adjective_short import channel_map


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos", required=True, help="Comma-separated language:videoId map")
    args = parser.parse_args()
    registry = channel_map()
    results = []
    for item in args.videos.split(","):
        code, separator, video_id = item.strip().partition(":")
        if not separator or code not in registry or not video_id:
            raise RuntimeError(f"Invalid video mapping: {item}")
        service = youtube_service(code)
        expected_channel = registry[code]["channel_id"]
        mine = authenticated_channel_id(service)
        if mine != expected_channel:
            raise RuntimeError(f"Authenticated channel mismatch for {code}: expected {expected_channel}, got {mine}")
        result = make_old_video_private(service, video_id, expected_channel)
        results.append({"language_code": code, **result})
    print(json.dumps({"status": "verified", "count": len(results), "items": results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
