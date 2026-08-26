from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from .time_utils import iso_kst


@dataclass(slots=True)
class PublishJob:
    job_id: str
    site_id: str
    title: str
    content_html: str
    labels: list[str] = field(default_factory=list)
    publish_now: bool = True
    source_keyword: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.job_id.strip():
            errors.append("job_id is required")
        if not self.site_id.strip():
            errors.append("site_id is required")
        if not self.title.strip():
            errors.append("title is required")
        if not self.content_html.strip():
            errors.append("content_html is required")
        return errors


@dataclass(slots=True)
class PublishResult:
    ok: bool
    platform: str
    site_id: str
    job_id: str
    status: str
    public_url: str = ""
    remote_id: str = ""
    error_code: str = ""
    message: str = ""
    completed_at: str = field(default_factory=iso_kst)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Publisher(Protocol):
    def publish(self, job: PublishJob) -> PublishResult: ...
