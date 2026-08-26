from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse


SUPPORTED_PLATFORMS = {"wordpress", "naver", "blogger", "tistory"}
CONTENT_TYPES = {"blog", "news_ko", "news_en"}
PUBLISH_MODES = {"automatic", "review", "paused"}


@dataclass(slots=True)
class SiteConfig:
    """One independently configurable publishing destination.

    The registry is a list of these records, so no platform or site-count limit is
    encoded in the application. Additional accounts are added as rows/config records.
    """

    site_id: str
    platform: str
    name: str
    url: str
    secret_name: str = ""
    enabled: bool = True
    content_type: str = "blog"
    group: str = ""
    language: str = "en"
    timezone: str = "Asia/Seoul"
    publish_mode: str = "automatic"
    daily_min: int = 0
    daily_max: int = 1
    weekly_min: int = 0
    weekly_max: int = 7
    min_gap_minutes: int = 30
    allowed_hours: list[int] = field(default_factory=lambda: list(range(24)))
    content_profile: str = "option_1"
    min_chars: int = 1800
    target_chars: int = 2400
    max_chars: int = 3200
    persona: str = ""
    tone: str = ""
    category_mode: str = "existing_only"
    default_category: str = ""
    allowed_categories: list[str] = field(default_factory=list)
    image_mode: str = "mixed"
    image_min: int = 1
    image_max: int = 2
    keyword_mode: str = "golden_keyword"
    keyword_rules: dict[str, Any] = field(default_factory=dict)
    rss_sources: list[str] = field(default_factory=list)
    affiliate_profile: str = "none"
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SiteConfig":
        known = {field_name for field_name in cls.__dataclass_fields__}
        values = {key: value for key, value in raw.items() if key in known}
        unknown = {key: value for key, value in raw.items() if key not in known}
        values["extra"] = {**values.get("extra", {}), **unknown}
        return cls(**values)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.site_id.strip():
            errors.append("site_id is required")
        if self.platform not in SUPPORTED_PLATFORMS:
            errors.append(f"unsupported platform: {self.platform}")
        if self.content_type not in CONTENT_TYPES:
            errors.append(f"unsupported content_type: {self.content_type}")
        if self.publish_mode not in PUBLISH_MODES:
            errors.append(f"unsupported publish_mode: {self.publish_mode}")
        if self.platform == "wordpress" and urlparse(self.url).scheme not in {"http", "https"}:
            errors.append("wordpress url must be absolute")
        for low, high, label in (
            (self.daily_min, self.daily_max, "daily"),
            (self.weekly_min, self.weekly_max, "weekly"),
            (self.min_chars, self.max_chars, "characters"),
            (self.image_min, self.image_max, "images"),
        ):
            if low < 0 or high < low:
                errors.append(f"invalid {label} range: {low}-{high}")
        if not self.min_chars <= self.target_chars <= self.max_chars:
            errors.append("target_chars must be within min_chars/max_chars")
        if self.content_type.startswith("news") and not self.rss_sources:
            errors.append("news destination requires rss_sources")
        if not self.allowed_hours or any(hour < 0 or hour > 23 for hour in self.allowed_hours):
            errors.append("allowed_hours must contain values from 0 to 23")
        return errors

    def to_sheet_row(self) -> list[Any]:
        return [
            self.site_id,
            self.platform,
            self.name,
            self.url,
            self.content_type,
            self.group,
            "ON" if self.enabled else "OFF",
            self.publish_mode,
            self.daily_min,
            self.daily_max,
            self.weekly_min,
            self.weekly_max,
            self.min_gap_minutes,
            self.content_profile,
            self.min_chars,
            self.target_chars,
            self.max_chars,
            self.persona,
            self.tone,
            self.category_mode,
            self.default_category,
            self.image_mode,
            self.image_min,
            self.image_max,
            self.keyword_mode,
            self.affiliate_profile,
            self.secret_name,
            self.language,
            self.timezone,
            ",".join(self.allowed_categories),
            ",".join(self.rss_sources),
        ]

    @classmethod
    def from_sheet_row(cls, header: list[str], row: list[Any]) -> "SiteConfig":
        """Build a destination from a Google Sheets row.

        Empty trailing cells are allowed. Values controlled through the Korean
        dashboard are normalized here so the publishing engine receives typed
        values instead of spreadsheet strings.
        """
        raw = dict(zip(header, [*row, *([""] * max(0, len(header) - len(row)))]))
        bool_value = str(raw.get("enabled", "ON")).strip().upper()
        raw["enabled"] = bool_value in {"ON", "TRUE", "1", "YES", "Y"}
        for name in ("allowed_categories", "rss_sources"):
            value = str(raw.get(name, "")).strip()
            raw[name] = [item.strip() for item in value.split(",") if item.strip()]
        for name in (
            "daily_min", "daily_max", "weekly_min", "weekly_max",
            "min_gap_minutes", "min_chars", "target_chars", "max_chars",
            "image_min", "image_max",
        ):
            value = raw.get(name, "")
            if value != "":
                raw[name] = int(value)
            else:
                raw.pop(name, None)
        return cls.from_dict({key: value for key, value in raw.items() if value != ""})
