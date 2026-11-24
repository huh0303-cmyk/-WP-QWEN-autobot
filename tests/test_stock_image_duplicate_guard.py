"""Regression tests: the same stock photo must not be attached to several posts.

Incident 2026-11-22/24 (jobkoreaglobal.com): two posts got Pexels #5439152.
Causes: (1) the duplicate-photo guard was silently off because only
TARGET_SITE_URL is set by the publish workflow, (2) candidate selection was
deterministic (always the first match), (3) a duplicate made the stage give up
instead of trying the next candidate.
"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import stock_image_provider as stock
import replicate_image_provider as gateway


def photo(pid):
    return {"id": str(pid), "description": "job interview office hiring Korea",
            "url": f"https://images.pexels.com/photos/{pid}/a.jpeg",
            "source": f"https://www.pexels.com/photo/{pid}", "author": "T",
            "width": 1600, "height": 1600}


def fake_host(url, asset_key, **kw):
    return f"https://raw.githubusercontent.com/r/p/main/{asset_key}.jpg"


def setup_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("STOCK_IMAGES_ENABLED", "true")
    monkeypatch.setenv("PEXELS_API_KEY", "test")
    monkeypatch.delenv("PIXABAY_KEY", raising=False)
    monkeypatch.setattr(stock, "USAGE_LEDGER", tmp_path / "usage.json")


def test_guard_is_active_when_only_target_site_url_is_set(monkeypatch):
    monkeypatch.delenv("WP_SITE_URL", raising=False)
    monkeypatch.delenv("WORDPRESS_SITE_URL", raising=False)
    monkeypatch.setenv("TARGET_SITE_URL", "https://example.test")
    with patch("editorial_image_guard.filter_wp_images", return_value=[]) as guard:
        assert gateway._site_safe_image("https://x/y.jpg") is None
        guard.assert_called_once()


def test_duplicate_candidate_is_skipped_and_next_one_used(monkeypatch, tmp_path):
    setup_env(monkeypatch, tmp_path)
    bad = fake_host("", "stock-pexels-111")
    with patch.object(stock, "_search", return_value=[photo(111), photo(222)]), \
         patch("stable_image_hosting.host_permanently", side_effect=fake_host), \
         patch.object(stock, "_duplicate_on_site", side_effect=lambda u: u == bad):
        for _ in range(10):
            (tmp_path / "usage.json").unlink(missing_ok=True)
            got = stock.find_stock_image("job interview", force=True, selected_provider="pexels")
            assert got is not None and "222" in got


def test_selection_is_not_always_the_first_match(monkeypatch, tmp_path):
    setup_env(monkeypatch, tmp_path)
    seen = set()
    with patch.object(stock, "_search", return_value=[photo(111), photo(222), photo(333)]), \
         patch("stable_image_hosting.host_permanently", side_effect=fake_host), \
         patch.object(stock, "_duplicate_on_site", return_value=False):
        for _ in range(60):
            (tmp_path / "usage.json").unlink(missing_ok=True)
            got = stock.find_stock_image("job interview", force=True, selected_provider="pexels")
            seen.add(got)
    assert len(seen) >= 2


def test_industrial_visa_articles_do_not_get_a_job_interview_photo():
    from editorial_topic_scope import stock_query
    assert stock_query("E-9 quota changes manufacturing hiring", "") == "factory workers"
    assert stock_query("Korea job interview preparation", "") == "job interview"
