from pathlib import Path

from scripts.opening_recent_snapshot import stamp
from control_center import blog_metadata, control_home
from control_center.blog_korea365_ranking import build_ranking
import control_center.blog_korea365_ranking as ranking


ROOT = Path(__file__).resolve().parents[1]


def test_youtube_oauth_receipt_displays_identity_without_claiming_publication(monkeypatch, tmp_path):
    import sys
    import types

    monkeypatch.setitem(sys.modules, "fcntl", types.ModuleType("fcntl"))
    from control_center import social_accounts

    channel_id = "UCKZsfAWyCmY0jckf4IWZrqw"
    inventory = tmp_path / "inventory.json"
    inventory.write_text('{"youtube":[{"name":"CAFE_KPOP","channel_id":"' + channel_id + '"}]}', encoding="utf-8")
    config = tmp_path / "channels.json"
    config.write_text('{"channels":[{"channel_id":"' + channel_id + '","channel_type":"playlist"}]}', encoding="utf-8")
    receipts = tmp_path / "receipts.json"
    receipts.write_text('{"' + channel_id + '":{"channel_id":"' + channel_id + '","secret_name":"YOUTUBE_OAUTH_REFRESH_TOKEN_KPOP","verified_at_utc":"2026-10-01T00:00:00+00:00"}}', encoding="utf-8")
    monkeypatch.setattr(social_accounts, "INVENTORY", inventory)
    monkeypatch.setattr(social_accounts, "YOUTUBE_CONFIG", config)
    monkeypatch.setattr(social_accounts, "YOUTUBE_OAUTH_RECEIPTS", receipts)
    card = social_accounts._youtube_cards()[0]
    assert card["state_label"] == "OAuth 채널 ID 확인 · 공개 영수증 없음"
    assert card["connection_level"] == "identity_verified"
    receipts.write_text('{"' + channel_id + '":{"channel_id":"wrong","secret_name":"YOUTUBE_OAUTH_REFRESH_TOKEN_KPOP","verified_at_utc":"2026-10-01T00:00:00+00:00"}}', encoding="utf-8")
    assert "OAuth 채널 ID 확인" not in social_accounts._youtube_cards()[0]["state_label"]


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
    assert "GSC 클릭/노출" in template
    assert "visitorMetric(c)" in template
    assert "GSC 미연결" in template
    assert "GSC 소유권 인증 필요" in template
    assert "GSC 연결 · 클릭 데이터 없음" in template
    assert '<th>순위</th><th>플랫폼</th><th>사이트</th><th>누적 수익 (USD)</th>' in template
    assert '<th>순위</th><th>플랫폼</th><th>채널/계정</th><th>누적 수익 (USD)</th>' in template
    assert "return 'US$'+nf.format(r.amount)" in template
    assert "title=\"수익창출\">🏅" in template
    assert "수익 데이터 미연결</span>" not in template
    assert "timeZone:'Asia/Seoul'" in template
    assert "'블로그 순위 ('+dateLabel(todayKst())" in template
    assert "'YouTube + SNS 순위 ('+dateLabel(todayKst())" in template
    assert "rank(c.row_number)" in template
    assert "rank(c.rank)" not in template
    assert "recentPublication(c)" in template
    assert "Post ID " in template


def test_blog_ranking_preserves_real_gsc_clicks_and_impressions():
    row = {
        "site_id": "wp_test",
        "domain": "example.com",
        "yesterday_visitors": 12,
        "gsc_clicks": 3,
        "gsc_impressions": 91,
        "gsc_ctr": 0.0329,
        "gsc_position": 8.4,
        "gsc_date": "2026-09-26",
        "gsc_connected": True,
    }
    card = build_ranking(lambda: [row], lambda: [], lambda: [], lambda: [])["cards"][0]
    assert card["gsc_connected"] is True
    assert (card["gsc_clicks"], card["gsc_impressions"], card["gsc_date"]) == (3, 91, "2026-09-26")


def test_blog_ranking_uses_verified_gsc_inventory_when_clicks_are_absent(monkeypatch):
    monkeypatch.setattr(
        ranking,
        "_gsc_property_for",
        lambda url: {
            "siteUrl": "https://example.blogspot.com/",
            "permissionLevel": "siteOwner",
        },
    )
    card = ranking._card(
        {"url": "https://example.blogspot.com", "name": "Example"},
        "blogspot",
        "blogspot",
    )
    assert card["gsc_connected"] is True
    assert card["gsc_status"] == "connected"
    assert card["gsc_permission"] == "siteOwner"


