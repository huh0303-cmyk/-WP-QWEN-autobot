import sys
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
import stock_image_provider as stock
import replicate_image_provider as gateway


def candidate(description="Seoul skyline at night", provider="Pexels"):
    return {"id":"1", "description":description, "url":"https://images.pexels.com/photos/1/a.jpeg",
            "source":"https://www.pexels.com/photo/1", "author":"Test", "width":1600, "height":900}


def test_topic_requires_all_keywords():
    assert stock.matches("Seoul skyline", "Seoul skyline in evening")
    assert not stock.matches("Seoul skyline", "New York skyline")
    assert not stock.matches("Samsung Galaxy Fold", "a mobile phone")
    assert not stock.matches("", "Seoul")


def test_free_match_prevents_paid_call(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("STOCK_IMAGES_ENABLED", "true")
    monkeypatch.setenv("PEXELS_API_KEY", "test")
    with patch.object(stock, "_search", return_value=[candidate()]), patch("stable_image_hosting.host_permanently", return_value="https://raw.githubusercontent.com/r/p/main/photo.jpg"), patch.object(gateway, "_create_prediction") as paid:
        url=gateway.generate_image_url("Seoul skyline")
        assert url.startswith("https://raw.githubusercontent.com/")
        assert "Pexels" in stock.credit_html(url)
        assert "License" in stock.credit_html(url)
        paid.assert_not_called()


def test_irrelevant_goes_to_next_provider(monkeypatch,tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("STOCK_IMAGES_ENABLED","true")
    monkeypatch.setenv("PEXELS_API_KEY","test")
    monkeypatch.setenv("PIXABAY_KEY","test")
    with patch.object(stock,"_search",return_value=[candidate("New York skyline")]) as search, patch("stable_image_hosting.host_permanently") as host:
        assert stock.find_stock_image("Seoul skyline") is None
        assert [c.args[0] for c in search.call_args_list] == ["Pexels","Pixabay"]
        host.assert_not_called()


def test_event_stock_not_used_as_evidence(monkeypatch):
    monkeypatch.setenv("STOCK_IMAGES_ENABLED","true")
    with patch.object(stock,"_search") as search:
        assert stock.find_stock_image("Iran attack", "NEWS ILLUSTRATION ONLY") is None
        search.assert_not_called()


def test_cache_prevents_repeat_search(monkeypatch,tmp_path):
    monkeypatch.setattr(stock,"CACHE",tmp_path)
    response=Mock(); response.json.return_value={"photos":[]}
    with patch.object(stock.requests,"get",return_value=response) as get:
        assert stock._search("Pexels","Seoul skyline","key") == []
        assert stock._search("Pexels","Seoul skyline","key") == []
        assert get.call_count == 1


def test_unavailable_stock_keeps_sdxl_flux_order(monkeypatch):
    monkeypatch.setenv("STOCK_IMAGES_ENABLED","true")
    gateway._prompt_cache.clear(); gateway._attempted_prompts.clear()
    with patch.object(stock,"find_stock_image",return_value=None), patch.object(gateway,"_token",return_value="test"), patch.object(gateway,"_create_prediction",return_value={"status":"failed"}) as paid:
        assert gateway.generate_image_url("unmatched subject") is None
        assert [c.args[0] for c in paid.call_args_list] == list(gateway.ALLOWED_MODELS)
