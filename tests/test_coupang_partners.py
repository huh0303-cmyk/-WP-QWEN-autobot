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


def test_shared_global_pool_is_available_to_every_site(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(cp, "ROOT", tmp_path)
    catalog = tmp_path / "data" / "affiliate" / "global-coupang-product-pool.json"
    catalog.parent.mkdir(parents=True)
    catalog.write_text(json.dumps({"products": [{
        "title": f"공통 상품 {i}",
        "affiliate_url": f"https://link.coupang.com/a/shared{i:02d}",
        "image_url": f"https://image{i}.coupangcdn.com/image/affiliate/banner/shared{i}.jpg",
        "category": "k_health",
        "price_krw": 25000,
        "affiliate_confirmed": True
    } for i in range(10)]}, ensure_ascii=False), encoding="utf-8")
    assert len(cp.load_candidates("wp_jobkorea365")) == 10
    assert len(cp.load_candidates("wp_ktrip365")) == 10

def test_global_categories_are_classified():
    assert cp._category({"category": "k_electronics", "search_text": "노트북"}) == "k_electronics"
    assert cp._category({"category": "korea_travel", "search_text": "서울 여행 패키지"}) == "korea_travel"
    assert cp._category({"category": "korea_hotels", "search_text": "서울 호텔"}) == "korea_hotels"

def test_compact_cards_use_five_desktop_columns(monkeypatch):
    monkeypatch.setattr(cp, "load_candidates", lambda site_id="": fake_pool(12))
    monkeypatch.setattr(cp, "load_header_buttons", lambda site_id="": {
        "buttons": [
            {"provider": "coupang_partners", "affiliate_url": "https://example.com/c", "label": "Coupang"},
            {"provider": "olive_young_global", "affiliate_url": "https://example.com/o", "label": "Olive Young", "verified": True},
            {"provider": "trip_com", "affiliate_url": "https://example.com/t", "label": "Trip.com"}
        ],
        "trip_com_categories": [
            {"key": "hotels", "affiliate_url": "https://example.com/h", "label": "Hotels", "verified": True},
            {"key": "flights", "affiliate_url": "https://example.com/f", "label": "Flights", "verified": True},
            {"key": "tours_and_packages", "affiliate_url": "https://example.com/p", "label": "Tours", "verified": True}
        ]
    })
    footer = cp.render_footer("Article", "Body", "testsite", "ko")
    assert "repeat(5,minmax(0,1fr))" in footer
    assert "함께 살펴볼 추천 상품" in footer
    assert "쿠팡에서 확인하기" in footer
