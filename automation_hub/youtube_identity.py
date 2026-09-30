from __future__ import annotations

from .youtube_registry import load_channels


def expected_channel_id(channel_key: str) -> str:
    for channel in load_channels():
        if channel.channel_key == channel_key:
            return channel.channel_id
    raise KeyError(channel_key)


def verify_authenticated_channel(service, channel_key: str) -> str:
    """Stop an upload when OAuth belongs to a different YouTube channel."""
    expected = expected_channel_id(channel_key)
    response = service.channels().list(part="id", mine=True, maxResults=1).execute()
    items = response.get("items", [])
    actual = items[0].get("id", "") if items else ""
    if actual != expected:
        raise RuntimeError(
            f"YouTube OAuth channel mismatch for {channel_key}: expected {expected}, got {actual or 'none'}"
        )
    return actual


def verify_uploaded_video(service, video_id: str, channel_key: str, privacy_status: str) -> dict:
    """Verify the exact uploaded video belongs to the locked channel and has the requested visibility."""
    expected = expected_channel_id(channel_key)
    response = service.videos().list(part="snippet,status", id=video_id).execute()
    items = response.get("items", [])
    if len(items) != 1:
        raise RuntimeError(f"YouTube upload verification could not retrieve {video_id}")
    video = items[0]
    actual_channel = video.get("snippet", {}).get("channelId", "")
    actual_privacy = video.get("status", {}).get("privacyStatus", "")
    if actual_channel != expected or actual_privacy != privacy_status:
        raise RuntimeError(
            "YouTube upload identity/privacy mismatch: "
            f"expected {expected}/{privacy_status}, got {actual_channel or 'none'}/{actual_privacy or 'none'}"
        )
    return video

