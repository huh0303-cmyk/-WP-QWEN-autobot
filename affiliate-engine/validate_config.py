import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
policy = json.loads((root / "config/affiliate_distribution_policy.json").read_text(encoding="utf-8-sig"))
shared = json.loads((root / "config/affiliate/london-shared-policy.json").read_text(encoding="utf-8-sig"))
routing = json.loads((root / "affiliate-engine/config/affiliate-routing.json").read_text(encoding="utf-8-sig"))

expected = {"health_functional_foods": 5, "k_beauty_skincare": 5}
expected_buttons = ["coupang_partners", "olive_young_global", "trip_com"]
expected_colors = {"coupang_partners": "orange", "olive_young_global": "green", "trip_com": "blue"}

assert policy["policy_version"] == "7.0.0"
assert policy["per_article_total"] == 10
assert policy["provider_allocation"] == {"coupang_partners": 10}
assert len(policy["required_slots"]) == 10
assert {k: sum(1 for x in policy["required_slots"] if x["category"] == k) for k in expected} == expected
assert {k: sum(1 for x in routing["required_slots"] if x["category"] == k) for k in expected} == expected
assert routing["version"] == "7.0.0"
assert routing["selection_policy"]["pool_category_counts"] == expected
assert routing["selection_policy"]["per_article_category_counts"] == expected
assert routing["selection_policy"]["randomize_per_article"] is False

# Validate the actual schema: shared policy v9 uses footer_logo_banners,
# not the removed legacy header_buttons property.
assert shared["version"] == 9
assert shared["footer_logo_banners"] == expected_buttons
assert shared["product_cards"]["count"] == 10
assert shared["product_cards"]["provider_count"] == {"coupang_partners": 10}
assert shared["product_cards"]["category_count"] == expected

# Top-button declaration order is not the visual order; header_design is authoritative.
assert {x["provider"] for x in routing["top_buttons"]} == set(expected_buttons)
assert {x["provider"]: x["brand_color"] for x in routing["top_buttons"]} == expected_colors
assert routing["header_design"]["order"] == expected_buttons
assert policy["header_design"]["order"] == expected_buttons
assert policy["header_design"]["no_extra_trip_category_text_link_row_below_buttons"] is True
assert policy["header_design"]["official_logo_image_required"] is True
assert policy["article_placement"]["location"] == "absolute_article_footer_only"
assert policy["article_placement"]["sequence"][0] == "three_official_company_logo_banners_in_one_horizontal_row"
assert routing["affiliate_programs"]["agoda"]["enabled"] is False
assert shared["guardrails"]["agoda_enabled"] is False

print("AFFILIATE_CONFIG_VALID=PASS")
print("POLICY=v7.0.0_LOCKED; SHARED_POLICY=v9")
print("HEADER=COUPANG_ORANGE+OLIVEYOUNG_GREEN+TRIPCOM_BLUE")
print("PER_ARTICLE=HEALTH5+KBEAUTY_SKINCARE5")
print("UP_TO_10_VERIFIED_PRODUCTS=REQUIRED")
print("AGODA=DISABLED")
