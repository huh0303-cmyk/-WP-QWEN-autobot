"""Focused tests for the blog.korea365.org unified 68-card ranking.

Covers: (1) the config-only site counts that make up 27 WordPress (25
general + 2 newsrooms) + 33 Blogspot + 5 Tistory + 3 Naver = 68, (2) the
Naver public collector's honest fallback behaviour, and (3) the ranking
aggregator's sort/rank logic and "no fake zeros" guarantee.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from control_center import blog_korea365_ranking, blog_visitors, naver_blog  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Config-only counts: 27 + 33 + 5 + 3 = 68
# ---------------------------------------------------------------------------

def test_wordpress_unique_domains_total_27():
    profiles = json.loads((ROOT / "config" / "content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    domains = {
        p["wordpress"]["url"].replace("https://", "").replace("http://", "").rstrip("/")
        for p in profiles if (p.get("wordpress") or {}).get("url")
    }
    news_domains = {"koreanews365.com", "theseouljournal.com"}
    assert len(domains) == 27
    assert news_domains <= domains
    assert len(domains - news_domains) == 25


def test_blogspot_total_33():
    profiles = json.loads((ROOT / "config" / "content_engine_profiles.json").read_text(encoding="utf-8"))["profiles"]
    blogspot_urls = {p["blogspot"]["url"] for p in profiles if (p.get("blogspot") or {}).get("url")}
    assert len(blogspot_urls) == 33


def test_tistory_total_5():
    sites = json.loads((ROOT / "config" / "tistory_portfolio.json").read_text(encoding="utf-8"))["sites"]
    assert len(sites) == 5


def test_naver_total_3():
    rooms = json.loads((ROOT / "config" / "automation_rooms.json").read_text(encoding="utf-8"))["rooms"]
    naver_rooms = [r for r in rooms if r.get("platform") == "naver"]
    assert len(naver_rooms) == 3


# ---------------------------------------------------------------------------
# 2. Naver public collector: honest fallback, never a fake zero
# ---------------------------------------------------------------------------

def _rss_bytes(items):
    entries = "".join(
        f"<item><title>{title}</title><link>{link}</link><pubDate>{pub_date}</pubDate></item>"
        for title, link, pub_date in items
    )
    return f"<?xml version='1.0'?><rss><channel>{entries}</channel></rss>".encode("utf-8")


def test_naver_summary_rss_success_homepage_missing_total(monkeypatch):
    naver_blog._naver_public_summary.cache_clear()

    def fake_get(url, timeout=None, headers=None):
        response = mock.Mock()
        response.raise_for_status = mock.Mock()
        if "rss.blog.naver.com" in url:
            response.content = _rss_bytes([
                ("Latest post", "https://blog.naver.com/huh0303/1", "Mon, 28 Sep 2026 09:00:00 +0900"),
            ])
        else:
            response.text = "<html>no widget here</html>"
        return response

    monkeypatch.setattr(naver_blog.requests, "get", fake_get)
    summary = naver_blog._naver_public_summary("huh0303", 0)
    assert summary["connected"] is True
    assert summary["latest_title"] == "Latest post"
    # The homepage did not expose the "전체보기 (N)" widget, so the true
    # total must stay unconfirmed rather than being guessed from RSS length.
    assert summary["total_posts"] is None


def test_naver_summary_total_failure_never_crashes_or_fakes(monkeypatch):
    naver_blog._naver_public_summary.cache_clear()

    def fake_get(url, timeout=None, headers=None):
        raise naver_blog.requests.RequestException("network down")

    monkeypatch.setattr(naver_blog.requests, "get", fake_get)
    summary = naver_blog._naver_public_summary("huh3", 0)
    assert summary["connected"] is False
    assert summary["total_posts"] is None
    assert summary["error"] == "rss_unavailable"


def test_get_naver_data_never_fabricates_visitor_numbers(monkeypatch, tmp_path):
    monkeypatch.setattr(naver_blog, "ROOT", tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "automation_rooms.json").write_text(json.dumps({
        "rooms": [
            {"room_id": "naver_n1", "platform": "naver", "destination_id": "huh0303", "name": "N1"},
            {"room_id": "naver_n2", "platform": "naver", "destination_id": "huh3", "name": "N2"},
            {"room_id": "naver_n3", "platform": "naver", "destination_id": "huh4", "name": "N3"},
        ]
    }), encoding="utf-8")
    naver_blog._naver_public_summary.cache_clear()
    monkeypatch.setattr(naver_blog, "_naver_public_summary", lambda blog_id, bucket: {
        "connected": False, "total_posts": None, "today": 0,
        "latest_url": "", "latest_title": "", "latest_at": None, "error": "rss_unavailable",
    })
    monkeypatch.setattr(naver_blog, "_naver_visitor_stats", lambda blog_id, bucket: {
        "connected": False, "reason": "visitor gadget unavailable",
    })
    rows = naver_blog.get_naver_data()
    assert len(rows) == 3
    for row in rows:
        assert row["today_visitors"] is None
        assert row["total_visitors"] is None
        assert row["visitor_error"]  # honest reason present, not silently blank


# ---------------------------------------------------------------------------
# 3. Ranking aggregator: sort order, rank assignment, delta passthrough
# ---------------------------------------------------------------------------

def _wp_row(domain, today, delta, kind="blog"):
    return {
        "site_id": f"wp_{domain}", "domain": domain,
        "today_visitors": (today or 0) + 1 if today is not None else None, "today_delta": 1 if today is not None else None,
        "yesterday_visitors": today, "yesterday_delta": delta,
        "total_visitors": (today or 0) * 100, "total_delta": delta, "total_posts": 10, "posts_delta": 1,
        "indexed": 8, "indexed_delta": 0, "index_checked_at": "2026-09-27T00:00:00+09:00",
        "visitor_connected": today is not None, "cadence": {"kind": kind},
        "admin_review_url": f"https://{domain}/wp-admin/",
    }


def _blogspot_row(name, today, delta):
    return {
        "site_id": f"blogger_{name}", "name": name, "url": f"https://{name}.blogspot.com",
        "today_visitors": (today or 0) + 1 if today is not None else None, "today_delta": 1 if today is not None else None,
        "yesterday_visitors": today, "yesterday_delta": delta, "total_visitors": (today or 0) * 50,
        "total_delta": delta, "total_posts": 20, "posts_delta": 2, "indexed": None, "indexed_delta": None,
        "admin_review_url": "https://www.blogger.com/",
    }


def _tistory_row(name):
    return {
        "site_id": f"tistory_{name}", "name": name, "url": f"https://{name}.tistory.com",
        "today_visitors": None, "today_delta": None, "total_visitors": None, "total_delta": None,
        "total_posts": 5, "posts_delta": 0, "indexed": None, "indexed_delta": None,
        "admin_review_url": f"https://{name}.tistory.com/manage/posts",
    }


def _naver_row(name):
    return {
        "site_id": f"naver_{name}", "name": name, "url": f"https://blog.naver.com/{name}",
        "today_visitors": None, "today_delta": None, "total_visitors": None, "total_delta": None,
        "visitor_error": naver_blog.VISITOR_UNAVAILABLE_REASON,
        "total_posts": None, "posts_delta": None, "indexed": None, "indexed_delta": None,
        "admin_review_url": f"https://blog.naver.com/GoBlogWrite.naver?blogId={name}",
    }


def test_build_ranking_combines_and_sorts_all_cards():
    wp_rows = [_wp_row("a.com", 50, 5), _wp_row("news.com", 200, -10, kind="newsroom")]
    blogspot_rows = [_blogspot_row("bg1", 300, 20), _blogspot_row("bg2", None, None)]
    tistory_rows = [_tistory_row("t1")]
    naver_rows = [_naver_row("n1")]

    payload = blog_korea365_ranking.build_ranking(
        lambda: wp_rows, lambda: blogspot_rows, lambda: tistory_rows, lambda: naver_rows,
    )

    assert payload["total_cards"] == 6
    assert payload["display_date"]
    assert payload["ranked_cards"] == 3  # only the three cards with a confirmed count
    assert payload["unranked_cards"] == 3
    assert [card["row_number"] for card in payload["cards"]] == list(range(1, 7))

    cards = payload["cards"]
    # Descending by yesterday_visitors: bg1(300) > news.com(200) > a.com(50), then unranked.
    ranked = [c for c in cards if c["rank"] is not None]
    assert [c["yesterday_visitors"] for c in ranked] == [300, 200, 50]
    assert [c["rank"] for c in ranked] == [1, 2, 3]
    unranked = [c for c in cards if c["rank"] is None]
    assert len(unranked) == 3
    assert all(c["yesterday_visitors"] is None for c in unranked)

    news_card = next(c for c in cards if c["site_id"] == "wp_news.com")
    assert news_card["kind"] == "news"
    blog_card = next(c for c in cards if c["site_id"] == "wp_a.com")
    assert blog_card["kind"] == "wordpress"

    assert payload["platform_counts"] == {"wordpress": 2, "blogspot": 2, "tistory": 1, "naver": 1}
    assert ranked[0]["connector_status"]["visitor_delta"]["connected"] is True


def test_build_ranking_never_coerces_none_to_zero():
    payload = blog_korea365_ranking.build_ranking(
        lambda: [_wp_row("a.com", None, None)],
        lambda: [], lambda: [_tistory_row("t1")], lambda: [_naver_row("n1")],
    )
    for card in payload["cards"]:
        if card["site_id"] in {"tistory_t1", "naver_n1", "wp_a.com"}:
            assert card["yesterday_visitors"] is None
            assert card["rank"] is None


def test_naver_card_reports_disconnected_visitor_status():
    payload = blog_korea365_ranking.build_ranking(
        lambda: [], lambda: [], lambda: [], lambda: [_naver_row("n1")],
    )
    card = payload["cards"][0]
    assert card["connector_status"]["visitors"]["connected"] is False
    assert card["connector_status"]["visitors"]["reason"] == naver_blog.VISITOR_UNAVAILABLE_REASON


def test_tistory_card_reports_no_visitor_widget_reason():
    payload = blog_korea365_ranking.build_ranking(
        lambda: [], lambda: [], lambda: [_tistory_row("t1")], lambda: [],
    )
    card = payload["cards"][0]
    assert card["connector_status"]["visitors"]["connected"] is False
    assert card["connector_status"]["visitors"]["reason"]


def test_missing_visitor_delta_is_its_own_connector_failure():
    row = _wp_row("a.com", 50, None)
    payload = blog_korea365_ranking.build_ranking(lambda: [row], lambda: [], lambda: [], lambda: [])
    status = payload["cards"][0]["connector_status"]
    assert status["visitors"]["connected"] is True
    assert status["visitor_delta"]["connected"] is False
    assert status["visitor_delta"]["reason"] == "직전 비교값 수집 필요"


# ---------------------------------------------------------------------------
# 4. Flask route: shape, status, cache header
# ---------------------------------------------------------------------------

def test_install_route_returns_ranked_payload():
    import flask
    app = flask.Flask(__name__)
    blog_korea365_ranking.install(
        app,
        lambda: [_wp_row("a.com", 10, 1)],
        lambda: [_blogspot_row("bg1", 20, 2)],
        lambda: [_tistory_row("t1")],
        lambda: [_naver_row("n1")],
    )
    client = app.test_client()
    response = client.get("/api/blog-korea365/ranking")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    payload = response.get_json()
    assert payload["total_cards"] == 4
    assert payload["cards"][0]["yesterday_visitors"] == 20


def test_dashboard_shows_ordinal_rank_and_site_opening_date():
    template = (ROOT / "control_center" / "templates" / "blog_dashboard.html").read_text(encoding="utf-8")
    assert "c.row_number+'위'" in template
    assert "사이트 생성일" in template
    assert "c.opening_date" in template


def test_blogger_central_counter_reads_zero_as_connected(monkeypatch, tmp_path):
    db = tmp_path / "visitors.sqlite3"
    today = datetime.now(timezone(timedelta(hours=9))).date()
    yesterday = (today - timedelta(days=1)).isoformat()
    day_before = (today - timedelta(days=2)).isoformat()
    monkeypatch.setattr(blog_visitors, "_today", lambda: today.isoformat())
    with sqlite3.connect(db) as conn:
        conn.executescript("""
            CREATE TABLE daily(site_key TEXT,date TEXT,count INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(site_key,date));
            CREATE TABLE total(site_key TEXT PRIMARY KEY,count INTEGER NOT NULL DEFAULT 0);
            INSERT INTO total VALUES('kfinance365',3);
        """)
        conn.execute("INSERT INTO daily VALUES(?,?,?)", ("kfinance365", yesterday, 2))
        conn.execute("INSERT INTO daily VALUES(?,?,?)", ("kfinance365", day_before, 1))
    stats = blog_visitors.read_site_stats(db, "kfinance365")
    assert stats["connected"] is True
    assert stats["today"] == 0
    assert stats["yesterday"] == 2
    assert stats["yesterday_delta"] == 1
    assert stats["total"] == 3
