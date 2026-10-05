import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import blogger_free_image as b


def test_relevance_requires_shared_word():
    assert b._relevant("Seoul palace autumn", "Gyeongbokgung palace in autumn")
    assert not b._relevant("Seoul palace autumn", "a bowl of soup")


def test_insert_after_first_paragraph_with_alt():
    out = b.insert_image("<p>one</p><p>two</p>", {"url": "https://images.pexels.com/x.jpg"}, 'Title "q"')
    assert out.index("<img") > out.index("one") and out.index("<img") < out.index("two")
    assert 'alt="Title &quot;q&quot;"' in out


def test_fallback_order_and_none(monkeypatch):
    calls = []
    for name in ("_pexels", "_pixabay", "_wikimedia", "_ai_free"):
        monkeypatch.setattr(b, name, (lambda n: lambda q: calls.append(n))(name))
    assert b.pick_image("Seoul palace autumn") is None
    assert calls == ["_pexels", "_pixabay", "_wikimedia", "_ai_free"]


def test_exception_falls_through(monkeypatch):
    def boom(q): raise RuntimeError("x")
    monkeypatch.setattr(b, "_pexels", boom)
    monkeypatch.setattr(b, "_pixabay", lambda q: None)
    monkeypatch.setattr(b, "_wikimedia", lambda q: {"url": "https://upload.wikimedia.org/a.jpg", "provider": "Wikimedia", "id": "1", "desc": "d"})
    assert b.pick_image("Seoul palace autumn")["provider"] == "Wikimedia"


def test_empty_query_none():
    assert b.pick_image("") is None
