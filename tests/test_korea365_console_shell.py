from pathlib import Path

from jinja2 import Environment, FileSystemLoader


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "control_center" / "templates"


def test_three_domains_share_one_responsive_navigation():
    for name, active in (
        ("control_home.html", "control"),
        ("blog_dashboard.html", "blog"),
        ("social_accounts.html", "social"),
    ):
        source = (TEMPLATES / name).read_text(encoding="utf-8")
        assert "_korea365_app_nav.html" in source
        assert f"active_console = '{active}'" in source
        assert "korea365-app-shell.css" in source

    nav = (TEMPLATES / "_korea365_app_nav.html").read_text(encoding="utf-8")
    for href in (
        "https://control.korea365.org",
        "https://blog.korea365.org",
        "https://sns.korea365.org",
    ):
        assert href in nav
    assert "aria-current=\"page\"" in nav


def test_console_copy_distinguishes_pipeline_receipt_and_schedule_state():
    control = (TEMPLATES / "control_home.html").read_text(encoding="utf-8")
    blog = (TEMPLATES / "blog_dashboard.html").read_text(encoding="utf-8")
    social = (TEMPLATES / "social_accounts.html").read_text(encoding="utf-8")

    assert "완료 기준은 공개 영수증입니다" in control
    assert "응답이 늦어도 바로 다시 누르지 마세요" in blog
    assert "정기 예약 경로까지 모두 통합됐다는 뜻은 아닙니다" in blog
    assert "채널 인증 성공도 공개 완료와 다르며" in social
    assert "플랫폼별 4개 행은 운영 역할 목표" in social
    assert "모든 블로그가 같은 n8n 흐름" not in blog


def test_shared_console_shell_fits_small_screens():
    css = (ROOT / "control_center" / "static" / "korea365-app-shell.css").read_text(encoding="utf-8")
    assert ".k365-app-nav" in css
    assert "@media(max-width:720px)" in css
    assert ".k365-ops-note" in css


def test_shared_navigation_partial_compiles_for_all_host_views():
    environment = Environment(loader=FileSystemLoader(str(TEMPLATES)))
    for name in ("control_home.html", "blog_dashboard.html", "social_accounts.html"):
        environment.get_template(name)
