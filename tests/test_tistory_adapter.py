import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automation_hub.publishing import PublishJob  # noqa: E402
from automation_hub.tistory_adapter import TistoryPublisher, _blog_name_from_url  # noqa: E402


def test_blog_name_parsed_from_url():
    assert _blog_name_from_url("https://k-trip365.tistory.com/") == "k-trip365"


def test_publish_fails_cleanly_without_access_token(monkeypatch):
    monkeypatch.delenv("TISTORY_ACCESS_TOKEN", raising=False)
    publisher = TistoryPublisher(site_id="tistory_ktrip365", blog_url="https://k-trip365.tistory.com/")
    job = PublishJob(job_id="tistory_ktrip365:2026-08-30", site_id="tistory_ktrip365", title="Title", content_html="<p>Body</p>")
    result = publisher.publish(job)
    assert result.ok is False
    assert result.status == "FAILED"
    assert result.error_code == "missing_credential"


def test_publish_succeeds_on_tistory_200(monkeypatch):
    monkeypatch.setenv("TISTORY_ACCESS_TOKEN", "fake-token")
    publisher = TistoryPublisher(site_id="tistory_ktrip365", blog_url="https://k-trip365.tistory.com/")
    job = PublishJob(job_id="tistory_ktrip365:2026-08-30", site_id="tistory_ktrip365", title="Title", content_html="<p>Body</p>")
    fake_response = MagicMock()
    fake_response.json.return_value = {"tistory": {"status": "200", "postId": "42", "url": "https://k-trip365.tistory.com/42"}}
    fake_response.raise_for_status.return_value = None
    with patch("automation_hub.tistory_adapter.requests.post", return_value=fake_response) as post:
        result = publisher.publish(job)
    post.assert_called_once()
    assert result.ok is True
    assert result.status == "PUBLISHED"
    assert result.public_url == "https://k-trip365.tistory.com/42"


def test_publish_reports_failed_on_tistory_error_status(monkeypatch):
    monkeypatch.setenv("TISTORY_ACCESS_TOKEN", "fake-token")
    publisher = TistoryPublisher(site_id="tistory_ktrip365", blog_url="https://k-trip365.tistory.com/")
    job = PublishJob(job_id="tistory_ktrip365:2026-08-30", site_id="tistory_ktrip365", title="Title", content_html="<p>Body</p>")
    fake_response = MagicMock()
    fake_response.json.return_value = {"tistory": {"status": "401", "error_message": "invalid token"}}
    fake_response.raise_for_status.return_value = None
    with patch("automation_hub.tistory_adapter.requests.post", return_value=fake_response):
        result = publisher.publish(job)
    assert result.ok is False
    assert result.status == "FAILED"
    assert result.error_code == "tistory_status_401"
