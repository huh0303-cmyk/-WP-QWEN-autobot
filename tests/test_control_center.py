from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from control_center.db import Store
from control_center.quality import score_article
from control_center.registry import load_wordpress_sites
from control_center.service import ControlCenter
from control_center.app import ADSENSE_BLOGGER_URLS, HIDDEN_BLOGGER_URLS, _dispatch_draft_workflow, _site_rows, app as control_center_app, compact_category, get_review_queue, get_sns_data, get_youtube_data, wordpress_cadence
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


def test_visitor_deploy_uses_current_wordpress_secret_names():
    workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "deploy-visitor-api.yml").read_text(encoding="utf-8")
    from scripts.site_registry import ACTIVE_SITES
    for _, secret_name, _ in ACTIVE_SITES:
        assert f"{secret_name}: ${{{{ secrets.{secret_name} }}}}" in workflow


def test_pwa_has_ten_youtube_rooms_in_two_groups():
    channels = get_youtube_data()
    assert len(channels) == 10
    assert sum(row["group"] == "PLAYLIST" for row in channels) == 5
    assert sum(row["group"] == "KNOWLEDGE" for row in channels) == 5
    assert all(row["sheet_controlled"] for row in channels)
    assert all(row["channel_key"] for row in channels)
    assert all(row["action_ready"] for row in channels)
    assert len({row["channel_key"] for row in channels}) == 10
    assert all(row["official_name"] for row in channels)
    assert all(row["handle"] for row in channels)
    assert all(row["channel_id"].startswith("UC") for row in channels)
    assert all(row["subscriber_count"] is not None for row in channels)
    assert all(row["content_count"] is not None for row in channels)
    assert all(row["created_at"] for row in channels)


def test_youtube_cards_show_official_identity_growth_and_pastel_action():
    template = (Path(__file__).resolve().parents[1] / "control_center" / "templates" / "index.html").read_text(encoding="utf-8")
    assert "{{ channel.official_name }}" in template
    assert "@{{ channel.handle }}" in template
    assert "구독자 수 (증감)" in template
    assert "콘텐츠 수 (증감)" in template
    assert "채널 개설일" in template
    assert "from-sky-200 to-indigo-200" in template
    youtube = template[template.index('<section id="youtube"'):template.index('<section id="sns"')]
    assert "bg-red-700 px-4 text-sm" not in youtube


def test_pwa_has_per_target_buttons_for_all_draft_only_modules():
    template = (Path(__file__).resolve().parents[1] / "control_center" / "templates" / "index.html").read_text(encoding="utf-8")
    assert "키워드보고발행" in template
    assert "바이럴자동발행" in template
    assert "YouTube 콘텐츠 바로 만들기 · 비공개" in template
    assert 'name="site_id" value="{{ blog.site_id }}"' in template
    assert 'name="channel_key" value="{{ channel.channel_key }}"' in template
    assert "{% if site.auth_ready %}" in template
    assert "{% if blog.connected %}" in template
    assert "{% if channel.action_ready %}" in template
    assert 'id="review-queue"' not in template
    assert "완성된 영상은 먼저 비공개로 저장됩니다." in template


def test_sns_cards_do_not_offer_unconnected_publish_actions():
    accounts = get_sns_data()
    assert accounts
    assert all(account["publish_connected"] is False for account in accounts)
    assert all(account["publish_unavailable_reason"] for account in accounts)
    template = (Path(__file__).resolve().parents[1] / "control_center" / "templates" / "index.html").read_text(encoding="utf-8")
    assert "SNS 콘텐츠 바로 올리기 · 연결 없음" in template
    assert "{{ account.publish_unavailable_reason }}" in template


def test_blogspot_cards_use_the_real_automatic_queue_without_manual_source_url():
    # 2026-09-04 CEO: added a second "키워드보고발행" button (chips from the
    # paired WP site's own category pool) alongside the original
    # "바이럴자동발행" auto-research button — so a keyword field is now
    # expected here, but a manual free-text source URL is still gone.
    template = (Path(__file__).resolve().parents[1] / "control_center" / "templates" / "index.html").read_text(encoding="utf-8")
    blogspot = template[template.index('{% for blog in bloggers %}'):template.index('{% endfor %}', template.index('{% for blog in bloggers %}'))]
    assert 'name="selection_mode" value="auto"' in blogspot
    assert 'name="source_wp_url"' not in blogspot
    assert 'name="keyword" class="force-keyword-input"' in blogspot
    assert "의미상 가까운 공개 글만 자동 연결" in template
    assert "맞는 글이 없으면 억지로 연결하지 않습니다." in template


