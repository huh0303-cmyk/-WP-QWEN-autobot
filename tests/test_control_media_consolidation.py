from pathlib import Path

from scripts.opening_recent_snapshot import stamp
from control_center import blog_metadata


ROOT = Path(__file__).resolve().parents[1]


def test_control_home_keeps_blog_and_social_as_two_equal_tables():
    template = (ROOT / "control_center" / "templates" / "control_home.html").read_text(encoding="utf-8")
    assert "grid-template-columns:repeat(2,minmax(0,1fr))" in template
    assert '<tbody id="blog-rows">' in template
    assert '<tbody id="social-rows">' in template
    assert '<tbody id="youtube-rows">' not in template
    assert '<tbody id="sns-rows">' not in template
    assert "fetch('/api/control/social-ranking'" in template
    assert "fetch('/api/control/youtube-ranking'" not in template
    assert "fetch('/api/control/sns-ranking'" not in template


def test_visible_navigation_has_only_control_blog_and_combined_social():
    for relative in (
        "control_center/templates/control_home.html",
        "control_center/templates/blog_dashboard.html",
        "control_center/templates/index.html",
    ):
        template = (ROOT / relative).read_text(encoding="utf-8")
        assert "YOUTUBE + SNS" in template
        assert 'href="https://youtube.korea365.org"' not in template


def test_quick_publish_links_reuse_existing_workflows():
    control = (ROOT / "control_center" / "templates" / "control_home.html").read_text(encoding="utf-8")
    london = (ROOT / "control_center" / "templates" / "london_gpt.html").read_text(encoding="utf-8")
    assert "'/london-gpt?site_id='" in control
    assert "social-accounts?platform='+encodeURIComponent(c.platform||'통합')" in control
    assert "const launchSite=launchParams.get('site_id')||''" in london
    assert "refreshPlatform(launchSite)" in london


def test_recent_publication_snapshot_preserves_kst_time():
    assert stamp("2026-09-29T01:23:45Z") == "2026-09-29T10:23+09:00"


def test_local_opening_snapshot_fills_assets_missing_from_remote(monkeypatch, tmp_path):
    local = tmp_path / "data"
    local.mkdir()
    (local / "opening_recent_snapshot.json").write_text(
        '{"youtube":{"new-id":{"opening_date":"2026-09-12","recent_publish_date":"2026-09-13"}}}',
        encoding="utf-8",
    )

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"youtube": {"old-id": {"opening_date": "2025-01-01"}}}

    monkeypatch.setattr(blog_metadata, "ROOT", tmp_path)
    monkeypatch.setattr(blog_metadata.requests, "get", lambda *args, **kwargs: Response())
    blog_metadata._opening_recent_snapshot.cache_clear()
    result = blog_metadata._opening_recent_snapshot(20260929)
    assert result["youtube"]["old-id"]["opening_date"] == "2025-01-01"
    assert result["youtube"]["new-id"]["recent_publish_date"] == "2026-09-13"


def test_pm_lock_records_three_visible_apps_and_youtube_alias():
    policy = (ROOT / "docs" / "KOREA365_PM_LOCK_2026-09-29.md").read_text(encoding="utf-8")
    assert "combined YouTube, Instagram, Threads, TikTok, Facebook" in policy
    assert "compatibility alias only" in policy
    assert "CONTROL / BLOG / YOUTUBE+SNS" in policy


def test_combined_social_detail_uses_mobile_scrollable_table_not_cards():
    template = (ROOT / "control_center" / "templates" / "social_accounts.html").read_text(encoding="utf-8")
    assert '<table id="socialTable" class="account-table">' in template
    assert '<article class="card"' not in template
    assert "YOUTUBE + SNS 생산·발행 통제실" in template
    assert "overflow:auto" in template


def test_london_agent_three_has_three_free_image_fallbacks():
    template = (ROOT / "control_center" / "templates" / "london_gpt.html").read_text(encoding="utf-8")
    assert "A Pexels → B Pixabay → C Wikimedia" in template
    assert 'value="wikimedia"' in template
    assert 'value="replicate_sdxl"' not in template
    assert 'value="replicate_flux"' not in template


def test_blog_and_social_are_lightweight_publishing_sheets():
    blog = (ROOT / "control_center" / "templates" / "blog_dashboard.html").read_text(encoding="utf-8")
    social = (ROOT / "control_center" / "templates" / "social_accounts.html").read_text(encoding="utf-8")
    assert "1. 핵심 주제어" in blog
    assert "검색량 · Google/Naver 신호 · 미디어 언급량" in blog
    assert 'id="publishSite"' in blog
    assert "4-Agent 발행 시작" in blog
    assert '<table class="ranking">' in blog
    assert '<table id="socialTable" class="account-table">' in social
    assert "YOUTUBE + SNS 생산·발행 통제실" in social
    assert "로그인·권한 필요" in social
    assert "<th>번호</th><th>플랫폼</th>" in social
    assert "<td>{{loop.index}}</td><td>" in social
    assert "전체 = 모든 YouTube+SNS" in social
    assert "생산·발행 트리거" in social
    for platform in ("YouTube", "TikTok", "Instagram", "Facebook", "Threads"):
        assert f'tr[data-platform="{platform}"] td' in social
        assert f'a[data-platform="{platform}"]' in social
    assert '<a data-platform="{{p}}"' in social
    assert "<th>구분</th><th>채널/계정</th><th>채널 주제</th><th>운영 역할</th>" in social
    assert "<th>구독자·팔로워(증감)</th><th>방문·조회수(증감)</th><th>콘텐츠수(증감)</th><th>$ 수익</th><th>채널/페이지 생성일</th><th>최근 발행일</th>" in social
    assert "<th>생산·발행 트리거</th><th>계정 ID</th>" in social
    assert "fetch('/api/control/social-ranking'" in social
    assert "item.content_count_delta" in social
    assert "k365-social-column-widths-v5" in social
    assert 'class="metric-revenue">미연결' in social
    assert 'class="metric-opening">미확인' in social
    assert 'class="metric-recent">미확인' in social
    assert "tr.classList.toggle('monetized-row'" in social
    assert "col-resizer" in social


def test_youtube_group_order_and_verified_survival_channels_are_explicit():
    source = (ROOT / "control_center" / "social_accounts.py").read_text(encoding="utf-8")
    inventory = (ROOT / "config" / "london_social_account_inventory_2026-09-24.json").read_text(encoding="utf-8")
    assert '"language": 0, "playlist": 1, "knowledge": 2, "health": 3, "shopping": 4' in source
    assert '"Chinese Survival": 4' in source
    assert '"Portuguese Survival": 5' in source
    assert '"Vietnamese Survival": 6' in source
    assert "UCGTd7RhfaUaGGbVRsNPUN6Q" in inventory
    assert "UCKvKhETLGPaRV3qfWv2bM2g" in inventory
    assert "UCRZ0uc_bxKDMwz3noBBi9KQ" in inventory
    assert '"name": "SIS-Language Center"' in inventory
    assert '"state_label": "공개 핸들 확인 실패 · UC ID 필요"' in source


def test_social_ranking_exposes_real_metric_deltas_without_zero_fill():
    source = (ROOT / "control_center" / "control_home.py").read_text(encoding="utf-8")
    assert '"video_delta": _delta(videos, previous.get("videos")' in source
    assert '"content_count_delta": item.get("video_delta")' in source
    assert '"content_count_delta": item.get("content_delta")' in source
    assert '"target_total": 48' in source
    assert '"target_youtube": 24' in source
    assert '"status": "수익 OAuth 필요"' in source
    assert '"opening_date": str(item.get("created_at")' in source
