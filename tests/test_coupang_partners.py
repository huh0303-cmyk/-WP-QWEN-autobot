import pytest
import automation_hub.coupang_partners as cp

def fake_pool(count=10):
    rows = []
    for i in range(count):
        category = "health" if i < (count + 1) // 2 else "beauty"
        rows.append({
            "url": f"https://link.coupang.com/a/test{i:02d}",
            "title": f"추천 상품 {i}",
            "image": f"https://image{i}.coupangcdn.com/image/affiliate/banner/test{i}.jpg",
            "source": "fixture",
            "price_krw": 19000 + i * 1000,
            "category": category,
            "search_text": f"추천 상품 건강기능식품 스킨케어 {i}",
        })
    return rows

def test_exactly_ten_unique_cards_are_selected(monkeypatch):
    monkeypatch.setattr(cp, "load_candidates", lambda site_id="": fake_pool(10))
    items = cp.select_products("건강과 스킨케어", "건강기능식품 스킨케어", "testsite")
    assert len(items) == 10
    assert sum(1 for x in items if cp._category(x) == "health_functional_foods") == 5
    assert sum(1 for x in items if cp._category(x) == "k_beauty_skincare") == 5
    assert len({x["url"] for x in items}) == 10

def test_fewer_than_five_in_category_blocks_selection(monkeypatch):
    monkeypatch.setattr(cp, "load_candidates", lambda site_id="": fake_pool(9))
    with pytest.raises(ValueError, match="affiliate_catalog_requires_five_k_beauty_skincare"):
        cp.select_products("Article", "Body", "testsite")

def test_footer_replaces_own_marker_without_duplication(monkeypatch):
    monkeypatch.setattr(cp, "load_candidates", lambda site_id="": fake_pool(10))
    monkeypatch.setattr(cp, "load_header_buttons", lambda site_id="": {
        "buttons": [
            {"provider": "coupang_partners", "affiliate_url": "https://example.com/coupang", "label": "Coupang"},
            {"provider": "trip_com", "affiliate_url": "https://example.com/trip", "label": "Trip.com"},
            {"provider": "olive_young_global", "affiliate_url": "https://example.com/olive", "label": "Olive Young", "verified": True},
        ],
        "trip_com_categories": [],
    })
    original = "<p>Article</p>" + cp.START + "old" + cp.END
    updated = cp.apply_footer(original, "Vitamin D", "testsite", "ko")
    assert updated.count(cp.START) == 1
    assert updated.count(cp.END) == 1
    assert "<p>Article</p>" in updated
    assert updated.count("https://link.coupang.com/a/test") == 20
    assert updated.index("Coupang") < updated.index("Trip.com") < updated.index("Olive Young")
    assert "24 hours" in updated

def test_unknown_legacy_affiliate_markup_is_preserved(monkeypatch):
    monkeypatch.setattr(cp, "load_candidates", lambda site_id="": fake_pool(10))
    monkeypatch.setattr(cp, "load_header_buttons", lambda site_id="": None)
    original = '<p><a href="https://link.coupang.com/a/example">old</a></p>'
    with pytest.raises(RuntimeError, match="Affiliate header requires"):
        cp.apply_footer(original, "Article", "testsite")
