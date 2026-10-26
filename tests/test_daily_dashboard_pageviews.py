from scripts import daily_dashboard as dashboard


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


def test_scrape_total_pageviews_widget(monkeypatch):
    html = "<h2>Total Pageviews</h2><table><tr><td>0</td><td>20</td></tr><tr><td>1</td><td>84</td></tr></table><h2>Archive</h2>"
    monkeypatch.setattr(dashboard.requests, "get", lambda *args, **kwargs: FakeResponse(html))
    assert dashboard.scrape_widget_pageviews("https://jobkorea365.blogspot.com") == 84


def test_scrape_total_pageviews_handles_commas(monkeypatch):
    html = "Total Pageviews <span>1,284</span> Archive"
    monkeypatch.setattr(dashboard.requests, "get", lambda *args, **kwargs: FakeResponse(html))
    assert dashboard.scrape_widget_pageviews("https://example.blogspot.com") == 1284
