from __future__ import annotations

import json
from pathlib import Path

from .eligibility import SUPPORTED_ROOM_EXPRESSIONS
from .rooms import RoomRegistry

CONTRACTS_PATH = Path(__file__).resolve().parents[1] / "config" / "automation_workflow_contracts.json"


def load_contracts(path: str | Path = CONTRACTS_PATH) -> dict:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return raw.get("contracts", {})


def validate_contract_expressions(contracts: dict) -> dict[str, list[str]]:
    """Every room.* expression a contract references must be one this hub
    actually knows how to resolve. Anything else (e.g. a typo, or a field
    that isn't safe/meaningful to hand to a workflow_dispatch input) fails
    validation instead of silently passing the literal string through."""
    problems: dict[str, list[str]] = {}
    for workflow, contract in contracts.items():
        for input_name, expr in (contract.get("inputs") or {}).items():
            if isinstance(expr, str) and expr.startswith("room.") and expr not in SUPPORTED_ROOM_EXPRESSIONS:
                problems.setdefault(workflow, []).append(
                    f"unsupported room expression for input {input_name!r}: {expr}"
                )
    return problems


def validate_channel_groups(registry: RoomRegistry, contracts: dict) -> dict[str, list[str]]:
    """A workflow contract's channel_groups is a real constraint, not
    documentation: every room dispatched through it must declare a matching
    room.group."""
    problems: dict[str, list[str]] = {}
    for room in registry.rooms:
        if not room.enabled:
            continue
        contract = contracts.get(room.workflow)
        if not contract:
            continue
        channel_groups = contract.get("channel_groups")
        if channel_groups and room.group not in set(channel_groups):
            problems.setdefault(room.room_id, []).append(
                f"room.group {room.group!r} not in workflow {room.workflow} channel_groups {channel_groups}"
            )
    return problems


def validate_contracts() -> dict[str, list[str]]:
    registry = RoomRegistry.load()
    contracts = load_contracts()
    problems: dict[str, list[str]] = {}

    for room in registry.rooms:
        # Placeholder rooms (for example future Naver accounts) must never
        # block the production WordPress/Blogger/Tistory plan while disabled.
        # They become contract-enforced as soon as they are enabled.
        if not room.enabled:
            continue
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

    for workflow, errors in validate_contract_expressions(contracts).items():
        problems.setdefault(workflow, []).extend(errors)
    for room_id, errors in validate_channel_groups(registry, contracts).items():
        problems.setdefault(room_id, []).extend(errors)

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
