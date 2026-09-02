"""Fail-closed readiness checks for the ten-channel YouTube runner."""
from __future__ import annotations

import datetime as dt
import os
from dataclasses import dataclass, field
from typing import Mapping

from .sheet_schema import YOUTUBE_CHANNEL_HEADER
from .youtube_identity import verify_authenticated_channel
from .youtube_registry import YouTubeChannel, load_channels


TRUE_VALUES = {"ON", "TRUE", "1", "YES"}
FALSE_VALUES = {"OFF", "FALSE", "0", "NO"}
READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
FORBIDDEN_MUTATION_SCOPES = {
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube",
}


@dataclass(slots=True)
class ReadinessResult:
    channel_key: str
    config_ready: bool = False
    credentials_ready: bool = False
    upload_scope_ready: bool = False
    oauth_ready: bool = False
    expected_channel_id: str = ""
    verified_channel_id: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return self.config_ready and self.credentials_ready and self.upload_scope_ready and self.oauth_ready and not self.errors

    def as_dict(self) -> dict[str, object]:
        return {
            "channel_key": self.channel_key,
            "ready": self.ready,
            "config_ready": self.config_ready,
            "credentials_ready": self.credentials_ready,
            "upload_scope_ready": self.upload_scope_ready,
            "oauth_ready": self.oauth_ready,
            "expected_channel_id": self.expected_channel_id,
            "verified_channel_id": self.verified_channel_id,
            "errors": self.errors,
        }


def _first_env(env: Mapping[str, str], *names: str) -> str:
    return next((str(env.get(name, "")).strip() for name in names if str(env.get(name, "")).strip()), "")


def credential_values(
    channel: YouTubeChannel,
    env: Mapping[str, str] | None = None,
    *,
    allow_runtime_alias: bool = True,
) -> dict[str, str]:
    """Resolve per-channel credentials without exposing their values in reports."""
    source = env or os.environ
    profile = channel.secret_profile
    refresh_names = [f"YOUTUBE_OAUTH_REFRESH_TOKEN_{profile}"]
    # A worker maps its selected profile into this generic runtime variable.
    # The legacy unsuffixed repository secret belongs only to globalmusic.
    if allow_runtime_alias or channel.channel_key == "globalmusic":
        refresh_names.append("YOUTUBE_OAUTH_REFRESH_TOKEN")
    return {
        "client_id": _first_env(source, f"YOUTUBE_OAUTH_CLIENT_ID_{profile}", "YOUTUBE_OAUTH_CLIENT_ID", "YOUTUBE_OAUTH_CLIENT_ID_NEW"),
        "client_secret": _first_env(source, f"YOUTUBE_OAUTH_CLIENT_SECRET_{profile}", "YOUTUBE_OAUTH_CLIENT_SECRET", "YOUTUBE_OAUTH_CLIENT_SECRET_NEW"),
        "refresh_token": _first_env(source, *refresh_names),
    }


