from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from automation_hub.youtube_identity import verify_uploaded_video
from automation_hub.youtube_release import load_release_policy, result_url


ROOT = Path(__file__).resolve().parents[1]


def _service(channel_id: str, privacy: str):
    service = Mock()
    service.videos.return_value.list.return_value.execute.return_value = {
        "items": [{"id": "abcdefghijk", "snippet": {"channelId": channel_id}, "status": {"privacyStatus": privacy}}]
    }
    return service


def test_release_policy_is_immediate_public_and_identity_locked():
    policy = load_release_policy()
    assert policy["upload_privacy_status"] == "public"
    assert policy["public_allowed"] is True
    assert policy["require_authenticated_channel_id_match"] is True
    assert result_url("abcdefghijk") == "https://youtu.be/abcdefghijk"


def test_post_upload_verification_accepts_exact_channel_and_public_status():
    expected = "UC7jOhyMa-FIrzZuea97z1Pw"
    with patch("automation_hub.youtube_identity.expected_channel_id", return_value=expected):
        row = verify_uploaded_video(_service(expected, "public"), "abcdefghijk", "mbb", "public")
    assert row["id"] == "abcdefghijk"


def test_post_upload_verification_rejects_wrong_privacy_or_channel():
    expected = "UC7jOhyMa-FIrzZuea97z1Pw"
    with patch("automation_hub.youtube_identity.expected_channel_id", return_value=expected):
        with pytest.raises(RuntimeError, match="identity/privacy mismatch"):
            verify_uploaded_video(_service(expected, "private"), "abcdefghijk", "mbb", "public")
        with pytest.raises(RuntimeError, match="identity/privacy mismatch"):
            verify_uploaded_video(_service("UCwrong", "public"), "abcdefghijk", "mbb", "public")


def test_existing_video_release_workflow_uses_verified_script():
    text = (ROOT / ".github/workflows/youtube-publish-existing-now.yml").read_text(encoding="utf-8")
    assert "scripts/youtube_set_privacy.py" in text
    assert "--privacy public" in text
    assert "PUBLICATION_RECEIPT" in text
