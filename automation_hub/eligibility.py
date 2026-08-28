"""Single source of truth for "is this room allowed to run right now".

Both room_scheduler (planning) and dispatch_builder (payload generation) must
agree on exactly which rooms are eligible. Before this module existed the two
callers each re-implemented their own eligibility checks and had drifted out
of sync (dispatch_builder, for example, never checked destination_id,
duplicate_guard, or the schedule window at all, and allowed a
publish_policy=="awaiting_approval" room to bypass a workflow's real
safe_policy). This module is now the only place that decision is made.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from .rooms import SAFE_POLICIES, AutomationRoom
from .youtube_registry import load_channels as load_youtube_channels

# The only room.* expressions a workflow contract is allowed to reference.
# room.room_id is not in the task's literal list but every existing contract
# relies on it to identify which room triggered a run, so it stays supported.
SUPPORTED_ROOM_EXPRESSIONS = {
    "room.room_id",
    "room.platform",
    "room.account_id",
    "room.destination_id",
    "room.language",
    "room.name",
    "room.name_url",
}

_YOUTUBE_ACCOUNT_ID_BY_DESTINATION: dict[str, str] | None = None


def _youtube_account_id_by_destination() -> dict[str, str]:
    """channel_id -> channel_key, loaded from the authoritative youtube_registry
    instead of duplicating account_id into automation_rooms.json for every
    YouTube room (keeps a single source of truth per rule F)."""
    global _YOUTUBE_ACCOUNT_ID_BY_DESTINATION
    if _YOUTUBE_ACCOUNT_ID_BY_DESTINATION is None:
        try:
            channels = load_youtube_channels()
        except Exception:
            channels = []
        _YOUTUBE_ACCOUNT_ID_BY_DESTINATION = {c.channel_id: c.channel_key for c in channels}
    return _YOUTUBE_ACCOUNT_ID_BY_DESTINATION


def room_url(room: AutomationRoom) -> str:
    raw = (room.name or "").strip()
    if not raw:
        return ""
    if urlparse(raw).scheme in {"http", "https"}:
        return raw
    return f"https://{raw}"


def resolve_room_expression(expr: Any, room: AutomationRoom) -> Any:
    if not isinstance(expr, str):
        return expr
    if expr == "room.room_id":
        return room.room_id
    if expr == "room.platform":
        return room.platform
    if expr == "room.account_id":
        if room.account_id:
            return room.account_id
        if room.platform == "youtube":
            return _youtube_account_id_by_destination().get(room.destination_id, "")
        return ""
    if expr == "room.destination_id":
        return room.destination_id
    if expr == "room.language":
        return room.language
    if expr == "room.name":
        return room.name
    if expr == "room.name_url":
        return room_url(room)
    return expr


def _within_schedule_window(room: AutomationRoom, now: datetime) -> bool:
    policy = room.schedule_policy or {}
    hours = policy.get("allowed_hours")
    if hours and now.hour not in {int(h) for h in hours}:
        return False
    weekdays = policy.get("weekdays")
    if weekdays and now.weekday() not in {int(d) for d in weekdays}:
        return False
    return True


def _next_run_ready(room: AutomationRoom, now: datetime) -> bool:
    if not room.next_run:
        return True
    try:
        next_run = datetime.fromisoformat(room.next_run)
    except ValueError:
        return True
    if next_run.tzinfo is None:
        next_run = next_run.replace(tzinfo=now.tzinfo)
    return now >= next_run


@dataclass(slots=True)
class Eligibility:
    room_id: str
    eligible: bool
    reason: str = ""
    mode: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)
    artifact_kind: str = ""


def evaluate_room(room: AutomationRoom, contracts: dict[str, Any], now: datetime) -> Eligibility:
    """The single eligibility judgment shared by room_scheduler and
    dispatch_builder. Order matters only for which `reason` is reported;
    every check below still runs for every room regardless of platform."""
    rid = room.room_id

    if not room.enabled:
        return Eligibility(rid, False, "disabled")
    if room.publish_policy not in SAFE_POLICIES:
        return Eligibility(rid, False, "unsafe_policy")
    if room.publish_policy == "paused":
        return Eligibility(rid, False, "paused")
    if not room.workflow:
        return Eligibility(rid, False, "missing_workflow")
    if room.platform in {"blogger", "tistory", "youtube"} and not room.destination_id:
        return Eligibility(rid, False, "missing_destination")
    if not room.duplicate_guard:
        return Eligibility(rid, False, "duplicate_guard_off")
    if not _within_schedule_window(room, now):
        return Eligibility(rid, False, "outside_schedule_window")
    if not _next_run_ready(room, now):
        return Eligibility(rid, False, "next_run_in_future")

    contract = contracts.get(room.workflow)
    if not contract:
        return Eligibility(rid, False, "missing_contract")
    if room.platform not in set(contract.get("platforms", [])):
        return Eligibility(rid, False, "platform_not_allowed_by_contract")

    safe_policy = contract.get("safe_policy")
    # Exact match only. "awaiting_approval" is a real, distinct safe_policy for
    # Tistory's own contract, never a bypass another platform can borrow.
    if room.publish_policy != safe_policy:
        return Eligibility(rid, False, "policy_mismatch")

    channel_groups = contract.get("channel_groups")
    if channel_groups and room.group not in set(channel_groups):
        return Eligibility(rid, False, "channel_group_mismatch")

    mode = contract.get("mode", "")
    if mode == "scheduler_managed":
        return Eligibility(rid, True, mode="scheduler_managed", artifact_kind=contract.get("artifact_kind", ""))
    if mode != "workflow_dispatch":
        return Eligibility(rid, False, f"unsupported_mode:{mode}")

    inputs: dict[str, Any] = {}
    for key, expr in (contract.get("inputs") or {}).items():
        if isinstance(expr, str) and expr.startswith("room.") and expr not in SUPPORTED_ROOM_EXPRESSIONS:
            return Eligibility(rid, False, f"unsupported_room_expression:{expr}")
        inputs[key] = resolve_room_expression(expr, room)
    # Hard safety gate: no room-generated payload may approve public publication.
    if "publication_approved" in inputs:
        inputs["publication_approved"] = False

    for required_key in contract.get("required_inputs", []):
        if not inputs.get(required_key):
            return Eligibility(rid, False, f"required_input_empty:{required_key}")

    return Eligibility(
        rid, True, mode="workflow_dispatch", inputs=inputs,
        artifact_kind=contract.get("artifact_kind", ""),
    )
