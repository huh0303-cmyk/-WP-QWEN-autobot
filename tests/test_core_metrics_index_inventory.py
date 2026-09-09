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
