"""Canonical owner-approved YouTube release policy."""
from __future__ import annotations

import json
from pathlib import Path


POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "youtube_release_policy.json"


def load_release_policy(path: str | Path = POLICY_PATH) -> dict:
    policy = json.loads(Path(path).read_text(encoding="utf-8"))
    if policy.get("upload_privacy_status") not in {"private", "public"}:
        raise ValueError("YouTube upload_privacy_status must be private or public")
    if policy.get("public_allowed") is not (policy["upload_privacy_status"] == "public"):
        raise ValueError("YouTube public_allowed does not match upload_privacy_status")
    if policy.get("require_authenticated_channel_id_match") is not True:
        raise ValueError("YouTube channel identity verification cannot be disabled")
    if policy.get("require_post_upload_privacy_verification") is not True:
        raise ValueError("YouTube post-upload privacy verification cannot be disabled")
    return policy


def upload_privacy_status() -> str:
    return str(load_release_policy()["upload_privacy_status"])


def public_allowed() -> bool:
    return bool(load_release_policy()["public_allowed"])


def result_url(video_id: str) -> str:
    return f"https://youtu.be/{video_id}" if public_allowed() else f"https://studio.youtube.com/video/{video_id}/edit"


def calendar_status() -> str:
    return "공개완료" if public_allowed() else "비공개 업로드"
