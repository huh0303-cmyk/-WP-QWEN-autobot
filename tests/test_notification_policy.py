from pathlib import Path
from unittest.mock import patch

from automation_hub.draft_notifier import notify_blogger_draft
from scripts.publishing_completion_notify import send_email


def test_normal_completion_email_is_suppressed_by_default(monkeypatch):
    monkeypatch.delenv("NORMAL_COMPLETION_EMAIL_ENABLED", raising=False)
    with patch("smtplib.SMTP_SSL") as smtp:
        assert send_email("done", "body") is True
        smtp.assert_not_called()


def test_blogger_still_records_review_without_sending_mail(monkeypatch):
    monkeypatch.delenv("NORMAL_COMPLETION_EMAIL_ENABLED", raising=False)
    with patch("scripts.review_sheet.append_review_rows", return_value=True), patch("smtplib.SMTP") as smtp:
        assert notify_blogger_draft(site_id="blogger_x", title="Draft", review_url="https://example.test/edit",
                                    search_description="Description") is True
        smtp.assert_not_called()


def test_policy_keeps_failure_and_daily_summary_channels():
    policy = (Path(__file__).resolve().parents[1] / "docs" / "CONTROL_ROOM_NOTIFICATION_POLICY.md").read_text(encoding="utf-8")
    assert "일일 CEO 종합보고 1회" in policy
    assert "실패·긴급 장애 알림" in policy
