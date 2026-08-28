#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_source(path: str) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    text = p.read_text(encoding="utf-8", errors="replace")
    try:
        raw = json.loads(text)
        return raw if isinstance(raw, dict) else {"raw": raw}
    except Exception:
        source: dict[str, Any] = {"raw_log": text[-12000:]}
        patterns = [
            (r"studio\.youtube\.com/video/([A-Za-z0-9_-]{6,})/edit", "video_id", "https://studio.youtube.com/video/{}/edit"),
            (r"youtube\.com/watch\?v=([A-Za-z0-9_-]{6,})", "video_id", "https://youtube.com/watch?v={}"),
        ]
        for pattern, id_key, url_template in patterns:
            match = re.search(pattern, text)
            if match:
                source[id_key] = match.group(1)
                source["video_url"] = url_template.format(match.group(1))
                break
        error_lines = [line.strip() for line in text.splitlines() if any(token in line.lower() for token in ("error", "failed", "❌", "unauthorized", "forbidden", "oauth", "scope"))]
        if error_lines:
            source["error_message"] = error_lines[-1][:2000]
        return source


def _first(source: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = source.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize a platform worker result into one room-result contract")
    parser.add_argument("--room-id", default=os.getenv("ROOM_ID", ""))
    parser.add_argument("--platform", required=True)
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--source", default="")
    parser.add_argument("--outcome", choices=["success", "failure"], required=True)
    parser.add_argument("--output", default="artifacts/automation-room-result.json")
    args = parser.parse_args()

    source = _load_source(args.source)
    artifact_id = _first(source, "artifact_id", "post_id", "remote_id", "video_id", "id")
    artifact_url = _first(source, "artifact_url", "public_url", "url", "video_url", "studio_url", "edit_url")
    failure_reason = _first(source, "failure_reason", "error_message", "message", "error")

    status = "SUCCESS" if args.outcome == "success" else "FAILED"
    lowered = failure_reason.lower()
    if args.outcome == "failure" and any(token in lowered for token in ("oauth", "unauthorized", "forbidden", "credential", "token", "scope")):
        status = "AUTH_REQUIRED"
    if args.outcome == "success" and not artifact_id:
        status = "AWAITING_APPROVAL" if args.platform == "tistory" else "SUCCESS"

    result = {
        "timestamp": _now(),
        "room_id": args.room_id,
        "platform": args.platform,
        "workflow": args.workflow,
        "run_id": os.getenv("GITHUB_RUN_ID", ""),
        "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT", ""),
        "status": status,
        "artifact_id": artifact_id,
        "artifact_url": artifact_url,
        "failure_reason": failure_reason,
        "source_path": args.source,
        "source": source,
        "public_allowed": False,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("room_id", "platform", "status", "artifact_id")}, ensure_ascii=False))
    print(f"ROOM_RESULT_WRITTEN={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
