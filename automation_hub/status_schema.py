from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

ALLOWED_STATUS = {
    "READY",
    "PLANNED",
    "DISPATCHED",
    "RUNNING",
    "SUCCESS",
    "FAILED",
    "AUTH_REQUIRED",
    "QUALITY_FAIL",
    "AWAITING_APPROVAL",
    "SKIPPED",
    "PAUSED",
    "EMPTY",
}


@dataclass(slots=True)
class AutomationStatus:
    timestamp: str
    room_id: str
    platform: str
    workflow: str = ""
    job_id: str = ""
    run_id: str = ""
    scheduled_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    status: str = "READY"
    artifact_id: str = ""
    artifact_url: str = ""
    publish_policy: str = ""
    failure_reason: str = ""
    retry_count: int = 0
    next_run: str = ""
    details: dict[str, Any] | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.room_id:
            errors.append("room_id is required")
        if not self.platform:
            errors.append("platform is required")
        if self.status not in ALLOWED_STATUS:
            errors.append(f"unsupported status: {self.status}")
        if self.retry_count < 0:
            errors.append("retry_count cannot be negative")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_status(room_id: str, platform: str, status: str, **kwargs: Any) -> AutomationStatus:
    row = AutomationStatus(
        timestamp=kwargs.pop("timestamp", utc_now_iso()),
        room_id=room_id,
        platform=platform,
        status=status,
        **kwargs,
    )
    errors = row.validate()
    if errors:
        raise ValueError("; ".join(errors))
    return row


SHEET_HEADER = [
    "timestamp", "room_id", "platform", "workflow", "job_id", "run_id",
    "scheduled_at", "started_at", "completed_at", "status", "artifact_id",
    "artifact_url", "publish_policy", "failure_reason", "retry_count",
    "next_run", "details",
]
