from control_center import audit_engine


class FakeResponse:
    def __init__(self, status_code=200, url="https://example.com/post", text="<html><h1>Expected Title</h1></html>"):
        self.status_code = status_code
        self.url = url
        self.text = text
        self.content = text.encode("utf-8")
        self.headers = {"content-type": "text/html; charset=utf-8"}


def test_web_publication_requires_real_target_page(monkeypatch):
    monkeypatch.setattr(audit_engine.requests, "get", lambda *a, **k: FakeResponse())
    result = audit_engine.verify_web_publication(
        "https://example.com/post",
        "https://example.com",
        expected_title="Expected Title",
    )
    assert result.verified is True
    assert result.state == "VERIFIED_COMPLETE"
    assert result.evidence["http_status"] == 200


def test_web_publication_rejects_wrong_host(monkeypatch):
    called = {"value": False}

    def fake_get(*args, **kwargs):
        called["value"] = True
        return FakeResponse()

    monkeypatch.setattr(audit_engine.requests, "get", fake_get)
    result = audit_engine.verify_web_publication(
        "https://wrong.example/post",
        "https://example.com",
    )
    assert result.verified is False
    assert result.state == "NEEDS_ATTENTION"
    assert called["value"] is False


def test_private_youtube_receipt_is_not_public_complete():
    receipt = {
        "video_id": "AbCdEf12345",
        "privacy_status": "private",
        "channel_key": "demo",
        "verified_channel_id": "UC1234567890123456789012",
    }
    result = audit_engine.verify_youtube_receipt(
        receipt,
        expected_channel_id="UC1234567890123456789012",
        expected_channel_key="demo",
        expected_privacy="private",
    )
    assert result.verified is True
    assert result.state == "VERIFIED_PRIVATE"
    assert "studio.youtube.com/video/AbCdEf12345/edit" in result.evidence["review_url"]


def test_youtube_receipt_rejects_wrong_channel():
    receipt = {
        "video_id": "AbCdEf12345",
        "privacy_status": "private",
        "channel_key": "demo",
        "verified_channel_id": "UC0000000000000000000000",
    }
    result = audit_engine.verify_youtube_receipt(
        receipt,
        expected_channel_id="UC1234567890123456789012",
        expected_channel_key="demo",
        expected_privacy="private",
    )
    assert result.verified is False
    assert result.state == "NEEDS_ATTENTION"
