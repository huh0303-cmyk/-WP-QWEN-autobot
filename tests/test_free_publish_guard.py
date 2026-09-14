from datetime import datetime, timezone
from unittest.mock import Mock
import pytest
import requests
from scripts import free_publish_guard as guard

def test_midnight_uses_korea_date_and_existing_post_blocks(monkeypatch):
    response = Mock()
    response.json.return_value = {"items": [{"id": "42"}]}
    request = Mock(return_value=response)
    monkeypatch.setattr(guard.requests, "get", request)
    assert guard.blogger_daily_gate("123", "test", now=datetime(2026, 9, 9, 16, tzinfo=timezone.utc)) == "daily_limit_reached"
    assert request.call_args.kwargs["params"]["startDate"] == "2026-09-10T00:00:00+09:00"

def test_inventory_error_never_allows_write(monkeypatch):
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError()
    monkeypatch.setattr(guard.requests, "get", Mock(return_value=response))
    with pytest.raises(requests.HTTPError):
        guard.blogger_daily_gate("123", "test")

def test_held_destination_and_missing_token_do_not_call_api(monkeypatch):
    request = Mock()
    monkeypatch.setattr(guard.requests, "get", request)
    assert guard.blogger_daily_gate(guard.HELD_BLOGGER_ID, "test")
    assert guard.blogger_daily_gate("123", "")
    request.assert_not_called()
