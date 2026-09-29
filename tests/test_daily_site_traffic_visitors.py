from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import daily_site_traffic  # noqa: E402


def test_footer_visitor_stats_keeps_yesterday_comparison(monkeypatch):
    response = mock.Mock(status_code=200)
    response.json.return_value = {
        "date": "2026-09-29",
        "count": 60,
        "yesterday_count": 115,
        "day_before_yesterday_count": 100,
        "total": 3502,
    }
    monkeypatch.setattr(daily_site_traffic.requests, "get", lambda *args, **kwargs: response)

    result, error = daily_site_traffic.get_footer_visitor_stats("https://kstudy365.com")

    assert error is None
    assert result["yesterday_visitors"] == 115
    assert result["day_before_yesterday_visitors"] == 100
    assert result["yesterday_delta"] == 15
