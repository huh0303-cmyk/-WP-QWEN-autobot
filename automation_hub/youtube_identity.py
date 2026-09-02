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
    response = service.channels().list(part="id", mine=True, maxResults=50).execute()
    items = response.get("items", [])
    actual_ids = [item.get("id", "") for item in items if item.get("id")]
    if actual_ids != [expected]:
        raise RuntimeError(
            f"YouTube OAuth channel mismatch for {channel_key}: expected only {expected}, "
            f"got {','.join(actual_ids) or 'none'}"
        )
    return expected