def test_blog_ranking_marks_unverified_gsc_property_as_user_auth_required(monkeypatch):
    monkeypatch.setattr(
        ranking,
        "_gsc_property_for",
        lambda url: {
            "siteUrl": "https://example.tistory.com/",
            "permissionLevel": "siteUnverifiedUser",
        },
    )
    card = ranking._card(
        {"url": "https://example.tistory.com", "name": "Example"},
        "tistory",
        "tistory",
    )
    assert card["gsc_connected"] is False
    assert card["gsc_status"] == "user_auth_required"
    assert card["gsc_permission"] == "siteUnverifiedUser"


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
    blog = (ROOT / "control_center" / "templates" / "blog_dashboard.html").read_text(encoding="utf-8")
    assert "'https://blog.korea365.org/publish?site_id='" in control
    assert "'/publish?site_id='" in blog
    assert "/london-gpt?site_id=" not in control + blog
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
    assert "즉시발행 시작" in blog
    assert "같은 n8n 흐름" in blog
    assert '<table class="ranking">' in blog
    assert '<table id="socialTable" class="account-table">' in social
    assert "YOUTUBE + SNS 생산·발행 통제실" in social
    assert "로그인·권한 필요" in social
    assert "<th>번호</th><th>플랫폼</th>" in social
    assert "<td>{{loop.index}}</td><td>" in social
    assert "확인된 YouTube 채널과 SNS 운영 대상" in social
    assert "생산·발행 트리거" in social
    for platform in ("YouTube", "TikTok", "Instagram", "Facebook", "Threads"):
        assert f'tr[data-platform="{platform}"] td' in social
        assert f'a[data-platform="{platform}"]' in social
    assert '<a data-platform="{{p}}"' in social
    assert "<th>구분</th><th>채널/계정</th><th>채널 주제</th><th>운영 역할</th>" in social
    assert "<th>구독자수(증감)</th><th>어제 방문·조회수(증감)</th><th>콘텐츠수(증감)</th><th>누적 수익 (USD)</th><th>개설일자</th><th>최근 발행일</th>" in social
    assert "return '🏅 US$'+new Intl.NumberFormat('ko-KR').format(revenue.amount)" in social
    assert "<th>생산·발행 트리거</th><th>계정 ID</th>" in social
    assert "fetch('/api/control/social-ranking'" in social
    assert "item.content_count_delta" in social
    assert "k365-social-column-widths-v6" in social
    assert "item.yesterday_views,item.yesterday_views_delta" in social
    assert "return '🏅'" in social
    assert 'class="metric-revenue">—' in social
    assert 'class="metric-opening">미확인' in social
    assert 'class="metric-recent">미확인' in social
    assert "tr.classList.toggle('monetized-row'" in social
    assert "col-resizer" in social


def test_youtube_group_order_and_verified_survival_channels_are_explicit():
    source = (ROOT / "control_center" / "social_accounts.py").read_text(encoding="utf-8")
    inventory = (ROOT / "config" / "london_social_account_inventory_2026-09-24.json").read_text(encoding="utf-8")
    assert '"language": 0, "playlist": 1, "knowledge": 2, "health": 3, "shopping": 4' in source
    assert '"서울국제대학-TOPIK센터": 0' in source
    assert '"Chinese Survival": 5' in source
    assert '"Portuguese Survival": 6' in source
    assert '"Vietnamese Survival": 7' in source
    assert inventory.count('"group": "language"') == 10
    assert inventory.count('"group": "health"') == 2
    assert inventory.count('"group": "shopping"') == 2
    assert '"role": "multilingual_shopping"' in inventory
    assert "UCGTd7RhfaUaGGbVRsNPUN6Q" in inventory
    assert "UCKvKhETLGPaRV3qfWv2bM2g" in inventory
    assert "UCRZ0uc_bxKDMwz3noBBi9KQ" in inventory
    assert inventory.count('"recent_publish_date": "2026-09-13"') >= 3
    assert '"name": "Jisoo2"' in inventory
    assert '"previous_name": "SIS-Language Center"' in inventory
    assert "Planned shopping slots have no UC ID" in source


def test_social_ranking_exposes_real_metric_deltas_without_zero_fill():
    source = (ROOT / "control_center" / "control_home.py").read_text(encoding="utf-8")
    assert '"video_delta": _delta(videos, previous.get("videos")' in source
    assert '"content_count_delta": item.get("video_delta")' in source
    assert '"content_count_delta": item.get("content_delta")' in source
    assert '"target_total": 39' in source
    assert '"target_youtube": 23' in source
    assert '"target_sns": 16' in source
    assert '"display_date": now.date().isoformat()' in source
    assert 'for row_number, row in enumerate(rows, 1):' in source
    assert 'row["row_number"] = row_number' in source
    assert '"status": "수익 데이터 권한 필요"' in source
    assert '"opening_date": str(item.get("created_at")' in source
    assert 'timeline.get("recent_publish_date") or str(item.get("recent_publish_date")' in source
    assert '"yesterday_views": item.get("view_delta")' in source
    assert '"yesterday_views_delta": item.get("views_delta")' in source
    assert "if item.get(\"handle\") and item.get(\"channel_id\")" in source