def test_blogspot_public_button_continues_to_exact_platform_publish_job():
    workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "blogger-rewrite.yml").read_text(encoding="utf-8")
    queue = (Path(__file__).resolve().parents[1] / "scripts" / "queue_blogger_rewrite.py").read_text(encoding="utf-8")
    assert "actions: write" in workflow
    assert "steps.queue.outputs.job_id" in workflow
    assert "gh workflow run platform-publish-v2.yml" in workflow
    assert '-f job_id="$QUEUED_JOB_ID"' in workflow
    assert 'output_file.write(f"job_id={job_id}\\n")' in queue


def test_all_sites_show_the_two_publish_actions():
    # 2026-09-04 CEO: "두개 버튼으로 해줘 모든사이트 WP, 블팟, 티스토리까지" —
    # every WP/Blogspot/Tistory card now shows both "키워드보고발행" (chip
    # picked, seen before publishing) and "바이럴자동발행" (blind live
    # cross-media research), not just the two originally special-cased
    # general sites (koreanews365.com/korea365.org) — those two keep a
    # separate backend workflow (RSS-based newsroom publisher) in app.py,
    # but the button UI is now uniform across all sites.
    template = (Path(__file__).resolve().parents[1] / "control_center" / "templates" / "index.html").read_text(encoding="utf-8")
    app_source = (Path(__file__).resolve().parents[1] / "control_center" / "app.py").read_text(encoding="utf-8")
    assert 'registered.url.rstrip("/") == "https://koreanews365.com"' in app_source
    assert template.count("키워드보고발행") >= 3
    assert template.count("바이럴자동발행") >= 3


def test_koreanews_viral_button_dispatches_newsroom_workflow(monkeypatch):
    monkeypatch.delenv("CONTROL_CENTER_USERNAME", raising=False)
    monkeypatch.delenv("CONTROL_CENTER_PASSWORD", raising=False)
    monkeypatch.setenv("CONTROL_CENTER_GITHUB_TOKEN", "test-token")
    client = control_center_app.test_client()
    with patch("control_center.app.requests.post") as dispatch:
        dispatch.return_value.status_code = 204
        response = client.post(
            "/trigger/publish-site-now",
            data={"csrf_token": control_center_app.config["CONTROL_CENTER_CSRF"], "domain": "koreanews365.com"},
        )
    assert response.status_code == 302
    assert dispatch.call_args.args[0].endswith("/newsrooms-daily-publisher.yml/dispatches")
    assert dispatch.call_args.kwargs["json"]["inputs"]["newsroom"] == "koreanews365"


def test_blogspot_automatic_topic_dispatch_does_not_require_a_manual_wp_url(monkeypatch):
    monkeypatch.delenv("CONTROL_CENTER_USERNAME", raising=False)
    monkeypatch.delenv("CONTROL_CENTER_PASSWORD", raising=False)
    client = control_center_app.test_client()
    with patch("control_center.app._queue_draft_trigger", return_value="draft-test"), patch(
        "control_center.app._dispatch_draft_workflow", return_value="https://example.test/workflow"
    ) as dispatch:
        response = client.post(
            "/trigger/draft",
            data={
                "csrf_token": control_center_app.config["CONTROL_CENTER_CSRF"],
                "platform": "blogger",
                "site_id": "blogger_ktrip365",
                "domain": "k-trip365.blogspot.com",
                "selection_mode": "auto",
                "text_model": "gpt-5-mini",
                "image_model": "none",
            },
        )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("#blogspot")
    payload = dispatch.call_args.args[0]
    assert payload["keyword"] == ""
    assert payload["source_wp_url"] is None
    assert payload["selection_mode"] == "auto"


def test_blogspot_automatic_topic_rejects_an_unconnected_target(monkeypatch):
    monkeypatch.delenv("CONTROL_CENTER_USERNAME", raising=False)
    monkeypatch.delenv("CONTROL_CENTER_PASSWORD", raising=False)
    client = control_center_app.test_client()
    with patch("control_center.app._queue_draft_trigger") as queue, patch(
        "control_center.app._dispatch_draft_workflow"
    ) as dispatch:
        response = client.post(
            "/trigger/draft",
            data={
                "csrf_token": control_center_app.config["CONTROL_CENTER_CSRF"],
                "platform": "blogger",
                "site_id": "blogger_not_registered",
                "domain": "not-registered.blogspot.com",
                "selection_mode": "auto",
                "text_model": "gpt-5-mini",
                "image_model": "none",
            },
        )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("#blogspot")
    queue.assert_not_called()
    dispatch.assert_not_called()


