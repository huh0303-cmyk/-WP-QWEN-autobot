from scripts import daily_dashboard as dashboard


class FakeFeedResponse:
    ok = True

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FakeRSSResponse:
    ok = True

    def __init__(self, xml):
        self.content = xml.encode("utf-8")


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


def test_tistory_content_metadata_parses_public_rss_date(monkeypatch):
    xml = """<?xml version="1.0"?>
    <rss version="2.0"><channel><item>
      <pubDate>Fri, 23 Oct 2026 19:17:47 +0900</pubDate>
    </item></channel></rss>"""
    calls = []
    monkeypatch.setattr(
        dashboard.requests,
        "get",
        lambda url, **kwargs: (calls.append(url) or FakeRSSResponse(xml)),
    )

    result = dashboard.content_metadata("https://huh0303.tistory.com", "tistory")

    assert calls == ["https://huh0303.tistory.com/rss"]
    assert result == {
        "content_count": None,
        "latest_publish_date": "2026-10-23",
    }


def test_naver_content_metadata_parses_public_rss_date(monkeypatch):
    xml = """<?xml version="1.0"?>
    <rss version="2.0"><channel><item>
      <pubDate>Wed, 07 Oct 2026 10:39:41 +0900</pubDate>
    </item></channel></rss>"""
    calls = []
    monkeypatch.setattr(
        dashboard.requests,
        "get",
        lambda url, **kwargs: (calls.append(url) or FakeRSSResponse(xml)),
    )

    result = dashboard.content_metadata(
        "https://blog.naver.com/health-standard", "naver"
    )

    assert calls == ["https://rss.blog.naver.com/health-standard.xml"]
    assert result == {
        "content_count": None,
        "latest_publish_date": "2026-10-07",
    }
