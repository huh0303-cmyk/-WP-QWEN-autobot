from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

from .rooms import RoomRegistry
from .workflow_contracts import load_contracts


def _room_url(room) -> str:
    raw = (room.name or "").strip()
    if not raw:
        return ""
    if urlparse(raw).scheme in {"http", "https"}:
        return raw
    return f"https://{raw}"


def _resolve_value(expr, room):
    if not isinstance(expr, str):
        return expr
    if expr == "room.platform":
        return room.platform
    if expr == "room.account_id":
        return room.account_id
    if expr == "room.destination_id":
        return room.destination_id
    if expr == "room.language":
        return room.language
    if expr == "room.name":
        return room.name
    if expr == "room.name_url":
        return _room_url(room)
    return expr


def build_dispatch_plan(registry: RoomRegistry | None = None) -> dict:
    registry = registry or RoomRegistry.load()
    contracts = load_contracts()
    dispatches = []
    managed = []
    skipped = []

    for room in registry.rooms:
        if not room.enabled:
            skipped.append({"room_id": room.room_id, "reason": "disabled"})
            continue
        if room.publish_policy == "paused":
            skipped.append({"room_id": room.room_id, "reason": "paused"})
            continue
        if not room.workflow:
            skipped.append({"room_id": room.room_id, "reason": "missing_workflow"})
            continue
        contract = contracts.get(room.workflow)
        if not contract:
            skipped.append({"room_id": room.room_id, "reason": "missing_contract"})
            continue

        safe_policy = contract.get("safe_policy")
        if room.publish_policy not in {safe_policy, "awaiting_approval"}:
            skipped.append({"room_id": room.room_id, "reason": "policy_mismatch"})
            continue

        mode = contract.get("mode", "")
        entry = {
            "room_id": room.room_id,
            "platform": room.platform,
            "workflow": room.workflow,
            "publish_policy": room.publish_policy,
            "artifact_kind": contract.get("artifact_kind", ""),
        }

        if mode == "scheduler_managed":
            entry["mode"] = "scheduler_managed"
            managed.append(entry)
            continue

        if mode != "workflow_dispatch":
            entry["reason"] = f"unsupported_mode:{mode}"
            skipped.append(entry)
            continue

        inputs = {
            key: _resolve_value(value, room)
            for key, value in (contract.get("inputs") or {}).items()
        }
        # Hard safety gate: no room-generated payload may approve public publication.
        if "publication_approved" in inputs:
            inputs["publication_approved"] = False
        entry.update({"mode": "workflow_dispatch", "inputs": inputs})
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
    parser.add_argument("--output", default="artifacts/automation-dispatch-plan.json")
    args = parser.parse_args()

    registry = RoomRegistry.load()
    problems = registry.validate()
    if problems:
        print(json.dumps({"registry_errors": problems}, ensure_ascii=False, indent=2))
        return 1

    plan = build_dispatch_plan(registry)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(plan["summary"], ensure_ascii=False))
    print(f"DISPATCH_PLAN_WRITTEN={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
