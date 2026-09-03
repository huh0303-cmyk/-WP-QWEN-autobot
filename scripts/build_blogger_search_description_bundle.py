#!/usr/bin/env python3
"""Build the UI-save bundle; Blogger v3 does not expose searchDescription."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from automation_hub.blogger_search_description import build_search_description, validate_search_description  # noqa: E402


def build_bundle(results_path: Path) -> dict:
    profiles = json.loads((ROOT / "config/content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    result_doc = json.loads(results_path.read_text(encoding="utf-8"))
    results = result_doc.get("results", result_doc)
    by_key = {row["site"]: row for row in results}
    records = []
    for profile in profiles:
        key = profile["site_key"]
        result = by_key.get(key)
        if not result or not result.get("post_id"):
            raise RuntimeError(f"publication result missing post ID for {key}")
        blog = profile["blogspot"]
        description = build_search_description(
            title=f"{key.replace('_', ' ').title()} — {result.get('title') or profile['wordpress']['theme']}",
            topic=f"{profile['wordpress']['theme']} · {key.replace('_', ' ')}", language=profile["language"],
        )
        records.append({
            "site_key": key,
            "blog_id": str(blog["destination_id"]),
            "post_id": str(result["post_id"]),
            "edit_url": f"https://www.blogger.com/blog/post/edit/{blog['destination_id']}/{result['post_id']}",
            "public_url": result.get("url", ""),
            "title": result.get("title") or profile["wordpress"]["theme"],
            "language": profile["language"],
            "topic": profile["wordpress"]["theme"],
            "search_description": validate_search_description(description),
            "description_chars": len(description),
            "persistence": "UI_SAVE_REQUIRED_NOT_EXPOSED_BY_BLOGGER_V3",
        })
    if len(records) != 33 or len({r["edit_url"] for r in records}) != 33 or len({r["search_description"] for r in records}) != 33:
        raise RuntimeError("bundle scope/uniqueness guard failed")
    return {"count": 33, "api_persistence_claimed": False, "records": records}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--output", default="artifacts/blogger-33-search-descriptions-ui.json")
    args = parser.parse_args()
    bundle = build_bundle(Path(args.results))
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "count": bundle["count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
