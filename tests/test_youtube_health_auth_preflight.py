import pytest

from scripts import youtube_health_auth_preflight as check


class Response:
    def __init__(self, body):
        self.body = body
        self.ok = True

    def json(self):
        return self.body


@pytest.mark.parametrize("scope,channel,ok", [
    ("https://www.googleapis.com/auth/youtube.upload", "UC-expected", True),
    ("https://www.googleapis.com/auth/youtube.upload", "UC-other", False),
    ("https://www.googleapis.com/auth/youtube.readonly", "UC-expected", False),
])
def test_requires_write_scope_and_exact_channel(monkeypatch, scope, channel, ok):
    for name, value in {
        "PROFILE": "health_usa", "EXPECTED_CHANNEL_ID": "UC-expected",
        "CLIENT_ID": "test", "CLIENT_SECRET": "test", "REFRESH_TOKEN": "test",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(check.requests, "post", lambda *a, **kw: Response({
        "access_token": "test", "scope": scope,
    }))
    monkeypatch.setattr(check.requests, "get", lambda *a, **kw: Response({
        "items": [{"id": channel}],
    }))
    if ok:
        check.main()
    else:
        with pytest.raises(RuntimeError):
            check.main()
