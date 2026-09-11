import json

import pytest

from automation_hub.blogger_search_description import build_search_description, validate_search_description
from scripts.build_blogger_search_description_bundle import build_bundle


def test_generated_descriptions_are_valid_and_unique():
    values = [
        build_search_description(title=f"Unique title {i}", topic=f"Topic {i}", language="en")
        for i in range(33)
    ]
    assert len(set(values)) == 33
    assert all(100 <= len(value) <= 120 for value in values)


def test_empty_or_out_of_range_description_fails():
    for value in ("", "short", "x" * 121):
        with pytest.raises(ValueError):
            validate_search_description(value)


def test_bundle_has_33_ui_only_records(tmp_path):
    profiles = json.loads((__import__("pathlib").Path(__file__).resolve().parents[1] / "config/content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    rows = [{"site": p["site_key"], "post_id": str(i + 1000), "url": f"https://example.test/{i}", "title": f"Title {i}"} for i, p in enumerate(profiles)]
    source = tmp_path / "results.json"; source.write_text(json.dumps({"results": rows}), encoding="utf-8")
    bundle = build_bundle(source)
    assert bundle["count"] == 33
    assert bundle["api_persistence_claimed"] is False
    assert all(row["persistence"] == "UI_SAVE_REQUIRED_NOT_EXPOSED_BY_BLOGGER_V3" for row in bundle["records"])
