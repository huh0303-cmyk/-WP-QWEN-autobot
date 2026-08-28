from __future__ import annotations

import json
from pathlib import Path

from .rooms import RoomRegistry

CONTRACTS_PATH = Path(__file__).resolve().parents[1] / "config" / "automation_workflow_contracts.json"


def load_contracts(path: str | Path = CONTRACTS_PATH) -> dict:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return raw.get("contracts", {})


def validate_contracts() -> dict[str, list[str]]:
    registry = RoomRegistry.load()
    contracts = load_contracts()
    problems: dict[str, list[str]] = {}

    for room in registry.rooms:
        if not room.workflow:
            continue
        contract = contracts.get(room.workflow)
        if contract is None:
            problems.setdefault(room.room_id, []).append(f"missing workflow contract: {room.workflow}")
            continue
        if room.platform not in set(contract.get("platforms", [])):
            problems.setdefault(room.room_id, []).append(
                f"workflow {room.workflow} does not allow platform {room.platform}"
            )
        safe_policy = contract.get("safe_policy")
        if room.enabled and room.publish_policy not in {safe_policy, "paused"}:
            # Tistory intentionally stays awaiting_approval; Blogger/WordPress draft; YouTube private.
            problems.setdefault(room.room_id, []).append(
                f"room policy {room.publish_policy} differs from workflow safe policy {safe_policy}"
            )

    return problems


def main() -> int:
    problems = validate_contracts()
    if problems:
        print(json.dumps(problems, ensure_ascii=False, indent=2))
        return 1
    print("WORKFLOW CONTRACTS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