def test_revenue_cells_use_cumulative_amount_and_only_topik_is_youtube_monetized(monkeypatch, tmp_path):
    (tmp_path / "situation_room_history.json").write_text(
        '{"latest":{"adsense_khealth365":{"today":6,"cumulative":8625,"currency":"KRW"}},'
        '"previous":{"adsense_khealth365":{"today":0,"cumulative":8619,"currency":"KRW"}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(blog_metadata, "ROOT", tmp_path)

    blog_revenue = blog_metadata.revenue_info("k-health365.com", {})
    assert blog_revenue["amount"] is None
    assert blog_revenue["delta"] is None
    assert blog_revenue["currency"] == "USD"

    topik = control_home._social_revenue("YouTube", "seoul_topik1", "UCdA24IuR-JE7qButWv5jLqA")
    other = control_home._social_revenue("YouTube", "English_survival", "UCrjkKWMHzAAvpLIFgHnwcWg")
    assert topik["monetized"] is True
    assert other["monetized"] is False


def test_youtube_ranking_prefers_full_public_api_snapshot(monkeypatch, tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "config" / "london_social_account_inventory_2026-09-24.json").write_text(
        '{"youtube":[{"name":"Old label","handle":"SIS_FrenchSurvival","channel_id":"UC-test","group":"language"}],'
        '"unconfirmed":[{"platform":"youtube","name":"Jisoo2","handle":"sis_languagecenter"}]}',
        encoding="utf-8",
    )
    (tmp_path / "data" / "youtube_public_metrics.json").write_text(
        '{"checked_at_kst":"2026-09-29T09:00:00+09:00","channels":{"UC-test":{"name":"French Survival","subscribers":7,"views":321,"videos":4,"connected":true}}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(control_home, "ROOT", tmp_path)
    monkeypatch.setattr(control_home, "opening_recent_info", lambda *args: {})
    result = control_home.build_youtube_ranking(1)
    assert result["ranked"] == 1
    assert result["total"] == 1
    assert result["rows"][0]["name"] == "French Survival"
    assert result["rows"][0]["subscribers"] == 7
    assert result["rows"][0]["views"] == 321


def test_sns_ranking_uses_persisted_official_probe(monkeypatch, tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "config" / "sns_six_channel_policy.json").write_text(
        '{"accounts":[{"platform":"Instagram","role":"korean_topik","display_name":"SIS Korean","handle":"sis_topik1"}]}',
        encoding="utf-8",
    )
    (tmp_path / "data" / "ceo_sns_probe.json").write_text(
        '{"rows":[{"platform":"Instagram","brand":"TOPIK","followers":3555,"status":"조회 성공"}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(control_home, "ROOT", tmp_path)
    result = control_home.build_sns_ranking(1)
    assert result["ranked"] == 1
    assert result["rows"][0]["followers"] == 3555
    assert result["rows"][0]["metric_status"] == "조회 성공"


def test_metrics_workflows_redeploy_only_sanitized_dashboard_snapshots():
    workflow = (ROOT / ".github" / "workflows" / "deploy-to-vps.yml").read_text(encoding="utf-8")
    assert '"Daily Google metrics snapshot"' in workflow
    assert '"CEO SNS current statistics (read-only)"' in workflow
    assert "data/gsc_properties.json" in workflow
    assert "data/youtube_public_metrics.json data/ceo_sns_probe.json" in workflow
    assert 'git -C "$ROOT" show "HEAD:$rel"' in workflow
    assert "systemctl restart korea365-control.service" in workflow


def test_social_platforms_are_grouped_in_requested_order():
    control = (ROOT / "control_center" / "control_home.py").read_text(encoding="utf-8")
    accounts = (ROOT / "control_center" / "social_accounts.py").read_text(encoding="utf-8")
    template = (ROOT / "control_center" / "templates" / "control_home.html").read_text(encoding="utf-8")
    expected = '{"YouTube": 0, "Facebook": 1, "Threads": 2, "Instagram": 3, "TikTok": 4}'
    assert expected in control
    assert expected in accounts
    assert "YouTube · Facebook · Threads · Instagram · TikTok 순서" in template
