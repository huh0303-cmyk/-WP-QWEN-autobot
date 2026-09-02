from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from control_center.db import Store
from control_center.quality import score_article
from control_center.registry import load_wordpress_sites
from control_center.service import ControlCenter
from control_center.app import _site_rows, get_youtube_data
from control_center.keywords import weekly_suggestions
from control_center.states import QUALITY_PASSED, WP_DRAFTED
from control_center.wordpress import DraftResult
from control_center.models import DEFAULT_IMAGE_MODEL, DEFAULT_TEXT_MODEL, IMAGE_MODELS


GOOD_ARTICLE = {
    "title": "Korea Job Seeker Visa Requirements and Practical Checks",
    "meta_description": "Check Korea job seeker visa requirements, official verification steps, documents, timing, and practical cautions before applying.",
    "content_html": """
      <p>Korea job seeker visa requirements should be checked against the official immigration guidance as of September 2026.</p>
      <p>Rules can change, so verify the current procedure with Korea Immigration Service. This overview is not legal advice.</p>
      <h2>Start with your eligibility</h2><p>{body}</p>
      <h2>Prepare the required records</h2><p>{body}</p>
      <h2>Verify before submitting</h2><p>{body}</p>
    """.format(body="Applicants should compare their situation with the official requirements and prepare consistent records. " * 24),
    "labels": ["Korea visa", "job seeker", "immigration", "application documents"],
    "image_queries": [],
}


def test_registry_has_exactly_27_wordpress_sites():
    sites = load_wordpress_sites()
    assert len(sites) == 27
    assert len({site.site_id for site in sites}) == 27


def test_pwa_has_ten_youtube_rooms_in_two_groups():
    channels = get_youtube_data()
    assert len(channels) == 10
    assert sum(row["group"] == "PLAYLIST" for row in channels) == 5
    assert sum(row["group"] == "KNOWLEDGE" for row in channels) == 5
    assert all(row["sheet_controlled"] for row in channels)


def test_locked_default_content_and_image_engines():
    assert DEFAULT_TEXT_MODEL == "gemini-2.5-flash"
    assert DEFAULT_IMAGE_MODEL == "black-forest-labs/flux-schnell"
    assert list(IMAGE_MODELS) == [
        "none",
        "black-forest-labs/flux-schnell",
        "bytedance/sdxl-lightning-4step",
        "jyoung105/sdxl-turbo",
    ]


def test_khealth_is_always_first_in_traffic_order():
    rows, _ = _site_rows(load_wordpress_sites())
    assert rows[0]["domain"] == "k-health365.com"


def test_job_creation_is_idempotent():
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "db.sqlite3")
        first = store.create_job(site_id="wp_kvisa365", keyword="Korea visa requirements")
        second = store.create_job(site_id="wp_kvisa365", keyword="  korea VISA requirements ")
        assert first["id"] == second["id"]


def test_job_persists_selected_models():
    with tempfile.TemporaryDirectory() as tmp:
        center = ControlCenter(Store(Path(tmp) / "db.sqlite3"))
        job = center.create(
            "wp_kvisa365", "Korea visa renewal checklist",
            "gemini-2.5-flash", "bytedance/sdxl-lightning-4step",
        )
        assert job["text_model"] == "gemini-2.5-flash"
        assert job["image_model"] == "bytedance/sdxl-lightning-4step"


def test_quality_gate_accepts_compliant_article():
    score, failures = score_article(GOOD_ARTICLE, keyword="Korea job seeker visa requirements", target_chars=2400)
    assert score >= 75, failures


def test_service_never_publishes_and_recovers_same_draft():
    with tempfile.TemporaryDirectory() as tmp:
        center = ControlCenter(Store(Path(tmp) / "db.sqlite3"))
        job = center.create("wp_kvisa365", "Korea job seeker visa requirements")
        with patch("control_center.service.generate_article", return_value=GOOD_ARTICLE):
            generated = center.generate(job["id"])
        assert generated["state"] == QUALITY_PASSED
        with patch("control_center.service.create_draft", return_value=DraftResult("123", "https://example.test/edit", "https://example.test/preview")) as creator:
            drafted = center.draft(job["id"])
        assert drafted["state"] == WP_DRAFTED
        assert drafted["wp_post_id"] == "123"
        payload = creator.call_args.args[0]
        assert payload.site_id == "wp_kvisa365"


def test_store_rejects_unsafe_publish_transition():
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "db.sqlite3")
        job = store.create_job(site_id="wp_kvisa365", keyword="Korea visa requirements")
        with pytest.raises(ValueError):
            store.transition(job["id"], "PUBLISHED")


def test_weekly_keyword_suggestions_are_stable_and_bounded():
    first = weekly_suggestions("korea365.org")
    second = weekly_suggestions("korea365.org")
    assert first == second
    assert 0 < len(first) <= 5
    assert all(item.keyword for item in first)
