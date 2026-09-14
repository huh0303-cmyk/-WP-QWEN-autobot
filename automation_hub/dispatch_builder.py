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


def _selected_room_ids(plan_path: str | Path | None) -> set[str] | None:
    """Rooms room_scheduler already marked eligible, if a plan file is given.
    Returns None when no plan was passed (dispatch_builder then judges every
    room itself, using the exact same eligibility function)."""
    if not plan_path:
        return None
    path = Path(plan_path)
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    selected = raw.get("selected")
    if not isinstance(selected, list):
        return None
    return {row.get("room_id") for row in selected if isinstance(row, dict)}


def build_dispatch_plan(
    registry: RoomRegistry | None = None,
    now: datetime | None = None,
    plan_path: str | Path | None = None,
) -> dict:
    registry = registry or RoomRegistry.load()
    now = now or datetime.now(KST)
    contracts = load_contracts()
    allowed_room_ids = _selected_room_ids(plan_path)

    dispatches = []
    managed = []
    skipped = []

    for room in registry.rooms:
        if allowed_room_ids is not None and room.room_id not in allowed_room_ids:
            skipped.append({"room_id": room.room_id, "reason": "not_in_scheduler_plan"})
            continue

        result = evaluate_room(room, contracts, now)
        if not result.eligible:
            skipped.append({"room_id": room.room_id, "reason": result.reason})
            continue

        entry = {
            "room_id": room.room_id,
            "platform": room.platform,
            "workflow": room.workflow,
            "publish_policy": room.publish_policy,
            "artifact_kind": result.artifact_kind,
            "mode": result.mode,
        }
        if result.mode == "scheduler_managed":
            managed.append(entry)
        else:
            entry["inputs"] = result.inputs
            dispatches.append(entry)

    return {
        "mode": "DRY_RUN",
        "public_allowed": False,
        "summary": {
            "rooms_total": len(registry.rooms),
            "dispatch_ready": len(dispatches),
            "scheduler_managed": len(managed),
            "skipped": len(skipped),
        },
        "dispatches": dispatches,
        "scheduler_managed": managed,
        "skipped": skipped,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build safe GitHub workflow_dispatch payloads from automation rooms")
    parser.add_argument("--plan", default=None, help="Optional room_scheduler plan.json to restrict rooms to")
    parser.add_argument("--output", default="artifacts/automation-dispatch-plan.json")
    args = parser.parse_args()

    registry = RoomRegistry.load()
    problems = registry.validate()
    if problems:
        print(json.dumps({"registry_errors": problems}, ensure_ascii=False, indent=2))
        return 1

    plan = build_dispatch_plan(registry, plan_path=args.plan)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(plan["summary"], ensure_ascii=False))
    print(f"DISPATCH_PLAN_WRITTEN={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
