import pytest
import automation_hub.coupang_partners as cp

def fake_pool(count=10):
    return [
        {
            "url": f"https://link.coupang.com/a/test{i:02d}",
            "title": f"추천 상품 {i}",
            "image": f"https://image{i}.coupangcdn.com/image/affiliate/banner/test{i}.jpg",
            "source": "fixture",
            "price_krw": 19000 + i * 1000,
            "category": "korea_lifestyle_hot_items",
            "search_text": f"추천 상품 생활용품 {i}",
        }
        for i in range(count)
    ]

def test_exactly_ten_unique_verified_cards_are_selected(monkeypatch):
    monkeypatch.setattr(cp, "load_candidates", lambda site_id="": fake_pool(12))
    items = cp.select_products("한국 생활용품 추천", "생활용품 추천 상품", "testsite")
    assert len(items) == 10
    assert len({x["url"] for x in items}) == 10

def test_fewer_than_ten_products_blocks_footer(monkeypatch):
    monkeypatch.setattr(cp, "load_candidates", lambda site_id="": fake_pool(9))
    with pytest.raises(RuntimeError, match="exactly 10"):
        cp.render_footer("Article", "Body", "testsite", "en")

def test_footer_replaces_own_marker_without_duplication(monkeypatch):
    monkeypatch.setattr(cp, "load_candidates", lambda site_id="": fake_pool(10))
    original = "<p>Article</p>" + cp.START + "old" + cp.END
    updated = cp.apply_footer(original, "Vitamin D", "testsite", "ko")
    assert updated.count(cp.START) == 1
    assert updated.count(cp.END) == 1
    assert "<p>Article</p>" in updated
    assert updated.count("https://link.coupang.com/a/test") == 20

def test_unknown_legacy_affiliate_markup_is_preserved(monkeypatch):
    monkeypatch.setattr(cp, "load_candidates", lambda site_id="": fake_pool(10))
    original = '<p><a href="https://link.coupang.com/a/example">old</a></p>'
    assert cp.apply_footer(original, "Article", "testsite") == original
