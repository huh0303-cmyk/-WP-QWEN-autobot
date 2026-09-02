from pathlib import Path

from automation_hub.rooms import RoomRegistry
from automation_hub.workflow_contracts import load_contracts

ROOT = Path(__file__).resolve().parents[1]


def test_room_counts_are_fixed():
    registry = RoomRegistry.load()
    summary = registry.summary()
    assert summary["total"] == 78
    assert summary["wordpress"] == 27
    assert summary["blogger"] == 33
    assert summary["tistory"] == 5
    assert summary["naver"] == 3
    assert summary["youtube"] == 10


def test_all_room_policies_are_non_public():
    registry = RoomRegistry.load()
    assert all(room.publish_policy in {"draft", "private", "awaiting_approval", "paused"} for room in registry.rooms)
    assert all(room.duplicate_guard for room in registry.rooms)


def test_contracts_require_identity_for_dispatched_rooms():
    contracts = load_contracts()
    assert {"room_id", "target_site_url"} <= set(contracts["daily-network-publish.yml"]["required_inputs"])
    assert {"room_id", "platform"} <= set(contracts["platform-publish-v2.yml"]["required_inputs"])
    assert {"room_id", "channel"} <= set(contracts["generate-youtube-playlist.yml"]["required_inputs"])
    assert {"room_id", "channel"} <= set(contracts["curio-longform-daily.yml"]["required_inputs"])


def test_result_collector_treats_missing_optional_artifact_as_noop():
    workflow = (ROOT / ".github" / "workflows" / "automation-room-result-collector.yml").read_text(encoding="utf-8")
    assert "mkdir -p collected-artifacts" in workflow
    assert "head -n 1 || true" in workflow


def test_wordpress_contract_cannot_approve_publication():
    contract = load_contracts()["daily-network-publish.yml"]
    assert contract["safe_policy"] == "draft"
    assert contract["inputs"]["publication_approved"] is False


def test_youtube_contracts_are_private():
    contracts = load_contracts()
    for workflow in ("generate-youtube-playlist.yml", "curio-longform-daily.yml"):
        assert contracts[workflow]["safe_policy"] == "private"
        assert contracts[workflow]["inputs"]["publish_delay_hours"] == ""


def test_playlist_uploader_has_hard_private_status():
    text = (ROOT / "scripts" / "youtube_publish_approved.py").read_text(encoding="utf-8")
    assert '"privacyStatus": "private"' in text
    assert '"privacyStatus": "public"' not in text
    assert 'status["publishAt"]' not in text


def test_curio_uploader_has_hard_private_status():
    text = (ROOT / "scripts" / "curio_upload.py").read_text(encoding="utf-8")
    assert '"privacyStatus": "private"' in text
    assert '"privacyStatus": "public"' not in text
    assert 'status["publishAt"]' not in text
