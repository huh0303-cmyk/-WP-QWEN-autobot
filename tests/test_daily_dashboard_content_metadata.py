from scripts import daily_dashboard as dashboard


class FakeFeedResponse:
    ok = True

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def test_blogspot_content_metadata_parses_published_object(monkeypatch):
    payload = {
        "feed": {
            "openSearch$totalResults": {"$t": "84"},
            "entry": [
                {"published": {"$t": "2026-11-06T05:30:12.581-08:00"}}
            ],
        }
    }
    monkeypatch.setattr(
        dashboard.requests,
        "get",
        lambda *args, **kwargs: FakeFeedResponse(payload),
    )

    result = dashboard.content_metadata(
        "https://studyinkorea365.blogspot.com", "blogspot"
    )

    assert result == {
        "content_count": 84,
        "latest_publish_date": "2026-11-06",
    }


def test_blogspot_content_metadata_handles_empty_feed(monkeypatch):
    payload = {
        "feed": {
            "openSearch$totalResults": {"$t": "0"},
            "entry": [],
        }
    }
    monkeypatch.setattr(
        dashboard.requests,
        "get",
        lambda *args, **kwargs: FakeFeedResponse(payload),
    )

    result = dashboard.content_metadata(
        "https://empty.example.blogspot.com", "blogspot"
    )

    assert result == {
        "content_count": 0,
        "latest_publish_date": None,
    }
