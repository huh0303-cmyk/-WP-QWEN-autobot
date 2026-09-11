from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOMS_PATH = Path(__file__).resolve().parents[1] / "config" / "automation_rooms.json"
ALLOWED_PLATFORMS = {"wordpress", "blogger", "tistory", "youtube"}
SAFE_POLICIES = {"draft", "private", "awaiting_approval", "paused"}


@dataclass(slots=True)
class AutomationRoom:
    room_id: str
    platform: str
    name: str
    enabled: bool = False
    source_id: str = ""
    account_id: str = ""
    destination_id: str = ""
    workflow: str = ""
    language: str = "en"
    group: str = ""
    publish_policy: str = "paused"
    duplicate_guard: bool = True
    schedule_policy: dict[str, Any] = field(default_factory=dict)
    persona: str = ""
    status: str = "EMPTY"
    next_run: str = ""
    notes: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AutomationRoom":
        known = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in raw.items() if k in known})

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.room_id:
            errors.append("room_id is required")
        # Disabled placeholder rooms may describe a future platform without
        # blocking today's production plan. Full platform validation begins
        # only when that room is enabled for execution.
        if self.enabled and self.platform not in ALLOWED_PLATFORMS:
            errors.append(f"unsupported platform: {self.platform}")
        if self.publish_policy not in SAFE_POLICIES:
            errors.append(f"unsafe publish_policy: {self.publish_policy}")
        if not self.duplicate_guard:
            errors.append("duplicate_guard must stay enabled")
        if self.enabled and not self.workflow:
            errors.append("enabled room requires workflow")
        if self.enabled and self.platform in {"blogger", "tistory", "youtube"} and not self.destination_id:
            errors.append("enabled remote room requires destination_id")
        return errors


class RoomRegistry:
    def __init__(self, rooms: list[AutomationRoom], expected_counts: dict[str, int] | None = None):
        self.rooms = rooms
        self.expected_counts = expected_counts or {}

    @classmethod
    def load(cls, path: str | Path = ROOMS_PATH) -> "RoomRegistry":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            [AutomationRoom.from_dict(item) for item in raw.get("rooms", [])],
            {str(k): int(v) for k, v in raw.get("expected_counts", {}).items()},
        )

    def summary(self) -> dict[str, int]:
        out: dict[str, int] = {"total": len(self.rooms), "enabled": 0}
        for room in self.rooms:
            out[room.platform] = out.get(room.platform, 0) + 1
            if room.enabled:
                out["enabled"] += 1
        return out

    def validate(self) -> dict[str, list[str]]:
        problems: dict[str, list[str]] = {}
        seen: set[str] = set()
        for room in self.rooms:
            errors = room.validate()
            if room.room_id in seen:
                errors.append("duplicate room_id")
            seen.add(room.room_id)
            if errors:
                problems[room.room_id or "<blank>"] = errors
        summary = self.summary()
        for platform, expected in self.expected_counts.items():
            actual = summary.get(platform, 0)
            if actual != expected:
                problems[f"count:{platform}"] = [f"expected {expected}, found {actual}"]
        return problems


def main() -> int:
    registry = RoomRegistry.load()
    print(json.dumps(registry.summary(), ensure_ascii=False, indent=2))
    problems = registry.validate()
    if problems:
        print(json.dumps(problems, ensure_ascii=False, indent=2))
        return 1
    print("ROOM REGISTRY PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
