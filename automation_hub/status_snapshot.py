from __future__ import annotations

import argparse
import json
from pathlib import Path

from .rooms import RoomRegistry
from .status_schema import make_status


def build_snapshot() -> dict:
    registry = RoomRegistry.load()
    rows = []
    for room in registry.rooms:
        if not room.enabled:
            status = "EMPTY" if room.status == "EMPTY" else "PAUSED"
        elif room.status in {"QUALITY_FAIL", "AUTH_REQUIRED", "FAILED", "AWAITING_APPROVAL"}:
            status = room.status
        else:
            status = "READY"
        row = make_status(
            room_id=room.room_id,
            platform=room.platform,
            status=status,
            workflow=room.workflow,
            publish_policy=room.publish_policy,
            next_run=room.next_run,
            details={
                "name": room.name,
                "group": room.group,
                "enabled": room.enabled,
                "destination_id_present": bool(room.destination_id),
                "duplicate_guard": room.duplicate_guard,
            },
        )
        rows.append(row.to_dict())
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return {"summary": {"total": len(rows), "by_status": counts}, "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/automation-room-status.json")
    args = parser.parse_args()
    snapshot = build_snapshot()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(snapshot["summary"], ensure_ascii=False))
    print(f"STATUS_WRITTEN={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
