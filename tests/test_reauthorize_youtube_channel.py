"""Focused secret-scope checks for owner-approved YouTube OAuth repair."""

from subprocess import CompletedProcess
from unittest.mock import patch

from scripts.reauthorize_youtube_channel import _sync_gh_secret


def test_new_channel_secret_uses_existing_youtube_environment():
    replies = [
        CompletedProcess([], 0, stdout='[{"name":"EXISTING"}]', stderr=""),
        CompletedProcess([], 0, stdout="", stderr=""),
    ]
    with patch("scripts.reauthorize_youtube_channel.subprocess.run", side_effect=replies) as run:
        scope = _sync_gh_secret("NEW_CHANNEL", "private-token")
    assert scope == "environment:youtube-channels"
    assert run.call_args_list[1].args[0] == [
        "gh", "secret", "set", "--env", "youtube-channels", "NEW_CHANNEL"
    ]
    assert run.call_args_list[1].kwargs["input"] == "private-token"


def test_existing_repository_secret_updates_in_place():
    replies = [
        CompletedProcess([], 0, stdout='[{"name":"EXISTING"}]', stderr=""),
        CompletedProcess([], 0, stdout="", stderr=""),
    ]
    with patch("scripts.reauthorize_youtube_channel.subprocess.run", side_effect=replies) as run:
        scope = _sync_gh_secret("EXISTING", "private-token")
    assert scope == "repository"
    assert run.call_args_list[1].args[0] == ["gh", "secret", "set", "EXISTING"]
