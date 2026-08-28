from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .eligibility import evaluate_room
from .rooms import RoomRegistry
from .workflow_contracts import load_contracts

KST = ZoneInfo("Asia/Seoul")


def build_plan(registry: RoomRegistry, now: datetime | None = None) -> dict:
    now = now or datetime.now(KST)
    contracts = load_contracts()
    selected = []
    skipped = []
    for room in registry.rooms:
        result = evaluate_room(room, contracts, now)
        row = {
            "room_id": room.room_id,
            "platform": room.platform,
            "workflow": room.workflow,
            "destination_id": room.destination_id,
            "publish_policy": room.publish_policy,
            "status": room.status,
        }
        if result.eligible:
            selected.append(row)
        else:
            row["reason"] = result.reason
            skipped.append(row)

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
