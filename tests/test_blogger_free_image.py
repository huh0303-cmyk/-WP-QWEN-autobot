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
    for name in ("_pexels", "_pixabay", "_wikimedia"):
        monkeypatch.setattr(b, name, (lambda n: lambda q: calls.append(n))(name))
    assert b.pick_image("Seoul palace autumn") is None
    # Pexels/Pixabay are shuffled; Wikimedia is always last; no AI source exists any more.
    assert set(calls[:2]) == {"_pexels", "_pixabay"} and calls[2] == "_wikimedia" and len(calls) == 3


def test_no_pollinations_anywhere():
    assert not hasattr(b, "_ai_free")


def test_insert_image_is_square():
    out = b.insert_image("<p>one</p>", {"url": "https://images.pexels.com/x.jpg"}, "t")
    assert 'width="1080" height="1080"' in out


def test_pexels_url_is_1x1_crop():
    url = b._pexels_square({"src": {"original": "https://images.pexels.com/photos/1/pexels-photo-1.jpeg"}})
    assert "fit=crop" in url and "w=1080" in url and "h=1080" in url


def test_square_jpeg_crop():
    import io
    from PIL import Image
    import square_image
    buf = io.BytesIO(); Image.new("RGB", (1600, 900), (10, 20, 30)).save(buf, "JPEG")
    out = Image.open(io.BytesIO(square_image.to_square_jpeg(buf.getvalue())))
    assert out.size == (1080, 1080)


def test_exception_falls_through(monkeypatch):
    def boom(q): raise RuntimeError("x")
    monkeypatch.setattr(b, "_pexels", boom)
    monkeypatch.setattr(b, "_pixabay", lambda q: None)
    monkeypatch.setattr(b, "_wikimedia", lambda q: {"url": "https://upload.wikimedia.org/a.jpg", "provider": "Wikimedia", "id": "1", "desc": "d"})
    assert b.pick_image("Seoul palace autumn")["provider"] == "Wikimedia"


def test_empty_query_none():
    assert b.pick_image("") is None
