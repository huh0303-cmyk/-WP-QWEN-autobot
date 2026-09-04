from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


DEFAULT_PATH = Path(__file__).resolve().parents[1] / "config" / "youtube_channels.json"


@dataclass(slots=True)
class YouTubeChannel:
    channel_key: str
    channel_type: str
    display_name: str
    channel_id: str
    secret_profile: str
    workflow: str
    enabled: bool = True
    interval_days_min: int = 2
    interval_days_max: int = 3
    publish_delay_hours: int = 3
    allowed_hour_start: int = 0
    allowed_hour_end: int = 23
    topic_mode: str = "auto"
    language: str = "en"
    tone: str = ""
    official_name: str = ""
    handle: str = ""
    created_at: str = ""
    subscriber_count_snapshot: int | None = None
    video_count_snapshot: int | None = None
    next_run_at: str = ""
    last_dispatched_at: str = ""
    last_run_status: str = ""

    def validate(self) -> list[str]:
        errors = []
        if self.channel_type not in {"playlist", "knowledge"}:
            errors.append("channel_type must be playlist or knowledge")
        if not self.channel_id.startswith("UC") or len(self.channel_id) != 24:
            errors.append("invalid YouTube channel_id")
        if self.interval_days_min < 1 or self.interval_days_max < self.interval_days_min:
            errors.append("invalid interval range")
        if not 0 <= self.allowed_hour_start <= self.allowed_hour_end <= 23:
            errors.append("invalid allowed hour range")
        expected = "generate-youtube-playlist.yml" if self.channel_type == "playlist" else "curio-longform-daily.yml"
        if self.workflow != expected:
            errors.append(f"workflow must be {expected}")
        return errors

    def to_row(self) -> list[object]:
        return [
            self.channel_key, self.channel_type, self.display_name, self.channel_id,
            self.secret_profile, self.workflow, "ON" if self.enabled else "OFF",
            self.interval_days_min, self.interval_days_max, self.publish_delay_hours,
            self.allowed_hour_start, self.allowed_hour_end, self.topic_mode,
            self.language, self.tone, self.next_run_at, self.last_dispatched_at,
            self.last_run_status,
        ]


def load_channels(path: str | Path = DEFAULT_PATH) -> list[YouTubeChannel]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    channels = [YouTubeChannel(**item) for item in raw["channels"]]
    seen = set()
    for channel in channels:
        errors = channel.validate()
        if channel.channel_key in seen:
            errors.append("duplicate channel_key")
        if channel.channel_id in {item.channel_id for item in channels if item.channel_key in seen}:
            errors.append("duplicate channel_id")
        if errors:
            raise ValueError(f"{channel.channel_key}: {errors}")
        seen.add(channel.channel_key)
    return channels

