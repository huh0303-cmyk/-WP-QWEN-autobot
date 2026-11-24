import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import wp_repair_posts as repair

GOOD_HTML = ('<p>How to hire E-9 workers. Checked on 25 November 2026.</p>'
             '<a href="https://www.moel.go.kr/a">a</a><a href="https://www.work24.go.kr/b">b</a>')
GOOD = {"id": 1, "title": "How to Hire E-9 Workers: Employer Steps and Checks", "slug": "how-to-hire-e-9-workers",
        "meta_description": "x" * 140, "focus_keyword": "Hire E-9 Workers", "tags": ["a", "b", "c"]}


def test_every_committed_manifest_is_valid():
    for manifest in (ROOT / "data" / "repairs").glob("*/manifest.json"):
        repair.load_manifest(manifest.parent)


def test_good_post_passes():
    assert repair.validate_post(GOOD, GOOD_HTML) == []


@pytest.mark.parametrize("change,fragment", [
    ({"title": "E-9 Visa Ceiling Adjustments Prompt Overhaul of Employer Application Procedures in Manufacturing"}, "title must be"),
    ({"meta_description": "too short"}, "meta description"),
    ({"focus_keyword": "something else"}, "focus keyword"),
    ({"slug": "Bad Slug"}, "slug"),
    ({"tags": ["a"]}, "tags"),
])
def test_bad_fields_are_reported(change, fragment):
    problems = repair.validate_post({**GOOD, **change}, GOOD_HTML)
    assert any(fragment in p for p in problems), problems


def test_missing_official_sources_and_date_are_reported():
    problems = repair.validate_post(GOOD, "<p>Hire E-9 workers.</p><a href='https://example.com/x'>x</a>")
    assert any("official" in p for p in problems) and any("checked on" in p for p in problems)
