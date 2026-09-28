from pathlib import Path

from scripts.opening_recent_snapshot import stamp


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


def test_pm_lock_records_three_visible_apps_and_youtube_alias():
    policy = (ROOT / "docs" / "KOREA365_PM_LOCK_2026-09-29.md").read_text(encoding="utf-8")
    assert "combined YouTube, Instagram, Threads, TikTok, Facebook" in policy
    assert "compatibility alias only" in policy
    assert "CONTROL / BLOG / YOUTUBE+SNS" in policy


def test_combined_social_detail_uses_mobile_scrollable_table_not_cards():
    template = (ROOT / "control_center" / "templates" / "social_accounts.html").read_text(encoding="utf-8")
    assert '<table class="account-table">' in template
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
    assert '<table class="account-table">' in social
    assert "YOUTUBE + SNS 생산·발행 통제실" in social
    assert "로그인·권한 필요" in social
