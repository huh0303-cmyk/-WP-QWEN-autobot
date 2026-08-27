from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .rooms import RoomRegistry

KST = ZoneInfo("Asia/Seoul")
SAFE_POLICIES = {"draft", "private", "awaiting_approval", "paused"}


def _allowed_now(room, now: datetime) -> bool:
    policy = room.schedule_policy or {}
    hours = policy.get("allowed_hours")
    if hours and now.hour not in {int(h) for h in hours}:
        return False
    weekdays = policy.get("weekdays")
    if weekdays and now.weekday() not in {int(d) for d in weekdays}:
        return False
    return True


def build_plan(registry: RoomRegistry, now: datetime | None = None) -> dict:
    now = now or datetime.now(KST)
    selected = []
    skipped = []
    for room in registry.rooms:
        reason = None
        if not room.enabled:
            reason = "disabled"
        elif room.publish_policy not in SAFE_POLICIES:
            reason = "unsafe_policy"
        elif room.publish_policy == "paused":
            reason = "paused"
        elif not room.workflow:
            reason = "missing_workflow"
        elif room.platform in {"blogger", "tistory", "youtube"} and not room.destination_id:
            reason = "missing_destination"
        elif not room.duplicate_guard:
            reason = "duplicate_guard_off"
        elif not _allowed_now(room, now):
            reason = "outside_schedule_window"

        row = {
            "room_id": room.room_id,
            "platform": room.platform,
            "workflow": room.workflow,
            "destination_id": room.destination_id,
            "publish_policy": room.publish_policy,
            "status": room.status,
        }
        if reason:
            row["reason"] = reason
            skipped.append(row)
        else:
            selected.append(row)

    return {
        "generated_at": now.isoformat(),
        "mode": "PLAN_ONLY",
        "public_allowed": False,
        "summary": {
            "rooms_total": len(registry.rooms),
            "selected": len(selected),
            "skipped": len(skipped),
        },
        "selected": selected,
        "skipped": skipped,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a safe execution plan from automation rooms")
    parser.add_argument("--output", default="artifacts/automation-room-plan.json")
    args = parser.parse_args()

    registry = RoomRegistry.load()
    problems = registry.validate()
    if problems:
        print(json.dumps({"registry_errors": problems}, ensure_ascii=False, indent=2))
        return 1

    plan = build_plan(registry)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(plan["summary"], ensure_ascii=False))
    print(f"PLAN_WRITTEN={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