def test_blogspot_automatic_topic_uses_the_evidence_backed_rewrite_workflow(monkeypatch):
    monkeypatch.setenv("CONTROL_CENTER_GITHUB_TOKEN", "test-token")
    with patch("control_center.app.requests.post") as dispatch:
        dispatch.return_value.status_code = 204
        workflow_url = _dispatch_draft_workflow({
            "platform": "blogger",
            "site_id": "blogger_ktrip365",
            "selection_mode": "auto",
            "keyword": "",
            "source_wp_url": None,
            "text_model": "gpt-5-mini",
            "image_model": "none",
        })
    assert workflow_url.endswith("/blogger-rewrite.yml")
    assert dispatch.call_args.args[0].endswith("/blogger-rewrite.yml/dispatches")
    inputs = dispatch.call_args.kwargs["json"]["inputs"]
    assert inputs["source_wp_url"] == ""
    assert inputs["blogger_site_id"] == "blogger_ktrip365"
    assert inputs["persona"] == "Korea travel planner"
    assert inputs["publish_now"] == "true"


def test_blogger_failure_status_is_visible_and_retryable_in_recent_activity():
    header = ["created_at", "job_id", "site_id", "status", "publish_now", "title", "content", "labels", "source", "review_url", "x", "error_code", "message", "finished_at"]
    failure = ["2026-09-04T10:00:00", "blogger-rewrite-1", "blogger_ktrip365", "failed", "FALSE", "", "", "", "https://k-trip365.com", "", "", "NO_RELATED_WP_SOURCE", "관련 WordPress 글이 없어 억지 연결을 차단했습니다.", "2026-09-04T10:01:00"]
    queue_csv = ",".join(header) + "\n" + ",".join(failure) + "\n"
    queue_response = Mock(text=queue_csv)
    queue_response.raise_for_status.return_value = None
    editorial_response = Mock(text="created_at,platform,channel,title,review_url,status,decision,note\n")
    editorial_response.raise_for_status.return_value = None
    with patch("control_center.app.requests.get", side_effect=[queue_response, editorial_response]):
        items = get_review_queue()
    assert len(items) == 1
    assert items[0]["status"] == "실패 · NO_RELATED_WP_SOURCE"
    assert items[0]["retryable"] is True
    assert items[0]["review_url"] == ""


def test_superseded_queue_rows_are_hidden_from_recent_activity():
    header = ["created_at", "job_id", "site_id", "status", "publish_now", "title", "content", "labels", "source", "review_url", "x", "error_code", "message", "finished_at"]
    old = ["2026-09-03T10:00:00", "old-tistory", "tistory_life365", "superseded", "FALSE", "old title", "", "", "", "https://example.com/review", "", "", "", ""]
    queue_response = Mock(text=",".join(header) + "\n" + ",".join(old) + "\n")
    queue_response.raise_for_status.return_value = None
    editorial_response = Mock(text="created_at,platform,channel,title,review_url,status,decision,note\n")
    editorial_response.raise_for_status.return_value = None
    with patch("control_center.app.requests.get", side_effect=[queue_response, editorial_response]):
        assert get_review_queue() == []


def test_youtube_trigger_rejects_an_unconnected_channel_without_dispatch(monkeypatch):
    monkeypatch.delenv("CONTROL_CENTER_USERNAME", raising=False)
    monkeypatch.delenv("CONTROL_CENTER_PASSWORD", raising=False)
    monkeypatch.setenv("CONTROL_CENTER_GITHUB_TOKEN", "test-token")
    client = control_center_app.test_client()
    with patch("control_center.app.requests.post") as dispatch:
        response = client.post(
            "/trigger/youtube-batch",
            data={"csrf_token": control_center_app.config["CONTROL_CENTER_CSRF"], "channel_key": ""},
        )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("#youtube")
    dispatch.assert_not_called()


