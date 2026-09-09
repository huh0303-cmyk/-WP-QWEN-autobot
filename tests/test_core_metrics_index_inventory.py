import sys
from pathlib import Path
from unittest.mock import Mock
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import core_metrics_gsc as metrics


def response(total, links):
    result = Mock()
    result.headers = {"X-WP-Total": str(total)}
    result.json.return_value = [{"link": link} for link in links]
    return result


def test_inventory_uses_all_pages(monkeypatch):
    calls = Mock(side_effect=[response(3, ["https://site/a", "https://site/b"]), response(3, ["https://site/c"])])
    monkeypatch.setattr(metrics.requests, "get", calls)
    assert metrics.published_wordpress_urls("https://site") == ["https://site/a", "https://site/b", "https://site/c"]
    assert calls.call_args.kwargs["params"]["page"] == 2


def test_changed_inventory_cannot_claim_complete_count(monkeypatch):
    monkeypatch.setattr(metrics.requests, "get", Mock(side_effect=[response(3, ["a", "b"]), response(4, ["c", "d"])]))
    with pytest.raises(ValueError):
        metrics.published_wordpress_urls("https://site")


def test_failed_inspection_does_not_reuse_old_zero():
    row = {"indexed": 0, "indexed_delta": 0, "index_checked_at": "yesterday", "total_posts": 283}
    metrics.unavailable(row, "No permission")
    assert row["indexed"] is None and row["indexed_delta"] is None
    assert row["index_unknown"] == 283 and row["index_partial"]


def test_parallel_refresh_keeps_unknown_separate(monkeypatch):
    for key in ("GOOGLE_METRICS_CLIENT_ID", "GOOGLE_METRICS_CLIENT_SECRET", "GOOGLE_METRICS_REFRESH_TOKEN"):
        monkeypatch.setenv(key, "test")
    def get(url, **kwargs):
        result = Mock()
        result.json.return_value = {"siteEntry": [{"siteUrl": "https://site/"}]}
        return result
    def post(url, **kwargs):
        result = Mock()
        if "oauth2" in url:
            result.json.return_value = {"access_token": "test"}
        else:
            verdict = {"a": "PASS", "b": "NEUTRAL", "c": "VERDICT_UNSPECIFIED"}[kwargs["json"]["inspectionUrl"].rsplit("/", 1)[1]]
            result.json.return_value = {"inspectionResult": {"indexStatusResult": {"verdict": verdict}}}
        return result
    monkeypatch.setattr(metrics.requests, "get", get)
    monkeypatch.setattr(metrics.requests, "post", post)
    report = {"generated_at": "2026-09-10", "records": [{"platform": "blogger", "url": "https://site", "total_posts": 3,
              "published_urls": ["https://site/a", "https://site/b", "https://site/c"], "errors": []}]}
    row = metrics.refresh(report, {"days": {}})["records"][0]
    assert (row["indexed"], row["index_unindexed"], row["index_unknown"]) == (1, 1, 1)
    assert row["index_partial"] and row["indexed_delta"] is None
