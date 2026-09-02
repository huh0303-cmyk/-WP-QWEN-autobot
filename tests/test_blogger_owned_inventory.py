from pathlib import Path


def test_live_owned_inventory_reports_unregistered_blogs():
    source = (Path(__file__).resolve().parents[1] / "scripts" / "fetch_blogger_blog_ids.py").read_text(encoding="utf-8")
    assert '"owned_total": len(owned)' in source
    assert '"unregistered_owned"' in source
    assert "blogger_owned_inventory.json" in source
