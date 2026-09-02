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
from control_center.app import _site_rows, compact_category, get_youtube_data, wordpress_cadence
from control_center.keywords import weekly_suggestions
from control_center.states import QUALITY_PASSED, WP_DRAFTED
from control_center.wordpress import DraftResult
from control_center.models import DEFAULT_IMAGE_MODEL, DEFAULT_TEXT_MODEL, IMAGE_MODELS


def test_control_room_uses_one_daily_post_for_every_regular_wordpress_site():
    site = type("Site", (), {"content_type": "blog"})()
    assert wordpress_cadence(site) == {
        "daily_min": 1,
        "daily_max": 1,
        "weekly_min": 7,
        "weekly_max": 7,
        "label": "하루 1포스팅 · 주 7포스팅",
        "kind": "blog",
    }


def test_control_room_keeps_newsroom_rss_exception():
    site = type("Site", (), {"content_type": "news_ko"})()
    assert wordpress_cadence(site) == {
        "daily_min": 3,
        "daily_max": 10,
        "weekly_min": None,
        "weekly_max": None,
        "label": "RSS 하루 3~10회",
        "kind": "newsroom",
    }


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


def test_pwa_has_per_target_buttons_for_all_draft_only_modules():
    template = (Path(__file__).resolve().parents[1] / "control_center" / "templates" / "index.html").read_text(encoding="utf-8")
    assert "Blogspot 비공개 초안 생성" in template
    assert "이 사이트 비공개 초안 생성" in template
    assert "이 채널 비공개 업로드 시작" in template
    assert 'name="site_id" value="{{ blog.site_id }}"' in template
    assert 'name="channel_key" value="{{ channel.channel_key }}"' in template
    assert 'id="review-queue"' in template
    assert "관리자에서 초안 검토·발행" in template
    assert "YouTube Studio에서 검토·공개" in template


def test_blogspot_dashboard_uses_green_connection_and_compact_categories():
    template = (Path(__file__).resolve().parents[1] / "control_center" / "templates" / "index.html").read_text(encoding="utf-8")
    assert "연결됨" in template
    assert "blog.official_categories[:8]" in template
    assert compact_category("international students") == "intl students"
    assert compact_category("A category name that is unnecessarily long", 16).endswith("…")
    assert "당일 방문자 내림차순" in template
    assert "오늘 {{ loop.index }}위" in template


def test_locked_default_content_and_image_engines():
    assert DEFAULT_TEXT_MODEL == "gpt-5-mini"
    assert DEFAULT_IMAGE_MODEL == "bytedance/sdxl-lightning-4step"
    assert list(IMAGE_MODELS) == [
        "none",
        "bytedance/sdxl-lightning-4step",
        "black-forest-labs/flux-schnell",
    ]


def test_wordpress_cards_are_ranked_by_daily_traffic():
    rows, _ = _site_rows(load_wordpress_sites())
    daily = [row["today_visitors"] for row in rows if row["today_visitors"] is not None]
    assert daily == sorted(daily, reverse=True)


def test_wordpress_kpis_appear_before_site_metadata():
    template = (Path(__file__).resolve().parents[1] / "control_center" / "templates" / "index.html").read_text(encoding="utf-8")
    wordpress = template.index("{% for site in sites %}")
    kpis = template.index("당일 방문자(어제 대비)", wordpress)
    category = template.index("사이트 분야:", wordpress)
    persona = template.index("페르소나:", wordpress)
    assert wordpress < kpis < category < persona


def test_review_queue_is_visible_directly_in_control_room():
    template = (Path(__file__).resolve().parents[1] / "control_center" / "templates" / "index.html").read_text(encoding="utf-8")
    assert "승인대기 글 목록" in template
    assert "review_items" in template
    assert "글 검토·승인 →" in template


def test_all_wordpress_drafts_require_rankmath_focus_keyword():
    publisher = (Path(__file__).resolve().parents[1] / "control_center" / "wordpress.py").read_text(encoding="utf-8")
    direct_writer = (Path(__file__).resolve().parents[1] / "scripts" / "auto_write_and_draft.py").read_text(encoding="utf-8")
    assert '"rank_math_focus_keyword": keyword.strip()' in publisher
    assert '"rank_math_focus_keyword": focus_keyword' in direct_writer
    assert "focus keyword is required" in direct_writer


def test_connection_badges_do_not_overstate_metrics_connectivity():
    template = (Path(__file__).resolve().parents[1] / "control_center" / "templates" / "index.html").read_text(encoding="utf-8")
    assert "Blogger 발행 ID 등록" in template
    assert "방문자·색인 연결 상태가 아니라" in template
    assert "방문자·Google 색인이 아니라 공개 RSS 피드 연결 상태" in template


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
    assert score >= 70, failures


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
