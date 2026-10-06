import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import image_guarantee as g


def test_card_is_png_and_never_fails():
    data = g.make_card_png("한글날 사흘 주말 여행자보험 체크리스트", "한국보험정보")
    assert data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) > 5000
    assert g.make_card_png("", "")[:4] == b"\x89PNG"


def test_ensure_image_falls_through_to_card(monkeypatch):
    import blogger_free_image as free
    monkeypatch.setattr(free, "pick_image", lambda *a, **k: None)
    monkeypatch.setattr(g, "_openverse", lambda q: None)
    out = g.ensure_image("보험금 청구", queries=["insurance claim"], theme="보험", host=False)
    assert out["provider"] == "GeneratedCard" and out["png"][:4] == b"\x89PNG"


def test_openverse_used_before_card(monkeypatch):
    import blogger_free_image as free
    monkeypatch.setattr(free, "pick_image", lambda *a, **k: None)
    monkeypatch.setattr(g, "_openverse", lambda q: {"url": "https://x/y.jpg", "provider": "Openverse", "id": "1"})
    out = g.ensure_image("t", queries=["insurance"], host=False)
    assert out["provider"] == "Openverse"