def validate_sheet_registry(values: list[list[object]], channels: list[YouTubeChannel] | None = None) -> list[str]:
    """Validate the Sheet control plane against the canonical ten-channel registry."""
    canonical = channels or load_channels()
    if not values or [str(value) for value in values[0]] != YOUTUBE_CHANNEL_HEADER:
        return ["YouTube channel sheet header mismatch"]
    rows: dict[str, list[str]] = {}
    errors: list[str] = []
    for index, raw in enumerate(values[1:], 2):
        if not raw or not str(raw[0]).strip():
            continue
        row = [str(value or "").strip() for value in raw] + [""] * max(0, len(YOUTUBE_CHANNEL_HEADER) - len(raw))
        key = row[0]
        if key in rows:
            errors.append(f"duplicate Sheet channel_key at row {index}: {key}")
            continue
        rows[key] = row[:len(YOUTUBE_CHANNEL_HEADER)]
    expected = {channel.channel_key: channel for channel in canonical}
    if set(rows) != set(expected):
        errors.append(f"Sheet roster mismatch: expected={sorted(expected)} actual={sorted(rows)}")
    for key in sorted(set(rows) & set(expected)):
        row, channel = rows[key], expected[key]
        checks = {
            "channel_type": (row[1], channel.channel_type),
            "display_name": (row[2], channel.display_name),
            "channel_id": (row[3], channel.channel_id),
            "secret_profile": (row[4], channel.secret_profile),
            "workflow": (row[5], channel.workflow),
            "interval_days_min": (row[7], str(channel.interval_days_min)),
            "interval_days_max": (row[8], str(channel.interval_days_max)),
        }
        for field_name, (actual, wanted) in checks.items():
            if actual != wanted:
                errors.append(f"{key}: Sheet {field_name} mismatch")
        if row[6].upper() not in TRUE_VALUES | FALSE_VALUES:
            errors.append(f"{key}: enabled must be ON or OFF")
        if row[7:9] != ["2", "3"]:
            errors.append(f"{key}: interval must remain 2-3 days")
        if row[15]:
            try:
                parsed = dt.datetime.fromisoformat(row[15].replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    errors.append(f"{key}: next_run_at must include a timezone")
            except ValueError:
                errors.append(f"{key}: invalid next_run_at")
    return errors


def assert_access_scope(credentials, required_scope: str) -> None:
    """Require an actually granted scope, not merely a requested refresh scope."""
    granted = set(credentials.granted_scopes or ())
    if granted:
        dangerous = granted & FORBIDDEN_MUTATION_SCOPES
        if dangerous:
            raise RuntimeError(f"OAuth access token contains forbidden mutation scopes: {sorted(dangerous)}")
        if required_scope not in granted:
            raise RuntimeError(f"OAuth access token did not grant required scope: {required_scope}")
        return
    # Google may omit `scope` from a refresh response. Verify the short-lived
    # access token explicitly and fail closed; never assume the requested scope.
    import requests

    try:
        response = requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"access_token": credentials.token}, timeout=15,
        )
        if response.status_code != 200:
            raise RuntimeError("tokeninfo rejected the access token")
        token_scopes = set(str(response.json().get("scope", "")).split())
    except Exception:
        raise RuntimeError("Could not verify OAuth access-token scopes") from None
    dangerous = token_scopes & FORBIDDEN_MUTATION_SCOPES
    if dangerous:
        raise RuntimeError(f"OAuth access token contains forbidden mutation scopes: {sorted(dangerous)}")
    if required_scope not in token_scopes:
        raise RuntimeError(f"OAuth access token did not grant required scope: {required_scope}")


def build_youtube_service(
    channel: YouTubeChannel,
    env: Mapping[str, str] | None = None,
    *,
    allow_runtime_alias: bool = True,
):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    values = credential_values(channel, env, allow_runtime_alias=allow_runtime_alias)
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError(f"missing OAuth credential fields: {', '.join(missing)}")
    # The refresh token retains its originally granted scopes. Do not request a
    # broader scope during refresh; the preflight only reads the authenticated ID.
    credentials = Credentials(
        token=None,
        refresh_token=values["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=values["client_id"],
        client_secret=values["client_secret"],
        scopes=[READONLY_SCOPE],
    )
    credentials.refresh(Request())
    assert_access_scope(credentials, READONLY_SCOPE)
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


def verify_upload_scope(
    channel: YouTubeChannel,
    env: Mapping[str, str] | None = None,
    *,
    allow_runtime_alias: bool = True,
) -> None:
    """Refresh an upload-only token without making a YouTube write request."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    values = credential_values(channel, env, allow_runtime_alias=allow_runtime_alias)
    credentials = Credentials(
        token=None,
        refresh_token=values["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=values["client_id"],
        client_secret=values["client_secret"],
        scopes=[UPLOAD_SCOPE],
    )
    credentials.refresh(Request())
    assert_access_scope(credentials, UPLOAD_SCOPE)


def check_channel(
    channel: YouTubeChannel,
    *,
    env: Mapping[str, str] | None = None,
    probe: bool = True,
    allow_runtime_alias: bool = True,
) -> ReadinessResult:
    result = ReadinessResult(channel_key=channel.channel_key, expected_channel_id=channel.channel_id)
    config_errors = channel.validate()
    if config_errors:
        result.errors.extend(config_errors)
        return result
    result.config_ready = True
    missing = [name for name, value in credential_values(channel, env, allow_runtime_alias=allow_runtime_alias).items() if not value]
    if missing:
        result.errors.append(f"missing OAuth credential fields: {', '.join(missing)}")
        return result
    result.credentials_ready = True
    if not probe:
        result.upload_scope_ready = True
        result.oauth_ready = True
        return result
    try:
        verify_upload_scope(channel, env, allow_runtime_alias=allow_runtime_alias)
        result.upload_scope_ready = True
        actual = verify_authenticated_channel(
            build_youtube_service(channel, env, allow_runtime_alias=allow_runtime_alias), channel.channel_key,
        )
    except Exception as exc:
        result.errors.append(f"OAuth/channel probe failed: {type(exc).__name__}: {exc}")
        return result
    result.verified_channel_id = actual
    result.oauth_ready = True
    return result