def test_youtube_trigger_dispatches_the_selected_real_channel(monkeypatch):
    channel = get_youtube_data()[0]
    monkeypatch.delenv("CONTROL_CENTER_USERNAME", raising=False)
    monkeypatch.delenv("CONTROL_CENTER_PASSWORD", raising=False)
    monkeypatch.setenv("CONTROL_CENTER_GITHUB_TOKEN", "test-token")
    client = control_center_app.test_client()
    with patch("control_center.app.requests.post") as dispatch:
        dispatch.return_value.status_code = 204
        response = client.post(
            "/trigger/youtube-batch",
            data={
                "csrf_token": control_center_app.config["CONTROL_CENTER_CSRF"],
                "channel_key": channel["channel_key"],
            },
        )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("#youtube")
    payload = dispatch.call_args.kwargs["json"]
    assert payload["inputs"]["channel_key"] == channel["channel_key"]
    assert payload["inputs"]["run_now"] == "true"


def test_blogspot_dashboard_uses_precise_connection_label_and_compact_categories():
    template = (Path(__file__).resolve().parents[1] / "control_center" / "templates" / "index.html").read_text(encoding="utf-8")
    assert "발행 준비됨" in template
    assert "blog.official_categories[:8]" in template
    assert compact_category("international students") == "intl students"
    assert compact_category("A category name that is unnecessarily long", 16).endswith("…")
    assert "당일 방문자 내림차순" in template
    assert "오늘 {{ loop.index }}위" in template


def test_adsense_blogger_sites_receive_gold_approval_cards():
    assert ADSENSE_BLOGGER_URLS == {
        "https://skin.k-health365.com",
        "https://glow.k-health365.com",
    }
    template = (Path(__file__).resolve().parents[1] / "control_center" / "templates" / "index.html").read_text(encoding="utf-8")
    assert "{% if blog.google_approved %}" in template
    assert "G승인" in template


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


def test_recent_activity_panel_is_removed_from_control_room():
    template = (Path(__file__).resolve().parents[1] / "control_center" / "templates" / "index.html").read_text(encoding="utf-8")
    assert "최근 글 현황" not in template
    assert "최근 글 목록" not in template
    assert "review_items" not in template
    assert 'href="#review-queue"' not in template
    review_template = (Path(__file__).resolve().parents[1] / "control_center" / "templates" / "tistory_review.html").read_text(encoding="utf-8")
    assert "비공개 검토 대기" in review_template
    assert "검색 설명" in review_template
    assert 'href="/#tistory"' in review_template


def test_control_room_displays_only_active_blogger_portfolio():
    template = (Path(__file__).resolve().parents[1] / "control_center" / "templates" / "index.html").read_text(encoding="utf-8")
    assert "Blogspot {{ bloggers|length }}" in template
    assert "BLOGSPOT {{ bloggers|length }}" in template
    assert "실제 운영 사이트만 표시" in template
    assert "Blogspot 27" not in template


def test_duplicate_medical_tour_blog_is_hidden_from_control_room():
    assert HIDDEN_BLOGGER_URLS == {"https://koreamedicaltour1.blogspot.com"}
    portfolio = json.loads((Path(__file__).resolve().parents[1] / "config" / "blogger_portfolio.json").read_text(encoding="utf-8"))["channels"]
    production = next(row for row in portfolio if row["blogspot"] == "https://koreamedicaltour365.blogspot.com")
    assert production["destination_id"] == "270775542645307723"


def test_all_wordpress_drafts_require_rankmath_focus_keyword():
    publisher = (Path(__file__).resolve().parents[1] / "control_center" / "wordpress.py").read_text(encoding="utf-8")
    direct_writer = (Path(__file__).resolve().parents[1] / "scripts" / "auto_write_and_draft.py").read_text(encoding="utf-8")
    assert '"rank_math_focus_keyword": keyword.strip()' in publisher
    assert '"rank_math_focus_keyword": focus_keyword' in direct_writer
    assert "focus keyword is required" in direct_writer


def test_connection_badges_do_not_overstate_metrics_connectivity():
    template = (Path(__file__).resolve().parents[1] / "control_center" / "templates" / "index.html").read_text(encoding="utf-8")
    assert "Blogger 발행 대상 ID 등록 여부" in template
    assert "방문자·색인 연결 상태가 아니라" in template
    assert "방문자·Google 색인이 아니라 공개 RSS 피드 연결 상태" in template


def test_dashboard_discloses_metric_evidence_and_unknown_index_count():
    template = (Path(__file__).resolve().parents[1] / "control_center" / "templates" / "index.html").read_text(encoding="utf-8")
    assert "실측 {{ site.visitor_checked_at }}" in template
    assert "판정 미확인 {{ site.index_unknown }}개 별도" in template


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
