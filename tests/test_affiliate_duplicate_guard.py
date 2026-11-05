import automation_hub.coupang_partners as cp


def test_legacy_one_product_module_is_removed_but_article_content_is_kept():
    article = (
        '<p>Article text stays.</p>'
        '<figure><img src="https://site.example/article.jpg"></figure>'
        '<div class="affiliate-recommendation"><p>Disclosure</p>'
        '<div><a href="https://link.coupang.com/a/abc123">'
        '<img src="https://site.example/product.jpg" alt="Omega-3"></a></div>'
        '</div>'
    )
    cleaned = cp._remove_legacy_single_product_modules(article)
    assert "Article text stays." in cleaned
    assert "article.jpg" in cleaned
    assert "affiliate-recommendation" not in cleaned
    assert "product.jpg" not in cleaned


def test_unrelated_div_is_not_removed():
    article = '<div class="related-products"><img src="https://site.example/x.jpg"></div>'
    assert cp._remove_legacy_single_product_modules(article) == article


def test_existing_tracked_product_is_not_selected_again(monkeypatch):
    pool = [
        {
            "url": f"https://link.coupang.com/a/test{i:02d}",
            "title": f"상품 {i}",
            "image": f"https://image{i}.coupangcdn.com/image/affiliate/banner/test{i}.jpg",
            "source": "fixture",
            "price_krw": 50000,
            "category": "korea_lifestyle_hot_items",
            "search_text": f"상품 생활용품 {i}",
        }
        for i in range(11)
    ]
    monkeypatch.setattr(cp, "load_candidates", lambda site_id="": pool)
    body = '<a href="https://link.coupang.com/a/test00">already placed</a>'
    selected = cp.select_products("생활용품", body, "testsite")
    assert len(selected) == 10
    assert "https://link.coupang.com/a/test00" not in {p["url"] for p in selected}


def test_duplicate_image_asset_is_not_selected_twice(monkeypatch):
    pool = [
        {
            "url": f"https://link.coupang.com/a/test{i:02d}",
            "title": f"상품 {i}",
            "image": f"https://image{i}.coupangcdn.com/image/affiliate/banner/test{i}.jpg",
            "source": "fixture",
            "price_krw": 50000,
            "category": "korea_lifestyle_hot_items",
            "search_text": f"상품 생활용품 {i}",
        }
        for i in range(11)
    ]
    pool[1]["image"] = pool[0]["image"]
    monkeypatch.setattr(cp, "load_candidates", lambda site_id="": pool)
    selected = cp.select_products("생활용품", "", "testsite")
    assert len(selected) == 10
    assert len({cp._canonical_asset_url(p["image"]) for p in selected}) == 10
