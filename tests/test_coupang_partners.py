from automation_hub.coupang_partners import apply_footer, select_products, START, END

def test_soft_category_policy_selects_unique_verified_products():
    items = select_products("Vitamin D and daily skincare routine", "vitamin D, toner, sunscreen, omega-3, skin hydration")
    assert len(items) == 10
    assert len({x["url"] for x in items}) == len(items)
    assert all(x["url"].startswith("https://link.coupang.com/") for x in items)
    assert all(x["image"].startswith("https://") for x in items)

def test_footer_replaces_own_marker_without_duplication():
    original = "<p>Article</p>" + START + "old" + END
    updated = apply_footer(original, "Vitamin D", "wp_khealth365", "ko")
    assert updated.count(START) == 1
    assert updated.count(END) == 1
    assert "<p>Article</p>" in updated

def test_unknown_legacy_affiliate_markup_is_preserved():
    original = '<p><a href="https://link.coupang.com/a/example">old</a></p>'
    assert apply_footer(original, "Article") == original
